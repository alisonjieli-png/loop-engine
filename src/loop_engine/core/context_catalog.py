"""Build the active and candidate Context Intelligence populations.

Architectural role: internal catalog for Intelligence Search and Retrieval.

Owns: projecting the packaged question, method, lens, policy, template, and
guidance registries into one Context catalog. Candidate packs are opt-in.

Does not own: four-layer classification, retrieval, source approval, or
promotion.

Verification: ``self_test()`` checks active and review populations and tiers.
"""
from __future__ import annotations


def build_context_records(*, include_candidates: bool = False) -> list:
    from .store_serve import StoreRecord
    from .facets import ContextFacetSpec, context_facets
    from ..code_nodes.string_foundry import (load_seed_pack,
                                              seed_pack_store_records,
                                              load_candidate_bank)
    records = []
    if include_candidates:
        records.extend(seed_pack_store_records(load_seed_pack()["records"]))
        records.extend(load_candidate_bank())
    record_ids = {record.record_id for record in records}

    def add(record):
        if record.record_id not in record_ids:
            records.append(record)
            record_ids.add(record.record_id)

    from ..loop.loop_templates import template_records
    for record in template_records():
        add(record)

    from ..strings.solution_shaping import solution_shaping_pack
    from ..code_nodes.measurement import measurement_pack
    for bank, category in ((solution_shaping_pack(), "solution_shaping"),
                           (measurement_pack(), "measurement")):
        for item in getattr(bank, "_by_id", {}).values():
            base = item.envelope()
            body = dict(base.body or {})
            body["facets"] = context_facets(ContextFacetSpec(
                category=category, subcategory=item.kind,
                scope="package", lifecycle=item.maturity,
                provenance=item.provenance))
            add(StoreRecord(base.record_id, base.kind, base.title,
                            body=body, tags=base.tags, tier=base.tier,
                            source=category))

    from ..strings.interrogation import interrogation_bank
    seen_interrogation_ids: dict[str, int] = {}
    for item in interrogation_bank():
        slug = f"{item.category}.{item.subcategory}" if item.subcategory \
            else item.category
        occurrence = seen_interrogation_ids.get(slug, 0)
        seen_interrogation_ids[slug] = occurrence + 1
        record_id = f"interrogation.{slug}" if not occurrence \
            else f"interrogation.{slug}.{occurrence}"
        add(StoreRecord(
            record_id, "question", str(item.question),
            body={"role": "question", "maturity": "registered",
                  "how_to_answer": item.how_to_answer,
                  "answerable_by": item.answerable_by,
                  "facets": context_facets(ContextFacetSpec(
                      category="interrogation",
                      subcategory=item.subcategory or item.category,
                      context_type="question", scope="package",
                      lifecycle="registered", provenance="interrogation_bank"))},
            tags=("interrogation", item.category, item.subcategory),
            source="interrogation"))

    from ..code_nodes.guidance_ledger import BOOTSTRAP_GUIDANCE
    for item in BOOTSTRAP_GUIDANCE:
        add(StoreRecord(
            f"guidance.{item['key']}", "context", item["text"],
            body={"role": "instruction", "maturity": "registered",
                  "facets": context_facets(ContextFacetSpec(
                      category="guidance", subcategory=item.get("kind", ""),
                      context_type="instruction", scope="package",
                      lifecycle="registered", provenance="guidance_ledger"))},
            tags=("guidance", item.get("kind", "instruction")),
            source="guidance_ledger"))

    from ..code_nodes.string_foundry import improvement_seed_records
    for record in improvement_seed_records():
        add(record)

    from ..strings.question_engine import core_forms, as_store_records
    from ..strings.output_templates import template_records as output_records
    from ..strings.decision_schemas import schema_records
    from ..strings.interrogation import preset_records
    for record in (as_store_records(core_forms()) + output_records()
                   + schema_records() + preset_records()):
        add(record)

    from ..loop.lens import ROLE_LENSES, METHOD_LENSES
    for short_name, lens in {**ROLE_LENSES, **METHOD_LENSES}.items():
        thinking = short_name if lens.kind == "method" else ""
        add(StoreRecord(
            lens.id, "persona" if lens.kind == "role" else "context",
            f"{lens.kind.title()} lens: {short_name.replace('_', ' ')}",
            body={"role": f"{lens.kind}_lens", "maturity": "registered",
                  "focus": list(lens.focus),
                  "default_questions": list(lens.default_questions),
                  "facets": context_facets(ContextFacetSpec(
                      category="role_lens" if lens.kind == "role"
                      else "thinking_method",
                      subcategory=short_name, context_type="persona"
                      if lens.kind == "role" else "method",
                      job_position=short_name if lens.kind == "role" else "",
                      thinking_style=thinking, scope="package",
                      lifecycle="registered", provenance="lens_registry"))},
            tags=("lens", lens.kind, short_name), source="lens_registry"))

    from ..strings.context import CONTEXT_POLICIES
    for name, policy in CONTEXT_POLICIES.items():
        add(StoreRecord(
            f"context_policy.{name}", "context",
            f"Context policy: {name.replace('_', ' ')}",
            body={"role": "context_policy", "policy": dict(policy),
                  "maturity": "registered",
                  "facets": context_facets(ContextFacetSpec(
                      category="context_policy", subcategory=name,
                      context_type="instruction", scope="package",
                      lifecycle="registered",
                      provenance="context_policy_registry"))},
            tags=("context_policy", name), source="context_policy_registry"))

    from ..strings.ask_strategies import core_strategies
    for name, strategy in core_strategies().items():
        detail_direction = ("progressive_detail"
                            if name == "blueprint_progressive_detail"
                            else "summary_only" if name == "direct_next"
                            else "")
        add(StoreRecord(
            f"ask_strategy.{name}", "strategy", strategy.description,
            body={"role": "ask_strategy", "shape": strategy.shape,
                  "detail_direction": detail_direction,
                  "maturity": "registered" if strategy.tier == "core"
                  else "candidate",
                  "facets": context_facets(ContextFacetSpec(
                      category="asking_method", subcategory=name,
                      context_type="method", thinking_style="exploration",
                      detail_direction=detail_direction,
                      scope="package", lifecycle="registered"
                      if strategy.tier == "core" else "candidate",
                      provenance="ask_strategy_registry"))},
            tags=("ask_strategy", strategy.shape, name), tier=strategy.tier,
            source="ask_strategy_registry"))

    from ..strings.prompt_fragments import seed_registry
    for fragment in seed_registry()._frags.values():
        add(StoreRecord(
            fragment.id, "context", fragment.template,
            body={"role": "prompt_fragment", "version": fragment.version,
                  "serialization_format": "plain_text",
                  "format_example": fragment.template,
                  "maturity": "registered",
                  "facets": context_facets(ContextFacetSpec(
                      category="prompt_fragment",
                      subcategory=fragment.purpose,
                      context_type="template", scope="package",
                      serialization_format="plain_text",
                      lifecycle="registered",
                      provenance="prompt_fragment_registry"))},
            tags=("prompt_fragment", fragment.purpose),
            source="prompt_fragment_registry"))

    from .context_ontology import ontology_records
    for record in ontology_records():
        add(record)

    if not include_candidates:
        records = [record for record in records
                   if record.tier == "core"
                   and str((record.body or {}).get("maturity", ""))
                   != "candidate"]
    return records


