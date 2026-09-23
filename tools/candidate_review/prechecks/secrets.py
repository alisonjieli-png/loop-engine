"""Secrets pre-check engine ``builtin_secret_patterns``.

Refuses an item when anything a reviewer would be sent about it holds a value
shaped like a credential: the body, the purpose, the item record and every
cited source file. Nothing secret-shaped therefore ever leaves this machine in
a review request. The patterns are the repository's own secret patterns (the
list the conformance scan and the model call export use) plus the extra shapes
the panel declares, such as live payment keys, fine-grained repository tokens,
cloud keys, signed tokens and private key headers. A finding names the place
and the pattern by its number and never repeats the matched text.
"""
from __future__ import annotations

import json
import re

from loop_engine.core.model_call_records import default_secret_patterns

from ..records import read_part, refuse
from . import result_of

VERSION = "1"


def secret_patterns(settings: dict) -> tuple:
    part = read_part(settings, "builtin_secret_patterns", ("extra_patterns",))
    extra = part["extra_patterns"]
    if type(extra) is not list or any(type(item) is not str or not item for item in extra):
        refuse("invalid_precheck_settings", "extra_patterns is a list of patterns")
    try:
        return tuple(re.compile(pattern) for pattern in (*default_secret_patterns(), *extra))
    except re.error:
        refuse("invalid_precheck_settings", "a secret pattern is not a valid pattern")


class SecretPatterns:
    kind = "secrets"
    engine_id = "builtin_secret_patterns"

    def __init__(self, settings: dict, policy) -> None:
        self.patterns = secret_patterns(settings)

    def availability(self):
        return True, "", VERSION

    def check(self, request, context):
        item = request.item
        places = [("body", request.body_text_lenient),
                  ("purpose", str(item.get("reference", {}).get("purpose", ""))),
                  ("item record", json.dumps(item, sort_keys=True, ensure_ascii=False))]
        places += [(f"cited source {source.path}", source.text) for source in request.cited_sources]
        findings = []
        for place, value in places:
            for number, pattern in enumerate(self.patterns):
                if pattern.search(value):
                    findings.append(("secret_shaped_value",
                                     f"the {place} holds a value shaped like secret pattern {number}"))
        return result_of(self.kind, self.engine_id, VERSION, findings)
