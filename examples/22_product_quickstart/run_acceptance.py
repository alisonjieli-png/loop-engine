"""Run four product tasks through one generic solver and real Docker effects."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from loop_engine.code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution)
from loop_engine.code_nodes.solve_runtime import SolveRequest, solve_task
from loop_engine.core.adaptive_practitioner_records import NextActionDecision
from loop_engine.templates.intake import TaskIntakeRequest, intake_task


def _orientation(summary: str, outputs: list[str]) -> dict:
    return {
        "original_task_ref": "replaced_by_runtime",
        "task_summary": summary,
        "ultimate_goal": "Return the requested verified artifacts.",
        "immediate_goal": "Build, execute, and verify the requested result.",
        "current_state": "The task and permitted local inputs are available.",
        "desired_state": "Every requested artifact exists and passes verification.",
        "inputs": ["original task", "permitted local inputs"],
        "outputs": outputs, "operator_bundle": ["generate", "execute", "verify"],
        "response_contract": "artifacts plus execution and verification evidence",
        "decision_consumer": "requesting user", "explicit_constraints": [],
        "inferred_constraints": ["keep all effects inside the workspace"],
        "non_goals": [], "knowns": ["real artifacts are required"],
        "unknowns": [], "assumptions": [], "ambiguities": [],
        "delegated_choices": ["internal implementation details"],
        "safe_defaults": ["standard library Python"],
        "blocking_questions": [], "research_questions": [],
        "subproblems": ["construct", "execute", "verify"],
        "dependencies": ["construct before execute", "execute before verify"],
        "parallel_candidates": [], "candidate_profiles": ["practitioner.solver"],
        "candidate_capabilities": ["core.generated_project"],
        "verification_obligations": [
            "all declared commands meet their expected exit contracts",
            "every requested artifact exists and opens"],
        "confidence_profile": {"overall": 0.9},
        "proposed_next_action": "Build the project in the confined workspace.",
    }


def _decision() -> dict:
    return {
        "action_kind": "BUILD_CAPABILITY",
        "goal": "Produce the requested verified artifacts.",
        "reason": "The task requires real local files and execution evidence.",
        "inputs": {}, "expected_output": "Verified project artifacts.",
        "required_capabilities": ["core.generated_project"],
        "permissions": ["workspace_write", "sandbox_command"],
        "budget": {"estimated_cost": 1.0, "risk": 0.1, "reversibility": 1.0},
        "dependencies": [], "scheduling": "sequential",
        "verification": "Run commands and inspect every expected artifact.",
        "return_destination": "requesting user", "confidence": 0.9,
        "fallback": {"action_kind": "REPAIR"},
    }


def _action_id(decision: dict) -> str:
    record = NextActionDecision.from_mapping(decision)
    body = json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
    return "action:" + hashlib.sha256(body.encode()).hexdigest()[:20]


def _answers(summary: str, outputs: list[str], candidate: dict,
             files: dict[str, str]) -> tuple[str, ...]:
    decision = _decision()
    how = {
        "action_id": _action_id(decision), "how_mode": "generate",
        "act_mode": "run_dag", "capability_ref": "core.generated_project",
        "arguments": {}, "steps": ["create", "execute", "verify"],
        "spawned_tasks": [], "rationale": "Use the registered project capability.",
    }
    verification = {
        "verdict": "accept", "best_index": 0, "scores": [1.0],
        "notes": "Commands met their exit contracts and artifacts passed inspection.",
        "remaining_gaps": [], "advisory_findings": [],
        "new_requirement_proposals": [],
    }
    route = {"route": "stop_success", "reason": "Artifacts are verified."}
    sequence = [
        _orientation(summary, outputs), {"actions": [decision]}, how, candidate]
    sequence.extend({"path": path, "content": content}
                    for path, content in files.items())
    sequence.extend((verification, route))
    return tuple(json.dumps(item) for item in sequence)


def _task_a() -> tuple[TaskIntakeRequest, tuple[str, ...]]:
    task = (
        "Create a Python command-line program that reads a JSON file of "
        "expenses, totals spending by category, writes a Markdown report, "
        "and includes runnable verification.")
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "expense_report_tool",
        "summary": "Expense report command and verified Markdown output.",
        "files": [
            {"path": "expense_report.py", "purpose": "Implement the command.",
             "acceptance": ["Reads JSON and writes a category report."]},
            {"path": "verify.py", "purpose": "Exercise the command.",
             "acceptance": ["Checks exact category totals."]}],
        "commands": [{"argv": ["python", "verify.py"],
                      "purpose": "Run end-to-end verification.",
                      "timeout_seconds": 30, "command_kind": "verify",
                      "network_access": False, "expected_exit_codes": [0]}],
        "expected_artifacts": [
            {"path": "expense_report.py", "media_type": "text/x-python",
             "minimum_bytes": 1},
            {"path": "report.md", "media_type": "text/markdown",
             "minimum_bytes": 1}],
    }
    files = {
        "expense_report.py": '''import argparse\nimport json\nfrom collections import defaultdict\nfrom pathlib import Path\n\ndef main():\n    parser = argparse.ArgumentParser()\n    parser.add_argument("input")\n    parser.add_argument("output")\n    args = parser.parse_args()\n    rows = json.loads(Path(args.input).read_text())\n    totals = defaultdict(float)\n    for row in rows:\n        totals[str(row["category"])] += float(row["amount"])\n    lines = ["# Expense report", ""]\n    lines += [f"- {name}: {totals[name]:.2f}" for name in sorted(totals)]\n    Path(args.output).write_text("\\n".join(lines) + "\\n")\n\nif __name__ == "__main__":\n    main()\n''',
        "verify.py": '''import json\nimport subprocess\nimport sys\nfrom pathlib import Path\nrows = [{"category": "Food", "amount": 12.5}, {"category": "Travel", "amount": 8}, {"category": "Food", "amount": 2.5}]\nPath("sample.json").write_text(json.dumps(rows))\nsubprocess.run([sys.executable, "expense_report.py", "sample.json", "report.md"], check=True)\nreport = Path("report.md").read_text()\nassert "Food: 15.00" in report and "Travel: 8.00" in report\nprint("expense report verified")\n''',
    }
    return TaskIntakeRequest(text=task), _answers(
        "Build and verify an expense report command.",
        ["Python command", "Markdown report"], candidate, files)


def _task_b(fixtures: Path) -> tuple[TaskIntakeRequest, tuple[str, ...]]:
    goal = (
        "Normalize product names in the supplied CSV, mark rows with quantity "
        "five or lower as low stock, and write a cleaned CSV plus a summary.")
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "inventory_transform",
        "summary": "Cleaned inventory and low-stock summary.",
        "files": [
            {"path": "transform.py", "purpose": "Transform the supplied CSV.",
             "acceptance": ["Preserves rows and marks low stock."]},
            {"path": "verify.py", "purpose": "Verify transformed outputs.",
             "acceptance": ["Checks names, row count, and flags."]}],
        "commands": [
            {"argv": ["python", "transform.py"], "purpose": "Create outputs.",
             "timeout_seconds": 30, "command_kind": "execute",
             "network_access": False, "expected_exit_codes": [0]},
            {"argv": ["python", "verify.py"], "purpose": "Verify outputs.",
             "timeout_seconds": 30, "command_kind": "verify",
             "network_access": False, "expected_exit_codes": [0]}],
        "expected_artifacts": [
            {"path": "cleaned.csv", "media_type": "text/csv", "minimum_bytes": 1},
            {"path": "summary.md", "media_type": "text/markdown", "minimum_bytes": 1}],
    }
    files = {
        "transform.py": '''import csv\nfrom pathlib import Path\nsource = Path("inputs/inventory.csv")\nwith source.open(newline="") as stream:\n    rows = list(csv.DictReader(stream))\nfor row in rows:\n    row["product_name"] = " ".join(row["product_name"].split()).title()\n    row["low_stock"] = "yes" if int(row["quantity"]) <= 5 else "no"\nwith Path("cleaned.csv").open("w", newline="") as stream:\n    writer = csv.DictWriter(stream, fieldnames=[*rows[0].keys()])\n    writer.writeheader(); writer.writerows(rows)\nlow = [row for row in rows if row["low_stock"] == "yes"]\nPath("summary.md").write_text(f"# Inventory summary\\n\\nRows: {len(rows)}\\n\\nLow stock: {len(low)}\\n")\n''',
        "verify.py": '''import csv\nfrom pathlib import Path\nwith Path("cleaned.csv").open(newline="") as stream:\n    rows = list(csv.DictReader(stream))\nassert len(rows) == 3\nassert rows[0]["product_name"] == "Blue Widget"\nassert [row["low_stock"] for row in rows] == ["yes", "no", "yes"]\nassert "Low stock: 2" in Path("summary.md").read_text()\nprint("inventory verified")\n''',
    }
    return TaskIntakeRequest(dataset=str(fixtures / "inventory.csv"), goal=goal), _answers(
        "Transform and verify a supplied inventory table.",
        ["cleaned CSV", "summary"], candidate, files)


def _task_c(fixtures: Path) -> tuple[TaskIntakeRequest, tuple[str, ...]]:
    goal = (
        "Inspect the supplied Markdown folder and create an index containing "
        "each title, headings, file path, and a short summary.")
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "document_index",
        "summary": "Verified index of supplied Markdown documents.",
        "files": [
            {"path": "index_docs.py", "purpose": "Build the document index.",
             "acceptance": ["Includes every supplied Markdown file."]},
            {"path": "verify.py", "purpose": "Verify index coverage.",
             "acceptance": ["Checks titles, headings, paths, and summaries."]}],
        "commands": [
            {"argv": ["python", "index_docs.py"], "purpose": "Create index.",
             "timeout_seconds": 30, "command_kind": "execute",
             "network_access": False, "expected_exit_codes": [0]},
            {"argv": ["python", "verify.py"], "purpose": "Verify index.",
             "timeout_seconds": 30, "command_kind": "verify",
             "network_access": False, "expected_exit_codes": [0]}],
        "expected_artifacts": [
            {"path": "index.md", "media_type": "text/markdown", "minimum_bytes": 1}],
    }
    files = {
        "index_docs.py": '''from pathlib import Path\nroot = Path("inputs/docs")\nsections = ["# Document index", ""]\nfor path in sorted(root.glob("*.md")):\n    text = path.read_text()\n    lines = text.splitlines()\n    title = next((line[2:] for line in lines if line.startswith("# ")), path.stem)\n    headings = [line.lstrip("# ") for line in lines if line.startswith("## ")]\n    paragraphs = [line for line in lines if line and not line.startswith("#")]\n    summary = paragraphs[0] if paragraphs else "No summary available."\n    sections += [f"## {title}", "", f"Path: {path.as_posix()}", "", f"Headings: {', '.join(headings)}", "", f"Summary: {summary}", ""]\nPath("index.md").write_text("\\n".join(sections))\n''',
        "verify.py": '''from pathlib import Path\ntext = Path("index.md").read_text()\nfor required in ("Alpha guide", "Beta notes", "Setup", "Verification", "inputs/docs/alpha.md", "inputs/docs/beta.md", "Summary:"):\n    assert required in text, required\nprint("document index verified")\n''',
    }
    return TaskIntakeRequest(repository=str(fixtures / "docs"), goal=goal), _answers(
        "Index and verify supplied Markdown documents.",
        ["Markdown document index"], candidate, files)


def _task_d(fixtures: Path) -> tuple[TaskIntakeRequest, tuple[str, ...]]:
    goal = (
        "Reproduce the supplied Python package failure, repair the package, "
        "rerun its verification, and return the repaired files.")
    candidate = {
        "record_type": "generated_project_candidate/v1",
        "project_id": "package_repair",
        "summary": "Reproduced failure, executable repair, and passing package.",
        "files": [{"path": "repair.py", "purpose": "Create a repaired copy.",
                   "acceptance": ["Applies a concrete source patch."]}],
        "commands": [
            {"argv": ["python", "inputs/failing_package/test_calc.py"],
             "purpose": "Reproduce the original failure.", "timeout_seconds": 30,
             "command_kind": "verify", "network_access": False,
             "expected_exit_codes": [1]},
            {"argv": ["python", "repair.py"], "purpose": "Apply repair.",
             "timeout_seconds": 30, "command_kind": "execute",
             "network_access": False, "expected_exit_codes": [0]},
            {"argv": ["python", "repaired_package/test_calc.py"],
             "purpose": "Verify the repaired package.", "timeout_seconds": 30,
             "command_kind": "verify", "network_access": False,
             "expected_exit_codes": [0]}],
        "expected_artifacts": [
            {"path": "repaired_package/calc.py", "media_type": "text/x-python",
             "minimum_bytes": 1}],
    }
    files = {
        "repair.py": '''from pathlib import Path\nsource = Path("inputs/failing_package")\ntarget = Path("repaired_package")\ntarget.mkdir()\noriginal = (source / "calc.py").read_text()\npatched = original.replace("return left - right", "return left + right")\nassert patched != original\n(target / "calc.py").write_text(patched)\n(target / "test_calc.py").write_text((source / "test_calc.py").read_text())\nprint("repair applied")\n''',
    }
    return TaskIntakeRequest(repository=str(fixtures / "failing_package"), goal=goal), _answers(
        "Repair and verify the supplied failing package.",
        ["repaired Python package"], candidate, files)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_root.resolve()
    if output.exists():
        if any(output.iterdir()):
            raise SystemExit("output root must be empty")
    else:
        output.mkdir(parents=True)
    fixtures = Path(__file__).resolve().parent / "fixtures"
    tasks = (_task_a(), _task_b(fixtures), _task_c(fixtures), _task_d(fixtures))
    records = []
    for index, (intake_request, answers) in enumerate(tasks, 1):
        task_id = chr(96 + index)
        run_root = output / f"task-{task_id}-runs"
        workspace = output / f"task-{task_id}-workspace"
        execution = fixture_model_execution(FixtureModelExecutionRequest(
            answers=answers, max_model_calls=len(answers)))
        outcome = solve_task(SolveRequest(
            intake_task(intake_request), model_execution=execution,
            runs_dir=str(run_root), interaction_mode="autonomous", max_passes=1,
            allow_workspace_writes=True, allow_sandbox_commands=True,
            workspace_root=str(workspace),
            allow_source_materialization_to_model=(index > 1)))
        value = outcome.to_dict()
        value["assurance_profile"] = {
            "model_semantics": "offline typed fixture, not live quality proof",
            "effects": "real Docker execution and real file inspection",
        }
        path = output / f"task-{task_id}.json"
        path.write_text(json.dumps(value, indent=2, default=str) + "\n")
        records.append(value)
        if not outcome.solved:
            raise SystemExit(f"task {task_id} failed: {outcome.failure_code}")
        if not all(Path(item["path"]).is_file() for item in value["artifacts"]):
            raise SystemExit(f"task {task_id} artifact is not readable")
    repair_commands = records[-1]["result"]["commands"]
    report = {
        "record_type": "product_acceptance/v1",
        "tasks": len(records), "completed_verified": sum(
            item["terminal_code"] == "COMPLETED_VERIFIED" for item in records),
        "unique_graph_digests": len({item["graph_digest"] for item in records}),
        "total_model_calls": sum(item["model_calls"] for item in records),
        "total_tool_calls": sum(item["tool_calls"] for item in records),
        "repair_reproduced_failure": repair_commands[0]["expectation_met"]
        and repair_commands[0]["exit_code"] == 1,
        "repair_verified": repair_commands[-1]["expectation_met"]
        and repair_commands[-1]["exit_code"] == 0,
        "limitations": [
            "Model semantics use a typed offline fixture in this acceptance run.",
            "A separate authorized live-provider solve is required."],
    }
    (output / "acceptance.json").write_text(
        json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
