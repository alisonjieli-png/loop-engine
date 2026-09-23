"""Summarize the trial records into results tables, applying the frozen claim rules.

    python runner/summarize.py

Reads `trials/records/*.json` and `trials/requests.jsonl`. Writes
`results/summary.json` and `results/tables.md`. Only the Python standard
library is used.
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
TRIALS = STUDY / "trials"
RESULTS = STUDY / "results"
COMPARISONS = (
    ("small-agents", "small-none"),
    ("flash-agents", "flash-none"),
    ("small-agents", "large-none"),
    ("flash-agents", "large-none"),
    ("small-none", "large-none"),
    ("flash-none", "large-none"),
    ("small-prompt", "small-none"),
    ("small-prompt", "small-agents"),
)
SECONDARY = {
    "phones": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
               "change_recall", "missing_rows"),
    "emails": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
               "change_recall", "missing_rows"),
    "addresses": ("part_accuracy", "rewritten_parts", "correct_hold_rate", "unneeded_review_rate",
                  "missing_rows"),
    "duplicates": ("pair_precision", "pair_recall", "closure_pair_f1", "false_merges",
                   "hard_negative_merges", "correct_hold_rate"),
}


def load_records():
    records = []
    for path in sorted((TRIALS / "records").glob("*.json")):
        records.append(json.loads(path.read_text(encoding="utf-8")))
    return records


def mean(values):
    values = [value for value in values if value is not None]
    return round(statistics.fmean(values), 4) if values else None


def spread(values):
    values = [value for value in values if value is not None]
    return round(statistics.stdev(values), 4) if len(values) > 1 else None


def verdict(first, second):
    """The frozen rule: clear only when every repetition of one arm beats every one of the other."""
    if not first or not second:
        return "not_run"
    if min(first) > max(second):
        return "first_clearly_higher"
    if min(second) > max(first):
        return "second_clearly_higher"
    return "not_separated"


def main():
    records = load_records()
    counted = [record for record in records if record["counts_in_results"]]
    cells = {}
    for record in counted:
        cells.setdefault((record["family"], record["arm"]), []).append(record)
    families = sorted({record["family"] for record in counted},
                      key=["phones", "emails", "addresses", "duplicates"].index)
    arms = [arm for arm in ("small-none", "small-agents", "small-prompt", "flash-none",
                            "flash-agents", "large-none")
            if any(record["arm"] == arm for record in counted)]
    table = []
    for family in families:
        for arm in arms:
            group = sorted(cells.get((family, arm), []), key=lambda r: r["repetition"])
            if not group:
                continue
            primary = [record["score"]["primary"] for record in group]
            row = {
                "family": family, "arm": arm, "model": group[0]["model"], "steps": len(group),
                "primary_metric": group[0]["score"]["primary_metric"],
                "primary_by_repetition": primary,
                "primary_mean": mean(primary), "primary_sd": spread(primary),
                "primary_min": min(primary), "primary_max": max(primary),
                "passed": sum(record["score"]["passed"] for record in group),
                "statuses": [record["status"] for record in group],
                "requests_mean": mean([record["requests"]["physical"] for record in group]),
                "prompt_tokens_mean": mean([record["requests"]["prompt_tokens_known_sum"]
                                            for record in group
                                            if record["requests"]["usage_unknown_requests"] == 0]),
                "completion_tokens_mean": mean([record["requests"]["completion_tokens_known_sum"]
                                                for record in group
                                                if record["requests"]["usage_unknown_requests"] == 0]),
                "usage_unknown_requests": sum(record["requests"]["usage_unknown_requests"]
                                              for record in group),
                "elapsed_seconds_mean": mean([record["elapsed_seconds"] for record in group]),
                "material_in_every_request": all(
                    record["requests"]["requests_with_every_material_marker"]
                    == record["requests"]["physical"] for record in group)
                if group[0]["material_mode"] != "none" else None,
                "material_in_no_request": all(
                    record["requests"]["requests_with_any_material_marker"] == 0 for record in group)
                if group[0]["material_mode"] == "none" else None,
                "secondary_means": {name: mean([record["score"]["metrics"].get(name)
                                                for record in group])
                                    for name in SECONDARY[family]},
            }
            table.append(row)
    comparisons = []
    for family in families:
        for first, second in COMPARISONS:
            a = [record["score"]["primary"] for record in cells.get((family, first), [])]
            b = [record["score"]["primary"] for record in cells.get((family, second), [])]
            if not a or not b:
                continue
            comparisons.append({"family": family, "first": first, "second": second,
                                "first_mean": mean(a), "second_mean": mean(b),
                                "difference_of_means": round(mean(a) - mean(b), 4),
                                "verdict": verdict(a, b)})
    ledger = [json.loads(line) for line in (TRIALS / "requests.jsonl").read_text(
        encoding="utf-8").splitlines() if line.strip()]
    sent = [row for row in ledger if row["event"] == "sent"]
    completed = [row for row in ledger if row["event"] == "completed"]
    by_model = {}
    for row in completed:
        entry = by_model.setdefault(row["model"], {"requests": 0, "usage_known": 0,
                                                   "prompt_tokens": 0, "completion_tokens": 0,
                                                   "outcomes": {}})
        entry["requests"] += 1
        entry["outcomes"][row["outcome"]] = entry["outcomes"].get(row["outcome"], 0) + 1
        usage = row.get("usage")
        if isinstance(usage, dict) and usage.get("prompt_tokens") is not None:
            entry["usage_known"] += 1
            entry["prompt_tokens"] += usage["prompt_tokens"]
            entry["completion_tokens"] += usage.get("completion_tokens") or 0
    phases = {}
    for record in records:
        key = f"{record['phase']}:{record['status']}"
        phases[key] = phases.get(key, 0) + 1
    summary = {
        "record_type": "data_cleanup_results/v1",
        "physical_requests": len(sent),
        "refused_requests": [row["reason"] for row in ledger if row["event"] == "refused"],
        "requests_by_phase": {
            phase: sum(1 for row in sent if (row["trial_id"].split("-")[0] == phase
                                             or (phase == "main" and row["trial_id"][:2] in ("r1", "r2", "r3"))))
            for phase in ("probe", "pilot", "main")},
        "by_model": by_model,
        "trial_statuses": phases,
        "table": table,
        "comparisons": comparisons,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    lines = ["| Family | Arm | Steps | Primary by repetition | Mean | Range | Passed | Requests per step | Seconds per step |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in table:
        lines.append(
            f"| {row['family']} | {row['arm']} | {row['steps']} | "
            f"{', '.join(f'{value:.3f}' for value in row['primary_by_repetition'])} | "
            f"{row['primary_mean']:.3f} | {row['primary_min']:.3f} to {row['primary_max']:.3f} | "
            f"{row['passed']} of {row['steps']} | {row['requests_mean']:.1f} | "
            f"{row['elapsed_seconds_mean']:.0f} |")
    lines += ["", "| Family | Comparison | Means | Verdict |", "|---|---|---|---|"]
    for item in comparisons:
        lines.append(f"| {item['family']} | {item['first']} against {item['second']} | "
                     f"{item['first_mean']:.3f} against {item['second_mean']:.3f} | "
                     f"{item['verdict'].replace('_', ' ')} |")
    (RESULTS / "tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("physical_requests", "refused_requests",
                                                    "requests_by_phase", "trial_statuses")},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
