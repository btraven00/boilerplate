# Schema-driven CLI parsing for omnibenchmark module entrypoints (R).
#
# Reserved, overwrite-on-update path (src/common/r/) — see AGENTS.md. Mirrors
# src/common/python/cli.py: the CLI is defined as data in
# src/common/schema/<interface>.json and built into a parser the same way in
# both languages, so Python and R entrypoints share one contract.
#
# Dependencies: jsonlite only (to read the schema). The arg parsing itself is
# base R — deliberately NOT the `argparse` package, which wraps Python's argparse
# (a heavy cross-language dep that fights "lean per language", AGENTS.md).
#
# An *interface* is a named, versioned CLI contract owned by a benchmark; a
# module "satisfies" it by carrying its schema and parsing against it. Schema:
#   { "interface": "embedding", "version": "0.1.0",
#     "benchmark": "omni-scrna/split-stages-plan",
#     "args": [ {"flag":"--name","type":"string","help":"...","dest":"<opt>"}, ... ] }
#
# Conventions: every arg is required; unknown flags rejected; dest defaults to
# the flag with dots/dashes -> "_" unless overridden. Types: path|string|integer|number.
# An optional "choices" list restricts accepted values (an enum).
#
# Layering — an interface is composed from up to three files in schema/, each
# contributing args, later layers winning per flag:
#   _base.json               universal args every module gets (--output_dir, --name)
#   <interface>.json         the stage's I/O contract (benchmark-owned)
#   <interface>.extends.json module-local extras/overrides (author-owned)
# parse_args("pca") merges all three by convention; a module carrying only
# <interface>.json behaves as before. "_*" and "*.extends.json" are not stages.
#
# Usage in an entrypoint (in a rendered module the shared code is `common/`):
#   source("common/cli.R")              # R has no import namespace; we source()
#   args <- parse_args("embedding")     # or parse_args() if the module has one schema
#   # args$output_dir, args$name, args$pcas, args$clusters_truth

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
COMMON_VERSION <- "0.2.1"  # x-release-version — stamped from src/common/VERSION by `pixi run version`

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

# Version of the src/common shared code, so a module can report which copy of the
# boilerplate scaffolding it carries. Stamped from src/common/VERSION (single
# source of truth) — bump VERSION and run `pixi run version`.
common_version <- function() COMMON_VERSION

.r_types <- c(path = "character", string = "character",
              integer = "integer", number = "double")

.default_dest <- function(flag) gsub("[.-]", "_", sub("^--", "", flag))

.coerce <- function(val, type) {
  switch(.r_types[[type]] %||% "character",
         integer = as.integer(val),
         double  = as.numeric(val),
         as.character(val))
}
`%||%` <- function(a, b) if (is.null(a) || is.na(a)) b else a

.BASE_SCHEMA <- "_base"             # universal args, merged first; not a stage
.EXTENDS_SUFFIX <- ".extends.json"  # module-local overlay for <interface>

# A stage schema is a plain <interface>.json — not the base ("_*") nor an overlay.
.is_stage_schema <- function(name)
  !startsWith(name, "_") && !endsWith(name, .EXTENDS_SUFFIX)

.read_schema <- function(path) {
  if (!file.exists(path)) return(NULL)
  jsonlite::fromJSON(path, simplifyDataFrame = FALSE)
}

# Overlay `child` args onto `parent`: same flag overrides (keeping position), a
# new flag is appended.
.merge_args <- function(parent, child) {
  flags <- vapply(parent, function(a) a$flag, character(1))
  for (a in child) {
    i <- match(a$flag, flags)
    if (is.na(i)) { parent <- c(parent, list(a)); flags <- c(flags, a$flag) }
    else parent[[i]] <- a
  }
  parent
}

# Compose an interface: _base (universal) -> <interface> (stage contract) ->
# <interface>.extends (module-local overrides), later layers winning per flag.
load_interface <- function(interface = NULL, schema_dir = .SCHEMA_DIR) {
  if (is.null(interface)) {
    found <- list.files(schema_dir, pattern = "\\.json$")
    stages <- found[vapply(found, .is_stage_schema, logical(1))]
    if (length(stages) != 1L)
      stop(sprintf("specify an interface; found %d stage schemas in %s",
                   length(stages), schema_dir))
    interface <- sub("\\.json$", "", stages)
  }
  stage_path <- file.path(schema_dir, paste0(interface, ".json"))
  if (!file.exists(stage_path)) stop(sprintf("interface schema not found: %s", stage_path))
  spec <- jsonlite::fromJSON(stage_path, simplifyDataFrame = FALSE)

  args <- list()
  base <- .read_schema(file.path(schema_dir, paste0(.BASE_SCHEMA, ".json")))
  if (!is.null(base)) args <- .merge_args(args, base$args)
  args <- .merge_args(args, spec$args)
  ext <- .read_schema(file.path(schema_dir, paste0(interface, .EXTENDS_SUFFIX)))
  if (!is.null(ext)) args <- .merge_args(args, ext$args)

  spec$args <- args
  spec
}

parse_args <- function(interface = NULL,
                       argv = commandArgs(trailingOnly = TRUE),
                       schema_dir = .SCHEMA_DIR) {
  schema <- load_interface(interface, schema_dir)

  specs <- list()  # keyed by flag sans leading "--"
  for (arg in schema$args) {
    key <- sub("^--", "", arg$flag)
    dest <- if (!is.null(arg$dest)) arg$dest else .default_dest(arg$flag)
    specs[[key]] <- list(type = arg$type, dest = dest, choices = arg$choices)
  }

  values <- list()
  i <- 1L
  while (i <= length(argv)) {
    tok <- argv[[i]]
    if (!startsWith(tok, "--")) stop(sprintf("unexpected argument: %s", tok))
    key <- substring(tok, 3L)
    if (is.null(specs[[key]])) stop(sprintf("unknown argument: --%s", key))
    if (i + 1L > length(argv)) stop(sprintf("--%s requires a value", key))
    sp <- specs[[key]]
    val <- .coerce(argv[[i + 1L]], sp$type)
    if (!is.null(sp$choices) && !(val %in% unlist(sp$choices)))
      stop(sprintf("--%s must be one of: %s", key,
                   paste(unlist(sp$choices), collapse = ", ")))
    values[[sp$dest]] <- val
    i <- i + 2L
  }

  missing <- Filter(function(k) is.null(values[[specs[[k]]$dest]]), names(specs))
  if (length(missing) > 0L)
    stop(sprintf("missing required argument(s): %s",
                 paste0("--", missing, collapse = ", ")))
  values
}
