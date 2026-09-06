"""Hydrated prior material used by the offline stage-assistance fixture.

The body is deliberately generic and cross-task. It supplies a response
program, a context plan, and a verified local outcome without granting
authority or acting as an instruction.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from loop_engine.core.solve_control_manifest import (
    CONTROL_COMPONENT_IDS,
    ControlComponentRecord,
    PublicSolveControlManifest,
)
from loop_engine.core.stage_assistance_material import (
    StageAssistanceMaterial,
    StageAssistanceMaterialDraft,
)
from loop_engine.core.stage_evidence_records import StageRetrievalCandidate

CONTROL_HISTORY_PROBE = "CONTROL_MANIFEST_PRIOR_TEXT_MUST_NOT_ENTER_PROMPT"
PROJECT_SOURCE = (
    "from pathlib import Path\n"
    "Path('output.txt').write_text('done\\n', encoding='utf-8')\n"
)
REJECTED_PROJECT_SOURCE = PROJECT_SOURCE.replace("'done\\n'", "'wrong\\n'")
INDEPENDENT_PROBE_SOURCE = (
    "import json, subprocess, sys, tempfile\n"
    "from pathlib import Path\n"
    "subject = Path('subject').resolve()\n"
    "def text_or_none(path):\n"
    "    return path.read_text(encoding='utf-8') if path.is_file() else None\n"
    "with tempfile.TemporaryDirectory(prefix='paired-oracle-') as root:\n"
    "    result = subprocess.run([sys.executable, str(subject / 'main.py')],\n"
    "        cwd=root, capture_output=True, text=True, timeout=10)\n"
    "    print(json.dumps({'exit_code': result.returncode,\n"
    "        'regenerated': text_or_none(Path(root) / 'output.txt'),\n"
    "        'delivered': text_or_none(subject / 'output.txt')}))\n"
)


def fixture_verification_response(prompt: str) -> str | None:
    """Fixed independent oracle data, not an answer chosen from task results."""
    try:
        packet = json.loads(prompt)
    except (TypeError, ValueError):
        return None
    if not isinstance(packet, dict):
        return None
    kind = packet.get("record_type")
    if kind == "independent_probe_design/v1":
        value = {
            "status": "ready", "notes": "Observe delivery and regeneration independently.",
            "files": [{"path": "checks/probe.py", "content": INDEPENDENT_PROBE_SOURCE}],
            "cases": [{
                "case_id": "delivery_and_regeneration",
                "criterion_refs": ["criterion:0", "criterion:1"],
                "purpose": "Read the frozen output and regenerate it in an empty directory.",
                "argv": ["python", "checks/probe.py"], "timeout_seconds": 15,
                "comparison": "json_equal",
                "expected": {"exit_code": 0, "regenerated": "done\n", "delivered": "done\n"},
            }],
        }
    elif kind == "independent_probe_review/v1":
        value = {
            "valid": True, "criterion_refs": ["criterion:0", "criterion:1"],
            "issues": [],
            "notes": "Fixed fixture oracle checks exact task text and fresh execution.",
        }
    else:
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def fixture_execute(request, _context) -> dict:
    """Execute only these authored fixtures; Docker metadata is injected.

    This exercises frozen-subject reading and controller comparisons with real
    local Python output. It is not a sandbox qualification or a general host
    executor. Unknown code and command shapes are refused before execution.
    """
    from loop_engine.core.workspace_backends import RestrictedLocalWorkspace
    from loop_engine.core.workspace_contracts import CommandRequest, WorkspaceSpec

    files = tuple((item.path, item.content) for item in request.manifest.files)
    if request.read_only_execution:
        expected_files = (("checks/probe.py", INDEPENDENT_PROBE_SOURCE),)
        if files != expected_files:
            raise ValueError("unknown independent fixture source")
        supplied = {item.path: item.content for item in request.input_artifacts}
        if (set(supplied) != {"subject/main.py", "subject/output.txt"}
                or supplied["subject/main.py"] not in (
                    PROJECT_SOURCE.encode(), REJECTED_PROJECT_SOURCE.encode())):
            raise ValueError("unknown independent fixture subject")
        expected_command = ("python", "checks/probe.py")
    else:
        if (len(files) != 1 or files[0][0] != "main.py"
                or files[0][1] not in (PROJECT_SOURCE, REJECTED_PROJECT_SOURCE)
                or request.input_artifacts):
            raise ValueError("unknown generated fixture source")
        expected_command = ("python", "main.py")
    if (len(request.manifest.commands) != 1
            or request.manifest.commands[0].argv != expected_command):
        raise ValueError("unknown fixture command")
    root = Path(request.workspace_root)
    root.mkdir(parents=True, exist_ok=False)
    for item in request.input_artifacts:
        path = root / item.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(item.content)
    for item in request.manifest.files:
        path = root / item.path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item.content, encoding="utf-8")
    workspace = RestrictedLocalWorkspace(WorkspaceSpec(
        "trusted_stage_assistance_fixture", str(root), execution_enabled=True,
        allowed_commands=(sys.executable,)))
    command = request.manifest.commands[0]
    result = workspace.command(CommandRequest(
        (sys.executable, *command.argv[1:]),
        timeout_seconds=command.timeout_seconds, execution_authorized=True))
    commands = [{"argv": list(command.argv), "purpose": command.purpose,
                 "ok": result.ok, "exit_code": result.exit_code,
                 "stdout": result.stdout, "stderr": result.stderr,
                 "output_truncated": result.output_truncated,
                 "error_code": result.error_code}]
    artifacts = []
    for artifact in request.manifest.expected_artifacts:
        path = root / artifact.path
        raw = path.read_bytes() if path.is_file() else b""
        artifacts.append({
            "path": artifact.path, "media_type": artifact.media_type,
            "minimum_bytes": artifact.minimum_bytes, "present": path.is_file(),
            "byte_count": len(raw), "digest": hashlib.sha256(raw).hexdigest(),
            "error_code": "", "verified": path.is_file() and len(raw) >= artifact.minimum_bytes,
        })
    return {
        "record_type": "generated_project_execution/v1",
        "manifest_digest": request.manifest.digest, "workspace_path": str(root),
        "workspace": {"workspace_id": "fixture", "backend_kind": "restricted_local", "root": str(root)},
        "sandbox": {"backend_kind": "docker", "workspace_read_only": request.read_only_execution,
                    "network_policy": "none", "image": request.image,
                    "execution_evidence_state": "INJECTED_CONTRACT_FIXTURE_ONLY",
                    "actual_backend": "restricted_local_trusted_fixture"},
        "writes": [], "commands": commands, "artifacts": artifacts,
        "deterministic_checks_passed": result.ok and all(item["verified"] for item in artifacts),
    }


def fixture_control_manifest(
    source_state_digest: str,
) -> PublicSolveControlManifest:
    """Describe why this injected-provider comparison is mechanism-only."""
    unresolved = {
        "runtime_definition": ("dirty_runtime_build_digest",),
        "model_execution": ("arm_specific_injected_response_queue",),
        "execution_environment": ("project_executor_implementation_digest",),
        "evaluation": ("independent_evaluator_identity",),
        "workspace_isolation": ("initial_workspace_content_digest",),
        "observer_sinks": ("progress_callback_implementation_digest",),
    }
    components = tuple(ControlComponentRecord.create(
        name, "unknown" if name in unresolved else "exact",
        {"fixture": "stage_assistance_public_solve/v2", "component": name,
         **({"source_state_digest": source_state_digest}
            if name == "task_and_source" else {}),
         **({"contamination_probe": CONTROL_HISTORY_PROBE}
            if name == "runtime_definition" else {})},
        unresolved.get(name, ())) for name in CONTROL_COMPONENT_IDS)
    blocking = tuple(field for name in CONTROL_COMPONENT_IDS
                     for field in unresolved.get(name, ()))
    return PublicSolveControlManifest(
        "stage-assistance-offline-fixture", "mechanism_only",
        components, blocking)


def fixture_material(
    candidate: StageRetrievalCandidate,
    index: int,
) -> StageAssistanceMaterial:
    return StageAssistanceMaterial.create(
        StageAssistanceMaterialDraft(
            material_ref=f"stage-material:fixture:{index}",
            candidate_ref=candidate.candidate_ref,
            source_occurrence_ref=candidate.source_occurrence_ref,
            semantic_signature=candidate.semantic_signature,
            hydration_level="L2",
            material_kind="response_program_and_context_plan",
            content={
                "source_candidate_ref": candidate.candidate_ref,
                "semantic_stage_signature": candidate.semantic_signature,
                "prior_stage_summary": (
                    "A bounded artifact stage succeeded after preserving an exact "
                    "output contract and independent file verification."
                ),
                "response_program_candidate": {
                    "required_sections": [
                        "candidate action",
                        "expected observation",
                        "verification",
                    ]
                },
                "context_plan_candidate": {
                    "include": ["task contract", "latest state", "artifact checks"],
                    "exclude": ["unrelated parent-task details"],
                },
                "known_local_outcome": "verified",
            },
            source_evidence_refs=(
                "run-history:fixture:prior",
                "stage-outcome:fixture:locally-verified",
            ),
        )
    )


def fixture_lineage_summary(result: dict) -> dict:
    action_links = tuple(result.get("stage_action_links", ()))
    execution_links = tuple(result.get("stage_execution_links", ()))
    outcome_links = tuple(result.get("stage_outcome_links", ()))
    assistance = result.get("intelligence", {}).get("stage_assistance", {})
    exact_chain = bool(
        len(action_links) == len(execution_links) == len(outcome_links) == 1
        and action_links[0].get("action_occurrence_ref")
        == execution_links[0].get("action_occurrence_ref")
        == outcome_links[0].get("action_occurrence_ref")
        and execution_links[0].get("execution_ref")
        == outcome_links[0].get("execution_ref")
        and action_links[0].get("stage_occurrence_id")
        == execution_links[0].get("stage_occurrence_id")
        == outcome_links[0].get("stage_occurrence_id")
        and outcome_links[0].get("verifier_stage_occurrence_id")
        and outcome_links[0].get("verifier_semantic_call_id")
        and outcome_links[0].get("verifier_stage_occurrence_id")
        != outcome_links[0].get("stage_occurrence_id"))
    return {
        "selected_action_link_records": len(action_links),
        "action_execution_link_records": len(execution_links),
        "action_outcome_link_records": len(outcome_links),
        "linked_action_ids": sorted({
            str(item.get("action_id") or "")
            for item in (*action_links, *execution_links, *outcome_links)
            if item.get("action_id")
        }),
        "linked_stage_occurrence_ids": sorted({
            str(item.get("stage_occurrence_id") or "")
            for item in (*action_links, *execution_links, *outcome_links)
            if item.get("stage_occurrence_id")
        }),
        "direct_local_verification_passed": bool(outcome_links)
        and all(item.get("local_verification") is True for item in outcome_links),
        "outcome_attribution_methods": sorted({
            str(item.get("attribution_method") or "")
            for item in outcome_links
            if item.get("attribution_method")
        }),
        "exact_occurrence_chain_complete": exact_chain,
        "attribution_confidence_unknown": bool(outcome_links)
        and all(item.get("attribution_confidence") is None
                for item in outcome_links),
        "control_manifest_ref": assistance.get("control_manifest_ref", ""),
        "control_manifest_digest": assistance.get(
            "control_manifest_digest", ""),
        "control_set_digest": assistance.get("control_set_digest", ""),
        "control_evidence_class": assistance.get(
            "control_evidence_class", "unrecorded"),
        "control_blocking_unknowns": assistance.get(
            "control_blocking_unknowns", []),
    }


def fixture_lineage_is_complete(arm: dict) -> bool:
    return bool(
        arm.get("stage_credit_known") == 1
        and arm.get("selected_action_link_records") == 1
        and arm.get("action_execution_link_records") == 1
        and arm.get("action_outcome_link_records") == 1
        and arm.get("direct_local_verification_passed")
        and arm.get("exact_occurrence_chain_complete")
        and arm.get("attribution_confidence_unknown")
        and arm.get("outcome_attribution_methods")
        == ["DIRECT_LOCAL_VERIFIER"]
    )


__all__ = (
    "CONTROL_HISTORY_PROBE",
    "fixture_control_manifest",
    "fixture_lineage_is_complete",
    "fixture_lineage_summary",
    "fixture_material",
)
