import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from rights_preflight.__main__ import main

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, "fixtures")


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = main(list(argv))
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def copy(self, name):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        dst = os.path.join(tmp, name)
        shutil.copytree(os.path.join(FIX, name), dst)
        return dst

    def test_scan_writes_manifest(self):
        d = self.copy("project")
        code, out, _ = run("scan", d)
        self.assertEqual(code, 0)
        m = json.loads(Path(d, "rights-manifest.json").read_text())
        self.assertEqual(len(m["files"]), 5)
        self.assertIn("images/photo.png", out)
        self.assertIn("5 media files", out)

    def test_scan_output_option(self):
        d = self.copy("project")
        out_path = os.path.join(d, "out.json")
        self.assertEqual(run("scan", d, "-o", out_path)[0], 0)
        self.assertTrue(os.path.exists(out_path))

    def test_check_exit_codes(self):
        self.assertEqual(run("check", os.path.join(FIX, "project"))[0], 0)
        code, out, _ = run("check", os.path.join(FIX, "project"), "--commercial")
        self.assertEqual(code, 1)
        self.assertIn("images/nc.png: non-commercial", out)
        self.assertEqual(run("check", os.path.join(FIX, "broken"))[0], 1)

    def test_check_json(self):
        code, out, _ = run("check", os.path.join(FIX, "broken"), "--json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["files"], 5)
        self.assertEqual(len(data["problems"]), 7)
        code, out, _ = run("check", os.path.join(FIX, "project"), "--json")
        self.assertEqual((code, json.loads(out)["ok"]), (0, True))

    def test_credits_writes_file(self):
        d = self.copy("project")
        self.assertEqual(run("credits", d)[0], 0)
        self.assertIn("## SIL Open Font License 1.1 (OFL)", Path(d, "CREDITS.md").read_text())

    def test_bad_inputs_exit_2(self):
        self.assertEqual(run("check", os.path.join(FIX, "nope"))[0], 2)
        d = self.copy("project")
        Path(d, "rights.json").write_text("[1, 2]")
        code, _, err = run("check", d)
        self.assertEqual(code, 2)
        self.assertIn("rights.json", err)

    def test_action_runs_the_cli(self):
        action = Path(HERE, "..", "action.yml").read_text()
        self.assertIn("using: composite", action)
        self.assertIn("python3 -m rights_preflight check", action)


if __name__ == "__main__":
    unittest.main()
