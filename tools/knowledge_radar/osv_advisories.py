"""Offline OSV querybatch reference projection, not a security certificate.

The batch endpoint returns advisory identifiers and modification timestamps.
Full advisory capture, withdrawal checking and fix selection are separate work.
This parser dispatches no requests and grants no effects.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
import re

REQUEST_RECORD_TYPE = "osv_querybatch_request/v1"
OBSERVATION_RECORD_TYPE = "osv_advisory_reference_observation/v1"
ALLOWED_HOST = "api.osv.dev"
BATCH_ENDPOINT = "https://api.osv.dev/v1/querybatch"
MAXIMUM_QUERIES = 64
MAXIMUM_RESPONSE_BYTES = 1048576
ALLOWED_ECOSYSTEMS = frozenset(("PyPI", "npm", "crates.io", "Go", "Maven", "NuGet"))
_PKG_NAME = re.compile(r"[A-Za-z0-9@][A-Za-z0-9._/@:+-]{0,191}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._!+-]{0,63}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_ADV_ID = re.compile(r"[A-Z0-9]{2,12}-[A-Za-z0-9._-]{2,64}\Z")
_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z)?\Z")


class OSVQueryError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _require(condition: bool, code: str = "osv_response_invalid") -> None:
    if not condition:
        raise OSVQueryError(code)


@dataclass(frozen=True)
class PackagePin:
    ecosystem: str
    name: str
    version: str | None = None
    commit: str | None = None
    page_token: str | None = None

    def __post_init__(self) -> None:
        _require(self.ecosystem in ALLOWED_ECOSYSTEMS, "osv_ecosystem_invalid")
        _require(isinstance(self.name, str) and bool(_PKG_NAME.fullmatch(self.name)), "osv_package_name_invalid")
        _require(
            (self.version is not None) ^ (self.commit is not None),
            "osv_pin_requires_exact_version_or_commit",
        )
        if self.version is not None:
            _require(isinstance(self.version, str) and bool(_VERSION.fullmatch(self.version)), "osv_version_invalid")
        if self.commit is not None:
            _require(isinstance(self.commit, str) and bool(_COMMIT.fullmatch(self.commit)), "osv_commit_invalid")
        if self.page_token is not None:
            _require(isinstance(self.page_token, str) and 0 < len(self.page_token) <= 256, "osv_page_token_invalid")

    def query_payload(self) -> dict[str, object]:
        if self.commit is not None:
            payload: dict[str, object] = {"commit": self.commit}
        else:
            payload = {"package": {"name": self.name, "ecosystem": self.ecosystem}, "version": self.version}
        if self.page_token is not None:
            payload["page_token"] = self.page_token
        return payload


@dataclass(frozen=True)
class OSVBatchRequest:
    pins: tuple[PackagePin, ...]

    def __post_init__(self) -> None:
        _require(type(self.pins) is tuple and 0 < len(self.pins) <= MAXIMUM_QUERIES, "osv_batch_size_invalid")
        _require(all(isinstance(pin, PackagePin) for pin in self.pins), "osv_pin_invalid")

    def body_dict(self) -> dict[str, object]:
        return {"queries": [pin.query_payload() for pin in self.pins]}

    def plan(self) -> dict[str, object]:
        return {
            "record_type": REQUEST_RECORD_TYPE,
            "endpoint_url": BATCH_ENDPOINT,
            "query_count": len(self.pins),
            "queries": [pin.query_payload() for pin in self.pins],
            "network_requests_dispatched": 0,
            "effects_granted": [],
        }


def parse_batch_response(
    body: bytes,
    request: OSVBatchRequest,
    *,
    observed_on: str,
) -> dict[str, object]:
    """Project only batch references; all remediation and withdrawal facts remain unknown."""
    _require(type(body) is bytes and 0 < len(body) <= MAXIMUM_RESPONSE_BYTES, "osv_response_byte_limit")
    _require(isinstance(observed_on, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", observed_on)), "osv_date_invalid")
    try:
        date.fromisoformat(observed_on)
    except ValueError:
        raise OSVQueryError("osv_date_invalid") from None
    try:
        data = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        raise OSVQueryError("osv_json_invalid") from None

    _require(type(data) is dict and type(data.get("results")) is list, "osv_results_invalid")
    results = data["results"]
    _require(len(results) == len(request.pins), "osv_result_count_mismatch")

    matches: list[dict[str, object]] = []
    no_matches_on_complete_query: list[str] = []
    paginated_queries: list[dict[str, object]] = []

    for pin, row in zip(request.pins, results):
        _require(type(row) is dict, "osv_result_row_invalid")
        next_token = row.get("next_page_token")
        if next_token is not None:
            _require(isinstance(next_token, str) and 0 < len(next_token) <= 256, "osv_page_token_invalid")
            paginated_queries.append(
                {
                    "ecosystem": pin.ecosystem,
                    "package": pin.name,
                    "version": pin.version,
                    "commit": pin.commit,
                    "next_page_token": next_token,
                }
            )
        vulns = row.get("vulns", [])
        _require(type(vulns) is list, "osv_vulns_list_invalid")
        active_for_pin = 0
        for vuln in vulns:
            _require(type(vuln) is dict, "osv_vuln_entry_invalid")
            adv_id = vuln.get("id")
            _require(isinstance(adv_id, str) and bool(_ADV_ID.fullmatch(adv_id)), "osv_advisory_id_invalid")
            modified = vuln.get("modified")
            _require(isinstance(modified, str) and bool(_ISO_TS.fullmatch(modified)), "osv_modified_invalid")
            try:
                datetime.fromisoformat(modified.replace("Z", "+00:00"))
            except ValueError:
                raise OSVQueryError("osv_modified_invalid") from None
            _require(set(vuln) == {"id", "modified"}, "osv_batch_reference_fields_invalid")
            active_for_pin += 1
            matches.append(
                {
                    "ecosystem": pin.ecosystem,
                    "package": pin.name,
                    "pinned_version": pin.version,
                    "pinned_commit": pin.commit,
                    "advisory_id": adv_id,
                    "modified": modified,
                    "advisory_details_checked": False,
                    "recommended_action": "Fetch and verify the full advisory before deciding remediation",
                }
            )
        if active_for_pin == 0 and next_token is None and pin.page_token is None:
            no_matches_on_complete_query.append(f"{pin.ecosystem}:{pin.name}@{pin.version or pin.commit}")

    return {
        "record_type": OBSERVATION_RECORD_TYPE,
        "observed_on": observed_on,
        "response_sha256": hashlib.sha256(body).hexdigest(),
        "queried_pin_count": len(request.pins),
        "reference_count": len(matches),
        "matches": matches,
        "no_matches_on_complete_query": no_matches_on_complete_query,
        "paginated_queries": paginated_queries,
        "coverage_complete": len(paginated_queries) == 0 and all(pin.page_token is None for pin in request.pins),
        "advisory_details_checked": False,
        "blanket_security_certificate": False,
        "unrelated_update_tasks_generated": 0,
        "effects_granted": [],
    }
