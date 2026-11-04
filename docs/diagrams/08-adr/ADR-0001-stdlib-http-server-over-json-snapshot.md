# ADR-0001 — Python stdlib HTTP server over a shipped JSON snapshot, no database

- Status: accepted (retro-documented)
- Date of decision: 2026-10-04 (first commit `e75f0cc`), standalone layout 2026-10-11 (`fd1b37a`)

## Context

แค็ตตาล็อก SaaS ฟรีเป็นไฟล์ generated ขนาดประมาณ 680 KB (648 services, 18 starter stacks) ที่อ่านอย่างเดียว ไม่มีการเขียนจากผู้ใช้

## Decision

- ใช้ `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler` (stdlib) ไม่มี web framework
- ข้อมูลเป็นไฟล์ JSON ใน repo (`data/free-saas-master-catalog-2026.json`) ถูก COPY เข้า image; ไม่มี database (`service.yaml` `writes: []`)
- `CatalogStore` cache snapshot ใน memory และ reload เมื่อ `st_mtime` เปลี่ยน; contract ต้องเป็น `solo-empire.free-saas-catalog.v1` และ id ต้องไม่ซ้ำ ไม่งั้น 503

## Consequences

- dependency runtime น้อย (`solo-empire-service-auth`, `sentry-sdk`); ไม่มี DB ให้ backup
- อัปเดตข้อมูล = commit ไฟล์ใหม่ + redeploy (ใน container mtime ไม่เปลี่ยนเอง)
- `BaseHTTPRequestHandler` ไม่รองรับ `HEAD` (ไม่มี `do_HEAD` จึงได้ 501 จาก stdlib) และ access log ถูกปิด (`log_message` return)

## Evidence

`server.py` (imports, `CatalogStore`, `SaasCatalogRequestHandler`), `Dockerfile`, `service.yaml`, `pyproject.toml`, `README.md`, `git log`
