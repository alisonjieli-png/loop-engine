"""Offline proof that a fresh harness instance loads only its step's material.

Roadmap S-6.42 asks for a recorded test that Codex, Claude Code, OpenCode and
Pi each start an independent instance holding only one step's files. This
tool makes the September 22 isolation test repeatable. For every fresh
instance recipe of the release catalogue it:

1. finds the installed program and records its exact version;
2. builds a new launch folder (an earlier run is never reused or deleted)
   with an empty home folder, the harness's own configuration folder, and the
   step folder as its own git root under a parent holding decoy instruction
   files;
3. starts the harness headless inside Bubblewrap with no network, the real
   home folder replaced by decoys at every global location the recipe names,
   and a loopback endpoint that records each request and answers no model;
4. assesses the requests with ``assess_observation``: every step marker the
   recipe claims must arrive and no decoy marker may;
5. runs two controls beside the recipe. With the step's instruction file
   missing, the launch must fail whenever the recipe claims that file;
   otherwise the whole check fails, because it could not have failed. With
   the user's home folder kept (decoys in HOME), the result is recorded to
   show whether the empty home rule matters for that harness at that version.

No model is called and no request leaves the machine. The result is the
record ``harness_fresh_instance_run/v1`` in ``result.json`` of the run folder.
A missing program or a missing Bubblewrap is recorded as not tested with its
dependency, never as a pass.

    PYTHONPATH=src python tools/check_harness_fresh_instances.py \
        [--recipe codex.fresh_instance] [--output-root DIRECTORY]
"""
from __future__ import annotations

import argparse
from dataclasses import replace
import datetime
import hashlib
import json
import os
from pathlib import Path
import pwd
import secrets
import shutil
import signal
import subprocess
import sys
import threading
import time

TOOL = Path(__file__).resolve()
ROOT = TOOL.parents[1]
BUBBLEWRAP = "/usr/bin/bwrap"
GIT = "/usr/bin/git"
PYTHON = "/usr/bin/python3"
#: The loopback port inside the sandbox's own network namespace.
ENDPOINT_PORT = 18080
ENDPOINT_ORIGIN = f"http://127.0.0.1:{ENDPOINT_PORT}"
#: The only programs a launch may find by search path.
SANDBOX_PATH = "/usr/bin:/bin"
#: The folder of a launch that the recipe uses as the harness's configuration.
CONFIGURATION_FOLDER = "configuration"
#: git reads no machine-wide configuration while it creates the step's root.
GIT_VARIABLES = {"PATH": SANDBOX_PATH, "GIT_CONFIG_NOSYSTEM": "1"}
PROBE_PROMPT = "Reply with the word ready."
#: A fixed, obviously fake credential: the endpoint records no header value.
PROBE_CREDENTIAL = "not-a-real-key"
LAUNCH_VARIANTS = ("recipe", "home_folder_kept", "instruction_file_missing")
BOUND_OUTPUT = 1024 * 1024

#: The protocol server every step declares, written into each launch folder.
PROTOCOL_SERVER = r'''import json, sys
log, marker = sys.argv[1], sys.argv[2]
def note(text):
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(text + "\n")
note("start " + marker)
tools = [{"name": "baltor_step_echo", "description": marker + " Echo one value for the step probe.",
          "inputSchema": {"type": "object", "properties": {"value": {"type": "string"}}}}]
for line in sys.stdin:
    try:
        message = json.loads(line)
    except ValueError:
        continue
    method = message.get("method", "")
    note("request " + method + " " + marker)
    if "id" not in message:
        continue
    if method == "initialize":
        version = (message.get("params") or {}).get("protocolVersion") or "2025-06-18"
        result = {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                  "serverInfo": {"name": "baltor-step-probe", "version": "1.0.0"}}
    elif method == "tools/list":
        result = {"tools": tools}
    elif method in ("resources/list", "prompts/list", "resources/templates/list"):
        result = {method.split("/")[0]: []} if method != "resources/templates/list" else {"resourceTemplates": []}
    elif method == "ping":
        result = {}
    elif method == "tools/call":
        result = {"content": [{"type": "text", "text": "ready"}]}
    else:
        reply = {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "not supported"}}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()
        continue
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": message["id"], "result": result}) + "\n")
    sys.stdout.flush()
'''


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "x", encoding="utf-8") as handle:
        handle.write(text)


