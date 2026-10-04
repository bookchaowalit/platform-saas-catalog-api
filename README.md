# Solo Empire SaaS Catalog API

`saas-catalog-api` is a small read-only backend that pages and filters
[`systems/cloud-platform/free-saas-master-catalog-2026.json`](../../systems/cloud-platform/free-saas-master-catalog-2026.json)
for the `/saas` module of [`apps/solo-web`](../../apps/solo-web/). The catalog
JSON stays canonical (regenerate it with the existing catalog tooling); the
service reloads when the file changes and never activates a provider.

The free-text credit-card column is collapsed into `no_card` (exactly "No"),
`card_required` ("Yes…" or "Billing…"), and `verify` (everything else), so the
UI never presents an unclear row as card-free.

## Run

From the repository root:

```bash
python3 -m pip install ./packages/service-auth ./services/saas-catalog-api
python3 services/saas-catalog-api/server.py
```

The default listener is `http://127.0.0.1:3490`. Configure
`SAAS_CATALOG_API_HOST`, `SAAS_CATALOG_API_PORT`,
`SAAS_CATALOG_API_CATALOG_PATH`, and `SAAS_CATALOG_API_CORS_ORIGINS` as needed.
A non-loopback host requires valid scoped JWT configuration and enforces production authorization.

```text
GET /health
GET /api/v1/saas?category=&card=&commercial=&q=&limit=&offset=
```

See the [SaaS Catalog API v1 contract](contracts/saas-catalog.v1.md).

## Deploy

This folder is an independent deploy unit described by [`service.yaml`](service.yaml).
Build from the repository root; the image contains only this service and the
files listed in `data.reads`, plus the declared reusable `service-auth` dependency:

```bash
docker build -f services/saas-catalog-api/Dockerfile -t solo-empire/saas-catalog-api .
```

The image enforces scoped JWT authorization and binds `0.0.0.0`.
`deploy.target` stays `unassigned` until the parent deployment configuration selects a target. `task services:check` reports drift from the
[decentralized services spec](../../docs/superpowers/specs/2026-10-04-decentralized-services-and-storage-design.md).

## Test

```bash
python3 services/saas-catalog-api/tests/test_server.py
```

## Scoped authorization and readiness

[Railway configuration](railway.toml) selects the Dockerfile and `/ready`
health check (30 seconds), with at most 3 restarts after failure. It declares
no region, resources, runtime secret values, or existing cloud deployment.

Configure `SAAS_CATALOG_API_AUTH_ISSUER` with the exact HTTPS origin of Solo Web,
`SAAS_CATALOG_API_AUTH_PUBLIC_KEY` with its PEM RSA public key (at least 2048 bits),
and `SAAS_CATALOG_API_AUTH_SUBJECTS` with the comma-separated allowed OIDC owner
subjects. See [.env.example](.env.example); provide configuration at runtime.
The signing private key belongs only to Solo Web and is never copied to this image.

Reads require an RS256 JWT: `iss` matches that origin, `aud=saas-catalog-api`,
`sub` is allowed, `tenant_id=owner`, `scope=saas:read`, and
`iat`, `nbf`, `exp`, `jti` are required. Lifetime is at most 120 seconds
with 5 seconds clock leeway. The verifier uses only the configured local key
and rejects remote key headers. Key rotation replaces the configured public
key and restarts the service; old signatures then fail. Missing configuration
returns `503 reads_disabled`; invalid tokens return `401 unauthorized`;
a valid token for another owner/tenant/scope returns `403 forbidden`.
Production never accepts `SAAS_CATALOG_API_TOKEN`. Partial JWT configuration
fails closed even in development.

`GET /health` is public liveness. `GET /ready` returns 200 only when the
source snapshot parses and JWT configuration is valid; otherwise it returns
503 with safe source/auth states. A local fixture with auth disabled reports
`auth=development`, not deployment readiness. Metadata contains a SHA-256
`revision` of its source snapshot and preserves its original dates.
Atomic source replacement triggers reload. This does not assert provider
freshness or a live deployment.

The listener accepts PaaS `PORT`; explicit `SAAS_CATALOG_API_PORT` or `--port`
takes precedence. Package installation is required; no sibling source-path
injection is used at runtime.
