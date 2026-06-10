# Shared CLI helpers

> **Defining a stage's CLI contract, or maintaining `src/common/schema/`?** See
> [Stage interfaces](stage-interfaces.md). This page is about *using* the shared
> helpers from a module entrypoint.

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

You don't write the base or stage flags — `add_base_args`/`add_stage_args` bring
in whatever the boilerplate and the benchmark declared. A stage flag can arrive
under a tidier attribute name than its flag (e.g. `--normalized_selected.h5` →
`args.input_h5`); run your entrypoint with `--help` to see exactly what you get.

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

`common/cli.*`, `_base.json`, and each stage `<interface>.json` are vendored
from the boilerplate repo (TODO: insert a footnote saying, in the future they
can be defined in the benchmark itself). Until `ob` can automate this, you need
to refresh the common code every time it changes with a script from the
boilerplate repo.

You can sync common code **from your module root** against a checkout of the boilerplate in a sibling directory, like this:

```sh
cd my-module && python ../boilerplate/scripts/pull.py
```

It fetches the common boilerplate code from the ref that is pinned in your
`omnibenchmark.yaml`. Your own method params live in your entrypoint, not in
`common/`, so they stay put. See [`AGENTS.md`](../AGENTS.md) and [adding CI](ci.md).
