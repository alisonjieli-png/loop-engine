"""Compare the website this checkout serves with its site map, one rule at a time.

Kind: development check over packaged files. The rules, their known-wrong cases and their mutant controls
live in `tools/test_website_site_map.py`; this file applies the same rules to the served website itself.

It is kept out of the continuous integration list until the pages that the target site map of September
23, 2026 restores are merged, because on 243a8811 (Fly release 20) five rules refuse the served website:
the pages are missing. That run is saved as
`artifacts/website-audit-2026-09-23/site-map-check-on-main-243a8811.txt`, and
`docs/verification/HANDOFF-SITE-STANDARDS-2026-09-23.md` names the line that adds this check to the list.

    PYTHONPATH=src:tools python -m unittest tools/check_website_site_map.py
"""
from __future__ import annotations

import unittest

from test_website_site_map import KNOWN_WRONG_OUTPUT, RULES, report, served_site


class ServedWebsite(unittest.TestCase):
    """The website this checkout serves, compared with its site map, one rule at a time."""

    @classmethod
    def setUpClass(cls):
        cls.site = served_site()

    def check_served(self, name):
        problems = RULES[name](self.site)
        if problems:
            self.fail(f"{name} refuses the served website ({KNOWN_WRONG_OUTPUT} holds the run on 243a8811):\n"
                      + report({name: problems}))


for _name in RULES:
    setattr(ServedWebsite, f"test_the_served_website_{_name}", lambda self, name=_name: self.check_served(name))



if __name__ == "__main__":
    unittest.main()
