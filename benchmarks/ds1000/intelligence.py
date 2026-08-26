"""Frozen intelligence records and canonical retrieval for DS-1000 v1."""
from __future__ import annotations

from dataclasses import dataclass

from loop_engine.loop.loop_capsule import LoopRef
from loop_engine.loop.recursive_loop import Loop, LoopConfig, StepOutcome
from loop_engine.core.intelligence_layers import (
    LAYERS,
    materialize_intelligence_ref,
    query_intelligence,
)
from loop_engine.core.store_serve import StoreRecord

from code_intelligence import code_intelligence_records


LENSES = (
    "first_principles",
    "alternate_methods",
    "missing_constraints",
    "common_failures",
    "verification",
    "output_shape",
    "cost",
)

CONTEXT_TEXT = {
    "first_principles": (
        "Derive the smallest correct library operation from the stated input "
        "and output semantics before adding convenience transformations."),
    "alternate_methods": (
        "Consider at least one vectorized or library-native alternative and "
        "prefer the method whose behavior matches the requested edge cases."),
    "missing_constraints": (
        "Identify unstated shape, dtype, index, randomness, and version "
        "constraints. Do not invent values that the prompt does not grant."),
    "common_failures": (
        "Watch for wrong axis, data leakage, unstable randomness, deprecated "
        "APIs, accidental mutation, and returning the wrong object type."),
    "verification": (
        "Check imports, variable names, output type, shape, determinism, and "
        "whether the code is a drop-in completion rather than a full program."),
    "output_shape": (
        "Return only the Python completion requested by the task. Do not add "
        "Markdown, prose, tests, package installation, or a main program."),
    "cost": (
        "Use the simplest bounded computation that solves the task. Avoid "
        "unnecessary training, copies, loops, or searches when a direct API "
        "already expresses the operation."),
}

USER_RECORD_ID = "ds1000.user.current_owner_rules"
BENCHMARK_ID = "ds1000-pandas-sklearn-4-v1"
CONTEXT_LENS_FAMILY = {
    "first_principles": "first_principles",
    "missing_constraints": "first_principles",
    "alternate_methods": "",
    "common_failures": "failure_adversarial",
    "verification": "verification_evaluation",
    "output_shape": "output_contract_format",
    "cost": "cost_resource",
}


@dataclass(frozen=True)
class SelectedItem:
    record_id: str
    layer: str
    loop_ref: str
    title: str
    materialized_value: object
    prompt_text: str
    query: str

    def as_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "layer": self.layer,
            "loop_ref": self.loop_ref,
            "title": self.title,
            "materialized_value": self.materialized_value,
            "prompt_text": self.prompt_text,
            "query": self.query,
        }


@dataclass
class IntelligenceSelection:
    items: dict[str, SelectedItem]
    searches: list[dict]
    retrieval_spawned_loop_id: str

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_intelligence_selection/v1",
            "items": {key: value.as_dict()
                      for key, value in sorted(self.items.items())},
            "searches": self.searches,
            "retrieval_spawned_loop_id": self.retrieval_spawned_loop_id,
            "queried_layers": list(LAYERS),
            "lenses": list(LENSES),
        }


def context_records() -> tuple[StoreRecord, ...]:
    return tuple(StoreRecord(
        f"ds1000.context.{lens}",
        "context",
        f"DS-1000 {lens.replace('_', ' ')} lens",
        body={
            "role": "method",
            "text": text,
            "maturity": "registered",
            "metadata": {
                "benchmark_ids": [BENCHMARK_ID],
                "lens_families": ([CONTEXT_LENS_FAMILY[lens]]
                                  if CONTEXT_LENS_FAMILY[lens] else []),
            },
            "facets": {
                "category": "method",
                "subcategory": lens,
                "scope": "ds1000_population_v1",
                "lifecycle": "registered",
            },
        },
        tags=("ds1000", "context", lens),
        tier="core",
        source="benchmarks/ds1000/intelligence.py",
    ) for lens, text in CONTEXT_TEXT.items())


def user_record() -> StoreRecord:
    return StoreRecord(
        USER_RECORD_ID,
        "context",
        "Current owner rules for the DS-1000 full Practitioner run",
        body={
            "role": "instruction",
            "text": (
                "Run the full end-to-end Loop Engine path only. The selected "
                "mode is non-deterministic. Use a source-backed maximum output "
                "of 65536 with the exact Ollama Cloud model and no fake model "
                "or failover. Use varied Context lenses. Keep the evaluator "
                "and reference solution hidden from model prompts. Keep every "
                "failure visible."),
            "maturity": "registered",
            "metadata": {
                "benchmark_ids": [BENCHMARK_ID],
                "lens_families": ["missing_information"],
            },
            "facets": {
                "category": "instruction",
                "subcategory": "owner_constraint",
                "scope": "ds1000_population_v1",
                "lifecycle": "registered",
            },
        },
        tags=("ds1000", "user_advice", "owner_constraint"),
        tier="core",
        source="active user direction",
    )


