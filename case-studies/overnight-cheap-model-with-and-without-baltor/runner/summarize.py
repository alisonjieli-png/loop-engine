"""Summarize the step records into results tables, applying the frozen claim rules.

    python runner/summarize.py

Reads `design.json`, `trials/records/*.json`, `trials/scores/*.json`,
`trials/requests.jsonl`, `probe/*.json`, `population/item-reference.json` and,
when present, the copied run logs in `trials/run-logs/`. Writes
`results/summary.json` and `results/tables.md`. It was written and frozen
before the first counted model call. Only the Python standard library is used.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
TRIALS = STUDY / "trials"
RESULTS = STUDY / "results"
SECONDARY = {
    "phones": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
               "change_recall", "missing_rows"),
    "emails": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
               "change_recall", "missing_rows"),
    "names": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
              "change_recall", "missing_rows"),
    "websites": ("wrong_changes_to_correct_values", "correct_hold_rate", "guess_rate_on_hold_rows",
                 "change_recall", "missing_rows"),
    "addresses": ("part_accuracy", "rewritten_parts", "correct_hold_rate", "unneeded_review_rate",
                  "missing_rows"),
    "duplicates": ("pair_precision", "pair_recall", "closure_pair_f1", "false_merges",
                   "hard_negative_merges", "correct_hold_rate"),
}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_records():
    folder = TRIALS / "records"
    return [load_json(path) for path in sorted(folder.glob("*.json"))] if folder.is_dir() else []


def load_ledger():
    path = TRIALS / "requests.jsonl"
    rows = []
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def mean(values):
    values = [value for value in values if value is not None]
    return round(statistics.fmean(values), 4) if values else None


def verdict(first, second):
    """The frozen rule: clear only when every repetition of one arm beats every one of the other."""
    if not first or not second:
        return "not_run"
    if min(first) > max(second):
        return "first_clearly_higher"
    if min(second) > max(first):
        return "second_clearly_higher"
    return "not_separated"


def usage_totals(ledger, trial_ids):
    """Provider-reported tokens for the steps; None when any request lacks usage."""
    prompt = completion = cached = 0
    unknown = 0
    for row in ledger:
        if row.get("event") != "completed" or row.get("trial_id") not in trial_ids:
            continue
        usage = row.get("usage_reported")
        if not isinstance(usage, dict) or usage.get("prompt_tokens") is None:
            unknown += 1
            continue
        prompt += usage.get("prompt_tokens") or 0
        completion += usage.get("completion_tokens") or 0
        cached += (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0
    return {"prompt_tokens": prompt, "completion_tokens": completion,
            "cached_prompt_tokens": cached, "requests_without_usage": unknown}


def record_usage(group):
    """Tokens of the step attempts in a group, from their own ledger rows."""
    return {"prompt_tokens": sum(r["requests"]["prompt_tokens_known_sum"] for r in group),
            "completion_tokens": sum(r["requests"]["completion_tokens_known_sum"] for r in group),
            "cached_prompt_tokens": sum(r["requests"]["cached_prompt_tokens_known_sum"]
                                        for r in group),
            "requests_without_usage": sum(r["requests"]["usage_unknown_requests"] for r in group)}


def parse_time(text):
    return datetime.fromisoformat(text) if text else None


def coverage_breakdown(design, counted):
    """Row accuracy of each arm on rows where the item's own method gives the truth or not."""
    reference = load_json(STUDY / "population" / "item-reference.json")["families"]
    table = {}
    for record in counted:
        family = record["family"]
        labels = reference[family].get("row_labels")
        if not labels:
            continue
        score = load_json(TRIALS / "scores" / f"{record['trial_id']}.a{record['attempt']}.json")
        cell = table.setdefault(f"{family}|{record['arm']}", {})
        for outcome in score["outcomes"]:
            label = labels[outcome["id"]]
            bucket = cell.setdefault(label, {"rows": 0, "correct": 0})
            bucket["rows"] += 1
            bucket["correct"] += outcome["outcome"] == "correct"
    for cell in table.values():
        for bucket in cell.values():
            bucket["accuracy"] = round(bucket["correct"] / bucket["rows"], 4) if bucket["rows"] else None
    return dict(sorted(table.items()))


