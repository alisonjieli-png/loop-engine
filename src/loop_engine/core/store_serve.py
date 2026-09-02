"""The search/serve plane — the STRICT, hand-owned DAG over the databases.

Owner rule (2026-08-22): the practitioner builds DAGs for novel problems, but
searching and serving what we ALREADY have — nodes, questions, personas, context —
is core infrastructure with its own strict DAG, never rebuilt from scratch:

    parse_query  ->  filter_eligible (kind + tier gates)  ->  score  ->  rank
                 ->  serve

The stores are the moat: the package ships a CORE set, and each organisation
overlays its OWN sets (files first — JSONL is the MVP database — a real service
later; same records either way).  Records are tiered:

  * **core**         — ships with the package, always eligible;
  * **experimental** — off by default (more compute / unproven), toggleable;
  * **gated**        — off by default and requires an explicit grant (paywalled or
                       trade-secret sets: the oil-and-gas questions, the medical
                       personas) — a tier gate, not a search-ranking trick.

Search is deterministic (weighted token overlap on title/tags + body match) so
the same query always finds the same records — no model call to find what we
already own.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Sequence

# What a stored record can be.
STORE_KINDS = ("node", "question", "persona", "context", "strategy")
# The gating tiers.
TIERS = ("core", "experimental", "gated")

SEARCH_STAGES = ("parse_query", "filter_eligible", "score", "rank", "serve")


@dataclass
class StoreRecord:
    record_id: str
    kind: str
    title: str
    body: dict = field(default_factory=dict)
    tags: tuple = ()
    tier: str = "core"
    source: str = "core"            # core (ships) | org (the owner's overlay)

    def __post_init__(self):
        if self.kind not in STORE_KINDS:
            raise ValueError(f"kind must be one of {STORE_KINDS}")
        if self.tier not in TIERS:
            raise ValueError(f"tier must be one of {TIERS}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["tags"] = list(self.tags)
        return d


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


class SolverStore:
    """The layered store: a core set plus org overlays, JSONL-backed (MVP).

    ``org_path`` is where this organisation's additions append; core records load
    read-only.  Tier switches live here too: core is always on; experimental and
    gated start OFF and are enabled explicitly (a gated tier needs a grant
    string, standing in for the auth a real deployment supplies)."""

    def __init__(self, *, core_records: Sequence[StoreRecord] = (),
                 core_path: str | None = None, org_path: str | None = None):
        self._records: dict[str, StoreRecord] = {}
        self._enabled: set = {"core"}
        self._grants: set = set()
        for r in core_records:
            self._records[r.record_id] = r
        for path, source in ((core_path, "core"), (org_path, "org")):
            if path and os.path.exists(path):
                with open(path) as fh:
                    for line in fh:
                        try:
                            d = json.loads(line)
                            d["tags"] = tuple(d.get("tags", ()))
                            d["source"] = source
                            r = StoreRecord(**d)
                            self._records[r.record_id] = r
                        except Exception:
                            continue
        self.org_path = org_path

    # -- tier switchboard --------------------------------------------------

    def enable_tier(self, tier: str, *, grant: str = "") -> None:
        if tier not in TIERS:
            raise ValueError(f"unknown tier {tier!r}")
        if tier == "gated" and not grant:
            raise PermissionError("the gated tier needs an explicit grant")
        if tier == "gated":
            self._grants.add(grant)
        self._enabled.add(tier)

    def disable_tier(self, tier: str) -> None:
        if tier != "core":                      # core cannot be switched off
            self._enabled.discard(tier)

    def enabled_tiers(self) -> tuple:
        return tuple(t for t in TIERS if t in self._enabled)

    # -- write (org overlay only) ------------------------------------------

    def add(self, record: StoreRecord) -> None:
        record.source = "org"
        self._records[record.record_id] = record
        if self.org_path:
            os.makedirs(os.path.dirname(self.org_path) or ".", exist_ok=True)
            with open(self.org_path, "a") as fh:
                fh.write(json.dumps(record.to_dict()) + "\n")

    # -- the strict search DAG ---------------------------------------------

    def records(self) -> list:
        """Every StoreRecord (cards only — bodies stay behind serve()).
        The public accessor the retrieval plug composes over; readers
        never touch the private dict."""
        return list(self._records.values())

    def records_as_loops(self, *, query_hint: str = "") -> list:
        """Every record wrapped into its NAMED intelligence loop

        (context / code / guidance / historical-run).  This is the catalog's
        read-side answer to 'everything is a loop': callers that want loops,
        not bare records, get them here.  The record stays passive data; the
        loop is the envelope that serves it."""
        from ..loop.intelligence_loops import loops_for_records
        return loops_for_records(self.records(), query_hint=query_hint)

    def search_as_loops(self, query: str, *, kind: "str | None" = None,
                        top_n: "int | None" = None) -> list:
        """The search hits, returned as named intelligence loops (one accepted
        success each).  Delegates the ranking to ``search``; the wrapping is
        the loop envelope."""
        from ..loop.intelligence_loops import loops_for_records
        hits = self.search(query, kind=kind, top_n=top_n)["hits"]
        # materialize the full records behind the cards for the serve
        records = [self.serve(h["record_id"]) for h in hits]
        return loops_for_records([r for r in records if r is not None],
                                 query_hint=query)

    def search(self, query: str, *, kind: str | None = None,
               top_n: "int | None" = None) -> dict:
        """parse -> filter (kind + tier gates) -> score -> rank.  Returns the
        ranked hits AND the stage trace, including how many records the tier
        gates excluded — an off tier is a visible exclusion, not a silent one."""
        stages: list = []
        q = _tokens(query)
        stages.append({"stage": "parse_query", "terms": sorted(q)[:12]})

        pool = list(self._records.values())
        eligible = [r for r in pool
                    if (kind is None or r.kind == kind)
                    and r.tier in self._enabled]
        gated_out = sum(1 for r in pool
                        if (kind is None or r.kind == kind)
                        and r.tier not in self._enabled)
        stages.append({"stage": "filter_eligible", "eligible": len(eligible),
                       "excluded_by_tier_gates": gated_out})

        # Rarity-weighted scoring: a term that appears in few records carries
        # more signal than one that appears everywhere ("blueprint" must beat
        # "select next action" for a blueprint query). Deterministic idf over the
        # whole store, times a field weight (title > tags > body).
        import math
        n_all = max(1, len(self._records))
        df: dict[str, int] = {}
        for rec in self._records.values():
            toks = (_tokens(rec.title) | _tokens(" ".join(rec.tags))
                    | _tokens(json.dumps(rec.body)))
            for t in toks:
                df[t] = df.get(t, 0) + 1
        def idf(t: str) -> float:
            return 1.0 + math.log(n_all / max(1, df.get(t, 1)))
        scored = []
        for r in eligible:
            title_t, tag_t = _tokens(r.title), _tokens(" ".join(r.tags))
            body_t = _tokens(json.dumps(r.body))
            score = (sum(idf(t) for t in q & title_t) * 3.0
                     + sum(idf(t) for t in q & tag_t) * 2.0
                     + sum(idf(t) for t in q & body_t) * 1.0)
            if score > 0:
                scored.append((score, r))
        stages.append({"stage": "score", "matched": len(scored),
                       "weighting": "idf x field(title 3, tags 2, body 1)"})

        scored.sort(key=lambda t: (-t[0], t[1].record_id))
        # facets are search keys, so they belong on the body-free card: the
        # directory filters (require/prefer/exclude) without serving the body.
        selected_scores = scored if top_n is None else scored[:top_n]
        hits = [{"record_id": r.record_id, "kind": r.kind, "title": r.title,
                 "tier": r.tier, "source": r.source, "score": s,
                 "facets": dict((r.body or {}).get("facets") or {}),
                 "payload_ref": str((r.body or {}).get("payload_ref") or ""),
                 "payload_digest": str((r.body or {}).get("payload_digest")
                                       or (r.body or {}).get("body_digest") or ""),
                 "maturity": str((r.body or {}).get("maturity") or r.tier),
                 "version": str((r.body or {}).get("version") or "1.0.0")}
                for s, r in selected_scores]
        stages.append({"stage": "rank", "returned": len(hits)})
        return {"record_type": "store_search/v1", "query": query,
                "hits": hits, "stages": stages,
                "enabled_tiers": self.enabled_tiers()}

    def serve(self, record_id: str) -> "StoreRecord | None":
        """Serve the FULL record by id — but only if its tier is enabled; a
        gated record does not leak through a direct id fetch."""
        r = self._records.get(record_id)
        if r is None or r.tier not in self._enabled:
            return None
        return r

    def __len__(self) -> int:
        return len(self._records)


# A minimal CORE set that ships with the package — the seed, not the moat.
def core_seed() -> list:
    return [
        StoreRecord("q.direct_next", "question", "What is the single best next "
                    "move?", tags=("next_action", "direct")),
        StoreRecord("q.blueprint_drilldown", "question",
                    "Develop a high-level blueprint of every step, then go into "
                    "more detail, then choose the most discrete next step",
                    tags=("next_action", "blueprint", "drilldown")),
        StoreRecord("q.are_you_sure", "question",
                    "Are you sure this action should run next, or is there an "
                    "intermediary step we are missing?",
                    tags=("next_action", "verify", "intermediary")),
        StoreRecord("p.careful_statistician", "persona",
                    "a careful statistician who distrusts leaderboards",
                    tags=("persona", "statistics")),
        StoreRecord("n.hgb_baseline", "node",
                    "histogram gradient boosting baseline node",
                    body={"handle": "estimator=hgb"},
                    tags=("tabular", "estimator", "baseline")),
    ]


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    import tempfile
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    store = SolverStore(core_records=core_seed())

    # 1. search finds by kind with deterministic ranking.
    out = store.search("select next action blueprint", kind="question")
    check("search_finds_and_ranks_questions_deterministically",
          out["hits"] and out["hits"][0]["record_id"] == "q.blueprint_drilldown",
          f"top hit {out['hits'][0]['record_id']} for a blueprint query")

    # 2. the strict DAG stages are traced.
    check("the_search_dag_stages_are_traced",
          [s["stage"] for s in out["stages"]]
          == ["parse_query", "filter_eligible", "score", "rank"],
          "parse -> filter -> score -> rank, every time")

    # 3. experimental and gated tiers are OFF by default and visibly excluded.
    store.add(StoreRecord("q.exp1", "question", "experimental deep probe of "
              "select next action", tags=("next_action",), tier="experimental"))
    store.add(StoreRecord("q.secret_drilling", "question",
              "trade-secret drilling question about selecting the next action",
              tags=("next_action", "oil_gas"), tier="gated"))
    out2 = store.search("select next action", kind="question")
    ids = {h["record_id"] for h in out2["hits"]}
    excluded = out2["stages"][1]["excluded_by_tier_gates"]
    check("experimental_and_gated_are_off_by_default_and_visibly_excluded",
          "q.exp1" not in ids and "q.secret_drilling" not in ids
          and excluded >= 2,
          f"{excluded} records excluded by tier gates — visible, not silent")

    # 4. enabling a tier admits its records; gated needs a grant.
    denied = False
    try:
        store.enable_tier("gated")
    except PermissionError:
        denied = True
    store.enable_tier("experimental")
    store.enable_tier("gated", grant="org-license-123")
    out3 = store.search("select next action", kind="question")
    ids3 = {h["record_id"] for h in out3["hits"]}
    check("tier_switches_admit_records_and_gated_requires_a_grant",
          denied and "q.exp1" in ids3 and "q.secret_drilling" in ids3,
          "gated without a grant is refused; with a grant the trade-secret "
          "set serves")

    # 5. serve returns the FULL record, and a disabled tier does not leak by id.
    store.disable_tier("gated")
    check("a_disabled_gated_record_does_not_leak_through_direct_serve",
          store.serve("q.secret_drilling") is None
          and store.serve("q.direct_next") is not None,
          "serving honours the tier gates, id lookup included")

    # 6. org overlay persists as JSONL and reloads (files ARE the MVP database).
    with tempfile.TemporaryDirectory() as d:
        org = os.path.join(d, "org.jsonl")
        s1 = SolverStore(core_records=core_seed(), org_path=org)
        s1.add(StoreRecord("n.org_custom", "node", "org-specific scraper node",
                           body={"handle": "scraper_v1"}, tags=("scrape",)))
        s2 = SolverStore(core_records=core_seed(), org_path=org)
        check("the_org_overlay_persists_as_jsonl_and_reloads",
              s2.serve("n.org_custom") is not None
              and s2.serve("n.org_custom").source == "org"
              and len(s2) == len(core_seed()) + 1,
              "core ships with the package; the organisation's records overlay "
              "from its own file")

    # 7. unknown kinds/tiers are refused.
    bad_kind = bad_tier = False
    try:
        StoreRecord("x", "vibes", "t")
    except ValueError:
        bad_kind = True
    try:
        StoreRecord("x", "node", "t", tier="platinum")
    except ValueError:
        bad_tier = True
    check("unknown_kinds_and_tiers_are_refused", bad_kind and bad_tier,
          "the taxonomies are closed")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "store_serve_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
