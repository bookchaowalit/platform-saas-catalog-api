# 01 — Business process (As-Is / To-Be)

repo นี้คือ read-only HTTP API (Python stdlib `http.server`) ที่แบ่งหน้าและกรอง JSON snapshot ไฟล์เดียว `data/free-saas-master-catalog-2026.json` ให้โมดูล `/saas` ของ Solo Web (`bookchaowalit/life-dashboard-web`) และ MCP server `saas-catalog-mcp` ของ owner ไม่มี database, ไม่เรียก provider, ไม่ activate อะไร (ดู [`PRODUCT.md`](../../PRODUCT.md))

## As-Is (จากโค้ดวันนี้)

```mermaid
flowchart LR
    GEN["External generator (outside this repo)"] -->|"writes JSON snapshot + commit"| SNAP["data/free-saas-master-catalog-2026.json"]
    SNAP -->|"python3 scripts/validate_catalog.py"| VAL{"contract ok, non-empty, unique ids?"}
    VAL -->|"FAIL exit 2"| FIX["Fix snapshot"]
    VAL -->|"OK"| PUSH["Push to main"]
    PUSH --> CI["GitHub Actions CI + security"]
    CI -->|"pass"| RW["Railway Wait for CI then Docker build"]
    RW --> IMG["Image bakes the snapshot file"]
    OWNER["Owner"] --> WEB["Solo Web /saas page"]
    WEB -->|"BFF mints service JWT"| API["GET /api/v1/saas"]
    AGENT["Owner agent"] --> MCP["saas-catalog-mcp saas.list / saas.get"]
    MCP -->|"mints own 60 s JWT"| API
    IMG --> API
    API -->|"filter + page + buckets"| RESP["summary, signals, starter_stacks, services page, boundary text"]
    RESP --> DECIDE["Owner picks provider, then verifies current terms manually"]
```

ขั้นตอน "verify current terms" อยู่นอกระบบ: payload มีแค่ข้อความ `boundary` ว่า "verify current limits and terms before activating any provider" ระบบไม่บันทึกว่า verify แล้วหรือยัง

Sources: `server.py`, `scripts/validate_catalog.py`, `Dockerfile`, `railway.toml`, `.railway/railway.ts`, `saas_catalog_mcp.py`, `README.md`, `PRODUCT.md`, `contracts/saas-catalog.v1.md`, Solo Web `lib/backends.ts` + `modules/saas/api.ts` (life-dashboard-web `09c1001`, read-only)

## To-Be

ไม่มีเอกสาร To-Be ใน repo (`specs/001-l2-baseline/spec.md` เป็น tooling baseline ไม่ใช่ process ใหม่, ไม่มี `docs/UPGRADE-PLAN.md`, ไม่มี issue) สิ่งที่ `PRODUCT.md` ระบุว่ายังเปิดอยู่:

## Open questions

- ใครเป็นคน refresh snapshot และบ่อยแค่ไหน (`PRODUCT.md` เขียนว่า "[ต้องยืนยัน]"); ใน 90 วันไฟล์ data ถูกแก้ครั้งเดียว (`fd1b37a`, 2026-10-11) และ `scripts/sync_catalog.py` ถูกลบใน `0fc3fe7`
- เป้าหมายของ snapshot age และสัดส่วน `verify` rows ("[ต้องยืนยัน: no target set]" ใน `PRODUCT.md`)
- To-Be process ทั้งหมด: owner ต้องกำหนด
