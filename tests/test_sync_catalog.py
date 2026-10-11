"""Tests for scripts/sync_catalog.py (validate, copy, staleness check)."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "sync_catalog.py"
SPEC = importlib.util.spec_from_file_location("sync_catalog", SCRIPT)
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


def catalog(*paths: str) -> dict:
    return {"contract": sync.CONTRACT, "services": [{"id": p, "service": p} for p in paths]}


class SyncCatalogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.source = self.tmp / "source.json"
        self.dest = self.tmp / "data" / "free-saas-master-catalog-2026.json"

    def write_source(self, payload) -> None:
        self.source.write_text(json.dumps(payload), encoding="utf-8")

    def run_main(self, *extra: str) -> int:
        return sync.main(["--source", str(self.source), "--dest", str(self.dest), *extra])

    def test_copies_valid_source_and_then_reports_current(self) -> None:
        self.write_source(catalog("a", "b"))
        self.assertEqual(self.run_main("--check"), 1)  # missing snapshot is stale
        self.assertEqual(self.run_main(), 0)
        self.assertEqual(json.loads(self.dest.read_text()), catalog("a", "b"))
        self.assertEqual(self.run_main("--check"), 0)

    def test_check_never_writes_and_detects_drift(self) -> None:
        self.write_source(catalog("a"))
        self.run_main()
        self.write_source(catalog("a", "c"))
        self.assertEqual(self.run_main("--check"), 1)
        self.assertEqual(len(json.loads(self.dest.read_text())["services"]), 1)

    def test_invalid_shape_is_rejected_and_snapshot_kept(self) -> None:
        self.write_source(catalog("a"))
        self.run_main()
        for bad in ({"services": []}, catalog("a", "a"), [], {"contract": "x", "services": [{"id": "a"}]}):
            self.write_source(bad)
            self.assertEqual(self.run_main(), 2)
        self.assertEqual(json.loads(self.dest.read_text()), catalog("a"))

    def test_missing_source_fails_unless_skip_missing(self) -> None:
        self.assertEqual(self.run_main(), 2)
        self.assertEqual(self.run_main("--check", "--skip-missing"), 0)

    def test_committed_snapshot_has_valid_shape(self) -> None:
        _, payload = sync.load_validated(sync.DEST)
        self.assertGreater(len(payload["services"]), 0)


if __name__ == "__main__":
    unittest.main()
