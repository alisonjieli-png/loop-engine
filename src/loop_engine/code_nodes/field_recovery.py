"""Email recovery and malformed field detection with a confidence per decision.

Two more members of the detection and correction family. Email recovery
turns the common ways people spoil an address (spelled-out symbols, doubled
or stray punctuation around the separator, a typed domain from a declared
correction table) back into a valid address, and refuses to guess when the
shape stays invalid or a repair is ambiguous; every correction names its
reasons and carries a confidence that is the weakest named signal, so the
same apply, hold, and escalate bands as text conformance decide what
happens. Malformed field detection finds the values in a column whose
induced character pattern differs from the column's dominant pattern, with
a confidence that is the share margin, and says so honestly when no
dominant pattern exists. The tables are data a caller can replace; the
module grants no authority and changes no source.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .text_conformance_operations import (
    DEFAULT_APPLY_AT_OR_ABOVE, DEFAULT_ESCALATE_BELOW, OUTCOMES, classify, correction,
    email_normalize, induce_pattern,
)

RECOVERY_RECORD_TYPE = "email_recovery_report/v1"
MALFORMED_RECORD_TYPE = "malformed_field_report/v1"
DEFAULT_DOMINANT_SHARE = 0.6
#: Spelled-out separators people type to hide an address, replaced whole.
SYMBOL_WORDS = ((" at ", "@"), ("(at)", "@"), ("[at]", "@"), ("{at}", "@"),
                (" dot ", "."), ("(dot)", "."), ("[dot]", "."), ("{dot}", "."))
#: Punctuation slips around the separator and the dots, with their confidence.
PUNCTUATION_REPAIRS = (("@@", "@", 0.9), ("..", ".", 0.9), (",com", ".com", 0.9),
                       (".com.", ".com", 0.9), ("@.", "@", 0.85), (".@", "@", 0.85))
#: Typed domains and the domain they almost always mean, with the confidence
#: of that reading; a real domain that is also a plausible typo stays below
#: the apply band so it is held for review rather than rewritten.
DOMAIN_CORRECTIONS = (
    ("gmial.com", "gmail.com", 0.9), ("gmail.con", "gmail.com", 0.9), ("gmal.com", "gmail.com", 0.85),
    ("gamil.com", "gmail.com", 0.85), ("gmail.co", "gmail.com", 0.7),
    ("hotmail.con", "hotmail.com", 0.9), ("hotmial.com", "hotmail.com", 0.85),
    ("hotmail.co", "hotmail.com", 0.7), ("yahoo.con", "yahoo.com", 0.9), ("yaho.com", "yahoo.com", 0.85),
    ("outlook.con", "outlook.com", 0.9), ("outlok.com", "outlook.com", 0.85),
    ("icloud.con", "icloud.com", 0.9),
)
SYMBOL_CONFIDENCE = 0.9
TRAILING_PUNCTUATION_CONFIDENCE = 0.92
AMBIGUOUS_CONFIDENCE = 0.5
INVALID_CONFIDENCE = 0.3


class FieldRecoveryError(ValueError):
    """A recovery table, parameter, or request is invalid."""


@dataclass(frozen=True)
class RecoveryTables:
    """The declared repair data; a caller supplies its own to extend or replace it."""

    symbol_words: tuple = SYMBOL_WORDS
    punctuation_repairs: tuple = PUNCTUATION_REPAIRS
    domain_corrections: tuple = DOMAIN_CORRECTIONS

    def __post_init__(self):
        for name in ("symbol_words", "punctuation_repairs", "domain_corrections"):
            rows = tuple(getattr(self, name))
            width = 2 if name == "symbol_words" else 3
            if any(len(row) != width or not isinstance(row[0], str) or not isinstance(row[1], str)
                   for row in rows):
                raise FieldRecoveryError(f"{name} rows need {width} fields with text first")
            if width == 3 and any(type(row[2]) not in (int, float) or not 0 <= row[2] <= 1 for row in rows):
                raise FieldRecoveryError(f"{name} confidences must be numbers from 0 to 1")
            object.__setattr__(self, name, rows)


@dataclass(frozen=True)
class RecoveryPolicy:
    apply_at_or_above: float = DEFAULT_APPLY_AT_OR_ABOVE
    escalate_below: float = DEFAULT_ESCALATE_BELOW

    def __post_init__(self):
        for name in ("apply_at_or_above", "escalate_below"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not 0 <= value <= 1:
                raise FieldRecoveryError(f"{name} must be a number from 0 to 1")
        if self.escalate_below > self.apply_at_or_above:
            raise FieldRecoveryError("escalate_below cannot exceed apply_at_or_above")


def recover_email(value: str, tables: RecoveryTables | None = None) -> dict:
    """One address repaired from declared tables, or left alone with the reason."""
    tables = tables or RecoveryTables()
    if not isinstance(tables, RecoveryTables):
        raise FieldRecoveryError("email recovery needs typed RecoveryTables")
    original = str(value)
    text = original.strip()
    reasons, factors = [], []
    lowered = text.lower()
    for word, symbol in tables.symbol_words:
        if word in lowered:
            index = lowered.index(word)
            text = text[:index] + symbol + text[index + len(word):]
            lowered = text.lower()
            reasons.append(f"symbol_word:{word.strip()}")
            factors.append(SYMBOL_CONFIDENCE)
    for wrong, right, confidence in tables.punctuation_repairs:
        if wrong in text:
            text = text.replace(wrong, right)
            reasons.append(f"punctuation:{wrong}")
            factors.append(confidence)
    if text.endswith(".") or text.endswith(","):
        text = text.rstrip(".,")
        reasons.append("trailing_punctuation_removed")
        factors.append(TRAILING_PUNCTUATION_CONFIDENCE)
    local, separator, domain = text.rpartition("@")
    if separator:
        domain_lower = domain.lower()
        for wrong, right, confidence in tables.domain_corrections:
            if domain_lower == wrong:
                text = local + "@" + right
                reasons.append(f"domain:{wrong}->{right}")
                factors.append(confidence)
                break
    normalized = email_normalize(text)
    if "multiple_values_or_spaces" in normalized["reasons"]:
        return correction(original, AMBIGUOUS_CONFIDENCE, reasons + ["ambiguous_address"], False)
    if "invalid_email_shape" in normalized["reasons"]:
        return correction(original, INVALID_CONFIDENCE, reasons + ["unrecoverable_shape"], False)
    output = normalized["output"]
    changed = output != original
    if not changed:
        return correction(original, 1.0, ["valid_address"], False)
    if output != text:
        reasons.append("email_normalized")
        factors.append(normalized["confidence"])
    return correction(output, min(factors) if factors else normalized["confidence"], reasons, True)


def recover_column(values, tables: RecoveryTables | None = None,
                   policy: RecoveryPolicy | None = None) -> dict:
    """Every value's correction with its outcome, and exact counts per outcome."""
    policy = policy or RecoveryPolicy()
    if not isinstance(policy, RecoveryPolicy):
        raise FieldRecoveryError("email recovery needs a typed RecoveryPolicy")
    rows, counts = [], {outcome: 0 for outcome in OUTCOMES}
    for index, value in enumerate(values):
        result = recover_email("" if value is None else str(value), tables)
        outcome = classify(result["confidence"], result["changed"], policy.apply_at_or_above,
                           policy.escalate_below)
        counts[outcome] += 1
        rows.append({"index": index, "input": "" if value is None else str(value), **result,
                     "outcome": outcome})
    return {"record_type": RECOVERY_RECORD_TYPE, "total": len(rows), "counts": counts, "rows": rows}


