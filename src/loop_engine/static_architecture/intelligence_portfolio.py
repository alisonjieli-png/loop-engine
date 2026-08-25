"""Typed intelligence portfolios for non-deterministic consuming Loops.

Architectural role: internal selection service for Intelligence Search and Retrieval.

The four-layer catalog already owns retrieval and :class:`LoopRef`
materialization.  This module composes those contracts into one small map/fold
boundary for model-led consuming Loops:

* map one task across seven orthogonal, ontology-backed lens families;
* select exactly one active, unique LoopRef per family;
* materialize those refs through the existing intelligence access loops;
* record the exact refs made visible to each non-deterministic consuming Loop; and
* fold/export consuming Loop consumption without copying retrieved bodies into evidence.

It creates no prompt bank, performs no model call, and never enables the
candidate Context tier. Empty Runtime History and Solution and User Feedback
layers remain explicit in the portfolio rather than disappearing.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Mapping, Sequence

from ..loop.loop_capsule import LoopRef, MaterializedPayload
from .code_intelligence_assets import CodeAssetSpec, code_asset_record
from .context_ontology import (CONTEXT_KINDS, QUESTION_FAMILIES,
                               RESPONSE_SHAPES, SERIALIZATION_FORMATS,
                               THINKING_METHODS)
from .intelligence_layers import (LAYERS, LAYER_PUBLIC_KEY,
                                  LAYER_PUBLIC_LABEL,
                                  build_intelligence_catalog,
                                  materialize_intelligence_ref,
                                  normalize_layer_records,
                                  query_intelligence)


class IntelligencePortfolioError(ValueError):
    """A portfolio request or consumption record violated an invariant."""

class PortfolioCoverageError(IntelligencePortfolioError):
    """The active catalog could not cover every required lens family."""


class LensFamily(str, Enum):
    """The required, non-overlapping reasons for retrieving intelligence."""

    FIRST_PRINCIPLES = "first_principles"
    ALTERNATIVES_ANALOGY = "alternatives_analogy"
    MISSING_INFORMATION = "missing_information"
    FAILURE_ADVERSARIAL = "failure_adversarial"
    COST_RESOURCE = "cost_resource"
    VERIFICATION_EVALUATION = "verification_evaluation"
    OUTPUT_CONTRACT_FORMAT = "output_contract_format"


REQUIRED_LENS_FAMILIES = tuple(LensFamily)
SELECTOR_VERSION = "intelligence_portfolio/v2"

@dataclass(frozen=True)
class LensDefinition:
    """Ontology labels used as retrieval keys, never a generated prompt."""

    family: LensFamily
    retrieval_labels: tuple[str, ...]
    context_types: tuple[str, ...] = ()
    question_families: tuple[str, ...] = ()
    thinking_styles: tuple[str, ...] = ()
    category_groups: tuple[str, ...] = ()
    categories: tuple[str, ...] = ()
    response_shapes: tuple[str, ...] = ()
    serialization_formats: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        controlled = (
            ("context_types", self.context_types, CONTEXT_KINDS),
            ("question_families", self.question_families,
             QUESTION_FAMILIES),
            ("thinking_styles", self.thinking_styles, THINKING_METHODS),
            ("response_shapes", self.response_shapes, RESPONSE_SHAPES),
            ("serialization_formats", self.serialization_formats,
             SERIALIZATION_FORMATS),
        )
        for name, values, vocabulary in controlled:
            unknown = [value for value in values if value not in vocabulary]
            if unknown:
                raise IntelligencePortfolioError(
                    f"{name} contains values outside the Context ontology: "
                    f"{unknown!r}")


LENS_DEFINITIONS = {
    LensFamily.FIRST_PRINCIPLES: LensDefinition(
        LensFamily.FIRST_PRINCIPLES,
        ("first_principles", "decomposition", "assumptions", "invariants"),
        context_types=("question", "method", "heuristic"),
        question_families=("first_principles", "decomposition"),
        thinking_styles=("first_principles", "decomposition"),
        category_groups=("question", "method", "heuristic")),
    LensFamily.ALTERNATIVES_ANALOGY: LensDefinition(
        LensFamily.ALTERNATIVES_ANALOGY,
        ("analogy", "novel_alternatives", "counterfactual",
         "maximum_diversity", "comparison"),
        context_types=("question", "method", "analogy", "perspective"),
        question_families=("analogy", "novel_alternatives", "comparison",
                           "counterfactual"),
        thinking_styles=("analogy", "maximum_diversity", "counterfactual",
                         "assumption_reversal", "exploration"),
        category_groups=("question", "method", "instruction", "persona")),
    LensFamily.MISSING_INFORMATION: LensDefinition(
        LensFamily.MISSING_INFORMATION,
        ("missing_items", "evidence_needed", "prerequisites", "uncertainty",
         "information_gain", "gap_analysis"),
        context_types=("question", "method", "checklist", "consideration"),
        question_families=("missing_items", "evidence_needed",
                           "prerequisites", "uncertainty"),
        thinking_styles=("information_gain", "gap_analysis",
                         "uncertainty_calibration"),
        category_groups=("question", "method", "checklist", "instruction")),
    LensFamily.FAILURE_ADVERSARIAL: LensDefinition(
        LensFamily.FAILURE_ADVERSARIAL,
        ("failure", "adversarial_review", "premortem", "falsification",
         "top_avoid", "failure_recovery"),
        context_types=("question", "warning", "failure_pattern", "checklist"),
        question_families=("adversarial_review", "premortem", "falsification",
                           "top_avoid", "failure_recovery", "worst_way"),
        thinking_styles=("adversarial_review", "premortem", "falsification",
                         "failure_first", "failure_analysis", "avoidance"),
        category_groups=("question", "warning", "checklist", "instruction")),
    LensFamily.COST_RESOURCE: LensDefinition(
        LensFamily.COST_RESOURCE,
        ("cost_compression", "cost_value_analysis", "minimum_complexity",
         "budget", "resource", "efficiency"),
        context_types=("question", "method", "constraint", "consideration",
                       "heuristic", "persona"),
        question_families=("cost_compression", "constraint_review"),
        thinking_styles=("cost_value_analysis", "minimum_complexity",
                         "constraint_analysis", "prioritization"),
        category_groups=("question", "method", "constraint", "heuristic",
                         "persona", "instruction")),
    LensFamily.VERIFICATION_EVALUATION: LensDefinition(
        LensFamily.VERIFICATION_EVALUATION,
        ("verification", "evaluation", "rubric", "metric", "validate",
         "evidence_needed"),
        context_types=("evaluation", "rubric", "question", "checklist",
                       "method"),
        question_families=("evidence_needed", "falsification", "calibration"),
        thinking_styles=("verification", "statistical_reasoning",
                         "falsification", "uncertainty_calibration"),
        category_groups=("evaluation", "template", "checklist", "question",
                         "method", "validate"),
        response_shapes=("evaluation", "measurement_spec", "verdict")),
    LensFamily.OUTPUT_CONTRACT_FORMAT: LensDefinition(
        LensFamily.OUTPUT_CONTRACT_FORMAT,
        ("output_contract", "output_template", "response_shape",
         "serialization_format", "schema", "format_example"),
        context_types=("output_contract", "format_example", "template",
                       "prompt_fragment"),
        category_groups=("template",),
        categories=("output_template",)),
}

def _as_family(value: LensFamily | str) -> LensFamily:
    try:
        return value if isinstance(value, LensFamily) else LensFamily(value)
    except (TypeError, ValueError) as exc:
        raise IntelligencePortfolioError(
            f"unknown intelligence lens family {value!r}") from exc

@dataclass(frozen=True)
class BenchmarkCodeRegistration:
    """One admitted, benchmark-scoped Code asset with callable entrypoints."""

    spec: CodeAssetSpec
    benchmark_ids: tuple[str, ...]
    lens_families: tuple[LensFamily | str, ...]
    entrypoints: tuple[tuple[str, Callable], ...]

    def __post_init__(self) -> None:
        if self.spec.lifecycle != "registered" or not self.spec.admission_ref:
            raise IntelligencePortfolioError(
                "benchmark Code Intelligence must be registered through an "
                "admission_ref")
        benchmarks = tuple(str(value).strip() for value in self.benchmark_ids)
        if (not benchmarks or any(not value for value in benchmarks)
                or len(benchmarks) != len(set(benchmarks))):
            raise IntelligencePortfolioError(
                "benchmark_ids must contain unique non-empty identifiers")
        families = tuple(_as_family(value) for value in self.lens_families)
        if (not families or len(families) != len(set(families))):
            raise IntelligencePortfolioError(
                "a Code registration needs unique lens families")
        bound = dict(self.entrypoints)
        if (len(bound) != len(self.entrypoints)
                or set(bound) != set(self.spec.entrypoints)
                or any(not callable(value) for value in bound.values())):
            raise IntelligencePortfolioError(
                "Code entrypoints must bind every declared entrypoint exactly "
                "once to a real callable")
        object.__setattr__(self, "benchmark_ids", benchmarks)
        object.__setattr__(self, "lens_families", families)

    @property
    def entrypoint_map(self) -> dict[str, Callable]:
        return dict(self.entrypoints)


@dataclass(frozen=True)
class BenchmarkCodePack:
    """A small in-process pack; search cards never contain its callables."""

    pack_id: str
    registrations: tuple[BenchmarkCodeRegistration, ...]

    def __post_init__(self) -> None:
        if not self.pack_id.strip() or not self.registrations:
            raise IntelligencePortfolioError(
                "a benchmark Code pack needs an id and registrations")
        asset_ids = [item.spec.asset_id for item in self.registrations]
        payload_refs = [item.spec.body_ref.uri for item in self.registrations]
        if len(asset_ids) != len(set(asset_ids)):
            raise IntelligencePortfolioError("Code asset ids cannot repeat")
        if len(payload_refs) != len(set(payload_refs)):
            raise IntelligencePortfolioError("Code payload refs cannot repeat")

    def records_for(self, benchmark_id: str) -> list:
        """Registered search cards that explicitly name this benchmark."""
        from .store_serve import StoreRecord
        records = []
        for registration in self.registrations:
            if benchmark_id not in registration.benchmark_ids:
                continue
            base = code_asset_record(registration.spec)
            body = dict(base.body)
            metadata = dict(body.get("metadata") or {})
            metadata.update({
                "benchmark_ids": list(registration.benchmark_ids),
                "lens_families": [value.value
                                  for value in registration.lens_families],
                "code_pack_id": self.pack_id,
            })
            body["metadata"] = metadata
            facets = dict(body.get("facets") or {})
            facets.update({"domain": benchmark_id, "scope": "benchmark",
                           "lifecycle": "registered"})
            body["facets"] = facets
            tags = tuple(base.tags) + (
                f"benchmark:{benchmark_id}",
                *(f"lens:{value.value}"
                  for value in registration.lens_families),
            )
            records.append(StoreRecord(
                base.record_id, base.kind, base.title, body=body, tags=tags,
                tier="core", source=f"benchmark_code_pack:{self.pack_id}"))
        return records

    def resolve(self, payload_ref: str) -> MaterializedPayload:
        """Resolve an admitted body to its real callable entrypoint map."""
        for registration in self.registrations:
            if registration.spec.body_ref.uri == payload_ref:
                return MaterializedPayload(
                    registration.entrypoint_map,
                    registration.spec.body_ref.digest,
                    local_ref=payload_ref)
        raise KeyError(payload_ref)


@dataclass(frozen=True)
class PortfolioRequest:
    """One complete portfolio request for one consuming model-led Loop."""

    task: str
    consuming_loop_id: str
    benchmark_id: str = ""
    mode: str = "non_deterministic"
    lens_families: tuple[LensFamily | str, ...] = REQUIRED_LENS_FAMILIES

    def __post_init__(self) -> None:
        if not self.task.strip():
            raise IntelligencePortfolioError("a portfolio needs a task")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}",
                            self.consuming_loop_id):
            raise IntelligencePortfolioError("invalid consuming_loop_id")
        if self.mode != "non_deterministic":
            raise IntelligencePortfolioError(
                "intelligence portfolios are for non_deterministic "
                "consuming model-led Loops only")
        families = tuple(_as_family(value) for value in self.lens_families)
        if len(families) != len(set(families)):
            raise IntelligencePortfolioError(
                "duplicate lens families are refused")
        if set(families) != set(REQUIRED_LENS_FAMILIES):
            missing = sorted(value.value for value in
                             set(REQUIRED_LENS_FAMILIES) - set(families))
            raise PortfolioCoverageError(
                f"every required lens family must be requested; missing {missing}")
        object.__setattr__(self, "lens_families", families)


@dataclass
class PortfolioSelectionServices:
    """Injected stores and loop evidence for selection."""

    layer_records: Mapping[str, Sequence] | None = None
    code_pack: BenchmarkCodePack | None = None
    ledger: Any = None
    parent: Any = None


@dataclass
class PortfolioMaterializationServices:
    """Injected stores and resolvers for selected refs."""

    layer_records: Mapping[str, Sequence] | None = None
    code_pack: BenchmarkCodePack | None = None
    external_resolver: Callable[[str], object] | None = None
    ledger: Any = None
    parent: Any = None


@dataclass(frozen=True)
class LensQueryTrace:
    family: LensFamily
    retrieval_labels: tuple[str, ...]
    query_loop_id: str
    hits: int
    eligible_hits: int
    best_affinity_cohort: int
    selected_rank: int
    selected_ref: str
    empty_layers: tuple[str, ...]
    model_calls: int = 0

    def to_dict(self) -> dict:
        return {"family": self.family.value,
                "retrieval_labels": list(self.retrieval_labels),
                "query_loop_id": self.query_loop_id, "hits": self.hits,
                "eligible_hits": self.eligible_hits,
                "best_affinity_cohort": self.best_affinity_cohort,
                "selected_rank": self.selected_rank,
                "selected_ref": self.selected_ref,
                "empty_layers": list(self.empty_layers),
                "model_calls": self.model_calls}


@dataclass(frozen=True)
class PortfolioItem:
    family: LensFamily
    ref: LoopRef
    record_id: str
    layer: str
    public_label: str
    retrieval_rank: int
    retrieval_score: float
    affinity: int
    selection_reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {"family": self.family.value, "record_id": self.record_id,
                "layer": self.layer, "public_label": self.public_label,
                "retrieval_rank": self.retrieval_rank,
                "retrieval_score": self.retrieval_score,
                "affinity": self.affinity,
                "selection_reasons": list(self.selection_reasons),
                "loop_ref": self.ref.as_dict()}


@dataclass(frozen=True)
class LayerCoverage:
    layer: str
    public_key: str
    public_label: str
    supplied_records: int
    eligible_records: int
    excluded_candidate_records: int
    query_attempts: int
    unique_hits: int
    selected_refs: int
    state: str

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass(frozen=True)
class IntelligencePortfolio:
    portfolio_id: str
    task: str
    consuming_loop_id: str
    benchmark_id: str
    mode: str
    items: tuple[PortfolioItem, ...]
    query_traces: tuple[LensQueryTrace, ...]
    layer_coverage: tuple[LayerCoverage, ...]
    selection_model_calls: int = 0

    def __post_init__(self) -> None:
        families = [item.family for item in self.items]
        refs = [item.ref.loop_ref for item in self.items]
        if (len(self.items) != len(REQUIRED_LENS_FAMILIES)
                or set(families) != set(REQUIRED_LENS_FAMILIES)
                or len(families) != len(set(families))):
            raise PortfolioCoverageError(
                "a portfolio must contain one item per required lens family")
        if len(refs) != len(set(refs)):
            raise IntelligencePortfolioError(
                "one LoopRef cannot occupy two lens families")
        if self.mode != "non_deterministic" or self.selection_model_calls:
            raise IntelligencePortfolioError(
                "selection must stay scoped to non_deterministic consuming Loops and "
                "zero-model")

    @property
    def refs(self) -> tuple[LoopRef, ...]:
        return tuple(item.ref for item in self.items)

    def to_dict(self) -> dict:
        return {"record_type": SELECTOR_VERSION,
                "portfolio_id": self.portfolio_id, "task": self.task,
                "consuming_loop_id": self.consuming_loop_id,
                "benchmark_id": self.benchmark_id, "mode": self.mode,
                "bound": "one_unique_ref_per_required_lens_family",
                "items": [item.to_dict() for item in self.items],
                "query_traces": [trace.to_dict()
                                 for trace in self.query_traces],
                "layer_coverage": [row.to_dict()
                                   for row in self.layer_coverage],
                "selection_model_calls": self.selection_model_calls}


def _catalog(request: PortfolioRequest, services) -> dict:
    source = (services.layer_records if services.layer_records is not None
              else build_intelligence_catalog())
    normalized = normalize_layer_records(dict(source))
    catalog = {layer: list(normalized.get(layer) or ()) for layer in LAYERS}
    if services.code_pack is not None:
        additions = services.code_pack.records_for(request.benchmark_id)
        known = {record.record_id for record in catalog["code_intelligence"]}
        duplicate = [record.record_id for record in additions
                     if record.record_id in known]
        if duplicate:
            raise IntelligencePortfolioError(
                f"benchmark Code ids collide with the catalog: {duplicate}")
        catalog["code_intelligence"].extend(additions)
    return catalog
def _lifecycle(record) -> str:
    body = dict(record.body or {})
    facets = dict(body.get("facets") or {})
    return str(body.get("maturity") or facets.get("lifecycle")
               or record.tier)
def _eligible(record, *, benchmark_id: str, family: LensFamily) -> bool:
    lifecycle = _lifecycle(record)
    if (record.tier != "core" or lifecycle in
            {"draft", "candidate", "quarantined", "deprecated", "retired"}):
        return False
    body = dict(record.body or {})
    metadata = dict(body.get("metadata") or {})
    benchmark_ids = tuple(metadata.get("benchmark_ids") or ())
    families = tuple(metadata.get("lens_families") or ())
    if benchmark_ids and benchmark_id not in benchmark_ids:
        return False
    if families and family.value not in families:
        return False
    if body.get("role") == "code_asset":
        return (lifecycle == "registered" and bool(body.get("entrypoints"))
                and bool(body.get("admission_ref")))
    return True


def _affinity(definition: LensDefinition, hit: dict, record,
              benchmark_id: str) -> tuple[int, tuple[str, ...]]:
    classification = dict(hit.get("classification") or {})
    hierarchy = dict(classification.get("context_hierarchy") or {})
    body = dict(record.body or {})
    facets = dict(body.get("facets") or {})
    score = 0
    reasons = []

    def match(field: str, targets: tuple[str, ...], weight: int) -> None:
        nonlocal score
        value = str(hierarchy.get(field) or facets.get(field) or
                    body.get(field) or "")
        if value and value in targets:
            score += weight
            reasons.append(f"{field}:{value}")

    match("context_type", definition.context_types, 4)
    match("question_family", definition.question_families, 8)
    match("thinking_style", definition.thinking_styles, 8)
    match("response_shape", definition.response_shapes, 5)
    match("serialization_format", definition.serialization_formats, 4)
    group = str(classification.get("category_group") or "")
    category = str(classification.get("category") or "")
    if group in definition.category_groups:
        score += 3
        reasons.append(f"category_group:{group}")
    if category in definition.categories:
        score += 6
        reasons.append(f"category:{category}")
    if body.get("role") == "context_ontology_value":
        axis, value = str(body.get("axis", "")), str(body.get("value", ""))
        axis_targets = {
            "context_type": definition.context_types,
            "question_family": definition.question_families,
            "thinking_style": definition.thinking_styles,
            "response_shape": definition.response_shapes,
            "serialization_format": definition.serialization_formats,
        }
        if value in axis_targets.get(axis, ()):
            score += 2
            reasons.append(f"ontology:{axis}:{value}")
        score -= 3
    elif any(key in body for key in (
            "template", "instruction", "default_questions", "focus",
            "format_example", "entrypoints", "handle")):
        score += 2
        reasons.append("materializable_action")
    metadata = dict(body.get("metadata") or {})
    if (benchmark_id and benchmark_id in
            tuple(metadata.get("benchmark_ids") or ())
            and definition.family.value in
            tuple(metadata.get("lens_families") or ())):
        score += 100
        reasons.append(f"registered_benchmark_code:{benchmark_id}")
    return score, tuple(reasons)


def _portfolio_id(request: PortfolioRequest,
                  items: Sequence[PortfolioItem]) -> str:
    body = {"selector": SELECTOR_VERSION, "task": request.task,
            "consuming_loop_id": request.consuming_loop_id,
            "benchmark_id": request.benchmark_id,
            "items": [(item.family.value, item.ref.loop_ref, item.ref.digest)
                      for item in items]}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()).hexdigest()
    return f"intelligence-portfolio:{digest[:24]}"


def select_intelligence_portfolio(
        request: PortfolioRequest,
        services: PortfolioSelectionServices | None = None
) -> IntelligencePortfolio:
    """Map all four layers and choose one active ref per required family."""
    services = services or PortfolioSelectionServices()
    catalog = _catalog(request, services)
    index = {(layer, record.record_id): record
             for layer in LAYERS for record in catalog[layer]}
    population = sum(len(records) for records in catalog.values())
    used_refs = set()
    items, traces = [], []
    hit_ids = {layer: set() for layer in LAYERS}

    for family in request.lens_families:
        definition = LENS_DEFINITIONS[family]
        labels = tuple(label.replace("_", " ")
                       for label in definition.retrieval_labels)
        # Keep ontology labels inside the FTS backend's bounded term prefix.
        lexical_query = " ".join((*labels, request.benchmark_id, request.task))
        result = query_intelligence(
            lexical_query, catalog, mode="lexical", top_n=max(1, population),
            include_candidates=False, ledger=services.ledger,
            parent=services.parent)
        query_loop = dict(result["query_loop"])
        if query_loop.get("model_calls") != 0:
            raise IntelligencePortfolioError(
                "loop-native intelligence selection made a model call")
        candidates = []
        for rank, hit in enumerate(result["hits"], start=1):
            layer = hit["layer"]
            hit_ids[layer].add(hit["record_id"])
            record = index.get((layer, hit["record_id"]))
            if (record is None or not _eligible(
                    record, benchmark_id=request.benchmark_id, family=family)):
                continue
            ref = LoopRef.from_dict(hit["loop_ref"])
            if (ref.loop_ref in used_refs
                    or ref.handshake.maturity == "candidate"):
                continue
            affinity, reasons = _affinity(
                definition, hit, record, request.benchmark_id)
            candidates.append((affinity, float(hit.get("score", 0.0)),
                               rank, hit, ref, reasons))
        if not candidates:
            raise PortfolioCoverageError(
                f"active four-layer retrieval found no unique ref for "
                f"{family.value}")
        candidates.sort(key=lambda row: (-row[0], -row[1], row[2],
                                         row[4].loop_ref))
        best_affinity = candidates[0][0]
        cohort = [row for row in candidates if row[0] == best_affinity]
        lane_digest = hashlib.sha256(
            f"{request.consuming_loop_id}|{request.benchmark_id}|{family.value}"
            .encode()).digest()
        chosen = cohort[int.from_bytes(lane_digest[:8], "big") % len(cohort)]
        affinity, retrieval_score, rank, hit, ref, reasons = chosen
        used_refs.add(ref.loop_ref)
        item = PortfolioItem(
            family, ref, hit["record_id"], hit["layer"],
            hit["public_label"], rank, retrieval_score, affinity, reasons)
        items.append(item)
        traces.append(LensQueryTrace(
            family, definition.retrieval_labels,
            str(query_loop.get("loop_id", "")), len(result["hits"]),
            len(candidates), len(cohort), rank, ref.loop_ref,
            tuple(result["unqueried"]), model_calls=0))

    coverage = []
    for layer in LAYERS:
        records = catalog[layer]
        eligible = [record for record in records
                    if record.tier == "core" and _lifecycle(record) not in
                    {"draft", "candidate", "quarantined", "deprecated",
                     "retired"}]
        selected = sum(item.layer == layer for item in items)
        coverage.append(LayerCoverage(
            layer, LAYER_PUBLIC_KEY[layer], LAYER_PUBLIC_LABEL[layer],
            len(records), len(eligible), len(records) - len(eligible),
            len(request.lens_families), len(hit_ids[layer]), selected,
            "empty_visible" if not records else "queried"))
    return IntelligencePortfolio(
        _portfolio_id(request, items), request.task, request.consuming_loop_id,
        request.benchmark_id, request.mode, tuple(items), tuple(traces),
        tuple(coverage), selection_model_calls=0)
@dataclass(frozen=True)
class MaterializedLensValue:
    family: LensFamily
    ref: LoopRef
    value: object
    access_loop_id: str
    access_digest: str
    observed_payload_digest: str

    def evidence_dict(self) -> dict:
        return {"family": self.family.value, "loop_ref": self.ref.loop_ref,
                "ref_digest": self.ref.digest,
                "access_loop_id": self.access_loop_id,
                "access_digest": self.access_digest,
                "observed_payload_digest": self.observed_payload_digest,
                "value_type": type(self.value).__name__}
@dataclass(frozen=True)
class LoopIntelligenceConsumption:
    consuming_loop_id: str
    mode: str
    portfolio_id: str
    consumed: tuple[MaterializedLensValue, ...]
    materialization_model_calls: int
    record_digest: str

    def __post_init__(self) -> None:
        families = [item.family for item in self.consumed]
        refs = [item.ref.loop_ref for item in self.consumed]
        if self.mode != "non_deterministic":
            raise IntelligencePortfolioError(
                "consumption belongs to a non_deterministic consuming Loop")
        if (set(families) != set(REQUIRED_LENS_FAMILIES)
                or len(families) != len(set(families))
                or len(refs) != len(set(refs))):
            raise IntelligencePortfolioError(
                "consumption needs seven unique families and refs")
        if self.materialization_model_calls or not self.record_digest:
            raise IntelligencePortfolioError(
                "materialization must be zero-model and digest-addressed")

    @property
    def consumed_refs(self) -> tuple[str, ...]:
        return tuple(item.ref.loop_ref for item in self.consumed)

    def to_dict(self) -> dict:
        return {"record_type": "intelligence_consumption_record/v2",
                "consuming_loop_id": self.consuming_loop_id, "mode": self.mode,
                "portfolio_id": self.portfolio_id,
                "consumed": [item.evidence_dict() for item in self.consumed],
                "consumed_refs": list(self.consumed_refs),
                "materialization_model_calls":
                    self.materialization_model_calls,
                "record_digest": self.record_digest}

    def context_policy(self):
        """The exact ref projection accepted by typed consuming Loop delegation."""
        from ..loop.delegation_runtime import ContextVisibilityPolicy
        return ContextVisibilityPolicy(
            fresh=True, selected_refs=self.consumed_refs,
            shared_runtime_memory=False, summary_return=True)

    def run_history_fields(self) -> dict:
        """Fields for the eventual real model event; this emits no event."""
        return {"consumed_refs": self.consumed_refs,
                "detail": {"intelligence_portfolio_id": self.portfolio_id,
                           "intelligence_consumption_record":
                               self.record_digest}}
@dataclass(frozen=True)
class LoopIntelligenceMaterialization:
    portfolio: IntelligencePortfolio
    values: tuple[MaterializedLensValue, ...]
    consumption: LoopIntelligenceConsumption

    def values_by_family(self) -> dict[LensFamily, object]:
        return {item.family: item.value for item in self.values}
def _consumption_digest(portfolio: IntelligencePortfolio,
                        values: Sequence[MaterializedLensValue]) -> str:
    body = {"consuming_loop_id": portfolio.consuming_loop_id,
            "mode": portfolio.mode, "portfolio_id": portfolio.portfolio_id,
            "consumed": [(value.family.value, value.ref.loop_ref,
                          value.ref.digest, value.access_digest,
                          value.observed_payload_digest)
                         for value in values]}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True).encode()).hexdigest()
def materialize_portfolio_for_loop(
        portfolio: IntelligencePortfolio,
        services: PortfolioMaterializationServices | None = None
) -> LoopIntelligenceMaterialization:
    """Materialize selected refs and bind an exact consuming Loop consumption record."""
    services = services or PortfolioMaterializationServices()
    request = PortfolioRequest(
        portfolio.task, portfolio.consuming_loop_id,
        benchmark_id=portfolio.benchmark_id, mode=portfolio.mode)
    catalog = _catalog(request, services)
    def resolve_external(payload_ref: str):
        if services.code_pack is not None:
            try:
                return services.code_pack.resolve(payload_ref)
            except KeyError:
                pass
        if services.external_resolver is not None:
            return services.external_resolver(payload_ref)
        raise ValueError(f"no resolver registered for {payload_ref!r}")
    values = []
    for item in portfolio.items:
        out = materialize_intelligence_ref(
            item.ref, catalog, external_resolver=resolve_external,
            ledger=services.ledger, parent=services.parent)
        if out.get("model_calls") != 0:
            raise IntelligencePortfolioError(
                "intelligence materialization made a model call")
        values.append(MaterializedLensValue(
            item.family, item.ref, out["value"], str(out["loop_id"]),
            str(out["digest"]), str(out.get("payload_digest", ""))))
    consumption = LoopIntelligenceConsumption(
        portfolio.consuming_loop_id, portfolio.mode, portfolio.portfolio_id,
        tuple(values), 0, _consumption_digest(portfolio, values))
    return LoopIntelligenceMaterialization(
        portfolio, tuple(values), consumption)
def fold_loop_intelligence_consumption(
        consumptions: Sequence[LoopIntelligenceConsumption]) -> dict:
    """Fold exact per-consuming Loop consumption without conflating repeated refs."""
    consumptions = tuple(consumptions)
    consuming_ids = [record.consuming_loop_id for record in consumptions]
    if len(consuming_ids) != len(set(consuming_ids)):
        raise IntelligencePortfolioError(
            "one fold cannot contain duplicate consuming Loop identities")
    families = {family.value: 0 for family in REQUIRED_LENS_FAMILIES}
    unique_refs = set()
    by_consuming_loop = {}
    for record in consumptions:
        if record.mode != "non_deterministic":
            raise IntelligencePortfolioError(
                "only non_deterministic consuming Loop consumption can be folded")
        by_consuming_loop[record.consuming_loop_id] = list(record.consumed_refs)
        unique_refs.update(record.consumed_refs)
        for item in record.consumed:
            families[item.family.value] += 1
    body = {"consuming_loops": consuming_ids, "by_consuming_loop": by_consuming_loop,
            "lens_family_uses": families,
            "unique_refs": sorted(unique_refs)}
    return {"record_type": "intelligence_consumption_fold/v2",
            "consuming_loop_count": len(consumptions), "by_consuming_loop": by_consuming_loop,
            "lens_family_uses": families,
            "unique_ref_count": len(unique_refs),
            "fold_digest": hashlib.sha256(
                json.dumps(body, sort_keys=True).encode()).hexdigest()}


def export_intelligence_portfolios(
        portfolios: Sequence[IntelligencePortfolio],
        consumptions: Sequence[LoopIntelligenceConsumption] = ()) -> dict:
    """Body-free evidence export for mapped portfolios and folded use."""
    portfolios = tuple(portfolios)
    known = {portfolio.portfolio_id for portfolio in portfolios}
    unknown = [record.portfolio_id for record in consumptions
               if record.portfolio_id not in known]
    if unknown:
        raise IntelligencePortfolioError(
            f"consumption refers to portfolios absent from the export: {unknown}")
    return {"record_type": "intelligence_portfolio_export/v2",
            "portfolios": [portfolio.to_dict() for portfolio in portfolios],
            "consumption": fold_loop_intelligence_consumption(consumptions),
            "payload_bodies_exported": False}


def self_test() -> dict:
    """Run real-catalog and real-callable checks from the test companion."""
    from .intelligence_portfolio_checks import run_checks
    return run_checks()