def preflight_history_record(preflight: dict) -> StoreRecord:
    runtime = dict(preflight.get("runtime") or {})
    return StoreRecord(
        "ds1000.history.preflight",
        "strategy",
        "Previous run: DS-1000 v1 source, sandbox, and evaluator preflight",
        body={
            "history_type": "run",
            "run_id": "ds1000-v1-preflight",
            "summary": (
                "The pinned source, selected IDs, locked runtime, reference "
                "self-check, negative evaluator check, and engine gates passed. "
                "No model candidate had been evaluated at this point."),
            "runtime_image_id": runtime.get("image_id", ""),
            "model_generation_calls": 0,
            "maturity": "committed",
            "metadata": {
                "benchmark_ids": [BENCHMARK_ID],
                "lens_families": ["alternatives_analogy"],
            },
            "facets": {
                "category": "run",
                "subcategory": "preflight",
                "scope": "ds1000_population_v1",
                "lifecycle": "committed",
            },
        },
        tags=("ds1000", "previous_run", "preflight"),
        tier="core",
        source="benchmarks/ds1000 preflight",
    )


def failure_history_record(problem_id: int, candidate_sha256: str,
                           upstream_result: str) -> StoreRecord:
    return StoreRecord(
        f"ds1000.history.failure.{problem_id}.{candidate_sha256[:12]}",
        "strategy",
        f"Previous failed evaluation for DS-1000 problem {problem_id}",
        body={
            "history_type": "failure",
            "problem_id": int(problem_id),
            "candidate_sha256": candidate_sha256,
            "upstream_result": upstream_result,
            "summary": (
                "The synthesized candidate failed the pinned upstream "
                "evaluator. Use the exact failure signal for one bounded repair."),
            "maturity": "committed",
            "metadata": {
                "benchmark_ids": [BENCHMARK_ID],
                "lens_families": ["failure_adversarial"],
            },
            "facets": {
                "category": "failure",
                "subcategory": "upstream_evaluation",
                "scope": "ds1000_population_v1",
                "lifecycle": "committed",
            },
        },
        tags=("ds1000", "previous_run", "failure", str(problem_id)),
        tier="core",
        source="current campaign upstream evaluation",
    )


def build_layer_records(preflight: dict, *, extra_history=()) -> dict:
    return {
        "context_intelligence": list(context_records()),
        "code_intelligence": list(code_intelligence_records()),
        "runtime_history_solution_intelligence": [
            preflight_history_record(preflight), *list(extra_history)],
        "user_feedback_intelligence": [user_record()],
    }


def _prompt_text(record: StoreRecord, value: object) -> str:
    body = dict(record.body or {})
    if body.get("text"):
        return str(body["text"])
    if body.get("summary"):
        return str(body["summary"])
    if body.get("handle"):
        handle = body["handle"]
        return (f"Available registered operation {handle['module']}:"
                f"{handle['callable']} with contract "
                f"{body.get('typed_contract')}")
    return str(value)


def _select_one(need: str, target_id: str, layer_records: dict,
                *, parent: Loop) -> tuple[SelectedItem, dict]:
    result = query_intelligence(
        need, layer_records, mode="lexical", top_n=32,
        ledger=parent.ledger, parent=parent)
    if result["unqueried"]:
        raise RuntimeError(
            f"intelligence search left layers unqueried: {result['unqueried']}")
    hit = next((row for row in result["hits"]
                if row["record_id"] == target_id), None)
    if hit is None:
        raise RuntimeError(
            f"intelligence search for {need!r} did not return {target_id}")
    ref = LoopRef.from_dict(hit["loop_ref"])
    materialized = materialize_intelligence_ref(
        ref, layer_records, ledger=parent.ledger, parent=parent)
    layer = str(hit["layer"])
    record = next(record for record in layer_records[layer]
                  if record.record_id == target_id)
    item = SelectedItem(
        record_id=target_id,
        layer=layer,
        loop_ref=ref.loop_ref,
        title=record.title,
        materialized_value=materialized["value"],
        prompt_text=_prompt_text(record, materialized["value"]),
        query=need,
    )
    search_summary = {
        "need": need,
        "target_record_id": target_id,
        "selected_loop_ref": ref.loop_ref,
        "query_loop": result["query_loop"],
        "hit_record_ids": [row["record_id"] for row in result["hits"]],
        "unqueried": result["unqueried"],
    }
    return item, search_summary


