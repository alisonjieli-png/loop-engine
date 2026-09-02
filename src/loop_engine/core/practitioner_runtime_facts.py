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

from .adaptive_practitioner_records import AdaptivePractitionerError
from .adaptive_practitioner_source import (
    inspectable_source_files, project_input_path)
from .adaptive_practitioner_supervision import DEFAULT_SUPERVISION_POLICY

RUNTIME_FACTS_RECORD_TYPE = "practitioner_runtime_facts/v1"

#: Manifest paths carried inline; the total and a digest are always present
#: so a truncated list is never mistaken for the whole manifest.
MANIFEST_PATH_LIMIT = 64


def _source_manifest(services) -> dict | None:
    request = services.request
    if not (request.allow_source_materialization_to_model
            and request.source_refs):
        return None
    try:
        files = inspectable_source_files(services)
    except (AdaptivePractitionerError, OSError, ValueError):
        return None
    paths = sorted(relative for relative, _path in files)
    digest = hashlib.sha256("\n".join(paths).encode("utf-8")).hexdigest()
    carried = paths[:MANIFEST_PATH_LIMIT]
    return {
        "paths": carried,
        "sandbox_paths": {relative: project_input_path(relative)
                          for relative in carried},
        "total": len(paths),
        "truncated": len(paths) > MANIFEST_PATH_LIMIT,
        "digest": digest,
        "usage": ("core.source.inspect admits exactly these relative paths; "
                  "call it with paths omitted to receive the manifest with "
                  "sizes, or with a subset of these paths for contents"),
        "sandbox_paths_usage": (
            "generated code runs in the workspace, not beside the source: "
            "open a file at its sandbox_paths value, never at its admitted "
            "path. These are the exact paths the runtime materializes"),
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


def runtime_facts(services) -> dict:
    """Exact, model-visible facts about this run. Never advisory."""
    request = services.request
    policy = DEFAULT_SUPERVISION_POLICY.action_fence
    return {
        "record_type": RUNTIME_FACTS_RECORD_TYPE,
        "authority": "runtime",
        "workspace_root": str(services.workspace_base),
        "execution_isolation": (
            "host_process" if request.allow_local_execution
            else "container"),
        "granted_permissions": list(granted_permissions(request)),
        "interaction_mode": str(request.interaction_mode),
        "source_manifest": _source_manifest(services),
        "source_roles": _source_roles(services),
        "action_fence": services.action_fence.model_view(policy),
    }


def self_test() -> dict:
    """Prove the projection states the manifest and the fence exactly."""
    import os
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
        "passed": (facts.get("execution_isolation") == "host_process"
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
        "test": "no_source_authority_means_no_manifest_and_no_error",
        "passed": (closed_facts["source_manifest"] is None
                   and closed_facts["granted_permissions"] == []
                   and closed_facts["action_fence"]["fenced"] == []),
        "detail": closed_facts["execution_isolation"],
    }]
    return {"module": "core.practitioner_runtime_facts",
            "passed": all(item["passed"] for item in tests), "tests": tests}
