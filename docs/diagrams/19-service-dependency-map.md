# 19 — Service dependency map

```mermaid
flowchart LR
    subgraph up["Upstream callers (depend on this API)"]
        SW["Solo Web /saas (life-dashboard-web)"]
        MCP["saas-catalog-mcp"]
        UPW["platform-uptime-worker"]
        GW["platform-api-gateway route saas-catalog"]
    end
    API["saas-catalog-api on Railway"]
    subgraph down["Runtime dependencies"]
        FILE[("Snapshot JSON in image")]
        ENVV["Railway variables: auth issuer, public key, subjects, CORS"]
        RWY["Railway platform: build, healthcheck, sleep"]
        SEN["Sentry (optional)"]
    end
    subgraph lib["Libraries (uv.lock)"]
        SA["solo-empire-service-auth (vendored, PyJWT + cryptography)"]
        SDK["sentry-sdk"]
        MCPL["mcp + httpx (MCP only)"]
    end
    SW --> API
    MCP --> API
    UPW --> API
    GW -.-> API
    API --> FILE
    API --> ENVV
    API --> RWY
    API -.-> SEN
    API --> SA
    API --> SDK
    MCP --> MCPL
    SW -.->|"trust: issuer + key pair"| ENVV
```

ไม่มี DB, cache, queue หรือ CDN API ทำงานได้ด้วย snapshot + env เท่านั้น; Sentry ล่มไม่กระทบ request (เรียกเฉพาะ path 500)

Sources: `server.py`, `_sentry.py`, `saas_catalog_mcp.py`, `pyproject.toml`, `uv.lock`, `Dockerfile`, `railway.toml`, platform-uptime-worker `src/targets.ts`, platform-api-gateway `routes.json`, Solo Web `lib/backends.ts` (read-only)
