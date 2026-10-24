# SPEC-001 — L2 baseline: locked dependencies, strict types, domain rules under test

Standard: ADR-0004 — TDD + SDD (architecture-docs, `docs/architecture/decisions/ADR-0004-tdd-sdd-standard.md`).
Big Loop Plan Wave 2 (solo-empire `repository-catalog/roadmaps/BIG-LOOP-PLAN-2026-10-21.md`).

## Document control

| Field | Value |
|---|---|
| Spec ID / version | SPEC-001 / 1.0 |
| Status | in review (implemented; owner approval pending) |
| Repository / path | bookchaowalit/platform-saas-catalog-api / `specs/001-l2-baseline/spec.md` |
| Owner (maker) | Claude Code (Wave 2 cells session) |
| Reviewer (checker) | Fresh Claude reviewer session (no maker context) |
| Approver | Owner (bookchaowalit): pending, see the Wave 2 report owner actions |
| Requirement links | Big Loop DoD L2: `PRODUCT.md`, ≥ 3 test files, Sentry, type check; L1 lockfile |
| Main-only | yes: committed straight to `main`, so the red run is local (ADR-0004 rule 2, v1.1) |
| Created / approved | 2026-10-22 / pending owner |

## 1. Problem and intent

- **Problem:** The read-only SaaS catalog API pages and filters a shipped free-SaaS snapshot for Solo Web /saas; its card/commercial bucket, loading and search/paging rules were only partly covered, with no lockfile, type check, strict lint or coverage gate.
- **Outcome:** the image installs exactly `uv.lock` (`uv sync --frozen`), CI runs Ruff, mypy
  (strict on `src/`) and a coverage gate on shared CI v1.1.1, and the cell's own rules have
  tests of their own beyond the generic contract suite.
- **Why now:** Wave 2 of the Big Loop Plan; milestone M1 is 2026-11-15.

## 2. Scope

| In scope | Out of scope (non-goals) |
|---|---|
| Lock file and frozen install, CI caller bump, Ruff/mypy config and fixes, rule tests, `PRODUCT.md` | New endpoints or fields; schema changes |

## 3. Behaviour — scenarios

### AC-01 — Only a plain No is card-free

- **Given** card text 'No', 'no', '  NO  '
- **When** card_bucket runs
- **Then** no_card
- **Test:** `tests/test_card_and_commercial_buckets.py::test_only_a_plain_no_counts_as_no_card` · level: unit / API with local fakes

### AC-02 — Unclear card text is verify

- **Given** empty, None, 'Verify', 'No (unless ...)', 'Sometimes', 'N/A'
- **When** card_bucket runs
- **Then** verify, never no_card
- **Test:** `tests/test_card_and_commercial_buckets.py::test_anything_unclear_is_verify_never_card_free` · level: unit / API with local fakes

### AC-03 — Commercial yes only for exact Yes

- **Given** commercial text variants
- **When** commercial_bucket runs
- **Then** yes only for a plain Yes
- **Test:** `tests/test_card_and_commercial_buckets.py::test_commercial_use_is_yes_only_when_the_catalog_says_exactly_yes` · level: unit / API with local fakes

### AC-04 — Only HTTPS official URLs

- **Given** http, javascript, missing and long https URLs
- **When** a service is projected
- **Then** only https kept, cut to 300
- **Test:** `tests/test_card_and_commercial_buckets.py::test_only_https_official_urls_are_kept_and_cut_to_300` · level: unit / API with local fakes

### AC-05 — Unknown bucket filter is a 400

- **Given** the API
- **When** card or commercial is not a known bucket
- **Then** 400 invalid_field
- **Test:** `tests/test_card_and_commercial_buckets.py::test_an_unknown_bucket_filter_is_a_400` · level: unit / API with local fakes

### AC-06 — Wrong contract or duplicate ids fail closed

- **Given** a snapshot with another contract or duplicate ids
- **When** GET /api/v1/saas
- **Then** 503 catalog_unavailable
- **Test:** `tests/test_catalog_loading.py::test_duplicate_service_ids_are_a_503_not_a_partial_list` · level: unit / API with local fakes

### AC-07 — Starter stack dashes become null

- **Given** a stack with a dash, a blank and a 400-char reason
- **When** the snapshot loads
- **Then** dash and blank are null, reason cut to 300, unknown keys dropped
- **Test:** `tests/test_catalog_loading.py::test_starter_stack_dashes_and_blanks_become_null_and_text_is_cut` · level: unit / API with local fakes

### AC-08 — Reload only on mtime change

- **Given** a served snapshot
- **When** the file changes with the same, then a new mtime
- **Then** cached first, reloaded after
- **Test:** `tests/test_catalog_loading.py::test_the_catalog_reloads_only_when_its_mtime_changes` · level: unit / API with local fakes

### AC-09 — Search fields

