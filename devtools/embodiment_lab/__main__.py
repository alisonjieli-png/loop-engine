"""Create, qualify, run and compare independent embodiment experiments."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import platform
import time
from pathlib import Path

from .catalog import IMPLEMENTED, inventory, select
from .context import ExperimentContext
from .contracts import RunPolicy, TaskCase, WorkPacket, canonical, digest
from .storage import ResultRecorder, confined_root, write_new
from .study import generate, load, qualify


def source_identity() -> dict:
    root = Path(__file__).parent
    files = {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.py"))
        if "__pycache__" not in p.parts
    }
    return {
        "digest": digest(files),
        "files": files,
        "python": platform.python_version(),
    }


def run_experiment(
    name: str, study: Path, output: Path, policy: RunPolicy, limit: int | None = None
) -> dict:
    embodiment = select(name)
    cases = load(study)
    if limit is not None:
        if limit < 1:
            raise ValueError("case limit must be positive")
        cases = cases[:limit]
    root = confined_root(output, create=True)
    packets = tuple(WorkPacket(case.case_id, case) for case in cases)
    manifest = {
        "record_type": "embodiment_run/v1",
        "variant": name,
        "source": source_identity(),
        "study_digest": digest(json.loads((study / "manifest.json").read_text())),
        "selected_case_ids": [c.case_id for c in cases],
        "policy": {"seconds": policy.seconds, "concurrency": policy.concurrency},
        "evidence_class": "deterministic_mechanism",
        "model_authorized": False,
        "network_authorized": False,
        "isolation": "trusted_fixture_processes_not_a_security_sandbox",
    }
    write_new(root / "run-manifest.json", manifest)
    recorder = ResultRecorder(root)
    context = ExperimentContext(root, policy, recorder)
    error = None
    try:
        asyncio.run(embodiment.runner(packets, context))
    except Exception as exc:  # noqa: BLE001 - preserve unexpected trial failures in the denominator.
        error = type(exc).__name__ + ": " + str(exc)[:200]
    finally:
        recorder.close()
    observed = {r["case_id"] for r in context.rows}
    for packet in packets:
        if packet.task.case_id not in observed:
            context.failure(packet, RuntimeError(error or "no_result_returned"))
    accepted = {r["case_id"] for r in context.rows if r["accepted"]}
    unchanged = source_identity()["digest"] == manifest["source"]["digest"]
    result = {
        "record_type": "embodiment_comparison_row/v1",
        "variant": name,
        "evidence_class": "deterministic_mechanism",
        "tasks": len(cases),
        "verified_tasks": len(accepted),
        "candidate_attempts": len(context.rows),
        "failed_candidates": sum(not r["accepted"] for r in context.rows),
        "duration_seconds": time.monotonic() - context.started,
        "distinct_worker_pids": sorted(
            {r["pid"] for r in context.rows if r.get("pid")}
        ),
        "model_calls": 0
        if all(r.get("model_calls") == 0 for r in context.rows)
        else None,
        "source_unchanged": unchanged,
        "error": error,
        "passed": bool(cases)
        and len(accepted) == len(cases)
        and not error
        and unchanged,
        "rows": context.rows,
        "manifest_digest": digest(manifest),
    }
    write_new(root / "result.json", result)
    return result


def summary(result: dict) -> dict:
    return {k: v for k, v in result.items() if k != "rows"}


def main(argv=None, fixed_variant=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    for command in ("snapshot-reference", "prepare-reference"):
        p = sub.add_parser(command)
        p.add_argument("--source", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
    create = sub.add_parser("create")
    create.add_argument("--out", type=Path, required=True)
    create.add_argument("--count", type=int, default=1000)
    create.add_argument("--seed", type=int, default=7301)
    check = sub.add_parser("qualify")
    check.add_argument("--study", type=Path, required=True)
    check.add_argument("--out", type=Path)
    serving = sub.add_parser("view")
    serving.add_argument("--run", type=Path, required=True)
    serving.add_argument("--task", type=Path, required=True)
    serving.add_argument(
        "--view", choices=("best", "all_verified", "random"), default="best"
    )
    serving.add_argument("--seed", type=int, default=0)
    serving.add_argument("--version", type=int)
    for command in ("run", "compare"):
        p = sub.add_parser(command)
        if command == "run" and fixed_variant is None:
            p.add_argument("--variant", required=True)
        p.add_argument("--study", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        p.add_argument("--seconds", type=float, default=60)
        p.add_argument("--concurrency", type=int, default=2)
        p.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            value = inventory()
        elif args.command in ("snapshot-reference", "prepare-reference"):
            from .reference_sources import prepare, snapshot

            value = (
                snapshot(args.source, args.out)
                if args.command == "snapshot-reference"
                else prepare(args.source, args.out)
            )
            if args.command == "snapshot-reference":
                value = {
                    k: v
                    for k, v in value.items()
                    if k not in ("files", "excluded", "dirty_state_at_snapshot")
                }
        elif args.command == "create":
            manifest = generate(args.out, args.count, args.seed)
            value = {
                "path": str(args.out),
                "tasks": manifest["count"],
                "digest": digest(manifest),
            }
        elif args.command == "qualify":
            value = qualify(load(args.study))
            if args.out:
                write_new(args.out, value)
            print(canonical({k: v for k, v in value.items() if k != "checks"}))
            return 0 if value["passed"] else 1
        elif args.command == "view":
            from .serving import view

            value = view(
                args.run,
                TaskCase.from_dict(json.loads(args.task.read_text())),
                {"view": args.view, "seed": args.seed, "version": args.version},
            )
        else:
            policy = RunPolicy(args.seconds, args.concurrency)
            if args.command == "run":
                result = run_experiment(
                    fixed_variant or args.variant,
                    args.study,
                    args.out,
                    policy,
                    args.limit,
                )
                print(canonical(summary(result)))
                return 0 if result["passed"] else 1
            root = confined_root(args.out, create=True)
            value = [
                summary(
                    run_experiment(
                        item.name, args.study, root / item.folder, policy, args.limit
                    )
                )
                for item in IMPLEMENTED
            ]
            write_new(root / "comparison.json", value)
            print(canonical(value))
            return 0 if all(v["passed"] for v in value) else 1
        print(canonical(value))
        return 0
    except Exception as exc:  # noqa: BLE001 - the CLI returns a named refusal, never a false pass.
        print(
            canonical(
                {
                    "status": "refused",
                    "error": type(exc).__name__,
                    "reason": str(exc)[:400],
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
