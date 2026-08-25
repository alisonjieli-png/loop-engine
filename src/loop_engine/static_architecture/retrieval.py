"""Standardized retrieval — ONE interface over Strings and Code Nodes.

Architectural role: Static Architecture service (the retrieval layer the
directory's search-by-need delegates to).

Owns:
    - Retriever: one search() over ANY records (String cards and Code Node
      cards alike) with three modes — ``lexical``, ``vector``, ``hybrid``
      (RRF of both) — over PLUGGABLE engine backends (the swap registry:
      backend_handshakes()): lexical = store idf | SQLite FTS5 BM25
      (default) | LanceDB tantivy; vector = crc32 hashed features
      (deterministic default) | learned LOCAL model2vec —
      every adoption tournament-gated (evidence receipt), every space
      identity-tracked (EmbeddingSpace);
    - facet filtering (require/prefer/exclude via facets.FacetFilter)
      applied identically in every mode;
    - honest capability labeling: hashed vectors buy MORPHOLOGY and
      typo/partial-overlap robustness, NOT semantic synonymy — the learned
      LOCAL upgrade is the model2vec backend below,
      adopted 2026-08-23 via the frozen-query tournament receipt.

Does not own:
    - the stores (store_serve/duckdb_catalog serve bodies), the directory
      (capability_directory delegates here), or any hosted endpoint —
      local-no-server, local+DuckDB, and hosted profiles all front THIS
      interface; per-backend search code is never forked.

Public entry points:
    - Retriever(records).search(query, mode=..., flt=..., top_n=...)
    - hash_vector(text) -> the deterministic local vector

Key invariants:
    - identical query + records + mode -> identical ranking ACROSS
      processes (crc32 bucketing, never the salted builtin hash);
    - every hit names the mode(s) that surfaced it (search provenance);
    - facet filters behave exactly as in capability_directory (one grammar).

Verification: self_test() — includes the canary that vector mode retrieves
a morphological/typo variant that lexical token match misses.
"""
from __future__ import annotations

import math
import re
import zlib
import hashlib

_DIMS = 512


def _bucket(kind: str, piece: str) -> int:
    """Stable hash bucket via crc32 — the builtin hash() is salt-randomized
    per process (PYTHONHASHSEED), which silently broke the identical-ranking
    invariant across runs; the semantic canary caught it."""
    return zlib.crc32(f"{kind}:{piece}".encode()) % _DIMS


def _tokens(text: str) -> list:
    return re.findall(r"[a-z0-9]+", (text or "").lower())


SEARCHABLE_BODY_FIELDS = (
    "description", "summary", "text", "template", "key_phrases", "labels",
    "keywords", "symbols", "entrypoints", "components", "asset_kind",
    "source_kind", "template_id", "domain", "subdomain", "project_type",
    "task_type", "job_title", "thinking_method", "question_family",
    "serialization_format", "format_example", "module", "role", "metadata",
    "facets")

_SECRET_SHAPED_KEYS = ("secret", "token", "password", "credential", "api_key")


def _flatten_search_value(value, *, depth: int = 0) -> list:
    if depth > 3 or value is None:
        return []
    if isinstance(value, dict):
        out = []
        for key, item in value.items():
            out.append(str(key))
            if any(part in str(key).lower() for part in _SECRET_SHAPED_KEYS):
                continue
            out.extend(_flatten_search_value(item, depth=depth + 1))
        return out
    if isinstance(value, (list, tuple, set)):
        out = []
        for item in value:
            out.extend(_flatten_search_value(item, depth=depth + 1))
        return out
    if isinstance(value, (str, int, float, bool)):
        return [str(value)]
    return []


def record_search_text(record) -> str:
    """Build bounded search text from a card and flexible safe metadata."""
    body = dict(record.body or {})
    parts = [record.title, *record.tags]
    for field in SEARCHABLE_BODY_FIELDS:
        if field in body:
            parts.extend(_flatten_search_value(body[field]))
    return " ".join(str(part) for part in parts if part)[:12000]


