"""What a run measured: queries planned and executed, raw and unique results, licence leads, routes, yield and decay.

Counts stay separate, as the evidence rules require: combinations examined, queries planned, requests sent,
responses stored, queries executed (stored and parsed 200), raw result rows, distinct candidates, candidates whose
reported licence is on the allowlist, and rows routed to each line. None of them is a package count: a candidate is
a lead that its line must still read, decide the licence of and check.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict

from .evidence import Ledger, parse_stamp


def _by(rows):
    return {row[0]: row[1] for row in rows}


def yield_curve(ledger: Ledger, executor_id: str, bucket: int, run_id: "str | None" = None) -> list:
    """Mean new distinct candidates per executed query, in buckets of executions in time order."""
    where = "and run_id=?" if run_id else ""
    rows = ledger.rows("select new_unique, items from attempts where executor_id=? and state='folded' and parse_status in "
                       f"('ok','empty','partial') {where} order by started_at, attempt_id",
                       (executor_id, run_id) if run_id else (executor_id,))
    curve = []
    for start in range(0, len(rows), bucket):
        part = rows[start:start + bucket]
        curve.append({"executions": f"{start + 1}-{start + len(part)}", "mean_new_unique": round(statistics.mean(r[0] or 0 for r in part), 2),
                      "mean_rows": round(statistics.mean(r[1] or 0 for r in part), 2),
                      "unique_share": round(sum(r[0] or 0 for r in part) / max(1, sum(r[1] or 0 for r in part)), 3)})
    return curve


def decay_fit(curve: list) -> "float | None":
    """Least-squares slope of log(mean new unique) per bucket: negative means yield decays as the product is explored."""
    points = [(index, math.log(row["mean_new_unique"])) for index, row in enumerate(curve) if row["mean_new_unique"] > 0]
    if len(points) < 3:
        return None
    mean_x = statistics.mean(x for x, _ in points)
    mean_y = statistics.mean(y for _, y in points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    return round(sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator, 4) if denominator else None


def report(ledger: Ledger, executors: dict, *, run_id: "str | None" = None, products=None, bucket: int = 25) -> dict:
    run_filter = "where run_id=?" if run_id else ""
    args = (run_id,) if run_id else ()
    attempts = ledger.rows("select executor_id, state, http_status, parse_status, items, new_unique, cost, started_at "
                           f"from attempts {run_filter}", args)
    per = defaultdict(lambda: defaultdict(int))
    first, last = None, None
    for executor_id, state, status, parse_status, items, new_unique, cost, started in attempts:
        row = per[executor_id]
        row["requests_sent"] += 1
        row["cost_units"] += cost or 0
        row["responses_stored"] += state in ("stored", "folded")
        row["not_stored"] += state in ("not_stored", "abandoned_unknown_outcome", "intent")
        executed = state == "folded" and parse_status in ("ok", "empty", "partial")
        row["queries_executed"] += executed
        row["empty_executions"] += executed and parse_status == "empty"
        row["raw_results"] += items or 0
        row["new_unique_candidates"] += new_unique or 0
        row["http_" + str(status)] += 1
        stamp_ = parse_stamp(started)
        first = stamp_ if first is None or stamp_ < first else first
        last = stamp_ if last is None or stamp_ > last else last
    hours = max((last - first).total_seconds() / 3600, 1e-9) if first and last else None
    cursors = ledger.rows("select product_id, examined, emitted, excluded, duplicates from cursors")
    planned = _by(ledger.rows("select executor_id, count(*) from queries group by executor_id"))
    executed_total = _by(ledger.rows("select executor_id, count(*) from queries where state='executed' group by executor_id"))
    total_candidates = ledger.scalar("select count(*) from candidates")
    allowlisted = ledger.scalar("select count(*) from candidates where allowlisted=1")
    reported = ledger.scalar("select count(*) from candidates where licence_reported is not null")
    by_kind = {row[0]: {"candidates": row[1], "allowlisted": row[2], "licence_reported": row[3]}
               for row in ledger.rows("select kind, count(*), sum(allowlisted), sum(licence_reported is not null) "
                                      "from candidates group by kind")}
    by_executor = {row[0]: {"candidates_first_found": row[1], "allowlisted": row[2]}
                   for row in ledger.rows("select first_executor, count(*), sum(allowlisted) from candidates group by first_executor")}
    routes = {row[0]: {"candidates": row[1], "allowlisted": row[2]}
              for row in ledger.rows("select route, count(*), sum(allowlisted) from candidates group by route order by 2 desc")}
    basis = _by(ledger.rows("select licence_basis, count(*) from candidates group by licence_basis order by 2 desc"))
    multi = ledger.scalar("select count(*) from candidates where origins > 1")
    lanes = {}
    for executor_id, row in sorted(per.items()):
        executor = executors.get(executor_id)
        curve = yield_curve(ledger, executor_id, bucket, run_id)
        recent = curve[-1]["mean_new_unique"] if curve else 0.0
        overall = row["new_unique_candidates"] / row["queries_executed"] if row["queries_executed"] else 0.0
        steady = steady_requests_per_day(executor, row, hours) if executor else None
        lanes[executor_id] = {**dict(row), "queries_planned_in_ledger": planned.get(executor_id, 0),
                              "queries_executed_all_runs": executed_total.get(executor_id, 0),
                              "unique_per_executed_query": round(overall, 2), "yield_curve": curve,
                              "log_yield_slope_per_bucket": decay_fit(curve),
                              "steady_requests_per_day": steady,
                              "projected_new_unique_per_day_at_recent_yield": round(steady * recent) if steady else None}
    projection = project(lanes)
    product_space = None
    if products is not None:
        product_space = {"products": len(products), "virtual_product_total": sum(product.total for product in products),
                         "by_executor": {}}
        for product in products:
            entry = product_space["by_executor"].setdefault(product.executor_id, 0)
            product_space["by_executor"][product.executor_id] = entry + product.total
    exclusions = defaultdict(int)
    examined = emitted = duplicates = 0
    import json as _json
    for _, ex, em, excluded, dup in cursors:
        examined += ex or 0
        emitted += em or 0
        duplicates += dup or 0
        for reason, count in _json.loads(excluded or "{}").items():
            exclusions[reason] += count
    return {"record_type": "research_query_report/v1", "run_id": run_id,
            "window": {"first_request": first.isoformat() if first else None, "last_request": last.isoformat() if last else None,
                       "hours": round(hours, 3) if hours else None},
            "planning": {"combinations_examined": examined, "queries_emitted": emitted,
                         "skipped_within_refresh_period": duplicates, "excluded": dict(exclusions),
                         "product_space": product_space},
            "lanes": lanes,
            "candidates": {"distinct": total_candidates, "found_by_more_than_one_query": multi,
                           "licence_reported": reported, "reported_licence_on_allowlist": allowlisted,
                           "allowlisted_share": round(allowlisted / total_candidates, 4) if total_candidates else None,
                           "licence_basis": basis, "by_kind": by_kind, "by_first_executor": by_executor},
            "routes": routes, "projection": projection}


def steady_requests_per_day(executor, row, hours) -> "float | None":
    """Requests a day this lane sustains: the interval, the daily ceiling (in requests), and the observed rate."""
    by_interval = 86400 / executor.minimum_interval
    ceiling = executor.daily_ceiling
    if ceiling is not None and executor.cost_unit != "request":
        mean_cost = row["cost_units"] / max(1, row["requests_sent"])
        ceiling = ceiling / max(1.0, mean_cost)
    observed = row["requests_sent"] / hours * 24 if hours and hours > 0.25 else None
    candidates = [value for value in (by_interval, ceiling) if value is not None]
    steady = min(candidates)
    if observed is not None and ceiling is None:
        # The observed rate includes waits for shared allowances; it is the honest steady rate.
        steady = min(steady, observed)
    return round(steady, 1)


def project(lanes: dict) -> dict:
    daily = sum(lane["projected_new_unique_per_day_at_recent_yield"] or 0 for lane in lanes.values())
    slopes = [lane["log_yield_slope_per_bucket"] for lane in lanes.values() if lane["log_yield_slope_per_bucket"] is not None]
    return {"new_unique_per_day_at_recent_yield": daily, "new_unique_per_30_days_without_decay": daily * 30,
            "median_log_yield_slope_per_bucket": statistics.median(slopes) if slopes else None,
            "note": "Recent yield is the mean new distinct candidates per executed query in each lane's last bucket. The 30-day figure "
                    "assumes no further decay and is an upper bound when the slope is negative; candidates are leads, not packages."}
