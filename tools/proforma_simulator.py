"""Deterministic multi-scenario pro-forma financial, email stack, and catalogue hosting simulator.

Models and compares three operational dimensions for Baltor (Loop Engine):
1. Pricing and tier mix variations across Conservative, Base, and Aggressive growth curves
   (Days 1 to 7, Month 1, Month 3, Month 6, Month 12), comparing Current Launch Pricing against
   Multi-Tier Expansion (including Basic $9 free window through December 31, 2026 Eastern,
   Founding 10 free Pro slots, Pro $49, Max $99, Team $199, AgentBriefs $299 and $799 pilots,
   and Playground sponsorships).
2. Email and support hosting engine variations across 100, 1,000, 10,000, and 100,000 monthly
   emails, including Resend Free + Cloudflare Email Routing, Resend Pro + Cloudflare Email
   Workers + Fastmail JMAP, AWS SES + Cloudflare Email Workers, and Postmark + Fastmail, with
   multi-provider failover wrapped in the six envelope layers of loop_engine.core.engines.envelope.
3. Hosting and catalogue serving variations across 1.90M, 5M, and 10M distinct component files,
   comparing Fly.io attached NVMe volumes, Fly.io control plane + Cloudflare R2 + Edge static
   export, and Cloudflare Worker-first edge caching + R2 content-addressed storage.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    EFFECT_NONE,
    EFFECT_UNKNOWN,
    ENGINE_SOURCE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    RECONCILE_BEFORE_RETRY,
    RETRY_AFTER_FIX,
    RETRY_AFTER_WAIT,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
     RecoveryAllowance,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    EnvelopePreflightCheck,
    run_preflight,
)
from loop_engine.core.engines.envelope_tracking import (  # noqa: E402
    DISPATCH,
    EFFECT_STATE_CONFIRMED,
    EFFECT_STATE_NONE,
    EFFECT_STATE_UNKNOWN,
    REQUEST_ANSWERED,
    REQUEST_OUTCOMES,
    TASK_COMPLETED,
    TASK_FAILED,
    journal_decision,
    journal_intent,
    journal_outcome,
     journal_reconciliation,
    request_identity_digest,
)

SIMULATOR_RECORD_VERSION = "proforma_comparison_report/v1"
EMAIL_FAILOVER_OUTCOME_VERSION = "email_dispatch_outcome/v1"

MODEL_CURRENT_LAUNCH = "current_launch"
MODEL_MULTI_TIER_EXPANSION = "multi_tier_expansion"
PRICING_MODELS = (MODEL_CURRENT_LAUNCH, MODEL_MULTI_TIER_EXPANSION)

SCENARIO_CONSERVATIVE = "conservative"
SCENARIO_BASE = "base"
SCENARIO_AGGRESSIVE = "aggressive"
GROWTH_SCENARIOS = (SCENARIO_CONSERVATIVE, SCENARIO_BASE, SCENARIO_AGGRESSIVE)

HORIZON_DAYS_1_TO_7 = "days_1_to_7"
HORIZON_MONTH_1 = "month_1"
HORIZON_MONTH_3 = "month_3"
HORIZON_MONTH_6 = "month_6"
HORIZON_MONTH_12 = "month_12"
HORIZONS = (
    HORIZON_DAYS_1_TO_7,
    HORIZON_MONTH_1,
    HORIZON_MONTH_3,
    HORIZON_MONTH_6,
    HORIZON_MONTH_12,
)

# Days 1-7 (Oct 2026) and Month 1 (Nov 2026) fall within the Basic free window through Dec 31, 2026.
FREE_WINDOW_HORIZONS = (HORIZON_DAYS_1_TO_7, HORIZON_MONTH_1)
FOUNDING_FREE_PRO_SLOT_CAP = 10
INFRASTRUCTURE_MONTHLY_ALLOWANCE_USD = 50.0
STRIPE_PERCENT_FEE = 0.029
STRIPE_FIXED_FEE_USD = 0.30
TARGET_MRR_USD = 100_000.0

STACK_RESEND_FREE_CF_ROUTING = "resend_free_cf_routing"
STACK_RESEND_PRO_CF_WORKERS_FASTMAIL = "resend_pro_cf_workers_fastmail"
STACK_AWS_SES_CF_WORKERS = "aws_ses_cf_workers"
STACK_POSTMARK_FASTMAIL = "postmark_fastmail"
EMAIL_STACKS = (
    STACK_RESEND_FREE_CF_ROUTING,
    STACK_RESEND_PRO_CF_WORKERS_FASTMAIL,
    STACK_AWS_SES_CF_WORKERS,
    STACK_POSTMARK_FASTMAIL,
)
EMAIL_VOLUMES = (100, 1_000, 10_000, 100_000)

ARCH_FLY_VOLUME_ORIGIN = "fly_volume_origin"
ARCH_FLY_ORIGIN_R2_EDGE_EXPORT = "fly_origin_r2_edge_export"
ARCH_WORKER_FIRST_R2_D1_CACHE = "worker_first_r2_d1_cache"
HOSTING_ARCHITECTURES = (
    ARCH_FLY_VOLUME_ORIGIN,
    ARCH_FLY_ORIGIN_R2_EDGE_EXPORT,
    ARCH_WORKER_FIRST_R2_D1_CACHE,
)
CATALOGUE_FILE_COUNTS = (1_900_000, 5_000_000, 10_000_000)

FAILURE_NONE = "none"
FAILURE_QUOTA_EXCEEDED = "quota_exceeded"
FAILURE_PROVIDER_UNAVAILABLE = "provider_unavailable"
FAILURE_DROPPED_AFTER_WRITE = "dropped_after_write"
FAILURE_INVALID_RECIPIENT = "invalid_recipient"
SIMULATED_FAILURES = (
    FAILURE_NONE,
    FAILURE_QUOTA_EXCEEDED,
    FAILURE_PROVIDER_UNAVAILABLE,
    FAILURE_DROPPED_AFTER_WRITE,
    FAILURE_INVALID_RECIPIENT,
)

REFUSAL_OUTCOME = REQUEST_OUTCOMES[3]


class ProformaSimulationError(ValueError):
    """Raised when a simulation parameter or state violates a declared boundary constraint."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class PricingCatalog:
    """Monthly unit prices in USD for Baltor and sibling brand offerings."""

    basic_monthly_usd: float = 9.0
    pro_monthly_usd: float = 49.0
    pro_annual_monthly_equiv_usd: float = 290.0 / 12.0
    max_monthly_usd: float = 99.0
    team_monthly_usd: float = 199.0
    agentbriefs_standard_usd: float = 299.0
    agentbriefs_enterprise_usd: float = 799.0
    playground_sponsor_usd: float = 1_000.0
    founding_free_pro_cap: int = FOUNDING_FREE_PRO_SLOT_CAP

    def __post_init__(self) -> None:
        for field_name in (
            "basic_monthly_usd",
            "pro_monthly_usd",
            "pro_annual_monthly_equiv_usd",
            "max_monthly_usd",
            "team_monthly_usd",
            "agentbriefs_standard_usd",
            "agentbriefs_enterprise_usd",
            "playground_sponsor_usd",
        ):
            val = getattr(self, field_name)
            if not isinstance(val, (int, float)) or val <= 0 or not math.isfinite(val):
                raise ProformaSimulationError(
                    "invalid_price",
                    f"{field_name} must be a positive finite number, got {val!r}",
                )
        if (
            not isinstance(self.founding_free_pro_cap, int)
            or self.founding_free_pro_cap < 0
            or self.founding_free_pro_cap > FOUNDING_FREE_PRO_SLOT_CAP
        ):
            raise ProformaSimulationError(
                "invalid_founding_cap",
                f"founding_free_pro_cap must be between 0 and {FOUNDING_FREE_PRO_SLOT_CAP}",
            )