def claim_decisions(design, comparisons, table):
    rules = design["claim_decision"]
    material, baseline = rules["material_arm"], rules["baseline_arm"]
    key = f"{material} against {baseline}"
    verdicts = comparisons.get(key, {})
    better = sorted(f for f, v in verdicts.items() if v == "first_clearly_higher")
    worse = sorted(f for f, v in verdicts.items() if v == "second_clearly_higher")
    needed = rules["families_needed"]
    if len(better) >= needed and not worse:
        overall = "material_helps_across_families"
    elif len(worse) >= needed and not better:
        overall = "material_hurts_across_families"
    elif better and worse:
        overall = "mixed"
    elif better or worse:
        overall = "clear_in_some_families_only"
    else:
        overall = "no_clear_difference"
    no_material = [row for row in table if row["arm"] == baseline]
    hard_families = sorted(row["family"] for row in no_material
                           if (row["primary_mean"] is not None
                               and row["primary_mean"] < rules["hardness_mean_below"])
                           or row["passed"] < row["steps"])
    hardness = ("hard_enough" if len(hard_families) >= rules["hardness_families_needed"]
                else "not_hard_enough")
    return {"comparison": key, "families_clearly_better_with_material": better,
            "families_clearly_worse_with_material": worse, "families_needed": needed,
            "overall": overall, "families_where_the_no_material_arm_fails_part":
                hard_families, "hardness": hardness}


def overnight_facts(design, records, ledger):
    main = [record for record in records if record["phase"] == "main"]
    starts = [parse_time(record["started_at"]) for record in main if record.get("started_at")]
    ends = [parse_time(record["ended_at"]) for record in main if record.get("ended_at")]
    logs = TRIALS / "run-logs"
    drill = load_json(logs / "drill-fired.json") if (logs / "drill-fired.json").is_file() else None
    supervisor = ((logs / "supervisor.log").read_text(encoding="utf-8").splitlines()
                  if (logs / "supervisor.log").is_file() else [])
    by_status = {}
    for record in main:
        by_status[record["status"]] = by_status.get(record["status"], 0) + 1
    planned = design["repetitions"] * len(design["families"]) * len(design["arms"])
    counted = [record for record in main if record["counts_in_results"]]
    return {
        "main_steps_planned": planned,
        "main_steps_counted": len(counted),
        "main_step_records_by_status": by_status,
        "first_main_step_started_at": min(starts).isoformat() if starts else None,
        "last_main_step_ended_at": max(ends).isoformat() if ends else None,
        "wall_clock_hours": round((max(ends) - min(starts)).total_seconds() / 3600, 3)
        if starts and ends else None,
        "sum_of_step_seconds": round(sum(record.get("elapsed_seconds") or 0 for record in main), 1),
        "interruption_drill": drill,
        "interrupted_attempts": [f"{record['trial_id']}.a{record['attempt']}" for record in main
                                 if record["status"] == "interrupted"],
        "provider_outage_attempts": [f"{record['trial_id']}.a{record['attempt']}" for record in main
                                     if record["status"] == "provider_outage"],
        "supervisor_log": supervisor,
        "counted_steps_passing_the_scorer": sum(record["score"]["passed"] for record in counted),
        "counted_steps_with_an_output_file": sum(record["output_present"] for record in counted),
    }


