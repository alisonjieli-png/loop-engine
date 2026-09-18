"""Offline checks for text conformance.

The checks cover the seven operations on the owner's example patterns, the
layered exception catalogs, rule and policy validation, the run with its
apply, hold, and escalate outcomes, idempotence, escalation requests bound
to the registered contract, rule proposal from profiles, the validate
endpoint, and the resolver's typed task support and path confinement.
"""
from __future__ import annotations

import json

from . import text_conformance_operations as operations
from .text_conformance import (CATALOG_SOURCES, ESCALATION_CONTRACT_ID, OUTCOMES, RESOLVER_ID,
                               TASK_RECORD_TYPE, ConformancePolicy, ConformanceRule,
                               EscalationRequest, ExceptionCatalogLayer, TextConformanceError,
                               TextConformanceResolver, catalog_layer_from_file,
                               load_packaged_catalogs, merge_layers, propose_rules,
                               run_conformance, second_pass_changes, text_conformance_surface,
                               text_conformance_validate_endpoint)


def _refuses(action) -> bool:
    try:
        action()
    except (TextConformanceError, ValueError):
        return True
    return False


def run_checks() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    catalogs = merge_layers([load_packaged_catalogs()])
    case = lambda value, evidence=None: operations.case_normalize(value, {}, catalogs, evidence)
    check("packaged_catalogs_carry_every_kind_the_operations_read",
          all(kind in catalogs for kind in ("legal_suffixes", "surname_exceptions",
                                            "internal_capital_prefixes", "minor_words",
                                            "preserved_tokens", "null_sentinels")))
    check("all_caps_name_is_title_cased_with_surname_prefix_and_suffix",
          case("MCDOUGLAS & SONS, INC.")["output"] == "McDouglas & Sons, Inc."
          and operations.suffix_canonicalize("McDouglas & Sons, Inc.", {}, catalogs)["output"]
          == "McDouglas & Sons Inc")
    lapointe = case("LAPOINTE CONSULTING LLC")
    check("catalog_exception_keeps_internal_capital_and_legal_suffix_casing",
          lapointe["output"] == "LaPointe Consulting LLC"
          and "surname_exception:LaPointe" in lapointe["reasons"]
          and "legal_suffix_cased:LLC" in lapointe["reasons"]
          and "preserved_token" in case("IBM CORP")["reasons"])
    aa = case("AA CAREERS")
    check("unverified_short_token_lowers_confidence_below_the_apply_threshold",
          aa["output"] == "AA Careers" and aa["confidence"] < operations.DEFAULT_APPLY_AT_OR_ABOVE
          and "short_token_kept_upper_unverified" in aa["reasons"])
    check("mixed_case_input_keeps_deliberate_uppercase_and_internal_capitals",
          case("ABC Consulting Inc.")["output"] == "ABC Consulting Inc."
          and case("MacDonald Farms")["output"] == "MacDonald Farms"
          and case("ACME Corp")["confidence"] == 1.0)
    check("hyphenated_initials_and_apostrophe_prefixes_are_handled",
          case("l-e industries")["output"] == "L-E Industries"
          and case("O'BRIEN PLUMBING")["output"] == "O'Brien Plumbing"
          and case("SMITH'S GARAGE")["output"] == "Smith's Garage")
    particles = case("de la cruz bakery")
    check("leading_particle_is_capitalized_and_inner_particles_are_ambiguous",
          particles["output"] == "De la Cruz Bakery"
          and "particle_lowercased_ambiguous" in particles["reasons"]
          and particles["confidence"] <= float(catalogs["particle_confidence"]))
    evidence = operations.learn_column_evidence(
        [{"n": "ABC Consulting"}, {"n": "ABC Partners"}, {"n": "ABC CONSULTING"}], ["n"])
    check("column_evidence_teaches_a_casing_the_all_caps_row_inherits",
          evidence["n"]["abc"]["form"] == "ABC"
          and case("ABC CONSULTING", evidence["n"])["output"] == "ABC Consulting"
          and "column_evidence:ABC" in case("ABC CONSULTING", evidence["n"])["reasons"])
    check("plain_all_caps_name_reaches_the_apply_threshold",
          case("ACME CORPORATION")["confidence"] >= operations.DEFAULT_APPLY_AT_OR_ABOVE
          and case("JOHNSON & JOHNSON")["output"] == "Johnson & Johnson")
    check("suffix_styles_and_comma_policy_are_parameters",
          operations.suffix_canonicalize("Acme, Inc.", {"style": "short_with_period"}, catalogs)["output"] == "Acme Inc."
          and operations.suffix_canonicalize("Acme Inc", {"style": "long_form"}, catalogs)["output"] == "Acme Incorporated"
          and operations.suffix_canonicalize("Acme Inc", {"comma_before_suffix": "add"}, catalogs)["output"] == "Acme, Inc"
          and operations.suffix_canonicalize("Acme Co., Ltd.", {}, catalogs)["output"] == "Acme Co Ltd")
    spa = operations.suffix_canonicalize("Acme Spa", {}, catalogs)
    check("an_ambiguous_suffix_carries_its_catalog_confidence",
          spa["output"] == "Acme SpA" and spa["confidence"] == catalogs["ambiguous_suffixes"]["spa"]
          and "ambiguous_suffix:spa" in spa["reasons"])
    check("whitespace_normalization_is_lossless_and_named",
          operations.whitespace_normalize("  Beta   Industries  ")
          == {"output": "Beta Industries", "confidence": 0.99, "changed": True,
              "reasons": ["nonstandard_space_character", "leading_or_trailing_whitespace",
                          "internal_whitespace_run"]})
    folded = operations.unicode_normalize("Müller Straße", {"ascii_fold": "hold"}, catalogs)
    retained = operations.unicode_normalize("Müller", {}, catalogs)
    check("unicode_folding_is_off_by_default_and_low_confidence_when_held",
          retained["output"] == "Müller" and "non_ascii_retained" in retained["reasons"]
          and folded["output"] == "Muller Strasse" and folded["confidence"] == 0.5
          and operations.unicode_normalize("x", {"ascii_fold": "apply"}, catalogs)["confidence"] == 1.0
          and _refuses(lambda: operations.unicode_normalize("x", {"ascii_fold": "maybe"}, catalogs)))
    check("phone_email_and_website_normalization_report_their_signals",
          operations.phone_normalize("(312) 555-0199", {"default_country_code": "1"}, catalogs)["output"] == "+13125550199"
          and operations.phone_normalize("+1 217-555-0100 ext 42", {"default_country_code": "1"}, catalogs)["output"] == "+12175550100 ext 42"
          and operations.phone_normalize("12345", {"default_country_code": "1"}, catalogs)["confidence"] < operations.DEFAULT_ESCALATE_BELOW
          and operations.email_normalize("Mailto:John.Doe@Example.COM", {}, catalogs)["output"] == "john.doe@example.com"
          and operations.email_normalize("bad@", {}, catalogs)["confidence"] < operations.DEFAULT_ESCALATE_BELOW
          and operations.website_normalize("HTTPS://WWW.Acme.Example.com/About/", {}, catalogs)["output"] == "https://www.acme.example.com/About"
          and operations.website_normalize("acme.example.com", {}, catalogs)["reasons"] == ["scheme_added"])
    check("classification_follows_the_thresholds",
          operations.classify(0.95, True, 0.9, 0.6) == OUTCOMES[0]
          and operations.classify(0.8, True, 0.9, 0.6) == OUTCOMES[1]
          and operations.classify(0.3, False, 0.9, 0.6) == OUTCOMES[2]
          and operations.classify(1.0, False, 0.9, 0.6) == OUTCOMES[3])
    check("pattern_induction_and_profiles_describe_the_column",
          operations.induce_pattern("+1 217-555-0100") == {"shape": "+9 999-999-9999", "collapsed": "+9 9+-9+-9+"}
          and operations.profile_column(["ACME", "Beta ", "n/a"], catalogs)["counts"]
          == {"all_upper": 1, "mixed_case": 1, "null_or_sentinel": 1, "whitespace_issue": 1}
          and "regexp_matches" in operations.duckdb_profile_sql("rows", 'na"me'))

    rules = (ConformanceRule("whitespace", "whitespace_normalize", ("name",)),
             ConformanceRule("case", "case_normalize", ("name",)),
             ConformanceRule("suffix", "suffix_canonicalize", ("name",)),
             ConformanceRule("email", "email_normalize", ("email",)))
    rows = [{"name": "ACME CORPORATION", "email": "A@Example.com"},
            {"name": "AA CAREERS", "email": "bad@"},
            {"name": "Acme Spa", "email": "ok@example.org"}]
    run = run_conformance(rows, rules, ConformancePolicy(), catalogs)
    applied = [item for item in run.corrections if item.outcome == OUTCOMES[0]]
    held = [item for item in run.corrections if item.outcome == OUTCOMES[1]]
    escalated = [item for item in run.corrections if item.outcome == OUTCOMES[2]]
    check("a_run_applies_confident_corrections_holds_ambiguous_ones_and_escalates_low_ones",
          run.output_rows[0]["name"] == "Acme Corp" and run.output_rows[0]["email"] == "a@example.com"
          and run.output_rows[1]["name"] == "AA CAREERS"
          and {(item.column, item.row_ref) for item in held} == {("name", "1"), ("name", "2")}
          and run.output_rows[2]["name"] == "Acme Spa"
          and [(item.column, item.row_ref) for item in escalated] == [("email", "1")]
          and len(applied) == 3 and run.report.rows == 3)
    check("the_report_counts_match_the_corrections_and_the_pass_is_idempotent",
          run.report.overall == {"applied": 3, "held": 2, "escalated": 1, "unchanged": 0}
          and run.report.idempotent is True and not run.report.complete
          and sum(run.report.confidence_histogram) == 6
          and run.report.to_dict()["content_digest"] == run.report.to_dict()["content_digest"])
    escalation = run.escalations[0] if run.escalations else EscalationRequest(
        "none", "none", "none", (("none", 0.0),), (), ("human_review",))
    check("an_escalation_names_candidates_reasons_targets_and_the_registered_contract",
          len(run.escalations) == 1 and escalation.contract_id == ESCALATION_CONTRACT_ID
          and escalation.candidates[0][0] == "bad@" and escalation.targets == ConformancePolicy().escalation_targets
          and escalation.suggested_output().cardinality == 3
          and "bad@" in escalation.question() and "email" in escalation.question()
          and _refuses(lambda: EscalationRequest("0", "c", "v", (), (), ("model_judgment",))))
    with_held = run_conformance(rows, rules, ConformancePolicy(escalate_held=True), catalogs)
    check("escalate_held_sends_held_corrections_too",
          len(with_held.escalations) == 3)
    check("every_escalation_carries_a_model_versus_not_decision_naming_the_service_model",
          len(run.decisions) == 1 and run.decisions[0].operation_id == "conform.email"
          and run.decisions[0].chosen.kind == "service_model"
          and run.decisions[0].candidates[0].implementation_id == RESOLVER_ID
          and "0.30" in run.decisions[0].reason and len(with_held.decisions) == 3)
    together = run_conformance([{"name": "MÜLLER GMBH"}, {"name": "3M COMPANY"}, {"name": "Acme Spa"},
                                {"name": "ACME CORPORATION"}], rules[:3], ConformancePolicy(), catalogs)
    rule_dicts = [rule.to_dict() for rule in rules[:3]]
    check("case_and_suffix_rules_agree_so_a_second_pass_changes_nothing",
          together.report.idempotent is True
          and [row["name"] for row in together.output_rows] == ["Müller GmbH", "3M Co", "Acme Spa", "Acme Corp"]
          and together.report.overall["held"] == 1
          and second_pass_changes(together.output_rows, rule_dicts, catalogs, ConformancePolicy().to_dict(), {}) == 0
          and second_pass_changes([{"name": "MÜLLER GMBH"}, {"name": "ACME CORPORATION"}], rule_dicts,
                                  catalogs, ConformancePolicy().to_dict(), {}) == 3)
    check("rules_and_policies_refuse_invalid_shapes",
          _refuses(lambda: ConformanceRule("r", "guess", ("a",)))
          and _refuses(lambda: ConformanceRule("r", "case_normalize", ()))
          and _refuses(lambda: ConformanceRule("r", "case_normalize", ("a",), apply_at_or_above=0.5, escalate_below=0.7))
          and _refuses(lambda: ConformanceRule("r", "suffix_canonicalize", ("a",), {"style": "loud"}))
          and _refuses(lambda: ConformancePolicy(escalate_below=0.95))
          and _refuses(lambda: ConformancePolicy(escalation_targets=("oracle",)))
          and ConformanceRule.from_dict(rules[1].to_dict()) == rules[1]
          and ConformancePolicy.from_dict(ConformancePolicy(0.8, 0.5).to_dict()) == ConformancePolicy(0.8, 0.5))
    inline = ExceptionCatalogLayer("inline", CATALOG_SOURCES[3],
                                   {"surname_exceptions": {"acme": "ACME", "lapointe": "Lapointe"},
                                    "preserved_tokens": ["ZZ"]})
    merged = merge_layers([load_packaged_catalogs(), inline])
    check("a_later_layer_overrides_mappings_and_extends_lists",
          merged["surname_exceptions"]["acme"] == "ACME" and merged["surname_exceptions"]["lapointe"] == "Lapointe"
          and merged["surname_exceptions"]["dubois"] == "DuBois"
          and "ZZ" in merged["preserved_tokens"] and "LLC" in merged["preserved_tokens"]
          and operations.case_normalize("ACME CORP", {}, merged)["output"] == "ACME Corp"
          and _refuses(lambda: ExceptionCatalogLayer("x", "guess", {}))
          and _refuses(lambda: ExceptionCatalogLayer("x", "inline", {"unknown_kind": []}))
          and _refuses(lambda: ExceptionCatalogLayer("x", "inline", {"minor_words": {"a": 1}})))
    proposals = propose_rules({
        "name": operations.profile_column(["ACME INC", "beta corp", "Gamma"], catalogs),
        "email": operations.profile_column(["a@b.co", "c@d.org"], catalogs),
        "site": operations.profile_column(["x.example.com", "https://y.org"], catalogs),
        "phone": operations.profile_column(["+1 217 555 0100", "3125550199"], catalogs),
        "notes": operations.profile_column(["fine", "also fine"], catalogs)})
    check("rule_proposals_follow_the_profile_evidence_with_reasons",
          [item.rule.rule_id for item in proposals] == ["email.email", "case.name", "suffix.name",
                                                        "phone.phone", "website.site"]
          and all(item.reasons for item in proposals)
          and all(item.rule.operation in operations.OPERATIONS for item in proposals))
    validate = text_conformance_validate_endpoint(rows=[{"name": "ACME INC"}])
    check("the_validate_endpoint_profiles_proposes_and_emits_duckdb_sql_without_changing_data",
          validate["profiles"]["name"]["counts"]["all_upper"] == 1
          and validate["proposals"] and "FROM rows" in validate["duckdb_sql"]["name"])
    from ..core.capability_directory import default_directory
    directory = default_directory(surfaces=(text_conformance_surface(),))
    served = directory.call("text_conformance", "run", rows=[{"name": "ACME CORPORATION"}],
                            rules=[rules[1].to_dict()])
    check("the_surface_registers_in_a_directory_and_serves_run_and_validate",
          directory.discover("validate", surface_kind="code_node_registry")
          == ["contract_registry", "text_conformance"]
          and served.ok and served.value["output_rows"][0]["name"] == "Acme Corporation"
          and directory.call("text_conformance", "validate", rows=[{"name": "ACME INC"}]).ok)

    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as outer:
        root = Path(outer) / "root"
        root.mkdir()
        folder = str(root)
        (Path(outer) / "outside.csv").write_text("name\nOUTSIDE ROW\n", "utf-8")
        (Path(outer) / "outside.json").write_text(json.dumps({"surname_exceptions": {"x": "X"}}), "utf-8")
        (root / "catalog.json").write_text(json.dumps({"surname_exceptions": {"beta": "BeTa"}}), "utf-8")
        (root / "rows.csv").write_text("name\nBETA INC\nAA CAREERS\n", "utf-8")
        layer = catalog_layer_from_file("catalog.json", folder)
        check("a_task_folder_catalog_is_read_inside_its_root_and_refused_outside",
              layer.source == CATALOG_SOURCES[1] and layer.catalogs["surname_exceptions"]["beta"] == "BeTa"
              and _refuses(lambda: catalog_layer_from_file("../outside.json", folder)))
        resolver = TextConformanceResolver(folder)
        task = json.dumps({"record_type": TASK_RECORD_TYPE, "input_path": "rows.csv",
                           "rules": [rules[1].to_dict()], "catalog_files": ["catalog.json"]})
        result = resolver.execute(task)
        check("the_resolver_supports_only_the_typed_task_record_and_reads_inside_the_root",
              resolver.resolver_id == RESOLVER_ID and resolver.supports(task)
              and not resolver.supports("conform the names please")
              and not resolver.supports(json.dumps({"record_type": "other/v1"}))
              and result["output_rows"][0]["name"] == "BeTa Inc"
              and result["output_rows"][1]["name"] == "AA CAREERS"
              and [item["source"] for item in result["catalog_layers"]] == ["packaged", "task_folder"]
              and _refuses(lambda: resolver.execute(json.dumps(
                  {"record_type": TASK_RECORD_TYPE, "input_path": "../outside.csv",
                   "rules": [rules[1].to_dict()]}))))
        check("the_resolver_verifies_only_a_complete_pass_and_hands_back_escalations_otherwise",
              result["verified"] is False and result["escalations"] == []
              and result["report"]["overall"]["held"] == 1
              and resolver.execute(json.dumps({"record_type": TASK_RECORD_TYPE,
                                               "rows": [{"name": "ACME CORPORATION"}],
                                               "rules": [rules[1].to_dict()]}))["verified"] is True
              and _refuses(lambda: resolver.execute(json.dumps(
                  {"record_type": TASK_RECORD_TYPE, "input_path": "rows.csv", "max_rows": 1,
                   "rules": [rules[1].to_dict()]}))))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "text_conformance_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
