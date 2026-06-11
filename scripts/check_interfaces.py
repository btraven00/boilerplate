#!/usr/bin/env python3
"""Check that omnibenchmark.yaml `implements` matches the carried interfaces.

For each `implements: <label>/<interface>@<version>`:
  - <label> must be defined in `template-for` (by `name`),
  - <schema-dir>/<interface>.json must exist with a matching `interface`
    and `version`.

Schemas are read from `--schema-dir` (default `src/common/schema`, where a real
module's vendored copies live). The boilerplate itself carries no source schemas
— they now live in the plan's `schema/` — so its own CI points this at the
example fixtures in `tests/fixtures/schema/`.

Exits non-zero on any mismatch — a CI gate that keeps a module's declared
interfaces and the schemas it carries in sync. Lives only in the boilerplate.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
_IMPL = re.compile(r"^(?P<label>[^/]+)/(?P<iface>[^@]+)@(?P<ver>.+)$")


def check(root: Path, schema_dir: Path | None = None) -> list[str]:
    """Return a list of human-readable problems (empty == consistent)."""
    errors: list[str] = []
    data = yaml.safe_load((root / "omnibenchmark.yaml").read_text()) or {}

    labels = {
        e["name"]
        for e in (data.get("template-for") or [])
        if isinstance(e, dict) and "name" in e
    }
    schema_dir = schema_dir or root / "src" / "common" / "schema"

    for item in data.get("implements") or []:
        m = _IMPL.match(str(item))
        if not m:
            errors.append(f"implements '{item}': want <label>/<interface>@<version>")
            continue
        label, iface, ver = m["label"], m["iface"], m["ver"]
        if label not in labels:
            errors.append(f"implements '{item}': label '{label}' not in template-for")
        schema = schema_dir / f"{iface}.json"
        if not schema.is_file():
            errors.append(f"implements '{item}': missing schema {iface}.json")
            continue
        spec = json.loads(schema.read_text())
        if spec.get("interface") != iface:
            errors.append(f"{iface}.json: interface is '{spec.get('interface')}'")
        if str(spec.get("version")) != ver:
            errors.append(
                f"{iface}.json: version '{spec.get('version')}' != declared '{ver}'")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--schema-dir", type=Path, default=None,
                    help="dir holding <interface>.json (default src/common/schema)")
    args = ap.parse_args()
    schema_dir = args.schema_dir
    if schema_dir is not None and not schema_dir.is_absolute():
        schema_dir = ROOT / schema_dir
    errors = check(ROOT, schema_dir)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)
    if errors:
        return 1
    print("interfaces: implements <-> schemas consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
