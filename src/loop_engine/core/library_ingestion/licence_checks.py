"""Known-wrong checks for the licence gate of outside material.

Verbatim import needs an accepted licence proven by the licence file itself.
These checks require: no licence file, an unrecognized text and a recognized
licence the policy does not list all refuse verbatim import; a licence that
forbids derivative works refuses an outline as well; a nested licence file
overrides the repository licence; the licence interface and the text must
agree for a repository licence; a file-level notice that disagrees blocks a
verbatim copy; an added restriction makes a permissive text unrecognized;
and a share-alike text is never taken for the plain attribution licence.
"""
from __future__ import annotations

from .licences import (
    LicenceFile, LicencePolicy, decide_licence, governing_licence_path, licence_words,
    load_templates, match_licence, match_words, prohibits_recreation)
from .provenance import OUTLINE_ONLY, REFUSED, VERBATIM, read_licence_evidence
from .record_rules import LibraryRecordError, bytes_digest

MIT_FIXTURE = """MIT License

Copyright (c) 2026 Example Author

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
#: The same text with one added condition. A permissive name on a restricted text
#: is the case a badge or a first line alone would get wrong.
RESTRICTED_MIT_FIXTURE = MIT_FIXTURE + """
Additional condition: the Software may not be used in any product that is sold,
hosted or offered to customers without written permission from the author, and
redistribution through any catalogue or marketplace is forbidden.
"""
#: Written for this check in the shape of a source-available skill licence.
PROPRIETARY_FIXTURE = """Copyright 2026 Example Company. All rights reserved.

