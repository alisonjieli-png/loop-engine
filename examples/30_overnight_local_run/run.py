"""Set up an overnight run on a local model, end to end, with no key.

Five sections, in the order the operator meets them:

  1. Will it fit?      the memory arithmetic for three machine tiers
  2. Does it answer?   one governed call over the real local adapter
  3. What may it do?   the night's written plan, screened before it starts
  4. It went quiet     what the night does when the server stops answering
  5. The morning       Run History saved, played back, graded, measured

No provider key is read and no socket is opened. Section 2 answers the
real adapter from a fixture transport, the same way the repository's own
custom endpoint checks do, so the wire format, the streaming contract, the
token accounting and the refusal classification are exercised rather than
described. What it does not do is prove that any particular server on any
particular machine answers, and the guide says so in the same words.

Run:
    python3 examples/30_overnight_local_run/run.py
"""
from __future__ import annotations

import argparse
import email.message
import io
import json
import os
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loop_engine import LoopLedger                                  # noqa: E402
from loop_engine.loop.recursive_loop import (Loop, LoopConfig,      # noqa: E402
                                             StepOutcome)
from loop_engine.loop.supervision_policy import SupervisionPolicy   # noqa: E402
from loop_engine.core import custom_endpoint as ce                  # noqa: E402
from loop_engine.core.custom_endpoint import CustomEndpoint, make_adapter  # noqa: E402
from loop_engine.core.model_capabilities import ModelOutputCapability      # noqa: E402
from loop_engine.core.model_routes import ModelRoute                # noqa: E402
from loop_engine.core.night_budget import NightBudget               # noqa: E402
from loop_engine.core.overnight_outcome import classify, summarise  # noqa: E402
from loop_engine.core.provider_failure_classes import decide        # noqa: E402
from loop_engine.core.run_history import RunHistory                 # noqa: E402
from loop_engine.code_nodes.run_playback import playback            # noqa: E402
from loop_engine.code_nodes.loop_report import (report_from_run,    # noqa: E402
                                                write_report)
from loop_engine.memory.working.state import WorkingMemoryState     # noqa: E402

import local_fit                                                    # noqa: E402
import overnight_plan                                               # noqa: E402
from local_fit import GIB, LocalModel, MachineTier, fit, largest_context

LINE = "-" * 72

# ---------------------------------------------------------------- section 1

#: Three machines, described by the memory a model may occupy on them.
#: These are the tiers the guide uses. They are definitions of a tier, not
#: measurements of any product: put your own machine's figures here.
TIERS = (
    MachineTier(
        name="laptop, 16 GiB unified memory",
        usable_video_bytes=11 * GIB, usable_system_bytes=11 * GIB,
        runtime_reserve_bytes=1.5 * GIB,
        note="one pool shared with the operating system and the display; "
             "about two thirds is what a model may take"),
    MachineTier(
        name="workstation, one 24 GiB graphics card",
        usable_video_bytes=23 * GIB, usable_system_bytes=64 * GIB,
        runtime_reserve_bytes=1.5 * GIB,
        note="weights and cache in video memory; system memory is the "
             "fallback that costs bus traffic on every token"),
    MachineTier(
        name="server, 128 GiB system memory and 8 GiB video memory",
        usable_video_bytes=7 * GIB, usable_system_bytes=120 * GIB,
        runtime_reserve_bytes=2 * GIB,
        note="almost everything loads and almost nothing is resident on the "
             "card, so most of each token crosses the bus"),
)

#: Model shapes are inputs, not claims. Read layers, key/value heads and the
#: head dimension from the model's own configuration file before you trust a
#: row of this table for a model you have not loaded.
MODELS = (
    LocalModel(name="8B at q4_0, 32k context", layers=32, key_value_heads=8,
               head_dimension=128, parameters=8e9, quantisation="q4_0",
               maximum_context_tokens=32768),
    LocalModel(name="14B at q4_0, 32k context", layers=48, key_value_heads=8,
               head_dimension=128, parameters=14e9, quantisation="q4_0",
               maximum_context_tokens=32768),
    LocalModel(name="32B at q4_0, 32k context", layers=64, key_value_heads=8,
               head_dimension=128, parameters=32e9, quantisation="q4_0",
               maximum_context_tokens=32768),
    LocalModel(name="70B at q4_0, 32k context", layers=80, key_value_heads=8,
               head_dimension=128, parameters=70e9, quantisation="q4_0",
               maximum_context_tokens=32768),
)


