#!/usr/bin/env python3
"""Focused offline tests for the free SaaS catalog projection."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
import time
import subprocess
import os
from unittest.mock import patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from service_auth import AuthPolicy
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

    def test_scoped_production_auth_and_safe_errors(self) -> None:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode()
        policy = AuthPolicy("https://solo.example", "saas-catalog-api", public,
                            frozenset({"fixture-owner"}), "saas:read")
        api = SaasCatalogApi(self.path, environment="production", auth_policy=policy)
        now = int(time.time())
        claims = dict(iss="https://solo.example", aud="saas-catalog-api", sub="fixture-owner",
                      tenant_id="owner", scope="saas:read", iat=now, nbf=now,
                      exp=now+120, jti="fixture-request")
        def headers(changes=None):
            return {"Authorization": "Bearer " + jwt.encode(
                {**claims, **(changes or {})}, key, algorithm="RS256")}
        self.assertEqual(api.handle("GET", "/health").status, 200)
        self.assertEqual(api.handle("GET", "/ready").status, 200)
        self.assertEqual(api.handle("GET", "/api/v1/saas").status, 401)
        response = api.handle("GET", "/api/v1/saas", headers=headers())
        self.assertEqual(response.status, 200)
        self.assertEqual(len(response.payload["source"]["revision"]), 64)
        for changes, expected in (
            ({"scope": "other:read"}, 403), ({"tenant_id": "other"}, 403),
            ({"sub": "other-owner"}, 403), ({"iss": "https://other.example"}, 401),
            ({"aud": "other-api"}, 401), ({"exp": now-300}, 401),
            ({"nbf": now+300}, 401),
        ):
            with self.subTest(changes=changes):
                denied = api.handle("GET", "/api/v1/saas", headers=headers(changes))
                self.assertEqual(denied.status, expected)
                self.assertEqual(set(denied.payload), {"error"})
                self.assertNotIn("Bearer", json.dumps(denied.payload))
        self.assertEqual(api.handle("GET", "/api/v1/saas", headers={"Authorization": "Bearer " + "x"*9000}).status, 401)

    def test_static_token_is_never_production_authorization(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = SaasCatalogApi(self.path, token="development-only", environment="production")
        self.assertEqual(api.handle("GET", "/api/v1/saas",
                                   headers={"Authorization": "Bearer development-only"}).status, 503)
        self.assertEqual(api.handle("GET", "/health").status, 200)
        self.assertEqual(api.handle("GET", "/ready").payload["auth"], "disabled")

    def test_readiness_and_remote_bind_fail_closed(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            api = SaasCatalogApi(self.path, environment="development")
        self.assertEqual(api.handle("GET", "/ready").payload["auth"], "development")
        self.assertEqual(api.handle("GET", "/ready").status, 503)
        self.path.unlink()
        self.assertEqual(api.handle("GET", "/ready").payload["source"], "unavailable")
        self.assertEqual(api.handle("GET", "/health").status, 200)
        env = {**os.environ, "SAAS_CATALOG_API_TOKEN": "legacy-token", "SAAS_CATALOG_API_ENV": "development"}
        for suffix in ("AUTH_ISSUER", "AUTH_PUBLIC_KEY", "AUTH_SUBJECTS"):
            env.pop("SAAS_CATALOG_API_" + suffix, None)
        result = subprocess.run([sys.executable, str(ROOT / "server.py"), "--host", "0.0.0.0"],
                                env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 2)
        self.assertIn("SAAS_CATALOG_API_AUTH_*", result.stderr)

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
