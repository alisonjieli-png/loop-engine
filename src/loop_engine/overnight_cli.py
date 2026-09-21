"""One command that starts a night on a local model and reads it back.

Four operations, and the first one is the one that saves a night:

    overnight check     ask the machine whether tonight can start at all
    overnight start     declare the authority and run, unattended
    overnight resume    continue an interrupted night without repeating an
                        effect that already happened
    overnight report    print the morning report of a saved night

``check`` never starts anything. ``start`` refuses to begin when ``check``
would refuse, so a night that cannot finish is stopped at the keyboard
rather than at two in the morning.

The model is reached through the engine's own custom endpoint adapter over
a real socket, with the output capacity read from the server's own model
information and named in the record. No credential is read, sent or
written, because a local server declares no authentication.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

MIB = 1024 ** 2
DEFAULT_BASE_URL = "http://127.0.0.1:11434"
DEFAULT_RESIDENCY_REASON = (
    "the weights load once for the night instead of once for each step; "
    "the record of September 21, 2026 measured one machine where the first "
    "call paid 87.28 seconds to load and the next two took 0.71 and 0.78 "
    "seconds")


def _capacity_from_server(readiness: dict):
    """The declared output capacity, with the exact source named."""
    from .core.model_capabilities import ModelOutputCapability

    for finding in readiness.get("findings", []):
        reported = (finding.get("observed") or {}).get("reported") or {}
        if reported.get("context_length"):
            return ModelOutputCapability(
                int(reported["context_length"]),
                "the local server's own model information at /api/show, "
                "field context_length",
                observed_at=time.strftime("%Y-%m-%d"))
    return None


def _endpoint(arguments, readiness: dict, residency_seconds: int):
    """The endpoint this night runs on, declared in full."""
    from .core.custom_endpoint import CustomEndpoint

    capability = _capacity_from_server(readiness)
    if capability is None:
        raise SystemExit(
            "the server reported no context length, so no output capacity "
            "can be declared; this night will not guess one")
    return CustomEndpoint(
        name="local_night", base_url=arguments.base_url, model=arguments.model,
        wire=arguments.wire, locality="local", auth_scheme="none",
        output_capability=capability, counts_as_evidence=False,
        residency_seconds=int(residency_seconds),
        context_tokens=int(arguments.context_tokens),
        timeout=float(arguments.hours) * 3600.0)


def _model_caller(endpoint, allocation=None):
    """One physical call per step, at the allowance the night declared.

    With no allocation the call asks for the full capacity the route
    declared, which is what the gateway requires of anyone who has not made
    an explicit decision. With one, the typed allocation itself is handed to
    the adapter, because a bare smaller number is refused by design.
    """
    from .core.custom_endpoint import make_adapter

    adapter = make_adapter(endpoint)

    def call(prompt, *, timeout, max_output_tokens=0):
        if not str(prompt).strip():
            prompt = "Reply with the object {\"patch\": {}} and nothing else."
        return adapter.chat(prompt, max_tokens=int(max_output_tokens),
                            temperature=0.2, timeout=float(timeout),
                            output_capability=allocation)
    return call


def _output_allocation(arguments, endpoint):
    """The typed decision that selects less than the declared capacity.

    Returns ``(allowance, allocation, record)``. With no
    ``--max-output-tokens`` the allowance is zero and the allocation is
    absent, meaning the full declared capacity, because an invented smaller
    default is exactly what the gateway's refusal exists to prevent.
    """
    from .core.model_capabilities import ModelOutputAllocation

    selected = int(arguments.max_output_tokens or 0)
    if selected < 1:
        return 0, None, {
            "record_type": "overnight_output_allocation/v1",
            "requested_tokens": "the route's full declared capacity",
            "capacity": endpoint.output_capability.maximum_output_tokens,
            "capacity_source": endpoint.output_capability.source,
            "reason": "no allowance was selected, so nothing smaller than "
                      "the capacity the server declared was requested"}
    allocation = ModelOutputAllocation(
        capability=endpoint.output_capability, provider_id="local_night",
        model_id=endpoint.model, route_name="custom.local_night",
        requested_tokens=selected,
        decision_ref="overnight-cli/--max-output-tokens",
        reason="an unattended step returns one small object, and a step "
               "that runs past its time grant is a night that does not "
               "finish; this is a ceiling, not a target")
    return selected, allocation, {
        "record_type": "overnight_output_allocation/v1",
        "requested_tokens": allocation.requested_tokens,
        "capacity": allocation.capability.maximum_output_tokens,
        "capacity_source": allocation.capability.source,
        "route_name": allocation.route_name,
        "decision_ref": allocation.decision_ref,
        "reason": allocation.reason}


def _gate_runner(seconds: float):
    """Run the declared gate script through the engine's own verifier."""
    from .core.verifier_execute import VerifierError, verifier_execute_operation

    class _Request:
        def __init__(self, path):
            self.verifier_path = path

    class _Services:
        def __init__(self, path):
            self.request = _Request(path)

    def run(path):
        try:
            return verifier_execute_operation(
                {"timeout_seconds": max(1.0, min(3600.0, seconds))},
                _Services(path))
        except VerifierError as error:
            return {"passed": False, "exit_code": None,
                    "output_tail": list(getattr(error, "output_tail", []))
                    or [str(error)[:200]]}
    return run


