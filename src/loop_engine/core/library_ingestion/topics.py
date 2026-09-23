"""Topic words from a closed list, the only words ever taken from an author's text.

A registry description or a skill written under a licence this library does
not accept is never copied. What may be taken from it is the set of words
that appear in the closed list in topic_words.json: technology, task and
platform names that state what the item is about, not how its author said
it. They become search tags for link-mode cards and topics for outlines.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from .record_rules import read_record

TOPICS_RECORD_TYPE = "library_topic_words/v1"
TOPICS_FILE = Path(__file__).with_name("topic_words.json")
_WORD = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=2)
def topic_vocabulary(path: str = str(TOPICS_FILE)) -> frozenset:
    record = read_record(json.loads(Path(path).read_text(encoding="utf-8")), TOPICS_RECORD_TYPE,
                         ("purpose", "words"))
    return frozenset(record["words"])


def topic_words(*texts: str, limit: int = 8) -> list:
    """The closed-list words that appear in the given texts, in order of first appearance."""
    vocabulary = topic_vocabulary()
    found = []
    for text in texts:
        for word in _WORD.findall(str(text or "").lower()):
            if word in vocabulary and word not in found:
                found.append(word)
    return found[:limit]
