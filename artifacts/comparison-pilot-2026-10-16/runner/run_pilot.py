"""Run the frozen October 16 comparison pilot: three tasks, two arms, two repetitions, one model route.

The runner refuses to start unless every frozen file still has the digest in
design/design-freeze.json. It then works through the frozen plan in order and
writes one trial record per attempt under results/trials/. A trial that
already has a record is skipped, so an interrupted run resumes where it
stopped. Every model request passes through the counting proxy (meter.py),
which counts it before it is sent and refuses anything beyond the trial's cap,
the trial's deadline or the pilot's ceiling.

Usage:
    python3 run_pilot.py --pilot-root DIR --work DIR --python-env DIR --extra-bin DIR \
        --baltor-key-file FILE [--probe | --trials ID,ID | --all]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import egress_proxy  # noqa: E402
import harness  # noqa: E402
import meter  # noqa: E402
import scoring  # noqa: E402

DESIGN_PATH = ROOT / "design" / "design.json"
FREEZE_PATH = ROOT / "design" / "design-freeze.json"
RESULTS = ROOT / "results"  # replaced by --results-dir for a fixture run
PROVIDER_FAILURES = {"rate_limited", "provider_error", "upstream_unreachable", "stream_interrupted",
                     "provider_key_missing"}
EDITABLE = {
    "a-cachetools-tlru": (re.compile(r"^(src/cachetools/__init__\.pyi?|docs/.*|CHANGELOG\.rst|tests/.*)$"),),
    "b-dotenv-backslash": (re.compile(r"^(src/dotenv/parser\.py|tests/.*|ROOT_CAUSE\.md|CHANGELOG\.md)$"),),
    "c-spaceship-titanic": (re.compile(r"^(?!data/|TASK\.md$).*$"),),
}


def now_text():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_freeze():
    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    problems = []
    for relative, digest in freeze["files"].items():
        path = ROOT / relative
        if not path.is_file() or sha256_file(path) != digest:
            problems.append(relative)
    if problems:
        raise SystemExit("frozen files changed: " + ", ".join(problems))
    return freeze


class Redactor:
    """Replace every known secret value before anything is written to the results folder."""

    def __init__(self, values):
        self.values = [value for value in values if value and len(value) >= 12]

    def text(self, value):
        for secret in self.values:
            value = value.replace(secret, "[REDACTED]")
        return value

    def object(self, value):
        return json.loads(self.text(json.dumps(value)))

    def assert_clean(self, folder):
        for path in Path(folder).rglob("*"):
            if path.is_file():
                data = path.read_bytes()
                for secret in self.values:
                    if secret.encode() in data:
                        raise SystemExit(f"secret found in {path}; refusing to continue")


def read_events(path):
    events = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def summarize_events(events):
    tools, calls, texts = Counter(), [], []
    tokens = Counter()
    steps = 0
    for event in events:
        part = event.get("part") or {}
        if event.get("type") == "tool_use":
            state = part.get("state") or {}
            name = part.get("tool")
            tools[name] += 1
            # Tool output text is never kept: it can hold competition data rows or account-gated library bodies.
            calls.append({"tool": name, "status": state.get("status"),
                          "input": json.dumps(state.get("input"), ensure_ascii=False)[:600],
                          "output_chars": len(state.get("output") or "")})
        elif event.get("type") == "text":
            texts.append(part.get("text") or "")
        elif event.get("type") == "step_finish":
            steps += 1
            for key, value in (part.get("tokens") or {}).items():
                if isinstance(value, (int, float)):
                    tokens[key] += value
                elif isinstance(value, dict):
                    for inner, amount in value.items():
                        if isinstance(amount, (int, float)):
                            tokens[key + "_" + inner] += amount
    return {"steps": steps, "tool_counts": dict(tools), "tool_calls": calls,
            "final_text": (texts[-1] if texts else "")[:1500], "harness_reported_tokens": dict(tokens)}


def baltor_activity(events, project, template):
    """What the Baltor arm offered, selected, read, placed and loaded, from the harness's own tool events."""
    searches, reads, manifests, other_mcp, skill_loads, client_commands = [], [], [], [], [], []
    retrieved_bodies = []
    for event in events:
        if event.get("type") != "tool_use":
            continue
        part = event.get("part") or {}
        state = part.get("state") or {}
        name = part.get("tool") or ""
        arguments = state.get("input") or {}
        output = state.get("output") or ""
        if name == "baltor_intelligence_search":
            hits = re.findall(r'"identity"\s*:\s*"([^"]+)"', output)
            searches.append({"query": arguments.get("query"), "status": state.get("status"),
                             "hit_identities": list(dict.fromkeys(hits))[:10], "output_chars": len(output)})
        elif name == "baltor_provisioning_read":
            reads.append({"identity": arguments.get("identity"), "expected_digest": arguments.get("expected_digest"),
                          "status": state.get("status"), "output_chars": len(output),
                          "refusal": (re.search(r'"code"\s*:\s*"([a-z_]+)"', output) or [None, None])[1]})
            if state.get("status") == "completed":
                retrieved_bodies.append(output)
        elif name == "baltor_provisioning_manifest":
            manifests.append({"identity": arguments.get("identity"), "status": state.get("status")})
        elif name.startswith("baltor_"):
            other_mcp.append({"tool": name, "status": state.get("status"),
                              "input": json.dumps(arguments, ensure_ascii=False)[:300]})
        elif name == "skill":
            skill_loads.append({"name": arguments.get("name"), "status": state.get("status")})
        elif name == "bash" and "baltor" in json.dumps(arguments):
            command = arguments.get("command") or ""
            client_commands.append({"command": command[:500], "status": state.get("status"),
                                    "output_chars": len(output)})
            if " fetch " in command or " install " in command:
                retrieved_bodies.append(output)
    installed = sorted(path.name for path in (Path(project) / ".opencode" / "skills").glob("*")
                       if path.is_dir() and not path.name.startswith(".") and path.name != "baltor-library") \
        if (Path(project) / ".opencode" / "skills").is_dir() else []
    used = used_material(retrieved_bodies, project, template)
    any_use = bool(searches or reads or manifests or other_mcp or client_commands
                   or any(row["name"] == "baltor-library" for row in skill_loads))
    return {"searches": searches, "reads": reads, "manifests": manifests, "other_mcp_calls": other_mcp,
            "skill_loads": skill_loads, "client_commands": client_commands, "installed_skills": installed,
            "abstained_from_baltor": not any_use, "material_overlap_with_work": used}


