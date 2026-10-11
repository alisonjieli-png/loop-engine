"""Public Greenhouse metadata behind the existing knowledge_radar_source/v1 edge.

The list endpoint is deliberately requested without content=true. Unknown
fields, job prose and application data never enter observations. A published
listing is a source claim, not verified hiring demand or an execution grant.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import parse_qsl, unquote, urlsplit, urlunsplit

from loop_engine.core.library_ingestion.https_transport import HTTPS_SCHEME

from .community_intake import hints, public_url, read_registry
from .engines import EngineAnswer, FAILED, OK, PARTIAL, ReadContext, clean_title, observation
from .records import RadarQuestion, ResearchCost, SourceBinding, read_contracts

ENGINE = "greenhouse_public_jobs"
REQUEST = "greenhouse_public_jobs_request/v1"
RESULT = "greenhouse_public_jobs_result/v1"
HOST = "boards-api.greenhouse.io"
MAXIMUM_BYTES = 1024 * 1024
MAXIMUM_ROWS = 1000
ACCOUNT = "greenhouse:public-job-board"
RIGHTS = {"source_contract_engine": ENGINE, "documentation_checked_on": "2026-10-11",
          "scope": "private_metadata_research", "raw_body_retained": False,
          "job_prose_retained": False, "redistribution_authorized": False,
          "employer_reuse_rights": "not_established"}
_CONTACT = re.compile(r"[^\s@]+@[^\s@]+|(?:\+?\d[\d ()-]{6,}\d)")


class GreenhouseError(ValueError):
    """A stable refusal code without supplied source text."""


@dataclass(frozen=True)
class GreenhouseRequest:
    board: str
    limit: int = 20

    def __post_init__(self):
        if type(self.board) is not str or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.board):
            raise GreenhouseError("greenhouse_board_invalid")
        if type(self.limit) is not int or not 1 <= self.limit <= 60:
            raise GreenhouseError("greenhouse_limit_invalid")

    @property
    def path(self):
        return "/v1/boards/" + self.board + "/jobs"

    @property
    def url(self):
        return urlunsplit((HTTPS_SCHEME, HOST, self.path, "", ""))

    def to_record(self):
        return {"record_type": REQUEST, **asdict(self)}


def read_request(value):
    if type(value) is not dict or set(value) != {"record_type", "board", "limit"} or value.get("record_type") != REQUEST:
        raise GreenhouseError("greenhouse_request_contract")
    return GreenhouseRequest(value["board"], value["limit"])


def source_contract():
    return read_contracts(json.loads(Path(__file__).with_name("source-contracts-v1.json").read_text()))[ENGINE]


def read_context(request, *, observed_at, network=None):
    binding = SourceBinding(ENGINE, "Public job metadata", request.to_record())
    question = RadarQuestion(id="public_job_metadata", question="Which published job metadata does this board report?",
        title="Public job source discovery", area="tools", status="active", gap_reason="", audience="Internal research",
        constraints=("Private metadata only; title hints are not task evidence",), baseline="No source observation",
        acceptable_evidence=("Bounded public board response",), intended_output="Private source leads",
        purpose="Select job responsibilities for later source verification", use_when="One public read is authorized",
        sensitivity="general", research_cost=ResearchCost(5, 1), volatility="days", refresh="daily", delivery=("tool",),
        valid_days=1, reask=("Source listing changes",), recheck=("Source access or terms change",),
        not_established=("Hiring demand, task frequency and source reuse rights",),
        would_change=("A new supported source observation",), limit=request.limit, sources=(binding,), seeds=(), assets={})
    return ReadContext(question, binding, observed_at, observed_at[:10], source_contract(), None, network=network)


def _text(value):
    if type(value) is not str or len(value) > 200 or _CONTACT.search(unescape(value)):
        raise GreenhouseError("unsafe_or_missing_text")
    title, refusal = clean_title(value)
    if refusal:
        raise GreenhouseError("unsafe_or_missing_text")
    return title


def _time(value):
    if value is None:
        return None
    if type(value) is not str or len(value) > 40 or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})", value):
        raise GreenhouseError("source_date_invalid")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except ValueError:
        raise GreenhouseError("source_date_invalid") from None


def _job_url(value, item_id):
    # Preserve the original URL, including its job identity. Never follow it.
    if type(value) is not str or "@" in unquote(value) or any(c.isspace() for c in value):
        raise GreenhouseError("source_url_invalid")
    try:
        public_url(value)
        parts = urlsplit(value)
        query = parse_qsl(parts.query, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise GreenhouseError("source_url_invalid") from None
    if parts.fragment or query not in ([], [("gh_jid", str(item_id))]):
        raise GreenhouseError("source_url_query_unsupported")
    return value


def _public_row(row):
    for name in ("is_private", "private", "is_internal", "internal", "internal_only", "draft"):
        if name in row and row[name] is not False:
            raise GreenhouseError("nonpublic_row")
    for name in ("isListed", "published", "is_published", "active", "is_public"):
        if name in row and row[name] is not True:
            raise GreenhouseError("nonpublic_row")
    for name, allowed in (("visibility", ("public", "published")), ("status", ("open", "published", "live"))):
        if name in row and row[name] not in allowed:
            raise GreenhouseError("nonpublic_row")


class GreenhousePublicJobs:
    engine_id, engine_version = ENGINE, "1.0.0"
    material_facts = ("metadata_sha256",)

    def parse(self, context, body, *, transport_observed=False):
        request = read_request(context.binding.parameters)
        if context.binding.engine != ENGINE or context.contract.engine_id != ENGINE:
            raise GreenhouseError("greenhouse_engine_binding_mismatch")
        if type(body) is not bytes or len(body) > MAXIMUM_BYTES:
            raise GreenhouseError("greenhouse_body_too_large")
        try:
            data = json.loads(body)
        except (ValueError, RecursionError):
            raise GreenhouseError("greenhouse_json_invalid") from None
        if type(data) is not dict or type(data.get("jobs")) is not list or len(data["jobs"]) > MAXIMUM_ROWS:
            raise GreenhouseError("greenhouse_list_invalid")
        _public_row(data)
        rows = data["jobs"]
        total = data.get("meta", {}).get("total") if type(data.get("meta")) is dict else None
        if type(total) is not int or total < 0:
            raise GreenhouseError("greenhouse_total_invalid")
        registry = read_registry()
        digest, seen, result, exclusions = sha256(body).hexdigest(), set(), [], {}
        for index, row in enumerate(rows):
            try:
                if type(row) is not dict:
                    raise GreenhouseError("job_row_invalid")
                _public_row(row)
                item_id, internal_id = row.get("id"), row.get("internal_job_id")
                if type(item_id) is not int or not 0 < item_id < 2**63 or type(internal_id) is not int or not 0 < internal_id < 2**63:
                    raise GreenhouseError("job_identity_invalid_or_prospect")
                if item_id in seen:
                    raise GreenhouseError("duplicate_job_id")
                seen.add(item_id)
                title = _text(row.get("title"))
                url = _job_url(row.get("absolute_url"), item_id)
                updated, published, expiry = (_time(row.get(key)) for key in ("updated_at", "first_published", "application_deadline"))
                employer = _text(row["company_name"]) if row.get("company_name") is not None else None
                projection = {"board": request.board, "item_id": item_id, "internal_job_id": internal_id,
                              "title": title, "url": url, "company_name": employer,
                              "updated_at": updated, "published_at": published, "valid_through": expiry}
                metadata_digest = sha256(json.dumps(projection, sort_keys=True).encode()).hexdigest()
                facts = {"board": request.board, "canonical_collection_id": "greenhouse:" + request.board,
                         "provider_item_id": str(item_id), "internal_job_id": str(internal_id),
                         "company_name": employer, "company_name_known": employer is not None,
                         "source_updated_at": updated, "source_updated_at_known": updated is not None,
                         "source_body_sha256": digest, "metadata_sha256": metadata_digest,
                         "source_rows": len(rows), "source_reported_total": total,
                         "source_claims_independently_verified": False, "transport_observed": transport_observed,
                         "public_list_presence_observed": transport_observed, "vacancy_status": "unverified",
                         "raw_redistribution_allowed": False, "delivery_scope": "private_research",
                         "signals": ",".join(hints(title, registry["signals"])),
                         "tools_mentioned": ",".join(hints(title, registry["tools"])),
                         "hint_basis": "literal_title_keywords_not_verified_tasks", "task_evidence": "not_collected"}
                key = "greenhouse:" + request.board + ":" + str(item_id)
                result.append(observation(context, self, key=key, origin=key, title=title, url=url,
                    source_address=request.url, facts=facts, licence=None,
                    licence_basis="Job text reuse rights unestablished; private metadata research only",
                    source_published_at=published, effective_until=expiry,
                    last_verified_at=context.observed_at if transport_observed else None))
            except GreenhouseError as error:
                reason = str(error)
                exclusions[reason] = exclusions.get(reason, 0) + 1
        excluded = [{"reason": reason, "count": count} for reason, count in sorted(exclusions.items())]
        limited = len(result) > request.limit
        if limited:
            excluded.append({"reason": "selection_limit", "count": len(result) - request.limit})
        if total != len(rows):
            excluded.append({"reason": "source_count_mismatch", "count": len(rows)})
        return EngineAnswer(PARTIAL if excluded else OK, "public_job_metadata_parsed", tuple(result[:request.limit]),
                            excluded=tuple(excluded), complete=not excluded)

    def read(self, context):
        if not getattr(context.network, "greenhouse_managed_transport", False):
            return EngineAnswer(FAILED, "greenhouse_managed_transport_required", complete=False)
        request = read_request(context.binding.parameters)
        before = context.network.budget.used
        response = context.network.get(ENGINE, HOST, request.path, {})
        spent = context.network.budget.used - before
        if response.status != 200:
            return EngineAnswer(FAILED, "public_job_read_failed", requests=spent, complete=False)
        try:
            return replace(self.parse(context, response.body, transport_observed=True), requests=spent)
        except (ValueError, RecursionError):
            return EngineAnswer(FAILED, "public_job_parse_failed", requests=spent, complete=False)