@dataclass(frozen=True)
class HorizonCohortMix:
    """Subscriber and sponsor counts at one horizon checkpoint."""

    horizon: str
    in_basic_free_window: bool
    founding_free_pro_accounts: int
    public_good_free_accounts: int
    basic_free_preview_accounts: int
    basic_paid_opt_in_accounts: int
    pro_monthly_accounts: int
    pro_annual_accounts: int
    max_monthly_accounts: int
    team_monthly_accounts: int
    agentbriefs_standard_accounts: int
    agentbriefs_enterprise_accounts: int
    playground_sponsors: int

    def __post_init__(self) -> None:
        if self.horizon not in HORIZONS:
            raise ProformaSimulationError("invalid_horizon", f"unknown horizon {self.horizon!r}")
        if self.founding_free_pro_accounts > FOUNDING_FREE_PRO_SLOT_CAP:
            raise ProformaSimulationError(
                "founding_cap_exceeded",
                f"founding_free_pro_accounts ({self.founding_free_pro_accounts}) exceeds cap {FOUNDING_FREE_PRO_SLOT_CAP}",
            )
        if self.in_basic_free_window and self.basic_paid_opt_in_accounts > 0:
            raise ProformaSimulationError(
                "basic_charged_during_free_window",
                "basic_paid_opt_in_accounts must be 0 while Basic is in its free window through Dec 31, 2026",
            )
        for count_field in (
            "founding_free_pro_accounts",
            "public_good_free_accounts",
            "basic_free_preview_accounts",
            "basic_paid_opt_in_accounts",
            "pro_monthly_accounts",
            "pro_annual_accounts",
            "max_monthly_accounts",
            "team_monthly_accounts",
            "agentbriefs_standard_accounts",
            "agentbriefs_enterprise_accounts",
            "playground_sponsors",
        ):
            value = getattr(self, count_field)
            if not isinstance(value, int) or value < 0:
                raise ProformaSimulationError(
                    "negative_cohort_count",
                    f"{count_field} must be a non-negative integer, got {value!r}",
                )


@dataclass(frozen=True)
class ProformaHorizonProjection:
    """Calculated financial and operational metrics for one (model, scenario, horizon) tuple."""

    pricing_model: str
    growth_scenario: str
    horizon: str
    in_basic_free_window: bool
    total_registered_accounts: int
    paid_subscriber_accounts: int
    free_supported_accounts: int
    gross_mrr_usd: float
    annual_prepaid_cash_inflow_usd: float
    stripe_fees_usd: float
    infrastructure_cost_usd: float
    email_stack_cost_usd: float
    net_mrr_usd: float
    operating_margin_pct: float
    mrr_target_progress_pct: float
    revenue_by_stream_usd: Mapping[str, float]

    def to_dict(self) -> dict:
        return {
            "pricing_model": self.pricing_model,
            "growth_scenario": self.growth_scenario,
            "horizon": self.horizon,
            "in_basic_free_window": self.in_basic_free_window,
            "total_registered_accounts": self.total_registered_accounts,
            "paid_subscriber_accounts": self.paid_subscriber_accounts,
            "free_supported_accounts": self.free_supported_accounts,
            "gross_mrr_usd": round(self.gross_mrr_usd, 2),
            "annual_prepaid_cash_inflow_usd": round(self.annual_prepaid_cash_inflow_usd, 2),
            "stripe_fees_usd": round(self.stripe_fees_usd, 2),
            "infrastructure_cost_usd": round(self.infrastructure_cost_usd, 2),
            "email_stack_cost_usd": round(self.email_stack_cost_usd, 2),
            "net_mrr_usd": round(self.net_mrr_usd, 2),
            "operating_margin_pct": round(self.operating_margin_pct, 2),
            "mrr_target_progress_pct": round(self.mrr_target_progress_pct, 2),
            "revenue_by_stream_usd": {k: round(v, 2) for k, v in self.revenue_by_stream_usd.items()},
        }


