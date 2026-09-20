"""Validate the continuation roadmap and render its current status artifact.

Reads the existing roadmap authority. It never changes a task status, starts
work, grants authority, or qualifies a deployment. A listed dependency and a
recorded test result remain different facts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs/roadmap/roadmap.yaml"


class PlanError(ValueError):
    """The plan cannot be used without guessing its meaning."""


def validate(data: dict) -> dict:
    if data.get("schema_version") != "roadmap/v1":
        raise PlanError("unsupported roadmap version")
    plan = data.get("continuation", {})
    if plan.get("schema_version") != "continuation_plan/v1":
        raise PlanError("unsupported continuation version")
    steps = data.get("steps", [])
    by_id = {step["id"]: step for step in steps}
    if len(by_id) != len(steps):
        raise PlanError("duplicate step identifier")
    states = set(data["statuses"])
    for step in steps:
        if step["status"] not in states:
            raise PlanError(f"unknown status for {step['id']}")
        if any(dep not in by_id for dep in step.get("depends_on", [])):
            raise PlanError(f"unknown dependency for {step['id']}")
    visiting, visited = set(), set()

    def visit(identity):
        if identity in visiting:
            raise PlanError(f"dependency cycle at {identity}")
        if identity in visited:
            return
        visiting.add(identity)
        for dep in by_id[identity].get("depends_on", []):
            visit(dep)
        visiting.remove(identity)
        visited.add(identity)

    for identity in by_id:
        visit(identity)
    orders = plan["launch_order"] + plan["improvement_order"]
    if len(set(orders)) != len(orders):
        raise PlanError("continuation order repeats a step")
    references = list(orders)
    covered = set()
    for stream in plan["workstreams"]:
        members = stream["legacy_steps"] + stream["continuation_steps"]
        references.extend(members)
        covered.update(members)
    for group in plan["milestones"] + plan["launch_gates"]:
        references.extend(group["steps"])
    missing = sorted(set(references) - set(by_id))
    if missing:
        raise PlanError(f"unknown referenced steps: {missing}")
    if set(by_id) - covered:
        raise PlanError(f"unassigned initiatives: {sorted(set(by_id) - covered)}")
    if {key for key in by_id if key.startswith('S-6.')} != set(orders):
        raise PlanError("every continuation step must have one scheduling position")
    decisions = {row["id"]: row for row in plan["decisions"]}
    if len(decisions) != len(plan["decisions"]):
        raise PlanError("duplicate authority decision identifier")
    for step in steps:
        for requirement in step.get("authority_requirements", []):
            if requirement not in decisions:
                raise PlanError(f"unknown authority requirement: {requirement}")
    for row in plan["milestones"]:
        start, end = row["hours"]
        if not 0 <= start < end <= 24:
            raise PlanError("milestone is outside the declared 24-hour window")
    validate_owner_actions(plan.get("owner_actions", []), by_id)
    validate_delivery_plan(plan, by_id)
    return by_id


def validate_owner_actions(rows, steps):
    """Owner preparation is distinct from runtime grants and release evidence."""
    required = {"id", "title", "phase", "depends_on", "steps", "guide", "instructions",
                "return_fields", "completion", "safety"}
    if not isinstance(rows, list):
        raise PlanError("owner actions must be a list")
    by_id = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != required:
            raise PlanError("owner action fields are incomplete or unknown")
        if not isinstance(row["id"], str) or not re.fullmatch(r"OWNER-[0-9]{2}", row["id"]) or row["id"] in by_id:
            raise PlanError("owner action identifiers must be unique")
        if row["phase"] not in ("now", "after_endpoint", "before_public", "before_charging", "optional", "prepared", "engineering"):
            raise PlanError("unknown owner action phase")
        for field in ("title", "guide", "completion", "safety"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise PlanError("owner action needs meaningful text")
        for field in ("depends_on", "steps", "instructions", "return_fields"):
            if not isinstance(row[field], list) or any(not isinstance(value, str) or not value for value in row[field]):
                raise PlanError("owner action lists must contain text")
        if not row["instructions"] or not row["return_fields"] or not row["steps"] or any(key not in steps for key in row["steps"]):
            raise PlanError("owner action needs instructions, handoff fields and known engineering steps")
        by_id[row["id"]] = row
    def visit(identity, active):
        if identity not in by_id or identity in active:
            raise PlanError("unknown or cyclic owner action dependency")
        for dependency in by_id[identity]["depends_on"]:
            visit(dependency, active | {identity})
    for identity in by_id:
        visit(identity, set())


def validate_delivery_plan(plan, steps):
    """Planning detail references existing work; it never qualifies a release."""
    fields = {"id", "title", "stage", "steps", "depends_on", "actions",
              "acceptance", "adversarial", "authority_note", "owning_paths", "verification_cases", "rollback"}
    rows = plan.get("delivery_batches", [])
    if not isinstance(rows, list):
        raise PlanError("delivery packages must be a list")
    packages = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != fields:
            raise PlanError("delivery package fields are incomplete or unknown")
        if not isinstance(row["id"], str) or not re.fullmatch(r"D-[0-9]{2}", row["id"]) or row["id"] in packages:
            raise PlanError("delivery package identifiers must be unique")
        if row["stage"] not in ("initial_service", "core_proof", "public_launch", "continued_improvement"):
            raise PlanError("unknown delivery stage")
        for field in ("title", "acceptance", "adversarial", "authority_note", "rollback"):
            if not isinstance(row[field], str) or not row[field].strip():
                raise PlanError("delivery package needs meaningful checks and authority limits")
        for field in ("steps", "depends_on", "actions"):
            values = row[field]
            if (not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values)
                    or len(values) != len(set(values))):
                raise PlanError("delivery lists must contain unique meaningful text")
        if not row["actions"] or not row["steps"] or any(key not in steps for key in row["steps"]):
            raise PlanError("delivery package needs actions and known owning steps")
        owners = row["owning_paths"]
        if (not isinstance(owners, list) or not owners or any(not isinstance(owner, str) for owner in owners)
                or len(set(owners)) != len(owners)):
            raise PlanError("delivery package needs distinct existing owning boundaries")
        for owner in owners:
            if (not isinstance(owner, str) or not owner or Path(owner).is_absolute()
                    or ".." in Path(owner).parts or ROOT not in (ROOT / owner).resolve().parents
                    or not (ROOT / owner).exists()):
                raise PlanError("delivery owner must be an existing repository path")
        cases = row["verification_cases"]
        if not isinstance(cases, list) or not cases:
            raise PlanError("delivery package needs discriminating verification cases")
        case_ids = set()
        for case in cases:
            if (not isinstance(case, dict) or set(case) != {"id", "proof_level", "scenario", "pass_condition", "negative_control"}
                    or any(not isinstance(case[field], str) or not case[field].strip() for field in case)):
                raise PlanError("verification case fields are incomplete or unknown")
            if not re.fullmatch(re.escape(row["id"]) + r"-T[0-9]{2}", case["id"]) or case["id"] in case_ids:
                raise PlanError("verification cases need unique package-bound identifiers")
            if case["proof_level"] not in ("source_review", "local_contract", "real_provider", "end_to_end", "operational_drill", "held_out_comparison"):
                raise PlanError("verification proof level must distinguish fixtures from live outcomes")
            case_ids.add(case["id"])
        packages[row["id"]] = row
    visited = set()
    def visit(identity, active):
        if identity not in packages or identity in active:
            raise PlanError("unknown or cyclic delivery dependency")
        if identity in visited:
            return
        for dependency in packages[identity]["depends_on"]:
            visit(dependency, active | {identity})
        visited.add(identity)
    for identity in packages:
        visit(identity, set())
    benefits = plan.get("launch_benefits", [])
    if not isinstance(benefits, list):
        raise PlanError("launch benefits must be a list")
    seen = set()
    for row in benefits:
        if not isinstance(row, dict) or set(row) != {"id", "title", "draft", "state", "steps", "evidence_needed"}:
            raise PlanError("launch benefit fields are incomplete or unknown")
        if any(not isinstance(row[field], str) or not row[field].strip()
               for field in ("id", "title", "draft", "evidence_needed")):
            raise PlanError("launch benefit needs meaningful text and evidence requirements")
        if row["id"] in seen or row["state"] != "draft_requires_qualification":
            raise PlanError("launch benefits are distinct drafts, not accepted public claims")
        if (not isinstance(row["steps"], list) or not row["steps"]
                or any(not isinstance(key, str) or key not in steps for key in row["steps"])):
            raise PlanError("launch benefit needs known owning steps")
        seen.add(row["id"])


def eligible_steps(data: dict, *, track: str = "launch") -> list[dict]:
    by_id = validate(data)
    plan = data["continuation"]
    decisions = {row["id"]: row for row in plan["decisions"]}
    verified = set(plan["eligible_dependency_states"])

    def dependency_verified(identity):
        row = by_id[identity]
        return (row["status"] in verified and bool(row.get("evidence"))
                and all(dependency_verified(dep) for dep in row.get("depends_on", [])))

    chosen = []
    for identity in plan[f"{track}_order"]:
        step = by_id[identity]
        if step["status"] != "ready":
            continue
        if not all(dependency_verified(dep) for dep in step.get("depends_on", [])):
            continue
        if any(decisions[key].get("state") != "authorized"
               or not decisions[key].get("evidence")
               for key in step.get("authority_requirements", [])):
            continue
        chosen.append(step)
    return chosen


def gate_status(data: dict, gate: dict) -> str:
    """Report recorded evidence without deriving a pass from task counts."""
    by_id = validate(data)
    verified = set(data["continuation"]["eligible_dependency_states"])
    if any(by_id[key]["status"] not in verified or not by_id[key].get("evidence")
           for key in gate["steps"]):
        return "Not verified: required work remains"
    review = gate.get("review", {})
    if (review.get("result") != "passed" or not review.get("evidence")
            or not review.get("source_revision") or not review.get("reviewer")):
        return "Not verified: release evidence needs review"
    return "Recorded pass; check evidence and source freshness before release"


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(data: dict, digest: str, root: Path = ROOT) -> str:
    by_id = validate(data)
    plan = data["continuation"]
    artifact = root / plan["artifact"]

    def link(path, label):
        relative = Path(os.path.relpath(root / path, artifact.parent)).as_posix()
        return f"[{label}]({relative})"

    lines = ["# Continuation status", "", "Kind: generated planning artifact.", "",
             "Source: `roadmap.yaml`. Regenerate with",
             "`python tools/build_continuation_status.py`; `--check` rejects a stale view.", "",
             f"Plan fingerprint: `{digest}`.", "",
             f"Started: {plan['started_at']}. Historical target: {plan['target_at']}. This is not a release forecast.", "",
             plan["outcome"], "",
             link(plan["plan"], "Execution plan") + " | " +
             link("docs/guides/hosting-and-deployment-procedures.md", "Hosting procedures") + " | " +
             link("docs/guides/launch-owner-checklist.md", "Owner checklist") + " | " +
             link("docs/guides/product-style-guide.md", "Style guide"), "",
             "## Next eligible work", ""]
    for track in ("launch", "improvement"):
        eligible = eligible_steps(data, track=track)
        summary = "; ".join(f"{s['id']}: {s['title']}" for s in eligible)
        lines.append(f"- {track.capitalize()}: {summary or 'none currently ready; review dependencies and authority'}.")
    lines.extend(["", "## Work in progress", "",
                  "These steps are already being built. They are not completed dependencies or permission to deploy.", "",
                  "| Step | Current evidence | Next local work |", "|---|---|---|"])
    active = [by_id[identity] for identity in plan["launch_order"] + plan["improvement_order"]
              if by_id[identity]["status"] == "building"]
    for step in active:
        lines.append(f"| {step['id']} | {cell(step.get('evidence') or 'No evidence recorded')} | "
                     f"{cell(step.get('next_local_work') or 'Continue the declared acceptance checks')} |")
    if not active:
        lines.append("| none | No active implementation recorded | Select authorized eligible work |")
    lines.extend(["", "## Release gates", "",
                  "A completed planning task, import, or published module does not establish a release gate.", "",
                  "| Gate | State | Required steps |", "|---|---|---|"])
    for gate in plan["launch_gates"]:
        lines.append(f"| {cell(gate['title'])} | {gate_status(data, gate)} | {', '.join(gate['steps'])} |")
    lines.extend(["", "## Delivery packages", "", plan.get("delivery_planning_note", "Planning only."), ""])
    for row in plan.get("delivery_batches", []):
        lines.extend([f"### {row['id']}: {row['title']}", "",
                      f"Owning steps: {', '.join(row['steps'])}. Acceptance dependencies: {', '.join(row['depends_on']) or 'none'}.", "",
                      "Owning boundaries: " + "; ".join(f"`{path}`" for path in row["owning_paths"]) + ".", "",
                      *[f"- {action}" for action in row["actions"]], "",
                      f"Complete when: {row['acceptance']}", "",
                      f"Failure control: {row['adversarial']}", "",
                      f"Authority: {row['authority_note']}", "",
                      f"Rollback or safe stop: {row['rollback']}", "",
                      "Verification cases are required evidence, not recorded passes.", "",
                      "| Case | Evidence level | Scenario | Pass condition | Negative control |",
                      "|---|---|---|---|---|"])
        for case in row["verification_cases"]:
            lines.append("| " + " | ".join(cell(case[field]) for field in ("id", "proof_level", "scenario", "pass_condition", "negative_control")) + " |")
        lines.append("")
    lines.extend(["## Launch benefit drafts", "", "These are proposed messages, not qualified performance claims.", ""])
    for row in plan.get("launch_benefits", []):
        lines.extend([f"### {row['title']}", "", row["draft"], "",
                      f"Required evidence: {row['evidence_needed']}", "",
                      f"Owning steps: {', '.join(row['steps'])}.", ""])
    lines.extend(["## Original planning windows", "",
                  "Historical planning targets, not a current schedule, release forecast or completion evidence.", "",
                  "| Hours from start | Work | Steps |", "|---|---|---|"])
    for row in plan["milestones"]:
        lines.append(f"| {row['hours'][0]} to {row['hours'][1]} | {cell(row['title'])} | {', '.join(row['steps'])} |")
    for title, track in (("Launch work", "launch"), ("Continued improvements", "improvement")):
        lines.extend(["", f"## {title}", "", "| Step | Deliverable | Status | Dependencies |", "|---|---|---|---|"])
        for identity in plan[f"{track}_order"]:
            step = by_id[identity]
            lines.append(f"| {identity} | {cell(step['title'])} | {step['status']} | {', '.join(step.get('depends_on', [])) or 'none'} |")
    lines.extend(["", "## Every retained initiative", "",
                  "Legacy statuses remain historical component claims until current integration evidence is recorded.", "",
                  "| Workstream | Earlier steps | Continuation steps |", "|---|---|---|"])
    for stream in plan["workstreams"]:
        lines.append(f"| {cell(stream['title'])} | {', '.join(stream['legacy_steps'])} | {', '.join(stream['continuation_steps'])} |")
    lines.extend(["", "## Hosting coverage", "",
                  "Documented procedures are preparation, not live deployment qualification.", "",
                  "| Target | Status | Procedure |", "|---|---|---|"])
    for target in plan["hosting_targets"]:
        procedure = f"../guides/hosting-and-deployment-procedures.md#{target['procedure']}"
        lines.append(f"| {cell(target['title'])} | {target['status']} | [Routine]({procedure}) |")
    lines.extend(["", "## Decisions and independent work", ""])
    for decision in plan["decisions"]:
        lines.extend([f"- `{decision['id']}`: {decision['state']}. {decision['requirement']}",
                      f"  Independent work: {decision['independent_work']}"])
    lines.extend(["", "## Activity", ""])
    for entry in plan["activity"]:
        lines.append(f"- {entry['at']}: {entry['event']}. {entry['outcome']} Evidence: {entry['evidence']}")
    lines.extend(["", "## Earlier artifact", "",
                  f"[Claude System Map]({plan['previous_artifact']}) remains the recovered historical view.",
                  "This repository artifact is maintained from the plan. Editing the hosted Claude copy",
                  "requires a connected editing surface; this generator does not publish it.", ""])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--roadmap", type=Path, default=ROADMAP)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--next", action="store_true")
    args = parser.parse_args(argv)
    raw = args.roadmap.read_bytes()
    try:
        data = yaml.safe_load(raw)
        validate(data)
        if args.next:
            print(json.dumps({track: [s["id"] for s in eligible_steps(data, track=track)]
                              for track in ("launch", "improvement")}))
            return 0
        text = render(data, hashlib.sha256(raw).hexdigest())
    except (PlanError, KeyError, TypeError, yaml.YAMLError) as exc:
        parser.exit(2, f"Invalid continuation plan: {exc}\n")
    output = args.output or ROOT / data["continuation"]["artifact"]
    if args.check:
        if not output.is_file() or output.read_text("utf-8") != text:
            print(f"{output} is stale; regenerate it")
            return 1
        print(f"{output} is current")
        return 0
    output.write_text(text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
