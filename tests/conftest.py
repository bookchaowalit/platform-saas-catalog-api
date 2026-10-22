"""Shared fixture: a SaasCatalogApi over a throwaway catalog file (development auth, no network)."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from server import CATALOG_CONTRACT, SaasCatalogApi

MakeApi = Callable[..., SaasCatalogApi]


@pytest.fixture
def catalog_path(tmp_path: Path) -> Path:
    return tmp_path / "catalog.json"


@pytest.fixture
def make_api(catalog_path: Path) -> MakeApi:
    def make(*services: dict[str, Any], **catalog: Any) -> SaasCatalogApi:
        payload = {"contract": CATALOG_CONTRACT, "services": list(services), **catalog}
        catalog_path.write_text(json.dumps(payload), encoding="utf-8")
        return SaasCatalogApi(catalog_path, token="", environment="development")

    return make
