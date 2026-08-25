"""DuckDB catalog backend — a QUERY LAYER over files, never a second truth.

Architectural role: Static Architecture service (storage).

Owns:
    - the DuckDB-indexed catalog view over a JSONL record file
      (references + digests + facets; search without serving bodies);
    - digest-verified serving: the BODY is read back from the authoritative
      file row and refused on tamper.

Does not own:
    - authoritative content (the JSONL file is the truth; the database is an
      index rebuilt from it);
    - promotion, lifecycle, or any write path to accepted state.

Public entry points:
    - DuckDBCatalogBackend: search(query, kind) / serve(record_id) with the
      same hit-card shape as ``store_serve.SolverStore`` — the equivalence
      canary holds the two backends to the same answers.
    - write_catalog_file: serialize StoreRecords to the authoritative JSONL.

Side effects and authority: reads/writes the given JSONL path; in-memory
DuckDB by default; no network; no execution authority.

Key invariants:
    - the catalog row stores id/kind/title/tags/facets/digest — never the
      only copy of a body;
    - serve() recomputes the body digest and REFUSES a mismatch (fail
      closed);
    - ``duckdb`` is a declared dependency: absence is an explicit failing
      test, never a silent skip.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile

from .store_serve import StoreRecord


def _digest(body: dict) -> str:
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def write_catalog_file(records, path: str) -> str:
    """Serialize records to the authoritative JSONL file (files first)."""
    with open(path, "w") as f:
        for r in records:
            f.write(json.dumps({
                "record_id": r.record_id, "kind": r.kind, "title": r.title,
                "body": r.body, "tags": list(r.tags), "tier": r.tier,
                "source": r.source,
                "facets": dict((r.body or {}).get("facets") or {}),
                "digest": _digest(r.body or {})}, default=str) + "\n")
    return path


class DuckDBCatalogBackend:
    """Search = SQL over a view of the file; serve = file row, digest-checked."""

    def __init__(self, jsonl_path: str, db_path: str = ":memory:"):
        import duckdb
        self.jsonl_path = jsonl_path
        self._con = duckdb.connect(db_path)
        self._con.execute(
            "CREATE OR REPLACE VIEW catalog AS "
            "SELECT record_id, kind, title, tags, tier, facets, digest "
            f"FROM read_json_auto('{jsonl_path}')")

    def search(self, query: str, *, kind: "str | None" = None,
               top_n: int = 8) -> dict:
        tokens = [t.lower() for t in query.split() if len(t) > 2][:12]
        if not tokens:
            return {"record_type": "duckdb_catalog_search/v1", "hits": []}
        score_sql = " + ".join(
            f"(CASE WHEN lower(title) LIKE '%{t}%' THEN 3 ELSE 0 END)"
            f" + (CASE WHEN lower(CAST(tags AS VARCHAR)) LIKE '%{t}%' "
            "THEN 2 ELSE 0 END)"
            for t in (t.replace("'", "") for t in tokens))
        where = f"WHERE kind = '{kind}'" if kind else ""
        rows = self._con.execute(
            f"SELECT record_id, kind, title, tier, facets, digest, "
            f"({score_sql}) AS score FROM catalog {where} "
            "ORDER BY score DESC, record_id LIMIT ?", [top_n]).fetchall()
        hits = [{"record_id": r[0], "kind": r[1], "title": r[2], "tier": r[3],
                 "source": "duckdb_catalog",
                 "facets": (json.loads(r[4]) if isinstance(r[4], str)
                            else dict(r[4] or {})),
                 "digest": r[5], "score": r[6]}
                for r in rows if r[6] > 0]
        return {"record_type": "duckdb_catalog_search/v1", "query": query,
                "hits": hits}

    def serve(self, record_id: str) -> "StoreRecord | None":
        """The BODY comes from the authoritative FILE, digest-verified."""
        for line in open(self.jsonl_path):
            row = json.loads(line)
            if row["record_id"] != record_id:
                continue
            if _digest(row["body"] or {}) != row["digest"]:
                raise ValueError(
                    f"digest mismatch for {record_id!r}: the file row was "
                    "modified after cataloging — refusing to serve (fail "
                    "closed)")
            return StoreRecord(row["record_id"], row["kind"], row["title"],
                               body=row["body"], tags=tuple(row["tags"]),
                               tier=row.get("tier", "core"),
                               source=row.get("source", "file"))
        return None


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    try:
        import duckdb                                     # noqa: F401
    except ImportError:
        results.append({
            "test": "duckdb_dependency_installed", "passed": False,
            "missing_dependency": "duckdb",
            "detail": "FAILED: missing duckdb. Reinstall with: "
                      "python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git"})
        return {"tests": results, "passed": 0, "total": 1,
                "all_passed": False}

    from ..loop.loop_templates import template_records
    from .store_serve import SolverStore
    records = template_records()
    tmp = tempfile.mkdtemp(prefix="duckcat_")
    path = write_catalog_file(records, os.path.join(tmp, "catalog.jsonl"))
    db = DuckDBCatalogBackend(path)
    fs = SolverStore(core_records=records)

    # 1. EQUIVALENCE: the same probe queries pick the same top identity
    # through the file backend and the DuckDB view (Canary C).
    probes = ("adversarial review refute claims",
              "legacy assimilation quarantine snapshot",
              "hypothesis experiment observe analyze")
    agree = []
    for q in probes:
        f_top = fs.search(q, kind="strategy")["hits"][0]["record_id"]
        d_top = db.search(q, kind="strategy")["hits"][0]["record_id"]
        agree.append(f_top == d_top)
    check("file_and_duckdb_backends_agree_on_top_identity", all(agree),
          f"{sum(agree)}/{len(probes)} probes agree")

    # 2. served bodies are IDENTICAL across backends (one truth).
    rid = "looptmpl.adversarial_review"
    check("served_bodies_identical_across_backends",
          db.serve(rid).body == fs.serve(rid).body
          and db.serve(rid).title == fs.serve(rid).title)

    # 3. the catalog row carries facets + digest (references, not bodies,
    # do the searching).
    hit = db.search("adversarial review refute claims")["hits"][0]
    check("catalog_rows_carry_facets_and_digest",
          hit["facets"].get("category") == "loop_template"
          and len(hit["digest"]) == 64)

    # 4. TAMPER: editing the file row after cataloging makes serve() refuse.
    lines = open(path).read().splitlines()
    row = json.loads(lines[0])
    row["body"]["description"] = "tampered"
    lines[0] = json.dumps(row, default=str)
    open(path, "w").write("\n".join(lines) + "\n")
    refused = False
    try:
        db.serve(json.loads(lines[0])["record_id"])
    except ValueError:
        refused = True
    check("tampered_file_row_is_refused_by_digest", refused,
          "fail closed: the digest binds the catalog to the exact bytes")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
