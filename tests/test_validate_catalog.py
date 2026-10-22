"""Tests for scripts/validate_catalog.py (snapshot shape check)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_catalog.py"
SPEC = importlib.util.spec_from_file_location("validate_catalog", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
validator = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(validator)


def catalog(*ids: str) -> dict:
    return {"contract": validator.CONTRACT, "services": [{"id": i} for i in ids]}


class ValidateCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.path = Path(tempfile.mkdtemp()) / "snapshot.json"

    def run_main(self, payload) -> int:
        self.path.write_text(json.dumps(payload), encoding="utf-8")
        return validator.main(["--path", str(self.path)])

    def test_valid_shape_passes(self) -> None:
        assert self.run_main(catalog("a", "b")) == 0

    def test_invalid_shapes_are_rejected(self) -> None:
        bad: object
        for bad in (
            {"contract": "x", "services": []},
            catalog("a", "a"),
            [],
            {"contract": "x", "services": [{"id": "a"}]},
        ):
            assert self.run_main(bad) == 2

    def test_missing_file_fails(self) -> None:
        assert validator.main(["--path", str(self.path.parent / "absent.json")]) == 2

    def test_committed_snapshot_has_valid_shape(self) -> None:
        payload = validator.load_validated(validator.DEST)
        assert len(payload["services"]) > 0


if __name__ == "__main__":
    unittest.main()