def software_paths(executable: Path) -> list:
    """The installed program to mount read-only: its package folder when it
    lives inside ``node_modules``, else the program file itself."""
    resolved = executable.resolve()
    for folder in resolved.parents:
        if folder.parent.name == "node_modules" and not folder.name.startswith("@"):
            return [str(folder)]
        if folder.parent.name.startswith("@") and folder.parent.parent.name == "node_modules":
            return [str(folder)]
    return [str(resolved)]


def _sandbox(command, *, binds, software, decoys, tmp_folder, home):
    """Bubblewrap with no network, a read-only root and the home folder
    replaced by an empty folder holding only the planted decoys."""
    arguments = [BUBBLEWRAP, "--unshare-net", "--unshare-ipc", "--unshare-pid", "--unshare-uts",
                 "--die-with-parent", "--new-session", "--ro-bind", "/", "/", "--dev", "/dev",
                 "--proc", "/proc", "--tmpfs", home]
    for source, target in decoys:
        arguments += ["--ro-bind", source, target]
    for path in software:
        arguments += ["--ro-bind", path, path]
    for path in binds:
        arguments += ["--bind", path, path]
    arguments += ["--ro-bind", str(TOOL), str(TOOL), "--bind", str(tmp_folder), "/tmp"]
    return arguments + ["--", *command]


def _run_inner(job: dict, folder: Path, *, software, decoys, home) -> dict:
    job_path = folder / "job.json"
    _write(job_path, json.dumps(job, indent=1))
    command = _sandbox([PYTHON, str(TOOL), "--inner", str(job_path)],
                       binds=[str(folder)], software=software, decoys=decoys,
                       tmp_folder=folder / "tmp", home=home)
    outcome = subprocess.run(command, stdin=subprocess.DEVNULL, capture_output=True,
                             timeout=job["timeout"] + 60, env={"PATH": SANDBOX_PATH})
    result_path = Path(job["result"])
    if not result_path.is_file():
        return {"exit_code": None, "timed_out": False, "sandbox_exit": outcome.returncode,
                "sandbox_error": outcome.stderr.decode("utf-8", "replace")[-400:]}
    return json.loads(result_path.read_text(encoding="utf-8"))


def installed_version(recipe, executable: Path, folder: Path, software, home) -> dict:
    """Run the program's version command in the same sandbox and parse it."""
    import re
    folder.mkdir(parents=True)
    (folder / "tmp").mkdir()
    (folder / "empty-home").mkdir()
    job = {"command": [str(executable), *recipe.version_arguments],
           "variables": {"PATH": SANDBOX_PATH, "HOME": str(folder / "empty-home"),
                           "TERM": "dumb", "LANG": "C.UTF-8", "NO_COLOR": "1"},
           "cwd": str(folder), "port": ENDPOINT_PORT, "capture": str(folder / "capture"),
           "timeout": 60, "result": str(folder / "launch.json"), "stdout": str(folder / "stdout.txt")}
    outcome = _run_inner(job, folder, software=software, decoys=(), home=home)
    text = (folder / "stdout.txt").read_text(encoding="utf-8", errors="replace") if (
        folder / "stdout.txt").is_file() else ""
    for line in text.splitlines():
        match = re.match(recipe.version_pattern, line.strip())
        if match:
            return {"version": match.group(1), "exit_code": outcome.get("exit_code")}
    return {"version": None, "exit_code": outcome.get("exit_code"), "output": text[:200]}


def _markers(token: str) -> dict:
    return {"instruction_file": f"BALTOR-STEP-AGENTS-{token}", "skills": f"BALTOR-STEP-SKILL-{token}",
            "protocol_servers": f"BALTOR-STEP-MCP-{token}", "global": f"BALTOR-DECOY-GLOBAL-{token}",
            "parent": f"BALTOR-DECOY-PARENT-{token}"}


