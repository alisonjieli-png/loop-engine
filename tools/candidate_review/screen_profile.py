"""The Community screen for imported packages: four criteria, the imported prechecks (roadmap S-6.199).

The screen is the one model review a package receives before it is published as
Community. It keeps the imported reader, the imported prechecks and the panel's
reviewer authority, quorum and budget policy, and swaps only the written
criteria and the reviewer instructions for the four screen questions. The
eight-criterion review in ``imported_profile`` stays the full review that runs
after publication. A screen verdict is recorded under its own criteria digest,
so a ledger row always says which review a package received.
"""
from __future__ import annotations

import json
from pathlib import Path

from .configuration import compile_criteria, load_instructions
from .imported_profile import configuration as imported_configuration, engines as imported_engines

RESOURCES = Path(__file__).resolve().parent / "resources"
SCREEN_CRITERIA = ("hidden_instructions", "undeclared_effects", "false_description", "no_use_to_a_harness")
PROFILE_NAME = "community_screen"


def resources():
    path = RESOURCES / "COMMUNITY-SCREEN.md"
    criteria = compile_criteria(json.loads((RESOURCES / "community-screen-criteria.json").read_text()),
                                path.read_text())
    return criteria, load_instructions(RESOURCES / "COMMUNITY-SCREEN-INSTRUCTIONS.md")


configuration = imported_configuration
engines = imported_engines
