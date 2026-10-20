import hashlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from rights_preflight import scan, write_manifest, read_font_names, read_xmp

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
PROJECT = os.path.join(FIX, "project")


class EmbeddedTest(unittest.TestCase):
    def test_font_name_table(self):
        names = read_font_names(Path(os.path.join(PROJECT, "fonts/Demo.ttf")).read_bytes())
        self.assertEqual(names[1], "Demo Sans")
        self.assertEqual(names[9], "Ada Demo")
        self.assertIn("Open Font License", names[13])

    def test_xmp(self):
        x = read_xmp(Path(os.path.join(PROJECT, "images/photo.png")).read_bytes())
        self.assertEqual(x["rights"], "CC BY 4.0")
        self.assertEqual(x["creator"], "Jane Photo")
        self.assertEqual(x["web_statement"], "https://creativecommons.org/licenses/by/4.0/")

    def test_garbage_is_ignored(self):
        self.assertEqual(read_font_names(b"\x00\x01"), {})
        self.assertEqual(read_xmp(b"<x:xmpmeta><broken"), {})
        self.assertEqual(read_xmp(b'<x:xmpmeta><!DOCTYPE x [<!ENTITY a "a">]></x:xmpmeta>'), {})


class ScanTest(unittest.TestCase):
    def setUp(self):
        self.files = {f["path"]: f for f in scan(PROJECT)}

    def test_lists_only_media(self):
        self.assertEqual(sorted(self.files), [
            "audio/beep.wav", "fonts/Demo.ttf", "images/nc.png", "images/photo.png", "models/cube.obj"])
        self.assertEqual(
            {p: f["type"] for p, f in self.files.items()},
            {"audio/beep.wav": "audio", "fonts/Demo.ttf": "font", "images/nc.png": "image",
             "images/photo.png": "image", "models/cube.obj": "3d"})

    def test_size_and_hash(self):
        for p, f in self.files.items():
            data = Path(os.path.join(PROJECT, p)).read_bytes()
            self.assertEqual(f["size"], len(data))
            self.assertEqual(f["sha256"], hashlib.sha256(data).hexdigest())

    def test_rights_sources_and_precedence(self):
        photo = self.files["images/photo.png"]
        self.assertEqual(photo["rights"]["license_id"], "CC-BY")
        self.assertEqual(photo["rights"]["author"], "Jane Photo")
        self.assertEqual(photo["rights"]["source"], "https://example.com/photo")
        self.assertEqual(photo["rights_from"], {"license": "embedded", "author": "embedded", "source": "sidecar"})
        font = self.files["fonts/Demo.ttf"]
        self.assertEqual(font["rights"]["license_id"], "OFL")
        self.assertEqual(font["rights"]["author"], "Ada Demo")
        self.assertEqual(self.files["audio/beep.wav"]["rights"]["license_id"], "CC0")
        self.assertEqual(self.files["audio/beep.wav"]["rights_from"]["license"], "rules")
        self.assertEqual(self.files["models/cube.obj"]["rights"]["license_id"], "ai-generated")

    def test_sidecar_beats_rules_beats_embedded(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        shutil.copy(os.path.join(PROJECT, "images/photo.png"), os.path.join(tmp, "p.png"))
        Path(os.path.join(tmp, "rights.json")).write_text(json.dumps({"rules": [{"glob": "*.png", "license": "CC0", "author": "Rule"}]}))
        Path(os.path.join(tmp, "p.png.rights.json")).write_text(json.dumps({"author": "Side"}))
        (f,) = scan(tmp)
        self.assertEqual(f["rights"]["license"], "CC0")
        self.assertEqual(f["rights"]["author"], "Side")

    def test_first_matching_rule_wins_and_subdir_glob(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        os.makedirs(os.path.join(tmp, "a/b"))
        Path(os.path.join(tmp, "a/b/x.mp3")).write_bytes(b"x")
        Path(tmp, "rights.json").write_text(json.dumps(
            {"rules": [{"glob": "a/**", "license": "MIT"}, {"glob": "*.mp3", "license": "CC0"}]}))
        (f,) = scan(tmp)
        self.assertEqual(f["rights"]["license"], "MIT")

    def test_skips_hidden_dirs(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        for d in (".git", "node_modules"):
            os.makedirs(os.path.join(tmp, d))
            Path(os.path.join(tmp, d, "x.png")).write_bytes(b"x")
        self.assertEqual(scan(tmp), [])

    def test_write_manifest(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        out = os.path.join(tmp, "rights-manifest.json")
        write_manifest(scan(PROJECT), out)
        m = json.loads(Path(out).read_text())
        self.assertEqual(m["tool"], "rights-preflight")
        self.assertEqual(len(m["files"]), 5)


if __name__ == "__main__":
    unittest.main()
