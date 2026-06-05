# validate-module

Reusable composite GitHub Action that validates an omnibenchmark module with
`ob validate module`, using **omnibenchmark from its `main` branch**.

The omnibenchmark toolchain (pixi + omnibenchmark) is self-contained in the
action, so **the module being validated does not need to be pixi-based** and
carries no omnibenchmark dependency of its own.

## Use it directly

Add a workflow to your module — this is all it takes:

```yaml
name: Validate module
on: [push, pull_request, workflow_dispatch]
jobs:
  validate-module:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: omni-scrna/boilerplate/actions/validate-module@main
```

Or install that caller workflow from the catalog:

```sh
actions/install.sh validate-module ../my-module
```

## Inputs

| input    | default | description                                          |
|----------|---------|------------------------------------------------------|
| `path`   | `.`     | Path to the module to validate.                      |
| `strict` | `false` | Treat warnings as errors (`ob validate module --strict`). |

Example with inputs:

```yaml
      - uses: omni-scrna/boilerplate/actions/validate-module@main
        with:
          strict: "true"
```

## Files

- `action.yml` — the composite action (setup pixi → run `ob validate module`).
- `pixi.toml` — the action's private toolchain manifest (pins omnibenchmark@main).
- `workflow.yml` — the thin caller workflow installed into a module.
