"""Safe Studio projections for delegated and external runtime work.

This module reads saved-run event details and explicitly supplied live
registries. It does not retain a second history. Every projection uses an
allowlist, so raw prompts, spawned-task context, secrets, instructions, tool inputs,
tool outputs, and approval resume tokens do not enter Studio payloads.

Spawned tasks, external harness results, approvals, context artifacts, MCP
terminal results, and skill loads all carry bounded saved-run details. Live
registry references add current inventory without becoming another store.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class StudioReadSources:
    """References to live authoritative objects used by read-only views."""

    harness_registry: object = None
    mcp_registry: object = None
    mcp_server_ids: tuple[str, ...] = ()
    skill_registry: object = None
    approval_states: tuple[object, ...] = ()
    context_payloads: tuple[object, ...] = ()
    compactions: tuple[object, ...] = ()

    def __post_init__(self):
        server_ids = tuple(self.mcp_server_ids)
        if (any(not isinstance(value, str) or not value.strip()
                for value in server_ids)
                or len(server_ids) != len(set(server_ids))):
            raise ValueError(
                "mcp_server_ids must contain unique nonempty strings")
        object.__setattr__(self, "mcp_server_ids", server_ids)
        for name in ("approval_states", "context_payloads", "compactions"):
            object.__setattr__(self, name, tuple(getattr(self, name)))


def project_run_runtime(events: Sequence[object]) -> dict:
    """Build a safe per-run view from raw or persisted event objects."""
    spawned_tasks: dict[str, dict] = {}
    harness_runs = []
    mcp_calls = []
    approvals: dict[str, dict] = {}
    artifacts = []
    compactions = []
    skill_loads = []
    for sequence, event in enumerate(events):
        detail, loop_id, mode = _event_parts(event)
        observation_kind = str(
            detail.get("_ledger_event") or detail.get("event") or "")
        custom_kind = str(detail.get("custom_kind", ""))
        if custom_kind.startswith(("spawned_task_", "spawned_task_")):
            normalized_kind = custom_kind.replace(
                "spawned_task_", "spawned_task_", 1)
            _project_spawned_event(
                spawned_tasks, normalized_kind, detail, loop_id, mode,
                sequence)

        harness = detail.get("external_harness_result")
        if isinstance(harness, Mapping):
            harness_runs.append(_safe_harness_run(harness, loop_id, sequence))

        if observation_kind == "effect_approval_requested":
            request_id = str(detail.get("request_id", ""))
            approvals[request_id] = _safe_approval(
                detail, loop_id, sequence)
        elif observation_kind == "effect_approval_decided":
            request_id = str(detail.get("request_id", ""))
            approvals[request_id] = _safe_approval(
                detail, loop_id, sequence)

        if observation_kind == "context_artifact_stored":
            artifacts.append(_safe_context_artifact(detail, loop_id, sequence))
        elif observation_kind == "context_compaction_completed":
            compactions.append(_safe_compaction(detail, loop_id, sequence))

        if observation_kind == "mcp_call_terminal":
            mcp_calls.append(_safe_mcp_terminal(detail, loop_id, sequence))
        elif detail.get("mcp_server") and detail.get("mcp_tool"):
            # Compatibility for histories created before the terminal observer.
            mcp_calls.append({
                "sequence": sequence,
                "loop_id": loop_id,
                "server_id": str(detail.get("mcp_server", "")),
                "tool_name": str(detail.get("mcp_tool", "")),
                "effect": str(detail.get("effect", "")),
                "status": "completed",
                "request_digest_prefix": str(
                    detail.get("request_digest", ""))[:12],
                "has_output_ref": bool(detail.get("output_ref")),
            })

        if observation_kind == "skill_load_terminal":
            skill_loads.append({
                "sequence": sequence,
                "loop_id": loop_id,
                "skill_id": str(detail.get("skill_id", "")),
                "version": str(detail.get("version", "")),
                "lifecycle": str(detail.get("lifecycle", "")),
                "manifest_digest_prefix": str(
                    detail.get("manifest_digest", ""))[:12],
                "file_count": int(detail.get("file_count", 0) or 0),
                "status": str(detail.get("status", "")),
                "error_code": str(detail.get("error_code", "")),
            })

    return {
        "record_type": "studio_run_runtime/v2",
        "source": "run_history_events",
        "spawned_tasks": list(spawned_tasks.values()),
        "external_harness_runs": harness_runs,
        "mcp_calls": mcp_calls,
        "skill_loads": skill_loads,
        "effect_approvals": {
            "playback_available": True,
            "items": list(approvals.values()),
        },
        "context_artifacts": {
            "playback_available": True,
            "items": artifacts,
            "compactions": compactions,
        },
        "history_gaps": [],
    }


def project_runtime_inventory(
        sources: "StudioReadSources | None" = None) -> dict:
    """Project live registries without copying their private or executable data."""
    selected = sources or StudioReadSources()
    return {
        "record_type": "studio_runtime_inventory/v1",
        "source": "live_authoritative_references",
        "harnesses": _harness_inventory(selected.harness_registry),
        "mcp": _mcp_inventory(selected.mcp_registry, selected.mcp_server_ids),
        "skills": _skill_inventory(selected.skill_registry),
        "effect_approvals": _approval_inventory(selected.approval_states),
        "context_artifacts": _context_inventory(
            selected.context_payloads, selected.compactions),
        "history_gaps": [],
        "privacy": (
            "No raw prompt, private spawned-task context, secret, skill instruction, "
            "tool argument, tool output, or approval resume token is projected."
        ),
    }


def _event_parts(event: object) -> tuple[dict, str, str]:
    if hasattr(event, "detail"):
        return (
            dict(getattr(event, "detail", {}) or {}),
            str(getattr(event, "loop_id", "") or ""),
            str(getattr(event, "mode", "") or ""),
        )
    if isinstance(event, Mapping):
        return dict(event), str(event.get("loop_id", "")), str(
            event.get("mode", ""))
    return {}, "", ""


def _project_spawned_event(tasks: dict[str, dict], kind: str, detail: dict,
                           loop_id: str, mode: str, sequence: int) -> None:
    task_id = str(detail.get("spawned_task_id", "")
                  or detail.get("spawned_task_id", ""))
    if not task_id:
        return
    row = tasks.setdefault(task_id, {
        "task_id": task_id,
        "spawning_loop_id": loop_id,
        "spawned_loop_id": "",
        "profile": "",
        "mode": "",
        "status": "unknown",
        "updates": 0,
        "selected_ref_count": 0,
        "shared_runtime_memory": False,
        "return_destination": "",
        "terminal_code": "",
        "output_roles": [],
        "steps_run": 0,
        "model_calls": 0,
        "error_code": "",
        "first_sequence": sequence,
        "last_sequence": sequence,
    })
    row["last_sequence"] = sequence
    if kind == "spawned_task_started":
        row.update({
            "spawned_loop_id": str(detail.get("spawned_loop_id", "")
                                   or detail.get("spawned_loop_id", "")),
            "profile": str(detail.get("profile", "")),
            "mode": mode or str(detail.get("mode", "")),
            "status": "running",
            "selected_ref_count": int(
                detail.get("selected_ref_count", 0) or 0),
            "shared_runtime_memory": bool(
                detail.get("shared_runtime_memory", False)),
            "return_destination": str(
                detail.get("return_destination", "")),
        })
    elif kind == "spawned_task_updated":
        row["updates"] += 1
    elif kind == "spawned_task_terminal":
        row.update({
            "status": str(detail.get("status", "unknown")),
            "terminal_code": str(detail.get("terminal_code", "")),
            "output_roles": [str(value) for value in
                             detail.get("output_roles", ())],
            "steps_run": int(detail.get("steps_run", 0) or 0),
            "model_calls": int(detail.get("model_calls", 0) or 0),
            "error_code": str(detail.get("error_code", "")),
        })


def _safe_harness_run(value: Mapping, loop_id: str,
                      sequence: int) -> dict:
    artifacts = value.get("artifacts", ())
    spawned_tasks = (value.get("spawned_task_ids", ())
                     or value.get("spawned_task_ids", ()))
    return {
        "sequence": sequence,
        "loop_id": loop_id,
        "request_id": str(value.get("request_id", "")),
        "harness_id": str(value.get("harness_id", "")),
        "status": str(value.get("status", "")),
        "completed": bool(value.get("completed", False)),
        "acceptance": str(value.get("acceptance", "not_evaluated")),
        "physical_model_calls": value.get("physical_model_calls"),
        "detailed_model_calls": value.get("detailed_model_calls"),
        "call_count_complete": bool(value.get("call_count_complete", False)),
        "total_tokens": value.get("total_tokens"),
        "total_cost": value.get("total_cost"),
        "accounting_complete": bool(value.get("accounting_complete", False)),
        "tool_events": int(value.get("tool_events", 0) or 0),
        "artifact_count": len(artifacts) if isinstance(
            artifacts, (list, tuple)) else 0,
        "spawned_task_count": len(spawned_tasks) if isinstance(
            spawned_tasks, (list, tuple)) else 0,
        "has_checkpoint": bool(value.get("checkpoint_ref")),
        "has_trace": bool(value.get("trace_ref")),
        "has_raw_events": bool(value.get("raw_events_ref")),
        "elapsed_seconds": value.get("elapsed_seconds"),
        "adapter_version": str(value.get("adapter_version", "")),
        "error_code": str(value.get("error_code", "")),
    }


def _safe_approval(value: Mapping, loop_id: str, sequence: int) -> dict:
    return {
        "sequence": sequence,
        "loop_id": loop_id,
        "request_id": str(value.get("request_id", "")),
        "effect_class": str(value.get("effect_class", "")),
        "operation": str(value.get("operation", "")),
        "target_digest_prefix": str(value.get("target_digest", ""))[:12],
        "status": str(value.get("status", "")),
        "action": str(value.get("action", "")),
        "state_revision": int(value.get("state_revision", 0) or 0),
        "schema_version": str(value.get("schema_version", "")),
    }


def _safe_context_artifact(value: Mapping, loop_id: str,
                           sequence: int) -> dict:
    return {
        "sequence": sequence,
        "loop_id": loop_id,
        "digest_prefix": str(value.get("digest", ""))[:12],
        "byte_count": int(value.get("byte_count", 0) or 0),
        "media_type": str(value.get("media_type", "")),
        "artifact_kind": str(value.get("artifact_kind", "")),
        "estimated_tokens": int(value.get("estimated_tokens", 0) or 0),
        "token_counter_id": str(value.get("token_counter_id", "")),
        "offloaded": bool(value.get("offloaded", False)),
    }


def _safe_compaction(value: Mapping, loop_id: str,
                     sequence: int) -> dict:
    return {
        "sequence": sequence,
        "loop_id": loop_id,
        "raw_digest_prefix": str(value.get("raw_digest", ""))[:12],
        "compacted_digest_prefix": str(
            value.get("compacted_digest", ""))[:12],
        "compacted_bytes": int(value.get("compacted_bytes", 0) or 0),
        "omitted_bytes": int(value.get("omitted_bytes", 0) or 0),
        "strategy": str(value.get("strategy", "")),
        "loop_profile": str(value.get("loop_profile", "")),
    }


def _safe_mcp_terminal(value: Mapping, loop_id: str,
                       sequence: int) -> dict:
    return {
        "sequence": sequence,
        "loop_id": loop_id,
        "server_id": str(value.get("server_id", "")),
        "tool_name": str(value.get("tool_name", "")),
        "effect": str(value.get("effect", "")),
        "status": str(value.get("status", "")),
        "request_digest_prefix": str(value.get("request_digest", ""))[:12],
        "has_output_ref": bool(value.get("has_output_ref", False)),
        "has_approval": bool(value.get("has_approval", False)),
        "error_code": str(value.get("error_code", "")),
    }


def _harness_inventory(registry: object) -> dict:
    if registry is None:
        from .external_harness import HarnessRegistry
        from .external_harness_adapters import builtin_harness_adapters
        registry = HarnessRegistry(builtin_harness_adapters())
    inventory = getattr(registry, "inventory", None)
    if not callable(inventory):
        return {"configured": False, "items": [],
                "gap": "No readable HarnessRegistry was supplied."}
    rows = []
    for info in inventory():
        rows.append({
            "harness_id": str(getattr(info, "harness_id", "")),
            "adapter_version": str(getattr(info, "adapter_version", "")),
            "package_name": str(getattr(info, "package_name", "")),
            "package_version": str(getattr(info, "package_version", "")),
            "features": list(getattr(info, "features", ()) or ()),
            "limitations": list(getattr(info, "limitations", ()) or ()),
            "available": bool(getattr(info, "available", False)),
        })
    return {"configured": True, "items": rows}


def _mcp_inventory(registry: object,
                   server_ids: tuple[str, ...]) -> dict:
    if registry is None or not server_ids:
        return {
            "configured": False,
            "items": [],
            "gap": (
                "Studio needs an McpRegistry and explicit server ids. "
                "McpRegistry has no public all-server inventory method."
            ),
        }
    rows = []
    for server_id in server_ids:
        server = registry.server(server_id)
        tools = registry.tools(server_id)
        rows.append({
            "server_id": str(server.server_id),
            "transport": str(server.transport),
            "enabled": bool(server.enabled),
            "protocol_version": str(server.protocol_version),
            "tools": [{
                "name": str(tool.name),
                "description": str(tool.description),
                "effect": str(tool.effect),
                "requires_approval": bool(tool.requires_approval),
            } for tool in tools],
        })
    return {"configured": True, "items": rows}


def _skill_inventory(registry: object) -> dict:
    inventory = getattr(registry, "inventory", None) if registry else None
    if not callable(inventory):
        return {
            "configured": False,
            "items": [],
            "gap": "Studio needs a live SkillRegistry reference.",
        }
    rows = []
    for manifest in inventory(include_candidates=True):
        rows.append({
            "skill_id": str(manifest.skill_id),
            "title": str(manifest.title),
            "description": str(manifest.description),
            "version": str(manifest.version),
            "lifecycle": str(manifest.lifecycle),
            "source": str(manifest.source),
            "tags": list(manifest.tags),
            "file_count": len(manifest.files),
            "manifest_digest_prefix": str(manifest.manifest_digest)[:12],
        })
    return {"configured": True, "items": rows}


def _approval_inventory(states: tuple[object, ...]) -> dict:
    rows = []
    for state in states:
        request = getattr(state, "request", None)
        effect = getattr(request, "effect", None)
        if request is None or effect is None:
            continue
        decision = getattr(state, "decision", None)
        edited_effect = getattr(decision, "edited_effect", None) if decision else None
        if edited_effect is not None:
            effect = edited_effect
        action = getattr(decision, "action", "") if decision else ""
        effect_class = getattr(effect, "effect_class", "")
        rows.append({
            "request_id": str(getattr(request, "request_id", "")),
            "loop_id": str(getattr(request, "loop_id", "")),
            "effect_class": str(getattr(effect_class, "value", effect_class)),
            "operation": str(getattr(effect, "operation", "")),
            "target_digest_prefix": hashlib.sha256(str(
                getattr(effect, "target", "")).encode()).hexdigest()[:12],
            "status": str(getattr(
                getattr(state, "status", ""), "value",
                getattr(state, "status", ""))),
            "action": str(getattr(action, "value", action)),
            "state_revision": int(getattr(state, "state_revision", 0)),
            "schema_version": str(getattr(state, "schema_version", "")),
        })
    return {
        "configured": bool(states),
        "playback_available": True,
        "items": rows,
    }


def _context_inventory(payloads: tuple[object, ...],
                       compactions: tuple[object, ...]) -> dict:
    items = []
    for payload in payloads:
        raw = getattr(payload, "raw", None)
        if raw is None:
            continue
        items.append({
            "digest_prefix": str(getattr(raw, "digest", ""))[:12],
            "byte_count": int(getattr(raw, "byte_count", 0)),
            "media_type": str(getattr(raw, "media_type", "")),
            "artifact_kind": str(getattr(raw, "artifact_kind", "")),
            "estimated_tokens": int(getattr(payload, "estimated_tokens", 0)),
            "token_counter_id": str(getattr(payload, "token_counter_id", "")),
            "offloaded": bool(getattr(payload, "offloaded", False)),
        })
    compacted_rows = []
    for result in compactions:
        raw = getattr(result, "raw", None)
        compacted = getattr(result, "compacted", None)
        if raw is None or compacted is None:
            continue
        compacted_rows.append({
            "raw_digest_prefix": str(getattr(raw, "digest", ""))[:12],
            "compacted_digest_prefix": str(
                getattr(compacted, "digest", ""))[:12],
            "compacted_bytes": int(getattr(compacted, "byte_count", 0)),
            "omitted_bytes": int(getattr(result, "omitted_bytes", 0)),
            "strategy": str(getattr(result, "strategy", "")),
            "loop_profile": str(getattr(result, "loop_profile", "")),
        })
    return {
        "configured": bool(payloads or compactions),
        "playback_available": True,
        "items": items,
        "compactions": compacted_rows,
    }


def _view_test_cases() -> list[dict]:
    """Focused privacy and projection checks folded by studio_server."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"name": name, "passed": bool(passed), "note": detail})

    events = [
        {"event": "custom", "loop_id": "spawning", "mode": "hybrid",
         "custom_kind": "spawned_task_started",
         "spawned_task_id": "task-1", "spawned_loop_id": "spawned-1",
         "profile": "practitioner.solver",
         "selected_ref_count": 2, "shared_runtime_memory": False,
         "return_destination": "spawning_context",
         "private_context": "PRIVATE_SPAWNED_CONTEXT"},
        {"event": "custom", "loop_id": "spawning",
         "custom_kind": "spawned_task_updated", "spawned_task_id": "task-1",
         "instruction": "PRIVATE_UPDATE"},
        {"event": "custom", "loop_id": "spawning",
         "custom_kind": "spawned_task_terminal",
         "spawned_task_id": "task-1",
         "status": "succeeded", "terminal_code": "SUCCESS",
         "output_roles": ("answer/v1",), "steps_run": 3,
         "model_calls": 1, "error_code": "", "raw_output": "PRIVATE_OUTPUT"},
        {"event": "custom", "loop_id": "harness-loop",
         "external_harness_result": {
             "record_type": "external_harness_result/v2",
             "request_id": "request-1", "harness_id": "deep_agents",
             "status": "completed", "completed": True,
             "acceptance": "not_evaluated", "physical_model_calls": 1,
             "detailed_model_calls": 1, "call_count_complete": True,
             "total_tokens": 20, "total_cost": 0.01,
             "accounting_complete": True, "tool_events": 2,
             "artifacts": ["artifact-1"],
             "spawned_task_ids": ["spawned-1"],
             "checkpoint_ref": "PRIVATE_CHECKPOINT_LOCATION",
             "trace_ref": "PRIVATE_TRACE_LOCATION",
             "raw_events_ref": "PRIVATE_RAW_EVENTS_LOCATION",
             "adapter_version": "1.0.0", "error": "PRIVATE_ERROR"},
         "raw_prompt": "PRIVATE_PROMPT"},
    ]
    run = project_run_runtime(events)
    serialized = json.dumps(run, sort_keys=True)
    check("run_runtime_projects_only_bounded_spawned_harness_and_mcp_fields",
          run["spawned_tasks"][0]["status"] == "succeeded"
          and run["spawned_tasks"][0]["updates"] == 1
          and run["spawned_tasks"][0]["spawning_loop_id"] == "spawning"
          and run["spawned_tasks"][0]["spawned_loop_id"] == "spawned-1"
          and run["external_harness_runs"][0]["harness_id"] == "deep_agents",
          "spawned task and harness relationship shapes were projected")
    check("run_runtime_omits_private_context_prompts_outputs_and_locations",
          "PRIVATE" not in serialized
          and "raw_prompt" not in serialized
          and "workspace_policy_ref" not in serialized,
          "the projection is an allowlist, not a detail passthrough")
    check("runtime_surfaces_use_the_canonical_history_instead_of_a_gap_store",
          run["effect_approvals"]["playback_available"]
          and run["context_artifacts"]["playback_available"]
          and not run["history_gaps"],
          "the projection declares canonical playback support")

    import tempfile
    from ..loop.effect_approval import (
        ApprovalDecision, ApprovalRequest, EffectApprovalService,
        EffectClass, EffectSpec)
    from ..loop.recursive_loop import LoopLedger
    from .run_history import RunHistory, as_ledger_events, to_canonical_events
    from ..loop.intelligence_loops import serve_historical_intelligence
    from .context_artifacts import (
        CompactionRequest, ContextArtifactManager, ContextArtifactServices,
        ContextArtifactStore, ContextArtifactStoreSpec, ContextOffloadPolicy,
        compact_context_as_loop)
    from .mcp_adapter import (
        InjectedMcpTransport, McpCallRequest, McpInvocationServices,
        McpRegistry, McpServerSpec, McpToolSpec)
    from .runtime_observer import RuntimeObservationServices
    from .skill_registry import SkillLoadPurpose, SkillRegistry

    ledger = LoopLedger()
    runtime = RuntimeObservationServices(ledger=ledger)

    mcp = McpRegistry()
    async def catalog_lookup(_request):
        return {}
    mcp.register(
        McpServerSpec("catalog", "in_process", credential_refs=(
            "secret:PRIVATE_MCP_TOKEN",), tool_allowlist=("lookup",)),
        InjectedMcpTransport((McpToolSpec(
            "catalog", "lookup", "Look up one catalog item.", {}, "pure"),),
            catalog_lookup))
    mcp.discover("catalog", runtime=runtime)

    approval_service = EffectApprovalService(runtime)
    approval = approval_service.create(ApprovalRequest(
        "approval-live-1", "loop-live-1",
        EffectSpec(EffectClass.NETWORK_WRITE, "post", "PRIVATE_TARGET"),
        "PRIVATE_REASON"))
    resolved_approval = approval_service.resume(
        approval.pending, approval.resume_token,
        ApprovalDecision.approve("approval-live-1", "PRIVATE_REVIEWER"))

    with tempfile.TemporaryDirectory() as directory:
        store = ContextArtifactStore(ContextArtifactStoreSpec(directory))
        context_services = ContextArtifactServices(store, runtime)
        manager = ContextArtifactManager(
            context_services, ContextOffloadPolicy(max_inline_bytes=10,
                                                   max_inline_tokens=2))
        mcp.invoke(McpCallRequest(
            "catalog", "lookup", {"query": "PRIVATE_MCP_ARGUMENT"}),
            services=McpInvocationServices(
                runtime=runtime, artifact_manager=manager))
        payload = manager.capture("PRIVATE_RAW_CONTEXT " * 20)
        compacted = compact_context_as_loop(
            CompactionRequest(payload.raw, max_summary_bytes=96),
            services=context_services)

        from pathlib import Path
        skill_root = Path(directory) / "safe-skill"
        skill_root.mkdir()
        (skill_root / "SKILL.md").write_text(
            "---\nname: safe-skill\nversion: 1.0.0\n"
            "description: Review one bounded output.\n---\n"
            "PRIVATE_SKILL_INSTRUCTIONS\n", encoding="utf-8")
        skills = SkillRegistry()
        skills.discover((str(skill_root),))
        skills.load(
            "safe-skill", purpose=SkillLoadPurpose.CANDIDATE_REVIEW,
            runtime=runtime)

        inventory = project_runtime_inventory(StudioReadSources(
            mcp_registry=mcp,
            mcp_server_ids=("catalog",),
            skill_registry=skills,
            approval_states=(resolved_approval,),
            context_payloads=(payload,),
            compactions=(compacted,),
        ))
        saved = serve_historical_intelligence(
            "studio-runtime-observer-test",
            lambda: RunHistory.from_ledger(
                ledger.events, run_id="studio-runtime-observer-test"),
        )["value"]
        playback = project_run_runtime(saved.event_log)
        canonical = to_canonical_events(as_ledger_events(saved.event_log))
    inventory_json = json.dumps(inventory, sort_keys=True)
    check("runtime_inventory_reads_harness_mcp_skill_approval_and_context_sources",
          len(inventory["harnesses"]["items"]) == 4
          and inventory["mcp"]["items"][0]["tools"][0]["name"] == "lookup"
          and inventory["skills"]["items"][0]["skill_id"] == "safe-skill"
          and inventory["effect_approvals"]["items"][0]["status"] == "decided"
          and inventory["context_artifacts"]["items"][0]["offloaded"],
          "each view reads the supplied authoritative object at request time")
    check("runtime_inventory_omits_roots_secrets_raw_context_and_resume_tokens",
          "PRIVATE" not in inventory_json
          and approval.resume_token not in inventory_json
          and "root_path" not in inventory_json
          and "instructions" not in inventory_json,
          "only display-safe metadata crosses into the payload")
    playback_json = json.dumps(playback, sort_keys=True)
    check("approval_context_MCP_and_skill_events_survive_saved_playback",
          playback["effect_approvals"]["items"][0]["status"] == "decided"
          and playback["context_artifacts"]["items"]
          and playback["context_artifacts"]["compactions"]
          and playback["mcp_calls"][0]["status"] == "completed"
          and playback["skill_loads"][0]["skill_id"] == "safe-skill"
          and not playback["history_gaps"],
          "real service events survived a saved-history round trip")
    check("saved_runtime_playback_omits_private_service_data",
          "PRIVATE" not in playback_json
          and "resume_token" not in playback_json
          and "instructions" not in playback_json
          and "arguments" not in playback_json,
          "saved events contain safe identities, digests, statuses, and counts")
    observed_families = {row["type"] for row in canonical}
    check("saved_service_events_keep_their_canonical_families",
          {"loop.paused", "loop.resumed", "state.committed",
           "tool.invocation.completed", "intelligence.context.retrieved"}
          <= observed_families
          and not [family for family in observed_families
                   if family.startswith("x.")],
          "saved-history round trip retained mapped raw observation kinds")

    return tests
