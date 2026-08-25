"""Composable ontology for Context Intelligence.

Architectural role: Static Architecture ontology and labeling service.

Owns: stable vocabularies for context kinds, question families, thinking
methods, list structures, serialization formats, evidence states,
relationships, key-phrase extraction, derived tags, and searchable ontology
records.

Does not own: the stored context bodies, retrieval ranking, source approval,
or promotion. The axes stay composable so the catalog never materializes the
full Cartesian product.

Verification: ``self_test()`` checks coverage, examples, normalization, key
phrases, tags, and searchable records.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter
from dataclasses import dataclass


CONTEXT_KINDS = (
    "context", "question", "method", "heuristic", "instruction",
    "checklist", "checklist_item", "warning", "constraint",
    "consideration", "persona", "perspective", "analogy",
    "example", "format_example", "template", "prompt_fragment",
    "prompt_pattern",
    "output_contract", "decision_schema", "evaluation", "rubric", "fact",
    "definition", "glossary", "source_note", "failure_pattern", "other")

QUESTION_FAMILIES = (
    "direct", "best_way", "worst_way", "first_principles", "analogy",
    "decomposition", "outline_to_detail", "missing_items",
    "top_improvements", "top_avoid", "best_practices", "inversion",
    "adversarial_review", "premortem", "falsification", "evidence_needed",
    "comparison", "pairwise", "ranking", "elimination", "prerequisites",
    "uncertainty", "calibration", "causal_reasoning", "counterfactual",
    "novel_alternatives", "stakeholder_view", "constraint_review",
    "failure_recovery", "cost_compression")

THINKING_METHODS = (
    "first_principles", "analogy", "decomposition", "outline_to_detail",
    "inversion", "assumption_reversal", "falsification", "premortem",
    "gap_analysis", "adversarial_review", "comparison", "ranking",
    "elimination", "causal_reasoning", "statistical_reasoning",
    "systems_thinking", "constraint_analysis", "uncertainty_calibration",
    "information_gain", "minimum_complexity", "maximum_diversity",
    "counterfactual", "failure_first", "cost_value_analysis", "improvement",
    "avoidance", "best_practices", "failure_analysis", "prioritization",
    "verification", "exploration", "other")

LIST_STRUCTURES = (
    "none", "flat_list", "numbered_steps", "checklist", "ranked_list",
    "top_n", "bottom_n", "nested_outline", "tree", "matrix", "table",
    "timeline", "pros_and_cons", "decision_table", "key_value_pairs")

SERIALIZATION_FORMATS = (
    "plain_text", "markdown", "json", "jsonl", "yaml", "csv", "tsv",
    "html", "xml", "python_literal", "markdown_table", "mermaid")

RESPONSE_SHAPES = (
    "free_text", "single_value", "boolean", "score", "ranking", "list",
    "checklist", "comparison", "decomposition", "proposals", "elimination",
    "verdict", "key_value", "table", "graph", "timeline", "code",
    "code_or_test", "measurement_spec", "evaluation", "free")

EVIDENCE_STATUSES = (
    "unsourced", "proposed", "inferred", "source_backed", "reviewed",
    "verified", "disputed", "superseded", "retired")

UTILITY_STATUSES = (
    "unmeasured", "retrieved", "used", "changed_decision", "helpful",
    "neutral", "harmful", "negative_transfer")

RELATIONSHIP_TYPES = (
    "is_a", "part_of", "broader_than", "narrower_than", "related_to",
    "realizes", "instantiates", "variant_of", "composed_of", "requires",
    "depends_on", "compatible_with", "incompatible_with", "parsed_by",
    "validated_by", "evaluated_by", "contradicts", "supports",
    "supported_by", "supersedes", "example_of", "negative_example_of",
    "applies_to", "contraindicated_for", "fails_under", "derived_from",
    "distills_to_code", "used_by_template", "produced_by_run")

DETAIL_DIRECTIONS = (
    "summary_only", "high_level_to_detail", "detail_to_summary",
    "progressive_detail", "atomic_steps", "implementation_detail")

SPEECH_ACTS = (
    "ask", "answer", "define", "explain", "instruct", "warn", "compare",
    "rank", "classify", "extract", "summarize", "decompose", "generate",
    "critique", "verify", "falsify", "estimate", "recommend", "decide",
    "abstain")

POLARITIES = (
    "neutral", "positive", "negative", "supporting", "opposing",
    "inverted", "adversarial", "balanced")

COMPARISON_MODES = (
    "none", "pairwise", "one_to_many", "many_to_many", "baseline_relative",
    "counterfactual", "analogy", "before_after", "tradeoff")

ORDERING_RULES = (
    "none", "source_order", "priority", "rank", "chronological",
    "reverse_chronological", "dependency", "cost", "risk", "confidence",
    "alphabetical", "custom")

CLAIM_STATUSES = (
    "observation", "claim", "assumption", "hypothesis", "proposal",
    "decision", "refusal", "unknown", "not_applicable")

LIFECYCLE_STATES = (
    "draft", "candidate", "validated", "registered", "quarantined",
    "deprecated", "superseded", "retired")

ACCESS_LEVELS = (
    "public", "organization", "project", "team", "private", "restricted")

SOURCE_TYPES = (
    "hand_authored", "user_provided", "official_source", "primary_source",
    "published_research", "repository", "package", "historical_run",
    "derived", "model_generated", "unknown")

FRESHNESS_STATES = (
    "current", "time_bound", "stale", "unknown", "not_time_sensitive")

RISK_LEVELS = ("none", "low", "medium", "high", "critical", "unknown")

APPLICABILITY_STATUSES = (
    "general", "conditional", "required", "preferred", "contraindicated",
    "incompatible", "unknown")


# One registry drives validation, searchable ontology records, and docs. Open
# dimensions such as job title, industry, domain, geography, and key phrase are
# intentionally absent. They accept explicit values rather than pretending a
# package can enumerate every profession or jurisdiction in advance.
CONTROLLED_AXES = {
    "context_type": CONTEXT_KINDS,
    "question_family": QUESTION_FAMILIES,
    "thinking_style": THINKING_METHODS,
    "speech_act": SPEECH_ACTS,
    "polarity": POLARITIES,
    "comparison_mode": COMPARISON_MODES,
    "detail_direction": DETAIL_DIRECTIONS,
    "list_structure": LIST_STRUCTURES,
    "ordering_rule": ORDERING_RULES,
    "serialization_format": SERIALIZATION_FORMATS,
    "response_shape": RESPONSE_SHAPES,
    "claim_status": CLAIM_STATUSES,
    "evidence_status": EVIDENCE_STATUSES,
    "utility_status": UTILITY_STATUSES,
    "lifecycle": LIFECYCLE_STATES,
    "access_level": ACCESS_LEVELS,
    "source_type": SOURCE_TYPES,
    "freshness_status": FRESHNESS_STATES,
    "risk_level": RISK_LEVELS,
    "applicability_status": APPLICABILITY_STATUSES,
}

CONTEXT_METADATA_GROUPS = {
    "identity_and_governance": (
        "record_id", "schema_version", "version", "digest", "canonical_label",
        "aliases", "language", "lifecycle", "access_level", "tenant",
        "provenance"),
    "artifact_semantics": (
        "context_type", "semantic_intent", "definition", "category_path"),
    "role": (
        "role_family", "job_title", "job_aliases", "seniority",
        "responsibilities", "stakeholders", "decisions", "deliverables"),
    "work": (
        "industry", "domain", "subdomain", "topic", "project_type",
        "task_type", "workflow_stage"),
    "reasoning": (
        "speech_act", "question_family", "thinking_style", "polarity",
        "comparison_mode", "detail_direction"),
    "presentation": (
        "response_shape", "list_structure", "cardinality", "ordering_rule",
        "serialization_format", "schema_ref", "parser_ref", "validator_ref",
        "format_example", "negative_format_example"),
    "operating_context": (
        "geography", "jurisdiction", "time_horizon", "data_regime",
        "failure_regime", "risk_level", "privacy", "latency", "budget"),
    "epistemic_state": (
        "claim_status", "evidence_status", "source_refs", "source_type",
        "freshness_status", "confidence", "contradictions",
        "abstention_conditions"),
    "applicability": (
        "applicability_status", "applies_when", "contraindications",
        "required_inputs", "compatible_with", "incompatible_with"),
    "retrieval": (
        "canonical_label", "aliases", "key_phrases", "labels", "tags",
        "blocking_keys", "embedding_space", "lexical_hash"),
    "history": (
        "retrieval_event_refs", "selection_event_refs", "outcome_event_refs",
        "failure_event_refs", "lifecycle_event_refs"),
}


# Historical and author-friendly spellings resolve to one stored vocabulary.
# Aliases are accepted at ingestion, but catalog facets store the value on the
# right. This keeps filters stable without refusing useful older records.
ONTOLOGY_ALIASES = {
    "context_type": {
        "string": "context", "prompt": "prompt_fragment",
        "format": "format_example"},
    "question_family": {
        "whats_missing": "missing_items", "rank_options": "ranking",
        "verify_check": "evidence_needed",
        "generate_novel": "novel_alternatives",
        "decompose": "decomposition", "calibrate": "calibration"},
    "thinking_style": {
        "adversarial": "adversarial_review", "systems": "systems_thinking",
        "calibration": "uncertainty_calibration"},
    "list_structure": {
        "bullets": "flat_list", "numbered_list": "numbered_steps",
        "outline": "nested_outline", "key_value": "key_value_pairs"},
    "serialization_format": {
        "text": "plain_text", "md": "markdown", "ndjson": "jsonl"},
    "response_shape": {
        "simple_value": "single_value", "string_statement": "free_text",
        "json_list": "list", "if_then_rule": "key_value"},
    "claim_status": {"proposed": "proposal", "assumed": "assumption"},
    "lifecycle": {
        "core": "registered", "experimental": "candidate",
        "implemented": "validated", "committed": "registered"},
    "access_level": {"internal": "organization", "user": "private"},
}


FORMAT_CONTRACTS = {
    "plain_text": {
        "media_type": "text/plain", "extension": ".txt",
        "example": "Decision: use the deterministic parser. Reason: it passed."},
    "markdown": {
        "media_type": "text/markdown", "extension": ".md",
        "example": "## Decision\n\nUse the deterministic parser."},
    "json": {
        "media_type": "application/json", "extension": ".json",
        "example": '{"items":[{"name":"parser","status":"accepted"}]}'},
    "jsonl": {
        "media_type": "application/x-ndjson", "extension": ".jsonl",
        "example": '{"name":"parser"}\n{"name":"validator"}'},
    "yaml": {
        "media_type": "application/yaml", "extension": ".yaml",
        "example": "items:\n  - name: parser\n    status: accepted"},
    "csv": {
        "media_type": "text/csv", "extension": ".csv",
        "example": "name,status\nparser,accepted"},
    "tsv": {
        "media_type": "text/tab-separated-values", "extension": ".tsv",
        "example": "name\tstatus\nparser\taccepted"},
    "html": {
        "media_type": "text/html", "extension": ".html",
        "example": "<ul><li>parser: accepted</li></ul>"},
    "xml": {
        "media_type": "application/xml", "extension": ".xml",
        "example": '<items><item name="parser" status="accepted"/></items>'},
    "python_literal": {
        "media_type": "text/x-python", "extension": ".py",
        "example": "{'items': [{'name': 'parser', 'status': 'accepted'}]}"},
    "markdown_table": {
        "media_type": "text/markdown", "extension": ".md",
        "example": "| Name | Status |\n|---|---|\n| parser | accepted |"},
    "mermaid": {
        "media_type": "text/plain", "extension": ".mmd",
        "example": "flowchart LR\n  input --> parser --> output"},
}

FORMAT_TRAITS = {
    "plain_text": {
        "structure": "unstructured", "streamable": True,
        "parser": "text", "use_when": "A person will read the answer directly.",
        "avoid_when": "Another program must consume exact fields."},
    "markdown": {
        "structure": "document", "streamable": True,
        "parser": "commonmark", "use_when": "Headings, prose, and code must coexist.",
        "avoid_when": "A strict machine schema is required."},
    "json": {
        "structure": "structured", "streamable": False,
        "parser": "json", "use_when": "One complete typed object crosses a boundary.",
        "avoid_when": "Results must be appended one at a time.",
        "negative_example": "{'items': [trailing,]}"},
    "jsonl": {
        "structure": "record_stream", "streamable": True,
        "parser": "json_per_line", "use_when": "Independent records are appended or streamed.",
        "avoid_when": "Records must share one enclosing schema object.",
        "negative_example": '[{"name":"parser"},{"name":"validator"}]'},
    "yaml": {
        "structure": "structured", "streamable": False,
        "parser": "yaml", "use_when": "A person edits nested configuration.",
        "avoid_when": "Parser portability or type ambiguity is a concern."},
    "csv": {
        "structure": "table", "streamable": True,
        "parser": "csv", "use_when": "Rows share a flat column schema.",
        "avoid_when": "Values are deeply nested."},
    "tsv": {
        "structure": "table", "streamable": True,
        "parser": "tsv", "use_when": "Flat text fields contain many commas.",
        "avoid_when": "Fields contain unescaped tabs or nested values."},
    "html": {
        "structure": "document", "streamable": True,
        "parser": "html", "use_when": "The output is rendered in a browser.",
        "avoid_when": "Plain text or a data object is sufficient."},
    "xml": {
        "structure": "structured", "streamable": True,
        "parser": "xml", "use_when": "An existing XML contract requires it.",
        "avoid_when": "No XML consumer exists."},
    "python_literal": {
        "structure": "language_literal", "streamable": False,
        "parser": "ast.literal_eval", "use_when": "A trusted Python-only tool expects a literal.",
        "avoid_when": "The boundary crosses languages or trust domains."},
    "markdown_table": {
        "structure": "table", "streamable": False,
        "parser": "commonmark_table", "use_when": "A person compares a small fixed table.",
        "avoid_when": "Rows are numerous or consumed by code."},
    "mermaid": {
        "structure": "graph", "streamable": False,
        "parser": "mermaid", "use_when": "Labeled nodes and edges explain the structure.",
        "avoid_when": "Exact numeric comparison is the main point."},
}

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "before", "by", "can",
    "do", "for", "from", "how", "in", "is", "it", "of", "on", "or",
    "our", "should", "that", "the", "this", "to", "what", "when", "which",
    "with", "would", "your"}


def extract_key_phrases(text: str, *, max_phrases: int = 12) -> list:
    """Extract stable unigram and adjacent-bigram phrases without a model."""
    words = [word for word in re.findall(r"[a-z0-9][a-z0-9_+-]*",
                                         str(text).lower())
             if word not in _STOPWORDS and len(word) > 2]
    unigrams = Counter(words)
    bigrams = Counter(" ".join(pair) for pair in zip(words, words[1:])
                      if pair[0] != pair[1])
    ranked = sorted(
        [(count + 1, phrase) for phrase, count in bigrams.items()]
        + [(count, word) for word, count in unigrams.items()],
        key=lambda item: (-item[0], item[1]))
    out = []
    for _, phrase in ranked:
        if phrase not in out:
            out.append(phrase)
        if len(out) >= max(1, int(max_phrases)):
            break
    return out


def normalize_ontology(metadata: dict) -> dict:
    """Validate known axes while preserving explicit open-domain labels."""
    out = dict(metadata or {})
    for key, vocabulary in CONTROLLED_AXES.items():
        value = out.get(key, "")
        value = ONTOLOGY_ALIASES.get(key, {}).get(value, value)
        if value:
            out[key] = value
        if value and value not in vocabulary:
            raise ValueError(f"{key}={value!r} not in {vocabulary}")
    relations = tuple(out.get("relationship_types") or ())
    unknown = [value for value in relations if value not in RELATIONSHIP_TYPES]
    if unknown:
        raise ValueError(f"unknown relationship types {unknown}")
    out["relationship_types"] = list(relations)
    return out


def derive_tags(metadata: dict, text: str = "") -> tuple:
    """Build sorted low-cardinality tags plus bounded key-phrase tags."""
    meta = normalize_ontology(metadata)
    keys = (
        "context_type", "question_family", "thinking_style", "speech_act",
        "polarity", "comparison_mode", "detail_direction", "list_structure",
        "ordering_rule", "serialization_format", "response_shape",
        "claim_status", "evidence_status", "utility_status", "lifecycle",
        "access_level", "source_type", "freshness_status", "risk_level",
        "applicability_status", "domain", "project_type", "task_type",
        "job_role", "workflow_stage")
    tags = {f"{key}:{meta[key]}" for key in keys if meta.get(key)}
    tags.update(f"key:{phrase.replace(' ', '_')}"
                for phrase in extract_key_phrases(text, max_phrases=6))
    return tuple(sorted(tags))


def format_contract(name: str) -> dict:
    if name not in FORMAT_CONTRACTS:
        raise KeyError(f"unknown format {name!r}; have {SERIALIZATION_FORMATS}")
    return {"name": name, **FORMAT_CONTRACTS[name], **FORMAT_TRAITS[name]}


def validate_format_example(name: str, value: str) -> bool:
    """Check examples for the formats the standard library can parse."""
    if not isinstance(value, str) or not value.strip():
        return False
    if name == "json":
        json.loads(value)
    elif name == "jsonl":
        for line in value.splitlines():
            json.loads(line)
    elif name in ("csv", "tsv"):
        rows = list(csv.reader(io.StringIO(value),
                               delimiter="," if name == "csv" else "\t"))
        if len(rows) < 2 or len({len(row) for row in rows}) != 1:
            return False
    return True


@dataclass(frozen=True)
class ContextRelationship:
    """One typed, evidence-bearing edge between Context records."""
    relation: str
    target_id: str
    target_version: str = ""
    status: str = "asserted"
    evidence_refs: tuple = ()
    provenance: str = ""

    def __post_init__(self):
        if self.relation not in RELATIONSHIP_TYPES:
            raise ValueError(f"unknown Context relationship {self.relation!r}")
        if not self.target_id:
            raise ValueError("a Context relationship needs a target_id")
        if self.status not in ("asserted", "verified", "disputed", "retired"):
            raise ValueError("relationship status is not recognized")

    def to_dict(self) -> dict:
        return {"relation": self.relation, "target_id": self.target_id,
                "target_version": self.target_version, "status": self.status,
                "evidence_refs": list(self.evidence_refs),
                "provenance": self.provenance}


@dataclass(frozen=True)
class ContextRecipe:
    """References for one lazily composed Context item, not rendered text."""
    recipe_id: str
    question_pattern_ref: str
    role_lens_ref: str = ""
    thinking_methods: tuple = ()
    context_policy_ref: str = ""
    output_contract_ref: str = ""
    serialization_format: str = "plain_text"
    slot_values: tuple = ()
    component_versions: tuple = ()
    relationship_refs: tuple = ()

    def __post_init__(self):
        if not self.recipe_id or not self.question_pattern_ref:
            raise ValueError("a Context recipe needs an id and question pattern")
        unknown = [method for method in self.thinking_methods
                   if method not in THINKING_METHODS]
        if unknown:
            raise ValueError(f"unknown thinking methods {unknown}")
        if self.serialization_format not in SERIALIZATION_FORMATS:
            raise ValueError("unknown Context recipe serialization format")
        if len(dict(self.slot_values)) != len(self.slot_values):
            raise ValueError("Context recipe slot names must be unique")

    @property
    def digest(self) -> str:
        return hashlib.sha256(json.dumps(
            self.to_dict(include_digest=False), sort_keys=True).encode()
        ).hexdigest()

    def to_dict(self, *, include_digest: bool = True) -> dict:
        body = {
            "record_type": "context_recipe/v1", "recipe_id": self.recipe_id,
            "question_pattern_ref": self.question_pattern_ref,
            "role_lens_ref": self.role_lens_ref,
            "thinking_methods": list(self.thinking_methods),
            "context_policy_ref": self.context_policy_ref,
            "output_contract_ref": self.output_contract_ref,
            "serialization_format": self.serialization_format,
            "slot_values": dict(self.slot_values),
            "component_versions": dict(self.component_versions),
            "relationship_refs": list(self.relationship_refs)}
        if include_digest:
            body["digest"] = self.digest
        return body


def ontology_records() -> list:
    """Serve each reusable ontology value as one searchable Context record."""
    from .store_serve import StoreRecord
    from .facets import context_facets
    records = []

    def add(axis: str, value: str, *, example: str = ""):
        text = f"Context ontology {axis}: {value.replace('_', ' ')}"
        records.append(StoreRecord(
            f"context_ontology.{axis}.{value}", "context", text,
            body={"role": "context_ontology_value", "axis": axis,
                  "value": value, "format_example": example,
                  "key_phrases": extract_key_phrases(text),
                  "maturity": "registered",
                  "facets": context_facets(
                      category="context_ontology", subcategory=axis,
                      context_type="definition", scope="package",
                      lifecycle="registered", provenance="context_ontology")},
            tags=("context_ontology", axis, value),
            source="context_ontology"))

    for axis, vocabulary in CONTROLLED_AXES.items():
        for value in vocabulary:
            add(axis, value, example=(FORMAT_CONTRACTS[value]["example"]
                                     if axis == "serialization_format" else ""))
    return records


def self_test() -> dict:
    phrases = extract_key_phrases(
        "Rank retrieval methods by retrieval quality and runtime cost.")
    meta = normalize_ontology({
        "context_type": "question", "question_family": "ranking",
        "thinking_style": "comparison", "speech_act": "rank",
        "comparison_mode": "many_to_many", "polarity": "neutral",
        "list_structure": "ranked_list", "ordering_rule": "rank",
        "serialization_format": "json", "response_shape": "ranking",
        "claim_status": "proposal", "evidence_status": "unsourced",
        "utility_status": "unmeasured", "lifecycle": "candidate",
        "access_level": "project", "freshness_status": "current",
        "risk_level": "low", "applicability_status": "conditional",
        "relationship_types": ("applies_to", "used_by_template")})
    tags = derive_tags(meta, "rank retrieval methods by runtime cost")
    records = ontology_records()
    relationship = ContextRelationship(
        "validated_by", "output.ranking.v1", target_version="1.0.0",
        status="verified", evidence_refs=("run:test",),
        provenance="ontology_self_test")
    recipe = ContextRecipe(
        "recipe.rank_methods", "qform.rank_options",
        role_lens_ref="lens.software_architect",
        thinking_methods=("comparison", "ranking"),
        context_policy_ref="context_policy.goal_and_recent_findings",
        output_contract_ref="output.ranked_candidates.v1",
        serialization_format="json",
        slot_values=(("task", "choose a retrieval engine"),
                     ("options", "FTS5, LanceDB, Qdrant")),
        component_versions=(("qform.rank_options", "1.0.0"),),
        relationship_refs=("relationship.rank.validator",))
    tests = [
        {"test": "ontology_has_broad_composable_axes",
         "passed": len(CONTEXT_KINDS) >= 20
         and len(QUESTION_FAMILIES) >= 30
         and len(THINKING_METHODS) >= 20
         and len(SERIALIZATION_FORMATS) >= 10
         and len(CONTROLLED_AXES) >= 20
         and len(CONTEXT_METADATA_GROUPS) >= 10},
        {"test": "json_and_non_json_formats_have_examples",
         "passed": all(value in FORMAT_CONTRACTS
                       for value in SERIALIZATION_FORMATS)
         and all(value in FORMAT_TRAITS for value in SERIALIZATION_FORMATS)
         and format_contract("json")["example"].startswith("{")
         and "| Name |" in format_contract("markdown_table")["example"]
         and validate_format_example("json", format_contract("json")["example"])
         and validate_format_example("jsonl", format_contract("jsonl")["example"])
         and validate_format_example("csv", format_contract("csv")["example"])},
        {"test": "key_phrases_and_tags_are_deterministic",
         "passed": phrases == extract_key_phrases(
             "Rank retrieval methods by retrieval quality and runtime cost.")
         and "retrieval methods" in phrases
         and "serialization_format:json" in tags},
        {"test": "ontology_values_are_searchable_without_cartesian_products",
         "passed": len(records) == sum(len(values)
                                        for values in CONTROLLED_AXES.values())
         and any(record.record_id.endswith("serialization_format.json")
                 for record in records)
         and any(record.record_id.endswith("speech_act.verify")
                 for record in records)},
        {"test": "aliases_normalize_to_one_stored_vocabulary",
         "passed": normalize_ontology({
             "thinking_style": "adversarial", "serialization_format": "md",
             "lifecycle": "core", "claim_status": "proposed"})
         == {"thinking_style": "adversarial_review",
             "serialization_format": "markdown", "lifecycle": "registered",
             "claim_status": "proposal", "relationship_types": []}},
        {"test": "relationships_and_recipes_are_typed_and_body_free",
         "passed": relationship.to_dict()["relation"] == "validated_by"
         and len(recipe.digest) == 64
         and recipe.to_dict()["question_pattern_ref"] == "qform.rank_options"
         and "rendered_text" not in recipe.to_dict()},
    ]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
