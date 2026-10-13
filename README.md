# platform-saas-catalog-api
Moved out of solo-empire `services/saas-catalog-api` on 2026-10-11 with its history (subtree split). `vendor/service-auth` is a vendored copy of `bookchaowalit/service-auth`.

**Ownership.** `data/free-saas-master-catalog-2026.json` is the deployable snapshot this repository ships (point `SAAS_CATALOG_API_CATALOG_PATH` at another path to override). The snapshot is produced elsewhere and written into this repository; check its shape with:

```bash
python3 scripts/validate_catalog.py             # contract, non-empty services, unique ids
```

Test: `PYTHONPATH=vendor/service-auth python3 -m unittest discover -s tests -v`

---

# Solo Empire SaaS Catalog API

`saas-catalog-api` is a small read-only backend that pages and filters
[`data/free-saas-master-catalog-2026.json`](data/free-saas-master-catalog-2026.json)
for the `/saas` module of `solo-web` (`bookchaowalit/owner-web`). The catalog
JSON snapshot is written into this repository by its generator; the
service reloads when the file changes and never activates a provider.

The free-text credit-card column is collapsed into `no_card` (exactly "No"),
`card_required` ("Yes…" or "Billing…"), and `verify` (everything else), so the
UI never presents an unclear row as card-free.

## Run

From this repository root:

```bash
python3 -m pip install ./vendor/service-auth .
python3 server.py
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
The repository root is the Docker build context (service + `vendor/service-auth` + the `data/` catalog snapshot).

```bash
docker build -t solo-saas-catalog .
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

## MCP server (`saas-catalog-mcp`)

`saas_catalog_mcp.py` is this service's MCP server (stdio). It is read-only: `saas.list` (category, card, commercial, text; paged) and `saas.get` (one service by id, filtered from the list because the API has no detail route). Every tool is one HTTP call to the
deployed or local API; there is no file or database access, no tool takes an identity argument (actor, workspace,
tenant, token, ...), unknown arguments are rejected before any HTTP call, and errors are a fixed message from the HTTP
status (for example `403: forbidden`), never upstream text.

**Auth (backend auth is unchanged).** The API accepts only a 120-second RS256 service JWT from Solo Web
(`aud=saas-catalog-api`, `scope=saas:read`, `tenant_id=owner`, allowlisted owner `sub`). For local use the MCP mints that same
token itself, per call, as the Solo Web BFF does: it reads Solo Web's signing key and the owner subject from files
(never printed or returned), signs a 60-second token fixed to this service's audience and scope, and sends it as the
bearer. No tool argument can change the subject, audience or scope.

| Variable | Meaning |
|---|---|
| `EMPIRE_SAAS_CATALOG_API` | API base URL (env, else `~/.config/empire-platform/client.env`); https, http only on loopback |
| `SOLO_WEB_PUBLIC_ORIGIN` | the JWT issuer: Solo Web's public https origin (not a secret) |
| `SOLO_WEB_SERVICE_KEY_FILE` | default `~/.config/solo-web/service-private.pem`, mode 600 |
| `SOLO_WEB_OWNER_SUBJECTS_FILE` | default `~/.config/solo-web/owner-subjects.txt`, mode 600; the first subject is used |
| `EMPIRE_TOKEN` | optional ready service JWT; used instead of minting (the key is then not read) |

Trade-off: the signing key can mint tokens for every Solo Web service, so only run this MCP as the owner on a machine
that already holds that key. A narrower alternative, if the key must not sit beside agents, is a Solo Web owner-session
endpoint that issues a per-service token; set `EMPIRE_TOKEN` from it and the key is never read.

Run: `uv venv .venv && uv pip install ./vendor/service-auth -e ".[dev]"`, then `.venv/bin/saas-catalog-mcp` (see `.mcp.json`).
Tests: `.venv/bin/pytest tests/test_mcp.py` (fake HTTP transport and a throwaway key; the minted token is checked with
the vendored `service_auth` verifier the API uses).
