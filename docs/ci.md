# Adding CI to your module

This guide is for **module authors**: how to validate your omni-scrna module in
CI. It frames the workflow and the choices; the [`actions/`](../actions/) catalog
READMEs are the source of truth for each action's inputs and behaviour.

Validation runs `ob validate module` against omnibenchmark's `main` branch. The
toolchain (pixi + omnibenchmark) lives **inside the reusable action**, so your
module does not need to be pixi-based and takes on no omnibenchmark dependency
of its own.

## Two ways to wire it up

### A. Reference the action directly (recommended)

Add this workflow to your module at `.github/workflows/validate-module.yml`:

<!-- embed:actions/validate-module/workflow.yml -->
```yaml
# Caller workflow installed into a module at .github/workflows/validate-module.yml.
# It is intentionally tiny: all the work lives in the reusable composite action,
# so fixes upstream reach every module without re-installing.
name: Validate module

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

jobs:
  validate-module:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - uses: omni-scrna/boilerplate/actions/validate-module@main
```
<!-- /embed -->

That's the whole file. Because the work lives in the reusable composite action
referenced by `uses: …@main`, fixes to the **action** reach your module
automatically — you never re-install. The few lines of the caller workflow
itself are yours to maintain, though: the `actions/checkout` version, for
instance, is pinned in your copy and only changes when you bump it.

### B. Install the workflow from the catalog

If you'd rather not hand-write YAML, the boilerplate ships the same file and a
POSIX installer:

```sh
actions/install.sh --list                        # list available actions
actions/install.sh validate-module ../my-module  # copy the workflow in
```

`install.sh` does not assume your module uses pixi and **never overwrites** an
existing workflow. Commit the copied file to enable CI.

## Inputs

The action accepts `path` (default `.`) and `strict` (default `false`). To treat
warnings as errors:

```yaml
      - uses: omni-scrna/boilerplate/actions/validate-module@main
        with:
          strict: "true"
```

See [`actions/validate-module/README.md`](../actions/validate-module/README.md)
for the full table.

## A note on versioning

Both paths pin the action at `@main`, so upstream fixes reach every module
immediately — but so would a breaking change. If your module needs stability,
watch for tagged releases of the boilerplate and pin to a tag instead.

---

> The workflow snippet above is embedded verbatim from
> `actions/validate-module/workflow.yml` and kept in sync by `pixi run docs`
> (see [`scripts/embed_snippets.py`](../scripts/embed_snippets.py)). Don't edit
> it by hand.
