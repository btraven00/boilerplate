"""Tests for scripts/check_interfaces.py (implements <-> schema consistency)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import check_interfaces as ci  # noqa: E402

MANIFEST = """\
entrypoints:
  default: run.sh
template-for:
  - name: split-stages
    url: https://example.com/plan
    plan: benchmark.yaml
implements:
  - {impl}
"""


def make_root(impl, schema):
    d = Path(tempfile.mkdtemp())
    (d / "omnibenchmark.yaml").write_text(MANIFEST.format(impl=impl))
    sdir = d / "src" / "common" / "schema"
    sdir.mkdir(parents=True)
    if schema is not None:
        (sdir / "embedding.json").write_text(json.dumps(schema))
    return d


GOOD = {"interface": "embedding", "version": "0.1.0", "args": []}


class TestCheckInterfaces(unittest.TestCase):
    def test_consistent(self):
        self.assertEqual(ci.check(make_root("split-stages/embedding@0.1.0", GOOD)), [])

    def test_version_mismatch(self):
        errs = ci.check(make_root("split-stages/embedding@0.2.0", GOOD))
        self.assertTrue(any("version" in e for e in errs))

    def test_unknown_label(self):
        errs = ci.check(make_root("other/embedding@0.1.0", GOOD))
        self.assertTrue(any("not in template-for" in e for e in errs))

    def test_missing_schema(self):
        errs = ci.check(make_root("split-stages/embedding@0.1.0", None))
        self.assertTrue(any("missing schema" in e for e in errs))

    def test_malformed(self):
        errs = ci.check(make_root("not-a-valid-ref", GOOD))
        self.assertTrue(any("want <label>" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
