# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## Who this is for — read first

There are **two audiences**, and most of this file addresses the first:

1. **Maintainers of the template** — agents/humans editing *this* repo. The
   rest of this document is for you.
2. **Consumers** — an agent (Claude, etc.) working inside a *module* repo,
   pointed here to wire that module up. **If that's you, you are not meant to
   edit this repo.** Go to [`docs/`](docs/) for task-oriented guides, starting
   with [`docs/ci.md`](docs/ci.md) (add validation CI). Prefer the no-checkout
   path: reference an action by `uses: omni-scrna/boilerplate/actions/<name>@main`
   in the module's own workflow. Later, language utilities to copy in will live
   under `src/common/`. Don't copy `actions/`, `scripts/`, or this file into a
   module — they belong to the template.

## What this repository is

This is the **boilerplate** for modules of the
[omni-scrna](https://github.com/omni-scrna/) omnibenchmark. A module is a
self-contained repository that implements one or more *stages* of the benchmark
(e.g. a method, a metric, a data loader). This repo is the canonical source of
the shared scaffolding those modules copy in (common utilities, I/O contracts,
validators), plus the CI actions they reference and the developer tasks for
working on the template itself.

Common code is, in principle, supposed to be distributed with
[Copier](https://copier.readthedocs.io/), **not** git
submodules (but we're still trying out the workflow and we might change our
minds later). Module authors generate their repo from this template and later
run `copier update` to pull upstream improvements. Copier's three-way merge lets an
author tweak the copied code locally and still receive updates without losing
their edits.

## Design philosophy — read this before changing anything

The ecosystem for a given benchmark is supposed to be **bazaar-style, not
cathedral-style**. Conventions are *opt-in* and *convention-driven*, never
enforced by a heavy runtime dependency.  The guiding rule:

> Give module authors a paved path that makes their lives easier, and they might 
> use it. Force a heavy dependency on them and it will not fit their needs.

Concretely, this means:

- **Prefer conventions over machinery.** A predictable directory name or file
  contract is better than a full framework or package the author must import. But
  mature benchmarks _might_ evolve into full frameworks.
- **Keep the footprint lean per language.** An R module author should never have to
  look at Python boilerplate, and vice versa. Template logic renders only what
  a module actually needs. Embracing a new language should be possible without
  requiring a heavy runtime dependency.
- **Everything copied in done for the author to edit and possibly customize.** Do
  not write code that assumes the template's files are pristine; `copier update`
  merges, it does not overwrite.
- **This is a prototype that earns its way into the core.** Pieces of
  `src/common/` that prove universally useful across the benchmark, and generic enough in terms of dependencies, are candidates
  to graduate upstream (into `obkit` or the core engine). Benchmark-specific I/O
  contracts stay here. Don't prematurely promote things.

## Repository layout

```
.
├── AGENTS.md            # this file
├── README.md
├── omnibenchmark.yaml   # makes this repo double as a (self-validating) module; also plan:
├── run.sh               # placeholder default entrypoint (so it validates as a module)
├── CITATION.cff         # required for `ob validate module`
├── LICENSE
├── pixi.toml            # dev tasks for working ON the template (not copied into modules)
├── .github/workflows/   # this repo's own CI (docs sync + self-validation, not the catalog)
├── scripts/             # repo maintenance helpers (e.g. doc-snippet embedding)
├── tests/               # tests for src/common (template-only, gate merges)
├── actions/             # reusable CI / automation entry points
├── docs/                # module-author documentation
├── src/
│   └── common/          # shared code copied into every module
│       ├── python/      # rendered for Python modules
│       └── r/           # rendered for R modules
│                        # (schema/ exists only in a module, vendored from the benchmark)
└── validators/          # I/O contract checks, routed by stage/output
```

Note for agents: most directories now have content. `src/common/{python,r}/`
holds the shared CLI helpers (`cli.py` / `cli.R`); the schemas they read are
benchmark-owned (the plan's `schema/`), vendored into a module's
`src/common/schema/` — the boilerplate keeps only example copies in the example
module fixture `tests/fixtures/module/`. `validators/` holds one copied example.
These are early/spike-stage — read before assuming a shape.

### `src/common/{python,r}/` and `src/common/schema/`
Shared, language-split utilities copied into a module — a **reserved,
overwrite-on-update path**: authors are told not to edit it, so it can be
re-rendered cleanly (see *Working in this repo*). Keep the public surface
(function/CLI names) **identical across languages** so the Python and R
implementations feel like one contract; keep dependencies light.

The first utility is **shared CLI helpers**. An *interface* — a named CLI contract
owned by a benchmark — is defined as data in the benchmark's own
`schema/<interface>.json` and vendored into a module's `src/common/schema/`. The
boilerplate carries none itself (example copies live in the example module
fixture `tests/fixtures/module/` for the tests and docs). The module author writes their **own**
`argparse` (Python) / `argparser` (R) CLI and owns the parser; `cli.py` (stdlib
`argparse`) and `cli.R` (the `argparser` CRAN package + `jsonlite` — `argparser`
is pure R, *not* the `argparse` package, which pulls Python) just *inject* the
shared args — the universal base and the stage's I/O contract — onto it. A module "satisfies" an interface by carrying its schema and
adding it to its parser. **Add new shared utilities under the correct language
directory**, with matching surfaces.

**Interface naming.** An interface name == the **entrypoint** a module exposes
for a stage (`pca`, `knn`), which is the stable handle the plan binds a module by
(`repository.entrypoint:` in `benchmark_conda.yaml`). It is *not* the plan's
internal stage `id` (those carry ordinal prefixes, e.g. `five-pca`, and language
variants like `embedding-py`/`embedding-r` share one interface). Stage-id,
entrypoint, and output namespaces are distinct and **mapped, not unified** — so
never rename a module's existing flags/outputs to "match" a stage id.

**What's shared vs. what's the author's.** Two synced files in `schema/` back the
helpers; method params are *not* schema-driven — the author hand-writes them:

- `_base.json` — universal args every module gets (`--output_dir`, `--name`);
  benchmark-owned like the stage schemas, vendored from the benchmark's `schema/`.
  Added by `add_base_args`.
- `<interface>.json` — the stage's I/O contract (benchmark-owned; reserved,
  overwrite-on-update). Added by `add_stage_args(parser, "<interface>")`.
- method params (`--solver`, `--n_components`, …) — **author-owned**, written as
  plain `argparse` in the author's own entrypoint, so `pull`/`copier update`
  never touches them.

A schema arg may carry an optional `choices` list (an enum) and a `dest` rename.
The **Python** engine adds each arg `required=True` and enforces `choices`/`dest`;
the **R** engine deliberately does not (see *Import convention* below).

**Import convention.** In a *rendered* module the shared code lives at
`src/common/` (the pull script drops the language segment, leaving the chosen
language's files plus `schema/`), so entrypoints use it as:

```python
import argparse
from common import cli                 # `src/` on the path; `common` is the package
p = argparse.ArgumentParser()
cli.add_base_args(p); cli.add_stage_args(p, "embedding")   # then your own p.add_argument(...)
args = p.parse_args()
```
```r
source("src/common/cli.R")            # R (no import namespace; we source())
p <- arg_parser("module")
p <- add_base_args(p); p <- add_stage_args(p, "embedding")   # then your own add_argument(...)
args <- parse_args(p)
```

Both languages mutate the author's parser (Python `argparse`, R `argparser` — pure
R, not the Python-wrapping `argparse` package), then parse. They are **not**
symmetric: `cli.py` enforces the schema's `required`/`choices` and applies its
`dest` renames, while `cli.R` is intentionally minimal — it only translates each
schema arg into an `argparser::add_argument` call and lets `argparser` own naming
and parsing, so `required`/`choices`/`dest` aren't enforced there (parse with
`argparser`'s own `parse_args`). The template keeps the `src/common/{python,r}/` split
for maintenance; vendoring flattens the chosen language to `src/common/cli.*`
with `schema/` alongside. Python's `cli.py` locates `schema/` relative to itself
(`__file__`), so it works at either path; R's `cli.R` has no `__file__`, so it
reads the `SCHEMA_DIR` global, set to `src/common/schema` (the vendored layout,
which the template's own tests also match) — reassign that global to point
elsewhere.

The common code carries **no explicit version string**. Which copy of the
scaffolding a module carries is identified by the **template `ref`** it was pulled
at (the boilerplate commit/tag in `omnibenchmark.yaml`), recorded exactly as the
resolved commit in `src/common/.provenance.json` (see below). A check-for-updates
compares that recorded commit against the template's latest `main`. Stage schemas
are likewise **not** independently versioned: a module carries whatever its
benchmark's `schema/` publishes at the pinned `ref` (the `ref` is the only version
handle), and the common code loads a stage by name — erroring if it isn't there.

### `validators/`
I/O contract checks, routed `validators/<STAGE_NAME>/<OUTPUT_NAME>/validate.<ext>`
— a self-documenting layout so tooling can discover a stage's contract by path.
Each validator receives a single output file path and uses as few dependencies
as possible. The routing mirrors the plan's, so a validator written in one home
runs unchanged in the other (the convention's upstream prototype is
[split-stages-plan](https://github.com/omni-scrna/split-stages-plan)'s
`validators/`).

`five-pca/pcas.tsv/validate.R` is currently a copy from the plan, kept as a
concrete example to build the shared scaffolding against — flagged with a `TODO`
to remove once validators get a proper home. How validators are ultimately
owned, distributed, and shared with `src/common/` helpers is still open design.

**Temporary exception:** `validators/five-pca/pcas.tsv/validate.R` is a copy
from the plan, kept here as a concrete example to build the shared scaffolding
against. It is the *one* deliberate duplication, flagged with a `TODO` in the
file — remove it from this repo once validators get a proper home.

### `actions/`
A **catalog of reusable GitHub Actions** for modules. Each subdirectory is one
composite action (`action.yml`) that a module references with `uses:` — its
logic is *not* copied in. Unlike `src/common/` (copied in, author-owned), CI is
shared infrastructure, so the "fix once, every module gets it" model fits, and
the heavy toolchain (pixi + omnibenchmark) lives *inside the action* so modules
stay lean and need not be pixi-based. `actions/install.sh` drops an action's
thin caller workflow into a module's `.github/workflows/` (plain POSIX sh, no
pixi assumption, non-destructive). See `actions/README.md`.

Note: these are actions, not workflows, so **nothing in `actions/` runs when
this repo's CI runs** — an `action.yml` only executes when another repo's
workflow `uses:` it. (This repo's own `.github/workflows/ci.yml` tests the
repo's deliverables — see *Continuous integration* below — not the catalog.)
The first action is `validate-module` (`ob validate module` against
omnibenchmark's `main`).

### `docs/`
Documentation aimed at module authors: how to generate a module, how to declare
its language and stages, how to run validation, and how to take a
`copier update`. So far this holds `cli.md` (module-author guide: wiring an
entrypoint's CLI with the `add_base_args`/`add_stage_args` helpers) and `ci.md`
(adding the `validate-module` action to a module). The stage-schema *format* —
types, `choices`, `dest`, base/stage/method ownership, aimed at benchmark authors
— now lives with the schemas, in the plan's `docs/stage-schemas.md`.
Doc pages may embed real files verbatim (see *Developer tasks*), so don't
hand-edit a fenced block wrapped in `<!-- embed:… -->` markers — edit the source
file and run `pixi run docs`.

### `omnibenchmark.yaml` — module config + plan link
A *plan* (master plan) is an omnibenchmark benchmark definition — e.g.
[`omni-scrna/split-stages-plan`](https://github.com/omni-scrna/split-stages-plan),
whose `benchmark_conda.yaml` lays out the stages (data → QC → HVGs → PCA →
clustering). Modules generated from this boilerplate implement those stages; the
plan owns the validators for each stage's outputs.

This repo carries its own `omnibenchmark.yaml`, which does double duty:

```yaml
entrypoints:
  default: run.sh        # placeholder — real entrypoints (validators) come later
plan:                    # the plan this boilerplate is the template for
  repo: https://github.com/omni-scrna/split-stages-plan
  file: benchmark_conda.yaml   # the benchmark definition within that repo
  ref: main
```

- **`entrypoints`** make the repo a valid omnibenchmark module, so it
  **self-validates**: `ob validate module .` (and the `validate-module` action)
  pass against it. The validator only requires an `entrypoints.default` key, not
  a working entrypoint yet — hence the `run.sh` placeholder.
- **`plan`** is the single template→plan pointer: the boilerplate is a template
  for *one* plan, so it records that plan's `repo`/`file`/`ref`. Only dev tooling
  reads it — `refresh-fixtures` vendors the example schemas from this plan's
  `schema/` — and `ob` ignores it. Note this is **not** a module's `benchmarks:`:
  the boilerplate consumes no benchmark.

A **module's** manifest is the consumer shape, declared with `benchmarks:` — a list
of the benchmark(s) it plugs into, each `{name, repo, plan, ref}`. `pull` vendors
each one's whole `schema/` dir into `src/common/schema/`; the entrypoint loads the
stage it needs by name and the engine errors if that schema isn't vendored. There
is no `implements:` ledger and no per-interface version handshake — a module simply
carries the schemas its benchmark publishes at the pinned `ref`. See
`tests/fixtures/module/omnibenchmark.yaml` for a worked example — a realistic module
with vendored `src/common/schema/`.

### Vendoring shared code + interfaces (`scripts/pull.py`, interim)
How the shared code and interface schemas get *into* a module — until `ob` owns
it. `scripts/pull.py` takes the module root as an optional argument (default: the
current directory) — it reads `<root>/omnibenchmark.yaml` and writes
`<root>/src/common`, so it isn't copied into modules; point it at a module, or run
it from inside one:

```sh
python boilerplate/scripts/pull.py path/to/module   # or, from the module root:
cd my-module && python ../boilerplate/scripts/pull.py
```

It reads that module's `omnibenchmark.yaml` and shallow+sparse-fetches at pinned
refs:

- **`boilerplate:`** `{repo, ref, lang}` → the common engine (`cli.*`) into the
  module's `src/common/` package (with `src/` on the path, `from common import
  cli` works).
- the benchmark's schemas → `src/common/schema/`: the whole `schema/` dir
  (`_base.json` + every stage `<iface>.json`) of each **`benchmarks:`** entry.

Vendored files are committed in the module (offline-runnable) — `pull` just
refreshes them. To take an upstream change, bump
the `ref` in `omnibenchmark.yaml` (when moving to a new pin), re-run `pull`, and
commit the refresh.

`pull` also writes `src/common/.provenance.json`, recording the *resolved* sources
it fetched from — the common code's resolved commit, and each benchmark's
repo/ref/commit. With no version literal in the shared code, this is *the* exact
sync witness (and the version handle: diff its recorded commit against the
template's latest `main` to check for updates) — the record of what a module
actually carries, especially when a `ref` is a moving branch. It's committed
alongside the copied-over files. (Author-facing docs deliberately omit this; it's
reference for maintainers and for debugging a module's sync state.)

A consuming module declares:

```yaml
boilerplate:
  repo: https://github.com/omni-scrna/boilerplate
  ref: v0.1.0          # pin; tag or branch
  lang: python
benchmarks:
  - { name: split-stages, repo: …/split-stages-plan, plan: benchmark_conda.yaml, ref: main }
```

This is deliberately lightweight and easy to delete once `ob` subsumes it (no
submodule residue). Precondition for the schema pull: the benchmark must
publish a `schema/` dir (the plan now does; if it's absent `pull` notes and skips
it). Discovery is bidirectional: a plan can point at its boilerplate, and
a module's `benchmarks` points back at the plan.

### `scripts/` and `pixi.toml`
Maintenance for working *on* the template itself — **never copied into a
module** (Copier renders `src/common/`, not these). The root `pixi.toml` is a
dev-task manifest, deliberately separate from `actions/*/pixi.toml` (which are
private action toolchains). Its tasks:

- `pixi run docs` / `docs-check` — re-embed doc snippets / fail on drift.
- `pixi run test` — Python + R tests for `src/common` (under `tests/`).
- `pixi run lint` / `typecheck` — `ruff` and `mypy` over the Python side.
- `pixi run check` — all of the above; this is what CI runs and gates on.

`scripts/embed_snippets.py` (stdlib only) injects a referenced file verbatim
into the `<!-- embed:PATH -->` / `<!-- /embed -->` block of each Markdown file
listed in its `TARGETS`, keeping a doc's copy from drifting from the **real
file**. Run `docs` locally to fix a stale embed.

Tests live in `tests/` (template-only, not copied into modules). Keep them
green — they gate merges. R linting/typechecking are intentionally omitted to
stay minimal (R has no standard type checker; `lintr` is heavy).

### Continuous integration
`.github/workflows/ci.yml` tests **this repo's own deliverables** and **gates
merges** (set branch protection to require both jobs). The `checks` job runs
`pixi run check` (docs-sync, interface consistency, `ruff`,
`mypy`, Python/R tests). The
`validate-module` job dogfoods the catalog action against this repo
(`uses: ./actions/validate-module`) — which works because the repo doubles as a
module (`omnibenchmark.yaml`), and is also the **only place the action runs live
on GitHub**, since
a composite action otherwise only executes when another repo `uses:` it. Keep CI
focused on what this repo ships.

## Conventions to preserve

- **Language separation:** never mix Python and R boilerplate in a shared path;
  use `src/common/python/` and `src/common/r/`.
- **Stage/output routing:** validators route as
  `validators/<STAGE_NAME>/<OUTPUT_NAME>/validate.<ext>`, one file path per
  validator. Keep it identical to the plan's convention so a validator runs
  unchanged in either repo.
- **Copier-templated paths:** rendered files use Jinja conditionals / `.jinja`
  suffixes so a module only materializes what it needs. Preserve the
  conditionals when editing templated files; don't hard-code one language's
  assumptions into shared logic.
- **Embedded doc snippets:** when a doc must show a file that also exists for
  real (e.g. a caller workflow), embed it with `<!-- embed:PATH -->` markers and
  let `pixi run docs` fill it, rather than pasting a copy. The real file stays
  the source of truth. Terser, hand-written *teaching* examples (a condensed
  `uses:` snippet in a README) are fine to keep inline — embed only when the doc
  is meant to mirror a shipped file exactly.

## Working in this repo

- This is a **template**, so files here may contain Jinja (`{{ ... }}`,
  `{% ... %}`) and `.jinja` suffixes. This might not be the case later on if we
decide to fully embrace git submodules. Edit the template source, not a
rendered output.
 - Changes here propagate to every module via `copier update`. Treat backward
  compatibility of conventions (paths, CLI names, contract shapes) as a
  first-class concern — a rename can break every downstream module's merge.
- When in doubt, favor the smallest convention that solves the problem over a
  new dependency or abstraction.
- A convention we can recommend as good practices is to reserve some paths (like `src/common`) for code being propagated from templates. If module authors avoid touching src/common, we can always overwrite that sub-path.
