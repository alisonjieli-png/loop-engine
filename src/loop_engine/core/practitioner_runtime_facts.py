"""Runtime facts the Practitioner states to the model instead of letting it guess.

Architectural role: one deterministic projection, rebuilt for every model
call, of facts the runtime already holds exactly: the admitted source
manifest, the workspace root, the execution isolation the run was granted,
the permissions in force, and the repeated-action fence view with every typed
capability rejection so far. The model reads them under ``runtime_facts``;
it cannot change them. This is the distillation principle applied to the
packet: whatever a deterministic tool can state exactly is stated exactly,
before any reasoning is spent on it.

Why it exists: two live runs spent their budgets on facts the runtime knew.
One guessed an absolute dataset path the source capability could never
admit; another stopped to ask which workspace path and packages it would
have. Both answers were already in the run's own state.

Owns:
    - runtime_facts(): the projection and its bounds.

Does not own: the source manifest (core.adaptive_practitioner_source), the
fence (core.action_fence), or where the projection is placed in the packet
(core.adaptive_practitioner).
"""
from __future__ import annotations

import hashlib

from ..templates.intake import CapturedInstructionProvenance
from .adaptive_practitioner_records import AdaptivePractitionerError
from .adaptive_practitioner_source import inventory_source_files, project_input_path
from .adaptive_practitioner_supervision import DEFAULT_SUPERVISION_POLICY
from .generated_project import selected_execution_backend
from .independent_verification import IndependentVerificationPolicy
from .runtime_capacity import (
    model_evidence_bytes,
    paths_within_allowance,
    supplied_input_ceiling,
)

RUNTIME_FACTS_RECORD_TYPE = "practitioner_runtime_facts/v1"

#: How many manifest paths travel inline is measured, not written down: the
#: run's own context budget states the bytes a heavy list may spend, and the
#: paths themselves state how long they are. Sixty short paths and six very
#: long ones cost the same, and a fixed count would be wrong for both. The
#: total and a digest are always present, so a trimmed list is never mistaken
#: for the whole manifest.


def _source_manifest(services) -> dict | None:
    request = services.request
    if not (request.allow_source_materialization_to_model
            and request.source_refs):
        return None
    try:
        inventory = inventory_source_files(services)
    except (AdaptivePractitionerError, OSError, ValueError):
        return None
    files = inventory.files
    paths = sorted(relative for relative, _path in files)
    digest = hashlib.sha256("\n".join(paths).encode("utf-8")).hexdigest()
    carried = paths[:paths_within_allowance(
        paths, model_evidence_bytes(services))]
    by_path = dict(files)
    sizes = {}
    for relative in carried:
        try:
            sizes[relative] = by_path[relative].stat().st_size
        except (KeyError, OSError):
            sizes[relative] = None
    binary = dict(inventory.materializable)
    binary_paths = sorted(binary)
    carried_binary = binary_paths[:paths_within_allowance(
        binary_paths, model_evidence_bytes(services))]
    binary_files = {}
    for relative in carried_binary:
        try:
            byte_count = binary[relative].stat().st_size
        except OSError:
            byte_count = None
        binary_files[relative] = {
            "sandbox_path": project_input_path(relative),
            "byte_count": byte_count}
    return {
        "paths": carried,
        "sandbox_paths": {relative: project_input_path(relative)
                          for relative in carried},
        "sandbox_input_files": binary_files,
        "sandbox_input_total": len(binary_paths),
        "sandbox_input_usage": (
            "these supplied files are binary, so they are never readable as "
            "text: select one with core.source.inspect paths to deliver it to "
            "a project, then open it at its sandbox_path with code that reads "
            "its format"),
        "byte_counts": sizes,
        "placement_capacity": supplied_input_ceiling(),
        "total": len(paths),
        "truncated": len(carried) < len(paths),
        "digest": digest,
        "usage": ("core.source.inspect admits exactly these relative paths; "
                  "call it with paths omitted to receive the manifest with "
                  "sizes, or with a subset of these paths for contents"),
        "sandbox_paths_usage": (
            "generated code runs in the workspace, not beside the source: "
            "open a file at its sandbox_paths value, never at its admitted "
            "path. These are the exact paths the runtime materializes, and "
            "byte_counts is what each one weighs. placement_capacity is "
            "what this machine measured it can materialize right now, with "
            "the memory and disk figures behind it; a source above it must "
            "be read some other way"),
    }


def _source_roles(services) -> dict | None:
    """The saved reading of the supplied files, marked as a reading."""
    record = getattr(services, "source_roles", None)
    if not isinstance(record, dict):
        return None
    return {**record, "usage": (
        "what this run read each supplied file to be, and the fields that "
        "reading rests on. It is a recorded reading, not authority: where "
        "what you observe contradicts a role, the observation wins and the "
        "contradiction is worth stating")}


