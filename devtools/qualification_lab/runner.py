"""Standalone Ollama-assisted component qualification and run audit."""
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CATALOG_PATH = ROOT / "qualification_catalog.json"


def load_catalog() -> dict:
    value = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if value.get("record_type") != "component_qualification_catalog/v1":
        raise ValueError("qualification catalog has the wrong contract")
    return value


def select_case(case_id: str) -> dict:
    for item in load_catalog()["cases"]:
        if item["case_id"] == case_id:
            return item
    raise ValueError(f"unknown qualification case {case_id!r}")


def render_prompt(case: dict) -> str:
    contract = {
        "record_type": "component_qualification_result/v1",
        "case_id": case["case_id"],
        "verdict": "PASS|FAIL|UNKNOWN",
        "invariant_results": [{
            "invariant": "registered invariant",
            "state": "PASS|FAIL|UNKNOWN",
            "evidence": ["exact evidence reference"],
            "reason": "bounded explanation"
        }],
        "failures": ["blocking failure"],
        "unknowns": ["unresolved evidence gap"],
        "recommended_next_test": "one bounded next test"
    }
    sections = [
        "[ROLE]\nIndependent component qualification reviewer.",
        "[RULES]\nReview one component contract only. Do not claim execution. "
        "Do not infer permission. Preserve UNKNOWN. A broad design argument "
        "is not evidence.",
        "[CASE]\n" + json.dumps(case, indent=2, sort_keys=True),
        "[QUESTIONS]\n" + "\n".join(
            f"{index}. {question}" for index, question in enumerate(
                case["questions"], 1)),
        "[OUTPUT]\nReturn JSON only:\n" + json.dumps(
            contract, indent=2, sort_keys=True),
    ]
    return "\n\n".join(sections)


def call_ollama(case: dict, model: str, base_url: str) -> dict:
    key = os.environ.get("OLLAMA_API_KEY", "").strip()
    if not key:
        raise ValueError("OLLAMA_API_KEY is required for an Ollama run")
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": render_prompt(case)}],
        "stream": False,
        "format": "json",
    }).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat", data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    with urllib.request.urlopen(request, timeout=180) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload.get("message", {}).get("content", "")
    result = json.loads(content)
    validate_result(case, result)
    return result


def validate_result(case: dict, result: dict) -> None:
    if result.get("record_type") != "component_qualification_result/v1":
        raise ValueError("qualification result has the wrong record type")
    if result.get("case_id") != case["case_id"]:
        raise ValueError("qualification result targets another case")
    if result.get("verdict") not in ("PASS", "FAIL", "UNKNOWN"):
        raise ValueError("qualification verdict is not registered")
    rows = result.get("invariant_results")
    if not isinstance(rows, list):
        raise ValueError("invariant_results must be a list")
    expected = set(case["invariants"])
    observed = {row.get("invariant") for row in rows
                if isinstance(row, dict)}
    if observed != expected:
        raise ValueError("qualification result must cover every invariant once")
    if any(row.get("state") not in ("PASS", "FAIL", "UNKNOWN")
           for row in rows):
        raise ValueError("invariant state is not registered")


def _normalized_gap(value: str) -> str:
    words = re.findall(r"[a-z0-9]+", value.lower())
    ignored = {"the", "a", "an", "and", "or", "is", "are", "still",
               "must", "before", "can", "be", "to", "from", "for"}
    return " ".join(sorted(set(words) - ignored))


def audit_run(path: Path) -> dict:
    run = json.loads(path.read_text(encoding="utf-8"))
    actions = run.get("action_decisions", [])
    verifications = run.get("verification", [])
    projects = run.get("project_attempts", [])
    research = [item for item in actions
                if item.get("action_kind") == "RESEARCH_SOURCE"]
    gaps = Counter(
        _normalized_gap(
            str(gap.get("gap") or "") if isinstance(gap, dict) else str(gap))
        for record in verifications
        for gap in record.get("remaining_gaps", []))
    passed_projects = [item for item in projects
                       if item.get("deterministic_checks_passed")]
    findings = []
    if len(research) > 3 and passed_projects:
        findings.append({
            "code": "POST_PROJECT_RESEARCH_EXCEEDED",
            "observed": len(research), "limit": 3})
    if run.get("passes", 0) > 6 and not run.get("solved"):
        findings.append({
            "code": "LONG_UNRESOLVED_RUN", "passes": run.get("passes")})
    repeated_gaps = [{"gap": gap, "count": count}
                     for gap, count in gaps.items() if gap and count >= 3]
    if repeated_gaps:
        findings.append({
            "code": "REPEATED_VERIFICATION_GAP",
            "gaps": repeated_gaps})
    if passed_projects and not run.get("solved"):
        findings.append({
            "code": "VERIFIED_ARTIFACT_STATE_NOT_TERMINAL",
            "project_count": len(passed_projects),
            "final_route": run.get("final_route")})
    return {
        "record_type": "loop_engine_black_box_audit/v1",
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "solved": bool(run.get("solved")),
        "passes": run.get("passes"),
        "model_calls": run.get("model_calls"),
        "action_counts": dict(Counter(
            item.get("action_kind") for item in actions)),
        "project_attempts": len(projects),
        "deterministically_passed_projects": len(passed_projects),
        "findings": findings,
        "verdict": "PASS" if not findings else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list")
    render = commands.add_parser("render")
    render.add_argument("--case", required=True)
    ollama = commands.add_parser("ollama")
    ollama.add_argument("--case", required=True)
    ollama.add_argument("--model", required=True)
    ollama.add_argument("--base-url", default="https://ollama.com")
    audit = commands.add_parser("audit-run")
    audit.add_argument("--result", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "list":
        print(json.dumps([
            {key: item[key] for key in (
                "case_id", "component_kind", "stage", "goal")}
            for item in load_catalog()["cases"]], indent=2))
    elif args.command == "render":
        print(render_prompt(select_case(args.case)))
    elif args.command == "ollama":
        print(json.dumps(call_ollama(
            select_case(args.case), args.model, args.base_url), indent=2))
    else:
        print(json.dumps(audit_run(args.result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