- **Given** services matching in name, use case, replaces, subcategory or only notes
- **When** q is set
- **Then** only id, service, subcategory, best_use_case and replaces match, case-insensitive
- **Test:** `tests/test_search_and_paging.py::test_text_search_covers_id_name_subcategory_use_case_and_replaces_only` · level: unit / API with local fakes

### AC-10 — Paging and filter bounds

- **Given** limit outside 1-100, offset outside 0-5000, oversized q or category
- **When** GET /api/v1/saas
- **Then** 400 invalid_limit, invalid_offset or invalid_field
- **Test:** `tests/test_search_and_paging.py::test_out_of_range_paging_and_oversized_filters_are_a_400` · level: unit / API with local fakes

### AC-11 — Shipped snapshot loads

- **Given** data/free-saas-master-catalog-2026.json
- **When** the store loads it
- **Then** unique ids, starter stacks and a snapshot date
- **Test:** `tests/test_catalog_loading.py::test_the_shipped_snapshot_loads_with_unique_ids` · level: unit / API with local fakes

## 4. Interfaces and data

| Interface | Change | Contract |
|---|---|---|
| G | E | T |
| G | E | T |
| G | E | T |
| M | C | P |

- **Data model / migration:** N/A — no schema change.
- **Backward compatibility:** same routes and payloads; only tooling, locks, typing fixes and tests changed unless a scenario above says otherwise.

## 5. Non-functional requirements

| NFR | Target | How it is tested |
|---|---|---|
| Performance | N/A — no hot-path change beyond one comparison per declared range | — |
| Security / privacy | Authorization unchanged; Sentry sends no PII and scrubs tokens/URLs | existing auth tests, Sentry tests |
| Reliability / observability | Reproducible install from the lock file; opt-in Sentry error reporting | image rehearsal before push; Sentry tests |
| Accessibility / UX | N/A — API only | — |

## 6. Test plan (TDD)

- **Test levels:** unit and API tests with local fakes; no hosted service is called.
- **Test data:** generated in each test; no production data.
- **Coverage:** CI gate `coverage-threshold: "83"` (measured 85.71% on 2026-10-22, minus 2 points).
- **Not test-first (exceptions):** tests that pin behaviour the service already had
  (characterization tests, marked below) were written after the code by nature; tooling and
  config changes are covered by CI itself.

### Red / green log

| Scenario | Test | Red: commit / run + failure message | Green: commit / run | Refactor note |
|---|---|---|---|---|
| AC-01 | `tests/test_card_and_commercial_buckets.py::test_only_a_plain_no_counts_as_no_card` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-02 | `tests/test_card_and_commercial_buckets.py::test_anything_unclear_is_verify_never_card_free` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-03 | `tests/test_card_and_commercial_buckets.py::test_commercial_use_is_yes_only_when_the_catalog_says_exactly_yes` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-04 | `tests/test_card_and_commercial_buckets.py::test_only_https_official_urls_are_kept_and_cut_to_300` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-05 | `tests/test_card_and_commercial_buckets.py::test_an_unknown_bucket_filter_is_a_400` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-06 | `tests/test_catalog_loading.py::test_duplicate_service_ids_are_a_503_not_a_partial_list` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-07 | `tests/test_catalog_loading.py::test_starter_stack_dashes_and_blanks_become_null_and_text_is_cut` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-08 | `tests/test_catalog_loading.py::test_the_catalog_reloads_only_when_its_mtime_changes` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-09 | `tests/test_search_and_paging.py::test_text_search_covers_id_name_subcategory_use_case_and_replaces_only` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-10 | `tests/test_search_and_paging.py::test_out_of_range_paging_and_oversized_filters_are_a_400` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |
| AC-11 | `tests/test_catalog_loading.py::test_the_shipped_snapshot_loads_with_unique_ids` | characterization (behaviour already present; passed on first run) | CI run of the pushed tip | none |

## 7. Risks and open questions

| # | Risk or question | Impact | Owner | Resolution / date |
|---|---|---|---|---|
| 1 | Stored rows written before a range rule existed may already be inverted | a patch touching one of those dates is refused until both are fixed | owner | patches that do not touch the range still work |

## 8. Change log

| Version | Date | Change | Scenarios affected | Approved by |
|---|---|---|---|---|
| 1.0 | 2026-10-22 | Implemented with the Wave 2 baseline | all | pending owner |

## Approval

| Gate | Role | Name / date | Decision | Evidence |
|---|---|---|---|---|
| Implemented (DoD) | Reviewer (checker) | Fresh Claude reviewer / 2026-10-22 | see Wave 2 report | CI run of the pushed tip |
| Implemented (DoD) | Approver | Owner | pending | Wave 2 report |

## Review (2026-10-24): changes requested

Checker: independent Claude reviewer subagent (`solo:solo-reviewer`, Sonnet, read-only, no maker context). Status unchanged until fixed.

- Tests run by the checker: .venv/bin/pytest -q: 102 passed, 7 subtests passed
- Gap: All cited tests pass, but the §4 Interfaces table is corrupted (single-letter rows). Regenerate it.
