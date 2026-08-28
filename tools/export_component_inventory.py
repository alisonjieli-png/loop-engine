"""Export generated component architecture inventories from one Loop run."""
from __future__ import annotations

import json
from pathlib import Path

from loop_engine.core.component_inventory import (
    ComponentInventoryRequest, run_component_inventory)


def _jsonl(path: Path, records) -> None:
    path.write_text("".join(
        json.dumps(item, sort_keys=True, ensure_ascii=False, default=str) + "\n"
        for item in records), encoding="utf-8")


def main() -> int:
    repository = Path(__file__).resolve().parents[1]
    package = repository / "src" / "loop_engine"
    output = repository / "artifacts" / "architecture"
    output.mkdir(parents=True, exist_ok=True)
    inventory = run_component_inventory(ComponentInventoryRequest(str(package)))
    component_records = [
        {"inventory_kind": "file", **item} for item in inventory["files"]]
    component_records.extend(
        {"inventory_kind": "symbol", **item} for item in inventory["symbols"])
    component_records.extend(
        {"inventory_kind": "explicit_component", **item}
        for item in inventory["explicit_components"])
    component_records.append({
        "inventory_kind": "run_evidence",
        "record_type": inventory["record_type"],
        "inventory_loop_id": inventory["inventory_loop_id"],
        "file_count": len(inventory["files"]),
        "symbol_count": len(inventory["symbols"]),
        "explicit_component_count": len(inventory["explicit_components"]),
    })
    _jsonl(output / "component_inventory.jsonl", component_records)
    _jsonl(output / "component_interactions.jsonl",
           inventory["interactions"])
    (output / "folder_map.json").write_text(json.dumps(
        inventory["folder_map"], indent=2, sort_keys=True), encoding="utf-8")
    _jsonl(output / "string_blob_findings.jsonl",
           inventory["native_semantic_operations"])
    _jsonl(output / "redundancy_findings.jsonl", ({
        "finding_id": "component.redundancy.prompt_assembly_authority",
        "decision": "REUSE_AS_IS_AND_EXTEND",
        "subject": "core.reasoning_call.PromptAssemblySpec",
        "evidence": "adaptive Practitioner now reuses this layout authority",
    }, {
        "finding_id": "component.redundancy.semantic_native_baseline",
        "decision": "REPLACE_WITH_LOOP_OPERATION_IN_BOUNDED_BATCHES",
        "subject": "remaining native semantic operations",
        "count": len(inventory["native_semantic_operations"]),
        "evidence": "exact file, symbol, line, and operation inventory",
    }))
    _jsonl(output / "context_handoff_findings.jsonl", ({
        "finding_id": "context.handoff.full_horizon_stack",
        "severity": "HIGH",
        "state": "REQUIRED_NOT_IMPLEMENTED",
        "evidence": (
            "typed spawned work exists, but global, long, medium, short, "
            "parent, local, availability, materialization, and demand-pull "
            "fields are not yet one complete component contract"),
    },))
    _jsonl(output / "generalization_candidates.jsonl", ({
        "candidate_id": "generalize.native_semantic_operations",
        "route": "parameterized_atomic_primitives",
        "state": "candidate",
        "remaining_count": len(inventory["native_semantic_operations"]),
    }, {
        "candidate_id": "generalize.context_handoff",
        "route": "extend_existing_spawn_contract",
        "state": "candidate",
    }, {
        "candidate_id": "generalize.component_classification",
        "route": "file_and_symbol_review_batches",
        "state": "candidate",
        "unclassified_symbols": sum(
            item["component_mapping"] == "unclassified"
            for item in inventory["symbols"]),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