def word_shingles(text, size=8):
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text)
    return {" ".join(words[index:index + size]) for index in range(max(0, len(words) - size + 1))}


def used_material(bodies, project, template):
    """An inference, not an observation: how much of the harness's added work repeats retrieved text."""
    if not bodies:
        return {"retrieved_bodies": 0, "shared_shingles": 0, "note": "nothing was retrieved"}
    added = []
    for name, row in scoring.changed_files(template, project).items():
        if row["state"] != "deleted" and not name.startswith(".opencode/"):
            added.append((Path(project) / name).read_text(encoding="utf-8", errors="replace"))
    work = word_shingles("\n".join(added))
    material = set()
    for body in bodies:
        material |= word_shingles(body)
    shared = work & material
    return {"retrieved_bodies": len(bodies), "work_shingles": len(work), "material_shingles": len(material),
            "shared_shingles": len(shared), "examples": sorted(shared)[:5],
            "note": "eight-word sequences shared by retrieved text and the files the harness changed; an inference"}


def workspace_changes(task, template, project):
    changes = {name: row for name, row in scoring.changed_files(template, project).items()
               if not name.startswith(".opencode/")}
    pattern = EDITABLE[task][0]
    incidents = [{"file": name, **row} for name, row in changes.items()
                 if row["state"] != "added" and not pattern.match(name)]
    return changes, incidents


