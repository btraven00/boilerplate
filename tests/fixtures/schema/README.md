# schema fixtures

Example stage schemas, kept **only to exercise the shared `cli` helpers** in
`tests/test_cli.py` / `tests/test_cli.R`.

These are **not** the source of truth. The canonical, benchmark-owned schemas now
live in the plan repo at
[`omni-scrna/split-stages-plan` → `schema/`](https://github.com/omni-scrna/split-stages-plan/tree/main/schema);
a real module vendors the ones it implements into its own `src/common/schema/`
via `scripts/pull.py`. These copies just stand in for that vendored set so the
template's tests can run offline.
