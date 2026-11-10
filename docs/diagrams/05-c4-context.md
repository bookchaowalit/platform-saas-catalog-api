# 05 — C4 Context

```mermaid
C4Context
    title System Context - saas-catalog-api
    Person(owner, "Owner", "Solo Empire owner")
    Person(agent, "Owner agent", "Local AI agent over MCP stdio")
    System(api, "saas-catalog-api", "Read-only projection of the free SaaS catalog snapshot")
    System_Ext(solo, "Solo Web", "life-dashboard-web, /saas module and BFF, signs service JWTs")
    System_Ext(railway, "Railway", "Hosts the container, healthcheck /ready, serverless sleep")
    System_Ext(github, "GitHub", "Repo, Actions CI and security, deployment records")
    System_Ext(sentry, "Sentry", "Error events when SENTRY_DSN is set")
    System_Ext(uptime, "platform-uptime-worker", "Hourly probe of /health")
    System_Ext(gateway, "platform-api-gateway", "Route saas-catalog registered in routes.json")
    System_Ext(gen, "Snapshot generator", "Outside this repo, writes the JSON snapshot")
    Rel(owner, solo, "Uses /saas page")
    Rel(solo, api, "GET /api/v1/saas with RS256 JWT", "HTTPS")
    Rel(agent, api, "GET /api/v1/saas via saas-catalog-mcp", "HTTPS")
    Rel(uptime, api, "GET /health", "HTTPS")
    Rel(railway, api, "Runs and probes /ready")
    Rel(github, railway, "main after CI passes")
    Rel(api, sentry, "Unexpected 500 errors", "HTTPS")
    Rel(gen, github, "Commits data/ snapshot")
    Rel(gateway, api, "Proxies /v1/saas-catalog/*", "HTTPS")
```

หมายเหตุ: ไม่มีระบบ provider ภายนอกใด ๆ ใน context นี้ (API ไม่เรียก SaaS ที่อยู่ในแค็ตตาล็อก)

Sources: `server.py`, `saas_catalog_mcp.py`, `_sentry.py`, `.railway/railway.ts`, `.railway/railway.ts`, `README.md`, `PRODUCT.md`, platform-uptime-worker `src/targets.ts`, platform-api-gateway `routes.json` + `README.md`, Solo Web `lib/backends.ts` (all read-only)

## Open questions

- gateway ตรวจ token จาก issuer platform-identity / empire-platform แล้วส่ง token ต่อ แต่ API นี้รับเฉพาะ `iss` = Solo Web origin (`SAAS_CATALOG_API_AUTH_ISSUER`) ดังนั้น request ผ่าน gateway น่าจะได้ 401; มี consumer ใช้ route `saas-catalog` ของ gateway จริงหรือไม่
