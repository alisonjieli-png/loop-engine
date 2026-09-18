"""Duplicate detection for names, addresses, emails, and phones, with blocking keys and a confidence.

This is the second pre-packaged detection and correction family after text
conformance. Rows are compared only inside blocks formed by declared blocking
keys, so a population is never compared all against all by accident; every
compared pair carries named signals per field, and its confidence is the
weakest named signal, so an exact email match with a different name is a
possible duplicate for review, never an automatic merge. Clusters follow
only decisions above the duplicate threshold; a possible pair becomes a typed
decision request for a judge behind the model call boundary. Nothing here
deletes a row: a dedupe is a proposal that names the survivor and the merged
identities, and the module grants no authority.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from ..core.response_contracts import TYPED_DECISION
from ..core.typed_decision import TypedDecisionRequest, decide
from .text_conformance_operations import email_normalize

FIELD_KINDS = ("name", "address", "email", "phone")
SIGNALS = ("key_equal", "token_jaccard", "sequence_ratio")
OUTCOMES = ("duplicate", "possible", "distinct")
BLOCKING_KEYS = ("name_first_token", "name_initials", "address_number", "email_exact",
                 "phone_last_digits")
STRATEGIES = ("keep_first", "keep_most_complete")
DECISION_CANDIDATES = ("same_entity", "different_entities")
REPORT_RECORD_TYPE = "duplicate_report/v1"
PROPOSAL_RECORD_TYPE = "dedupe_proposal/v1"
DEFAULT_DUPLICATE_AT_OR_ABOVE = 0.92
DEFAULT_POSSIBLE_AT_OR_ABOVE = 0.75
DEFAULT_MAX_BLOCK_SIZE = 500
PHONE_KEY_DIGITS = 10
PHONE_BLOCK_DIGITS = 7
#: Whole-word address abbreviations expanded before comparison; data, not branches.
ADDRESS_ABBREVIATIONS = (
    ("st", "street"), ("ave", "avenue"), ("rd", "road"), ("blvd", "boulevard"), ("dr", "drive"),
    ("ln", "lane"), ("ct", "court"), ("pl", "place"), ("apt", "apartment"), ("ste", "suite"),
    ("fl", "floor"), ("n", "north"), ("s", "south"), ("e", "east"), ("w", "west"),
    ("hwy", "highway"), ("pkwy", "parkway"), ("po", "post office"), ("bldg", "building"),
)
_ADDRESS_MAP = dict(ADDRESS_ABBREVIATIONS)
_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_SPACES = re.compile(r"\s+")
_LEADING_NUMBER = re.compile(r"^(\d+[a-z]?)\b")


class DuplicateDetectionError(ValueError):
    """A field specification, policy, or request is invalid."""


@dataclass(frozen=True)
class DuplicateFieldSpec:
    """Which columns hold which kind of value; at least one kind is declared."""

    name: str = ""
    address: str = ""
    email: str = ""
    phone: str = ""
    identity: str = ""

    def __post_init__(self):
        for column in (self.name, self.address, self.email, self.phone, self.identity):
            if not isinstance(column, str):
                raise DuplicateDetectionError("field specification columns must be text")
        if not any(getattr(self, kind) for kind in FIELD_KINDS):
            raise DuplicateDetectionError(f"declare at least one of {FIELD_KINDS}")

    @property
    def declared(self) -> tuple[str, ...]:
        return tuple(kind for kind in FIELD_KINDS if getattr(self, kind))


@dataclass(frozen=True)
class DuplicatePolicy:
    """Thresholds, blocking keys, and the block size ceiling."""

    duplicate_at_or_above: float = DEFAULT_DUPLICATE_AT_OR_ABOVE
    possible_at_or_above: float = DEFAULT_POSSIBLE_AT_OR_ABOVE
    blocking_keys: tuple[str, ...] = BLOCKING_KEYS
    max_block_size: int = DEFAULT_MAX_BLOCK_SIZE
    version: str = "1.0.0"

    def __post_init__(self):
        for name in ("duplicate_at_or_above", "possible_at_or_above"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not 0 <= value <= 1:
                raise DuplicateDetectionError(f"{name} must be a number from 0 to 1")
        if self.possible_at_or_above > self.duplicate_at_or_above:
            raise DuplicateDetectionError("possible_at_or_above cannot exceed duplicate_at_or_above")
        keys = tuple(self.blocking_keys)
        if not keys or any(key not in BLOCKING_KEYS for key in keys):
            raise DuplicateDetectionError(f"blocking keys must be drawn from {BLOCKING_KEYS}")
        if type(self.max_block_size) is not int or self.max_block_size < 2:
            raise DuplicateDetectionError("max_block_size must be an integer of at least 2")
        object.__setattr__(self, "blocking_keys", keys)

    def to_dict(self) -> dict:
        return {"duplicate_at_or_above": self.duplicate_at_or_above,
                "possible_at_or_above": self.possible_at_or_above,
                "blocking_keys": list(self.blocking_keys), "max_block_size": self.max_block_size,
                "version": self.version}


def _clean(text: str) -> str:
    return _SPACES.sub(" ", _PUNCTUATION.sub(" ", str(text).casefold())).strip()


def name_key(text: str, catalogs: dict | None = None) -> str:
    """Casefolded name without punctuation or trailing legal suffix tokens."""
    suffixes = (catalogs or {}).get("legal_suffixes") or {}
    tokens = _clean(text).split(" ") if _clean(text) else []
    while len(tokens) > 1 and tokens[-1] in suffixes:
        tokens.pop()
    return " ".join(tokens)


def address_key(text: str) -> str:
    """Casefolded address with declared abbreviations expanded whole word."""
    tokens = _clean(text).split(" ") if _clean(text) else []
    return " ".join(_ADDRESS_MAP.get(token, token) for token in tokens)


def email_key(text: str) -> str:
    """The normalized address, or empty text when the value is not an address."""
    result = email_normalize(str(text))
    output = result["output"].strip().casefold()
    return output if "@" in output else ""


def phone_key(text: str) -> str:
    """The last national-length digits of the value, or empty text."""
    digits = re.sub(r"\D", "", str(text))
    return digits[-PHONE_KEY_DIGITS:] if len(digits) >= PHONE_BLOCK_DIGITS else ""


_KEY_BUILDERS = {
    FIELD_KINDS[0]: lambda value, catalogs: name_key(value, catalogs),
    FIELD_KINDS[1]: lambda value, catalogs: address_key(value),
    FIELD_KINDS[2]: lambda value, catalogs: email_key(value),
    FIELD_KINDS[3]: lambda value, catalogs: phone_key(value),
}


def _blocking_values(kind: str, keys: dict) -> tuple[str, ...]:
    """The blocking values one row contributes for one blocking key kind."""
    name, address, email, phone = (keys.get(item, "") for item in FIELD_KINDS)
    if kind == BLOCKING_KEYS[0]:
        return (name.split(" ")[0],) if name else ()
    if kind == BLOCKING_KEYS[1]:
        return ("".join(sorted(token[0] for token in name.split(" ") if token)),) if name else ()
    if kind == BLOCKING_KEYS[2]:
        match = _LEADING_NUMBER.match(address)
        return (match.group(1),) if match else ()
    if kind == BLOCKING_KEYS[3]:
        return (email,) if email else ()
    return (phone[-PHONE_BLOCK_DIGITS:],) if phone else ()


def _jaccard(left: str, right: str) -> float:
    a, b = set(left.split(" ")) - {""}, set(right.split(" ")) - {""}
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compare_keys(left: dict, right: dict, kinds) -> dict:
    """Named signals per declared field where both rows carry a value."""
    signals = {}
    for kind in kinds:
        a, b = left.get(kind, ""), right.get(kind, "")
        if not a or not b:
            continue
        equal = 1.0 if a == b else 0.0
        if kind in FIELD_KINDS[2:]:
            signals[kind] = {SIGNALS[0]: equal}
            continue
        signals[kind] = {SIGNALS[0]: equal, SIGNALS[1]: round(_jaccard(a, b), 3),
                         SIGNALS[2]: round(SequenceMatcher(None, a, b).ratio(), 3)}
    return signals


def field_similarity(signal: dict) -> float:
    """One field's similarity: exact keys are certain; otherwise the best textual signal."""
    if signal.get(SIGNALS[0]) == 1.0:
        return 1.0
    return max(signal.get(SIGNALS[1], 0.0), signal.get(SIGNALS[2], 0.0))


