#!/usr/bin/env python3
"""Refresh or check data/free-saas-master-catalog-2026.json against the solo-empire source.

solo-empire owns the catalog: `task free:saas -- import` (infra/scripts/discovery/free_saas_catalog.py)
generates systems/cloud-platform/free-saas-master-catalog-2026.json from its workbook. This repository only ships a
deployable snapshot, so it can drift. This command copies the source after validating its
shape, or reports staleness.

Source resolution: --source, then $SOLO_EMPIRE_ROOT/systems/cloud-platform/free-saas-master-catalog-2026.json, then the
nearest ancestor checkout that contains infra/scripts/discovery/free_saas_catalog.py.

    python3 scripts/sync_catalog.py           # validate and copy the source over the snapshot
    python3 scripts/sync_catalog.py --check   # exit 1 when the snapshot differs from the source
    python3 scripts/sync_catalog.py --check --skip-missing   # exit 0 with a warning when the source is absent (CI)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT = "solo-empire.free-saas-catalog.v1"
SOURCE_REL = Path("systems") / "cloud-platform" / "free-saas-master-catalog-2026.json"
GENERATOR_REL = Path("infra") / "scripts" / "discovery" / "free_saas_catalog.py"
DEST = Path(__file__).resolve().parents[1] / "data" / "free-saas-master-catalog-2026.json"
MAX_BYTES = 20 * 1024 * 1024  # snapshot is ~0.7 MB; guards against a wrong file


def find_source_root(start: Path = Path(__file__).resolve()) -> Path | None:
    override = os.environ.get("SOLO_EMPIRE_ROOT")
    if override:
        return Path(override).expanduser()
    for parent in start.parents:
        if (parent / GENERATOR_REL).is_file():
            return parent
    return None


def default_source() -> Path | None:
    root = find_source_root()
    return root / SOURCE_REL if root else None


def validate_catalog(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["catalog must be a JSON object"]
    errors: list[str] = []
    if payload.get("contract") != CONTRACT:
        errors.append(f"contract must be {CONTRACT}")
    services = payload.get("services")
    if not isinstance(services, list) or not services:
        return errors + ["services must be a non-empty list"]
    seen: set[str] = set()
    for index, record in enumerate(services):
        ident = record.get("id") if isinstance(record, dict) else None
        if not isinstance(ident, str) or not ident:
            errors.append(f"services[{index}]: id must be a non-empty string")
        elif ident in seen:
            errors.append(f"duplicate service id: {ident}")
        else:
            seen.add(ident)
    return errors


def load_validated(source: Path) -> tuple[bytes, dict[str, Any]]:
    raw = source.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{source} exceeds the {MAX_BYTES} byte catalog limit")
    payload = json.loads(raw.decode("utf-8"))
    errors = validate_catalog(payload)
    if errors:
        raise ValueError("invalid catalog: " + "; ".join(errors[:5]))
    return raw, payload


def is_current(source_payload: dict[str, Any], dest: Path) -> bool:
    try:
        return json.loads(dest.read_text(encoding="utf-8")) == source_payload
    except (OSError, ValueError):
        return False


def atomic_write(dest: Path, data: bytes) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=dest.parent, prefix=".catalog-", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        os.replace(tmp, dest)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", type=Path, help="solo-empire free-saas-master-catalog-2026.json (default: auto-detected)")
    parser.add_argument("--dest", type=Path, default=DEST, help="snapshot to write or check")
    parser.add_argument("--check", action="store_true", help="do not write; exit 1 when the snapshot is stale")
    parser.add_argument("--skip-missing", action="store_true", help="exit 0 with a warning when the source is absent")
    args = parser.parse_args(argv)

    source = args.source or default_source()
    if source is None or not source.is_file():
        message = f"solo-empire SaaS catalog not found ({source or 'no solo-empire checkout above this repo'}); set SOLO_EMPIRE_ROOT or --source"
        if args.skip_missing:
            print(f"WARN: {message}; skipping", file=sys.stderr)
            return 0
        print(f"FAIL: {message}", file=sys.stderr)
        return 2

    try:
        raw, payload = load_validated(source)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2

    current = is_current(payload, args.dest)
    count = len(payload["services"])
    if args.check:
        if current:
            print(f"OK: {args.dest.name} matches the source ({count} services)")
            return 0
        print(f"STALE: {args.dest} differs from {source}; run `python3 scripts/sync_catalog.py`", file=sys.stderr)
        return 1
    if current:
        print(f"OK: {args.dest.name} already current ({count} services)")
        return 0
    atomic_write(args.dest, raw)
    print(f"OK: wrote {args.dest} ({count} services) from {source}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
