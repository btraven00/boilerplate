#!/usr/bin/env python3
"""Refresh tests/fixtures/schema/ from the plan's schema/ (boilerplate dev only).

The fixtures are example schemas that exercise the cli helpers offline; the real
schemas live in the plan. This re-vendors them from the plan (the same source
`pull.py` uses for a module), so the engine is tested against the *real* contract.

  refresh_fixtures.py            # overwrite the fixtures from the plan
  refresh_fixtures.py --check    # exit 1 if they differ (CI drift gate)

The plan repo+ref come from omnibenchmark.yaml's first `template-for` entry;
override with --repo/--ref. If the plan publishes no schema/ yet, this is a no-op.
"""
from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pull import _sparse_fetch  # noqa: E402 — share the (cone-mode-safe) clone helper

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures" / "schema"


def _plan_source(repo: str | None, ref: str | None) -> tuple[str, str]:
    """Resolve the plan repo+ref: CLI overrides, else first template-for entry."""
    if repo and ref:
        return repo, ref
    cfg = yaml.safe_load((ROOT / "omnibenchmark.yaml").read_text()) or {}
    tf = [e for e in (cfg.get("template-for") or []) if isinstance(e, dict)]
    if not tf:
        sys.exit("no template-for entry in omnibenchmark.yaml")
    return repo or tf[0]["repo"], ref or tf[0].get("ref", "main")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="fail on drift instead of writing")
    ap.add_argument("--repo")
    ap.add_argument("--ref")
    a = ap.parse_args()
    repo, ref = _plan_source(a.repo, a.ref)

    src = _sparse_fetch(repo, ref, ["schema"])
    try:
        plan_schema = src / "schema"
        files = sorted(plan_schema.glob("*.json")) if plan_schema.is_dir() else []
        if not files:
            print(f"note: {repo}@{ref} publishes no schema/ yet — nothing to refresh")
            return 0

        FIXTURES.mkdir(parents=True, exist_ok=True)
        drift = []
        for f in files:
            dest = FIXTURES / f.name
            if a.check:
                if not dest.exists() or not filecmp.cmp(f, dest, shallow=False):
                    drift.append(f.name)
            else:
                shutil.copy2(f, dest)
                print(f"refreshed tests/fixtures/schema/{f.name}")

        if a.check and drift:
            print(f"error: fixtures drifted from {repo}@{ref}: {', '.join(drift)}\n"
                  f"       run `pixi run refresh-fixtures` to update them.", file=sys.stderr)
            return 1
        if a.check:
            print(f"fixtures match {repo}@{ref}")
    finally:
        shutil.rmtree(src, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