def simhash64(text: str) -> str:
    """Stable 64-bit lexical locality hash for optional blocking."""
    weights = [0] * 64
    for token in _tokens(text):
        digest = int.from_bytes(hashlib.blake2b(
            token.encode(), digest_size=8).digest(), "big")
        for bit in range(64):
            weights[bit] += 1 if digest & (1 << bit) else -1
    value = sum((1 << bit) for bit, weight in enumerate(weights)
                if weight >= 0)
    return f"{value:016x}"


def hash_vector(text: str) -> list:
    """Deterministic LOCAL feature vector: token hashing + character
    3-gram hashing into ``_DIMS`` buckets (signed), L2-normalized.  No
    learned weights; morphology-robust, not synonym-aware."""
    v = [0.0] * _DIMS
    toks = _tokens(text)
    for t in toks:
        v[_bucket("tok", t)] += 2.0
        padded = f"##{t}##"
        for i in range(len(padded) - 2):
            v[_bucket("3g", padded[i:i + 3])] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def _cosine(a: list, b: list) -> float:
    return sum(x * y for x, y in zip(a, b))


from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingSpace:
    """The exact identity of a vector space. Vectors from different spaces
    are NEVER comparable — changing the model, revision, dimensions,
    normalization, or distance creates a NEW space and an explicit
    reindex, per the embedding-space law (owner retrieval plan,
    2026-08-24). Content-addressed via ``space_id``."""
    model: str
    revision: str
    dims: int
    normalization: str = "l2"
    distance: str = "cosine"

    @property
    def space_id(self) -> str:
        import hashlib
        key = f"{self.model}|{self.revision}|{self.dims}|"               f"{self.normalization}|{self.distance}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]


def require_same_space(a: "EmbeddingSpace", b: "EmbeddingSpace") -> None:
    """Fail closed when two vector sets would be compared across spaces."""
    if a.space_id != b.space_id:
        raise ValueError(
            f"embedding-space mismatch: {a.model}@{a.revision}/{a.dims}d vs "
            f"{b.model}@{b.revision}/{b.dims}d — vectors from different "
            "spaces are never comparable; reindex explicitly")


def backend_handshakes() -> list:
    """The swappable-plug registry: every retrieval backend declares what
    it is, what scale tier it serves, and the reference-not-body law
    (the index holds cards and file references; bodies stay in files —
    search returns a handle, materialization is a separate step)."""
    common = {"bodies_never_in_index": True, "swap": "by constructor name"}
    return [
        {"name": "store", "kind": "lexical", "engine": "in-memory idf",
         "scale_tier": "jsonl_in_memory (thousands)",
         "persistence": "none — loads from JSONL files", **common},
        {"name": "fts5", "kind": "lexical", "engine": "SQLite FTS5 BM25",
         "scale_tier": "embedded (hundreds of thousands)",
         "persistence": "optional single file", **common},
        {"name": "lancedb", "kind": "lexical+hybrid-capable",
         "engine": "LanceDB (tantivy FTS + IVF-PQ vectors)",
         "scale_tier": "embedded (tens of millions; 250K measured: "
                       "5-7ms queries, 296MB)",
         "persistence": "columnar files, object-storage capable",
         "requires_dependency": "lancedb", **common},
        {"name": "hash", "kind": "vector", "engine": "crc32 3-gram features",
         "scale_tier": "jsonl_in_memory (thousands)",
         "persistence": "none", **common},
        {"name": "model2vec", "kind": "vector",
         "engine": "learned LOCAL static embeddings",
         "scale_tier": "embedded (millions; 250K encoded in 6s on CPU)",
         "persistence": "vectors rebuildable from files",
         "requires_dependency": "model2vec", **common},
    ]


