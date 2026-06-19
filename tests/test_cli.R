#!/usr/bin/env Rscript
# Tests for src/common/r/cli.R (the shared CLI helpers).
# Plain base R + stopifnot (no testthat). Exits non-zero on first failure.

# The cli helpers are tested against the plan's real schema/, fetched into this
# gitignored dir by `pixi run fetch-schema` (run it before the tests).
source("src/common/r/cli.R")
SCHEMA_DIR <- "tests/fixtures/schema"

errors <- function(expr) tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
parser <- function() arg_parser("test", hide.opts = TRUE)

# An entrypoint-style parser: shared base + a real stage's args, then argparser parses.
stage_parser <- function() add_stage_args(add_base_args(parser()), "two-filter")
argv <- c("--output_dir", "o", "--name", "n",
          "--properties.info", "p", "--rawdata.h5ad", "r")

# happy path: base + stage args injected, then argparser parses. Field names come
# straight from argparser (the flag minus `--`; dots kept).
a <- parse_args(stage_parser(), argv = argv)
stopifnot(
  a$name == "n",                       # from _base.json
  a$output_dir == "o",                 # from _base.json
  a[["properties.info"]] == "p",       # stage arg
  a[["rawdata.h5ad"]] == "r"
)

# argparser rejects unknown flags
stopifnot(errors(parse_args(stage_parser(), argv = c(argv, "--bogus", "x"))))

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
p <- add_argument(stage_parser(), "--n_components", type = "integer", help = "k")
am <- parse_args(p, argv = c(argv, "--n_components", "50"))
stopifnot(am$n_components == 50L, is.integer(am$n_components))

# type coercion comes from argparser
p2 <- add_argument(parser(), "--i", type = "integer", help = "i")
p2 <- add_argument(p2, "--f", type = "numeric", help = "f")
b <- parse_args(p2, argv = c("--i", "3", "--f", "1.5"))
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

# namespaced load: helpers confined to `ns`, schema still located
ns <- new.env()
source("src/common/r/cli.R", local = ns)
ns$SCHEMA_DIR <- "tests/fixtures/schema"
stopifnot(exists("add_stage_args", envir = ns, inherits = FALSE))
np <- ns$add_stage_args(ns$add_base_args(parser()), "two-filter")
nsa <- parse_args(np, argv = argv)
stopifnot(nsa[["properties.info"]] == "p", nsa$name == "n")

cat("R cli tests: PASS\n")
