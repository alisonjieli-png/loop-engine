"""The ongoing independent audit of generated components admitted by deterministic qualification.

The owner, October 5, 2026: "independent review should be an ongoing processes, not something that stops
publications". Components are admitted by ``admit-qualified`` (qualified_admission.py) and published; this job
reviews every published generator batch afterwards, with the same written plan, the same calibrated reviewer of a
family that did not write the generators and the same decision ledger as the sampled review before it.

```text
audit (one scheduled run; hybrid: deterministic selection, one calibrated non-producer reviewer's verdicts)
├── read    the configuration, the admission folders it names, the decision ledger, the held-versions file and
│           the calls this audit already spent today
├── pick    for each qualification run (in the configured order), the published batches the ledger has not
│           decided, largest first, while the calibration (6 calls) and their planned calls fit what is left of
│           the daily ceiling; the planned calls come from a pass that calls no model, with the run's own seed
├── review  the sampled review, unchanged (sampled_review.py): calibration in the same run, planted controls,
│           each call in this run's own panel ledger, each decision appended to the decision ledger with the
│           members its reviewer rejected
├── withdraw  each rejected component: a ready request with the exact operator command and the reviewer's
│             reason; the lead runs it on production, this job never does
├── hold    a generator version whose recorded defect rate reaches the tolerance is added to the held-versions
│           file, so nothing more of it is admitted until a repaired version exists
└── status  status.json: the run, its calls, decisions, withdrawals, holds and what is left to audit
```

A producer never approves its own work: the reviewer's family must differ from the producer family, which the
sampled review's panel enforces. Nothing here publishes, withdraws or writes the import store.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import shlex
from types import SimpleNamespace

from . import decisions, sampled_review, sampling

CONFIG_RECORD = "generated_audit_configuration/v1"
CONFIG_FIELDS = ("record_type", "reviewer", "producer_family", "daily_call_ceiling", "admission_folders",
                 "decision_ledger", "held_versions", "store_root", "state", "host_config")
STATUS_RECORD = "generated_audit_status/v1"
WITHDRAWAL_RECORD = "catalogue_withdrawal_request/v1"
CALIBRATION_CALLS = 6
#: The calls a run may spend beyond its plan, for a provider's rate-limit retries.
RETRY_SLACK = 3


class AuditError(ValueError):
    """A stable refusal code and an operator message."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