class SqliteFtsBackend:
    """Proper BM25 lexical via the standard library's SQLite FTS5 — the
    adopted open-source engine for the local-no-server profile (zero new
    dependencies; DuckDB's fts extension is the same idea in the DuckDB
    profile)."""

    def __init__(self, records):
        import sqlite3
        self._con = sqlite3.connect(":memory:")
        self._con.execute(
            "CREATE VIRTUAL TABLE recs USING fts5(rid UNINDEXED, body)")
        self._con.executemany(
            "INSERT INTO recs VALUES (?, ?)",
            [(r.record_id, record_search_text(r)) for r in records])

    def search(self, query: str, top_n: int) -> list:
        toks = _tokens(query)
        if not toks:
            return []
        match = " OR ".join(f'"{t}"' for t in toks[:12])
        try:
            rows = self._con.execute(
                "SELECT rid, bm25(recs) FROM recs WHERE recs MATCH ? "
                "ORDER BY bm25(recs) LIMIT ?", (match, top_n)).fetchall()
        except Exception:                                   # noqa: BLE001
            return []
        return [(rid, -score) for rid, score in rows]       # bm25: lower=better


class LanceDbBackend:
    """Embedded multi-channel store (LanceDB) as a LEXICAL backend — real
    BM25 via its tantivy full-text index. Adopted through the frozen-query
    tournament round 2 (2026-08-24): its FTS beat the FTS5 OR-match
    lexical (MRR 0.467 vs 0.308) and its native score-aware hybrid held
    at 0.533 where naive RRF degraded to 0.325. A missing declared dependency
    is an explicit error, never a silent downgrade."""

    def __init__(self, records):
        try:
            import lancedb
        except ImportError as e:
            raise RuntimeError(
                "lancedb is missing. Reinstall with: python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git. "
                "The backend will not silently downgrade.") from e
        import tempfile
        self._dir = tempfile.mkdtemp(prefix="loop_engine-lancedb-")
        db = lancedb.connect(self._dir)
        self._tbl = db.create_table("recs", [
            {"rid": r.record_id, "body": record_search_text(r)}
            for r in records])
        self._tbl.create_fts_index("body", replace=True)

    def search(self, query: str, top_n: int) -> list:
        try:
            rows = (self._tbl.search(query, query_type="fts")
                    .limit(top_n).to_list())
        except Exception:                                   # noqa: BLE001
            return []
        return [(r["rid"], float(r.get("_score", 0.0))) for r in rows]


class Model2VecBackend:
    """LEARNED local embeddings via model2vec static models (numpy-only
    inference, ~30MB, no network at inference once cached) — the adopted
    open-source engine answering the learned-local-embedding question.
    Real semantics beyond morphology; still fully LOCAL per the law."""

    MODEL = "minishlab/potion-base-8M"

    def __init__(self, records, model: str = None):
        import os as _os
        _os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        try:
            from model2vec import StaticModel
        except ImportError as e:
            raise RuntimeError(
                "model2vec is missing. Reinstall with: python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git. "
                "The backend will not silently downgrade.") from e
        # Default defended by the 2026-08-23 frozen-query tournament
        # (evidence/retrieval-engine-tournament-20260823.json): on the real
        # 170-record bank, potion-retrieval-32M and a full transformer did
        # NOT beat base-8M (MRR 0.511/0.564 vs 0.550, n=10 — inseparable),
        # so the smallest model wins the tie; larger models are one
        # argument away, re-judged when the bank grows 10x.
        self._model = StaticModel.from_pretrained(model or self.MODEL)
        self.space = EmbeddingSpace(model=model or self.MODEL,
                                    revision="hf-cache-pin", dims=256)
        texts = [record_search_text(r) for r in records]
        self._ids = [r.record_id for r in records]
        import numpy as np
        E = self._model.encode(texts)
        self._E = E / (np.linalg.norm(E, axis=1, keepdims=True) + 1e-12)

    def search(self, query: str, top_n: int) -> list:
        import numpy as np
        q = self._model.encode([query])[0]
        q = q / (np.linalg.norm(q) + 1e-12)
        sims = self._E @ q
        order = np.argsort(-sims)[:top_n]
        return [(self._ids[i], float(sims[i])) for i in order
                if sims[i] > 0.05]


