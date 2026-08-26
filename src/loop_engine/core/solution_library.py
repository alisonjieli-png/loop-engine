"""Solution Library — first-class composite Solution Assets, searchable.

Architectural role: internal solution storage and search service.

Owns:
    - SolutionAsset: the first-class COMPOSITE object — it reduces entirely
      to the two foundational forms (spec/manifest/evidence/history are
      Strings; the compiled solution is a composite Code Node) and is NEVER
      a third primitive;
    - the task fingerprint (problem kind, output role, metric, scale band,
      modality) used as the similarity key;
    - find_similar: search the library by fingerprint + facets and return
      ranked PRIORS — a prior Solution is a STARTING POINT, never proof it
      will work again (every result carries that stance).

Does not own:
    - solution semantics (solution_canvas), compilation (solution_compiler),
      promotion (asset_lifecycle), or the store engine (store_serve /
      duckdb_catalog serve the records like any other Strings).

Public entry points:
    - SolutionAsset(...).to_record() / fingerprint()
    - task_fingerprint(problem, output_role, metric, rows, modality)
    - SolutionLibrary(store).add(asset) / find_similar(fingerprint)

Key invariants:
    - every hit is labeled prior_not_proof=True;
    - evidence/scores ride the record with their honesty labels intact.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _scale_band(rows: int) -> str:
    if rows < 10_000:
        return "small"
    if rows < 1_000_000:
        return "medium"
    return "large"


def task_fingerprint(*, problem: str, output_role: str, metric: str = "",
                     rows: int = 0, modality: str = "tabular") -> str:
    """The similarity key: coarse enough to match FAMILIES, precise enough
    to keep regression away from classification."""
    return "|".join((modality, problem, output_role, metric or "any",
                     _scale_band(rows)))


@dataclass
class SolutionAsset:
    """The composite: references, evidence, boundaries — Strings all the way
    down, plus the compiled Code Node's digest."""
    asset_id: str
    spec_record_id: str                 # the SolutionSpec String
    fingerprint: str
    compiled_digest: str = ""           # the composite Code Node's plan digest
    evaluation_evidence: tuple = ()     # honesty-labeled score lines
    runtime: dict = field(default_factory=dict)   # calls/tokens/wall observed
    failure_history: tuple = ()
    applicability: str = ""
    lineage: tuple = ()                 # parent assets / originating runs
    maturity: str = "candidate"

    def to_record(self):
        from .store_serve import StoreRecord
        from .facets import string_facets
        modality, problem, out_role, metric, band = \
            (self.fingerprint.split("|") + ["", "", "", "", ""])[:5]
        return StoreRecord(
            f"solasset.{self.asset_id}", "strategy",
            f"Solution asset: {self.asset_id} — {problem} {out_role} "
            f"({metric}, {band} {modality})",
            body={"role": "solution_asset",
                  "fingerprint": self.fingerprint,
                  "spec_record_id": self.spec_record_id,
                  "compiled_digest": self.compiled_digest,
                  "evaluation_evidence": list(self.evaluation_evidence),
                  "runtime": dict(self.runtime),
                  "failure_history": list(self.failure_history),
                  "applicability": self.applicability,
                  "lineage": list(self.lineage),
                  "maturity": self.maturity,
                  "facets": string_facets(category="solution_asset",
                                          subcategory=problem,
                                          lifecycle=self.maturity)},
            tags=("solution_asset", problem, out_role, band, modality,
                  self.maturity))


