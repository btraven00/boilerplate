#!/usr/bin/env python3
"""Vendor shared code + interface schemas into a module (interim, pre-`ob`).

Reads ./omnibenchmark.yaml and pulls, at pinned refs, via shallow+sparse git:

  - `boilerplate:` {repo, ref, lang} -> the common engine + schemas, into
    ./common/ (the import package: `from common.cli import parse_args`).
  - each `implements: <label>/<iface>@<ver>` -> the benchmark's authoritative
    interfaces/<iface>.json (repo/ref from the matching `template-for` entry),
    overlaying ./common/schema/<iface>.json.

It also records the *resolved* source commit in ./common/.provenance.json — an
exact sync witness, independent of `common/VERSION` (which only moves on a bump,
so it can't tell apart two states sharing a version). Commit it: it's the record
of what this module carries, especially when `ref` is a moving branch.

This is the interim distribution mechanism; `ob` will subsume it. The script is
CWD-relative (it reads ./omnibenchmark.yaml and writes ./common), so its own
location doesn't matter — run it from your **module root** against the
boilerplate checked out as a sibling repo:

    cd my-module && python ../boilerplate/scripts/pull.py

`ref` is a branch or tag.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml

_IMPL = re.compile(r"^(?P<label>[^/]+)/(?P<iface>[^@]+)@(?P<ver>.+)$")


def _sparse_fetch(repo: str, ref: str, paths: list[str]) -> Path:
    """Shallow + sparse checkout of `paths` from repo@ref; return the temp dir."""
    tmp = Path(tempfile.mkdtemp())
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, "--filter=blob:none",
         "--sparse", repo, str(tmp)], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(tmp), "sparse-checkout", "set", *paths],
        check=True, capture_output=True)
    return tmp


def _copy_glob(src_dir: Path, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    for f in src_dir.glob("*"):
        if f.is_file():
            shutil.copy2(f, dest_dir / f.name)


def _git_head(repo_dir: Path) -> str:
    """Resolved commit SHA of the (shallow) clone."""
    out = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _write_provenance(common: Path, *, repo: str, ref: str, lang: str,
                      commit: str, version: str | None) -> None:
    """Stamp what was vendored, so the module witnesses its sync state exactly —
    even when `ref` is a moving branch and VERSION hasn't been bumped."""
    common.mkdir(parents=True, exist_ok=True)
    prov = {
        "repo": repo,
        "ref": ref,
        "commit": commit,
        "version": version,
        "lang": lang,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (common / ".provenance.json").write_text(json.dumps(prov, indent=2) + "\n")


def _vendor_common(bp: dict, common: Path) -> None:
    lang = bp.get("lang", "python")
    ref = bp.get("ref", "main")
    src = _sparse_fetch(bp["repo"], ref, ["src/common"])
    try:
        _copy_glob(src / "src" / "common" / lang, common)
        _copy_glob(src / "src" / "common" / "schema", common / "schema")
        version_file = src / "src" / "common" / "VERSION"
        version = version_file.read_text().strip() if version_file.exists() else None
        if version is not None:
            shutil.copy2(version_file, common / "VERSION")
        commit = _git_head(src)
        _write_provenance(common, repo=bp["repo"], ref=ref, lang=lang,
                          commit=commit, version=version)
    finally:
        shutil.rmtree(src, ignore_errors=True)
    print(f"vendored common/ ({lang}) from {bp['repo']}@{ref} -> {commit[:12]} (v{version})")


def _vendor_interfaces(cfg: dict, common: Path) -> None:
    benches = {
        e["name"]: e
        for e in (cfg.get("template-for") or [])
        if isinstance(e, dict) and "name" in e
    }
    for item in cfg.get("implements") or []:
        m = _IMPL.match(str(item))
        if not m:
            continue
        bench = benches.get(m["label"])
        if not bench:
            print(f"skip {item}: no template-for label '{m['label']}'", file=sys.stderr)
            continue
        iface, ref = m["iface"], bench.get("ref", "main")
        rel = f"interfaces/{iface}.json"
        try:
            src = _sparse_fetch(bench["repo"], ref, [rel])
        except subprocess.CalledProcessError:
            print(f"skip {item}: fetch from {bench['repo']}@{ref} failed", file=sys.stderr)
            continue
        try:
            if (src / rel).exists():
                shutil.copy2(src / rel, common / "schema" / f"{iface}.json")
                print(f"vendored common/schema/{iface}.json from {bench['repo']}@{ref}")
            else:
                print(f"note {item}: {rel} not published in {bench['repo']} yet",
                      file=sys.stderr)
        finally:
            shutil.rmtree(src, ignore_errors=True)


def main() -> int:
    cfg = yaml.safe_load((Path.cwd() / "omnibenchmark.yaml").read_text()) or {}
    common = Path.cwd() / "common"
    if cfg.get("boilerplate"):
        _vendor_common(cfg["boilerplate"], common)
    _vendor_interfaces(cfg, common)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
