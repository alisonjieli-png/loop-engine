"""Run the five 3D tasks with and without Baltor and report the pass rate of each condition.

Kind: comparison runner for the 3D showcase question of September 27, 2026 ("does material from Baltor make a
harness better at 3D modeling?"). The first comparison ran one run per task and condition; this runner runs a
fixed number of paired runs, grades them with checks frozen before the first run and reports every run.

Conditions, identical except for the Baltor material and one sentence that names where it is:

    without_baltor   OpenCode on the task text only.
    with_baltor      Before the harness starts, the runner acts as the customer's client: it searches Baltor with
                     the task text, takes the top skills of that search (frozen once before the first run),
                     downloads every file of each package with digest checks and places the files where OpenCode
                     reads project skills (.opencode/skills/<name>/). A fresh harness then starts with exactly
                     that material. No Baltor connection is open during the run.

Both conditions use the same OpenCode binary, model, sandbox, time budget and call ceiling. Every model call goes
through tools/showcase_3d/proxy.py, which records it.

Commands (every command takes --config CONFIG.json; see README.md):

    plan              write the paired, seeded schedule
    freeze            run the checker controls and record every check definition with its digest
    select            search Baltor once per task and record the selected identities and digests
    probe-installer   ask the first-party installer, in preview, whether it can place the selection natively
    run               run the schedule (resumable); waits while the shared model server is busy
    report            pass rate per condition with a Wilson 95 percent interval, and every run

A step that writes a record refuses to overwrite a different existing record.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import math
import os
import random
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPOSITORY = TOOLS.parent
SOURCE_ROOT = REPOSITORY / "src"
sys.path.insert(0, str(HERE))
from tasks import CONDITIONS, TASKS, check_definition_records, prompt_for  # noqa: E402

RUN_RECORD = "showcase_3d_run/v1"
MANIFEST_RECORD = "showcase_3d_check_manifest/v1"
SELECTION_RECORD = "showcase_3d_selection/v1"
SCHEDULE_RECORD = "showcase_3d_schedule/v1"
REPORT_RECORD = "showcase_3d_report/v1"
#: Grading is frozen: these files may not change after the freeze. The runner files are recorded with every run.
GRADING_FILES = ("tasks.py", "checks.py", "render_check.mjs", "controls.py")
RUNNER_FILES = ("rerun.py", "proxy.py")
#: The runner files as they were when this process started, recorded with every run.
RUNNER_DIGESTS = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in RUNNER_FILES}
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PHYSICAL = ("ok", "upstream_error", "transport_error")
DELIVERY_LOCK = threading.Lock()
LIMITS_LOCK = threading.Lock()


# ----------------------------------------------------------------------------------------------------------------
# Small records and statistics


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, value) -> None:
    """Write a JSON record; an existing different record is never replaced."""
    text = json.dumps(value, indent=1, sort_keys=True) + "\n"
    if path.exists() and path.read_text() != text:
        raise SystemExit(f"refused: {path} exists with other content; keep it and choose a new label")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def wilson(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion; (0, 1) when there are no trials."""
    if trials == 0:
        return (0.0, 1.0)
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    half = z * math.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return (max(0.0, centre - half), min(1.0, centre + half))


def newcombe(x1: int, n1: int, x2: int, n2: int) -> tuple[float, float, float]:
    """Difference p1 - p2 with Newcombe's hybrid score interval (method 10)."""
    p1, p2 = x1 / n1, x2 / n2
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return (d, d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2), d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2))


def token_totals(calls: list[dict]) -> dict:
    """Totals of the physical calls; a total is null when any call's usage is unknown."""
    physical = [c for c in calls if c.get("outcome") in PHYSICAL]
    unknown = sum(1 for c in physical if c.get("prompt_tokens") is None or c.get("completion_tokens") is None)
    known = unknown == 0 and bool(physical)
    return {"prompt_tokens": sum(c["prompt_tokens"] for c in physical) if known else (0 if not physical else None),
            "completion_tokens": sum(c["completion_tokens"] for c in physical) if known else (0 if not physical else None),
            "calls_with_unknown_usage": unknown}


# ----------------------------------------------------------------------------------------------------------------
# Sharing the model server


@dataclass(frozen=True)
class Sharing:
    slots_utc: tuple[str, ...]
    slot_minutes: int
    margin_minutes: int
    busy_patterns: tuple[str, ...]
    poll_seconds: int


def slot_conflict(moment: datetime, budget_seconds: int, sharing: Sharing) -> str:
    """Why a run started at `moment` with this budget would overlap a daily slot, or an empty string."""
    end = moment + timedelta(seconds=budget_seconds + 60 * sharing.margin_minutes)
    for day in (-1, 0, 1):
        for slot in sharing.slots_utc:
            hour, minute = (int(part) for part in slot.split(":"))
            start = (moment + timedelta(days=day)).replace(hour=hour, minute=minute, second=0, microsecond=0)
            finish = start + timedelta(minutes=sharing.slot_minutes)
            if moment < finish and end > start:
                return f"daily slot {slot} UTC ({start.isoformat()} to {finish.isoformat()})"
    return ""


