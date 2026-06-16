# Shared CLI helpers

> **Defining a stage's CLI contract (a benchmark author)?** See the plan's
> [Stage schemas](https://github.com/omni-scrna/split-stages-plan/blob/main/docs/stage-schemas.md).
> This page is about *using* the shared helpers from a module entrypoint.

This guide is for **module authors**: you write your own `argparse` (Python) or
`argparser` (R) CLI, and import a couple of helpers from `src/common/` to inject the
*shared* parts that are provided by the benchmark (the universal base args and
your stage's I/O contract). In this way, Python and R modules share the same definition of
the CLI arguments, and you can update definitions easily if the benchmark changes.

## The idea

You own your entrypoint's parser. The flags that are **shared** (the base args, and the stage's I/O contract)
are declared as JSON in the benchmark's plan `schema/` folder (copied into
your module's `src/common/schema/`) and *added onto your parser* by using
`src/common/cli`. Your own any method parameters you add by hand, for python
that's `argparse` and for R `argparser`. 

In this way the whole CLI for an entrypoint stays visible in your file.

```python
import argparse
from common import cli

p = argparse.ArgumentParser()
cli.add_base_args(p)                 # --output_dir, --name   (src/common/schema/_base.json)
cli.add_stage_args(p, "embedding")   # the stage I/O contract (src/common/schema/embedding.json)
# your own method params — plain argparse, fully visible & owned:
p.add_argument("--solver", choices=["arpack", "randomized"], required=True)
p.add_argument("--n_components", type=int, required=True)
args = p.parse_args()
# args.output_dir, args.name, args.pcas, args.solver, args.n_components
```

R works the same way, with the [`argparser`](https://cran.r-project.org/package=argparser)
package (pure R): the helpers add the shared args onto your parser, and you add
your own with `argparser` directly. Load into a dedicated environment so the
helpers don't land in your global scope:

```r
cli <- new.env()
source("src/common/cli.R", local = cli)    # namespaced: helpers stay inside `cli`
p <- arg_parser("PCA module")
p <- cli$add_base_args(p)                   # --output_dir, --name
p <- cli$add_stage_args(p, "embedding")     # the stage I/O contract
# your own method params — argparser directly (its add_argument requires `help`):
p <- add_argument(p, "--n_components", type = "integer", help = "number of PCs")
args <- parse_args(p)                        # argparser's own parser
# args$output_dir, args$name, args$pcas.tsv, args$n_components
```

The R helpers are deliberately thin: they only translate the schema's flags into
`argparser::add_argument` calls, then hand off to `argparser` for parsing. So
`argparser` owns naming (a flag's value is read off the de-dashed flag, e.g.
`--pcas.tsv` → `args$pcas.tsv`) and there's no enforcement of `required` or
`choices`. (The Python engine does honor a schema `dest` and marks args required;
if you need that parity in R, enforce it in your entrypoint.)

Loading into `cli` (via `source(..., local = cli)`, or equally `sys.source(...,
envir = cli)`) keeps every helper inside that environment — call them as
`cli$add_base_args()` — so nothing collides with your own globals. Plain
`source("src/common/cli.R")` into the global scope works too. The helpers find the
shared schema at `src/common/schema/` (relative to your module root, where `ob`
runs entrypoints); if yours lives elsewhere, pass `schema_dir =` or set
`cli$SCHEMA_DIR` once after sourcing.

You don't have to write the base or stage flags: `add_base_args`/`add_stage_args` bring
in whatever the boilerplate and the benchmark declared for the current version of the benchmark.
Run your entrypoint with `--help` to see exactly what you get.

## Worked example

Say the benchmark's `pca` stage contract declares one input:

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

## Where common files come from

You don't hand-write `src/common/`. The engine (`cli.R` / `cli.py`) and the
schema JSON it reads (`src/common/schema/`) are **copied** into your module and
refreshed with one script, pointed at your module (or run from inside it):

```sh
python boilerplate/scripts/pull.py path/to/module   # or, from the module root:
cd my-module && python ../boilerplate/scripts/pull.py
```

This fetches the engine from the boilerplate and the schemas from the benchmark,
at the refs pinned in your `omnibenchmark.yaml`. Your own method params live in
your entrypoint, not in `src/common/`, so they stay put across pulls. The full
workflow —what to pin, what to commit, when to re-run— is in
[getting the shared code into your module](common-code.md); see also
[`AGENTS.md`](../AGENTS.md) and [adding CI](ci.md).