def granted_permissions(request) -> tuple[str, ...]:
    """The permission names in force for this run, computed once here."""
    return tuple(name for name, allowed in (
        ("source_read", request.allow_source_materialization_to_model
         and bool(request.source_refs)),
        ("network_read", request.allow_network_reads),
        ("workspace_write", request.allow_workspace_writes),
        ("sandbox_command", request.allow_sandbox_commands)) if allowed)


def _captured_instruction(services) -> dict | None:
    """Project the validated text snapshot, never imply an external file read."""
    provenance = getattr(services.request, "instruction_provenance", None)
    if provenance is None:
        return None
    if type(provenance) is not CapturedInstructionProvenance:
        raise ValueError("instruction provenance must use its exact passive contract")
    provenance.validate_text(services.request.task)
    return {
        **provenance.to_dict(),
        "text_in_original_input": True,
        "inspection_required_for_instruction_text": False,
        "external_data_authority_unchanged": True,
    }


def runtime_facts(services) -> dict:
    """Exact, model-visible facts about this run. Never advisory."""
    from ..code_nodes.solve_terminal import (
        DEFAULT_RESOLUTION_COMPLETION_POLICY,
        resolution_input_contract,
    )
    from .outcome_vector import DEFAULT_OUTCOME_VECTOR_POLICY

    request = services.request
    policy = DEFAULT_SUPERVISION_POLICY.action_fence
    captured_instruction = _captured_instruction(services)
    return {
        "record_type": RUNTIME_FACTS_RECORD_TYPE,
        "authority": "runtime",
        "workspace_root": str(services.workspace_base),
        # Decided the way execution decides it. Reading the flag alone said
        # "host_process" whenever local execution was authorised, while
        # Docker — being available — took priority and ran the code in a
        # container. A run told the wrong machine writes code for it.
        "execution_isolation": selected_execution_backend(
            bool(request.allow_local_execution)),
        "granted_permissions": list(granted_permissions(request)),
        "interaction_mode": str(request.interaction_mode),
        "host_runtime": getattr(request, "host_runtime_manifest", {}),
        "host_permission_scope": (
            "Host descriptor permissions apply only to the selected host operations. "
            "They do not grant core capabilities or bypass exact host approval."),
        "execution_isolation_scope": "core.generated_project; registered hosts declare their own isolation",
        "resolution_completion_policy":
            DEFAULT_RESOLUTION_COMPLETION_POLICY.to_dict(),
        "outcome_vector_policy": DEFAULT_OUTCOME_VECTOR_POLICY.to_dict(),
        **_verification_facts(services),
        **({"captured_instruction": captured_instruction}
           if captured_instruction is not None else {}),
        "source_manifest": _source_manifest(services),
        "source_roles": _source_roles(services),
        "action_fence": services.action_fence.model_view(policy),
        "direct_resolution_input_contract": resolution_input_contract(),
    }


def _verification_facts(services) -> dict:
    """Acceptance gates and control actions never add user task criteria."""
    policy = getattr(services.request, "independent_verification_policy",
                     IndependentVerificationPolicy())
    if not isinstance(policy, IndependentVerificationPolicy):
        raise TypeError("verification policy must use its typed contract")
    from .adaptive_practitioner_result import (
        best_available_task_result, task_result_succeeded)
    presented = best_available_task_result(services)
    return {
        "independent_verification": {
            **policy.to_dict(), "authority": "runtime", "advisory": False,
            "adds_task_criteria": False,
            "unavailable_establishes_subject_failure": False,
            "interpretation": (
                "When required is true, this acceptance gate is runtime policy. Do not copy "
                "it into user verification_obligations. A provider or checker "
                "failure leaves checking incomplete; it does not require "
                "regenerating an otherwise unchanged project."),
        },
        "control_actions": [{
            "action_kind": "RETURN_RESULT", "authority": "runtime",
            "available": True, "required_capabilities": [],
            "permissions": [],
            "result_source": (
                "best_available_task_result" if presented is not None
                else "best_available_resolution_from_current_state"),
            "presented_attempt_number": (
                presented.get("attempt_number")
                if isinstance(presented, dict) else None),
            "presented_result_passed_checks": (
                task_result_succeeded(presented)
                if presented is not None else None),
            "direct_input_contract_ref":
                "runtime_facts.direct_resolution_input_contract",
            "runs_verification": True, "regenerates_project": False,
            "interpretation": (
                "Select RETURN_RESULT without capability requirements to submit "
                "an existing task result for verification, or to publish a "
                "best-available resolution when no further executable task work "
                "is possible. When a later attempt failed its checks, the "
                "submitted result is the latest earlier execution whose checks "
                "passed, so passing work can be verified again instead of being "
                "rewritten. A resolution must preserve useful analysis, explicit "
                "assumptions, missing pieces, provisional or analogous work, and "
                "next actions. Put those contributions in the exact resolution "
                "object named by direct_input_contract_ref. It cannot bypass "
                "required acceptance gates or claim that an external effect "
                "occurred."),
        }],
    }


