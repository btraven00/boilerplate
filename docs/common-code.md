# Getting the shared code into your module

For **module authors**: `src/common/` is a **reserved, copied-in path** — your
module's local copy of shared code, which you don't hand-write. A script copies in
two things, at the refs you pin, so Python
and R modules share one contract (your own method params stay in your entrypoint —
see [cli.md](cli.md)):

- **the common engine** (`cli.py` / `cli.R`) — from this boilerplate repo.
- **the schemas** (`_base.json` + each stage `<interface>.json`) — from the
  **benchmark's** `schema/`.

## Pull it

[`scripts/pull.py`](../scripts/pull.py) takes the module root as an optional
argument (default: the current directory), reading `<root>/omnibenchmark.yaml` and
writing `<root>/src/common`. Point it at your module, or run it from inside one:

```sh
python boilerplate/scripts/pull.py path/to/module   # or, from the module root:
cd my-module && python ../boilerplate/scripts/pull.py
```

It writes the engine to `src/common/` (flattening the `lang` you pick to
`src/common/cli.*`) and the schemas to `src/common/schema/`. Configure it in your
`omnibenchmark.yaml`:

```yaml
boilerplate:
  repo: https://github.com/omni-scrna/boilerplate
  ref: v0.1.0          # pin: a tag or a branch
  lang: r              # or: python
template-for:
  - { name: split-stages, repo: …/split-stages-plan, plan: benchmark_conda.yaml, ref: main }
implements:
  - split-stages/embedding@0.1.0
```

Optional, if your module uses pixi — paste into `pixi.toml` for `pixi run pull`:

```toml
[tasks]
pull = "python ../boilerplate/scripts/pull.py"
```

## Commit it, re-run on change

Re-run `pull.py` whenever the boilerplate or the plan schemas changes upstream.
If a benchmark has not published a schema at `schema/<iface>.json`, the `pull.py` script notes it and skips.

See [`AGENTS.md`](../AGENTS.md) for rationale, [cli.md](cli.md) for the helpers,
[ci.md](ci.md) for CI.
