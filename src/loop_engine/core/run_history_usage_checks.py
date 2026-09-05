"""Direct offline persistence checks for versioned Run History model usage.

The fixtures cross no provider, network, or external storage boundary.
"""
from __future__ import annotations

import tempfile

from .run_history import RunHistory, as_ledger_events


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
    return {"record_type": "run_history_usage_test/v1", "tests": tests,
            "passed": int(preserved), "total": 1,
            "all_passed": preserved}


__all__ = ("self_test",)
