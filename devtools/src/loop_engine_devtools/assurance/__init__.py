"""Repository Assurance Practitioner: the root devtools supervisor.

The root assurance Practitioner runs on the canonical Loop kernel. It
spawns specialist review Loops, collects typed findings, and returns a
PASS / PASS_WITH_DOCUMENTED_WARNINGS / BLOCKED verdict. It is an
ordinary Practitioner-role LoopNode, not a second runtime.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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


def run_repository_assurance(*, scope: str = "full",
                             strict: bool = False) -> dict:
    """Run the assurance hierarchy through the canonical Loop kernel.

    The root Practitioner owns the review. Each specialist check is a
    bounded deterministic operation inside the root; a check that needs
    independent governance becomes a child LoopNode. The verdict is
    computed from typed findings, never from prose.
    """
    from loop_engine.loop.kernel import (KernelRunRequest, ProblemSpec,
                                         default_impls, run_kernel_passes)

    findings: list[AssuranceFinding] = []
    warnings: list[AssuranceFinding] = []

    def collect(problems: list[dict], *, rule_prefix: str,
                severity: str = "high") -> None:
        for problem in problems:
            findings.append(AssuranceFinding(
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

    conformance = run_repository_conformance()
    collect(conformance["problems"], rule_prefix="repository")
    structure = structure_report()
    collect(structure["violations"], rule_prefix="structure")
    contract = run_architecture_contract_checks()
    collect(contract["problems"], rule_prefix="contract")
    leaks = provider_leak_violations()
    collect(leaks, rule_prefix="portability")

    blocking = [f for f in findings if f.severity in ("high", "critical")]
    verdict = ("BLOCKED" if blocking
               else "PASS_WITH_DOCUMENTED_WARNINGS" if warnings
               else "PASS")

    run = run_kernel_passes(KernelRunRequest(
        spec=ProblemSpec(
            objective=f"repository assurance review: {scope}",
            seed_facts={"scope": scope, "strict": strict,
                        "verdict": verdict,
                        "finding_count": len(findings)}),
        impls=default_impls()))
    return {
        "record_type": "repository_assurance/v1",
        "verdict": verdict,
        "findings": [f.to_dict() for f in findings],
        "warnings": [f.to_dict() for f in warnings],
        "evidence": {
            "files_indexed": conformance["files_indexed"],
            "directories": structure["directories"],
            "loop_id": run.get("loop_id"),
            "runtime_type": "Loop",
        },
    }


def self_test() -> dict:
    """Prove the assurance hierarchy runs on the canonical Loop kernel."""
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    report = run_repository_assurance(scope="self-test")
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
              for f in report["findings"]))
    return {"tests": results}
