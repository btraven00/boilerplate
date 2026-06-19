#!/usr/bin/env python3
"""Copy over the shared templates + stage schemas into a module (temporary solution until we have a proper distribution mechanism
incorporated in omnibenchmark).

Reads ./omnibenchmark.yaml and pulls, at pinned refs, via shallow+sparse git:

  - `templates:` {repo, ref, lang} -> the common engine (cli.*), into
    ./src/common/ (the import package: with `src/` on the path, `from common
    import cli`).
  - the benchmark's schemas, into ./src/common/schema/: the whole `schema/` dir
    (`_base.json` + every stage `<iface>.json`) of each benchmark in `benchmarks:`.

It also records the *resolved* sources in ./src/common/.origin.json — the
common code commit and each benchmark the schemas came from (repo/ref/commit).
With no version literal in the shared code, the template commit *is* the version
handle. Module author should commit it: it's the record of what this module
carries, especially when a `ref` is a moving branch.

This is a temporary distribution mechanism. `ob` will eventually automate much of this step.

This script takes the module root as an optional argument.

    python boilerplate/scripts/pull.py path/to/module   # or, from the module root:
    cd my-module && python ../boilerplate/scripts/pull.py

`ref` is a branch or tag.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import yaml


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


def _copy_glob(src_dir: Path, dest_dir: Path) -> list[Path]:
    """Copy every file in src_dir into dest_dir. Returns the files written."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for f in src_dir.glob("*"):
        if f.is_file():
            dest = dest_dir / f.name
            shutil.copy2(f, dest)
            written.append(dest)
    return written


def _git_head(repo_dir: Path) -> str:
    """Resolved commit SHA of the (shallow) clone."""
    out = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True)
    return out.stdout.strip()


def _write_provenance(common: Path, engine: dict | None, schemas: list[dict]) -> None:
    """Witness exactly what was copied over and from where: the engine source and
    each benchmark the schemas came from (repo / ref / resolved commit). The engine
    `commit` is the version handle — diff it against the template's latest main to
    check for updates (there is no version literal). Commit it."""
    common.mkdir(parents=True, exist_ok=True)
    prov = {
        "common": engine,
        "schemas": schemas,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (common / ".origin.json").write_text(json.dumps(prov, indent=2) + "\n")


def _vendor_common(bp: dict, common: Path) -> tuple[dict, list[Path]]:
    """Copy the engine (cli.*) from the boilerplate. Returns the engine source
    record (for provenance) and the files written."""
    lang = bp.get("lang", "python")
    ref = bp.get("ref", "main")
    src = _sparse_fetch(bp["repo"], ref, ["src/common"])
    try:
        # Only the engine comes from the boilerplate now; schemas (incl. _base)
        # come from the benchmark — see _vendor_schemas.
        written = _copy_glob(src / "src" / "common" / lang, common)
        commit = _git_head(src)
    finally:
        shutil.rmtree(src, ignore_errors=True)
    return {"repo": bp["repo"], "ref": ref, "commit": commit, "lang": lang}, written


def _fetch_schemas_from(bench: dict, schema_dir: Path) -> tuple[list[str], str | None]:
    """Vendor the whole schema/ dir (every *.json) of one benchmark in a single
    sparse checkout. Returns (names vendored, the benchmark's resolved commit)."""
    ref = bench.get("ref", "main")
    try:
        src = _sparse_fetch(bench["repo"], ref, ["schema"])
    except subprocess.CalledProcessError:
        print(f"skip {bench['repo']}@{ref}: fetch failed", file=sys.stderr)
        return [], None
    try:
        files = sorted((src / "schema").glob("*.json")) if (src / "schema").is_dir() else []
        if not files:
            print(f"note: {bench['repo']}@{ref} publishes no schema/ yet", file=sys.stderr)
            return [], _git_head(src)
        schema_dir.mkdir(parents=True, exist_ok=True)
        got = []
        for f in files:
            shutil.copy2(f, schema_dir / f.name)
            got.append(f.stem)
        return got, _git_head(src)
    finally:
        shutil.rmtree(src, ignore_errors=True)


def _vendor_schemas(cfg: dict, common: Path) -> tuple[list[Path], list[dict]]:
    """Vendor each benchmark's whole schema/ dir into src/common/schema/. A module
    carries every schema its benchmark(s) publish; the engine loads one by name at
    runtime and errors if it's absent (no separate `implements` ledger).
    Returns (files written, per-benchmark provenance records)."""
    benches = [
        e for e in (cfg.get("benchmarks") or [])
        if isinstance(e, dict) and "repo" in e
    ]
    schema_dir = common / "schema"

    written: list[Path] = []
    records: list[dict] = []
    for bench in benches:
        got, commit = _fetch_schemas_from(bench, schema_dir)
        written += [schema_dir / f"{stem}.json" for stem in got]
        if got:
            records.append({"benchmark": bench.get("name", bench["repo"]),
                            "repo": bench["repo"], "ref": bench.get("ref", "main"),
                            "commit": commit, "files": got})
    return written, records


def _sync_summary(root: Path, written: list[Path]) -> None:
    """Git-style summary of what this sync did to the module's tree: which copied
    files are new, which were already up to date (unchanged), and which had local
    edits the copy overwrote (changed — shouldn't happen; the upstream copy is the
    source of truth). Classifies each written file against the module's git index.
    Falls back to a plain list when the module isn't a git repo."""
    if not written:
        return
    try:
        top = Path(subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            check=True, capture_output=True, text=True).stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        rels = sorted(str(p.relative_to(root)) for p in written)
        print(f"\nsynced {len(rels)} files (not a git repo — no status breakdown):")
        for rel in rels:
            print(f"    {rel}")
        return

    rels = sorted(str(p.relative_to(top)) for p in written)
    out = subprocess.run(
        ["git", "-C", str(top), "status", "--porcelain", "--untracked-files=all",
         "--", *rels], check=True, capture_output=True, text=True)
    codes = {line[3:]: line[:2] for line in out.stdout.splitlines()}

    new, changed, unchanged = [], [], []
    for rel in rels:
        code = codes.get(rel, "")
        if code in ("??", "A ", "AM"):
            new.append(rel)
        elif code:                  # tracked but differs from index/HEAD
            changed.append(rel)
        else:                       # not reported by git -> matches what's committed
            unchanged.append(rel)

    print("\nsync summary:")
    for rel in new:
        print(f"    new        {rel}")
    for rel in changed:
        print(f"    changed!   {rel}  (local edits overwritten)")
    for rel in unchanged:
        print(f"    unchanged  {rel}")
    print(f"  {len(new)} new, {len(changed)} changed, {len(unchanged)} unchanged")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    cfg = yaml.safe_load((root / "omnibenchmark.yaml").read_text()) or {}
    common = root / "src" / "common"
    bp = cfg.get("templates")

    written: list[Path] = []
    if bp:
        engine, engine_files = _vendor_common(bp, common)
        written += engine_files
    else:
        engine = None
    schema_files, schemas = _vendor_schemas(cfg, common)
    written += schema_files
    _write_provenance(common, engine, schemas)

    _sync_summary(root, written)

    if engine:
        msg = (f"OK: synced src/common/ <- {engine['repo']}@{engine['ref']} "
               f"{engine['commit'][:12]}")
    else:
        msg = "OK: nothing to sync (no `templates:` in omnibenchmark.yaml)"
    if schema_files:
        msg += f"; schemas: {len(schema_files)} copied"
    print(msg)
    print("note: commit the schemas you use (src/common/schema/) along with "
          "src/common/.origin.json — they record what this module uses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