def request_accounting(design, records, ledger):
    sent = [row for row in ledger if row.get("event") == "sent"]
    refused = [row for row in ledger if row.get("event") == "refused"]

    def phase_of(trial_id):
        if trial_id.startswith("probe-"):
            return "probe"
        if trial_id.startswith("pilot-"):
            return "pilot"
        return "main"

    by_phase = {}
    for row in sent:
        phase = phase_of(row["trial_id"])
        by_phase[phase] = by_phase.get(phase, 0) + 1
    excluded = [r for r in records if not r["counts_in_results"]]
    excluded_requests = sum(r["requests"]["physical"] for r in records
                            if r["phase"] == "main" and not r["counts_in_results"])
    outcomes = {}
    for row in ledger:
        if row.get("event") == "completed":
            outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    totals = usage_totals(ledger, {row["trial_id"] for row in ledger})
    attributed = sorted(sequence for record in records
                        for sequence in record["requests"].get("ledger_sequences", []))
    probes = [load_json(path) for path in sorted((STUDY / "probe").glob("probe-*.json"))]
    probe_sent = sum(p["requests"]["physical"] for p in probes)
    record_sent = sum(r["requests"]["physical"] for r in records)
    return {"ceiling": design["request_ceiling"], "physical_requests": len(sent),
            "physical_requests_by_phase": by_phase,
            "requests_of_excluded_main_attempts": excluded_requests,
            "refused_without_forwarding": len(refused),
            "refusal_reasons": sorted({row["reason"] for row in refused}),
            "completed_outcomes": outcomes, "excluded_records": len(excluded),
            "sent_requests_in_step_records": record_sent, "sent_requests_in_probe_records": probe_sent,
            "every_sent_request_belongs_to_a_record": record_sent + probe_sent == len(sent),
            "duplicate_ledger_sequences_across_records": len(attributed) - len(set(attributed)),
            **totals}