def busy_lines(process_list: str, patterns: tuple[str, ...], own_pids: set[int]) -> list[str]:
    """Lines of `pgrep -af .` style output whose command matches a busy pattern, excluding this runner."""
    found = []
    for line in process_list.splitlines():
        pid_text, _, command = line.strip().partition(" ")
        if not pid_text.isdigit() or int(pid_text) in own_pids or "showcase_3d" in command:
            continue
        if any(pattern in command for pattern in patterns):
            found.append(line.strip()[:200])
    return found


def process_list() -> str:
    return subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True, text=True, timeout=30).stdout


def own_process_ids() -> set[int]:
    pids, pid = {os.getpid()}, os.getpid()
    while pid > 1:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
            pid = int(fields[1]); pids.add(pid)
        except Exception:
            break
    return pids


def wait_for_model_server(sharing: Sharing, budget_seconds: int, log: Path, maximum_wait_seconds: int) -> bool:
    """Block until no daily slot overlaps the next batch and no busy process runs; False after the maximum wait."""
    waited = 0
    while True:
        moment = datetime.now(timezone.utc)
        slot = slot_conflict(moment, budget_seconds, sharing)
        busy = busy_lines(process_list(), sharing.busy_patterns, own_process_ids())
        if not slot and not busy:
            if waited:
                with log.open("a") as handle:
                    handle.write(json.dumps({"at": now(), "event": "clear", "waited_seconds": waited}) + "\n")
            return True
        with log.open("a") as handle:
            handle.write(json.dumps({"at": now(), "event": "waiting", "slot": slot, "busy": busy[:5]}) + "\n")
        if waited >= maximum_wait_seconds:
            return False
        time.sleep(sharing.poll_seconds)
        waited += sharing.poll_seconds


# ----------------------------------------------------------------------------------------------------------------
# Configuration and credentials


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if config.get("record_type") != "showcase_3d_configuration/v1":
        raise SystemExit("the configuration must be showcase_3d_configuration/v1")
    for key in ("evidence_folder", "work_folder", "opencode", "node", "python_environment", "python_install_root",
                "hidden_home", "playwright_core", "chrome", "three_package", "customer_client", "service_origin",
                "service_credential_reference", "model_endpoint", "model", "proxy_port", "delivery_engine",
                "step_effects", "selection", "budget", "runs_per_cell", "pairs_in_parallel", "seed", "sharing"):
        if key not in config:
            raise SystemExit(f"the configuration lacks {key}")
    return config


def sharing_of(config: dict) -> Sharing:
    s = config["sharing"]
    return Sharing(tuple(s["slots_utc"]), int(s["slot_minutes"]), int(s["margin_minutes"]), tuple(s["busy_patterns"]),
                   int(s["poll_seconds"]))


def service_key(config: dict) -> str:
    spec = importlib.util.spec_from_file_location("operator_credentials", TOOLS / "operator_credentials.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    value = module.resolve(config["service_credential_reference"],
                           data=json.loads((TOOLS / "operator_credentials.json").read_text(encoding="utf-8")))
    return value if isinstance(value, str) else getattr(value, "value", "")


def scrub(text: str, secret: str) -> str:
    return text.replace(secret, "<service-key>") if secret else text


def kill_processes_under(folder: Path) -> list[int]:
    """Kill every process of this user whose working folder is inside `folder`; a harness may start commands in
    their own sessions, which a process-group kill does not reach."""
    killed, root = [], str(folder.resolve())
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            working = os.readlink(entry / "cwd")
        except OSError:
            continue
        if working == root or working.startswith(root + os.sep):
            try:
                os.kill(int(entry.name), signal.SIGKILL); killed.append(int(entry.name))
            except OSError:
                pass
    return killed


def run_bounded(argv: list[str], timeout: float, env: dict, cwd: Path, sweep: Path) -> tuple:
    """Run a command in its own process group. At the time budget the group is killed and every process left with a
    working folder under `sweep` is killed too, so no harness outlives its budget. Returns (exit, out, err, timed_out,
    killed)."""
    process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True,
                               env=env, cwd=str(cwd), start_new_session=True)
    try:
        out, err = process.communicate(timeout=timeout)
        return process.returncode, out, err, False, []
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        killed = kill_processes_under(sweep)
        try:
            out, err = process.communicate(timeout=30)
        except subprocess.TimeoutExpired:
            out, err = "", ""
        return None, out or "", err or "", True, killed


# ----------------------------------------------------------------------------------------------------------------
# plan, freeze, select


def plan(config: dict, label: str, only_task: str | None, runs: int | None) -> dict:
    tasks = [only_task] if only_task else list(TASKS)
    count = runs or int(config["runs_per_cell"])
    pairs = [{"pair": f"{task}-r{n}", "task": task, "run_number": n} for task in tasks for n in range(1, count + 1)]
    random.Random(int(config["seed"])).shuffle(pairs)
    size = int(config["pairs_in_parallel"])
    batches = [pairs[i:i + size] for i in range(0, len(pairs), size)]
    schedule = {"record_type": SCHEDULE_RECORD, "label": label, "seed": config["seed"], "conditions": list(CONDITIONS),
                "batches": [[{**pair, "runs": [f"{label}-{pair['pair']}-{condition}" for condition in CONDITIONS]}
                             for pair in batch] for batch in batches]}
    schedule["digest"] = hashlib.sha256(json.dumps(schedule["batches"], sort_keys=True).encode()).hexdigest()
    return schedule


