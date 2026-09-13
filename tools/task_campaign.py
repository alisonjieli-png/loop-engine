"""Task-database campaign: harness arms on gated ML tasks.

Population: /home/username/task_database/adapted (8 tasks, each with
task.txt, gate.sh holdout gate, metric.json floor). The 318 raw
kaggle_tasks have no gates and are excluded until adapted.

Evaluator: each task's own gate.sh (seeded holdout vs floor). No LLM judge.

Evaluator note: the task gate is both the campaign evaluator and the
solver's mid-run verifier (the solve runs with --verifier gate.sh), so a
gate pass is not an independent held-out result; the solver has already
seen the same gate while working. The behavior stays as it is and the
report names this in its limitations.

Resilience contract: every cell is attempted in isolation; any crash,
timeout, or refusal is recorded on that cell and the batch continues.
The standardized report (JSON + markdown) is always written, including
partial results. Safety boundaries are never bypassed to achieve this:
a refused effect is a recorded cell outcome, not a crash.

Usage:
  python tools/task_campaign.py --list
  python tools/task_campaign.py --validate-all
  python tools/task_campaign.py --matrix --arms opencode,pi --tasks <t1>,<t2>
  python tools/task_campaign.py --run --arms opencode --tasks <t> \\
      --settings-file /tmp/tactical-probe/tactical-settings.yaml \\
      --provider tactical --model-id gemma-4-coding-abliterated \\
      --model-route custom.tactical --max-model-calls 30 --cell-timeout 1800
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import traceback
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

TASK_DB = Path("/home/username/task_database/adapted")
RECORD_TYPE = "task_campaign_cell/v1"
REPORT_TYPE = "task_campaign_report/v1"


def list_tasks() -> list[dict]:
    items = []
    for task_dir in sorted(TASK_DB.iterdir()):
        if not task_dir.is_dir():
            continue
        metric = {}
        metric_path = task_dir / "metric.json"
        if metric_path.is_file():
            metric = json.loads(metric_path.read_text())
        zips = list((task_dir / "data").glob("*.zip")) if (task_dir / "data").is_dir() else []
        items.append({
            "task": task_dir.name,
            "has_task_txt": (task_dir / "task.txt").is_file(),
            "has_gate": (task_dir / "gate.sh").is_file(),
            "has_metric": bool(metric),
            "metric": metric.get("metric", ""),
            "floor": metric.get("floor", None),
            "zip_bytes": sum(p.stat().st_size for p in zips),
        })
    return items


def validate_task(name: str) -> dict:
    task_dir = TASK_DB / name
    errors = []
    if not task_dir.is_dir():
        return {"task": name, "valid": False, "errors": ["missing task dir"]}
    for fname in ("task.txt", "gate.sh", "metric.json"):
        if not (task_dir / fname).is_file():
            errors.append(f"missing {fname}")
    try:
        metric = json.loads((task_dir / "metric.json").read_text())
        if not metric.get("metric") or not isinstance(metric.get("floor"), (int, float)):
            errors.append("metric.json needs metric name and numeric floor")
    except (ValueError, OSError) as exc:
        errors.append(f"metric.json unreadable: {type(exc).__name__}")
    zips = list((task_dir / "data").glob("*.zip")) if (task_dir / "data").is_dir() else []
    if not zips:
        errors.append("no data zip")
    else:
        try:
            with zipfile.ZipFile(zips[0]) as zf:
                bad = zf.testzip()
                if bad is not None:
                    errors.append(f"zip corrupt at {bad}")
        except Exception as exc:
            errors.append(f"zip unreadable: {type(exc).__name__}")
    return {"task": name, "valid": not errors, "errors": errors}


def configured_arms() -> list[str]:
    embodiments = ROOT / "embodiments"
    if not embodiments.is_dir():
        return []
    return sorted(d.name for d in embodiments.iterdir()
                  if (d / "harness.json").is_file())


def matrix(tasks: list[str], arms: list[str]) -> list[dict]:
    return [{"record_type": RECORD_TYPE, "task": t, "arm": a, "status": "staged"}
            for t in tasks for a in arms]


def _scan_outcome(text: str) -> dict:
    """Return the solve outcome doc from multi-doc stdout ({} if absent).

    Falls back to summing physical calls from gateway-result docs (any
    model_gateway_result/ version) when the solve died before printing its
    outcome (crash path); a missing outcome doc is itself recorded, never
    papered over.
    """
    decoder = json.JSONDecoder()
    found: dict = {}
    calls: list[int] = []
    idx, end = 0, len(text or "")
    while idx < end:
        try:
            obj, idx = decoder.raw_decode(text, idx)
        except ValueError:
            idx += 1
            continue
        if isinstance(obj, dict):
            if ("terminal_code" in obj
                    or "outcome" in str(obj.get("record_type", ""))):
                found = obj
            if str(obj.get("record_type", "")).startswith(
                    "model_gateway_result/"):
                count = obj.get("physical_model_calls")
                if isinstance(count, int):
                    calls.append(count)
    if found:
        if found.get("model_calls") is None and calls:
            found = dict(found, model_calls=sum(calls),
                         model_calls_from="gateway_docs_fallback")
        return found
    if calls:
        return {"model_calls": sum(calls),
                "model_calls_from": "gateway_docs_fallback",
                "note": "no solve outcome doc in stdout"}
    return {}


EVALUATION_CONTRACT = """
## Evaluation contract (machine-checked, do not remove)

