"""Duplicate record finder: score record pairs that share a blocking key and group likely duplicates.

Only pairs that share at least one blocking key are compared, which keeps the work near linear. Each compared pair
gets a weighted average of field similarities: exact, normalized text, token Jaccard, edit-distance ratio, digits
only and date equality. A field missing on either side is left out and the weights are renormalized. Pairs at or
above the duplicate threshold are duplicates, pairs at or above the review threshold are possible duplicates, and
duplicates are grouped into clusters with union-find. A pure function of its JSON input; the command line reads
standard input and writes standard output.
"""
from __future__ import annotations

import itertools
import re
import unicodedata

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_id": "two records share an id",
    "field_absent": "a compared or blocking field appears in no record",
    "weights_invalid": "the field weights sum to zero",
    "thresholds_out_of_order": "the review threshold is above the duplicate threshold",
    "too_many_pairs": "the blocking keys produce more than the pair limit; use stricter blocking",
}
METHODS = ("exact", "normalized", "token_jaccard", "edit_ratio", "digits", "date")
TRANSFORMS = ("normalized", "prefix3", "soundex", "digits", "last4_digits")
INPUT_SCHEMA = {
    "type": "object", "required": ["records", "fields", "blocking"], "additionalProperties": False,
    "properties": {
        "records": {"type": "array", "minItems": 2, "maxItems": 100000, "items": {"type": "object"},
                    "description": "records as objects; each has the id field"},
        "id_field": {"type": "string", "description": "field holding the record id (default id)"},
        "fields": {"type": "array", "minItems": 1, "maxItems": 30, "description":
                   "compared fields with a weight and a method (exact, normalized, token_jaccard, edit_ratio, "
                   "digits, date)",
                   "items": {"type": "object", "required": ["name", "method"], "additionalProperties": False,
                             "properties": {"name": {"type": "string"}, "method": {"enum": list(METHODS)},
                                            "weight": {"type": "number", "minimum": 0, "maximum": 100}}}},
        "blocking": {"type": "array", "minItems": 1, "maxItems": 10, "description":
                     "keys that candidate pairs must share: a field and a transform (normalized, prefix3, soundex, "
                     "digits, last4_digits)",
                     "items": {"type": "object", "required": ["field", "transform"], "additionalProperties": False,
                               "properties": {"field": {"type": "string"},
                                              "transform": {"enum": list(TRANSFORMS)}}}},
        "duplicate_threshold": {"type": "number", "minimum": 0, "maximum": 1,
                                "description": "score at or above which a pair is a duplicate (default 0.85)"},
        "review_threshold": {"type": "number", "minimum": 0, "maximum": 1,
                             "description": "score at or above which a pair is a possible duplicate (default 0.7)"},
        "max_pairs": {"type": "integer", "minimum": 1, "maximum": 2000000,
                      "description": "refuse when blocking yields more candidate pairs (default 200000)"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["summary", "pairs", "clusters"],
    "properties": {
        "summary": {"type": "object", "description": "records, candidate pairs, duplicates, possible, clusters"},
        "pairs": {"type": "array", "description": "pairs at or above the review threshold, best first",
                  "items": {"type": "object", "required": ["a", "b", "score", "decision", "field_scores"],
                            "properties": {"decision": {"enum": ["duplicate", "possible"]}}}},
        "clusters": {"type": "array", "description": "groups of duplicates with the first id as representative",
                     "items": {"type": "object", "required": ["representative", "members"]}},
    },
}


def normalized(value) -> str:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text)).strip()


def soundex(value) -> str:
    """American Soundex of the first word: a letter and three digits."""
    word = re.sub(r"[^a-z]", "", normalized(value).split(" ")[0] if normalized(value) else "")
    if not word:
        return ""
    codes = {**dict.fromkeys("bfpv", "1"), **dict.fromkeys("cgjkqsxz", "2"), **dict.fromkeys("dt", "3"),
             "l": "4", **dict.fromkeys("mn", "5"), "r": "6"}
    result, previous = word[0].upper(), codes.get(word[0], "")
    for letter in word[1:]:
        code = codes.get(letter, "")
        if code and code != previous:
            result += code
        if letter not in "hw":
            previous = code
    return (result + "000")[:4]


def edit_ratio(left: str, right: str) -> float:
    left, right = left[:200], right[:200]
    if not left and not right:
        return 1.0
    previous = list(range(len(right) + 1))
    for row, character in enumerate(left, 1):
        current = [row]
        for column, other in enumerate(right, 1):
            current.append(min(previous[column] + 1, current[column - 1] + 1,
                               previous[column - 1] + (character != other)))
        previous = current
    return 1.0 - previous[-1] / max(len(left), len(right))