def detect_malformed(values, *, dominant_share: float = DEFAULT_DOMINANT_SHARE) -> dict:
    """Values whose collapsed character pattern is not the column's dominant pattern."""
    if type(dominant_share) not in (int, float) or not 0 < dominant_share <= 1:
        raise FieldRecoveryError("dominant_share must be a number above 0 and at most 1")
    texts = ["" if value is None else str(value).strip() for value in values]
    patterns = [induce_pattern(text)["collapsed"] for text in texts]
    counts = Counter(patterns)
    total = len(texts)
    if not total:
        return {"record_type": MALFORMED_RECORD_TYPE, "total": 0, "dominant_pattern": "",
                "dominant_share": 0.0, "no_dominant_pattern": True, "flagged": []}
    pattern, count = counts.most_common(1)[0]
    share = round(count / total, 3)
    if share < dominant_share:
        return {"record_type": MALFORMED_RECORD_TYPE, "total": total, "dominant_pattern": pattern,
                "dominant_share": share, "no_dominant_pattern": True, "flagged": []}
    flagged = [{"index": index, "value": texts[index], "pattern": found,
                "confidence": round(max(0.0, min(1.0, share - counts[found] / total)), 3),
                "reasons": [f"pattern_differs_from_dominant:{pattern}"]}
               for index, found in enumerate(patterns) if found != pattern]
    return {"record_type": MALFORMED_RECORD_TYPE, "total": total, "dominant_pattern": pattern,
            "dominant_share": share, "no_dominant_pattern": False, "flagged": flagged}


