"""Post-hoc retrieval diagnostic, outside the comparison: what Baltor search offers for each pilot task.

Written after the trials, when every Baltor-arm harness had abstained from
Baltor, to separate "the library had nothing suitable" from "the harness never
looked". It sends the customer's own searches with the pilot account's key,
which a search never counts as a download, and records hit metadata only:
identity, kind, tier, declared effects and a short purpose. No body is read,
no model is called and nothing here changes a trial result.

Usage: python3 retrieval_diagnostic.py --key-file FILE --output FILE
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENDPOINT = "https://baltor.ai/api/v1/retrieval"
QUERIES = {
    "a-cachetools-tlru": ["time aware LRU cache", "cache with per item time to live python",
                          "recreate a class from its documentation and tests"],
    "b-dotenv-backslash": ["dotenv parser", "escaped backslash in quoted value regex",
                           "debug a regression across two modules"],
    "c-spaceship-titanic": ["Spaceship Titanic", "tabular binary classification scikit-learn",
                            "kaggle getting started competition"],
}


def search(key, query):
    body = json.dumps({"record_type": "service_retrieval_request/v2", "query": query, "mode": "lexical",
                       "top_n": 5}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    key = args.key_file.read_text(encoding="utf-8").strip()
    rows = []
    for task, queries in QUERIES.items():
        for query in queries:
            status, payload = search(key, query)
            result = payload.get("result") or {}
            hits = []
            for hit in result.get("hits") or []:
                reference = hit.get("reference") or {}
                hits.append({"identity": reference.get("identity"), "kind": hit.get("kind"),
                             "library_tier": hit.get("library_tier"),
                             "declared_effects": hit.get("declared_effects"),
                             "body_allowed": hit.get("body_allowed"),
                             "purpose": (hit.get("purpose") or "")[:160]})
            rows.append({"task": task, "query": query, "http_status": status,
                         "bodies_loaded": result.get("bodies_loaded"), "hits": hits})
    report = {"record_type": "comparison_pilot_retrieval_diagnostic/v1",
              "observed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "endpoint": ENDPOINT, "mode": "lexical", "top_n": 5,
              "interpretation": "Search offers only; nothing was read or downloaded, and no trial result changes.",
              "searches": rows}
    text = json.dumps(report, indent=1) + "\n"
    if key in text:
        raise SystemExit("refusing to write a report that contains the key")
    args.output.write_text(text, encoding="utf-8")
    for row in rows:
        print(row["task"], "|", row["query"], "|", [(hit["identity"], hit["kind"]) for hit in row["hits"]])


if __name__ == "__main__":
    main()
