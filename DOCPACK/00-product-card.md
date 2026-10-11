---
title: solo-saas-catalog — Product Card
doc_id: CARD-solo-saas-catalog
doc_type: product-card
verdict: showcase
version: 0.1
date: 2026-10-11
status: ร่างเพื่อพิจารณา
owner: Product owner (Book Dev)
---

# solo-saas-catalog — Product Card

## 1. สรุปคุณค่าในหนึ่งประโยค

ช่วยเจ้าของค้นและกรองแค็ตตาล็อก SaaS ที่มีแผนฟรี (แบ่งตามข้อกำหนดบัตรเครดิต) ผ่าน API ที่โมดูล `/saas` ของ `solo-web` เรียกใช้

## 2. ปัญหาและผู้ใช้เป้าหมาย

- ปัญหา: รายการ SaaS ฟรีเป็นไฟล์ workbook/JSON ใหญ่ ค้นยาก
- ผู้ใช้: เจ้าของ (internal) ผ่าน `solo-web`

## 3. สิ่งที่ทำได้จริงตอนนี้

- `server.py` เสนอ API อ่านอย่างเดียวที่แบ่งหน้าและกรอง `data/free-saas-master-catalog-2026.json` และ reload เมื่อไฟล์เปลี่ยน; ไม่เปิดใช้ provider ใด ๆ
- จัดคอลัมน์บัตรเครดิตเป็น `no_card`, `card_required`, `verify` ตาม README
- `scripts/validate_catalog.py` ตรวจ contract + unique id ของ snapshot

## 4. หลักฐานสถานะ

| รายการ | ค่า (ตรวจจาก repository) |
|---|---|
| Stack | Python (stdlib server) |
| Commits | 7 (แรก 2026-10-04 → ล่าสุด 2026-10-11) |
| Source | ประมาณ 971 บรรทัดใน 6 ไฟล์ (ไม่รวมเทสต์) |
| Tests | 3 ไฟล์ |
| CI | ไม่มี |
| Deploy config | `Dockerfile`, `railway.toml`, `service.yaml`; ไม่ได้ตรวจ live |
| Live URL | ไม่มี (ไม่ได้ตรวจ) |
| README | 94 บรรทัด |

## 5. คุณค่าและจุดต่าง

- ข้อมูลหลักเป็นของ solo-empire (generated ที่นั่น) repo นี้เป็น snapshot ที่ deploy ได้
- มุมรายได้: ไม่มี **[สมมติฐาน]** ว่าแค็ตตาล็อกอาจเป็น data product สาธารณะได้

## 6. ช่องว่างสำคัญ

- snapshot ต้องถูกเขียนลง repo นี้โดย generator ภายนอก ถ้าไม่อัปเดตข้อมูลเก่า
- `vendor/service-auth` เป็นสำเนา ต้องอัปเดตตามต้นทาง
- ไม่มี CI

## 7. คำตัดสิน

**`showcase`** — บริการเล็กที่ใช้งานในระบบ มีเทสต์ แต่ไม่ใช่ธุรกิจ จะเปลี่ยนถ้าเปิดแค็ตตาล็อกเป็นข้อมูลสาธารณะที่มีผู้ใช้

## 8. ขั้นต่อไป

1. รัน `python3 scripts/validate_catalog.py` ยืนยันรูปแบบ snapshot
2. เพิ่ม CI รันเทสต์ unittest

## การอนุมัติ

| บทบาท | สถานะ | วันที่ | ลงนาม |
|---|---|---|---|
| Product owner (Book Dev) | รอพิจารณา | — | ________ |

## แหล่งข้อมูล

- `README.md`
- `server.py`, `scripts/validate_catalog.py`, `railway.toml`, `tests/`
