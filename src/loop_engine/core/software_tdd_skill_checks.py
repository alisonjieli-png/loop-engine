"""Checks for the packaged optional software TDD skill.

Owns discovery, independent admission, exact loading, and nonsoftware refusal
evidence. It does not execute TDD work.
"""
from __future__ import annotations

import hashlib
from importlib.resources import files

from .skill_registry import (
    SkillAdmissionRecord, SkillLoadPurpose, SkillRegistry)


def self_test():
    tests=[]
    def check(n,o,d=""): tests.append({"test":n,"passed":bool(o),"detail":d})
    root=files("loop_engine").joinpath("skills/software-tdd-red-green-refactor")
    registry=SkillRegistry()
    candidate=registry.discover((str(root),))[0]
    check("software_tdd_discovers_as_candidate",
          candidate.lifecycle=="candidate" and candidate.skill_id
          =="software-tdd-red-green-refactor")
    evidence=hashlib.sha256(b"independent software skill review").hexdigest()
    admission=SkillAdmissionRecord(
        "admission.software-tdd.1",candidate.skill_id,candidate.version,
        candidate.manifest_digest,"independent-skill-verifier",
        ("test:software-tdd-contract",),evidence)
    admitted=registry.admit(admission)
    loaded=registry.load(admitted.skill_id,admitted.version,
                         purpose=SkillLoadPurpose.TASK_USE)
    check("admitted_skill_loads_exact_instructions",
          loaded.admission==admission and "minimum implementation" in loaded.instructions)
    check("skill_is_explicitly_software_scoped",
          "Use only for software task slices" in loaded.instructions)
    passed=sum(x["passed"] for x in tests)
    return {"record_type":"software_tdd_skill_self_test/v1","tests":tests,
            "passed":passed,"total":len(tests),"all_passed":passed==len(tests)}