def browser_flags(config: dict) -> list[str]:
    return ["--node", config["node"], "--playwright-core", config["playwright_core"], "--chrome", config["chrome"]]


def opencode_listing() -> tuple[tuple[str, ...], dict]:
    """The first-party installer's own no-model OpenCode listing command, reused rather than copied."""
    for folder in (str(SOURCE_ROOT), str(TOOLS)):
        if folder not in sys.path:
            sys.path.insert(0, folder)
    from install_selected_material import OPENCODE_PROFILE
    return OPENCODE_PROFILE.listing.arguments, dict(OPENCODE_PROFILE.listing.process_settings)


def freeze(config: dict, extra: Path | None) -> dict:
    evidence = Path(config["evidence_folder"])
    reference, controls = evidence / "reference", Path(config["work_folder"]) / "controls"
    report = evidence / "controls.json"
    python = Path(config["python_environment"]) / "bin" / "python"
    command = [str(python), str(HERE / "controls.py"), str(reference), str(controls), str(report),
               "--three", config["three_package"]] + browser_flags(config) + (["--extra", str(extra)] if extra else [])
    done = subprocess.run(command, capture_output=True, text=True, timeout=3600)
    print(done.stdout[-4000:])
    if done.returncode != 0:
        print(done.stderr[-3000:])
        raise SystemExit("controls did not behave as expected; nothing is frozen")
    control_report = json.loads(report.read_text())
    manifest = {"record_type": MANIFEST_RECORD, "frozen_at": now(),
                "grading_files": {name: sha256_file(HERE / name) for name in GRADING_FILES},
                "reference": {name: sha256_file(reference / name) for name in ("bracket_reference.stl", "broken.stl")},
                "checks": check_definition_records(),
                "controls": {"report_sha256": sha256_file(report), "count": len(control_report["controls"]),
                             "all_ok": control_report["all_controls_ok"]}}
    manifest["digest"] = hashlib.sha256(json.dumps({k: v for k, v in manifest.items() if k != "frozen_at"},
                                                   sort_keys=True).encode()).hexdigest()
    return manifest


def verify_frozen(config: dict) -> dict:
    manifest = json.loads((Path(config["evidence_folder"]) / "manifest.json").read_text())
    changed = [name for name, digest in manifest["grading_files"].items() if sha256_file(HERE / name) != digest]
    if changed:
        raise SystemExit(f"refused: {changed} changed after the freeze; freeze again under a new evidence folder")
    return manifest


def client_configuration(config: dict, folder: Path) -> Path:
    path = folder / "customer-client.json"
    write_new(path, {"record_type": "baltor_library_client_configuration/v2", "origin": config["service_origin"],
                     "credential_environment": "BALTOR_SERVICE_TOKEN", "authority_effects": list(config["step_effects"])})
    return path


def select(config: dict) -> dict:
    evidence = Path(config["evidence_folder"])
    folder = evidence / "selection"; folder.mkdir(parents=True, exist_ok=True)
    client_config = client_configuration(config, evidence)
    key = service_key(config)
    rule = config["selection"]
    chosen = {}
    for task, spec in TASKS.items():
        query = spec["prompt"].removeprefix("Task: ")
        done = subprocess.run(["python3", config["customer_client"], "--config", str(client_config), "search", query,
                               "--limit", str(rule["search_limit"])], capture_output=True, text=True, timeout=120,
                              env={**os.environ, "BALTOR_SERVICE_TOKEN": key})
        if done.returncode != 0:
            raise SystemExit(f"search failed for {task}: {scrub(done.stdout + done.stderr, key)[:300]}")
        saved = folder / f"{task}.json"
        saved.write_text(done.stdout)
        result = json.loads(done.stdout); result = result.get("result", result)
        items = [{"identity": hit["reference"]["identity"], "digest": hit["reference"]["body_digest"],
                  "kind": hit.get("kind"), "rank": rank + 1,
                  "files": len((hit.get("package") or {}).get("files") or []) or 1}
                 for rank, hit in enumerate(result["hits"]) if hit.get("kind") == rule["kind"]][:int(rule["top"])]
        chosen[task] = {"query_sha256": hashlib.sha256(query.encode()).hexdigest(), "search_file": saved.name,
                        "search_sha256": sha256_file(saved), "catalogue_release": result.get("catalogue_release"),
                        "items": items}
    return {"record_type": SELECTION_RECORD, "selected_at": now(), "rule": rule, "step_effects": config["step_effects"],
            "tasks": chosen}


# ----------------------------------------------------------------------------------------------------------------
# Delivery engines: both place full packages where OpenCode reads project skills


