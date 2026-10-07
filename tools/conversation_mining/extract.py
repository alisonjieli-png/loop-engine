"""Intent extraction and screening.

``classify`` a line's intent and ``extract`` the phrases worth following up.
Every extracted phrase goes through the query multiplier's ``words()``
normalisation and its sensitive/secret screen; a phrase that fails is dropped
and counted, never stored. The goal is an index of what the owner asked for or
complained about, tied back to where it was said.
"""
from __future__ import annotations

import re

from knowledge_radar.query_matrix import SECRET_PATTERNS, words
from knowledge_radar.community_intake import public_url

#: Marker patterns for each intent. These are cheap lexical signals, not a
#: model. A line may match more than one; the first in order wins.
REQUEST = re.compile(
    r"\b(i need|we need|we should|let'?s|can you|could you|please|i want|i'?d like|"
    r"build|create|add|implement|generate|make us|document|explore|review|fix)\b",
    re.IGNORECASE)
PAIN = re.compile(
    r"\b(why are you having (so much )?trouble|annoying|too slow|not working|broken|"
    r"still not|doesn'?t work|fails?|failed|error|issue with|problem)\b",
    re.IGNORECASE)
PREFERENCE = re.compile(
    r"\b(i prefer|should be|style|brand|tone|format|more beautiful|stylized|improved)\b",
    re.IGNORECASE)
DECISION = re.compile(
    r"\b(approved|i approve|authorized|go ahead|ship it|deploy|open registration|decided)\b",
    re.IGNORECASE)
REFERENCE = re.compile(
    r"(https?://\S+|github\.com/\S+|huggingface\.co/\S+|@[a-z0-9-]+/[a-z0-9-]+)",
    re.IGNORECASE)

#: Phrase extraction: noun-ish and verb-object fragments the owner used. This
#: is deliberately crude; the dimension mapper does the finer bucketing.
_PHRASE = re.compile(
    r"\b([a-z][a-z0-9+#./-]*(?: [a-z0-9+#./-]+){0,4})\b", re.IGNORECASE)

#: Stop phrases that carry no follow-up value (greetings, fillers).
_STOP = {
    "i", "me", "my", "we", "you", "the", "a", "an", "and", "or", "is", "are", "was",
    "were", "it", "this", "that", "to", "of", "in", "on", "for", "with", "as", "at",
    "be", "by", "from", "have", "has", "had", "do", "does", "did", "can", "could",
    "should", "would", "will", "just", "really", "very", "so", "if", "then", "than",
    "ok", "okay", "yes", "no", "thanks", "thank you", "hello", "hi", "hey",
}


def classify(text: str) -> str:
    """Assign one intent to a line. Order chooses the strongest signal."""
    if DECISION.search(text):
        return "decision"
    if PAIN.search(text):
        return "pain"
    if REFERENCE.search(text):
        return "reference"
    if PREFERENCE.search(text):
        return "preference"
    if REQUEST.search(text):
        return "request"
    return "request"


def extract_phrases(text: str, *, limit: int = 12) -> tuple:
    """Return screened phrases and the number refused by the sensitive-text screen."""
    found = []
    refused = 0
    for match in _PHRASE.finditer(text):
        candidate = match.group(1).strip()
        if not candidate or candidate.lower() in _STOP:
            continue
        # Skip pure link fragments; those are references, captured separately.
        if candidate.startswith(("http", "github.com", "huggingface.co")):
            continue
        try:
            normal = words(candidate)
        except ValueError:
            # Screened out: sensitive, control-char, secret-shaped or malformed.
            refused += 1
            continue
        if normal and normal not in found:
            found.append(normal)
        if len(found) >= limit:
            break
    return tuple(found), refused


def extract_references(text: str, *, limit: int = 6) -> tuple:
    """Keep safe public source references; signed/private URLs never enter the index."""
    refs = []
    for match in REFERENCE.finditer(text):
        ref = match.group(1).rstrip(".,);\"'")
        if ref.startswith(("github.com/", "huggingface.co/")):
            ref = "https://" + ref
        try:
            ref = public_url(ref)
            if any(pattern.search(ref) for pattern in SECRET_PATTERNS):
                continue
        except ValueError:
            continue
        if ref not in refs:
            refs.append(ref)
        if len(refs) >= limit:
            break
    return tuple(refs)
