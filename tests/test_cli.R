#!/usr/bin/env Rscript
# Tests for src/common/r/cli.R (the shared CLI helpers).
# Plain base R + stopifnot (no testthat). Exits non-zero on first failure.

source("src/common/r/cli.R")

emb <- c("--output_dir", "o", "--name", "n",
         "--pcas.tsv", "p", "--rawdata.clusters_truth", "t")

errors <- function(expr) {
  tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
}

# happy path: assemble base + stage specs (the entrypoint idiom), then parse
emb_specs <- c(base_args(), stage_args("embedding"))
a <- parse_args(emb_specs, argv = emb)
stopifnot(
  a$name == "n",                 # from _base.json
  a$output_dir == "o",           # from _base.json
  a$pcas == "p",                 # stage schema dest override
  a$clusters_truth == "t"
)

# default dest maps dots and dashes
stopifnot(.default_dest("--a.b-c") == "a_b_c")

# strictness
stopifnot(errors(parse_args(emb_specs, argv = c(emb, "--bogus", "x"))))  # unknown
stopifnot(errors(parse_args(emb_specs, argv = c("--name", "n"))))        # missing
stopifnot(errors(stage_args("does-not-exist")))                          # bad iface

# base_args() yields the universal args on their own
ba <- parse_args(base_args(), argv = c("--output_dir", "o", "--name", "n"))
stopifnot(ba$output_dir == "o", ba$name == "n")

# the author's own method params coexist with the shared specs
specs <- c(emb_specs, list(
  list(flag = "--solver", type = "string", choices = c("arpack", "randomized")),
  list(flag = "--n_components", type = "integer")))
am <- parse_args(specs, argv = c(emb, "--solver", "arpack", "--n_components", "50"))
stopifnot(am$solver == "arpack", am$n_components == 50L)

# type coercion
tspecs <- list(
  list(flag = "--i", type = "integer"),
  list(flag = "--f", type = "number"))
b <- parse_args(tspecs, argv = c("--i", "3", "--f", "1.5"))
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

# choices: an enum restricts accepted values
cspecs <- list(list(flag = "--solver", type = "string",
                    choices = c("arpack", "randomized")))
stopifnot(parse_args(cspecs, argv = c("--solver", "arpack"))$solver == "arpack")
stopifnot(errors(parse_args(cspecs, argv = c("--solver", "BOGUS"))))   # rejected

# version accessor reads src/common/VERSION
v <- common_version()
stopifnot(
  v == trimws(readLines("src/common/VERSION", warn = FALSE)[1]),
  grepl("^[0-9]+\\.[0-9]+\\.[0-9]+", v)
)

cat("R cli tests: PASS\n")
