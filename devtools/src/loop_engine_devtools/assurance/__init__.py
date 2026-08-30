"""Repository Assurance Practitioner: the root devtools supervisor.

The root assurance Practitioner runs on the canonical Loop kernel. It
spawns specialist review Loops, collects typed findings, and returns a
PASS / PASS_WITH_DOCUMENTED_WARNINGS / BLOCKED verdict. It is an
ordinary Practitioner-role Loop, not a second runtime.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class AssuranceFinding:
    """One typed finding from a specialist review Loop."""

    rule: str
    severity: str
    path: str
    detail: str
    invariant_id: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity,
                "path": self.path, "detail": self.detail,
                "invariant_id": self.invariant_id}


@dataclass(frozen=True)
class AssuranceVerdict:
    """The integrated result of one assurance run."""

    verdict: str
    findings: tuple[AssuranceFinding, ...] = ()
    warnings: tuple[AssuranceFinding, ...] = ()
    evidence: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"verdict": self.verdict,
                "findings": [f.to_dict() for f in self.findings],
                "warnings": [f.to_dict() for f in self.warnings],
                "evidence": self.evidence}


@dataclass(frozen=True)
class RepositoryAssuranceRequest:
    """Passive configuration for one profile-driven assurance Loop."""

    repository_root: Path
    scope: str = "full"
    strict: bool = False
    profile_id: str = "practitioner.verifier"
    steps: tuple[str, ...] = (
        "inventory", "architecture", "semantics", "boundaries", "report")
    write_evidence: bool = False
    evidence_path: str = "artifacts/verification/file_alignment_audit.jsonl"


@dataclass(frozen=True)
class FileAlignmentRecord:
    """One file's current static alignment evidence and exact open findings."""

    path: str
    boundary: str
    artifact_kind: str
    checks: tuple[str, ...]
    findings: tuple[str, ...]
    status: str

    def to_dict(self) -> dict:
        return {"record_type": "file_alignment_record/v1", **self.__dict__}


def _repository_files(root: Path) -> tuple[Path, ...]:
    excluded = {".git", ".venv", "__pycache__", ".pytest_cache", "dist",
                "build", ".mypy_cache", ".ruff_cache"}
    return tuple(sorted(path for path in root.rglob("*")
                        if path.is_file()
                        and not excluded.intersection(path.parts)))


def _file_records(root: Path, findings: list[AssuranceFinding]) \
        -> tuple[FileAlignmentRecord, ...]:
    by_path: dict[str, list[str]] = {}
    for finding in findings:
        normalized = finding.path.replace("\\", "/").removeprefix("./")
        by_path.setdefault(normalized, []).append(
            f"{finding.rule}: {finding.detail}")
        if normalized and not normalized.startswith((
                "src/", "devtools/", "docs/", "examples/", "benchmarks/",
                "showcase/", ".github/")):
            by_path.setdefault(f"src/loop_engine/{normalized}", []).append(
                f"{finding.rule}: {finding.detail}")
    records = []
    for path in _repository_files(root):
        relative = path.relative_to(root).as_posix()
        suffix = path.suffix.lower()
        kind = {
            ".py": "python_module", ".md": "documentation",
            ".yaml": "configuration", ".yml": "configuration",
            ".json": "data_record", ".jsonl": "data_records",
            ".toml": "configuration", ".html": "web_asset",
            ".js": "web_code", ".css": "web_asset",
        }.get(suffix, "artifact")
        boundary = relative.split("/", 1)[0]
        problems = tuple(sorted(set(by_path.get(relative, ()))))
        records.append(FileAlignmentRecord(
            relative, boundary, kind,
            ("ownership", "ontology", "semantic_identity",
             "call_boundary" if suffix == ".py" else "provenance"),
            problems,
            "VERIFIED_BY_CURRENT_GATES" if not problems
            else "REQUIRED_NOT_ALIGNED"))
    return tuple(records)


def _write_file_evidence(
        request: RepositoryAssuranceRequest,
        records: tuple[FileAlignmentRecord, ...],
        summary: dict) -> str:
    if not request.write_evidence:
        return "NOT_REQUESTED"
    target = (request.repository_root / request.evidence_path).resolve()
    repository = request.repository_root.resolve()
    if target != repository and repository not in target.parents:
        raise PermissionError("assurance evidence path escapes repository")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps({"record_type": "file_alignment_summary/v1",
                                 **summary}, sort_keys=True) + "\n")
        for record in records:
            handle.write(json.dumps(record.to_dict(), sort_keys=True) + "\n")
    return str(target)


