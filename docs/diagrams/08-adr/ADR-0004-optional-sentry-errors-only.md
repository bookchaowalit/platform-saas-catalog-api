# ADR-0004 — Optional Sentry, errors only, no tracing and no PII

- Status: accepted (retro-documented)
- Date of decision: 2026-10-18 (`f0a2e0d` #2, `4d4952e` #3)

## Decision

- `init_sentry()` ทำงานเฉพาะเมื่อมี `SENTRY_DSN`; release = `RAILWAY_GIT_COMMIT_SHA` หรือ `SENTRY_RELEASE`
- `traces_sample_rate=None` (tracing ปิดสนิท), `send_default_pii=False`, `include_local_variables=False`, `max_request_body_size="never"`, LoggingIntegration ปิดทั้ง breadcrumbs และ events
- `before_send=_scrub_event`: ตัด request เหลือ method, ลบ `extra`, breadcrumbs `data`, `dynamic_sampling_context`, scrub URL password / bearer / JWT
- `server.py` เรียก `capture(exc)` เฉพาะใน except สุดท้าย (500 `internal_error`)

## Consequences

- 503 `catalog_unavailable` (OSError, ValueError, TypeError, KeyError) และ 4xx ไม่ถูกส่งไป Sentry: snapshot เสียใน production จะไม่มี event ใน Sentry
- ไม่มี performance data

## Evidence

`_sentry.py`, `server.py` (`handle`), `tests/test_sentry.py`, `README.md`
