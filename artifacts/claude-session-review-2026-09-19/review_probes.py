"""Offline reproductions for the September 19 session review.

These probes observe the existing implementation without modifying it. All
write probes use disposable directories; all keys and bodies are fixtures.
No provider, network, billing, or remote service is invoked.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from loop_engine.code_nodes.solve_runtime import solve_dependencies
from loop_engine.core.guardrail_intelligence import Guardrail, GuardrailSet
from loop_engine.core.harness_intelligence import (
    HarnessIntelligenceCatalogue,
    HarnessIntelligenceDraft,
    item_from_body,
)
from loop_engine.core.intelligence_tagging import TagSet
from loop_engine.core.model_call_collection import LearningEventCollector
from loop_engine.core.model_call_records import COMPLETED, STARTED, learning_records
from loop_engine.core.node_provisioning import (
    ASSIGNMENT_FILE,
    NodeAssignment,
    provision,
    provision_plan,
)
from loop_engine.core.provisioning_server import (
    ProvisioningRequest,
    ProvisioningServer,
    ProvisioningTenant,
)
from loop_engine.core.service_api import ServiceApplication, key_digest, new_tenant
from loop_engine.core.spawned_provisioning import provision_spawned


def main() -> None:
    observations = []

    def record(probe, present, observed):
        observations.append({
            "probe": probe,
            "finding_present": bool(present),
            "observed": observed,
        })

    request = SimpleNamespace(
        model_execution=None, progress=None, reuse_observation_port=None,
        project_executor=None, extension_snapshot={}, host_runtime=None,
    )
    dependencies = solve_dependencies(request, ())
    with tempfile.TemporaryDirectory(prefix="loop-review-provision-") as folder:
        services = SimpleNamespace(
            dependencies=dependencies,
            request=SimpleNamespace(allow_workspace_writes=True),
            workspace_base=Path(folder) / "spawned",
        )
        result = provision_spawned(
            services, node_id="review-assignment", objective="Inspect a supplied file")
        record("public_solve_has_no_provisioning_catalogue",
               not result["provisioned"], result)

    catalogue = HarnessIntelligenceCatalogue()
    with tempfile.TemporaryDirectory(prefix="loop-review-path-") as folder:
        root = Path(folder) / "plan"
        root.mkdir()
        provision_plan(
            (NodeAssignment("../escaped", "reason", "Inspect a review fixture"),),
            catalogue=catalogue, root=root)
        escaped = (Path(folder) / "escaped" / ASSIGNMENT_FILE).is_file()
        record("plan_identifier_escapes_provisioning_root", escaped,
               {"outside_folder_created": escaped,
                "files_inside_plan": sorted(p.name for p in root.iterdir())})

    with tempfile.TemporaryDirectory(prefix="loop-review-symlink-") as folder:
        root = Path(folder) / "plan"
        root.mkdir()
        outside = Path(folder) / "outside.txt"
        outside.write_text("REVIEW_ONLY_ORIGINAL", encoding="utf-8")
        (root / ASSIGNMENT_FILE).symlink_to(outside)
        provision(NodeAssignment("safe-id", "reason", "Inspect a review fixture"),
                  catalogue=catalogue, root=root)
        overwritten = outside.read_text("utf-8") != "REVIEW_ONLY_ORIGINAL"
        record("assignment_write_follows_existing_symlink", overwritten,
               {"outside_file_overwritten": overwritten})

    rules = GuardrailSet()
    rules.register(Guardrail(
        "review.authorization", "Confirm authorization", "permission", "block",
        "before_provisioning", "authorization must pass",
        judge="model_judged", on_unavailable="escalate"))
    with tempfile.TemporaryDirectory(prefix="loop-review-guardrail-") as folder:
        result = provision(
            NodeAssignment("guarded", "reason", "Inspect a review fixture"),
            catalogue=catalogue, root=folder, guardrails=rules)
        record("unavailable_blocking_guardrail_allows_provisioning",
               (Path(folder) / ASSIGNMENT_FILE).is_file()
               and bool(result.guardrails["escalated_by"]),
               {"files_created": sorted(p.name for p in Path(folder).iterdir()),
                "guardrails": result.guardrails})

    events = []
    for number in (1, 2):
        base = {"run_id": "review-run", "step": "route", "format_attempt": 1,
                "transport_attempt": 1, "model_call_number": number,
                "pass_number": number}
        events.extend((
            {**base, "event_type": STARTED, "prompt_digest": str(number) * 64},
            {**base, "event_type": COMPLETED, "output_digest": str(number) * 64},
        ))
    records = learning_records(events)
    identities = [r.record_id for r in records]
    record("repeated_steps_overwrite_learning_records",
           len(set(identities)) != len(identities),
           {"expected_call_numbers": [1, 2],
            "actual_call_numbers": [r.model_call_number for r in records],
            "actual_record_ids": identities})

    collector = LearningEventCollector()
    for event in events:
        collector(event)
    collector({**events[-1], "output_preview": "REVIEW_ONLY_RESPONSE_MARKER"})
    report = collector.report()
    retained = "REVIEW_ONLY_RESPONSE_MARKER" in str(collector.events)
    record("response_preview_retained_but_report_denies_bodies",
           retained and not report["bodies_retained"],
           {"response_marker_retained": retained,
            "reported_bodies_retained": report["bodies_retained"]})
    record("collector_report_contains_count_not_training_rows",
           isinstance(report["records"], int),
           {"report": report, "derived_rows_available_on_collector": len(collector.records())})

    item = item_from_body(HarnessIntelligenceDraft(
        "review.item", "skill", "A review fixture", "context_intelligence",
        "review.source", tags=TagSet({
            "lifecycle": ["candidate"], "data_sensitivity": ["regulated"],
            "authentication": ["operator"],
        })), "review fixture body")
    catalogue.register(item)
    server = ProvisioningServer(
        catalogue,
        (ProvisioningTenant("ordinary-tenant", key_digest("review-fixture-key"), "bodies"),),
        body_reader=lambda _: "review fixture body",
    )
    result = server.handle(ProvisioningRequest("read", "review-fixture-key", "review.item"))
    record("provisioning_has_no_qualification_or_sensitivity_access_gate",
           "body" in result,
           {"served": "body" in result, "tenant_entitlement": "bodies",
            "item_tags": item.tags.to_dict()})
    record("read_claims_metered_without_installed_meter",
           result["metered"] and server.meter is None,
           {"reported_metered": result["metered"], "meter_installed": server.meter is not None})

    tenant, key = new_tenant("review-tenant", "review-namespace")
    application = ServiceApplication((tenant,))
    statuses = {path: application.handle("POST", path, key, b"{}")[0]
                for path in ("/mcp", "/provision", "/read", "/v1/usage")}
    record("existing_http_service_does_not_expose_provisioning_protocol",
           statuses["/mcp"] == 404 and statuses["/provision"] == 404, statuses)

    source_paths = (
        "src/loop_engine/code_nodes/solve_runtime.py",
        "src/loop_engine/core/spawned_provisioning.py",
        "src/loop_engine/core/node_provisioning.py",
        "src/loop_engine/core/guardrail_intelligence.py",
        "src/loop_engine/core/model_call_records.py",
        "src/loop_engine/core/model_call_collection.py",
        "src/loop_engine/core/harness_intelligence.py",
        "src/loop_engine/core/intelligence_tagging.py",
        "src/loop_engine/core/provisioning_server.py",
        "src/loop_engine/core/service_api.py",
    )
    result = {
        "record_type": "claude_session_review_probes/v1",
        "date": "2026-09-19",
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True).strip(),
        "source_state": "existing uncommitted work included; no implementation edited",
        "source_sha256": {p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
                          for p in source_paths},
        "provider_calls": 0,
        "remote_effects": 0,
        "probes": observations,
        "finding_count": sum(r["finding_present"] for r in observations),
        "probe_count": len(observations),
        "interpretation": "Finding presence reproduces a defect or launch gap; it is not a passing product test.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
