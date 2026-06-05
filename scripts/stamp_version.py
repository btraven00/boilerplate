#!/usr/bin/env python3
"""Stamp src/common/VERSION into the language sources as a literal.

Single source of truth = src/common/VERSION. Each line tagged `x-release-version`
(a comment — `#` in both Python and R) has its first quoted string rewritten to
the current version, so the vendored copy carries `__version__` / `COMMON_VERSION`
with no runtime file dependency.

    stamp_version.py            # rewrite stamps in place
    stamp_version.py --check    # exit non-zero if any stamp is stale (CI)

This tool lives only in the boilerplate repo; it is never copied into modules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = (ROOT / "src" / "common" / "VERSION").read_text().strip()
TARGETS = ["src/common/python/cli.py", "src/common/r/cli.R"]
TAG = "x-release-version"
_QUOTED = re.compile(r"""(["'])[^"']*\1""")


def _restamp(text: str) -> str:
    out = []
    for line in text.splitlines(keepends=True):
        if TAG in line:
            line = _QUOTED.sub(f'"{VERSION}"', line, count=1)
        out.append(line)
    return "".join(out)


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale = []
    for rel in TARGETS:
        path = ROOT / rel
        old = path.read_text()
        new = _restamp(old)
        if new == old:
            continue
        if check:
            stale.append(rel)
        else:
            path.write_text(new)
            print(f"stamped {rel} -> {VERSION}")
    if check and stale:
        print("stale version stamp (run `pixi run version`): " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
