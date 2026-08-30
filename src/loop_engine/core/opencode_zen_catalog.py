"""Live OpenCode Zen model metadata for safe zero-cost route binding.

OpenCode publishes the models it currently serves.  Models.dev publishes the
matching wire, price, context, and output limits.  This adapter intersects the
two sources so a temporary free-model name never becomes product logic.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone

from .model_capabilities import ModelOutputCapability, UnknownModelOutputLimit

ZEN_ROOT = "https://opencode.ai/zen/v1"
ZEN_MODELS_URL = f"{ZEN_ROOT}/models"
MODELS_DEV_URL = "https://models.dev/api.json"


@dataclass(frozen=True)
class OpenCodeZenModel:
    """One currently offered zero-cost chat-completions model."""

    model: str
    context_length: int
    maximum_output_tokens: int
    structured_output: bool


def _json(url: str, *, api_key: str = "") -> object:
    headers = ({"Authorization": f"Bearer {api_key}"} if api_key else {})
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, OSError, ValueError):
        return {}


def live_model_ids(*, api_key: str = "", payload: object = None) -> tuple[str, ...]:
    """Return exact model IDs from OpenCode's live Zen endpoint."""
    body = _json(ZEN_MODELS_URL, api_key=api_key) if payload is None else payload
    rows = body.get("data", ()) if isinstance(body, dict) else ()
    return tuple(sorted(
        str(row.get("id")) for row in rows
        if isinstance(row, dict) and row.get("id")))


def metadata(*, payload: object = None) -> dict:
    """Return the OpenCode provider block from Models.dev."""
    body = _json(MODELS_DEV_URL) if payload is None else payload
    provider = body.get("opencode", {}) if isinstance(body, dict) else {}
    return provider if isinstance(provider, dict) else {}


def zero_cost_models(*, api_key: str = "", live_payload: object = None,
                     metadata_payload: object = None) -> tuple[OpenCodeZenModel, ...]:
    """Intersect current Zen offerings with zero-cost, typed metadata.

    The generic chat-completions adapter can only use models whose declared
    wire is OpenAI compatible.  Models served through a Responses or Anthropic
    wire stay visible in OpenCode, but are not silently sent to the wrong API.
    """
    live = set(live_model_ids(api_key=api_key, payload=live_payload))
    provider = metadata(payload=metadata_payload)
    provider_npm = str(provider.get("npm") or "")
    rows = provider.get("models", {})
    if not isinstance(rows, dict):
        return ()
    choices = []
    for model_id, row in rows.items():
        if model_id not in live or not isinstance(row, dict):
            continue
        cost = row.get("cost") or {}
        limit = row.get("limit") or {}
        npm = str((row.get("provider") or {}).get("npm") or provider_npm)
        maximum = limit.get("output")
        if (row.get("status") == "deprecated"
                or npm != "@ai-sdk/openai-compatible"
                or cost.get("input") != 0 or cost.get("output") != 0
                or not isinstance(maximum, int) or maximum < 1):
            continue
        choices.append(OpenCodeZenModel(
            model=str(model_id),
            context_length=int(limit.get("context") or 0),
            maximum_output_tokens=maximum,
            structured_output=bool(row.get("structured_output"))))
    return tuple(sorted(
        choices,
        key=lambda item: (-int(item.structured_output),
                          -item.maximum_output_tokens,
                          -item.context_length, item.model)))


def select_zero_cost_model(*, api_key: str = "", live_payload: object = None,
                           metadata_payload: object = None) -> OpenCodeZenModel:
    """Select by declared compatibility and capacity, never by model name."""
    choices = zero_cost_models(
        api_key=api_key, live_payload=live_payload,
        metadata_payload=metadata_payload)
    if not choices:
        raise UnknownModelOutputLimit(
            "OpenCode Zen has no currently offered zero-cost OpenAI-compatible "
            "model with a declared output limit")
    return choices[0]


def output_capability_for(model: str, *, metadata_payload: object = None
                          ) -> ModelOutputCapability:
    """Resolve one exact output maximum from current Models.dev metadata."""
    provider = metadata(payload=metadata_payload)
    rows = provider.get("models", {}) if isinstance(provider, dict) else {}
    row = rows.get(model, {}) if isinstance(rows, dict) else {}
    maximum = (row.get("limit") or {}).get("output") \
        if isinstance(row, dict) else None
    if not isinstance(maximum, int) or maximum < 1:
        raise UnknownModelOutputLimit(
            f"Models.dev did not declare an output limit for {model!r}")
    return ModelOutputCapability(
        maximum, "Models.dev OpenCode model limit.output",
        endpoint=MODELS_DEV_URL,
        observed_at=datetime.now(timezone.utc).isoformat())


def self_test() -> dict:
    live = {"data": [{"id": "free-wide"}, {"id": "paid"},
                     {"id": "wrong-wire"}, {"id": "stale-free"}]}
    meta = {"opencode": {
        "npm": "@ai-sdk/openai-compatible",
        "models": {
            "free-wide": {"structured_output": True,
                          "limit": {"context": 100, "output": 80},
                          "cost": {"input": 0, "output": 0}},
            "paid": {"structured_output": True,
                     "limit": {"context": 200, "output": 100},
                     "cost": {"input": 1, "output": 2}},
            "wrong-wire": {"structured_output": True,
                           "provider": {"npm": "@ai-sdk/openai"},
                           "limit": {"context": 300, "output": 200},
                           "cost": {"input": 0, "output": 0}},
            "stale-free": {"structured_output": True,
                           "limit": {"context": 400, "output": 300},
                           "cost": {"input": 0, "output": 0}},
        }}}
    # Remove the stale model from the live offering.  It must not be selected
    # merely because the metadata service still knows about it.
    live["data"] = live["data"][:-1]
    selected = select_zero_cost_model(
        live_payload=live, metadata_payload=meta)
    capability = output_capability_for(
        selected.model, metadata_payload=meta)
    checks = [
        {"test": "selection_intersects_live_and_metadata",
         "passed": selected.model == "free-wide"},
        {"test": "paid_and_incompatible_wires_are_excluded",
         "passed": [item.model for item in zero_cost_models(
             live_payload=live, metadata_payload=meta)] == ["free-wide"]},
        {"test": "output_limit_is_source_backed",
         "passed": capability.maximum_output_tokens == 80
         and capability.source.startswith("Models.dev")},
    ]
    passed = sum(1 for item in checks if item["passed"])
    return {"record_type": "opencode_zen_catalog_test/v1",
            "tests": checks, "passed": passed, "total": len(checks),
            "all_passed": passed == len(checks),
            "provider_calls_made": 0}
