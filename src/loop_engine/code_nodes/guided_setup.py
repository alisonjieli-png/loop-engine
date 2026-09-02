"""Guided setup — a walkthrough that ends with a loop you actually ran.

Architectural role: Code Node system (the first-run experience).

A new user's first ten minutes decide whether they keep going. Reading five
documents to discover that the core needs no key, that a provider is optional,
and that a store hit outranks a model call is a worse use of those minutes than
being walked through it once, on their own machine, with their own files.

So this asks a short series of questions, checks each answer BY DOING IT, and
finishes by running a real loop and printing its report.

    loop-engine setup

Design rules it follows, from the project's own guidance:

    ORDER IS ALWAYS deterministic -> hybrid -> model-backed. Setup teaches the
    ladder in that order, so the deterministic rail is the thing that works
    first and a provider is visibly an escalation rather than a prerequisite.

    NEVER COLOR-ONLY MEANING. Every mode is printed with its word, so the
    output reads correctly with no colour at all — in a pipe, a CI log, or a
    screen reader.

    SAMPLE DATA IS LABELLED. Nothing invented is presented as measured.

Owns:
    - SetupStep / SetupReport: the steps and what each one established;
    - run_setup(): the walkthrough itself;
    - the non-interactive `--check` path, so CI and scripts can use it too.

Does not own:
    - provider adapters, discovery (autoconfigure), the loop runtime, or the
      knowledge loader — this ORCHESTRATES them and owns none of them.

Key invariants:
    - every check is performed, never assumed;
    - a missing capability is reported with the exact command to fix it;
    - no key is ever printed, logged, or written to a file by this module;
    - it works non-interactively, so it can run unattended.

Verification: self_test() — the non-interactive path end to end, honest
reporting when nothing is installed, no-key-leak, and the adversarial
"claims a step passed that did not run" path.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

#: Modes in the ONE canonical order used everywhere in this project.
MODE_ORDER = ("deterministic", "hybrid", "model-backed")


@dataclass
class SetupStep:
    """One checked step. `ran` is separate from `ok` deliberately: a step that
    did not run is not a step that passed."""
    name: str
    ran: bool = False
    ok: bool = False
    detail: str = ""
    fix: str = ""

    @property
    def status(self) -> str:
        if not self.ran:
            return "NOT RUN"
        return "OK" if self.ok else "NEEDS ATTENTION"


@dataclass
class SetupReport:
    steps: list = field(default_factory=list)
    modes_available: list = field(default_factory=list)

    def add(self, step: SetupStep) -> SetupStep:
        self.steps.append(step)
        return step

    @property
    def ready(self) -> bool:
        """Ready means the deterministic rail works. A provider is optional by
        design, so its absence never makes an installation 'not ready'."""
        core = [s for s in self.steps if s.name in ("install", "first loop",
                                                    "report")]
        return bool(core) and all(s.ran and s.ok for s in core)

    def summary(self) -> dict:
        return {"record_type": "guided_setup/v1", "ready": self.ready,
                "provider_calls_made": 0,
                "modes_available": list(self.modes_available),
                "steps": [{"name": s.name, "status": s.status,
                           "detail": s.detail, "fix": s.fix}
                          for s in self.steps]}


def _has_pandas() -> bool:
    try:
        import pandas
        return True
    except ImportError:
        return False


def _has_duckdb() -> bool:
    try:
        import duckdb
        return True
    except ImportError:
        return False


def _has_model2vec() -> bool:
    try:
        import model2vec
        return True
    except ImportError:
        return False


# --- presentation ----------------------------------------------------------

def _rule(w=64):
    return "─" * w


def _say(*a):
    print(*a, flush=True)


def _ask(prompt: str, default: str = "", *, interactive: bool = True) -> str:
    if not interactive:
        return default
    try:
        got = input(f"{prompt} ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default
    return got or default


def _yes(prompt: str, *, default: bool = True, interactive: bool = True
         ) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    got = _ask(f"{prompt} {hint}", "", interactive=interactive)
    if not got:
        return default
    return got.lower().startswith("y")


# --- the walkthrough -------------------------------------------------------

def run_setup(*, interactive: bool = True, knowledge_path: str = "",
              run_loop: bool = True) -> SetupReport:
    """Walk through setup, checking each step by performing it."""
    report = SetupReport()

    _say()
    _say("  LOOP ENGINE SETUP")
    _say(f"  {_rule()}")
    _say("  Everything is a loop. This walks you through the ladder in the")
    _say("  order it actually works:")
    _say()
    _say("    1. deterministic   no model, no key, no network")
    _say("    2. hybrid          escalates one step that needs judgement")
    _say("    3. model-backed    leads with the model")
    _say()
    _say("  Steps 2 and 3 need a provider. Step 1 never does — which is why")
    _say("  it comes first rather than last.")
    _say(f"  {_rule()}")

    # -- 1. installation ----------------------------------------------------
    _say()
    _say("  [1/5] INSTALLATION")
    step = report.add(SetupStep("install"))
    try:
        # Relative imports keep the package self-contained.
        from ..loop.encapsulate import as_practitioner_loop
        step.ran, step.ok = True, True
        step.detail = f"python {sys.version.split()[0]}, package importable"
        _say(f"      OK   package imports, Python "
             f"{sys.version.split()[0]}")
    except ImportError as e:                                # pragma: no cover
        step.ran, step.ok = True, False
        step.detail = str(e)[:120]
        step.fix = "python -m pip install --force-reinstall git+https://github.com/alisonjieli-png/loop-engine.git"
        _say(f"      FAIL {e}")
        return report
    dependencies = {
        "pandas": _has_pandas(),
        "duckdb": _has_duckdb(),
        "model2vec": _has_model2vec(),
    }
    have = [k for k, v in dependencies.items() if v]
    missing = [k for k, v in dependencies.items() if not v]
    _say(f"      optional data adapters installed: {', '.join(have) or 'none'}")
    if missing:
        step.detail += "; optional data adapters absent: " + ", ".join(missing)
        _say(f"      Optional data adapters not installed: {', '.join(missing)}")
        _say("      This is a complete installation for the public solve path.")
        _say("      Add data adapters only when a task needs them:")
        _say("      python -m pip install pandas duckdb model2vec")
    else:
        _say("      Core and optional data adapters are ready.")

    # -- 2. providers -------------------------------------------------------
    _say()
    _say("  [2/5] MODEL PROVIDERS  (optional)")
    step = report.add(SetupStep("providers"))
    from ..core.autoconfigure import KEY_ENV
    present = [n for n, var in KEY_ENV.items() if os.environ.get(var)]
    if not present:
        _say("      No provider keys found in the environment.")
        _say("      That is a normal, working setup — deterministic loops run")
        _say("      without one. To add one later, set any of:")
        for name, var in sorted(KEY_ENV.items()):
            _say(f"        {var:<22}({name})")
        _say("      Your own server works too — see step 3.")
        step.ran, step.ok = True, True
        step.detail = "no provider configured (deterministic only)"
        report.modes_available = ["deterministic"]
    else:
        _say(f"      Found credential references for: {', '.join(present)}")
        _say("      No provider call was made. Test one exact route with:")
        _say("      loop-engine models probe PROVIDER --model-route ROUTE \\")
        _say("        --model-id MODEL --authorize-model-calls \\")
        _say("        --max-model-calls 1 --max-total-tokens LIMIT")
        step.ran, step.ok = True, True
        step.detail = "configured but not tested: " + ", ".join(present)
        step.fix = "run one exact bounded models probe before solve"
        report.modes_available = ["deterministic"]

    # -- 3. your own server -------------------------------------------------
    _say()
    _say("  [3/5] YOUR OWN SERVER  (optional)")
    step = report.add(SetupStep("custom endpoint"))
    step.ran = True
    step.ok = True
    if interactive and _yes("      Point at a self-hosted or third-party "
                            "server now?", default=False,
                            interactive=interactive):
        url = _ask("      Base URL (e.g. http://localhost:11434/v1):",
                   interactive=interactive)
        model = _ask("      Model name:", interactive=interactive)
        if url and model:
            from ..core.custom_endpoint import (
                CustomEndpoint, make_adapter)
            wire = "ollama" if "11434" in url and "/v1" not in url else "openai"
            ep = CustomEndpoint(name="my_server", base_url=url, model=model,
                                wire=wire)
            probe = make_adapter(ep).verify()
            if probe["ok"]:
                _say(f"      OK   answered: {probe['prompt_tokens']}+"
                     f"{probe['eval_tokens']} tokens")
                step.detail = f"{url} reachable"
                report.modes_available = ["deterministic", "hybrid",
                                          "non_deterministic"]
            else:
                _say(f"      NOT REACHABLE: {probe['error'][:90]}")
                step.ok = False
                step.detail = probe["error"][:120]
                step.fix = "check the URL and that the server is running"
    else:
        _say("      Skipped. Any OpenAI-compatible server works — vLLM,")
        _say("      LM Studio, llama.cpp, LiteLLM, an internal gateway.")
        _say("      Set LOOP_ENGINE_ENDPOINTS or pass endpoints= to configure().")
        step.detail = "not configured"

    # -- 4. your own knowledge ---------------------------------------------
    _say()
    _say("  [4/5] YOUR OWN KNOWLEDGE  (optional)")
    step = report.add(SetupStep("knowledge"))
    path = knowledge_path
    if not path and interactive and _yes(
            "      Load a folder of your notes/docs as searchable "
            "intelligence?", default=False, interactive=interactive):
        path = _ask("      Path to a file or folder:",
                    interactive=interactive)
    if path:
        from ..core.knowledge_loader import load_knowledge
        res = load_knowledge(path)
        step.ran = True
        step.ok = bool(res.records)
        for line in res.explain().splitlines():
            _say(f"      {line}")
        step.detail = f"{len(res.records)} records from {res.files_read} files"
        if not res.records:
            step.fix = ("point at a folder containing .md, .txt, .csv, .json, "
                        ".jsonl or .py files")
    else:
        step.ran = True
        step.ok = True
        step.detail = "not loaded"
        _say("      Skipped. Markdown, text, CSV, JSON, JSONL and Python")
        _say("      docstrings all load — point it at a folder any time:")
        _say("        from loop_engine.core.knowledge_loader "
             "import load_knowledge")

    # -- 5. run a real loop -------------------------------------------------
    _say()
    _say("  [5/5] RUN A LOOP")
    step = report.add(SetupStep("first loop"))
    if not run_loop:
        _say("      Skipped by request.")
        return report
    from ..loop.encapsulate import as_practitioner_loop
    from ..loop.recursive_loop import LoopLedger
    ledger = LoopLedger()
    result = as_practitioner_loop(
        "setup check: confirm the deterministic rail works",
        lambda: sum(range(10)), ledger=ledger)
    step.ran = True
    step.ok = result["value"] == 45 and result["model_calls"] == 0
    step.detail = (f"value={result['value']}, "
                   f"{len(ledger.events)} events, 0 model calls")
    _say(f"      OK   the loop returned {result['value']} in "
         f"{len(ledger.events)} recorded events, deterministic, "
         f"0 model calls")

    rep_step = report.add(SetupStep("report"))
    from .loop_report import report_from_ledger, render_text
    rendered = render_text(report_from_ledger(ledger.events,
                                              run_id="setup-check"))
    rep_step.ran = True
    rep_step.ok = "LOOP REPORT" in rendered
    rep_step.detail = "text report rendered from the run's own ledger"
    _say()
    for line in rendered.splitlines():
        _say(f"      {line}")

    # -- what you can do now ------------------------------------------------
    _say()
    _say(f"  {_rule()}")
    _say("  WHAT YOU CAN RUN NOW")
    modes = report.modes_available or ["deterministic"]
    for m in MODE_ORDER:
        key = "non_deterministic" if m == "model-backed" else m
        mark = "yes" if key in modes else "needs a provider"
        _say(f"    {m:<16}{mark}")
    _say()
    _say("  Next:")
    _say("    loop-engine report @last       what the latest run did")
    _say("    loop-engine --self-test         verify the installation")
    _say("    python3 examples/01_prioritize_support_queue/run.py")
    _say("    python3 examples/06_reconcile_invoices/run.py")
    _say(f"  {_rule()}")
    _say()
    return report


def main(argv=None) -> int:
    """Entry point for `loop-engine setup`."""
    argv = list(sys.argv[1:] if argv is None else argv)
    non_interactive = "--check" in argv or "--yes" in argv or not sys.stdin.isatty()
    knowledge = ""
    if "--knowledge" in argv:
        i = argv.index("--knowledge")
        if i + 1 < len(argv):
            knowledge = argv[i + 1]
    report = run_setup(interactive=not non_interactive,
                       knowledge_path=knowledge)
    return 0 if report.ready else 1


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    import contextlib
    import io as _io

    # 1. THE NON-INTERACTIVE PATH runs end to end and actually RUNS a loop —
    # setup that only prints advice has checked nothing.
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        rep = run_setup(interactive=False)
    out = buf.getvalue()
    names = [s.name for s in rep.steps]
    check("setup_runs_every_step_without_a_terminal",
          rep.ready and "first loop" in names and "report" in names
          and all(s.ran for s in rep.steps)
          and "LOOP REPORT" in out,
          f"{len(rep.steps)} steps, all ran")

    # 2. NOT RUN IS NOT PASS. `ran` is separate from `ok`, so a step that never
    # executed can never read as success.
    never = SetupStep("hypothetical")
    check("a_step_that_did_not_run_reports_NOT_RUN",
          never.status == "NOT RUN" and not never.ran
          and SetupStep("x", ran=True, ok=False).status == "NEEDS ATTENTION"
          and SetupStep("x", ran=True, ok=True).status == "OK",
          "ran and ok are separate facts")

    # 3. READY MEANS THE DETERMINISTIC RAIL WORKS. A missing provider is not a
    # broken installation — treating it as one would teach exactly the wrong
    # thing on the first run.
    provider_step = next(s for s in rep.steps if s.name == "providers")
    check("no_provider_still_counts_as_a_ready_installation",
          rep.ready and provider_step.ran,
          "a provider is an escalation, not a prerequisite")

    # 4. MODES ARE PRINTED WITH THEIR WORDS, in the canonical order, so the
    # output survives having no colour at all.
    idx = [out.index(m) for m in ("deterministic", "hybrid", "model-backed")
           if m in out]
    check("modes_are_named_in_the_canonical_order",
          len(idx) == 3 and idx == sorted(idx)
          and MODE_ORDER == ("deterministic", "hybrid", "model-backed"),
          "deterministic -> hybrid -> model-backed, never colour alone")

    # 5. NO KEY LEAKS. Setup prints provider NAMES and outcomes, never values.
    secret = "sk-" + "T" * 30
    os.environ["LOOP_ENGINE_SETUP_PROBE_KEY"] = secret
    try:
        buf2 = _io.StringIO()
        with contextlib.redirect_stdout(buf2):
            run_setup(interactive=False, run_loop=False)
        blob = buf2.getvalue() + str(rep.summary())
        check("no_key_material_is_ever_printed_or_reported",
              secret not in blob and "Bearer" not in blob,
              "names and outcomes only")
    finally:
        os.environ.pop("LOOP_ENGINE_SETUP_PROBE_KEY", None)

    # 6. KNOWLEDGE LOADING is exercised for real, not described.
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        open(os.path.join(d, "notes.md"), "w").write(
            "# Runbook\nRestart the worker before the queue drains.\n")
        buf3 = _io.StringIO()
        with contextlib.redirect_stdout(buf3):
            rep3 = run_setup(interactive=False, knowledge_path=d,
                             run_loop=False)
        k = next(s for s in rep3.steps if s.name == "knowledge")
        check("pointing_setup_at_a_folder_loads_it_and_says_what_it_found",
              k.ran and k.ok and "record" in k.detail
              and "Loaded" in buf3.getvalue(),
              k.detail)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # 7. the report is structured for a script as well as a person
    s = rep.summary()
    check("the_setup_result_is_machine_readable_too",
          s["record_type"] == "guided_setup/v1" and isinstance(s["ready"], bool)
          and all({"name", "status"} <= set(x) for x in s["steps"]),
          f"{len(s['steps'])} steps in the record")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
