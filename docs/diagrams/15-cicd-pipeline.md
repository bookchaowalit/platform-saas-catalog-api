# 15 — CI/CD pipeline

```mermaid
flowchart TD
    PUSH["push to main"] --> CI
    PR["pull_request"] --> CI
    WD["workflow_dispatch"] --> CI
    CI["Workflow CI, concurrency ci-ref, cancel-in-progress"]
    CI --> API["job api: ci-python.yml @87dc5e1c v1.1.1"]
    CI --> SEC["job security: security.yml @87dc5e1c v1.1.1"]
    subgraph apij["api / python (.) on ubuntu-24.04"]
        A1["Checkout"] --> A2["setup-uv, Python 3.12"] --> A3["uv sync --frozen --all-extras"] --> A4["Ruff check + format --check"] --> A5["mypy ."] --> A6["pytest -q --cov"] --> A7["Coverage gate >= 83"]
    end
    subgraph secj["security"]
        S1["gitleaks"]
        S2["semgrep p/default"]
        S3["osv-scanner"]
        S4["trivy-fs HIGH,CRITICAL vuln+misconfig"]
    end
    API --> apij
    SEC --> secj
    apij --> GATE{"All check suites green on main?"}
    secj --> GATE
    GATE -->|"yes, Railway Wait for CI"| DEP["Railway builds Dockerfile and deploys solo-saas-catalog"]
    GATE -->|"no"| STAY["Production stays on previous deployment"]
    DEP --> HC["Healthcheck /ready, 30 s"]
    REN["Renovate: Monday before 9am, lockfile monthly"] --> PR
```

Postgres step ของ `ci-python.yml` ไม่ทำงาน (`postgres` input ไม่ได้ตั้ง, default false) ผล 90 วัน: 14 runs, success ทั้งหมด (7 push main, 7 pull_request)

Sources: `.github/workflows/ci.yml`, platform-ci-workflows `.github/workflows/ci-python.yml` และ `security.yml` @ `87dc5e1c` (read-only), `renovate.json`, `.railway/railway.ts`, `.railway/railway.ts`, `README.md`, `gh run list -R bookchaowalit/platform-saas-catalog-api --limit 100`, `gh run view <latest> --json jobs`

## Open questions

- `scripts/validate_catalog.py` ไม่ใช่ step แยกใน CI (ถูกเรียกผ่าน test `test_committed_snapshot_has_valid_shape` เท่านั้น)
- Docker image ไม่ถูก build ใน CI (build ครั้งแรกคือบน Railway)
