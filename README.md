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
python3 services/saas-catalog-api/server.py
```

The default listener is `http://127.0.0.1:3490`. Configure
`SAAS_CATALOG_API_HOST`, `SAAS_CATALOG_API_PORT`,
`SAAS_CATALOG_API_CATALOG_PATH`, and `SAAS_CATALOG_API_CORS_ORIGINS` as needed.
A non-loopback host fails to start unless `SAAS_CATALOG_API_TOKEN` is set, and
`SAAS_CATALOG_API_ENV=production` refuses reads without a token.

```text
GET /health
GET /api/v1/saas?category=&card=&commercial=&q=&limit=&offset=
```

See the [SaaS Catalog API v1 contract](contracts/saas-catalog.v1.md).

## Test

```bash
python3 services/saas-catalog-api/tests/test_server.py
```