# Cohort trajectories per scenario and horizon before pricing-model filtering.
# In MODEL_CURRENT_LAUNCH, only Basic ($9 after Dec 2026), Pro ($49 monthly / $290 annual),
# Founding 10 free Pro slots, and Public Good free accounts are active (Max, Team, AgentBriefs,
# and Playground sponsorships are zeroed out because their paid checkouts are not yet active).
_SCENARIO_COHORTS: Mapping[str, Mapping[str, dict]] = MappingProxyType({
    SCENARIO_CONSERVATIVE: MappingProxyType({
        HORIZON_DAYS_1_TO_7: {
            "founding": 10, "public_good": 15, "basic_free": 40, "basic_paid": 0,
            "pro_mo": 4, "pro_yr": 1, "max_mo": 1, "team_mo": 0, "ab_std": 0, "ab_ent": 0, "sponsors": 0,
        },
        HORIZON_MONTH_1: {
            "founding": 10, "public_good": 45, "basic_free": 140, "basic_paid": 0,
            "pro_mo": 18, "pro_yr": 4, "max_mo": 5, "team_mo": 1, "ab_std": 1, "ab_ent": 0, "sponsors": 0,
        },
        HORIZON_MONTH_3: {
            "founding": 10, "public_good": 120, "basic_free": 0, "basic_paid": 85,
            "pro_mo": 55, "pro_yr": 12, "max_mo": 16, "team_mo": 4, "ab_std": 3, "ab_ent": 1, "sponsors": 1,
        },
        HORIZON_MONTH_6: {
            "founding": 10, "public_good": 260, "basic_free": 0, "basic_paid": 210,
            "pro_mo": 130, "pro_yr": 25, "max_mo": 42, "team_mo": 12, "ab_std": 8, "ab_ent": 2, "sponsors": 2,
        },
        HORIZON_MONTH_12: {
            "founding": 10, "public_good": 600, "basic_free": 0, "basic_paid": 520,
            "pro_mo": 310, "pro_yr": 60, "max_mo": 110, "team_mo": 30, "ab_std": 20, "ab_ent": 6, "sponsors": 4,
        },
    }),
    SCENARIO_BASE: MappingProxyType({
        HORIZON_DAYS_1_TO_7: {
            "founding": 10, "public_good": 30, "basic_free": 95, "basic_paid": 0,
            "pro_mo": 12, "pro_yr": 3, "max_mo": 4, "team_mo": 1, "ab_std": 1, "ab_ent": 0, "sponsors": 0,
        },
        HORIZON_MONTH_1: {
            "founding": 10, "public_good": 110, "basic_free": 380, "basic_paid": 0,
            "pro_mo": 48, "pro_yr": 10, "max_mo": 15, "team_mo": 4, "ab_std": 3, "ab_ent": 1, "sponsors": 1,
        },
        HORIZON_MONTH_3: {
            "founding": 10, "public_good": 320, "basic_free": 0, "basic_paid": 260,
            "pro_mo": 165, "pro_yr": 35, "max_mo": 55, "team_mo": 16, "ab_std": 10, "ab_ent": 3, "sponsors": 2,
        },
        HORIZON_MONTH_6: {
            "founding": 10, "public_good": 750, "basic_free": 0, "basic_paid": 680,
            "pro_mo": 420, "pro_yr": 85, "max_mo": 150, "team_mo": 45, "ab_std": 28, "ab_ent": 9, "sponsors": 5,
        },
        HORIZON_MONTH_12: {
            "founding": 10, "public_good": 1_800, "basic_free": 0, "basic_paid": 1_650,
            "pro_mo": 980, "pro_yr": 190, "max_mo": 380, "team_mo": 115, "ab_std": 65, "ab_ent": 22, "sponsors": 10,
        },
    }),
    SCENARIO_AGGRESSIVE: MappingProxyType({
        HORIZON_DAYS_1_TO_7: {
            "founding": 10, "public_good": 60, "basic_free": 240, "basic_paid": 0,
            "pro_mo": 32, "pro_yr": 8, "max_mo": 10, "team_mo": 3, "ab_std": 2, "ab_ent": 1, "sponsors": 1,
        },
        HORIZON_MONTH_1: {
            "founding": 10, "public_good": 250, "basic_free": 950, "basic_paid": 0,
            "pro_mo": 140, "pro_yr": 30, "max_mo": 45, "team_mo": 12, "ab_std": 8, "ab_ent": 3, "sponsors": 2,
        },
        HORIZON_MONTH_3: {
            "founding": 10, "public_good": 800, "basic_free": 0, "basic_paid": 820,
            "pro_mo": 540, "pro_yr": 110, "max_mo": 190, "team_mo": 60, "ab_std": 35, "ab_ent": 14, "sponsors": 6,
        },
        HORIZON_MONTH_6: {
            "founding": 10, "public_good": 1_900, "basic_free": 0, "basic_paid": 2_100,
            "pro_mo": 1_250, "pro_yr": 240, "max_mo": 480, "team_mo": 150, "ab_std": 85, "ab_ent": 32, "sponsors": 12,
        },
        HORIZON_MONTH_12: {
            "founding": 10, "public_good": 4_500, "basic_free": 0, "basic_paid": 4_800,
            "pro_mo": 2_600, "pro_yr": 500, "max_mo": 1_050, "team_mo": 340, "ab_std": 180, "ab_ent": 68, "sponsors": 25,
        },
    }),
})


def build_cohort_mix(
    pricing_model: str,
    growth_scenario: str,
    horizon: str,
) -> HorizonCohortMix:
    """Build a validated cohort mix for one pricing model, growth scenario, and horizon."""
    if pricing_model not in PRICING_MODELS:
        raise ProformaSimulationError("invalid_pricing_model", f"unknown pricing_model {pricing_model!r}")
    if growth_scenario not in GROWTH_SCENARIOS:
        raise ProformaSimulationError("invalid_growth_scenario", f"unknown growth_scenario {growth_scenario!r}")
    if horizon not in HORIZONS:
        raise ProformaSimulationError("invalid_horizon", f"unknown horizon {horizon!r}")
    raw = _SCENARIO_COHORTS[growth_scenario][horizon]
    in_free_window = horizon in FREE_WINDOW_HORIZONS
    is_expansion = pricing_model == MODEL_MULTI_TIER_EXPANSION
    # Under current_launch, higher tiers without active checkout (Max, Team, AgentBriefs, Sponsors)
    # stay at 0 paid accounts, while 35% of would-be Max/Team buyers subscribe to Pro ($49) instead.
    diverted_to_pro = 0 if is_expansion else round(0.35 * (raw["max_mo"] + raw["team_mo"]))
    return HorizonCohortMix(
        horizon=horizon,
        in_basic_free_window=in_free_window,
        founding_free_pro_accounts=raw["founding"],
        public_good_free_accounts=raw["public_good"],
        basic_free_preview_accounts=raw["basic_free"],
        basic_paid_opt_in_accounts=raw["basic_paid"],
        pro_monthly_accounts=raw["pro_mo"] + diverted_to_pro,
        pro_annual_accounts=raw["pro_yr"],
        max_monthly_accounts=raw["max_mo"] if is_expansion else 0,
        team_monthly_accounts=raw["team_mo"] if is_expansion else 0,
        agentbriefs_standard_accounts=raw["ab_std"] if is_expansion else 0,
        agentbriefs_enterprise_accounts=raw["ab_ent"] if is_expansion else 0,
        playground_sponsors=raw["sponsors"] if is_expansion else 0,
    )