def retrieve_predecision_intelligence(root: Loop,
                                       layer_records: dict) -> IntelligenceSelection:
    """Search and materialize every required record before model decisions."""
    spawned_loop = root.spawn(
        "retrieve Context, Code, Previous Run, and User Feedback Intelligence",
        LoopConfig(
            framework="custom",
            custom_steps=("retrieve",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            power="light",
            max_depth=5,
            stop_condition="run_to_completion",
        ))
    holder: dict = {"items": {}, "searches": []}

    def handler(loop, step, context):
        for lens in LENSES:
            target = f"ds1000.context.{lens}"
            item, search = _select_one(
                f"DS-1000 {lens.replace('_', ' ')} lens", target,
                layer_records, parent=loop)
            holder["items"][target] = item
            holder["searches"].append(search)
        for record in code_intelligence_records():
            item, search = _select_one(
                record.title, record.record_id, layer_records, parent=loop)
            holder["items"][record.record_id] = item
            holder["searches"].append(search)
        history_id = layer_records["runtime_history_solution_intelligence"][-1].record_id
        history_item, history_search = _select_one(
            layer_records["runtime_history_solution_intelligence"][-1].title,
            history_id, layer_records, parent=loop)
        holder["items"][history_id] = history_item
        holder["searches"].append(history_search)
        user_item, user_search = _select_one(
            "current owner rules full end-to-end hidden evaluator failures visible",
            USER_RECORD_ID, layer_records, parent=loop)
        holder["items"][USER_RECORD_ID] = user_item
        holder["searches"].append(user_search)
        return StepOutcome(
            output=(f"retrieved:{len(holder['items'])}:all-four-layers"),
            mode="deterministic",
            confidence=1.0,
        )

    result = spawned_loop.run(handler=handler, max_steps=2)
    if result.stopped != "done":
        raise RuntimeError("bounded intelligence spawned_loop did not complete")
    root.ledger.record(
        loop_id=root.loop_id,
        event="custom",
        action="active_user_feedback_intelligence_consumed",
        consumed_intelligence_refs=(holder["items"][USER_RECORD_ID].loop_ref,),
        owner_rules="full path, non-deterministic, maximum output, no fake "
                    "model, varied lenses, hidden evaluator, visible failures",
    )
    return IntelligenceSelection(
        items=holder["items"],
        searches=holder["searches"],
        retrieval_spawned_loop_id=spawned_loop.loop_id,
    )


def planned_portfolio_ids() -> dict[str, tuple[str, ...]]:
    code_ids = tuple(record.record_id for record in code_intelligence_records())
    common = (*code_ids, "ds1000.history.preflight", USER_RECORD_ID)
    candidate_a = (
        *common,
        "ds1000.context.first_principles",
        "ds1000.context.missing_constraints",
        "ds1000.context.output_shape",
        "ds1000.context.cost",
    )
    candidate_b = (
        *common,
        "ds1000.context.alternate_methods",
        "ds1000.context.common_failures",
        "ds1000.context.verification",
    )
    synthesis = tuple(dict.fromkeys((*candidate_a, *candidate_b)))
    return {
        "candidate_a": candidate_a,
        "candidate_b": candidate_b,
        "synthesis": synthesis,
    }


def portfolio(selection: IntelligenceSelection, role: str) -> tuple[SelectedItem, ...]:
    ids = planned_portfolio_ids()[role]
    missing = [record_id for record_id in ids
               if record_id not in selection.items]
    if missing:
        raise RuntimeError(f"portfolio {role} misses records {missing}")
    return tuple(selection.items[record_id] for record_id in ids)


def preflight_selection(preflight: dict) -> dict:
    """Resolve the planned references without making a provider call."""
    root = Loop(
        "preflight the frozen DS-1000 intelligence portfolios",
        LoopConfig(
            framework="custom",
            custom_steps=("select",),
            allowable_modes=("deterministic",),
            preferred_modes=("deterministic",),
            delegated_modes=("deterministic",),
            power="light",
            max_depth=5,
        ))
    holder = {}

    def handler(loop, step, context):
        holder["selection"] = retrieve_predecision_intelligence(
            loop, build_layer_records(preflight))
        return StepOutcome(
            output="selected:frozen-portfolios",
            mode="deterministic",
            confidence=1.0,
        )

    result = root.run(handler=handler, max_steps=2)
    selection = holder["selection"]
    return {
        "record_type": "ds1000_preflight_intelligence/v1",
        "model_generation_calls": 0,
        "root_stopped": result.stopped,
        "selection": selection.as_dict(),
        "portfolios": {
            role: [selection.items[record_id].loop_ref
                   for record_id in record_ids]
            for role, record_ids in planned_portfolio_ids().items()
        },
    }
