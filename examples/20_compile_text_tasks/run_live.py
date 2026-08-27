"""Run the five public text tasks through one authorized live model route."""
from __future__ import annotations

import argparse
from pathlib import Path

from loop_engine.core.live_model_verification import LiveModelVerificationError
from loop_engine.core.live_text_scenarios import (
    LiveTextScenario,
    LiveTextScenarioSuiteRequest,
    run_live_text_scenarios,
)

from scenario_definitions import (
    LIVE_EXPECTED_STATUS, LIVE_INTERACTION_MODE, TASK_SCENARIOS)
from run import compile_text_tasks


def load_scenarios(tasks_dir: Path) -> tuple[LiveTextScenario, ...]:
    return tuple(
        LiveTextScenario(
            scenario_id=scenario_id,
            task_text=(tasks_dir / filename).read_text(
                encoding="utf-8").strip(),
            interaction_mode=LIVE_INTERACTION_MODE.value,
            expected_status=LIVE_EXPECTED_STATUS,
            source_ref=(
                f"examples/20_compile_text_tasks/tasks/{filename}"),
        )
        for filename, scenario_id, _mode, _expected_status in TASK_SCENARIOS)


def build_parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(
        description="Run five bounded live Ollama text scenarios")
    parser.add_argument("--provider", default="ollama_cloud")
    parser.add_argument("--route", default="cloud.default")
    parser.add_argument("--model", default="")
    parser.add_argument("--repository-root", default=str(repository_root))
    parser.add_argument("--evidence-out", default="")
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-model-calls", type=int, default=0)
    parser.add_argument("--max-total-tokens", type=int)
    parser.add_argument("--authorize-model-calls", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    tasks_dir = Path(__file__).resolve().parent / "tasks"
    compiled = compile_text_tasks(tasks_dir)
    try:
        result = run_live_text_scenarios(
            LiveTextScenarioSuiteRequest(
                provider=args.provider,
                repository_root=args.repository_root,
                route_name=args.route,
                model=args.model,
                authorize_model_calls=args.authorize_model_calls,
                max_physical_model_calls=args.max_model_calls,
                max_total_tokens=args.max_total_tokens,
                timeout_seconds=args.timeout,
                evidence_path=args.evidence_out,
            ),
            load_scenarios(tasks_dir),
        )
    except LiveModelVerificationError as exc:
        print(f"Live text scenarios refused before completion: {exc}")
        return 2

    for scenario in result["scenarios"]:
        print(
            f"{scenario['scenario_id']}: {scenario['status']} | "
            f"decision={scenario['observed_status'] or 'invalid'} | "
            f"calls={scenario['physical_model_calls']}")
    print(
        f"Live suite: {result['status']} | "
        f"compiled={len(compiled)} | "
        f"provider={result['provider']} | model={result['model']} | "
        f"calls={result['physical_model_calls']} | "
        f"evidence={result['evidence_path']}")
    return 0 if result["provider_integration_proven"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
