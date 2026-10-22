# Product

<!-- impeccable:product-schema 1 -->

## Platform

api

## Users

- The Solo Empire owner, through the `/saas` module of Solo Web
  (`bookchaowalit/life-dashboard-web`), which calls this API through its BFF with a short-lived
  service JWT.
- The owner's agents, through this repository's read-only MCP server (`saas-catalog-mcp`, tools
  `saas.list` and `saas.get`).

## Product Purpose

Pick free SaaS providers for a new project from one curated snapshot: what each service gives for
free, whether it needs a credit card, whether commercial use is allowed, its lock-in risk and what
it replaces, plus starter stacks per use case. The free-text card column is collapsed into
`no_card`, `card_required` and `verify`, so an unclear row is never shown as card-free.

Success: the `/saas` page filters the snapshot by category, card, commercial use and text, and
every provider a project adopts was checked against its current terms first.

## Positioning

A read-only projection of a JSON snapshot shipped in this repository, not a provider
integration: it holds no credentials, calls no provider and activates nothing, and every payload
says to verify current limits and terms before activating a provider. No database.

## Operating Context

- Production: `https://solo-saas-catalog-production.up.railway.app` (`/health`; Railway health
  check `/ready`), Railway project `platform-saas-catalog-api`, service `solo-saas-catalog`,
  Singapore, serverless (the first read after idle is slower). Deployed when `main` changes,
  after CI and security checks pass.
- Snapshot today (`data/free-saas-master-catalog-2026.json`, dated 2026-08-30): 648 services in
  29 categories, 18 starter stacks; 118 `no_card`, 18 `card_required`, 512 `verify`; 159
  commercial `yes`. The workbook marks 496 rows as needing current-limit verification.
- Monitored by `platform-uptime-worker` (`saas-catalog-api`); errors go to Sentry when
  `SENTRY_DSN` is set, without personal data.
- Who refreshes the snapshot and how often [ต้องยืนยัน].

## Capabilities and Constraints

- `GET /health`: public liveness. `GET /ready`: 200 only when the snapshot loads and the JWT
  configuration is valid.
- `GET /api/v1/saas?category=&card=&commercial=&q=&limit=&offset=`: summary (total, matched,
  categories, no-card, commercial yes, needs verification), category/card/commercial/lock-in
  signals, starter stacks, source metadata (revision, snapshot and catalog dates) and one page of
  services. `category` is an exact match; `card` is one of `no_card`, `card_required`, `verify`;
  `commercial` one of `yes`, `verify`; `q` (at most 80 characters) matches id, service,
  subcategory, best use case and replaces, case-insensitive. `limit` 1–100 (default 30), `offset`
  0–5,000. Anything else is a 400 with a stable code.
- Buckets: `no_card` only for a plain "No"; `card_required` for text starting with "Yes" or
  "Billing"; everything else `verify`. Commercial `yes` only for a plain "Yes".
- Projection: text fields cut to 400 characters, ids to 80, starter-stack fields to 300 (a dash
  or blank is null); `official_url` only when it is HTTPS (at most 300 characters).
- A snapshot with another contract, duplicate ids or that cannot be read makes the API answer 503
  `catalog_unavailable` instead of a partial list; rows without an id are skipped. The snapshot
  reloads when its file changes.
- Reads need an RS256 JWT from Solo Web (`aud=saas-catalog-api`, `scope=saas:read`,
  `tenant_id=owner`, allowlisted `sub`, at most 120 seconds); otherwise 503 `reads_disabled`, 401
  or 403. Other methods are 405; unexpected errors are a generic 500 reported to Sentry.
- Out of scope: live provider limits or prices, sign-up, and editing the catalog through the API.

## Measures

- Snapshot load failures in production (503 `catalog_unavailable`; target: 0).
- 5xx rate and uptime on `/health` (Sentry and `platform-uptime-worker`).
- Snapshot age (`source.snapshot_date`) and the share of `verify` rows [ต้องยืนยัน: no target set].