def section_one_fit() -> list[dict]:
    """Print the fit table the guide quotes, and return its rows."""
    print(LINE)
    print("1. WILL IT FIT")
    print(LINE)
    print("weights = parameters x bytes per weight (from the block layout)")
    print("cache   = 2 x layers x kv heads x head dim x tokens x element bytes")
    print("total   = weights + cache + the reserve you declare\n")
    rows = []
    for tier in TIERS:
        print(f"{tier.name}")
        print(f"  {tier.note}")
        header = (f"  {'model':<26}{'weights':>9}{'cache':>9}"
                  f"{'total':>9}  {'placement':<9} longest context")
        print(header)
        for model in MODELS:
            report = fit(tier, model, 8192)
            resident = largest_context(tier, model, placement="video")
            loadable = largest_context(tier, model, placement="split")
            longest = (f"{resident} in video memory" if resident
                       else (f"{loadable} split" if loadable else "does not load"))
            print(f"  {model.name:<26}{report['weights_gib']:>8.2f}G"
                  f"{report['kv_cache_gib']:>8.2f}G{report['total_gib']:>8.2f}G"
                  f"  {report['placement']:<9} {longest}")
            rows.append({**report, "longest_video_context": resident,
                         "longest_loadable_context": loadable})
        print()
    return rows


# ---------------------------------------------------------------- section 2

class _FixtureResponse:
    """A response object shaped like the one urllib returns."""

    def __init__(self, body=b"", lines=()):
        self._body, self._lines = body, list(lines)

    def read(self, limit=None):
        return self._body if limit is None else self._body[:limit]

    def __iter__(self):
        return iter(self._lines)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _FixtureOpener:
    """Answers each request from a script. The last entry repeats."""

    def __init__(self, script):
        self.script, self.requests = list(script), []

    def open(self, request, timeout=None):
        body = request.data
        self.requests.append({
            "url": request.full_url,
            "json": json.loads(body.decode()) if body else None})
        item = self.script.pop(0) if len(self.script) > 1 else self.script[0]
        if isinstance(item, BaseException):
            raise item
        return item


def _http_error(status, body=b"", headers=None):
    message = email.message.Message()
    for name, value in (headers or {}).items():
        message[name] = value
    return ce.urllib.error.HTTPError(
        "http://127.0.0.1:11434/api/chat", status, f"status {status}",
        message, io.BytesIO(body))


def _ndjson(*objects):
    return [json.dumps(item).encode() + b"\n" for item in objects]


def _through_fixture(endpoint, opener, prompt):
    """One adapter call answered by the fixture instead of a socket."""
    saved_opener, saved_slot = ce._endpoint_opener, ce._claim_call_slot
    ce._endpoint_opener = lambda _endpoint: opener
    ce._claim_call_slot = lambda _name: 0.0
    try:
        return make_adapter(endpoint).chat(
            prompt, max_tokens=0, temperature=0.0, timeout=30)
    finally:
        ce._endpoint_opener, ce._claim_call_slot = saved_opener, saved_slot


LOCAL_ENDPOINT = CustomEndpoint(
    name="local_ollama",
    base_url="http://127.0.0.1:11434",
    model="qwen3:8b",
    wire="ollama",
    locality="local",
    auth_scheme="none",
    stream="stream",
    think="model",
    counts_as_evidence=False,
    output_capability=ModelOutputCapability(
        32768, "local server configuration read by the operator"),
)


