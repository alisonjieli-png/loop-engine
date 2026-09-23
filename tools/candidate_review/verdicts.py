"""Read one reviewer's answer into a typed verdict, or say exactly why it is not one.

A reviewer's answer is untrusted text. It counts only when it is one JSON object
with exactly the declared keys, names the digest of the exact bytes it was
asked about, decides ``approve`` or ``reject``, cites only criteria the request
listed, and follows two rules: a rejection has at least one blocking finding
and a written reason; an approval has no blocking finding. Anything else is an
invalid answer with a stable code, which the panel records and replaces with a
reviewer of a family it has not heard yet. There is no formatting repair: an
invalid answer is never rewritten into a valid one. An engine may declare that
its model writes reasoning before the verdict; then the verdict is the last
JSON object of the text, and text after it is still refused.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

APPROVE, REJECT = "approve", "reject"
DECISIONS = (APPROVE, REJECT)
#: How an engine declares its answers arrive. ``json_only``: the answer is one JSON object (or one fenced
#: JSON block) and nothing else. ``json_after_reasoning``: the answer is the last JSON object in the text
#: and nothing follows it, for a model that writes its reasoning into the answer text. Text after the
#: verdict is refused in both formats.
JSON_ONLY, JSON_AFTER_REASONING = "json_only", "json_after_reasoning"
ANSWER_FORMATS = (JSON_ONLY, JSON_AFTER_REASONING)
TRAILING_FENCE = re.compile(r"\n?```[ \t]*\Z")
ANSWER_FIELDS = frozenset({"body_sha256", "decision", "findings", "reasons"})
FINDING_FIELDS = frozenset({"criterion_id", "blocking", "text"})
#: The answer must name the digest of the bytes it judged. The mutant control in the checks turns
#: this off to prove that an answer about other bytes is refused by this comparison.
BIND_TO_BODY_DIGEST = True
#: One fenced JSON block is accepted, because the instructions show the answer in one.
FENCED = re.compile(r"\A```(?:json)?[ \t]*\n(.*)\n```\Z", re.DOTALL)
TEXT_LIMIT = 4000
MAXIMUM_FINDINGS = 40


@dataclass(frozen=True)
class Finding:
    criterion_id: str
    blocking: bool
    text: str

    def to_dict(self) -> dict:
        return {"criterion_id": self.criterion_id, "blocking": self.blocking, "text": self.text}


@dataclass(frozen=True)
class VerdictContent:
    decision: str
    findings: tuple
    reasons: str

    def to_dict(self) -> dict:
        return {"decision": self.decision, "findings": [finding.to_dict() for finding in self.findings],
                "reasons": self.reasons}


def _final_object(text: str):
    """The last JSON object in the text when nothing but whitespace or a closing fence follows it."""
    stripped = TRAILING_FENCE.sub("", text.strip()).rstrip()
    decoder = json.JSONDecoder()
    for index in reversed([position for position, character in enumerate(stripped) if character == "{"]):
        try:
            value, end = decoder.raw_decode(stripped, index)
        except ValueError:
            continue
        if type(value) is dict and not stripped[end:].strip():
            return value
    return None


def parse_verdict(text: str, *, body_sha256: str, criteria_ids, answer_format: str = JSON_ONLY) -> tuple:
    """Return (VerdictContent, "") for a valid answer, or (None, code) for an invalid one."""
    if answer_format not in ANSWER_FORMATS:
        return None, "answer_format_unknown"
    stripped = str(text).strip()
    if answer_format == JSON_AFTER_REASONING:
        value = _final_object(stripped)
    else:
        fenced = FENCED.match(stripped)
        if fenced:
            stripped = fenced.group(1).strip()
        try:
            value = json.loads(stripped)
        except ValueError:
            value = None
    if type(value) is not dict:
        return None, "answer_not_json"
    if set(value) - ANSWER_FIELDS:
        return None, "answer_fields_unknown"
    if ANSWER_FIELDS - set(value):
        return None, "answer_fields_missing"
    if BIND_TO_BODY_DIGEST and value["body_sha256"] != body_sha256:
        return None, "answer_names_other_bytes"
    decision = value["decision"]
    if decision not in DECISIONS:
        return None, "decision_unknown"
    reasons = value["reasons"]
    if type(reasons) is not str or len(reasons) > TEXT_LIMIT:
        return None, "reasons_invalid"
    rows = value["findings"]
    if type(rows) is not list or len(rows) > MAXIMUM_FINDINGS:
        return None, "findings_invalid"
    findings = []
    for row in rows:
        if type(row) is not dict or set(row) != FINDING_FIELDS:
            return None, "finding_invalid"
        if row["criterion_id"] not in criteria_ids:
            return None, "finding_cites_unknown_criterion"
        if type(row["blocking"]) is not bool or type(row["text"]) is not str or not row["text"].strip() \
                or len(row["text"]) > TEXT_LIMIT:
            return None, "finding_invalid"
        findings.append(Finding(row["criterion_id"], row["blocking"], row["text"].strip()))
    blocking = [finding for finding in findings if finding.blocking]
    if decision == REJECT and not blocking:
        return None, "rejection_without_blocking_finding"
    if decision == REJECT and not reasons.strip():
        return None, "rejection_without_reason"
    if decision == APPROVE and blocking:
        return None, "approval_with_blocking_finding"
    return VerdictContent(decision, tuple(findings), reasons.strip()), ""
