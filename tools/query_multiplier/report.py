"""What a run measured: queries planned and executed, raw and unique results, licence leads, routes, yield and decay.

Counts stay separate, as the evidence rules require: combinations examined, queries planned, requests sent,
responses stored, queries executed (stored and parsed 200), raw result rows, distinct candidates, candidates whose
reported licence is on the allowlist, and rows routed to each line. None of them is a package count: a candidate is
a lead that its line must still read, decide the licence of and check.
"""
from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict

from .evidence import Ledger, parse_stamp
from .executors import EMPTY, OK, PARTIAL


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
        curve.append({"executions": f"{start + 1}-{start + len(part)}", "count": len(part),
                      "mean_new_unique": round(statistics.mean(r[0] or 0 for r in part), 2),
                      "mean_rows": round(statistics.mean(r[1] or 0 for r in part), 2),
                      "unique_share": round(sum(r[0] or 0 for r in part) / max(1, sum(r[1] or 0 for r in part)), 3)})
    return curve


def product_yields(ledger: Ledger, run_id: "str | None" = None) -> dict:
    """Yield per product, and per dimension with and without its value: the global baseline (a null geography)
    against country or region queries answers the October 1 review's open question with measured numbers."""
    where = "and a.run_id=?" if run_id else ""
    rows = ledger.rows("select q.product_id, q.assignment, a.items, a.new_unique, a.parse_status from attempts a "
                       "join queries q using(query_id) where a.state='folded' and a.parse_status in ('ok','empty','partial') "
                       f"and q.origin='product' {where}", (run_id,) if run_id else ())
    products = defaultdict(lambda: [0, 0, 0, 0])
    presence = defaultdict(lambda: [0, 0, 0])
    for product_id, assignment, items, new_unique, status in rows:
        entry = products[product_id]
        entry[0] += 1
        entry[1] += status == EMPTY
        entry[2] += new_unique or 0
        entry[3] += items or 0
        for name, value in json.loads(assignment or "{}").items():
            key = (name, "with_value" if value is not None else "null")
            presence[key][0] += 1
            presence[key][1] += status == EMPTY
            presence[key][2] += new_unique or 0
    by_product = {name: {"executions": n, "empty_share": round(empty / n, 3), "new_unique_per_execution": round(new / n, 2),
                         "rows_per_execution": round(rows_ / n, 2)} for name, (n, empty, new, rows_) in sorted(products.items())}
    by_dimension = defaultdict(dict)
    for (name, side), (n, empty, new) in sorted(presence.items()):
        by_dimension[name][side] = {"executions": n, "empty_share": round(empty / n, 3), "new_unique_per_execution": round(new / n, 2)}
    return {"by_product": by_product, "by_dimension_presence": dict(by_dimension)}


def decay_fit(curve: list) -> "float | None":
    """Least-squares slope of log(mean new unique) per bucket: negative means yield decays as the product is explored."""
    points = [(index, math.log(row["mean_new_unique"])) for index, row in enumerate(curve) if row["mean_new_unique"] > 0]
    if len(points) < 3:
        return None
    mean_x = statistics.mean(x for x, _ in points)
    mean_y = statistics.mean(y for _, y in points)
    denominator = sum((x - mean_x) ** 2 for x, _ in points)
    return round(sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator, 4) if denominator else None


