"""Licence pre-check engine ``builtin_licence_rules``.

Refuses an item whose declared licence is not one the panel accepts, whose
licence state is not settled, or whose text states another licence than the
one it declares. Material without a clear permissive licence is never copied
into the catalogue; an item written as original work carries the licence of
the repository that wrote it. Approving the text of an item whose rights are
not settled would not make it servable, so such an item never reaches a
reviewer.
"""
from __future__ import annotations

import re

from ..records import read_part, refuse, text_field
from . import result_of

VERSION = "1"


class LicenceRules:
    kind = "licence"
    engine_id = "builtin_licence_rules"

    def __init__(self, settings: dict, policy) -> None:
        part = read_part(settings, self.engine_id, ("licence_states_accepted", "licence_sentence"))
        states = part["licence_states_accepted"]
        if type(states) is not list or not states or any(type(state) is not str for state in states):
            refuse("invalid_precheck_settings", "licence_states_accepted is a non-empty list of states")
        sentence = text_field(part["licence_sentence"], "licence_sentence", limit=200)
        before, marker, after = sentence.partition("{licence}")
        if not marker or "{" in before + after:
            refuse("invalid_precheck_settings", "licence_sentence names {licence} once")
        self.states = tuple(states)
        self.sentence = sentence
        self.accepted = tuple(policy.accepted_licences)
        self.stated = re.compile(re.escape(before) + r"(\S+?)" + re.escape(after) + r"(?=\s|$)")

    def availability(self):
        return True, "", VERSION

    def check(self, request, context):
        item = request.item
        licence = item.get("reference", {}).get("license")
        findings = []
        if licence not in self.accepted:
            findings.append(("licence_not_accepted",
                             f"the declared licence {licence!r} is not one of {list(self.accepted)}"))
        if item.get("license_state") not in self.states:
            findings.append(("licence_state_not_settled",
                             f"the licence state {item.get('license_state')!r} is not one of {list(self.states)}"))
        text = request.body_text_lenient
        expected = self.sentence.format(licence=licence)
        if expected not in text:
            findings.append(("licence_sentence_missing", f"the text does not state {expected!r}"))
        others = sorted({found for found in self.stated.findall(text) if found != licence})
        if others:
            findings.append(("licence_sentence_disagrees", f"the text also states the licences {others}"))
        return result_of(self.kind, self.engine_id, VERSION, findings)
