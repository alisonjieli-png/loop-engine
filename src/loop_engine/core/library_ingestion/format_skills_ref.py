"""Engine agent_skills_reference_validator of the library_format_validation engine slot.

The adopted reference validator of the Agent Skills specification:
skills-ref 0.1.0 (Apache-2.0) from agentskills/agentskills at commit
69ef37e9424c0a7ea9dd2293b559e43ec8176379, installed in the tools
environment because it needs Python 3.11 or later. It validates the rendered
file as a folder, exactly as a harness would see it. Its own README says it
is for demonstration, so it runs beside the built-in rules, never instead of
them. A missing library makes the engine ineligible with dependency_missing.
"""
from __future__ import annotations

import tempfile
from pathlib import Path


def _validate_function():
    try:
        from skills_ref import validate  # optional engine dependency, Apache-2.0
    except ImportError:
        return None
    return validate


class AgentSkillsReferenceValidator:
    """skills-ref validate, run on the rendered SKILL.md in a folder named after the skill."""

    engine_id = "agent_skills_reference_validator"
    engine_version = "1.0.0"
    engine_kind = "format_rules"
    effects = ("reads_fs", "writes_fs")
    third_party = "skills-ref 0.1.0 (Apache-2.0), agentskills/agentskills at 69ef37e"
    applies_to = ("skill",)
    dependency = "skills_ref"

    @classmethod
    def availability(cls, settings: dict):
        return (True, "available") if _validate_function() is not None else (False, "dependency_missing")

    @classmethod
    def from_settings(cls, settings: dict, resources: dict):
        """Construct from declared settings and the run's resources; nothing starts here."""
        return cls()

    def describe(self) -> dict:
        return {"engine_id": self.engine_id, "engine_version": self.engine_version,
                "third_party": self.third_party, "applies_to": list(self.applies_to)}

    def validate_skill(self, folder: str, text: str) -> list:
        validate = _validate_function()
        if validate is None:
            raise RuntimeError("skills-ref is not installed")
        with tempfile.TemporaryDirectory(prefix="skills-ref-") as root:
            skill = Path(root) / folder
            skill.mkdir()
            (skill / "SKILL.md").write_text(text, encoding="utf-8")
            return [str(problem) for problem in validate(skill)]