def launch(recipe, variant: str, folder: Path, executable: Path, software, *, timeout, home, version):
    """One offline launch of one recipe variant; returns the assessment."""
    from loop_engine.core.harness_fresh_instances import (
        FreshInstanceLayout, FreshInstanceObservation, assess_observation, configuration_files,
        decoy_files, render_launch, step_material_files)
    token = secrets.token_hex(6)
    marks = _markers(token)
    for name in ("empty-home", "decoy-home", "passwd-home", CONFIGURATION_FOLDER, "parent/step", "tmp",
                 "capture"):
        (folder / name).mkdir(parents=True)
    server, server_log = folder / "protocol_server.py", folder / "protocol-server.log"
    _write(server, PROTOCOL_SERVER)
    layout = FreshInstanceLayout(
        empty_home=str(folder / "empty-home"), configuration_folder=str(folder / CONFIGURATION_FOLDER),
        step_folder=str(folder / "parent/step"), step_parent=str(folder / "parent"),
        model_origin=ENDPOINT_ORIGIN, model_name="probe",
        model_credential=PROBE_CREDENTIAL, probe_prompt=PROBE_PROMPT,
        protocol_server_name="baltor_step",
        protocol_server_command=(PYTHON, str(server), str(server_log), marks["protocol_servers"]),
        model_context_capacity=32768, model_output_capacity=1024)
    decoy_server = (PYTHON, str(server), str(server_log), marks["global"])
    if variant == "home_folder_kept":
        layout = replace(layout, empty_home=str(folder / "decoy-home"))
    instructions = f"# Step instructions\n\n{marks['instruction_file']} Follow this step only.\n"
    for path, text in step_material_files(recipe, layout, instructions=instructions,
                                          skill_description=f"{marks['skills']} The step skill."):
        if variant == "instruction_file_missing" and text == instructions:
            continue
        _write(Path(path), text)
    for path, text in configuration_files(recipe, layout):
        _write(Path(path), text)
    for base in ("decoy-home", "passwd-home"):
        for path, text in decoy_files(recipe, str(folder / base), marks["global"], decoy_server):
            _write(Path(path), text)
    for name in ("AGENTS.md", "CLAUDE.md"):
        _write(folder / "parent" / name, f"# Parent instructions\n\n{marks['parent']}\n")
    subprocess.run([GIT, "init", "-q", layout.step_folder], check=True, capture_output=True,
                   env={**GIT_VARIABLES, "HOME": str(folder / CONFIGURATION_FOLDER)})
    arguments, environment = render_launch(recipe, layout)
    # The endpoint learns only whether a request carried the probe credential:
    # it compares digests of the two header forms and records whether one
    # matched. The job's variables do carry the fixed probe credential, which
    # is fake; a real credential must never be written to a job file.
    job = {"credential_sha256": [_sha256(("Bearer " + PROBE_CREDENTIAL).encode()),
                                 _sha256(PROBE_CREDENTIAL.encode())],
           "command": [str(executable), *arguments],
           "variables": {"PATH": SANDBOX_PATH, "TERM": "dumb", "LANG": "C.UTF-8",
                         "NO_COLOR": "1", **environment},
           "cwd": layout.step_folder, "port": ENDPOINT_PORT, "capture": str(folder / "capture"),
           "timeout": timeout, "result": str(folder / "launch.json"),
           "stdout": str(folder / "stdout.txt")}
    passwd_decoys = [(str(folder / "passwd-home" / location), f"{home}/{location}")
                     for location in recipe.global_locations]
    outcome = _run_inner(job, folder, software=software, decoys=passwd_decoys, home=home)
    bodies = [path.read_bytes() for path in sorted((folder / "capture").glob("request-*.body"))]
    delivered = any(json.loads(path.read_text(encoding="utf-8"))["credential_matches"]
                    for path in sorted((folder / "capture").glob("request-*.json")))
    events = tuple(line.strip() for line in server_log.read_text(encoding="utf-8").splitlines()
                   ) if server_log.is_file() else ()
    observation = FreshInstanceObservation(
        recipe.recipe_id, version, tuple(body.decode("utf-8", "replace") for body in bodies), events,
        outcome.get("exit_code"), bool(outcome.get("timed_out")),
        tuple((kind, marks[kind]) for kind in ("instruction_file", "skills", "protocol_servers")),
        (marks["global"], marks["parent"]))
    assessment = assess_observation(recipe, observation)
    written = sorted(str(path.relative_to(folder / "tmp")) for path in (folder / "tmp").rglob("*")
                     if path.is_file())
    assessment.update(variant=variant, request_count=len(bodies), credential_delivered=delivered,
                      request_sha256=[_sha256(body) for body in bodies],
                      request_bytes=[len(body) for body in bodies],
                      first_request_seconds=outcome.get("first_request_seconds"),
                      elapsed_seconds=outcome.get("elapsed_seconds"),
                      protocol_server_events=len(events),
                      tmp_files_written=written[:40], tmp_file_count=len(written))
    if "sandbox_error" in outcome:
        assessment["sandbox_error"] = outcome["sandbox_error"]
    return assessment