The local holdout gate `gate.sh` (which you must not edit) imports
`solution.py` from this directory and calls `predict(row)` once per
held-out row, where `row` is a dict of the training CSV's columns.
Your `solution.py` MUST define:

    def predict(row): ...

returning one predicted target value per row (same values as the training
`target` column). Train any model you like on `data/*.zip`; keep all
effects inside this directory. A script without `predict(row)` fails the
gate even if it prints good numbers.
"""


def _archive_previous_attempt(cell_dir: Path) -> str:
    """Move an existing cell directory aside; nothing is ever deleted.

    Returns the archived path as a string, or "" when there was nothing
    to archive. The name carries a UTC timestamp; a collision within the
    same second gets a numeric suffix.
    """
    if not (cell_dir.exists() or cell_dir.is_symlink()):
        return ""
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ")
    archived = cell_dir.with_name(f"{cell_dir.name}.previous-{stamp}")
    counter = 1
    while archived.exists() or archived.is_symlink():
        counter += 1
        archived = cell_dir.with_name(
            f"{cell_dir.name}.previous-{stamp}-{counter}")
    cell_dir.rename(archived)
    return str(archived)


def stage_cell(task: str, cell_dir: Path) -> dict:
    """Copy the task and append the machine-checked contract (recorded).

    A previous attempt in the same cell directory (its workspace, solver
    output, and cell record) is archived beside it, never deleted, and the
    archived path is recorded as previous_attempt_dir.
    """
    import hashlib
    previous = _archive_previous_attempt(cell_dir)
    shutil.copytree(TASK_DB / task, cell_dir, symlinks=False,
                    ignore=shutil.ignore_patterns("__pycache__"))
    task_txt = cell_dir / "task.txt"
    original = task_txt.read_bytes()
    task_txt.write_bytes(original + EVALUATION_CONTRACT.encode("utf-8"))
    return {"staged_sha256": hashlib.sha256(original).hexdigest(),
            "contract_appended": True,
            "previous_attempt_dir": previous}


def _outcome_artifact(outcome: dict | None,
                      cell_dir: Path) -> tuple[Path | None, bool]:
    """The solution.py the solve outcome names, confined to the cell.

    Returns (path, verified). The outcome's artifacts carry a path (absolute
    when the solve had a workspace) and a verified flag; verified artifacts
    win over unverified ones, then the outcome's own order. Anything that
    is not a solution.py, is missing, or resolves outside the cell is
    ignored, so absent stays absent.
    """
    if not isinstance(outcome, dict):
        return None, False
    root = cell_dir.resolve()
    workspace = str(outcome.get("workspace") or "")
    ranked: list[tuple[int, int, Path, bool]] = []
    for index, item in enumerate(outcome.get("artifacts") or ()):
        if isinstance(item, dict):
            raw = item.get("path") or item.get("artifact_ref") or ""
            verified = bool(item.get("verified"))
        else:
            raw, verified = item, False
        raw = str(raw or "")
        if not raw or Path(raw).name != "solution.py":
            continue
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = (Path(workspace) / candidate if workspace
                         else cell_dir / candidate)
        try:
            resolved = candidate.resolve()
            usable = resolved.is_file() and resolved.is_relative_to(root)
        except OSError:
            usable = False
        if usable:
            ranked.append((0 if verified else 1, index, resolved, verified))
    if not ranked:
        return None, False
    ranked.sort(key=lambda entry: entry[:2])
    _rank, _index, resolved, verified = ranked[0]
    return resolved, verified


def bridge_artifacts(cell_dir: Path, outcome: dict | None = None) -> dict:
    """Copy the solver's solution.py to the gate directory.

    The solver works in workspace/attempt-N/; the gate reads the cell
    root. The artifact named by the solve outcome is preferred, so the
    gate sees the attempt the engine accepted; without one, the newest
    attempt by modification time is used and the rule is recorded
    (bridged_rule, bridged_accepted) so the report shows which applied.
    Bridging is recorded, never fabricated: absent stays absent.
    """
    named, verified = _outcome_artifact(outcome, cell_dir)
    if named is not None:
        destination = cell_dir / "solution.py"
        if destination.resolve() != named:
            shutil.copyfile(named, destination)
        return {"bridged": True,
                "bridged_from": str(named.relative_to(cell_dir.resolve())),
                "bridged_rule": ("outcome_artifact" if verified
                                 else "outcome_artifact_unverified"),
                "bridged_accepted": verified}
    attempts = sorted((cell_dir / "workspace").glob("attempt-*/solution.py"),
                      key=lambda p: p.stat().st_mtime) if (
                          cell_dir / "workspace").is_dir() else []
    if not attempts:
        return {"bridged": False, "bridged_from": "",
                "bridged_rule": "none", "bridged_accepted": False}
    newest = attempts[-1]
    shutil.copyfile(newest, cell_dir / "solution.py")
    return {"bridged": True,
            "bridged_from": str(newest.relative_to(cell_dir)),
            "bridged_rule": "newest_by_mtime",
            "bridged_accepted": False}


def run_cell(task: str, arm: str, runs_dir: Path, args) -> dict:
    """Attempt one cell in isolation; every failure mode becomes a record."""
    cell = {"record_type": RECORD_TYPE, "task": task, "arm": arm,
            "status": "staged", "solve_rc": None, "solve_terminal": None,
            "solve_error": "", "gate_passed": None,
            "gate_score": None, "model_calls": None, "error": "",
            "elapsed_seconds": 0.0}
    import time
    started = time.monotonic()
    cell_dir = runs_dir / "cells" / f"{task}__{arm}"
    # Unix sockets cap at 108 bytes: the relay socket cannot live under the
    # deep cell dir. One short socket dir per cell, indexed to stay small.
    sock_dir = runs_dir / "socks" / f"{abs(hash((task, arm))) % 100000:05d}"
    if len(os.fsencode(str(sock_dir.resolve()))) + 40 >= 108:
        sock_dir = Path("/tmp") / "tcs" / f"{abs(hash((task, arm))) % 100000:05d}"
    try:
        sock_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    outcome: dict = {}
    try:
        cell.update(stage_cell(task, cell_dir))
        harness_json = ROOT / "embodiments" / arm / "harness.json"
        solve_cmd = [
            str(ROOT / ".venv" / "bin" / "python"), "-m", "loop_engine",
            "--solve", "--file", "task.txt", "--unattended", "--quickstart",
            "--settings-file", args.settings_file,
            "--compile-provider", args.provider,
            "--model-id", args.model_id, "--model-route", args.model_route,
            "--embodiment", arm, "--embodiment-config", str(harness_json),
            "--harness-socket-dir", str(sock_dir),
            "--verifier", "gate.sh",
            "--authorize-model-calls", "--max-model-calls",
            str(args.max_model_calls),
            "--workspace", "workspace", "--runs-dir", "runs",
            "--format", "json", "--quiet-model-io",
        ]
        try:
            solve_env = {"PATH": "/usr/bin:/bin",
                         "HOME": str(cell_dir / "home"),
                         "TACTICAL_API_KEY": os.environ.get(
                             "TACTICAL_API_KEY", "")}
            for key in ("LOOP_ENGINE_CALL_SPACING_SECS",
                        "LOOP_ENGINE_SLOT_DIR", "LOOP_ENGINE_SLOT_LOG"):
                if os.environ.get(key):
                    solve_env[key] = os.environ[key]
            proc = subprocess.run(
                solve_cmd, cwd=cell_dir, capture_output=True, text=True,
                timeout=args.cell_timeout, env=solve_env)
            cell["solve_rc"] = proc.returncode
            outcome = _scan_outcome(proc.stdout)
            (cell_dir / "solve.stdout.json").write_text(
                proc.stdout[-200000:], encoding="utf-8")
            (cell_dir / "solve.stderr.txt").write_text(
                proc.stderr[-200000:], encoding="utf-8")
            cell["solve_terminal"] = outcome.get("terminal_code")
            cell["model_calls"] = outcome.get("model_calls")
            cell["model_calls_from"] = outcome.get("model_calls_from", "")
            cell["solve_note"] = outcome.get("note", "")
            cell["solve_error"] = json.dumps(
                outcome.get("result"))[:300] if outcome else ""
        except subprocess.TimeoutExpired:
            cell["status"] = "solve_timeout"
            cell["error"] = (f"solve exceeded {args.cell_timeout}s; "
                             "partial artifacts retained")
        if cell["status"] == "staged":
            cell["status"] = ("solved"
                              if cell["solve_rc"] == 0 else "solve_failed")
        cell.update(bridge_artifacts(cell_dir, outcome))
        try:
            gate_env = {"PATH": (str(ROOT / ".venv" / "bin")
                                 + ":/usr/bin:/bin:/usr/local/bin"),
                        "HOME": str(cell_dir / "home"),
                        "VIRTUAL_ENV": str(ROOT / ".venv")}
            gate = subprocess.run(
                ["bash", "gate.sh"], cwd=cell_dir, capture_output=True,
                text=True, timeout=600.0, env=gate_env)
            tail = (gate.stdout + gate.stderr).strip().splitlines()
            cell["gate_output_tail"] = tail[-3:]
            cell["gate_passed"] = gate.returncode == 0
            for line in tail:
                if "holdout metric" in line:
                    try:
                        cell["gate_score"] = float(
                            line.split("=")[1].split()[0])
                    except (ValueError, IndexError):
                        pass
            cell["status"] = ("gate_passed" if gate.returncode == 0
                              else "gate_failed")
        except subprocess.TimeoutExpired:
            cell["status"] = "gate_timeout"
            cell["error"] = "gate.sh exceeded 600s"
        except OSError as exc:
            cell["status"] = "gate_error"
            cell["error"] = f"gate launch failed: {type(exc).__name__}"
    except Exception:
        cell["status"] = "cell_error"
        cell["error"] = traceback.format_exc(limit=5)[-1500:]
    finally:
        cell["elapsed_seconds"] = round(time.monotonic() - started, 1)
        try:
            (cell_dir / "cell.json").write_text(
                json.dumps(cell, indent=1) + "\n", encoding="utf-8")
        except OSError:
            pass
    return cell


def write_report(cells: list[dict], runs_dir: Path) -> dict:
    """Standardized campaign report, always written, failures retained."""
    fresh: list[dict] = []
    for cell in cells:
        disk = runs_dir / "cells" / f"{cell['task']}__{cell['arm']}" / "cell.json"
        try:
            fresh.append(json.loads(disk.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            fresh.append(cell)
    try:
        prior = json.loads((runs_dir / "report.json").read_text(
            encoding="utf-8")).get("cells", [])
    except (OSError, ValueError):
        prior = []
    merged = {(c["task"], c["arm"]): c for c in prior
              if isinstance(c, dict) and "task" in c and "arm" in c}
    for cell in fresh:
        merged[(cell["task"], cell["arm"])] = cell
    cells = [merged[key] for key in sorted(merged)]
    by_status: dict[str, int] = {}
    for cell in cells:
        by_status[cell.get("status", "?")] = by_status.get(
            cell.get("status", "?"), 0) + 1
    report = {
        "record_type": REPORT_TYPE,
        "created_at": datetime.datetime.now(
            datetime.timezone.utc).isoformat(timespec="seconds"),
        "cells_total": len(cells),
        "cells_attempted": sum(1 for c in cells
                               if c.get("status") not in ("staged",
                                                          "deferred")),
        "cells_deferred": sum(1 for c in cells
                              if c.get("status") == "deferred"),
        "gate_passed": sum(1 for c in cells
                           if c.get("status") == "gate_passed"),
        "by_status": by_status,
        "cells": cells,
        "limitations": [
            "gate.sh is each task's evaluator; floors are naive baselines.",
            "gate.sh is also the solver's mid-run verifier, so a gate pass "
            "is not an independent held-out result.",
            "Failures are retained with causes; absence of a gate pass is "
            "not proof the arm cannot solve the task.",
        ],
    }
    (runs_dir / "report.json").write_text(
        json.dumps(report, indent=1) + "\n", encoding="utf-8")
    lines = ["# Task campaign report", "",
             f"Created: {report['created_at']}",
             f"Cells: {report['gate_passed']}/{report['cells_total']} gates passed "
             f"({report['cells_attempted']} attempted, "
             f"{report['cells_deferred']} deferred)", "",
             "| task | arm | status | gate | score | model calls | secs | solve_terminal | error |",
             "|---|---|---|---|---|---|---|---|---|"]
    for cell in cells:
        lines.append(
            f"| {cell['task']} | {cell['arm']} | {cell['status']} | "
            f"{cell['gate_passed']} | {cell['gate_score']} | "
            f"{cell['model_calls']} | {cell['elapsed_seconds']} | "
            f"{cell.get('solve_terminal')} | "
            f"{((cell.get('solve_error') or cell['error']) or '')[:80]} |")
    lines += ["", "## Limitations", "",
              *[f"- {item}" for item in report["limitations"]], ""]
    (runs_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def endpoint_healthy(base_url: str, key_env: str, model: str,
                     timeout: float = 60.0,
                     insecure: bool = False) -> tuple[bool, str]:
    """One tiny probe: healthy only on a fast, successful completion.

    TLS is verified with the platform default context. insecure=True
    restores the old unverified probe (no hostname check, no certificate
    check) and prints a warning, because the key travels as a bearer token
    over that connection.
    """
    import time
    import urllib.request
    import ssl
    key = os.environ.get(key_env, "").strip()
    if not key:
        return False, f"no key in {key_env}"
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        print(json.dumps({
            "warning": "health probe TLS verification disabled "
                       "(--insecure-health-probe); the bearer key is sent "
                       "over an unverified connection",
            "url": base_url}), file=sys.stderr, flush=True)
    payload = json.dumps(
        {"model": model,
         "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
         "max_tokens": 8}).encode()
    started = time.monotonic()
    try:
        request = urllib.request.Request(
            base_url.rstrip("/") + "/chat/completions", data=payload,
            headers={"Authorization": "Bearer " + key,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(request, context=ctx,
                                    timeout=timeout) as response:
            json.loads(response.read().decode())
    except Exception as exc:
        return False, f"{type(exc).__name__}: {str(exc)[:120]}"
    elapsed = time.monotonic() - started
    if elapsed > timeout:
        return False, f"too slow: {elapsed:.0f}s"
    return True, f"ok in {elapsed:.1f}s" + (" (insecure TLS)" if insecure
                                            else "")


def deferred_record(cell: dict, reason: str) -> dict:
    return {"record_type": RECORD_TYPE, "task": cell["task"],
            "arm": cell["arm"], "status": "deferred",
            "solve_rc": None, "solve_terminal": None, "solve_error": "",
            "gate_passed": None, "gate_score": None, "model_calls": None,
            "error": reason, "elapsed_seconds": 0.0}


def run_campaign(cells: list[dict], runs_dir: Path, args) -> int:
    """Run every cell; a cell failure never aborts the batch."""
    if not args.settings_file or not args.provider or not args.model_id:
        print(json.dumps({"error": "live run needs --settings-file, "
                                   "--provider, and --model-id"}))
        return 2
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "socks").mkdir(parents=True, exist_ok=True)
    done: list[dict] = []
    jobs = max(1, int(getattr(args, "jobs", 1) or 1))
    health_gate = bool(getattr(args, "health_gate", False))
    spacing = max(0.0, float(getattr(args, "cell_spacing", 0.0) or 0.0))
    insecure = bool(getattr(args, "insecure_health_probe", False))
    if health_gate and jobs > 1:
        print(json.dumps({"warning": "health gate needs ordering; "
                                     "forcing --jobs 1"}))
        jobs = 1
    if health_gate and insecure:
        print(json.dumps({"warning": "--insecure-health-probe disables TLS "
                                     "certificate and hostname verification "
                                     "for every health probe"}), flush=True)

    def gated(cell: dict, attempt: str) -> dict | None:
        """None means run now; a record means deferred this pass."""
        if not health_gate:
            return None
        healthy, detail = endpoint_healthy(
            args.health_url, args.health_key_env, args.model_id,
            timeout=float(getattr(args, "health_timeout", 30.0) or 30.0),
            insecure=insecure)
        print(json.dumps({"health": healthy, "detail": detail,
                          "cell": f"{cell['task']}__{cell['arm']}",
                          "attempt": attempt}), flush=True)
        if healthy:
            return None
        return deferred_record(
            cell, f"endpoint unhealthy on {attempt} pass: {detail}")

    try:
        if jobs == 1:
            import time
            deferred: list[dict] = []
            queue = list(cells)
            for index, cell in enumerate(queue):
                if index and spacing:
                    time.sleep(spacing)
                record = gated(cell, "first")
                if record is not None:
                    deferred.append(cell)
                    done.append(record)
                    continue
                done.append(run_cell(cell["task"], cell["arm"], runs_dir,
                                    args))
                print(json.dumps({"cell": f"{cell['task']}__{cell['arm']}",
                                  "status": done[-1]["status"],
                                  "progress": f"{len(done)}/{len(cells)}"}),
                      flush=True)
            if deferred:
                print(json.dumps({"retrying_deferred": len(deferred)}),
                      flush=True)
                for cell in deferred:
                    record = gated(cell, "retry")
                    if record is not None:
                        continue  # stays deferred from the first pass
                    record = run_cell(cell["task"], cell["arm"], runs_dir,
                                      args)
                    for position, prior in enumerate(done):
                        if (prior["task"], prior["arm"]) == (
                                cell["task"], cell["arm"]):
                            done[position] = record
                    print(json.dumps(
                        {"cell": f"{cell['task']}__{cell['arm']}",
                         "status": record["status"], "retry": True}),
                        flush=True)
        else:
            import concurrent.futures
            import time
            with concurrent.futures.ThreadPoolExecutor(
                    max_workers=jobs) as pool:
                future_of = {}
                for index, cell in enumerate(cells):
                    if index and spacing:
                        time.sleep(spacing / jobs)
                    future_of[pool.submit(
                        run_cell, cell["task"], cell["arm"],
                        runs_dir, args)] = cell
                for future in concurrent.futures.as_completed(future_of):
                    try:
                        record = future.result()
                    except Exception:
                        cell = future_of[future]
                        record = {"record_type": RECORD_TYPE,
                                  "task": cell["task"], "arm": cell["arm"],
                                  "status": "cell_error",
                                  "error": traceback.format_exc(
                                      limit=5)[-1500:]}
                    done.append(record)
                    print(json.dumps({"cell": f"{record['task']}__{record['arm']}",
                                      "status": record["status"],
                                      "progress": f"{len(done)}/{len(cells)}"}),
                          flush=True)
            done.sort(key=lambda r: (r["task"], r["arm"]))
    finally:
        report = write_report(done, runs_dir)
        print(json.dumps({"report": str(runs_dir / "report.json"),
                          "gate_passed": report["gate_passed"],
                          "total": report["cells_total"],
                          "by_status": report["by_status"]}, indent=1))
    return 0
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--validate-all", action="store_true")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--arms", default="",
                        help="comma-separated harness arms (default: all configured)")
    parser.add_argument("--tasks", default="",
                        help="comma-separated task names (default: all valid)")
    parser.add_argument("--runs-dir", default="/tmp/task-campaign",
                        help="cell outputs land here, never in the database")
    parser.add_argument("--run", action="store_true",
                        help="attempt every cell: stage, solve, gate, record")
    parser.add_argument("--settings-file", default="",
                        help="YAML settings declaring the provider route")
    parser.add_argument("--provider", default="",
                        help="compile provider id for live solve")
    parser.add_argument("--model-id", default="",
                        help="exact model for live solve")
    parser.add_argument("--model-route", default="",
                        help="exact route for live solve")
    parser.add_argument("--max-model-calls", type=int, default=30)
    parser.add_argument("--cell-timeout", type=float, default=1800.0,
                        help="wall seconds per cell solve attempt")
    parser.add_argument("--jobs", type=int, default=1,
                        help="parallel cells (independent dirs, indexed sockets)")
    parser.add_argument("--cell-spacing", type=float, default=0.0,
                        help="seconds between cell starts (serial) or "
                             "stagger quantum (parallel)")
    parser.add_argument("--health-gate", action="store_true",
                        help="probe the endpoint before each cell; defer "
                             "cells while unhealthy, retry once at the end "
                             "(forces --jobs 1)")
    parser.add_argument("--health-url", default="https://ai.tacticalengineering.net:6969/v1",
                        help="base URL probed by --health-gate")
    parser.add_argument("--health-key-env", default="TACTICAL_API_KEY",
                        help="env var holding the probe credential")
    parser.add_argument("--health-timeout", type=float, default=30.0,
                        help="seconds per health probe (a blackholed endpoint "
                             "takes the full timeout)")
    parser.add_argument("--insecure-health-probe", action="store_true",
                        help="disable TLS certificate and hostname "
                             "verification for the health probe (the old "
                             "behavior); prints a warning")
    args = parser.parse_args(argv)

    if args.list:
        print(json.dumps(list_tasks(), indent=1))
        return 0
    if args.validate_all:
        results = [validate_task(item["task"]) for item in list_tasks()]
        bad = [r for r in results if not r["valid"]]
        print(json.dumps({"valid": len(results) - len(bad),
                          "invalid": len(bad), "failures": bad}, indent=1))
        return 1 if bad else 0
    valid = [item["task"] for item in list_tasks()
             if validate_task(item["task"])["valid"]]
    tasks = [t for t in (args.tasks.split(",") if args.tasks else valid) if t]
    unknown_tasks = set(args.tasks.split(",")) - set(valid) if args.tasks else set()
    if unknown_tasks:
        print(json.dumps({"error": "unknown or invalid tasks",
                          "tasks": sorted(unknown_tasks)}))
        return 2
    known_arms = configured_arms()
    arms = [a for a in (args.arms.split(",") if args.arms else known_arms) if a]
    unknown_arms = set(args.arms.split(",")) - set(known_arms) if args.arms else set()
    if unknown_arms:
        print(json.dumps({"error": "unknown arms (no harness.json)",
                          "arms": sorted(unknown_arms)}))
        return 2
    cells = matrix(tasks, arms)
    if args.matrix or args.dry_run:
        runs = Path(args.runs_dir)
        runs.mkdir(parents=True, exist_ok=True)
        (runs / "matrix.json").write_text(
            json.dumps(cells, indent=1) + "\n", encoding="utf-8")
        print(json.dumps({"cells": len(cells), "tasks": tasks, "arms": arms,
                          "matrix": str(runs / "matrix.json"),
                          "live": False,
                          "note": "dry run: no provider contacted, no solver launched"},
                         indent=1))
        return 0
    if args.run:
        return run_campaign(cells, Path(args.runs_dir), args)
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