def _install_interruption_record(authority, task: str) -> tuple:
    """Name the reason in the working folder when the night is stopped.

    A catchable signal writes the engine's own run checkpoint beside the
    journal, so the morning has the reason as well as the effect record. A
    hard kill catches nothing by design, which is why the journal is
    flushed to the operating system on every entry rather than at the end.
    """
    from .core.run_checkpoint import RunCheckpoint, install_signal_checkpoint

    checkpoint = RunCheckpoint(
        run_id="overnight", workspace_base=authority.workspace_root,
        checkpoint_dir=authority.workspace_root, task=str(task))
    return install_signal_checkpoint(checkpoint)


def _readiness(arguments) -> dict:
    from .core.local_model_readiness import LocalModelRequest, check_readiness

    return check_readiness(LocalModelRequest(
        base_url=arguments.base_url, model=arguments.model,
        context_tokens=int(arguments.context_tokens),
        video_memory_bytes=int(arguments.video_memory_mib) * MIB))


def _authority(arguments, residency_seconds: int):
    from .code_nodes.overnight_authority import OvernightAuthority, ResidencyPolicy

    return OvernightAuthority(
        night_hours=float(arguments.hours),
        max_model_calls=int(arguments.max_model_calls),
        workspace_root=str(Path(arguments.workspace).expanduser().resolve()),
        residency=ResidencyPolicy(
            keep_resident_seconds=residency_seconds,
            reason=str(arguments.residency_reason)),
        read_roots=tuple(arguments.read_root or ()),
        write_roots=tuple(arguments.write_root or ()),
        gate_command=str(Path(arguments.gate).expanduser().resolve())
        if arguments.gate else "",
        outage_wait_seconds=float(arguments.outage_wait_seconds))


def _residency_seconds(arguments) -> int:
    """The declared residency, in seconds, defaulting to the whole night."""
    if arguments.keep_resident_seconds is not None:
        return int(arguments.keep_resident_seconds)
    return int(float(arguments.hours) * 3600.0)


