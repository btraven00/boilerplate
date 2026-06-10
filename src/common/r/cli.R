# Shared CLI helpers for omnibenchmark module entrypoints (R).
#
# Reserved, overwrite-on-update path (src/common/r/) — see AGENTS.md. Mirrors
# src/common/python/cli.py: the module author writes their OWN CLI and owns the
# parsing; this file just supplies the shared, synced contract (universal base
# args + the stage's I/O contract) as arg-specs, so Python and R entrypoints share
# one contract. Base R has no parser object, so the idiom is "assemble the spec
# list — common supplies the shared chunks, you append your own — then parse":
#
#   source("common/cli.R")              # R has no import namespace; we source()
#   specs <- c(base_args(),             # --output_dir, --name (schema/_base.json)
#              stage_args("embedding"), # the stage I/O contract (schema/embedding.json)
#              list(                     # the author's own method params, fully visible:
#                list(flag = "--solver", type = "string", choices = c("arpack", "randomized")),
#                list(flag = "--n_components", type = "integer")))
#   args <- parse_args(specs)
#   # args$output_dir, args$name, args$pcas, args$solver, args$n_components
#
# Dependencies: jsonlite only (to read the schema). The arg parsing itself is
# base R — deliberately NOT the `argparse` package, which wraps Python's argparse
# (a heavy cross-language dep that fights "lean per language", AGENTS.md).
#
# An arg-spec is a list(flag=, type=, dest=<opt>, choices=<opt>, help=<opt>).
# Conventions for schema-declared args: each is required; dest defaults to the
# flag with dots/dashes -> "_" unless overridden. Types: path|string|integer|number.
# An optional "choices" vector restricts accepted values (an enum).
#
# Note (history): an earlier iteration was a parser FACTORY — it built the whole
# parser from JSON, composed a third <interface>.extends.json overlay, and
# auto-picked the sole schema (parse_args("embedding")). That was deliberately
# simplified to these import-helpers; the richer version is recoverable from git
# history if it's ever wanted back.

suppressPackageStartupMessages(library(jsonlite))

# Resolve this file's directory at SOURCE time (so the schema dir is known later,
# after source() returns and the frame is gone). Handles Rscript --file and source().
.this_dir <- function() {
  # When this file is source()d (the normal case), the sourced path is the right
  # anchor — prefer it over --file (which points at the outer script).
  for (i in rev(seq_len(sys.nframe()))) {
    of <- sys.frame(i)$ofile
    if (!is.null(of)) return(dirname(normalizePath(of)))
  }
  a <- commandArgs(trailingOnly = FALSE)
  f <- sub("^--file=", "", grep("^--file=", a, value = TRUE))
  if (length(f)) return(dirname(normalizePath(f)))
  getwd()
}
COMMON_VERSION <- "0.3.0"  # x-release-version — stamped from src/common/VERSION by `pixi run version`

# Works under both layouts: rendered `common/cli.R` (schema is a sibling) and the
# template's `common/r/cli.R` (schema is one level up).
.find_schema_dir <- function() {
  here <- .this_dir()
  for (base in c(here, dirname(here))) {
    cand <- file.path(base, "schema")
    if (dir.exists(cand)) return(cand)
  }
  file.path(here, "schema")
}
.SCHEMA_DIR <- .find_schema_dir()
.BASE_SCHEMA <- "_base"  # universal args (--output_dir, --name)

# Version of the src/common shared code, so a module can report which copy of the
# boilerplate scaffolding it carries. Stamped from src/common/VERSION (single
# source of truth) — bump VERSION and run `pixi run version`.
common_version <- function() COMMON_VERSION

.r_types <- c(path = "character", string = "character",
              integer = "integer", number = "double")

.default_dest <- function(flag) gsub("[.-]", "_", sub("^--", "", flag))

`%||%` <- function(a, b) if (is.null(a) || is.na(a)) b else a

.coerce <- function(val, type) {
  switch(.r_types[[type]] %||% "character",
         integer = as.integer(val),
         double  = as.numeric(val),
         as.character(val))
}

.read_args <- function(path) {
  if (!file.exists(path)) stop(sprintf("schema not found: %s", path))
  jsonlite::fromJSON(path, simplifyDataFrame = FALSE)$args
}

# Shared arg-specs from schema/_base.json (universal base args).
base_args <- function(schema_dir = .SCHEMA_DIR)
  .read_args(file.path(schema_dir, paste0(.BASE_SCHEMA, ".json")))

# Shared arg-specs from schema/<interface>.json (the stage's I/O contract).
stage_args <- function(interface, schema_dir = .SCHEMA_DIR)
  .read_args(file.path(schema_dir, paste0(interface, ".json")))

# Parse argv against an assembled list of arg-specs (shared chunks from
# base_args()/stage_args() plus the author's own). Every spec is required;
# unknown flags are rejected; values are type-coerced and choice-checked.
parse_args <- function(specs, argv = commandArgs(trailingOnly = TRUE)) {
  by_key <- list()  # keyed by flag sans leading "--"
  for (arg in specs) {
    key <- sub("^--", "", arg$flag)
    dest <- if (!is.null(arg$dest)) arg$dest else .default_dest(arg$flag)
    by_key[[key]] <- list(type = arg$type, dest = dest, choices = arg$choices)
  }

  values <- list()
  i <- 1L
  while (i <= length(argv)) {
    tok <- argv[[i]]
    if (!startsWith(tok, "--")) stop(sprintf("unexpected argument: %s", tok))
    key <- substring(tok, 3L)
    if (is.null(by_key[[key]])) stop(sprintf("unknown argument: --%s", key))
    if (i + 1L > length(argv)) stop(sprintf("--%s requires a value", key))
    sp <- by_key[[key]]
    val <- .coerce(argv[[i + 1L]], sp$type)
    if (!is.null(sp$choices) && !(val %in% unlist(sp$choices)))
      stop(sprintf("--%s must be one of: %s", key,
                   paste(unlist(sp$choices), collapse = ", ")))
    values[[sp$dest]] <- val
    i <- i + 2L
  }

  missing <- Filter(function(k) is.null(values[[by_key[[k]]$dest]]), names(by_key))
  if (length(missing) > 0L)
    stop(sprintf("missing required argument(s): %s",
                 paste0("--", missing, collapse = ", ")))
  values
}