def skill_folder_name(skill_text: str, identity: str) -> str:
    """The skill's own frontmatter name when it is a valid folder name, otherwise a name made from the identity."""
    match = re.search(r"^---\s*\n(.*?)\n---", skill_text, re.S)
    if match:
        found = re.search(r"^name:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", match.group(1), re.M)
        if found and SKILL_NAME.match(found.group(1).strip()) and len(found.group(1).strip()) <= 64:
            return found.group(1).strip()
    made = re.sub(r"[^a-z0-9]+", "-", identity.lower()).strip("-")[:64].strip("-")
    return made or "baltor-item"


def safe_relative(path: str) -> PurePosixPath:
    """A package path that stays inside its folder, or a refusal."""
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or not candidate.parts or any(part in ("", ".", "..") for part in candidate.parts) or "\\" in path:
        raise ValueError(f"unsafe package path {path!r}")
    return candidate


def place_staged(staged: Path, receipt: dict, skills_root: Path, taken: set[str]) -> dict:
    """Copy a verified staged package into .opencode/skills/<name>/ and check every placed byte again."""
    files = receipt["files"]
    sources = {}
    for entry in files:
        relative = "SKILL.md" if entry["path"] == "body" else entry["path"]
        source = staged / ("body" if entry["path"] == "body" else f"payload/{entry['path']}")
        sources[str(safe_relative(relative))] = (source, entry["digest"])
    if "SKILL.md" not in sources:
        raise ValueError("the package has no SKILL.md at its root")
    name = skill_folder_name(sources["SKILL.md"][0].read_text(encoding="utf-8", errors="replace"), receipt["identity"])
    base, n = name, 2
    while name in taken:
        name = f"{base}-{n}"; n += 1
    taken.add(name)
    target_root = skills_root / name
    placed = []
    for relative, (source, digest) in sorted(sources.items()):
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"staged file missing or a link: {relative}")
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError(f"refused to replace {target}")
        shutil.copyfile(source, target)
        actual = sha256_file(target)
        if actual != digest:
            raise ValueError(f"placed bytes differ for {relative}")
        placed.append({"path": f".opencode/skills/{name}/{relative}", "sha256": actual, "size_bytes": target.stat().st_size})
    return {"skill_folder": f".opencode/skills/{name}", "files": placed}


def deliver_customer_client(config: dict, run_root: Path, project: Path, items: list[dict], search_file: Path,
                            client_config: Path, key: str) -> dict:
    """Engine customer_client_stage_and_place: the first-party customer client fetches, the runner places."""
    stage = run_root / "stage"; stage.mkdir(exist_ok=True)
    skills_root = project / ".opencode" / "skills"
    taken, delivered, errors = set(), [], []
    for item in items:
        request_id, placed = str(uuid.uuid4()), None
        attempts = []
        for attempt in range(1, 4):
            output = stage / f"{item['identity']}-attempt-{attempt}"
            with DELIVERY_LOCK:
                done = subprocess.run(["python3", config["customer_client"], "--config", str(client_config), "fetch",
                                       "--selection", str(search_file), "--identity", item["identity"], "--digest", item["digest"],
                                       "--request-id", request_id, "--output", str(output), "--authorize-download"],
                                      capture_output=True, text=True, timeout=300, env={**os.environ, "BALTOR_SERVICE_TOKEN": key})
            receipt_path = output / "receipt.json"
            if done.returncode == 0 and receipt_path.exists():
                receipt = json.loads(receipt_path.read_text())
                if receipt.get("complete"):
                    try:
                        placed = place_staged(output, receipt, skills_root, taken)
                    except ValueError as exc:
                        attempts.append({"attempt": attempt, "error": "placement_refused: " + str(exc)[:200]})
                    break
            failure = output / "failure.json"
            reason = json.loads(failure.read_text()).get("failure") if failure.exists() else scrub(done.stdout[-200:], key)
            attempts.append({"attempt": attempt, "error": reason})
            if attempt < 3:
                time.sleep((10, 30)[attempt - 1])
        record = {"identity": item["identity"], "selected_digest": item["digest"], "request_id": request_id,
                  "attempts": attempts, "placed": placed}
        (delivered if placed else errors).append(record)
    return {"engine": "customer_client_stage_and_place", "delivered": delivered, "not_delivered": errors}


