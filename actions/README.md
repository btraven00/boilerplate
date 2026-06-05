# Action catalog

This directory is a **catalog of reusable GitHub Actions** for omni-scrna
modules. Each subdirectory is one action, packaged as a standard composite
GitHub Action (`action.yml`). Modules reference an action by `uses:`; they do
**not** copy its logic in.

Actions are *opt-in*. A module picks the ones it wants; nothing is forced.

> **Why composite actions, not copied-in code?** CI is shared infrastructure
> that benefits from "fix once, every module gets it." Packaging as a GitHub
> Action also keeps the heavy toolchain (pixi + omnibenchmark) *inside the
> action*, so modules stay lean and need not be pixi-based. (Source utilities in
> `src/common/` use the opposite model — copied in, author-owned — because they
> run locally and are meant to be edited.)
>
> Because these are actions and not workflows, **nothing here runs in this
> repo**: an `action.yml` only executes when another repo's workflow `uses:` it.
> This repo has no `.github/workflows/` of its own and stays inert.

## Anatomy of an action

```
actions/<name>/
├── action.yml     # the composite action (what runs)
├── pixi.toml      # (if needed) the action's private toolchain — never touches the module
├── workflow.yml   # the thin caller workflow a module installs to invoke the action
└── README.md      # usage + inputs
```

## Using an action from a module

Reference it directly in a module workflow (≈6 lines):

```yaml
jobs:
  validate-module:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: omni-scrna/boilerplate/actions/validate-module@main
```

…or install the ready-made caller workflow from this catalog:

```sh
actions/install.sh --list                       # see what's available
actions/install.sh validate-module ../my-module # drop the workflow into a module
```

`install.sh` is plain POSIX sh — it does not assume the module uses pixi, and it
never overwrites an existing workflow.

## Available actions

- **[`validate-module`](validate-module/)** — runs `ob validate module` against
  omnibenchmark's `main` branch.