def self_test() -> dict:
    """Recoveries with their bands, refusals, exact counts, and malformed detection."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except FieldRecoveryError:
            return True
        return False

    policy = RecoveryPolicy()

    def outcome(result):
        return classify(result["confidence"], result["changed"], policy.apply_at_or_above,
                        policy.escalate_below)

    spelled = recover_email("John.Smith at Example dot com")
    check("spelled_out_symbols_are_recovered_into_a_valid_address_and_applied",
          spelled["output"] == "john.smith@example.com" and spelled["changed"]
          and outcome(spelled) == OUTCOMES[0] and spelled["confidence"] == SYMBOL_CONFIDENCE
          and any(reason.startswith("symbol_word:") for reason in spelled["reasons"]))
    typo = recover_email("maria@gmail.con")
    check("a_declared_domain_typo_is_corrected_with_its_declared_confidence",
          typo["output"] == "maria@gmail.com" and typo["confidence"] == 0.9
          and outcome(typo) == OUTCOMES[0] and "domain:gmail.con->gmail.com" in typo["reasons"])
    ambiguous_domain = recover_email("maria@gmail.co")
    check("a_plausible_typo_that_is_also_a_real_domain_is_held_not_applied",
          ambiguous_domain["output"] == "maria@gmail.com" and ambiguous_domain["confidence"] == 0.7
          and outcome(ambiguous_domain) == OUTCOMES[1])
    doubled = recover_email("sam@@example..com,")
    check("punctuation_slips_are_repaired_and_the_weakest_repair_sets_the_confidence",
          doubled["output"] == "sam@example.com" and doubled["confidence"] == 0.9
          and outcome(doubled) == OUTCOMES[0] and "trailing_punctuation_removed" in doubled["reasons"])
    valid = recover_email("Ana@Example.com")
    check("an_address_that_only_needs_normalization_is_normalized_and_a_valid_one_is_unchanged",
          valid["output"] == "ana@example.com" and valid["changed"] and "email_normalized" in valid["reasons"]
          and recover_email("ana@example.com") == correction("ana@example.com", 1.0, ["valid_address"], False)
          and outcome(recover_email("ana@example.com")) == OUTCOMES[3])
    two = recover_email("ana@example.com; bo@example.com")
    broken = recover_email("ana.example.com")
    check("ambiguous_and_unrecoverable_values_are_escalated_and_left_unchanged",
          not two["changed"] and two["confidence"] == AMBIGUOUS_CONFIDENCE and outcome(two) == OUTCOMES[2]
          and not broken["changed"] and broken["confidence"] == INVALID_CONFIDENCE
          and outcome(broken) == OUTCOMES[2] and "unrecoverable_shape" in broken["reasons"])
    column = recover_column(["ana@example.com", "maria@gmail.con", "x at y dot org", None, "bad"])
    check("a_column_report_keeps_exact_counts_per_outcome",
          column["total"] == 5 and sum(column["counts"].values()) == 5
          and column["counts"][OUTCOMES[0]] == 2 and column["counts"][OUTCOMES[2]] == 2
          and column["counts"][OUTCOMES[3]] == 1 and column["rows"][2]["output"] == "x@y.org")
    custom = RecoveryTables(domain_corrections=(("exmaple.com", "example.com", 0.88),))
    check("a_caller_supplied_table_replaces_the_declared_one_and_is_validated",
          recover_email("ana@exmaple.com", custom)["output"] == "ana@example.com"
          and recover_email("ana@gmail.con", custom)["output"] == "ana@gmail.con"
          and refuses(lambda: RecoveryTables(domain_corrections=(("a", "b", 1.5),)))
          and refuses(lambda: RecoveryTables(symbol_words=(("only",),)))
          and refuses(lambda: RecoveryPolicy(escalate_below=0.95, apply_at_or_above=0.9))
          and refuses(lambda: recover_email("x", {"symbol_words": ()})))
    dates = detect_malformed(["2026-09-18", "2026-09-19", "2026-10-01", "18/09/2026", "2026-11-30"])
    check("a_value_whose_pattern_differs_from_the_dominant_pattern_is_flagged_with_the_share_margin",
          not dates["no_dominant_pattern"] and dates["dominant_pattern"] == "9+-9+-9+"
          and dates["dominant_share"] == 0.8 and len(dates["flagged"]) == 1
          and dates["flagged"][0]["index"] == 3 and dates["flagged"][0]["confidence"] == 0.6
          and dates["flagged"][0]["reasons"] == ["pattern_differs_from_dominant:9+-9+-9+"])
    mixed = detect_malformed(["abc", "123", "a1", "-", "x y"])
    check("a_column_without_a_dominant_pattern_flags_nothing_and_says_so",
          mixed["no_dominant_pattern"] and mixed["flagged"] == [] and mixed["total"] == 5
          and detect_malformed([])["no_dominant_pattern"]
          and refuses(lambda: detect_malformed(["a"], dominant_share=0)))
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "field_recovery_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
