#!/usr/bin/env python3
"""Embed files verbatim into Markdown to keep snippets from drifting.

A Markdown file marks an embed with a pair of HTML comments:

    <!-- embed:actions/validate-module/workflow.yml -->
    ```yaml
    ...this block is regenerated from the file...
    ```
    <!-- /embed -->

Running this script rewrites every embed block with the current contents of
the referenced file (path is repo-root-relative). The fence language is
inferred from the file extension, or set explicitly with `lang=`:

    <!-- embed:actions/install.sh lang=console -->

Usage:
    embed_snippets.py            # rewrite embeds in place
    embed_snippets.py --check    # exit non-zero if any embed is stale (CI)

This tool lives only in the boilerplate repo; it is never copied into modules.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Markdown files to scan, repo-root-relative. Keep this explicit so the tool's
# blast radius is obvious and it never wanders into .pixi/ or generated output.
TARGETS = [
    "docs/ci.md",
    "docs/cli.md",
]

EXT_LANG = {
    ".yml": "yaml",
    ".yaml": "yaml",
    ".sh": "sh",
    ".py": "python",
    ".toml": "toml",
    ".md": "markdown",
    ".json": "json",
}

# <!-- embed:PATH [lang=LANG] --> <fence> BODY <fence> <!-- /embed -->
BLOCK = re.compile(
    r"(?P<open><!--\s*embed:(?P<path>\S+?)(?:\s+lang=(?P<lang>\S+?))?\s*-->\n)"
    r"```[^\n]*\n.*?```\n"
    r"(?P<close><!--\s*/embed\s*-->)",
    re.DOTALL,
)


def render(match: re.Match) -> str:
    rel = match.group("path")
    src = ROOT / rel
    if not src.is_file():
        raise SystemExit(f"error: embed source not found: {rel}")
    lang = match.group("lang") or EXT_LANG.get(src.suffix, "")
    body = src.read_text().rstrip("\n")
    fence = f"```{lang}\n{body}\n```\n"
    return f"{match.group('open')}{fence}{match.group('close')}"


def main() -> int:
    check = "--check" in sys.argv[1:]
    stale: list[str] = []
    for rel in TARGETS:
        md = ROOT / rel
        if not md.is_file():
            raise SystemExit(f"error: target Markdown not found: {rel}")
        old = md.read_text()
        new = BLOCK.sub(render, old)
        if new != old:
            if check:
                stale.append(rel)
            else:
                md.write_text(new)
                print(f"updated {rel}")
    if check and stale:
        print("stale embeds (run `pixi run docs`): " + ", ".join(stale))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