def deliver_first_party_installer(config: dict, run_root: Path, project: Path, items: list[dict], key: str,
                                  run_id: str, preview: bool = False) -> dict:
    """Engine first_party_installer: tools/install_selected_material.py fetches and places natively."""
    report = run_root / f"installer-{'preview' if preview else 'install'}.json"
    command = [str(Path(config["python_environment"]) / "bin" / "python"), str(TOOLS / "install_selected_material.py"),
               "--origin", config["service_origin"], "--key-variable", "BALTOR_SERVICE_TOKEN", "--client", "opencode",
               "--target", str(project), "--report", str(report), "--request-prefix", run_id]
    for item in items:
        command += ["--identity", item["identity"]]
    for effect in config["step_effects"]:
        command += ["--step-effect", effect]
    command += ["--preview"] if preview else ["--authorize-install", "--client-executable", config["opencode"]]
    with DELIVERY_LOCK:
        done = subprocess.run(command, capture_output=True, text=True, timeout=600,
                              env={**os.environ, "BALTOR_SERVICE_TOKEN": key, "PYTHONPATH": os.pathsep.join((str(SOURCE_ROOT), str(TOOLS)))})
    data = json.loads(report.read_text()) if report.exists() else {"refusal": scrub(done.stdout[-300:] + done.stderr[-300:], key)}
    placed = []
    skills_root = project / ".opencode" / "skills"
    if skills_root.exists():
        for path in sorted(p for p in skills_root.rglob("*") if p.is_file()):
            placed.append({"path": str(path.relative_to(project)), "sha256": sha256_file(path), "size_bytes": path.stat().st_size})
    items_report = [{"identity": row.get("identity"), "refusal": row.get("refusal"), "state": row.get("state")}
                    for row in data.get("items", [])]
    return {"engine": "first_party_installer", "preview": preview, "installer_summary": data.get("summary"),
            "items": items_report, "placed_files": placed, "exit_code": done.returncode}


# ----------------------------------------------------------------------------------------------------------------
# One run


def sandbox(config: dict, run_root: Path, project: Path, argv: list[str]) -> list[str]:
    opencode_root = Path(config["opencode"]).resolve().parent.parent
    cache = Path(config["work_folder"]) / "opencode-cache"
    return ["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--tmpfs", config["hidden_home"],
            "--ro-bind", str(opencode_root), str(opencode_root),
            "--ro-bind", config["python_install_root"], config["python_install_root"],
            "--ro-bind", config["python_environment"], config["python_environment"],
            "--bind", str(cache), str(cache),
            "--bind", str(run_root), str(run_root),
            "--die-with-parent", "--chdir", str(project)] + argv


def harness_environment(python_environment: Path, opencode_folder: Path, run_root: Path, cache: Path) -> dict:
    return {"PATH": os.pathsep.join((str(python_environment / "bin"), str(opencode_folder), os.defpath)),
            "HOME": str(run_root / "home"), "XDG_CONFIG_HOME": str(run_root / "xdg-config"),
            "XDG_DATA_HOME": str(run_root / "xdg-data"), "XDG_STATE_HOME": str(run_root / "xdg-state"),
            "XDG_CACHE_HOME": str(cache), "TERM": "dumb", "LANG": "C.UTF-8",
            "OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_CLAUDE_CODE": "1", "VIRTUAL_ENV": str(python_environment),
            "MPLBACKEND": "Agg"}


def set_limit(limits: Path, run_id: str, calls: int) -> None:
    with LIMITS_LOCK:
        data = json.loads(limits.read_text()) if limits.exists() else {"*": 0}
        data[run_id] = calls
        temporary = limits.with_name(f"limits.{os.getpid()}.{threading.get_ident()}.tmp")
        temporary.write_text(json.dumps(data, indent=1)); temporary.replace(limits)


