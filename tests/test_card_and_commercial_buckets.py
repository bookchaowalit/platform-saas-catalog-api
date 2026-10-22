"""Card and commercial-use rules: free text is collapsed into honest buckets, unclear means verify."""

from __future__ import annotations

import pytest

from server import card_bucket, commercial_bucket, project_service


@pytest.mark.parametrize("text", ["No", "no", "  NO  "])
def test_only_a_plain_no_counts_as_no_card(text):
    assert card_bucket(text) == "no_card"


@pytest.mark.parametrize(
    "text",
    ["Yes", "yes, for paid add-ons", "Billing account often required", " billing"],
)
def test_yes_or_billing_text_means_a_card_is_required(text):
    assert card_bucket(text) == "card_required"


@pytest.mark.parametrize(
    "text", [None, "", "Verify", "No (unless you exceed the quota)", "Sometimes", "N/A"]
)
def test_anything_unclear_is_verify_never_card_free(text):
    assert card_bucket(text) == "verify"


@pytest.mark.parametrize(
    ("text", "bucket"),
    [
        ("Yes", "yes"),
        (" yes ", "yes"),
        ("Yes (personal only)", "verify"),
        (None, "verify"),
    ],
)
def test_commercial_use_is_yes_only_when_the_catalog_says_exactly_yes(text, bucket):
    assert commercial_bucket(text) == bucket


def test_a_projected_service_carries_both_buckets_and_nulls_empty_text():
    service = project_service(
        {"id": "w", "credit_card_required": "No", "commercial_use": "Yes", "notes": ""}
    )
    assert service["card_bucket"] == "no_card"
    assert service["commercial_bucket"] == "yes"
    assert service["notes"] is None
    assert service["free_limits"] is None


def test_text_is_cut_to_400_characters_and_the_id_to_80():
    service = project_service({"id": "i" * 100, "notes": "n" * 500, "storage": 5})
    assert len(service["id"]) == 80
    assert len(service["notes"]) == 400
    assert service["storage"] == "5"


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://x.example/docs", "https://x.example/docs"),
        ("http://x.example/docs", None),
        ("javascript:alert(1)", None),
        (None, None),
        ("https://x.example/" + "p" * 400, ("https://x.example/" + "p" * 400)[:300]),
    ],
)
def test_only_https_official_urls_are_kept_and_cut_to_300(url, expected):
    assert project_service({"id": "x", "official_url": url})["official_url"] == expected


@pytest.fixture
def api(make_api):
    return make_api(
        {
            "id": "a",
            "category": "Compute",
            "credit_card_required": "No",
            "commercial_use": "Yes",
        },
        {
            "id": "b",
            "category": "Compute",
            "credit_card_required": "Yes",
            "commercial_use": "Yes",
        },
        {"id": "c", "category": "Database", "credit_card_required": "Maybe"},
    )


def ids(api, query: str) -> list[str]:
    response = api.handle("GET", "/api/v1/saas" + query)
    assert response.status == 200, response.payload
    return [service["id"] for service in response.payload["services"]]


def test_card_and_commercial_filters_use_the_buckets(api):
    assert ids(api, "?card=no_card") == ["a"]
    assert ids(api, "?card=card_required") == ["b"]
    assert ids(api, "?card=verify") == ["c"]
    assert ids(api, "?commercial=yes") == ["a", "b"]
    assert ids(api, "?commercial=verify&card=verify") == ["c"]


@pytest.mark.parametrize("query", ["?card=free", "?commercial=no", "?card=NO_CARD"])
def test_an_unknown_bucket_filter_is_a_400(api, query):
    response = api.handle("GET", "/api/v1/saas" + query)
    assert response.status == 400
    assert response.payload["error"]["code"] == "invalid_field"


def test_summary_and_signals_count_every_bucket(api):
    payload = api.handle("GET", "/api/v1/saas").payload
    assert payload["summary"]["no_card"] == 1
    assert payload["summary"]["commercial_yes"] == 2
    assert payload["summary"]["needs_verification"] == 1
    assert payload["signals"]["card"] == [
        {"value": "no_card", "count": 1},
        {"value": "card_required", "count": 1},
        {"value": "verify", "count": 1},
    ]
    assert payload["signals"]["commercial"] == [
        {"value": "yes", "count": 2},
        {"value": "verify", "count": 1},
    ]
