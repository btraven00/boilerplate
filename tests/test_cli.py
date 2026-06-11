"""Tests for src/common/python/cli.py (the shared CLI helpers)."""
import argparse
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "common" / "python"))

import cli  # noqa: E402

# Example schemas stand in for the set a real module vendors from the plan's
# schema/ — see tests/fixtures/schema/README.md.
SCHEMA = ROOT / "tests" / "fixtures" / "schema"

# An entrypoint-style parser: shared base + stage args, then the author's own.
EMB = ["--output_dir", "o", "--name", "n",
       "--pcas.tsv", "p", "--rawdata.clusters_truth", "t"]


def _embedding_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    cli.add_base_args(p, schema_dir=SCHEMA)
    cli.add_stage_args(p, "embedding", schema_dir=SCHEMA)
    return p


class TestCli(unittest.TestCase):
    def test_base_then_stage_happy_path(self):
        a = _embedding_parser().parse_args(EMB)
        self.assertEqual(str(a.output_dir), "o")      # from _base.json
        self.assertEqual(a.name, "n")                 # from _base.json
        self.assertEqual(str(a.pcas), "p")            # stage schema dest override
        self.assertEqual(str(a.clusters_truth), "t")
        self.assertIsInstance(a.pcas, Path)           # type: path
        self.assertIsInstance(a.output_dir, Path)

    def test_default_dest_maps_dots_and_dashes(self):
        self.assertEqual(cli._default_dest("--a.b-c"), "a_b_c")

    def test_unknown_flag_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            _embedding_parser().parse_args(EMB + ["--bogus", "x"])

    def test_missing_required_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            _embedding_parser().parse_args(["--name", "n"])

    def test_unknown_interface_errors(self):
        with self.assertRaises(SystemExit):
            cli.add_stage_args(argparse.ArgumentParser(), "does-not-exist", schema_dir=SCHEMA)

    def test_missing_schema_dir_errors(self):
        with self.assertRaises(SystemExit):
            cli.add_base_args(argparse.ArgumentParser(), schema_dir=Path("no/such/dir"))

    def test_common_version(self):
        v = cli.common_version()
        self.assertEqual(v, (ROOT / "src" / "common" / "VERSION").read_text().strip())
        self.assertRegex(v, r"^\d+\.\d+\.\d+")

    # ── helpers add args to the author's own parser ───────────────────────────
    def test_add_base_args_adds_universal(self):
        p = argparse.ArgumentParser()
        cli.add_base_args(p, schema_dir=SCHEMA)
        a = p.parse_args(["--output_dir", "o", "--name", "n"])
        self.assertEqual(str(a.output_dir), "o")
        self.assertEqual(a.name, "n")

    def test_author_method_params_coexist(self):
        # Shared base + stage from schema, then the author's own plain argparse.
        p = _embedding_parser()
        p.add_argument("--solver", choices=["arpack", "randomized"], required=True)
        p.add_argument("--n_components", type=int, required=True)
        a = p.parse_args(EMB + ["--solver", "arpack", "--n_components", "50"])
        self.assertEqual(a.solver, "arpack")
        self.assertEqual(a.n_components, 50)

    # ── type coercion + choices on schema-declared args ───────────────────────
    def test_type_coercion(self):
        # add_stage_args coerces per the schema's declared types.
        p = argparse.ArgumentParser()
        cli._add_args(p, [
            {"flag": "--i", "type": "integer"},
            {"flag": "--f", "type": "number"},
            {"flag": "--s", "type": "string"},
            {"flag": "--p", "type": "path"},
        ])
        a = p.parse_args(["--i", "3", "--f", "1.5", "--s", "x", "--p", "y"])
        self.assertEqual(a.i, 3)
        self.assertEqual(a.f, 1.5)
        self.assertEqual(a.s, "x")
        self.assertIsInstance(a.p, Path)

    def test_choices_accepts_valid(self):
        p = argparse.ArgumentParser()
        cli._add_args(p, [
            {"flag": "--solver", "type": "string", "choices": ["arpack", "randomized"]}])
        self.assertEqual(p.parse_args(["--solver", "arpack"]).solver, "arpack")

    def test_choices_rejects_invalid(self):
        p = argparse.ArgumentParser()
        cli._add_args(p, [
            {"flag": "--solver", "type": "string", "choices": ["arpack", "randomized"]}])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            p.parse_args(["--solver", "BOGUS"])


if __name__ == "__main__":
    unittest.main()