def similarity(left, right, method: str) -> float:
    if method == "exact":
        return 1.0 if str(left) == str(right) else 0.0
    if method == "digits":
        a, b = re.sub(r"\D", "", str(left)), re.sub(r"\D", "", str(right))
        return 1.0 if a and a == b else 0.0
    if method == "date":
        return 1.0 if str(left).strip()[:10] == str(right).strip()[:10] else 0.0
    a, b = normalized(left), normalized(right)
    if method == "normalized":
        return 1.0 if a == b else 0.0
    if method == "token_jaccard":
        first, second = set(a.split()), set(b.split())
        return len(first & second) / len(first | second) if first | second else 1.0
    return edit_ratio(a, b)


def block_key(value, transform: str) -> str:
    if value is None or str(value).strip() == "":
        return ""
    if transform == "normalized":
        return normalized(value)
    if transform == "prefix3":
        return normalized(value).replace(" ", "")[:3]
    if transform == "soundex":
        return soundex(value)
    digits = re.sub(r"\D", "", str(value))
    return digits[-4:] if transform == "last4_digits" else digits


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    records, id_field = payload["records"], payload.get("id_field", "id")
    ids = [str(record.get(id_field, "")) for record in records]
    if "" in ids or len(set(ids)) != len(ids):
        raise KitRefusal("duplicate_id", f"every record needs a distinct {id_field}")
    names = [row["name"] for row in payload["fields"]] + [row["field"] for row in payload["blocking"]]
    for name in names:
        if not any(name in record for record in records):
            raise KitRefusal("field_absent", name)
    weights = [row.get("weight", 1.0) for row in payload["fields"]]
    if sum(weights) <= 0:
        raise KitRefusal("weights_invalid", "at least one weight must be above zero")
    high, low = payload.get("duplicate_threshold", 0.85), payload.get("review_threshold", 0.7)
    if low > high:
        raise KitRefusal("thresholds_out_of_order", f"review {low} above duplicate {high}")
    blocks = {}
    for index, record in enumerate(records):
        for position, rule in enumerate(payload["blocking"]):
            key = block_key(record.get(rule["field"]), rule["transform"])
            if key:
                blocks.setdefault((position, key), []).append(index)
    candidates = set()
    limit = payload.get("max_pairs", 200000)
    for members in blocks.values():
        if len(members) * (len(members) - 1) // 2 + len(candidates) > limit:
            raise KitRefusal("too_many_pairs", f"more than {limit} candidate pairs")
        candidates.update(itertools.combinations(members, 2))
    pairs = []
    for left, right in sorted(candidates):
        scores, total, weight_sum = {}, 0.0, 0.0
        for rule, weight in zip(payload["fields"], weights):
            a, b = records[left].get(rule["name"]), records[right].get(rule["name"])
            if a is None or b is None or str(a).strip() == "" or str(b).strip() == "":
                continue
            value = similarity(a, b, rule["method"])
            scores[rule["name"]] = round(value, 4)
            total += weight * value
            weight_sum += weight
        score = round(total / weight_sum, 4) if weight_sum else 0.0
        if score >= low:
            pairs.append({"a": ids[left], "b": ids[right], "score": score,
                          "decision": "duplicate" if score >= high else "possible", "field_scores": scores})
    position = {identity: index for index, identity in enumerate(ids)}
    pairs.sort(key=lambda row: (-row["score"], position[row["a"]], position[row["b"]]))
    parent = {identity: identity for identity in ids}

    def root(identity):
        while parent[identity] != identity:
            parent[identity] = parent[parent[identity]]
            identity = parent[identity]
        return identity

    for row in pairs:
        if row["decision"] == "duplicate":
            first, second = root(row["a"]), root(row["b"])
            if first != second:
                keep, drop = sorted((first, second), key=position.get)
                parent[drop] = keep
    groups = {}
    for identity in ids:
        groups.setdefault(root(identity), []).append(identity)
    clusters = [{"representative": members[0], "members": members} for members in groups.values() if len(members) > 1]
    clusters.sort(key=lambda row: position[row["representative"]])
    summary = {"records": len(records), "candidate_pairs": len(candidates),
               "duplicates": sum(row["decision"] == "duplicate" for row in pairs),
               "possible": sum(row["decision"] == "possible" for row in pairs), "clusters": len(clusters),
               "records_in_clusters": sum(len(row["members"]) for row in clusters)}
    return {"summary": summary, "pairs": pairs, "clusters": clusters}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