def evaluate_cohort_projection(
    pricing_model: str,
    growth_scenario: str,
    cohort: HorizonCohortMix,
    catalog: PricingCatalog | None = None,
) -> ProformaHorizonProjection:
    """Compute MRR, Stripe fees, infrastructure/email costs, and net margin for a cohort mix."""
    if pricing_model not in PRICING_MODELS:
        raise ProformaSimulationError("invalid_pricing_model", f"unknown pricing_model {pricing_model!r}")
    if growth_scenario not in GROWTH_SCENARIOS:
        raise ProformaSimulationError("invalid_growth_scenario", f"unknown growth_scenario {growth_scenario!r}")
    prices = catalog or PricingCatalog()
    if cohort.founding_free_pro_accounts > prices.founding_free_pro_cap:
        raise ProformaSimulationError(
            "founding_cap_exceeded",
            f"founding_free_pro_accounts ({cohort.founding_free_pro_accounts}) > {prices.founding_free_pro_cap}",
        )

    streams = {
        "basic_feeds": cohort.basic_paid_opt_in_accounts * prices.basic_monthly_usd,
        "pro_monthly": cohort.pro_monthly_accounts * prices.pro_monthly_usd,
        "pro_annual_amortized": cohort.pro_annual_accounts * prices.pro_annual_monthly_equiv_usd,
        "max_monthly": cohort.max_monthly_accounts * prices.max_monthly_usd,
        "team_monthly": cohort.team_monthly_accounts * prices.team_monthly_usd,
        "agentbriefs_standard": cohort.agentbriefs_standard_accounts * prices.agentbriefs_standard_usd,
        "agentbriefs_enterprise": cohort.agentbriefs_enterprise_accounts * prices.agentbriefs_enterprise_usd,
        "playground_sponsorships": cohort.playground_sponsors * prices.playground_sponsor_usd,
    }
    gross_mrr = sum(streams.values())
    annual_cash_inflow = cohort.pro_annual_accounts * (prices.pro_annual_monthly_equiv_usd * 12.0)

    paid_accounts = (
        cohort.basic_paid_opt_in_accounts
        + cohort.pro_monthly_accounts
        + cohort.pro_annual_accounts
        + cohort.max_monthly_accounts
        + cohort.team_monthly_accounts
        + cohort.agentbriefs_standard_accounts
        + cohort.agentbriefs_enterprise_accounts
        + cohort.playground_sponsors
    )
    free_accounts = (
        cohort.founding_free_pro_accounts
        + cohort.public_good_free_accounts
        + cohort.basic_free_preview_accounts
    )
    total_accounts = paid_accounts + free_accounts

    # Monthly card transactions: monthly subscribers + 1/12th of annual renewals per month on average.
    monthly_tx_count = (
        cohort.basic_paid_opt_in_accounts
        + cohort.pro_monthly_accounts
        + max(1, round(cohort.pro_annual_accounts / 12.0)) if cohort.pro_annual_accounts else 0
    ) + (
        cohort.max_monthly_accounts
        + cohort.team_monthly_accounts
        + cohort.agentbriefs_standard_accounts
        + cohort.agentbriefs_enterprise_accounts
        + cohort.playground_sponsors
    )
    stripe_fees = gross_mrr * STRIPE_PERCENT_FEE + monthly_tx_count * STRIPE_FIXED_FEE_USD

    # Infrastructure scales from the $38.50/mo Fly + R2 1.90M baseline up with active traffic.
    base_infra = 38.50
    traffic_scaling = max(0.0, (total_accounts - 200) * 0.035)
    infra_cost = round(base_infra + traffic_scaling, 2)

    # Email volume scales with total accounts (~6 transactional/digest emails per account per month).
    est_emails = max(100, total_accounts * 6)
    email_cost = 0.0 if est_emails <= 3_000 else (25.0 if est_emails <= 50_000 else 25.0 + (est_emails - 50_000) * 0.0009)

    net_mrr = gross_mrr - stripe_fees - infra_cost - email_cost
    margin_pct = (net_mrr / gross_mrr * 100.0) if gross_mrr > 0 else 0.0
    target_pct = (gross_mrr / TARGET_MRR_USD) * 100.0

    return ProformaHorizonProjection(
        pricing_model=pricing_model,
        growth_scenario=growth_scenario,
        horizon=cohort.horizon,
        in_basic_free_window=cohort.in_basic_free_window,
        total_registered_accounts=total_accounts,
        paid_subscriber_accounts=paid_accounts,
        free_supported_accounts=free_accounts,
        gross_mrr_usd=gross_mrr,
        annual_prepaid_cash_inflow_usd=annual_cash_inflow,
        stripe_fees_usd=stripe_fees,
        infrastructure_cost_usd=infra_cost,
        email_stack_cost_usd=email_cost,
        net_mrr_usd=net_mrr,
        operating_margin_pct=margin_pct,
        mrr_target_progress_pct=target_pct,
        revenue_by_stream_usd=streams,
    )


def simulate_pricing_matrix(catalog: PricingCatalog | None = None) -> list[ProformaHorizonProjection]:
    """Run all (pricing_model, growth_scenario, horizon) combinations."""
    results: list[ProformaHorizonProjection] = []
    for model in PRICING_MODELS:
        for scenario in GROWTH_SCENARIOS:
            for horizon in HORIZONS:
                cohort = build_cohort_mix(model, scenario, horizon)
                results.append(evaluate_cohort_projection(model, scenario, cohort, catalog=catalog))
    return results


# ---------------------------------------------------------------------------
# 2. Email & Support Hosting Engine Variations + Envelope Failover Simulator
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class EmailStackCostPoint:
    """Cost and quota eligibility of one email stack at one monthly volume."""

    stack_id: str
    stack_label: str
    monthly_emails: int
    within_plan_quota: bool
    monthly_cost_usd: float
    effective_cost_per_1k_usd: float
    hard_cap_reason: str
    supports_scoped_api_auth: bool
    supports_oauth_or_jmap: bool
    supports_mcp_bridge: bool
    supports_programmable_inbound_worker: bool
    automatic_failover_chain: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "stack_id": self.stack_id,
            "stack_label": self.stack_label,
            "monthly_emails": self.monthly_emails,
            "within_plan_quota": self.within_plan_quota,
            "monthly_cost_usd": round(self.monthly_cost_usd, 2),
            "effective_cost_per_1k_usd": round(self.effective_cost_per_1k_usd, 4),
            "hard_cap_reason": self.hard_cap_reason,
            "supports_scoped_api_auth": self.supports_scoped_api_auth,
            "supports_oauth_or_jmap": self.supports_oauth_or_jmap,
            "supports_mcp_bridge": self.supports_mcp_bridge,
            "supports_programmable_inbound_worker": self.supports_programmable_inbound_worker,
            "automatic_failover_chain": list(self.automatic_failover_chain),
        }


