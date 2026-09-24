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

A batch answer judges several candidates in one reply. It counts only when it
is one JSON object with exactly the key ``verdicts`` holding exactly one
verdict per candidate, in the order the request named them. Each verdict must
name its own candidate's identity and the digest of that candidate's bytes and
is then read by the same rules as a single answer, so one bad verdict costs
only its own candidate. A list of another length says the reviewer lost track
of the candidates, and no verdict in it counts.
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
#: A batch answer holds exactly this key, and each of its verdicts the answer fields and the identity.
BATCH_FIELDS = frozenset({"verdicts"})
MEMBER_FIELDS = ANSWER_FIELDS | {"identity"}
#: Each verdict of a batch must name its own candidate. The mutant control turns this off to prove that a
#: verdict naming another candidate is refused by this comparison.
BIND_TO_MEMBER_IDENTITY = True
#: A batch answer must hold one verdict per candidate. The mutant control turns this off to prove that a
#: list that dropped or added a verdict is refused by this comparison.
BATCH_COUNT_MUST_MATCH = True
#: One fenced JSON block is accepted, because the instructions show the answer in one.
FENCED = re.compile(r"\A```(?:json)?[ \t]*\n(.*)\n```\Z", re.DOTALL)
TEXT_LIMIT = 4000
MAXIMUM_FINDINGS = 40
#: What the JSON reader raises on text that is not one answer. Text nested deeper than the reader's
#: recursion limit raises RecursionError, which is not a ValueError; an answer never stops the run.
UNREADABLE = (ValueError, RecursionError)


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
        except UNREADABLE:
            continue
        if type(value) is dict and not stripped[end:].strip():
            return value
    return None


def _answer_value(text: str, answer_format: str):
    """The one JSON value an answer holds in its declared format, or None."""
    stripped = str(text).strip()
    if answer_format == JSON_AFTER_REASONING:
        return _final_object(stripped)
    fenced = FENCED.match(stripped)
    if fenced:
        stripped = fenced.group(1).strip()
    try:
        return json.loads(stripped)
    except UNREADABLE:
        return None


def parse_verdict(text: str, *, body_sha256: str, criteria_ids, answer_format: str = JSON_ONLY) -> tuple:
    """Return (VerdictContent, "") for a valid answer, or (None, code) for an invalid one."""
    if answer_format not in ANSWER_FORMATS:
        return None, "answer_format_unknown"
    value = _answer_value(text, answer_format)
    if type(value) is not dict:
        return None, "answer_not_json"
    return verdict_from_value(value, body_sha256=body_sha256, criteria_ids=criteria_ids)


def parse_batch_verdicts(text: str, *, members, answer_format: str = JSON_ONLY) -> tuple:
    """Read a batch answer: (per-member results, "") or (None, code) when no verdict in it can count.

    ``members`` lists (identity, body_sha256, criteria_ids) in the order the request named the candidates;
    each result is (VerdictContent, "") or (None, code) for that candidate."""
    if answer_format not in ANSWER_FORMATS:
        return None, "answer_format_unknown"
    value = _answer_value(text, answer_format)
    if type(value) is not dict:
        return None, "answer_not_json"
    if set(value) != BATCH_FIELDS:
        return None, "batch_answer_fields_invalid"
    rows = value["verdicts"]
    if type(rows) is not list:
        return None, "batch_verdicts_not_a_list"
    members = list(members)
    if BATCH_COUNT_MUST_MATCH and len(rows) != len(members):
        return None, "batch_verdict_count_mismatch"
    results = []
    for position, (identity, body_sha256, criteria_ids) in enumerate(members):
        row = rows[position] if position < len(rows) else None
        if type(row) is not dict:
            results.append((None, "answer_not_json"))
        elif set(row) - MEMBER_FIELDS:
            results.append((None, "answer_fields_unknown"))
        elif MEMBER_FIELDS - set(row):
            results.append((None, "answer_fields_missing"))
        elif BIND_TO_MEMBER_IDENTITY and row["identity"] != identity:
            results.append((None, "answer_names_other_candidate"))
        else:
            results.append(verdict_from_value({name: row[name] for name in ANSWER_FIELDS}, body_sha256=body_sha256,
                                              criteria_ids=criteria_ids))
    return results, ""


def verdict_from_value(value: dict, *, body_sha256: str, criteria_ids) -> tuple:
    """The single-answer rules applied to one JSON object: (VerdictContent, "") or (None, code)."""
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
        if type(row) is not dict or set(row) != FINDING_FIELDS or type(row["criterion_id"]) is not str:
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