def render_report(result: dict) -> str:
    """The morning report: what happened, in the order a person reads it."""
    state = result.get("state") or {}
    outcome = result.get("outcome") or {}
    lines = [
        "# Overnight run report",
        "",
        f"Task: {result.get('task', '')}",
        "",
        "## How it ended",
        "",
        f"- Ending: {result.get('ending', '')}",
        f"- Terminal code: {result.get('terminal_code', '')}",
        f"- Outcome: {outcome.get('rung', 'not graded')}"
        + (f" ({outcome.get('because', '')})" if outcome.get("because") else ""),
        f"- Independently verified: "
        + ("yes" if result.get("verified") else "no"),
        f"- Rounds: {result.get('rounds', 0)}",
        f"- Elapsed: {result.get('elapsed_seconds', 0)} s",
        "",
        "## What the server reported",
        "",
        f"- Physical model calls: {result.get('model_calls', 0)}",
        f"- Prompt tokens reported by the server: "
        f"{result.get('prompt_tokens_reported', 0)}",
        f"- Output tokens reported by the server: "
        f"{result.get('eval_tokens_reported', 0)}",
        f"- Calls where the server reported no usage: "
        f"{result.get('calls_with_no_usage_reported', 0)}",
        f"- Weights kept loaded for: "
        f"{(result.get('residency') or {}).get('keep_resident_seconds')} s "
        f"({(result.get('residency') or {}).get('reason', '')})",
        f"- Output allowance: "
        + str((result.get("output_allocation") or {}).get(
            "requested_tokens", "not recorded"))
        + " ("
        + str((result.get("output_allocation") or {}).get("reason", ""))
        + ")",
        "",
        "## What it tried",
        "",
    ]
    for item in result.get("tried", []):
        lines.append(f"- round {item['round']}, {item['step']}: "
                     f"{item['elapsed_seconds']} s, "
                     + ("answered" if item["ok"] else "failed"))
    lines += ["", "## What it rejected and why", ""]
    rejected = result.get("rejected") or []
    lines += ([f"- round {item['round']}, {item['step']}: {item['why']}"
               for item in rejected] or ["- nothing was rejected"])
    lines += ["", "## What it refused to do", ""]
    lines += ([f"- {item}" for item in result.get("refusals") or []]
              or ["- nothing was refused"])
    lines += ["", "## What it did about each failure", ""]
    for item in result.get("next_actions", []):
        lines.append(f"- {item['action']}: {item['detail']}")
    lines += ["", "## What it verified", ""]
    gates = result.get("gate_runs") or []
    declared_gate = str(result.get("gate_command") or "")
    if gates:
        lines += [f"- round {item['round']}: gate "
                  + ("passed" if item["passed"] else "failed")
                  + f" (exit {item.get('exit_code')})" for item in gates]
    elif declared_gate:
        lines.append(f"- the gate {declared_gate} was declared and never ran, "
                     "so nothing here independently verified the work")
    else:
        lines.append("- no gate was declared, so nothing here independently "
                     "verified the work")
    lines += ["", "## What remains provisional", ""]
    if result.get("verified"):
        lines.append("- nothing: the declared gate passed")
    else:
        lines.append("- every change below is provisional; the declared gate "
                     "did not pass")
    for name in ("hypothesis", "reproduction", "observed_failure",
                 "blocked_on"):
        if state.get(name):
            lines.append(f"- {name}: {state[name]}")
    for name in ("files_changed", "ruled_out", "unknowns"):
        for item in state.get(name) or []:
            lines.append(f"- {name}: {item}")
    lines += ["", "## Where the saved night is", "",
              f"- Working folder: {result.get('workspace_root', '')}",
              f"- Journal: {result.get('journal', '')}",
              f"- Report: {result.get('workspace_root', '')}/report.md", ""]
    return "\n".join(lines)


def _save(result: dict) -> None:
    folder = Path(result.get("workspace_root", ""))
    try:
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "report.json").write_text(
            json.dumps(result, indent=1, sort_keys=True), encoding="utf-8")
        (folder / "report.md").write_text(render_report(result),
                                          encoding="utf-8")
    except OSError:
        pass


def _print_readiness(readiness: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(readiness, indent=1, sort_keys=True))
        return
    print(readiness["sentence"])
    for finding in readiness["findings"]:
        mark = {"passed": "ok", "refused": "no", "unknown": "??"}[
            finding["state"]]
        print(f"  [{mark}] {finding['check']}")
        print(f"       {finding['sentence']}")


def _run_night(arguments, resuming: bool) -> int:
    from .code_nodes.overnight_journal import OvernightJournal
    from .code_nodes.overnight_night import NightRunners, run_night
    from .core.step_state import StepState

    readiness = _readiness(arguments)
    if not readiness["ready"]:
        _print_readiness(readiness, arguments.json)
        print("\nrefused: this night was not started.")
        return 2
    residency = _residency_seconds(arguments)
    authority = _authority(arguments, residency)
    journal = OvernightJournal(authority.workspace_root)
    state = None
    if resuming:
        plan = journal.resume_plan()
        print(plan["sentence"])
        if not plan["can_resume"]:
            return 2
        state = _state_from_journal(journal, arguments.task)
        journal.append("resumed", repeated=plan["may_repeat"])
    task = str(arguments.task or "").strip()
    if not task:
        print("error: a night needs a task; pass --task or --task-file")
        return 2
    endpoint = _endpoint(arguments, readiness, residency)
    allowance, allocation, allocation_record = _output_allocation(
        arguments, endpoint)
    _install_interruption_record(authority, task)
    result = run_night(
        task=task, authority=authority,
        runners=NightRunners(
            call_model=_model_caller(endpoint, allocation),
            run_gate=_gate_runner(float(arguments.gate_timeout_seconds))
            if authority.gate_command else None),
        journal=journal, output_allowance=allowance,
        state=state or StepState.start(task, authority.gate_command))
    result["endpoint"] = endpoint.describe()
    result["output_allocation"] = allocation_record
    result["readiness"] = readiness
    _save(result)
    if arguments.json:
        print(json.dumps(result, indent=1, sort_keys=True))
    else:
        print(render_report(result))
    return 0 if result["terminal_code"] == "COMPLETED_VERIFIED" else 1


