"""How a contract is matched: exact is one mode, not the rule for everything.

The owner's September 18 direction: whenever a contract is proposed, decide
how a value is compared with it. A byte-exact comparison is right for a
digest or an identifier and wrong for a restated requirement, a candidate
row with extra keys, or a description that says the same thing in other
words. Making every contract exact makes the engine brittle; making every
contract loose makes it unsafe. So each contract names one of five modes,
and the decisive facts stay exact inside the looser modes through blocking
keys.

```text
Match modes, strict to open
├── exact            the values are equal as given
├── canonical        equal after whitespace, case, quote, and key-order canonicalization
├── purpose          the observed value serves the declared purpose: required keys
│                    present with compatible types; extra keys allowed
├── semantic_blocked blocking keys equal exactly; the remaining text similar above
│                    a declared threshold, measured deterministically
└── model_judged     beyond deterministic reach; the result names the judgment
                     contract a separate model call must answer, and decides nothing
```

Matching grants nothing and never rewrites either side. A ``model_judged``
result is a typed request for a judgment, not a pass.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

MATCH_MODES = ("exact", "canonical", "purpose", "semantic_blocked", "model_judged")
EXACT, CANONICAL, PURPOSE, SEMANTIC_BLOCKED, MODEL_JUDGED = MATCH_MODES

_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'",
                         "«": '"', "»": '"'})
_SPACE = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9]+")


class ContractMatchError(ValueError):
    """A match policy is invalid or a value cannot be compared in its mode."""


def canonical_text(value: str) -> str:
    """Lowercase, straight quotes, single spaces; the text people call the same."""
    return _SPACE.sub(" ", str(value).translate(_QUOTES)).strip().lower()


def canonical_value(value):
    """Canonicalize strings inside any JSON-like value, keeping its structure."""
    if isinstance(value, str):
        return canonical_text(value)
    if isinstance(value, dict):
        return {str(key): canonical_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [canonical_value(item) for item in value]
    return value


def _type_family(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "text"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (list, tuple)):
        return "list"
    return "null" if value is None else type(value).__name__


def _tokens(value) -> set[str]:
    return set(_TOKEN.findall(canonical_text(json.dumps(value, sort_keys=True, default=str)
                                             if not isinstance(value, str) else value)))


def token_similarity(left, right) -> float:
    """Jaccard similarity of the token sets; deterministic and model free."""
    a, b = _tokens(left), _tokens(right)
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


@dataclass(frozen=True)
class ContractMatchPolicy:
    """The declared way one contract is compared with an observed value."""

    mode: str
    required_keys: tuple[str, ...] = ()
    blocking_keys: tuple[str, ...] = ()
    threshold: float = 0.0
    judge_contract_id: str = ""

    def __post_init__(self):
        if self.mode not in MATCH_MODES:
            raise ContractMatchError(f"match mode must be one of {MATCH_MODES}")
        for name in ("required_keys", "blocking_keys"):
            keys = tuple(getattr(self, name))
            if any(not isinstance(item, str) or not item for item in keys):
                raise ContractMatchError(f"{name} must be nonempty key names")
            object.__setattr__(self, name, keys)
        if type(self.threshold) not in (int, float) or not 0 <= self.threshold <= 1:
            raise ContractMatchError("threshold must be a number from 0 to 1")
        if self.mode == SEMANTIC_BLOCKED and self.threshold == 0:
            raise ContractMatchError("a semantic match declares a threshold above 0")
        if self.mode == MODEL_JUDGED and not self.judge_contract_id:
            raise ContractMatchError("a model judged match names the judgment contract it needs")
        if self.mode != MODEL_JUDGED and self.judge_contract_id:
            raise ContractMatchError("only a model judged match names a judgment contract")
        if self.mode != SEMANTIC_BLOCKED and self.blocking_keys:
            raise ContractMatchError("blocking keys belong to a semantic match")

    def to_dict(self) -> dict:
        return {"record_type": "contract_match_policy/v1", "mode": self.mode,
                "required_keys": list(self.required_keys),
                "blocking_keys": list(self.blocking_keys), "threshold": self.threshold,
                "judge_contract_id": self.judge_contract_id}


@dataclass(frozen=True)
class ContractMatch:
    """The outcome of one comparison; ``matched`` is None only when a judgment is needed."""

    mode: str
    matched: "bool | None"
    score: float
    reason: str
    blocked_on: tuple[str, ...] = ()
    judge_contract_id: str = ""

    def to_dict(self) -> dict:
        return {"record_type": "contract_match/v1", "mode": self.mode, "matched": self.matched,
                "score": self.score, "reason": self.reason, "blocked_on": list(self.blocked_on),
                "judge_contract_id": self.judge_contract_id}


#: Text that must say the same thing, not the same bytes.
CANONICAL_TEXT = ContractMatchPolicy(CANONICAL)


def match_contract(policy: ContractMatchPolicy, expected, observed) -> ContractMatch:
    """Compare ``observed`` with ``expected`` the way the policy declares."""
    if not isinstance(policy, ContractMatchPolicy):
        raise ContractMatchError("a typed ContractMatchPolicy is required")
    if policy.mode == EXACT:
        matched = expected == observed
        return ContractMatch(EXACT, matched, 1.0 if matched else 0.0,
                             "equal as given" if matched else "values differ")
    if policy.mode == CANONICAL:
        matched = canonical_value(expected) == canonical_value(observed)
        return ContractMatch(CANONICAL, matched, 1.0 if matched else 0.0,
                             "equal after canonicalization" if matched
                             else "values differ after canonicalization")
    if policy.mode == PURPOSE:
        if not isinstance(observed, dict):
            return ContractMatch(PURPOSE, False, 0.0, "a purpose match needs an object")
        expected_fields = expected if isinstance(expected, dict) else {}
        required = policy.required_keys or tuple(expected_fields)
        missing = tuple(key for key in required if key not in observed)
        if missing:
            return ContractMatch(PURPOSE, False, 0.0,
                                 "missing required keys: " + ", ".join(missing), missing)
        wrong = tuple(key for key in required if key in expected_fields
                      and _type_family(expected_fields[key]) != _type_family(observed[key]))
        if wrong:
            return ContractMatch(PURPOSE, False, 0.0,
                                 "incompatible types for: " + ", ".join(wrong), wrong)
        return ContractMatch(PURPOSE, True, 1.0, "required keys present with compatible types")
    if policy.mode == SEMANTIC_BLOCKED:
        if not isinstance(expected, dict) or not isinstance(observed, dict):
            return ContractMatch(SEMANTIC_BLOCKED, False, 0.0,
                                 "a semantic match with blocking keys needs objects")
        blocked = tuple(key for key in policy.blocking_keys
                        if canonical_value(expected.get(key)) != canonical_value(observed.get(key)))
        if blocked:
            return ContractMatch(SEMANTIC_BLOCKED, False, 0.0,
                                 "blocking keys differ: " + ", ".join(blocked), blocked)
        free_expected = {key: value for key, value in expected.items()
                         if key not in policy.blocking_keys}
        free_observed = {key: value for key, value in observed.items()
                         if key not in policy.blocking_keys}
        score = token_similarity(free_expected, free_observed)
        matched = score >= policy.threshold
        return ContractMatch(SEMANTIC_BLOCKED, matched, score,
                             f"similarity {score:.3f} against threshold {policy.threshold}")
    return ContractMatch(MODEL_JUDGED, None, 0.0,
                         "beyond deterministic reach; a judgment call decides",
                         judge_contract_id=policy.judge_contract_id)


def self_test() -> dict:
    """Each mode accepts what it should and refuses what it must."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def refuses(action):
        try:
            action()
        except ContractMatchError:
            return True
        return False

    exact = ContractMatchPolicy(EXACT)
    check("exact_match_is_equality_as_given",
          match_contract(exact, "Reply by Friday", "Reply by Friday").matched
          and not match_contract(exact, "Reply by Friday", "reply by friday").matched
          and match_contract(exact, {"a": 1}, {"a": 1}).matched)
    check("canonical_match_forgives_whitespace_case_and_typographic_quotes",
          match_contract(CANONICAL_TEXT, 'Close at 6 pm on "Friday"',
                         "close  at 6 pm on “Friday” ").matched
          and not match_contract(CANONICAL_TEXT, "Close at 6 pm on Friday",
                                 "Close at 6 pm on Friday. Include the phone number.").matched
          and match_contract(CANONICAL_TEXT, {"b": "X Y", "a": 1}, {"a": 1, "b": "x  y"}).matched)
    purpose = ContractMatchPolicy(PURPOSE, required_keys=("candidate", "confidence"))
    check("purpose_match_allows_extra_keys_and_checks_types",
          match_contract(purpose, {"candidate": "a", "confidence": 0.5},
                         {"candidate": "b", "confidence": 90, "why": "x"}).matched
          and not match_contract(purpose, {"candidate": "a", "confidence": 0.5},
                                 {"candidate": "b"}).matched
          and match_contract(purpose, {"candidate": "a", "confidence": 0.5},
                             {"candidate": "b"}).blocked_on == ("confidence",)
          and not match_contract(purpose, {"candidate": "a", "confidence": 0.5},
                                 {"candidate": "b", "confidence": "high"}).matched
          and not match_contract(purpose, {"candidate": "a"}, ["a"]).matched)
    semantic = ContractMatchPolicy(SEMANTIC_BLOCKED, blocking_keys=("unit", "action"),
                                   threshold=0.5)
    same = {"unit": "USD", "action": "list", "text": "list the inactive accounts by owner"}
    check("semantic_match_keeps_blocking_keys_exact_and_similarity_deterministic",
          match_contract(semantic, same, {"unit": "usd", "action": "List",
                                          "text": "list inactive accounts, by owner"}).matched
          and not match_contract(semantic, same, {**same, "action": "remove"}).matched
          and match_contract(semantic, same, {**same, "action": "remove"}).blocked_on == ("action",)
          and not match_contract(semantic, same, {"unit": "USD", "action": "list",
                                                  "text": "rotate the signing keys"}).matched
          and match_contract(semantic, same, same).score == 1.0)
    judged = ContractMatchPolicy(MODEL_JUDGED, judge_contract_id="independent.criterion_judgment")
    verdict = match_contract(judged, "The reply must apologize", "We are sorry for the delay.")
    check("a_model_judged_match_decides_nothing_and_names_its_judgment_contract",
          verdict.matched is None and verdict.judge_contract_id == "independent.criterion_judgment"
          and verdict.to_dict()["matched"] is None)
    check("invalid_policies_are_refused",
          all(refuses(action) for action in (
              lambda: ContractMatchPolicy("fuzzy"),
              lambda: ContractMatchPolicy(SEMANTIC_BLOCKED, blocking_keys=("unit",)),
              lambda: ContractMatchPolicy(MODEL_JUDGED),
              lambda: ContractMatchPolicy(EXACT, judge_contract_id="x"),
              lambda: ContractMatchPolicy(PURPOSE, blocking_keys=("unit",)),
              lambda: ContractMatchPolicy(CANONICAL, threshold=2),
              lambda: match_contract("exact", 1, 1))))
    check("policies_and_matches_render_as_records",
          semantic.to_dict()["blocking_keys"] == ["unit", "action"]
          and match_contract(exact, 1, 2).to_dict()["reason"] == "values differ")
    passed = sum(item["passed"] for item in tests)
    return {"record_type": "contract_matching_test/v1", "tests": tests, "passed": passed,
            "total": len(tests), "all_passed": passed == len(tests)}