def evaluate_email_stack(stack_id: str, monthly_emails: int) -> EmailStackCostPoint:
    """Compute monthly cost, quota status, and protocol capabilities for an email stack."""
    if stack_id not in EMAIL_STACKS:
        raise ProformaSimulationError("invalid_email_stack", f"unknown email stack {stack_id!r}")
    if not isinstance(monthly_emails, int) or monthly_emails <= 0:
        raise ProformaSimulationError("invalid_email_volume", "monthly_emails must be a positive integer")

    if stack_id == STACK_RESEND_FREE_CF_ROUTING:
        # Resend Free: 100 emails/day hard cap (~3,000/month), $0/mo.
        within = monthly_emails <= 3_000
        cost = 0.0
        reason = "" if within else "exceeds_resend_free_100_per_day_3000_per_month_cap"
        return EmailStackCostPoint(
            stack_id=stack_id,
            stack_label="Resend Free ($0) + Cloudflare Email Routing",
            monthly_emails=monthly_emails,
            within_plan_quota=within,
            monthly_cost_usd=cost,
            effective_cost_per_1k_usd=0.0,
            hard_cap_reason=reason,
            supports_scoped_api_auth=True,
            supports_oauth_or_jmap=False,
            supports_mcp_bridge=True,
            supports_programmable_inbound_worker=False,
            automatic_failover_chain=("resend_free_api", "aws_ses_api"),
        )

    if stack_id == STACK_RESEND_PRO_CF_WORKERS_FASTMAIL:
        # Resend Pro ($20/mo includes 50,000 emails, $0.90 per 1,000 extra) + CF Email Workers ($0) + Fastmail ($5/mo).
        overage_blocks = max(0, math.ceil((monthly_emails - 50_000) / 1_000))
        cost = 20.0 + 5.0 + overage_blocks * 0.90
        return EmailStackCostPoint(
            stack_id=stack_id,
            stack_label="Resend Pro ($20) + Cloudflare Email Workers + Fastmail JMAP ($5)",
            monthly_emails=monthly_emails,
            within_plan_quota=True,
            monthly_cost_usd=cost,
            effective_cost_per_1k_usd=(cost / monthly_emails) * 1_000.0,
            hard_cap_reason="",
            supports_scoped_api_auth=True,
            supports_oauth_or_jmap=True,
            supports_mcp_bridge=True,
            supports_programmable_inbound_worker=True,
            automatic_failover_chain=("resend_pro_api", "aws_ses_api", "fastmail_jmap_submission"),
        )

    if stack_id == STACK_AWS_SES_CF_WORKERS:
        # AWS SES ($0.10 per 1,000 outbound + $0.02 inbound worker storage allowance) + CF Email Workers ($0).
        cost = (monthly_emails / 1_000.0) * 0.10
        return EmailStackCostPoint(
            stack_id=stack_id,
            stack_label="AWS SES ($0.10/1k) + Cloudflare Email Workers",
            monthly_emails=monthly_emails,
            within_plan_quota=True,
            monthly_cost_usd=cost,
            effective_cost_per_1k_usd=0.10,
            hard_cap_reason="",
            supports_scoped_api_auth=True,
            supports_oauth_or_jmap=False,
            supports_mcp_bridge=True,
            supports_programmable_inbound_worker=True,
            automatic_failover_chain=("aws_ses_api", "resend_pro_api"),
        )

    # STACK_POSTMARK_FASTMAIL: Postmark ($15/mo for 10,000 emails, $1.80 per 1,000 extra) + Fastmail JMAP ($5/mo).
    overage_blocks = max(0, math.ceil((monthly_emails - 10_000) / 1_000))
    cost = 15.0 + 5.0 + overage_blocks * 1.80
    return EmailStackCostPoint(
        stack_id=stack_id,
        stack_label="Postmark ($15/10k) + Fastmail JMAP ($5)",
        monthly_emails=monthly_emails,
        within_plan_quota=True,
        monthly_cost_usd=cost,
        effective_cost_per_1k_usd=(cost / monthly_emails) * 1_000.0,
        hard_cap_reason="",
        supports_scoped_api_auth=True,
        supports_oauth_or_jmap=True,
        supports_mcp_bridge=True,
        supports_programmable_inbound_worker=False,
        automatic_failover_chain=("postmark_api", "fastmail_jmap_submission", "aws_ses_api"),
    )


def simulate_email_stack_matrix() -> list[EmailStackCostPoint]:
    """Compare all four email stacks across 100, 1,000, 10,000, and 100,000 monthly emails."""
    return [
        evaluate_email_stack(stack_id, volume)
        for stack_id in EMAIL_STACKS
        for volume in EMAIL_VOLUMES
    ]


EMAIL_COMPONENT_ID = "transactional_and_support_email"
EMAIL_CONTRACT_VERSION = "email_send_request/v1"
EMAIL_RECOVERY_POLICY = EnvelopeRecoveryPolicy(
    EMAIL_COMPONENT_ID,
    2,
    ("quota_exceeded", "provider_unavailable"),
)

EMAIL_REFUSAL_GUIDANCE = MappingProxyType({
    "invalid_recipient": (
        "The recipient address is malformed or empty, so no message was queued or sent.",
        "Supply a valid recipient address with a local part and domain, then send the request again.",
        RETRY_AFTER_FIX,
        CALLER,
        EFFECT_NONE,
        False,
        None,
    ),
    "quota_exceeded": (
        "The primary email provider reached its daily or monthly send ceiling before writing the message.",
        "Wait for the quota window or route the request to the configured fallback email engine.",
        RETRY_NOW_SAME_IDENTITY,
        OPERATOR,
        EFFECT_NONE,
        True,
        None,
    ),
    "provider_unavailable": (
        "The selected email provider refused the connection before any message payload was accepted.",
        "Wait five seconds or allow the envelope to fail over to the next declared email provider.",
        RETRY_AFTER_WAIT,
        OPERATOR,
        EFFECT_NONE,
        True,
        5,
    ),
    "delivery_outcome_unknown": (
        "The connection dropped after the message payload was sent, so the provider may already have queued it.",
        "Query the provider message log for this request identity and reconcile before sending again.",
        RECONCILE_BEFORE_RETRY,
        OPERATOR,
        EFFECT_UNKNOWN,
        False,
        None,
    ),
})


def build_email_refusal(code: str) -> EnvelopeRefusal:
    """Build an envelope_refusal/v1 record for an email dispatch refusal code."""
    msg, next_act, retry_rule, actor, eff_commit, auto_retry, wait_s = EMAIL_REFUSAL_GUIDANCE[code]
    return envelope_refusal(
        code,
        msg,
        next_act,
        retry=retry_rule,
        effect_commitment=eff_commit,
        next_action_by=actor,
        retry_after_seconds=wait_s,
        automatic_retry=auto_retry,
    )


