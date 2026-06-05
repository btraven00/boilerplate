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
├── omnibenchmark.yaml   # makes this repo double as a (self-validating) module; also template-for:
├── run.sh               # placeholder default entrypoint (so it validates as a module)
├── CITATION.cff         # required for `ob validate module`
├── LICENSE
├── pixi.toml            # dev tasks for working ON the template (not copied into modules)
├── .github/workflows/   # this repo's own CI (docs sync + self-validation, not the catalog)
├── scripts/             # repo maintenance helpers (e.g. doc-snippet embedding)
├── actions/             # reusable CI / automation entry points
├── docs/                # module-author documentation
├── src/
│   └── common/          # shared code copied into every module
│       ├── python/      # rendered for Python modules
│       └── r/           # rendered for R modules
└── validators/          # I/O contract checks, routed by stage/output
```

Note for agents: `actions/`, `docs/`, `scripts/`, `.github/workflows/`,
`omnibenchmark.yaml`, and the root `pixi.toml` have content; `src/common/{python,r}/`
and `validators/` are still **empty placeholders** whose *intended* purpose is
described below. Do not assume files exist — check first.

### `src/common/{python,r}/`
Shared, language-split utilities that get copied into a module: logging setup,
format converters, a thin CLI, and helpers for reading/writing the benchmark's
data formats. The language split exists so Copier can conditionally render only
the language(s) a module declares. **Add new shared utilities under the correct
language directory**, and keep the public surface (function/CLI names) stable
across languages where it makes sense, so the two implementations feel like one
contract.

### `validators/`
I/O contract checks, routed `validators/<STAGE_NAME>/<OUTPUT_NAME>/validate.<ext>`
— a self-documenting layout so tooling can discover a stage's contract by path.
Each validator receives a single output file path and uses as few dependencies
as possible. The routing is shared with the plan, so a validator written in one
home runs unchanged in the other.

Validators live in **two homes, split by role**:

- **This repo's `validators/`** ships *reusable, inheritable* validators that a
  module copies in (via Copier, like `src/common/`) to test its **own** outputs
  *before* the benchmark runs — generic checks (a TSV is well-formed, an `.h5ad`
  opens, expected shape/columns) and starter templates an author can specialize.
  Author-owned and editable once copied.
- **The plan** owns the *authoritative, stage-specific* validator for each
  `STAGE/OUTPUT`, run at benchmark time (the upstream prototype of this
  convention — see [split-stages-plan](https://github.com/omni-scrna/split-stages-plan)'s
  `validators/five-pca/pcas.tsv/validate.R`).

Both import the shared helpers under `src/common/` (read one file path, load the
format, assertion utilities), so the two feel like one contract. **Don't
duplicate the same `STAGE/OUTPUT` validator across both repos:** keep this repo's
validators generic/inheritable, leave stage-specific ones to the plan, and
*pick* the plan's validators (`pixi run fixtures`, see *`omnibenchmark.yaml` —
module config + plan link*) to check the shared helpers keep running against the
real contract.

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
`copier update`. So far this holds `ci.md` (adding the `validate-module` action
to a module). Doc pages may embed real files verbatim (see *Developer tasks*),
so don't hand-edit a fenced block wrapped in `<!-- embed:… -->` markers — edit
the source file and run `pixi run docs`.

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
template-for:
  - https://github.com/omni-scrna/split-stages-plan
```

- **`entrypoints`** make the repo a valid omnibenchmark module, so it
  **self-validates**: `ob validate module .` (and the `validate-module` action)
  pass against it. CI dogfoods the action on this repo (see *Continuous
  integration*). The validator only requires an `entrypoints.default` key, not a
  working entrypoint yet — hence the `run.sh` placeholder.
- **`template-for`** declares which plan(s) this boilerplate scaffolds — the
  source of truth for "which plan do we belong to." `ob` ignores the key;
  `scripts/pick_fixtures.sh` (`pixi run fixtures`) reads it to shallow+sparse-clone
  each plan's `validators/` into a gitignored `.fixtures/` for local work.

### `scripts/` and `pixi.toml`
Maintenance for working *on* the template itself — **never copied into a
module** (Copier renders `src/common/`, not these). The root `pixi.toml` is a
dev-task manifest, deliberately separate from `actions/*/pixi.toml` (which are
private action toolchains). Its tasks:

- `pixi run docs` — re-embed file snippets into the docs.
- `pixi run docs-check` — fail if any embedded snippet is stale.

`scripts/embed_snippets.py` (stdlib only) injects a referenced file verbatim
into the `<!-- embed:PATH -->` / `<!-- /embed -->` block of each Markdown file
listed in its `TARGETS`. This keeps a doc's copy of a file from drifting by
making the **real file the single source of truth**. `docs-check` runs in CI
(below); run `docs` locally to fix a stale embed.

### Continuous integration
`.github/workflows/ci.yml` tests **this repo's own deliverables**. Two jobs:
`docs` gates docs sync (`pixi run docs-check`), and `validate-module` dogfoods
the catalog action against this repo (`uses: ./actions/validate-module`) — which
works because the repo doubles as a module (`omnibenchmark.yaml`). That
self-validation is also the **only place the action runs live on GitHub**, since
a composite action otherwise only executes when another repo `uses:` it. Keep CI
focused on what this repo ships.

## Conventions to preserve

- **Language separation:** never mix Python and R boilerplate in a shared path;
  use `src/common/python/` and `src/common/r/`.
- **Stage/output routing:** validators route as
  `validators/<STAGE_NAME>/<OUTPUT_NAME>/validate.<ext>`, one file path per
  validator. This mirrors the plan's convention — keep it identical so picked
  fixtures run unchanged.
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
