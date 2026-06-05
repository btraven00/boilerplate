#!/usr/bin/env sh
# Install a catalog action's caller workflow into a module repo.
#
# Usage:
#   actions/install.sh <action> <target-module-dir>
#   actions/install.sh --list
#
# This only copies the action's `workflow.yml` to the module's
# .github/workflows/. The action's real work (and the omnibenchmark dependency)
# lives in the reusable composite action, referenced by the workflow — so the
# module gains CI without taking on pixi or omnibenchmark itself.
#
# Non-destructive: an existing workflow is never overwritten.
set -eu

CATALOG="$(CDPATH= cd "$(dirname "$0")" && pwd)"

list_actions() {
  echo "Available actions:"
  for dir in "$CATALOG"/*/; do
    [ -f "${dir}action.yml" ] || continue
    name="$(basename "$dir")"
    desc="$(sed -n 's/^description: *//p' "${dir}action.yml" | head -1 | sed 's/^"//; s/"$//')"
    printf '  %-18s %s\n' "$name" "$desc"
  done
  echo
  echo "Install with:  actions/install.sh <action> <target-module-dir>"
}

case "${1:-}" in
  ""|-h|--help)
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
    ;;
  -l|--list|list)
    list_actions
    exit 0
    ;;
esac

action="$1"
target="${2:-}"
src="$CATALOG/$action/workflow.yml"

[ -f "$CATALOG/$action/action.yml" ] || { echo "error: unknown action '$action'. Try --list." >&2; exit 1; }
[ -n "$target" ] || { echo "error: missing target module dir." >&2; exit 2; }
[ -d "$target" ] || { echo "error: target module dir does not exist: $target" >&2; exit 1; }
[ -f "$src" ] || { echo "error: action '$action' has no installable workflow.yml." >&2; exit 1; }

dst="$target/.github/workflows/$action.yml"
if [ -f "$dst" ]; then
  echo "skip   $dst (already exists)"
  exit 0
fi

mkdir -p "$target/.github/workflows"
cp "$src" "$dst"
echo "copy   $dst"
echo "Installed '$action'. Commit it in the module to enable CI."
