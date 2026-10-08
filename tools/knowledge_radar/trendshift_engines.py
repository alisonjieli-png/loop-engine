"""Two selectable adapters at the existing knowledge-radar source edge.

The Signal adapter reads the documented authenticated API. The public adapter
reads only the current daily page's JSON-LD. Neither grants republication,
executes website scripts, resolves GitHub identities independently or retries
through a different engine after a provider refusal.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from hashlib import sha256
import json
from pathlib import Path

from .engines import EngineAnswer, FAILED, OK, PARTIAL, ReadContext, observation
from .records import RadarQuestion, ResearchCost, SourceBinding, read_contracts
from .trendshift_parsing import parse_page
from .trendshift_request import API_SCHEMA, API_SCHEMA_SHA256, PUBLIC, SIGNAL, SPIKES, TERMS, TrendshiftError, read_request


def source_contract(engine):
    return read_contracts(json.loads(Path(__file__).with_name("source-contracts-v1.json").read_text()))[engine]


def read_context(request, *, observed_at, network=None, repository=None):
    """A typed internal research question, not a new registry or a published feed definition."""
    binding = SourceBinding(request.engine, "Trendshift source observations", request.parameters())
    question = RadarQuestion(id="trendshift_repository_discovery", question="Which repositories does this source selection list?",
        title="Trendshift repository discovery", area="tools", status="active", gap_reason="", audience="Internal source research",
        constraints=("Private source observations only",), baseline="No source observation",
        acceptable_evidence=("Exact source response and typed fields",), intended_output="Private source references",
        purpose="Select repositories for later independent source research", use_when="A bounded source read is authorized",
        sensitivity="general", research_cost=ResearchCost(5, 1), volatility="days", refresh="daily", delivery=("tool",),
        valid_days=1, reask=("Source selection changes",), recheck=("Source access or contract changes",),
        not_established=("Adoption, quality, numeric identity resolution and code reuse rights",),
        would_change=("A changed source response",), limit=request.limit, sources=(binding,), seeds=(), assets={})
    return ReadContext(question, binding, observed_at, observed_at[:10], source_contract(request.engine), repository, network=network)


class TrendshiftPublic:
    engine_id, engine_version = PUBLIC, "1.0.0"
    material_facts = ("source_rank", "source_list_date", "source_period")

    def parse(self, context, body, *, transport_observed=True):
        return self.parse_with_page(context, body, transport_observed=transport_observed)[0]

    def parse_with_page(self, context, body, *, transport_observed=True):
        """Keep pagination in the private CLI result without changing the shared source edge."""
        request = read_request(context.binding.parameters)
        if request.engine != self.engine_id:raise TrendshiftError("trendshift_engine_binding_mismatch")
        host, path, query, _ = request.target(context.today)
        page = parse_page(body, request)
        digest = sha256(body).hexdigest()
        source_url = "https://" + host + path
        observed, period = [], request.period
        for row in page.rows:
            identity = ("github-id:" + str(row["github_repository_id"])) if row["github_repository_id"] else "github-slug:" + row["full_name"].lower()
            if request.kind == SPIKES:
                freshness = "historical_gain_window"
            elif period is not None:
                freshness = "historical_rank_with_query_time_counts" if request.engine == SIGNAL else "historical"
            elif page.source_date is None:
                freshness = "source_period_not_reported"
            else:
                age = (date.fromisoformat(context.today) - date.fromisoformat(page.source_date)).days
                freshness = ("stale_source_list" if age > 1 else "source_clock_ahead" if age < 0
                             else "source_dated_list_local_timezone_unknown")
            facts = {**row, "source_kind": request.kind, "source_window": request.window, "source_period": period,
                     "source_list_date": page.source_date, "freshness": freshness,
                     "source_body_sha256": digest, "source_rows": page.source_rows,
                     "source_query": str(sorted(query.items())), "source_claims_independently_verified": False,
                     "numeric_github_id_resolved_independently": False, "raw_redistribution_allowed": False,
                     "delivery_scope": "private_research", "rights_terms": TERMS,
                     "transport_observed": transport_observed, "metrics_are_historical_end_counts": False,
                     "global_rank_known": row["source_rank"] is not None}
            if request.kind == SPIKES:
                facts.update(gain_metric=request.metric, window_start=request.start, window_end=request.end)
            if request.engine == SIGNAL:
                facts.update(api_contract_url=API_SCHEMA, api_contract_sha256=API_SCHEMA_SHA256)
                if request.kind != SPIKES:facts["current_counts_observed_at"] = context.observed_at
            value = observation(context, self, key=identity, origin=identity, title=row["full_name"], url=row["github_url"],
                source_address=source_url, facts=facts, licence=None,
                licence_basis="Trendshift restricted source data; repository code rights are not established",
                source_published_at=page.source_date, claim_dated_by_source=bool(page.source_date and period is None),
                last_verified_at=context.observed_at if transport_observed else None)
            observed.append(value)
        answer = EngineAnswer(PARTIAL if page.excluded else OK, "empty_source_list" if not page.rows else "source_page_parsed",
                              observations=tuple(observed), excluded=page.excluded, complete=page.complete)
        return answer, page

    def read(self, context):
        return self.read_with_page(context)[0]

    def read_with_page(self, context):
        if not getattr(context.network, "trendshift_managed_transport", False):
            return EngineAnswer(FAILED, "trendshift_managed_transport_required", complete=False), None
        request = read_request(context.binding.parameters)
        if request.engine != self.engine_id:raise TrendshiftError("trendshift_engine_binding_mismatch")
        host, path, query, accept = request.target(context.today)
        before = context.network.budget.used
        answer = context.network.get(self.engine_id, host, path, query, accept=accept)
        spent = context.network.budget.used - before
        if answer.status != 200:
            reason = ("access_refused" if answer.status in (401, 403) else "rate_limited" if answer.status == 429 else
                      "source_not_found" if answer.status in (404, 410) else "unexpected_not_modified" if answer.status == 304 else
                      "source_http_error" if answer.status is not None else "source_transport_error")
            return EngineAnswer(FAILED, reason, requests=spent, complete=False), None
        try:
            parsed, page = self.parse_with_page(context, answer.body)
            return replace(parsed, requests=spent), page
        except (ValueError, RecursionError):
            return EngineAnswer(FAILED, "source_parse_failed", requests=spent, complete=False), None


class TrendshiftSignal(TrendshiftPublic):
    engine_id = SIGNAL

    def read_with_page(self, context):
        if not getattr(context.network, "trendshift_authenticated_transport", False):
            return EngineAnswer(FAILED, "signal_credential_transport_required", complete=False), None
        return super().read_with_page(context)


ENGINES = (TrendshiftSignal(), TrendshiftPublic())
