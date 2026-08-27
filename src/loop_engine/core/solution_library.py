"""Searchable prior solutions with typed task compatibility.

``SolutionLibrary`` stores passive Solution assets in a supplied store. A hit
is prior evidence, never proof that the solution applies again. New records
emit a versioned ``TaskFingerprint`` mapping. The pre-v1 pipe-delimited value
is accepted only by the exact compatibility reader in ``task_fingerprint``.

The library discovers and assesses candidates. It does not select or execute
them, compile a Solution Canvas, promote a candidate, or own storage.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .resolution import (
    ResolutionCandidate,
    ResolutionEligibility,
    ResolutionOrigin,
)
from .task_fingerprint import (
    TaskFingerprint,
    TaskFingerprintError,
    TaskFingerprintRequest,
    assess_compatibility,
    parse_task_fingerprint,
    task_fingerprint,
)


def _observed_number(value: object) -> float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _verification_strength(maturity: str, runtime: dict) -> float:
    observed = _observed_number(runtime.get("verification_strength"))
    if observed is not None:
        return max(0.0, min(1.0, observed))
    return {
        "candidate": 0.0,
        "draft": 0.0,
        "validated": 0.7,
        "registered": 0.8,
        "quarantined": 0.0,
        "deprecated": 0.0,
        "superseded": 0.0,
        "retired": 0.0,
    }.get(maturity, 0.0)


def _resolution_eligibility(maturity: str) -> ResolutionEligibility:
    if maturity == "registered":
        return ResolutionEligibility.EXECUTABLE
    if maturity in ("draft", "candidate", "validated"):
        return ResolutionEligibility.CANDIDATE_ONLY
    return ResolutionEligibility.UNAVAILABLE


@dataclass
class SolutionAsset:
    """Passive references, evidence, runtime observations, and lineage."""

    asset_id: str
    spec_record_id: str
    fingerprint: TaskFingerprint | dict | str
    compiled_digest: str = ""
    evaluation_evidence: tuple = ()
    runtime: dict = field(default_factory=dict)
    failure_history: tuple = ()
    applicability: str = ""
    lineage: tuple = ()
    maturity: str = "candidate"

    def __post_init__(self) -> None:
        self.fingerprint = parse_task_fingerprint(self.fingerprint)
        if self.maturity not in (
                "draft", "candidate", "validated", "registered", "quarantined",
                "deprecated", "superseded", "retired"):
            raise ValueError("solution maturity is not recognized")

    def to_record(self):
        from .facets import string_facets
        from .store_serve import StoreRecord

        fingerprint = self.fingerprint
        assert isinstance(fingerprint, TaskFingerprint)
        return StoreRecord(
            f"solasset.{self.asset_id}",
            "strategy",
            (f"Solution asset: {self.asset_id}: {fingerprint.problem} "
             f"{fingerprint.output_role} ({fingerprint.metric or 'any'}, "
             f"{fingerprint.scale_band.value} {fingerprint.modality})"),
            body={
                "role": "solution_asset",
                "fingerprint": fingerprint.to_dict(),
                "fingerprint_digest": fingerprint.digest,
                "spec_record_id": self.spec_record_id,
                "compiled_digest": self.compiled_digest,
                "evaluation_evidence": list(self.evaluation_evidence),
                "runtime": dict(self.runtime),
                "failure_history": list(self.failure_history),
                "applicability": self.applicability,
                "lineage": list(self.lineage),
                "maturity": self.maturity,
                "facets": string_facets(
                    category="solution_asset",
                    subcategory=fingerprint.problem,
                    lifecycle=self.maturity),
            },
            tags=(
                "solution_asset", fingerprint.problem, fingerprint.output_role,
                fingerprint.scale_band.value, fingerprint.modality,
                self.maturity),
        )


class SolutionLibrary:
    """Search prior Solution assets through a supplied store."""

    def __init__(self, store) -> None:
        self._store = store

    def add(self, asset: SolutionAsset) -> str:
        if not isinstance(asset, SolutionAsset):
            raise TypeError("SolutionLibrary.add needs SolutionAsset")
        record = asset.to_record()
        self._store.add(record)
        return record.record_id

    def _assessed_records(
            self, fingerprint: TaskFingerprint) -> list[tuple[object, object]]:
        from ..loop.intelligence_loops import (
            search_as_loop,
            serve_record_as_loop,
        )

        result = search_as_loop(
            self._store,
            f"solution_asset {fingerprint.search_text()}",
            pillar="runtime_history_solution_intelligence")["value"]
        assessed: list[tuple[object, object]] = []
        for hit in result.get("hits", ()):
            if (hit.get("facets") or {}).get("category") != "solution_asset":
                continue
            record = serve_record_as_loop(
                self._store, hit["record_id"],
                pillar="runtime_history_solution_intelligence")["value"]
            if record is None:
                continue
            try:
                candidate_fingerprint = parse_task_fingerprint(
                    record.body.get("fingerprint"))
            except TaskFingerprintError:
                continue
            assessment = assess_compatibility(
                fingerprint, candidate_fingerprint)
            assessed.append((record, assessment))
        assessed.sort(key=lambda pair: (
            not pair[1].exact,
            bool(pair[1].hard_failures),
            pair[0].record_id,
        ))
        return assessed

    def find_candidates(
            self, fingerprint: TaskFingerprint, *,
            top_n: int = 5) -> tuple[ResolutionCandidate, ...]:
        """Return typed candidates with hard and soft compatibility evidence."""
        if not isinstance(fingerprint, TaskFingerprint):
            raise TypeError("find_candidates needs TaskFingerprint")
        if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
            raise ValueError("top_n must be a positive integer")
        candidates: list[ResolutionCandidate] = []
        for record, assessment in self._assessed_records(fingerprint):
            body = record.body
            candidate_fingerprint = parse_task_fingerprint(body["fingerprint"])
            runtime = body.get("runtime") or {}
            maturity = body.get("maturity") or "candidate"
            candidates.append(ResolutionCandidate(
                candidate_ref=record.record_id,
                origin=(ResolutionOrigin.EXACT_REUSE if assessment.exact
                        else ResolutionOrigin.PARAMETERIZED_REUSE),
                fingerprint=candidate_fingerprint,
                compatibility=assessment,
                eligibility=_resolution_eligibility(maturity),
                source_state=maturity,
                expected_quality=_observed_number(runtime.get("quality")),
                expected_cost=_observed_number(runtime.get("cost")),
                expected_latency_seconds=_observed_number(
                    runtime.get("wall_seconds")),
                verification_strength=_verification_strength(
                    maturity, runtime),
                evidence_refs=(f"solution_asset:{record.record_id}",),
            ))
        return tuple(candidates[:top_n])

    def find_similar(
            self, fingerprint: TaskFingerprint, *, top_n: int = 5) -> list[dict]:
        """Return a compatibility projection for existing callers and reports."""
        candidates = self.find_candidates(fingerprint, top_n=top_n)
        return [{
            **candidate.to_dict(),
            "record_id": candidate.candidate_ref,
            "fingerprint_digest": candidate.fingerprint.digest,
            "exact_fingerprint_match": candidate.compatibility.exact,
            "prior_not_proof": True,
        } for candidate in candidates]


def self_test() -> dict:
    tests = []

    def check(name, ok, note=""):
        tests.append({"name": name, "passed": bool(ok), "note": note})

    from .resolution import (
        ResolutionRequest,
        select_resolution_as_loop,
    )
    from .store_serve import SolverStore, StoreRecord

    requested = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="addicted_label",
        metric="roc_auc", rows=691_369, modality="tabular",
        operator="predict", response_topology="label",
        input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1"))
    related = task_fingerprint(TaskFingerprintRequest(
        problem="classification", output_role="Survived",
        metric="accuracy", rows=891, modality="tabular",
        operator="predict", response_topology="label",
        input_contract="tabular_dataset/v1",
        output_contract="prediction_labels/v1"))
    regression = task_fingerprint(TaskFingerprintRequest(
        problem="regression", output_role="price", metric="rmse",
        rows=50_000, modality="tabular", operator="predict",
        response_topology="score", input_contract="tabular_dataset/v1",
        output_contract="prediction_scores/v1"))

    store = SolverStore()
    library = SolutionLibrary(store)
    library.add(SolutionAsset(
        "s6e8_lightgbm", "solution.tabular_lightgbm", requested,
        compiled_digest="d" * 64, maturity="registered",
        runtime={"quality": 0.95, "cost": 0.1, "wall_seconds": 2.0,
                 "verification_strength": 1.0}))
    library.add(SolutionAsset(
        "titanic_lightgbm", "solution.tabular_lightgbm_titanic", related,
        maturity="validated",
        runtime={"quality": 0.8, "cost": 0.05, "wall_seconds": 1.0}))
    library.add(SolutionAsset(
        "house_ridge", "solution.tabular_ridge", regression,
        maturity="registered"))
    legacy_record = StoreRecord(
        "solasset.legacy", "strategy", "Legacy classification solution",
        body={
            "role": "solution_asset",
            "fingerprint": "tabular|classification|legacy_label|accuracy|small",
            "runtime": {}, "maturity": "registered",
            "facets": {"category": "solution_asset"},
        },
        tags=("solution_asset", "classification", "legacy_label"))
    store.add(legacy_record)

    current_record = SolutionAsset(
        "current", "solution.current", requested).to_record()
    check("new_solution_records_emit_typed_fingerprints",
          isinstance(current_record.body["fingerprint"], dict)
          and current_record.body["fingerprint"]["schema_version"]
              == "task_fingerprint/v1")
    candidates = library.find_candidates(requested, top_n=10)
    refs = {candidate.candidate_ref for candidate in candidates}
    check("legacy_and_current_solution_records_are_read",
          "solasset.legacy" in refs and "solasset.s6e8_lightgbm" in refs)
    exact = next(candidate for candidate in candidates
                 if candidate.candidate_ref == "solasset.s6e8_lightgbm")
    wrong_family = next(candidate for candidate in candidates
                        if candidate.candidate_ref == "solasset.house_ridge")
    check("compatibility_is_typed_and_family_safe",
          exact.compatibility.exact
          and not wrong_family.compatibility.compatible)
    run = select_resolution_as_loop(ResolutionRequest(
        requested, candidates, maximum_cost=1.0,
        maximum_latency_seconds=10.0,
        minimum_quality=0.7,
        minimum_verification_strength=0.7))
    check("verified_exact_reuse_is_selected_through_loop",
          run.decision.selected_candidate_ref == "solasset.s6e8_lightgbm"
          and run.model_calls == 0)
    projected = library.find_similar(requested, top_n=10)
    check("prior_projection_never_claims_present_proof",
          projected and all(item["prior_not_proof"] for item in projected))
    return {"tests": tests}


__all__ = (
    "SolutionAsset", "SolutionLibrary", "TaskFingerprint",
    "TaskFingerprintRequest", "task_fingerprint",
)
