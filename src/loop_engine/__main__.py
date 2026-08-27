"""Command-line interface for Loop Engine.

    PYTHONPATH=. python3 -m loop_engine --self-test
    ... --self-test      # run the deterministic self-test suite
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile

from ._self_test import self_test


def _run_self_test_captured(test_fn=self_test) -> tuple[dict, int]:
    """Run noisy folded tests behind a real OS-backed text stream."""
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stream:
        with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
            report = test_fn()
        stream.flush()
        stream.seek(0)
        captured_lines = sum(1 for _line in stream)
    return report, captured_lines


def _concise_self_test_summary(report: dict, captured_lines: int) -> dict:
    failures = []
    for item in report.get("tests", ()):
        if item.get("passed"):
            continue
        failures.append({
            "test": item.get("test") or item.get("name") or "unnamed test",
            "detail": str(item.get("detail") or item.get("note") or "")[:300],
            **({"missing_dependency": item["missing_dependency"]}
               if item.get("missing_dependency") else {}),
        })
    return {
        "record_type": "loop_engine_self_test_summary/v1",
        "passed": report.get("passed", 0),
        "total": report.get("total", 0),
        "all_passed": bool(report.get("all_passed")),
        "missing_dependencies": report.get("missing_dependencies", []),
        "captured_output_lines": captured_lines,
        "failures": failures,
    }


def _read_task_file(path: str) -> str:
    """Read a task file, refusing missing or unreadable paths."""
    if not path:
        return ""
    import os
    if not os.path.isfile(path):
        print(f"error: task file not found: {path}")
        return ""
    with open(path, encoding="utf-8") as handle:
        return handle.read().strip()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="loop-engine",
                                     description=__doc__.splitlines()[0])
    test_output = parser.add_mutually_exclusive_group()
    test_output.add_argument(
        "--self-test", action="store_true",
        help="run all tests and print one concise summary plus failures")
    test_output.add_argument(
        "--self-test-verbose", action="store_true",
        help="run all tests with module demo output and the full JSON report")
    parser.add_argument("--categories", action="store_true",
                        help="print the retired resolver category view (empty)")
    parser.add_argument("--map", action="store_true",
                        help="print the nine-step kernel map: where every "
                        "capability lives")
    parser.add_argument("--profiles", action="store_true",
                        help="print the versioned Loop profile catalog")
    parser.add_argument("--doctor", action="store_true",
                        help="check package, architecture, settings, and the "
                             "no-key deterministic lane without network calls")
    parser.add_argument("--live-demo", action="store_true",
                        help="watch a real canonical Loop run live: "
                        "localhost page with the step rail + console log "
                        "(deterministic stage-0 fixture, zero model calls)")
    parser.add_argument("--studio", action="store_true",
                        help="serve Loop Engine Studio (local, read-only, "
                        "backed by saved run history) on --port")
    parser.add_argument("--port", type=int,
                        help="local port (Studio defaults to 8765; live demo "
                             "defaults to 8770)")
    parser.add_argument("--runs-dir",
                        help="shared saved-run directory; defaults to "
                             "$LOOP_ENGINE_RUNS_DIR or ~/.loop-engine/runs")
    parser.add_argument("--conformance", action="store_true",
                        help="run the machine-enforced conformance scan + "
                        "zero-tolerance gates; writes "
                        "architecture_conformance.json; exits nonzero on any "
                        "violation")
    parser.add_argument("--structure", action="store_true",
                        help="print the repository structure report")
    parser.add_argument("--structure-json", action="store_true",
                        help="print the repository structure report as JSON")
    parser.add_argument("--repo-conformance", action="store_true",
                        help="run the repository conformance harness")
    parser.add_argument("--architecture-contract", action="store_true",
                        help="validate the machine-readable architecture contract")
    parser.add_argument("--task-compile", action="store_true",
                        help="compile freeform text into a typed task")
    parser.add_argument(
        "--compile-provider",
        choices=("ollama_cloud", "openrouter", "opencode_go"),
        default="",
        help="optionally add one authorized model-assisted Orientation review; "
             "the deterministic compilation remains authoritative")
    parser.add_argument(
        "--provider-key-env", default="", metavar="ENV_NAME",
        help="read the selected provider key from this environment variable; "
             "the key value is never a command argument")
    parser.add_argument(
        "--prompt-for-provider-key", action="store_true",
        help="read the selected provider key through a hidden terminal prompt")
    parser.add_argument(
        "--interaction-mode",
        choices=("ask_when_material", "autonomous"),
        default="ask_when_material",
        help="task compilation during compile or solve may ask for material "
             "missing information, or run autonomously and abstain when "
             "policy cannot resolve safely")
    parser.add_argument(
        "--task-feedback", action="append", default=[], metavar="SLOT=VALUE",
        help="optional registered task feedback slot; repeat when needed")
    parser.add_argument("--text", default="",
                        help="freeform task text for --task-compile or --solve")
    parser.add_argument("--file", default="",
                        help="task file for --task-compile or --solve")
    parser.add_argument("--url", default="",
                        help="URL source for task compilation or solve")
    parser.add_argument("--dataset", default="",
                        help="dataset path; pair with --text for its goal")
    parser.add_argument("--repository", default="",
                        help="repository path; pair with --text for its goal")
    parser.add_argument("--task-pack", default="",
                        help="versioned JSON task-pack path")
    parser.add_argument("--solve", action="store_true",
                        help="solve a task from --text or --file")
    parser.add_argument("--templates", action="store_true",
                        help="list registered task templates")
    parser.add_argument("--learn", action="store_true",
                        help="stage learning candidates from the latest run")
    parser.add_argument("--lesson", default="",
                        help="evidence-bounded candidate lesson for --learn")
    parser.add_argument("--candidates", action="store_true",
                        help="list staged learning candidates")
    parser.add_argument("--candidate-action",
                        choices=("review", "promote", "rollback"),
                        help="govern one exact learning-candidate version")
    parser.add_argument("--candidate-id", default="")
    parser.add_argument("--candidate-version", default="")
    parser.add_argument("--candidate-digest", default="")
    parser.add_argument("--decision", choices=("accept", "reject"),
                        default="accept")
    parser.add_argument("--decision-reason", default="")
    parser.add_argument("--evidence", action="append", default=[],
                        help="evidence reference; repeat for multiple refs")
    parser.add_argument("--demo", choices=("five-step",),
                        help="run the five-step product demo")
    parser.add_argument("--report", metavar="RUN_ID", nargs="?", const="@last",
                        help="render a loop report for a saved run "
                             "(default: the most recent). Use --format and "
                             "--out to choose the rendering and destination.")
    parser.add_argument("--runs", action="store_true",
                        help="list the saved runs a report can be built from")
    parser.add_argument("--format", default="text",
                        choices=("text", "markdown", "html", "json"),
                        help="report rendering (default: text)")
    parser.add_argument("--out", metavar="PATH",
                        help="write the report to PATH instead of stdout")
    parser.add_argument("--setup", action="store_true",
                        help="guided walkthrough: checks the installation, "
                             "providers, your own server and knowledge, then "
                             "runs a real loop")
    parser.add_argument("--example",
                        choices=("support-queue", "intelligence-layers",
                                 "context-seed"),
                        help="run a useful example included with the package")
    parser.add_argument("--campaign", choices=("plan", "run"),
                        help="plan or run the five-problem pilot campaign")
    parser.add_argument("--verify-live-model", metavar="PROVIDER",
                        help="verify one real Ollama Cloud, Mistral, or custom "
                             "provider call against repository metadata")
    parser.add_argument("--model-route", default="",
                        help="exact route for live verification or "
                             "provider-assisted task compilation")
    parser.add_argument("--model-id", default="",
                        help="exact model for live verification or "
                             "provider-assisted task compilation")
    parser.add_argument("--models-action",
                        choices=("inventory", "routes", "explain", "benchmark"),
                        help="inspect or explain model routing without provider calls")
    parser.add_argument("--model-purpose", default="decide_label",
                        help="gateway purpose for models explain")
    parser.add_argument("--operator", default="",
                        help="task operator override for models explain")
    parser.add_argument("--response-topology", default="",
                        help="response topology override for models explain")
    parser.add_argument("--local-only", action="store_true",
                        help="restrict model selection to local routes")
    parser.add_argument("--deterministic-sufficient", action="store_true",
                        help="declare a source-backed deterministic procedure "
                             "for models explain")
    parser.add_argument("--repository-root", default=".",
                        help="repository whose pyproject.toml is used by the "
                             "live verification")
    parser.add_argument("--live-evidence-out", default="",
                        help="new JSON evidence path; default is a protected "
                             "file below ~/.loop-engine/evidence")
    parser.add_argument("--live-timeout", type=float, default=300.0,
                        help="wall-time limit for the one live provider call")
    parser.add_argument("--settings-action", choices=("init", "show", "check"),
                        help="create, show, or validate user settings")
    parser.add_argument("--settings-file",
                        help="explicit YAML settings path")
    parser.add_argument("--modes", default="",
                        help="comma-separated campaign modes; defaults to "
                             "the user settings")
    parser.add_argument("--providers", default="",
                        help="comma-separated campaign providers; defaults "
                             "to enabled providers in user settings")
    parser.add_argument("--thinking-power", default="",
                        choices=("", "small", "medium", "high", "max",
                                 "specialized"),
                        help="model capacity tier for model-using campaign "
                             "arms")
    parser.add_argument("--cases", default="",
                        help="comma-separated campaign case IDs; default all")
    parser.add_argument("--authorize-model-calls", action="store_true",
                        help="explicitly allow bounded model calls")
    parser.add_argument("--max-model-calls", type=int, default=0,
                        help="hard physical model-call ceiling")
    parser.add_argument("--max-total-tokens", type=int,
                        help="hard provider-reported token ceiling")
    parser.add_argument("--watch", action="store_true",
                        help="print campaign events while arms run")
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if raw_argv[:1] == ["setup"]:
        raw_argv[:1] = ["--setup"]
    elif raw_argv[:1] == ["doctor"]:
        raw_argv[:1] = ["--doctor"]
    elif raw_argv[:1] == ["solve"]:
        raw_argv[:1] = ["--solve"]
    elif raw_argv[:2] == ["task", "compile"]:
        raw_argv[:2] = ["--task-compile"]
    elif raw_argv[:2] == ["models", "probe"]:
        if len(raw_argv) < 3 or raw_argv[2].startswith("-"):
            parser.error("models probe requires a provider id")
        raw_argv[:3] = ["--verify-live-model", raw_argv[2]]
    elif raw_argv[:1] == ["models"]:
        if len(raw_argv) < 2 or raw_argv[1] not in (
                "inventory", "routes", "explain", "benchmark"):
            parser.error(
                "models requires inventory, routes, explain, benchmark, or probe")
        raw_argv[:2] = ["--models-action", raw_argv[1]]
    elif raw_argv[:1] == ["learn"]:
        raw_argv[:1] = ["--learn"]
    elif raw_argv[:2] == ["candidates", "list"]:
        raw_argv[:2] = ["--candidates"]
    elif raw_argv[:1] == ["candidates"]:
        if len(raw_argv) < 2 or raw_argv[1] not in (
                "review", "promote", "rollback"):
            parser.error("candidates requires list, review, promote, or rollback")
        raw_argv[:2] = ["--candidate-action", raw_argv[1]]
    elif raw_argv[:1] == ["campaign"]:
        if len(raw_argv) < 2 or raw_argv[1] not in ("plan", "run"):
            parser.error("campaign requires plan or run")
        raw_argv[:2] = ["--campaign", raw_argv[1]]
    elif raw_argv[:1] == ["settings"]:
        if len(raw_argv) < 2 or raw_argv[1] not in ("init", "show", "check"):
            parser.error("settings requires init, show, or check")
        raw_argv[:2] = ["--settings-action", raw_argv[1]]
    args = parser.parse_args(raw_argv)
    if args.doctor:
        from .cli_operations import run_doctor
        return run_doctor(args)
    if args.models_action:
        from .cli_operations import run_models_action
        return run_models_action(args)
    if args.verify_live_model:
        from .core.live_model_verification import (
            LiveModelVerificationError, LiveModelVerificationRequest,
            plan_live_model_verification, run_live_model_verification)
        try:
            request = LiveModelVerificationRequest(
                provider=args.verify_live_model,
                repository_root=args.repository_root,
                settings_file=args.settings_file or "",
                route_name=args.model_route,
                model=args.model_id,
                authorize_model_calls=args.authorize_model_calls,
                max_physical_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens,
                timeout_seconds=args.live_timeout,
                evidence_path=args.live_evidence_out)
            if not args.authorize_model_calls:
                planned = plan_live_model_verification(request).safe_summary()
                planned["status"] = "NOT_RUN"
                planned["reason"] = (
                    "add --authorize-model-calls, --max-model-calls 1, and "
                    "an adequate --max-total-tokens value to make the call")
                print(json.dumps(planned, indent=1))
                return 2
            result = run_live_model_verification(request)
            print(json.dumps(result, indent=1))
            return 0 if result["provider_integration_proven"] else 1
        except (LiveModelVerificationError, KeyError, ValueError) as exc:
            print(json.dumps({
                "record_type": "live_model_verification_refusal/v1",
                "status": "NOT_RUN",
                "provider_integration_proven": False,
                "reason": str(exc),
            }, indent=1))
            return 2
    if args.settings_action:
        from .core.settings_loader import (
            load_runtime_settings, write_default_settings)
        from .core.runtime_settings import SettingsError
        try:
            if args.settings_action == "init":
                created = write_default_settings(args.settings_file)
                print(f"Created Loop Engine settings at {created.path} "
                      f"through {created.loop_id}")
                return 0
            loaded = load_runtime_settings(args.settings_file)
            summary = loaded.safe_summary()
            if args.settings_action == "check":
                gateway = loaded.settings.build_gateway()
                enabled = set(gateway.providers)
                usable_by_tier = {}
                for tier in loaded.settings.models.tiers:
                    usable = []
                    for route_name in tier.routes:
                        route = gateway.registry.get(route_name)
                        if route.provider in enabled:
                            usable.append(route_name)
                    usable_by_tier[tier.name] = usable
                summary["validation"] = {
                    "valid": True,
                    "network_calls": 0,
                    "usable_routes_by_tier": usable_by_tier,
                }
            print(json.dumps(summary, indent=1))
            return 0
        except (SettingsError, KeyError, ValueError, RuntimeError) as exc:
            print(f"Settings refused: {exc}")
            return 2
    if args.campaign:
        from .code_nodes.campaign_runner import (
            CAMPAIGN_MODES, CampaignRunOptions, CampaignRunner, campaign_arms,
            default_campaign_spec, default_problem_cases)
        from .core.settings_loader import load_runtime_settings
        try:
            loaded = load_runtime_settings(args.settings_file)
        except ValueError as exc:
            parser.error(str(exc))
        runtime_settings = loaded.settings
        modes = (tuple(value.strip() for value in args.modes.split(",")
                       if value.strip()) or runtime_settings.loop.preferred_modes)
        providers = (tuple(value.strip()
                           for value in args.providers.split(",")
                           if value.strip())
                     or runtime_settings.models.enabled_provider_ids())
        thinking_power = (args.thinking_power
                          or runtime_settings.models.default_thinking_power)
        all_cases = default_problem_cases()
        requested_cases = {value.strip() for value in args.cases.split(",")
                           if value.strip()}
        cases = tuple(case for case in all_cases
                      if not requested_cases or case.case_id in requested_cases)
        unknown_cases = requested_cases - {case.case_id for case in all_cases}
        if unknown_cases:
            parser.error(f"unknown campaign cases: {sorted(unknown_cases)}")
        bad_modes = [mode for mode in modes if mode not in CAMPAIGN_MODES]
        if bad_modes:
            parser.error(f"unknown campaign modes: {bad_modes}")
        arms = campaign_arms(
            modes=modes, providers=providers,
            llm_thinking_power=thinking_power)
        if args.campaign == "plan":
            model_arms = sum(1 for case in cases
                             for arm in arms
                             if arm.mode != "deterministic")
            print(json.dumps({
                "record_type": "campaign_plan/v1",
                "cases": [case.summary() for case in cases],
                "arms": [arm.arm_id for arm in arms],
                "runs": len(cases) * len(arms),
                "model_arms": model_arms,
                "minimum_model_call_ceiling": model_arms,
                "model_authorization_required": bool(model_arms),
                "llm_thinking_power": thinking_power,
            }, indent=1))
            return 0
        try:
            spec = default_campaign_spec(
                modes=modes, providers=providers,
                llm_thinking_power=thinking_power,
                cases=cases,
                authorize_model_calls=args.authorize_model_calls,
                max_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens)
        except ValueError as exc:
            print(f"Campaign refused: {exc}")
            return 2
        from .core.run_history import default_runs_dir
        runs_dir = default_runs_dir(
            args.runs_dir or runtime_settings.history.resolved_runs_dir())
        result = CampaignRunner(spec, CampaignRunOptions(
            runs_dir=runs_dir, watch=args.watch,
            runtime_settings=runtime_settings)).run()
        print(json.dumps(result.to_dict(), indent=1))
        return 0 if result.accepted == len(result.arms) else 1
    if args.setup:
        from .code_nodes.guided_setup import run_setup
        return 0 if run_setup().ready else 1
    if args.example:
        from .code_nodes.public_examples import run_example
        print(run_example(args.example))
        return 0
    if args.runs or args.report:
        import os
        from .core.run_history import default_runs_dir
        from .code_nodes.loop_report import (report_from_run, render_text,
                                             render_markdown, render_html)
        runs_dir = default_runs_dir(args.runs_dir or "")
        saved = sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []
        if args.runs:
            if not saved:
                print("No saved runs yet. Run a Loop and save its run history "
                      "to make it appear here.")
                return 0
            print(f"{len(saved)} saved run(s):")
            for r in saved:
                print(f"  {r}")
            return 0
        if not saved:
            print("No saved runs to report on yet.")
            return 1
        run_id = saved[-1] if args.report == "@last" else args.report
        if run_id not in saved:
            print(f"No saved run named {run_id!r}. Known runs: "
                  + ", ".join(saved[:8]) + ("…" if len(saved) > 8 else ""))
            return 1
        rep = report_from_run(runs_dir, run_id)
        body = {"text": render_text, "markdown": render_markdown,
                "html": render_html,
                "json": lambda r: json.dumps(r.as_dict(), indent=1)
                }[args.format](rep)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(body)
            print(f"wrote {args.format} report for {run_id} -> {args.out}")
        else:
            print(body)
        return 0
    if args.live_demo:
        from .code_nodes.live_run_demo import run_live_demo
        run_live_demo(port=args.port or 8770, pace_seconds=0.6,
                      serve_forever=True, runs_dir=args.runs_dir or "")
        return 0
    if args.studio:
        from .core.studio_server import serve
        serve(args.port or 8765, runs_dir=args.runs_dir or "")
        return 0
    if args.conformance:
        from .conformance_report import run_conformance
        report = run_conformance()
        print(report["human_summary"])
        return 0 if report["all_gates_pass"] else 1
    if args.structure:
        from .repository_structure import (render_structure_text,
                                           structure_report)
        print(render_structure_text(structure_report()))
        return 0
    if args.structure_json:
        from .repository_structure import structure_report
        print(json.dumps(structure_report(), indent=1))
        return 0
    if args.repo_conformance:
        from .repository_conformance import run_repository_conformance
        report = run_repository_conformance()
        print(json.dumps(report, indent=1))
        return 0 if report["passed"] else 1
    if args.architecture_contract:
        from .architecture_contract import run_architecture_contract_checks
        report = run_architecture_contract_checks()
        print(json.dumps(report, indent=1))
        return 0 if report["passed"] else 1
    if args.templates:
        from .templates.library import TemplateLibrary
        library = TemplateLibrary()
        print(json.dumps({
            "record_type": "task_templates/v1",
            "templates": [t.to_dict() for t in
                          (library.get(i) for i in library.ids())],
        }, indent=1))
        return 0
    if args.task_compile:
        from .cli_operations import run_task_compile
        return run_task_compile(args)
    if args.solve:
        from .cli_operations import run_solve
        return run_solve(args)
    if args.learn:
        from .cli_operations import run_learn
        return run_learn(args)
    if args.candidate_action:
        from .cli_operations import run_candidate_action
        return run_candidate_action(args)
    if args.candidates:
        from .memory.storage.repository import CandidateJournal
        journal = CandidateJournal()
        candidates = journal.list_candidates()
        print(json.dumps({
            "record_type": "learning_candidates/v1",
            "storage": str(journal.journal),
            "candidates": candidates,
            "note": ("no candidates staged; run --learn first"
                     if not candidates else
                     f"{len(candidates)} candidate(s) staged; each awaits "
                     "independent review"),
        }, indent=1))
        return 0
    if args.demo == "five-step":
        from .cli_operations import run_five_step_demo
        return run_five_step_demo(args)
    if args.map:
        from .architecture_map import render_map as render_architecture
        print(render_architecture())
        return 0
    if args.profiles:
        from .loop.loop_profile_catalog import (
            PROFILE_ONTOLOGY_VERSION, profile_catalog)
        profiles = profile_catalog()
        print(json.dumps({
            "record_type": "loop_profile_catalog/v1",
            "ontology_version": PROFILE_ONTOLOGY_VERSION,
            "profiles": profiles,
        }, indent=1))
        return 0
    if args.categories:
        print(json.dumps({"resolver_categories": [],
                          "default_levels": {},
                          "move_types": []}, indent=1))
        return 0
    if args.self_test or args.self_test_verbose:
        if args.self_test_verbose:
            report = self_test()
            print(json.dumps(report, indent=1))
        else:
            report, captured_lines = _run_self_test_captured()
            print(json.dumps(_concise_self_test_summary(
                report, captured_lines), indent=1))
        return 0 if report["all_passed"] else 1
    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
