"""Typed structural diagnostics for untrusted independent verifier plans.

This validates declarations and coverage before probe file generation. It does
not assign criterion references, generate expectations, execute code or approve
an oracle. The existing independent verifier remains the operational owner.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .generated_project import GeneratedProjectCommand, GeneratedProjectFile, GeneratedProjectFileSpec


@dataclass(frozen=True)
class ProbePlanDiagnostic:
    code: str
    detail: str
    missing_criteria: tuple[str, ...] = ()
    unknown_criteria: tuple[str, ...] = ()
    repairable: bool = True

    def to_dict(self):
        return {"record_type": "independent_probe_plan_diagnostic/v1", "code": self.code,
                "detail": self.detail, "missing_criteria": list(self.missing_criteria),
                "unknown_criteria": list(self.unknown_criteria), "repairable": self.repairable}


class InvalidProbePlan(ValueError):
    def __init__(self, diagnostic: ProbePlanDiagnostic):
        self.diagnostic = diagnostic
        super().__init__(diagnostic.detail)


def validate_probe_plan(value, criteria, *, materialized=False):
    """Validate actual model claims; return declarations and typed commands."""
    required = set(dict(criteria))
    declared = set()
    if isinstance(value, dict) and isinstance(value.get("cases"), list):
        for case in value["cases"]:
            if isinstance(case, dict) and isinstance(case.get("criterion_refs"), list):
                declared.update(ref for ref in case["criterion_refs"] if isinstance(ref, str))

    def fail(code, detail, **kwargs):
        kwargs.setdefault("missing_criteria", tuple(sorted(required - declared)))
        kwargs.setdefault("unknown_criteria", tuple(sorted(declared - required)))
        raise InvalidProbePlan(ProbePlanDiagnostic(code, detail, **kwargs))

    if not isinstance(value, dict) or value.get("status") != "ready":
        unavailable = isinstance(value, dict) and value.get("status") == "unavailable"
        fail("verifier_unavailable" if unavailable else "invalid_plan_status",
             "independent verifier could not construct executable checks", repairable=not unavailable)
    files, cases = value.get("files"), value.get("cases")
    if not isinstance(files, list) or not files or not isinstance(cases, list) or not cases:
        fail("missing_files_or_cases", "independent probe requires declared files and nonempty cases")
    typed_files, paths = [], set()
    for item in files:
        allowed = ({"path", "content"},) if materialized else ({"path", "content"}, {"path", "purpose"})
        if (not isinstance(item, dict) or set(item) not in allowed
                or any(not isinstance(part, str) for part in item.values())):
            fail("invalid_file_declaration", "independent probe file shape is invalid")
        try:
            file = GeneratedProjectFile(**item) if "content" in item else GeneratedProjectFileSpec(**item)
        except (TypeError, ValueError):
            fail("invalid_file_declaration", "independent probe file declaration is invalid")
        if not file.path.startswith("checks/") or file.path in paths:
            fail("invalid_file_path", "independent probe files require unique paths under checks/")
        paths.add(file.path)
        typed_files.append(file)
    commands, ids, covered = [], set(), set()
    for case in cases:
        if not isinstance(case, dict) or set(case) != {
                "case_id", "criterion_refs", "purpose", "argv", "timeout_seconds", "comparison", "expected"}:
            fail("invalid_case_declaration", "independent probe case shape is invalid")
        case_id, refs = case["case_id"], case["criterion_refs"]
        if (not isinstance(case_id, str) or not case_id.strip() or case_id in ids
                or not isinstance(refs, list) or not refs
                or any(not isinstance(ref, str) or not ref for ref in refs)
                or len(refs) != len(set(refs))):
            fail("invalid_case_identity", "independent case identity or coverage is invalid")
        if case["comparison"] not in ("json_equal", "text_equal"):
            fail("invalid_comparison", "independent comparison is unsupported")
        if case["comparison"] == "text_equal" and (not isinstance(case["expected"], str) or not case["expected"]):
            fail("invalid_expectation", "text comparison needs nonempty exact expected output")
        try:
            json.dumps(case["expected"], ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
            if not isinstance(case["argv"], list) or not isinstance(case["purpose"], str):
                raise ValueError("argv is not a list")
            command = GeneratedProjectCommand(tuple(case["argv"]), case["purpose"], case["timeout_seconds"], "verify")
        except (TypeError, ValueError):
            fail("invalid_case_execution", "independent case expectation or command is invalid")
        argv = case["argv"]
        if len(argv) < 2 or argv[1] not in paths or argv[0] not in ("python", "python3"):
            fail("invalid_case_execution", "independent command must run its exact declared check file")
        commands.append(command)
        ids.add(case_id)
        covered.update(refs)
    if covered != required:
        fail("criterion_coverage_mismatch", "independent checks do not cover exactly the registered criteria",
             missing_criteria=tuple(sorted(required - covered)), unknown_criteria=tuple(sorted(covered - required)))
    return tuple(typed_files), tuple(commands)
