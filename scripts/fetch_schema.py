#!/usr/bin/env python3
"""Fetch the plan's schema/ into tests/fixtures/schema/ for the test run.

The cli helpers are tested against the **real**, benchmark-owned schemas, not a
checked-in copy. This fetches them fresh from the plan (the same source pull.py
uses for a real module) into a gitignored dir the tests read. CI runs this before
`pixi run check`; run it locally once before `pixi run test`.

  fetch_schema.py                        # fetch into tests/fixtures/schema/
  fetch_schema.py --repo ... --ref ...   # override the plan source

The plan repo+ref come from omnibenchmark.yaml's `plan` entry unless overridden.
If the plan publishes no schema/ yet, this is a no-op.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pull import _sparse_fetch  # noqa: E402 — share the (cone-mode-safe) clone helper

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "tests" / "fixtures" / "schema"


def _plan_source(repo: str | None, ref: str | None) -> tuple[str, str]:
    """Resolve the plan repo+ref: CLI overrides, else the `plan` entry."""
    if repo and ref:
        return repo, ref
    cfg = yaml.safe_load((ROOT / "omnibenchmark.yaml").read_text()) or {}
    plan = cfg.get("plan")
    if not isinstance(plan, dict) or "repo" not in plan:
        sys.exit("no plan entry in omnibenchmark.yaml")
    return repo or plan["repo"], ref or plan.get("ref", "main")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo")
    ap.add_argument("--ref")
    a = ap.parse_args()
    repo, ref = _plan_source(a.repo, a.ref)

    src = _sparse_fetch(repo, ref, ["schema"])
    try:
        plan_schema = src / "schema"
        files = sorted(plan_schema.glob("*.json")) if plan_schema.is_dir() else []
        if not files:
            print(f"note: {repo}@{ref} publishes no schema/ yet — nothing to fetch")
            return 0
        # Clean first so a stage the plan dropped doesn't linger as a stale file.
        if SCHEMA_DIR.exists():
            shutil.rmtree(SCHEMA_DIR)
        SCHEMA_DIR.mkdir(parents=True)
        for f in files:
            shutil.copy2(f, SCHEMA_DIR / f.name)
            print(f"fetched tests/fixtures/schema/{f.name} from {repo}@{ref}")
    finally:
        shutil.rmtree(src, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
