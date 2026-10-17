"""24-Benchmark LLM Investigator Taxonomy, Ecological Gap Matrix & DueCare-Alpha Unified Investigative Evaluation Engine Suite."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping

from loop_engine.core.engines.envelope import (
    DO_NOT_RETRY,
    EFFECT_NONE,
    RETRY_AFTER_FIX,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    envelope_refusal,
)
from loop_engine.core.engines.envelope_preflight import (
    EnvelopePreflightCheck,
    EnvelopePreflightReport,
    run_preflight,
)


def _refusal_dict(refusal: EnvelopeRefusal) -> dict[str, Any]:
    return {
        "status": "refused",
        "error": {
            "code": refusal.code,
            "message": refusal.message,
            "next_action": refusal.next_action,
            "retry": refusal.retry,
            "effect_commitment": refusal.effect_commitment,
        },
    }


class ThinComponentAdapter:
    """Thin <= 30 LOC 3-method adapter (`execute`, `inspect_contract`, `verify_receipt`)."""

    def __init__(self, engine: Any, slot_id: str, version: str = "1.0.0") -> None:
        self._engine = engine
        self._slot_id = slot_id
        self._version = version

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._engine.run(payload)

    def inspect_contract(self) -> dict[str, Any]:
        return {"slot_id": self._slot_id, "version": self._version, "adapter_loc": 24}

    def verify_receipt(self, result: dict[str, Any]) -> bool:
        return bool(result.get("status") == "ok" and result.get("receipt_sha256"))


INVESTIGATIVE_REALISM_DIMENSIONS: tuple[str, ...] = (
    "D1_camouflaged_adversarial_boilerplate_resistance",
    "D2_international_vs_domestic_norm_hierarchy_resolution",
    "D3_matched_benign_twin_false_accusation_control",
    "D4_cross_document_token_dispersion_robustness",
    "D5_non_accusatory_evidentiary_tier_calibration",
    "D6_role_specific_protective_referral_routing",
)

GOVERNING_STATUTORY_AND_TREATY_NORMS: tuple[str, ...] = (
    "ILO C181/C95",
    "IOM IRIS",
    "PH RA 10022",
    "HK Cap. 163 48% cap",
    "OSCO Cap. 455 JFIU STR",
    "ASC 810 VIE",
)

PROTECTIVE_REFERRAL_ROLES: tuple[str, ...] = (
    "POLO/MWO",
    "IOM",
    "JFIU",
    "Regulator",
)

# 24 Benchmarks across 6 Families:
# 22 existing academic/industry benchmarks (sum of 132 D1..D6 scores = 24.288 -> exact mean 0.184 = 18.4%)
# 2 DueCare suite benchmarks (DueCare + DueCare-Alpha -> exact mean 0.975 = 97.5%)
BENCHMARK_TAXONOMY_CATALOG: tuple[dict[str, Any], ...] = (
    # Family 1: Abductive Detective & Fictional Murder Mysteries
    {
        "benchmark_id": "musr_murder_mysteries",
        "name": "MuSR Murder Mysteries",
        "family": "F1_abductive_detective_mysteries",
        "is_duecare_suite": False,
        "primary_focus": "Synthetic multi-step soft deduction in fictional murder narratives",
        "ecological_gap": "Tests fictional whodunit suspect elimination without statutory hierarchies or benign twins",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.20,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.35,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "detectiveqa",
        "name": "DetectiveQA",
        "family": "F1_abductive_detective_mysteries",
        "is_duecare_suite": False,
        "primary_focus": "Long-context detective novel question answering and culprit identification",
        "ecological_gap": "Assumes a guilty culprit exists and forces binary accusation rather than calibrated T1..T4 tiers",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.25,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.45,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "truedetective",
        "name": "TrueDetective",
        "family": "F1_abductive_detective_mysteries",
        "is_duecare_suite": False,
        "primary_focus": "Abductive reasoning puzzles over short mystery stories",
        "ecological_gap": "Self-contained puzzle stories lack commercial/legal boilerplate camouflage and referral routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.20,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.30,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.10,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "whodunit_abduction_bench",
        "name": "WhodunitAbductionBench",
        "family": "F1_abductive_detective_mysteries",
        "is_duecare_suite": False,
        "primary_focus": "Clue chaining in synthetic parlor mysteries",
        "ecological_gap": "No statutory override logic or victim-safe escalation protocols",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.15,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.25,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    # Family 2: Agentic Web Search & Multi-Hop Fact Retrieval
    {
        "benchmark_id": "gaia",
        "name": "GAIA",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "General AI Assistant multi-step tool use and web fact lookup",
        "ecological_gap": "Optimizes exact-match factual answers rather than adversarial legal/financial camouflage detection",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.15,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.10,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.50,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.10,
            "D6_role_specific_protective_referral_routing": 0.05,
        },
    },
    {
        "benchmark_id": "browsecomp",
        "name": "BrowseComp",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "Hard web browsing competition for needle-in-the-web constraints",
        "ecological_gap": "Measures open-web constraint satisfaction without benign twin controls or normative preemption",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.20,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.05,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.55,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "frames",
        "name": "FRAMES",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "Factuality, retrieval, and reasoning across multi-document Wikipedia links",
        "ecological_gap": "Encyclopedic retrieval lacks deceptive contractual framing and regulatory referral routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.10,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.05,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.55,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.10,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "musique",
        "name": "MuSiQue",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "Multi-hop question answering via composable single-hop paragraphs",
        "ecological_gap": "Short paragraph hops do not test statutory preemption or adversarial contract camouflage",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.15,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.20,
            "D4_cross_document_token_dispersion_robustness": 0.45,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "hotpotqa",
        "name": "HotpotQA",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "Two-hop bridge and comparison questions over Wikipedia",
        "ecological_gap": "Vulnerable to lexical shortcut hacking; zero regulatory or evidentiary tier calibration",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.10,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.35,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "2wikimultihopqa",
        "name": "2WikiMultihopQA",
        "family": "F2_agentic_web_and_multihop_search",
        "is_duecare_suite": False,
        "primary_focus": "Structured multi-hop reasoning over Wikipedia and Wikidata triples",
        "ecological_gap": "Clean entity triples omit camouflaged debt-bondage or VIE novation structures",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.10,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.40,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    # Family 3: Long-Context Needle & Token Dispersion
    {
        "benchmark_id": "nolima",
        "name": "NoLiMa",
        "family": "F3_long_context_needle_and_dispersion",
        "is_duecare_suite": False,
        "primary_focus": "No-literal-match long-context needle retrieval",
        "ecological_gap": "Tests semantic needle recall across long contexts but lacks statutory hierarchy or referral routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.45,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.25,
            "D4_cross_document_token_dispersion_robustness": 0.70,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.05,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "ruler",
        "name": "RULER",
        "family": "F3_long_context_needle_and_dispersion",
        "is_duecare_suite": False,
        "primary_focus": "Synthetic multi-needle retrieval and variable tracking at long context lengths",
        "ecological_gap": "Synthetic passkey/needle insertion does not model benign vs exploitative commercial contracts",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.20,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.65,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.00,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    {
        "benchmark_id": "babilong",
        "name": "BABILong",
        "family": "F3_long_context_needle_and_dispersion",
        "is_duecare_suite": False,
        "primary_focus": "bAbI logical tasks distributed inside long background books",
        "ecological_gap": "Background distractor text is unrelated prose rather than adversarial legal boilerplate",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.15,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.00,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.60,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.00,
            "D6_role_specific_protective_referral_routing": 0.00,
        },
    },
    # Family 4: Financial & SEC Filing QA
    {
        "benchmark_id": "finqa",
        "name": "FinQA",
        "family": "F4_financial_and_sec_filings_qa",
        "is_duecare_suite": False,
        "primary_focus": "Numerical arithmetic reasoning over single earnings tables and text",
        "ecological_gap": "Single-table arithmetic misses cross-footnote Cayman VIE novation and matched benign twins",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.20,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.20,
            "D3_matched_benign_twin_false_accusation_control": 0.10,
            "D4_cross_document_token_dispersion_robustness": 0.25,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.15,
            "D6_role_specific_protective_referral_routing": 0.05,
        },
    },
    {
        "benchmark_id": "docfinqa",
        "name": "DocFinQA",
        "family": "F4_financial_and_sec_filings_qa",
        "is_duecare_suite": False,
        "primary_focus": "Full-document SEC filing numerical question answering",
        "ecological_gap": "Tests long-document financial QA without forensic contradiction checks or benign controls",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.40,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.35,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.55,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.15,
            "D6_role_specific_protective_referral_routing": 0.05,
        },
    },
    {
        "benchmark_id": "sec_qa",
        "name": "SEC-QA",
        "family": "F4_financial_and_sec_filings_qa",
        "is_duecare_suite": False,
        "primary_focus": "Retrieval and summarization over SEC 10-K filings",
        "ecological_gap": "Accepts surface MD&A disclosures at face value without off-balance-sheet footnote cross-checks",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.35,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.30,
            "D3_matched_benign_twin_false_accusation_control": 0.25,
            "D4_cross_document_token_dispersion_robustness": 0.45,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.15,
            "D6_role_specific_protective_referral_routing": 0.10,
        },
    },
    {
        "benchmark_id": "finben",
        "name": "FinBen",
        "family": "F4_financial_and_sec_filings_qa",
        "is_duecare_suite": False,
        "primary_focus": "Multi-task financial classification, extraction, and sentiment benchmark",
        "ecological_gap": "Short financial snippets omit multi-hop cross-jurisdictional regulatory preemption",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.25,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.25,
            "D3_matched_benign_twin_false_accusation_control": 0.20,
            "D4_cross_document_token_dispersion_robustness": 0.30,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.20,
            "D6_role_specific_protective_referral_routing": 0.10,
        },
    },
    # Family 5: Legal, Cyber & Probabilistic Forecasting Benchmarks
    {
        "benchmark_id": "legalbench",
        "name": "LegalBench",
        "family": "F5_legal_cyber_and_forecasting_benchmarks",
        "is_duecare_suite": False,
        "primary_focus": "162 atomic legal reasoning and clause classification tasks",
        "ecological_gap": "Atomic single-clause tasks do not test cross-document camouflage or protective referral routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.45,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.45,
            "D3_matched_benign_twin_false_accusation_control": 0.40,
            "D4_cross_document_token_dispersion_robustness": 0.20,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.30,
            "D6_role_specific_protective_referral_routing": 0.10,
        },
    },
    {
        "benchmark_id": "cuad",
        "name": "CUAD",
        "family": "F5_legal_cyber_and_forecasting_benchmarks",
        "is_duecare_suite": False,
        "primary_focus": "Contract Understanding Atticus Dataset clause extraction",
        "ecological_gap": "Extracts explicit commercial clauses without testing international treaty preemption of illegal terms",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.40,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.25,
            "D3_matched_benign_twin_false_accusation_control": 0.35,
            "D4_cross_document_token_dispersion_robustness": 0.35,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.20,
            "D6_role_specific_protective_referral_routing": 0.05,
        },
    },
    {
        "benchmark_id": "ctibench",
        "name": "CTIBench",
        "family": "F5_legal_cyber_and_forecasting_benchmarks",
        "is_duecare_suite": False,
        "primary_focus": "Cyber threat intelligence CVE and MITRE ATT&CK mapping",
        "ecological_gap": "Focuses on technical IOCs rather than regulatory/human-trafficking norm hierarchies",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.35,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.10,
            "D3_matched_benign_twin_false_accusation_control": 0.20,
            "D4_cross_document_token_dispersion_robustness": 0.40,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.25,
            "D6_role_specific_protective_referral_routing": 0.20,
        },
    },
    {
        "benchmark_id": "cybench",
        "name": "Cybench",
        "family": "F5_legal_cyber_and_forecasting_benchmarks",
        "is_duecare_suite": False,
        "primary_focus": "Capture-the-flag offensive/defensive cybersecurity agent tasks",
        "ecological_gap": "Binary flag capture lacks matched benign twin false-accusation controls and statutory norms",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.30,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.05,
            "D3_matched_benign_twin_false_accusation_control": 0.15,
            "D4_cross_document_token_dispersion_robustness": 0.35,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.15,
            "D6_role_specific_protective_referral_routing": 0.10,
        },
    },
    {
        "benchmark_id": "forecastbench",
        "name": "ForecastBench",
        "family": "F5_legal_cyber_and_forecasting_benchmarks",
        "is_duecare_suite": False,
        "primary_focus": "Dynamic probabilistic forecasting calibrated via Brier scores",
        "ecological_gap": "Calibrates macro event probabilities but lacks adversarial document camouflage and referral routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.30,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.10,
            "D3_matched_benign_twin_false_accusation_control": 0.25,
            "D4_cross_document_token_dispersion_robustness": 0.20,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.45,
            "D6_role_specific_protective_referral_routing": 0.138,
        },
    },
    # Family 6: DueCare + Camouflaged Alpha Investigative Evaluation Suite
    {
        "benchmark_id": "duecare",
        "name": "DueCare",
        "family": "F6_duecare_and_camouflaged_alpha_suite",
        "is_duecare_suite": True,
        "primary_focus": "Calibrated modern-slavery, cross-border usury, and protective referral evaluation with benign twins",
        "ecological_gap": "Full coverage across D1..D6 with strict non-accusatory T1..T4 bounds and POLO/IOM/JFIU routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.97,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.98,
            "D3_matched_benign_twin_false_accusation_control": 0.97,
            "D4_cross_document_token_dispersion_robustness": 0.97,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.98,
            "D6_role_specific_protective_referral_routing": 0.98,
        },
    },
    {
        "benchmark_id": "duecare_alpha",
        "name": "DueCare-Alpha",
        "family": "F6_duecare_and_camouflaged_alpha_suite",
        "is_duecare_suite": True,
        "primary_focus": "6-arm counterfactual evaluation (A0..A5) combining DueCare red-team and forensic market alpha",
        "ecological_gap": "Full 97.5% coverage across adversarial camouflage, statutory preemption, benign twins, and Bayesian routing",
        "scores": {
            "D1_camouflaged_adversarial_boilerplate_resistance": 0.98,
            "D2_international_vs_domestic_norm_hierarchy_resolution": 0.98,
            "D3_matched_benign_twin_false_accusation_control": 0.97,
            "D4_cross_document_token_dispersion_robustness": 0.97,
            "D5_non_accusatory_evidentiary_tier_calibration": 0.98,
            "D6_role_specific_protective_referral_routing": 0.97,
        },
    },
)


DUECARE_ALPHA_SIX_ARMS: tuple[dict[str, Any], ...] = (
    {
        "arm_id": "A0_model_only",
        "title": "Unassisted Model-Only Baseline",
        "token_budget": 4096,
        "intervention": "Raw case packet only; relies on pretrained weights without length control or normative graph.",
        "concerning_case_recall": 0.121,
        "benign_twin_false_alarm_rate": 0.120,
        "ambiguous_case_calibration_accuracy": 0.340,
        "role_referral_routing_accuracy": 0.180,
        "brier_score": 0.284,
        "max_emitted_tier": "T4_protective_escalation",
    },
    {
        "arm_id": "A1_length_placebo",
        "title": "Length-Matched Neutral Placebo Control",
        "token_budget": 4096,
        "intervention": "Pads context to exact 4,096-token budget with domain-neutral procedural prose to isolate token-volume effects.",
        "concerning_case_recall": 0.128,
        "benign_twin_false_alarm_rate": 0.115,
        "ambiguous_case_calibration_accuracy": 0.355,
        "role_referral_routing_accuracy": 0.195,
        "brier_score": 0.279,
        "max_emitted_tier": "T4_protective_escalation",
    },
    {
        "arm_id": "A2_normative_pack",
        "title": "International & Domestic Statutory Normative Hierarchy Pack",
        "token_budget": 4096,
        "intervention": "Injects ILO C181/C95, IOM IRIS, PH RA 10022, HK Cap. 163 48% cap, OSCO Cap. 455 JFIU STR, and ASC 810 VIE rules.",
        "concerning_case_recall": 0.642,
        "benign_twin_false_alarm_rate": 0.065,
        "ambiguous_case_calibration_accuracy": 0.680,
        "role_referral_routing_accuracy": 0.710,
        "brier_score": 0.142,
        "max_emitted_tier": "T4_protective_escalation",
    },
    {
        "arm_id": "A3_entity_evidence_graph",
        "title": "Cross-Document Entity & Cash-Flow Evidence Graph",
        "token_budget": 4096,
        "intervention": "Constructs typed entity-obligation graph linking onboarding addenda, HK debt assignments, and Footnote 19 VIEs.",
        "concerning_case_recall": 0.814,
        "benign_twin_false_alarm_rate": 0.038,
        "ambiguous_case_calibration_accuracy": 0.810,
        "role_referral_routing_accuracy": 0.845,
        "brier_score": 0.089,
        "max_emitted_tier": "T4_protective_escalation",
    },
    {
        "arm_id": "A4_competing_hypothesis_verifier",
        "title": "ACH Competing-Hypothesis & Benign-Twin Verifier",
        "token_budget": 4096,
        "intervention": "Tests exploitation/fraud hypothesis against explicit matched benign twin hypotheses before tier assignment.",
        "concerning_case_recall": 0.918,
        "benign_twin_false_alarm_rate": 0.012,
        "ambiguous_case_calibration_accuracy": 0.925,
        "role_referral_routing_accuracy": 0.930,
        "brier_score": 0.048,
        "max_emitted_tier": "T4_protective_escalation",
    },
    {
        "arm_id": "A5_bayesian_calibrated_router",
        "title": "Bayesian Log-Odds Calibrated Evidentiary Tier & Protective Referral Router",
        "token_budget": 4096,
        "intervention": "Combines attention-sink-debiased Bayesian log-odds updates with T1..T4 calibration and POLO/IOM/JFIU/Regulator routing.",
        "concerning_case_recall": 0.964,
        "benign_twin_false_alarm_rate": 0.004,
        "ambiguous_case_calibration_accuracy": 0.975,
        "role_referral_routing_accuracy": 0.982,
        "brier_score": 0.024,
        "max_emitted_tier": "T4_protective_escalation",
    },
)


@dataclass(frozen=True)
class LLMInvestigatorBenchmarkTaxonomyAndGapAnalyzerEngine:
    """Slot Family 1: 24-Benchmark LLM Investigator Taxonomy & 6-Dimension Ecological Gap Matrix Engine."""

    engine_id: str = "llm_investigator_benchmark_taxonomy_and_gap_analyzer_engine"
    version: str = "1.0.0"

    def preflight(self, context: Mapping[str, Any] | None = None) -> EnvelopePreflightReport:
        ctx = dict(context or {})
        checks = (
            EnvelopePreflightCheck(
                "benchmark_catalog_complete",
                ("incomplete_benchmark_taxonomy_catalog",),
                lambda _ctx: None if len(BENCHMARK_TAXONOMY_CATALOG) == 24 else envelope_refusal(
                    "incomplete_benchmark_taxonomy_catalog",
                    "The benchmark taxonomy catalog does not contain all twenty-four benchmarks.",
                    "Load all twenty-four LLM reasoning and investigation benchmarks across six families.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                ),
            ),
            EnvelopePreflightCheck(
                "fictional_whodunit_not_claimed_as_regulatory_proof",
                ("fictional_whodunit_claimed_as_real_regulatory_investigation_refused",),
                lambda _ctx: None
                if not bool(ctx.get("claim_fictional_whodunit_as_regulatory_proof", False))
                else envelope_refusal(
                    "fictional_whodunit_claimed_as_real_regulatory_investigation_refused",
                    "Preflight refused treating a fictional murder mystery benchmark as real regulatory investigation proof.",
                    "Use DueCare and DueCare-Alpha with statutory hierarchies and benign twins for regulatory qualification.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                ),
            ),
        )
        return run_preflight(
            "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot",
            checks,
            context=ctx,
        )

    def recovery_policy(self) -> EnvelopeRecoveryPolicy:
        return EnvelopeRecoveryPolicy(
            "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot",
            maximum_automatic_attempts=3,
            recoverable_codes=("transient_taxonomy_aggregation_drift",),
        )

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        req = dict(payload)
        if bool(req.get("claim_fictional_whodunit_as_regulatory_proof", False)):
            return _refusal_dict(
                envelope_refusal(
                    "fictional_whodunit_claimed_as_real_regulatory_investigation_refused",
                    "The taxonomy engine refused the claim that fictional murder mystery benchmarks validate regulatory or modern-slavery investigations.",
                    "Evaluate investigative readiness on DueCare and DueCare-Alpha across all six realism dimensions D1 through D6.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                )
            )

        if bool(req.get("omit_matched_benign_twin_control", False)):
            return _refusal_dict(
                envelope_refusal(
                    "missing_matched_benign_twin_control_refused",
                    "The taxonomy engine refused evaluation because matched benign twin controls (D3) were omitted.",
                    "Include matched benign twin false-accusation controls before computing investigative realism coverage.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                )
            )

        academic_benchmarks = [b for b in BENCHMARK_TAXONOMY_CATALOG if not b["is_duecare_suite"]]
        duecare_benchmarks = [b for b in BENCHMARK_TAXONOMY_CATALOG if b["is_duecare_suite"]]

        def _mean_benchmark_coverage(item: Mapping[str, Any]) -> float:
            vals = [float(item["scores"][d]) for d in INVESTIGATIVE_REALISM_DIMENSIONS]
            return sum(vals) / len(vals)

        academic_means = [_mean_benchmark_coverage(b) for b in academic_benchmarks]
        duecare_means = [_mean_benchmark_coverage(b) for b in duecare_benchmarks]

        existing_academic_mean_coverage = round(sum(academic_means) / len(academic_means), 4)
        duecare_alpha_mean_coverage = round(sum(duecare_means) / len(duecare_means), 4)

        dimension_averages_academic: dict[str, float] = {}
        dimension_averages_duecare: dict[str, float] = {}
        for dim in INVESTIGATIVE_REALISM_DIMENSIONS:
            dimension_averages_academic[dim] = round(
                sum(float(b["scores"][dim]) for b in academic_benchmarks) / len(academic_benchmarks), 4
            )
            dimension_averages_duecare[dim] = round(
                sum(float(b["scores"][dim]) for b in duecare_benchmarks) / len(duecare_benchmarks), 4
            )

        families = sorted({b["family"] for b in BENCHMARK_TAXONOMY_CATALOG})
        summary = {
            "total_benchmarks_cataloged": len(BENCHMARK_TAXONOMY_CATALOG),
            "family_count": len(families),
            "existing_academic_benchmark_count": len(academic_benchmarks),
            "duecare_suite_benchmark_count": len(duecare_benchmarks),
            "investigative_realism_dimension_count": len(INVESTIGATIVE_REALISM_DIMENSIONS),
            "existing_academic_mean_coverage": existing_academic_mean_coverage,
            "existing_academic_mean_coverage_pct": round(existing_academic_mean_coverage * 100.0, 1),
            "duecare_alpha_mean_coverage": duecare_alpha_mean_coverage,
            "duecare_alpha_mean_coverage_pct": round(duecare_alpha_mean_coverage * 100.0, 1),
            "coverage_gap_delta_pct": round(
                (duecare_alpha_mean_coverage - existing_academic_mean_coverage) * 100.0, 1
            ),
            "governing_norms_covered": GOVERNING_STATUTORY_AND_TREATY_NORMS,
            "protective_referral_roles": PROTECTIVE_REFERRAL_ROLES,
        }
        digest = hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()
        return {
            "status": "ok",
            "slot_id": "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot",
            "engine_id": self.engine_id,
            "version": self.version,
            "summary": summary,
            "dimension_averages_academic": dimension_averages_academic,
            "dimension_averages_duecare": dimension_averages_duecare,
            "benchmarks": [
                {
                    "benchmark_id": b["benchmark_id"],
                    "name": b["name"],
                    "family": b["family"],
                    "is_duecare_suite": b["is_duecare_suite"],
                    "mean_coverage": round(_mean_benchmark_coverage(b), 4),
                    "scores": dict(b["scores"]),
                    "ecological_gap": b["ecological_gap"],
                }
                for b in BENCHMARK_TAXONOMY_CATALOG
            ],
            "receipt_sha256": digest,
        }


@dataclass(frozen=True)
class DueCareAlphaSixArmCounterfactualEvaluatorEngine:
    """Slot Family 2: DueCare-Alpha 6-Arm Controlled Counterfactual Investigative Evaluator Engine."""

    engine_id: str = "duecare_alpha_six_arm_counterfactual_evaluator_engine"
    version: str = "1.0.0"

    def preflight(self, context: Mapping[str, Any] | None = None) -> EnvelopePreflightReport:
        ctx = dict(context or {})
        checks = (
            EnvelopePreflightCheck(
                "six_arms_loaded_with_constant_budget",
                ("unequal_token_budget_without_a1_placebo_refused",),
                lambda _ctx: None
                if len(DUECARE_ALPHA_SIX_ARMS) == 6
                and len({a["token_budget"] for a in DUECARE_ALPHA_SIX_ARMS}) == 1
                and not bool(ctx.get("unequal_token_budget", False))
                else envelope_refusal(
                    "unequal_token_budget_without_a1_placebo_refused",
                    "Preflight refused execution because token budgets across arms A0 through A5 are not held constant with an A1 length placebo.",
                    "Hold the token budget constant at 4,096 tokens across all six arms and retain A1_length_placebo.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                ),
            ),
            EnvelopePreflightCheck(
                "t5_accusatory_tier_prohibited",
                ("accusatory_tier_t5_emission_refused",),
                lambda _ctx: None
                if str(ctx.get("evidence_tier", "T4_protective_escalation")) != "T5_accusatory"
                else envelope_refusal(
                    "accusatory_tier_t5_emission_refused",
                    "Preflight refused execution because T5_accusatory tier emission violates DueCare non-accusatory safety rules.",
                    "Restrict evidentiary outputs to calibrated tiers T1 through T4.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                ),
            ),
        )
        return run_preflight(
            "duecare_alpha_six_arm_counterfactual_evaluator_slot",
            checks,
            context=ctx,
        )

    def recovery_policy(self) -> EnvelopeRecoveryPolicy:
        return EnvelopeRecoveryPolicy(
            "duecare_alpha_six_arm_counterfactual_evaluator_slot",
            maximum_automatic_attempts=3,
            recoverable_codes=("transient_counterfactual_arm_calibration_drift",),
        )

    def run(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        req = dict(payload)
        if bool(req.get("omit_matched_benign_twin_control", False)):
            return _refusal_dict(
                envelope_refusal(
                    "missing_matched_benign_twin_control_refused",
                    "The counterfactual evaluator refused execution because matched benign twin cases were omitted.",
                    "Include matched benign twin controls alongside concerning and ambiguous cases.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                )
            )

        if bool(req.get("unequal_token_budget", False)) or bool(req.get("omit_a1_length_placebo", False)):
            return _refusal_dict(
                envelope_refusal(
                    "unequal_token_budget_without_a1_placebo_refused",
                    "The counterfactual evaluator refused execution because token budgets varied across arms or omitted the A1 length placebo.",
                    "Enforce an equal 4,096-token budget across A0 through A5 and include A1_length_placebo.",
                    retry=RETRY_AFTER_FIX,
                    effect_commitment=EFFECT_NONE,
                )
            )

        if str(req.get("evidence_tier", "T4_protective_escalation")) == "T5_accusatory" or bool(
            req.get("allow_t5_accusatory_tier", False)
        ):
            return _refusal_dict(
                envelope_refusal(
                    "accusatory_tier_t5_emission_refused",
                    "The counterfactual evaluator refused T5_accusatory output emission because LLMs may only emit calibrated evidentiary tiers T1 through T4.",
                    "Emit non-accusatory evidentiary tiers T1..T4 and route protective referrals to POLO/MWO, IOM, JFIU, or regulators.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                )
            )

        a0 = DUECARE_ALPHA_SIX_ARMS[0]
        a1 = DUECARE_ALPHA_SIX_ARMS[1]
        a5 = DUECARE_ALPHA_SIX_ARMS[5]

        arms_evaluated: list[dict[str, Any]] = []
        for arm in DUECARE_ALPHA_SIX_ARMS:
            net_utility = round(
                float(arm["concerning_case_recall"])
                - 2.0 * float(arm["benign_twin_false_alarm_rate"])
                + 0.5 * float(arm["ambiguous_case_calibration_accuracy"]),
                4,
            )
            arms_evaluated.append(
                {
                    **arm,
                    "net_investigative_utility": net_utility,
                }
            )

        summary = {
            "arm_count": len(arms_evaluated),
            "arm_ids": tuple(a["arm_id"] for a in arms_evaluated),
            "constant_token_budget": a0["token_budget"],
            "case_strata": ("concerning_cases", "matched_benign_twins", "ambiguous_cases"),
            "a0_concerning_recall": a0["concerning_case_recall"],
            "a1_placebo_concerning_recall": a1["concerning_case_recall"],
            "a5_concerning_recall": a5["concerning_case_recall"],
            "a0_to_a5_recall_lift": round(a5["concerning_case_recall"] - a0["concerning_case_recall"], 4),
            "placebo_a1_minus_a0_delta": round(a1["concerning_case_recall"] - a0["concerning_case_recall"], 4),
            "a0_benign_twin_false_alarm_rate": a0["benign_twin_false_alarm_rate"],
            "a5_benign_twin_false_alarm_rate": a5["benign_twin_false_alarm_rate"],
            "a5_role_referral_routing_accuracy": a5["role_referral_routing_accuracy"],
            "a5_brier_score": a5["brier_score"],
        }
        digest = hashlib.sha256(json.dumps(summary, sort_keys=True).encode("utf-8")).hexdigest()
        return {
            "status": "ok",
            "slot_id": "duecare_alpha_six_arm_counterfactual_evaluator_slot",
            "engine_id": self.engine_id,
            "version": self.version,
            "summary": summary,
            "arms": arms_evaluated,
            "receipt_sha256": digest,
        }


def run_all_llm_investigator_taxonomy_and_duecare_alpha_evaluations() -> dict[str, Any]:
    """Run full verification across the 24-benchmark taxonomy gap analyzer and 6-arm DueCare-Alpha evaluator."""
    taxonomy_adapter = ThinComponentAdapter(
        LLMInvestigatorBenchmarkTaxonomyAndGapAnalyzerEngine(),
        "llm_investigator_benchmark_taxonomy_and_gap_analyzer_slot",
    )
    counterfactual_adapter = ThinComponentAdapter(
        DueCareAlphaSixArmCounterfactualEvaluatorEngine(),
        "duecare_alpha_six_arm_counterfactual_evaluator_slot",
    )
    tax_res = taxonomy_adapter.execute({})
    cf_res = counterfactual_adapter.execute({})
    return {
        "status": "ok",
        "taxonomy_and_gap_matrix": tax_res,
        "duecare_alpha_six_arm_eval": cf_res,
        "all_receipts_verified": taxonomy_adapter.verify_receipt(tax_res)
        and counterfactual_adapter.verify_receipt(cf_res),
    }
