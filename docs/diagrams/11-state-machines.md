# 11 — State machines

ไม่มี entity ที่มี status field แบบ persisted (ไม่มี database) state ที่มีจริงในโค้ดคือ cache ของ snapshot, ผล readiness, การจัด bucket และ deployment status ที่ GitHub บันทึก

## CatalogStore cache

```mermaid
stateDiagram-v2
    [*] --> Empty
    Empty --> Loaded: snapshot() parses, contract ok, ids unique
    Empty --> Error: OSError or ValueError
    Loaded --> Loaded: snapshot() with same mtime, served from memory
    Loaded --> Loaded: mtime changed and new file valid, replace snapshot
    Loaded --> Error: mtime changed and file invalid or missing
    Error --> Loaded: next call finds a valid file
    Error --> Error: next call still fails
    note right of Error
        Request gets 503 catalog_unavailable.
        Old snapshot is kept in memory but not served
        because stat or parse raises first.
    end note
```

Sources: `server.py` (`CatalogStore.snapshot`, `handle` except branches), `tests/test_catalog_loading.py`

## Readiness (`GET /ready`)

```mermaid
stateDiagram-v2
    [*] --> Evaluate
    Evaluate --> Ready: source available AND auth ready
    Evaluate --> NotReady: otherwise
    state NotReady {
        [*] --> AuthDevelopment: development and policy not configured
        [*] --> AuthDisabled: policy configured but invalid, or production without policy
        [*] --> SourceUnavailable: snapshot raises
    }
    Ready --> [*]: 200 status ready
    NotReady --> [*]: 503 status not_ready
```

`auth=development` ก็ยังได้ 503 เสมอ (`ready = source_ready and auth_ready`)

Sources: `vendor/service-auth/service_auth/__init__.py` (`readiness`), `tests/test_server.py::test_readiness_and_remote_bind_fail_closed`

## Card bucket classification

```mermaid
stateDiagram-v2
    [*] --> Normalize: strip and lower credit_card_required
    Normalize --> no_card: equals "no"
    Normalize --> card_required: starts with "yes" or "billing"
    Normalize --> verify: anything else, including empty
```

Sources: `server.py` (`card_bucket`, `commercial_bucket`), `tests/test_card_and_commercial_buckets.py`

## Production deployment record (GitHub deployments, Railway)

```mermaid
stateDiagram-v2
    [*] --> in_progress: Railway starts deploy of main SHA
    in_progress --> success: healthcheck passed
    success --> inactive: next deployment succeeds
    inactive --> in_progress: redeploy of the same deployment
```

ค่าที่เห็นจริง: deployment `21d5d41` success 2026-10-24, inactive 2026-10-29 17:12 UTC, success อีกครั้ง 2026-10-30 18:48 UTC; ไม่เห็นสถานะ `failure` ใน 4 deployments

Sources: `gh api repos/bookchaowalit/platform-saas-catalog-api/deployments/<id>/statuses` (2026-11-04)

## Open questions

- อะไรทำให้ deployment `21d5d41` เป็น inactive 2026-10-29 แล้ว success ใหม่ 2026-10-30 (ไม่มี deployment record อื่นใน GitHub ช่วงนั้น: อาจเป็น redeploy/variable change ใน Railway)
