# example module fixture

A stand-in for a real module generated from this boilerplate: an
`omnibenchmark.yaml` plus the schemas a module vendors into `src/common/schema/`.
It exists so the tests run against a **realistic module layout** rather than the
boilerplate itself: `tests/test_cli.py` / `tests/test_cli.R` read
`src/common/schema/` to exercise the shared `cli` helpers offline — the same path
a real module uses.

The schemas here are **not** the source of truth. The canonical, benchmark-owned
schemas live in the plan repo at
[`omni-scrna/split-stages-plan` → `schema/`](https://github.com/omni-scrna/split-stages-plan/tree/main/schema);
`pixi run refresh-fixtures` re-vendors them here from the plan (the same source
`scripts/pull.py` uses for a real module), so the engine is tested against the
real contract.
