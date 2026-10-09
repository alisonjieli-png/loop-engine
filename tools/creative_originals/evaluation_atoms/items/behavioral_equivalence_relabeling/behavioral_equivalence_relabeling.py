"""Method-blind relabeling and behavioral equivalence classes for candidate systems.

Two problems in comparing many candidates: a reader (or a model acting as judge) who knows which method produced
which output is biased by the name, and several "different" candidates often behave identically. This tool
- replaces names with seeded neutral labels (candidate_01, candidate_02, ...) and keeps the key separately, so the
  label order reveals nothing about the names;
- groups candidates whose outputs on the same probe inputs are identical, after optional rounding of numbers to a
  fixed number of decimals (rounding keeps the grouping an equivalence relation; a tolerance would not, because
  "within 0.01" is not transitive);
- reports the classes in blind labels with a SHA-256 fingerprint of each class's canonical outputs.

    echo '{"call": "equivalence_classes", "arguments": {"outputs": {"a": [1, 2], "b": [1, 2], "c": [1, 3]}}}' | python3 behavioral_equivalence_relabeling.py
"""
from __future__ import annotations

import hashlib
import json
import math

import atom_cli
import numerics


def _names(names):
    values = numerics.labels(names, "names")
    if len(set(values)) != len(values):
        raise ValueError("names must be unique")
    return sorted(values, key=lambda value: (type(value).__name__, value))


def blind_labels(names, seed):
    """Seeded neutral labels: {"mapping": {name: label}, "key": {label: name}}.

    The sorted names are shuffled with a seeded Fisher-Yates shuffle and the i-th name gets "candidate_" plus i + 1,
    zero-padded to the width of the count."""
    ordered = _names(names)
    shuffled = numerics.shuffled(numerics.seeded_random(seed), ordered)
    width = len(str(len(shuffled)))
    mapping = {str(name): f"candidate_{index + 1:0{width}d}" for index, name in enumerate(shuffled)}
    return {"mapping": mapping, "key": {label: name for name, label in mapping.items()}}


def _normalized(value, decimals, path):
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError(f"{path} is not a finite number")
        if decimals is None:
            return value
        rounded = round(float(value), decimals)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, (list, tuple)):
        return [_normalized(item, decimals, f"{path}[{index}]") for index, item in enumerate(value)]
    if isinstance(value, dict):
        return {str(key): _normalized(item, decimals, f"{path}.{key}") for key, item in value.items()}
    raise ValueError(f"{path} must be JSON data")


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def equivalence_classes(outputs, decimals=None):
    """Group candidates whose outputs on every probe are equal (numbers rounded to ``decimals`` when given).

    outputs: {candidate: [output for each probe]}, the same probe count for every candidate.
    Returns {"classes": [{"members", "fingerprint"}] (largest first, then by first member), "class_count",
    "candidate_count"}."""
    if not isinstance(outputs, dict) or not outputs:
        raise ValueError("outputs is an object of candidate to a list of probe outputs")
    if decimals is not None:
        decimals = numerics.integer(decimals, "decimals", minimum=0, maximum=15)
    lengths = set()
    groups = {}
    for name, values in outputs.items():
        if not isinstance(values, list):
            raise ValueError(f"outputs[{name!r}] must be a list")
        lengths.add(len(values))
        normalized = _normalized(values, decimals, f"outputs[{name!r}]")
        key = _fingerprint(normalized)
        groups.setdefault(key, []).append(str(name))
    if len(lengths) != 1:
        raise ValueError("every candidate needs the same number of probe outputs")
    classes = [{"members": sorted(members), "fingerprint": key} for key, members in groups.items()]
    classes.sort(key=lambda row: (-len(row["members"]), row["members"][0]))
    return {"classes": classes, "class_count": len(classes), "candidate_count": len(outputs)}


def blind_report(outputs, seed, decimals=None):
    """Equivalence classes expressed in blind labels, with the key kept apart.

    Returns {"classes": [{"members" (labels), "fingerprint"}], "class_count", "key"}."""
    result = equivalence_classes(outputs, decimals)
    labels = blind_labels(list(outputs), seed)
    classes = [{"members": sorted(labels["mapping"][name] for name in row["members"]),
                "fingerprint": row["fingerprint"]} for row in result["classes"]]
    classes.sort(key=lambda row: (-len(row["members"]), row["members"][0]))
    return {"classes": classes, "class_count": result["class_count"], "key": labels["key"]}


FUNCTIONS = {"blind_labels": blind_labels, "equivalence_classes": equivalence_classes, "blind_report": blind_report}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["blind_labels", "equivalence_classes", "blind_report", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
