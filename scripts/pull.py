#!/usr/bin/env python3
"""Vendor the shared engine + stage schemas into a module (interim, pre-`ob`).

Reads ./omnibenchmark.yaml and pulls, at pinned refs, via shallow+sparse git:

  - `boilerplate:` {repo, ref, lang} -> the common engine (cli.*), into
    ./src/common/ (the import package: with `src/` on the path, `from common
    import cli`).
  - the benchmark's schemas, into ./src/common/schema/: `_base.json` (universal)
    plus each `implements: <label>/<iface>@<ver>` -> the benchmark's authoritative
    schema/<iface>.json (repo/ref from the matching `template-for` entry).

It also records the *resolved* sources in ./src/common/.provenance.json — the
engine commit and each benchmark the schemas came from (repo/ref/commit) — an
exact sync witness, independent of `src/common/VERSION` (which only moves on a
bump). Commit it: it's the record of what this module carries, especially when a
`ref` is a moving branch.

This is the interim distribution mechanism; `ob` will subsume it. The script is
CWD-relative (it reads ./omnibenchmark.yaml and writes ./src/common), so its own
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


def _write_provenance(common: Path, engine: dict | None, schemas: list[dict]) -> None:
    """Witness exactly what was vendored and from where: the engine source and each
    benchmark the schemas came from (repo / ref / resolved commit). Independent of
    the engine VERSION (which only moves on a bump). Commit it."""
    common.mkdir(parents=True, exist_ok=True)
    prov = {
        "engine": engine,
        "schemas": schemas,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (common / ".provenance.json").write_text(json.dumps(prov, indent=2) + "\n")


def _vendor_common(bp: dict, common: Path) -> dict:
    """Copy the engine (cli.* + VERSION) from the boilerplate. Returns the engine
    source record for provenance."""
    lang = bp.get("lang", "python")
    ref = bp.get("ref", "main")
    src = _sparse_fetch(bp["repo"], ref, ["src/common"])
    try:
        # Only the engine comes from the boilerplate now; schemas (incl. _base)
        # come from the benchmark — see _vendor_schemas.
        _copy_glob(src / "src" / "common" / lang, common)
        version_file = src / "src" / "common" / "VERSION"
        version = version_file.read_text().strip() if version_file.exists() else None
        if version is not None:
            shutil.copy2(version_file, common / "VERSION")
        commit = _git_head(src)
    finally:
        shutil.rmtree(src, ignore_errors=True)
    return {"repo": bp["repo"], "ref": ref, "commit": commit,
            "version": version, "lang": lang}


def _fetch_schemas_from(bench: dict, names: list[str],
                        schema_dir: Path) -> tuple[list[str], str | None]:
    """Fetch schema/<name>.json for each name from one benchmark in a single sparse
    checkout. Returns (names actually vendored, the benchmark's resolved commit)."""
    ref = bench.get("ref", "main")
    # Sparse-checkout the schema/ dir (cone mode takes directories, not files),
    # then copy the specific files we want.
    try:
        src = _sparse_fetch(bench["repo"], ref, ["schema"])
    except subprocess.CalledProcessError:
        print(f"skip {bench['repo']}@{ref}: fetch failed", file=sys.stderr)
        return [], None
    try:
        schema_dir.mkdir(parents=True, exist_ok=True)
        got = []
        for n in names:
            f = src / "schema" / f"{n}.json"
            if f.exists():
                shutil.copy2(f, schema_dir / f"{n}.json")
                print(f"vendored src/common/schema/{n}.json from {bench['repo']}@{ref}")
                got.append(n)
            else:
                print(f"note: schema/{n}.json not published in {bench['repo']} yet",
                      file=sys.stderr)
        return got, _git_head(src)
    finally:
        shutil.rmtree(src, ignore_errors=True)


def _vendor_schemas(cfg: dict, common: Path) -> tuple[int, int, list[dict]]:
    """Vendor _base + each implemented schema from the benchmark(s) in template-for.
    Returns (vendored count, pending count, per-benchmark provenance records)."""
    benches = {
        e["name"]: e
        for e in (cfg.get("template-for") or [])
        if isinstance(e, dict) and "name" in e
    }
    schema_dir = common / "schema"

    # What to fetch from which benchmark: _base from the first template-for (it's
    # the same everywhere), plus each implemented schema from its label's benchmark.
    wanted: dict[str, set[str]] = {}
    if benches:
        wanted[next(iter(benches))] = {"_base"}
    unresolved = 0
    for item in cfg.get("implements") or []:
        m = _IMPL.match(str(item))
        if not m:
            continue
        if m["label"] not in benches:
            print(f"skip {item}: no template-for label '{m['label']}'", file=sys.stderr)
            unresolved += 1
            continue
        wanted.setdefault(m["label"], set()).add(m["iface"])

    vendored = missing = 0
    records: list[dict] = []
    for label, names in wanted.items():
        bench = benches[label]
        got, commit = _fetch_schemas_from(bench, sorted(names), schema_dir)
        vendored += len(got)
        missing += len(names) - len(got)
        if got:
            records.append({"benchmark": label, "repo": bench["repo"],
                            "ref": bench.get("ref", "main"), "commit": commit,
                            "files": got})
    return vendored, unresolved + missing, records


def main() -> int:
    cfg = yaml.safe_load((Path.cwd() / "omnibenchmark.yaml").read_text()) or {}
    common = Path.cwd() / "src" / "common"
    bp = cfg.get("boilerplate")
    engine = _vendor_common(bp, common) if bp else None
    vendored, pending, schemas = _vendor_schemas(cfg, common)
    _write_provenance(common, engine, schemas)

    if engine:
        msg = (f"OK: synced src/common/ <- {engine['repo']}@{engine['ref']} "
               f"{engine['commit'][:12]} (v{engine['version']})")
    else:
        msg = "OK: nothing to sync (no `boilerplate:` in omnibenchmark.yaml)"
    if vendored or pending:
        msg += f"; schemas: {vendored} vendored, {pending} pending"
    print(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
