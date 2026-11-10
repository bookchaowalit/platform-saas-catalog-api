# 21 — Incident response

ไม่มี runbook เฉพาะ repo นี้ flow ด้านล่างประกอบจาก alert channel และ rollback ที่พบจริง

```mermaid
flowchart TD
    A1["platform-uptime-worker: /health fails, Telegram alert"] --> T
    A2["Sentry: new 500 internal_error issue"] --> T
    A3["Owner: Solo Web /saas shows error"] --> T
    A4["Railway: deploy healthcheck /ready fails, previous deployment stays"] --> T
    T["Triage: curl /health and /ready"] --> Q{"Which state?"}
    Q -->|"/ready 503 source unavailable"| F1["Snapshot broken: run scripts/validate_catalog.py, revert data commit"]
    Q -->|"/ready 503 auth disabled"| F2["Fix SAAS_CATALOG_API_AUTH_* in Railway, restart"]
    Q -->|"401 or 403 from Solo Web"| F3["Check issuer, public key pair, subjects vs Solo Web"]
    Q -->|"process down or 5xx"| F4["Railway: redeploy previous deployment"]
    F1 --> FIX["Fix on main, CI green, Railway deploys"]
    F2 --> V
    F3 --> V
    F4 --> V
    FIX --> V["Verify /health 200, /ready 200, /saas loads"]
    V --> PM["Postmortem: not defined in this repo"]
```

| Channel | Source |
|---|---|
| Telegram via platform-uptime-worker | platform-uptime-worker `src/targets.ts` (target `saas-catalog-api`) and its `README.md` (read-only) |
| Sentry | `_sentry.py`, `README.md` |
| Railway deploy result | `.railway/railway.ts`, `README.md` "Deploy" |

Sources: `README.md`, `.railway/railway.ts`, `_sentry.py`, `server.py`, `scripts/validate_catalog.py`, `vendor/service-auth/service_auth/__init__.py`, platform-uptime-worker `src/targets.ts` (read-only)

## Open questions

- ไม่มี postmortem template หรือ incident log ใน repo นี้; ใช้ของ central หรือไม่
- ใครรับ alert Sentry ของ project นี้ (ไม่มีข้อมูลใน repo)