def run_one(config: dict, label_folder: Path, run: dict, selection: dict, calls_per_run: int, client_config: Path) -> dict:
    run_id, task, condition = run["run_id"], run["task"], run["condition"]
    out = label_folder / "runs" / run_id
    if (out / "run.json").exists():
        return json.loads((out / "run.json").read_text())
    work = Path(config["work_folder"]) / label_folder.name / run_id
    if work.exists():
        shutil.move(str(work), str(work) + f".abandoned-{int(time.time())}")
    project = work / "project"
    for folder in (project, work / "home", work / "xdg-config" / "opencode", work / "xdg-data", work / "xdg-state"):
        folder.mkdir(parents=True)
    (Path(config["work_folder"]) / "opencode-cache").mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    reference = Path(config["evidence_folder"]) / "reference"
    for name in TASKS[task]["supplied"]:
        (project / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(reference / name, project / name)
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    key = service_key(config)
    delivery, delivery_seconds = None, 0.0
    if condition == "with_baltor":
        items = selection["tasks"][task]["items"]
        started = time.time()
        if config["delivery_engine"] == "customer_client_stage_and_place":
            search_file = Path(config["evidence_folder"]) / "selection" / selection["tasks"][task]["search_file"]
            delivery = deliver_customer_client(config, work, project, items, search_file, client_config, key)
        elif config["delivery_engine"] == "first_party_installer":
            delivery = deliver_first_party_installer(config, work, project, items, key, run_id)
        else:
            raise SystemExit(f"unknown delivery engine {config['delivery_engine']}")
        delivery_seconds = round(time.time() - started, 1)
    body = {"provider": {"measured": {"npm": "@ai-sdk/openai-compatible", "name": "measured",
                                      "options": {"baseURL": f"http://127.0.0.1:{config['proxy_port']}/r/{run_id}/v1",
                                                  "apiKey": "local-counting-proxy"},
                                      "models": {config["model"]: {"name": config["model"]}}}},
            "model": f"measured/{config['model']}", "small_model": f"measured/{config['model']}",
            "autoupdate": False, "share": "disabled", "permission": {"edit": "allow", "bash": "allow", "webfetch": "deny"}}
    (work / "xdg-config" / "opencode" / "opencode.json").write_text(json.dumps(body, indent=2))
    environment = harness_environment(Path(config["python_environment"]), Path(config["opencode"]).parent, work,
                                      Path(config["work_folder"]) / "opencode-cache")
    listing_arguments, listing_settings = opencode_listing()
    _, listing_out, listing_err, _, _ = run_bounded(sandbox(config, work, project, [config["opencode"], *listing_arguments]),
                                                     180, {**environment, **listing_settings}, project, work)
    try:
        listed_rows = [{"name": row.get("name"), "location": str(row.get("location", ""))} for row in json.loads(listing_out)]
    except Exception:
        listed_rows = None
    write_new(out / "skill-listing.json", {"parsed": listed_rows is not None, "skills": listed_rows,
                                          "stderr_tail": listing_err[-2000:]})
    names = {row["name"] for row in listed_rows or []}
    placed_folders = [entry["placed"]["skill_folder"].rsplit("/", 1)[-1] for entry in (delivery or {}).get("delivered", [])]
    listed = {name: name in names for name in placed_folders}
    version = subprocess.run([config["opencode"], "--version"], capture_output=True, text=True, timeout=60).stdout.strip()
    prompt = prompt_for(task, condition)
    (out / "prompt.txt").write_text(prompt)
    limits = label_folder / "limits.json"
    set_limit(limits, run_id, calls_per_run)
    argv = [config["opencode"], "run", "--format", "json", "--auto", "--title", run_id, prompt]
    started_at, t0 = now(), time.time()
    exit_code, stdout, stderr, timed_out, killed = run_bounded(["nice", "-n", "10"] + sandbox(config, work, project, argv),
                                                               int(config["budget"]["wall_seconds"]), environment, project, work)
    wall = round(time.time() - t0, 1)
    set_limit(limits, run_id, 0)
    (out / "events.jsonl").write_text(scrub(stdout, key))
    (out / "stderr.txt").write_text(scrub(stderr, key)[-20000:])
    ledger = label_folder / "model-calls.jsonl"
    calls = [json.loads(line) for line in ledger.read_text().splitlines() if f'"run_id": "{run_id}"' in line] if ledger.exists() else []
    physical = [c for c in calls if c.get("outcome") in PHYSICAL]
    check, checker_attempts = None, []
    for _ in range(3):
        # The checker grades the same saved output each time; it is run again only when the checker itself failed.
        checked = subprocess.run([str(Path(config["python_environment"]) / "bin" / "python"), str(HERE / "checks.py"), task,
                                  str(project), "--reference", str(reference)] + browser_flags(config),
                                 capture_output=True, text=True, timeout=900)
        try:
            check = json.loads(checked.stdout.strip().splitlines()[-1])
        except Exception:
            check = {"passed": False, "checks": [], "reason": "checker_failed: " + checked.stderr[-300:]}
        fault = check.get("reason", "").startswith("checker_failed") or any(
            c["name"] in ("checker_ran", "render_harness") and not c["passed"] for c in check.get("checks", []))
        checker_attempts.append({"passed": check.get("passed"), "checker_fault": fault, "reason": check.get("reason", "")[:200]})
        if not fault:
            break
    output = project / TASKS[task]["output"]
    output_digest = sha256_file(output) if output.exists() else None
    if output.exists():
        shutil.copy(output, out / output.name)
    for extra in ("_checker_screenshot.png",):
        if (project / extra).exists():
            shutil.copy(project / extra, out / extra)
    for script in project.glob("*.py"):
        shutil.copy(script, out / ("script-" + script.name))
    refused = [c for c in calls if c.get("outcome") == "refused"]
    failures = []
    if timed_out:
        failures.append("harness_time_budget_reached")
    if refused:
        failures.append("call_ceiling_reached")
    if any(c.get("outcome") != "ok" for c in physical):
        failures.append("model_endpoint_error")
    if condition == "with_baltor" and (delivery or {}).get("not_delivered"):
        failures.append("delivery_incomplete")
    if exit_code not in (0, None) and not refused:
        failures.append(f"harness_exit_{exit_code}")
    if checker_attempts[-1]["checker_fault"]:
        failures.append("checker_error")
    if not check.get("passed"):
        failures.append("checks_failed")
    record = {"record_type": RUN_RECORD, "run_id": run_id, "label": label_folder.name, "task": task, "condition": condition,
              "run_number": run["run_number"], "pair": run["pair"], "batch": run["batch"], "started": started_at, "ended": now(),
              "wall_seconds": wall, "time_budget_seconds": int(config["budget"]["wall_seconds"]), "timed_out": timed_out,
              "exit_code": exit_code, "harness": {"name": "opencode", "version": version}, "model": config["model"],
              "model_endpoint": config["model_endpoint"], "call_ceiling": calls_per_run, "model_calls": len(physical),
              "model_calls_answered": sum(1 for c in physical if c.get("outcome") == "ok"), "refused_by_ceiling": len(refused),
              "longest_call_seconds": max((c.get("seconds") or 0 for c in physical), default=0),
              "calls_over_300_seconds": sum(1 for c in physical if (c.get("seconds") or 0) > 300),
              **token_totals(calls), "delivery": delivery, "delivery_seconds": delivery_seconds,
              "skills_listed_by_opencode": listed, "passed": bool(check.get("passed")), "checks": check.get("checks", []),
              "check_reason": check.get("reason"), "checker_attempts": checker_attempts, "failures": failures,
              "output_sha256": output_digest,
              "manifest_digest": json.loads((Path(config["evidence_folder"]) / "manifest.json").read_text())["digest"],
              "runner_files": RUNNER_DIGESTS, "processes_killed_at_budget": len(killed),
              "delivery_engine": config["delivery_engine"] if condition == "with_baltor" else None}
    write_new(out / "run.json", record)
    with (label_folder / "runs.jsonl").open("a") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


# ----------------------------------------------------------------------------------------------------------------
# The whole schedule


def start_proxy(config: dict, label_folder: Path, session_ceiling: int) -> subprocess.Popen:
    ledger, limits = label_folder / "model-calls.jsonl", label_folder / "limits.json"
    if not limits.exists():
        limits.write_text(json.dumps({"*": 0}))
    process = subprocess.Popen([sys.executable, str(HERE / "proxy.py"), "--endpoint", config["model_endpoint"],
                                "--port", str(config["proxy_port"]), "--ledger", str(ledger), "--limits", str(limits),
                                "--session-ceiling", str(session_ceiling)],
                               stdout=(label_folder / "proxy-output.txt").open("a"), stderr=subprocess.STDOUT,
                               start_new_session=True)
    for _ in range(60):
        time.sleep(1)
        if ledger.exists() and '"proxy_start"' in ledger.read_text().splitlines()[-1]:
            return process
        if process.poll() is not None:
            break
    raise SystemExit("the counting proxy did not start; see proxy-output.txt")


def run_schedule(config: dict, label: str, calls_per_run: int, session_ceiling: int, maximum_wait_seconds: int) -> None:
    verify_frozen(config)
    evidence = Path(config["evidence_folder"])
    label_folder = evidence / label
    schedule = json.loads((label_folder / "schedule.json").read_text())
    selection = json.loads((evidence / "selection.json").read_text())
    client_config = evidence / "customer-client.json"
    sharing = sharing_of(config)
    waits = label_folder / "waits.jsonl"
    proxy = None
    try:
        for number, batch in enumerate(schedule["batches"], 1):
            runs = [{"run_id": run_id, "task": pair["task"], "condition": condition, "run_number": pair["run_number"],
                     "pair": pair["pair"], "batch": number}
                    for pair in batch for run_id, condition in zip(pair["runs"], schedule["conditions"])]
            runs = [run for run in runs if not (label_folder / "runs" / run["run_id"] / "run.json").exists()]
            if not runs:
                continue
            if not wait_for_model_server(sharing, int(config["budget"]["wall_seconds"]) + 900, waits, maximum_wait_seconds):
                print(f"{now()} stopped: the model server stayed busy; run the same command again to resume", flush=True)
                return
            if proxy is None:
                proxy = start_proxy(config, label_folder, session_ceiling)
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(runs)) as pool:
                futures = {}
                for run in runs:
                    futures[pool.submit(run_one, config, label_folder, run, selection, calls_per_run, client_config)] = run
                    time.sleep(3)
                for future in concurrent.futures.as_completed(futures):
                    run = futures[future]
                    try:
                        record = future.result()
                        print(f"{now()} {run['run_id']} {'passed' if record['passed'] else 'failed'} "
                              f"calls={record['model_calls']} wall={record['wall_seconds']}s {record['check_reason'][:100]}", flush=True)
                    except Exception as exc:
                        print(f"{now()} {run['run_id']} runner_error {type(exc).__name__}: {str(exc)[:200]}", flush=True)
    finally:
        if proxy is not None:
            os.killpg(proxy.pid, signal.SIGTERM)


