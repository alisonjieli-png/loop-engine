#!/usr/bin/env python3
"""Run one task through composed OpenCode steps: orient, plan, implement, verify.

A failed verify does not retry. It composes an OBSERVATION step that has no
edit or write tool, so the only available move is to look at what actually
happened, and the observation is carried into the next implement attempt.
That is the difference this loop is built to demonstrate: the shape of the
next step changes after a failure, rather than the wording of the same one.

Verification is the project's own command, run in the workspace, and its
real exit code decides. No step is asked whether it succeeded.

Usage:
    OLLAMA_API_KEY=... XDG_DATA_HOME=/some/fresh/dir \\
      python3 tools/opencode_loop.py --task "..." --workspace /tmp/run1 \\
        --verify "python3 -m pytest -q" [--model ollama-cloud/gemma4:31b]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from loop_engine.core.opencode_step_composition import (   # noqa: E402
    compose_instance, default_catalogue, default_core, default_skill_library,
    dynamic_step_layer, observation_step_layer)
from loop_engine.core.opencode_step_session import (        # noqa: E402
    OpenCodeStepProfile, OpenCodeStepSession)

SCHEMAS = {
    "orient": ('{"task_summary": string, "immediate_goal": string, '
               '"unknowns": [string], "proposed_next_action": string}'),
    "plan": ('{"steps": [string], "first_step": string, '
             '"how_first_step_is_checked": string}'),
    "implement": ('{"files_written": [string], "what_changed": string, '
                  '"ready_to_verify": boolean}'),
}
OBSERVE_SCHEMA = ('{"command_run": string, "output_observed": string, '
                  '"contradiction": string}')


class _Authority:
    def __init__(self, budget): self.max_model_calls = budget


class _Request:
    def __init__(self, prompt): self.prompt = prompt


def run_step(layer, workspace, model, schema, body, budget):
    """Compose an instance for one step and run it."""
    instance = compose_instance(default_core(), layer, workspace)
    profile = OpenCodeStepProfile(
        model=model, workspace=workspace, timeout_seconds=420.0,
        agent=instance.agent_name,
        additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
    session = OpenCodeStepSession(
        authority=_Authority(budget), profile=profile)
    prompt = f"{body}\n\nReturn one JSON object with keys: {schema}"
    text = session.invoke(_Request(prompt), None)
    result = session.results[-1]
    try:
        return json.loads(text), result
    except ValueError:
        return {"_unparsed": text[:600]}, result


def verify(command, workspace):
    """Run the project's own gate. Its exit code is the verdict."""
    done = subprocess.run(command, shell=True, cwd=str(workspace),
                          capture_output=True, text=True, timeout=600)
    output = (done.stdout + done.stderr).strip()
    return done.returncode == 0, output


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--verify", required=True,
                    help="the project's own command; its exit code decides")
    ap.add_argument("--model", default="ollama-cloud/gemma4:31b")
    ap.add_argument("--attempts", type=int, default=2)
    args = ap.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    catalogue, library = default_catalogue(), default_skill_library()
    transcript, carried = [], ""

    for name in ("orient", "plan"):
        layer, provenance = dynamic_step_layer(
            catalogue.select(name), args.task, library)
        body = args.task + (f"\n\nPrevious step:\n{carried}" if carried else "")
        value, result = run_step(layer, workspace, args.model,
                                 SCHEMAS[name], body, 2)
        carried = json.dumps(value)[:1200]
        transcript.append({"step": name, "skills": sorted(layer.skills),
                           "why": provenance, "value": value})
        print(f"\n── {name}   skills={sorted(layer.skills) or '[]'}  "
              f"in={result.input_tokens} out={result.output_tokens}")
        for key, item in value.items():
            print(f"     {key}: {str(item)[:130]}")

    observation = ""
    for attempt in range(1, args.attempts + 1):
        layer, _ = dynamic_step_layer(
            catalogue.select("implement"), args.task, library)
        body = (args.task + f"\n\nPlan:\n{carried}"
                + (f"\n\nObserved on the previous attempt:\n{observation}"
                   if observation else ""))
        value, result = run_step(layer, workspace, args.model,
                                 SCHEMAS["implement"], body, 3)
        print(f"\n── implement (attempt {attempt})  "
              f"in={result.input_tokens} out={result.output_tokens}")
        for key, item in value.items():
            print(f"     {key}: {str(item)[:130]}")

        ok, output = verify(args.verify, workspace)
        print(f"\n── verify: {'PASSED' if ok else 'FAILED'}   $ {args.verify}")
        print("     " + "\n     ".join(output.splitlines()[-6:]))
        transcript.append({"step": "implement", "attempt": attempt,
                           "value": value, "verify_passed": ok})
        if ok:
            print(f"\n  RESULT: verified after {attempt} attempt(s)")
            (workspace / "loop-transcript.json").write_text(
                json.dumps(transcript, indent=2), encoding="utf-8")
            return 0

        if attempt < args.attempts:
            # The failure changes the SHAPE of the next step, not its wording.
            obs_layer = observation_step_layer("verify", output)
            obs_value, _ = run_step(obs_layer, workspace, args.model,
                                    OBSERVE_SCHEMA, args.task, 2)
            observation = json.dumps(obs_value)[:1000]
            print(f"\n── observe (no edit tool)  "
                  f"skills={sorted(obs_layer.skills)}")
            for key, item in obs_value.items():
                print(f"     {key}: {str(item)[:170]}")
            transcript.append({"step": "observe", "value": obs_value})

    print(f"\n  RESULT: not verified after {args.attempts} attempt(s) — "
          "reporting the real failure rather than claiming success")
    (workspace / "loop-transcript.json").write_text(
        json.dumps(transcript, indent=2), encoding="utf-8")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
