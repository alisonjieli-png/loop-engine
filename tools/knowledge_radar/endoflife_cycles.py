"""Bounded endoflife.date v1 release cycle reader and support/EOL evaluator.

Separates upstream vendor-announced support and end-of-life dates from local
environment checks. Never invents a support date when a cycle marks EOL as a
boolean or omits active-support dates.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
import re

REQUEST_RECORD_TYPE = "endoflife_product_request/v1"
OBSERVATION_RECORD_TYPE = "endoflife_cycle_observation/v1"
ALLOWED_HOST = "endoflife.date"
MAXIMUM_RESPONSE_BYTES = 524288
MAXIMUM_CYCLES = 120
_PRODUCT = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")
_CYCLE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,31}\Z")


class EndOfLifeReadError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str = "endoflife_response_invalid") -> None:
    if not condition:
        raise EndOfLifeReadError(code)


def _iso_day(value: object) -> str:
    _require(isinstance(value, str), "endoflife_date_invalid")
    try:
        parsed = date.fromisoformat(value)
        _require(parsed.isoformat() == value, "endoflife_date_invalid")
    except ValueError:
        raise EndOfLifeReadError("endoflife_date_invalid") from None
    return value


@dataclass(frozen=True)
class EndOfLifeRequest:
    product: str
    pinned_cycle: str | None = None
    warning_window_days: int = 90

    def __post_init__(self) -> None:
        _require(isinstance(self.product, str) and bool(_PRODUCT.fullmatch(self.product)), "endoflife_product_invalid")
        if self.pinned_cycle is not None:
            _require(isinstance(self.pinned_cycle, str) and bool(_CYCLE.fullmatch(self.pinned_cycle)), "endoflife_cycle_invalid")
        _require(type(self.warning_window_days) is int and 1 <= self.warning_window_days <= 365, "endoflife_window_invalid")

    @property
    def endpoint_url(self) -> str:
        return f"https://{ALLOWED_HOST}/api/v1/products/{self.product}/"

    def plan(self) -> dict[str, object]:
        return {
            "record_type": REQUEST_RECORD_TYPE,
            "product": self.product,
            "pinned_cycle": self.pinned_cycle,
            "warning_window_days": self.warning_window_days,
            "endpoint_url": self.endpoint_url,
            "network_requests_dispatched": 0,
            "effects_granted": [],
        }


def _evaluate_cycle_status(
    eol_from: str | None,
    is_eol: bool | None,
    eoes_from: str | None,
    as_of_date: date,
    warning_days: int,
) -> tuple[str, int | None]:
    days_to_eol: int | None = None
    if eol_from is not None:
        days_to_eol = (date.fromisoformat(eol_from) - as_of_date).days
        if days_to_eol <= 0:
            return "end_of_life_reached", days_to_eol
        if days_to_eol <= warning_days:
            return "approaching_eol", days_to_eol
    elif is_eol:
        return "end_of_life_reached", None

    if eoes_from is not None:
        days_to_active_end = (date.fromisoformat(eoes_from) - as_of_date).days
        if days_to_active_end <= 0:
            return "active_support_ended", days_to_eol
        return "active_support", days_to_eol
    return "unknown_support", days_to_eol


def parse_product_cycles(
    body: bytes,
    request: EndOfLifeRequest,
    *,
    as_of: str,
) -> dict[str, object]:
    """Parse a bound endoflife.date v1 product capture; missing support stays unknown."""
    _require(type(body) is bytes and 0 < len(body) <= MAXIMUM_RESPONSE_BYTES, "endoflife_response_byte_limit")
    as_of_str = _iso_day(as_of)
    as_of_date = date.fromisoformat(as_of_str)
    try:
        raw = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise EndOfLifeReadError("endoflife_json_invalid") from None

    if type(raw) is dict and type(raw.get("result")) is dict:
        if "schema_version" in raw:
            _require(isinstance(raw["schema_version"], str)
                     and bool(re.fullmatch(r"1\.\d+\.\d+", raw["schema_version"])),
                     "endoflife_schema_version_unsupported")
        result_obj = raw["result"]
        _require(str(result_obj.get("name", "")).lower() == request.product, "endoflife_product_mismatch")
        releases = result_obj.get("releases")
    else:
        raise EndOfLifeReadError("endoflife_schema_invalid")

    _require(type(releases) is list and 0 < len(releases) <= MAXIMUM_CYCLES, "endoflife_cycles_limit")

    cycles: list[dict[str, object]] = []
    pinned_assessment: dict[str, object] | None = None
    seen_cycles: set[str] = set()

    for row in releases:
        _require(type(row) is dict, "endoflife_cycle_row_invalid")
        cycle_name = row.get("name")
        _require(isinstance(cycle_name, str) and bool(_CYCLE.fullmatch(cycle_name)), "endoflife_cycle_name_invalid")
        _require(cycle_name not in seen_cycles, "endoflife_duplicate_cycle")
        seen_cycles.add(cycle_name)

        release_date_raw = row.get("releaseDate")
        release_date = _iso_day(release_date_raw) if release_date_raw is not None else None

        eol_from_raw = row.get("eolFrom")
        is_eol = row.get("isEol")
        _require(is_eol is None or type(is_eol) is bool, "endoflife_eol_field_invalid")
        is_lts = row.get("isLts")
        _require(is_lts is None or type(is_lts) is bool, "endoflife_lts_field_invalid")
        eol_from: str | None = None
        if isinstance(eol_from_raw, str):
            eol_from = _iso_day(eol_from_raw)
        elif eol_from_raw is not None:
            raise EndOfLifeReadError("endoflife_eol_field_invalid")

        eoes_raw = row.get("eoasFrom")
        eoes_from = _iso_day(eoes_raw) if eoes_raw is not None else None

        latest_name = None
        if type(row.get("latest")) is dict and isinstance(row["latest"].get("name"), str):
            latest_name = row["latest"]["name"]
        elif row.get("latest") is not None:
            raise EndOfLifeReadError("endoflife_latest_version_invalid")
        if latest_name is not None:
            _require(bool(_CYCLE.fullmatch(latest_name)), "endoflife_latest_version_invalid")

        status, days_to_eol = _evaluate_cycle_status(
            eol_from,
            is_eol,
            eoes_from,
            as_of_date,
            request.warning_window_days,
        )
        cycle_record = {
            "cycle": cycle_name,
            "release_date": release_date,
            "active_support_ends_on": eoes_from,
            "security_eol_on": eol_from,
            "is_eol": (status == "end_of_life_reached") if eol_from is not None or is_eol is not None else None,
            "is_lts": is_lts,
            "latest_patch": latest_name,
            "lifecycle_status": status,
            "days_until_eol": days_to_eol,
        }
        cycles.append(cycle_record)
        if request.pinned_cycle is not None and cycle_name == request.pinned_cycle:
            pinned_assessment = cycle_record

    if request.pinned_cycle is not None and pinned_assessment is None:
        pinned_assessment = {
            "cycle": request.pinned_cycle,
            "lifecycle_status": "unknown_cycle_not_in_source",
            "days_until_eol": None,
        }

    return {
        "record_type": OBSERVATION_RECORD_TYPE,
        "product": request.product,
        "as_of": as_of_str,
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "cycle_count": len(cycles),
        "pinned_cycle_assessment": pinned_assessment,
        "cycles": cycles,
        "vendor_confirmation_required": True,
        "effects_granted": [],
    }
