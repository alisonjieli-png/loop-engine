#!/usr/bin/env python3
"""Run one task through composed OpenCode steps: orient, plan, implement, verify.

A failed verify does not retry. It composes an OBSERVATION step that has no
edit or write tool, so the only available move is to look at what actually
happened, and the observation is carried into the next implement attempt.
That is the difference this loop is built to demonstrate: the shape of the
next step changes after a failure, rather than the wording of the same one.

Verification is the project's own command, run in the workspace, and its
real exit code decides. No step is asked whether it succeeded.

The verify command is the one fixed timeout here: --step-timeout (default
600 seconds). Model steps take a share of --hours instead. Model calls are
bounded across the whole loop by --max-model-calls, one SharedCallCeiling
handed to every step's session, so the ceiling binds over the run rather
than restarting at zero on each step.

Usage:
    OLLAMA_API_KEY=... XDG_DATA_HOME=/some/fresh/dir \\
      python3 tools/opencode_loop.py --task "..." --workspace /tmp/run1 \\
        --verify "python3 -m pytest -q" [--model ollama-cloud/gemma4:31b]
        [--step-timeout 600] [--max-model-calls N] [--gate-env NAME]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from overnight import SharedCallCeiling, gate_environment  # noqa: E402
from loop_engine.core.opencode_step_composition import (   # noqa: E402
    compose_instance, default_catalogue, default_core, default_skill_library,
    dynamic_step_layer, observation_step_layer)
from loop_engine.core.opencode_step_session import (        # noqa: E402
    OpenCodeStepProfile, OpenCodeStepSession)
from loop_engine.core.night_budget import NightBudget       # noqa: E402

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

#: Seconds the verify command may take. Named so the documentation can say
#: it exists; it is a flag (--step-timeout) rather than a number in a call.
DEFAULT_STEP_TIMEOUT = 600.0


class _Authority:
    """The per-step form, kept for callers that pass their own authority.

    main() no longer uses it: a fresh one per step compares a ceiling with
    a counter that restarts at zero, so it bounds one step and never the
    run. A SharedCallCeiling from tools/overnight.py is what main() hands
    to every step instead.
    """

    def __init__(self, budget): self.max_model_calls = budget


class _Request:
    def __init__(self, prompt): self.prompt = prompt


def run_step(layer, workspace, model, schema, body, budget, authority=None):
    """Compose an instance for one step and run it.

    ``authority`` is what the session reads its ceiling from. A
    SharedCallCeiling is charged with the session's calls afterwards, so
    the next step sees less; absent, the per-step ``_Authority(4)`` of
    earlier versions is used.
    """
    instance = compose_instance(default_core(), layer, workspace)
    profile = OpenCodeStepProfile(
        model=model, workspace=workspace, timeout_seconds=budget.grant(),
        agent=instance.agent_name,
        additional_environment=("OLLAMA_API_KEY", "XDG_DATA_HOME"))
    session = OpenCodeStepSession(
        authority=authority if authority is not None else _Authority(4),
        profile=profile)
    prompt = f"{body}\n\nReturn one JSON object with keys: {schema}"
    try:
        text = session.invoke(_Request(prompt), None)
    finally:
        if hasattr(authority, "charge"):
            authority.charge(session, instance.agent_name)
    result = session.results[-1]
    try:
        return json.loads(text), result
    except ValueError:
        return {"_unparsed": text[:600]}, result


def verify(command, workspace, timeout: float = DEFAULT_STEP_TIMEOUT,
           environment=None):
    """Run the project's own gate. Its exit code is the verdict.

    ``timeout`` is --step-timeout. ``environment`` defaults to the
    allowlist from tools/overnight.py (PATH, HOME, LANG, TERM, TMPDIR), not
    the whole environment of whoever started the loop.
    """
    env = environment if environment is not None else gate_environment()
    try:
        done = subprocess.run(command, shell=True, cwd=str(workspace),
                              capture_output=True, text=True,
                              timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return False, (f"the verify command did not finish within "
                       f"{timeout:.0f}s (--step-timeout)")
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
    ap.add_argument("--hours", type=float, default=12.0,
                    help="wall-clock budget; steps take a share of what remains")
    ap.add_argument("--step-timeout", type=float, default=DEFAULT_STEP_TIMEOUT,
                    help="seconds the --verify command may take (default "
                         f"{DEFAULT_STEP_TIMEOUT:.0f}); model steps are not "
                         "bounded by this, they take a share of --hours")
    ap.add_argument("--max-model-calls", type=int, default=None,
                    help="model calls the whole loop may make across every "
                         "step (default: --step-model-calls times the planned "
                         "steps); 0 means no loop ceiling, only the per-step one")
    ap.add_argument("--step-model-calls", type=int, default=4,
                    help="model calls one step may make (default 4)")
    ap.add_argument("--gate-env", action="append", default=[], metavar="NAME",
                    help="admit one more environment variable into the verify "
                         "command; repeatable")
    ap.add_argument("--gate-inherit-env", action="store_true",
                    help="run the verify command with the whole environment, "
                         "as earlier versions did")
    args = ap.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    catalogue, library = default_catalogue(), default_skill_library()
    budget = NightBudget(hours=args.hours, expected_steps=6)
    transcript, carried = [], ""
    # orient, plan, one implement per attempt, one observe between attempts.
    planned = 2 + args.attempts + max(0, args.attempts - 1)
    total = (args.max_model_calls if args.max_model_calls is not None
             else args.step_model_calls * planned)
    ceiling = SharedCallCeiling(None if total <= 0 else total,
                                per_step=args.step_model_calls)
    environment = gate_environment(args.gate_env,
                                   inherit=args.gate_inherit_env)

    def spent(name) -> bool:
        """True, and said out loud, when the loop's call ceiling is used up."""
        if not ceiling.exhausted:
            return False
        print(f"\n── {name} not started: {ceiling.charged}/{ceiling.total} "
              "model calls spent (--max-model-calls)")
        transcript.append({"step": "ceiling", "before": name,
                           "charged": ceiling.charged, "total": ceiling.total})
        return True

    def finish(code: int) -> int:
        transcript.append({"model_calls": ceiling.to_dict()})
        (workspace / "loop-transcript.json").write_text(
            json.dumps(transcript, indent=2), encoding="utf-8")
        return code

    for name in ("orient", "plan"):
        if spent(name):
            break
        layer, provenance = dynamic_step_layer(
            catalogue.select(name), args.task, library)
        body = args.task + (f"\n\nPrevious step:\n{carried}" if carried else "")
        value, result = run_step(layer, workspace, args.model,
                                 SCHEMAS[name], body, budget, ceiling)
        carried = json.dumps(value)[:1200]
        transcript.append({"step": name, "skills": sorted(layer.skills),
                           "why": provenance, "value": value})
        print(f"\n── {name}   skills={sorted(layer.skills) or '[]'}  "
              f"in={result.input_tokens} out={result.output_tokens}")
        for key, item in value.items():
            print(f"     {key}: {str(item)[:130]}")

    observation = ""
    for attempt in range(1, args.attempts + 1):
        if spent(f"implement (attempt {attempt})"):
            break
        layer, _ = dynamic_step_layer(
            catalogue.select("implement"), args.task, library)
        body = (args.task + f"\n\nPlan:\n{carried}"
                + (f"\n\nObserved on the previous attempt:\n{observation}"
                   if observation else ""))
        value, result = run_step(layer, workspace, args.model,
                                 SCHEMAS["implement"], body, budget, ceiling)
        print(f"\n── implement (attempt {attempt})  "
              f"in={result.input_tokens} out={result.output_tokens}")
        for key, item in value.items():
            print(f"     {key}: {str(item)[:130]}")

        ok, output = verify(args.verify, workspace, timeout=args.step_timeout,
                            environment=environment)
        print(f"\n── verify: {'PASSED' if ok else 'FAILED'}   $ {args.verify}")
        print("     " + "\n     ".join(output.splitlines()[-6:]))
        transcript.append({"step": "implement", "attempt": attempt,
                           "value": value, "verify_passed": ok})
        if ok:
            print(f"\n  RESULT: verified after {attempt} attempt(s)")
            return finish(0)

        if attempt < args.attempts:
            if spent("observe"):
                break
            # The failure changes the SHAPE of the next step, not its wording.
            obs_layer = observation_step_layer("verify", output)
            obs_value, _ = run_step(obs_layer, workspace, args.model,
                                    OBSERVE_SCHEMA, args.task, budget, ceiling)
            observation = json.dumps(obs_value)[:1000]
            print(f"\n── observe (no edit tool)  "
                  f"skills={sorted(obs_layer.skills)}")
            for key, item in obs_value.items():
                print(f"     {key}: {str(item)[:170]}")
            transcript.append({"step": "observe", "value": obs_value})

    print(f"\n  RESULT: not verified after {args.attempts} attempt(s) — "
          "reporting the real failure rather than claiming success")
    return finish(1)


if __name__ == "__main__":
    raise SystemExit(main())