def simulate_email_failover_dispatch(
    *,
    request_id: str,
    recipient: str,
    provider_chain: tuple[str, ...],
    injected_failures: Mapping[str, str] | None = None,
    existing_journal: tuple = (),
    reconcile_to_state: str | None = None,
) -> dict:
    """Dispatch an email through an ordered provider failover chain wrapped in the six envelope layers.

    Enforces:
    1. Carrier + preflight check on recipient format before any provider call.
    2. Handshake negotiation for each provider (`external_effect`, `network_egress`).
    3. Tracking journal (`journal_intent`, `journal_outcome`, `journal_reconciliation`).
    4. Safe automatic failover ONLY when the failed provider wrote nothing (`EFFECT_NONE`);
       if a provider fails with `dropped_after_write` (`EFFECT_UNKNOWN`), failover halts
       immediately with `RECONCILE_BEFORE_RETRY` so a customer never receives duplicate emails.
    """
    failures = dict(injected_failures or {})
    allowance = RecoveryAllowance(2)
    req_digest = request_identity_digest(request_id)
    journal = list(existing_journal)

    if reconcile_to_state is not None:
        rec_entry = journal_reconciliation(
            journal,
            component=EMAIL_COMPONENT_ID,
            request_identity=req_digest,
            observed_effect_state=reconcile_to_state,
            result_digest=req_digest if reconcile_to_state == EFFECT_STATE_CONFIRMED else "",
            at="2026-10-16T22:00:05Z",
        )
        journal.append(rec_entry)

    # Carrier check: non-empty provider chain
    if not provider_chain:
        refusal = build_email_refusal("provider_unavailable")
        trace = EnvelopeTrace(
            EMAIL_COMPONENT_ID,
            ((LAYER_CARRIER, LAYER_REFUSED),),
            False,
            LAYER_CARRIER,
            refusal,
        )
        return {
            "record_type": EMAIL_FAILOVER_OUTCOME_VERSION,
            "delivered": False,
            "selected_provider": "",
            "attempts": [],
            "refusal": refusal.to_dict(),
            "trace": trace.to_dict(),
            "journal": [e.to_dict() for e in journal],
        }

    # Tracking check before dispatch
    track_decision = journal_decision(journal, req_digest)
    if track_decision.decision != DISPATCH:
        refusal = build_email_refusal("delivery_outcome_unknown")
        trace = EnvelopeTrace(
            EMAIL_COMPONENT_ID,
            (
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_REFUSED),
            ),
            False,
            LAYER_TRACKING,
            refusal,
        )
        return {
            "record_type": EMAIL_FAILOVER_OUTCOME_VERSION,
            "delivered": False,
            "selected_provider": "",
            "attempts": [],
            "journal_decision": track_decision.to_dict(),
            "refusal": refusal.to_dict(),
            "trace": trace.to_dict(),
            "journal": [e.to_dict() for e in journal],
        }

    # Preflight check on recipient address
    def _check_recipient(ctx: Mapping) -> EnvelopeRefusal | None:
        addr = ctx.get("recipient", "")
        if not isinstance(addr, str) or "@" not in addr or addr.startswith("@") or addr.endswith("@"):
            return build_email_refusal("invalid_recipient")
        return None

    preflight_report = run_preflight(
        EMAIL_COMPONENT_ID,
        (EnvelopePreflightCheck("recipient_address_valid", ("invalid_recipient",), _check_recipient),),
        context={"recipient": recipient},
    )
    if not preflight_report.ready:
        trace = EnvelopeTrace(
            EMAIL_COMPONENT_ID,
            (
                (LAYER_CARRIER, LAYER_ACCEPTED),
                (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                (LAYER_ACCOUNT, LAYER_ACCEPTED),
                (LAYER_TRACKING, LAYER_ACCEPTED),
                (LAYER_PREFLIGHT, LAYER_REFUSED),
            ),
            False,
            LAYER_PREFLIGHT,
            preflight_report.refusal,
        )
        return {
            "record_type": EMAIL_FAILOVER_OUTCOME_VERSION,
            "delivered": False,
            "selected_provider": "",
            "attempts": [],
            "preflight": preflight_report.to_dict(),
            "refusal": preflight_report.refusal.to_dict() if preflight_report.refusal else None,
            "trace": trace.to_dict(),
            "journal": [e.to_dict() for e in journal],
        }

    attempts_log = []
    handshakes = []
    last_refusal: EnvelopeRefusal | None = None

    for idx, provider in enumerate(provider_chain):
        hs_req = EnvelopeHandshakeRequest(
            EMAIL_COMPONENT_ID,
            (EMAIL_CONTRACT_VERSION,),
            ("transactional_send",),
            ("inbound_webhook",),
            ("external_effect",),
        )
        hs_decl = EnvelopeHandshakeDeclaration(
            provider,
            (EMAIL_CONTRACT_VERSION,),
            ("transactional_send", "inbound_webhook"),
            ("external_effect",),
        )
        verdict = negotiate_handshake(hs_req, hs_decl)
        handshakes.append(verdict.to_dict())

        intent = journal_intent(
            journal,
            component=EMAIL_COMPONENT_ID,
            request_identity=req_digest,
            repeatable=False,
            at=f"2026-10-16T22:00:1{idx}Z",
        )
        journal.append(intent)

        mode = failures.get(provider, FAILURE_NONE)
        if mode not in SIMULATED_FAILURES:
            raise ProformaSimulationError("invalid_failure_mode", f"unknown failure mode {mode!r}")

        if mode == FAILURE_NONE:
            result_hash = request_identity_digest({"request_id": request_id, "provider": provider})
            committed = journal_outcome(
                journal,
                component=EMAIL_COMPONENT_ID,
                request_identity=req_digest,
                request_outcome=REQUEST_ANSWERED,
                task_outcome=TASK_COMPLETED,
                effect_state=EFFECT_STATE_CONFIRMED,
                result_digest=result_hash,
                at=f"2026-10-16T22:00:2{idx}Z",
            )
            journal.append(committed)
            attempts_log.append({"provider": provider, "outcome": "delivered", "effect_state": EFFECT_STATE_CONFIRMED})
            trace = EnvelopeTrace(
                EMAIL_COMPONENT_ID,
                (
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, LAYER_ACCEPTED),
                    (LAYER_TRACKING, LAYER_ACCEPTED),
                    (LAYER_PREFLIGHT, LAYER_ACCEPTED),
                ),
                True,
                "",
                None,
            )
            return {
                "record_type": EMAIL_FAILOVER_OUTCOME_VERSION,
                "delivered": True,
                "selected_provider": provider,
                "attempts": attempts_log,
                "handshake": handshakes,
                "preflight": preflight_report.to_dict(),
                "refusal": None,
                "trace": trace.to_dict(),
                "journal": [e.to_dict() for e in journal],
            }

        if mode == FAILURE_DROPPED_AFTER_WRITE:
            # Uncertain effect! Record EFFECT_STATE_UNKNOWN and block automatic retry/failover.
            committed = journal_outcome(
                journal,
                component=EMAIL_COMPONENT_ID,
                request_identity=req_digest,
                request_outcome=REFUSAL_OUTCOME,
                task_outcome=TASK_FAILED,
                effect_state=EFFECT_STATE_UNKNOWN,
                result_digest="",
                at=f"2026-10-16T22:00:2{idx}Z",
            )
            journal.append(committed)
            last_refusal = build_email_refusal("delivery_outcome_unknown")
            can_recover = may_recover(EMAIL_RECOVERY_POLICY, last_refusal, allowance)
            attempts_log.append({
                "provider": provider,
                "outcome": "halted_for_reconciliation",
                "effect_state": EFFECT_STATE_UNKNOWN,
                "may_recover": can_recover,
            })
            break

        # Pre-effect refusal (quota_exceeded or provider_unavailable)
        refusal_code = "quota_exceeded" if mode == FAILURE_QUOTA_EXCEEDED else "provider_unavailable"
        committed = journal_outcome(
            journal,
            component=EMAIL_COMPONENT_ID,
            request_identity=req_digest,
            request_outcome=REFUSAL_OUTCOME,
            task_outcome=TASK_FAILED,
            effect_state=EFFECT_STATE_NONE,
            result_digest="",
            at=f"2026-10-16T22:00:2{idx}Z",
        )
        journal.append(committed)
        last_refusal = build_email_refusal(refusal_code)
        has_next = idx + 1 < len(provider_chain)
        can_recover = has_next and may_recover(EMAIL_RECOVERY_POLICY, last_refusal, allowance)
        attempts_log.append({
            "provider": provider,
            "outcome": "failed_over" if can_recover else "refused",
            "effect_state": EFFECT_STATE_NONE,
            "refusal_code": refusal_code,
            "may_recover": can_recover,
        })
        if not can_recover:
            break

    assert last_refusal is not None
    trace = EnvelopeTrace(
        EMAIL_COMPONENT_ID,
        (
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_ACCEPTED),
            (LAYER_TRACKING, LAYER_ACCEPTED),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        ),
        True,
        ENGINE_SOURCE,
        last_refusal,
    )
    return {
        "record_type": EMAIL_FAILOVER_OUTCOME_VERSION,
        "delivered": False,
        "selected_provider": "",
        "attempts": attempts_log,
        "handshake": handshakes,
        "preflight": preflight_report.to_dict(),
        "refusal": last_refusal.to_dict(),
        "trace": trace.to_dict(),
        "journal": [e.to_dict() for e in journal],
    }


