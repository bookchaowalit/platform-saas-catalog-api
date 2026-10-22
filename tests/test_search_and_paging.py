"""Search, filter and paging rules for GET /api/v1/saas."""

from __future__ import annotations

import pytest

from server import (
    DEFAULT_LIMIT,
    MAX_FILTER_LENGTH,
    MAX_LIMIT,
    MAX_OFFSET,
    MAX_QUERY_LENGTH,
)


@pytest.fixture
def api(make_api):
    return make_api(
        {
            "id": "workers",
            "service": "Edge Workers",
            "category": "Compute",
            "subcategory": "Functions",
        },
        {
            "id": "pg",
            "service": "Postgres",
            "category": "Database",
            "best_use_case": "Edge-near SQL",
        },
        {"id": "kv", "service": "KV", "category": "Database", "replaces": "Redis"},
        {
            "id": "mail",
            "service": "Mail",
            "category": "Email",
            "notes": "edge notes are not searched",
        },
    )


def ids(api, query: str = "") -> list[str]:
    response = api.handle("GET", "/api/v1/saas" + query)
    assert response.status == 200, response.payload
    return [service["id"] for service in response.payload["services"]]


def test_text_search_covers_id_name_subcategory_use_case_and_replaces_only(api):
    assert ids(api, "?q=EDGE") == ["workers", "pg"]
    assert ids(api, "?q=redis") == ["kv"]
    assert ids(api, "?q=functions") == ["workers"]
    assert ids(api, "?q=notes") == []


def test_category_filter_is_an_exact_match(api):
    assert ids(api, "?category=Database") == ["pg", "kv"]
    assert ids(api, "?category=database") == []


def test_summary_counts_the_whole_catalog_and_the_matches(api):
    payload = api.handle("GET", "/api/v1/saas?category=Database").payload
    assert payload["summary"]["services_total"] == 4
    assert payload["summary"]["services_matched"] == 2
    assert payload["summary"]["categories"] == 3
    assert payload["signals"]["categories"] == [
        {"value": "Database", "count": 2},
        {"value": "Compute", "count": 1},
        {"value": "Email", "count": 1},
    ]
    assert payload["signals"]["lock_in"] == [{"value": "unknown", "count": 4}]


def test_paging_slices_the_matches_in_catalog_order(api):
    assert ids(api, "?limit=2") == ["workers", "pg"]
    assert ids(api, "?limit=2&offset=2") == ["kv", "mail"]
    assert ids(api, "?offset=10") == []
    filters = api.handle("GET", "/api/v1/saas").payload["filters"]
    assert (filters["limit"], filters["offset"]) == (DEFAULT_LIMIT, 0)


@pytest.mark.parametrize(
    ("query", "code"),
    [
        ("?limit=0", "invalid_limit"),
        (f"?limit={MAX_LIMIT + 1}", "invalid_limit"),
        ("?limit=ten", "invalid_limit"),
        ("?offset=-1", "invalid_offset"),
        (f"?offset={MAX_OFFSET + 1}", "invalid_offset"),
        (f"?q={'x' * (MAX_QUERY_LENGTH + 1)}", "invalid_field"),
        (f"?category={'c' * (MAX_FILTER_LENGTH + 1)}", "invalid_field"),
    ],
)
def test_out_of_range_paging_and_oversized_filters_are_a_400(api, query, code):
    response = api.handle("GET", "/api/v1/saas" + query)
    assert response.status == 400
    assert response.payload["error"]["code"] == code


def test_paging_bounds_are_inclusive(api):
    assert api.handle("GET", f"/api/v1/saas?limit={MAX_LIMIT}").status == 200
    assert api.handle("GET", f"/api/v1/saas?offset={MAX_OFFSET}").status == 200


def test_the_payload_says_limits_must_be_verified_before_use(api):
    payload = api.handle("GET", "/api/v1/saas").payload
    assert payload["schema_version"] == "solo-empire.saas-catalog.v1"
    assert "verify current limits and terms" in payload["boundary"]
