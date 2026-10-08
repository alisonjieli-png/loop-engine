"""Private organization-opportunity drafts projected from existing radar observations.

This is a passive export within the knowledge radar, not a source engine,
store, scheduler or sender. A caller supplies organization mappings and the
host's suppression set separately from untrusted observations. Exact evidence
binding proves which observation was used, not that its claims are true.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import ipaddress
import json
import re
import unicodedata
from urllib.parse import urlsplit

from loop_engine.core.library_ingestion.record_rules import (
    LibraryRecordError, digest_value, host_name, identifier, member, read_part,
    read_record, text_value,
)
from loop_engine.core.model_call_records import default_secret_patterns
from .records import Observation, day, read_observation

REQUEST_TYPE = "organization_opportunity_request/v1"
BRIEF_TYPE = "organization_opportunity_brief/v1"
KINDS = ("customer_candidate", "partner", "newsletter", "accelerator", "investor", "credit_program", "competitor")
MAXIMUM_BRIEFS = 100
MAXIMUM_OBSERVATIONS = 1000
_FIELDS = ("organization_id", "name", "website", "kind", "fit_hypothesis", "proposed_proof",
           "unknowns", "evidence", "contact_observation_key")
_PERSONAL_FIELD = re.compile(r"(?:^|_)(?:email|phone|person|employee|individual|contact|token|password|secret|credential|api_key)(?:_|$)", re.I)
_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_SECRET_PATTERNS = tuple(re.compile(pattern) for pattern in default_secret_patterns())
_CREDENTIAL_ASSIGNMENT = re.compile(r"(?i)\b(?:api[_-]?key|password|token|secret)\s*[:=]|\bbearer\s+")


def _refuse(code):
    raise LibraryRecordError(code, "organization opportunity export refused")


def _text(value, field, maximum=600):
    value = text_value(value, field, limit=maximum)
    if _EMAIL.search(value):
        _refuse("opportunity_personal_contact_refused")
    normalized = unicodedata.normalize("NFKC", value)
    if _CREDENTIAL_ASSIGNMENT.search(normalized) or any(pattern.search(normalized) for pattern in _SECRET_PATTERNS):
        _refuse("opportunity_credential_text_refused")
    return value


def _url(value):
    value = _text(value, "organization public page", 2048)
    try:
        parts = urlsplit(value)
        valid = (parts.scheme == "https" and parts.hostname and not parts.username and not parts.password
                 and parts.port in (None, 443) and not parts.query and not parts.fragment and value.isascii()
                 and not re.search(r"[\s\\]", value))
    except ValueError:
        valid = False
    if not valid:
        _refuse("opportunity_public_page_required")
    host = host_name(parts.hostname, "organization host")
    if host.endswith((".localhost", ".local", ".internal", ".invalid")):
        _refuse("opportunity_public_page_required")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return value
    _refuse("opportunity_public_page_required")


def _domain(url):
    return urlsplit(_url(url)).hostname.removeprefix("www.")


def _belongs(url, domain):
    host = _domain(url)
    return host == domain or host.endswith("." + domain)


def _canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        _refuse("opportunity_non_json_value")


def observation_digest(value: Observation) -> str:
    return sha256(_canonical(value.to_dict()).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class OpportunityDraft:
    """An immutable serialized draft; it cannot authorize publication or outreach."""

    serialized: str

    def to_dict(self):
        return json.loads(self.serialized)


def _observations(values):
    if type(values) not in (list, tuple) or len(values) > MAXIMUM_OBSERVATIONS:
        _refuse("opportunity_observation_bound")
    found = {}
    for value in values:
        row = read_observation(value.to_dict() if isinstance(value, Observation) else value)
        if row.key in found:
            _refuse("opportunity_duplicate_observation")
        found[row.key] = row
    return found


def _date(value):
    if value is None:
        return None
    if "T" in value:
        try:
            datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _refuse("opportunity_invalid_evidence_time")
    return date.fromisoformat(day(value[:10], "evidence day"))


def build_draft(request, observations, *, as_of: str, suppressed_domains) -> OpportunityDraft:
    """Bind selected public organization facts, preserve unknowns and compute freshness.

    No caller can set a current/approved status. Suppression comes from the
    host's existing managed records, not a field in a source or request.
    A missing contact observation leaves no route, never a guessed address.
    """
    now = date.fromisoformat(day(as_of, "as_of"))
    if type(suppressed_domains) not in (set, frozenset, tuple, list):
        _refuse("opportunity_suppression_required")
    blocked = {host_name(value, "suppressed domain").removeprefix("www.") for value in suppressed_domains}
    row = read_record(request, REQUEST_TYPE, _FIELDS)
    organization_id = identifier(row["organization_id"], "organization_id")
    website = _url(row["website"])
    if urlsplit(website).path not in ("", "/"):
        _refuse("opportunity_organization_origin_required")
    domain = _domain(website)
    unknowns = row["unknowns"]
    if type(unknowns) is not list or not 1 <= len(unknowns) <= 8:
        _refuse("opportunity_unknowns_required")
    unknowns = [_text(value, "unknown") for value in unknowns]
    evidence = row["evidence"]
    if type(evidence) is not list or not 1 <= len(evidence) <= 12:
        _refuse("opportunity_evidence_bound")
    available, selected, facts = _observations(observations), {}, []
    for reference in evidence:
        reference = read_part(reference, "evidence reference", ("observation_key", "observation_digest", "fact_keys"))
        key = _text(reference["observation_key"], "observation key", 300)
        item = available.get(key)
        expected = digest_value(reference["observation_digest"], "observation_digest")
        if item is None or observation_digest(item) != expected or key in selected:
            _refuse("opportunity_evidence_binding_invalid")
        if not _belongs(item.url, domain):
            _refuse("opportunity_official_organization_source_required")
        keys = reference["fact_keys"]
        if type(keys) is not list or not 1 <= len(keys) <= 8 or any(type(value) is not str for value in keys):
            _refuse("opportunity_fact_keys_invalid")
        if len(set(keys)) != len(keys) or any(value not in item.facts for value in keys):
            _refuse("opportunity_fact_binding_invalid")
        projected = {}
        for name in keys:
            if _PERSONAL_FIELD.search(name):
                _refuse("opportunity_personal_contact_refused")
            value = item.facts[name]
            if isinstance(value, str):
                _text(value, "organization fact")
            projected[name] = value
        selected[key] = item
        facts.append({"observation_key": key, "observation_digest": expected, "url": item.url,
                      "observed_at": item.observed_at, "last_verified_at": item.last_verified_at,
                      "review_after": item.review_after, "facts": projected,
                      "evidence_class": "source_observation_not_independent_verification"})
    contact_key = row["contact_observation_key"]
    contact = None
    if contact_key is not None:
        if type(contact_key) is not str or contact_key not in selected:
            _refuse("opportunity_contact_binding_invalid")
        contact = {"kind": "organization_page", "url": _url(selected[contact_key].url), "observation_key": contact_key}
    dates = [(_date(item.observed_at), _date(item.last_verified_at), _date(item.review_after),
              _date(item.effective_from), _date(item.effective_until)) for item in selected.values()]
    if any(observed > now or (verified is not None and verified > now) for observed, verified, *_ in dates):
        _refuse("opportunity_future_observation")
    stale = any((review is not None and review <= now) or (until is not None and until <= now)
                for _, _, review, _, until in dates)
    unknown = any(verified is None or review is None for _, verified, review, _, _ in dates)
    future = any(start is not None and start > now for _, _, _, start, _ in dates)
    freshness = "stale" if stale else "unverified" if unknown else "not_yet_effective" if future else "current"
    suppressed = any(domain == value or domain.endswith("." + value) for value in blocked)
    result = {"record_type": BRIEF_TYPE, "organization_id": organization_id,
              "name": _text(row["name"], "name", 180), "website": website,
              "kind": member(row["kind"], "kind", KINDS), "as_of": as_of,
              "fit_hypothesis": _text(row["fit_hypothesis"], "fit_hypothesis"),
              "proposed_proof": _text(row["proposed_proof"], "proposed_proof"),
              "unknowns": unknowns, "evidence": facts, "freshness": freshness,
              "contact_route": None if suppressed else contact,
              "suppression": "blocked" if suppressed else "not_listed",
              "review_state": "suppressed" if suppressed else "needs_review",
              "delivery_scope": "private_draft", "outreach_authorized": False,
              "source_content_authority": "untrusted_data", "customer_interest": "not_established",
              "coverage": "selected_observations_only"}
    return OpportunityDraft(_canonical(result))


def export_jsonl(requests, observations, *, as_of: str, suppressed_domains) -> str:
    """One bounded atomic projection. Validate every row before returning any bytes."""
    if type(requests) is not list or not 1 <= len(requests) <= MAXIMUM_BRIEFS:
        _refuse("opportunity_export_bound")
    rows = [build_draft(value, observations, as_of=as_of, suppressed_domains=suppressed_domains) for value in requests]
    identities = [row.to_dict()["organization_id"] for row in rows]
    if len(set(identities)) != len(identities):
        _refuse("opportunity_duplicate_organization")
    return "".join(row.serialized + "\n" for row in rows)