class Pilot:
    def __init__(self, args, design, fixture=None):
        self.args = args
        self.design = design
        self.results = args.results_dir.resolve()
        self.work = args.work.resolve()
        self.work.mkdir(parents=True, exist_ok=True)
        self.pilot_root = args.pilot_root.resolve()
        self.token = args.baltor_key_file.read_text(encoding="utf-8").strip()
        self.redactor = Redactor([self.token, os.environ.get(design["model_route"]["key_variable"], "")])
        route = design["model_route"]
        if fixture is not None:
            upstream = meter.Upstream(scheme="http", host="127.0.0.1", port=fixture, base_path="/v1", key_variable=None)
        else:
            upstream = meter.Upstream(scheme="https", host=route["host"], port=443, base_path=route["base_path"],
                                      key_variable=route["key_variable"])
        self.meter = meter.Meter(self.work / "ledger.jsonl", self.work / "transcripts",
                                 ceiling=design["budgets"]["pilot_ceiling_physical_requests"], upstream=upstream)
        self.meter_port = self.meter.start()
        self.opencode = Path(design["harness"]["binary_path"])
        if sha256_file(self.opencode) != design["harness"]["binary_sha256"]:
            raise SystemExit("the OpenCode binary differs from the frozen digest")
        self.entry = json.loads((ROOT / design["treatment"]["connection_entry_file"]).read_text())["mcp"]["baltor"]
        self.bootstrap = (ROOT / design["treatment"]["bootstrap_file"]).read_text(encoding="utf-8")
        self.treatment = (ROOT / design["treatment"]["prompt_line_file"]).read_text(encoding="utf-8")

    def close(self):
        self.meter.stop()

    def prompt(self, task, arm):
        text = (ROOT / "design" / "tasks" / task / "prompt.txt").read_text(encoding="utf-8")
        return text + (self.treatment if arm == "baltor" else "")

    def run_attempt(self, trial, attempt, cap, budget_seconds):
        task, arm = trial["task"], trial["arm"]
        attempt_id = f"{trial['id']}-attempt{attempt}"
        folder = self.work / attempt_id
        if folder.exists():
            raise SystemExit(f"{folder} exists; inspect it before running this attempt again")
        home = folder / "home"
        home.mkdir(parents=True)
        template = self.pilot_root / "templates" / task / "project"
        shutil.copytree(template, home / "project", symlinks=False)
        step_id = "s" + secrets.token_hex(6)
        harness.write_config(home, harness.opencode_config(self.meter_port, step_id, self.design["model_route"]["model"],
                                                           baltor_entry=self.entry if arm == "baltor" else None))
        proxy = egress_proxy.EgressProxy(folder / "egress.jsonl", attempt_id, self.design["network"]["allowed_hosts"])
        proxy_port = proxy.start()
        env = harness.sandbox_environment(proxy_port, self.args.python_env, self.args.extra_bin,
                                          pythonpath=self.design["tasks"][task].get("pythonpath"),
                                          baltor_token=self.token if arm == "baltor" else None)
        record = {"record_type": "comparison_pilot_trial/v1", "trial_id": trial["id"], "attempt": attempt,
                  "attempt_id": attempt_id, "plan_index": trial["index"], "task": task, "arm": arm,
                  "repetition": trial["repetition"], "meter_step_id": step_id, "started_at": now_text(),
                  "model": self.design["model_route"]["model"], "request_cap": cap,
                  "wall_clock_budget_seconds": budget_seconds}
        started = time.monotonic()
        setup = None
        if arm == "baltor":
            setup = harness.shell_in_sandbox(home, self.args.python_env, self.args.extra_bin, self.opencode, env,
                                             self.bootstrap, 300, folder / "setup.out", folder / "setup.err")
            setup_text = (folder / "setup.out").read_text(encoding="utf-8", errors="replace")
            setup["verified_ok_lines"] = setup_text.count(": OK")
        record["setup"] = setup
        remaining = max(60.0, budget_seconds - (time.monotonic() - started))
        context = meter.StepContext(trial_id=step_id, model=self.design["model_route"]["model"], arm=arm,
                                    family=task, repetition=trial["repetition"], cap=cap,
                                    deadline_monotonic=time.monotonic() + remaining)
        self.meter.open_step(context)

        def should_stop():
            if context.refused and context.physical >= cap:
                return "request_cap_reached"
            return None

        result = harness.run(home, self.args.python_env, self.args.extra_bin, self.opencode, env,
                             self.prompt(task, arm), "task", remaining, folder / "events.jsonl",
                             folder / "stderr.txt", should_stop=should_stop)
        self.meter.close_step(step_id)
        proxy.stop()
        record["harness"] = {key: result[key] for key in ("exit_status", "elapsed_seconds", "timed_out",
                                                          "stopped_by_runner")}
        record["elapsed_total_seconds"] = round(time.monotonic() - started, 3)
        record["finished_at"] = now_text()
        record["model_requests"] = self.request_summary(step_id)
        events = read_events(folder / "events.jsonl")
        record["events"] = summarize_events(events)
        project = home / "project"
        if arm == "baltor":
            record["baltor"] = baltor_activity(events, project, template)
        egress = [json.loads(line) for line in (folder / "egress.jsonl").read_text().splitlines()] \
            if (folder / "egress.jsonl").exists() else []
        record["egress"] = {"allowed": dict(Counter(row["host"] for row in egress if row.get("allowed"))),
                            "refused": dict(Counter(row["host"] for row in egress if not row.get("allowed")))}
        changes, incidents = workspace_changes(task, template, project)
        record["workspace_changes"] = changes
        record["wrong_file_incidents"] = incidents
        record["score"] = scoring.score(task, project, self.pilot_root, self.args.python_env, self.args.extra_bin)
        outcomes = record["model_requests"]["outcomes"]
        record["provider_failure_seen"] = any(outcomes.get(name) for name in PROVIDER_FAILURES)
        record["accepted"] = bool(record["score"].get("passed"))
        record["artifact_patch"] = None
        if task in ("a-cachetools-tlru", "b-dotenv-backslash"):
            patch = scoring.unified_patch(template, project)
            record["artifact_patch"] = f"results/patches/{attempt_id}.patch"
            self.write_result(record["artifact_patch"], patch)
        else:
            solution = project / "solution.py"
            if solution.is_file():
                record["artifact_patch"] = f"results/solutions/{attempt_id}-solution.py"
                self.write_result(record["artifact_patch"], solution.read_text(encoding="utf-8", errors="replace")[:60000])
        snapshot = folder / "final-project.tar"
        subprocess.run(["tar", "-cf", str(snapshot), "-C", str(home), "project"], check=False)
        self.write_result(f"results/trials/{attempt_id}.json", json.dumps(self.redactor.object(record), indent=1) + "\n")
        with open(self.results / "egress.jsonl", "a", encoding="utf-8") as handle:
            for row in egress:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
        return record

    def write_result(self, relative, text):
        path = self.results / Path(relative).relative_to("results")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.redactor.text(text), encoding="utf-8")

    def request_summary(self, step_id):
        rows = [json.loads(line) for line in (self.work / "ledger.jsonl").read_text(encoding="utf-8").splitlines()
                if line.strip()]
        mine = [row for row in rows if row.get("trial_id") == step_id]
        sent = [row for row in mine if row.get("event") == "sent"]
        refused = [row for row in mine if row.get("event") == "refused"]
        done = [row for row in mine if row.get("event") == "completed"]
        usage = Counter()
        missing = 0
        for row in done:
            if row.get("usage") and row["usage"].get("prompt_tokens") is not None:
                for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
                    usage[key] += row["usage"].get(key) or 0
            else:
                missing += 1
        return {"physical": len(sent), "refused": len(refused),
                "refusal_reasons": dict(Counter(row.get("reason") for row in refused)),
                "completed": len(done), "outcomes": dict(Counter(row.get("outcome") for row in done)),
                "http_statuses": dict(Counter(str(row.get("http_status")) for row in done)),
                "usage_totals": dict(usage), "requests_missing_usage": missing,
                "cached_input_tokens": "not reported by the provider",
                "provider_elapsed_ms": sum(row.get("elapsed_ms") or 0 for row in done),
                "requests": [{"sequence": row.get("sequence"), "elapsed_ms": row.get("elapsed_ms"),
                              "prompt_tokens": (row.get("usage") or {}).get("prompt_tokens"),
                              "completion_tokens": (row.get("usage") or {}).get("completion_tokens"),
                              "finish_reason": row.get("finish_reason"), "tool_calls": row.get("tool_calls"),
                              "outcome": row.get("outcome"), "messages": row.get("messages"),
                              "tools_offered": row.get("tools")} for row in done]}

    def run_trial(self, trial):
        budgets = self.design["budgets"]
        cap, seconds = budgets["trial_request_cap"], budgets["trial_wall_clock_seconds"]
        existing = sorted((self.results / "trials").glob(f"{trial['id']}-attempt*.json"))
        attempts = [json.loads(path.read_text()) for path in existing]
        if any(not row.get("provider_failure_seen") for row in attempts):
            print(f"{trial['id']}: already recorded")
            return
        if len(attempts) >= 1 + budgets["provider_failure_reruns"]:
            print(f"{trial['id']}: provider failures used every permitted attempt")
            return
        if attempts:
            time.sleep(budgets["provider_failure_wait_seconds"])
        if self.meter.remaining() < cap:
            raise SystemExit(f"stopping: {self.meter.remaining()} requests remain under the ceiling, below one cap")
        record = self.run_attempt(trial, len(attempts) + 1, cap, seconds)
        print(json.dumps({"trial": record["attempt_id"], "accepted": record["accepted"],
                          "physical": record["model_requests"]["physical"],
                          "elapsed": record["elapsed_total_seconds"],
                          "provider_failure_seen": record["provider_failure_seen"]}))
        if record["provider_failure_seen"]:
            self.run_trial(trial)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pilot-root", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--extra-bin", type=Path, required=True)
    parser.add_argument("--baltor-key-file", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--fixture", action="store_true",
                        help="dry run against offline_fake_model.py: zero provider calls, results outside the record")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--trials")
    args = parser.parse_args()
    check_freeze()
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    fake = None
    if args.fixture:
        if args.results_dir.resolve() == RESULTS.resolve():
            raise SystemExit("a fixture run writes its records outside the pilot results folder")
        from offline_fake_model import FakeModel
        fake = FakeModel([{"tool": "bash", "arguments": {"command": "ls -A && git status --short",
                                                         "description": "List the project"}}],
                         args.work / "fixture-requests")
        pilot = Pilot(args, design, fixture=fake.start())
    else:
        pilot = Pilot(args, design)
    try:
        plan = design["plan"]
        if args.trials:
            wanted = set(args.trials.split(","))
            plan = [trial for trial in plan if trial["id"] in wanted]
        for trial in plan:
            pilot.run_trial(trial)
    finally:
        pilot.close()
        if fake is not None:
            fake.stop()
        if (pilot.work / "ledger.jsonl").exists():
            shutil.copy2(pilot.work / "ledger.jsonl", pilot.results / "ledger.jsonl")
        pilot.redactor.assert_clean(pilot.results)


if __name__ == "__main__":
    main()
