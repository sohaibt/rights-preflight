import os
import unittest

from rights_preflight import check, scan

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def codes(problems):
    return sorted((p["path"], p["code"]) for p in problems)


class CheckTest(unittest.TestCase):
    def test_clean_project_passes(self):
        self.assertEqual(check(scan(os.path.join(FIX, "project"))), [])

    def test_commercial_flags_nc(self):
        self.assertEqual(codes(check(scan(os.path.join(FIX, "project")), commercial=True)),
                         [("images/nc.png", "non-commercial")])

    def test_broken_project(self):
        self.assertEqual(codes(check(scan(os.path.join(FIX, "broken")))), [
            ("a.png", "missing-license"),
            ("b.png", "missing-author"),
            ("b.png", "missing-source"),
            ("c.mp3", "unknown-license"),
            ("d.jpg", "bad-sidecar"),
            ("d.jpg", "missing-license"),
            ("e.png", "unknown-license"),
        ])

    def test_messages_are_readable(self):
        problems = {(p["path"], p["code"]): p["message"] for p in check(scan(os.path.join(FIX, "broken")))}
        self.assertIn("WTFPL", problems[("c.mp3", "unknown-license")])
        self.assertIn("CC-BY", problems[("b.png", "missing-author")])


if __name__ == "__main__":
    unittest.main()
