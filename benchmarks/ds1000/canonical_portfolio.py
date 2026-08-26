"""Bind DS-1000 model-led spawned Loops to intelligence portfolios."""
from __future__ import annotations

from dataclasses import dataclass

from loop_engine.core.intelligence_portfolio import (
    LoopIntelligenceMaterialization,
    PortfolioMaterializationServices,
    PortfolioRequest,
    PortfolioSelectionServices,
    materialize_portfolio_for_loop,
    select_intelligence_portfolio,
)

from code_intelligence import benchmark_code_pack
from intelligence import (
    BENCHMARK_ID,
    USER_RECORD_ID,
    build_layer_records,
)


class SpawnedLoopIntelligenceGateError(RuntimeError):
    """A spawned model Loop used a different intelligence selection."""


@dataclass(frozen=True)
class PromptIntelligenceItem:
    family: str
    record_id: str
    layer: str
    loop_ref: str
    prompt_text: str


@dataclass(frozen=True)
class PreparedSpawnedLoopIntelligence:
    materialization: LoopIntelligenceMaterialization
    prompt_items: tuple[PromptIntelligenceItem, ...]

    @property
    def consumption(self):
        return self.materialization.consumption

    def as_dict(self) -> dict:
        return {
            "record_type": "ds1000_spawned_loop_intelligence/v1",
            "portfolio": self.materialization.portfolio.to_dict(),
            "consumption": self.consumption.to_dict(),
            "prompt_projection": [{
                "family": item.family,
                "record_id": item.record_id,
                "layer": item.layer,
                "loop_ref": item.loop_ref,
            } for item in self.prompt_items],
            "payload_bodies_exported": False,
        }


def _role_layer_records(preflight: dict, role: str, *, extra_history=()) -> dict:
    records = build_layer_records(preflight, extra_history=extra_history)
    # The canonical BenchmarkCodePack supplies the six Code records. The
    # simpler cards were already searched and materialized by the root and are
    # removed here to avoid duplicate IDs.
    records["code_intelligence"] = []
    if role == "candidate_a":
        records["context_intelligence"] = [
            record for record in records["context_intelligence"]
            if record.record_id != "ds1000.context.missing_constraints"]
    elif role == "candidate_b":
        records["context_intelligence"] = [
            record for record in records["context_intelligence"]
            if record.record_id != "ds1000.context.first_principles"]
    elif role == "repair":
        records["context_intelligence"] = [
            record for record in records["context_intelligence"]
            if record.record_id != "ds1000.context.common_failures"]
    return records


def _record_index(records: dict, code_pack) -> dict:
    all_records = {
        (layer, record.record_id): record
        for layer, values in records.items() for record in values
    }
    for record in code_pack.records_for(BENCHMARK_ID):
        all_records[("code_intelligence", record.record_id)] = record
    return all_records


def _prompt_text(record, value: object) -> str:
    body = dict(record.body or {})
    if body.get("text"):
        return str(body["text"])
    if body.get("summary"):
        return str(body["summary"])
    if body.get("role") == "code_asset":
        contracts = body.get("contracts") or {}
        return (
            f"A registered deterministic operation is available: "
            f"{record.title}. Its declared contracts are {contracts}. "
            "The model does not execute this operation itself.")
    return record.title


def prepare_spawned_loop_intelligence(task, spawned_loop, preflight: dict, role: str,
                               *, extra_history=()) -> PreparedSpawnedLoopIntelligence:
    """Select, materialize, and bind exact use to one spawned Loop."""
    records = _role_layer_records(
        preflight, role, extra_history=extra_history)
    code_pack = benchmark_code_pack()
    request = PortfolioRequest(
        task=(f"DS-1000 problem {task.problem_id} {task.library} public code "
              f"completion for {role}"),
        consuming_loop_id=spawned_loop.loop_id,
        benchmark_id=BENCHMARK_ID,
        mode="non_deterministic",
    )
    selected = select_intelligence_portfolio(
        request,
        PortfolioSelectionServices(
            layer_records=records,
            code_pack=code_pack,
            ledger=spawned_loop.ledger,
            parent=spawned_loop,
        ))
    materialized = materialize_portfolio_for_loop(
        selected,
        PortfolioMaterializationServices(
            layer_records=records,
            code_pack=code_pack,
            ledger=spawned_loop.ledger,
            parent=spawned_loop,
        ))
    selected_ids = {item.record_id for item in selected.items}
    history_id = records["runtime_history_solution_intelligence"][-1].record_id
    if USER_RECORD_ID not in selected_ids:
        raise SpawnedLoopIntelligenceGateError(
            f"{role} portfolio did not consume active User Feedback Intelligence")
    if role == "repair":
        if history_id not in selected_ids:
            raise SpawnedLoopIntelligenceGateError(
                "repair portfolio did not consume the failed prior evaluation")
    elif "ds1000.history.preflight" not in selected_ids:
        raise SpawnedLoopIntelligenceGateError(
            f"{role} portfolio did not consume Runtime History and Solution Intelligence")

    index = _record_index(records, code_pack)
    values = {value.family: value.value for value in materialized.values}
    prompt_items = []
    for item in selected.items:
        record = index[(item.layer, item.record_id)]
        prompt_items.append(PromptIntelligenceItem(
            family=item.family.value,
            record_id=item.record_id,
            layer=item.layer,
            loop_ref=item.ref.loop_ref,
            prompt_text=_prompt_text(record, values[item.family]),
        ))
    if tuple(item.loop_ref for item in prompt_items) \
            != materialized.consumption.consumed_refs:
        raise SpawnedLoopIntelligenceGateError(
            "prompt projection differs from canonical spawned_loop consumption")
    return PreparedSpawnedLoopIntelligence(
        materialization=materialized,
        prompt_items=tuple(prompt_items),
    )