def section_two_answer() -> list[dict]:
    """One governed call over the real adapter, answered by a fixture."""
    print(LINE)
    print("2. DOES IT ANSWER")
    print(LINE)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed),
                       "detail": str(detail)[:200]})
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if detail:
            print(f"        {str(detail)[:150]}")

    described = LOCAL_ENDPOINT.describe()
    check("the_endpoint_record_never_carries_a_key",
          described.get("has_key") is False and "api_key" not in described,
          json.dumps({key: described[key] for key in sorted(described)
                      if key in ("name", "base_url", "model", "wire",
                                 "locality", "has_key", "auth_scheme")}))

    opener = _FixtureOpener([_FixtureResponse(lines=_ndjson(
        {"model": "qwen3:8b", "message": {"role": "assistant",
                                          "content": "ready"}, "done": False},
        {"model": "qwen3:8b", "message": {"role": "assistant", "content": ""},
         "done": True, "done_reason": "stop",
         "prompt_eval_count": 14, "eval_count": 1}))])
    answer = _through_fixture(LOCAL_ENDPOINT, opener, "reply with one word")
    sent = opener.requests[0]
    check("the_call_reaches_the_ollama_chat_path_on_the_declared_host",
          sent["url"] == "http://127.0.0.1:11434/api/chat", sent["url"])
    check("the_declared_output_maximum_is_requested_not_a_smaller_guess",
          sent["json"]["options"]["num_predict"] == 32768,
          f"num_predict={sent['json']['options']['num_predict']}")
    check("the_answer_arrives_with_provider_reported_token_counts",
          answer.ok and answer.text == "ready" and answer.prompt_tokens == 14
          and answer.eval_tokens == 1 and answer.done_reason == "stop",
          f"text={answer.text!r} in={answer.prompt_tokens} "
          f"out={answer.eval_tokens} reason={answer.done_reason}")

    cut = _FixtureOpener([_FixtureResponse(lines=_ndjson(
        {"model": "qwen3:8b", "message": {"role": "assistant",
                                          "content": "half an ans"},
         "done": False}))])
    truncated = _through_fixture(LOCAL_ENDPOINT, cut, "reply with one word")
    check("a_stream_that_stops_early_is_a_failure_not_a_short_answer",
          not truncated.ok and truncated.done is False,
          truncated.error)

    refused = _FixtureOpener([_http_error(
        503, b'{"error":"model is loading"}', {"Retry-After": "20"})])
    unavailable = _through_fixture(LOCAL_ENDPOINT, refused, "reply")
    check("a_refusal_carries_its_own_stated_wait",
          not unavailable.ok and unavailable.retry_after_seconds == 20.0,
          f"retry_after_seconds={unavailable.retry_after_seconds}")
    print()
    return checks


# ---------------------------------------------------------------- section 3

def section_three_plan(runs_dir: str, workspace: str) -> tuple[dict, list[dict]]:
    """Declare the night, screen it, and hand out the first time grant."""
    print(LINE)
    print("3. WHAT MAY IT DO")
    print(LINE)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed),
                       "detail": str(detail)[:200]})
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if detail:
            print(f"        {str(detail)[:150]}")

    authority = overnight_plan.DeclaredAuthority(
        authorize_model_calls=True, max_model_calls=400,
        allow_workspace_writes=True, allow_sandbox_commands=True,
        allow_local_counted_generation=True, spending_authority="none")
    wait = overnight_plan.DeclaredWait(
        outage_wait_seconds=60.0, allowance_wait_seconds=900.0,
        wait_attempt_ceiling=8)
    plan = overnight_plan.OvernightPlan(
        task_name="repair the failing import check",
        route_name="custom.local_ollama", night_hours=12.0, expected_steps=8,
        authority=authority, wait=wait, runs_dir=runs_dir,
        workspace_root=workspace,
        verifier_command="python -m pytest tests/test_imports.py -q",
        notes=("local weights, no spending authority, no network reads",))
    route = ModelRoute("custom.local_ollama", "local_ollama", "qwen3:8b",
                       "local", purposes=("counted_generation", "decide_label"))
    plan.screen(route)
    check("the_plan_names_its_route_and_passes_the_route_policy",
          plan.to_dict()["route_name"] == route.name, route.name)

    supervision = SupervisionPolicy(
        identical_failures_before_stop=3,
        non_progress_passes_before_escalation=3,
        unaccepted_passes_before_stop=9,
        non_accepted_iterations_before_stop=25)
    check("non_progress_is_a_declared_limit_not_an_attempt_count",
          supervision.escalation_ladder[-1] == "stop_unprofitable",
          "ladder: " + ", ".join(supervision.escalation_ladder))

    budget = NightBudget(hours=plan.night_hours,
                         expected_steps=plan.expected_steps)
    print(f"        {budget.explain('orient')}")
    late = NightBudget(hours=plan.night_hours,
                       expected_steps=plan.expected_steps)
    late.started = late.started - 11.0 * 3600
    print(f"        {late.explain('verify')}")
    check("a_time_grant_shrinks_as_the_night_runs_down",
          late.grant("verify") < budget.grant("orient"),
          f"{late.grant('verify') / 60:.0f} min against "
          f"{budget.grant('orient') / 60:.0f} min")

    for ending in plan.endings:
        codes = ", ".join(overnight_plan.ACCEPTED_ENDINGS[ending])
        print(f"        ending {ending}: {codes}")
    print()
    return plan.to_dict(), checks


# ---------------------------------------------------------------- section 4

