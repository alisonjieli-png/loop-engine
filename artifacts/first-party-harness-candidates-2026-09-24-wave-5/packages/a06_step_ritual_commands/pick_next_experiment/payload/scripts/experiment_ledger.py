"""Summarize an experiment ledger, append one checked next experiment and record run results, refusing any configuration that already ran. Effects: reads files under --root; propose and record append one line to the ledger; no network, no subprocess, no model call.

Usage from the workspace root:

    python3 -I -B .baltor/pick-next-experiment/scripts/experiment_ledger.py summary --root .
    python3 -I -B .baltor/pick-next-experiment/scripts/experiment_ledger.py propose --root .
    python3 -I -B .baltor/pick-next-experiment/scripts/experiment_ledger.py record  --root . --id E-005 \
        --status done --score 0.401 [--fold-scores 0.40,0.41] [--minutes 38] [--notes TEXT]

The ledger is .baltor/experiments/ledger.jsonl (contracts/experiment-ledger-line.schema.json):
a header line {"record_type": "experiment_ledger/v1", "metric": ..., "direction": "lower"
or "higher", "ignore_keys": [...], "config_keys": [...], "budget_minutes": ...}, one JSON
object per experiment (id, status planned, running, done or failed, config, and a
score when done), and update lines {"record_type": "experiment_update/v1", ...} that
move an experiment from planned to running, done or failed. The ledger is only ever
appended to. A configuration fingerprint is the SHA-256 of the canonical JSON of
config without ignore_keys, with whole floats written as integers.

propose reads .baltor/experiments/proposal.json and appends it with status planned
only when no ledger entry has the same fingerprint, every config key is a setting of
the ledger (the header's config_keys, else the keys earlier runs used), and the
change names every key it changes. A failed configuration may run again only as a
retry: retry_of names the newest run with that configuration, which failed, and
environment_change says what was fixed outside the configuration. Each run prints
one JSON object. Exit status: 0 success, 1 check failed, 2 refused input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LEDGER = Path(".baltor") / "experiments" / "ledger.jsonl"
PROPOSAL = Path(".baltor") / "experiments" / "proposal.json"
NOTES = Path(".baltor") / "experiments" / "notes.md"
MAX_BYTES = 16 * 1024 * 1024
ENTRY_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")
NUMBERED = re.compile(r"E-(\d{1,9})\Z")
TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
STATUSES = ("planned", "running", "done", "failed")
MOVES = {"planned": ("running", "done", "failed"), "running": ("done", "failed"), "done": (), "failed": ()}
HEADER_KEYS = {"record_type", "metric", "direction", "ignore_keys", "config_keys", "budget_minutes"}
UPDATE_KEYS = {"record_type", "id", "status", "at", "score", "fold_scores", "cost_minutes", "notes"}
PROPOSAL_KEYS = {"record_type", "base", "config", "change", "reason", "expected_effect", "cost", "ending_rule",
                 "retry_of", "environment_change"}
WIDE_CHANGE = 3


class Refused(Exception):
    """Input that this script will not process."""


def emit(payload: dict, code: int) -> int:
    print(json.dumps(payload, indent=1, ensure_ascii=False))
    return code


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def strict_json(text: str):
    def pairs(items):
        seen = {}
        for key, value in items:
            if key in seen:
                raise ValueError(f"duplicate key {key!r}")
            seen[key] = value
        return seen

    def constant(name):
        raise ValueError(f"nonstandard constant {name}")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


def inside(root: Path, relative: Path) -> Path:
    if relative.is_absolute() or ".." in relative.parts:
        raise Refused(f"path must be relative and without '..': {relative.as_posix()}")
    full = root / relative
    if not full.resolve().is_relative_to(root):
        raise Refused(f"path leaves the workspace through a link: {relative.as_posix()}")
    return full


def read_text(path: Path, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise Refused(f"no regular file at {label}")
    if path.stat().st_size > MAX_BYTES:
        raise Refused(f"{label} is larger than {MAX_BYTES} bytes; it is refused, not cut")
    try:
        return path.read_bytes().decode("utf-8")
    except UnicodeDecodeError as error:
        raise Refused(f"{label} is not UTF-8") from error


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def normalize(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    return value


def fingerprint(config: dict, ignore: set[str]) -> str:
    kept = {key: value for key, value in config.items() if key not in ignore}
    text = json.dumps(normalize(kept), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fold_list(value) -> bool:
    return isinstance(value, list) and 2 <= len(value) <= 100 and all(is_number(item) for item in value)


def check_header(header: dict) -> None:
    unknown = sorted(set(header) - HEADER_KEYS)
    if unknown:
        raise Refused(f"the ledger header holds unknown keys {unknown}")
    if not isinstance(header.get("metric"), str) or not header["metric"].strip() \
            or header.get("direction") not in ("higher", "lower"):
        raise Refused("the ledger header names a metric and a direction, higher or lower")
    for name in ("ignore_keys", "config_keys"):
        value = header.get(name, [])
        if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
            raise Refused(f"the ledger header {name} is a list of config keys")
    budget = header.get("budget_minutes")
    if budget is not None and (not is_number(budget) or budget <= 0):
        raise Refused("the ledger header budget_minutes is a positive number")


def apply_update(entries: dict, update: dict, number: int) -> None:
    unknown = sorted(set(update) - UPDATE_KEYS)
    if unknown:
        raise Refused(f"ledger line {number} is an update with unknown keys {unknown}")
    entry = entries.get(update.get("id"))
    if entry is None:
        raise Refused(f"ledger line {number} updates {update.get('id')!r}, which no earlier line lists")
    if update.get("status") not in MOVES[entry["status"]]:
        raise Refused(f"ledger line {number} moves {entry['id']} from {entry['status']} to {update.get('status')!r}, "
                      "which is not allowed")
    if not isinstance(update.get("at"), str) or not TIME.fullmatch(update["at"]):
        raise Refused(f"ledger line {number} at is a UTC time such as 2026-09-23T22:10:00Z")
    if update["status"] == "done" and not is_number(update.get("score")):
        raise Refused(f"ledger line {number} marks {entry['id']} done without a numeric score")
    if "fold_scores" in update and not fold_list(update["fold_scores"]):
        raise Refused(f"ledger line {number} fold_scores is a list of 2 to 100 numbers")
    if "cost_minutes" in update and (not is_number(update["cost_minutes"]) or update["cost_minutes"] < 0):
        raise Refused(f"ledger line {number} cost_minutes is a number of zero or more")
    entry.update({key: value for key, value in update.items() if key not in ("record_type", "id", "at")})
    entry.setdefault("updates", []).append({"status": update["status"], "at": update.get("at")})


def load_ledger(root: Path) -> tuple[Path, dict, list[dict]]:
    path = inside(root, LEDGER)
    if not path.exists():
        raise Refused(f"no ledger at {LEDGER.as_posix()}; a person creates it with its header line first")
    records = []
    for number, line in enumerate(read_text(path, LEDGER.as_posix()).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = strict_json(line)
        except ValueError as error:
            raise Refused(f"ledger line {number} is not strict JSON: {error}") from error
        if not isinstance(value, dict):
            raise Refused(f"ledger line {number} is not one JSON object")
        records.append((number, value))
    if not records or records[0][1].get("record_type") != "experiment_ledger/v1":
        raise Refused("the first ledger line must be the header with record_type experiment_ledger/v1")
    header = records[0][1]
    check_header(header)
    entries: dict[str, dict] = {}
    for number, value in records[1:]:
        if value.get("record_type") == "experiment_update/v1":
            apply_update(entries, value, number)
            continue
        if "record_type" in value:
            raise Refused(f"ledger line {number} has record_type {value['record_type']!r}; entries have none")
        if not isinstance(value.get("id"), str) or not ENTRY_ID.fullmatch(value["id"]):
            raise Refused(f"ledger line {number} needs an id of letters, digits, '.', '-' or '_'")
        if value["id"] in entries:
            raise Refused(f"ledger line {number} repeats the id {value['id']}")
        if value.get("status") not in STATUSES:
            raise Refused(f"ledger line {number} status must be one of {', '.join(STATUSES)}")
        if not isinstance(value.get("config"), dict) or not value["config"]:
            raise Refused(f"ledger line {number} needs a nonempty config object")
        if value["status"] == "done" and not is_number(value.get("score")):
            raise Refused(f"ledger line {number} is done but has no numeric score")
        if "fold_scores" in value and not fold_list(value["fold_scores"]):
            raise Refused(f"ledger line {number} fold_scores is a list of 2 to 100 numbers")
        entries[value["id"]] = dict(value)
    return path, header, list(entries.values())


def minutes_of(entry: dict) -> float:
    if is_number(entry.get("cost_minutes")):
        return float(entry["cost_minutes"])
    cost = entry.get("cost")
    if isinstance(cost, dict) and is_number(cost.get("minutes")):
        return float(cost["minutes"])
    return 0.0


def shown(value):
    return value if isinstance(value, (str, int, float, bool)) or value is None else json.dumps(value, sort_keys=True)


def known_keys(header: dict, entries: list[dict]) -> list[str]:
    declared = header.get("config_keys") or []
    seen = [key for entry in entries for key in entry["config"]]
    return list(dict.fromkeys([*declared, *seen])) if declared else list(dict.fromkeys(seen))


def spread(entry: dict) -> float | None:
    folds = entry.get("fold_scores")
    return round(max(folds) - min(folds), 6) if fold_list(folds) else None


def command_summary(root: Path) -> int:
    _path, header, entries = load_ledger(root)
    ignore = set(header.get("ignore_keys", []))
    done = [entry for entry in entries if entry["status"] == "done"]
    ranked = sorted(done, key=lambda entry: entry["score"], reverse=header["direction"] == "higher")
    values: dict[str, list] = {}
    for entry in entries:
        for key, value in entry["config"].items():
            bucket = values.setdefault(key, [])
            if shown(normalize(value)) not in bucket:
                bucket.append(shown(normalize(value)))
    varied = {key: items[:10] for key, items in values.items() if len(items) > 1 or
              any(key not in entry["config"] for entry in entries)}
    constant = {key: items[0] for key, items in values.items() if key not in varied}
    lead = within = None
    if len(ranked) >= 2:
        lead = round(abs(ranked[0]["score"] - ranked[1]["score"]), 6)
        best_spread = spread(ranked[0])
        within = None if best_spread is None else lead < best_spread
    notes = inside(root, NOTES)
    return emit({"record_type": "experiment_ledger_summary/v1", "ledger": LEDGER.as_posix(),
                 "metric": header["metric"], "direction": header["direction"], "ignore_keys": sorted(ignore),
                 "known_keys": known_keys(header, entries), "experiments": len(entries),
                 "by_status": {status: sum(1 for entry in entries if entry["status"] == status) for status in STATUSES},
                 "best": None if not ranked else {"id": ranked[0]["id"], "score": ranked[0]["score"],
                                                  "config": ranked[0]["config"], "fold_spread": spread(ranked[0])},
                 "top": [{"id": entry["id"], "score": entry["score"], "fold_spread": spread(entry)}
                         for entry in ranked[:3]],
                 "lead": lead, "lead_within_fold_spread": within,
                 "open": [{"id": entry["id"], "status": entry["status"], "change": entry.get("change")}
                          for entry in entries if entry["status"] in ("planned", "running")],
                 "failed": [{"id": entry["id"], "notes": entry.get("notes")} for entry in entries
                            if entry["status"] == "failed"],
                 "varied_keys": varied, "constant_keys": constant,
                 "minutes_used": round(sum(minutes_of(entry) for entry in entries), 1),
                 "budget_minutes": header.get("budget_minutes"),
                 "notes_file": NOTES.as_posix() if notes.is_file() else None}, 0)


def names_key(text: str, key: str) -> bool:
    lowered = text.lower()
    return key.lower() in lowered or key.lower().replace("_", " ") in lowered


def check_proposal(proposal: dict, header: dict, entries: list[dict]) -> tuple[list[str], list[str], dict]:
    findings, warnings, facts = [], [], {}
    ignore = set(header.get("ignore_keys", []))
    by_id = {entry["id"]: entry for entry in entries}
    findings += [f"unknown field {key!r}; the fields are in contracts/experiment-proposal.schema.json"
                 for key in sorted(set(proposal) - PROPOSAL_KEYS)]
    config = proposal.get("config")
    if not isinstance(config, dict) or not config:
        findings.append("config must be the full nonempty configuration object of the new experiment")
        config = None
    base = proposal.get("base")
    if base is None:
        if any(entry["status"] == "done" for entry in entries):
            findings.append("base is null, but finished experiments exist; name the experiment this change starts from")
    elif not isinstance(base, str) or base not in by_id:
        findings.append(f"base {base!r} is not an experiment id in the ledger")
    for name, limit in (("change", 500), ("reason", 1000)):
        value = proposal.get(name)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            findings.append(f"{name} must be a nonempty sentence of at most {limit} characters")
    effect = proposal.get("expected_effect")
    if not isinstance(effect, dict):
        findings.append("expected_effect must name metric, direction and size")
    else:
        findings += [f"expected_effect has an unknown field {key!r}" for key in sorted(set(effect) - {"metric", "direction", "size"})]
        if effect.get("metric") != header["metric"]:
            findings.append(f"expected_effect.metric must be the ledger metric {header['metric']}")
        if effect.get("direction") not in ("higher", "lower", "same"):
            findings.append("expected_effect.direction must be higher, lower or same")
        if not is_number(effect.get("size")) or effect["size"] < 0:
            findings.append("expected_effect.size must be a number of zero or more")
    cost = proposal.get("cost")
    if isinstance(cost, dict):
        findings += [f"cost has an unknown field {key!r}" for key in sorted(set(cost) - {"minutes", "model_calls"})]
    minutes = cost.get("minutes") if isinstance(cost, dict) else None
    calls = cost.get("model_calls") if isinstance(cost, dict) else None
    if not is_number(minutes) or not 0 < minutes <= 1440:
        findings.append("cost.minutes must be a number above 0 and at most 1440")
    if not isinstance(calls, int) or isinstance(calls, bool) or calls < 0:
        findings.append("cost.model_calls must be a whole number of zero or more")
    rule = proposal.get("ending_rule")
    if not isinstance(rule, str) or not rule.strip() or len(rule) > 500 or not re.search(r"\d", rule):
        findings.append("ending_rule must say when to stop with at least one number, such as a time limit or a threshold")
    retry_of = proposal.get("retry_of")
    if config is not None:
        known = known_keys(header, entries)
        unknown = [key for key in config if key not in ignore and key not in known]
        if known and unknown:
            findings.append(f"config key(s) {unknown} are not settings of this ledger; use the known_keys of the "
                            "summary. A person adds a new setting to the header's config_keys")
        mark = fingerprint(config, ignore)
        facts["fingerprint"] = mark
        same = [entry for entry in entries if fingerprint(entry["config"], ignore) == mark]
        if same:
            newest = same[-1]
            facts["repeat_of"] = newest["id"]
            environment = proposal.get("environment_change")
            if retry_of is None:
                findings.append(f"this configuration already ran or is listed as {newest['id']} (status "
                                f"{newest['status']}); change the configuration, or set retry_of when a failed run "
                                "failed for a reason outside the configuration")
            elif retry_of != newest["id"] or newest["status"] != "failed":
                findings.append(f"retry_of must name {newest['id']}, the newest run with this configuration, and "
                                f"only a failed run can be retried; it is {newest['status']}")
            elif not isinstance(environment, str) or not environment.strip() or len(environment) > 500:
                findings.append("a retry needs environment_change: one sentence on what was fixed outside the configuration")
            else:
                facts["retry_of"] = newest["id"]
        elif retry_of is not None:
            findings.append("retry_of is only for a configuration that already failed; this one never ran")
        if isinstance(base, str) and base in by_id:
            before = {key: value for key, value in by_id[base]["config"].items() if key not in ignore}
            after = {key: value for key, value in config.items() if key not in ignore}
            changed = sorted(key for key in set(before) | set(after)
                             if normalize(before.get(key)) != normalize(after.get(key)) or (key in before) != (key in after))
            facts["changed_keys"] = changed
            text = proposal.get("change") if isinstance(proposal.get("change"), str) else ""
            unnamed = [key for key in changed if not names_key(text, key)]
            if unnamed:
                findings.append(f"change must name every key it changes; it does not name {unnamed}")
            if len(changed) > WIDE_CHANGE:
                warnings.append(f"{len(changed)} keys changed from {base}; one or two changes keep the effect readable")
    budget = header.get("budget_minutes")
    if budget is not None and is_number(minutes):
        used = sum(minutes_of(entry) for entry in entries)
        if used + minutes > budget:
            findings.append(f"the ledger budget is {budget} minutes; {round(used, 1)} are used or planned and this "
                            f"experiment needs {minutes}")
    return findings, warnings, facts


def next_id(entries: list[dict]) -> str:
    numbers = [int(match.group(1)) for entry in entries for match in [NUMBERED.fullmatch(entry["id"])] if match]
    return f"E-{(max(numbers) + 1 if numbers else 1):03d}"


def append_line(path: Path, record: dict) -> None:
    existing = path.read_bytes()
    with open(path, "a", encoding="utf-8") as stream:
        if existing and not existing.endswith(b"\n"):
            stream.write("\n")
        stream.write(json.dumps(record, ensure_ascii=False, separators=(", ", ": ")) + "\n")


def command_propose(root: Path, options) -> int:
    path, header, entries = load_ledger(root)
    proposal_path = inside(root, Path(options.proposal))
    try:
        proposal = strict_json(read_text(proposal_path, options.proposal))
    except ValueError as error:
        raise Refused(f"{options.proposal} is not strict JSON: {error}") from error
    if not isinstance(proposal, dict):
        raise Refused(f"{options.proposal} is not one JSON object")
    findings, warnings, facts = check_proposal(proposal, header, entries)
    if findings:
        return emit({"record_type": "experiment_proposal_result/v1", "appended": False, "findings": findings,
                     "warnings": warnings, **facts}, 1)
    entry = {"id": next_id(entries), "status": "planned", "config": proposal["config"],
             "fingerprint": facts["fingerprint"], "base": proposal.get("base"), "change": proposal["change"].strip(),
             "reason": proposal["reason"].strip(), "expected_effect": proposal["expected_effect"],
             "cost": proposal["cost"], "ending_rule": proposal["ending_rule"].strip(), "planned_at": now()}
    if "retry_of" in facts:
        entry.update({"retry_of": facts["retry_of"], "environment_change": proposal["environment_change"].strip()})
    append_line(path, entry)
    return emit({"record_type": "experiment_proposal_result/v1", "appended": True, "id": entry["id"],
                 "ledger": LEDGER.as_posix(), "warnings": warnings, **facts}, 0)


def command_record(root: Path, options) -> int:
    path, _header, entries = load_ledger(root)
    by_id = {entry["id"]: entry for entry in entries}
    if not ENTRY_ID.fullmatch(options.id) or options.id not in by_id:
        raise Refused(f"experiment {options.id} is not in the ledger")
    update = {"record_type": "experiment_update/v1", "id": options.id, "status": options.status, "at": now()}
    if options.score is not None:
        if not math.isfinite(options.score):
            raise Refused("--score must be a finite number")
        update["score"] = options.score
    if options.fold_scores is not None:
        try:
            folds = [float(part) for part in options.fold_scores.split(",")]
        except ValueError as error:
            raise Refused("--fold-scores is a comma-separated list of numbers") from error
        if not fold_list(folds):
            raise Refused("--fold-scores holds 2 to 100 finite numbers")
        update["fold_scores"] = folds
    if options.minutes is not None:
        if not math.isfinite(options.minutes) or options.minutes < 0:
            raise Refused("--minutes must be a number of zero or more")
        update["cost_minutes"] = options.minutes
    if options.notes is not None:
        if not options.notes.strip() or len(options.notes) > 1000:
            raise Refused("--notes must be text of 1 to 1000 characters")
        update["notes"] = " ".join(options.notes.split())
    current = by_id[options.id]["status"]
    problem = None
    if options.status not in MOVES[current]:
        problem = f"{options.id} is {current}; it cannot move to {options.status}"
    elif options.status == "done" and "score" not in update:
        problem = "a done run needs --score"
    elif options.status == "failed" and "notes" not in update:
        problem = "a failed run needs --notes that say why it failed"
    if problem:
        return emit({"record_type": "experiment_record_result/v1", "recorded": False, "id": options.id,
                     "reason": problem}, 1)
    append_line(path, update)
    return emit({"record_type": "experiment_record_result/v1", "recorded": True, "id": options.id,
                 "from": current, "to": options.status, "ledger": LEDGER.as_posix()}, 0)


def main(argv: list[str] | None = None) -> int:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--root", default=".", help="workspace root; every path stays under it")
    parser = argparse.ArgumentParser(description="Summarize the experiment ledger and append checked lines.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("summary", parents=[shared], help="print the ledger summary")
    propose = commands.add_parser("propose", parents=[shared], help="check the proposal and append it")
    propose.add_argument("--proposal", default=PROPOSAL.as_posix(), help="proposal path relative to the root")
    record = commands.add_parser("record", parents=[shared], help="append a status update for one experiment")
    record.add_argument("--id", required=True)
    record.add_argument("--status", required=True, choices=("running", "done", "failed"))
    record.add_argument("--score", type=float)
    record.add_argument("--fold-scores")
    record.add_argument("--minutes", type=float)
    record.add_argument("--notes")
    options = parser.parse_args(argv)
    try:
        root = Path(options.root).resolve(strict=True)
        if not root.is_dir():
            raise Refused("--root is not a folder")
        if options.command == "summary":
            return command_summary(root)
        return command_propose(root, options) if options.command == "propose" else command_record(root, options)
    except (Refused, OSError) as error:
        return emit({"record_type": "experiment_ledger_refused/v1", "refused": True, "reason": str(error)}, 2)


if __name__ == "__main__":
    sys.exit(main())