def _state_from_journal(journal, task: str):
    """The state a resumed night starts from, rebuilt from what was saved."""
    from .core.step_state import StepState

    folder = Path(journal.directory)
    try:
        saved = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    values = saved.get("state")
    if not isinstance(values, dict) or not values.get("task"):
        return None
    state = StepState.start(values["task"], values.get("gate_command", ""))
    patch = {name: value for name, value in values.items()
             if name not in ("task", "gate_command")}
    return state.apply(patch) if patch else state


def _report(arguments) -> int:
    folder = Path(arguments.workspace).expanduser().resolve()
    try:
        saved = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print(f"error: no saved night in {folder}")
        return 2
    print(json.dumps(saved, indent=1, sort_keys=True) if arguments.json
          else render_report(saved))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loop-engine overnight",
        description="Start an unattended run on a local model and read it "
                    "back in the morning.")
    parser.add_argument("operation",
                        choices=("check", "start", "resume", "report"))
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL,
                        help="the local model server (default "
                             f"{DEFAULT_BASE_URL})")
    parser.add_argument("--model", default="",
                        help="the exact model the night runs")
    parser.add_argument("--wire", default="ollama", choices=("ollama", "openai"),
                        help="the request shape the server speaks")
    parser.add_argument("--context-tokens", type=int, default=8192,
                        help="context tokens the night asks for")
    parser.add_argument("--video-memory-mib", type=int, default=0,
                        help="this machine's video memory; undeclared is "
                             "refused rather than assumed")
    parser.add_argument("--task", default="", help="the problem statement")
    parser.add_argument("--task-file", default="",
                        help="a file holding the problem statement")
    parser.add_argument("--hours", type=float, default=8.0,
                        help="how long the night may run")
    parser.add_argument("--max-model-calls", type=int, default=40,
                        help="how many model calls the night may make")
    parser.add_argument("--max-output-tokens", type=int, default=0,
                        help="an explicit output allowance within the "
                             "capacity the server declared; without one the "
                             "full declared capacity is requested")
    parser.add_argument("--workspace", default="",
                        help="the working folder, which persists across "
                             "attempts")
    parser.add_argument("--read-root", action="append", default=[],
                        help="a folder the night may read; repeat as needed")
    parser.add_argument("--write-root", action="append", default=[],
                        help="a folder the night may write; repeat as needed")
    parser.add_argument("--gate", default="",
                        help="absolute path to the script that decides "
                             "success")
    parser.add_argument("--gate-timeout-seconds", type=float, default=300.0,
                        help="how long the gate may take")
    parser.add_argument("--keep-resident-seconds", type=int, default=None,
                        help="how long the server keeps the weights loaded; "
                             "defaults to the whole night")
    parser.add_argument("--residency-reason", default=DEFAULT_RESIDENCY_REASON,
                        help="why that residency was chosen")
    parser.add_argument("--outage-wait-seconds", type=float, default=60.0,
                        help="how long to wait for a server that went quiet")
    parser.add_argument("--json", action="store_true",
                        help="print the typed record instead of the report")
    return parser


def overnight_command(argument_list) -> int:
    """Run one overnight operation and return its exit status."""
    arguments = _parser().parse_args(list(argument_list))
    if arguments.task_file and not arguments.task:
        try:
            arguments.task = Path(
                arguments.task_file).expanduser().read_text(
                    encoding="utf-8").strip()
        except OSError:
            print(f"error: task file not found: {arguments.task_file}")
            return 2
    if arguments.operation == "report":
        if not arguments.workspace:
            print("error: report needs --workspace")
            return 2
        return _report(arguments)
    if not arguments.model:
        print("error: name the exact model with --model")
        return 2
    if arguments.operation == "check":
        readiness = _readiness(arguments)
        _print_readiness(readiness, arguments.json)
        return 0 if readiness["ready"] else 2
    if not arguments.workspace:
        print("error: a night needs an absolute --workspace it can keep "
              "its work in")
        return 2
    if not os.path.isabs(str(Path(arguments.workspace).expanduser())):
        print("error: --workspace must be an absolute path")
        return 2
    return _run_night(arguments, resuming=arguments.operation == "resume")


