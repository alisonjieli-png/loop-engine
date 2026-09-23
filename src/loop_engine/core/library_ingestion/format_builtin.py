"""Engine agent_skills_builtin_rules of the library_format_validation engine slot.

It checks a rendered SKILL.md against the Agent Skills specification: only
the six allowed frontmatter fields; a name of 1 to 64 lower case letters,
digits and single inner hyphens that equals the folder name; a description
of 1 to 1,024 characters; a compatibility note of at most 500 characters;
metadata that maps text to text; and a body. It is stricter than the
specification in two places, on purpose: a name is plain ASCII, and the
frontmatter may not contain three hyphens in a row, so that a parser that
splits on them, as the reference validator does, still reads it correctly.
The reference validator is a separate engine; both run on every skill.
"""
from __future__ import annotations

import re

from .rendering_types import RenderRefused
from .skill_rendering import (
    MAXIMUM_COMPATIBILITY_CHARACTERS, MAXIMUM_DESCRIPTION_CHARACTERS, MAXIMUM_NAME_CHARACTERS,
    SKILL_FIELDS, parse_skill)

_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class AgentSkillsBuiltinRules:
    """The specification's rules for one rendered SKILL.md, checked without any library."""

    engine_id = "agent_skills_builtin_rules"
    engine_version = "1.0.0"
    engine_kind = "format_rules"
    effects = ("pure",)
    third_party = "Agent Skills specification rules, written here; no library"
    applies_to = ("skill",)

    @classmethod
    def availability(cls, settings: dict):
        return True, "always_available"

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "engine_kind": self.engine_kind, "applies_to": list(self.applies_to)}

    def validate_skill(self, folder: str, text: str) -> list:
        try:
            parsed = parse_skill(text)
        except RenderRefused as error:
            return [error.code]
        closing = text.find("\n---", 4)
        problems = []
        if "---" in text[3:closing]:
            problems.append("the frontmatter contains three hyphens in a row")
        values = parsed.frontmatter
        extra = sorted(str(key) for key in set(values) - set(SKILL_FIELDS))
        if extra:
            problems.append(f"unexpected frontmatter fields: {', '.join(extra)}")
        name = values.get("name")
        if not isinstance(name, str) or not _NAME.match(name) or len(name) > MAXIMUM_NAME_CHARACTERS:
            problems.append("the name must be 1 to 64 lower case letters, digits and single inner hyphens")
        elif name != folder:
            problems.append(f"the name {name!r} must equal the folder name {folder!r}")
        description = values.get("description")
        if not isinstance(description, str) or not description.strip():
            problems.append("the description must be nonempty text")
        elif len(description) > MAXIMUM_DESCRIPTION_CHARACTERS:
            problems.append(f"the description has {len(description)} characters, above 1,024")
        if "compatibility" in values and (not isinstance(values["compatibility"], str)
                                          or len(values["compatibility"]) > MAXIMUM_COMPATIBILITY_CHARACTERS):
            problems.append("the compatibility note must be text of at most 500 characters")
        for field in ("license", "allowed-tools"):
            if field in values and not isinstance(values[field], str):
                problems.append(f"{field} must be text")
        metadata = values.get("metadata", {})
        if not isinstance(metadata, dict) or any(not isinstance(key, str) or not isinstance(value, str)
                                                 for key, value in metadata.items()):
            problems.append("metadata must map text to text")
        if not parsed.body.strip():
            problems.append("the skill has no body")
        return problems
