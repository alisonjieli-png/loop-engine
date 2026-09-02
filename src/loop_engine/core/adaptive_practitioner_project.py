"""Assembly of one generated project from model proposals.

Architectural role: everything between "the model wants to build something"
and "there is a validated, passive project manifest to execute". It resolves
which supplied sources become project inputs and where they are materialized,
asks the model for a project candidate and then for each authored file, and
reuses a file already authored under an unchanged contract instead of paying
for it twice.

It holds one line the whole system depends on: an expected artifact is
evidence that a command produced something, so a file the model typed is
never also an expected artifact. That rule lives in core.generated_project;
this module is where the model is told about it and where its repair
attempts land.

Owns:
    - generated_file_checkpoint_identity(): when authored content is reusable.
    - project_inputs(): which supplied sources are materialized, and where.
    - project_manifest(): the candidate, its files, and their repair loop.

Does not own: the project contract and its validation
(core.generated_project), capability dispatch
(core.adaptive_practitioner_capabilities), or execution.
"""
from __future__ import annotations

import hashlib
import json
import mimetypes
from dataclasses import asdict
from pathlib import Path

from ..loop.kernel import ExecutionPlan, PractitionerState
from .runtime_capacity import (
    model_evidence_bytes, supplied_input_ceiling)
from .adaptive_practitioner_records import (
    AdaptiveRunServices, ModelStepRequest)
from .adaptive_practitioner_source import (
    _resolve_requested_paths, inspectable_source_files, project_input_path,
    source_inspection_model_view)
from .context_artifacts import ContextArtifactRef
from .generated_project import (
    ALLOWED_PYTHON_EXECUTABLES, GeneratedProjectCandidate,
    GeneratedProjectError, GeneratedProjectFile, GeneratedProjectFileSpec,
    GeneratedProjectInputArtifact, GeneratedProjectManifest)


