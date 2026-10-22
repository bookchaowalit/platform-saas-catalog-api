#!/usr/bin/env python3
"""Check that the shipped snapshot data/free-saas-master-catalog-2026.json has the expected shape.

The snapshot is a deployable data file owned by this repository. The generator that
produces fresh content lives elsewhere and writes the file here; this command only
validates the shape (contract, non-empty services, unique id).

    python3 scripts/validate_catalog.py [--path FILE]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

CONTRACT = "solo-empire.free-saas-catalog.v1"
DEST = (
    Path(__file__).resolve().parents[1] / "data" / "free-saas-master-catalog-2026.json"
)
MAX_BYTES = 20 * 1024 * 1024


def validate_catalog(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return ["catalog must be a JSON object"]
    errors: list[str] = []
    if payload.get("contract") != CONTRACT:
        errors.append(f"contract must be {CONTRACT}")
    records = payload.get("services")
    if not isinstance(records, list) or not records:
        return [*errors, "services must be a non-empty list"]
    seen: set[str] = set()
    for index, record in enumerate(records):
        ident = record.get("id") if isinstance(record, dict) else None
        if not isinstance(ident, str) or not ident:
            errors.append(f"services[{index}]: id must be a non-empty string")
        elif ident in seen:
            errors.append(f"duplicate id: {ident}")
        else:
            seen.add(ident)
    return errors


def load_validated(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{path} exceeds the {MAX_BYTES} byte catalog limit")
    payload: dict[str, Any] = json.loads(raw.decode("utf-8"))  # a dict once validated
    errors = validate_catalog(payload)
    if errors:
        raise ValueError("invalid catalog: " + "; ".join(errors[:5]))
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--path", type=Path, default=DEST, help="snapshot to validate")
    args = parser.parse_args(argv)
    try:
        payload = load_validated(args.path)
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 2
    print(f"OK: {args.path.name} is valid ({len(payload['services'])} services)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