def main():
    design = load_json(STUDY / "design.json")
    records = load_records()
    ledger = load_ledger()
    counted = [record for record in records if record["counts_in_results"]]
    cells = {}
    for record in counted:
        cells.setdefault((record["family"], record["arm"]), []).append(record)
    reference = load_json(STUDY / "population" / "item-reference.json")["families"]
    table = []
    for family in design["families"]:
        for arm in design["arms"]:
            group = sorted(cells.get((family, arm), []), key=lambda r: r["repetition"])
            if not group:
                continue
            primary = [record["score"]["primary"] for record in group]
            usage = record_usage(group)
            known = usage["requests_without_usage"] == 0
            table.append({
                "family": family, "arm": arm, "model": group[0]["model"], "steps": len(group),
                "primary_metric": group[0]["score"]["primary_metric"],
                "primary_by_repetition": primary,
                "primary_mean": mean(primary), "primary_min": min(primary),
                "primary_max": max(primary),
                "passed": sum(record["score"]["passed"] for record in group),
                "statuses": [record["status"] for record in group],
                "requests_per_step": mean([record["requests"]["physical"] for record in group]),
                "prompt_tokens_per_step": round(usage["prompt_tokens"] / len(group), 1) if known else None,
                "completion_tokens_per_step": round(usage["completion_tokens"] / len(group), 1)
                if known else None,
                "cached_prompt_tokens_per_step": round(usage["cached_prompt_tokens"] / len(group), 1)
                if known else None,
                "requests_without_usage": usage["requests_without_usage"],
                "seconds_per_step": mean([record["elapsed_seconds"] for record in group]),
                "material_in_every_request": all(
                    record["requests"]["requests_with_every_material_marker"]
                    == record["requests"]["physical"] for record in group)
                if group[0]["material_mode"] != "none" else None,
                "material_in_no_request": all(
                    record["requests"]["requests_with_any_material_marker"] == 0 for record in group)
                if group[0]["material_mode"] == "none" else None,
                "input_unchanged_in_every_step": all(record["input_unchanged"] for record in group),
                "secondary_means": {name: mean([record["score"]["metrics"].get(name)
                                                for record in group])
                                    for name in SECONDARY[family]},
                "item_method_reference": reference[family]["primary"],
            })
    comparisons = {}
    for first, second in design["comparisons"]:
        key = f"{first} against {second}"
        comparisons[key] = {}
        for family in design["families"]:
            a = [r["score"]["primary"] for r in cells.get((family, first), [])]
            b = [r["score"]["primary"] for r in cells.get((family, second), [])]
            comparisons[key][family] = verdict(a, b)
    pooled = {}
    for arm in design["arms"]:
        values = [record["score"]["primary"] for record in counted if record["arm"] == arm]
        pooled[arm] = {"steps": len(values), "mean_primary": mean(values),
                       "passed": sum(record["score"]["passed"] for record in counted
                                     if record["arm"] == arm)}
    probes = [load_json(path) for path in sorted((STUDY / "probe").glob("probe-*.json"))]
    summary = {
        "record_type": "overnight_study_summary/v1",
        "design_sha256": __import__("hashlib").sha256(
            (STUDY / "design.json").read_bytes()).hexdigest(),
        "probes": [{"trial_id": p["trial_id"], "model": p["model"], "passed": p["passed"],
                    "physical_requests": p["requests"]["physical"]} for p in probes],
        "table": table,
        "comparisons": comparisons,
        "claim_decision": claim_decisions(design, comparisons, table),
        "pooled_description_not_a_claim": pooled,
        "item_method_reference": {family: {"primary": entry["primary"], "passed": entry["passed"]}
                                  for family, entry in reference.items()},
        "coverage_breakdown": coverage_breakdown(design, counted),
        "overnight": overnight_facts(design, records, ledger),
        "requests": request_accounting(design, records, ledger),
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (RESULTS / "tables.md").write_text(render(design, summary), encoding="utf-8")
    print(json.dumps({"claim_decision": summary["claim_decision"],
                      "requests": summary["requests"]["physical_requests"]}, indent=1))
    return 0


def number(value, places=3):
    return "unknown" if value is None else f"{value:.{places}f}"


def render(design, summary):
    lines = ["# Results tables", "",
             "Generated by `runner/summarize.py` from the step records. Do not edit by hand.", "",
             "## Primary metric by family and arm", "",
             "| Family | Arm | By repetition | Mean | Passed | Requests per step "
             "| Prompt tokens per step | Completion tokens per step | Seconds per step "
             "| Item method alone |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for row in summary["table"]:
        lines.append(
            f"| {row['family']} | {row['arm']} | "
            f"{', '.join(number(v) for v in row['primary_by_repetition'])} | "
            f"{number(row['primary_mean'])} | {row['passed']} of {row['steps']} | "
            f"{number(row['requests_per_step'], 1)} | {number(row['prompt_tokens_per_step'], 0)} | "
            f"{number(row['completion_tokens_per_step'], 0)} | {number(row['seconds_per_step'], 0)} | "
            f"{number(row['item_method_reference'])} |")
    lines += ["", "## Comparisons under the frozen rule", "",
              "Clear means every repetition of one arm scored above every repetition of the "
              "other.", "",
              "| Comparison | " + " | ".join(design["families"]) + " |",
              "|---|" + "---|" * len(design["families"])]
    words = {"first_clearly_higher": "first clearly higher",
             "second_clearly_higher": "second clearly higher",
             "not_separated": "not separated", "not_run": "not run"}
    for key, verdicts in summary["comparisons"].items():
        lines.append(f"| {key} | " + " | ".join(words[verdicts[f]] for f in design["families"])
                     + " |")
    decision = summary["claim_decision"]
    lines += ["", "## Claim decision", "",
              f"- Overall: {decision['overall'].replace('_', ' ')}.",
              f"- Families clearly better with material: "
              f"{', '.join(decision['families_clearly_better_with_material']) or 'none'}.",
              f"- Families clearly worse with material: "
              f"{', '.join(decision['families_clearly_worse_with_material']) or 'none'}.",
              f"- Population hardness: {decision['hardness'].replace('_', ' ')}; the arm without "
              f"material failed part of "
              f"{', '.join(decision['families_where_the_no_material_arm_fails_part']) or 'no family'}.",
              "", "## Requests", ""]
    requests = summary["requests"]
    lines += [f"- Physical requests: {requests['physical_requests']} of {requests['ceiling']}.",
              "- By phase: " + ", ".join(f"{k} {v}" for k, v in
                                          sorted(requests["physical_requests_by_phase"].items()))
              + ".",
              f"- Requests of excluded main attempts: {requests['requests_of_excluded_main_attempts']}.",
              f"- Refused without forwarding: {requests['refused_without_forwarding']}.",
              f"- Prompt tokens {requests['prompt_tokens']}, completion tokens "
              f"{requests['completion_tokens']}, cached prompt tokens "
              f"{requests['cached_prompt_tokens']}, requests without usage "
              f"{requests['requests_without_usage']}.", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
