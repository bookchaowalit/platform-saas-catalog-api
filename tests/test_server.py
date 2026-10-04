#!/usr/bin/env python3
"""Focused offline tests for the free SaaS catalog projection."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
sys.path.insert(0, str(ROOT))
from server import SaasCatalogApi, card_bucket  # noqa: E402


def service(service_id: str, **fields):
    row = {"id": service_id, "service": service_id.title(), "category": "Compute", "subcategory": "Edge",
           "credit_card_required": "Verify", "commercial_use": "Verify terms", "vendor_lock_in_risk": "Varies",
           "official_url": f"https://{service_id}.example/docs"}
    row.update(fields)
    return row


CATALOG = {
    "contract": "solo-empire.free-saas-catalog.v1",
    "source": {"snapshot_date": "2026-08-30"},
    "summary": {"workbook": {"catalog_date": "2026-08-30", "rows_requiring_current_limit_verification": "1"}},
    "starter_stacks": [{"use_case": "Typical SaaS", "layer": "DNS", "primary_free_option": "Cloudflare", "fallback_1": "—", "fallback_2": None, "why": "One account"}],
    "services": [
        service("workers", credit_card_required="No", commercial_use="Yes", best_use_case="Edge APIs"),
        service("bigcloud", category="Database", credit_card_required="Billing account often required", official_url="http://insecure.example"),
        service("mystery"),
    ],
}


class SaasCatalogApiTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "catalog.json"
        self.path.write_text(json.dumps(CATALOG), encoding="utf-8")
        self.api = SaasCatalogApi(self.path, token="", environment="development")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def get(self, target: str, **kwargs):
        return self.api.handle("GET", target, **kwargs)

    def test_card_buckets(self) -> None:
        self.assertEqual(card_bucket("No"), "no_card")
        self.assertEqual(card_bucket("No/Varies"), "verify")
        self.assertEqual(card_bucket("Yes/Varies"), "card_required")
        self.assertEqual(card_bucket(None), "verify")

    def test_overview(self) -> None:
        payload = self.get("/api/v1/saas").payload
        self.assertEqual(payload["schema_version"], "solo-empire.saas-catalog.v1")
        self.assertEqual(payload["summary"], {
            "services_total": 3, "services_matched": 3, "categories": 2,
            "no_card": 1, "commercial_yes": 1, "needs_verification": 1,
        })
        self.assertEqual(payload["starter_stacks"][0]["fallback_1"], None)
        services = {item["id"]: item for item in payload["services"]}
        self.assertIsNone(services["bigcloud"]["official_url"])
        self.assertEqual(services["bigcloud"]["card_bucket"], "card_required")

    def test_filters_and_paging(self) -> None:
        self.assertEqual([s["id"] for s in self.get("/api/v1/saas?card=no_card").payload["services"]], ["workers"])
        self.assertEqual([s["id"] for s in self.get("/api/v1/saas?category=Database").payload["services"]], ["bigcloud"])
        self.assertEqual([s["id"] for s in self.get("/api/v1/saas?commercial=yes").payload["services"]], ["workers"])
        self.assertEqual([s["id"] for s in self.get("/api/v1/saas?q=edge%20apis").payload["services"]], ["workers"])
        page = self.get("/api/v1/saas?limit=1&offset=1").payload
        self.assertEqual((page["summary"]["services_matched"], [s["id"] for s in page["services"]]), (3, ["bigcloud"]))
        for bad in ("card=maybe", "commercial=no", "limit=0", "limit=101", "offset=-1", "limit=x"):
            self.assertEqual(self.get(f"/api/v1/saas?{bad}").status, 400, bad)

    def test_read_only_auth_and_failures(self) -> None:
        self.assertEqual(self.api.handle("POST", "/api/v1/saas").status, 405)
        self.assertEqual(self.get("/api/v1/other").status, 404)
        guarded = SaasCatalogApi(self.path, token="t0ken", environment="development")
        self.assertEqual(guarded.handle("GET", "/api/v1/saas").status, 401)
        self.assertEqual(guarded.handle("GET", "/api/v1/saas", headers={"Authorization": "Bearer t0ken"}).status, 200)
        self.assertEqual(SaasCatalogApi(self.path, token="", environment="production").handle("GET", "/api/v1/saas").status, 503)
        self.path.write_text(json.dumps({**CATALOG, "contract": "other"}), encoding="utf-8")
        self.assertEqual(self.get("/api/v1/saas").payload["error"]["code"], "catalog_unavailable")

    def test_real_catalog_projects(self) -> None:
        real = REPO / "systems" / "cloud-platform" / "free-saas-master-catalog-2026.json"
        payload = SaasCatalogApi(real, token="", environment="development").handle("GET", "/api/v1/saas").payload
        self.assertEqual(payload["summary"]["services_total"], len(json.loads(real.read_text(encoding="utf-8"))["services"]))


if __name__ == "__main__":
    unittest.main()