# ----------------------------------------------------------------------------------------------------------------
# Report


def report(label_folder: Path) -> dict:
    latest = {}
    for line in (label_folder / "runs.jsonl").read_text().splitlines():
        record = json.loads(line)
        latest[record["run_id"]] = record
    runs = sorted(latest.values(), key=lambda r: (r["task"], r["run_number"], r["condition"]))
    cells = {}
    for record in runs:
        for key in (record["condition"], f"{record['task']}:{record['condition']}"):
            cell = cells.setdefault(key, {"runs": 0, "passed": 0})
            cell["runs"] += 1; cell["passed"] += int(record["passed"])
    for cell in cells.values():
        low, high = wilson(cell["passed"], cell["runs"])
        cell.update({"rate": cell["passed"] / cell["runs"], "wilson95_low": low, "wilson95_high": high})
    difference = None
    a, b = cells.get("with_baltor"), cells.get("without_baltor")
    if a and b:
        d, low, high = newcombe(a["passed"], a["runs"], b["passed"], b["runs"])
        difference = {"with_minus_without": d, "newcombe95_low": low, "newcombe95_high": high,
                      "note": "tasks are pooled; the tasks differ in difficulty"}
    value = {"record_type": REPORT_RECORD, "label": label_folder.name, "written": now(), "cells": cells,
             "difference": difference, "runs": runs}
    lines = [f"# 3D with and without Baltor: {label_folder.name}", "",
             "| Condition | Runs | Passed | Pass rate | Wilson 95% interval |", "|---|---|---|---|---|"]
    for key in sorted(cells):
        c = cells[key]
        lines.append(f"| {key} | {c['runs']} | {c['passed']} | {c['rate']:.2f} | {c['wilson95_low']:.2f} to {c['wilson95_high']:.2f} |")
    if difference:
        lines += ["", f"Difference with minus without, tasks pooled: {difference['with_minus_without']:+.2f} "
                      f"(Newcombe 95%: {difference['newcombe95_low']:+.2f} to {difference['newcombe95_high']:+.2f})."]
    recorded = [r for r in runs if "calls_over_300_seconds" in r]
    stalled = [r["run_id"] for r in recorded if r["calls_over_300_seconds"]]
    lines += ["", f"Runs with a model call over 300 seconds (a slow or stalled server): {len(stalled)} of {len(recorded)} "
                  f"that record it; not recorded for {len(runs) - len(recorded)}."]
    lines += ["", "| Run | Task | Condition | No. | Pass | Calls | Prompt tokens | Completion tokens | Wall s | Longest call s | Baltor files | Failing checks | Failures |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in runs:
        files = sum(len(d["placed"]["files"]) for d in (r.get("delivery") or {}).get("delivered", [])) if r.get("delivery") else 0
        failing = ", ".join(c["name"] for c in r["checks"] if not c["passed"]) or "none"
        longest = f"{r['longest_call_seconds']:.0f}" if "longest_call_seconds" in r else "not recorded"
        lines.append(f"| {r['run_id']} | {r['task']} | {r['condition']} | {r['run_number']} | {'pass' if r['passed'] else 'fail'} | "
                     f"{r['model_calls']} | {r['prompt_tokens']} | {r['completion_tokens']} | {r['wall_seconds']:.0f} | "
                     f"{longest} | {files} | {failing} | {', '.join(r['failures']) or 'none'} |")
    (label_folder / "report.md").write_text("\n".join(lines) + "\n")
    (label_folder / "report.json").write_text(json.dumps(value, indent=1, sort_keys=True))
    return value


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("plan", "freeze", "select", "probe-installer", "run", "report"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--label", default="rerun", help="Evidence subfolder and run id prefix, for example dry or rerun.")
    parser.add_argument("--only-task", choices=tuple(TASKS), default=None)
    parser.add_argument("--runs", type=int, default=None, help="Runs per task and condition; the configuration's by default.")
    parser.add_argument("--calls-per-run", type=int, default=None)
    parser.add_argument("--session-ceiling", type=int, default=None)
    parser.add_argument("--extra-controls", type=Path, default=None)
    parser.add_argument("--maximum-wait-hours", type=float, default=12.0)
    parser.add_argument("--wall-seconds", type=int, default=None, help="Time budget per run; the configuration's by default.")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    evidence = Path(config["evidence_folder"]); evidence.mkdir(parents=True, exist_ok=True)
    label_folder = evidence / args.label
    if args.command == "plan":
        schedule = plan(config, args.label, args.only_task, args.runs)
        write_new(label_folder / "schedule.json", schedule)
        print(json.dumps({"batches": len(schedule["batches"]), "runs": sum(2 * len(b) for b in schedule["batches"]),
                          "digest": schedule["digest"]}))
    elif args.command == "freeze":
        manifest = freeze(config, args.extra_controls)
        write_new(evidence / "manifest.json", manifest)
        print(json.dumps({"manifest_digest": manifest["digest"], "checks": len(manifest["checks"]), "controls": manifest["controls"]}))
    elif args.command == "select":
        write_new(evidence / "selection.json", select(config))
        print((evidence / "selection.json").read_text()[:3000])
    elif args.command == "probe-installer":
        selection = json.loads((evidence / "selection.json").read_text())
        key, results = service_key(config), {}
        for task, chosen in selection["tasks"].items():
            root = Path(config["work_folder"]) / "installer-probe" / f"{task}-{int(time.time())}"
            (root / "project").mkdir(parents=True)
            results[task] = deliver_first_party_installer(config, root, root / "project", chosen["items"], key,
                                                         f"probe-{task}", preview=True)
        write_new(evidence / f"installer-probe-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json", results)
        for task, result in results.items():
            print(task, [(item["identity"], (item.get("refusal") or {}).get("code")) for item in result["items"]])
    elif args.command == "run":
        calls = args.calls_per_run or int(config["budget"]["calls_per_run"])
        if args.wall_seconds:
            config["budget"]["wall_seconds"] = args.wall_seconds
        ceiling = args.session_ceiling or int(config["budget"]["session_calls"])
        run_schedule(config, args.label, calls, ceiling, int(args.maximum_wait_hours * 3600))
        report(label_folder)
    elif args.command == "report":
        print((label_folder / "report.md").read_text() if report(label_folder) else "")
    return 0


if __name__ == "__main__":
    sys.exit(main())