def pair_confidence(signals: dict) -> float:
    """The weakest named field signal; no compared field means no confidence."""
    if not signals:
        return 0.0
    return round(min(field_similarity(signal) for signal in signals.values()), 3)


def classify(confidence: float, policy: DuplicatePolicy) -> str:
    if confidence >= policy.duplicate_at_or_above:
        return OUTCOMES[0]
    if confidence >= policy.possible_at_or_above:
        return OUTCOMES[1]
    return OUTCOMES[2]


@dataclass(frozen=True)
class DuplicatePair:
    left: str
    right: str
    confidence: float
    outcome: str
    signals: dict
    blocking_key: str

    def to_dict(self) -> dict:
        return {"left": self.left, "right": self.right, "confidence": self.confidence,
                "outcome": self.outcome, "signals": self.signals, "blocking_key": self.blocking_key}


@dataclass(frozen=True)
class DuplicateReport:
    """Every compared pair with its outcome, the clusters, and exact counts."""

    rows: int
    fields: DuplicateFieldSpec
    policy: DuplicatePolicy
    pairs: tuple[DuplicatePair, ...]
    clusters: tuple[tuple[str, ...], ...]
    blocks: dict
    skipped_blocks: tuple[dict, ...] = ()
    comparisons: int = 0

    @property
    def counts(self) -> dict:
        counts = {outcome: 0 for outcome in OUTCOMES}
        for pair in self.pairs:
            counts[pair.outcome] += 1
        return counts

    @property
    def exhaustive_within_blocks(self) -> bool:
        return not self.skipped_blocks

    def of_outcome(self, outcome: str) -> tuple[DuplicatePair, ...]:
        if outcome not in OUTCOMES:
            raise DuplicateDetectionError(f"outcome must be one of {OUTCOMES}")
        return tuple(pair for pair in self.pairs if pair.outcome == outcome)

    def to_dict(self) -> dict:
        return {"record_type": REPORT_RECORD_TYPE, "rows": self.rows,
                "fields": {kind: getattr(self.fields, kind) for kind in FIELD_KINDS + ("identity",)},
                "policy": self.policy.to_dict(), "comparisons": self.comparisons,
                "counts": self.counts, "blocks": dict(self.blocks),
                "skipped_blocks": list(self.skipped_blocks),
                "exhaustive_within_blocks": self.exhaustive_within_blocks,
                "pairs": [pair.to_dict() for pair in self.pairs],
                "clusters": [list(cluster) for cluster in self.clusters]}


