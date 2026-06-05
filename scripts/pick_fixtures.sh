#!/usr/bin/env sh
# Pick validator fixtures from the benchmark plan(s) this boilerplate templates.
#
# Reads the template-for: URLs from .omni-template.yaml and pulls each plan's
# validators/ tree into .fixtures/<plan>/ (gitignored). We "pick" rather than
# vendor: the plan owns the validators and their I/O contract, so the boilerplate
# borrows them at test time and never drifts from the real contract.
#
# Plain POSIX sh + git; no pixi assumption.  Usage: scripts/pick_fixtures.sh
set -eu

ROOT="$(CDPATH= cd "$(dirname "$0")/.." && pwd)"
MANIFEST="$ROOT/omnibenchmark.yaml"   # template-for: lives here (this repo doubles as a module)
DEST="$ROOT/.fixtures"

[ -f "$MANIFEST" ] || { echo "error: $MANIFEST not found" >&2; exit 1; }

# Flat YAML list under template-for: — extract the "- <url>" entries.
urls="$(sed -n 's/^[[:space:]]*-[[:space:]]*\(https\{0,1\}:\/\/[^[:space:]]*\).*/\1/p' "$MANIFEST")"
[ -n "$urls" ] || { echo "error: no template-for: URLs in $MANIFEST" >&2; exit 1; }

rm -rf "$DEST"
mkdir -p "$DEST"

for url in $urls; do
  name="$(basename "$url" .git)"
  dst="$DEST/$name"
  echo "pick   $name (validators/)"
  # Shallow + sparse: grab only validators/, none of the plan's other content.
  git clone --depth 1 --filter=blob:none --sparse "$url" "$dst" >/dev/null 2>&1
  git -C "$dst" sparse-checkout set validators >/dev/null 2>&1
  [ -d "$dst/validators" ] || echo "warn   $name has no validators/ — skipping" >&2
done

echo "Fixtures picked into $DEST"
