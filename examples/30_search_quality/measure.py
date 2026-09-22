"""Measure how well catalogue search returns the right references.

The customer's coding tool asks for what one step needs and reads the first
few references. So the numbers that matter are: did the right item come back
at all, and where in the order. An average over every query hides the queries
that fail, so this module reports the failures by name.

WHAT THIS IS AND IS NOT
This is a ranking measurement over a fixed set of queries with the items that
should be returned for each. It is not a full-system Loop Engine benchmark: no
task population runs, no model is called, nothing is executed and nothing is
accepted. It says one thing only, about one ordering.

HOW A COMPARISON STAYS HONEST
Every query carries a split decided from the text of the query itself, so no
result can move a query between the two groups. A policy is chosen by reading
the development group and reported on both. If a change helps only the group
it was chosen on, the two numbers say so.

```text
Measurement
├── Population: every query in the judgement file, counted whole
│   ├── Origin
│   │   ├── starter_catalogue_search_queries/v1   the catalogue's own smoke queries,
│   │   │                                         whose purposes were edited until they
│   │   │                                         passed, so not independent evidence
│   │   └── written_for_this_measurement          written from titles and tags before
│   │                                             any ranking was measured
│   └── Split, from the query text
│       ├── development   read while choosing a policy
│       └── held_back     read once, after the choice
├── Answerable queries, measured by
│   ├── found_at_all      a relevant item appears anywhere in the returned order
│   ├── recall_at_1 / recall_at_3 / recall_at_10
│   └── mean_reciprocal_rank
└── Unanswerable queries, measured by
    └── answered_confidently   a hit returned for a request the catalogue cannot serve
```
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY / "src") not in sys.path:
    sys.path.insert(0, str(REPOSITORY / "src"))

from loop_engine.core.contract_matching import (  # noqa: E402
    CANONICAL, EXACT, PURPOSE, SEMANTIC_BLOCKED)
from loop_engine.core.harness_intelligence import (  # noqa: E402
    HarnessIntelligenceCatalogue, HarnessIntelligenceItem)
from loop_engine.core.harness_intelligence_search import (  # noqa: E402
    DEFAULT_SEARCH_POLICY, SEARCHABLE_FIELDS, SERVED_BEFORE_2026_09_21,
    CatalogueSearchField, CatalogueSearchPolicy, PreparedCatalogueSearch)
from loop_engine.core.intelligence_tagging import TagSet  # noqa: E402

RECORD_TYPE = "catalogue_search_measurement/v1"
JUDGEMENT_RECORD_TYPE = "catalogue_search_judgements/v1"
#: The positions a customer's coding tool actually reads.
CUT_OFFS = (1, 3, 10)
#: How deep the measurement looks before calling an item missing.
DEPTH = 20
DEFAULT_CATALOGUE = REPOSITORY / "examples/29_intelligence_service/starter-catalogue"
DEFAULT_JUDGEMENTS = Path(__file__).resolve().parent / "relevance-judgements.json"


class MeasurementError(ValueError):
    """The catalogue or the judgements cannot be read as this measurement needs."""


def _fields(**weights) -> tuple[CatalogueSearchField, ...]:
    """Every searchable field named once, so a weight of zero is a decision."""
    return tuple(CatalogueSearchField(name, weights.get(name, 0)) for name in SEARCHABLE_FIELDS)


#: The policies compared. Each names its match mode and the fields it reads, so
#: the difference between two rows of the report is a declared difference and
#: not a remembered one. Adding a row here adds a column to the comparison.
CANDIDATE_POLICIES = {
    "served_before": SERVED_BEFORE_2026_09_21,
    # The strictest mode is measured rather than assumed unsuitable. A customer
    # types in lower case and a purpose is written as a sentence, so letter for
    # letter comparison is expected to do badly; the row says how badly.
    "exact_purpose_and_identity": CatalogueSearchPolicy(
        EXACT, _fields(purpose=2, identity=1)),
    "canonical_purpose_only": CatalogueSearchPolicy(CANONICAL, _fields(purpose=1)),
    "canonical_purpose_and_identity": CatalogueSearchPolicy(
        CANONICAL, _fields(purpose=2, identity=1)),
    "purpose_fold_purpose_only": CatalogueSearchPolicy(PURPOSE, _fields(purpose=1)),
    "purpose_fold_purpose_and_identity": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1)),
    "purpose_fold_with_tags": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1, tags=2)),
    "purpose_fold_with_tags_and_layer": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1, tags=2, source_layer=1, kind=1)),
    "purpose_fold_identity_led": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=1, identity=3, tags=2)),
    "purpose_fold_common_term_ceiling": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1, tags=2), common_term_ceiling=0.2),
    "semantic_blocked_on_language": CatalogueSearchPolicy(
        SEMANTIC_BLOCKED, _fields(purpose=2, identity=1, tags=2),
        blocking_dimensions=("language",), coverage_floor=0.2),
    # A floor buys silence on a request this catalogue cannot serve and pays
    # for it in recall. The report shows both sides of that trade.
    "purpose_fold_floor_20": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1), coverage_floor=0.2),
    "purpose_fold_floor_30": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1), coverage_floor=0.3),
    "purpose_fold_floor_40": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1), coverage_floor=0.4),
    "purpose_fold_floor_50": CatalogueSearchPolicy(
        PURPOSE, _fields(purpose=2, identity=1), coverage_floor=0.5),
    "default": DEFAULT_SEARCH_POLICY,
}


@dataclass(frozen=True)
class Judgement:
    """One request and the items that should come back for it."""

    query: str
    relevant: tuple[str, ...]
    written_by: str
    origin: str
    split: str

    @property
    def answerable(self) -> bool:
        return bool(self.relevant)


def load_catalogue(folder: Path) -> HarnessIntelligenceCatalogue:
    """Register every published item of a starter catalogue, as the service holds it."""
    published = json.loads((folder / "items.json").read_text(encoding="utf-8"))
    rows = published.get("items")
    if not isinstance(rows, list) or not rows:
        raise MeasurementError(f"{folder}/items.json holds no items")
    catalogue = HarnessIntelligenceCatalogue()
    for row in rows:
        reference = row["reference"]
        tags = {name: tuple(values) for name, values in reference["tags"].items()
                if name != "record_type"}
        catalogue.register(HarnessIntelligenceItem(
            identity=reference["identity"], kind=reference["kind"],
            purpose=reference["purpose"], digest=reference["digest"],
            source_layer=reference["source_layer"], source_ref=reference["source_ref"],
            size_bytes=reference["size_bytes"], license_name=reference["license"],
            declared_effects=tuple(reference["declared_effects"]),
            styles=tuple(reference["styles"]),
            default_exposure=reference["exposure"], availability=reference["availability"],
            tags=TagSet(tags)))
    return catalogue


def load_judgements(path: Path, catalogue: HarnessIntelligenceCatalogue) -> tuple[Judgement, ...]:
    """Read the judgements and refuse one that names an item this catalogue does not hold."""
    record = json.loads(path.read_text(encoding="utf-8"))
    if record.get("record_type") != JUDGEMENT_RECORD_TYPE:
        raise MeasurementError(
            f"{path} is not a {JUDGEMENT_RECORD_TYPE} record; the measurement will not "
            "guess what an unknown judgement shape means")
    rows = []
    for entry in record["judgements"]:
        unknown = [name for name in entry["relevant"] if name not in catalogue.items]
        if unknown:
            raise MeasurementError(
                f"query {entry['query']!r} expects {unknown}, which this catalogue "
                "does not hold; a judgement is measured against the catalogue it names")
        rows.append(Judgement(entry["query"], tuple(entry["relevant"]),
                              entry["written_by"], entry["origin"], entry["split"]))
    if not rows:
        raise MeasurementError(f"{path} holds no judgements")
    return tuple(rows)


def _first_relevant_rank(order: "list[str]", relevant: "tuple[str, ...]") -> int:
    """The one based position of the first item that should have been returned, or zero."""
    for position, identity in enumerate(order, 1):
        if identity in relevant:
            return position
    return 0


def _blank_totals() -> dict:
    return {"answerable": 0, "found_at_all": 0, "reciprocal_rank_total": 0.0,
            "unanswerable": 0, "answered_confidently": 0,
            **{f"hit_at_{cut}": 0 for cut in CUT_OFFS}}


def _accumulate(totals: dict, judgement: Judgement, rank: int, returned: int) -> None:
    if not judgement.answerable:
        totals["unanswerable"] += 1
        totals["answered_confidently"] += 1 if returned else 0
        return
    totals["answerable"] += 1
    if rank:
        totals["found_at_all"] += 1
        totals["reciprocal_rank_total"] += 1.0 / rank
        for cut in CUT_OFFS:
            if rank <= cut:
                totals[f"hit_at_{cut}"] += 1


def _finish(totals: dict) -> dict:
    answerable = totals["answerable"]
    report = {"answerable_queries": answerable,
              "found_at_all": totals["found_at_all"],
              "unanswerable_queries": totals["unanswerable"],
              "answered_confidently": totals["answered_confidently"]}
    for cut in CUT_OFFS:
        report[f"recall_at_{cut}"] = (round(totals[f"hit_at_{cut}"] / answerable, 4)
                                      if answerable else None)
    report["mean_reciprocal_rank"] = (round(totals["reciprocal_rank_total"] / answerable, 4)
                                      if answerable else None)
    return report


def measure(catalogue: HarnessIntelligenceCatalogue, judgements, policy: CatalogueSearchPolicy,
            *, depth: int = DEPTH) -> dict:
    """Run one policy over every judgement and report the numbers and the failures by name.

    A group is any label a judgement carries: its split and its origin. Groups
    are read from the judgements rather than written here, so a new group in
    the file appears in the report without a change to this module.
    """
    if not isinstance(policy, CatalogueSearchPolicy):
        raise MeasurementError("a typed search policy is required")
    prepared = PreparedCatalogueSearch(catalogue, policy)
    overall = _blank_totals()
    groups: dict = {}
    failures, confident = [], []
    for judgement in judgements:
        result = prepared.search(judgement.query, top_n=depth)
        order = [hit["identity"] for hit in result["hits"]]
        rank = _first_relevant_rank(order, judgement.relevant)
        _accumulate(overall, judgement, rank, len(order))
        for label in (f"split:{judgement.split}", f"origin:{judgement.origin}"):
            _accumulate(groups.setdefault(label, _blank_totals()), judgement, rank, len(order))
        if judgement.answerable and (rank == 0 or rank > CUT_OFFS[1]):
            failures.append({"query": judgement.query, "expected": list(judgement.relevant),
                             "rank": rank, "split": judgement.split, "origin": judgement.origin,
                             "returned_first": order[:CUT_OFFS[1]]})
        if not judgement.answerable and order:
            confident.append({"query": judgement.query, "split": judgement.split,
                              "returned_first": order[:CUT_OFFS[1]]})
    return {"policy": policy.to_dict(), "depth": depth,
            "queries": len(judgements), "overall": _finish(overall),
            "groups": {label: _finish(totals) for label, totals in sorted(groups.items())},
            "failed_queries": failures,
            "unanswerable_queries_answered": confident}


def compare(catalogue: HarnessIntelligenceCatalogue, judgements, policies: dict,
            *, depth: int = DEPTH) -> dict:
    """Run every named policy over the same queries and keep the whole comparison."""
    measurements = {name: measure(catalogue, judgements, policy, depth=depth)
                    for name, policy in policies.items()}
    table = [{"policy": name,
              "development_recall_at_1": row["groups"]["split:development"]["recall_at_1"],
              "held_back_recall_at_1": row["groups"]["split:held_back"]["recall_at_1"],
              "development_recall_at_3": row["groups"]["split:development"]["recall_at_3"],
              "held_back_recall_at_3": row["groups"]["split:held_back"]["recall_at_3"],
              "development_mean_reciprocal_rank":
                  row["groups"]["split:development"]["mean_reciprocal_rank"],
              "held_back_mean_reciprocal_rank":
                  row["groups"]["split:held_back"]["mean_reciprocal_rank"],
              "overall_recall_at_3": row["overall"]["recall_at_3"],
              "overall_recall_at_10": row["overall"]["recall_at_10"],
              "overall_found_at_all": row["overall"]["found_at_all"],
              "overall_mean_reciprocal_rank": row["overall"]["mean_reciprocal_rank"],
              "failing_queries": len(row["failed_queries"]),
              "unanswerable_answered": row["overall"]["answered_confidently"]}
             for name, row in measurements.items()]
    return {"record_type": RECORD_TYPE, "catalogue_items": len(catalogue.items),
            "queries": len(judgements), "cut_offs": list(CUT_OFFS), "depth": depth,
            "comparison": table, "measurements": measurements}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--catalogue", type=Path, default=DEFAULT_CATALOGUE)
    parser.add_argument("--judgements", type=Path, default=DEFAULT_JUDGEMENTS)
    parser.add_argument("--policy", action="append", default=[],
                        help="measure only these named policies; repeatable")
    parser.add_argument("--depth", type=int, default=DEPTH)
    parser.add_argument("--report", type=Path, default=None,
                        help="write the whole comparison to this file")
    parser.add_argument("--failures", action="store_true",
                        help="print every failing query by name")
    arguments = parser.parse_args(argv)
    catalogue = load_catalogue(arguments.catalogue)
    judgements = load_judgements(arguments.judgements, catalogue)
    chosen = {name: CANDIDATE_POLICIES[name] for name in arguments.policy} or CANDIDATE_POLICIES
    report = compare(catalogue, judgements, chosen, depth=arguments.depth)
    if arguments.report is not None:
        arguments.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in
                      ("record_type", "catalogue_items", "queries", "comparison")}, indent=2))
    if arguments.failures:
        for name in chosen:
            for row in report["measurements"][name]["failed_queries"]:
                print(f"{name}\t{row['split']}\trank={row['rank']}\t{row['query']}"
                      f"\texpected={row['expected']}\tgot={row['returned_first']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
