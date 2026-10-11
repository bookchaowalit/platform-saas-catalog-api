# SaaS Catalog API v1 contract

`schema_version: solo-empire.saas-catalog.v1`

Read-only projection of the `solo-empire.free-saas-catalog.v1` file at
[`data/free-saas-master-catalog-2026.json`](../data/free-saas-master-catalog-2026.json) (snapshot of solo-empire `systems/cloud-platform/free-saas-master-catalog-2026.json`).
Values are a dated snapshot; verify current limits and terms before activating
any provider.

## Routes

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Liveness and schema version |
| `GET` | `/api/v1/saas` | Summary, signals, starter stacks, and one page of services |

Optional filters: `category` (exact), `card` (`no_card` / `card_required` /
`verify`), `commercial` (`yes` / `verify`), `q` (case-insensitive substring
over id, service, subcategory, best use case, and replaces; max 80
characters), `limit` (1–100, default 30), and `offset` (0–5000). Invalid
values return `400`; other methods return `405`.

## Response fields

- `source`: catalog `path`, `snapshot_date`, `catalog_date`,
  `rows_requiring_current_limit_verification`, and file `modified_at`.
- `summary` (unfiltered except `services_matched`): `services_total`,
  `services_matched`, `categories`, `no_card`, `commercial_yes`,
  `needs_verification` (card bucket `verify`).
- `signals`: unfiltered `{value, count}` lists for `categories`, `card`,
  `commercial`, and `lock_in` (vendor lock-in risk).
- `starter_stacks`: `use_case`, `layer`, `primary_free_option`, `fallback_1`,
  `fallback_2`, `why` (an em dash placeholder becomes `null`).
- `services`: the catalog's text columns (each capped at 400 characters),
  `official_url` (HTTPS only, otherwise `null`), `card_bucket`, and
  `commercial_bucket`.

## Boundary

- Snapshot metadata only: no credential, provider call, or activation.
- Errors use `{"error": {"code", "message"}}`; a missing file or unexpected
  catalog contract returns `503 catalog_unavailable`.

## Authorization, readiness and snapshot revision

Production GET reads require owner-scoped RS256 JWT authorization using
`SAAS_CATALOG_API_AUTH_ISSUER`, `SAAS_CATALOG_API_AUTH_PUBLIC_KEY`, and
`SAAS_CATALOG_API_AUTH_SUBJECTS`. Required audience is `saas-catalog-api`, scope is
`saas:read`, tenant is `owner`, and subject is an allowed OIDC owner.
Required `iat/nbf/exp/jti` constrain lifetime to 120 seconds (5 seconds leeway).
See [runtime configuration](../README.md#scoped-authorization-and-readiness).
Errors keep the v1 envelope: 401 invalid token, 403 owner/tenant/scope denial,
503 missing or invalid JWT configuration. Static tokens are local-development only.

`GET /health` remains public liveness. `GET /ready` returns safe
`status`, `source` (available/unavailable), and `auth`
(ready/development/disabled); 200 requires parsed source and configured JWT,
otherwise 503. No metadata rows appear in readiness responses.
`source.revision` is the SHA-256 source checksum, an additive v1
field. Source date and reload semantics remain unchanged.
