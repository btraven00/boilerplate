# AGENTS.md

Guidance for AI agents (and humans) working in this repository.

## What this repository is

This is the **boilerplate** for modules of the
[omni-scrna](https://github.com/omni-scrna/) omnibenchmark. A module is a
self-contained repository that implements one or more *stages* of the benchmark
(e.g. a method, a metric, a data loader). This repo is the canonical source of
the shared scaffolding those modules copy in: common utilities, I/O contracts,
validators, and developer tasks.

It is distributed with [Copier](https://copier.readthedocs.io/), **not** git
submodules. Module authors generate their repo from this template and later run
`copier update` to pull upstream improvements. Copier's three-way merge lets an
author tweak the copied code locally and still receive updates without losing
their edits.

## Design philosophy — read this before changing anything

The ecosystem is **bazaar-style, not cathedral-style**. Conventions are
*opt-in* and *convention-driven*, never enforced by a heavy runtime dependency.
The guiding rule:

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
  `src/common/` that prove universally useful across the benchmark are candidates
  to graduate upstream (into `obkit` or the core engine). Benchmark-specific I/O
  contracts stay here. Don't prematurely promote things.

## Repository layout

```
.
├── AGENTS.md            # this file
├── README.md
├── actions/             # reusable CI / automation entry points
├── docs/                # module-author documentation
├── src/
│   └── common/          # shared code copied into every module
│       ├── python/      # rendered for Python modules
│       └── r/           # rendered for R modules
└── validators/          # I/O contract checks, routed by stage/output
```

Note for agents: as of this writing the subdirectories are **empty
placeholders**. The layout below describes their *intended* purpose. Do not
assume files exist — check first.

### `src/common/{python,r}/`
Shared, language-split utilities that get copied into a module: logging setup,
format converters, a thin CLI, and helpers for reading/writing the benchmark's
data formats. The language split exists so Copier can conditionally render only
the language(s) a module declares. **Add new shared utilities under the correct
language directory**, and keep the public surface (function/CLI names) stable
across languages where it makes sense, so the two implementations feel like one
contract.

### `validators/`
**Not a current priority — deferred to later.** This directory will eventually
hold the I/O contract checks, routed by a `validators/<STAGE_NAME>/<OUTPUT_NAME>`
convention (a self-documenting layout so tooling can discover a stage's contract
by path). For now treat it as a reserved placeholder: don't build out validator
logic unless explicitly asked, and focus effort on `src/common/` and the
developer-task scaffolding instead.

### `actions/`
A **catalog of reusable GitHub Actions** for modules. Each subdirectory is one
composite action (`action.yml`) that a module references with `uses:` — its
logic is *not* copied in. Unlike `src/common/` (copied in, author-owned), CI is
shared infrastructure, so the "fix once, every module gets it" model fits, and
the heavy toolchain (pixi + omnibenchmark) lives *inside the action* so modules
stay lean and need not be pixi-based. `actions/install.sh` drops an action's
thin caller workflow into a module's `.github/workflows/` (plain POSIX sh, no
pixi assumption, non-destructive). See `actions/README.md`.

Note: these are actions, not workflows, so **nothing in `actions/` runs in this
repo** — an `action.yml` only executes when another repo's workflow `uses:` it.
This repo has no `.github/workflows/` of its own. The first action is
`validate-module` (`ob validate module` against omnibenchmark's `main`).

### `docs/`
Documentation aimed at module authors: how to generate a module, how to declare
its language and stages, how to run validation, and how to take a
`copier update`.

## Conventions to preserve

- **Language separation:** never mix Python and R boilerplate in a shared path;
  use `src/common/python/` and `src/common/r/`.
- **Stage/output routing (future):** when validators land, route them as
  `validators/<STAGE_NAME>/<OUTPUT_NAME>`. Not in scope yet.
- **Copier-templated paths:** rendered files use Jinja conditionals / `.jinja`
  suffixes so a module only materializes what it needs. Preserve the
  conditionals when editing templated files; don't hard-code one language's
  assumptions into shared logic.

## Working in this repo

- This is a **template**, so files here may contain Jinja (`{{ ... }}`,
  `{% ... %}`) and `.jinja` suffixes. Edit the template source, not a rendered
  output.
- Changes here propagate to every module via `copier update`. Treat backward
  compatibility of conventions (paths, CLI names, contract shapes) as a
  first-class concern — a rename can break every downstream module's merge.
- When in doubt, favor the smallest convention that solves the problem over a
  new dependency or abstraction.
