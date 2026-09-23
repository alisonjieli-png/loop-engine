"""Format pre-check engine ``agent_skills_reference``: the Agent Skills reference validator.

Adapted, not copied: the engine runs the reference validator's own command
(``agentskills validate``, package ``skills-ref``, Apache-2.0, Python 3.11 or
later) on the rendered skill file a client would install, and refuses the item
when the validator reports a problem. The shared interpreter of this repository
is Python 3.10, so the validator runs from its own environment, declared by the
program path; where it is not installed the engine is unavailable and the
built-in format rules still decide the kind.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import tempfile

from . import result_of
from .command import DeclaredProgram, bounded
from .rendering import write_rendered_skill

SKILL_FOLDER = "{skill_folder}"


class AgentSkillsReference:
    kind = "format"
    engine_id = "agent_skills_reference"

    def __init__(self, settings: dict, policy) -> None:
        self.program = DeclaredProgram(settings, self.engine_id, (SKILL_FOLDER,))
        self._version = None

    def availability(self):
        if self._version is None:
            self._version = self.program.version()
        return self._version

    def check(self, request, context):
        version = self.availability()[2]
        with tempfile.TemporaryDirectory(prefix="skill-validate-") as directory:
            folder = write_rendered_skill(request, Path(directory))
            try:
                finished = self.program.run({SKILL_FOLDER: str(folder)}, Path(directory))
            except subprocess.TimeoutExpired:
                return result_of(self.kind, self.engine_id, version,
                                 [("agent_skills_validation_timeout", "the validator did not finish in time")])
        if finished.returncode == 0:
            return result_of(self.kind, self.engine_id, version, [])
        output = bounded(finished.stdout + " " + finished.stderr).replace(str(folder), "SKILL_FOLDER")
        return result_of(self.kind, self.engine_id, version, [("agent_skills_validation_failed", output)])
