"""Stage review-only intelligence through the existing authoritative catalogue.

This development tool creates a new isolated database, not a hosted catalogue.
It exports acknowledged candidate records and tests normal versus review search.
It grants no execution, disclosure, qualification or promotion authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import closing
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import time

from loop_engine.catalog.protocol import CatalogRecordPrecondition, CatalogWriteBatch, require_atomic_batch
from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.core.intelligence_layers import IntelligenceSearchRequest, query_intelligence, LAYERS
from loop_engine.core.store_serve import StoreRecord

# These are existing catalogue identifiers and their public retrieval projection.
CATALOG_LAYERS = dict(zip(("context", "code", "runtime_history_solution", "user_feedback"), LAYERS))
SPEC_FIELDS = {"id", "layer", "family", "title", "tags", "text", "sources", "symbols"}


@dataclass(frozen=True)
class CandidateStageRequest:
    repository: Path
    namespace: str
    writes_authorized: bool = False


def compile_candidates(specifications: dict, request: CandidateStageRequest) -> list[dict]:
    if specifications.get("record_type") != "candidate_intelligence_specifications/v1":
        raise ValueError("Unsupported candidate specification contract")
    if not re.fullmatch(r"[a-z][a-z0-9_.-]{1,80}", request.namespace):
        raise ValueError("An explicit bounded namespace is required")
    rows = specifications.get("specifications")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 50:
        raise ValueError("One bounded population of specifications is required")
    root, records, identities = request.repository.resolve(), [], set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) - SPEC_FIELDS or SPEC_FIELDS - {"symbols"} - set(row)
                or not isinstance(row["layer"], str) or row["layer"] not in CATALOG_LAYERS
                or not isinstance(row["id"], str) or not re.fullmatch(r"[a-z0-9_]{1,80}", row["id"])
                or row["id"] in identities or not all(isinstance(row[key], str) and row[key].strip()
                                                       for key in ("family", "title", "text"))
                or len(row["text"]) > 12000 or not isinstance(row["tags"], list)
                or not all(isinstance(tag, str) and tag.strip() for tag in row["tags"])
                or not isinstance(row["sources"], list) or not row["sources"]):
            raise ValueError("Candidate fields, identity or lifecycle are invalid")
        sources = []
        for relative in row["sources"]:
            if not isinstance(relative, str):
                raise ValueError("Source must be a repository path")
            path = root / relative
            if (Path(relative).is_absolute() or ".." in Path(relative).parts
                    or any(part.startswith(".") for part in Path(relative).parts)
                    or any(root.joinpath(*Path(relative).parts[:index]).is_symlink() for index in range(1, len(Path(relative).parts) + 1))
                    or root not in path.resolve().parents or not path.is_file()):
                raise ValueError("Source must be a confined visible repository file")
            sources.append({"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        payload = {"record_type": "candidate_intelligence_specification/v1", "title": row["title"],
                   "text": row["text"], "family": row["family"], "symbols": row.get("symbols", []),
                   "sources": sources, "authoring": "assistant_authored_from_repository_sources",
                   "qualification": "not_independently_qualified", "license_state": "pending_review",
                   "lifecycle": "candidate", "execution_available": False}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        version = hashlib.sha256(json.dumps({"payload": payload, "layer": row["layer"], "tags": row["tags"]},
                                           sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        identity = request.namespace + "." + row["id"]
        records.append({"record_id": identity, "record_version": version, "intelligence_layer": row["layer"],
                        "source_collection": "learned", "artifact_kind": "intelligence_record", "lifecycle": "candidate",
                        "namespace": request.namespace, "attributes": {"family": row["family"], "tags": row["tags"],
                        "title": row["title"], "content_sha256": digest, "license_state": "pending_review"}, "payload": payload})
        identities.add(row["id"])
    return records


def stage_candidates(store, records: list[dict], request: CandidateStageRequest):
    if request.writes_authorized is not True:
        raise ValueError("Candidate staging requires exact write authority")
    if any(row["namespace"] != request.namespace or row["lifecycle"] != "candidate"
           or row["payload"]["lifecycle"] != "candidate" or row["payload"]["execution_available"] is not False
           or not row["record_id"].startswith(request.namespace + ".") for row in records):
        raise ValueError("Staging cannot broaden namespace or promote a record")
    require_atomic_batch(store)
    batch = CatalogWriteBatch.from_records(records, [CatalogRecordPrecondition(row["record_id"], must_not_exist=True) for row in records])
    acknowledgment = store.apply_batch(batch)
    if acknowledgment.committed is not True or acknowledgment.batch_digest != batch.digest:
        raise RuntimeError("Candidate staging commit is unknown")
    if any(store.get(row["record_id"]) != row for row in records):
        raise RuntimeError("Candidate readback differs; commitment is not qualified")
    return acknowledgment


def review_search(records: list[dict]) -> dict:
    layers = {key: [] for key in LAYERS}
    for row in records:
        body = row["payload"]
        layers[CATALOG_LAYERS[row["intelligence_layer"]]].append(StoreRecord(row["record_id"], "context", body["title"],
            body={"text": body["text"], "lifecycle": "candidate", "category": body["family"],
                  "symbols": body["symbols"], "source_identities": body["sources"]},
            tags=tuple(row["attributes"]["tags"]), tier="experimental", source="candidate_review_catalogue"))
    default = query_intelligence(IntelligenceSearchRequest("review", layers))
    probes = []
    for row in records:
        started = time.perf_counter()
        result = query_intelligence(IntelligenceSearchRequest(row["attributes"]["title"], layers, top_n=3, include_candidates=True))
        probes.append({"expected_identity": row["record_id"], "returned": [hit["record_id"] for hit in result["hits"]],
                       "found_in_first_three": row["record_id"] in [hit["record_id"] for hit in result["hits"]],
                       "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                       "physical_model_calls": result["query_loop"]["model_calls"]})
    return {"normal_search_hits": len(default["hits"]), "normal_search_excluded": len(default["excluded"]), "probes": probes,
            "limits": "Title-derived lexical smoke probes on authored candidates, not a held-out relevance or task-success benchmark"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--specifications", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--authorize-isolated-staging", action="store_true")
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if (not args.authorize_isolated_staging or any(path.exists() or path.is_symlink() for path in (args.database, args.export, args.report))
            or len({path.resolve() for path in (args.database, args.export, args.report)}) != 3):
        parser.error("Explicit staging authority and three distinct new output paths are required")
    root = Path(__file__).resolve().parents[1]
    request = CandidateStageRequest(root, args.namespace, True)
    records = compile_candidates(json.loads(args.specifications.read_text()), request)
    with closing(SQLiteRecordStore(str(args.database.resolve()))) as store:
        acknowledgment = stage_candidates(store, records, request)
        selected = store.query(IntelligenceQuery(namespaces=(args.namespace,), lifecycle=("candidate",)))
        export = store.export()
    review = review_search(selected)
    report = {"record_type": "candidate_intelligence_staging_report/v1", "records": len(selected),
              "families": dict(Counter(row["attributes"]["family"] for row in selected)),
              "layers": dict(Counter(row["intelligence_layer"] for row in selected)),
              "batch_digest": acknowledgment.batch_digest, "committed": acknowledgment.committed,
              "hosted_publication": False, "independent_qualification": False, "review_search": review}
    for target, value in ((args.export, export), (args.report, report)):
        with target.open("x") as stream:
            json.dump(value, stream, indent=2); stream.write("\n")
    print(json.dumps({key: report[key] for key in ("records", "families", "layers", "committed", "hosted_publication")}))
    return 0 if review["normal_search_hits"] == 0 and all(row["found_in_first_three"] for row in review["probes"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
