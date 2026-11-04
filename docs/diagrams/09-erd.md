# 09 — ERD (snapshot file model)

ไม่มี database ข้อมูลที่ persist มีไฟล์เดียว: `data/free-saas-master-catalog-2026.json` (contract `solo-empire.free-saas-catalog.v1`, version 1) ERD ด้านล่างคือโครงสร้างไฟล์นั้น และ object ที่ API project ออกมา

```mermaid
erDiagram
    CATALOG ||--|| SOURCE : has
    CATALOG ||--|| SUMMARY : has
    CATALOG ||--o{ COLUMN_NAME : lists
    CATALOG ||--o{ HOW_TO_USE : has
    CATALOG ||--o{ STARTER_STACK : has
    CATALOG ||--o{ SERVICE_ROW : has
    SUMMARY ||--|| WORKBOOK : has
    SUMMARY ||--|| COMPUTED : has
    COMPUTED ||--o{ BY_CATEGORY : has
    SERVICE_ROW ||--|| PROJECTED_SERVICE : "projected to"
    CATALOG {
        string contract
        int version
    }
    SOURCE {
        string file_name
        string sheet
        string sha256
        string snapshot_date
        int record_count
    }
    WORKBOOK {
        string services
        string categories
        string subcategories
        string rows_with_specific_quota_detail
        string rows_requiring_current_limit_verification
        string catalog_date
    }
    COMPUTED {
        int services
        int categories
        int subcategories
    }
    BY_CATEGORY {
        string category
        int services
    }
    HOW_TO_USE {
        string topic
        string guidance
    }
    STARTER_STACK {
        string use_case
        string layer
        string primary_free_option
        string fallback_1
        string fallback_2
        string why
    }
    SERVICE_ROW {
        string id PK
        int source_row
        string service
        string category
        string subcategory
        string free_tier_summary
        string free_limits
        string credit_card_required
        string commercial_use
        string vendor_lock_in_risk
        string best_use_case
        string replaces
        string official_url
        string last_verified
    }
    PROJECTED_SERVICE {
        string id "max 80"
        string text_fields "23 fields, max 400 each, empty is null"
        string official_url "https only, max 300"
        string card_bucket "no_card, card_required, verify"
        string commercial_bucket "yes, verify"
    }
```

`SERVICE_ROW` มี 26 คอลัมน์ (ตาม `columns`) ใน ERD แสดงเฉพาะที่ใช้ใน logic; คอลัมน์ที่เหลือ (`sleeps_pauses`, `bandwidth`, `storage`, `requests_compute`, `regions`, `custom_domain`, `api`, `open_standard_portability`, `overage_paid_entry`, `free_forever`, `self_host_alternative`, `notes`) ถูก project เป็น text field ตาม `TEXT_FIELDS` ส่วน `source_row` ไม่ถูกส่งออก API; `columns` และ `how_to_use` ไม่ถูก API อ่าน

ค่าปัจจุบัน: 648 services, 29 categories, 18 starter stacks, `snapshot_date` 2026-08-30 (คำนวณจากไฟล์ที่ `21d5d41`)

Sources: `data/free-saas-master-catalog-2026.json`, `server.py` (`TEXT_FIELDS`, `project_service`, `CatalogStore.snapshot`), `scripts/validate_catalog.py`, `service.yaml`, `contracts/saas-catalog.v1.md`

## Open questions

- ไม่มี JSON Schema ของ snapshot ใน repo; validator ตรวจแค่ contract, services ไม่ว่าง, id ไม่ซ้ำ
