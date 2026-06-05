"""Schema-driven CLI parsing for omnibenchmark module entrypoints (Python).

Reserved, overwrite-on-update path (``src/common/python/``) — see AGENTS.md.
The CLI an entrypoint accepts is defined as **data**, once, in
``src/common/schema/<interface>.json``, and built into a parser identically here
and in ``src/common/r/cli.R`` so Python and R entrypoints share one contract.

An *interface* is a named, versioned CLI contract owned by a benchmark; a module
"satisfies" it by carrying its schema and parsing against it. Schema shape::

    {
      "interface": "embedding",
      "version": "0.1.0",
      "benchmark": "omni-scrna/split-stages-plan",
      "args": [
        {"flag": "--name", "type": "string", "help": "...", "dest": "<optional>"},
        ...
      ]
    }

Conventions: every arg is **required** (a run is reproducible from its
invocation line); unknown flags are rejected; ``dest`` defaults to the flag with
dots/dashes turned into ``_`` (``--pcas.tsv`` -> ``pcas_tsv``) unless the schema
overrides it. Types: ``path | string | integer | number``.

Usage in an entrypoint (in a rendered module the shared code is the ``common``
package)::

    from common.cli import parse_args
    args = parse_args("embedding")        # or parse_args() if the module has one schema
    # args.output_dir, args.name, args.pcas, args.clusters_truth
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

__version__ = "0.1.0"  # x-release-version — stamped from src/common/VERSION by `pixi run version`

def _find_schema_dir() -> Path:
    # Works under both layouts: rendered `common/cli.py` (schema is a sibling)
    # and the template's `common/python/cli.py` (schema is one level up).
    here = Path(__file__).resolve().parent
    for base in (here, here.parent):
        if (base / "schema").is_dir():
            return base / "schema"
    return here / "schema"


_SCHEMA_DIR = _find_schema_dir()
_TYPES = {"path": Path, "string": str, "integer": int, "number": float}


def common_version() -> str:
    """Version of the src/common shared code, so a module can report which copy
    of the boilerplate scaffolding it carries. Stamped from src/common/VERSION
    (single source of truth) — bump VERSION and run `pixi run version`."""
    return __version__


def _default_dest(flag: str) -> str:
    return flag.lstrip("-").replace(".", "_").replace("-", "_")


def load_interface(interface: str | None = None, schema_dir: Path = _SCHEMA_DIR) -> dict:
    """Load an interface schema by name; if None, auto-pick the sole schema."""
    if interface is None:
        found = sorted(schema_dir.glob("*.json"))
        if len(found) != 1:
            raise SystemExit(
                f"specify an interface; found {len(found)} schemas in {schema_dir}")
        path = found[0]
    else:
        path = schema_dir / f"{interface}.json"
    if not path.is_file():
        raise SystemExit(f"interface schema not found: {path}")
    with open(path) as f:
        return json.load(f)


def build_parser(schema: dict) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{schema.get('interface', 'module')} interface "
                    f"v{schema.get('version', '?')}")
    for arg in schema["args"]:
        parser.add_argument(
            arg["flag"],
            required=True,
            dest=arg.get("dest", _default_dest(arg["flag"])),
            type=_TYPES.get(arg["type"], str),
            help=arg.get("help", ""),
        )
    return parser


def parse_args(interface: str | None = None, argv=None) -> argparse.Namespace:
    return build_parser(load_interface(interface)).parse_args(argv)


if __name__ == "__main__":  # smoke / live demo
    a = parse_args()
    for k, v in sorted(vars(a).items()):
        print(f"{k}={v}")
