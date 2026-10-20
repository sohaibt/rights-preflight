import os
import unittest

from rights_preflight import credits_markdown, scan

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class CreditsTest(unittest.TestCase):
    def test_grouped_by_license_in_table_order(self):
        md = credits_markdown(scan(os.path.join(FIX, "project")))
        self.assertTrue(md.startswith("# Credits\n"))
        heads = [line for line in md.splitlines() if line.startswith("## ")]
        self.assertEqual(heads, [
            "## Creative Commons Zero 1.0 (CC0)",
            "## Creative Commons Attribution 4.0 (CC-BY)",
            "## Creative Commons Attribution-NonCommercial 4.0 (CC-BY-NC)",
            "## SIL Open Font License 1.1 (OFL)",
            "## AI-generated (ai-generated)",
        ])
        self.assertIn("License: https://creativecommons.org/licenses/by/4.0/", md)
        self.assertIn("- `images/photo.png` by Jane Photo, source: https://example.com/photo", md)
        self.assertIn("- `fonts/Demo.ttf` by Ada Demo, source: https://example.com/foundry", md)

    def test_unresolved_files_listed_last(self):
        md = credits_markdown(scan(os.path.join(FIX, "broken")))
        self.assertEqual([line for line in md.splitlines() if line.startswith("## ")][-1],
                         "## Unknown or missing license")
        self.assertIn("- `c.mp3` (license: WTFPL)", md)
        self.assertIn("- `a.png`", md)


if __name__ == "__main__":
    unittest.main()