def section_four_quiet() -> list[dict]:
    """What the night decides when the server stops answering."""
    print(LINE)
    print("4. IT WENT QUIET")
    print(LINE)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed),
                       "detail": str(detail)[:200]})
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if detail:
            print(f"        {str(detail)[:150]}")

    situations = (
        ("the server is restarting", ["provider_unavailable"],
         "wait_for_recovery"),
        ("the host is unreachable", ["network_unreachable", "timeout"],
         "wait_for_recovery"),
        ("a hosted allowance is spent", ["usage_limit_reached"],
         "wait_for_allowance"),
        ("the model name is wrong", ["model_not_found"], "stop_route"),
        ("the key is wrong, after an outage", ["timeout", "authentication_failed"],
         "stop_route"),
        ("the prompt is longer than the context", ["context_window_exceeded"],
         "fail_cell"),
    )
    for description, codes, expected in situations:
        result = decide(codes, attempts_so_far=0, attempt_ceiling=8)
        check(f"{description.replace(' ', '_')}_is_{expected}",
              result["decision"] == expected,
              f"{', '.join(codes)} -> {result['decision']}: {result['reason']}")

    exhausted = decide(["provider_unavailable"], attempts_so_far=8,
                       attempt_ceiling=8)
    check("a_wait_is_bounded_by_the_declared_ceiling_not_repeated_forever",
          exhausted["decision"] == "fail_cell", exhausted["reason"])
    print()
    return checks


# ---------------------------------------------------------------- section 5

def _record_the_night(runs_dir: str) -> str:
    """Run one small governed Loop and save its Run History."""
    ledger = LoopLedger()
    starting_loop = Loop(
        "repair the failing import check",
        LoopConfig(framework="custom",
                   custom_steps=("orient", "reproduce", "repair", "verify"),
                   allowable_modes=("deterministic",), power="standard"),
        ledger=ledger)

    def handler(loop, step, context):
        if loop.depth > 0:
            return StepOutcome(f"{step}: the spawned check agreed")
        if step == "reproduce" and "reproduce:spawned" not in context:
            return StepOutcome("confirm the failure on a clean tree",
                               spawn_goal="confirm the failure on a clean tree")
        if step == "repair":
            return StepOutcome("moved the import into the function body")
        if step == "verify":
            return StepOutcome("verify: the project gate exits zero")
        return StepOutcome(f"{step}: complete")

    starting_loop.run(handler=handler, max_steps=20)
    run_id = (time.strftime("overnight-%Y%m%d-%H%M%S-")
              + f"{time.time_ns() % 1_000_000_000:09d}")
    history = RunHistory.from_ledger(ledger.events, run_id=run_id)
    history.commit()
    history.save(runs_dir)
    return run_id


