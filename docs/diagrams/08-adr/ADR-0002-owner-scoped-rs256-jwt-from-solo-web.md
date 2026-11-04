# ADR-0002 — Owner-scoped RS256 service JWT from Solo Web, verified with a local key

- Status: accepted (retro-documented)
- Date of decision: 2026-10-04 (`d5a425f` "prepare authenticated Solo Web and independent service pilots")

## Context

API ถูกเรียกผ่าน BFF ของ Solo Web และต้องไม่เปิดสาธารณะ

## Decision

- ใช้ vendored `service_auth` (สำเนาของ `bookchaowalit/platform-auth-sdk`) ตรวจ JWT RS256 ด้วย PEM public key ที่ตั้งใน env (`SAAS_CATALOG_API_AUTH_PUBLIC_KEY`, ≥ 2048 bit) ไม่ดึง JWKS และปฏิเสธ header `jku`, `jwk`, `x5u`, `x5c`, `crit`
- claim ที่บังคับ: iss, aud, sub, tenant_id, scope, iat, nbf, exp, jti; `aud=saas-catalog-api`, `scope=saas:read`, `tenant_id=owner`, sub อยู่ใน `SAAS_CATALOG_API_AUTH_SUBJECTS`; อายุ ≤ 120 s, leeway 5 s
- static bearer (`SAAS_CATALOG_API_TOKEN`) ใช้ได้เฉพาะ `environment=development` และ policy ยังไม่ configured; non-loopback host บังคับ production และต้องมี policy ที่ ready ไม่งั้น process exit
- MCP mint token เองอายุ 60 s ด้วย signing key ของ Solo Web แทนการถือ credential ระยะยาว

## Consequences

- หมุน key = เปลี่ยน env + restart; signature เก่าใช้ไม่ได้
- ไม่มี revocation list / jti replay check (jti ถูกตรวจแค่รูปแบบ)
- signing key ของ Solo Web บนเครื่อง owner mint token ให้ทุก service ได้ (README "Trade-off")

## Evidence

`vendor/service-auth/service_auth/__init__.py`, `server.py` (`_check_read_auth`, `main`), `saas_catalog_mcp.py` (`mint`), `README.md` "Scoped authorization and readiness", `contracts/saas-catalog.v1.md`, `tests/test_server.py`, `tests/test_mcp.py`