class SolutionLibrary:
    """The searchable library over any store backend (file or DuckDB)."""

    def __init__(self, store):
        self._store = store

    def add(self, asset: SolutionAsset) -> str:
        rec = asset.to_record()
        self._store.add(rec)
        return rec.record_id

    def find_similar(self, fingerprint: str, *, top_n: int = 5) -> list:
        """Ranked priors: exact-fingerprint hits first, then same
        problem/output family.  Every hit says prior_not_proof."""
        modality, problem, out_role = (fingerprint.split("|") + ["", ""])[:3]
        from ..loop.intelligence_loops import search_as_loop
        res = search_as_loop(
            self._store, f"solution_asset {modality} {problem} {out_role}",
            pillar="runtime_history_solution_intelligence")["value"]
        hits = []
        for h in res.get("hits", ()):
            if (h.get("facets") or {}).get("category") != "solution_asset":
                continue
            from ..loop.intelligence_loops import serve_record_as_loop
            rec = serve_record_as_loop(
                self._store, h["record_id"],
                pillar="runtime_history_solution_intelligence")["value"]
            if rec is None:
                continue
            their = (rec.body.get("fingerprint") or "").split("|")
            # HARD family filter: modality and problem kind must match — a
            # regression prior never advises a classification task.
            if their[:2] != [modality, problem]:
                continue
            exact = rec.body.get("fingerprint") == fingerprint
            hits.append({"record_id": h["record_id"],
                         "fingerprint": rec.body.get("fingerprint"),
                         "exact_fingerprint_match": exact,
                         "maturity": rec.body.get("maturity"),
                         "evaluation_evidence":
                             rec.body.get("evaluation_evidence", []),
                         "runtime": rec.body.get("runtime", {}),
                         "spec_record_id": rec.body.get("spec_record_id"),
                         "prior_not_proof": True})
        hits.sort(key=lambda x: (not x["exact_fingerprint_match"],
                                 x["maturity"] != "registered"))
        return hits[:top_n]


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .store_serve import SolverStore

    fp_s6e8 = task_fingerprint(problem="classification",
                               output_role="addicted_label",
                               metric="roc_auc", rows=691369)
    fp_titanic = task_fingerprint(problem="classification",
                                  output_role="Survived",
                                  metric="accuracy", rows=891)
    fp_reg = task_fingerprint(problem="regression", output_role="price",
                              metric="rmse", rows=50000)

    lib = SolutionLibrary(SolverStore())
    lib.add(SolutionAsset(
        "s6e8_lightgbm", "solution.tabular_lightgbm", fp_s6e8,
        compiled_digest="d" * 64,
        evaluation_evidence=("public roc_auc 0.95663 (SMOKE, one run — "
                             "never benchmark evidence)",),
        runtime={"model_calls": 1, "wall_seconds": 77.3},
        maturity="candidate"))
    lib.add(SolutionAsset(
        "titanic_lightgbm", "solution.tabular_lightgbm_titanic", fp_titanic,
        evaluation_evidence=("public 0.76794 (SMOKE)",),
        maturity="candidate"))
    lib.add(SolutionAsset(
        "house_ridge", "solution.tabular_ridge", fp_reg,
        maturity="candidate"))

    # 1. the fingerprint separates families (scale band, problem, metric).
    check("fingerprint_separates_task_families",
          fp_s6e8 == "tabular|classification|addicted_label|roc_auc|medium"
          and fp_titanic.endswith("|small") and "regression" in fp_reg,
          fp_s6e8)

    # 2. exact-fingerprint priors rank first; regression never leaks into a
    # classification query.
    hits = lib.find_similar(fp_s6e8)
    check("similar_solutions_rank_exact_first_and_stay_in_family",
          hits and hits[0]["record_id"] == "solasset.s6e8_lightgbm"
          and hits[0]["exact_fingerprint_match"]
          and all("regression" not in (h["fingerprint"] or "")
                  for h in hits),
          f"{len(hits)} priors; top is the exact-family asset")

    # 3. every hit carries the stance: a prior is not proof.
    check("every_prior_is_labeled_not_proof",
          all(h["prior_not_proof"] for h in hits))

    # 4. the asset reduces to the two foundational forms: the record is a
    # String; the compiled digest points at a composite Code Node.
    rec = SolutionAsset("x", "solution.x", fp_titanic,
                        compiled_digest="e" * 64).to_record()
    check("asset_reduces_to_strings_plus_a_code_node_digest",
          rec.body["role"] == "solution_asset"
          and len(rec.body["compiled_digest"]) == 64
          and rec.body["facets"]["category"] == "solution_asset",
          "no third primitive — a composite of the two")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
