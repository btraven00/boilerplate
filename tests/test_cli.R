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

# auto-pick the single schema
stopifnot(parse_args(argv = emb)$name == "n")

# type coercion via a temp schema
d <- tempfile(); dir.create(d)
writeLines(
  '{"interface":"t","version":"0","args":[{"flag":"--i","type":"integer","help":""},{"flag":"--f","type":"number","help":""}]}',
  file.path(d, "t.json"))
b <- parse_args("t", argv = c("--i", "3", "--f", "1.5"), schema_dir = d)
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

cat("R cli tests: PASS\n")
