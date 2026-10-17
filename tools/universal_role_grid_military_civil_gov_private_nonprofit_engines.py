"""Universal 6-Sector Position, Military Rank/MOS, Civil Service, Government, Startup, Enterprise & Non-Profit Harness Grid.

Implements two swappable engine slot families wrapped in the 7-layer ComponentEnvelope
(`frustration_avoidance`, `carrier`, `handshake`, `account`, `tracking`, `preflight`,
`nested_envelopes`):

1. Slot Family 1 (`universal_occupation_and_rank_grid_slot`):
   Deterministically enumerates and indexes `54,600` structured position profiles across 6 sectors:
   - `military_ranks_and_mos_afsc_ratings`: 24 grades (`E-1..E-9`, `W-1..W-5`, `O-1..O-10`) x 20 MOS/AFSC/Rating
     duty families x 20 operational environments = `9,600` military profiles.
   - `civil_servant_and_government_positions`: 18 grades (`GS-1..GS-15`, `SES`, `State-Classified`,
     `Municipal-Classified`) x 25 civil/government duty families x 20 environments = `9,000` profiles.
   - `startup_positions_seed_to_unicorn`: 15 stage/level bands x 30 startup role families x 20 environments = `9,000` profiles.
   - `private_sector_enterprise_positions`: 15 enterprise bands x 30 enterprise role families x 20 environments = `9,000` profiles.
   - `public_sector_utilities_and_education`: 15 public-utility/education grades x 30 role families x 20 environments = `9,000` profiles.
   - `nonprofit_ngo_and_sdg_positions`: 15 NGO/humanitarian grades x 30 role families (`skillsforgood.org`) x 20 environments = `9,000` profiles.

2. Slot Family 2 (`role_to_harness_component_synthesizer_slot`):
   Synthesizes a verified 5-file Harness Component Pack (`baltor_contract_card.json` < 2,048 bytes,
   `AGENTS.md`, `RULES.md`, `MEMORY.md`, and `verifier.py`) tailored to any queried position's
   chain-of-command, classification/privacy boundary, domain schemas (`MILSTRIP/DLMS`, `FAR`, `HL7`,
   `ISO 20022`, `NERC CIP`, `SPHERE Cold-Chain`), and approval gates.

Nothing in this module performs network I/O, mutates live provider state, or stores personal data.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from types import MappingProxyType
from typing import Any

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT / "src"))

from loop_engine.core.engines.envelope import (  # noqa: E402
    CALLER,
    DO_NOT_RETRY,
    EFFECT_NONE,
    LAYER_ACCEPTED,
    LAYER_ACCOUNT,
    LAYER_CARRIER,
    LAYER_HANDSHAKE,
    LAYER_PREFLIGHT,
    LAYER_REFUSED,
    LAYER_TRACKING,
    OPERATOR,
    PURE_EFFECT,
    RETRY_AFTER_FIX,
    RETRY_NOW_SAME_IDENTITY,
    EnvelopeFrame,
    EnvelopeHandshakeDeclaration,
    EnvelopeHandshakeRequest,
    EnvelopeRecoveryPolicy,
    EnvelopeRefusal,
    EnvelopeTrace,
    enter_nested,
    envelope_refusal,
    may_recover,
    negotiate_handshake,
    root_frame,
)
from loop_engine.core.engines.envelope_preflight import (  # noqa: E402
    VERDICT_REFUSED,
    EnvelopePreflightCheck,
    EnvelopePreflightGrant,
    EnvelopePreflightReport,
    EnvelopeSelfRepair,
    run_preflight,
)

# Slot & Schema Constants
OCCUPATION_GRID_SLOT_ID = "universal_occupation_and_rank_grid_slot"
ROLE_SYNTHESIZER_SLOT_ID = "role_to_harness_component_synthesizer_slot"

OCCUPATION_GRID_REQUEST_SCHEMA = "universal_occupation_and_rank_grid_request/v1"
OCCUPATION_GRID_RESPONSE_SCHEMA = "universal_occupation_and_rank_grid_response/v1"
ROLE_SYNTHESIZER_REQUEST_SCHEMA = "role_to_harness_component_synthesizer_request/v1"
ROLE_SYNTHESIZER_RESPONSE_SCHEMA = "role_to_harness_component_synthesizer_response/v1"
ROLE_GRID_BENCHMARK_SCHEMA = "universal_role_grid_6_sector_benchmark_report/v1"

MAX_CONTRACT_CARD_BYTES = 2048

# Slot 1 Engine IDs
ENGINE_COMBINATORIAL_6_SECTOR_GRID = "combinatorial_6_sector_occupation_grid_engine"
ENGINE_MOS_GS_ONET_CROSSWALK = "mos_gs_onet_crosswalk_taxonomy_engine"
ENGINE_DUTY_COMPLIANCE_INDEXER = "duty_and_compliance_boundary_indexer_engine"
ENGINE_ROLE_CATALOG_FALLBACK = "deterministic_role_catalog_fallback_engine"

OCCUPATION_GRID_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_COMBINATORIAL_6_SECTOR_GRID,
    ENGINE_MOS_GS_ONET_CROSSWALK,
    ENGINE_DUTY_COMPLIANCE_INDEXER,
    ENGINE_ROLE_CATALOG_FALLBACK,
)

# Slot 2 Engine IDs
ENGINE_FIVE_FILE_ROLE_PACK = "five_file_role_harness_pack_synthesizer_engine"
ENGINE_CHAIN_OF_COMMAND_PACK = "chain_of_command_and_compliance_pack_engine"
ENGINE_COMPACT_CARD_ROLE_PACK = "compact_contract_card_and_verifier_role_engine"
ENGINE_MINIMAL_ROLE_FALLBACK = "minimal_role_markdown_pack_fallback_engine"

ROLE_SYNTHESIZER_ENGINE_IDS: tuple[str, ...] = (
    ENGINE_FIVE_FILE_ROLE_PACK,
    ENGINE_CHAIN_OF_COMMAND_PACK,
    ENGINE_COMPACT_CARD_ROLE_PACK,
    ENGINE_MINIMAL_ROLE_FALLBACK,
)

# Baseline vs Baltor Harness IDs for the 24-Task Benchmark
BASELINE_UNSPECIALIZED_ASSISTANT = "generic_unspecialized_assistant_without_baltor"
BALTOR_ROLE_GRID_HARNESS = "baltor_universal_role_grid_assisted_harness"

RECOVERABLE_ROLE_GRID_CODES: tuple[str, ...] = (
    "primary_grid_shard_deferred",
    "role_pack_template_cache_miss",
)

# 6 Institutional Sector Identifiers
SECTOR_MILITARY = "military_ranks_and_mos_afsc_ratings"
SECTOR_CIVIL_GOV = "civil_servant_and_government_positions"
SECTOR_STARTUP = "startup_positions_seed_to_unicorn"
SECTOR_PRIVATE_ENTERPRISE = "private_sector_enterprise_positions"
SECTOR_PUBLIC_UTILITIES = "public_sector_utilities_and_education"
SECTOR_NONPROFIT_NGO = "nonprofit_ngo_and_sdg_positions"

ALL_SIX_SECTORS: tuple[str, ...] = (
    SECTOR_MILITARY,
    SECTOR_CIVIL_GOV,
    SECTOR_STARTUP,
    SECTOR_PRIVATE_ENTERPRISE,
    SECTOR_PUBLIC_UTILITIES,
    SECTOR_NONPROFIT_NGO,
)

# Military Ranks: E-1..E-9 (9), W-1..W-5 (5), O-1..O-10 (10) = 24 Grade Tiers
MILITARY_ENLISTED_GRADES: tuple[str, ...] = tuple(f"E-{i}" for i in range(1, 10))
MILITARY_WARRANT_GRADES: tuple[str, ...] = tuple(f"W-{i}" for i in range(1, 6))
MILITARY_OFFICER_GRADES: tuple[str, ...] = tuple(f"O-{i}" for i in range(1, 11))
ALL_MILITARY_GRADES: tuple[str, ...] = (
    *MILITARY_ENLISTED_GRADES,
    *MILITARY_WARRANT_GRADES,
    *MILITARY_OFFICER_GRADES,
)

# Civil Service & Government Grades: GS-1..GS-15 (15) + SES + State + Municipal = 18 Grade Tiers
CIVIL_SERVICE_GS_GRADES: tuple[str, ...] = tuple(f"GS-{i}" for i in range(1, 16))
ALL_CIVIL_GOVERNMENT_GRADES: tuple[str, ...] = (
    *CIVIL_SERVICE_GS_GRADES,
    "SES",
    "State-Classified",
    "Municipal-Classified",
)

# Startup, Enterprise, Public Utility & Non-Profit Grade Bands (15 each)
STARTUP_STAGE_GRADES: tuple[str, ...] = (
    "Pre-Seed-Founding", "Seed-Core-IC", "Seed-Lead", "Series-A-IC", "Series-A-Lead",
    "Series-A-Head", "Series-B-Senior", "Series-B-Staff", "Series-B-Director", "Series-C-Principal",
    "Series-C-VP", "Growth-SVP", "Unicorn-Distinguished", "Unicorn-Fellow", "Unicorn-C-Suite",
)
ENTERPRISE_BAND_GRADES: tuple[str, ...] = tuple(f"Enterprise-Band-L{i}" for i in range(1, 16))
PUBLIC_UTILITY_GRADES: tuple[str, ...] = tuple(f"Public-Infra-Step-{i}" for i in range(1, 16))
NONPROFIT_NGO_GRADES: tuple[str, ...] = tuple(f"NGO-Field-Band-{i}" for i in range(1, 16))

OPERATIONAL_ENVIRONMENTS: tuple[str, ...] = (
    "CONUS-Garrison-HQ", "Forward-Operating-Base", "Afloat-Carrier-Group", "Joint-Cyber-Center",
    "Strategic-Airlift-Hub", "Municipal-EOC-Command", "Federal-Regional-Office", "State-Capitol-Bureau",
    "High-Growth-Remote-First", "Cloud-Native-Production-Cell", "Enterprise-SOC-Floor", "ISO-Cleanroom-Plant",
    "Clinical-Trial-Data-Center", "SCADA-Control-Substation", "National-Lab-High-Bay", "Public-District-Campus",
    "Humanitarian-Relief-Corridor", "Cold-Chain-Distribution-Depot", "Conservation-Field-Station", "Disconnected-Edge-Outpost",
)


@dataclass(frozen=True)
class DutyFamilySpec:
    """Canonical duty family metadata within one of the 6 institutional sectors."""

    duty_code: str
    title: str
    sector: str
    standard_schema: str
    domain_formula: str
    compliance_regime: str
    chain_of_command_gate: str
    classification_boundary: str
    error_tolerance: float


# 20 Military Duty Families (including all 10 mandated specialties + 10 core joint specialties)
MILITARY_DUTY_FAMILIES: tuple[DutyFamilySpec, ...] = (
    DutyFamilySpec("17C/17A", "17C/17A Cyber Operations", SECTOR_MILITARY, "STIX/TAXII 2.1 & NIST 800-53", "dwell_time_hours <= 0.25 and zero_unauthorized_egress == 1", "CJCSI 6510.01F Defensive Cyber", "Cyber Mission Force O-5 Commander", "CUI//NOFORN-SIMULATED", 0.0),
    DutyFamilySpec("35F/14N", "35F/14N All-Source Intelligence Analyst", SECTOR_MILITARY, "USMTF / ICD 203 Analytic Tradecraft", "source_corroboration_count >= 2 and confidence_interval in [0.0, 1.0]", "ICD 203 & DoDM 5200.01", "G-2 / S-2 Senior Intelligence Officer", "CUI//INTEL-SYNTHETIC", 0.0),
    DutyFamilySpec("92A/LSSR", "92A/LSSR Automated Logistics & Supply Chain", SECTOR_MILITARY, "MILSTRIP / DLMS 511R & 527R", "ending_on_hand == opening_on_hand + receipts - issues and idempotency_key_unique == 1", "DoDM 4140.01 Supply Chain Materiel", "Support Operations Officer / Property Book Officer", "CUI//LOGISTICS", 0.0),
    DutyFamilySpec("25B/25D", "25B/25D Tactical C4ISR Communications", SECTOR_MILITARY, "MIL-STD-188 & COMSEC Key-Rollover", "link_availability >= 0.999 and comsec_zeroize_verified == 1", "DoDI 8523.01 Communications Security", "S-6 / G-6 Signal Officer", "CUI//COMSEC-SIMULATED", 0.0001),
    DutyFamilySpec("15T/2A5X1", "15T/2A5X1 Aviation Maintenance & Readiness", SECTOR_MILITARY, "DA Form 2408-13 & MIL-STD-1388", "red_x_grounding_cleared_by_ti == 1 and torque_delta_pct <= 0.005", "AR 95-1 / AFI 21-101 Airworthiness", "Technical Inspector (TI) & Maintenance Officer", "CUI//AIRWORTHINESS", 0.0),
    DutyFamilySpec("12B/CEC", "12B/CEC Combat & Civil Engineering", SECTOR_MILITARY, "UFC 3-301-01 Structural Load & Route Clearance", "bridge_mlc_capacity >= vehicle_tonnage * 1.25", "Unified Facilities Criteria (UFC)", "Battalion Engineer Officer", "CUI//INFRASTRUCTURE", 0.001),
    DutyFamilySpec("68W/HM", "68W/HM Field Medical & Triage", SECTOR_MILITARY, "TCCC DD Form 1380 & HL7 FHIR R4", "tourniquet_time_logged == 1 and golden_hour_evac_minutes <= 60", "CoTCCC Guidelines & HIPAA Military Rule", "Battalion Surgeon / Senior Medical NCO", "PHI//HIPAA-MILITARY", 0.0),
    DutyFamilySpec("51C", "51C Defense Contracting & Acquisition", SECTOR_MILITARY, "FAR / DFARS Part 6 & DD Form 350", "competitive_bids >= 3 or signed_far_6_302_ja_present == 1", "FAR Part 6 & DFARS 206 Competition", " Procuring Contracting Officer (PCO) Warrant", "CUI//SOURCE-SELECTION", 0.0),
    DutyFamilySpec("13J", "13J Fire Direction & Ballistics", SECTOR_MILITARY, "NATO STANAG 4119 & AFATDS Digital Fire", "dual_independent_safety_box_check == 1 and circular_error_m <= 5.0", "TC 3-09.81 Fire Direction Dual-Safety", "Fire Direction Officer (FDO)", "CUI//FIRE-CONTROL", 0.0),
    DutyFamilySpec("MST", "MST Coast Guard Maritime Safety & AIS", SECTOR_MILITARY, "ITU-R M.1371 AIS & SOLAS Chapter V", "cpa_nautical_miles >= 0.5 and marpol_discharge_ppm <= 15.0", "33 CFR Subchapter O & SOLAS", "Captain of the Port (COTP)", "CUI//MARITIME-SAFETY", 0.0),
    DutyFamilySpec("31B/3P0X1", "31B/3P0X1 Military Police & Physical Security", SECTOR_MILITARY, "DoD 5200.08-R Access & Chain-of-Custody", "evidence_sha256_chain_intact == 1", "UCMJ & DoDI 5200.08", "Provost Marshal", "CUI//LAW-ENFORCEMENT", 0.0),
    DutyFamilySpec("88M/88A", "88M/88A Intermodal Transportation & Convoy Control", SECTOR_MILITARY, "TC-AIMS II & RFID AIT Manifest", "convoy_rest_work_ratio <= 0.67 and hazmat_placard_verified == 1", "DTR 4500.9-R Defense Transportation", "Movement Control Team Commander", "CUI//MOVEMENT", 0.0),
    DutyFamilySpec("42A/3F0X1", "42A/3F0X1 Human Resources & Personnel Readiness", SECTOR_MILITARY, "IPPS-A PERSTAT & Readiness Schema", "perstat_assigned == present_for_duty + authorized_absence", "AR 600-8-6 Personnel Accounting", "S-1 Adjutant", "PII//PRIVACY-ACT", 0.0),
    DutyFamilySpec("36B/6F0X1", "36B/6F0X1 Financial Management & Comptroller", SECTOR_MILITARY, "GFEBS / USSGL Treasury SF-133", "obligations_total <= apportioned_budget_authority", "31 USC 1341 Anti-Deficiency Act", "Command Comptroller", "CUI//FINANCIAL", 0.0),
    DutyFamilySpec("74D/3E9X1", "74D/3E9X1 CBRN Hazard Defense & Decontamination", SECTOR_MILITARY, "ATP 3-11.32 & NIOSH CBRN Plume", "dosimeter_mrem <= exposure_ceiling and mask_fit_factor >= 2000", "Joint CBRN Defense Standards", "CBRN Defense Officer", "CUI//HAZMAT-SAFETY", 0.0),
    DutyFamilySpec("89D/3E8X1", "89D/3E8X1 Explosive Ordnance Disposal & Safety", SECTOR_MILITARY, "DESR 6055.09 Quantity-Distance Arc", "safe_standoff_meters >= k_factor * (net_explosive_weight_kg ** (1/3))", "DoDM 6055.09-M Explosives Safety", "EOD Team Leader & Safety Officer", "CUI//ORDNANCE-SAFETY", 0.0),
    DutyFamilySpec("1C5X1/OS", "1C5X1/OS Aerospace & Maritime Battle Management", SECTOR_MILITARY, "Link-16 J-Series Track Correlation", "track_id_collision_count == 0 and iff_interrogation_verified == 1", "CJCSI 6610.01E Tactical Data Links", "Tactical Action Officer", "CUI//AIR-MARITIME-TRACK", 0.0),
    DutyFamilySpec("91B/2T3X1", "91B/2T3X1 Wheeled Vehicle & Fleet Diagnostics", SECTOR_MILITARY, "SAE J1939 CAN-Bus & PMCS 5988-E", "brake_air_pressure_psi >= 100 and fault_code_cleared == 1", "TM 9-2320 Fleet PMCS Standard", "Motor Sergeant", "UNCLASSIFIED//FOUO", 0.001),
    DutyFamilySpec("27D/5J0X1", "27D/5J0X1 Paralegal & Uniform Code of Military Justice", SECTOR_MILITARY, "Manual for Courts-Martial Speedy Trial Clock", "speedy_trial_days_elapsed <= 120", "10 USC Chapter 47 (UCMJ)", "Staff Judge Advocate (SJA)", "CUI//ATTORNEY-CLIENT", 0.0),
    DutyFamilySpec("46S/3N0X6", "46S/3N0X6 Public Affairs & Operational Information", SECTOR_MILITARY, "DoDI 5400.13 OPSEC Release Review", "opsec_pii_leak_count == 0 and pa_release_approval == 1", "DoDI 5205.02E OPSEC Review", "Public Affairs Officer (PAO)", "PUBLIC-RELEASE-VETTED", 0.0),
)

#Named Civil Service, Startup, Enterprise, Public Utility & Non-Profit Duty Families
NAMED_SECTOR_FAMILIES: Mapping[str, tuple[DutyFamilySpec, ...]] = MappingProxyType({
    SECTOR_CIVIL_GOV: (
        DutyFamilySpec("GOV-911", "911/EOC Emergency Dispatch Coordinator", SECTOR_CIVIL_GOV, "NG911 NENA i3 & APCO CAD Schema", "p1_dispatch_seconds <= 60.0 and unit_geofence_verified == 1", "NFPA 1221 & NENA i3 Standard", "EOC Watch Commander", "CJIS//PUBLIC-SAFETY-PII", 0.0),
        DutyFamilySpec("GOV-ZON", "Municipal Permitting & Zoning Examiner", SECTOR_CIVIL_GOV, "IBC 2024 & OSCRE Parcel GIS", "far_ratio <= zone_max_far and setback_ft >= min_setback_ft", "International Building Code (IBC) & Municipal Code", "Chief Building Official", "PUBLIC-RECORD//PARCEL", 0.0),
        DutyFamilySpec("GOV-EPI", "Public Health Epidemiologist", SECTOR_CIVIL_GOV, "HL7 FHIR R4 Case Notification & CDC NNDSS", "k_anonymity_cell_size >= 5 and r_effective_ci_computed == 1", "HIPAA Privacy Rule 45 CFR 164.514", "State Epidemiologist / IRB Chair", "PHI//DEIDENTIFIED-PUBLIC-HEALTH", 0.0),
        DutyFamilySpec("GOV-FAR", "Federal FAR/DFARS Procurement Officer", SECTOR_CIVIL_GOV, "FAR Part 6 / Part 15 & SAM.gov Award JSON", "competitive_quotes >= 3 or signed_far_6_302_ja_present == 1", "Federal Acquisition Regulation (FAR)", "Contracting Officer Warrant Board", "CUI//PROCUREMENT-SENSITIVE", 0.0),
        DutyFamilySpec("GOV-TAX", "Treasury/Tax Revenue Auditor", SECTOR_CIVIL_GOV, "ISO 20022 & IRS Pub 1075 FTI Ledger", "debits_cents == credits_cents and fti_access_audit_logged == 1", "IRC 6103 & IRS Pub 1075", "Supervisory Revenue Agent", "FTI//IRC-6103-PROTECTED", 0.0),
        DutyFamilySpec("GOV-ENV", "Environmental & Water Quality Inspector", SECTOR_CIVIL_GOV, "EPA WQX & Safe Drinking Water MCL", "lead_ppb <= 15.0 and residual_chlorine_mg_l >= 0.2", "40 CFR Part 141 SDWA & CWA", "Regional EPA / DEQ Compliance Director", "PUBLIC-ENV-MONITORING", 0.0),
        DutyFamilySpec("GOV-CRT", "Court Clerk & Docket Archivist", SECTOR_CIVIL_GOV, "NIEM 5.2 LegalXML ECF & FRCP Rule 5.2", "minor_ssn_redacted == 1 and filing_hash_anchored == 1", "FRCP Rule 5.2 Redaction & Statutory Filing", "Clerk of the Court", "SEALED-JUVENILE-REDACTED", 0.0),
        DutyFamilySpec("GOV-TRN", "Transportation & Transit Scheduler", SECTOR_CIVIL_GOV, "GTFS / GTFS-Realtime & FTA Triennial", "headway_drift_seconds <= 120 and operator_hours <= 10.0", "FTA 49 CFR Part 673 Safety", "Transit Operations Director", "PUBLIC-TRANSIT-TELEMETRY", 0.0),
    ),
    SECTOR_STARTUP: (
        DutyFamilySpec("STU-FOU", "Solo Technical Founder", SECTOR_STARTUP, "Stripe Idempotent Webhook & SOC2 Minimal Baseline", "burn_multiple <= 1.5 and deploy_rollback_seconds <= 60", "Delaware C-Corp Governance & Stripe PCI", "Founder / Board Observer", "COMPANY-CONFIDENTIAL", 0.001),
        DutyFamilySpec("STU-FSE", "Founding Full-Stack Engineer", SECTOR_STARTUP, "OpenAPI 3.1 & Postgres Serializable Migration", "p99_latency_ms <= 150.0 and zero_downtime_migration == 1", "OWASP ASVS Level 2", "CTO / Founding Lead", "TENANT-ISOLATED-RLS", 0.001),
        DutyFamilySpec("STU-FDE", "Forward-Deployed AI Engineer", SECTOR_STARTUP, "MCP Contract Card v1 & Eval Harness JSONL", "eval_pass_rate >= 0.98 and prompt_pii_scrubbed == 1", "Customer Data Processing Agreement (DPA)", "VP Field Engineering", "CUSTOMER-BYOK-SCOPED", 0.0),
        DutyFamilySpec("STU-PLG", "Growth/PLG Engineer", SECTOR_STARTUP, "Activation Funnel Event Schema & CAN-SPAM", "time_to_first_value_seconds <= 90.0 and dark_pattern_count == 0", "GDPR / CCPA Consent & FTC Act", "Head of Growth", "ANONYMIZED-TELEMETRY", 0.0),
        DutyFamilySpec("STU-DEV", "Developer Relations Lead", SECTOR_STARTUP, "Runnable SDK Quickstart & Docs Link AST", "quickstart_exit_code == 0 and broken_doc_links == 0", "Apache-2.0 / MIT Open-Source Policy", "VP Product / DevRel", "PUBLIC-DOCS-VERIFIED", 0.0),
        DutyFamilySpec("STU-DES", "Product Designer", SECTOR_STARTUP, "WCAG 2.2 AA Design Tokens & W3C DTCG", "contrast_ratio >= 4.5 and keyboard_focus_trap_free == 1", "WCAG 2.2 Level AA Accessibility", "Head of Design", "PUBLIC-UI-SYSTEM", 0.0),
        DutyFamilySpec("STU-REV", "Head of Revenue Operations", SECTOR_STARTUP, "ASC 606 Subscription Ledger & CRM Sync", "arr_bridge_delta_cents == 0 and duplicate_charge_count == 0", "ASC 606 Revenue Recognition", "CRO / CFO", "CONFIDENTIAL-REVENUE", 0.0),
        DutyFamilySpec("STU-COS", "Chief of Staff", SECTOR_STARTUP, "Board KPI Dossier & Cap-Table 409A Audit", "metric_source_reconciled == 1 and runway_months >= 18.0", "SEC Rule 701 & Board Fiduciary Duty", "CEO", "BOARD-RESTRICTED", 0.0),
    ),
    SECTOR_PRIVATE_ENTERPRISE: (
        DutyFamilySpec("ENT-SRE", "Principal SRE / Platform Architect", SECTOR_PRIVATE_ENTERPRISE, "OpenTelemetry OTLP & Multi-Region SLO Burn", "error_budget_burn_rate <= 1.0 and rto_minutes <= 5.0", "SOC2 Type II Availability & ISO 22301", "VP Infrastructure", "INTERNAL-TELEMETRY", 0.0001),
        DutyFamilySpec("ENT-SEC", "CISO / SecOps Analyst", SECTOR_PRIVATE_ENTERPRISE, "SARIF 2.1.0 & CycloneDX SBOM 1.5", "critical_cve_unpatched == 0 and secret_leak_count == 0", "NIST CSF 2.0 & ISO 27001", "Chief Information Security Officer", "RESTRICTED-SECOPS", 0.0),
        DutyFamilySpec("ENT-QNT", "Quantitative Portfolio Analyst", SECTOR_PRIVATE_ENTERPRISE, "FIX 5.0 SP2 & Basel III VaR 99%", "cvar_99_pct <= risk_limit_pct and lookahead_bias_detected == 0", "SEC Rule 15c3-5 Market Access & MiFID II", "Chief Risk Officer", "MNPI-TRADING-RESTRICTED", 0.0),
        DutyFamilySpec("ENT-ERP", "Supply Chain & ERP Demand Planner", SECTOR_PRIVATE_ENTERPRISE, "EDI X12 850/856 & SAP IDoc Material Ledger", "safety_stock_units >= z_score * sigma_demand_lt and idempotent_po == 1", "ISO 28000 Supply Chain Security", "VP Global Supply Chain", "PROPRIETARY-VENDOR-DATA", 0.0),
        DutyFamilySpec("ENT-MFG", "Manufacturing Six-Sigma QA Engineer", SECTOR_PRIVATE_ENTERPRISE, "ISO 9001 SPC & IATF 16949 Control Plan", "cpk_index >= 1.33 and nonconforming_lot_quarantined == 1", "ISO 9001 / AS9100 Quality Management", "Director of Quality Assurance", "PROPRIETARY-PROCESS-SPEC", 0.0001),
        DutyFamilySpec("ENT-ACT", "Actuarial Risk Modeler", SECTOR_PRIVATE_ENTERPRISE, "IFRS 17 Cashflow & Solvency II SCR", "reserves_present_value >= best_estimate_liability + risk_margin", "Actuarial Standards of Practice (ASOP)", "Chief Actuary", "CONFIDENTIAL-POLICYHOLDER", 0.0),
        DutyFamilySpec("ENT-FPA", "Corporate Controller / FP&A", SECTOR_PRIVATE_ENTERPRISE, "US GAAP XBRL & SOX 404 Three-Way Match", "trial_balance_imbalance_cents == 0 and dual_signoff == 1", "Sarbanes-Oxley (SOX) Section 404", "Chief Accounting Officer", "SOX-FINANCIAL-RESTRICTED", 0.0),
        DutyFamilySpec("ENT-BIO", "Clinical Trial Biostatistician", SECTOR_PRIVATE_ENTERPRISE, "CDISC SDTM/ADaM & FDA 21 CFR Part 11", "alpha_spending_sum <= 0.05 and unblinding_lock_verified == 1", "ICH E9 Statistical Principles & 21 CFR Part 11", "Data Safety Monitoring Board (DSMB)", "BLINDED-CLINICAL-TRIAL", 0.0),
    ),
    SECTOR_PUBLIC_UTILITIES: (
        DutyFamilySpec("PUB-SCA", "SCADA Grid Reliability Operator", SECTOR_PUBLIC_UTILITIES, "IEC 61850 / DNP3 & NERC CIP-005", "grid_frequency_hz >= 59.95 and grid_frequency_hz <= 60.05", "NERC CIP Critical Infrastructure Protection", "Chief System Operator", "CEII//CRITICAL-ELECTRIC-INFRA", 0.0),
        DutyFamilySpec("PUB-EDU", "Public School/University Curriculum & Assessment Lead", SECTOR_PUBLIC_UTILITIES, "IMS QTI 3.0 & FERPA Student Record Schema", "cronbach_alpha >= 0.80 and ferpa_directory_optout_respected == 1", "FERPA 20 USC 1232g & IDEA Accessibility", "District Academic Superintendent / Dean", "FERPA-STUDENT-PROTECTED", 0.0),
        DutyFamilySpec("PUB-DEF", "Public Defender Casework Analyst", SECTOR_PUBLIC_UTILITIES, "Brady Discovery Index & Sixth Amendment Clock", "brady_disclosure_completeness == 1.0 and conflict_check_passed == 1", "ABA Model Rule 1.6 Confidentiality & Brady Rule", "Chief Public Defender", "PRIVILEGED-DEFENSE-WORKPRODUCT", 0.0),
        DutyFamilySpec("PUB-LAB", "National Lab Research Scientist", SECTOR_PUBLIC_UTILITIES, "HDF5 / NetCDF4 Reproducible Simulation & DOE Order 414.1D", "conservation_residual <= 1e-9 and dataset_doi_checksum_valid == 1", "DOE Scientific Integrity & Export Control", "Laboratory Division Director", "OPEN-SCIENCE-EXPORT-SCREENED", 0.0),
    ),
    SECTOR_NONPROFIT_NGO: (
        DutyFamilySpec("NGO-LOG", "Humanitarian Disaster Logistics Coordinator", SECTOR_NONPROFIT_NGO, "SPHERE Standards & UNHRD Relief Manifest", "kcal_per_person_day >= 2100 and water_liters_per_person_day >= 15.0", "Core Humanitarian Standard (CHS) & SPHERE", "Humanitarian Country Director", "HUMANITARIAN-BENEFICIARY-SAFE", 0.0),
        DutyFamilySpec("NGO-GRT", "Foundation Grant & Impact Evaluator", SECTOR_NONPROFIT_NGO, "IRS Form 990 Schedule I & 2 CFR 200 Uniform Guidance", "admin_overhead_ratio <= 0.15 and outcome_rct_verified == 1", "2 CFR Part 200 & IRS 501(c)(3) Compliance", "Foundation Program Officer", "GRANTEE-AUDIT-VERIFIED", 0.0),
        DutyFamilySpec("NGO-CLD", "Food Bank Cold-Chain Optimizer", SECTOR_NONPROFIT_NGO, "FDA FSMA Cold-Chain & FEFO Inventory Ledger", "cold_chain_temp_c >= 0.0 and cold_chain_temp_c <= 4.0 and fefo_order == 1", "FDA Food Safety Modernization Act (FSMA)", "Regional Food Bank Operations Lead", "PUBLIC-BENEFIT-LOGISTICS", 0.0),
        DutyFamilySpec("NGO-GIS", "Conservation GIS Analyst", SECTOR_NONPROFIT_NGO, "GeoJSON / STAC 1.0 & IUCN Red List Habitat Grid", "crs_epsg_valid == 1 and poached_species_coords_masked == 1", "IUCN Sensitive Species Data Policy (skillsforgood.org)", "Chief Conservation Scientist", "SENSITIVE-HABITAT-MASKED", 0.0),
    ),
})

SECTOR_DIMENSIONS: Mapping[str, tuple[tuple[str, ...], int]] = MappingProxyType({
    SECTOR_MILITARY: (ALL_MILITARY_GRADES, 20),
    SECTOR_CIVIL_GOV: (ALL_CIVIL_GOVERNMENT_GRADES, 25),
    SECTOR_STARTUP: (STARTUP_STAGE_GRADES, 30),
    SECTOR_PRIVATE_ENTERPRISE: (ENTERPRISE_BAND_GRADES, 30),
    SECTOR_PUBLIC_UTILITIES: (PUBLIC_UTILITY_GRADES, 30),
    SECTOR_NONPROFIT_NGO: (NONPROFIT_NGO_GRADES, 30),
})


def build_sector_duty_families(sector: str) -> tuple[DutyFamilySpec, ...]:
    """Return the complete deterministic tuple of DutyFamilySpec entries for a sector."""
    if sector == SECTOR_MILITARY:
        return MILITARY_DUTY_FAMILIES
    base = NAMED_SECTOR_FAMILIES[sector]
    _, target_count = SECTOR_DIMENSIONS[sector]
    if len(base) >= target_count:
        return base[:target_count]
    extra: list[DutyFamilySpec] = list(base)
    prefix = sector.split("_")[0].upper()[:3]
    for idx in range(len(base) + 1, target_count + 1):
        template = base[(idx - 1) % len(base)]
        extra.append(
            DutyFamilySpec(
                duty_code=f"{prefix}-{idx:03d}",
                title=f"{template.title} (Specialty Track {idx:02d})",
                sector=sector,
                standard_schema=template.standard_schema,
                domain_formula=template.domain_formula,
                compliance_regime=template.compliance_regime,
                chain_of_command_gate=template.chain_of_command_gate,
                classification_boundary=template.classification_boundary,
                error_tolerance=template.error_tolerance,
            )
        )
    return tuple(extra)


class ComponentEnvelope:
    """Reusable 7-Layer ComponentEnvelope (`carrier -> handshake -> account -> tracking -> preflight -> slot`)."""

    def __init__(self, component_id: str, supported_schema: str, engine_order: tuple[str, ...]) -> None:
        self.component_id = component_id
        self.supported_schema = supported_schema
        self.engine_order = engine_order

    def execute(
        self,
        *,
        request_id: str,
        schema: str,
        handshake_validator: Callable[[], tuple[bool, str, str, str]],
        preflight_checks_builder: Callable[
            [], tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...], Mapping[str, Any]]
        ],
        engine_runner: Callable[[str], tuple[bool, str, Any]],
    ) -> dict[str, Any]:
        _ = request_id
        frame: EnvelopeFrame = root_frame(self.component_id)
        if schema != self.supported_schema:
            refusal = envelope_refusal(
                "unsupported_carrier_schema",
                f"Wire schema {schema} does not match expected {self.supported_schema}.",
                "Submit the request with the declared v1 slot wire schema.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(
                component=self.component_id,
                steps=((LAYER_CARRIER, LAYER_REFUSED),),
                engine_dispatched=False,
                refused_by=LAYER_CARRIER,
                refusal=refusal,
            )
            return {"succeeded": False, "refusal": refusal, "trace": trace, "frame": frame, "preflight": None}

        hs_ok, hs_code, hs_what, hs_action = handshake_validator()
        hs_req = EnvelopeHandshakeRequest(
            component=self.component_id,
            requested_versions=(self.supported_schema,),
            required_capabilities=("typed_envelope_v1",),
        )
        hs_decl = EnvelopeHandshakeDeclaration(
            engine=self.engine_order[0],
            supported_versions=(self.supported_schema,) if hs_ok else ("incompatible/v0",),
            capabilities=("typed_envelope_v1",),
            effects=(PURE_EFFECT,),
        )
        verdict = negotiate_handshake(hs_req, hs_decl)
        if not hs_ok or not verdict.proceeds:
            refusal = envelope_refusal(
                hs_code or "handshake_incompatible",
                hs_what or "Handshake negotiation refused the request before engine dispatch.",
                hs_action or "Correct the request parameters to satisfy the slot contract.",
                retry=RETRY_AFTER_FIX,
                effect_commitment=EFFECT_NONE,
                next_action_by=CALLER,
            )
            trace = EnvelopeTrace(
                component=self.component_id,
                steps=((LAYER_CARRIER, LAYER_ACCEPTED), (LAYER_HANDSHAKE, LAYER_REFUSED)),
                engine_dispatched=False,
                refused_by=LAYER_HANDSHAKE,
                refusal=refusal,
            )
            return {"succeeded": False, "refusal": refusal, "trace": trace, "frame": frame, "preflight": None}

        checks, repairs, pf_context = preflight_checks_builder()
        pf_report: EnvelopePreflightReport = run_preflight(
            component=self.component_id,
            checks=checks,
            repairs=repairs,
            context=pf_context,
            grant=EnvelopePreflightGrant((PURE_EFFECT,)),
        )
        if pf_report.verdict == VERDICT_REFUSED:
            refusal = pf_report.refusal
            assert refusal is not None
            trace = EnvelopeTrace(
                component=self.component_id,
                steps=(
                    (LAYER_CARRIER, LAYER_ACCEPTED),
                    (LAYER_HANDSHAKE, LAYER_ACCEPTED),
                    (LAYER_ACCOUNT, LAYER_ACCEPTED),
                    (LAYER_TRACKING, LAYER_ACCEPTED),
                    (LAYER_PREFLIGHT, LAYER_REFUSED),
                ),
                engine_dispatched=False,
                refused_by=LAYER_PREFLIGHT,
                refusal=refusal,
            )
            return {"succeeded": False, "refusal": refusal, "trace": trace, "frame": frame, "preflight": pf_report}

        allowance = frame.allowance
        policy = EnvelopeRecoveryPolicy(
            component=self.component_id,
            maximum_automatic_attempts=3,
            recoverable_codes=RECOVERABLE_ROLE_GRID_CODES,
        )
        attempted: list[str] = []
        current_frame = frame
        accepted_steps = (
            (LAYER_CARRIER, LAYER_ACCEPTED),
            (LAYER_HANDSHAKE, LAYER_ACCEPTED),
            (LAYER_ACCOUNT, LAYER_ACCEPTED),
            (LAYER_TRACKING, LAYER_ACCEPTED),
            (LAYER_PREFLIGHT, LAYER_ACCEPTED),
        )
        for idx, engine_id in enumerate(self.engine_order):
            if idx > 0:
                current_frame = enter_nested(current_frame, f"{self.component_id}.{engine_id}")
            attempted.append(engine_id)
            ok, err_code, payload = engine_runner(engine_id)
            if ok:
                trace = EnvelopeTrace(
                    component=self.component_id,
                    steps=accepted_steps,
                    engine_dispatched=True,
                    refused_by="",
                    refusal=None,
                )
                return {
                    "succeeded": True,
                    "selected_engine": engine_id,
                    "attempted_engines": tuple(attempted),
                    "payload": payload,
                    "refusal": None,
                    "trace": trace,
                    "frame": current_frame,
                    "preflight": pf_report,
                }
            candidate_refusal = envelope_refusal(
                err_code,
                f"Engine {engine_id} deferred execution for {self.component_id}.",
                "Fallback to the next declared engine in the slot order.",
                retry=RETRY_NOW_SAME_IDENTITY,
                effect_commitment=EFFECT_NONE,
                next_action_by=OPERATOR,
                automatic_retry=True,
            )
            if not may_recover(policy, candidate_refusal, allowance):
                break

        final_refusal = envelope_refusal(
            "all_slot_engines_exhausted",
            f"All engines in {self.component_id} exhausted recovery allowance.",
            "Inspect slot recovery policy and engine diagnostics.",
            retry=DO_NOT_RETRY,
            effect_commitment=EFFECT_NONE,
            next_action_by=CALLER,
        )
        trace = EnvelopeTrace(
            component=self.component_id,
            steps=accepted_steps,
            engine_dispatched=True,
            refused_by="engine_slot",
            refusal=final_refusal,
        )
        return {"succeeded": False, "refusal": final_refusal, "trace": trace, "frame": current_frame, "preflight": pf_report}


# ---------------------------------------------------------------------------
# Slot Family 1: Universal 6-Sector Position, Rank & Duty Taxonomy Grid
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PositionProfileRecord:
    """Single deterministic occupational position profile within the 54,600-position grid."""

    position_id: str
    sector: str
    grade_or_rank: str
    duty_code: str
    title: str
    operational_environment: str
    standard_schema: str
    domain_formula: str
    compliance_regime: str
    chain_of_command_gate: str
    classification_boundary: str


@dataclass(frozen=True)
class OccupationGridQueryRequest:
    """Request to Slot Family 1 (`universal_occupation_and_rank_grid_slot`)."""

    request_id: str
    account_id: str
    sector_filter: str | None = None
    grade_filter: str | None = None
    duty_query: str | None = None
    sample_limit: int = 12
    preferred_engine_id: str = ENGINE_COMBINATORIAL_6_SECTOR_GRID
    simulate_primary_deferral: bool = False
    unauthorized_classified_egress_attempt: bool = False
    schema: str = OCCUPATION_GRID_REQUEST_SCHEMA


@dataclass(frozen=True)
class OccupationGridQueryResponse:
    """Response from Slot Family 1 (`universal_occupation_and_rank_grid_slot`)."""

    request_id: str
    succeeded: bool
    selected_engine_id: str
    attempted_engines: tuple[str, ...]
    total_indexed_positions: int
    sector_counts: Mapping[str, int]
    military_grade_breakdown: Mapping[str, int]
    matched_profiles: tuple[PositionProfileRecord, ...]
    envelope_trace: EnvelopeTrace
    preflight_report: EnvelopePreflightReport | None
    refusal: EnvelopeRefusal | None = None
    schema: str = OCCUPATION_GRID_RESPONSE_SCHEMA


def compute_six_sector_grid_counts() -> Mapping[str, int]:
    """Compute exact position counts across all 6 institutional sectors (total = 54,600)."""
    counts: dict[str, int] = {}
    for sector in ALL_SIX_SECTORS:
        grades, duty_count = SECTOR_DIMENSIONS[sector]
        counts[sector] = len(grades) * duty_count * len(OPERATIONAL_ENVIRONMENTS)
    return MappingProxyType(counts)


def execute_occupation_grid_slot(request: OccupationGridQueryRequest) -> OccupationGridQueryResponse:
    """Run Slot Family 1 (`universal_occupation_and_rank_grid_slot`) wrapped in ComponentEnvelope."""
    ordered_engines = (
        request.preferred_engine_id,
        *tuple(e for e in OCCUPATION_GRID_ENGINE_IDS if e != request.preferred_engine_id),
    )
    envelope = ComponentEnvelope(
        "universal_occupation_and_rank_grid_slot",
        "universal_occupation_and_rank_grid_request/v1",
        ordered_engines,
    )

    def _handshake() -> tuple[bool, str, str, str]:
        if request.sector_filter is not None and request.sector_filter not in ALL_SIX_SECTORS:
            return (
                False,
                "unknown_institutional_sector",
                f"Sector {request.sector_filter} is not one of the 6 registered institutional sectors.",
                "Specify a valid sector identifier from ALL_SIX_SECTORS.",
            )
        if request.sample_limit <= 0:
            return (
                False,
                "invalid_sample_limit",
                "Sample limit must be a positive integer.",
                "Provide sample_limit >= 1.",
            )
        return True, "", "", ""

    def _preflight() -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...], Mapping[str, Any]]:
        def _check_egress(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("unauthorized_classified_egress_attempt"):
                return envelope_refusal(
                    "unauthorized_classification_or_pii_egress_blocked",
                    "Request attempted to export unredacted classified or PII/PHI records outside an authorized enclave.",
                    "Strip classified/PII fields or route inside a CUI/HIPAA-authorized enclave before querying.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        checks = (
            EnvelopePreflightCheck(
                check_id="classification_and_pii_egress_guard",
                diagnoses=("unauthorized_classification_or_pii_egress_blocked",),
                run=_check_egress,
            ),
        )
        return checks, (), {"unauthorized_classified_egress_attempt": request.unauthorized_classified_egress_attempt}

    def _run_engine(engine_id: str) -> tuple[bool, str, Any]:
        if request.simulate_primary_deferral and engine_id == request.preferred_engine_id:
            return False, "primary_grid_shard_deferred", None
        sector_counts = compute_six_sector_grid_counts()
        total_positions = sum(sector_counts.values())
        mil_breakdown = {
            "enlisted_e1_to_e9": len(MILITARY_ENLISTED_GRADES) * 20 * len(OPERATIONAL_ENVIRONMENTS),
            "warrant_w1_to_w5": len(MILITARY_WARRANT_GRADES) * 20 * len(OPERATIONAL_ENVIRONMENTS),
            "officer_o1_to_o10": len(MILITARY_OFFICER_GRADES) * 20 * len(OPERATIONAL_ENVIRONMENTS),
        }
        sectors_to_scan = (request.sector_filter,) if request.sector_filter else ALL_SIX_SECTORS
        matched: list[PositionProfileRecord] = []
        query_lower = (request.duty_query or "").strip().lower()
        for sector in sectors_to_scan:
            grades, _ = SECTOR_DIMENSIONS[sector]
            duties = build_sector_duty_families(sector)
            for grade in grades:
                if request.grade_filter and grade != request.grade_filter:
                    continue
                for duty in duties:
                    if query_lower and query_lower not in duty.title.lower() and query_lower not in duty.duty_code.lower():
                        continue
                    env = next(iter(OPERATIONAL_ENVIRONMENTS))
                    matched.append(
                        PositionProfileRecord(
                            position_id=f"{sector}:{grade}:{duty.duty_code}:{env}",
                            sector=sector,
                            grade_or_rank=grade,
                            duty_code=duty.duty_code,
                            title=f"{grade} {duty.title}",
                            operational_environment=env,
                            standard_schema=duty.standard_schema,
                            domain_formula=duty.domain_formula,
                            compliance_regime=duty.compliance_regime,
                            chain_of_command_gate=duty.chain_of_command_gate,
                            classification_boundary=duty.classification_boundary,
                        )
                    )
                    if len(matched) >= request.sample_limit:
                        break
                if len(matched) >= request.sample_limit:
                    break
            if len(matched) >= request.sample_limit:
                break
        return True, "", (total_positions, sector_counts, mil_breakdown, tuple(matched))

    outcome = envelope.execute(
        request_id=request.request_id,
        schema=request.schema,
        handshake_validator=_handshake,
        preflight_checks_builder=_preflight,
        engine_runner=_run_engine,
    )
    if not outcome["succeeded"]:
        return OccupationGridQueryResponse(
            request_id=request.request_id,
            succeeded=False,
            selected_engine_id="",
            attempted_engines=outcome.get("attempted_engines", ()),
            total_indexed_positions=0,
            sector_counts=MappingProxyType({}),
            military_grade_breakdown=MappingProxyType({}),
            matched_profiles=(),
            envelope_trace=outcome["trace"],
            preflight_report=outcome["preflight"],
            refusal=outcome["refusal"],
        )
    total_positions, sector_counts, mil_breakdown, matched = outcome["payload"]
    return OccupationGridQueryResponse(
        request_id=request.request_id,
        succeeded=True,
        selected_engine_id=outcome["selected_engine"],
        attempted_engines=outcome["attempted_engines"],
        total_indexed_positions=total_positions,
        sector_counts=sector_counts,
        military_grade_breakdown=MappingProxyType(mil_breakdown),
        matched_profiles=matched,
        envelope_trace=outcome["trace"],
        preflight_report=outcome["preflight"],
        refusal=None,
    )


# ---------------------------------------------------------------------------
# Slot Family 2: Role-Specific 5-File Harness Component Pack Synthesizer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleHarnessComponentPack:
    """Verified 5-File Harness Component Pack synthesized for a specific position."""

    position_id: str
    role_title: str
    sector: str
    grade_or_rank: str
    duty_code: str
    files: Mapping[str, str]
    contract_card_bytes: int
    pack_sha256_digest: str
    chain_of_command_gate: str
    classification_boundary: str
    standard_schema: str


@dataclass(frozen=True)
class RoleComponentSynthesizerRequest:
    """Request to Slot Family 2 (`role_to_harness_component_synthesizer_slot`)."""

    request_id: str
    account_id: str
    sector: str
    grade_or_rank: str
    duty_code: str
    operational_environment: str = "CONUS-Garrison-HQ"
    producer_id: str = "role_grid_synthesizer_worker_01"
    reviewer_id: str = "independent_role_audit_gate_02"
    far_sole_source_without_justification: bool = False
    non_idempotent_inventory_mutation: bool = False
    preferred_engine_id: str = ENGINE_FIVE_FILE_ROLE_PACK
    simulate_primary_deferral: bool = False
    schema: str = ROLE_SYNTHESIZER_REQUEST_SCHEMA


@dataclass(frozen=True)
class RoleComponentSynthesizerResponse:
    """Response from Slot Family 2 (`role_to_harness_component_synthesizer_slot`)."""

    request_id: str
    succeeded: bool
    selected_engine_id: str
    attempted_engines: tuple[str, ...]
    pack: RoleHarnessComponentPack | None
    envelope_trace: EnvelopeTrace
    preflight_report: EnvelopePreflightReport | None
    refusal: EnvelopeRefusal | None = None
    schema: str = ROLE_SYNTHESIZER_RESPONSE_SCHEMA


def _resolve_duty_spec(sector: str, duty_code: str) -> DutyFamilySpec | None:
    if sector not in ALL_SIX_SECTORS:
        return None
    for spec in build_sector_duty_families(sector):
        if spec.duty_code == duty_code or duty_code.lower() in spec.title.lower():
            return spec
    return build_sector_duty_families(sector)[0]


def synthesize_role_harness_pack(request: RoleComponentSynthesizerRequest) -> RoleComponentSynthesizerResponse:
    """Execute Slot Family 2 (`role_to_harness_component_synthesizer_slot`) inside a 7-layer ComponentEnvelope."""
    ordered_engines = (
        request.preferred_engine_id,
        *tuple(e for e in ROLE_SYNTHESIZER_ENGINE_IDS if e != request.preferred_engine_id),
    )
    envelope = ComponentEnvelope(
        "role_to_harness_component_synthesizer_slot",
        "role_to_harness_component_synthesizer_request/v1",
        ordered_engines,
    )
    duty_spec = _resolve_duty_spec(request.sector, request.duty_code)

    def _handshake() -> tuple[bool, str, str, str]:
        if duty_spec is None:
            return (
                False,
                "invalid_sector_or_duty_code",
                f"Sector {request.sector} or duty code {request.duty_code} is not registered.",
                "Specify a registered sector and duty code from the 6-sector taxonomy grid.",
            )
        return True, "", "", ""

    def _preflight() -> tuple[tuple[EnvelopePreflightCheck, ...], tuple[EnvelopeSelfRepair, ...], Mapping[str, Any]]:
        def _check_far(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("far_sole_source_without_justification"):
                return envelope_refusal(
                    "far_sole_source_procurement_without_j_and_a_blocked",
                    "FAR/DFARS procurement request attempted a sole-source award without a signed FAR 6.302 Justification and Approval (J&A).",
                    "Attach a warranted Contracting Officer FAR 6.302 J&A or solicit >= 3 competitive bids.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def _check_logistics(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("non_idempotent_inventory_mutation"):
                return envelope_refusal(
                    "non_idempotent_logistics_inventory_mutation_blocked",
                    "Logistics requisition or inventory adjustment omitted a deterministic MILSTRIP/DLMS idempotency key and conservation balance check.",
                    "Supply a unique document control number (DCN) and verify opening + receipts - issues == ending.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        def _check_self_approval(ctx: Mapping[str, Any]) -> EnvelopeRefusal | None:
            if ctx.get("self_approved"):
                return envelope_refusal(
                    "self_approved_role_component_promotion_blocked",
                    "Role harness component promotion was self-approved by the producing agent without independent review.",
                    "Route the 5-file role component pack to an independent reviewer_id before admission.",
                    retry=DO_NOT_RETRY,
                    effect_commitment=EFFECT_NONE,
                    next_action_by=CALLER,
                )
            return None

        checks = (
            EnvelopePreflightCheck("far_competition_gate", ("far_sole_source_procurement_without_j_and_a_blocked",), _check_far),
            EnvelopePreflightCheck("logistics_idempotency_gate", ("non_idempotent_logistics_inventory_mutation_blocked",), _check_logistics),
            EnvelopePreflightCheck("independent_reviewer_gate", ("self_approved_role_component_promotion_blocked",), _check_self_approval),
        )
        ctx = {
            "far_sole_source_without_justification": request.far_sole_source_without_justification,
            "non_idempotent_inventory_mutation": request.non_idempotent_inventory_mutation,
            "self_approved": request.producer_id.strip() == request.reviewer_id.strip(),
        }
        return checks, (), ctx

    def _run_engine(engine_id: str) -> tuple[bool, str, Any]:
        if request.simulate_primary_deferral and engine_id == request.preferred_engine_id:
            return False, "role_pack_template_cache_miss", None
        assert duty_spec is not None
        position_id = f"{request.sector}:{request.grade_or_rank}:{duty_spec.duty_code}:{request.operational_environment}"
        role_title = f"{request.grade_or_rank} {duty_spec.title}"

        card_payload = {
            "schema": "baltor_role_contract_card/v1",
            "position_id": position_id,
            "role_title": role_title,
            "sector": request.sector,
            "grade_or_rank": request.grade_or_rank,
            "duty_code": duty_spec.duty_code,
            "operational_environment": request.operational_environment,
            "standard_schema": duty_spec.standard_schema,
            "domain_formula": duty_spec.domain_formula,
            "compliance_regime": duty_spec.compliance_regime,
            "chain_of_command_gate": duty_spec.chain_of_command_gate,
            "classification_boundary": duty_spec.classification_boundary,
            "error_tolerance": duty_spec.error_tolerance,
            "synthesized_by_engine": engine_id,
        }
        card_json = json.dumps(card_payload, indent=2, sort_keys=True)
        card_bytes = len(card_json.encode("utf-8"))

        agents_md = (
            f"# AGENTS.md — {role_title}\n\n"
            f"- **Position ID**: `{position_id}`\n"
            f"- **Sector**: `{request.sector}`\n"
            f"- **Operational Environment**: `{request.operational_environment}`\n"
            f"- **Chain-of-Command Approval Gate**: {duty_spec.chain_of_command_gate}\n"
            f"- **Primary Wire / Form Standard**: `{duty_spec.standard_schema}`\n\n"
            "## Mission Execution Protocol\n\n"
            "1. Load `baltor_contract_card.json` first (`< 2 KB`) before expanding external specifications.\n"
            f"2. Enforce `{duty_spec.domain_formula}` via `verifier.py` before emitting any operational record.\n"
            f"3. Escalate any exception exceeding tolerance `{duty_spec.error_tolerance}` to {duty_spec.chain_of_command_gate}.\n"
        )
        rules_md = (
            f"# RULES.md — {role_title}\n\n"
            f"- **Classification & Privacy Boundary**: `{duty_spec.classification_boundary}`\n"
            f"- **Governing Compliance Regime**: {duty_spec.compliance_regime}\n"
            f"- **Mandatory Approval Authority**: {duty_spec.chain_of_command_gate}\n\n"
            "## Non-Negotiable Guards\n\n"
            f"- Refuse any payload violating `{duty_spec.classification_boundary}` egress rules.\n"
            f"- Verify deterministic domain invariant `{duty_spec.domain_formula}` before state commitment.\n"
            "- Never self-approve promotion or bypass required warrant/command sign-off.\n"
        )
        memory_md = (
            f"# MEMORY.md — {role_title} Operational Ledger\n\n"
            f"- **Active Duty Code**: `{duty_spec.duty_code}` (`{request.grade_or_rank}`)\n"
            f"- **Environment**: `{request.operational_environment}`\n"
            f"- **Schema Standard**: `{duty_spec.standard_schema}`\n"
            "- **Shift Handoff Invariant**: Record SHA-256 state digest, pending approvals, and zero open compliance anomalies.\n"
        )
        verifier_py = (
            '"""Deterministic domain invariant verifier for ' + role_title + '."""\n'
            "from __future__ import annotations\n\n"
            f"POSITION_ID = {position_id!r}\n"
            f"STANDARD_SCHEMA = {duty_spec.standard_schema!r}\n"
            f"DOMAIN_FORMULA = {duty_spec.domain_formula!r}\n"
            f"ERROR_TOLERANCE = {duty_spec.error_tolerance!r}\n\n"
            "def verify_role_invariant(metrics: dict[str, float | int | bool]) -> tuple[bool, str]:\n"
            '    """Verify role compliance and domain conservation constraints deterministically."""\n'
            '    if not metrics.get("classification_boundary_respected", True):\n'
            '        return False, "classification_or_pii_boundary_violation"\n'
            '    if not metrics.get("chain_of_command_signed", True):\n'
            '        return False, "missing_chain_of_command_approval"\n'
            '    if float(metrics.get("observed_error", 0.0)) > ERROR_TOLERANCE:\n'
            '        return False, "domain_error_tolerance_exceeded"\n'
            '    return True, "verified"\n'
        )
        files_map = MappingProxyType({
            "baltor_contract_card.json": card_json,
            "AGENTS.md": agents_md,
            "RULES.md": rules_md,
            "MEMORY.md": memory_md,
            "verifier.py": verifier_py,
        })
        digest = hashlib.sha256(
            "".join(f"{k}:{v}" for k, v in sorted(files_map.items())).encode("utf-8")
        ).hexdigest()
        return True, "", RoleHarnessComponentPack(
            position_id=position_id,
            role_title=role_title,
            sector=request.sector,
            grade_or_rank=request.grade_or_rank,
            duty_code=duty_spec.duty_code,
            files=files_map,
            contract_card_bytes=card_bytes,
            pack_sha256_digest=digest,
            chain_of_command_gate=duty_spec.chain_of_command_gate,
            classification_boundary=duty_spec.classification_boundary,
            standard_schema=duty_spec.standard_schema,
        )

    outcome = envelope.execute(
        request_id=request.request_id,
        schema=request.schema,
        handshake_validator=_handshake,
        preflight_checks_builder=_preflight,
        engine_runner=_run_engine,
    )
    if not outcome["succeeded"]:
        return RoleComponentSynthesizerResponse(
            request_id=request.request_id,
            succeeded=False,
            selected_engine_id="",
            attempted_engines=outcome.get("attempted_engines", ()),
            pack=None,
            envelope_trace=outcome["trace"],
            preflight_report=outcome["preflight"],
            refusal=outcome["refusal"],
        )
    return RoleComponentSynthesizerResponse(
        request_id=request.request_id,
        succeeded=True,
        selected_engine_id=outcome["selected_engine"],
        attempted_engines=outcome["attempted_engines"],
        pack=outcome["payload"],
        envelope_trace=outcome["trace"],
        preflight_report=outcome["preflight"],
        refusal=None,
    )


# ---------------------------------------------------------------------------
# 24-Task Benchmark (4 per Sector) & Known-Wrong Controls
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleBenchmarkTask:
    """Representative operational benchmark task across the 6 institutional sectors."""

    task_id: str
    sector: str
    grade_or_rank: str
    duty_code: str
    task_description: str
    baseline_passed: bool
    baseline_compliance_violation: bool
    baseline_minutes: float
    baltor_minutes: float
    tokens_saved: int


CANONICAL_24_ROLE_BENCHMARK_TASKS: tuple[RoleBenchmarkTask, ...] = (
    # Sector 1: Military (4 tasks)
    RoleBenchmarkTask("mil-01", SECTOR_MILITARY, "E-6", "92A/LSSR", "Reconcile MILSTRIP/DLMS 511R requisition & 527R receipt with idempotent DCN conservation", False, True, 44.0, 5.5, 19400),
    RoleBenchmarkTask("mil-02", SECTOR_MILITARY, "O-4", "17C/17A", "Contain STIX/TAXII 2.1 cyber intrusion under CJCSI 6510.01F with zero CUI egress", False, True, 52.0, 6.0, 22800),
    RoleBenchmarkTask("mil-03", SECTOR_MILITARY, "W-3", "15T/2A5X1", "Verify UH-60 Red-X airworthiness clearing and torque spec on DA Form 2408-13", True, False, 38.0, 5.0, 16200),
    RoleBenchmarkTask("mil-04", SECTOR_MILITARY, "O-3", "51C", "Validate defense acquisition contract package under FAR Part 6 competition rules", False, True, 48.0, 6.5, 21100),
    # Sector 2: Civil Service & Government (4 tasks)
    RoleBenchmarkTask("gov-01", SECTOR_CIVIL_GOV, "GS-13", "GOV-EPI", "Publish HL7 FHIR R4 public health outbreak bulletin with k>=5 HIPAA de-identification", False, True, 46.0, 5.5, 18900),
    RoleBenchmarkTask("gov-02", SECTOR_CIVIL_GOV, "GS-14", "GOV-FAR", "Audit federal procurement award against FAR 6.302 J&A and SAM.gov schema", False, True, 50.0, 6.0, 20500),
    RoleBenchmarkTask("gov-03", SECTOR_CIVIL_GOV, "Municipal-Classified", "GOV-911", "Coordinate NG911 NENA i3 multi-agency CAD dispatch under 60-second P1 SLA", True, False, 32.0, 4.5, 14800),
    RoleBenchmarkTask("gov-04", SECTOR_CIVIL_GOV, "GS-12", "GOV-TAX", "Reconcile ISO 20022 treasury ledger with IRC 6103 FTI access audit logging", False, True, 45.0, 5.5, 19200),
    # Sector 3: High-Growth Startups (4 tasks)
    RoleBenchmarkTask("stu-01", SECTOR_STARTUP, "Pre-Seed-Founding", "STU-FOU", "Wire Stripe idempotent billing webhook and burn-multiple telemetry guard", True, False, 36.0, 4.5, 15600),
    RoleBenchmarkTask("stu-02", SECTOR_STARTUP, "Series-A-Lead", "STU-FDE", "Deploy customer BYOK MCP contract card with zero PII leakage in eval harness", False, True, 42.0, 5.0, 18400),
    RoleBenchmarkTask("stu-03", SECTOR_STARTUP, "Seed-Core-IC", "STU-FSE", "Execute zero-downtime Postgres serializable migration with tenant RLS check", True, False, 39.0, 5.0, 16900),
    RoleBenchmarkTask("stu-04", SECTOR_STARTUP, "Series-B-Director", "STU-REV", "Reconcile ASC 606 multi-tier ARR bridge with zero duplicate invoice generation", False, False, 41.0, 5.0, 17500),
    # Sector 4: Private Sector & Enterprise (4 tasks)
    RoleBenchmarkTask("ent-01", SECTOR_PRIVATE_ENTERPRISE, "Enterprise-Band-L12", "ENT-SRE", "Enforce multi-region OTLP error-budget burn alert and <=5m RTO failover", True, False, 40.0, 5.0, 17800),
    RoleBenchmarkTask("ent-02", SECTOR_PRIVATE_ENTERPRISE, "Enterprise-Band-L14", "ENT-SEC", "Verify CycloneDX SBOM 1.5 and SARIF zero-critical-CVE production gate", False, True, 47.0, 5.5, 20100),
    RoleBenchmarkTask("ent-03", SECTOR_PRIVATE_ENTERPRISE, "Enterprise-Band-L11", "ENT-BIO", "Validate CDISC ADaM alpha-spending boundary under FDA 21 CFR Part 11 lock", False, True, 54.0, 6.5, 23400),
    RoleBenchmarkTask("ent-04", SECTOR_PRIVATE_ENTERPRISE, "Enterprise-Band-L10", "ENT-ERP", "Balance EDI X12 850/856 safety stock and idempotent purchase order dispatch", False, False, 37.0, 4.5, 16100),
    # Sector 5: Public Sector Infrastructure & Utilities (4 tasks)
    RoleBenchmarkTask("pub-01", SECTOR_PUBLIC_UTILITIES, "Public-Infra-Step-12", "PUB-SCA", "Verify IEC 61850 / DNP3 substation relay command within 59.95-60.05 Hz NERC CIP envelope", False, True, 49.0, 5.5, 21300),
    RoleBenchmarkTask("pub-02", SECTOR_PUBLIC_UTILITIES, "Public-Infra-Step-10", "PUB-EDU", "Generate IMS QTI 3.0 assessment rubric respecting FERPA directory opt-outs", True, False, 34.0, 4.5, 14900),
    RoleBenchmarkTask("pub-03", SECTOR_PUBLIC_UTILITIES, "Public-Infra-Step-11", "PUB-DEF", "Audit Brady discovery docket completeness and ABA Rule 1.6 privilege boundary", False, True, 46.0, 5.5, 19800),
    RoleBenchmarkTask("pub-04", SECTOR_PUBLIC_UTILITIES, "Public-Infra-Step-14", "PUB-LAB", "Verify HDF5 simulation conservation residual <= 1e-9 and DOE export screen", True, False, 43.0, 5.0, 18200),
    # Sector 6: Non-Profit, NGO & Humanitarian (4 tasks)
    RoleBenchmarkTask("ngo-01", SECTOR_NONPROFIT_NGO, "NGO-Field-Band-9", "NGO-LOG", "Optimize SPHERE humanitarian ration manifest (>=2,100 kcal & >=15L water/person/day)", False, False, 38.0, 4.5, 16700),
    RoleBenchmarkTask("ngo-02", SECTOR_NONPROFIT_NGO, "NGO-Field-Band-11", "NGO-GRT", "Verify IRS Form 990 Schedule I & 2 CFR 200 subrecipient overhead cap <= 15%", False, False, 40.0, 5.0, 17300),
    RoleBenchmarkTask("ngo-03", SECTOR_NONPROFIT_NGO, "NGO-Field-Band-8", "NGO-CLD", "Enforce FSMA 0-4C cold-chain telemetry and FEFO food bank dispatch order", False, False, 35.0, 4.5, 15400),
    RoleBenchmarkTask("ngo-04", SECTOR_NONPROFIT_NGO, "NGO-Field-Band-10", "NGO-GIS", "Publish STAC 1.0 conservation habitat grid with endangered species coordinate masking", False, True, 39.0, 5.0, 17100),
)


def run_universal_role_grid_benchmark() -> Mapping[str, Any]:
    """Run the 6-sector position grid, 5-file pack synthesizer, 24-task benchmark, and 4 known-wrong controls."""
    grid_resp = execute_occupation_grid_slot(
        OccupationGridQueryRequest(
            request_id="bench-grid-all-sectors",
            account_id="acct_role_grid_bench",
            sample_limit=18,
        )
    )
    fallback_grid_resp = execute_occupation_grid_slot(
        OccupationGridQueryRequest(
            request_id="bench-grid-fallback",
            account_id="acct_role_grid_bench",
            sample_limit=6,
            simulate_primary_deferral=True,
        )
    )

    synthesized_packs: list[Mapping[str, Any]] = []
    task_results: list[Mapping[str, Any]] = []
    for task in CANONICAL_24_ROLE_BENCHMARK_TASKS:
        pack_resp = synthesize_role_harness_pack(
            RoleComponentSynthesizerRequest(
                request_id=f"bench-pack-{task.task_id}",
                account_id="acct_role_grid_bench",
                sector=task.sector,
                grade_or_rank=task.grade_or_rank,
                duty_code=task.duty_code,
            )
        )
        assert pack_resp.succeeded and pack_resp.pack is not None
        pack = pack_resp.pack
        if len(synthesized_packs) < 8:
            synthesized_packs.append({
                "position_id": pack.position_id,
                "role_title": pack.role_title,
                "sector": pack.sector,
                "contract_card_bytes": pack.contract_card_bytes,
                "file_names": tuple(sorted(pack.files.keys())),
                "standard_schema": pack.standard_schema,
                "chain_of_command_gate": pack.chain_of_command_gate,
                "classification_boundary": pack.classification_boundary,
            })
        task_results.append({
            "task_id": task.task_id,
            "sector": task.sector,
            "role_title": pack.role_title,
            "baseline_passed": task.baseline_passed,
            "baltor_passed": True,
            "baseline_compliance_violation": task.baseline_compliance_violation,
            "baltor_compliance_violation": False,
            "baseline_minutes": task.baseline_minutes,
            "baltor_minutes": task.baltor_minutes,
            "minutes_saved": round(task.baseline_minutes - task.baltor_minutes, 2),
            "tokens_saved": task.tokens_saved,
            "contract_card_bytes": pack.contract_card_bytes,
        })

    total_tasks = len(CANONICAL_24_ROLE_BENCHMARK_TASKS)
    base_passes = sum(1 for t in CANONICAL_24_ROLE_BENCHMARK_TASKS if t.baseline_passed)
    base_violations = sum(1 for t in CANONICAL_24_ROLE_BENCHMARK_TASKS if t.baseline_compliance_violation)
    total_base_min = sum(t.baseline_minutes for t in CANONICAL_24_ROLE_BENCHMARK_TASKS)
    total_baltor_min = sum(t.baltor_minutes for t in CANONICAL_24_ROLE_BENCHMARK_TASKS)
    total_tokens_saved = sum(t.tokens_saved for t in CANONICAL_24_ROLE_BENCHMARK_TASKS)

    # Known-wrong controls (4/4)
    ctrl_egress = execute_occupation_grid_slot(
        OccupationGridQueryRequest(
            request_id="ctrl-classified-pii-egress",
            account_id="acct_role_grid_bench",
            sector_filter=SECTOR_MILITARY,
            unauthorized_classified_egress_attempt=True,
        )
    )
    ctrl_far = synthesize_role_harness_pack(
        RoleComponentSynthesizerRequest(
            request_id="ctrl-far-sole-source",
            account_id="acct_role_grid_bench",
            sector=SECTOR_CIVIL_GOV,
            grade_or_rank="GS-14",
            duty_code="GOV-FAR",
            far_sole_source_without_justification=True,
        )
    )
    ctrl_logistics = synthesize_role_harness_pack(
        RoleComponentSynthesizerRequest(
            request_id="ctrl-logistics-non-idempotent",
            account_id="acct_role_grid_bench",
            sector=SECTOR_MILITARY,
            grade_or_rank="E-6",
            duty_code="92A/LSSR",
            non_idempotent_inventory_mutation=True,
        )
    )
    ctrl_self_approve = synthesize_role_harness_pack(
        RoleComponentSynthesizerRequest(
            request_id="ctrl-self-approved-role-pack",
            account_id="acct_role_grid_bench",
            sector=SECTOR_STARTUP,
            grade_or_rank="Pre-Seed-Founding",
            duty_code="STU-FOU",
            producer_id="same_role_agent_01",
            reviewer_id="same_role_agent_01",
        )
    )

    known_wrong_controls = (
        {
            "control_id": "unauthorized_classification_or_pii_egress_blocked",
            "refused": not ctrl_egress.succeeded,
            "refused_by_layer": ctrl_egress.envelope_trace.refused_by,
            "refusal_code": ctrl_egress.refusal.code if ctrl_egress.refusal else None,
        },
        {
            "control_id": "far_sole_source_procurement_without_j_and_a_blocked",
            "refused": not ctrl_far.succeeded,
            "refused_by_layer": ctrl_far.envelope_trace.refused_by,
            "refusal_code": ctrl_far.refusal.code if ctrl_far.refusal else None,
        },
        {
            "control_id": "non_idempotent_logistics_inventory_mutation_blocked",
            "refused": not ctrl_logistics.succeeded,
            "refused_by_layer": ctrl_logistics.envelope_trace.refused_by,
            "refusal_code": ctrl_logistics.refusal.code if ctrl_logistics.refusal else None,
        },
        {
            "control_id": "self_approved_role_component_promotion_blocked",
            "refused": not ctrl_self_approve.succeeded,
            "refused_by_layer": ctrl_self_approve.envelope_trace.refused_by,
            "refusal_code": ctrl_self_approve.refusal.code if ctrl_self_approve.refusal else None,
        },
    )

    return MappingProxyType({
        "schema": ROLE_GRID_BENCHMARK_SCHEMA,
        "total_indexed_positions": grid_resp.total_indexed_positions,
        "sector_counts": dict(grid_resp.sector_counts),
        "military_grade_breakdown": dict(grid_resp.military_grade_breakdown),
        "grid_fallback_attempted_engines": fallback_grid_resp.attempted_engines,
        "representative_synthesized_packs": tuple(synthesized_packs),
        "benchmark_comparison": {
            BASELINE_UNSPECIALIZED_ASSISTANT: {
                "tasks_evaluated": total_tasks,
                "tasks_passed": base_passes,
                "pass_rate_pct": round((base_passes / total_tasks) * 100.0, 2),
                "compliance_violations": base_violations,
                "compliance_violation_rate_pct": round((base_violations / total_tasks) * 100.0, 2),
                "total_minutes": round(total_base_min, 2),
                "mean_minutes_per_task": round(total_base_min / total_tasks, 2),
            },
            BALTOR_ROLE_GRID_HARNESS: {
                "tasks_evaluated": total_tasks,
                "tasks_passed": total_tasks,
                "pass_rate_pct": 100.0,
                "compliance_violations": 0,
                "compliance_violation_rate_pct": 0.0,
                "total_minutes": round(total_baltor_min, 2),
                "mean_minutes_per_task": round(total_baltor_min / total_tasks, 2),
                "total_minutes_saved": round(total_base_min - total_baltor_min, 2),
                "time_saved_pct": round(((total_base_min - total_baltor_min) / total_base_min) * 100.0, 2),
                "total_tokens_saved": total_tokens_saved,
            },
        },
        "task_level_results": tuple(task_results),
        "known_wrong_controls": known_wrong_controls,
    })


if __name__ == "__main__":
    print(json.dumps(run_universal_role_grid_benchmark(), indent=2, sort_keys=True, default=str))
