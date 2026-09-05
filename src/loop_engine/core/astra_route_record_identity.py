"""Pure validation and identity helpers for passive Astra route records.

This module performs no credential lookup, clock read, provider call, route
registration, or spending. It keeps canonical request identity separate from
candidate policy analysis and executable runtime authority.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


class AstraRouteRecordError(ValueError):
    """A passive Astra route record violates its local data contract."""


_ISSUER_REFERENCE = re.compile(
    r"^(?:user|organization|approval):[A-Za-z0-9_][A-Za-z0-9_.:/-]{0,159}$"
)
_SECRET_MARKERS = (
    "authorization:",
    "bearer ",
    "api_key=",
    "api_key:",
    "apikey=",
    "apikey:",
    "access_token=",
    "access_token:",
    "password=",
    "password:",
    "secret=",
    "secret:",
    "sk-",
    "sess-",
)


def one_line(value: object, name: str, *, allow_empty: bool = False) -> str:
    result = str(value).strip()
    if not result and not allow_empty:
        raise AstraRouteRecordError(f"{name} must be non-empty")
    if "\n" in result or "\r" in result or len(result) > 300:
        raise AstraRouteRecordError(f"{name} must be one short line")
    return result


def non_secret_reference(
    value: object,
    name: str,
    *,
    allow_empty: bool = False,
) -> str:
    result = one_line(value, name, allow_empty=allow_empty)
    lowered = result.lower()
    if result and any(marker in lowered for marker in _SECRET_MARKERS):
        raise AstraRouteRecordError(
            f"{name} must be a non-secret reference, never a credential value"
        )
    return result


def issuer_reference(value: object) -> str:
    result = non_secret_reference(value, "issuer_ref")
    if not _ISSUER_REFERENCE.fullmatch(result):
        raise AstraRouteRecordError(
            "issuer_ref must be a user, organization, or approval reference"
        )
    return result


def strings(values: tuple[str, ...], name: str) -> tuple[str, ...]:
    result = tuple(one_line(value, name) for value in values)
    if len(result) != len(set(result)):
        raise AstraRouteRecordError(f"{name} must not contain duplicates")
    return result


def optional_limit(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise AstraRouteRecordError(f"{name} must be a non-negative integer or unknown")
    return value


def positive_limit(value: int, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1:
        raise AstraRouteRecordError(f"{name} must be a positive integer")
    return value


def money(value: object | None, name: str) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise AstraRouteRecordError(f"{name} must be a monetary number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise AstraRouteRecordError(f"{name} must be a monetary number") from exc
    if not result.is_finite() or result < 0:
        raise AstraRouteRecordError(f"{name} must be finite and non-negative")
    return result


def timestamp(value: str, name: str) -> datetime:
    text = one_line(value, name)
    try:
        result = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AstraRouteRecordError(f"{name} must be an ISO-8601 timestamp") from exc
    if result.tzinfo is None:
        raise AstraRouteRecordError(f"{name} must include a timezone")
    return result.astimezone(timezone.utc)


def decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value.normalize(), "f")


def content_digest(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def text_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_digest(value: str, name: str) -> str:
    result = one_line(value, name)
    is_hex = all(character in "0123456789abcdef" for character in result)
    if len(result) != 64 or not is_hex:
        raise AstraRouteRecordError(f"{name} must be a SHA-256 digest")
    return result


def thinking_policy_binding(record: object) -> dict[str, object]:
    return {
        "policy_id": record.policy_id,
        "version": record.version,
        "mappings": [list(item) for item in record.mappings],
        "supported_efforts": list(record.supported_efforts),
    }


def capability_qualification_binding(record: object) -> dict[str, object]:
    return {
        "capability": record.capability,
        "model_declared": record.model_declared,
        "adapter_qualified": record.adapter_qualified,
        "qualification_ref": record.qualification_ref,
    }


def adapter_capability_binding(record: object) -> dict[str, object]:
    return {
        "version": record.version,
        "structured_output": capability_qualification_binding(record.structured_output),
        "tool_calling": capability_qualification_binding(record.tool_calling),
        "async_tool_calling": capability_qualification_binding(
            record.async_tool_calling
        ),
        "text_input_qualified": record.text_input_qualified,
        "text_output_qualified": record.text_output_qualified,
        "explicit_service_tier_qualified": (record.explicit_service_tier_qualified),
    }


def demand_binding(record: object) -> dict[str, object]:
    return {
        "demand_id": record.demand_id,
        "model_purpose": record.model_purpose,
        "thinking_power": record.thinking_power,
        "maximum_model_calls": record.maximum_model_calls,
        "maximum_input_tokens_per_call": record.maximum_input_tokens_per_call,
        "maximum_output_tokens_per_call": record.maximum_output_tokens_per_call,
        "service_tier": record.service_tier,
        "required_data_locality": record.required_data_locality,
        "required_modalities": list(record.required_modalities),
        "requires_structured_output": record.requires_structured_output,
        "requires_tool_calling": record.requires_tool_calling,
        "requires_async_tool_calling": record.requires_async_tool_calling,
    }


def authority_binding(record: object) -> dict[str, object]:
    return {
        "authority_id": record.authority_id,
        "issuer_ref": record.issuer_ref,
        "model_calls_authorized": record.model_calls_authorized,
        "paid_route_opt_in": record.paid_route_opt_in,
        "credential_ref": record.credential_ref,
        "authorized_route_name": record.authorized_route_name,
        "authorized_provider_id": record.authorized_provider_id,
        "authorized_model_id": record.authorized_model_id,
        "allowed_data_localities": list(record.allowed_data_localities),
        "allowed_service_tiers": list(record.allowed_service_tiers),
        "maximum_model_calls": record.maximum_model_calls,
        "maximum_input_tokens": record.maximum_input_tokens,
        "maximum_output_tokens": record.maximum_output_tokens,
        "maximum_total_tokens": record.maximum_total_tokens,
        "maximum_cost_usd": decimal_text(record.maximum_cost_usd),
        "version": record.version,
    }


def authority_safe_summary(record: object) -> dict[str, object]:
    return {
        "record_type": "paid_model_route_authority/v1",
        "authority_id": record.authority_id,
        "issuer_ref_present": True,
        "issuer_ref_sha256": text_digest(record.issuer_ref),
        "model_calls_authorized": record.model_calls_authorized,
        "paid_route_opt_in": record.paid_route_opt_in,
        "credential_ref": record.credential_ref,
        "authorized_route_name": record.authorized_route_name,
        "authorized_provider_id": record.authorized_provider_id,
        "authorized_model_id": record.authorized_model_id,
        "allowed_data_localities": list(record.allowed_data_localities),
        "allowed_service_tiers": list(record.allowed_service_tiers),
        "maximum_model_calls": record.maximum_model_calls,
        "maximum_input_tokens": record.maximum_input_tokens,
        "maximum_output_tokens": record.maximum_output_tokens,
        "maximum_total_tokens": record.maximum_total_tokens,
        "maximum_cost_usd": decimal_text(record.maximum_cost_usd),
        "version": record.version,
        "credential_value_present": False,
    }


def cost_exposure_dict(record: object) -> dict[str, object]:
    return {
        "maximum_model_calls": record.maximum_model_calls,
        "maximum_input_tokens": record.maximum_input_tokens,
        "maximum_output_tokens": record.maximum_output_tokens,
        "maximum_total_tokens": record.maximum_total_tokens,
        "input_rate_per_million_usd": str(record.input_rate_per_million_usd),
        "output_rate_per_million_usd": str(record.output_rate_per_million_usd),
        "service_tier": record.service_tier,
        "service_tier_multiplier": str(record.service_tier_multiplier),
        "long_context_surcharge_applied": record.long_context_surcharge_applied,
        "maximum_cost_usd": str(record.maximum_cost_usd),
        "method": record.method,
    }


def provider_readiness_binding(record: object) -> dict[str, object]:
    return {
        "availability": (
            record.availability.to_dict() if record.availability is not None else None
        ),
        "data_locality": record.data_locality,
        "data_locality_source_ref": record.data_locality_source_ref,
    }


def request_binding(record: object, schema_version: str) -> dict[str, object]:
    return {
        "record_type": "astra_route_readiness_request/v1",
        "schema_version": schema_version,
        "request_id": record.request_id,
        "demand": demand_binding(record.demand),
        "authority": authority_binding(record.authority),
        "provider_readiness": provider_readiness_binding(record.provider_readiness),
        "evaluated_at": record.evaluated_at,
        "reasoning_policy": thinking_policy_binding(record.reasoning_policy),
        "adapter_capabilities": adapter_capability_binding(record.adapter_capabilities),
    }