def self_test() -> dict:
    active = build_context_records()
    review = build_context_records(include_candidates=True)
    from .intelligence_layers import classify_record
    from .context_ontology import CONTROLLED_AXES, normalize_ontology
    invalid = []
    for record in active:
        hierarchy = classify_record(
            "context_intelligence", record).get("context_hierarchy", {})
        controlled = {key: hierarchy.get(key) for key in CONTROLLED_AXES
            if hierarchy.get(key)}
        try:
            normalize_ontology(controlled)
        except ValueError as exc:
            invalid.append((record.record_id, str(exc)))
    tests = [
        {"test": "active_context_excludes_candidate_tiers",
         "passed": active and all(record.tier == "core"
                                  for record in active)},
        {"test": "review_context_includes_integrity_checked_seed_pack",
         "passed": len(review) > len(active)
         and any(record.record_id == "SI-0001"
                 and record.tier == "experimental" for record in review)},
        {"test": "disconnected_context_registries_are_projected",
         "passed": any(record.record_id.startswith("qform.")
                       for record in active)
         and any(record.record_id.startswith("lens.") for record in active)
         and any(record.record_id.startswith("context_policy.")
                 for record in active)},
        {"test": "every_active_context_record_uses_valid_controlled_axes",
         "passed": not invalid},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
