"""Run the overnight study: one fresh Pi harness process for each step, unattended.

Every step builds a new step folder outside the repository, starts one Pi
process in it with an empty home folder and its own configuration folder,
and sends every model request through the counting proxy in `meter.py`,
which forwards it to the provider named in the design. After the process
ends, the independent scorer reads `output.csv`. The harness's own statement
that it finished is never used as a result.

Commands (run from the study folder):

    python runner/run_trials.py capture --run-folder F   # no model call: what each arm sends
    python runner/run_trials.py probe --run-folder F --model ID
                                                         # before the freeze: one short tool probe
    python runner/run_trials.py pilot --run-folder F     # the declared pilot, excluded from results
    python runner/run_trials.py main --run-folder F      # the frozen plan, unattended and resumable
    python runner/run_trials.py status --run-folder F    # progress, no model call

Unattended and resumable. `main` walks the whole plan with no human input.
Before it starts a step it writes a lease that names the step and, once the
harness starts, its process group. When the runner starts, every lease
without a step record belongs to a step that an earlier runner did not
finish: the runner stops what is left of that harness, waits until it has
observed the process group end, writes an `interrupted` record with the
requests that step used, and runs the step again as a new attempt. The
request ledger survives a crash, so a restart cannot reset the request count.
`runner/overnight.sh` restarts the runner after a crash.

The run folder holds the step folders, leases and request bodies. It is
outside the repository and is set with --run-folder. Only the Python standard
library is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import shutil
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY / "scorer"))

import meter as meter_module  # noqa: E402

DESIGN_PATH = STUDY / "design.json"
TRIALS = STUDY / "trials"
PROBE = STUDY / "probe"
MATERIAL = STUDY / "material"
CLOSED_PROXY = "http://127.0.0.1:9"
OUTAGE_OUTCOMES = {"rate_limited", "provider_error", "upstream_unreachable", "stream_interrupted"}
EXCLUDED_STATUSES = {"provider_outage", "interrupted"}
#: Exit codes of `main` and `pilot`. The supervisor restarts the runner only after a crash.
EXIT_COMPLETE, EXIT_BUDGET, EXIT_OUTAGE, EXIT_REFUSED = 0, 3, 4, 5


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_design():
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


def write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


# ---------------------------------------------------------------------------
# Material: the frozen bytes of approved catalogue items


def material_for(design, family):
    """(text, items, markers) for a family, refused unless every item matches its frozen approval."""
    approvals = json.loads((MATERIAL / "approvals.json").read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in approvals["items"]}
    texts, items, markers = [], [], []
    for identity in design["material"][family]:
        row = rows[identity]
        body = (MATERIAL / f"{identity}.md").read_bytes()
        digest = sha256_bytes(body)
        if row["outcome"] != "approved" or digest != row["body_digest"]:
            raise SystemExit(f"refused: {identity} is not an approved item with digest {digest}")
        text = body.decode("utf-8")
        texts.append(text)
        items.append({"identity": identity, "body_sha256": digest, "bytes": len(body),
                      "approval_ref": row["approval_ref"]})
        markers.append(text.splitlines()[0])
    return "\n".join(texts), items, markers


def prompt_for(family):
    return (STUDY / "population" / family / "prompt.txt").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Plans


def main_plan(design):
    plan = []
    for repetition in range(1, design["repetitions"] + 1):
        cells = [(family, arm) for family in design["families"] for arm in design["arms"]]
        random.Random(design["order_seed"] + repetition).shuffle(cells)
        for family, arm in cells:
            plan.append(dict(trial_id=f"r{repetition}-{family}-{arm}", repetition=repetition,
                             family=family, arm=arm, phase="main"))
    return plan


def pilot_plan(design):
    return [dict(trial_id=f"pilot-{item['family']}-{item['arm']}", repetition=0,
                 family=item["family"], arm=item["arm"], phase="pilot")
            for item in design["pilot"]["trials"]]


def arm_settings(design, arm):
    settings = dict(design["arms"][arm])
    settings["model_id"] = design["models"][settings["model"]]["id"]
    return settings


def model_slug(model_id):
    return "".join(character if character.isalnum() or character in "._-" else "-"
                   for character in model_id)


# ---------------------------------------------------------------------------
# Step folders and the harness process


def check_clean_parents(folder):
    for parent in [folder, *folder.parents]:
        for name in ("AGENTS.md", "CLAUDE.md", "AGENT.md"):
            if (parent / name).exists():
                raise SystemExit(f"refused: {parent / name} would load into every step")


def base_env(home, agent, tmp, step_path):
    env = {"PATH": step_path, "HOME": str(home), "PI_CODING_AGENT_DIR": str(agent),
           "PI_OFFLINE": "1", "PI_TELEMETRY": "0", "TERM": "dumb", "LANG": "C.UTF-8",
           "TMPDIR": str(tmp), "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
           "GIT_CONFIG_NOSYSTEM": "1"}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[name] = CLOSED_PROXY
    return env


def build_step(root, design, model_id, port, trial_id, prompt, input_path=None, agents_text=None):
    """Create a fresh step folder with its own home and Pi configuration."""
    if root.exists():
        raise SystemExit(f"refused: {root} already exists")
    home, agent, work, tmp = (root / name for name in ("home", "agent", "work", "tmp"))
    for folder in (home, agent, work, tmp):
        folder.mkdir(parents=True)
    if input_path is not None:
        shutil.copyfile(input_path, work / "input.csv")
    if agents_text is not None:
        (work / "AGENTS.md").write_text(agents_text, encoding="utf-8")
    harness = design["harness"]
    env = base_env(home, agent, tmp, harness["step_path"])
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], env=env, check=True)
    model = model_record(design, model_id)
    models = {"providers": {"meter": {
        "baseUrl": f"http://127.0.0.1:{port}/trial/{trial_id}/v1",
        "api": "openai-completions",
        "apiKey": "not-a-real-key",
        "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
        "models": [{"id": model_id, "name": model_id, "reasoning": False,
                    "input": ["text"], "contextWindow": model["context_window_declared"],
                    "maxTokens": harness["max_tokens"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]}}}
    (agent / "models.json").write_text(json.dumps(models, indent=1), encoding="utf-8")
    (agent / "settings.json").write_text(json.dumps(harness["pi_settings"], indent=1),
                                         encoding="utf-8")
    return work, env, prompt


def model_record(design, model_id):
    """The design's record for a model: a model of the arms, or a probe candidate."""
    for item in design["models"].values():
        if item["id"] == model_id:
            return item
    return design["probe"]["candidates"][model_id]


