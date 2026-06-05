"""Tests for src/common/python/cli.py (the schema-driven CLI engine)."""
import contextlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src" / "common" / "python"))

import cli  # noqa: E402

EMB = ["--output_dir", "o", "--name", "n",
       "--pcas.tsv", "p", "--rawdata.clusters_truth", "t"]


class TestCli(unittest.TestCase):
    def test_embedding_happy_path(self):
        a = cli.parse_args("embedding", EMB)
        self.assertEqual(a.name, "n")
        self.assertEqual(str(a.pcas), "p")            # schema dest override
        self.assertEqual(str(a.clusters_truth), "t")
        self.assertIsInstance(a.pcas, Path)           # type: path

    def test_default_dest_maps_dots_and_dashes(self):
        self.assertEqual(cli._default_dest("--a.b-c"), "a_b_c")

    def test_unknown_flag_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.parse_args("embedding", EMB + ["--bogus", "x"])

    def test_missing_required_rejected(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.parse_args("embedding", ["--name", "n"])

    def test_auto_pick_single_schema(self):
        a = cli.parse_args(None, EMB)
        self.assertEqual(a.name, "n")

    def test_type_coercion(self):
        schema = {"interface": "t", "args": [
            {"flag": "--i", "type": "integer"},
            {"flag": "--f", "type": "number"},
            {"flag": "--s", "type": "string"},
            {"flag": "--p", "type": "path"},
        ]}
        a = cli.build_parser(schema).parse_args(
            ["--i", "3", "--f", "1.5", "--s", "x", "--p", "y"])
        self.assertEqual(a.i, 3)
        self.assertEqual(a.f, 1.5)
        self.assertEqual(a.s, "x")
        self.assertIsInstance(a.p, Path)

    def test_unknown_interface_errors(self):
        with self.assertRaises(SystemExit):
            cli.load_interface("does-not-exist")


if __name__ == "__main__":
    unittest.main()