class Retriever:
    """One retrieval surface over heterogeneous records (Strings + Code
    Node cards).  Engine backends are pluggable behind THIS interface —
    lexical: the store's idf ("store") or SQLite FTS5 BM25 ("fts5");
    vector: deterministic hashes ("hash") or learned model2vec
    ("model2vec").  Records are ``store_serve.StoreRecord``-shaped."""

    def __init__(self, records, *, lexical_backend: str = "fts5",
                 vector_backend: str = "hash", vector_model: str = None):
        from .store_serve import SolverStore
        self._records = list(records)
        self._by_id = {r.record_id: r for r in self._records}
        if lexical_backend == "fts5":
            self._lex = SqliteFtsBackend(self._records)
        elif lexical_backend == "store":
            store = SolverStore(core_records=self._records)
            self._lex = type("_S", (), {"search": staticmethod(
                lambda q, n: [(h["record_id"], h["score"]) for h in
                              store.search(q, top_n=n)["hits"]])})()
        elif lexical_backend == "lancedb":
            self._lex = LanceDbBackend(self._records)
        else:
            raise ValueError(f"lexical_backend {lexical_backend!r} not in "
                             "store|fts5|lancedb")
        if vector_backend == "hash":
            self.embedding_space = EmbeddingSpace(
                model="loop_engine-crc32-3gram", revision="v2", dims=_DIMS)
            vecs = {r.record_id: hash_vector(
                record_search_text(r)) for r in self._records}
            self._vec = type("_V", (), {"search": staticmethod(
                lambda q, n: [(rid, s) for rid, s in sorted(
                    ((rid, _cosine(hash_vector(q), v))
                     for rid, v in vecs.items()), key=lambda t: -t[1])[:n]
                    if s > 0.05])})()
        elif vector_backend == "model2vec":
            self._vec = Model2VecBackend(self._records, model=vector_model)
            self.embedding_space = self._vec.space
        else:
            raise ValueError(f"vector_backend {vector_backend!r} not in "
                             "hash|model2vec")

    def _lexical(self, query: str, top_n: int) -> list:
        return self._lex.search(query, top_n)

    def _vector(self, query: str, top_n: int) -> list:
        return self._vec.search(query, top_n)

    def search(self, query: str, *, mode: str = "hybrid",
               flt=None, top_n: int = 8) -> dict:
        if mode not in ("lexical", "vector", "hybrid"):
            raise ValueError(f"mode {mode!r} not in lexical|vector|hybrid")
        pools = {}
        if mode in ("lexical", "hybrid"):
            pools["lexical"] = self._lexical(query, top_n * 2)
        if mode in ("vector", "hybrid"):
            pools["vector"] = self._vector(query, top_n * 2)
        # reciprocal-rank fusion across whichever pools ran
        fused: dict = {}
        for pname, pool in pools.items():
            for rank, (rid, _s) in enumerate(pool):
                e = fused.setdefault(rid, {"rrf": 0.0, "modes": []})
                e["rrf"] += 1.0 / (10 + rank)
                e["modes"].append(pname)
        hits = []
        from .facets import FacetFilter, facet_match
        f = flt or FacetFilter()
        for rid, e in sorted(fused.items(), key=lambda t: -t[1]["rrf"]):
            rec = self._by_id[rid]
            facets = dict((rec.body or {}).get("facets") or {})
            score_bonus = 0
            if not f.is_empty():
                ok, score_bonus, _why = facet_match(facets, f)
                if not ok:
                    continue
            hits.append({"record_id": rid, "title": rec.title,
                         "kind": rec.kind, "facets": facets,
                         "lsh64": simhash64(record_search_text(rec)),
                         "modes": sorted(set(e["modes"])),
                         "rrf": round(e["rrf"] + 0.01 * score_bonus, 5)})
            if len(hits) >= top_n:
                break
        return {"record_type": "retrieval/v1", "query": query,
                "mode": mode, "hits": hits,
                "capability_note": "hashed local vectors: morphology/typo "
                                   "robustness, not semantic synonymy"}


