# The schema-driven CLI

This guide is for **module authors**: how your entrypoints get their
command-line interface from the shared engine in `common/`, so Python and R
modules share one contract and you declare the CLI once, as data.

## The idea

An entrypoint doesn't hand-roll `argparse`. The flags it accepts are declared
once, as JSON, in `common/schema/`, and `common/cli.py` / `common/cli.R` build
the parser from it. Same schema → an identical parser in both languages.

```python
from common.cli import parse_args     # Python
args = parse_args("pca")              # build + parse the "pca" interface
# args.output_dir, args.name, args.input_h5, args.solver, ...
```
```r
source("common/cli.R")                # R (no import namespace; we source())
args <- parse_args("pca")
# args$output_dir, args$name, args$input_h5, args$solver, ...
```

Pass the interface name. Omit it (`parse_args()`) only when the module carries
exactly one stage schema.

## A schema

A stage's I/O contract is one file, `common/schema/<interface>.json`:

<!-- embed:src/common/schema/embedding.json -->
```json
{
  "interface": "embedding",
  "version": "0.1.0",
  "benchmark": "omni-scrna/split-stages-plan",
  "args": [
    { "flag": "--pcas.tsv", "dest": "pcas", "type": "path", "help": "PCA TSV (embedding matrix, cell_ids as rownames)" },
    { "flag": "--rawdata.clusters_truth", "dest": "clusters_truth", "type": "path", "help": "TSV of ground-truth cluster labels (cell_id, truths)" }
  ]
}
```
<!-- /embed -->

Top level: `interface` (its name), `version`, and an optional `benchmark`. Each
entry in `args` is one flag:

| field | required | meaning |
|---|---|---|
| `flag` | yes | the option string, e.g. `--pcas.tsv` |
| `type` | yes | `path` \| `string` \| `integer` \| `number` |
| `help` | no | help text |
| `dest` | no | attribute name (see defaulting below) |
| `choices` | no | allowed values — an enum |

Every arg is **required** (a run must be reproducible from its invocation line),
and unknown flags are rejected.

### Types

| `type` | Python | R |
|---|---|---|
| `path` | `pathlib.Path` | character |
| `string` | `str` | character |
| `integer` | `int` | integer |
| `number` | `float` | double |

`path` and `string` differ only by the Python type you get back (a `Path` is
handy for `open`/`mkdir`); both accept any string on the command line.

### Options (enums) — `choices`

Restrict a flag to a fixed set, exactly like `argparse` `choices`:

```json
{ "flag": "--solver", "type": "string", "choices": ["arpack", "randomized"] }
```

An out-of-set value is rejected with a clear message **before** your code runs —
so a method's valid solvers/flavors stay declared as data, not re-checked by hand.

### `dest` — the attribute name

By default a flag becomes an attribute with leading dashes stripped and `.`/`-`
turned into `_`: `--pcas.tsv` → `args.pcas_tsv`. Override it with `dest` when you
want a tidier name:

```json
{ "flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path" }
```

## Layering: `_base` + stage + `.extends`

A real interface is composed from up to three files in `common/schema/`, each
contributing args. **Later layers win per `flag`:**

| file | what it holds | who owns it | on `pull` / update |
|---|---|---|---|
| `_base.json` | universal args every module gets (`--output_dir`, `--name`) | boilerplate | overwritten |
| `<interface>.json` | the stage's I/O contract | the benchmark | overwritten |
| `<interface>.extends.json` | module-local extras / overrides (method params) | **you** | never touched |

`_base.json` (vendored, shipped with the engine):

<!-- embed:src/common/schema/_base.json -->
```json
{
  "interface": "_base",
  "version": "0.1.0",
  "args": [
    { "flag": "--output_dir", "type": "path", "help": "Output directory for results" },
    { "flag": "--name", "type": "string", "help": "Module name/identifier" }
  ]
}
```
<!-- /embed -->

`parse_args("pca")` discovers and merges all three by name — your entrypoint code
doesn't change. A module that carries only `<interface>.json` behaves exactly
like a single flat schema, so adopting the layers is opt-in.

> **Why a separate `.extends.json` instead of editing `<interface>.json`?**
> `<interface>.json` (and `_base.json`) are **reserved, overwrite-on-update**
> files — `pull` (and later `copier update`) rewrite them from upstream. Your
> method parameters live in `<interface>.extends.json`, a *different file* the
> update never overwrites. Listing the same `flag` in the overlay **overrides**
> the lower layer (to narrow `choices`, change `help`, …) without forking the
> upstream file.

Files starting with `_` or ending `.extends.json` are **not stages**, so the
single-schema auto-pick (`parse_args()` with no name) ignores them.

### Worked example

Stage contract `pca.json` (benchmark-owned — just the stage's I/O):

```json
{ "interface": "pca", "version": "0.1.0",
  "args": [
    { "flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path" }
  ] }
```

Your method parameters, `pca.extends.json` (yours to keep and edit):

```json
{ "interface": "pca",
  "args": [
    { "flag": "--solver", "type": "string", "choices": ["arpack", "randomized"] },
    { "flag": "--n_components", "type": "integer" },
    { "flag": "--random_seed", "type": "integer" }
  ] }
```

Merged, `parse_args("pca")` accepts:

```
--output_dir  --name                     (from _base.json)
--normalized_selected.h5                 (from pca.json)
--solver  --n_components  --random_seed  (from pca.extends.json)
```

## Naming an interface

An interface name is the **entrypoint** your module exposes for a stage (`pca`,
`knn`) — the stable handle the plan binds you by (`repository.entrypoint:` in the
benchmark definition). It is *not* the plan's internal stage `id` (those carry
ordinal prefixes, e.g. `five-pca`). Stage-id, entrypoint, and output namespaces
are distinct and **mapped, not unified** — so never rename your existing flags or
outputs just to "match" a stage id.

## Where the files come from

`common/cli.*` and `_base.json` are vendored from the boilerplate; each stage
`<interface>.json` from the benchmark. Until `ob` owns this, refresh them with
the boilerplate's `pull.py`, run **from your module root** against a sibling
checkout of the boilerplate:

```sh
cd my-module && python ../boilerplate/scripts/pull.py
```

It fetches at the ref pinned in your `omnibenchmark.yaml`. Your `.extends.json`
overlays are yours and stay put. See [`AGENTS.md`](../AGENTS.md) and
[adding CI](ci.md).

---

> The `_base.json` and `embedding.json` blocks above are embedded verbatim from
> `src/common/schema/` and kept in sync by `pixi run docs` (see
> [`scripts/embed_snippets.py`](../scripts/embed_snippets.py)). Don't edit them
> by hand.
