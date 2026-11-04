# ADR-0003 — Railway Docker deploy, serverless sleep, CD from main with Wait for CI

- Status: accepted (retro-documented)
- Date of decision: serverless sleep 2026-10-12 (`00a59f9`, `fddb6e8`); CD from GitHub 2026-10-18 (`862f88b`, `84d964c`)

## Context

บริการเล็ก traffic ต่ำ ต้องการต้นทุนต่ำและ deploy ที่ผ่าน CI เท่านั้น

## Decision

- Railway project `platform-saas-catalog-api`, service `solo-saas-catalog`, builder Dockerfile (`python:3.12-slim`, `uv sync --frozen`), user uid 10001
- healthcheck `/ready` timeout 30 s, `restartPolicyType = ON_FAILURE`, max 3 retries
- `sleepApplication: true` (serverless) ใน `.railway/railway.ts`
- source = GitHub `bookchaowalit/platform-saas-catalog-api` branch `main`, `checkSuites: true` (Wait for CI); `railway up` ไม่ใช้แล้ว
- region ไม่ได้อยู่ใน IaC (ต้อง `railway scale` เอง); `PRODUCT.md` บอกว่าอยู่ Singapore

## Consequences

- request แรกหลัง idle ช้า (cold start); uptime-worker probe รายชั่วโมงเพื่อไม่ปลุกตลอด
- push `282112e` (2026-10-22 01:44 UTC, CI success) ไม่มี GitHub deployment record; โค้ดนั้นขึ้น production พร้อม `21d5d41` (2026-10-24) สาเหตุยืนยันจาก repo ไม่ได้ (ดู Open questions ใน 22-dora.md)
- rollback = redeploy deployment เก่าใน Railway (manual)

## Evidence

`railway.toml`, `.railway/railway.ts`, `Dockerfile`, `README.md` "Deploy", `PRODUCT.md`, GitHub deployments API (`gh api repos/bookchaowalit/platform-saas-catalog-api/deployments`)
