# Core 22 SDLC diagram pack — platform-saas-catalog-api

ชุดภาพ Core 22 ตาม SDLC Diagram Catalog v2 วาดจากโค้ดและ config ใน repo นี้ (ณ `origin/main` `21d5d41`, 2026-10-24) repo นี้คือ read-only Python stdlib HTTP API (`server.py`) ที่กรองและแบ่งหน้า JSON snapshot `data/free-saas-master-catalog-2026.json` (648 services) ให้ Solo Web `/saas` บน Railway พร้อม MCP server `saas-catalog-mcp` สำหรับ agent ของ owner ไม่มี database

ทุกไฟล์มี `Sources:` ใต้ภาพ และ "Open questions" สำหรับสิ่งที่ยืนยันจากโค้ดไม่ได้ เอกสารที่มีอยู่แล้วถูก link (reuse) ไม่ได้คัดลอก: [`PRODUCT.md`](../../PRODUCT.md), [`README.md`](../../README.md), [`contracts/saas-catalog.v1.md`](../../contracts/saas-catalog.v1.md), [`specs/001-l2-baseline/spec.md`](../../specs/001-l2-baseline/spec.md), [`DOCPACK/00-product-card.md`](../../DOCPACK/00-product-card.md)

| # | Item | Status | File | Sources read |
|---|---|---|---|---|
| 01 | Business process As-Is / To-Be | done (To-Be = open question) | [01-business-process.md](01-business-process.md) | `server.py`, `scripts/validate_catalog.py`, `Dockerfile`, `PRODUCT.md`, Solo Web `lib/backends.ts` |
| 02 | Use cases | done | [02-use-cases.md](02-use-cases.md) | `server.py`, `vendor/service-auth`, `saas_catalog_mcp.py` |
| 03 | User flows | done | [03-user-flows.md](03-user-flows.md) | `server.py`, `saas_catalog_mcp.py`, Solo Web `modules/saas/api.ts` |
| 04 | Traceability (RTM) | done (SPEC-001 AC-01..11 + PRODUCT.md) | [04-traceability.md](04-traceability.md) | `specs/001-l2-baseline/spec.md`, `PRODUCT.md`, `tests/`, `ci.yml` |
| 05 | C4 Context | done | [05-c4-context.md](05-c4-context.md) | `server.py`, `README.md`, uptime-worker `targets.ts`, api-gateway `routes.json` |
| 06 | C4 Container | done | [06-c4-container.md](06-c4-container.md) | `Dockerfile`, `pyproject.toml`, `saas_catalog_mcp.py` |
| 07 | C4 Component | done | [07-c4-component.md](07-c4-component.md) | `server.py`, `vendor/service-auth`, `_sentry.py`, `saas_catalog_mcp.py` |
| 08 | ADRs | done (5) | [08-adr/](08-adr/) | `server.py`, `vendor/service-auth`, `railway.toml`, `.railway/railway.ts`, `_sentry.py`, `ci.yml`, `git log` |
| 09 | ERD | done (snapshot file model, no DB) | [09-erd.md](09-erd.md) | `data/free-saas-master-catalog-2026.json`, `server.py` |
| 10 | Sequences | done (3) | [10-sequences.md](10-sequences.md) | `server.py`, `saas_catalog_mcp.py`, `vendor/service-auth`, `railway.toml` |
| 11 | State machines | done (4) | [11-state-machines.md](11-state-machines.md) | `server.py`, `vendor/service-auth`, deployments API |
| 12 | API & integrations | done (reuses contract) | [12-api-integration.md](12-api-integration.md) | `server.py`, `contracts/saas-catalog.v1.md` |
| 13 | Threat model | done | [13-threat-model.md](13-threat-model.md) | `server.py`, `vendor/service-auth`, `saas_catalog_mcp.py`, `_sentry.py`, branch protection API |
| 14 | Backup & DR | done (no DB; RTO/RPO not defined) | [14-backup-dr.md](14-backup-dr.md) | `service.yaml`, `Dockerfile`, `.railway/railway.ts`, `README.md` |
| 15 | CI/CD pipeline | done | [15-cicd-pipeline.md](15-cicd-pipeline.md) | `ci.yml`, platform-ci-workflows @ `87dc5e1c`, `renovate.json`, `gh run list` |
| 16 | Deployment | done | [16-deployment.md](16-deployment.md) | `railway.toml`, `.railway/railway.ts`, `Dockerfile`, `.env.example`, `PRODUCT.md`, live `curl` |
| 17 | Test coverage matrix | done (gaps marked) | [17-test-coverage-matrix.md](17-test-coverage-matrix.md) | `tests/*.py`, `pyproject.toml`, `ci.yml` |
| 18 | Git & release workflow | done | [18-git-release-workflow.md](18-git-release-workflow.md) | `git log`, `gh pr list`, branch protection API |
| 19 | Service dependency map | done | [19-service-dependency-map.md](19-service-dependency-map.md) | `server.py`, `pyproject.toml`, `uv.lock`, sibling repos |
| 20 | Observability | done (gaps marked) | [20-observability.md](20-observability.md) | `server.py`, `_sentry.py`, `Dockerfile`, uptime-worker `targets.ts` |
| 21 | Incident response | done (no repo runbook) | [21-incident-response.md](21-incident-response.md) | `README.md`, `railway.toml`, `_sentry.py`, uptime-worker |
| 22 | DORA | done (4/5 computed, FDRT not computable) | [22-dora.md](22-dora.md) | GitHub deployments API, `gh run list`, `git log` |

## ADR list

- [ADR-0001](08-adr/ADR-0001-stdlib-http-server-over-json-snapshot.md) Stdlib HTTP server over a shipped JSON snapshot, no database
- [ADR-0002](08-adr/ADR-0002-owner-scoped-rs256-jwt-from-solo-web.md) Owner-scoped RS256 service JWT from Solo Web, local key
- [ADR-0003](08-adr/ADR-0003-railway-docker-serverless-cd-wait-for-ci.md) Railway Docker, serverless sleep, CD with Wait for CI
- [ADR-0004](08-adr/ADR-0004-optional-sentry-errors-only.md) Optional Sentry, errors only
- [ADR-0005](08-adr/ADR-0005-shared-ci-workflows-sha-pinned.md) Shared CI + security workflows, SHA-pinned

## Key gaps found

- No tests for CORS / `OPTIONS` / the 500 `internal_error` path; `vendor/service-auth/tests` not run by CI
- Only the 500 path reaches Sentry; 503 `catalog_unavailable` and `reads_disabled` are silent; no access logs, no metrics
- Uptime probes `/health` (no dependency check), not `/ready`
- No branch protection on `main`; no rate limit
- `service.yaml` `deploy.target: unassigned` is stale vs Railway
- Snapshot refresh owner and cadence undefined