Use of these materials is governed by your agreement with Example Company.
Notwithstanding anything in the agreement, users may not:
- Extract these materials or retain copies outside the service
- Reproduce or copy these materials
- Create derivative works based on these materials
- Distribute, sublicense or transfer these materials to any third party
"""


#: Written for this check in the shape of a notice that ties the reader to a provider's own terms.
EXTERNAL_TERMS_FIXTURE = """Use of these example skills and related files ("Materials") is governed by the
Example Developer Terms (available at https://example.invalid/legal/terms). By accessing, downloading,
or using these Materials, including through automated systems or AI agents, you agree to the Example
Developer Terms.
"""


def _file(path: str, text: str, github: "str | None" = None) -> LicenceFile:
    return LicenceFile(path, bytes_digest(text.encode()), text, github)


def _decide(item: str, files, **options) -> dict:
    return read_licence_evidence(decide_licence(item, {row.path: row for row in files}, **options))


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:300]})

    templates = load_templates()
    own = {spdx: match_words(template.words, templates).spdx for spdx, template in templates.items()}
    mit = match_licence(MIT_FIXTURE)
    check("every_stored_template_is_recognized_by_its_own_words_and_mit_text_by_its_words",
          all(spdx == found for spdx, found in own.items()) and mit.spdx == "MIT"
          and mit.similarity >= 0.98, {"mit": mit.similarity, "own": own})

    restricted = match_licence(RESTRICTED_MIT_FIXTURE)
    check("a_permissive_text_with_an_added_restriction_is_not_recognized",
          restricted.spdx is None and restricted.best == "MIT", restricted)

    share_alike_words = templates["CC-BY-4.0"].words | {"sharealike"}
    share = match_words(share_alike_words, templates)
    check("a_share_alike_text_is_never_taken_for_the_plain_attribution_licence",
          share.spdx != "CC-BY-4.0", share)

    item = "skills/example/SKILL.md"
    no_file = _decide(item, [])
    unknown = _decide(item, [_file("LICENSE", "Do what you like with it, but ask me first.", None)])
    gpl_words = sorted(templates["GPL-3.0"].words)
    gpl = _decide(item, [_file("LICENSE", " ".join(gpl_words), "GPL-3.0")])
    accepted = _decide(item, [_file("LICENSE", MIT_FIXTURE, "MIT")], root_path="LICENSE")
    check("an_item_without_an_accepted_licence_is_never_imported_verbatim",
          [row["decision"] for row in (no_file, unknown, gpl)] == [OUTLINE_ONLY] * 3
          and no_file["spdx_expression"] == "NONE" and gpl["reason"] == "licence_not_on_accepted_list"
          and accepted["decision"] == VERBATIM and accepted["spdx_expression"] == "MIT",
          [no_file["reason"], unknown["reason"], gpl["reason"], accepted["reason"]])

    external = _decide(item, [_file("skills/example/LICENSE.txt", EXTERNAL_TERMS_FIXTURE)])
    plain_notice = _decide(item, [_file("skills/example/LICENSE.txt", "Share this freely with your team.\n")])
    bound_notice = _decide(item, [_file("LICENSE", MIT_FIXTURE, "MIT")], root_path="LICENSE",
                           frontmatter_licence="By using this skill you agree to the Example Terms of Service")
    check("a_licence_that_binds_the_reader_to_outside_terms_leaves_nothing",
          external["decision"] == REFUSED and external["reason"] == "licence_binds_to_outside_terms"
          and bound_notice["decision"] == REFUSED
          and bound_notice["reason"] == "file_level_notice_binds_to_outside_terms"
          and plain_notice["decision"] == OUTLINE_ONLY,
          [external["reason"], bound_notice["reason"], plain_notice["reason"]])

    proprietary = _decide(item, [_file("skills/example/LICENSE.txt", PROPRIETARY_FIXTURE)])
    check("proprietary_text_is_never_imported_or_recreated",
          proprietary["decision"] == REFUSED and prohibits_recreation(PROPRIETARY_FIXTURE)
          and not prohibits_recreation(MIT_FIXTURE), proprietary["reason"])

    # A recognized licence whose own terms use the prohibition words must still
    # be read by its template: this Apache sentence says "shall not ... derivative works".
    apache_words = " ".join(sorted(templates["Apache-2.0"].words))
    apache_like = apache_words + (".\nFor the purposes of this License, Derivative Works shall not include "
                                  "works that remain separable from, or merely link (or bind by name) to "
                                  "the interfaces of, the Work and Derivative Works thereof.\n")
    apache = _decide(item, [_file("skills/example/LICENSE.txt", apache_like)])
    check("a_recognized_licence_is_read_by_its_template_not_by_the_prohibition_rule",
          prohibits_recreation(apache_like) and apache["decision"] == VERBATIM
          and apache["spdx_expression"] == "Apache-2.0", apache["reason"])

    nested_refused = _decide(item, [_file("LICENSE", MIT_FIXTURE, "MIT"),
                                    _file("skills/example/LICENSE.txt", PROPRIETARY_FIXTURE)],
                             root_path="LICENSE")
    nested_allowed = _decide(item, [_file("skills/example/LICENSE.txt", MIT_FIXTURE)])
    check("a_nested_licence_file_overrides_the_repository_licence",
          nested_refused["decision"] == REFUSED
          and nested_allowed["decision"] == VERBATIM
          and nested_allowed["governing_file"]["path"] == "skills/example/LICENSE.txt",
          [nested_refused["reason"], nested_allowed["reason"]])

    disagree = _decide(item, [_file("LICENSE", MIT_FIXTURE, "Apache-2.0")], root_path="LICENSE")
    unasserted = _decide(item, [_file("LICENSE", MIT_FIXTURE, "NOASSERTION")], root_path="LICENSE")
    check("a_repository_licence_needs_the_licence_interface_and_the_text_to_agree",
          disagree["decision"] == OUTLINE_ONLY and unasserted["decision"] == OUTLINE_ONLY
          and disagree["reason"] == "repository_licence_signals_disagree"
          and unasserted["reason"] == "repository_licence_not_asserted",
          [disagree["reason"], unasserted["reason"]])

    root = [_file("LICENSE", MIT_FIXTURE, "MIT")]
    conflicting = _decide(item, root, root_path="LICENSE", frontmatter_licence="Apache-2.0")
    matching = _decide(item, root, root_path="LICENSE", frontmatter_licence="MIT License")
    pointing = _decide(item, [_file("skills/example/LICENSE.txt", MIT_FIXTURE)],
                       frontmatter_licence="Complete terms in LICENSE.txt")
    free_text = _decide(item, root, root_path="LICENSE", frontmatter_licence="Proprietary")
    check("a_file_level_notice_that_disagrees_blocks_a_verbatim_copy",
          conflicting["decision"] == OUTLINE_ONLY and conflicting["reason"] == "licence_notices_disagree"
          and matching["decision"] == VERBATIM and pointing["decision"] == VERBATIM
          and free_text["decision"] in (OUTLINE_ONLY, REFUSED)
          and any(notice["kind"] == "frontmatter_licence" for notice in matching["file_level_notices"]),
          [conflicting["reason"], matching["reason"], pointing["reason"], free_text["reason"]])

    refused_policies = []
    for accepted_list in (("MIT", "NONE"), ("unknown",), ("MIT", "MIT"), ("GPL-3.0 OR MIT",), ()):
        try:
            LicencePolicy(accepted=accepted_list)
        except LibraryRecordError as error:
            refused_policies.append(error.code)
    check("a_policy_cannot_accept_no_licence_an_unknown_name_or_a_repeated_one",
          len(refused_policies) == 5, refused_policies)

    paths = {"LICENSE", "skills/LICENSE.md", "skills/example/LICENSE.txt", "other/LICENSE"}
    check("the_nearest_licence_file_governs_a_path",
          governing_licence_path("skills/example/SKILL.md", paths) == "skills/example/LICENSE.txt"
          and governing_licence_path("skills/another/SKILL.md", paths) == "skills/LICENSE.md"
          and governing_licence_path("docs/SKILL.md", paths) == "LICENSE"
          and governing_licence_path("docs/SKILL.md", {"other/LICENSE"}) is None)

    words = licence_words("Copyright (c) 2020 Someone\nhttps://example.org/terms\nThe [year] licence text")
    check("normalization_drops_copyright_lines_addresses_and_placeholders_and_joins_spellings",
          "someone" not in words and "example" not in words and "year" not in words
          and "license" in words and "licence" not in words, sorted(words))

    passed = sum(item["passed"] for item in tests)
    return {"record_type": "library_licence_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
