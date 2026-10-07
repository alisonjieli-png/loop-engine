"""Connect owner-signal mining to the interrogation grid.

Takes mined `owner_signal_record/v2` JSONL (from mine.py) and turns each signal
into an interrogation item: its phrases become the item text, its dimensions and
weight set the swarm's shape and priority. The result is an owner-prioritized
interrogation queue — the owner's asks, in the order they keep recurring, each
with a bounded set of questions to route into discovery.

Read-only over the signals file; writes JSON to an out path. No network, no
model, no library staging.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from conversation_mining import records as cm_records

# A signal's weight in the queue: repetition across sources and a bonus when it
# carries a reference (a concrete lead) or is a decision.
BASE_WEIGHT = 1.0
REFERENCE_BONUS = 0.5
DECISION_BONUS = 0.7


@dataclass(frozen=True)
class QueueItem:
    """An owner ask, ready for an interrogation swarm."""
    item_text: str
    source: str
    locators: tuple
    intents: tuple
    dimensions: tuple
    priority: float
    occurrences: int
    references: tuple = ()

    def record(self) -> dict:
        rec = {"record_type": "interrogation_queue_item/v1", "item_text": self.item_text,
               "source": self.source, "locators": sorted(self.locators),
               "intents": sorted(set(self.intents)), "dimensions": sorted(set(self.dimensions)),
               "priority": round(self.priority, 3), "occurrences": self.occurrences,
               "references": list(self.references), "publication_approved": False}
        return rec


def cluster(signals: list[dict]) -> dict:
    """Group exact phrase/reference sets; a shared opening phrase is not identical work."""
    buckets: dict = {}
    for sig in signals:
        sig = cm_records.read_signal(sig)
        phrases = sig.get("phrases") or []
        key = json.dumps([phrases, sig["references"]], sort_keys=True)
        bucket = buckets.setdefault(key, {"phrases": phrases, "locators": [], "intents": [],
                                          "dimensions": [], "count": 0, "source": sig.get("source", ""),
                                          "references": sig["references"]})
        bucket["locators"].append(sig.get("locator", ""))
        bucket["intents"].append(sig.get("intent", ""))
        bucket["dimensions"].extend(sig.get("dimensions") or [])
        bucket["count"] += 1
    return buckets


def to_queue(signals: list[dict]) -> list[QueueItem]:
    buckets = cluster(signals)
    items = []
    for key, bucket in buckets.items():
        phrase = " ".join(bucket["phrases"][:3])[:200] if bucket["phrases"] else "Review the attached source reference"
        intents = bucket["intents"]
        priority = BASE_WEIGHT * bucket["count"] \
            + REFERENCE_BONUS * intents.count("reference") \
            + DECISION_BONUS * intents.count("decision")
        items.append(QueueItem(item_text=phrase, source=bucket["source"],
                               locators=tuple(bucket["locators"]), intents=tuple(intents),
                               dimensions=tuple(sorted(set(bucket["dimensions"]))),
                               priority=priority, occurrences=bucket["count"], references=tuple(bucket["references"])))
    return sorted(items, key=lambda item: (-item.priority, -item.occurrences, item.item_text))


def build(signals_path: Path) -> tuple[list[QueueItem], dict]:
    signals = [json.loads(line) for line in Path(signals_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    items = to_queue(signals)
    summary = {"signals_in": len(signals), "queue_items": len(items),
               "intents": dict(Counter(s.get("intent") for s in signals)),
               "dimensions_touched": sorted({d for item in items for d in item.dimensions})}
    return items, summary