def _row_identity(row: dict, fields: DuplicateFieldSpec, index: int) -> str:
    if fields.identity and str(row.get(fields.identity, "")).strip():
        return str(row[fields.identity])
    return f"row:{index}"


def row_keys(row: dict, fields: DuplicateFieldSpec, catalogs: dict | None = None) -> dict:
    """The comparison key of every declared field for one row."""
    return {kind: _KEY_BUILDERS[kind](row.get(getattr(fields, kind), "") or "", catalogs)
            for kind in fields.declared}


def _clusters(identities, duplicate_pairs) -> tuple[tuple[str, ...], ...]:
    parent = {identity: identity for identity in identities}

    def find(item):
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for pair in duplicate_pairs:
        parent[find(pair.left)] = find(pair.right)
    groups: dict = {}
    for identity in identities:
        groups.setdefault(find(identity), []).append(identity)
    return tuple(tuple(members) for members in groups.values() if len(members) > 1)


def find_duplicates(rows, fields: DuplicateFieldSpec, policy: DuplicatePolicy | None = None,
                    *, catalogs: dict | None = None) -> DuplicateReport:
    """Compare rows inside declared blocks and report every pair with its outcome."""
    if not isinstance(fields, DuplicateFieldSpec):
        raise DuplicateDetectionError("duplicate detection needs a typed DuplicateFieldSpec")
    policy = policy or DuplicatePolicy()
    if not isinstance(policy, DuplicatePolicy):
        raise DuplicateDetectionError("duplicate detection needs a typed DuplicatePolicy")
    rows = list(rows)
    if any(not isinstance(row, dict) for row in rows):
        raise DuplicateDetectionError("rows must be mappings from column name to value")
    identities, keys = [], {}
    for index, row in enumerate(rows):
        identity = _row_identity(row, fields, index)
        if identity in keys:
            raise DuplicateDetectionError(f"row identity {identity!r} repeats")
        identities.append(identity)
        keys[identity] = row_keys(row, fields, catalogs)
    blocks: dict = {kind: {} for kind in policy.blocking_keys}
    for identity in identities:
        for kind in policy.blocking_keys:
            for value in _blocking_values(kind, keys[identity]):
                blocks[kind].setdefault(value, []).append(identity)
    compared, pairs, skipped, comparisons = set(), [], [], 0
    for kind in policy.blocking_keys:
        for value, members in blocks[kind].items():
            if len(members) > policy.max_block_size:
                skipped.append({"blocking_key": kind, "value": value, "size": len(members)})
                continue
            for position, left in enumerate(members):
                for right in members[position + 1:]:
                    edge = (left, right) if left < right else (right, left)
                    if edge in compared:
                        continue
                    compared.add(edge)
                    comparisons += 1
                    signals = compare_keys(keys[left], keys[right], fields.declared)
                    confidence = pair_confidence(signals)
                    pairs.append(DuplicatePair(left, right, confidence, classify(confidence, policy),
                                               signals, kind))
    pairs.sort(key=lambda pair: (-pair.confidence, pair.left, pair.right))
    duplicates = [pair for pair in pairs if pair.outcome == OUTCOMES[0]]
    block_counts = {kind: {"blocks": len(values),
                           "largest": max((len(members) for members in values.values()), default=0)}
                    for kind, values in blocks.items()}
    return DuplicateReport(len(rows), fields, policy, tuple(pairs), _clusters(identities, duplicates),
                           block_counts, tuple(skipped), comparisons)


