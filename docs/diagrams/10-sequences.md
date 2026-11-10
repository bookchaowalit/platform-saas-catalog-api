# 10 — Sequences

## S1 — Solo Web reads the catalog (happy path + error branches)

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser /saas
    participant W as Solo Web BFF
    participant H as SaasCatalogRequestHandler
    participant A as SaasCatalogApi
    participant P as service_auth
    participant S as CatalogStore
    B->>W: GET /api/saas/v1/saas?q=&card=&offset=
    W->>W: sign RS256 JWT aud saas-catalog-api scope saas:read
    W->>H: GET /api/v1/saas Authorization Bearer (timeout 8 s)
    alt Origin header set and not in allowlist
        H-->>W: 403 origin_not_allowed
    else
        H->>A: handle("GET", path, headers)
        A->>P: check_read_auth(policy, headers, environment)
        alt policy not ready
            P-->>A: AuthError 503 reads_disabled
        else invalid token
            P-->>A: AuthError 401 unauthorized
        else wrong tenant, sub or scope
            P-->>A: AuthError 403 forbidden
        end
        A->>A: query_value / bounded_int (400 on bad input)
        A->>S: snapshot()
        alt mtime changed or first load
            S->>S: read_text, json.loads, contract + duplicate check, project rows, sha256
        end
        S-->>A: services, stacks, metadata
        A->>A: filter, count summary and signals, slice offset..offset+limit
        A-->>H: Response 200 payload
        H-->>W: JSON, Cache-Control no-store, nosniff, CORS header if allowed origin
    end
    W-->>B: JSON
```

ไม่มี retry ทั้งฝั่ง server และ BFF ตามโค้ดที่อ่าน

Sources: `server.py`, `vendor/service-auth/service_auth/__init__.py`, Solo Web `lib/backends.ts`, `lib/auth.ts`, `modules/saas/api.ts` (read-only)

## S2 — MCP saas.get

```mermaid
sequenceDiagram
    autonumber
    participant G as Agent
    participant M as StrictMCPServer
    participant T as Toolbox
    participant K as mint()
    participant A as saas-catalog-api
    G->>M: call_tool saas.get {id}
    M->>M: SaasRef.model_validate (pattern, max 80)
    alt invalid
        M-->>G: ToolFailed invalid_arguments
    end
    M->>T: saas_get(a)
    T->>K: token()
    K->>K: EMPIRE_TOKEN or read key + subjects (mode 600) and sign 60 s JWT
    T->>A: GET /api/v1/saas?q=id&limit=100 (httpx timeout 30 s)
    alt httpx.HTTPError
        T-->>G: ToolFailed 503: unavailable
    else status >= 400
        T-->>G: ToolFailed status: reason
    end
    A-->>T: 200 page
    T->>T: find service with exact id
    alt found
        T-->>G: {service, source}
    else
        T-->>G: ToolFailed 404: not_found
    end
```

Sources: `saas_catalog_mcp.py`, `tests/test_mcp.py`

## S3 — Startup and readiness on Railway

```mermaid
sequenceDiagram
    autonumber
    participant R as Railway
    participant P as server.py main
    participant Pol as AuthPolicy
    participant S as CatalogStore
    R->>P: python /app/server.py (SAAS_CATALOG_API_HOST=0.0.0.0, ENV=production)
    P->>P: import: init_sentry() if SENTRY_DSN
    P->>P: SaasCatalogApi() builds AuthPolicy.from_env("SAAS_CATALOG_API_")
    P->>Pol: non-loopback host, so environment=production, ready?
    alt not ready
        P-->>R: parser.error, exit code 2
        R->>R: restart ON_FAILURE, max 3
    else ready
        P->>P: ThreadingHTTPServer.serve_forever on PORT
        R->>P: GET /ready (healthcheck timeout 30 s)
        P->>S: snapshot()
        alt loads and auth ready
            P-->>R: 200 ready
        else
            P-->>R: 503 not_ready
        end
    end
```

Sources: `server.py` (`main`), `Dockerfile`, `.railway/railway.ts`, `_sentry.py`, `vendor/service-auth/service_auth/__init__.py`