def _directory_bytes(path: str) -> int:
    total = 0
    for root, _folders, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def section_five_morning(runs_dir: str) -> tuple[list[dict], dict]:
    """Save, play back, grade, and measure what the night left on disk."""
    print(LINE)
    print("5. THE MORNING")
    print(LINE)
    checks = []

    def check(name, passed, detail=""):
        checks.append({"check": name, "passed": bool(passed),
                       "detail": str(detail)[:200]})
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
        if detail:
            print(f"        {str(detail)[:150]}")

    run_id = _record_the_night(runs_dir)
    history = RunHistory.load(runs_dir, run_id)
    chain = history.verify_chain()
    check("the_saved_run_history_verifies_without_rerunning_the_work",
          chain["intact"], f"{chain['events']} events, chain intact={chain['intact']}")

    lines = list(playback(history.event_log))
    print(f"        playback of {run_id}:")
    for line in lines[:6]:
        print(f"          {line}")
    if len(lines) > 6:
        print(f"          ... {len(lines) - 6} more lines")
    check("playback_reads_the_saved_run_rather_than_repeating_it",
          len(lines) > 0, f"{len(lines)} playback lines")

    report_path = os.path.join(runs_dir, run_id, "report.html")
    write_report(report_from_run(runs_dir, run_id), report_path)
    check("a_static_report_is_written_beside_the_run",
          os.path.exists(report_path), report_path)

    verified = classify(gate_passed=True, state={"files_changed":
                                                 ["src/package/module.py"]})
    test_only = classify(gate_passed=True, state={"files_changed":
                                                  ["tests/test_imports.py"]})
    localised = classify(gate_passed=False, state={
        "reproduction": "the import fails on a clean tree",
        "hypothesis": "a circular import through the settings module",
        "files_examined": ["src/package/settings.py", "src/package/module.py"]})
    undiagnosed = classify(gate_passed=False, state={
        "reproduction": "the import fails on a clean tree"})
    check("a_green_gate_on_source_is_graded_verified",
          verified.rung == "verified", verified.because)
    check("a_green_gate_reached_by_editing_only_tests_is_graded_apart",
          test_only.rung == "verified_by_test_change", test_only.because)
    check("a_red_gate_with_a_reproduction_and_a_named_cause_is_a_useful_morning",
          localised.rung == "cause_localised" and localised.actionable,
          f"{localised.rung}: {localised.because}")
    check("the_same_night_without_a_named_cause_is_not_promoted_to_useful",
          undiagnosed.rung == "narrowed" and not undiagnosed.actionable,
          f"{undiagnosed.rung}: {undiagnosed.because}")
    print("        " + summarise(
        [verified, test_only, localised, undiagnosed])["headline"])

    working = WorkingMemoryState(run_id=run_id, loop_id="loop-a")
    working.put("task_envelope", "goal", "repair the failing import check")
    working.put("private_scratch", "hypothesis", "a circular import")
    check("runtime_memory_holds_no_path_and_writes_no_file",
          not any(isinstance(getattr(working, name, None), str)
                  and os.path.sep in getattr(working, name)
                  for name in ("run_id", "loop_id")),
          "WorkingMemoryState is process state; nothing on disk survives it")

    saved_bytes = _directory_bytes(os.path.join(runs_dir, run_id))
    measured = {
        "record_type": "overnight_disk_measurement/v1",
        "run_id": run_id,
        "run_history_bytes": saved_bytes,
        "run_history_events": chain["events"],
        "bytes_per_event": round(saved_bytes / max(1, chain["events"]), 1),
        "note": ("measured on this run in this example; a night that calls a "
                 "model saves a far larger event log and its artifact folder "
                 "beside it"),
    }
    print(f"        Run History on disk: {saved_bytes} bytes for "
          f"{chain['events']} events "
          f"({measured['bytes_per_event']} bytes an event)")
    print("        Runtime Memory on disk: 0 bytes, because it is not stored")
    print()
    return checks, measured


# ---------------------------------------------------------------- assembly

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", default="",
                        help="keep the run history and report here instead of "
                             "a temporary folder")
    parser.add_argument("--json", action="store_true",
                        help="print the machine readable record as well")
    args = parser.parse_args()

    holder = None
    if args.output_root:
        root = os.path.abspath(args.output_root)
        os.makedirs(root, exist_ok=True)
    else:
        holder = tempfile.TemporaryDirectory(prefix="loop-engine-overnight-")
        root = holder.name
    runs_dir = os.path.join(root, "runs")
    workspace = os.path.join(root, "workspace")
    os.makedirs(runs_dir, exist_ok=True)
    os.makedirs(workspace, exist_ok=True)

    try:
        print("OVERNIGHT LOCAL RUN: SETUP, START TO MORNING")
        print("no provider key is read, no socket is opened\n")
        fit_rows = section_one_fit()
        checks = section_two_answer()
        plan_record, plan_checks = section_three_plan(runs_dir, workspace)
        checks += plan_checks
        checks += section_four_quiet()
        morning_checks, measured = section_five_morning(runs_dir)
        checks += morning_checks

        print(LINE)
        print("GUARD CHECKS: each one names the known wrong input it refuses")
        print(LINE)
        guards = local_fit.self_check() + overnight_plan.self_check()
        for row in guards:
            print(f"  {'PASS' if row['passed'] else 'FAIL'}  {row['check']}")
            if row["detail"]:
                print(f"        {row['detail'][:150]}")
        checks += guards

        failed = [row["check"] for row in checks if not row["passed"]]
        print()
        print(LINE)
        print(f"{len(checks) - len(failed)} of {len(checks)} checks passed")
        if failed:
            print("FAILED: " + ", ".join(failed))
        print(LINE)
        if args.json:
            print(json.dumps({
                "record_type": "overnight_local_example/v1",
                "fit": fit_rows, "plan": plan_record,
                "disk": measured,
                "checks": checks}, indent=1))
        if args.output_root:
            print(f"\nKept under {root}")
            print(f"  loop-engine studio --runs-dir {runs_dir} --port 0")
        return 1 if failed else 0
    finally:
        if holder is not None:
            holder.cleanup()


if __name__ == "__main__":
    raise SystemExit(main())
