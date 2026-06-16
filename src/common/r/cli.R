# Shared CLI helpers for omnibenchmark module entrypoints (R).
#
# Reserved, overwrite-on-update path (src/common/r/) — see AGENTS.md. Mirrors
# src/common/python/cli.py: the author owns the parser; these helpers inject the
# shared, synced contract (universal base args + the stage's I/O contract) onto
# it, and the author adds their own method params with argparser directly:
#
#   cli <- new.env(); source("src/common/cli.R", local = cli)
#   p <- arg_parser("PCA module")
#   p <- cli$add_base_args(p)                       # --output_dir, --name
#   p <- cli$add_stage_args(p, "embedding")          # the stage I/O contract
#   p <- add_argument(p, "--n_components", type = "integer", help = "PCs")  # your own
#   p <- cli$add_choice(p, "--solver", c("arpack", "randomized"))           # your own list of closed choices
#   args <- cli$parse_args(p)
#   # args$output_dir, args$name, args$pcas, args$n_components, args$solver
#
# Getting these files in place: this engine (src/common/cli.R) and the schema JSON
# it reads (src/common/schema/) are *copied* into your module, not hand-written.
# Run the pull step once to fetch them at the refs pinned in your
# omnibenchmark.yaml, and re-run it whenever they change upstream:
#
#   python boilerplate/scripts/pull.py path/to/module   # or, from the module root:
#   cd my-module && python ../boilerplate/scripts/pull.py
#
# See docs/common-code.md for the full workflow and docs/cli.md for using the helpers.
#
# We use the argparser CRAN package (pure R — unlike the argparse package, which
# wraps Python). argparser gives tokenizing, types, unknown-flag rejection and
# --help; cli$parse_args adds what argparser lacks for our contract — every arg
# is required, `choices` enums, a tidier `dest` name — for the flags these helpers
# register. argparser has no `choices`, so `add_choice` lets an author register an
# enum and still have it enforced.
#
# Schema arg-spec (in JSON): {flag, type, dest?, choices?, help?};
# types: path|string|integer|number.

# Attached so an entrypoint can call arg_parser()/add_argument(); we qualify internally.
suppressPackageStartupMessages(library(argparser))

COMMON_VERSION <- "0.1.0"  # x-release-version — stamped from src/common/VERSION by `pixi run version`

# Where the synced schema JSON lives (copied-in layout: src/common/schema/ at the
# module root). Override per call with `schema_dir =`, or set SCHEMA_DIR once after
# sourcing.
SCHEMA_DIR <- "src/common/schema"
.BASE_SCHEMA <- "_base"

# Version of the shared engine, so a module can report which copy it carries.
common_version <- function() COMMON_VERSION

`%||%` <- function(a, b) if (is.null(a)) b else a

# our schema type -> argparser type (path/string and anything else -> character)
.atype <- function(type) switch(type %||% "string",
                                integer = "integer", number = "numeric", "character")

# tidy attribute name for a flag: strip --, dots/dashes -> _ (schema `dest` wins);
# mirrors cli.py's _default_dest.
.default_dest <- function(flag) gsub("[.-]", "_", sub("^--", "", flag))

# argparser's own slot name for a flag: strip --, dashes -> _ (dots kept).
.argparser_key <- function(flag) gsub("-", "_", sub("^--", "", flag))

.read_args <- function(path) {
  if (!file.exists(path)) stop(sprintf("schema not found: %s", path), call. = FALSE)
  jsonlite::fromJSON(path, simplifyDataFrame = FALSE)$args
}

# Add one flag to the parser and register how parse_args should treat it (choices,
# dest). Shared by the schema args and author enums (add_choice); the `rules`
# attribute survives later add_argument() calls.
.add_arg <- function(p, flag, type = "string", help = "", dest = NULL, choices = NULL) {
  p <- argparser::add_argument(p, flag, help = help, type = .atype(type))
  rules <- attr(p, "rules") %||% list()
  rules[[.argparser_key(flag)]] <- list(dest = dest, choices = choices)
  attr(p, "rules") <- rules
  p
}

.add_specs <- function(p, specs) {
  for (spec in specs)
    p <- .add_arg(p, spec$flag, type = spec$type, help = spec$help %||% "",
                  dest = spec$dest %||% .default_dest(spec$flag),
                  choices = unlist(spec$choices))
  p
}

# Inject the universal base args (--output_dir, --name) onto the author's parser.
add_base_args <- function(p, schema_dir = SCHEMA_DIR)
  .add_specs(p, .read_args(file.path(schema_dir, paste0(.BASE_SCHEMA, ".json"))))

# Inject a stage's I/O contract (schema/<interface>.json) onto the author's parser.
add_stage_args <- function(p, interface, schema_dir = SCHEMA_DIR)
  .add_specs(p, .read_args(file.path(schema_dir, paste0(interface, ".json"))))

# Author helper for an enum param (argparser has no `choices`): add the flag and
# register its allowed values so cli$parse_args enforces them — the same path the
# schema args take.
add_choice <- function(p, flag, choices, type = "string", help = "")
  .add_arg(p, flag, type = type, help = help, choices = choices)

# Parse argv. argparser does tokenizing, typing, unknown-flag rejection and --help;
# we enforce required (every arg must be supplied) + choices, and map registered
# flags onto their `dest`.
parse_args <- function(p, argv = commandArgs(trailingOnly = TRUE)) {
  parsed <- argparser::parse_args(p, argv)
  rules <- attr(p, "rules") %||% list()

  # argparser has no concept of "required" args, so we must check for missing values
  values <- list()
  missing <- character(0)
  for (key in setdiff(names(parsed), c("", "help", "opts"))) {  # skip argparser's own slots
    val <- parsed[[key]]
    if (is.na(val)) {
      missing <- c(missing, key)
      next
    }
    rule <- rules[[key]]

    # enforce choices (if any), since argparser does not enforce them natively
    if (!is.null(rule$choices) && !(val %in% rule$choices))
      stop(sprintf("--%s must be one of: %s", key, paste(rule$choices, collapse = ", ")),
           call. = FALSE)
    values[[rule$dest %||% key]] <- val
  }
  if (length(missing))
    stop(sprintf("missing required argument(s): %s", paste0("--", missing, collapse = ", ")),
         call. = FALSE)
  values
}
