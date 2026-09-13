"""Frozen resource-bearing study generation and complete oracle control checks."""

from __future__ import annotations

import json
import random
from pathlib import Path

from .contracts import OPERATIONS, TaskCase, WorkPacket, digest
from .runtime import check_candidate, execute
from .storage import confined_root, write_new


def generate(root: Path, count: int, seed: int) -> dict:
    if type(count) is not int or not 1 <= count <= 10000 or type(seed) is not int:
        raise ValueError(
            "study count must be between 1 and 10000, seed must be integer"
        )
    root = confined_root(root, create=True)
    rng = random.Random(seed)
    entries = []
    for index in range(count):
        case = TaskCase(
            f"case-{index:05d}",
            OPERATIONS[index % len(OPERATIONS)],
            tuple(rng.randint(-50, 50) for _ in range(rng.randint(0, 128))),
        )
        payload = case.to_dict()
        relative = case.case_id + "/task.json"
        write_new(root / relative, payload)
        write_new(
            root / case.case_id / "contract.json",
            {
                "record_type": "embodiment_task_contract/v1",
                "input": "embodiment_task/v1",
                "output": "embodiment_result/v1",
                "operation": case.operation,
                "evaluator": "embodiment_lab.runtime.check_candidate@1.0.0",
                "evidence_class": "deterministic_mechanism",
                "task_digest": digest(payload),
            },
        )
        entries.append({"path": relative, "digest": digest(payload)})
    manifest = {
        "record_type": "embodiment_study/v1",
        "seed": seed,
        "count": count,
        "cases": entries,
        "evidence_class": "deterministic_mechanism",
        "model_quality_claim": False,
    }
    write_new(root / "manifest.json", manifest)
    return manifest


def load(root: Path) -> tuple[TaskCase, ...]:
    root = confined_root(root, create=False)
    manifest = json.loads((root / "manifest.json").read_text())
    if manifest.get("record_type") != "embodiment_study/v1" or manifest.get(
        "count"
    ) != len(manifest.get("cases", [])):
        raise ValueError("invalid study manifest")
    cases, names = [], set()
    for entry in manifest["cases"]:
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 2:
            raise ValueError("case path escape")
        path = root / relative
        if path.is_symlink() or path.parent.is_symlink():
            raise ValueError("case symlink refused")
        value = json.loads(path.read_text())
        if digest(value) != entry["digest"]:
            raise ValueError("study case drift")
        case = TaskCase.from_dict(value)
        if case.case_id in names:
            raise ValueError("duplicate case identity")
        names.add(case.case_id)
        cases.append(case)
    return tuple(cases)


def qualify(cases: tuple[TaskCase, ...]) -> dict:
    checks = []
    for case in cases:
        packet = WorkPacket(case.case_id + ".qualification", case)
        correct = execute(packet)
        wrong = dict(
            correct, value={"wrong": True}, value_digest=digest({"wrong": True})
        )
        checks.append(
            {
                "case_id": case.case_id,
                "positive": check_candidate(packet, correct)["accepted"],
                "negative_refused": not check_candidate(packet, wrong)["accepted"],
            }
        )
    return {
        "record_type": "embodiment_qualification/v1",
        "case_count": len(checks),
        "passed": bool(checks)
        and all(c["positive"] and c["negative_refused"] for c in checks),
        "checks": checks,
        "model_calls": 0,
        "evidence_class": "deterministic_mechanism",
    }
