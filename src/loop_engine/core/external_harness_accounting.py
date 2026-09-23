"""Post-run bounds and validation of canonical model observations.

Owns budget assessment and exact references to already-recorded gateway events.
It performs no provider call and grants no execution or acceptance authority.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .harness_model_authority import HarnessError

if TYPE_CHECKING:
    from .external_harness import HarnessRunRequest, HarnessRunResult


def _budget_failure(request: HarnessRunRequest, result: HarnessRunResult) -> str | None:
    if request.budget.max_model_calls is not None and not result.call_count_complete:
        return "model_call_accounting_incomplete"
    if result.completed and result.call_count_complete and not result.physical_model_calls:
        return "no_reported_model_call"
    if (request.budget.max_model_calls is not None
            and (result.physical_model_calls or 0) > request.budget.max_model_calls):
        return "model_call_budget_exhausted"
    if request.budget.max_total_tokens is not None and not result.accounting_complete:
        return "token_accounting_incomplete"
    if (request.budget.max_total_tokens is not None and result.total_tokens is not None
            and result.total_tokens > request.budget.max_total_tokens):
        return "token_budget_exhausted"
    if request.budget.max_cost is not None and result.total_cost is None:
        return "cost_accounting_incomplete"
    if (request.budget.max_cost is not None and result.total_cost is not None
            and result.total_cost > request.budget.max_cost):
        return "cost_budget_exhausted"
    if (request.budget.max_seconds is not None and result.elapsed_seconds is not None
            and result.elapsed_seconds > request.budget.max_seconds):
        return "time_budget_exhausted"
    if (request.budget.max_spawned_tasks is not None
            and len(result.spawned_task_ids) > request.budget.max_spawned_tasks):
        return "spawned_task_budget_exhausted"
    return None


def _usage_agrees(event, call) -> bool:
    """The ledger event and the gateway attempt describe the same usage.

    The ledger keeps a received response's reported zero counters as zero;
    the gateway attempt reads the same two zeros as absent usage (a legacy
    adapter's defaults are not evidence). Both are one description of one
    response, so the pair agrees; any other difference is a mismatch."""
    recorded = (event.get("prompt_tokens"), event.get("eval_tokens"))
    reported = (call.input_tokens, call.output_tokens)
    return recorded == reported or (recorded == (0, 0) and reported == (None, None))


def _validate_gateway_references(calls, events, owner_ids) -> dict:
    """Only fresh, matching canonical attempts may suppress imported events."""
    referenced = [call for call in calls if call.gateway_loop_id]
    requested = {}
    if len({call.gateway_loop_id for call in referenced}) != len(referenced):
        raise HarnessError("a gateway attempt cannot represent several physical calls")
    for call in referenced:
        rows = [event for event in events if event.get("loop_id") == call.gateway_loop_id]
        boundaries = [event for event in rows if event.get("event") == "model_boundary_deferred"]
        completed = [event for event in rows if event.get("event") in (
            "model_led", "model_invocation_failed")]
        if len(boundaries) != 1 or len(completed) != 1:
            raise HarnessError("gateway reference needs one fresh canonical physical attempt")
        boundary, event = boundaries[0], completed[0]
        if (event.get("owner_loop_id") not in owner_ids
                or event.get("owner_loop_id") != boundary.get("owner_loop_id")
                or not event.get("semantic_call_id")
                or event.get("semantic_call_id") != boundary.get("semantic_call_id")
                or any(not event.get(key) or event.get(key) != boundary.get(key)
                       for key in ("loop_definition_id", "loop_definition_version", "loop_definition_digest"))
                or (event.get("provider"), event.get("model")) != (call.provider, call.model)
                or (event.get("event") == "model_led") != call.ok
                or not _usage_agrees(event, call)):
            raise HarnessError("gateway reference identity, status or usage mismatch")
        if not call.model:
            binding = boundary.get("request_model_binding")
            fields = {"record_type", "provider", "model", "route"}
            if (type(binding) is not dict or set(binding) != fields
                    or binding["record_type"] != "model_request_binding/v1"
                    or any(type(binding[name]) is not str or not binding[name].strip()
                           for name in ("provider", "model", "route"))
                    or binding["provider"] != call.provider or binding["route"] != call.route_id):
                raise HarnessError("unknown reported model requires its exact canonical requested identity")
            requested[call.gateway_loop_id] = (binding["provider"], binding["model"], binding["route"])
    return requested
