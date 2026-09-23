"""Run the data cleanup demonstration: one fresh Pi harness for each step.

Every trial builds a new step folder outside the repository, starts one Pi
process in it with an empty home folder and its own configuration folder,
and sends every model request through the counting proxy in `meter.py`.
After the process ends, the independent scorer reads `output.csv`. The
harness's own statement that it finished is never used as a result.

Commands (run from the study folder):

    python runner/run_trials.py capture          # no model call: check what each arm sends
    python runner/run_trials.py pilot            # the declared pilot, excluded from results
    python runner/run_trials.py main             # the frozen main plan, resumable
    python runner/run_trials.py optional         # the optional arm, only within the budget rule

The run folder holds the step folders and request bodies. It is outside the
repository and is set with --run-folder. Only the Python standard library is
used.
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
REPOSITORY = STUDY.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY / "scorer"))

import meter as meter_module  # noqa: E402
import score_step  # noqa: E402

DESIGN_PATH = STUDY / "design.json"
TRIALS = STUDY / "trials"
CATALOGUE = REPOSITORY / "examples" / "29_intelligence_service" / "starter-catalogue"
PI = Path("/home/username/.local/bin/pi")
STEP_PATH = "/usr/local/bin:/usr/bin:/bin"
CLOSED_PROXY = "http://127.0.0.1:9"
OUTAGE_OUTCOMES = {"rate_limited", "provider_error", "upstream_unreachable", "stream_interrupted"}


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_design():
    return json.loads(DESIGN_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Material


def material_for(design, family):
    """(text, items, markers) for a family, refused unless every item is approved."""
    reviews = json.loads((CATALOGUE / "reviews.json").read_text(encoding="utf-8"))
    rows = {row["identity"]: row for row in reviews["rows"]}
    texts, items, markers = [], [], []
    for identity in design["material"][family]:
        row = rows[identity]
        body = (CATALOGUE / row["body_path"]).read_bytes()
        digest = sha256_bytes(body)
        if row["outcome"] != "approved" or digest != row["body_digest"]:
            raise SystemExit(f"refused: {identity} is not an approved item with digest {digest}")
        text = body.decode("utf-8")
        texts.append(text)
        items.append({"identity": identity, "body_sha256": digest, "bytes": len(body),
                      "approval_ref": row["approval_ref"]})
        markers.append(text.splitlines()[0])
    return "\n".join(texts), items, markers


def prompt_for(design, family, material_mode, material_text):
    prompt = (STUDY / "population" / family / "prompt.txt").read_text(encoding="utf-8")
    if material_mode == "prompt":
        prompt += "\n" + design["prompt_material_heading"] + "\n\n" + material_text
    return prompt


# ---------------------------------------------------------------------------
# Plan


def main_plan(design):
    plan = []
    for repetition in range(1, design["repetitions"] + 1):
        cells = [(family, arm) for family in design["families"] for arm in design["arms"]]
        random.Random(design["order_seed"] + repetition).shuffle(cells)
        for family, arm in cells:
            plan.append(dict(trial_id=f"r{repetition}-{family}-{arm}", repetition=repetition,
                             family=family, arm=arm, phase="main"))
    return plan


def optional_plan(design):
    plan = []
    for repetition in range(1, design["repetitions"] + 1):
        for family in design["families"]:
            for arm in design["optional_arms"]:
                plan.append(dict(trial_id=f"r{repetition}-{family}-{arm}", repetition=repetition,
                                 family=family, arm=arm, phase="optional"))
    return plan


def pilot_plan(design):
    return [dict(trial_id=f"pilot-{item['family']}-{item['arm']}", repetition=0,
                 family=item["family"], arm=item["arm"], phase="pilot")
            for item in design["pilot"]["trials"]]


def arm_settings(design, arm):
    settings = dict(design["arms"].get(arm) or design["optional_arms"][arm])
    settings["model_id"] = design["models"][settings["model"]]["id"]
    return settings


# ---------------------------------------------------------------------------
# Step folders and the harness process


def check_clean_parents(folder):
    for parent in [folder, *folder.parents]:
        for name in ("AGENTS.md", "CLAUDE.md", "AGENT.md"):
            if (parent / name).exists():
                raise SystemExit(f"refused: {parent / name} would load into every step")


def build_step(run_folder, spec, attempt, design, port, material):
    material_text, items, markers = material
    settings = arm_settings(design, spec["arm"])
    root = run_folder / "steps" / f"{spec['trial_id']}-a{attempt}"
    if root.exists():
        raise SystemExit(f"refused: {root} already exists")
    home, agent, work, tmp = (root / name for name in ("home", "agent", "work", "tmp"))
    for folder in (home, agent, work, tmp):
        folder.mkdir(parents=True)
    shutil.copyfile(STUDY / "population" / spec["family"] / "input.csv", work / "input.csv")
    if settings["material"] == "agents_file":
        (work / "AGENTS.md").write_text(material_text, encoding="utf-8")
    env = base_env(home, agent, tmp)
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], env=env, check=True)
    model = design["models"][settings["model"]]
    models = {"providers": {"meter": {
        "baseUrl": f"http://127.0.0.1:{port}/trial/{spec['trial_id']}/v1",
        "api": "openai-completions",
        "apiKey": "not-a-real-key",
        "compat": {"supportsDeveloperRole": False, "supportsReasoningEffort": False},
        "models": [{"id": model["id"], "name": model["id"], "reasoning": False,
                    "input": ["text"], "contextWindow": model["context_window_declared"],
                    "maxTokens": design["harness"]["max_tokens"],
                    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}}]}}}
    (agent / "models.json").write_text(json.dumps(models, indent=1), encoding="utf-8")
    (agent / "settings.json").write_text(json.dumps(design["harness"]["pi_settings"], indent=1),
                                         encoding="utf-8")
    prompt = prompt_for(design, spec["family"], settings["material"], material_text)
    return root, work, env, prompt, settings, items, markers


def base_env(home, agent, tmp):
    env = {"PATH": STEP_PATH, "HOME": str(home), "PI_CODING_AGENT_DIR": str(agent),
           "PI_OFFLINE": "1", "PI_TELEMETRY": "0", "TERM": "dumb", "LANG": "C.UTF-8",
           "TMPDIR": str(tmp), "NO_PROXY": "127.0.0.1,localhost", "no_proxy": "127.0.0.1,localhost",
           "GIT_CONFIG_NOSYSTEM": "1"}
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        env[name] = CLOSED_PROXY
    return env


def run_harness(work, env, prompt, model_id, timeout, events_path):
    command = [str(PI), "--no-session", "--offline", "--no-skills", "--mode", "json",
               "--provider", "meter", "--model", model_id, "-p", prompt]
    started = time.monotonic()
    timed_out = False
    with open(events_path, "wb") as events, open(events_path.with_suffix(".stderr"), "wb") as errors:
        process = subprocess.Popen(command, cwd=work, env=env, stdout=events, stderr=errors,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGTERM)
            try:
                code = process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                code = process.wait()
    return code, timed_out, round(time.monotonic() - started, 1)


def summarize_events(events_path):
    """A compact account of what the harness reported, for the trial record."""
    summary = {"assistant_messages": 0, "tool_calls": [], "tool_errors": 0, "final_text": "",
               "harness_errors": [], "reported_usage": []}
    if not events_path.is_file():
        return summary
    for line in events_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
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
    for path in sorted(work.rglob("*")):
        if ".git" in path.relative_to(work).parts or not path.is_file():
            continue
        files.append({"path": path.relative_to(work).as_posix(), "bytes": path.stat().st_size})
    return files


def ledger_rows(ledger_path, trial_id):
    if not ledger_path.is_file():
        return []
    rows = []
    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("trial_id") == trial_id:
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
    return {
        "physical": sum(row["event"] == "sent" for row in rows),
        "refused": [row["reason"] for row in rows if row["event"] == "refused"],
        "outcomes": outcomes,
        "usage_known_requests": len(known),
        "usage_unknown_requests": len(completed) - len(known),
        "prompt_tokens_known_sum": sum(item["prompt_tokens"] for item in known),
        "completion_tokens_known_sum": sum(item.get("completion_tokens") or 0 for item in known),
        "largest_prompt_tokens": max((item["prompt_tokens"] for item in known), default=None),
        "model_seconds": round(sum(row.get("elapsed_ms", 0) for row in completed) / 1000, 1),
        "requests_with_every_material_marker": sum(1 for item in markers if item and all(item)),
        "requests_with_any_material_marker": sum(1 for item in markers if any(item)),
    }


# ---------------------------------------------------------------------------
# One trial


class Budget:
    """Reserves the step cap before a trial starts, so lanes cannot overrun the ceiling."""

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


def run_trial(spec, attempt, design, meter, port, run_folder, budget):
    trial_id = spec["trial_id"]
    material = material_for(design, spec["family"])
    root, work, env, prompt, settings, items, markers = build_step(
        run_folder, spec, attempt, design, port, material)
    if not budget.reserve(trial_id):
        shutil.rmtree(root)
        return None
    context = meter_module.StepContext(
        trial_id=trial_id, model=settings["model_id"], arm=spec["arm"], family=spec["family"],
        repetition=spec["repetition"], cap=design["step_request_cap"],
        material_markers=tuple(markers))
    start_sequence = meter.sequence
    meter.open_step(context)
    started_at = now_text()
    try:
        code, timed_out, elapsed = run_harness(
            work, env, prompt, settings["model_id"], design["step_timeout_seconds"],
            root / "events.jsonl")
    finally:
        meter.close_step(trial_id)
        budget.release(trial_id)
    rows = [row for row in ledger_rows(meter.ledger_path, trial_id)
            if row["sequence"] > start_sequence]
    requests = request_summary(rows)
    input_after = (work / "input.csv").read_bytes() if (work / "input.csv").exists() else b""
    input_before = (STUDY / "population" / spec["family"] / "input.csv").read_bytes()
    output = work / "output.csv"
    outage = any(outcome in OUTAGE_OUTCOMES for outcome in requests["outcomes"])
    if outage:
        status = "provider_outage"
    elif "request_error" in requests["outcomes"]:
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
    score = score_step.score(spec["family"], STUDY / "population" / spec["family"] / "truth.json",
                             output)
    record = {
        "record_type": "data_cleanup_trial/v1",
        "trial_id": trial_id,
        "attempt": attempt,
        "phase": spec["phase"],
        "repetition": spec["repetition"],
        "family": spec["family"],
        "arm": spec["arm"],
        "model": settings["model_id"],
        "material_mode": settings["material"],
        "material_items": items if settings["material"] != "none" else [],
        "material_sha256": sha256_bytes(material[0].encode("utf-8"))
        if settings["material"] != "none" else None,
        "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
        "started_at": started_at,
        "ended_at": now_text(),
        "elapsed_seconds": elapsed,
        "harness_exit_code": code,
        "timed_out": timed_out,
        "status": status,
        "counts_in_results": spec["phase"] in ("main", "optional") and status != "provider_outage",
        "requests": requests,
        "harness_report": summarize_events(root / "events.jsonl"),
        "input_unchanged": input_after == input_before,
        "output_present": output.is_file(),
        "output_sha256": sha256_bytes(output.read_bytes()) if output.is_file() else None,
        "files_in_step_folder": step_files(work),
        "score": {key: score[key] for key in ("primary_metric", "primary", "passed", "metrics",
                                              "format_problems", "output_readable")},
    }
    name = f"{trial_id}.a{attempt}"
    (TRIALS / "records").mkdir(parents=True, exist_ok=True)
    (TRIALS / "scores").mkdir(parents=True, exist_ok=True)
    (TRIALS / "outputs").mkdir(parents=True, exist_ok=True)
    (TRIALS / "records" / f"{name}.json").write_text(json.dumps(record, indent=1, ensure_ascii=True)
                                                     + "\n", encoding="utf-8")
    (TRIALS / "scores" / f"{name}.json").write_text(json.dumps(score, indent=1, ensure_ascii=True)
                                                    + "\n", encoding="utf-8")
    if output.is_file():
        shutil.copyfile(output, TRIALS / "outputs" / f"{name}.csv")
    return record


def finished_trials():
    done = {}
    for path in sorted((TRIALS / "records").glob("*.json")) if (TRIALS / "records").is_dir() else []:
        record = json.loads(path.read_text(encoding="utf-8"))
        done.setdefault(record["trial_id"], []).append(record)
    return done


def run_lane(name, plan, design, meter, port, run_folder, budget, log):
    waits = design["outage_policy"]["wait_seconds"]
    for spec in plan:
        attempts = finished_trials().get(spec["trial_id"], [])
        if any(record["status"] != "provider_outage" for record in attempts):
            continue
        attempt = len(attempts) + 1
        waited = 0
        while True:
            record = run_trial(spec, attempt, design, meter, port, run_folder, budget)
            if record is None:
                log(f"[{name}] stopped before {spec['trial_id']}: the remaining budget "
                    f"({meter.remaining()}) cannot reserve a full step cap")
                return
            log(f"[{name}] {spec['trial_id']} a{attempt}: {record['status']}, "
                f"{record['requests']['physical']} requests, primary {record['score']['primary']}, "
                f"passed {record['score']['passed']}, total {meter.physical_total}")
            if record["status"] != "provider_outage":
                break
            pause = waits[min(attempt - 1, len(waits) - 1)]
            if waited + pause > design["outage_policy"]["max_total_wait_seconds"]:
                log(f"[{name}] provider outage persisted; lane stopped at {spec['trial_id']}")
                return
            log(f"[{name}] provider outage; waiting {pause} seconds before attempt {attempt + 1}")
            time.sleep(pause)
            waited += pause
            attempt += 1


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
    meter = meter_module.Meter(run_folder / "capture-ledger.jsonl", run_folder / "capture-bodies",
                               ceiling=50, upstream_port=stub.port, upstream_timeout=30)
    port = meter.start()
    budget = Budget(meter, design["step_request_cap"])
    results = []
    arms = list(design["arms"]) + list(design["optional_arms"])
    for arm in dict.fromkeys(arm_settings(design, a)["material"] for a in arms):
        chosen = next(a for a in arms if arm_settings(design, a)["material"] == arm)
        spec = dict(trial_id=f"capture-duplicates-{chosen}", repetition=0, family="duplicates",
                    arm=chosen, phase="capture")
        material = material_for(design, "duplicates")
        root, work, env, prompt, settings, items, markers = build_step(
            run_folder, spec, 1, design, port, material)
        context = meter_module.StepContext(trial_id=spec["trial_id"], model=settings["model_id"],
                                           arm=chosen, family="duplicates", repetition=0, cap=3,
                                           material_markers=tuple(markers))
        meter.open_step(context)
        code, timed_out, elapsed = run_harness(work, env, prompt, settings["model_id"], 120,
                                               root / "events.jsonl")
        meter.close_step(spec["trial_id"])
        bodies = sorted((run_folder / "capture-bodies" / spec["trial_id"]).glob("*-request.json"))
        first = json.loads(bodies[0].read_text()) if bodies else {}
        system = next((m.get("content") for m in first.get("messages", [])
                       if m.get("role") == "system"), "")
        system = system if isinstance(system, str) else json.dumps(system)
        text = bodies[0].read_text() if bodies else ""
        results.append({
            "arm": chosen, "material_mode": arm, "exit_code": code, "requests_seen": len(bodies),
            "system_prompt_chars": len(system),
            "request_bytes": len(text),
            "tools": [t.get("function", {}).get("name") for t in first.get("tools", [])],
            "markers_in_request": [marker in text for marker in markers],
            "markers_in_system_prompt": [marker in system for marker in markers],
            "agents_file_named_in_system_prompt": "AGENTS.md" in system,
            "leak_markers": [word for word in ("CodeGraph", "codegraph", "humanizer", "Astra")
                             if word in text],
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


def probe(design, meter, model_key, log):
    """One tiny request to confirm that a model answers and reports usage."""
    import urllib.request
    model_id = design["models"][model_key]["id"]
    trial_id = f"probe-{model_key}"
    context = meter_module.StepContext(trial_id=trial_id, model=model_id, arm="probe",
                                       family="none", repetition=0, cap=1)
    meter.open_step(context)
    body = json.dumps({"model": model_id, "stream": False, "messages": [
        {"role": "user", "content": design["pilot"]["probe_prompt"]}]}).encode()
    request = urllib.request.Request(
        f"http://127.0.0.1:{meter.server.server_address[1]}/trial/{trial_id}/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            text = response.read().decode("utf-8", errors="replace")
    except Exception as error:  # the ledger holds the outcome; this is for the console
        text = f"{type(error).__name__}"
    meter.close_step(trial_id)
    log(f"probe {model_id}: {text[:300]}")


# ---------------------------------------------------------------------------


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("phase", choices=("capture", "pilot", "main", "optional"))
    parser.add_argument("--run-folder", required=True)
    parser.add_argument("--lanes", type=int, default=2, choices=(1, 2))
    args = parser.parse_args(argv)
    design = load_design()
    run_folder = Path(args.run_folder).resolve()
    run_folder.mkdir(parents=True, exist_ok=True)
    check_clean_parents(run_folder / "steps")
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
        return 0
    meter = meter_module.Meter(TRIALS / "requests.jsonl", run_folder / "bodies",
                               design["request_ceiling"])
    port = meter.start()
    budget = Budget(meter, design["step_request_cap"])
    log(f"{args.phase}: {meter.physical_total} physical requests already recorded, "
        f"ceiling {design['request_ceiling']}")
    try:
        if args.phase == "pilot":
            for model_key in design["pilot"]["probe_models"]:
                probe(design, meter, model_key, log)
            plan = pilot_plan(design)
        elif args.phase == "main":
            plan = main_plan(design)
        else:
            needed = design["optional_rule"]["minimum_remaining_requests"]
            if meter.remaining() < needed:
                log(f"optional arm not run: {meter.remaining()} requests remain, rule needs {needed}")
                return 0
            plan = optional_plan(design)
        small = design["models"]["small"]["id"]
        local = [spec for spec in plan if arm_settings(design, spec["arm"])["model_id"] == small]
        cloud = [spec for spec in plan if spec not in local]
        lanes = [("local", local), ("cloud", cloud)] if args.lanes == 2 else [("all", plan)]
        threads = [threading.Thread(target=run_lane, args=(name, lane, design, meter, port,
                                                           run_folder, budget, log))
                   for name, lane in lanes if lane]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    finally:
        meter.stop()
    log(f"{args.phase} finished: {meter.physical_total} physical requests recorded in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