def self_test() -> dict:
    """Check dispatch, refusals and the report, without a socket."""
    import tempfile
    from contextlib import redirect_stdout
    from io import StringIO

    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:220]})

    def run(argument_list):
        output = StringIO()
        with redirect_stdout(output):
            code = overnight_command(argument_list)
        return code, output.getvalue()

    code, text = run(["check"])
    check("a_check_without_a_model_refuses_and_says_which_option_is_missing",
          code == 2 and "--model" in text, text.strip())
    code, text = run(["start", "--model", "a-model:7b"])
    check("a_night_without_a_working_folder_is_refused",
          code == 2 and "--workspace" in text, text.strip())
    code, text = run(["start", "--model", "a-model:7b", "--workspace",
                      "relative/folder"])
    check("a_relative_working_folder_is_refused",
          code == 2 and "absolute" in text, text.strip())
    with tempfile.TemporaryDirectory() as folder:
        code, text = run(["report", "--workspace", folder])
        check("a_report_for_a_night_that_never_ran_says_so",
              code == 2 and "no saved night" in text, text.strip())

    # A night against a server that is not there refuses before starting.
    code, text = run(["start", "--model", "a-model:7b", "--workspace", "/tmp",
                      "--base-url", "http://127.0.0.1:1", "--task", "x"])
    check("a_night_whose_machine_cannot_run_it_is_refused_before_it_starts",
          code == 2 and "this night was not started" in text, text.strip())

    report = render_report({
        "task": "repair the failing check", "ending": "declared_authority_spent",
        "terminal_code": "BUDGET_EXHAUSTED", "verified": False, "rounds": 2,
        "elapsed_seconds": 12.5, "model_calls": 4,
        "prompt_tokens_reported": 100, "eval_tokens_reported": 40,
        "calls_with_no_usage_reported": 0,
        "residency": {"keep_resident_seconds": 3600, "reason": "declared"},
        "tried": [{"round": 0, "step": "orient", "elapsed_seconds": 1.0,
                   "ok": True}],
        "rejected": [{"round": 0, "step": "orient", "why": "no object"}],
        "refusals": ["refused: writing '/etc/x' is outside the folders"],
        "next_actions": [{"action": "narrow_the_request", "detail": "no object"}],
        "gate_runs": [{"round": 0, "passed": False, "exit_code": 1}],
        "state": {"hypothesis": "the import is missing"},
        "outcome": {"outcome": "cause_localised", "because": "a hypothesis"},
        "workspace_root": "/night", "journal": "/night/journal.jsonl"})
    for heading in ("What it tried", "What it rejected and why",
                    "What it refused to do", "What it verified",
                    "What remains provisional", "Where the saved night is",
                    "What the server reported"):
        check(f"the_morning_report_says_{heading.lower().replace(' ', '_')}",
              heading in report)
    check("the_report_names_the_physical_calls_and_the_reported_tokens",
          "Physical model calls: 4" in report
          and "Output tokens reported by the server: 40" in report)
    check("the_report_does_not_call_unverified_work_verified",
          "Independently verified: no" in report
          and "every change below is provisional" in report)
    check("the_default_residency_reason_names_the_measured_record",
          "87.28 seconds" in DEFAULT_RESIDENCY_REASON)

    # A catchable signal has to leave the reason behind. Installed on a
    # real checkpoint, then the previous dispositions are put back so this
    # check does not change the handlers of the process running it.
    import signal

    from .code_nodes.overnight_authority import (OvernightAuthority,
                                                 ResidencyPolicy)
    from .core.run_checkpoint import CHECKPOINT_FILENAME

    with tempfile.TemporaryDirectory() as folder:
        previous = {name: signal.getsignal(getattr(signal, name))
                    for name in ("SIGTERM", "SIGINT", "SIGHUP")
                    if hasattr(signal, name)}
        authority = OvernightAuthority(
            night_hours=1.0, max_model_calls=1, workspace_root=folder,
            residency=ResidencyPolicy(keep_resident_seconds=60,
                                      reason="declared for this check"))
        installed = _install_interruption_record(authority, "a task")
        for name, handler in previous.items():
            signal.signal(getattr(signal, name), handler)
        check("a_catchable_signal_is_set_up_to_leave_the_reason_behind",
              "SIGTERM" in installed and "SIGINT" in installed,
              str(installed))
        from .core.run_checkpoint import RunCheckpoint
        written = RunCheckpoint(
            run_id="overnight", workspace_base=folder, checkpoint_dir=folder,
            task="a task").write_on_signal("SIGTERM")
        saved = json.loads(Path(written).read_text(encoding="utf-8"))
        check("the_checkpoint_names_the_signal_that_stopped_the_night",
              saved["reason"] == "interrupted by SIGTERM"
              and Path(folder, CHECKPOINT_FILENAME).is_file(),
              saved["reason"])
    passed = sum(item["passed"] for item in tests)
    return {"name": "overnight_cli", "tests": tests,
            "passed": passed, "total": len(tests)}