def _presented_attempt_facts() -> tuple[bool, str]:
    """RETURN_RESULT names the attempt it would present and whether it passed."""
    from types import SimpleNamespace

    passing = {"record_type": "generated_project_execution/v1",
               "attempt_number": 1, "deterministic_checks_passed": True}
    failing = {**passing, "attempt_number": 2,
               "deterministic_checks_passed": False}
    regressed = _verification_facts(SimpleNamespace(
        request=SimpleNamespace(), task_results=[passing, failing]))[
            "control_actions"][0]
    unresolved = _verification_facts(SimpleNamespace(
        request=SimpleNamespace(), task_results=[failing]))["control_actions"][0]
    passed = (regressed["result_source"] == "best_available_task_result"
              and regressed["presented_attempt_number"] == 1
              and regressed["presented_result_passed_checks"] is True
              and unresolved["presented_attempt_number"] == 2
              and unresolved["presented_result_passed_checks"] is False
              and "verified again instead of being rewritten"
              in regressed["interpretation"])
    return passed, (f"after a failure presents attempt "
                    f"{regressed['presented_attempt_number']}; with no passing "
                    f"attempt presents {unresolved['presented_attempt_number']}")


def self_test() -> dict:
    """Prove the projection states the manifest and the fence exactly."""
    import tempfile
    from pathlib import Path
    from types import SimpleNamespace

    from .action_fence import ActionFenceLedger

    with tempfile.TemporaryDirectory(prefix="loop-engine-facts-") as root:
        source = Path(root) / "dataset"
        source.mkdir()
        for name in ("train.csv", "test.csv", "sample_submission.csv"):
            (source / name).write_text("id,target\n1,0\n", encoding="utf-8")
        request = SimpleNamespace(
            allow_source_materialization_to_model=True,
            source_refs=(str(source),), allow_network_reads=False,
            allow_workspace_writes=True, allow_sandbox_commands=True,
            allow_local_execution=True, interaction_mode="autonomous")
        services = SimpleNamespace(
            request=request, workspace_base=Path(root) / "work",
            action_fence=ActionFenceLedger())
        try:
            facts = runtime_facts(services)
        except AdaptivePractitionerError as exc:
            facts = {"error": str(exc)}
        closed = SimpleNamespace(
            request=SimpleNamespace(
                allow_source_materialization_to_model=False, source_refs=(),
                allow_network_reads=False, allow_workspace_writes=False,
                allow_sandbox_commands=False, allow_local_execution=False,
                interaction_mode="ask_when_material"),
            workspace_base=Path(root), action_fence=ActionFenceLedger())
        closed_facts = runtime_facts(closed)
        instruction_text = "supplied instruction"
        closed.request.task = instruction_text
        closed.request.instruction_provenance = CapturedInstructionProvenance(
            hashlib.sha256(instruction_text.encode()).hexdigest(),
            len(instruction_text.encode()), ("instruction-origin.txt",))
        instruction_facts = runtime_facts(closed)
        closed.request.task = "different instruction"
        invalid_capture_refused = False
        try:
            runtime_facts(closed)
        except ValueError:
            invalid_capture_refused = True
    manifest = facts.get("source_manifest") or {}
    paths = manifest.get("paths") or []
    tests = [{
        "test": "the_admitted_manifest_is_stated_before_any_model_call",
        "passed": (manifest.get("total") == 3 and manifest.get("truncated")
                   is False and all(not path.startswith("/")
                                    for path in paths)
                   and any(path.endswith("train.csv") for path in paths)),
        "detail": str(paths)[:120],
    }, {
        "test": "isolation_and_permissions_are_exact_not_guessed",
        # Compared against the executor's own decision rather than a
        # written-down answer: this check previously asserted "host_process"
        # whenever local execution was authorised, which is what the fact
        # wrongly reported while Docker, being available, took priority.
        "passed": (facts.get("execution_isolation")
                   == selected_execution_backend(True)
                   and facts.get("execution_isolation") in (
                       "container", "host_process")
                   and facts.get("granted_permissions")
                   == ["source_read", "workspace_write", "sandbox_command"]
                   and facts.get("authority") == "runtime"),
        "detail": str(facts.get("granted_permissions")),
    }, {
        "test": "both_path_spaces_are_stated_so_generated_code_cannot_drift",
        "passed": (
            bool(paths)
            and set(manifest.get("sandbox_paths") or {}) == set(paths)
            and all((manifest["sandbox_paths"][path]
                     == project_input_path(path))
                    and manifest["sandbox_paths"][path] != path
                    for path in paths)),
        "detail": str(manifest.get("sandbox_paths"))[:160],
    }, {
        "test": "the_saved_file_reading_is_stated_or_explicitly_absent",
        "passed": ("source_roles" in facts
                   and facts["source_roles"] is None
                   and closed_facts["source_roles"] is None),
        "detail": str(facts.get("source_roles")),
    }, {
        "test": "captured_instruction_is_available_without_external_source_authority",
        "passed": (instruction_facts["captured_instruction"]["text_in_original_input"]
                   and instruction_facts["captured_instruction"]["capture_method"]
                   == "provided_text"
                   and not instruction_facts["captured_instruction"][
                       "inspection_required_for_instruction_text"]
                   and instruction_facts["source_manifest"] is None
                   and instruction_facts["granted_permissions"] == []),
        "detail": "captured instruction text is not an unread dataset",
    }, {
        "test": "absent_or_rebound_instruction_provenance_is_not_a_capture_claim",
        "passed": ("captured_instruction" not in closed_facts
                   and "captured_instruction" not in facts
                   and invalid_capture_refused),
        "detail": "unknown provenance stays absent; changed text is refused",
    }, {
        "test": "verification_policy_is_runtime_authority_without_new_task_criteria",
        "passed": (facts["independent_verification"]["required"] is True
                   and facts["independent_verification"]["authority"] == "runtime"
                   and facts["independent_verification"]["advisory"] is False
                   and facts["independent_verification"]["adds_task_criteria"] is False
                   and facts["independent_verification"][
                       "unavailable_establishes_subject_failure"] is False),
        "detail": "provider failure leaves evaluation incomplete",
    }, {
        "test": "return_result_describes_reverification_without_regeneration",
        "passed": (facts["control_actions"][0]["action_kind"] == "RETURN_RESULT"
                   and closed_facts["control_actions"][0]["available"] is True
                   and closed_facts["control_actions"][0]["result_source"]
                   == "best_available_resolution_from_current_state"
                   and facts["control_actions"][0]["runs_verification"] is True
                   and facts["control_actions"][0]["regenerates_project"] is False
                   and facts["control_actions"][0]["required_capabilities"] == []),
        "detail": "the existing control action preserves mandatory verification",
    }, {
        "test": "return_result_presents_the_latest_passing_attempt_after_a_later_failure",
        "passed": _presented_attempt_facts()[0],
        "detail": _presented_attempt_facts()[1],
    }, {
        "test": "runtime_requires_a_best_available_resolution_before_task_stop",
        "passed": (facts["resolution_completion_policy"][
                       "require_resolution_before_task_level_stop"] is True
                   and "produce a pro forma analysis from the available values"
                   in facts["resolution_completion_policy"]["methods"]
                   and len(facts["resolution_completion_policy"][
                       "truth_constraints"]) >= 3),
        "detail": facts["resolution_completion_policy"]["policy_id"],
    }, {
        "test": "runtime_exposes_each_direct_resolution_contribution_field",
        "passed": set(facts["direct_resolution_input_contract"]["resolution"])
        == {
            "what_can_be_completed", "what_cannot_be_completed",
            "missing_inputs_or_components", "analysis", "assumptions",
            "scenario_analysis", "pro_forma_analysis", "synthetic_material",
            "estimates", "analogous_solutions", "first_principles_solutions",
            "supplemental_items", "next_actions",
            "constraint_code", "method_assessments",
        },
        "detail": "RETURN_RESULT can carry a structured direct resolution",
    }, {
        "test": "runtime_exposes_the_canonical_action_vector_stop_policy",
        "passed": (
            facts["outcome_vector_policy"][
                "continue_while_safe_authorized_work_remains"] is True
            and facts["outcome_vector_policy"][
                "response_admission_is_not_process_or_output_success"] is True
            and facts["outcome_vector_policy"][
                "evaluate_private_reasoning"] is False),
        "detail": facts["outcome_vector_policy"]["policy_id"],
    }, {
        "test": "no_source_authority_means_no_manifest_and_no_error",
        "passed": (closed_facts["source_manifest"] is None
                   and closed_facts["granted_permissions"] == []
                   and closed_facts["action_fence"]["fenced"] == []),
        "detail": closed_facts["execution_isolation"],
    }]
    return {"module": "core.practitioner_runtime_facts",
            "passed": all(item["passed"] for item in tests), "tests": tests}
