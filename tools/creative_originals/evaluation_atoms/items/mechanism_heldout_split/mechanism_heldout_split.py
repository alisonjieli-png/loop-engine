"""Mechanism-held-out splits: test generalization to generating mechanisms never seen in training.

A synthetic task suite is usually produced by a few generators (templates, rule families, simulators). A random
task-level split puts tasks from the same generator on both sides, so the test measures recall of a mechanism, not
transfer to a new one. These splits hold out whole mechanisms:

- split_by_mechanism: the distinct mechanisms, sorted, are shuffled with a seeded Fisher-Yates shuffle and the
  first k = max(1, min(M - 1, floor(fraction * M + 0.5))) go to the test side;
- group_k_folds: mechanisms in order of decreasing task count (ties by name) go to the fold with the fewest tasks
  (ties to the lowest fold), so folds are balanced in tasks and no mechanism spans two folds;
- leakage: the mechanisms that appear on both sides of any given split.

    echo '{"call": "leakage", "arguments": {"tasks": [{"id": "t1", "mechanism": "m1"}, {"id": "t2", "mechanism": "m1"}], "train_ids": ["t1"], "test_ids": ["t2"]}}' | python3 mechanism_heldout_split.py
"""
from __future__ import annotations

import atom_cli
import numerics


def _tasks(tasks):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("tasks is a non-empty list of {id, mechanism}")
    mechanism_of, order = {}, []
    for index, task in enumerate(tasks):
        if not isinstance(task, dict) or set(task) != {"id", "mechanism"}:
            raise ValueError(f"tasks[{index}] must be {{id, mechanism}}")
        identity, mechanism = numerics.labels([task["id"], task["mechanism"]], f"tasks[{index}]")
        if identity in mechanism_of:
            raise ValueError(f"task id {identity!r} repeats")
        mechanism_of[identity] = mechanism
        order.append(identity)
    return mechanism_of, order


def _sorted_labels(values):
    return sorted(values, key=lambda value: (type(value).__name__, value))


def split_by_mechanism(tasks, holdout_fraction, seed):
    """Hold out a seeded selection of whole mechanisms.

    Returns {"train_ids", "test_ids" (input order), "train_mechanisms", "test_mechanisms" (sorted),
    "leaked_mechanisms" (always empty), "counts"}."""
    mechanism_of, order = _tasks(tasks)
    fraction = numerics.probability(holdout_fraction, "holdout_fraction", open_low=True, open_high=True)
    mechanisms = _sorted_labels(set(mechanism_of.values()))
    if len(mechanisms) < 2:
        raise ValueError("a mechanism-held-out split needs at least two mechanisms")
    shuffled = numerics.shuffled(numerics.seeded_random(seed), mechanisms)
    count = max(1, min(len(mechanisms) - 1, int(fraction * len(mechanisms) + 0.5)))
    held_out = set(shuffled[:count])
    test = [identity for identity in order if mechanism_of[identity] in held_out]
    train = [identity for identity in order if mechanism_of[identity] not in held_out]
    return {"train_ids": train, "test_ids": test,
            "train_mechanisms": _sorted_labels(set(mechanisms) - held_out), "test_mechanisms": _sorted_labels(held_out),
            "leaked_mechanisms": [], "counts": {"train_tasks": len(train), "test_tasks": len(test),
                                                "train_mechanisms": len(mechanisms) - count,
                                                "test_mechanisms": count}}


def group_k_folds(tasks, folds):
    """Balanced folds of whole mechanisms; returns {"folds": [[task ids]], "fold_mechanisms", "fold_sizes"}."""
    mechanism_of, order = _tasks(tasks)
    mechanisms = _sorted_labels(set(mechanism_of.values()))
    folds = numerics.integer(folds, "folds", minimum=2, maximum=len(mechanisms))
    sizes = {mechanism: sum(1 for identity in order if mechanism_of[identity] == mechanism) for mechanism in mechanisms}
    ranked = sorted(mechanisms, key=lambda mechanism: (-sizes[mechanism], type(mechanism).__name__, mechanism))
    loads, assigned = [0] * folds, [[] for _ in range(folds)]
    for mechanism in ranked:
        target = min(range(folds), key=lambda fold: (loads[fold], fold))
        assigned[target].append(mechanism)
        loads[target] += sizes[mechanism]
    members = [set(group) for group in assigned]
    return {"folds": [[identity for identity in order if mechanism_of[identity] in group] for group in members],
            "fold_mechanisms": [_sorted_labels(group) for group in assigned], "fold_sizes": loads}


def leakage(tasks, train_ids, test_ids):
    """Mechanisms present on both sides of a split, with the shared task counts.

    Returns {"leaked_mechanisms", "leaked_test_tasks" (test ids whose mechanism also trains), "overlapping_ids"}."""
    mechanism_of, _order = _tasks(tasks)
    train = numerics.labels(train_ids, "train_ids", minimum_length=0)
    test = numerics.labels(test_ids, "test_ids", minimum_length=0)
    unknown = [identity for identity in train + test if identity not in mechanism_of]
    if unknown:
        raise ValueError(f"unknown task ids: {unknown[:5]}")
    train_mechanisms = {mechanism_of[identity] for identity in train}
    test_mechanisms = {mechanism_of[identity] for identity in test}
    leaked = train_mechanisms & test_mechanisms
    return {"leaked_mechanisms": _sorted_labels(leaked),
            "leaked_test_tasks": [identity for identity in test if mechanism_of[identity] in leaked],
            "overlapping_ids": _sorted_labels(set(train) & set(test))}


FUNCTIONS = {"split_by_mechanism": split_by_mechanism, "group_k_folds": group_k_folds, "leakage": leakage}


def main(argv=None, stdin=None, stdout=None):
    """Run one JSON request from standard input (see atom_cli)."""
    return atom_cli.run(FUNCTIONS, argv, stdin, stdout)


__all__ = ["split_by_mechanism", "group_k_folds", "leakage", "main"]

if __name__ == "__main__":
    raise SystemExit(main())
