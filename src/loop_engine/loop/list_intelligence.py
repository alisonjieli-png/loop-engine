"""List intelligence — harvest every ranked list an LLM returns, and compound it.

When the swarm asks "what are the top 10 PyPI libraries for this task?", "which
researchers would attack this?", "what are the strongest methods here?", the
answer is useful twice: once for THIS graph, and forever after as evidence
about what gets suggested for tasks LIKE this one.  Today the second use is
thrown away.  This module keeps it.

Every list an LLM returns is harvested with the SITUATION it was asked in
(task family, metric, modality, construction step), so the store learns not a
global "best library" but a situational one — "for imbalanced classification,
imblearn and lightgbm are suggested most, and lightgbm is the one that most
often WON."  The store separates three things it never conflates:

- **suggestion frequency** — how often an item is proposed for a situation
  (an LLM popularity signal; useful for diversity and coverage, not truth);
- **acceptance count** — how often a harvested item, once tried, was part of
  an arrangement the fold oracle accepted (the only signal that means the item
  actually helped);
- **the situation** — the task shape the suggestion was made for, so a
  leader-board for imbalanced text is not blended with one for grouped
  regression.

Serving the accumulated leaders back into a future prompt ("libraries commonly
suggested for tasks like this, and the ones that have actually won") gives the
swarm a warm start that compounds over time — the "become smarter with every
run" substrate — while a protected exploration share and the append-only log
keep it honest and auditable.  A suggestion is never a promotion: a harvested
library or method is a CANDIDATE that must still pass the foundry gates (name,
version, licence, isolated smoke test) and the fold oracle before it counts.

Run: ``python -m loop_engine.loop.list_intelligence --self-test``.
Architectural role: Practitioner Loop.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

BENCH = Path(__file__).resolve().parent
DEFAULT_STORE = BENCH / "improvement-flywheel" / "list-intelligence.jsonl"

# The kinds of list the store recognizes.  Open — a new kind is just a new
# string; nothing here is a closed enum.
KNOWN_KINDS = ("pypi", "method", "researcher", "paper", "algorithm",
               "persona", "feature", "keyword")


def situation_key(situation: Mapping[str, Any]) -> str:
    """A stable key for a situation: the task-shape facets that matter for
    which suggestions apply.  Missing facets are omitted, so a coarse
    situation still matches."""
    facets = []
    for facet in ("family", "modality", "metric", "step"):
        value = situation.get(facet)
        if value:
            facets.append(f"{facet}={str(value).lower()}")
    return "|".join(facets) if facets else "any"


def normalize_item(item: Any) -> str:
    """Canonicalize a list item so 'LightGBM', 'lightgbm', ' lightgbm '
    collapse to one leader."""
    text = str(item).strip().lower()
    return re.sub(r"\s+", " ", text)


@dataclass
class ListIntelligence:
    """The compounding list store: appearance and acceptance counts per item
    per situation, plus its append-only transaction log."""
    # (kind, situation_key, item) -> {"appearances": int, "accepted": int,
    #                                  "display": str}
    counts: dict[tuple[str, str, str], dict] = field(default_factory=dict)
    store_path: Path | None = None

    # -- learning --------------------------------------------------------
    def harvest(self, kind: str, items: Sequence[Any],
                situation: Mapping[str, Any], *, source: str = "") -> dict:
        """Record a list an LLM returned for a situation.

        Each item's appearance count for this situation increments once (a
        repeated item in the same list still counts once — one suggestion is
        one suggestion).  Rank is preserved as a weak signal: the first item
        gets a small rank bonus, the last the least.
        """
        skey = situation_key(situation)
        # Log the original items (display casing preserved) and normalize on
        # BOTH the live and the replay path, so a rebuilt store is byte-for-
        # byte the same as the one that wrote the log.
        deduped = self._ingest(kind, skey, items)
        txn = {"record_type": "list_harvest/v1", "kind": kind,
               "situation": skey, "items": deduped, "source": source[:200]}
        self._append(txn)
        return {"kind": kind, "situation": skey, "harvested": len(deduped)}

    def _ingest(self, kind: str, skey: str,
                items: Iterable[Any]) -> list[str]:
        """Fold a list of raw items into the counts, preserving display
        casing and deduplicating within the one list.  Shared by the live
        harvest and the log replay so the two can never diverge."""
        seen: set[str] = set()
        kept: list[str] = []
        for rank, raw in enumerate(items):
            norm = normalize_item(raw)
            if not norm or norm in seen:
                continue
            seen.add(norm)
            entry = self.counts.setdefault(
                (kind, skey, norm),
                {"appearances": 0, "accepted": 0, "display": str(raw).strip(),
                 "rank_weight": 0.0})
            entry["appearances"] += 1
            # A modest first-place bonus so consistently top-ranked items lead
            # ties, without letting rank dominate raw frequency.
            entry["rank_weight"] += max(0.0, 1.0 - rank * 0.1)
            kept.append(str(raw).strip())
        return kept

    def record_acceptance(self, kind: str, item: Any,
                          situation: Mapping[str, Any]) -> dict:
        """Mark that a harvested item, once tried, was part of an accepted
        arrangement — the only signal that it actually helped."""
        skey = situation_key(situation)
        norm = normalize_item(item)
        key = (kind, skey, norm)
        entry = self.counts.get(key)
        if entry is None:
            entry = self.counts.setdefault(
                key, {"appearances": 0, "accepted": 0, "display": str(item),
                      "rank_weight": 0.0})
        entry["accepted"] += 1
        txn = {"record_type": "list_acceptance/v1", "kind": kind,
               "situation": skey, "item": norm}
        self._append(txn)
        return {"kind": kind, "item": norm, "accepted": entry["accepted"]}

    # -- consumption -----------------------------------------------------
    def leaders(self, kind: str, situation: Mapping[str, Any], *,
                top_n: int = 10) -> list[dict]:
        """The items most suggested for a matching situation, with both
        signals separated: appearances (suggestion frequency) and accepted
        (times it actually won).  Ranked by acceptance first, then frequency,
        then the rank bonus — so a proven item leads, but a frequently-
        suggested untried one is still surfaced."""
        skey = situation_key(situation)
        rows = [
            {"item": item, "display": entry["display"],
             "appearances": entry["appearances"],
             "accepted": entry["accepted"],
             "rank_weight": round(entry["rank_weight"], 3),
             "acceptance_rate": (entry["accepted"] / entry["appearances"]
                                 if entry["appearances"] else 0.0)}
            for (k, s, item), entry in self.counts.items()
            if k == kind and s == skey]
        rows.sort(key=lambda r: (-r["accepted"], -r["appearances"],
                                 -r["rank_weight"], r["item"]))
        return rows[:max(1, top_n)]

    def as_context(self, kind: str, situation: Mapping[str, Any], *,
                   top_n: int = 8) -> str:
        """A compact line to inject into a future prompt — the leaders and
        which of them have actually won, so the swarm gets a warm start."""
        rows = self.leaders(kind, situation, top_n=top_n)
        if not rows:
            return ""
        parts = []
        for row in rows:
            tag = (f"{row['display']}"
                   + (f" (won {row['accepted']}x)" if row["accepted"]
                      else f" (suggested {row['appearances']}x)"))
            parts.append(tag)
        return (f"For tasks like this, {kind} commonly suggested: "
                + "; ".join(parts)
                + ". These are CANDIDATES — the fold oracle still decides.")

    def snapshot(self, *, top_n: int = 20) -> dict:
        rows = sorted(
            ({"kind": k, "situation": s, "item": item,
              "appearances": e["appearances"], "accepted": e["accepted"]}
             for (k, s, item), e in self.counts.items()),
            key=lambda r: (-r["accepted"], -r["appearances"]))
        return {"record_type": "list_intelligence_snapshot/v1",
                "distinct_items": len(self.counts),
                "top": rows[:top_n]}

    # -- persistence -----------------------------------------------------
    def _append(self, txn: Mapping[str, Any]) -> None:
        if self.store_path is None:
            return
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.store_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(txn, ensure_ascii=False) + "\n")


def load(store_path: Path | None = DEFAULT_STORE) -> ListIntelligence:
    store = ListIntelligence(store_path=store_path)
    if store_path is None or not Path(store_path).exists():
        return store
    for line in Path(store_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            txn = json.loads(line)
        except Exception:                                       # noqa: BLE001
            continue
        kind = txn.get("record_type")
        if kind == "list_harvest/v1":
            store._ingest(txn.get("kind", "?"), txn.get("situation", "any"),
                          txn.get("items", ()))
        elif kind == "list_acceptance/v1":
            key = (txn.get("kind", "?"), txn.get("situation", "any"),
                   txn.get("item", ""))
            entry = store.counts.setdefault(
                key, {"appearances": 0, "accepted": 0,
                      "display": txn.get("item", ""), "rank_weight": 0.0})
            entry["accepted"] += 1
    return store


def parse_list_reply(content: str) -> list[str]:
    """Pull a list out of an LLM reply — a JSON array, or numbered/bulleted
    lines.  Tolerant: returns whatever list-shaped items it can find."""
    text = (content or "").strip()
    start, end = text.find("["), text.rfind("]")
    if 0 <= start < end:
        try:
            arr = json.loads(text[start:end + 1])
            if isinstance(arr, list):
                return [str(x) for x in arr if str(x).strip()]
        except Exception:                                       # noqa: BLE001
            pass
    items: list[str] = []
    for line in text.splitlines():
        m = re.match(r"\s*(?:\d+[.)]|[-*•])\s+(.*)", line)
        if m and m.group(1).strip():
            items.append(m.group(1).strip())
    return items


# ---------------------------------------------------------------------------
# Self-test — deterministic, no model, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    store = ListIntelligence()
    imbalanced = {"family": "classification", "modality": "tabular",
                  "metric": "roc_auc", "step": "model_choice"}
    grouped = {"family": "regression", "modality": "tabular",
               "metric": "rmse", "step": "model_choice"}

    # Harvest the same kind of list across several runs; counts accumulate.
    store.harvest("pypi", ["LightGBM", "imbalanced-learn", "XGBoost"],
                  imbalanced, source="run1")
    store.harvest("pypi", ["lightgbm", "catboost", "imbalanced-learn"],
                  imbalanced, source="run2")
    store.harvest("pypi", ["statsmodels", "scikit-learn"], grouped,
                  source="run3")
    check("harvest_accumulates_counts_and_canonicalizes_items",
          store.counts[("pypi",
                        situation_key(imbalanced), "lightgbm")]["appearances"]
          == 2
          and ("pypi", situation_key(imbalanced),
               "imbalanced-learn") in store.counts,
          "LightGBM and lightgbm collapse to one leader with two appearances "
          "for the imbalanced situation; casing and whitespace do not split it")

    # Leaders are situation-conditioned.
    imb_leaders = [r["item"] for r in store.leaders("pypi", imbalanced)]
    grp_leaders = [r["item"] for r in store.leaders("pypi", grouped)]
    check("leaders_are_situation_conditioned_not_global",
          "lightgbm" in imb_leaders and "statsmodels" in grp_leaders
          and "statsmodels" not in imb_leaders
          and "lightgbm" not in grp_leaders,
          "the imbalanced-classification leaderboard names lightgbm; the "
          "grouped-regression one names statsmodels; neither blends into the "
          "other")

    # Acceptance is separate from suggestion frequency and reorders leaders.
    store.record_acceptance("pypi", "imbalanced-learn", imbalanced)
    top = store.leaders("pypi", imbalanced)[0]
    check("acceptance_outranks_mere_suggestion_frequency",
          top["item"] == "imbalanced-learn" and top["accepted"] == 1
          and any(r["item"] == "lightgbm" and r["accepted"] == 0
                  for r in store.leaders("pypi", imbalanced)),
          "imbalanced-learn was suggested less than lightgbm but, once it was "
          "part of an accepted arrangement, it leads — the accepted signal "
          "outranks raw suggestion frequency")

    # as_context produces an injectable, honest warm-start line.
    ctx = store.as_context("pypi", imbalanced)
    check("as_context_yields_an_injectable_candidate_honest_line",
          "imbalanced-learn" in ctx and "won 1x" in ctx
          and "CANDIDATES" in ctx and "fold oracle" in ctx,
          "the context line surfaces the winner with its win count and states "
          "the items are candidates the oracle still decides — a warm start, "
          "never a promotion")

    # parse_list_reply reads JSON arrays and numbered/bulleted lists.
    from_json = parse_list_reply('```json\n["a", "b", "c"]\n```')
    from_bullets = parse_list_reply("1. First lib\n2. Second lib\n- third")
    check("parse_list_reply_reads_json_and_bulleted_replies",
          from_json == ["a", "b", "c"]
          and from_bullets == ["First lib", "Second lib", "third"],
          "a fenced JSON array and a numbered/bulleted reply both parse into "
          "clean item lists, so any list-shaped LLM answer can be harvested")

    # Persistence round-trips through the append-only log.
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="listintel-")) / "store.jsonl"
    persistent = ListIntelligence(store_path=tmp)
    persistent.harvest("researcher", ["Breiman", "Friedman", "Chen"],
                       imbalanced)
    persistent.record_acceptance("researcher", "Friedman", imbalanced)
    reloaded = load(tmp)
    r_top = reloaded.leaders("researcher", imbalanced)[0]
    check("the_store_rebuilds_from_its_append_only_log",
          r_top["item"] == "friedman" and r_top["accepted"] == 1
          and reloaded.leaders("researcher", imbalanced)
          == persistent.leaders("researcher", imbalanced),
          "replaying the harvest and acceptance transactions rebuilds the "
          "exact leaderboard — the compounding intelligence is durable and "
          "auditable")

    passed = sum(1 for row in results if row["passed"])
    return {"record_type": "list_intelligence_self_test",
            "tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--snapshot", action="store_true",
                        help="print the current leaderboards, strongest first")
    args = parser.parse_args(argv)
    if args.snapshot:
        print(json.dumps(load().snapshot(), indent=1))
        return 0
    if args.self_test:
        report = self_test()
        print(json.dumps(report, indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