def _refuse(code: str, message: str):
    raise AuditError(code, message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def read_config(path) -> dict:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if type(value) is not dict or set(value) != set(CONFIG_FIELDS) or value["record_type"] != CONFIG_RECORD:
        _refuse("audit_configuration_invalid", f"{path} is not a {CONFIG_RECORD} with exactly {list(CONFIG_FIELDS)}")
    if type(value["daily_call_ceiling"]) is not int or not CALIBRATION_CALLS < value["daily_call_ceiling"] <= 400:
        _refuse("audit_configuration_invalid", "the daily call ceiling is a whole number above the calibration's six")
    if type(value["admission_folders"]) is not list or not value["admission_folders"]:
        _refuse("audit_configuration_invalid", "the audit names the admission folders it audits")
    return value


def published_batches(folders) -> dict:
    """Qualification run to {batch: admitted components}, from the qualified rows of the admission folders."""
    runs = {}
    for folder in map(Path, folders):
        record = json.loads((folder / "reviews.json").read_text(encoding="utf-8"))
        run = (record.get("admission_basis") or {}).get("qualification_run")
        if not run:
            _refuse("admission_folder_invalid", f"{folder} names no qualification run")
        for row in record["rows"]:
            if row.get("outcome") == "approved" and row.get("approval_state") == "qualified":
                batch = row["decisions"][0]["basis"]["batch"]
                runs.setdefault(run, {}).setdefault(batch, 0)
                runs[run][batch] += 1
    return runs


def calls_today(state: Path, day: str) -> int:
    """The calls this audit's runs of ``day`` recorded in their own panel ledgers, whatever stopped them."""
    total = 0
    for ledger in sorted((state / "runs").glob(f"{day}*/panel-ledger.jsonl")):
        with open(ledger, encoding="utf-8") as stream:
            total += sum(1 for line in stream if '"record_type":"candidate_review_call/v2"' in line
                         or '"record_type":"candidate_review_batch_call/v1"' in line)
    return total


def _options(config: dict, run: str, folder: Path, batches, seed: str, *, authorize: bool, ceiling: int,
             output: Path):
    return SimpleNamespace(qualification=Path(run), store_root=Path(config["store_root"]),
                           ledger=folder / "panel-ledger.jsonl", output=output,
                           decisions=Path(config["decision_ledger"]), reviewer=config["reviewer"],
                           producer_family=config["producer_family"], batch=list(batches), controls_per_call=1,
                           call_ceiling=ceiling, token_ceiling=0, calibrate=True, authorize_model_calls=authorize,
                           measurement_only="", seed=seed)


def open_batches(config: dict, run: str, batches) -> tuple:
    """(open batches, settled batches with their reasons) of one qualification run, from the decision ledger."""
    ledger = decisions.DecisionLedger.open(config["decision_ledger"], for_append=False)
    frames = {batch: [] for batch in batches}
    with open(Path(run) / "qualification.jsonl", "rb") as stream:
        for line in stream:
            record = json.loads(line)
            if record.get("batch") in frames and record.get("outcome") == "qualified":
                frames[record["batch"]].append(record)
    refused = ledger.refusals({batch: records for batch, records in frames.items() if records})
    return sorted(batch for batch in batches if batch not in refused and frames[batch]), refused


def withdrawal_requests(config: dict, review: dict, review_path: Path, folders) -> list:
    """One ready request per rejected sampled component, with the exact operator command and the reason."""
    admitted = {}
    for folder in map(Path, folders):
        for row in json.loads((folder / "reviews.json").read_text(encoding="utf-8"))["rows"]:
            admitted[row["identity"]] = str(folder)
    requests = []
    for batch, entry in sorted(review.get("batches", {}).items()):
        for row in entry.get("verdicts", []):
            if row.get("decision") != "reject":
                continue
            reason = (row.get("reason") or "rejected under the written native criteria").strip()
            note = (f"Withdrawn after the ongoing independent audit of {batch} by {review['reviewer']} "
                    f"({row.get('call_ref', '')}): {reason}")[:900]
            command = ("loop-engine service withdraw-catalogue-item --config " + shlex.quote(config["host_config"])
                       + " --identity " + shlex.quote(row["identity"]) + " --note " + shlex.quote(note))
            requests.append({"record_type": WITHDRAWAL_RECORD, "identity": row["identity"],
                             "package_digest": row.get("body_sha256"), "batch": batch,
                             "criteria": row.get("criteria", []), "reason": reason, "reviewer": review["reviewer"],
                             "call_ref": row.get("call_ref"), "review_record": str(review_path),
                             "admission_folder": admitted.get(row["identity"], ""), "command": command,
                             "requested_at": _now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                             "executed": False, "executed_by": "the lead, on production; never this job"})
    return requests


def hold_generators(config: dict, generators, today: str) -> list:
    """Add each generator whose recorded rate reached the tolerance to the held-versions file; return the new holds."""
    from .qualified_admission import read_held
    ledger = decisions.DecisionLedger.open(config["decision_ledger"], for_append=False)
    rows, policy = ledger.history_rows(), sampling.SamplingPolicy()
    path = Path(config["held_versions"])
    held = read_held(path)
    added = []
    for generator in sorted(set(generators)):
        history = sampling.GeneratorHistory.from_decisions(generator, rows)
        rate = history.observed_rate(policy)
        if rate is None or rate < policy.tolerance_defect_rate or generator in held:
            continue
        added.append({"generator": generator, "held_at": today, "held_by": "the ongoing audit "
                      "(tools/qualify_generated_components.py audit)",
                      "reason": (f"recorded defect rate {history.defective} of {history.sampled} ({rate:.3f}) is at "
                                 f"or above the tolerance {policy.tolerance_defect_rate}; nothing more of this "
                                 "version is admitted until a repaired version exists")})
    if added:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["held"] = list(value["held"]) + added
        temporary = path.with_name(path.name + f".audit-{os.getpid()}")
        temporary.write_text(json.dumps(value, indent=1, sort_keys=True) + "\n")
        os.replace(temporary, path)
        read_held(path)
    return added


def run(config_path, *, review=None, now=None) -> dict:
    """One audit run. ``review`` replaces the sampled review's command for checks."""
    review = review or sampled_review.command
    config = read_config(config_path)
    started = now or _now()
    day = started.strftime("%Y-%m-%d")
    state = Path(config["state"])
    (state / "runs").mkdir(parents=True, exist_ok=True)
    (state / "withdrawals").mkdir(parents=True, exist_ok=True)
    from tools import qualify_generated_components as command_module
    root = command_module.ROOT
    spent = calls_today(state, day)
    budget = config["daily_call_ceiling"] - spent
    status = {"record_type": STATUS_RECORD, "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
              "reviewer": config["reviewer"], "daily_call_ceiling": config["daily_call_ceiling"],
              "calls_spent_today_before": spent, "runs": [], "withdrawal_requests": [], "holds_added": [],
              "settled": {}, "waiting": {}}
    generators = set()
    for run_folder, batches in published_batches(config["admission_folders"]).items():
        open_list, refused = open_batches(config, run_folder, batches)
        status["settled"].update({batch: reasons for batch, reasons in refused.items()})
        if not open_list:
            continue
        if budget <= CALIBRATION_CALLS:
            status["waiting"].update({batch: "the daily call ceiling is spent" for batch in open_list})
            continue
        seed = secrets.token_hex(16)
        name = started.strftime("%Y-%m-%dT%H%M%SZ") + "-" + Path(run_folder).name
        folder = state / "runs" / name
        folder.mkdir(parents=True, exist_ok=True)
        dry = folder / "plan.json"
        review(_options(config, run_folder, folder, open_list, seed, authorize=False, ceiling=0, output=dry), root)
        planned = {batch: entry["calls_planned"] for batch, entry in json.loads(dry.read_text())["batches"].items()}
        unfit = json.loads(dry.read_text()).get("calls_that_do_not_fit") or []
        blocked = {row["batch"] for row in unfit}
        chosen, room = [], budget - CALIBRATION_CALLS
        for batch in sorted(open_list, key=lambda value: (-batches[value], value)):
            if batch in blocked:
                status["waiting"][batch] = "a planned call does not fit the reviewer's window"
            elif planned.get(batch, 0) <= room:
                chosen.append(batch)
                room -= planned[batch]
            else:
                status["waiting"][batch] = f"needs {planned.get(batch)} calls; {room} are left today"
        if not chosen:
            continue
        needed = CALIBRATION_CALLS + sum(planned[batch] for batch in chosen)
        ceiling = min(budget, needed + RETRY_SLACK)
        output = folder / "review.json"
        entry = {"qualification": run_folder, "batches": chosen, "seed": seed, "calls_planned": needed,
                 "review": str(output)}
        try:
            result = review(_options(config, run_folder, folder, chosen, seed, authorize=True, ceiling=ceiling,
                                     output=output), root)
            entry["result"] = result
        except (ValueError, OSError) as error:
            entry["refused"] = str(error)[:500]
        spent_now = calls_today(state, day)
        budget = config["daily_call_ceiling"] - spent_now
        entry["calls_used"] = spent_now - spent
        spent = spent_now
        status["runs"].append(entry)
        if output.is_file():
            record = json.loads(output.read_text(encoding="utf-8"))
            if record.get("admissible"):
                for request in withdrawal_requests(config, record, output, config["admission_folders"]):
                    target = state / "withdrawals" / f"{request['identity']}.json"
                    if not target.exists():
                        target.write_text(json.dumps(request, indent=1, sort_keys=True) + "\n")
                        status["withdrawal_requests"].append(str(target))
            elif record.get("stopped"):
                entry["stopped"] = record["stopped"]
                break  # a reviewer that failed its calibration is not asked again today
        generators |= {sampling.generator_of(batch) for batch in chosen}
    status["holds_added"] = hold_generators(config, generators, day) if generators else []
    status["finished_at"] = _now().strftime("%Y-%m-%dT%H:%M:%SZ")
    status["calls_spent_today_after"] = calls_today(state, day)
    status["pending_withdrawals"] = sorted(str(path) for path in (state / "withdrawals").glob("*.json"))
    temporary = state / f"status.json.{os.getpid()}"
    temporary.write_text(json.dumps(status, indent=1, sort_keys=True, default=str) + "\n")
    os.replace(temporary, state / "status.json")
    return {key: status[key] for key in ("runs", "holds_added", "waiting", "calls_spent_today_after")} | {
        "withdrawal_requests": len(status["withdrawal_requests"])}


def command(options, root: Path) -> dict:
    return run(options.config)
