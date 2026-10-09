"""Checks for the licence rule of the licensed import: per file, per package, and what travels with a copy.

```text
Known-wrong cases, each refused a copy
├── a licence outside the owner's allowlist (GPL-3.0, CC-BY-SA-4.0): an idea record, never a copy
├── a licence named only in a file's metadata, with no licence text above it: an idea record
├── metadata that names another licence than the licence file: an idea record
├── a script whose SPDX header disagrees with the governing licence: the whole package is an idea
├── a repository licence GitHub does not assert: an idea record
└── a licence that forbids derivative works: a refusal, and nothing is kept
```

Beside them: all nine allowlisted licences are copied, a nested licence
file overrides the repository licence, the governing texts and a generated
attribution travel with a copy, and a removed-guard control shows that a
policy accepting GPL-3.0 would copy the GPL package the real policy refuses.
No network, process or model is used.
"""
from __future__ import annotations

import unittest
import hashlib
from pathlib import Path
import re

import test_licensed_import_support as support
from loop_engine.core.library_ingestion.licences import LicencePolicy, licence_words, match_licence, load_templates
from loop_engine.core.library_ingestion.provenance import OUTLINE_ONLY, REFUSED, VERBATIM

from licensed_import.licensing import (
    POLICY, attribution_text, carried_placements, decide_package, own_metadata_licence, root_licence_path,
    spdx_headers)
from licensed_import.records import ALLOWED_LICENCES


def _decide(members, licences, *, primary="skills/demo/SKILL.md", github="MIT", policy=POLICY):
    members = {path: (value.encode() if isinstance(value, str) else value) for path, value in members.items()}
    licences = {path: value.encode() for path, value in licences.items()}
    return decide_package(members, primary, licences, github_spdx=github, policy=policy)