# ---------------------------------------------------------------------------
# 3. Hosting & Catalogue Serving Variations (1.90M, 5M, 10M distinct files)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class HostingScalePoint:
    """Cost, storage footprint, and latency profile of a catalogue serving architecture."""

    architecture_id: str
    architecture_label: str
    distinct_files: int
    raw_catalogue_gb: float
    deduplicated_storage_gb: float
    fly_compute_and_volume_usd: float
    cloudflare_r2_and_workers_usd: float
    total_monthly_cost_usd: float
    within_50_usd_allowance: bool
    p50_read_latency_ms: float
    p95_read_latency_ms: float
    origin_disk_pressure: str
    deploy_resync_seconds: float

    def to_dict(self) -> dict:
        return {
            "architecture_id": self.architecture_id,
            "architecture_label": self.architecture_label,
            "distinct_files": self.distinct_files,
            "raw_catalogue_gb": round(self.raw_catalogue_gb, 2),
            "deduplicated_storage_gb": round(self.deduplicated_storage_gb, 2),
            "fly_compute_and_volume_usd": round(self.fly_compute_and_volume_usd, 2),
            "cloudflare_r2_and_workers_usd": round(self.cloudflare_r2_and_workers_usd, 2),
            "total_monthly_cost_usd": round(self.total_monthly_cost_usd, 2),
            "within_50_usd_allowance": self.within_50_usd_allowance,
            "p50_read_latency_ms": round(self.p50_read_latency_ms, 1),
            "p95_read_latency_ms": round(self.p95_read_latency_ms, 1),
            "origin_disk_pressure": self.origin_disk_pressure,
            "deploy_resync_seconds": round(self.deploy_resync_seconds, 1),
        }


def evaluate_hosting_scale(architecture_id: str, distinct_files: int) -> HostingScalePoint:
    """Model storage, monthly cost, latency, and deploy resync time for a file count."""
    if architecture_id not in HOSTING_ARCHITECTURES:
        raise ProformaSimulationError(
            "invalid_hosting_architecture",
            f"unknown architecture_id {architecture_id!r}",
        )
    if not isinstance(distinct_files, int) or distinct_files <= 0:
        raise ProformaSimulationError("invalid_file_count", "distinct_files must be a positive integer")

    # Average canonical component file + metadata index footprint: ~14.5 KB raw, ~9.2 KB content-addressed compressed.
    raw_gb = (distinct_files * 14_500) / 1e9
    dedup_gb = (distinct_files * 9_200) / 1e9
    scale_factor = distinct_files / 1_900_000.0

    if architecture_id == ARCH_FLY_VOLUME_ORIGIN:
        # Fly NVMe volume ($0.15/GB-month with 2x headroom for atomic SQLite/release swap) + RAM scaling.
        provisioned_nvme_gb = math.ceil(raw_gb * 2.2)
        fly_machine_usd = 15.40 if distinct_files <= 2_000_000 else (31.00 if distinct_files <= 5_000_000 else 62.00)
        fly_volume_usd = provisioned_nvme_gb * 0.15
        fly_egress_usd = 4.50 * scale_factor
        fly_total = fly_machine_usd + fly_volume_usd + fly_egress_usd
        cf_total = 0.0
        total = fly_total
        return HostingScalePoint(
            architecture_id=architecture_id,
            architecture_label="Fly.io Origin Machine + Attached NVMe Volume (Direct Origin Serving)",
            distinct_files=distinct_files,
            raw_catalogue_gb=raw_gb,
            deduplicated_storage_gb=dedup_gb,
            fly_compute_and_volume_usd=fly_total,
            cloudflare_r2_and_workers_usd=cf_total,
            total_monthly_cost_usd=total,
            within_50_usd_allowance=total <= INFRASTRUCTURE_MONTHLY_ALLOWANCE_USD,
            p50_read_latency_ms=42.0 + 6.0 * scale_factor,
            p95_read_latency_ms=135.0 + 28.0 * scale_factor,
            origin_disk_pressure="high" if distinct_files >= 5_000_000 else "moderate",
            deploy_resync_seconds=95.0 * scale_factor,
        )

    if architecture_id == ARCH_FLY_ORIGIN_R2_EDGE_EXPORT:
        # Fly control plane holds compact SQLite metadata index + auth/billing; R2 holds content-addressed bodies.
        index_nvme_gb = math.ceil(dedup_gb * 0.28) + 10
        fly_machine_usd = 15.40 if distinct_files <= 5_000_000 else 31.00
        fly_total = fly_machine_usd + index_nvme_gb * 0.15
        # Cloudflare R2: first 10 GB free, then $0.015/GB-month, $0 egress, plus Class A/B ops.
        billable_r2_gb = max(0.0, dedup_gb - 10.0)
        r2_storage_usd = billable_r2_gb * 0.015
        r2_ops_usd = 1.80 * scale_factor
        cf_total = 5.00 + r2_storage_usd + r2_ops_usd
        total = fly_total + cf_total
        return HostingScalePoint(
            architecture_id=architecture_id,
            architecture_label="Fly.io Control Plane + Cloudflare R2 Blobs + Edge Static Export",
            distinct_files=distinct_files,
            raw_catalogue_gb=raw_gb,
            deduplicated_storage_gb=dedup_gb,
            fly_compute_and_volume_usd=fly_total,
            cloudflare_r2_and_workers_usd=cf_total,
            total_monthly_cost_usd=total,
            within_50_usd_allowance=total <= INFRASTRUCTURE_MONTHLY_ALLOWANCE_USD,
            p50_read_latency_ms=18.0,
            p95_read_latency_ms=54.0 + 4.0 * scale_factor,
            origin_disk_pressure="low",
            deploy_resync_seconds=28.0 + 8.0 * scale_factor,
        )

    # ARCH_WORKER_FIRST_R2_D1_CACHE: Worker-first caching + R2 content-addressed bodies + minimal Fly auth/billing origin.
    fly_total = 15.40 + 10 * 0.15
    billable_r2_gb = max(0.0, dedup_gb - 10.0)
    r2_storage_usd = billable_r2_gb * 0.015
    worker_and_kv_ops_usd = 5.00 + 2.40 * scale_factor
    cf_total = r2_storage_usd + worker_and_kv_ops_usd
    total = fly_total + cf_total
    return HostingScalePoint(
        architecture_id=architecture_id,
        architecture_label="Cloudflare Worker-First Edge Cache + R2 Content-Addressed Store + Fly Auth Origin",
        distinct_files=distinct_files,
        raw_catalogue_gb=raw_gb,
        deduplicated_storage_gb=dedup_gb,
        fly_compute_and_volume_usd=fly_total,
        cloudflare_r2_and_workers_usd=cf_total,
        total_monthly_cost_usd=total,
        within_50_usd_allowance=total <= INFRASTRUCTURE_MONTHLY_ALLOWANCE_USD,
        p50_read_latency_ms=11.0,
        p95_read_latency_ms=34.0,
        origin_disk_pressure="minimal",
        deploy_resync_seconds=12.0 + 2.5 * scale_factor,
    )


