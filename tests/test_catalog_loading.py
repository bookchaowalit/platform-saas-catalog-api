"""Catalog loading rules: contract check, unique ids, starter stacks, metadata, mtime reload."""

from __future__ import annotations

import json
import os

import pytest


def get(api, query: str = ""):
    return api.handle("GET", "/api/v1/saas" + query)


def test_a_catalog_with_another_contract_is_a_503(make_api):
    api = make_api({"id": "a"}, contract="other.v1")
    response = get(api)
    assert response.status == 503
    assert response.payload["error"]["code"] == "catalog_unavailable"


def test_duplicate_service_ids_are_a_503_not_a_partial_list(make_api):
    response = get(make_api({"id": "a"}, {"id": "a"}))
    assert response.status == 503
    assert response.payload["error"]["code"] == "catalog_unavailable"


def test_a_missing_catalog_file_is_a_503(make_api, catalog_path):
    api = make_api({"id": "a"})
    catalog_path.unlink()
    assert get(api).status == 503


def test_rows_without_an_id_are_skipped(make_api):
    payload = get(make_api({"id": "a"}, {"service": "no id"}, {"id": ""})).payload
    assert [s["id"] for s in payload["services"]] == ["a"]
    assert payload["summary"]["services_total"] == 1


def test_starter_stack_dashes_and_blanks_become_null_and_text_is_cut(make_api):
    api = make_api(
        {"id": "a"},
        starter_stacks=[
            {
                "use_case": "Typical SaaS",
                "layer": "DNS",
                "primary_free_option": "Cloudflare",
                "fallback_1": "—",
                "fallback_2": "",
                "why": "w" * 400,
                "ignored": "dropped",
            }
        ],
    )
    (stack,) = get(api).payload["starter_stacks"]
    assert stack == {
        "use_case": "Typical SaaS",
        "layer": "DNS",
        "primary_free_option": "Cloudflare",
        "fallback_1": None,
        "fallback_2": None,
        "why": "w" * 300,
    }


def test_source_metadata_carries_the_snapshot_dates_and_a_revision(make_api):
    api = make_api(
        {"id": "a"},
        source={"snapshot_date": "2026-08-30"},
        summary={
            "workbook": {
                "catalog_date": "2026-08-30",
                "rows_requiring_current_limit_verification": "496",
            }
        },
    )
    source = get(api).payload["source"]
    assert source["path"] == "data/free-saas-master-catalog-2026.json"
    assert source["snapshot_date"] == "2026-08-30"
    assert source["catalog_date"] == "2026-08-30"
    assert source["rows_requiring_current_limit_verification"] == "496"
    assert len(source["revision"]) == 64


def test_the_catalog_reloads_only_when_its_mtime_changes(make_api, catalog_path):
    api = make_api({"id": "a"})
    os.utime(catalog_path, (1_700_000_000, 1_700_000_000))
    assert get(api).payload["summary"]["services_total"] == 1
    payload = json.loads(catalog_path.read_text())
    payload["services"].append({"id": "b"})
    catalog_path.write_text(json.dumps(payload))
    os.utime(catalog_path, (1_700_000_000, 1_700_000_000))
    assert get(api).payload["summary"]["services_total"] == 1  # cached snapshot
    os.utime(catalog_path, (1_700_000_060, 1_700_000_060))
    assert get(api).payload["summary"]["services_total"] == 2


def test_the_shipped_snapshot_loads_with_unique_ids():
    from server import CatalogStore, default_catalog_path

    services, stacks, metadata = CatalogStore(default_catalog_path()).snapshot()
    assert len(services) == len({s["id"] for s in services}) > 0
    assert stacks
    assert metadata["snapshot_date"]


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
def test_the_catalog_is_read_only(make_api, method):
    response = make_api({"id": "a"}).handle(method, "/api/v1/saas")
    assert response.status == 405
    assert response.payload["error"]["code"] == "method_not_allowed"
