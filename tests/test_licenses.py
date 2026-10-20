import unittest

from rights_preflight import LICENSES, resolve_license


class LicenseTableTest(unittest.TestCase):
    def test_table_has_v1_ids(self):
        self.assertEqual(
            list(LICENSES),
            ["CC0", "CC-BY", "CC-BY-SA", "CC-BY-NC", "OFL", "Apache-2.0", "MIT",
             "public-domain", "licensed-proprietary", "ai-generated"],
        )
        self.assertTrue(LICENSES["CC-BY"]["attribution"])
        self.assertTrue(LICENSES["CC-BY"]["commercial"])
        self.assertFalse(LICENSES["CC-BY-NC"]["commercial"])
        self.assertFalse(LICENSES["CC0"]["attribution"])

    def test_resolve_ids_and_aliases(self):
        cases = {
            "CC0": "CC0", "cc0-1.0": "CC0", "CC BY 4.0": "CC-BY", "cc-by-sa-4.0": "CC-BY-SA",
            "OFL-1.1": "OFL", "Apache 2.0": "Apache-2.0", "mit": "MIT",
            "Public Domain": "public-domain", "licensed-proprietary": "licensed-proprietary",
            "AI-Generated": "ai-generated",
        }
        for raw, want in cases.items():
            self.assertEqual(resolve_license(raw), want, raw)

    def test_resolve_from_free_text_and_urls(self):
        cases = {
            "This Font Software is licensed under the SIL Open Font License, Version 1.1.": "OFL",
            "https://openfontlicense.org": "OFL",
            "https://creativecommons.org/licenses/by-nc-sa/4.0/": "CC-BY-NC",
            "https://creativecommons.org/licenses/by/4.0/": "CC-BY",
            "http://creativecommons.org/publicdomain/zero/1.0/": "CC0",
            "Licensed under the Apache License, Version 2.0": "Apache-2.0",
        }
        for raw, want in cases.items():
            self.assertEqual(resolve_license(raw), want, raw)

    def test_unknown(self):
        self.assertIsNone(resolve_license("WTFPL"))
        self.assertIsNone(resolve_license("https://creativecommons.org/licenses/by-nd/4.0/"))
        self.assertIsNone(resolve_license("Copyright 2026 Foo. All rights reserved."))
        self.assertIsNone(resolve_license(""))


if __name__ == "__main__":
    unittest.main()
