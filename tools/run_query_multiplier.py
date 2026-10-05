"""Baltor's query multiplier: preview a plan, run its probes within every limit, import earlier queues, report.

    PYTHONPATH=src:tools python tools/run_query_multiplier.py plan --show 3
    PYTHONPATH=src:tools python tools/run_query_multiplier.py run --root ~/baltor-library/query-runs --minutes 120 \\
        --authorize-network-reads --authorize-local-writes
    PYTHONPATH=src:tools python tools/run_query_multiplier.py import --root ~/baltor-library/query-runs \\
        --sdg-planned-searches FILE --public-good-bank FILE --authorize-local-writes
    PYTHONPATH=src:tools python tools/run_query_multiplier.py report --root ~/baltor-library/query-runs

`plan` sends nothing and writes nothing. `run` needs both grants: network reads (public, non-confidential vocabulary
only) and private local writes under --root, which must be outside the repository. No model is called.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "src", ROOT / "tools", ROOT):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from query_multiplier import importers  # noqa: E402
from query_multiplier.dimensions import load_library  # noqa: E402
from query_multiplier.evidence import Ledger, stamp  # noqa: E402
from query_multiplier.executors import registry  # noqa: E402
from query_multiplier.planner import coverage, describe, load_plan, plan_dimensions, query_at  # noqa: E402
from query_multiplier.report import report  # noqa: E402
from query_multiplier.runner import Run  # noqa: E402
from query_multiplier.transport import Transport, load_policy  # noqa: E402

DEFAULT_PLAN = ROOT / "tools" / "query_multiplier" / "plans" / "default-v1.json"
DEFAULT_ONET = Path.home() / "loop-engine-data" / "onet" / "31.0" / "text"


def _roots(values) -> dict:
    roots = {"onet": str(DEFAULT_ONET)}
    for value in values or ():
        name, _, path = value.partition("=")
        roots[name] = path
    return roots


def _load(options):
    plan_path = Path(options.plan)
    library = load_library(data_roots=_roots(options.data_root), only=plan_dimensions(plan_path))
    executors = registry()
    products = load_plan(plan_path, library, executors)
    return library, executors, products, json.loads(plan_path.read_bytes())


def command_plan(options) -> dict:
    library, executors, products, _ = _load(options)
    out = {"library": {"version": library.version, "digest": library.digest,
                       "dimensions": {name: len(dimension.values) for name, dimension in library.dimensions.items()}},
           "products": describe(products), "virtual_product_total": sum(product.total for product in products),
           "executors": {name: executor.describe() for name, executor in executors.items()}}
    if options.show:
        samples = {}
        for product in products:
            rows, excluded, k = [], {}, 0
            executor = executors[product.executor_id]
            while len(rows) < options.show and k < 5000:
                query, reason = query_at(product, k, library, executor)
                k += 1
                if query is None:
                    excluded[reason] = excluded.get(reason, 0) + 1
                    continue
                rows.append({"k": query.k, "query_id": query.query_id[:16], "request": query.request})
            samples[product.id] = {"queries": rows, "excluded_before_these": excluded,
                                   "coverage_first_1000": coverage(product, range(1000))}
        out["samples"] = samples
    return out


def command_run(options) -> dict:
    if not (options.authorize_network_reads and options.authorize_local_writes):
        raise PermissionError("run_requires_network_and_local_write_grants")
    library, executors, products, plan = _load(options)
    ledger = Ledger(Path(options.root))
    transport = Transport(load_policy())
    run = Run(library=library, products=products, executors=executors, transport=transport, ledger=ledger,
              minutes=options.minutes, only=set(options.only) if options.only else None,
              imported_weight=plan.get("imported_plans_weight", 0) if not options.no_imported else 0)
    started = time.time()
    final = run.execute()
    summary = report(ledger, executors, run_id=run.run_id, products=products)
    summary["status"] = final
    summary["elapsed_minutes"] = round((time.time() - started) / 60, 2)
    path = ledger.day_folder() / f"run-{run.run_id}.json"
    path.write_text(json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8")
    ledger.write_status({**final, "report": str(path), "finished_at": stamp()})
    ledger.close()
    return {"run_id": run.run_id, "report": str(path), "state": final["state"],
            "executed": {name: lane["queries_executed"] for name, lane in summary["lanes"].items()},
            "distinct_candidates": summary["candidates"]["distinct"]}


def command_import(options) -> dict:
    if not options.authorize_local_writes:
        raise PermissionError("import_requires_local_write_grant")
    ledger = Ledger(Path(options.root))
    importer = importers.Importer(ledger)
    with ledger.lock:
        if options.sdg_planned_searches:
            importers.import_sdg_planned_searches(importer, Path(options.sdg_planned_searches))
        if options.public_good_bank:
            importers.import_public_good_bank(importer, Path(options.public_good_bank))
        if options.keyword_matrix:
            importers.import_keyword_matrix(importer, Path(options.keyword_matrix))
    out = {"counts": dict(importer.counts), "ledger": importers.summary(ledger)}
    ledger.close()
    return out


def command_report(options) -> dict:
    ledger = Ledger(Path(options.root))
    products = None
    executors = registry()
    if options.with_plan:
        _, executors, products, _ = _load(options)
    out = report(ledger, executors, run_id=options.run_id, products=products, bucket=options.bucket,
                 duty_hours=options.duty_hours)
    ledger.close()
    return out


def command_proposals(options) -> dict:
    from query_multiplier.routing import proposals
    ledger = Ledger(Path(options.root))
    value = proposals(ledger, allowlisted_only=not options.include_unlisted)
    folder = ledger.day_folder() / "proposals"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / ("proposals-" + stamp().replace(":", "") + ".json")
    path.write_text(json.dumps(value, indent=1, sort_keys=True), encoding="utf-8")
    ledger.close()
    return {"proposals": str(path), "counts": value["counts"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run", "import", "report", "proposals"):
        command = sub.add_parser(name)
        command.add_argument("--plan", default=str(DEFAULT_PLAN))
        command.add_argument("--data-root", action="append", help="name=path for a table outside the repository (onet=...)")
        if name != "plan":
            command.add_argument("--root", required=True, help="private folder outside the repository")
    sub.choices["plan"].add_argument("--show", type=int, default=0)
    run = sub.choices["run"]
    run.add_argument("--minutes", type=float, default=30.0)
    run.add_argument("--only", action="append", help="executor id; repeat to select several")
    run.add_argument("--no-imported", action="store_true")
    run.add_argument("--authorize-network-reads", action="store_true")
    run.add_argument("--authorize-local-writes", action="store_true")
    imported = sub.choices["import"]
    imported.add_argument("--sdg-planned-searches")
    imported.add_argument("--public-good-bank")
    imported.add_argument("--keyword-matrix")
    imported.add_argument("--authorize-local-writes", action="store_true")
    reporting = sub.choices["report"]
    reporting.add_argument("--run-id")
    reporting.add_argument("--bucket", type=int, default=25)
    reporting.add_argument("--with-plan", action="store_true")
    reporting.add_argument("--duty-hours", type=float, default=16.0, help="scheduled probing hours a day (hourly 40-minute passes: 16)")
    sub.choices["proposals"].add_argument("--include-unlisted", action="store_true",
                                          help="also rows whose reported licence is not on the allowlist")
    options = parser.parse_args(argv)
    try:
        result = {"plan": command_plan, "run": command_run, "import": command_import, "report": command_report,
                  "proposals": command_proposals}[options.command](options)
    except (ValueError, PermissionError, OSError) as error:
        print(json.dumps({"status": "refused", "error_class": type(error).__name__, "detail": str(error)[:300]}))
        return 2
    print(json.dumps(result, indent=1, sort_keys=True, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