def check_recipe(recipe, run_folder: Path, *, executable=None, timeout=60) -> dict:
    base = {"recipe_id": recipe.recipe_id, "harness": recipe.harness, "candidate": recipe.candidate,
            "recipe_digest": recipe.digest, "pinned_version": recipe.pinned_version}
    if recipe.candidate:
        return {**base, "status": "not_tested", "reason": "candidate recipe: listed for study, no "
                "launch and no support claim until isolation, cancellation and native loading are tested"}
    found = executable or shutil.which(recipe.executable)
    if not found:
        return {**base, "status": "not_tested", "missing_optional_dependencies": [recipe.executable]}
    program = Path(found).resolve()
    software = software_paths(program)
    home = pwd.getpwuid(os.getuid()).pw_dir
    folder = run_folder / recipe.recipe_id
    version = installed_version(recipe, program, folder / "version", software, home)
    launches = {variant: launch(recipe, variant, folder / variant, program, software,
                                timeout=timeout, home=home, version=version["version"])
                for variant in LAUNCH_VARIANTS}
    controls = {variant: not launches[variant]["passed"] for variant in LAUNCH_VARIANTS[1:]}
    # A check that cannot fail proves nothing: when the recipe claims the step's
    # instruction file, the launch without that file must fail. The kept home
    # folder is recorded, not required to fail: a recipe that takes the step's
    # files through explicit flags, or reads user files only from its own
    # configuration folder, adds nothing from a kept home folder (Pi and Claude
    # Code at their pinned versions), while Codex and OpenCode read its skills.
    claims_instructions = dict(recipe.material)["instruction_file"] == "loaded"
    unfailing = claims_instructions and not controls["instruction_file_missing"]
    result = {**base, "status": "passed" if launches["recipe"]["passed"] and not unfailing else "failed",
              "executable": str(program), "installed_version": version["version"],
              "version_matches_pin": version["version"] == recipe.pinned_version,
              "rung": launches["recipe"]["rung"], "launches": launches,
              "controls_failed_as_expected": controls}
    if unfailing:
        result["reason"] = ("the launch without the step's instruction file passed, "
                            "so this check could not fail")
    return result


