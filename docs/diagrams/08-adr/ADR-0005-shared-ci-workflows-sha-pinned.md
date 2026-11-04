# ADR-0005 — Shared CI and security workflows, SHA-pinned, coverage ratchet

- Status: accepted (retro-documented)
- Date of decision: 2026-10-17 (`ceebdb5` #1), bumped to v1.1.1 2026-10-22 (`282112e`)

## Decision

- `.github/workflows/ci.yml` เรียก reusable workflows ของ `bookchaowalit/platform-ci-workflows` ที่ SHA `87dc5e1c7e0416886a6371d5a101bb2ccba38edd` (v1.1.1): `ci-python.yml` (Ruff, mypy, pytest, coverage gate) และ `security.yml` (gitleaks, semgrep, osv-scanner, trivy-fs)
- GitHub-hosted runner (repo public, default `ubuntu-24.04`), Python 3.12 ให้ตรงกับ image
- `coverage-threshold: "83"` (วัดได้ 85.71% เมื่อ 2026-10-22 ลบ 2)
- Renovate (`renovate.json`) รวม PR ของ platform-ci-workflows เป็นกลุ่มเดียว, pin action digests

## Evidence

`.github/workflows/ci.yml`, `renovate.json`, platform-ci-workflows `ci-python.yml` / `security.yml` @ `87dc5e1c` (read-only), `gh run view` jobs ของ run ล่าสุด