def generated_file_checkpoint_identity(
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


def project_manifest(
        state_value: PractitionerState, plan: ExecutionPlan,
        services: AdaptiveRunServices,
        input_artifacts: tuple[GeneratedProjectInputArtifact, ...]
        ) -> GeneratedProjectManifest:
    """Ask the model for one project, then for each file it must author.

    Takes the Practitioner state and the selected plan rather than the
    capability's request object: this module is below capability dispatch and
    should not need a name that only exists above it.
    """
    state = {
            "state": {
                "state_version": state_value.version,
                "facts": state_value.facts,
                "artifact_refs": state_value.artifacts,
                "failures": list(state_value.failures),
            },
            "execution_plan": asdict(plan),
            "web_search_candidates": services.web_search_results,
            "web_evidence": services.web_results,
            "source_inspections": source_inspection_model_view(
                services.source_inspections,
                selected_content_byte_limit=model_evidence_bytes(services)),
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
                    "recreate supplied dataset, source, or evidence bodies. "
                    "Author only what a person would write by hand: code, "
                    "tests, configuration, documentation. Anything a command "
                    "produces belongs in expected_artifacts and must not "
                    "appear here"),
                "commands": (
                    "argv-only Python commands; create .venv, install declared "
                    "requirements, run the solution, then run its tests"),
                "expected_artifacts": (
                    "every output required by the original task, with media "
                    "type; minimum_bytes must equal the framework nonempty "
                    "value 1. These are checked after the commands run, so "
                    "each one must be produced by a command. A path here may "
                    "not also appear in files: typing an output is not "
                    "producing it, and results you did not compute are not "
                    "results"),
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
        # Carry why it stayed invalid. An exhausted repair that reports only
        # that it was exhausted tells the run nothing it can act on.
        raise GeneratedProjectError(
            "project candidate remained invalid after one model repair; "
            f"the attempts failed with {[item['error'] for item in failures]}")
    services.plan_details["project_candidate"] = candidate.to_dict()

    generated_files = []
    for file_spec in candidate.files:
        checkpoint_key, contract_digest = generated_file_checkpoint_identity(
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
                f"file {file_spec.path!r} remained invalid after one repair; "
                f"the attempts failed with "
                f"{[item['error'] for item in file_failures]}")
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


def project_inputs(
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
    # Checked by size, before any body is read, against what this machine
    # measures right now rather than a number written here. Discovering the
    # limit halfway through a copy leaves the run diagnosing an executor error
    # instead of a capacity, and a limit nobody measured refuses work the
    # machine could have done.
    capacity = supplied_input_ceiling()
    ceiling = capacity["bytes"]
    if ceiling is not None:
        oversize = sorted(
            (relative, available[relative].stat().st_size)
            for relative in selected_paths
            if available[relative].stat().st_size > ceiling)
        if oversize:
            raise GeneratedProjectError(
                f"selected sources exceed what this machine can materialize, "
                f"{ceiling} bytes, bound by {capacity['binding_constraint']} "
                f"({capacity['basis']}): {oversize}. Free space or memory, "
                "select smaller sources, or read them with code that streams "
                "rather than materializing them whole")
    return tuple(GeneratedProjectInputArtifact(
        project_input_path(relative), available[relative].read_bytes(),
        mimetypes.guess_type(available[relative].name)[0] or "text/plain",
        selected_records[relative])
        for relative in selected_paths)


def self_test() -> dict:
    """Prove input placement, checkpoint reuse, and the pre-authored refusal."""
    from .generated_project import (
        ExpectedProjectArtifact, GeneratedProjectCommand,
        GeneratedProjectFileSpec)

    used: set[str] = set()
    first_path = _input_artifact_path(
        "https://example.test/files/records.data", 1, used)
    used.add(first_path)
    duplicate_path = _input_artifact_path(
        "https://mirror.test/records.data", 2, used)

    file_spec = GeneratedProjectFileSpec(
        "pipeline.py", "Reusable pipeline.", ("Pipeline runs.",))
    command = GeneratedProjectCommand(("python", "pipeline.py"), "Run it.")
    artifact = ExpectedProjectArtifact("summary.json", "application/json")
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
    key_a, contract_a = generated_file_checkpoint_identity(
        candidate_a, file_spec, "same task")
    key_b, contract_b = generated_file_checkpoint_identity(
        candidate_b, file_spec, "same task")
    key_changed, _changed = generated_file_checkpoint_identity(
        candidate_changed, changed_file, "same task")
    try:
        GeneratedProjectCandidate(
            "checkpoint_typed", "Types its own result.", (file_spec,),
            (command,),
            (ExpectedProjectArtifact("pipeline.py", "text/x-python"),))
        typed_output_refused = ""
    except GeneratedProjectError as exc:
        typed_output_refused = str(exc)[:80]

    tests = [{
        "test": "fetched_inputs_preserve_safe_authoritative_basenames",
        "passed": (first_path == "inputs/records.data"
                   and duplicate_path == "inputs/source-2.data"),
        "detail": f"{first_path}; {duplicate_path}",
    }, {
        "test": "file_checkpoint_reuses_only_an_unchanged_semantic_contract",
        "passed": (key_a == key_b and contract_a == contract_b
                   and key_changed != key_a),
        "detail": f"{key_a[:32]}; changed={key_changed[:32]}",
    }, {
        "test": "a_project_may_not_type_the_output_it_claims_to_produce",
        "passed": bool(typed_output_refused),
        "detail": typed_output_refused or "a typed output was accepted",
    }, {
        "test": "a_supplied_source_is_placed_where_the_runtime_says_it_is",
        "passed": (project_input_path("comp/rows.csv")
                   == "inputs/comp/rows.csv"),
        "detail": project_input_path("comp/rows.csv"),
    }]
    return {"module": "core.adaptive_practitioner_project",
            "passed": all(item["passed"] for item in tests), "tests": tests}
