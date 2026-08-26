"""Installed utility examples for users who do not have a repository checkout.

Architectural role: Code Node system. These examples run real Loop Engine
paths and are also used by the source-tree walkthroughs.
"""

from __future__ import annotations


SUPPORT_TICKETS = (
    {"id": "SUP-1042", "severity": "high", "minutes_open": 95,
     "customers_blocked": 12, "summary": "Warehouse labels will not print"},
    {"id": "SUP-1043", "severity": "medium", "minutes_open": 180,
     "customers_blocked": 1, "summary": "Monthly export is missing a column"},
    {"id": "SUP-1044", "severity": "critical", "minutes_open": 20,
     "customers_blocked": 4, "summary": "Checkout rejects valid cards"},
)

SEVERITY_POINTS = {"low": 0, "medium": 20, "high": 50, "critical": 100}


def prioritize_support_queue(tickets=SUPPORT_TICKETS) -> list:
    """Order support work by severity, wait time, and customer impact."""
    ranked = []
    for ticket in tickets:
        score = (SEVERITY_POINTS[ticket["severity"]]
                 + min(ticket["minutes_open"] // 15, 20)
                 + ticket["customers_blocked"] * 3)
        ranked.append({**ticket, "priority_score": score})
    return sorted(ranked, key=lambda row: (-row["priority_score"], row["id"]))


def support_queue_example() -> str:
    from ..loop.recursive_loop import LoopLedger
    from ..loop.encapsulate import as_practitioner_loop
    from .loop_report import report_from_ledger, render_text
    ledger = LoopLedger()
    result = as_practitioner_loop(
        "prioritize the customer support queue",
        lambda: prioritize_support_queue(), ledger=ledger)
    lines = ["NEXT SUPPORT WORK"]
    for position, ticket in enumerate(result["value"], start=1):
        lines.append(
            f"{position}. {ticket['id']}  score={ticket['priority_score']:>3}  "
            f"{ticket['summary']}")
    lines.extend(("", f"model calls: {result['model_calls']}",
                  f"logged events: {len(ledger.events)}", "",
                  render_text(report_from_ledger(
                      ledger.events, run_id="support-queue-priority"))))
    return "\n".join(lines)


def intelligence_layers_example() -> str:
    from ..core.intelligence_layers import (
        build_intelligence_catalog, catalog_summary)
    active_catalog = build_intelligence_catalog()
    review_catalog = build_intelligence_catalog(include_candidates=True)
    summary = catalog_summary(active_catalog)
    lines = ["FOUR INTELLIGENCE LAYERS"]
    for layer in summary["layers"]:
        groups = ", ".join(f"{name}={count}" for name, count
                           in layer["category_groups"].items()) or "none"
        lines.append(f"{layer['public_label']:<38} {layer['items']:>4}  {groups}")
    candidate_context = (len(review_catalog["context_intelligence"])
                         - len(active_catalog["context_intelligence"]))
    lines.extend(("", f"Context candidates available for review: "
                  f"{candidate_context}",
                  "Candidates are excluded from normal retrieval.",
                  "Runtime Memory is separate and run-scoped."))
    return "\n".join(lines)


def context_seed_example() -> str:
    from .context_seed import ContextSeedSpec, run_context_seed
    spec = ContextSeedSpec(
        domain="space", subdomain="earth observation",
        project_types=("earth observation mission",),
        task_types=("mission risk review",),
        job_roles=("orbital mechanics engineer", "mission operations lead",
                   "space policy researcher"),
        source_policy="official_first", max_candidates=24)
    result = run_context_seed(spec)
    styles = sorted({record.body["classification"]["context_hierarchy"]
                     ["thinking_style"] for record in result.candidates})
    return "\n".join((
        "SPACE CONTEXT SEED",
        f"candidate records: {len(result.candidates)}",
        f"job roles: {len(spec.job_roles)}",
        f"thinking styles: {', '.join(styles)}",
        f"research questions: {len(result.research_questions)}",
        f"model calls: {result.loop_result.model_calls}",
        "installed: no",
        "promoted: no",
    ))


EXAMPLES = {"support-queue": support_queue_example,
            "intelligence-layers": intelligence_layers_example,
            "context-seed": context_seed_example}


def run_example(name: str) -> str:
    try:
        return EXAMPLES[name]()
    except KeyError as exc:
        raise ValueError(f"unknown example {name!r}; choose {sorted(EXAMPLES)}") \
            from exc


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    ranked = prioritize_support_queue()
    check("support_queue_orders_real_shaped_work",
          ranked[0]["id"] == "SUP-1044"
          and ranked[-1]["id"] == "SUP-1043")
    support = support_queue_example()
    check("installed_support_example_runs_as_a_loop",
          "SUP-1044" in support and "0 model calls" in support
          and "LOOP REPORT" in support)
    layers = intelligence_layers_example()
    check("installed_intelligence_example_shows_four_layers",
          all(label in layers for label in (
              "Context Intelligence", "Code Intelligence",
              "Runtime History and Solution Intelligence", "User Feedback Intelligence")))
    seed = context_seed_example()
    check("installed_context_seed_uses_the_self_improvement_boundary",
          "candidate records: 24" in seed and "model calls: 0" in seed
          and "installed: no" in seed and "promoted: no" in seed)
    refused = False
    try:
        run_example("missing-example")
    except ValueError:
        refused = True
    check("unknown_or_toy_example_name_is_refused", refused)
    passed = sum(1 for result in results if result["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
