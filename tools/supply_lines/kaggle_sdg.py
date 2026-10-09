"""SDG goals and targets proposed for a dataset by a rule that is data (kaggle_sdg_rules.json).

```text
propose(evidence, rules)
├── evidence: words from the dataset's name, file names, column names, the values of columns with few distinct
│   values, and its own documentation; lower-cased, camelCase and separators split, so "meansDebtBondage" and
│   "debt_bondage" both read "debt bondage"
├── a rule applies when one of its phrases appears as whole words in one of its fields (or one of its stems inside
│   a word, for columns written as one word) and none of its unless phrases does; each application records the
│   rule, the field and the phrase
└── the proposal: the union of the applied rules' goals, targets and indicators, each with its matches; no rule
    applied means no goal (never a guess), and the status stays "proposal"
```

Targets are checked against the SDG vocabulary the query planner already keeps
(tools/query_multiplier/data/sdg-vocabulary-v1.json, 169 targets); an indicator must belong to one of its rule's
targets. Nothing here grants a goal: a reviewer attaches PublicGoodGrant goals after independent approval.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

RULES_RECORD = "library_supply_kaggle_sdg_rules/v1"
PROPOSAL_STATUS = "proposal"
VOCABULARY_FILE = Path(__file__).resolve().parents[1] / "query_multiplier" / "data" / "sdg-vocabulary-v1.json"
EVIDENCE_FIELDS = ("name", "files", "columns", "values", "documentation")
#: Characters of a dataset's documentation read for phrases (its README and data card come first).
DOCUMENTATION_CHARACTERS = 12000
#: Word breaks inside camelCase and after an acronym: "meansDebtBondage", "TotalGHGEmissions".
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_SEPARATORS = re.compile(r"[^a-z0-9]+")
_INDICATOR = re.compile(r"(?:[1-9]|1[0-7])\.(?:[0-9]{1,2}|[a-c])\.[0-9]{1,2}")


class RulesError(ValueError):
    """A rule file that cannot be applied as written."""


def normalized(text: str) -> str:
    """Lower-case words with single spaces, camelCase split, every separator a space, padded for whole-word tests."""
    words = _SEPARATORS.sub(" ", _CAMEL.sub(" ", str(text)).lower()).split()
    return " " + " ".join(words) + " "


def vocabulary_targets(path: Path = VOCABULARY_FILE) -> dict:
    """{target id: (goal, phrase)} from the planner's SDG vocabulary."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    return {row["id"]: (int(row["goal"]), row["phrase"]) for row in record["targets"]}


def read_rules(path: Path, vocabulary: "dict | None" = None) -> dict:
    """The rule file, refused when a rule names a goal outside 1 to 17, a target the vocabulary lacks, a target of
    another goal, an indicator of none of its targets, a field outside EVIDENCE_FIELDS, or no phrase or reason."""
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    if record.get("record_type") != RULES_RECORD:
        raise RulesError(f"expected {RULES_RECORD}")
    vocabulary = vocabulary_targets() if vocabulary is None else vocabulary
    seen = set()
    for rule in record["rules"]:
        name = rule.get("id")
        goals = rule.get("goals")
        if not name or name in seen:
            raise RulesError(f"rule {name!r} is unnamed or repeated")
        seen.add(name)
        if (not isinstance(goals, list) or not goals or len(set(goals)) != len(goals)
                or any(type(goal) is not int or not 1 <= goal <= 17 for goal in goals)):
            raise RulesError(f"{name}: goals are distinct integers from 1 to 17")
        for target in rule.get("targets", []):
            if target not in vocabulary or vocabulary[target][0] not in goals:
                raise RulesError(f"{name}: target {target} is not a target of its goals in the SDG vocabulary")
        for indicator in rule.get("indicators", []):
            if not _INDICATOR.fullmatch(indicator) or indicator.rsplit(".", 1)[0] not in rule.get("targets", []):
                raise RulesError(f"{name}: indicator {indicator} belongs to none of its targets")
        if not rule.get("phrases") or not rule.get("reason") or not set(rule.get("fields", [])) <= set(
                EVIDENCE_FIELDS) or not rule.get("fields"):
            raise RulesError(f"{name}: a rule names its phrases, the fields it reads and its reason")
        stems = rule.get("stems", [])
        if any(not isinstance(stem, str) or len(normalized(stem).strip()) < 3 or " " in normalized(stem).strip()
               for stem in stems):
            raise RulesError(f"{name}: a stem is one word of at least three characters")
        rule["_phrases"] = [normalized(phrase) for phrase in rule["phrases"]]
        rule["_stems"] = [normalized(stem).strip() for stem in stems]
        rule["_unless"] = [normalized(phrase) for phrase in rule.get("unless", [])]
    return record


