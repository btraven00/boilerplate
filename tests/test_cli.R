#!/usr/bin/env Rscript
# Tests for src/common/r/cli.R (the shared CLI helpers).
# Plain base R + stopifnot (no testthat). Exits non-zero on first failure.

# Example schemas stand in for the set a real module vendors from the plan's
# schema/ — see tests/fixtures/module/README.md.
source("src/common/r/cli.R")
SCHEMA_DIR <- "tests/fixtures/module/src/common/schema"

errors <- function(expr) tryCatch({ force(expr); FALSE }, error = function(e) TRUE)
parser <- function() arg_parser("test", hide.opts = TRUE)

# An entrypoint-style parser: shared base + stage args, then the author's own.
emb_parser <- function() add_stage_args(add_base_args(parser()), "embedding")
emb <- c("--output_dir", "o", "--name", "n",
         "--pcas.tsv", "p", "--rawdata.clusters_truth", "t")

# happy path: base + stage args added to the author's parser, then parse
a <- parse_args(emb_parser(), argv = emb)
stopifnot(
  a$name == "n",                 # from _base.json
  a$output_dir == "o",           # from _base.json
  a$pcas == "p",                 # stage schema dest override (--pcas.tsv -> pcas)
  a$clusters_truth == "t"
)

# default dest maps dots and dashes
stopifnot(.default_dest("--a.b-c") == "a_b_c")

# strictness
stopifnot(errors(parse_args(emb_parser(), argv = c(emb, "--bogus", "x"))))     # unknown
stopifnot(errors(parse_args(emb_parser(), argv = c("--name", "n"))))           # missing
stopifnot(errors(add_stage_args(parser(), "does-not-exist")))                  # bad iface
stopifnot(errors(add_base_args(parser(), schema_dir = "no/such/dir")))         # no schema dir

# base args alone
ba <- parse_args(add_base_args(parser()), argv = c("--output_dir", "o", "--name", "n"))
stopifnot(ba$output_dir == "o", ba$name == "n")

# author method params: a plain argparser arg + an enum via add_choice
# (argparser's add_argument requires `help`)
p <- emb_parser()
p <- add_argument(p, "--n_components", type = "integer", help = "k")  # argparser directly
p <- add_choice(p, "--solver", c("arpack", "randomized"))  # enum, enforced
am <- parse_args(p, argv = c(emb, "--n_components", "50", "--solver", "arpack"))
stopifnot(am$n_components == 50L, is.integer(am$n_components), am$solver == "arpack")

# enum rejects an out-of-set value
stopifnot(errors(parse_args(p, argv = c(emb, "--n_components", "50", "--solver", "BOGUS"))))

# every arg is required — including the author's own (here --n_components is omitted)
stopifnot(errors(parse_args(p, argv = c(emb, "--solver", "arpack"))))

# type coercion comes from argparser
p2 <- add_argument(parser(), "--i", type = "integer", help = "i")
p2 <- add_argument(p2, "--f", type = "numeric", help = "f")
b <- parse_args(p2, argv = c("--i", "3", "--f", "1.5"))
stopifnot(is.integer(b$i), b$i == 3L, is.numeric(b$f), b$f == 1.5)

# namespaced load: helpers confined to `ns`, schema still located
ns <- new.env()
source("src/common/r/cli.R", local = ns)
ns$SCHEMA_DIR <- "tests/fixtures/module/src/common/schema"
stopifnot(exists("parse_args", envir = ns, inherits = FALSE))
np <- ns$add_stage_args(ns$add_base_args(parser()), "embedding")
nsa <- ns$parse_args(np, argv = emb)
stopifnot(nsa$pcas == "p", nsa$name == "n")

# version accessor reads src/common/VERSION
v <- common_version()
stopifnot(
  v == trimws(readLines("src/common/VERSION", warn = FALSE)[1]),
  grepl("^[0-9]+\\.[0-9]+\\.[0-9]+", v)
)

cat("R cli tests: PASS\n")
