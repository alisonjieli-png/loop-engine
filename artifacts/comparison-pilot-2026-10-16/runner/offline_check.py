"""Plumbing check of the pilot sandbox with a scripted endpoint and no model call.

It runs the pinned OpenCode binary in the trial sandbox against
`offline_fake_model.py` through the counting proxy and the egress proxy, then
reports what the harness could see and reach: the home folder, the Python
environment, a refused outside host and a missing workstation path. Usage:

    python3 offline_check.py --work DIR --python-env DIR --extra-bin DIR --opencode PATH --output REPORT.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import egress_proxy  # noqa: E402
import harness  # noqa: E402
import meter  # noqa: E402
from offline_fake_model import FakeModel  # noqa: E402

PROBE_COMMAND = ("pwd; echo HOME=$HOME; ls -A; python -c 'import sys, pandas, sklearn; print(sys.version.split()[0])'; "
                 "test -e /home/username/.bashrc && echo workstation-home-visible || echo workstation-home-hidden; "
                 "curl -sS -m 10 -o /dev/null -w 'example.com %{http_code}\\n' https://example.com || true")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--extra-bin", type=Path, required=True)
    parser.add_argument("--opencode", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gemma4:31b")
    parser.add_argument("--baltor-entry", type=Path, help="published OpenCode connection entry (JSON with mcp.baltor)")
    parser.add_argument("--bootstrap", type=Path, help="published quickstart bootstrap script")
    parser.add_argument("--baltor-key-file", type=Path, help="private file holding the customer's Baltor key")
    args = parser.parse_args()
    work = args.work.resolve()
    if work.exists():
        raise SystemExit("use a new work folder")
    home = work / "home"
    project = home / "project"
    project.mkdir(parents=True)
    (project / "README.md").write_text("fixture project\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=project, check=True)
    fake = FakeModel([{"tool": "bash", "arguments": {"command": PROBE_COMMAND, "description": "Inspect the sandbox"}}],
                     work / "fake-requests")
    fake_port = fake.start()
    upstream = meter.Upstream(scheme="http", host="127.0.0.1", port=fake_port, base_path="/v1", key_variable=None)
    counter = meter.Meter(work / "ledger.jsonl", work / "transcripts", ceiling=10, upstream=upstream)
    meter_port = counter.start()
    proxy = egress_proxy.EgressProxy(work / "egress.jsonl", "offline-check", ["baltor.ai", "app.baltor.ai"])
    proxy_port = proxy.start()
    trial = "offline-check"
    counter.open_step(meter.StepContext(trial_id=trial, model=args.model, arm="fixture", family="offline",
                                        repetition=1, cap=5))
    entry = token = None
    setup = None
    if args.baltor_entry:
        entry = json.loads(args.baltor_entry.read_text(encoding="utf-8"))["mcp"]["baltor"]
        token = args.baltor_key_file.read_text(encoding="utf-8").strip()
    harness.write_config(home, harness.opencode_config(meter_port, trial, args.model, baltor_entry=entry))
    env = harness.sandbox_environment(proxy_port, args.python_env, args.extra_bin, baltor_token=token)
    if args.bootstrap:
        setup = harness.shell_in_sandbox(home, args.python_env, args.extra_bin, args.opencode, env,
                                         args.bootstrap.read_text(encoding="utf-8"), 300,
                                         work / "setup.out", work / "setup.err")
    result = harness.run(home, args.python_env, args.extra_bin, args.opencode, env,
                         "Run one shell command to inspect the project, then answer DONE.", "offline check", 300,
                         work / "events.jsonl", work / "stderr.txt")
    counter.close_step(trial)
    counter.stop()
    proxy.stop()
    fake.stop()
    events = [json.loads(line) for line in (work / "events.jsonl").read_text(encoding="utf-8").splitlines()
              if line.strip().startswith("{")]
    tool_outputs = []
    for event in events:
        part = event.get("part") or {}
        if part.get("type") == "tool":
            state = part.get("state") or {}
            tool_outputs.append({"tool": part.get("tool"), "status": state.get("status"),
                                 "output": (state.get("output") or "")[:2000]})
    requests = sorted((work / "fake-requests").glob("*-request.json"))
    offered_tools = []
    if requests:
        first = json.loads(requests[0].read_text(encoding="utf-8"))
        offered_tools = sorted(tool["function"]["name"] for tool in first.get("tools") or [])
    egress = [json.loads(line) for line in (work / "egress.jsonl").read_text(encoding="utf-8").splitlines()] \
        if (work / "egress.jsonl").exists() else []
    report = {"record_type": "comparison_pilot_offline_check/v1", "model_calls": 0,
              "arm_configuration": "baltor" if entry else "without_baltor", "setup_result": setup,
              "harness_result": {key: value for key, value in result.items() if key != "sandbox_argv_without_prompt"},
              "event_types": sorted({event.get("type", "?") for event in events}),
              "requests_to_fixture": len(requests), "offered_tools": offered_tools,
              "tool_outputs": tool_outputs, "egress": egress}
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("harness_result", "event_types", "requests_to_fixture",
                                                   "offered_tools")}, indent=1))


if __name__ == "__main__":
    main()
