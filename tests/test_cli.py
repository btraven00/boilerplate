"""Tests for src/common/python/cli.py (the schema-driven CLI engine)."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
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
        d = self._schema_dir({
            "only.json": {"interface": "only", "version": "0", "args": [
                {"flag": "--x", "type": "string"}]},
        })
        self.assertEqual(cli.load_interface(None, d)["interface"], "only")

    def test_auto_pick_ambiguous_raises(self):
        d = self._schema_dir({
            "a.json": {"interface": "a", "version": "0", "args": []},
            "b.json": {"interface": "b", "version": "0", "args": []},
        })
        with self.assertRaises(SystemExit):
            cli.load_interface(None, d)

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

    def test_common_version(self):
        v = cli.common_version()
        self.assertEqual(v, (ROOT / "src" / "common" / "VERSION").read_text().strip())
        self.assertRegex(v, r"^\d+\.\d+\.\d+")

    # ── choices ──────────────────────────────────────────────────────────────
    SOLVER = {"interface": "t", "args": [
        {"flag": "--solver", "type": "string", "choices": ["arpack", "randomized"]}]}

    def test_choices_accepts_valid(self):
        a = cli.build_parser(self.SOLVER).parse_args(["--solver", "arpack"])
        self.assertEqual(a.solver, "arpack")

    def test_choices_rejects_invalid(self):
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.build_parser(self.SOLVER).parse_args(["--solver", "BOGUS"])

    # ── layering: _base -> <interface> -> <interface>.extends ─────────────────
    def _schema_dir(self, files: dict) -> Path:
        d = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        for name, spec in files.items():
            (d / name).write_text(json.dumps(spec))
        return d

    def test_layering_merges_base_stage_extends(self):
        d = self._schema_dir({
            "_base.json": {"interface": "_base", "args": [
                {"flag": "--output_dir", "type": "path"},
                {"flag": "--name", "type": "string"}]},
            "pca.json": {"interface": "pca", "version": "0.1.0", "args": [
                {"flag": "--normalized_selected.h5", "dest": "input_h5", "type": "path"}]},
            "pca.extends.json": {"interface": "pca", "args": [
                {"flag": "--solver", "type": "string", "choices": ["arpack", "randomized"]},
                {"flag": "--n_components", "type": "integer"}]},
        })
        spec = cli.load_interface("pca", d)
        self.assertEqual([a["flag"] for a in spec["args"]],
                         ["--output_dir", "--name", "--normalized_selected.h5",
                          "--solver", "--n_components"])
        a = cli.build_parser(spec).parse_args(
            ["--output_dir", "o", "--name", "n", "--normalized_selected.h5", "x.h5",
             "--solver", "arpack", "--n_components", "50"])
        self.assertEqual(str(a.input_h5), "x.h5")   # stage dest override survives merge
        self.assertEqual(a.n_components, 50)         # extends arg, integer-coerced
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            cli.build_parser(spec).parse_args(
                ["--output_dir", "o", "--name", "n", "--normalized_selected.h5", "x.h5",
                 "--solver", "BOGUS", "--n_components", "50"])  # choices from extends

    def test_extends_overrides_by_flag(self):
        d = self._schema_dir({
            "pca.json": {"interface": "pca", "version": "0.1.0", "args": [
                {"flag": "--solver", "type": "string", "help": "base"}]},
            "pca.extends.json": {"interface": "pca", "args": [
                {"flag": "--solver", "type": "string", "choices": ["arpack"], "help": "over"}]},
        })
        spec = cli.load_interface("pca", d)
        self.assertEqual(len(spec["args"]), 1)               # same flag, not duplicated
        self.assertEqual(spec["args"][0]["help"], "over")    # later layer wins
        self.assertEqual(spec["args"][0]["choices"], ["arpack"])

    def test_auto_pick_skips_base_and_extends(self):
        d = self._schema_dir({
            "_base.json": {"interface": "_base", "args": [{"flag": "--name", "type": "string"}]},
            "pca.json": {"interface": "pca", "version": "0.1.0", "args": [
                {"flag": "--x", "type": "string"}]},
            "pca.extends.json": {"interface": "pca", "args": [{"flag": "--y", "type": "string"}]},
        })
        self.assertEqual(cli.load_interface(None, d)["interface"], "pca")

    def test_base_provides_universal_args(self):
        # embedding.json no longer lists --output_dir/--name; _base supplies them,
        # so the effective CLI is unchanged (backward-compatible).
        a = cli.parse_args("embedding", EMB)
        self.assertEqual(str(a.output_dir), "o")
        self.assertEqual(a.name, "n")


if __name__ == "__main__":
    unittest.main()