class LicenceRuleChecks(unittest.TestCase):
    def test_pinned_real_apache_text_reproduces_its_template_words(self):
        root = Path(__file__).with_name("fixtures") / "licence-texts"
        canonical = (root / "apache-2.0-canonical.txt").read_bytes()
        google = (root / "google-api-client-LICENSE.txt").read_bytes()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), load_templates()["Apache-2.0"].source_sha256)
        self.assertEqual(hashlib.sha256(google).hexdigest(),
                         "c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4")
        canonical_text = re.sub(r"\A---\n.*?\n---\n", "", canonical.decode(), flags=re.S)
        self.assertEqual(canonical_text.split(), google.decode().split())
        self.assertEqual(licence_words(canonical.decode()), load_templates()["Apache-2.0"].words)
        for raw in (canonical, google):
            self.assertEqual(match_licence(raw.decode()).spdx, "Apache-2.0")
            self.assertEqual(_decide({"skills/demo/SKILL.md": support.skill("demo")},
                                    {"LICENSE": raw.decode()}, github="Apache-2.0").decision, VERBATIM)

    def test_real_apache_with_altered_obligations_remains_refused(self):
        text = (Path(__file__).with_name("fixtures") / "licence-texts/google-api-client-LICENSE.txt").read_text()
        self.assertIn("perpetual", text)
        for wrong in (text.replace("perpetual", "temporary", 1),
                      text + "\nRedistribution is permitted for noncommercial evaluation only.\n",
                      text + "\nCopyright 2026 Example. Commercial redistribution is prohibited.\n"):
            self.assertIsNone(match_licence(wrong).spdx)
            self.assertNotEqual(_decide({"skills/demo/SKILL.md": support.skill("demo")},
                                       {"LICENSE": wrong}, github="Apache-2.0").decision, VERBATIM)

    def test_an_apache_copy_that_numbers_its_clauses_is_recognized_and_a_holder_notice_stays_a_notice(self):
        # Babylon.js's license.md numbers clause 4(c) "3." instead of "(c)": until October 9, 2026 the normalizer read
        # the canonical "(c) You must retain" as a copyright notice, so the template lacked "retain" and this copy
        # was refused for adding it.
        text = (Path(__file__).with_name("fixtures") / "licence-texts/google-api-client-LICENSE.txt").read_text()
        numbered = text
        for letter, number in (("(a) You must give", "1. You must give"), ("(b) You must cause", "2. You must cause"),
                               ("(c) You must retain", "3. You must retain"), ("(d) If the Work", "4. If the Work")):
            self.assertIn(letter, numbered)
            numbered = numbered.replace(letter, number, 1)
        self.assertEqual(match_licence(numbered).spdx, "Apache-2.0")
        self.assertEqual(_decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": numbered},
                                 github="Apache-2.0").decision, VERBATIM)
        # Known wrong: a holder notice written with the mark alone is still set aside as a notice, and a clause that
        # adds an obligation is still refused.
        self.assertEqual(match_licence(text + "\n(c) 2026 Example Corp\n").spdx, "Apache-2.0")
        self.assertIsNone(match_licence(numbered.replace("3. You must retain", "3. You must pay a monthly "
                                                                                 "subscription and retain")).spdx)

    def test_wrapped_copyright_disclaimer_is_not_a_holder_notice(self):
        # This wrapping occurs in python-validators/validators' MIT licence.
        text = support.MIT.replace("COPYRIGHT HOLDERS", "\nCOPYRIGHT HOLDERS")
        self.assertEqual(licence_words(text), licence_words(support.MIT))
        self.assertEqual(match_licence(text).spdx, "MIT")
        result = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": text})
        self.assertEqual(result.decision, VERBATIM)

    def test_a_copyright_holder_restriction_is_not_discarded_as_a_notice(self):
        text = support.MIT + "\nCopyright holders prohibit commercial redistribution.\n"
        self.assertIsNone(match_licence(text).spdx)
        result = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": text})
        self.assertNotEqual(result.decision, VERBATIM)

    def test_the_policy_is_exactly_the_owners_allowlist(self):
        self.assertEqual(POLICY.accepted, ALLOWED_LICENCES)
        self.assertEqual(set(ALLOWED_LICENCES), {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "0BSD",
                                                 "CC0-1.0", "CC-BY-4.0", "Unlicense"})

    def test_every_allowlisted_licence_is_copied_with_its_text(self):
        texts = {"MIT": support.MIT, **{name: support.licence_text(name) for name in ALLOWED_LICENCES if name != "MIT"}}
        for name, text in texts.items():
            result = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": text}, github=name)
            self.assertEqual(result.decision, VERBATIM, (name, result.reason))
            self.assertEqual(result.spdx_expression, name)
            self.assertEqual(result.carried, ("LICENSE",))

    def test_a_licence_outside_the_allowlist_leaves_an_idea_record(self):
        for name, text in (("GPL-3.0", support.GPL), ("CC-BY-SA-4.0", support.SHARE_ALIKE)):
            result = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": text}, github=name)
            self.assertEqual((result.decision, result.reason), (OUTLINE_ONLY, "licence_not_on_accepted_list"), name)
            self.assertEqual(result.carried, ())

    def test_removed_guard_a_policy_that_accepts_gpl_would_copy_it(self):
        mutant = LicencePolicy(accepted=ALLOWED_LICENCES + ("GPL-3.0",))
        copied = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": support.GPL}, github="GPL-3.0",
                         policy=mutant)
        refused = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": support.GPL}, github="GPL-3.0")
        self.assertEqual(copied.decision, VERBATIM)
        self.assertEqual(refused.decision, OUTLINE_ONLY)

    def test_a_licence_named_only_in_metadata_leaves_an_idea_record(self):
        front = support.skill("demo").decode().replace("description:", "license: MIT\ndescription:")
        result = _decide({"skills/demo/SKILL.md": front}, {}, github=None)
        self.assertEqual((result.decision, result.reason), (OUTLINE_ONLY, "no_licence_file"))

    def test_metadata_that_names_another_licence_leaves_an_idea_record(self):
        front = support.skill("demo").decode().replace("description:", "license: Apache-2.0\ndescription:")
        result = _decide({"skills/demo/SKILL.md": front}, {"LICENSE": support.MIT})
        self.assertEqual((result.decision, result.reason), (OUTLINE_ONLY, "licence_notices_disagree"))

    def test_a_nested_licence_file_overrides_the_repository_licence(self):
        result = _decide({"skills/demo/SKILL.md": support.skill("demo")},
                         {"LICENSE": support.MIT, "skills/demo/LICENSE.txt": support.APACHE})
        self.assertEqual((result.decision, result.spdx_expression), (VERBATIM, "Apache-2.0"))
        self.assertEqual(result.carried, ("skills/demo/LICENSE.txt",))

    def test_one_file_that_may_not_be_copied_makes_the_whole_package_an_idea(self):
        script = b"# SPDX-License-Identifier: GPL-3.0\nprint('checked')\n"
        result = _decide({"skills/demo/SKILL.md": support.skill("demo"), "skills/demo/scripts/check.py": script},
                         {"LICENSE": support.MIT})
        self.assertEqual(result.decision, OUTLINE_ONLY)
        self.assertEqual(result.per_file["skills/demo/SKILL.md"]["decision"], VERBATIM)
        self.assertEqual(result.per_file["skills/demo/scripts/check.py"]["decision"], OUTLINE_ONLY)

    def test_a_repository_licence_github_does_not_assert_leaves_an_idea(self):
        result = _decide({"skills/demo/SKILL.md": support.skill("demo")}, {"LICENSE": support.MIT}, github=None)
        self.assertEqual((result.decision, result.reason), (OUTLINE_ONLY, "repository_licence_not_asserted"))

    def test_a_licence_that_forbids_derivative_works_is_refused(self):
        result = _decide({"skills/demo/SKILL.md": support.skill("demo")},
                         {"LICENSE": support.MIT, "skills/demo/LICENSE.txt": support.PROPRIETARY})
        self.assertEqual(result.decision, REFUSED)

    def test_a_primary_file_named_like_a_licence_is_still_decided(self):
        members = {".claude/commands/license-check.md": "Check every dependency's licence before a release.\n"}
        result = _decide(members, {"LICENSE": support.MIT}, primary=".claude/commands/license-check.md")
        self.assertEqual((result.decision, result.spdx_expression), (VERBATIM, "MIT"))
        self.assertIn(".claude/commands/license-check.md", result.per_file)

    def test_manifest_metadata_and_headers_are_read(self):
        self.assertEqual(own_metadata_licence("plugins/x/.claude-plugin/plugin.json", b'{"license": "MIT"}'), "MIT")
        self.assertIsNone(own_metadata_licence("assets/data.json", b'{"license": "GPL-3.0"}'))
        self.assertEqual(spdx_headers(b"#!/bin/sh\n# SPDX-License-Identifier: Apache-2.0\n"), ("Apache-2.0",))
        self.assertEqual(root_licence_path(["docs/LICENSE", "LICENSE.md", "LICENSE"]), "LICENSE")

    def test_carried_texts_never_overwrite_a_member_and_attribution_names_every_file(self):
        placed = carried_placements(["LICENSE", "other/LICENSE"], ["LICENSE", "SKILL.md"])
        self.assertEqual(placed, {"LICENSE": "UPSTREAM-LICENSE", "other/LICENSE": "UPSTREAM-2-LICENSE"})
        text = attribution_text(repository="acme/tools", commit="a" * 40, spdx="MIT",
                                rows=[("SKILL.md", "skills/demo/SKILL.md", "b" * 64)], licence_names=["LICENSE"],
                                imported_on="2026-09-24").decode()
        for fragment in ("github.com/acme/tools", "a" * 40, "MIT", "skills/demo/SKILL.md", "b" * 64, "not reviewed"):
            self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