def run_repository_assurance(request: RepositoryAssuranceRequest) -> dict:
    """Run a configured assurance profile through the canonical Loop.

    The root Practitioner owns the review. Each specialist check is a
    bounded deterministic operation inside the root; a check that needs
    independent governance becomes a child Loop. The verdict is
    computed from typed findings, never from prose.
    """
    from loop_engine import LoopConfig, Loop, StepOutcome
    from loop_engine.loop.loop_role import (
        LoopRelationship, LoopRole, LoopRoleIdentity)

    findings: list[AssuranceFinding] = []
    warnings: list[AssuranceFinding] = []

    def collect(problems: list[dict], *, rule_prefix: str,
                severity: str = "high", warning: bool = False) -> None:
        target = warnings if warning else findings
        for problem in problems:
            target.append(AssuranceFinding(
                rule=f"{rule_prefix}.{problem.get('rule', 'unknown')}",
                severity=severity,
                path=problem.get("file", problem.get("path", "")),
                detail=problem.get("detail", ""),
                invariant_id=problem.get("invariant_id", "")))

    from loop_engine.repository_conformance import \
        run_repository_conformance
    from loop_engine.repository_structure import structure_report
    from loop_engine.architecture_contract import \
        run_architecture_contract_checks
    from loop_engine.backend_isolation import provider_leak_violations

    from loop_engine.semantic_conformance import semantic_conformance_report
    from loop_engine.parameter_boundary import ScanRequest, scan_repository
    loop = Loop(
        f"repository assurance review: {request.scope}",
        LoopConfig(
            framework="custom", custom_steps=request.steps, power="deep",
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            exit_condition="steps_complete"),
        identity=LoopRoleIdentity(
            LoopRole.PRACTITIONER, request.profile_id),
        relationship=LoopRelationship.starting())
    state: dict = {}

    def handler(_loop: Loop, step: str, _context: dict) -> StepOutcome:
        if step == "inventory":
            state["conformance"] = run_repository_conformance()
            state["structure"] = structure_report()
            collect(state["conformance"]["problems"],
                    rule_prefix="repository")
            collect(state["structure"]["violations"],
                    rule_prefix="structure")
            count = state["conformance"]["files_indexed"]
        elif step == "architecture":
            state["contract"] = run_architecture_contract_checks()
            state["leaks"] = provider_leak_violations()
            collect(state["contract"]["problems"], rule_prefix="contract")
            collect(state["leaks"], rule_prefix="portability")
            count = len(state["contract"]["problems"]) + len(state["leaks"])
        elif step == "semantics":
            state["semantics"] = semantic_conformance_report()
            collect(state["semantics"]["violations"],
                    rule_prefix="semantics")
            count = len(state["semantics"]["violations"])
        elif step == "boundaries":
            state["parameter_report"] = scan_repository(ScanRequest(
                root=request.repository_root,
                exception_registry=(
                    request.repository_root / "docs" / "architecture"
                    / "call-boundary-exceptions.yaml"),
                current_version="0.1.0", revision="working-tree",
                require_registry=True))
            collect(state["parameter_report"]["violations"],
                    rule_prefix="call_boundary",
                    severity=("high" if request.strict else "medium"),
                    warning=not request.strict)
            count = state["parameter_report"]["unapproved_violations"]
        elif step == "report":
            state["file_records"] = _file_records(
                request.repository_root, [*findings, *warnings])
            count = len(state["file_records"])
        else:
            raise ValueError(f"unknown assurance step {step!r}")
        return StepOutcome(
            output={"step": step, "count": count},
            mode="deterministic", confidence=1.0)

    run = loop.run(handler=handler, max_steps=len(request.steps) + 1)
    conformance = state["conformance"]
    structure = state["structure"]
    contract = state["contract"]
    semantics = state["semantics"]
    parameter_report = state["parameter_report"]
    file_records = state["file_records"]
    blocking = [finding for finding in findings
                if finding.severity in ("high", "critical")]
    verdict = ("BLOCKED" if blocking
               else "PASS_WITH_DOCUMENTED_WARNINGS" if warnings
               else "PASS")
    summary = {
        "repository_root": str(request.repository_root),
        "scope": request.scope, "profile_id": request.profile_id,
        "steps": list(request.steps), "files": len(file_records),
        "aligned": sum(record.status == "VERIFIED_BY_CURRENT_GATES"
                       for record in file_records),
        "requires_alignment": sum(record.status == "REQUIRED_NOT_ALIGNED"
                                  for record in file_records),
        "findings": len(findings), "warnings": len(warnings),
        "verdict": verdict,
        "loop_id": run.loop_id,
    }
    evidence_path = _write_file_evidence(request, file_records, summary)
    return {
        "record_type": "repository_assurance/v1",
        "verdict": verdict,
        "findings": [f.to_dict() for f in findings],
        "warnings": [f.to_dict() for f in warnings],
        "evidence": {
            "files_indexed": conformance["files_indexed"],
            "files_in_full_audit": len(file_records),
            "files_requiring_alignment": summary["requires_alignment"],
            "directories": structure["directories"],
            "loop_id": run.loop_id,
            "runtime_type": "Loop",
            "profile_id": request.profile_id,
            "steps": list(request.steps),
            "parameter_boundary": parameter_report,
            "semantic_conformance": semantics,
            "file_alignment_evidence": evidence_path,
        },
    }


def self_test() -> dict:
    """Prove the assurance hierarchy runs on the canonical Loop kernel."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    report = run_repository_assurance(RepositoryAssuranceRequest(
        Path(__file__).resolve().parents[4], scope="self-test"))
    check("assurance_runs_through_the_canonical_loop_kernel",
          report["evidence"].get("runtime_type") == "Loop"
          and bool(report["evidence"].get("loop_id")))
    check("assurance_verdict_is_typed",
          report["verdict"] in ("PASS", "PASS_WITH_DOCUMENTED_WARNINGS",
                                "BLOCKED"))
    check("assurance_reports_evidence_counts",
          report["evidence"]["files_indexed"] > 100
          and report["evidence"]["directories"] > 20)
    check("assurance_findings_are_typed",
          all("rule" in f and "severity" in f and "path" in f
              for f in [*report["findings"], *report["warnings"]]))
    parameter_debt = report["evidence"]["parameter_boundary"][
        "unapproved_violations"]
    check("default_assurance_reports_staged_parameter_debt_as_warnings",
          (not parameter_debt and report["verdict"] == "PASS")
          or (parameter_debt > 0
              and report["verdict"] == "PASS_WITH_DOCUMENTED_WARNINGS"
              and len(report["warnings"]) == parameter_debt),
          f"{parameter_debt} staged call-boundary finding(s)")
    return {"tests": results}