def process_start_time(pid):
    """The kernel's start time of a process, which tells a reused process number apart."""
    try:
        text = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return None
    return text.rsplit(")", 1)[1].split()[19]


def group_members(pgid):
    """Process numbers of a process group that have not ended.

    A process that has ended but has not been collected by its parent still
    answers a signal check, so the state in /proc decides: `Z` has ended.
    Returns None where /proc is not available.
    """
    proc = Path("/proc")
    if not proc.is_dir():
        return None
    members = []
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / "stat").read_text().rsplit(")", 1)[1].split()
        except (OSError, IndexError):
            continue
        if int(fields[2]) == pgid and fields[0] != "Z":
            members.append(int(entry.name))
    return members


def group_alive(pgid):
    members = group_members(pgid)
    if members is not None:
        return bool(members)
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def stop_group(pgid, grace):
    """Stop a process group and wait until it is observed to have ended."""
    if not group_alive(pgid):
        return "already_ended"
    os.killpg(pgid, signal.SIGTERM)
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not group_alive(pgid):
            return "ended_after_sigterm"
        time.sleep(0.2)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        return "ended_after_sigterm"
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        if not group_alive(pgid):
            return "ended_after_sigkill"
        time.sleep(0.2)
    return "still_running"


def run_harness(work, env, prompt, model_id, design, events_path, on_started=None, watch=None):
    """Run one Pi process in its own session; a step that runs too long is stopped."""
    harness = design["harness"]
    command = [harness["executable"], "--no-session", "--offline", "--no-skills", "--mode", "json",
               "--provider", "meter", "--model", model_id, "-p", prompt]
    started = time.monotonic()
    timed_out = False
    ended = "finished"
    timeout = design["step_timeout_seconds"]
    with open(events_path, "wb") as events, open(events_path.with_suffix(".stderr"), "wb") as errors:
        process = subprocess.Popen(command, cwd=work, env=env, stdout=events, stderr=errors,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        if on_started is not None:
            on_started(process.pid)
        while True:
            try:
                code = process.wait(timeout=1)
                break
            except subprocess.TimeoutExpired:
                pass
            if watch is not None:
                watch()
            if time.monotonic() - started > timeout:
                timed_out = True
                ended = stop_group(process.pid, harness["stop_grace_seconds"])
                code = process.wait()
                break
    if group_alive(process.pid):
        stop_group(process.pid, harness["stop_grace_seconds"])
    return code, timed_out, ended, round(time.monotonic() - started, 1)


def summarize_events(events_path):
    """A compact account of what the harness reported, for the step record."""
    summary = {"assistant_messages": 0, "tool_calls": [], "tool_errors": 0, "final_text": "",
               "harness_errors": [], "reported_usage": []}
    if not events_path.is_file():
        return summary
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        kind = event.get("type")
        if kind == "message_end" and (event.get("message") or {}).get("role") == "assistant":
            message = event["message"]
            summary["assistant_messages"] += 1
            if message.get("usage"):
                summary["reported_usage"].append(message["usage"])
            if message.get("errorMessage"):
                summary["harness_errors"].append(str(message["errorMessage"])[:300])
            text = "".join(part.get("text", "") for part in message.get("content") or []
                           if isinstance(part, dict) and part.get("type") == "text")
            if text.strip():
                summary["final_text"] = text.strip()[:300]
        elif kind == "tool_execution_start":
            args = json.dumps(event.get("args"), ensure_ascii=True)
            summary["tool_calls"].append({"tool": event.get("toolName"), "args": args[:240]})
        elif kind == "tool_execution_end" and event.get("isError"):
            summary["tool_errors"] += 1
    return summary


def step_files(work):
    files = []
    if not work.is_dir():
        return files
    for path in sorted(work.rglob("*")):
        if ".git" in path.relative_to(work).parts or not path.is_file():
            continue
        files.append({"path": path.relative_to(work).as_posix(), "bytes": path.stat().st_size})
    return files


def ledger_rows(ledger_path, trial_id, after_sequence):
    if not ledger_path.is_file():
        return []
    rows = []
    for line in ledger_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("trial_id") == trial_id and int(row.get("sequence", 0)) > after_sequence:
            rows.append(row)
    return rows


def request_summary(rows):
    completed = [row for row in rows if row["event"] == "completed"]
    known = [row["usage"] for row in completed if isinstance(row.get("usage"), dict)
             and row["usage"].get("prompt_tokens") is not None]
    outcomes = {}
    for row in completed:
        outcomes[row["outcome"]] = outcomes.get(row["outcome"], 0) + 1
    markers = [row.get("material_markers_present") or [] for row in completed]
    sent = [row for row in rows if row["event"] == "sent"]
    return {
        "physical": len(sent),
        "sent_without_completion": len({row["sequence"] for row in sent}
                                       - {row["sequence"] for row in completed}),
        "refused": [row["reason"] for row in rows if row["event"] == "refused"],
        "outcomes": outcomes,
        "usage_known_requests": len(known),
        "usage_unknown_requests": len(sent) - len(known),
        "prompt_tokens_known_sum": sum(item["prompt_tokens"] for item in known),
        "completion_tokens_known_sum": sum(item.get("completion_tokens") or 0 for item in known),
        "cached_prompt_tokens_known_sum": sum(
            ((row.get("usage_reported") or {}).get("prompt_tokens_details") or {}).get("cached_tokens")
            or 0 for row in completed if isinstance(row.get("usage"), dict)
            and row["usage"].get("prompt_tokens") is not None),
        "ledger_sequences": sorted({row["sequence"] for row in rows}),
        "largest_prompt_tokens": max((item["prompt_tokens"] for item in known), default=None),
        "model_seconds": round(sum(row.get("elapsed_ms", 0) for row in completed) / 1000, 1),
        "structured_tool_call_responses": sum(1 for row in completed if row.get("tool_calls")),
        "requests_with_every_material_marker": sum(1 for item in markers if item and all(item)),
        "requests_with_any_material_marker": sum(1 for item in markers if any(item)),
    }


# ---------------------------------------------------------------------------
# Budget and leases


class Budget:
    """Reserves the step cap before a step starts, so the ceiling cannot be overrun."""

    def __init__(self, meter, cap):
        self.meter, self.cap = meter, cap
        self.lock = threading.Lock()
        self.reserved = {}

    def reserve(self, trial_id):
        with self.lock:
            outstanding = sum(self.cap - self.meter.steps[t].physical
                              for t in self.reserved if t in self.meter.steps)
            if self.meter.remaining() - outstanding < self.cap:
                return False
            self.reserved[trial_id] = True
            return True

    def release(self, trial_id):
        with self.lock:
            self.reserved.pop(trial_id, None)


def lease_path(run_folder, trial_id, attempt):
    return run_folder / "leases" / f"{trial_id}.a{attempt}.json"


def record_name(trial_id, attempt):
    return f"{trial_id}.a{attempt}"


def finished_trials():
    done = {}
    folder = TRIALS / "records"
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        record = json.loads(path.read_text(encoding="utf-8"))
        done.setdefault(record["trial_id"], []).append(record)
    return done


def next_attempt(trial_id, run_folder):
    """One more than any attempt already recorded, leased or given a step folder."""
    numbers = [record["attempt"] for record in finished_trials().get(trial_id, [])]
    for path in (run_folder / "leases").glob(f"{trial_id}.a*.json"):
        numbers.append(int(path.stem.rsplit(".a", 1)[1]))
    for path in (run_folder / "steps").glob(f"{trial_id}-a*"):
        numbers.append(int(path.name.rsplit("-a", 1)[1]))
    return max(numbers, default=0) + 1


def score_output(family, output):
    import score_step  # the scorer is imported when a step is scored, never before
    return score_step.score(family, STUDY / "population" / family / "truth.json", output)


def save_step_files(name, score, output):
    for folder in ("records", "scores", "outputs"):
        (TRIALS / folder).mkdir(parents=True, exist_ok=True)
    write_json_atomic(TRIALS / "scores" / f"{name}.json", score)
    if output.is_file():
        shutil.copyfile(output, TRIALS / "outputs" / f"{name}.csv")


def recover_interrupted(run_folder, design, ledger_path, log):
    """Close every step that an earlier runner started and did not record."""
    recovered = []
    for path in sorted((run_folder / "leases").glob("*.json")):
        lease = json.loads(path.read_text(encoding="utf-8"))
        name = record_name(lease["trial_id"], lease["attempt"])
        if (TRIALS / "records" / f"{name}.json").is_file():
            path.unlink()
            continue
        stopped = "no_harness_started"
        pid = lease.get("harness_pid")
        if pid is not None:
            if process_start_time(pid) not in (None, lease.get("harness_start_time")):
                stopped = "process_number_reused_by_another_process"
            else:
                stopped = stop_group(pid, design["harness"]["stop_grace_seconds"])
        if stopped == "still_running":
            raise SystemExit(f"refused: the harness of {name} is still running after SIGKILL")
        root = Path(lease["root"])
        work = root / "work"
        rows = ledger_rows(ledger_path, lease["trial_id"], lease["start_sequence"])
        output = work / "output.csv"
        record = dict(base_record(design, lease), status="interrupted", counts_in_results=False,
                      ended_at=now_text(), elapsed_seconds=None, harness_exit_code=None,
                      timed_out=False,
                      interruption={"recovered_at": now_text(), "harness_stopped": stopped,
                                    "runner_pid_of_lease": lease.get("runner_pid")},
                      requests=request_summary(rows),
                      harness_report=summarize_events(root / "events.jsonl"),
                      output_present=output.is_file(),
                      output_sha256=sha256_bytes(output.read_bytes()) if output.is_file() else None,
                      files_in_step_folder=step_files(work))
        if lease["family"] in design["families"]:
            score = score_output(lease["family"], output)
            record["score"] = {key: score[key] for key in ("primary_metric", "primary", "passed",
                                                           "metrics", "format_problems",
                                                           "output_readable")}
            save_step_files(name, score, output)
        write_json_atomic(TRIALS / "records" / f"{name}.json", record)
        path.unlink()
        recovered.append(name)
        log(f"recovered {name}: interrupted, harness {stopped}, "
            f"{record['requests']['physical']} requests counted")
    return recovered


def base_record(design, lease):
    return {
        "record_type": "overnight_step/v1",
        "trial_id": lease["trial_id"],
        "attempt": lease["attempt"],
        "phase": lease["phase"],
        "repetition": lease["repetition"],
        "family": lease["family"],
        "arm": lease["arm"],
        "model": lease["model"],
        "material_mode": lease["material_mode"],
        "material_items": lease["material_items"],
        "material_sha256": lease["material_sha256"],
        "prompt_sha256": lease["prompt_sha256"],
        "started_at": lease["started_at"],
        "step_root": lease["root"],
    }


# ---------------------------------------------------------------------------
# One step


class DrillFired(Exception):
    """Raised inside the drill watch only in tests; the real drill kills the runner."""


def run_trial(spec, attempt, design, meter, port, run_folder, budget, drill=None):
    trial_id = spec["trial_id"]
    settings = arm_settings(design, spec["arm"])
    material = material_for(design, spec["family"])
    material_text, items, markers = material
    agents = material_text if settings["material"] == "agents_file" else None
    prompt = prompt_for(spec["family"])
    if not budget.reserve(trial_id):
        return None
    root = run_folder / "steps" / f"{trial_id}-a{attempt}"
    lease = {
        "trial_id": trial_id, "attempt": attempt, "phase": spec["phase"],
        "repetition": spec["repetition"], "family": spec["family"], "arm": spec["arm"],
        "model": settings["model_id"], "material_mode": settings["material"],
        "material_items": items if agents is not None else [],
        "material_sha256": sha256_bytes(material_text.encode("utf-8")) if agents is not None else None,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "root": str(root), "start_sequence": meter.sequence, "started_at": now_text(),
        "runner_pid": os.getpid(), "harness_pid": None, "harness_start_time": None,
    }
    this_lease = lease_path(run_folder, trial_id, attempt)
    write_json_atomic(this_lease, lease)
    context = meter_module.StepContext(
        trial_id=trial_id, model=settings["model_id"], arm=spec["arm"], family=spec["family"],
        repetition=spec["repetition"], cap=design["step_request_cap"],
        material_markers=tuple(markers))
    try:
        work, env, prompt = build_step(root, design, settings["model_id"], port, trial_id, prompt,
                                       STUDY / "population" / spec["family"] / "input.csv", agents)

        def on_started(pid):
            lease.update(harness_pid=pid, harness_start_time=process_start_time(pid))
            write_json_atomic(this_lease, lease)

        def watch():
            if drill is not None and len(context.statuses) >= drill["after_completed_requests"]:
                drill["fire"](trial_id)

        meter.open_step(context)
        try:
            code, timed_out, ended, elapsed = run_harness(
                work, env, prompt, settings["model_id"], design, root / "events.jsonl",
                on_started=on_started, watch=watch)
        finally:
            meter.close_step(trial_id)
    finally:
        budget.release(trial_id)
    rows = ledger_rows(meter.ledger_path, trial_id, lease["start_sequence"])
    requests = request_summary(rows)
    input_after = (work / "input.csv").read_bytes() if (work / "input.csv").exists() else b""
    input_before = (STUDY / "population" / spec["family"] / "input.csv").read_bytes()
    output = work / "output.csv"
    outcomes = requests["outcomes"]
    if any(outcome in OUTAGE_OUTCOMES for outcome in outcomes):
        status = "provider_outage"
    elif "provider_key_missing" in outcomes:
        status = "provider_key_missing"
    elif "request_error" in outcomes:
        status = "model_request_refused_by_provider"
    elif timed_out:
        status = "step_timeout"
    elif "step_cap_reached" in requests["refused"]:
        status = "step_request_cap_reached"
    elif "total_ceiling_reached" in requests["refused"]:
        status = "total_ceiling_reached"
    elif code != 0:
        status = "harness_exit_error"
    else:
        status = "completed"
    score = score_output(spec["family"], output)
    record = dict(base_record(design, lease), **{
        "ended_at": now_text(),
        "elapsed_seconds": elapsed,
        "harness_exit_code": code,
        "timed_out": timed_out,
        "harness_ended": ended,
        "status": status,
        "counts_in_results": spec["phase"] == "main" and status not in EXCLUDED_STATUSES
        and status != "provider_key_missing",
        "requests": requests,
        "harness_report": summarize_events(root / "events.jsonl"),
        "input_unchanged": input_after == input_before,
        "output_present": output.is_file(),
        "output_sha256": sha256_bytes(output.read_bytes()) if output.is_file() else None,
        "files_in_step_folder": step_files(work),
        "score": {key: score[key] for key in ("primary_metric", "primary", "passed", "metrics",
                                              "format_problems", "output_readable")},
    })
    name = record_name(trial_id, attempt)
    save_step_files(name, score, output)
    write_json_atomic(TRIALS / "records" / f"{name}.json", record)
    this_lease.unlink()
    return record


def counts(record):
    return record["status"] not in EXCLUDED_STATUSES and record["status"] != "provider_key_missing"


def run_plan(plan, design, meter, port, run_folder, budget, log, drill=None):
    """Walk the plan once. Returns an exit code."""
    waits = design["outage_policy"]["wait_seconds"]
    for spec in plan:
        attempts = finished_trials().get(spec["trial_id"], [])
        if any(counts(record) for record in attempts):
            continue
        waited = 0
        outage_attempts = sum(record["status"] == "provider_outage" for record in attempts)
        while True:
            attempt = next_attempt(spec["trial_id"], run_folder)
            record = run_trial(spec, attempt, design, meter, port, run_folder, budget, drill)
            if record is None:
                log(f"stopped before {spec['trial_id']}: the remaining budget "
                    f"({meter.remaining()}) cannot reserve a full step cap")
                return EXIT_BUDGET
            log(f"{spec['trial_id']} a{attempt}: {record['status']}, "
                f"{record['requests']['physical']} requests, primary {record['score']['primary']}, "
                f"passed {record['score']['passed']}, total {meter.physical_total}")
            if record["status"] == "provider_key_missing":
                log("stopped: the provider key is missing; no step can run")
                return EXIT_REFUSED
            if record["status"] != "provider_outage":
                break
            outage_attempts += 1
            pause = waits[min(outage_attempts - 1, len(waits) - 1)]
            if waited + pause > design["outage_policy"]["max_total_wait_seconds"]:
                log(f"provider outage persisted; stopped at {spec['trial_id']}")
                return EXIT_OUTAGE
            log(f"provider outage; waiting {pause} seconds before the next attempt")
            time.sleep(pause)
            waited += pause
    return EXIT_COMPLETE


def make_drill(design, run_folder, log):
    """The declared interruption drill: once, the runner kills itself during a step."""
    settings = design.get("interruption_drill")
    marker = run_folder / "drill-fired.json"
    if not settings or marker.exists():
        return None

    def fire(trial_id):
        if trial_id != settings["trial_id"]:
            return
        write_json_atomic(marker, {"trial_id": trial_id, "fired_at": now_text(),
                                   "runner_pid": os.getpid(), "signal": "SIGKILL"})
        log(f"interruption drill: killing this runner during {trial_id}")
        os.kill(os.getpid(), signal.SIGKILL)

    return {"after_completed_requests": settings["after_completed_requests"], "fire": fire}


# ---------------------------------------------------------------------------
# Capture check: what each arm sends, with no model behind the endpoint


class CaptureUpstream:
    def __init__(self):
        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"

            def log_message(self, *args):
                return

            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                data = b'{"error":{"message":"capture stub: no model behind this endpoint"}}'
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


def capture(design, run_folder, log):
    stub = CaptureUpstream()
    upstream = meter_module.Upstream(scheme="http", host="127.0.0.1", port=stub.port,
                                     base_path="/v1")
    meter = meter_module.Meter(run_folder / "capture-ledger.jsonl", run_folder / "capture-bodies",
                               ceiling=50, upstream=upstream, upstream_timeout=30)
    port = meter.start()
    results = []
    family = design["capture_family"]
    for arm in design["arms"]:
        settings = arm_settings(design, arm)
        trial_id = f"capture-{family}-{arm}"
        material_text, items, markers = material_for(design, family)
        agents = material_text if settings["material"] == "agents_file" else None
        root = run_folder / "steps" / f"{trial_id}-a1"
        work, env, prompt = build_step(root, design, settings["model_id"], port, trial_id,
                                       prompt_for(family),
                                       STUDY / "population" / family / "input.csv", agents)
        context = meter_module.StepContext(trial_id=trial_id, model=settings["model_id"], arm=arm,
                                           family=family, repetition=0, cap=3,
                                           material_markers=tuple(markers))
        meter.open_step(context)
        code, timed_out, ended, elapsed = run_harness(work, env, prompt, settings["model_id"],
                                                      dict(design, step_timeout_seconds=120),
                                                      root / "events.jsonl")
        meter.close_step(trial_id)
        bodies = sorted((run_folder / "capture-bodies" / trial_id).glob("*-request.json"))
        first = json.loads(bodies[0].read_text()) if bodies else {}
        system = next((m.get("content") for m in first.get("messages", [])
                       if m.get("role") == "system"), "")
        system = system if isinstance(system, str) else json.dumps(system)
        text = bodies[0].read_text() if bodies else ""
        results.append({
            "arm": arm, "material_mode": settings["material"], "exit_code": code,
            "requests_seen": len(bodies), "system_prompt_chars": len(system),
            "request_bytes": len(text),
            "tools": [t.get("function", {}).get("name") for t in first.get("tools", [])],
            "markers_in_request": [marker in text for marker in markers],
            "markers_in_system_prompt": [marker in system for marker in markers],
            "agents_file_named_in_system_prompt": "AGENTS.md" in system,
            "leak_markers": [word for word in design["capture_leak_markers"] if word in text],
            "max_tokens": first.get("max_tokens", first.get("max_completion_tokens")),
            "stream": first.get("stream"),
            "stream_options": first.get("stream_options"),
            "temperature": first.get("temperature"),
        })
    meter.stop()
    stub.server.shutdown()
    out = run_folder / "capture-report.json"
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    log(json.dumps(results, indent=1))
    return results


# ---------------------------------------------------------------------------
# Probe, before the freeze: does a candidate model make structured tool calls in Pi?


def probe(design, meter, port, run_folder, model_id, log):
    settings = design["probe"]
    trial_id = f"probe-{model_slug(model_id)}"
    attempt = next_attempt(trial_id, run_folder)
    trial_id_attempt = f"{trial_id}-a{attempt}"
    root = run_folder / "steps" / trial_id_attempt
    work, env, prompt = build_step(root, design, model_id, port, trial_id_attempt,
                                   settings["prompt"])
    start_sequence = meter.sequence
    context = meter_module.StepContext(trial_id=trial_id_attempt, model=model_id, arm="probe",
                                       family="probe", repetition=0,
                                       cap=settings["step_request_cap"])
    meter.open_step(context)
    try:
        code, timed_out, ended, elapsed = run_harness(
            work, env, prompt, model_id, dict(design, step_timeout_seconds=settings["timeout_seconds"]),
            root / "events.jsonl")
    finally:
        meter.close_step(trial_id_attempt)
    rows = ledger_rows(meter.ledger_path, trial_id_attempt, start_sequence)
    requests = request_summary(rows)
    report = summarize_events(root / "events.jsonl")
    answer = work / settings["answer_file"]
    answer_text = answer.read_text(encoding="utf-8", errors="replace").strip() if answer.is_file() else None
    tools_run = sorted({call["tool"] for call in report["tool_calls"]})
    checks = {
        "structured_tool_calls_in_responses": requests["structured_tool_call_responses"] > 0,
        "harness_ran_required_tools": set(settings["required_tools"]) <= set(tools_run),
        "answer_file_holds_expected_text": answer_text == settings["expected_answer"],
        "harness_exit_code_zero": code == 0,
        "usage_reported_for_every_request": requests["usage_unknown_requests"] == 0,
    }
    record = {
        "record_type": "overnight_model_probe/v1",
        "trial_id": trial_id_attempt,
        "model": model_id,
        "prompt": settings["prompt"],
        "started_request_sequence": start_sequence,
        "elapsed_seconds": elapsed,
        "harness_exit_code": code,
        "timed_out": timed_out,
        "requests": requests,
        "finish_reasons": [row.get("finish_reason") for row in rows if row["event"] == "completed"],
        "tool_calls_by_response": [row.get("tool_calls") for row in rows
                                   if row["event"] == "completed"],
        "harness_report": report,
        "tools_run": tools_run,
        "answer_text": answer_text,
        "checks": checks,
        "passed": all(checks.values()),
        "runner_sha256": sha256_bytes((HERE / "run_trials.py").read_bytes()),
        "meter_sha256": sha256_bytes((HERE / "meter.py").read_bytes()),
        "recorded_at": now_text(),
    }
    PROBE.mkdir(parents=True, exist_ok=True)
    write_json_atomic(PROBE / f"{trial_id_attempt}.json", record)
    log(f"probe {model_id}: passed {record['passed']}, checks {checks}, "
        f"{requests['physical']} requests")
    return record


# ---------------------------------------------------------------------------


def status(design, run_folder):
    records = [record for items in finished_trials().values() for record in items]
    plan = main_plan(design)
    done = {record["trial_id"] for record in records if counts(record) and record["phase"] == "main"}
    ledger = TRIALS / "requests.jsonl"
    sent = 0
    if ledger.is_file():
        for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                sent += json.loads(line).get("event") == "sent"
            except json.JSONDecodeError:
                sent += 1
    by_status = {}
    for record in records:
        by_status[record["status"]] = by_status.get(record["status"], 0) + 1
    leases = sorted(path.name for path in (run_folder / "leases").glob("*.json"))
    print(json.dumps({"main_steps_counted": len(done), "main_steps_planned": len(plan),
                      "records_by_status": by_status, "physical_requests": sent,
                      "request_ceiling": design["request_ceiling"], "open_leases": leases},
                     indent=1))
    return EXIT_COMPLETE


def main(argv=None):
    global DESIGN_PATH, TRIALS, PROBE
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("phase", choices=("capture", "probe", "pilot", "main", "status"))
    parser.add_argument("--run-folder", required=True)
    parser.add_argument("--model", action="append", default=[],
                        help="probe only: a candidate model identity, in the order to try")
    parser.add_argument("--design", default=str(DESIGN_PATH),
                        help="the design record; tests pass a copy that names a scripted provider")
    parser.add_argument("--trials-folder", default=str(TRIALS),
                        help="where records and the request ledger go; tests pass a temporary one")
    args = parser.parse_args(argv)
    DESIGN_PATH, TRIALS = Path(args.design).resolve(), Path(args.trials_folder).resolve()
    if TRIALS != (STUDY / "trials").resolve():
        PROBE = TRIALS / "probe"
    design = load_design()
    run_folder = Path(args.run_folder).resolve()
    if STUDY.resolve() in [run_folder, *run_folder.parents]:
        raise SystemExit("refused: the run folder must be outside the study folder")
    run_folder.mkdir(parents=True, exist_ok=True)
    (run_folder / "steps").mkdir(exist_ok=True)
    (run_folder / "leases").mkdir(exist_ok=True)
    check_clean_parents(run_folder / "steps")
    if args.phase == "status":
        return status(design, run_folder)
    log_path = run_folder / f"{args.phase}.log"
    lock = threading.Lock()

    def log(message):
        line = f"{now_text()} {message}"
        with lock:
            print(line, flush=True)
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    if args.phase == "capture":
        capture(design, run_folder, log)
        return EXIT_COMPLETE
    upstream = meter_module.Upstream.from_design(design["provider"]["endpoint"])
    if upstream.key_variable and not os.environ.get(upstream.key_variable, "").strip():
        log(f"refused: the provider key variable {upstream.key_variable} is empty")
        return EXIT_REFUSED
    meter = meter_module.Meter(TRIALS / "requests.jsonl", run_folder / "bodies",
                               design["request_ceiling"], upstream,
                               design["provider"]["upstream_timeout_seconds"])
    port = meter.start()
    log(f"{args.phase}: runner {os.getpid()}, {meter.physical_total} physical requests already "
        f"recorded, ceiling {design['request_ceiling']}, upstream {upstream.describe()}")
    if meter.unreadable_ledger_lines:
        log(f"{meter.unreadable_ledger_lines} unreadable ledger lines were counted as sent requests")
    code = EXIT_COMPLETE
    try:
        recover_interrupted(run_folder, design, meter.ledger_path, log)
        if args.phase == "probe":
            for model_id in args.model:
                if meter.remaining() < design["probe"]["step_request_cap"]:
                    log("probe stopped: the ceiling cannot hold another probe")
                    return EXIT_BUDGET
                record = probe(design, meter, port, run_folder, model_id, log)
                if record["passed"]:
                    break
            return EXIT_COMPLETE
        budget = Budget(meter, design["step_request_cap"])
        if args.phase == "pilot":
            code = run_plan(pilot_plan(design), design, meter, port, run_folder, budget, log)
        else:
            code = run_plan(main_plan(design), design, meter, port, run_folder, budget, log,
                            make_drill(design, run_folder, log))
    finally:
        meter.stop()
        log(f"{args.phase} ended with code {code}: {meter.physical_total} physical requests "
            f"recorded in total")
    return code


if __name__ == "__main__":
    sys.exit(main())