def evidence_text(*, name: str, files=(), columns=(), values=(), documentation: str = "") -> dict:
    """The normalized text of each evidence field of one dataset."""
    return {"name": normalized(name), "files": normalized(" ".join(files)), "columns": normalized(" ".join(columns)),
            "values": normalized(" ".join(str(value) for value in values)),
            "documentation": normalized(documentation[:DOCUMENTATION_CHARACTERS])}


def propose(evidence: dict, rules: dict) -> dict:
    """The proposed goals, targets and indicators of one dataset with every match that put them there."""
    matches, goals, targets, indicators, applied = [], set(), set(), set(), []
    for rule in rules["rules"]:
        found = [(field, phrase.strip()) for field in rule["fields"] for phrase in rule["_phrases"]
                 if phrase in evidence.get(field, "")]
        # A stem matches inside a word, for columns written as one word ("TOTGHGEMISSIONS_METRICTONSCO2E").
        found += [(field, stem) for field in rule["fields"] for stem in rule["_stems"]
                  if stem in evidence.get(field, "") and not any(stem in phrase for _field, phrase in found)]
        if not found:
            continue
        if any(phrase in evidence.get(field, "") for field in rule["fields"] for phrase in rule["_unless"]):
            continue
        applied.append(rule["id"])
        goals.update(rule["goals"])
        targets.update(rule.get("targets", []))
        indicators.update(rule.get("indicators", []))
        matches += [{"rule": rule["id"], "field": field, "phrase": phrase} for field, phrase in found]
    return {"status": PROPOSAL_STATUS, "rules_version": rules["version"], "goals": sorted(goals),
            "targets": sorted(targets, key=_target_order), "indicators": sorted(indicators, key=_target_order),
            "rules": applied, "matches": matches}


def _target_order(identifier: str) -> tuple:
    return tuple(int(part) if part.isdigit() else 100 + ord(part[0]) for part in identifier.split("."))


def reasons(rules: dict, applied) -> list:
    """The written reason of each applied rule, in rule order."""
    by_id = {rule["id"]: rule["reason"] for rule in rules["rules"]}
    return [{"rule": name, "reason": by_id[name]} for name in applied]


def agreement(proposals: dict, review: dict) -> dict:
    """How many reviewed datasets the rules answer exactly as the review did (same goals and targets)."""
    rows, agreed = [], 0
    for slug, verdict in sorted(review.get("datasets", {}).items()):
        proposal = proposals.get(slug)
        same = (proposal is not None and proposal["goals"] == sorted(verdict["goals"])
                and proposal["targets"] == sorted(verdict["targets"], key=_target_order))
        agreed += same
        rows.append({"dataset": slug, "agrees": same,
                     "proposed": None if proposal is None else {"goals": proposal["goals"],
                                                                "targets": proposal["targets"]},
                     "reviewed": {"goals": sorted(verdict["goals"]),
                                  "targets": sorted(verdict["targets"], key=_target_order)}})
    return {"reviewed": len(rows), "agreed": agreed, "rows": rows}


__all__ = ["RULES_RECORD", "PROPOSAL_STATUS", "EVIDENCE_FIELDS", "RulesError", "normalized", "vocabulary_targets",
           "read_rules", "evidence_text", "propose", "reasons", "agreement"]
