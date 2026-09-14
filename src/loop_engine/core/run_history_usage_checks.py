"""Direct offline persistence checks for versioned Run History model usage.

The fixtures cross no provider, network, or external storage boundary.
"""
from __future__ import annotations

import tempfile

from .run_history import RunHistory, as_ledger_events
from .run_history_usage import TokenUsageTotals, total_model_usage


def self_test() -> dict:
    direct = RunHistory("run_usage_direct")
    direct_missing = direct.append("model_invocation", loop_id="direct")
    history = RunHistory.from_ledger([
        {"event": "model_led", "loop_id": "positive", "model": "m",
         "prompt_tokens": 2, "eval_tokens": 3, "total_tokens": 5},
        {"event": "model_led", "loop_id": "missing", "model": "m",
         "prompt_tokens": None, "eval_tokens": None, "total_tokens": None},
        {"event": "model_led", "loop_id": "partial", "model": "m",
         "prompt_tokens": None, "eval_tokens": 3, "total_tokens": None},
        {"event": "model_led", "loop_id": "zero", "model": "m",
         "prompt_tokens": 0, "eval_tokens": 0, "total_tokens": 0},
    ], run_id="run_usage_states")
    history.commit()
    with tempfile.TemporaryDirectory(prefix="run_history_usage_") as root:
        history.save(root)
        restored = RunHistory.load(root, history.run_id)
    calls = [event for event in restored.event_log
             if event.event_type == "model_invocation"]
    positive, missing, partial, zero = calls
    projected = as_ledger_events(calls)
    preserved = (
        direct_missing.prompt_tokens is None
        and direct_missing.eval_tokens is None
        and direct_missing.detail.get("usage_state") == "unknown"
        and (positive.prompt_tokens, positive.eval_tokens,
         positive.detail.get("total_tokens")) == (2, 3, 5)
        and missing.prompt_tokens is None and missing.eval_tokens is None
        and missing.detail.get("total_tokens") is None
        and missing.detail.get("usage_state") == "unknown"
        and partial.prompt_tokens is None and partial.eval_tokens == 3
        and partial.detail.get("usage_state") == "partial"
        and zero.prompt_tokens == 0 and zero.eval_tokens == 0
        and zero.detail.get("total_tokens") == 0
        and zero.detail.get("accounting_complete") is True
        and projected[1]["prompt_tokens"] is None
        and projected[3]["prompt_tokens"] == 0)
    tests = [{
        "test": "usage_states_survive_save_load_without_zero_coercion",
        "passed": preserved,
        "detail": "model_usage/v2 preserves positive, missing, partial, zero",
    }]
    def check(name, passed):
        tests.append({"test": name, "passed": bool(passed)})
    combined = total_model_usage(projected)
    check("aggregate_keeps_missing_usage_unknown_and_known_subtotals_separate",
          combined.total_tokens is None and combined.prompt_tokens is None
          and combined.eval_tokens is None and combined.known_subtotal == 8
          and combined.observations == 4 and not combined.complete)
    check("real_zero_and_empty_usage_remain_exact_zero",
          total_model_usage((projected[3],)).total_tokens == 0
          and total_model_usage(()).total_tokens == 0)
    partial_total = total_model_usage((projected[2],))
    check("partial_usage_preserves_known_direction",
          partial_total.prompt_tokens is None and partial_total.eval_tokens == 3)
    for invalid in (True, False, -1, 1.5, "3"):
        check("invalid_token_count_is_unknown_" + repr(invalid),
              total_model_usage(({"prompt_tokens": invalid, "eval_tokens": 0},)).total_tokens is None)
    check("usage_aggregation_is_additive_without_changing_unknowns",
          total_model_usage(projected[:2]) + total_model_usage(projected[2:]) == combined)
    for values in ((True, 0, 0, 0, 0), (0, 0, 0, 1, 0), (-1, 0, 0, 0, 0)):
        try:
            TokenUsageTotals(*values)
            refused = False
        except ValueError:
            refused = True
        check("invalid_usage_totals_refused_" + repr(values), refused)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "run_history_usage_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}


__all__ = ("self_test",)
