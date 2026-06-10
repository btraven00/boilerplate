#!/usr/bin/env Rscript
# Tests for src/common/r/cli.R (the schema-driven CLI engine).
# Plain base R + stopifnot (no testthat). Exits non-zero on first failure.

source("src/common/r/cli.R")

emb <- c("--output_dir", "o", "--name", "n",
         "--pcas.tsv", "p", "--rawdata.clusters_truth", "t")

errors <- function(expr) {
  tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
}

# happy path against the real embedding interface
a <- parse_args("embedding", argv = emb)
stopifnot(
  a$name == "n",
  a$pcas == "p",                 # schema dest override
  a$clusters_truth == "t",
  a$output_dir == "o"
)

# default dest maps dots and dashes
stopifnot(.default_dest("--a.b-c") == "a_b_c")

# strictness
stopifnot(errors(parse_args("embedding", argv = c(emb, "--bogus", "x"))))   # unknown
stopifnot(errors(parse_args("embedding", argv = c("--name", "n"))))         # missing
stopifnot(errors(load_interface("does-not-exist")))                          # bad iface

# auto-pick the single STAGE schema (in a dir holding exactly one)
dap <- tempfile(); dir.create(dap)
writeLines('{"interface":"only","version":"0","args":[{"flag":"--x","type":"string"}]}',
           file.path(dap, "only.json"))
stopifnot(parse_args(argv = c("--x", "v"), schema_dir = dap)$x == "v")
# auto-pick is ambiguous when a dir ships several stage schemas
dap2 <- tempfile(); dir.create(dap2)
writeLines('{"interface":"a","version":"0","args":[]}', file.path(dap2, "a.json"))
writeLines('{"interface":"b","version":"0","args":[]}', file.path(dap2, "b.json"))
stopifnot(errors(parse_args(schema_dir = dap2)))

# type coercion via a temp schema
d <- tempfile(); dir.create(d)
writeLines(
  '{"interface":"t","version":"0","args":[{"flag":"--i","type":"integer","help":""},{"flag":"--f","type":"number","help":""}]}',
  file.path(d, "t.json"))
b <- parse_args("t", argv = c("--i", "3", "--f", "1.5"), schema_dir = d)
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

# _base supplies the universal args, so the slimmed embedding.json still yields
# --output_dir/--name (backward-compatible). (covered by the happy path above)

# choices: an enum restricts accepted values
dc <- tempfile(); dir.create(dc)
writeLines(
  '{"interface":"t","version":"0","args":[{"flag":"--solver","type":"string","choices":["arpack","randomized"]}]}',
  file.path(dc, "t.json"))
stopifnot(parse_args("t", argv = c("--solver", "arpack"), schema_dir = dc)$solver == "arpack")
stopifnot(errors(parse_args("t", argv = c("--solver", "BOGUS"), schema_dir = dc)))   # rejected

# layering: _base -> <interface> -> <interface>.extends, later wins by flag
dl <- tempfile(); dir.create(dl)
writeLines('{"interface":"_base","args":[{"flag":"--output_dir","type":"path"},{"flag":"--name","type":"string"}]}',
           file.path(dl, "_base.json"))
writeLines('{"interface":"pca","version":"0.1.0","args":[{"flag":"--normalized_selected.h5","dest":"input_h5","type":"path"}]}',
           file.path(dl, "pca.json"))
writeLines('{"interface":"pca","args":[{"flag":"--solver","type":"string","choices":["arpack","randomized"]},{"flag":"--n_components","type":"integer"}]}',
           file.path(dl, "pca.extends.json"))
sp <- load_interface("pca", schema_dir = dl)
flags <- vapply(sp$args, function(a) a$flag, character(1))
stopifnot(identical(flags, c("--output_dir", "--name", "--normalized_selected.h5",
                             "--solver", "--n_components")))
al <- parse_args("pca", schema_dir = dl,
  argv = c("--output_dir", "o", "--name", "n", "--normalized_selected.h5", "x.h5",
           "--solver", "arpack", "--n_components", "50"))
stopifnot(al$input_h5 == "x.h5", al$n_components == 50L, al$solver == "arpack")
# choices contributed by the extends layer are enforced
stopifnot(errors(parse_args("pca", schema_dir = dl,
  argv = c("--output_dir", "o", "--name", "n", "--normalized_selected.h5", "x.h5",
           "--solver", "BOGUS", "--n_components", "50"))))
# auto-pick lands on the sole STAGE schema, skipping _base and .extends
stopifnot(load_interface(NULL, schema_dir = dl)$interface == "pca")

# extends overrides a lower layer by flag (no duplication)
do <- tempfile(); dir.create(do)
writeLines('{"interface":"pca","version":"0.1.0","args":[{"flag":"--solver","type":"string","help":"base"}]}',
           file.path(do, "pca.json"))
writeLines('{"interface":"pca","args":[{"flag":"--solver","type":"string","choices":["arpack"],"help":"over"}]}',
           file.path(do, "pca.extends.json"))
spo <- load_interface("pca", schema_dir = do)
stopifnot(length(spo$args) == 1L, spo$args[[1]]$help == "over")

# version accessor reads src/common/VERSION
v <- common_version()
stopifnot(
  v == trimws(readLines("src/common/VERSION", warn = FALSE)[1]),
  grepl("^[0-9]+\\.[0-9]+\\.[0-9]+", v)
)

cat("R cli tests: PASS\n")
