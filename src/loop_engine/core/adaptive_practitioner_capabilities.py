"""Compile one adaptive Practitioner capability action into a Solution graph.

The model selects a registered capability through ``NextActionDecision`` and
``ExecutionPlan``. This module creates a candidate Solution Canvas, validates
its authoritative ``LoopGraphDefinition``, executes it through Solution Loops,
and returns a typed result. It contains no task or domain routing.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from ..code_nodes.solution_canvas import SolutionLoopSpec, SolutionSpec
from ..code_nodes.solution_compiler import (
    compile_solution, render_canvas, run_compiled)
from ..code_nodes.solution_model_port import SolutionModelError
from ..loop.kernel import ExecutionPlan, PractitionerState, ResultPacket
from ..loop.encapsulate import as_practitioner_loop
from .adaptive_practitioner_records import (
    AdaptivePractitionerError, AdaptiveRunServices, ModelStepRequest,
    NextActionDecision)
from .generated_project import (
    ALLOWED_PYTHON_EXECUTABLES, DEFAULT_GENERATED_PROJECT_IMAGE,
    GeneratedProjectAuthority, GeneratedProjectCandidate,
    GeneratedProjectError, GeneratedProjectFile, GeneratedProjectFileSpec,
    GeneratedProjectExecutionContext, GeneratedProjectExecutionRequest,
    GeneratedProjectInputArtifact, GeneratedProjectManifest,
    validate_generated_project_input_use)
from .context_artifacts import ContextArtifactRef
from .web_fetch import WebFetchAuthority, WebFetchContext, WebFetchRequest
from .web_search import (
    WebSearchAuthority, WebSearchContext, WebSearchRequest)
from .adaptive_practitioner_orientation_capabilities import (
    environment_describe_operation, intelligence_search_operation)
from .adaptive_practitioner_source import (
    _resolve_requested_paths, inspectable_source_files,
    source_inspection_model_view, source_inspection_operation,
    source_profile_operation)


@dataclass(frozen=True)
class AdaptiveCapabilityExecutionRequest:
    """Current state, selected plan, and owning Practitioner Loop."""

    state: PractitionerState
    plan: ExecutionPlan
    owner_loop: object

    def __post_init__(self) -> None:
        if not isinstance(self.state, PractitionerState):
            raise AdaptivePractitionerError(
                "capability execution needs PractitionerState")
        if not isinstance(self.plan, ExecutionPlan):
            raise AdaptivePractitionerError(
                "capability execution needs ExecutionPlan")
        if (self.owner_loop is None
                or not getattr(self.owner_loop, "loop_id", "")
                or getattr(self.owner_loop, "ledger", None) is None):
            raise AdaptivePractitionerError(
                "capability execution needs an active owner Loop")


def _generated_file_checkpoint_identity(
        candidate: GeneratedProjectCandidate,
        file_spec: GeneratedProjectFileSpec,
        task: str) -> tuple[str, str]:
    """Bind reusable file content to its complete semantic file contract."""
    contract = {
        "task_digest": hashlib.sha256(task.encode("utf-8")).hexdigest(),
        "record_type": candidate.record_type,
        "active_file": file_spec.to_dict(),
        "all_files": [item.to_dict() for item in candidate.files],
        "commands": [item.to_dict() for item in candidate.commands],
        "expected_artifacts": [
            item.to_dict() for item in candidate.expected_artifacts],
    }
    contract_digest = hashlib.sha256(json.dumps(
        contract, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False).encode("utf-8")).hexdigest()
    checkpoint_key = "generated-file." + hashlib.sha256(json.dumps({
        "contract_digest": contract_digest,
        "path": file_spec.path,
    }, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return checkpoint_key, contract_digest


def build_action_canvas_candidate(
        decision_id: str, decision: NextActionDecision) -> dict:
    """Project one capability-bearing action into a passive candidate graph."""
    if not isinstance(decision, NextActionDecision):
        raise AdaptivePractitionerError(
            "candidate canvas needs NextActionDecision")
    if not decision.required_capabilities:
        return {
            "record_type": "solution_canvas_candidate/v1",
            "candidate_id": f"canvas:{decision_id}",
            "action_kind": decision.action_kind,
            "selected": False,
            "graph": None,
            "validation": {"valid": True, "violations": []},
            "note": "control action requires no executable capability graph",
        }
    capability_ref = decision.required_capabilities[0]
    spec = SolutionSpec(
        f"adaptive.candidate.{decision_id.replace(':', '_')}",
        permitted_loop_modes=("deterministic",),
        loops=(SolutionLoopSpec(
            "candidate_action", capability_ref,
            input_role="next_action_decision/v1",
            output_role="capability_result/v1",
            params={"action_kind": decision.action_kind,
                    "verification": decision.verification}),))
    return {
        "record_type": "solution_canvas_candidate/v1",
        "candidate_id": f"canvas:{decision_id}",
        "action_kind": decision.action_kind,
        "selected": False,
        "graph": spec.graph.to_dict(),
        "validation": spec.validate(),
    }


def _project_manifest(
        request: AdaptiveCapabilityExecutionRequest,
        services: AdaptiveRunServices,
        input_artifacts: tuple[GeneratedProjectInputArtifact, ...]
        ) -> GeneratedProjectManifest:
    state = {
            "state": {
                "state_version": request.state.version,
                "facts": request.state.facts,
                "artifact_refs": request.state.artifacts,
                "failures": list(request.state.failures),
            },
            "execution_plan": asdict(request.plan),
            "web_search_candidates": services.web_search_results,
            "web_evidence": services.web_results,
            "source_inspections": source_inspection_model_view(
                services.source_inspections),
            "available_input_artifacts": [
                item.to_dict() for item in input_artifacts],
            "available_input_text": ([{
                "path": item.path,
                "media_type": item.media_type,
                "content": item.content.decode("utf-8", errors="replace"),
            } for item in input_artifacts]
                if services.request.allow_source_materialization_to_model
                else []),
            "previous_project_attempts": [{
                "manifest_digest": item.get("manifest_digest"),
                "deterministic_checks_passed": item.get(
                    "deterministic_checks_passed"),
                "commands": item.get("commands"),
                "artifacts": item.get("artifacts"),
            } for item in services.project_attempts],
            "previous_construction_failures": {
                "candidate": services.plan_details.get(
                    "candidate_validation_failures", []),
                "files": services.plan_details.get(
                    "file_validation_failures", []),
            },
            "available_file_checkpoints":
                services.generated_file_checkpoint_summaries(),
            "project_contract": {
                "record_type": "generated_project_candidate/v1",
                "files": (
                    "ordered UTF-8 implementation, test, configuration, and "
                    "documentation file specifications. Never synthesize or "
                    "recreate supplied dataset, source, or evidence bodies"),
                "commands": (
                    "argv-only Python commands; create .venv, install declared "
                    "requirements, run the solution, then run its tests"),
                "expected_artifacts": (
                    "every output required by the original task, with media "
                    "type; minimum_bytes must equal the framework nonempty "
                    "value 1"),
                "runtime": "immutable Python Docker image",
                "network_inside_sandbox": "dependency_setup_only",
                "allowed_command_executables": list(ALLOWED_PYTHON_EXECUTABLES),
                "command_rule": (
                    "Use python -m MODULE instead of pip, pytest, or a shell "
                    "executable. Execute reviewed files rather than -c code. "
                    "Declare command_kind setup, execute, or verify. Only a "
                    "setup command whose argv begins python -m pip install may "
                    "set network_access true. Execute and verify commands must "
                    "use network_access false and read researched inputs from "
                    "the exact paths in available_input_artifacts. A README "
                    "mention or comment does not count as input use."),
            },
        }
    candidate_schema = json.dumps({
            "record_type": "generated_project_candidate/v1",
            "project_id": "lowercase_identifier",
            "summary": "string",
            "files": [{
                "path": "relative/path", "purpose": "string",
                "acceptance": ["string"]}],
            "commands": [{
                "argv": ["python", "file.py"], "purpose": "string",
                "timeout_seconds": 300,
                "command_kind": "setup|execute|verify",
                "network_access": False,
                "expected_exit_codes": [0]}],
            "expected_artifacts": [{
                "path": "relative/path", "media_type": "type/subtype",
                "minimum_bytes": 1}],
        }, separators=(",", ":"))
    failures: list[dict] = []
    candidate = None
    for attempt in range(1, 3):
        value = services.model(ModelStepRequest(
            "act",
            ("Design the complete project structure needed to execute and "
             "verify the task. Do not generate file contents yet."
             if attempt == 1 else
             "Repair the rejected project candidate without changing the task."),
            {**state, "candidate_validation_failures": failures},
            candidate_schema))
        try:
            candidate = GeneratedProjectCandidate.from_mapping(value)
            break
        except GeneratedProjectError as exc:
            failure = {
                "attempt": attempt, "error_type": type(exc).__name__,
                "error": str(exc)[:500]}
            failures.append(failure)
            services.plan_details.setdefault(
                "candidate_validation_failures", []).append(failure)
            services.diagnostic("project_candidate_invalid", failure)
    if candidate is None:
        raise GeneratedProjectError(
            "project candidate remained invalid after one model repair")
    services.plan_details["project_candidate"] = candidate.to_dict()

    generated_files = []
    for file_spec in candidate.files:
        checkpoint_key, contract_digest = _generated_file_checkpoint_identity(
            candidate, file_spec, services.request.task)
        checkpoint = services.generated_file_checkpoints.get(checkpoint_key)
        if checkpoint is not None:
            checkpoint_content = str(checkpoint.get("content") or "")
            checkpoint_digest = hashlib.sha256(
                checkpoint_content.encode("utf-8")).hexdigest()
            if (checkpoint.get("path") == file_spec.path
                    and checkpoint.get("contract_digest") == contract_digest
                    and checkpoint.get("content_digest") == checkpoint_digest):
                generated_file = GeneratedProjectFile(
                    file_spec.path, checkpoint_content)
                generated_files.append(generated_file)
                services.plan_details.setdefault(
                    "generated_files", []).append({
                        "path": generated_file.path,
                        "byte_count": len(
                            generated_file.content.encode("utf-8")),
                        "digest": checkpoint_digest,
                        "checkpoint_key": checkpoint_key,
                        "checkpoint_reused": True,
                    })
                services.publish(
                    "practitioner.file_checkpoint.reused", step="act",
                    artifact_path=generated_file.path,
                    checkpoint_digest=checkpoint_digest)
                continue
        file_schema = json.dumps({
            "path": file_spec.path, "content": "complete UTF-8 text",
        }, separators=(",", ":"))
        file_failures: list[dict] = []
        generated_file = None
        for attempt in range(1, 3):
            value = services.model(ModelStepRequest(
                "act",
                (f"Generate the complete content for {file_spec.path}."
                 if attempt == 1 else
                 f"Repair the rejected content for {file_spec.path}."),
                {
                    **state,
                    "project_candidate": candidate.to_dict(),
                    "active_file": file_spec.to_dict(),
                    "files_already_generated": [
                        item.to_dict() for item in generated_files],
                    "file_validation_failures": file_failures,
                }, file_schema))
            try:
                if set(value) != {"path", "content"}:
                    raise GeneratedProjectError(
                        "generated file fields do not match version 1")
                if str(value.get("path")) != file_spec.path:
                    raise GeneratedProjectError(
                        "generated file path differs from its specification")
                generated_file = GeneratedProjectFile(
                    file_spec.path, value.get("content"))
                break
            except GeneratedProjectError as exc:
                failure = {
                    "attempt": attempt, "path": file_spec.path,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500]}
                file_failures.append(failure)
                services.plan_details.setdefault(
                    "file_validation_failures", []).append(failure)
                services.diagnostic("project_file_invalid", failure)
        if generated_file is None:
            raise GeneratedProjectError(
                f"file {file_spec.path!r} remained invalid after one repair")
        generated_files.append(generated_file)
        checkpoint_summary = services.checkpoint_generated_file(
            checkpoint_key, generated_file.path, generated_file.content,
            contract_digest)
        services.plan_details.setdefault("generated_files", []).append({
            "path": generated_file.path,
            "byte_count": len(generated_file.content.encode("utf-8")),
            "digest": hashlib.sha256(
                generated_file.content.encode("utf-8")).hexdigest(),
            "checkpoint_key": checkpoint_key,
            "checkpoint_reused": False,
            "artifact_ref": checkpoint_summary["artifact_ref"],
        })
        services.publish(
            "practitioner.file_checkpoint.stored", step="act",
            artifact_path=generated_file.path,
            checkpoint_digest=checkpoint_summary["content_digest"])
    return GeneratedProjectManifest(
        candidate.project_id, candidate.summary, tuple(generated_files),
        candidate.commands, candidate.expected_artifacts)


def _web_operation(arguments, services, owner):
    maximum_bytes = arguments.get("maximum_bytes")
    return services.dependencies.web_fetcher(
        WebFetchRequest(
            str(arguments.get("url") or ""),
            str(arguments.get("purpose") or ""),
            maximum_bytes=(None if maximum_bytes is None
                           else int(maximum_bytes))),
        WebFetchAuthority(
            services.run_id, services.request.allow_network_reads),
        WebFetchContext(owner, services.artifacts))


def _search_operation(arguments, services, owner):
    maximum_results = arguments.get("maximum_results")
    return services.dependencies.web_searcher(
        WebSearchRequest(
            str(arguments.get("query") or ""),
            str(arguments.get("purpose") or ""),
            maximum_results=(None if maximum_results is None
                             else int(maximum_results))),
        WebSearchAuthority(
            services.run_id, services.request.allow_network_reads),
        WebSearchContext(owner))


def _input_artifact_path(
        final_url: str, index: int, used_paths: set[str]) -> str:
    url_path = final_url.split("?", 1)[0]
    suffix = Path(url_path).suffix[:12]
    if not suffix or not suffix.replace(".", "").isalnum():
        suffix = ".bin"
    basename = Path(url_path).name
    safe_basename = (
        basename if basename and len(basename) <= 120
        and all(character.isalnum() or character in ".-_"
                for character in basename)
        else "")
    named_path = f"inputs/{safe_basename}" if safe_basename else ""
    return (named_path if named_path and named_path not in used_paths
            else f"inputs/source-{index}{suffix}")


def _project_inputs(
        services: AdaptiveRunServices) -> tuple[GeneratedProjectInputArtifact, ...]:
    inputs = list(_local_project_inputs(services))
    used_paths = set()
    used_paths.update(item.path for item in inputs)
    for index, result in enumerate(services.web_results, 1):
        reference = ContextArtifactRef.from_dict(result["artifact_ref"])
        body = services.artifacts.store.get(reference)
        relative_path = _input_artifact_path(
            str(result.get("final_url") or ""), index, used_paths)
        used_paths.add(relative_path)
        inputs.append(GeneratedProjectInputArtifact(
            relative_path, body,
            str(result.get("media_type") or "application/octet-stream"),
            reference.digest))
    return tuple(inputs)


def _local_project_inputs(
        services: AdaptiveRunServices) -> tuple[GeneratedProjectInputArtifact, ...]:
    if services.request.source_kind not in {"dataset", "repository", "task_pack"}:
        return ()
    if not services.request.allow_source_materialization_to_model:
        raise PermissionError(
            "local task sources require explicit source-to-model authority")
    available = dict(inspectable_source_files(services))
    selected_records = {}
    for inspection in services.source_inspections:
        for item in inspection.get("selected", ()):
            raw = str(item.get("path") or "")
            if not raw:
                continue
            relative = raw if raw in available else (
                _resolve_requested_paths([raw], available).get(raw, ""))
            if relative:
                selected_records[relative] = str(item.get("digest") or "")
    selected_paths = tuple(selected_records)
    if not selected_paths:
        raise GeneratedProjectError(
            "local sources were supplied but the model has not selected any "
            "through core.source.inspect; request manifest_paths from "
            "core.source.inspect first, then select exact paths")
    missing = sorted(set(selected_paths) - set(available))
    if missing:
        raise GeneratedProjectError(
            f"selected local source paths are no longer available: {missing}")
    return tuple(GeneratedProjectInputArtifact(
        f"inputs/{relative}", available[relative].read_bytes(),
        mimetypes.guess_type(available[relative].name)[0] or "text/plain",
        selected_records[relative])
        for relative in selected_paths)


def execute_adaptive_capability(
        request: AdaptiveCapabilityExecutionRequest,
        services: AdaptiveRunServices) -> ResultPacket:
    """Compile, validate, and execute one selected generic capability."""
    plan = request.plan
    owner = request.owner_loop
    arguments = dict(plan.experiment.get("arguments") or {})
    manifest = None
    if plan.handle == "core.source.inspect":
        operation = lambda _value, _params: source_inspection_operation(
            arguments, services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "source_inspection_result/v1"
    elif plan.handle == "core.web.search":
        operation = lambda _value, _params: _search_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "web_search_result/v1"
    elif plan.handle == "core.web.get":
        operation = lambda _value, _params: _web_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "web_fetch_result/v1"
    elif plan.handle == "core.source.profile":
        operation = lambda _value, _params: source_profile_operation(
            arguments, services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "source_profile_result/v1"
    elif plan.handle == "core.environment.describe":
        operation = lambda _value, _params: environment_describe_operation(
            services)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "environment_description/v1"
    elif plan.handle == "core.intelligence.search":
        operation = lambda _value, _params: intelligence_search_operation(
            arguments, services, owner)
        input_value = arguments
        input_role = "next_action_decision/v1"
        output_role = "intelligence_search_result/v1"
    elif plan.handle == "core.generated_project":
        if services.web_search_results and not services.web_results:
            return ResultPacket(
                objective="resolve selected public source",
                errors=(
                    "web search produced candidates, but no selected source "
                    "has been fetched and verified",),
                confidence=0.0,
                limitations=(
                    "Search candidates are not evidence. Fetch a selected "
                    "source before constructing a source-dependent project.",))
        try:
            input_artifacts = _project_inputs(services)
            manifest = _project_manifest(request, services, input_artifacts)
        except (AdaptivePractitionerError, GeneratedProjectError,
                SolutionModelError, PermissionError) as exc:
            return ResultPacket(
                objective="prepare and construct a valid executable project",
                errors=(f"{type(exc).__name__}: {str(exc)[:500]}",),
                confidence=0.0,
                limitations=(
                    "The project could not be prepared from the current run "
                    "state. Select the required local sources through "
                    "core.source.inspect first; no workspace or command "
                    "effect was performed.",))
        try:
            input_validation = as_practitioner_loop(
                "validate generated project input use",
                lambda: validate_generated_project_input_use(
                    manifest, input_artifacts), parent=owner)["value"]
        except Exception as exc:  # noqa: BLE001
            services.diagnostic("project_input_use_invalid", {
                "error_type": type(exc).__name__, "error": str(exc)[:500]})
            return ResultPacket(
                objective="validate generated project input use",
                errors=(f"{type(exc).__name__}: {str(exc)[:500]}",),
                confidence=0.0,
                limitations=(
                    "The generated project ignored supplied inputs or violated "
                    "offline execution policy; no effect was performed.",))
        attempt = len(services.project_attempts) + 1
        workspace = services.workspace_base / f"attempt-{attempt}"

        def operation(_value, _params):
            result = services.dependencies.project_executor(
                GeneratedProjectExecutionRequest(
                    manifest, str(workspace), GeneratedProjectAuthority(
                        services.run_id,
                        services.request.allow_workspace_writes,
                        services.request.allow_sandbox_commands,
                        services.request.allow_network_reads),
                    DEFAULT_GENERATED_PROJECT_IMAGE,
                    input_artifacts=input_artifacts),
                GeneratedProjectExecutionContext(owner))
            result["manifest"] = manifest.to_dict()
            result["input_use_validation"] = input_validation
            result["workspace_path"] = str(workspace)
            return result
        input_value = manifest.to_dict()
        input_role = "generated_project_manifest/v1"
        output_role = "generated_project_execution/v1"
    else:
        return ResultPacket(
            objective=plan.handle or "unresolved action",
            errors=("action has no registered capability executor",),
            confidence=0.0)

    identity = hashlib.sha256(json.dumps(
        {"handle": plan.handle, "steps": list(plan.steps),
         "arguments": arguments}, sort_keys=True, default=str,
        separators=(",", ":")).encode()).hexdigest()[:20]
    spec = SolutionSpec(
        f"adaptive.action.{identity}",
        permitted_loop_modes=("deterministic",),
        loops=(SolutionLoopSpec(
            "execute_selected_capability", plan.handle,
            mode="deterministic", params={
                "instruction": plan.rationale,
                "plan_digest": identity,
            }, input_role=input_role, output_role=output_role),))
    registry = {plan.handle: operation}
    compiled = compile_solution(spec, registry)
    if compiled["plan"] is None:
        return ResultPacket(
            objective=plan.handle,
            errors=("Solution graph validation failed: "
                    + "; ".join(compiled["violations"]),),
            confidence=0.0)
    canvas = render_canvas(compiled["plan"])
    trace = []
    try:
        output = run_compiled(
            compiled["plan"], registry, input_value,
            trace=trace, ledger=owner.ledger, parent=owner)
    except Exception as exc:  # noqa: BLE001
        return ResultPacket(
            objective=plan.handle,
            errors=(f"{type(exc).__name__}: {str(exc)[:500]}",),
            confidence=0.0,
            lineage=(compiled["digest"],))
    services.plan_details["active_canvas"] = {
        "candidate_id": f"canvas:{identity}",
        "selected": True,
        "graph_digest": compiled["digest"],
        "loop_graph": compiled["plan"],
        "mermaid": canvas["mermaid"],
        "runtime_trace": trace,
    }
    if plan.handle == "core.source.inspect":
        services.source_inspections.append(output)
        services.selected_intelligence_refs.extend(
            f"source:{item['digest']}" for item in output["selected"]
            if f"source:{item['digest']}"
            not in services.selected_intelligence_refs)
        return ResultPacket(
            objective=(str(arguments.get("query") or "")
                       or "inspect supplied source"),
            result=output,
            evidence_refs=tuple(
                f"source:{item['digest']}" for item in output["selected"]),
            confidence=1.0,
            lineage=(compiled["digest"],))
    if plan.handle == "core.source.profile":
        return ResultPacket(
            objective="profile supplied source structure",
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "A structural profile is discovery evidence; it never "
                "selects a source or grants authority.",))
    if plan.handle == "core.environment.describe":
        return ResultPacket(
            objective="describe the runtime environment",
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "The environment description is effect-free discovery; "
                "provider names appear without secrets or availability "
                "proof.",))
    if plan.handle == "core.intelligence.search":
        return ResultPacket(
            objective=str(arguments.get("query") or "intelligence search"),
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "Intelligence references are advisory candidates; they "
                "never become active without the existing admission and "
                "promotion paths.",))
    if plan.handle == "core.web.search":
        services.web_search_results.append(output)
        return ResultPacket(
            objective=str(arguments.get("purpose") or "public web search"),
            result=output,
            confidence=1.0,
            lineage=(compiled["digest"],),
            limitations=(
                "Search candidates are not evidence until a URL is fetched.",))
    if plan.handle == "core.web.get":
        services.web_results.append(output)
        services.selected_intelligence_refs.append(
            f"artifact:{output['sha256']}")
        return ResultPacket(
            objective=str(arguments.get("purpose") or "public web research"),
            result=output,
            evidence_refs=(f"artifact:{output['sha256']}",),
            artifact_refs=(output["artifact_ref"]["object_key"],),
            confidence=1.0,
            lineage=(compiled["digest"],))
    output["context_evidence_count"] = len(services.web_results)
    services.project_attempts.append(output)
    errors = (() if output.get("deterministic_checks_passed") else (
        "generated project deterministic checks failed",))
    return ResultPacket(
        objective=(manifest.summary if manifest is not None else plan.handle),
        result=output,
        artifact_refs=tuple(item["path"] for item in output.get("artifacts", ())
                            if item.get("verified")),
        confidence=(1.0 if not errors else 0.0), errors=errors,
        lineage=(compiled["digest"], manifest.digest if manifest else ""))


def self_test() -> dict:
    """Static contract check; execution is covered by the adaptive suite."""
    from .generated_project import (
        ExpectedProjectArtifact, GeneratedProjectCommand)
    source = Path(__file__).read_text(encoding="utf-8").split(
        "def self_test()", 1)[0].lower()
    task_words = ("openml", "iris", "boosted-tree", "target_column=", "kaggle")
    passed = not any(word in source for word in task_words)
    used = set()
    first_path = _input_artifact_path(
        "https://example.test/files/records.data", 1, used)
    used.add(first_path)
    duplicate_path = _input_artifact_path(
        "https://mirror.test/records.data", 2, used)
    paths_passed = (
        first_path == "inputs/records.data"
        and duplicate_path == "inputs/source-2.data")
    file_spec = GeneratedProjectFileSpec(
        "pipeline.py", "Reusable pipeline.", ("Pipeline runs.",))
    command = GeneratedProjectCommand(
        ("python", "pipeline.py"), "Run pipeline.")
    artifact = ExpectedProjectArtifact("pipeline.py", "text/x-python")
    candidate_a = GeneratedProjectCandidate(
        "checkpoint_a", "First wording.", (file_spec,), (command,),
        (artifact,))
    candidate_b = GeneratedProjectCandidate(
        "checkpoint_b", "Different wording.", (file_spec,), (command,),
        (artifact,))
    changed_file = GeneratedProjectFileSpec(
        "pipeline.py", "Reusable pipeline.", ("Different contract.",))
    candidate_changed = GeneratedProjectCandidate(
        "checkpoint_c", "First wording.", (changed_file,), (command,),
        (artifact,))
    key_a, contract_a = _generated_file_checkpoint_identity(
        candidate_a, file_spec, "same task")
    key_b, contract_b = _generated_file_checkpoint_identity(
        candidate_b, file_spec, "same task")
    key_changed, _contract_changed = _generated_file_checkpoint_identity(
        candidate_changed, changed_file, "same task")
    checkpoint_identity_passed = (
        key_a == key_b and contract_a == contract_b
        and key_changed != key_a)
    tests = [{
        "test": "capability_graph_compiler_has_no_example_route",
        "passed": passed,
        "detail": "one generic Solution graph path",
    }, {
        "test": "fetched_inputs_preserve_safe_authoritative_basenames",
        "passed": paths_passed,
        "detail": f"{first_path}; {duplicate_path}",
    }, {
        "test": "file_checkpoint_reuses_only_an_unchanged_semantic_contract",
        "passed": checkpoint_identity_passed,
        "detail": f"{key_a[:32]}; changed={key_changed[:32]}",
    }]
    return {
        "record_type": "adaptive_capability_compilation_test/v1",
        "tests": tests,
        "passed": sum(item["passed"] for item in tests),
        "total": len(tests), "all_passed": all(
            item["passed"] for item in tests),
    }