def simulate_hosting_matrix() -> list[HostingScalePoint]:
    """Compare all three hosting architectures across 1.90M, 5M, and 10M distinct files."""
    return [
        evaluate_hosting_scale(arch_id, count)
        for arch_id in HOSTING_ARCHITECTURES
        for count in CATALOGUE_FILE_COUNTS
    ]


def build_full_proforma_report() -> dict:
    """Generate the complete deterministic pro-forma, email stack, and hosting comparison report."""
    pricing_rows = [row.to_dict() for row in simulate_pricing_matrix()]
    email_rows = [row.to_dict() for row in simulate_email_stack_matrix()]
    hosting_rows = [row.to_dict() for row in simulate_hosting_matrix()]

    # Representative failover traces
    failover_quota_demo = simulate_email_failover_dispatch(
        request_id="req-email-quota-001",
        recipient="founder@baltor.ai",
        provider_chain=("resend_free_api", "aws_ses_api"),
        injected_failures={"resend_free_api": FAILURE_QUOTA_EXCEEDED},
    )
    failover_uncertain_demo = simulate_email_failover_dispatch(
        request_id="req-email-uncertain-002",
        recipient="founder@baltor.ai",
        provider_chain=("resend_pro_api", "aws_ses_api"),
        injected_failures={"resend_pro_api": FAILURE_DROPPED_AFTER_WRITE},
    )

    return {
        "record_type": SIMULATOR_RECORD_VERSION,
        "pricing_projections": pricing_rows,
        "email_stack_comparisons": email_rows,
        "email_failover_demonstrations": {
            "pre_effect_quota_failover": failover_quota_demo,
            "uncertain_effect_reconciliation_halt": failover_uncertain_demo,
        },
        "hosting_scale_comparisons": hosting_rows,
    }


def self_test() -> dict:
    """Run deterministic self-checks and known-wrong controls for the pro-forma simulator."""
    report = build_full_proforma_report()
    assert len(report["pricing_projections"]) == len(PRICING_MODELS) * len(GROWTH_SCENARIOS) * len(HORIZONS)
    assert len(report["email_stack_comparisons"]) == len(EMAIL_STACKS) * len(EMAIL_VOLUMES)
    assert len(report["hosting_scale_comparisons"]) == len(HOSTING_ARCHITECTURES) * len(CATALOGUE_FILE_COUNTS)

    # Known-wrong control 1: charging Basic during free window is refused.
    rejected_free_window = False
    try:
        HorizonCohortMix(
            horizon=HORIZON_MONTH_1,
            in_basic_free_window=True,
            founding_free_pro_accounts=10,
            public_good_free_accounts=10,
            basic_free_preview_accounts=50,
            basic_paid_opt_in_accounts=5,
            pro_monthly_accounts=10,
            pro_annual_accounts=1,
            max_monthly_accounts=0,
            team_monthly_accounts=0,
            agentbriefs_standard_accounts=0,
            agentbriefs_enterprise_accounts=0,
            playground_sponsors=0,
        )
    except ProformaSimulationError as exc:
        rejected_free_window = exc.code == "basic_charged_during_free_window"
    assert rejected_free_window

    # Known-wrong control 2: Founding free Pro accounts exceeding 10 is refused.
    rejected_founding_cap = False
    try:
        HorizonCohortMix(
            horizon=HORIZON_DAYS_1_TO_7,
            in_basic_free_window=True,
            founding_free_pro_accounts=11,
            public_good_free_accounts=5,
            basic_free_preview_accounts=10,
            basic_paid_opt_in_accounts=0,
            pro_monthly_accounts=2,
            pro_annual_accounts=0,
            max_monthly_accounts=0,
            team_monthly_accounts=0,
            agentbriefs_standard_accounts=0,
            agentbriefs_enterprise_accounts=0,
            playground_sponsors=0,
        )
    except ProformaSimulationError as exc:
        rejected_founding_cap = exc.code == "founding_cap_exceeded"
    assert rejected_founding_cap

    # Known-wrong control 3: uncertain email delivery effect halts automatic failover.
    uncertain = report["email_failover_demonstrations"]["uncertain_effect_reconciliation_halt"]
    assert uncertain["delivered"] is False
    assert uncertain["refusal"]["retry"] == RECONCILE_BEFORE_RETRY
    assert len(uncertain["attempts"]) == 1

    return {"passed": True, "checks_run": 6}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true", help="Run built-in simulator checks and controls")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args(argv)
    if args.self_test:
        result = self_test()
        print(json.dumps(result, sort_keys=True))
        return 0
    report = build_full_proforma_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"Pro-forma simulator ready: {len(report['pricing_projections'])} pricing rows, "
            f"{len(report['email_stack_comparisons'])} email rows, "
            f"{len(report['hosting_scale_comparisons'])} hosting rows."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
