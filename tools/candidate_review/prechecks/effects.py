"""Effects pre-check engine ``builtin_effect_rules``.

The declared effects of an item use the engine's own effect vocabulary
(``loop_engine.core.facets.EFFECTS``), each at most once, and ``pure`` never
beside another effect. A fenced shell block in the body is a command the reader
is told to run, so it needs the ``spawns_process`` effect. Whether every other
step's effect is declared is a question of meaning; the reviewers judge it
against the written effects rule.
"""
from __future__ import annotations

import re

from loop_engine.core.facets import EFFECTS

from ..records import refuse
from . import result_of

VERSION = "1"
PURE, PROCESS = "pure", "spawns_process"
SHELL_FENCE = re.compile(r"^```[ \t]*(?:bash|sh|shell|console|zsh|fish|powershell|pwsh|cmd|bat)\b", re.IGNORECASE
                         | re.MULTILINE)


class EffectRules:
    kind = "effects"
    engine_id = "builtin_effect_rules"

    def __init__(self, settings: dict, policy) -> None:
        if settings:
            refuse("invalid_precheck_settings", "builtin_effect_rules takes no settings")

    def availability(self):
        return True, "", VERSION

    def check(self, request, context):
        effects = request.item.get("reference", {}).get("declared_effects")
        if type(effects) is not list or any(type(effect) is not str for effect in effects):
            return result_of(self.kind, self.engine_id, VERSION,
                             [("effects_not_a_list", "declared_effects is a list of effect names")])
        findings = []
        unknown = sorted({effect for effect in effects if effect not in EFFECTS})
        if unknown:
            findings.append(("effect_unknown", f"{unknown} are not effects of {list(EFFECTS)}"))
        if len(set(effects)) != len(effects):
            findings.append(("effect_repeated", "an effect is declared twice"))
        if PURE in effects and len(set(effects)) > 1:
            findings.append(("pure_combined", "pure excludes every other effect"))
        if SHELL_FENCE.search(request.body_text_lenient) and PROCESS not in effects:
            findings.append(("undeclared_process_effect",
                             f"the body holds a shell block and does not declare {PROCESS}"))
        return result_of(self.kind, self.engine_id, VERSION, findings)
