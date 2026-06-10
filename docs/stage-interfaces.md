# Stage interfaces (the shared CLI schema)

This page is for **benchmark authors** — who define a stage's CLI contract — and
**boilerplate contributors** — who maintain `src/common/schema/` and the
`common/cli` helpers. **Module authors don't need it:** to wire up an
entrypoint's CLI, see [the shared CLI helpers](cli.md). This page documents the
*format* of the schema those helpers read.

## What a stage interface is

An *interface* is a named, versioned CLI contract for one stage of a benchmark,
owned by the benchmark. A module "satisfies" it by carrying the schema and
injecting it onto its parser with `cli.add_stage_args(p, "<interface>")`. The
same JSON drives the Python (`argparse`) and R (base R) helpers identically, so
both languages expose the same flags.

## The schema file

A stage's I/O contract is one file, `src/common/schema/<interface>.json`:

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
invocation line, fully explicit, no defaults). Unknown flags are rejected by the
module's parser.

### Types

| `type` | Python | R |
|---|---|---|
| `path` | `pathlib.Path` | character |
| `string` | `str` | character |
| `integer` | `int` | integer |
| `number` | `float` | double |

`path` and `string` differ only by the Python type the entrypoint gets back (a
`Path` is handy for `open`/`mkdir`); both accept any string on the command line.

### Options (enums) — `choices`

Restrict a flag to a fixed set, exactly like `argparse` `choices`:

```json
{ "flag": "--solver", "type": "string", "choices": ["arpack", "randomized"] }
```

An out-of-set value is rejected with a clear message **before** the entrypoint's
code runs.

### `dest` — the attribute name

By default a flag becomes an attribute with leading dashes stripped and `.`/`-`
turned into `_`: `--pcas.tsv` → `args.pcas_tsv`. Set `dest` to give the
entrypoint a tidier name:

```json
{ "flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path" }
```

so the entrypoint reads `args.input_h5` while the stable flag stays
`--normalized_selected.h5`.

## What's shared vs. what's the module's

Three kinds of args, by owner — only the first two are schema-driven:

| source | what it holds | who owns it | on `pull` / update |
|---|---|---|---|
| `_base.json` | universal args every module gets (`--output_dir`, `--name`) | boilerplate | overwritten |
| `<interface>.json` | the stage's I/O contract | the benchmark | overwritten |
| the module's entrypoint | its method params (`--solver`, …) | the module author | never touched |

`cli.add_base_args` reads `_base.json`; `cli.add_stage_args` reads
`<interface>.json`. Method parameters are **not** in any schema — the module
author hand-writes them in plain `argparse`/base R (see [the shared CLI
helpers](cli.md)).

`_base.json` (vendored, shipped with the helpers):

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

## Where these live

`src/common/schema/` in the boilerplate is the interim home for stage schemas
(until benchmarks publish their own `interfaces/`). `_base.json` is
boilerplate-owned; each `<interface>.json` is benchmark-owned. Both are vendored
into a module's `common/schema/` by [`scripts/pull.py`](../scripts/pull.py) and
are **overwrite-on-update** — don't edit the vendored copies in a module. On any
change under `src/common/`, bump `src/common/VERSION` and run `pixi run version`;
see [`AGENTS.md`](../AGENTS.md) for the maintenance workflow.

---

> The `embedding.json` and `_base.json` blocks above are embedded verbatim from
> `src/common/schema/` and kept in sync by `pixi run docs` (see
> [`scripts/embed_snippets.py`](../scripts/embed_snippets.py)). Don't edit them
> by hand.