def report(ledger: Ledger, executors: dict, *, run_id: "str | None" = None, products=None, bucket: int = 25,
           duty_hours: float = 16.0) -> dict:
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
        executed = state == "folded" and parse_status in (OK, EMPTY, PARTIAL)
        row["queries_executed"] += executed
        row["empty_executions"] += executed and parse_status == EMPTY
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
        overall = row["new_unique_candidates"] / row["queries_executed"] if row["queries_executed"] else 0.0
        lanes[executor_id] = {**dict(row), "queries_planned_in_ledger": planned.get(executor_id, 0),
                              "queries_executed_all_runs": executed_total.get(executor_id, 0),
                              "unique_per_executed_query": round(overall, 2), "yield_curve": curve,
                              "log_yield_slope_per_bucket": decay_fit(curve),
                              "projection": lane_projection(executor, row, curve, hours, bucket, duty_hours)
                              if executor else None}
    projection = project(lanes, duty_hours)
    product_space = None
    if products is not None:
        product_space = {"products": len(products), "virtual_product_total": sum(product.total for product in products),
                         "by_executor": {}}
        for product in products:
            entry = product_space["by_executor"].setdefault(product.executor_id, 0)
            product_space["by_executor"][product.executor_id] = entry + product.total
    exclusions = defaultdict(int)
    examined = emitted = duplicates = 0
    for _, ex, em, excluded, dup in cursors:
        examined += ex or 0
        emitted += em or 0
        duplicates += dup or 0
        for reason, count in json.loads(excluded or "{}").items():
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
            "routes": routes, "projection": projection, "yields": product_yields(ledger, run_id)}


def lane_projection(executor, row, curve, hours, bucket, duty_hours) -> dict:
    """Steady requests a day for this lane and the new distinct candidates they would bring.

    Rate: the lower of the observed request rate (it includes every wait for shared allowances) and the lane's
    interval, over the scheduled hours a day, then the lane's daily ceiling. Yield: the mean new distinct
    candidates per executed query over the last quarter of this pass's executions. Upper bound: that yield held
    for a day and for thirty. Lower bound: the yield keeps the decay fitted over this pass's buckets, per
    execution, integrated over thirty days of executions.
    """
    observed = row["requests_sent"] / hours if hours and hours >= 0.5 else None
    by_interval = 3600 / executor.minimum_interval
    rate = min(observed, by_interval) if observed is not None else by_interval
    requests = rate * duty_hours
    ceiling = executor.daily_ceiling
    if ceiling is not None:
        mean_cost = row["cost_units"] / max(1, row["requests_sent"]) if executor.cost_unit != "request" else 1.0
        requests = min(requests, ceiling / max(1.0, mean_cost))
    executed_share = row["queries_executed"] / row["requests_sent"] if row["requests_sent"] else 0.0
    executions = requests * executed_share
    # A partial last bucket is too small to stand for the lane's current yield; only complete buckets count.
    complete = [point for point in curve if point["count"] == bucket] or curve
    quarter = max(1, len(complete) // 4)
    recent = statistics.mean(point["mean_new_unique"] for point in complete[-quarter:]) if complete else 0.0
    slope = decay_fit(complete)
    per_execution = min(0.0, slope / bucket) if slope is not None else 0.0
    month = executions * 30
    lower = (recent * (1 - math.exp(per_execution * month)) / -per_execution) if per_execution < 0 else recent * month
    return {"requests_per_day": round(requests), "executions_per_day": round(executions),
            "recent_new_unique_per_execution": round(recent, 2),
            "new_unique_per_day_upper": round(executions * recent),
            "new_unique_per_30_days_upper": round(executions * recent * 30),
            "new_unique_per_30_days_lower_with_fitted_decay": round(lower)}


def project(lanes: dict, duty_hours: float) -> dict:
    rows = [lane["projection"] for lane in lanes.values() if lane.get("projection")]
    return {"scheduled_hours_per_day": duty_hours,
            "new_unique_per_day_upper": sum(row["new_unique_per_day_upper"] for row in rows),
            "new_unique_per_30_days_upper": sum(row["new_unique_per_30_days_upper"] for row in rows),
            "new_unique_per_30_days_lower_with_fitted_decay": sum(row["new_unique_per_30_days_lower_with_fitted_decay"] for row in rows),
            "note": "Upper: the last quarter's yield per executed query held. Lower: each lane's yield decays at the rate "
                    "fitted over this pass, per execution, for thirty days. Candidates are leads, not packages; "
                    "shared allowances can lower every rate."}