def tournament_as_loop(backend_names: list, records: list,
                       frozen_queries: list, ledger=None) -> dict:
    """Loop-standardization item #4: an engine tournament runs AS a
    PractitionerLoop on the registered hypothesis_experiment template —
    observe (corpus), hypothesize (each backend is a hypothesis),
    experiment (frozen queries through each), analyze (hit@1 + MRR),
    revise (rank; losers eliminated). Deterministic, zero model calls;
    adoption still requires the receipt + the evidence-gated flip."""
    from ..loop.recursive_loop import Loop, StepOutcome
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    tmpl = next(b for b in TEMPLATE_LIBRARY
                if b["template_id"] == "hypothesis_experiment")
    state: dict = {"scores": {}}

    def handler(lp, step, ctx):
        if step == "observe":
            return StepOutcome(output=f"observe:{len(records)} records, "
                                      f"{len(frozen_queries)} frozen queries",
                               mode="deterministic", confidence=0.95)
        if step == "hypothesize":
            return StepOutcome(output="hypothesize:" + ",".join(backend_names),
                               mode="deterministic", confidence=0.9)
        if step == "experiment":
            for name in backend_names:
                r = Retriever(records, lexical_backend=name)
                hit1, mrr = 0, 0.0
                for fq in frozen_queries:
                    hits = [h["record_id"] for h in
                            r.search(fq["query"], mode="lexical")["hits"]]
                    acc = set(fq["accept"])
                    if hits and hits[0] in acc:
                        hit1 += 1
                    mrr += next((1.0 / (i + 1) for i, h in enumerate(hits)
                                 if h in acc), 0.0)
                n = max(1, len(frozen_queries))
                state["scores"][name] = {"hit_at_1": hit1,
                                         "mrr": round(mrr / n, 3)}
            return StepOutcome(output=f"experiment:{state['scores']}",
                               mode="deterministic", confidence=0.9)
        if step == "analyze":
            state["ranking"] = sorted(state["scores"],
                                      key=lambda k: -state["scores"][k]["mrr"])
            return StepOutcome(output="analyze:winner "
                                      + state["ranking"][0],
                               mode="deterministic", confidence=0.9)
        return StepOutcome(output="revise:losers eliminated, ranking kept",
                           mode="deterministic", confidence=0.9)

    loop = Loop("retrieval tournament", config_from_template(tmpl),
                ledger=ledger)
    res = loop.run(handler=handler, max_steps=len(loop.steps()) + 1)
    return {"loop_id": res.loop_id, "scores": state["scores"],
            "ranking": state.get("ranking", []),
            "model_calls": res.model_calls, "stopped": res.stopped}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from .store_serve import StoreRecord
    from .facets import FacetFilter, code_facets
    records = [
        StoreRecord("s.joinkeys", "context",
                    "Count distinct join keys on BOTH sides before any "
                    "merge; explosion is cheaper to prevent than debug",
                    body={}, tags=("heuristic", "etl")),
        StoreRecord("s.leakage", "context",
                    "watch for temporal leakage in point-in-time features",
                    body={}, tags=("warning", "leakage")),
        StoreRecord("n.probe", "node",
                    "residual predictability probe (cross-fitted)",
                    body={"facets": code_facets(
                        execution_mode="code_only",
                        determinism="deterministic",
                        locality="local_machine", effects=("pure",),
                        role="detect")},
                    tags=("probe", "residuals")),
        StoreRecord("n.api", "node",
                    "hosted stats API probe for residual analysis",
                    body={"facets": code_facets(
                        execution_mode="code_only",
                        determinism="deterministic",
                        locality="api_calling", effects=("network",),
                        role="detect")},
                    tags=("probe", "residuals")),
        StoreRecord(
            "n.large_worker", "node", "registered external system card",
            body={"metadata": {
                "keywords": ["kubernetes", "worker"],
                "symbols": ["run_preflight", "collect_diagnostics"],
                "extensions": {"org.example.search.v1": {
                    "blocking_keys": ["python", "worker_framework"]}}}},
            tags=("large_code",)),
    ]
    r = Retriever(records)

    # 1. one interface, both asset classes, hit provenance names the modes.
    h = r.search("residual predictability probe")
    check("one_interface_over_strings_and_code_nodes",
          h["hits"] and h["hits"][0]["record_id"] == "n.probe"
          and set(h["hits"][0]["modes"]) <= {"lexical", "vector"}
          and any(x["kind"] == "node" for x in h["hits"]),
          f"top: {h['hits'][0]['record_id']} via {h['hits'][0]['modes']}")

    # 2. THE CANARY: a typo/morphology query ("mergin keyz cardinality")
    # shares almost no exact tokens — vector mode retrieves the join-keys
    # heuristic where pure lexical token match returns nothing.
    lex = r.search("mergin keyz cardinality", mode="lexical")
    vec = r.search("mergin keyz cardinality", mode="vector")
    check("vector_mode_survives_typos_lexical_misses",
          not any(x["record_id"] == "s.joinkeys" for x in lex["hits"])
          and any(x["record_id"] == "s.joinkeys" for x in vec["hits"][:2]),
          "character 3-grams carry mergin~merge, keyz~keys into the first two")

    # 3. facet filters apply identically in every mode (the offline case).
    off = r.search("residual probe", mode="hybrid",
                   flt=FacetFilter(exclude={"locality": ("api_calling",)}))
    ids = {x["record_id"] for x in off["hits"]}
    check("facet_filters_apply_in_retrieval",
          "n.probe" in ids and "n.api" not in ids)

    # 4. determinism: identical inputs, identical ranking.
    a = r.search("temporal leakage features")
    b = r.search("temporal leakage features")
    check("retrieval_is_deterministic", a == b)

    # 5. honest capability label rides every result.
    check("capability_limits_are_labeled",
          "not semantic synonymy" in a["capability_note"])

    # Flexible namespaced card metadata joins the same bounded search text.
    # Search does not need a schema migration for every new descriptive field.
    metadata_hit = r.search(
        "kubernetes worker preflight diagnostics", mode="lexical")
    matching = next((hit for hit in metadata_hit["hits"]
                     if hit["record_id"] == "n.large_worker"), None)
    check("flexible_metadata_and_locality_hashes_are_searchable",
          matching is not None and len(matching["lsh64"]) == 16
          and matching["lsh64"] == simhash64(
              record_search_text(records[-1])),
          "nested keywords, symbols, blocking keys, and a stable SimHash card")

    # 6. ADOPTED ENGINE — SQLite FTS5 (stdlib BM25) is the default lexical
    # backend and ranks properly; unknown backends refuse.
    r5 = Retriever(records, lexical_backend="fts5")
    h5 = r5.search("temporal leakage features", mode="lexical")
    refused = 0
    for kw in ({"lexical_backend": "elastic"}, {"vector_backend": "faiss"}):
        try:
            Retriever(records, **kw)
        except ValueError:
            refused += 1
    check("fts5_bm25_is_the_default_lexical_engine",
          h5["hits"] and h5["hits"][0]["record_id"] == "s.leakage"
          and refused == 2,
          "stdlib FTS5 ranks; unknown backends refuse loudly")

    # 6b. ADOPTED ENGINE — LanceDB FTS (tournament round 2 winner on the
    # lexical leg). Present -> it ranks; absent -> explicit RuntimeError.
    try:
        r6 = Retriever(records, lexical_backend="lancedb")
    except RuntimeError as e:
        check("lancedb_backend_present_or_explicitly_absent",
              "lancedb is missing" in str(e), f"explicit absence: {e}")
    else:
        h6 = r6.search("temporal leakage features", mode="lexical")
        check("lancedb_backend_present_or_explicitly_absent",
              h6["hits"] and h6["hits"][0]["record_id"] == "s.leakage",
              "tantivy BM25 ranks the leakage record first")

    # 7. ADOPTED ENGINE — model2vec learned LOCAL embeddings: the SEMANTIC
    # canary.  A paraphrase query with no decisive shared tokens: the
    # learned backend separates the right record by a wide margin while
    # hashed vectors sit at noise level (measured, not assumed).  Explicit
    # failure if model2vec is missing, never a silent downgrade.
    try:
        rm = Retriever(records, vector_backend="model2vec")
    except RuntimeError:
        # NOT a silent downgrade: the missing declared dependency is a failure.
        results.append({
            "test": "model2vec_semantic_canary", "passed": False,
            "missing_dependency": "model2vec",
            "detail": "FAILED: missing model2vec. Reinstall with: "
                      "python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git"})
    else:
        # ZERO token overlap between query and target record text — the
        # hash leg cannot win on morphology, so only learned semantics can
        # rank s.joinkeys first.  Margins MEASURED on 2026-08-23 with
        # crc32-stable hashing: learned 0.2513 vs 0.0660 (margin 0.185,
        # threshold 0.09 = ~2x headroom); hash ranks s.leakage first.
        q = "combine two spreadsheets into one"
        sem = rm._vector(q, 4)
        hsh = Retriever(records, vector_backend="hash")._vector(q, 4)
        sem_margin = (sem[0][1] - sem[1][1]) if len(sem) > 1 else 1.0
        hsh_top = sorted(hsh, key=lambda t: -t[1])[0][0] if hsh else None
        check("model2vec_semantic_canary",
              sem and sem[0][0] == "s.joinkeys" and sem_margin > 0.09
              and hsh_top != "s.joinkeys",
              f"learned margin {sem_margin:.3f} ranks the paraphrase; "
              f"hash top is {hsh_top!r} — semantics beyond morphology")


    # 8. THE SWAPPABLE PLUG: every backend declares a handshake with its
    # scale tier, and the reference-not-body law holds on all of them.
    hs = backend_handshakes()
    check("backend_registry_handshakes_reference_not_body",
          {h["name"] for h in hs} == {"store", "fts5", "lancedb", "hash",
                                      "model2vec"}
          and all(h["bodies_never_in_index"] for h in hs)
          and all("scale_tier" in h for h in hs),
          f"{len(hs)} pluggable backends declared")

    # 9. EMBEDDING-SPACE LAW: retrievers carry their space identity; two
    # different spaces REFUSE comparison; the same space passes.
    ra = Retriever(records, vector_backend="hash")
    sp_hash = ra.embedding_space
    sp_other = EmbeddingSpace(model="future-model", revision="r1", dims=1024)
    refused_sp = False
    try:
        require_same_space(sp_hash, sp_other)
    except ValueError:
        refused_sp = True
    require_same_space(sp_hash, sp_hash)          # same space: no error
    check("embedding_space_identity_and_cross_space_refusal",
          refused_sp and len(sp_hash.space_id) == 16,
          f"hash space {sp_hash.space_id} refuses future-model@r1/1024d")

    # LOOP-STANDARDIZATION #4: a tournament runs AS a
    # hypothesis-experiment loop — the fixture rerun of round 1's store
    # vs fts5 comparison, now with loop evidence and zero model calls.
    from ..loop.recursive_loop import LoopLedger as _LL
    _lgT = _LL()
    tq = [{"query": "temporal leakage features", "accept": ["s.leakage"]},
          {"query": "join keys cardinality merge", "accept": ["s.joinkeys"]}]
    tw = tournament_as_loop(["store", "fts5"], records, tq, ledger=_lgT)
    steps_t = [e.get("step") for e in _lgT.events
               if e.get("event") == "run_step"]
    check("tournaments_run_as_hypothesis_experiment_loops",
          set(tw["scores"]) == {"store", "fts5"} and tw["ranking"]
          and tw["model_calls"] == 0 and tw["stopped"] == "done"
          and steps_t[:3] == ["observe", "hypothesize", "experiment"],
          f"winner {tw['ranking'][0]}: {tw['scores']}")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
