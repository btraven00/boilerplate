# validators

Ad-hoc validators run against every file produced by a stage. By convention:

- Every validator receives a **single file path** as its argument.
- Validators are dropped at **`<STAGE>/<OUTPUT_NAME>/validate.<ext>`** — a
  self-documenting layout so tooling can discover a stage's contract by path.
- Use **as few dependencies as possible**.

This mirrors the convention prototyped in the benchmark plan
([split-stages-plan](https://github.com/omni-scrna/split-stages-plan)'s
`validators/`), so a validator written here runs unchanged there and vice versa.

## TODO — temporary content

`five-pca/pcas.tsv/validate.R` is **copied from the plan** as a working example
to build shared validator scaffolding against; it currently lives in two repos.
Once validators get a proper home (as modules, or a dedicated package), remove
the copy so the contract has a single source of truth. See AGENTS.md.