@dataclass(frozen=True)
class DedupeProposal:
    """Survivors and merges as a proposal; the rows themselves are untouched."""

    strategy: str
    survivors: tuple[str, ...]
    merges: tuple[dict, ...]
    rows_in: int

    @property
    def rows_out(self) -> int:
        return len(self.survivors)

    def to_dict(self) -> dict:
        return {"record_type": PROPOSAL_RECORD_TYPE, "strategy": self.strategy,
                "rows_in": self.rows_in, "rows_out": self.rows_out,
                "survivors": list(self.survivors), "merges": list(self.merges)}


def _completeness(row: dict) -> int:
    return sum(1 for value in row.values() if str(value).strip())


def dedupe(rows, report: DuplicateReport, *, strategy: str = STRATEGIES[0]) -> DedupeProposal:
    """Propose one survivor per duplicate cluster; possible pairs are left for review."""
    if strategy not in STRATEGIES:
        raise DuplicateDetectionError(f"strategy must be one of {STRATEGIES}")
    rows = list(rows)
    by_identity = {_row_identity(row, report.fields, index): row for index, row in enumerate(rows)}
    order = {identity: index for index, identity in enumerate(by_identity)}
    merged_away, merges = set(), []
    for cluster in report.clusters:
        members = sorted(cluster, key=lambda identity: order[identity])
        if strategy == STRATEGIES[1]:
            members.sort(key=lambda identity: (-_completeness(by_identity[identity]), order[identity]))
        survivor, absorbed = members[0], members[1:]
        merged_away.update(absorbed)
        merges.append({"survivor": survivor, "merged": absorbed})
    survivors = tuple(identity for identity in by_identity if identity not in merged_away)
    return DedupeProposal(strategy, survivors, tuple(merges), len(rows))


def escalation_request(pair: DuplicatePair, left: dict, right: dict) -> TypedDecisionRequest:
    """One possible pair as a bounded typed decision for a judge behind the call boundary."""
    evidence = tuple(f"{side}: " + ", ".join(f"{key}={value}" for key, value in sorted(row.items()))
                     for side, row in (("left", left), ("right", right)))
    return TypedDecisionRequest(
        f"Do these two records describe the same entity? Signals: {pair.signals}",
        DECISION_CANDIDATES, evidence, response_contract_id=TYPED_DECISION,
        semantic_call_id=f"duplicate.{pair.left}.{pair.right}")


def decide_possible_pairs(report: DuplicateReport, rows, route, judge, *,
                          cost_ledger=None, run_id: str = "") -> tuple[dict, ...]:
    """Ask a judge about every possible pair; the answers are typed decisions, not merges."""
    rows = list(rows)
    by_identity = {_row_identity(row, report.fields, index): row for index, row in enumerate(rows)}
    answers = []
    for pair in report.of_outcome(OUTCOMES[1]):
        request = escalation_request(pair, by_identity[pair.left], by_identity[pair.right])
        outcome = decide(request, route, judge, cost_ledger=cost_ledger, run_id=run_id)
        answers.append({"pair": pair.to_dict(), "decision": outcome.decision.to_dict(),
                        "call_record": outcome.call_record.to_dict()})
    return tuple(answers)


