#!/usr/bin/env Rscript
# Tests for src/common/r/cli.R (the shared CLI helpers).
# Plain base R + stopifnot (no testthat). Exits non-zero on first failure.

# Example schemas stand in for the set a real module vendors from the plan's
# schema/ — see tests/fixtures/module/README.md.
source("src/common/r/cli.R")
SCHEMA_DIR <- "tests/fixtures/module/src/common/schema"

errors <- function(expr) tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
parser <- function() arg_parser("test", hide.opts = TRUE)

# An entrypoint-style parser: shared base + stage args, then argparser parses.
emb_parser <- function() add_stage_args(add_base_args(parser()), "embedding")
emb <- c("--output_dir", "o", "--name", "n",
         "--pcas.tsv", "p", "--rawdata.clusters_truth", "t")

# happy path: base + stage args injected, then argparser parses. Field names come
# straight from argparser (the flag minus `--`; dots kept).
a <- parse_args(emb_parser(), argv = emb)
stopifnot(
  a$name == "n",                       # from _base.json
  a$output_dir == "o",                 # from _base.json
  a[["pcas.tsv"]] == "p",              # stage arg
  a[["rawdata.clusters_truth"]] == "t"
)

# argparser rejects unknown flags
stopifnot(errors(parse_args(emb_parser(), argv = c(emb, "--bogus", "x"))))

# a missing schema / unknown interface still errors
stopifnot(errors(add_stage_args(parser(), "does-not-exist")))          # bad iface
# a bad SCHEMA_DIR also errors (override the global, then restore for later tests)
.saved_schema_dir <- SCHEMA_DIR
SCHEMA_DIR <- "no/such/dir"
stopifnot(errors(add_base_args(parser())))
SCHEMA_DIR <- .saved_schema_dir

# base args alone
ba <- parse_args(add_base_args(parser()), argv = c("--output_dir", "o", "--name", "n"))
stopifnot(ba$output_dir == "o", ba$name == "n")

# the author adds their own params with argparser directly; typing is argparser's
p <- add_argument(emb_parser(), "--n_components", type = "integer", help = "k")
am <- parse_args(p, argv = c(emb, "--n_components", "50"))
stopifnot(am$n_components == 50L, is.integer(am$n_components))

# type coercion comes from argparser
p2 <- add_argument(parser(), "--i", type = "integer", help = "i")
p2 <- add_argument(p2, "--f", type = "numeric", help = "f")
b <- parse_args(p2, argv = c("--i", "3", "--f", "1.5"))
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

# namespaced load: helpers confined to `ns`, schema still located
ns <- new.env()
source("src/common/r/cli.R", local = ns)
ns$SCHEMA_DIR <- "tests/fixtures/module/src/common/schema"
stopifnot(exists("add_stage_args", envir = ns, inherits = FALSE))
np <- ns$add_stage_args(ns$add_base_args(parser()), "embedding")
nsa <- parse_args(np, argv = emb)
stopifnot(nsa[["pcas.tsv"]] == "p", nsa$name == "n")

cat("R cli tests: PASS\n")
