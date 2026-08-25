"""Architecture map — the four top-level abstractions as the one projection authority.

Every module in this package belongs to exactly one of the four frozen
abstractions (loop | strings | code_nodes | static_architecture) or is package
plumbing at the root.  This map IS the folder shape: the mover consulted it,
`--map` prints it, `step_registry` resolves module paths through it, and the
self-test refuses any module on disk that is not classified here — so the
projection can never silently drift from the code.
"""
from __future__ import annotations

import os

# The package has one public import root.
PACKAGE = __package__ or "loop_engine"

#: the four frozen top-level abstractions (never a fifth)
SUBPACKAGES = ("loop", "strings", "code_nodes", "static_architecture")

#: package plumbing that stays at the root
ROOT_MODULES = ("__init__", "__main__", "_self_test", "_conformance_test",
                "_conformance_scan", "architecture_map", "conformance_report")

#: module -> subpackage.  "steps" and "regimes" are subpackages riding in loop/.
MODULE_MAP = {
    "loop": (
        "acceptance", "arbiter", "builtin_resolvers",
        "canvas", "context_shuffle", "decision_engine",
        "decision_slates", "escalation_governor", "hybrid_dimension_lattice",
        "research_to_capability", "list_intelligence",
        "decision_envelope", "decision_episode", "decision_need",
        "delegation", "deliberation", "kernel",
        "kernel_model_impls", "lens", "loop",
        "loop_handlers", "loop_templates", "methodical", "moves",
        "intelligence_loops", "practitioner_campaign", "practitioner_loop", "practitioner_methods", "receipts",
        "effective_spec", "encapsulate", "loop_capsule", "loop_contract", "loop_doctrine", "recursive_loop", "regimes", "registry",
        "resolvers", "route_bridge", "runner",
        "solve", "solver", "step_registry",
        "steps", "studio", "sub_practitioner",
        "tuning", "wiring",
    ),
    "strings": (
        "ask_strategies", "bias_checklist", "biases",
        "context", "decision_schemas", "domain_pack",
        "frame", "intelligence_strings", "interrogation",
        "knowledge", "knowledge_state", "notes",
        "output_templates", "packs", "prompt_fragments",
        "question_bank", "question_engine", "solution_shaping",
        "task_blueprint",
    ),
    "code_nodes": (
        "blueprint", "capture", "closure",
        "competition_solver", "enrichment", "failure_response",
        "follow_up", "housekeeping", "kaggle_executor", "live_run_demo",
        "learning_bundle", "guided_setup", "logic_ast", "universal_solve", "loop_report", "measurement",
        "pack_curation", "planning", "review_mode",
        "change_proposals", "foundry_probes", "guidance_ledger",
        "rl_vocabulary", "run_analytics",
        "run_playback", "run_quality",
        "runtime_contracts", "self_improve", "smoke_ladder",
        "solution_canvas", "solution_compiler", "solution_graph", "solution_records", "string_foundry",
    ),
    "static_architecture": (
        "asset_class", "asset_lifecycle", "capability_directory",
        "chronicle", "config", "event_vocabulary", "duckdb_catalog", "facets", "intelligence_layers",
        "runtime_memory", "user_intelligence",
        "intelligence_registry",
        "model_call",
        "model_routes", "ollama_client", "ollama_resolvers",
        "mistral_client", "openrouter_client", "provider_failover",
        "model_discovery", "autoconfigure", "custom_endpoint", "knowledge_loader",
        "opencode_client", "operating_profile", "persistence",
        "reasoning_call", "retrieval", "solution_library",
        "store_serve",
        "boundary_registry", "saas_routes",
        "studio_server",
    ),
}

_FLAT = {m: s for s, mods in MODULE_MAP.items() for m in mods}


def subpackage_of(module: str) -> str:
    """Which of the four abstractions owns this module ("" for root plumbing)."""
    if module in ROOT_MODULES:
        return ""
    return _FLAT[module]


def module_path(module: str) -> str:
    """Full import path for a bare module name, via the map."""
    sub = subpackage_of(module)
    return f"{PACKAGE}.{sub}.{module}" if sub else f"{PACKAGE}.{module}"


def render_map() -> str:
    out = ["ARCHITECTURE MAP — four top-level abstractions"]
    for s in SUBPACKAGES:
        mods = MODULE_MAP[s]
        out.append(f"  {s}/  ({len(mods)} modules)")
        out.append("    " + ", ".join(mods))
    return "\n".join(out)


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    here = os.path.dirname(__file__)
    # 1. every .py on disk is classified (root or one abstraction) — anti-drift.
    on_disk = sorted(f[:-3] for f in os.listdir(here) if f.endswith(".py"))
    stray = [m for m in on_disk if m not in ROOT_MODULES]
    check("no_unclassified_module_at_package_root", not stray,
          f"root may hold only plumbing; found: {stray}")
    for s in SUBPACKAGES:
        files = sorted(f[:-3] for f in os.listdir(os.path.join(here, s))
                       if f.endswith(".py") and f != "__init__.py")
        unmapped = [m for m in files if m not in _FLAT or _FLAT[m] != s]
        check(f"every_module_in_{s}_is_mapped_there", not unmapped,
              f"unmapped/misfiled: {unmapped}")
    # 2. every mapped module exists on disk where the map says.
    missing = []
    for m, s in _FLAT.items():
        target = os.path.join(here, s, m)
        if not (os.path.exists(target + ".py") or os.path.isdir(target)):
            missing.append(f"{s}/{m}")
    check("every_mapped_module_exists_on_disk", not missing, str(missing))
    # 3. exactly four abstractions, frozen.
    check("exactly_four_top_level_abstractions",
          tuple(MODULE_MAP) == SUBPACKAGES, "never a fifth")
    return {"tests": results}