def run(recipe_ids=(), *, output_root: Path, catalog=None, executables=None, timeout=60) -> dict:
    from loop_engine.core.harness_recipes import release_recipe_catalog
    catalog = catalog or release_recipe_catalog()
    recipes = [item for item in catalog.fresh_instance_recipes
               if not recipe_ids or item.recipe_id in recipe_ids]
    started = _now()
    folder = output_root / ("harness-fresh-instances-" + datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(3))
    folder.mkdir(parents=True)
    ready = Path(BUBBLEWRAP).is_file() and Path(GIT).is_file() and Path(PYTHON).is_file()
    results = []
    for recipe in recipes:
        if not ready and not recipe.candidate:
            missing = [name for name, path in (("bubblewrap", BUBBLEWRAP), ("git", GIT), ("python3", PYTHON))
                       if not Path(path).is_file()]
            results.append({"recipe_id": recipe.recipe_id, "harness": recipe.harness,
                            "candidate": False, "status": "not_tested",
                            "missing_optional_dependencies": missing})
            continue
        results.append(check_recipe(recipe, folder, executable=(executables or {}).get(recipe.recipe_id),
                                    timeout=timeout))
    from loop_engine.core.harness_fresh_instances import FRESH_INSTANCE_RUN_RECORD_TYPE
    record = {"record_type": FRESH_INSTANCE_RUN_RECORD_TYPE, "started_at": started, "finished_at": _now(),
              "tool_sha256": _sha256(TOOL.read_bytes()), "catalogue_digest": catalog.digest,
              "sandbox": {"launcher": "bubblewrap", "network": "unshared",
                          "home_folder": "replaced by decoys at every recipe global location",
                          "tmp": "one folder per launch", "root": "read only"},
              "model_calls": 0, "results": results,
              "summary": {status: sum(1 for item in results if item["status"] == status)
                          for status in ("passed", "failed", "not_tested")}}
    _write(folder / "result.json", json.dumps(record, indent=1, sort_keys=True))
    record["result_path"] = str(folder / "result.json")
    return record


def _inner(job_path: str) -> int:
    """Inside the sandbox: serve the loopback endpoint and run one command."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    job = json.loads(Path(job_path).read_text(encoding="utf-8"))
    capture = Path(job["capture"])
    capture.mkdir(exist_ok=True)
    expected = set(job.get("credential_sha256", ()))
    started = time.monotonic()
    state = {"count": 0, "first": None}
    lock = threading.Lock()

    class Endpoint(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _record(self, body: bytes):
            with lock:
                state["count"] += 1
                number = state["count"]
                if state["first"] is None:
                    state["first"] = round(time.monotonic() - started, 3)
            (capture / f"request-{number:03d}.body").write_bytes(body)
            presented = (self.headers.get("Authorization"), self.headers.get("x-api-key"))
            (capture / f"request-{number:03d}.json").write_text(json.dumps({
                "method": self.command, "path": self.path, "bytes": len(body),
                "header_names": sorted(self.headers.keys()),
                "credential_matches": any(value and _sha256(value.encode()) in expected
                                          for value in presented)}), encoding="utf-8")

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            self._record(self.rfile.read(min(length, 16 * 1024 * 1024)))
            data = json.dumps({"error": {"type": "invalid_request_error",
                                         "message": "loopback endpoint: no model is behind it"}}).encode()
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            self._record(b"")
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = ThreadingHTTPServer(("127.0.0.1", job["port"]), Endpoint)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    timed_out = False
    with open(job["stdout"], "wb") as output:
        process = subprocess.Popen(job["command"], cwd=job["cwd"], env=job["variables"],
                                   stdin=subprocess.DEVNULL, stdout=output,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.wait(timeout=job["timeout"])
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
    server.shutdown()
    Path(job["result"]).write_text(json.dumps({
        "exit_code": None if timed_out else process.returncode, "timed_out": timed_out,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "first_request_seconds": state["first"]}), encoding="utf-8")
    if os.path.getsize(job["stdout"]) > BOUND_OUTPUT:
        with open(job["stdout"], "r+b") as output:
            output.truncate(BOUND_OUTPUT)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--inner", help=argparse.SUPPRESS)
    parser.add_argument("--recipe", action="append", default=[])
    parser.add_argument("--output-root", default=str(ROOT / ".loop-engine-dev" / "harness-fresh-instances"))
    parser.add_argument("--timeout", type=int, default=60)
    arguments = parser.parse_args(argv)
    if arguments.inner:
        return _inner(arguments.inner)
    record = run(tuple(arguments.recipe), output_root=Path(arguments.output_root),
                 timeout=arguments.timeout)
    for item in record["results"]:
        detail = item.get("rung") or item.get("reason") or item.get("missing_optional_dependencies")
        print(f"{item['recipe_id']:36s} {item['status']:11s} {detail}")
    print("result:", record["result_path"])
    return 1 if record["summary"]["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