def summarize(report: DuplicateReport) -> dict:
    counts = report.counts
    return {"rows": report.rows, "comparisons": report.comparisons, **counts,
            "clusters": len(report.clusters),
            "rows_in_clusters": sum(len(cluster) for cluster in report.clusters),
            "exhaustive_within_blocks": report.exhaustive_within_blocks,
            "skipped_blocks": len(report.skipped_blocks)}


def self_test() -> dict:
    """Keys, blocking, the weakest-signal confidence, clusters, proposals, and escalation."""
    from ..core.typed_decision import EndpointJudge
    from .text_conformance import load_packaged_catalogs, merge_layers
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except DuplicateDetectionError:
            return True
        return False

    catalogs = merge_layers((load_packaged_catalogs(),))
    fields = DuplicateFieldSpec(name="company", address="address", email="email", phone="phone",
                                identity="id")
    rows = [
        {"id": "a", "company": "Acme Widgets, Inc.", "address": "12 N Main St., Ste 4",
         "email": "Sales@Acme.example", "phone": "+1 (415) 555-0100"},
        {"id": "b", "company": "ACME WIDGETS INC", "address": "12 North Main Street Suite 4",
         "email": "sales@acme.example", "phone": "415-555-0100"},
        {"id": "c", "company": "Acme Widgets", "address": "12 N Main St",
         "email": "", "phone": ""},
        {"id": "d", "company": "Beta Holdings LLC", "address": "9 Oak Ave",
         "email": "sales@acme.example", "phone": "415-555-0100"},
        {"id": "e", "company": "Gamma Foods Ltd", "address": "77 Pine Rd",
         "email": "hello@gamma.example", "phone": ""},
        {"id": "f", "company": "Delta Freight Corp", "address": "77 Pine Road",
         "email": "ops@delta.example", "phone": "212-555-0199"},
    ]
    check("keys_fold_case_punctuation_suffixes_and_address_abbreviations",
          name_key("Acme Widgets, Inc.", catalogs) == "acme widgets"
          and name_key("ACME WIDGETS INC", catalogs) == name_key("Acme Widgets", catalogs)
          and name_key("Inc", catalogs) == "inc"
          and address_key("12 N Main St., Ste 4") == "12 north main street suite 4"
          and email_key("Sales@Acme.example") == "sales@acme.example" and email_key("nobody") == ""
          and phone_key("+1 (415) 555-0100") == "4155550100" and phone_key("12") == "")
    report = find_duplicates(rows, fields, catalogs=catalogs)
    by_pair = {(pair.left, pair.right): pair for pair in report.pairs}
    ab = by_pair[("a", "b")]
    check("exact_keys_on_every_compared_field_make_a_duplicate",
          ab.outcome == OUTCOMES[0] and ab.confidence == 1.0
          and all(signal[SIGNALS[0]] == 1.0 for signal in ab.signals.values())
          and set(ab.signals) == set(FIELD_KINDS))
    bd = by_pair[("b", "d")]
    check("a_shared_email_and_phone_with_a_different_name_is_possible_or_distinct_never_a_duplicate",
          bd.outcome != OUTCOMES[0] and bd.confidence < DEFAULT_DUPLICATE_AT_OR_ABOVE
          and bd.signals[FIELD_KINDS[2]][SIGNALS[0]] == 1.0
          and bd.signals[FIELD_KINDS[3]][SIGNALS[0]] == 1.0
          and pair_confidence(bd.signals) == round(min(
              field_similarity(signal) for signal in bd.signals.values()), 3)
          and field_similarity(bd.signals[FIELD_KINDS[0]]) < DEFAULT_POSSIBLE_AT_OR_ABOVE,
          f"confidence={bd.confidence}")
    ac = by_pair.get(("a", "c"))
    check("a_shorter_name_with_the_same_address_is_a_possible_pair_for_review",
          ac is not None and ac.outcome == OUTCOMES[1]
          and FIELD_KINDS[2] not in ac.signals and FIELD_KINDS[3] not in ac.signals,
          f"confidence={ac.confidence if ac else None}")
    exhaustive = len(rows) * (len(rows) - 1) // 2
    check("blocking_keys_bound_the_comparisons_below_all_against_all_and_the_counts_add_up",
          0 < report.comparisons < exhaustive and len(report.pairs) == report.comparisons
          and sum(report.counts.values()) == report.comparisons
          and report.exhaustive_within_blocks and report.blocks[BLOCKING_KEYS[0]]["blocks"] >= 4,
          f"comparisons={report.comparisons} of {exhaustive}")
    check("clusters_follow_duplicate_pairs_only",
          report.clusters == (("a", "b"),)
          and all(pair.outcome == OUTCOMES[0] for pair in report.pairs
                  if {pair.left, pair.right} <= {"a", "b"}))
    proposal = dedupe(rows, report)
    fuller = dedupe(rows, report, strategy=STRATEGIES[1])
    check("a_dedupe_is_a_proposal_that_keeps_the_first_or_the_fullest_row_and_names_the_merged_ones",
          proposal.survivors == ("a", "c", "d", "e", "f") and proposal.rows_in == 6
          and proposal.rows_out == 5 and proposal.merges == ({"survivor": "a", "merged": ["b"]},)
          and fuller.merges[0]["survivor"] in ("a", "b") and len(rows) == 6
          and refuses(lambda: dedupe(rows, report, strategy="drop_all")))
    small = DuplicatePolicy(max_block_size=2, blocking_keys=(BLOCKING_KEYS[0],))
    limited = find_duplicates(rows, fields, small, catalogs=catalogs)
    check("a_block_above_the_size_ceiling_is_recorded_as_skipped_never_silently",
          not limited.exhaustive_within_blocks
          and limited.skipped_blocks[0]["blocking_key"] == BLOCKING_KEYS[0]
          and limited.skipped_blocks[0]["size"] == 3 and limited.to_dict()["skipped_blocks"])
    check("specifications_policies_and_rows_are_validated",
          all(refuses(action) for action in (
              lambda: DuplicateFieldSpec(),
              lambda: DuplicatePolicy(duplicate_at_or_above=1.5),
              lambda: DuplicatePolicy(possible_at_or_above=0.95, duplicate_at_or_above=0.9),
              lambda: DuplicatePolicy(blocking_keys=("soundex",)),
              lambda: DuplicatePolicy(max_block_size=1),
              lambda: find_duplicates([{"id": "x", "company": "A"}, {"id": "x", "company": "A"}],
                                      fields, catalogs=catalogs),
              lambda: find_duplicates(rows, {"name": "company"}, catalogs=catalogs),
              lambda: report.of_outcome("merged"))))
    seen = []

    def transport(payload):
        seen.append(payload)
        return {"decision": DECISION_CANDIDATES[0],
                "probabilities": {DECISION_CANDIDATES[0]: 0.8, DECISION_CANDIDATES[1]: 0.2},
                "confidence": 0.8, "reason": "same address and a shortened name"}

    judge = EndpointJudge(transport, provider="fixture", model="fixture-judge")
    answers = decide_possible_pairs(report, rows, judge.route("judge.fixture"), judge)
    possible = report.of_outcome(OUTCOMES[1])
    check("possible_pairs_become_typed_decisions_with_two_candidates_and_stay_out_of_the_clusters",
          len(answers) == len(possible) == len(seen) > 0
          and all(answer["decision"]["chosen"] == DECISION_CANDIDATES[0] for answer in answers)
          and all(answer["call_record"]["model_kind"] == "judgment" for answer in answers)
          and "same entity" in escalation_request(possible[0], rows[0], rows[2]).question
          and report.clusters == (("a", "b"),),
          f"answers={len(answers)}")
    summary = summarize(report)
    check("the_summary_and_the_record_keep_exact_denominators",
          summary["rows"] == 6 and summary["comparisons"] == report.comparisons
          and summary[OUTCOMES[0]] + summary[OUTCOMES[1]] + summary[OUTCOMES[2]] == report.comparisons
          and summary["rows_in_clusters"] == 2
          and report.to_dict()["record_type"] == REPORT_RECORD_TYPE
          and proposal.to_dict()["record_type"] == PROPOSAL_RECORD_TYPE)
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "duplicate_detection_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
