# 03 — User flows

API ไม่มีหน้าเว็บ flow ด้านล่างจึงเป็น journey ของแต่ละ role ผ่าน route จริง

## Flow A — Owner บนหน้า /saas ของ Solo Web

```mermaid
flowchart TD
    A["Owner opens Solo Web /saas"] --> B["Browser calls /api/saas/v1/saas?filters"]
    B --> C["Solo Web BFF route /api/[service]/[...path] allows only GET v1/saas"]
    C --> D["BFF signs RS256 JWT aud saas-catalog-api scope saas:read"]
    D --> E["GET /api/v1/saas on Railway, BFF timeout 8 s"]
    E --> F{"Origin header present and not allowed?"}
    F -->|"yes"| F1["403 origin_not_allowed"]
    F -->|"no"| G{"Auth policy ready?"}
    G -->|"no"| G1["503 reads_disabled"]
    G -->|"yes"| H{"Token valid?"}
    H -->|"bad signature, claims, lifetime"| H1["401 unauthorized"]
    H -->|"wrong tenant, sub or scope"| H2["403 forbidden"]
    H -->|"ok"| I{"Query valid?"}
    I -->|"no"| I1["400 invalid_field / invalid_limit / invalid_offset"]
    I -->|"yes"| J{"Snapshot loads?"}
    J -->|"no"| J1["503 catalog_unavailable"]
    J -->|"yes"| K["200 overview with one page of services"]
    K --> L["Owner changes filter or offset, repeat"]
```

Sources: `server.py` (`_dispatch`, `handle`, `_overview`, `query_value`, `bounded_int`), `vendor/service-auth/service_auth/__init__.py`, Solo Web `lib/backends.ts`, `lib/auth.ts`, `modules/saas/api.ts` (life-dashboard-web `09c1001`, read-only)

## Flow B — Owner agent ผ่าน MCP

```mermaid
flowchart TD
    A["Agent calls tool saas.list or saas.get"] --> B{"Arguments match strict model?"}
    B -->|"no or unknown tool"| B1["ToolFailed invalid_arguments / unknown_tool, no HTTP call"]
    B -->|"yes"| C["mint: EMPIRE_TOKEN or sign 60 s JWT from key file"]
    C -->|"ConfigError"| C1["ToolFailed 401: unauthorized"]
    C --> D["httpx GET /api/v1/saas, timeout 30 s, no redirects"]
    D -->|"transport error"| D1["ToolFailed 503: unavailable"]
    D -->|"status >= 400"| D2["ToolFailed fixed text from status"]
    D -->|"200"| E{"Tool?"}
    E -->|"saas.list"| F["Return payload"]
    E -->|"saas.get: q=id, limit=100"| G{"Exact id in page?"}
    G -->|"yes"| H["Return service + source"]
    G -->|"no"| I["ToolFailed 404: not_found"]
```

Sources: `saas_catalog_mcp.py` (`StrictMCPServer.call_tool`, `Toolbox.call`, `build_server`, `mint`, `main`), `.mcp.json`, `tests/test_mcp.py`

## Flow C — Probe / operator

```mermaid
flowchart LR
    P["Probe"] --> H["GET /health"] --> H200["200 status ok, always (no dependency check)"]
    P --> R["GET /ready"] --> RQ{"snapshot parses AND auth policy ready?"}
    RQ -->|"yes"| R200["200 status ready"]
    RQ -->|"no"| R503["503 not_ready with source and auth state"]
```

Sources: `server.py`, `vendor/service-auth/service_auth/__init__.py` (`readiness`), `.railway/railway.ts`, `Dockerfile`

## Open questions

- ไม่มี retry ในทุก flow (BFF, MCP, server) ตามโค้ดที่อ่าน; ถ้า Railway serverless ตื่นช้ากว่า 8 s BFF จะ timeout หรือไม่ ยังไม่ได้วัด
