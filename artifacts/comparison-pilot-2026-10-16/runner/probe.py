"""The declared model probe: one tiny tool task before the first trial, outside the comparison.

It checks that the frozen model route makes structured tool calls through the
pinned OpenCode in the trial sandbox. It uses the without-Baltor configuration,
a scratch project unrelated to the three tasks, at most four physical requests,
and the same counting proxy and ledger as the pilot, so its requests count
against the pilot ceiling. Usage:

    python3 probe.py --work DIR --python-env DIR --extra-bin DIR --model MODEL --output probe.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import egress_proxy  # noqa: E402
import harness  # noqa: E402
import meter  # noqa: E402
from run_pilot import check_freeze, read_events, summarize_events  # noqa: E402

PROMPT = "Create a file named answer.txt in the project folder that contains only the number 42, using a tool. Then reply DONE."
CAP = 4


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--python-env", type=Path, required=True)
    parser.add_argument("--extra-bin", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    check_freeze()
    design = json.loads((HERE.parent / "design" / "design.json").read_text(encoding="utf-8"))
    route = design["model_route"]
    work = args.work.resolve()
    folder = work / f"probe-{args.model.replace(':', '-')}"
    if folder.exists():
        raise SystemExit("this probe already ran; inspect its folder")
    home = folder / "home"
    (home / "project").mkdir(parents=True)
    (home / "project" / "README.md").write_text("scratch project for the model probe\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=home / "project", check=True)
    upstream = meter.Upstream(scheme="https", host=route["host"], port=443, base_path=route["base_path"],
                              key_variable=route["key_variable"])
    counter = meter.Meter(work / "ledger.jsonl", work / "transcripts",
                          ceiling=design["budgets"]["pilot_ceiling_physical_requests"], upstream=upstream)
    port = counter.start()
    proxy = egress_proxy.EgressProxy(folder / "egress.jsonl", "probe", design["network"]["allowed_hosts"])
    proxy_port = proxy.start()
    step = "probe-" + args.model.replace(":", "-")
    context = meter.StepContext(trial_id=step, model=args.model, arm="probe", family="probe", repetition=1, cap=CAP)
    counter.open_step(context)
    harness.write_config(home, harness.opencode_config(port, step, args.model))
    env = harness.sandbox_environment(proxy_port, args.python_env, args.extra_bin)
    result = harness.run(home, args.python_env, args.extra_bin, Path(design["harness"]["binary_path"]), env, PROMPT,
                         "probe", 300, folder / "events.jsonl", folder / "stderr.txt",
                         should_stop=lambda: "request_cap_reached" if context.refused else None)
    counter.close_step(step)
    counter.stop()
    proxy.stop()
    rows = [json.loads(line) for line in (work / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if line]
    mine = [row for row in rows if row.get("trial_id") == step]
    answer = home / "project" / "answer.txt"
    events = summarize_events(read_events(folder / "events.jsonl"))
    report = {"record_type": "comparison_pilot_model_probe/v1", "model": args.model, "cap": CAP,
              "physical_requests": sum(1 for row in mine if row.get("event") == "sent"),
              "requests": [{key: row.get(key) for key in ("sequence", "http_status", "outcome", "finish_reason",
                                                         "tool_calls", "usage", "elapsed_ms")}
                           for row in mine if row.get("event") == "completed"],
              "harness": {key: result[key] for key in ("exit_status", "elapsed_seconds", "timed_out",
                                                       "stopped_by_runner")},
              "tool_counts": events["tool_counts"], "final_text": events["final_text"][:300],
              "answer_file": answer.read_text(encoding="utf-8").strip() if answer.is_file() else None}
    report["passed"] = report["answer_file"] == "42" and bool(report["tool_counts"])
    args.output.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
