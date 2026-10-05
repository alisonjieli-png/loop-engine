"""The queue_import engine: earlier research queues enter the ledger as plans, never as executions.

```text
import (plans only; no request is sent and nothing counts as executed)
├── sdg_planned_searches   planned-searches-final.jsonl of the October 1 SDG discovery (148,800 rows:
│                          248 countries or areas x 25 themes x 3 topics x 8 templates)
├── public_good_bank       the 1,440-card Public Good query bank (Drive mirror v6); cards ChatGPT answered stay
│                          recorded as that outside run's evidence, not as Baltor executions
└── keyword_matrix         the 96,525-string country and keyword matrix, when its file is found
```

Each string is normalised (NFKC, case folded, spaces collapsed) and kept once across all queues; every origin
(file, line, the queue's own id) is kept. Rotation: rows are numbered within their key (SDG and country), and the
ledger hands them out by that number first, so the first thousand executions touch hundreds of SDG-country pairs
instead of the first country's rows. Imported text passes the same sensitive-pattern screen as every query.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path

from knowledge_radar.query_matrix import SECRET_PATTERNS, SENSITIVE_TERM

from .evidence import Ledger

MAXIMUM_QUERY = 400


def normalise(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def text_key(text: str) -> str:
    return hashlib.sha256(normalise(text).encode()).hexdigest()


def _screened(text) -> "str | None":
    if not isinstance(text, str) or not text.strip() or len(text) > MAXIMUM_QUERY:
        return None
    if any(unicodedata.category(char).startswith("C") for char in text):
        return None
    lowered = normalise(text)
    # The radar's screen: addresses, credential shapes and private paths never leave the process.
    if SENSITIVE_TERM.search(lowered.replace("site:", "")) or any(pattern.search(text) for pattern in SECRET_PATTERNS):
        return None
    return " ".join(text.split())


class Importer:
    def __init__(self, ledger: Ledger):
        self.ledger = ledger
        self.rank = Counter()
        self.counts = Counter()

    def add(self, origin: str, external_id: str, text, *, sdg: str = "", country: str = "") -> None:
        clean = _screened(text)
        if clean is None:
            self.counts[origin + ":refused_by_screen"] += 1
            return
        key = text_key(clean)
        rotation = f"sdg{sdg or '-'}|{country or '-'}"
        db = self.ledger.db
        exists = db.execute("select 1 from imported where text_key=?", (key,)).fetchone()
        if exists:
            db.execute("update imported set origins=origins+1 where text_key=?", (key,))
            self.counts[origin + ":duplicate_of_earlier_string"] += 1
        else:
            rank = self.rank[rotation]
            self.rank[rotation] += 1
            db.execute("insert into imported values(?,?,?,?,?,?,?,?,?,?)",
                       (key, clean, origin, 1, sdg, country, rotation, rank, "planned", None))
            self.counts[origin + ":new_string"] += 1
        db.execute("insert or ignore into imported_origins values(?,?,?,?)", (key, origin, str(external_id)[:120], "planned"))

    def commit(self):
        self.ledger.db.commit()


def import_sdg_planned_searches(importer: Importer, path: Path) -> None:
    origin = "sdg_discovery_20261001:" + Path(path).name
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except ValueError:
                importer.counts[origin + ":unreadable_line"] += 1
                continue
            importer.add(origin, row.get("query_id") or number, row.get("query"), sdg=str(row.get("sdg") or ""),
                         country=str(row.get("m49") or ""))
            if number % 5000 == 0:
                importer.commit()
    importer.commit()


def import_public_good_bank(importer: Importer, path: Path) -> None:
    origin = "public_good_bank_v6:" + Path(path).name
    document = json.loads(Path(path).read_bytes())
    for card in document.get("queries", []):
        sdg = str(card.get("domain_id") or "").removeprefix("SDG").lstrip("0") or "cross"
        if card.get("status") != "planned":
            # Answered by the outside ChatGPT run: kept as that run's evidence, never counted as ours.
            importer.counts[origin + ":answered_by_outside_run"] += 1
            importer.ledger.db.execute("insert or ignore into imported_origins values(?,?,?,?)",
                                       (text_key(card.get("search_query") or ""), origin, card.get("query_id"), "answered_elsewhere"))
            continue
        importer.add(origin, card.get("query_id"), card.get("search_query"), sdg=sdg, country=card.get("task_id") or "")
    importer.commit()


def import_keyword_matrix(importer: Importer, path: Path) -> None:
    origin = "keyword_matrix:" + Path(path).name
    with open(path, encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            try:
                row = json.loads(line)
            except ValueError:
                row = {"query": line.strip()}
            text = row.get("query") or row.get("q") or row.get("text") if isinstance(row, dict) else None
            importer.add(origin, row.get("id") or number if isinstance(row, dict) else number, text,
                         sdg=str((row or {}).get("sdg") or ""), country=str((row or {}).get("country") or (row or {}).get("m49") or ""))
            if number % 5000 == 0:
                importer.commit()
    importer.commit()


def summary(ledger: Ledger) -> dict:
    rows = ledger.rows("select first_origin, count(*), sum(origins) from imported group by first_origin")
    states = dict(ledger.rows("select state, count(*) from imported group by state"))
    keys = ledger.scalar("select count(distinct rotation_key) from imported")
    origins = dict(ledger.rows("select origin, count(*) from imported_origins group by origin"))
    return {"distinct_strings": sum(row[1] for row in rows), "strings_by_first_origin": {row[0]: row[1] for row in rows},
            "origin_rows": origins, "states": states, "rotation_keys": keys}
