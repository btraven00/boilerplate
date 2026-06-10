# Shared CLI helpers

This guide is for **module authors**: you write your own `argparse` (Python) or
base-R CLI, and import a couple of helpers from `common/` to inject the *shared*
parts that are provided by the benchmark (the universal base args and your
stage's I/O contract), so Python and R modules share the same definition of the
CLI arguments.

## The idea

You own your entrypoint's parser. The flags that are **shared** (the universal
base args, and the stage's I/O contract owned by the benchmark) are declared
once as JSON in the boilerplate repo's `common/schema/` and *added onto your
parser* by using `common/cli`. Your own any method parameters you add by hand,
for python that's plain `argparse`. In this way the whole CLI for an entrypoint
stays visible in your file.

```python
import argparse
from common import cli

p = argparse.ArgumentParser()
cli.add_base_args(p)                 # --output_dir, --name   (common/schema/_base.json)
cli.add_stage_args(p, "embedding")   # the stage I/O contract (common/schema/embedding.json)
# your own method params — plain argparse, fully visible & owned:
p.add_argument("--solver", choices=["arpack", "randomized"], required=True)
p.add_argument("--n_components", type=int, required=True)
args = p.parse_args()
# args.output_dir, args.name, args.pcas, args.solver, args.n_components
```

For R we use base R (TODO: is this fine?), so the idiom is "assemble the spec
list — `common` supplies the shared chunks, you append your own — then parse":

```r
source("common/cli.R")
specs <- c(base_args(),               # --output_dir, --name
           stage_args("embedding"),   # the stage I/O contract
           list(                       # your own method params, fully visible:
             list(flag = "--solver", type = "string", choices = c("arpack", "randomized")),
             list(flag = "--n_components", type = "integer")))
args <- parse_args(specs)
# args$output_dir, args$name, args$pcas, args$solver, args$n_components
```

## A schema

A stage's I/O contract is declared in one file, `common/schema/<stage>.json`:

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

Every schema-declared arg is **required** (a run must be reproducible from its
invocation line, fully explicit, no defaults). Unknown flags are rejected by
your parser.

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

An out-of-set value is rejected with a clear message **before** your code runs.

### `dest` — the attribute name

By default a flag becomes an attribute with leading dashes stripped and `.`/`-`
turned into `_`: `--pcas.tsv` → `args.pcas_tsv`. Override it with `dest` when
you want a tidier name:

```json
{ "flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path" }
```

## What's shared vs. what's yours

Two synced files back the helpers; your method params are not in a schema at all
— you write them as plain `argparse`.

| source | what it holds | who owns it | on `pull` / update |
|---|---|---|---|
| `_base.json` | universal args every module gets (`--output_dir`, `--name`) | boilerplate | overwritten |
| `<interface>.json` | the stage's I/O contract | the benchmark | overwritten |
| your `cli.py` / `cli.R` | your method params (`--solver`, …) | **you** | never touched |

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

`add_base_args` and `add_stage_args` read these two files; your method
parameters stay in your own entrypoint, so a `pull` (or later `copier update`)
that rewrites the synced schema never touches them.

### Worked example

Stage contract `pca.json` (benchmark-owned — just the stage's I/O):

```json
{ "interface": "pca", "version": "0.1.0",
  "args": [
    { "flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path" }
  ] }
```

Your entrypoint composes the shared args + your own method params:

```python
p = argparse.ArgumentParser()
cli.add_base_args(p)                 # --output_dir, --name
cli.add_stage_args(p, "pca")         # --normalized_selected.h5  (-> args.input_h5)
p.add_argument("--solver", choices=["arpack", "randomized"], required=True)
p.add_argument("--n_components", type=int, required=True)
p.add_argument("--random_seed", type=int, required=True)
args = p.parse_args()
```

So the effective CLI accepts:

```
--output_dir  --name                     (from _base.json, via add_base_args)
--normalized_selected.h5                 (from pca.json,  via add_stage_args)
--solver  --n_components  --random_seed  (your own, plain argparse)
```

## Naming an interface

An interface name is the **entrypoint** your module exposes for a stage (`pca`,
`knn`) — the stable handle the plan binds you by (`repository.entrypoint:` in
the benchmark definition). It is *not* the plan's internal stage `id` (those
carry ordinal prefixes, e.g. `five-pca`). Stage-id, entrypoint, and output
namespaces are distinct and **mapped, not unified** — so never rename your
existing flags or outputs just to "match" a stage id.

## Where the files come from

`common/cli.*`, `_base.json`, and each stage `<interface>.json` are vendored
from the boilerplate / benchmark. Until `ob` can automate, refresh them with the
boilerplate's `pull.py`, run **from your module root** against a sibling
checkout of the boilerplate:

```sh
cd my-module && python ../boilerplate/scripts/pull.py
```

It fetches the common boilerplate code from the ref that is pinned in your
`omnibenchmark.yaml`. Your own method params live in your entrypoint, not in
`common/`, so they stay put. See [`AGENTS.md`](../AGENTS.md) and [adding CI](ci.md).

---

> The `_base.json` and `embedding.json` blocks above are embedded verbatim from
> `src/common/schema/` and kept in sync by `pixi run docs` (see
> [`scripts/embed_snippets.py`](../scripts/embed_snippets.py)). Don't edit them
> by hand.
