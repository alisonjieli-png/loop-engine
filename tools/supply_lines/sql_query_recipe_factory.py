"""Template 4: Deterministic SQLite Analytical Query Recipe Factory (gen-sql-query-recipes).

Generates 50 parameterized SQLite analytical query recipe component packages across
5 analytical categories (10 recipes per category):
1. window_functions (rolling sums, ranks, lead/lag deltas, cumulative shares)
2. retention_cohorts (day-N retention, cohort survival, reactivation, churn)
3. pareto_percentiles (cost quantiles, latency buckets, top-K Pareto concentration)
4. gap_and_island_sessions (sessionization, streak detection, outage windows)
5. dag_rollups (recursive CTE critical paths, sub-DAG cost rollups, barrier readiness)

Every generated component includes:
- implement.py: parameterized sqlite3 execution with strict parameter validation and read-only SQL guard
- test_implement.py: live in-memory sqlite3 fixture verification, parameter refusal tests, and known-wrong controls
- SKILL.md and harness integration guides (claude-code, codex, cursor, opencode)
- LICENSE (MIT) and ATTRIBUTION.md
- CataloguePackage with SHA-256 digests and local preview metadata, not an admission record
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys
from typing import Any

_REPO_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _REPO_SRC not in sys.path:
    sys.path.insert(0, _REPO_SRC)

from loop_engine.core.service_runtime.catalogue_packages import (
    PACKAGE_BODY,
    CataloguePackage,
    CataloguePackageFile,
    sha256_hex,
)

FACTORY_ID = "gen-sql-query-recipes"
FACTORY_VERSION = "1.0.0"
GENERATED_ON = "2026-10-13"

MIT_LICENSE_TEXT = (
    "MIT License\n\n"
    "Copyright (c) 2026 Alie Jie Li\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy "
    "of this software and associated documentation files (the \"Software\"), to deal "
    "in the Software without restriction, including without limitation the rights "
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
    "copies of the Software, and to permit persons to whom the Software is "
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all "
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR "
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, "
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE "
    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER "
    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, "
    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE "
    "SOFTWARE.\n"
)

CATEGORIES = (
    "window_functions",
    "retention_cohorts",
    "pareto_percentiles",
    "gap_and_island_sessions",
    "dag_rollups",
)

SHARED_FIXTURE_DDL_AND_SEED = """
CREATE TABLE agent_runs (
    run_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    slot_id TEXT NOT NULL,
    day TEXT NOT NULL,
    epoch_sec INTEGER NOT NULL,
    cost_usd REAL NOT NULL,
    duration_ms INTEGER NOT NULL,
    tokens_in INTEGER NOT NULL,
    tokens_out INTEGER NOT NULL,
    succeeded INTEGER NOT NULL
);

INSERT INTO agent_runs VALUES
    ('r01', 'agent_a', 'slot_code', '2026-10-01', 1000, 0.10, 400, 1000, 200, 1),
    ('r02', 'agent_a', 'slot_code', '2026-10-01', 1120, 0.20, 600, 1500, 300, 1),
    ('r03', 'agent_a', 'slot_code', '2026-10-02', 2000, 0.15, 500, 1200, 250, 0),
    ('r04', 'agent_a', 'slot_code', '2026-10-03', 5000, 0.35, 900, 2000, 400, 1),
    ('r05', 'agent_b', 'slot_code', '2026-10-01', 1050, 0.50, 1200, 3000, 600, 1),
    ('r06', 'agent_b', 'slot_sql',  '2026-10-02', 1150, 0.80, 1500, 4000, 800, 1),
    ('r07', 'agent_b', 'slot_sql',  '2026-10-04', 8000, 0.40, 700, 1800, 350, 0),
    ('r08', 'agent_c', 'slot_sql',  '2026-10-01', 1080, 1.50, 2500, 6000, 1200, 1),
    ('r09', 'agent_c', 'slot_doc',  '2026-10-02', 2100, 0.05, 200, 500, 100, 1),
    ('r10', 'agent_c', 'slot_doc',  '2026-10-03', 2200, 0.25, 450, 1100, 220, 1);

CREATE TABLE dag_tasks (
    task_id TEXT PRIMARY KEY,
    parent_id TEXT,
    dag_id TEXT NOT NULL,
    layer_idx INTEGER NOT NULL,
    status TEXT NOT NULL,
    est_seconds INTEGER NOT NULL,
    actual_cost_usd REAL NOT NULL
);

INSERT INTO dag_tasks VALUES
    ('t1', NULL, 'dag_alpha', 0, 'COMPLETED', 30, 0.05),
    ('t2', 't1', 'dag_alpha', 1, 'COMPLETED', 60, 0.12),
    ('t3', 't1', 'dag_alpha', 1, 'COMPLETED', 45, 0.08),
    ('t4', 't2', 'dag_alpha', 2, 'COMPLETED', 90, 0.25),
    ('t5', 't3', 'dag_alpha', 2, 'FAILED',    50, 0.15),
    ('t6', NULL, 'dag_beta',  0, 'COMPLETED', 40, 0.10),
    ('t7', 't6', 'dag_beta',  1, 'RUNNING',   80, 0.20);
"""


@dataclass(frozen=True)
class SQLQueryRecipeSpec:
    component_id: str
    category: str
    title: str
    description: str
    sql: str
    param_names: tuple[str, ...]
    default_params: dict[str, Any]
    expected_first_row: dict[str, Any]
    expected_row_count: int


def _build_specs() -> tuple[SQLQueryRecipeSpec, ...]:
    specs: list[SQLQueryRecipeSpec] = [
        # --- Category 1: window_functions (10 recipes) ---
        SQLQueryRecipeSpec(
            "sql-window-agent-cumulative-cost",
            "window_functions",
            "Window cumulative agent cost by run order",
            "Computes running cumulative USD spend per agent ordered by epoch_sec.",
            "SELECT run_id, agent_id, ROUND(SUM(cost_usd) OVER (PARTITION BY agent_id ORDER BY epoch_sec ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_cost FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"run_id": "r01", "agent_id": "agent_a", "running_cost": 0.1},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-window-slot-duration-rank",
            "window_functions",
            "Window dense rank of run duration within slot",
            "Ranks runs inside an engine slot from slowest to fastest using DENSE_RANK.",
            "SELECT run_id, slot_id, duration_ms, DENSE_RANK() OVER (PARTITION BY slot_id ORDER BY duration_ms DESC) AS dur_rank FROM agent_runs WHERE slot_id = :slot_id ORDER BY dur_rank, run_id",
            ("slot_id",),
            {"slot_id": "slot_code"},
            {"run_id": "r05", "slot_id": "slot_code", "duration_ms": 1200, "dur_rank": 1},
            5,
        ),
        SQLQueryRecipeSpec(
            "sql-window-lag-cost-delta",
            "window_functions",
            "Window LAG cost delta between consecutive runs",
            "Computes the cost change from the immediately preceding run of the same agent.",
            "SELECT run_id, ROUND(cost_usd - COALESCE(LAG(cost_usd, 1) OVER (PARTITION BY agent_id ORDER BY epoch_sec), 0.0), 2) AS cost_delta FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"run_id": "r01", "cost_delta": 0.1},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-window-lead-next-epoch-gap",
            "window_functions",
            "Window LEAD time gap to next agent invocation",
            "Computes seconds elapsed until the next run for the specified agent.",
            "SELECT run_id, COALESCE(LEAD(epoch_sec, 1) OVER (PARTITION BY agent_id ORDER BY epoch_sec) - epoch_sec, 0) AS sec_to_next FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"run_id": "r01", "sec_to_next": 120},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-window-moving-avg-duration",
            "window_functions",
            "Window 2-run moving average duration",
            "Calculates a 2-row trailing moving average of duration_ms per agent.",
            "SELECT run_id, ROUND(AVG(duration_ms) OVER (PARTITION BY agent_id ORDER BY epoch_sec ROWS BETWEEN 1 PRECEDING AND CURRENT ROW), 1) AS moving_avg_ms FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"run_id": "r01", "moving_avg_ms": 400.0},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-window-slot-cost-share",
            "window_functions",
            "Window percentage share of slot spend",
            "Computes each run's percentage share of total slot spend using SUM() OVER (PARTITION BY slot_id).",
            "SELECT run_id, ROUND(100.0 * cost_usd / SUM(cost_usd) OVER (PARTITION BY slot_id), 1) AS slot_cost_pct FROM agent_runs WHERE slot_id = :slot_id ORDER BY run_id",
            ("slot_id",),
            {"slot_id": "slot_doc"},
            {"run_id": "r09", "slot_cost_pct": 16.7},
            2,
        ),
        SQLQueryRecipeSpec(
            "sql-window-first-last-run-comparison",
            "window_functions",
            "Window FIRST_VALUE and LAST_VALUE token comparison",
            "Compares each run's tokens_in against the first observed run for that agent.",
            "SELECT run_id, tokens_in, FIRST_VALUE(tokens_in) OVER (PARTITION BY agent_id ORDER BY epoch_sec) AS first_tokens_in FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_b"},
            {"run_id": "r05", "tokens_in": 3000, "first_tokens_in": 3000},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-window-row-number-latest-per-slot",
            "window_functions",
            "Window ROW_NUMBER latest execution per slot",
            "Selects the most recent execution in each engine slot using ROW_NUMBER().",
            "WITH ranked AS (SELECT run_id, slot_id, epoch_sec, ROW_NUMBER() OVER (PARTITION BY slot_id ORDER BY epoch_sec DESC) AS rn FROM agent_runs WHERE succeeded >= :min_succeeded) SELECT slot_id, run_id, epoch_sec FROM ranked WHERE rn = 1 ORDER BY slot_id",
            ("min_succeeded",),
            {"min_succeeded": 0},
            {"slot_id": "slot_code", "run_id": "r04", "epoch_sec": 5000},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-window-ntile-quartile-tokens",
            "window_functions",
            "Window NTILE(4) token consumption quartiles",
            "Assigns all runs matching a minimum token threshold into 4 NTILE quartiles.",
            "SELECT run_id, tokens_in, NTILE(4) OVER (ORDER BY tokens_in ASC, run_id ASC) AS token_quartile FROM agent_runs WHERE tokens_in >= :min_tokens ORDER BY tokens_in ASC, run_id ASC",
            ("min_tokens",),
            {"min_tokens": 500},
            {"run_id": "r09", "tokens_in": 500, "token_quartile": 1},
            10,
        ),
        SQLQueryRecipeSpec(
            "sql-window-running-success-rate",
            "window_functions",
            "Window running empirical success rate",
            "Computes the cumulative success rate per agent across sequential invocations.",
            "SELECT run_id, ROUND(AVG(CAST(succeeded AS REAL)) OVER (PARTITION BY agent_id ORDER BY epoch_sec ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_yield FROM agent_runs WHERE agent_id = :agent_id ORDER BY epoch_sec",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"run_id": "r01", "running_yield": 1.0},
            4,
        ),
        # --- Category 2: retention_cohorts (10 recipes) ---
        SQLQueryRecipeSpec(
            "sql-cohort-first-seen-day",
            "retention_cohorts",
            "Cohort first-seen activation day per agent",
            "Identifies each agent's initial activation date and total lifetime runs.",
            "SELECT agent_id, MIN(day) AS cohort_day, COUNT(*) AS lifetime_runs FROM agent_runs WHERE succeeded >= :min_succeeded GROUP BY agent_id ORDER BY agent_id",
            ("min_succeeded",),
            {"min_succeeded": 0},
            {"agent_id": "agent_a", "cohort_day": "2026-10-01", "lifetime_runs": 4},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-daily-active-agents",
            "retention_cohorts",
            "Cohort daily active agents and run volume",
            "Counts distinct active agents and total runs per calendar day on or after start_day.",
            "SELECT day, COUNT(DISTINCT agent_id) AS active_agents, COUNT(*) AS total_runs FROM agent_runs WHERE day >= :start_day GROUP BY day ORDER BY day",
            ("start_day",),
            {"start_day": "2026-10-01"},
            {"day": "2026-10-01", "active_agents": 3, "total_runs": 4},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-day1-retention-rate",
            "retention_cohorts",
            "Cohort next-day retention matrix",
            "Checks whether agents active on cohort_day returned on return_day.",
            "WITH d0 AS (SELECT DISTINCT agent_id FROM agent_runs WHERE day = :cohort_day), d1 AS (SELECT DISTINCT agent_id FROM agent_runs WHERE day = :return_day) SELECT COUNT(d0.agent_id) AS cohort_size, COUNT(d1.agent_id) AS retained_agents FROM d0 LEFT JOIN d1 ON d0.agent_id = d1.agent_id",
            ("cohort_day", "return_day"),
            {"cohort_day": "2026-10-01", "return_day": "2026-10-02"},
            {"cohort_size": 3, "retained_agents": 3},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-day2-retention-rate",
            "retention_cohorts",
            "Cohort day-2 survival check",
            "Measures how many agents from cohort_day remained active on day_plus_2.",
            "WITH d0 AS (SELECT DISTINCT agent_id FROM agent_runs WHERE day = :cohort_day), d2 AS (SELECT DISTINCT agent_id FROM agent_runs WHERE day = :day_plus_2) SELECT COUNT(d0.agent_id) AS cohort_size, COUNT(d2.agent_id) AS retained_day2 FROM d0 LEFT JOIN d2 ON d0.agent_id = d2.agent_id",
            ("cohort_day", "day_plus_2"),
            {"cohort_day": "2026-10-01", "day_plus_2": "2026-10-03"},
            {"cohort_size": 3, "retained_day2": 2},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-slot-adoption-breadth",
            "retention_cohorts",
            "Cohort multi-slot adoption breadth per agent",
            "Counts distinct engine slots exercised by each agent with at least min_runs.",
            "SELECT agent_id, COUNT(DISTINCT slot_id) AS distinct_slots, COUNT(*) AS run_count FROM agent_runs GROUP BY agent_id HAVING COUNT(*) >= :min_runs ORDER BY distinct_slots DESC, agent_id ASC",
            ("min_runs",),
            {"min_runs": 2},
            {"agent_id": "agent_b", "distinct_slots": 2, "run_count": 3},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-repeat-success-retention",
            "retention_cohorts",
            "Cohort repeat verified-success agents",
            "Lists agents achieving at least min_successes verified completions.",
            "SELECT agent_id, SUM(succeeded) AS verified_successes, COUNT(*) AS total_attempts FROM agent_runs GROUP BY agent_id HAVING SUM(succeeded) >= :min_successes ORDER BY verified_successes DESC, agent_id ASC",
            ("min_successes",),
            {"min_successes": 2},
            {"agent_id": "agent_a", "verified_successes": 3, "total_attempts": 4},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-reactivation-after-gap",
            "retention_cohorts",
            "Cohort reactivation after missed day",
            "Finds agents that had a gap of more than 1 day between consecutive active days.",
            "WITH days AS (SELECT DISTINCT agent_id, day FROM agent_runs), lagged AS (SELECT agent_id, day, LAG(day) OVER (PARTITION BY agent_id ORDER BY day) AS prev_day FROM days) SELECT agent_id, prev_day, day AS reactivated_day FROM lagged WHERE prev_day IS NOT NULL AND JULIANDAY(day) - JULIANDAY(prev_day) >= :min_gap_days ORDER BY agent_id",
            ("min_gap_days",),
            {"min_gap_days": 2},
            {"agent_id": "agent_b", "prev_day": "2026-10-02", "reactivated_day": "2026-10-04"},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-slot-retention-by-day",
            "retention_cohorts",
            "Cohort daily slot utilization matrix",
            "Summarizes daily active runs and success count for a specific slot.",
            "SELECT day, COUNT(*) AS runs, SUM(succeeded) AS successes FROM agent_runs WHERE slot_id = :slot_id GROUP BY day ORDER BY day",
            ("slot_id",),
            {"slot_id": "slot_code"},
            {"day": "2026-10-01", "runs": 3, "successes": 3},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-active-day-span",
            "retention_cohorts",
            "Cohort active calendar span per agent",
            "Computes active day span between first and last observed run for each agent.",
            "SELECT agent_id, MIN(day) AS first_day, MAX(day) AS last_day, CAST(JULIANDAY(MAX(day)) - JULIANDAY(MIN(day)) + 1 AS INTEGER) AS span_days FROM agent_runs WHERE tokens_in >= :min_tokens GROUP BY agent_id ORDER BY agent_id",
            ("min_tokens",),
            {"min_tokens": 100},
            {"agent_id": "agent_a", "first_day": "2026-10-01", "last_day": "2026-10-03", "span_days": 3},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-cohort-failure-recovery-rate",
            "retention_cohorts",
            "Cohort post-failure recovery verification",
            "Finds failed runs and checks whether the same agent succeeded on a subsequent run.",
            "SELECT f.run_id AS failed_run, f.agent_id, COUNT(s.run_id) AS subsequent_successes FROM agent_runs f LEFT JOIN agent_runs s ON f.agent_id = s.agent_id AND s.epoch_sec > f.epoch_sec AND s.succeeded = 1 WHERE f.succeeded = :failed_flag GROUP BY f.run_id, f.agent_id ORDER BY f.run_id",
            ("failed_flag",),
            {"failed_flag": 0},
            {"failed_run": "r03", "agent_id": "agent_a", "subsequent_successes": 1},
            2,
        ),
        # --- Category 3: pareto_percentiles (10 recipes) ---
        SQLQueryRecipeSpec(
            "sql-pareto-cumulative-cost-share",
            "pareto_percentiles",
            "Pareto cumulative spend concentration curve",
            "Orders runs from highest to lowest cost and computes cumulative share of total spend.",
            "SELECT run_id, cost_usd, ROUND(SUM(cost_usd) OVER (ORDER BY cost_usd DESC, run_id ASC) / SUM(cost_usd) OVER (), 3) AS cum_cost_share FROM agent_runs WHERE cost_usd >= :min_cost ORDER BY cost_usd DESC, run_id ASC",
            ("min_cost",),
            {"min_cost": 0.01},
            {"run_id": "r08", "cost_usd": 1.5, "cum_cost_share": 0.349},
            10,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-top-k-expensive-runs",
            "pareto_percentiles",
            "Pareto top-K highest cost executions",
            "Returns the top K costliest runs with their token-to-cost efficiency.",
            "SELECT run_id, agent_id, cost_usd, tokens_out FROM agent_runs ORDER BY cost_usd DESC, run_id ASC LIMIT :top_k",
            ("top_k",),
            {"top_k": 3},
            {"run_id": "r08", "agent_id": "agent_c", "cost_usd": 1.5, "tokens_out": 1200},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-duration-percent-rank",
            "pareto_percentiles",
            "Pareto PERCENT_RANK latency distribution",
            "Computes PERCENT_RANK() of duration_ms across runs for latency percentile auditing.",
            "SELECT run_id, duration_ms, ROUND(PERCENT_RANK() OVER (ORDER BY duration_ms ASC), 2) AS pct_rank FROM agent_runs WHERE duration_ms >= :min_duration_ms ORDER BY duration_ms ASC, run_id ASC",
            ("min_duration_ms",),
            {"min_duration_ms": 100},
            {"run_id": "r09", "duration_ms": 200, "pct_rank": 0.0},
            10,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-cume-dist-tokens",
            "pareto_percentiles",
            "Pareto CUME_DIST input token distribution",
            "Computes cumulative distribution CUME_DIST() of input tokens across runs.",
            "SELECT run_id, tokens_in, ROUND(CUME_DIST() OVER (ORDER BY tokens_in ASC), 2) AS cume_dist_val FROM agent_runs WHERE tokens_in >= :min_tokens ORDER BY tokens_in ASC, run_id ASC",
            ("min_tokens",),
            {"min_tokens": 100},
            {"run_id": "r09", "tokens_in": 500, "cume_dist_val": 0.1},
            10,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-cost-per-1k-output-tokens",
            "pareto_percentiles",
            "Pareto USD cost per 1,000 output tokens",
            "Ranks runs by normalized cost per 1,000 generated output tokens.",
            "SELECT run_id, slot_id, ROUND((cost_usd * 1000.0) / tokens_out, 3) AS usd_per_1k_out FROM agent_runs WHERE tokens_out >= :min_tokens_out ORDER BY usd_per_1k_out ASC, run_id ASC",
            ("min_tokens_out",),
            {"min_tokens_out": 100},
            {"run_id": "r01", "slot_id": "slot_code", "usd_per_1k_out": 0.5},
            10,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-slot-spend-concentration",
            "pareto_percentiles",
            "Pareto spend concentration by engine slot",
            "Aggregates total spend, average latency, and spend share by slot_id.",
            "SELECT slot_id, COUNT(*) AS runs, ROUND(SUM(cost_usd), 2) AS total_cost_usd, ROUND(AVG(duration_ms), 1) AS avg_ms FROM agent_runs WHERE cost_usd >= :min_cost GROUP BY slot_id ORDER BY total_cost_usd DESC",
            ("min_cost",),
            {"min_cost": 0.0},
            {"slot_id": "slot_sql", "runs": 3, "total_cost_usd": 2.7, "avg_ms": 1566.7},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-agent-spend-pareto-ratio",
            "pareto_percentiles",
            "Pareto agent spend and yield leaderboard",
            "Summarizes total spend, total tokens, and success count per agent.",
            "SELECT agent_id, ROUND(SUM(cost_usd), 2) AS spend_usd, SUM(tokens_in + tokens_out) AS total_tokens, SUM(succeeded) AS successes FROM agent_runs WHERE succeeded >= :min_succeeded GROUP BY agent_id ORDER BY spend_usd DESC",
            ("min_succeeded",),
            {"min_succeeded": 0},
            {"agent_id": "agent_c", "spend_usd": 1.8, "total_tokens": 9120, "successes": 3},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-latency-bucket-histogram",
            "pareto_percentiles",
            "Pareto latency bucket histogram",
            "Groups runs into fast (<500ms), medium (500-1199ms), and slow (>=1200ms) latency buckets.",
            "SELECT CASE WHEN duration_ms < 500 THEN 'fast_lt_500ms' WHEN duration_ms < 1200 THEN 'medium_500_1199ms' ELSE 'slow_gte_1200ms' END AS latency_bucket, COUNT(*) AS run_count FROM agent_runs WHERE duration_ms >= :min_ms GROUP BY latency_bucket ORDER BY latency_bucket",
            ("min_ms",),
            {"min_ms": 0},
            {"latency_bucket": "fast_lt_500ms", "run_count": 3},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-outlier-runs-above-multiple",
            "pareto_percentiles",
            "Pareto cost outlier detector vs slot average",
            "Finds runs whose cost exceeds a configurable multiple of their slot's mean cost.",
            "WITH slot_avg AS (SELECT run_id, slot_id, cost_usd, AVG(cost_usd) OVER (PARTITION BY slot_id) AS mean_slot_cost FROM agent_runs) SELECT run_id, slot_id, cost_usd, ROUND(mean_slot_cost, 2) AS mean_slot_cost FROM slot_avg WHERE cost_usd >= mean_slot_cost * :multiplier ORDER BY cost_usd DESC",
            ("multiplier",),
            {"multiplier": 1.5},
            {"run_id": "r08", "slot_id": "slot_sql", "cost_usd": 1.5, "mean_slot_cost": 0.9},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-pareto-p90-latency-candidates",
            "pareto_percentiles",
            "Pareto P80+ tail latency filter",
            "Extracts tail-latency runs at or above the 80th percentile of duration_ms.",
            "WITH dist AS (SELECT run_id, duration_ms, CUME_DIST() OVER (ORDER BY duration_ms ASC) AS cd FROM agent_runs) SELECT run_id, duration_ms, ROUND(cd, 2) AS cd FROM dist WHERE cd >= :min_cume_dist ORDER BY duration_ms DESC",
            ("min_cume_dist",),
            {"min_cume_dist": 0.8},
            {"run_id": "r08", "duration_ms": 2500, "cd": 1.0},
            3,
        ),
        # --- Category 4: gap_and_island_sessions (10 recipes) ---
        SQLQueryRecipeSpec(
            "sql-session-island-by-inactivity-threshold",
            "gap_and_island_sessions",
            "Gap-and-island sessionization by inactivity gap",
            "Groups agent runs into discrete sessions whenever elapsed time exceeds max_idle_sec.",
            "WITH step1 AS (SELECT run_id, agent_id, epoch_sec, CASE WHEN epoch_sec - LAG(epoch_sec) OVER (PARTITION BY agent_id ORDER BY epoch_sec) <= :max_idle_sec THEN 0 ELSE 1 END AS is_new_session FROM agent_runs WHERE agent_id = 'agent_a'), step2 AS (SELECT run_id, epoch_sec, SUM(is_new_session) OVER (ORDER BY epoch_sec) AS session_num FROM step1) SELECT session_num, COUNT(*) AS runs_in_session, MIN(epoch_sec) AS start_sec, MAX(epoch_sec) AS end_sec FROM step2 GROUP BY session_num ORDER BY session_num",
            ("max_idle_sec",),
            {"max_idle_sec": 300},
            {"session_num": 1, "runs_in_session": 2, "start_sec": 1000, "end_sec": 1120},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-session-consecutive-success-streaks",
            "gap_and_island_sessions",
            "Gap-and-island consecutive success streaks",
            "Measures contiguous streaks of succeeded=1 runs across global chronological order.",
            "WITH tagged AS (SELECT run_id, epoch_sec, succeeded, ROW_NUMBER() OVER (ORDER BY epoch_sec) - ROW_NUMBER() OVER (PARTITION BY succeeded ORDER BY epoch_sec) AS grp FROM agent_runs) SELECT MIN(run_id) AS first_run, COUNT(*) AS streak_len FROM tagged WHERE succeeded = :target_succeeded GROUP BY grp ORDER BY MIN(epoch_sec)",
            ("target_succeeded",),
            {"target_succeeded": 1},
            {"first_run": "r01", "streak_len": 5},
            2,
        ),
        SQLQueryRecipeSpec(
            "sql-session-slot-continuity-islands",
            "gap_and_island_sessions",
            "Gap-and-island contiguous slot execution islands",
            "Groups consecutive runs that stayed on the same slot_id without context switching.",
            "WITH tagged AS (SELECT run_id, slot_id, epoch_sec, ROW_NUMBER() OVER (ORDER BY epoch_sec) - ROW_NUMBER() OVER (PARTITION BY slot_id ORDER BY epoch_sec) AS island_id FROM agent_runs WHERE epoch_sec >= :min_epoch) SELECT slot_id, COUNT(*) AS contiguous_runs, MIN(epoch_sec) AS island_start FROM tagged GROUP BY slot_id, island_id ORDER BY island_start",
            ("min_epoch",),
            {"min_epoch": 1000},
            {"slot_id": "slot_code", "contiguous_runs": 2, "island_start": 1000},
            8,
        ),
        SQLQueryRecipeSpec(
            "sql-session-inter-arrival-time-summary",
            "gap_and_island_sessions",
            "Gap-and-island inter-arrival time statistics",
            "Calculates min, max, and average gap in seconds between consecutive runs of an agent.",
            "WITH gaps AS (SELECT epoch_sec - LAG(epoch_sec) OVER (PARTITION BY agent_id ORDER BY epoch_sec) AS gap_sec FROM agent_runs WHERE agent_id = :agent_id) SELECT COUNT(gap_sec) AS transitions, MIN(gap_sec) AS min_gap_sec, MAX(gap_sec) AS max_gap_sec FROM gaps WHERE gap_sec IS NOT NULL",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"transitions": 3, "min_gap_sec": 120, "max_gap_sec": 3000},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-session-burst-detection-window",
            "gap_and_island_sessions",
            "Gap-and-island burst invocation detector",
            "Finds pairs of runs occurring within burst_window_sec of each other.",
            "SELECT a.run_id AS first_run, b.run_id AS second_run, (b.epoch_sec - a.epoch_sec) AS delta_sec FROM agent_runs a JOIN agent_runs b ON a.run_id <> b.run_id AND b.epoch_sec >= a.epoch_sec AND (b.epoch_sec - a.epoch_sec) <= :burst_window_sec AND a.epoch_sec < b.epoch_sec ORDER BY delta_sec ASC, a.run_id ASC",
            ("burst_window_sec",),
            {"burst_window_sec": 60},
            {"first_run": "r02", "second_run": "r06", "delta_sec": 30},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-session-daily-activity-islands",
            "gap_and_island_sessions",
            "Gap-and-island contiguous active calendar days",
            "Groups an agent's active calendar dates into unbroken daily streaks.",
            "WITH d AS (SELECT DISTINCT day FROM agent_runs WHERE agent_id = :agent_id), numbered AS (SELECT day, JULIANDAY(day) - ROW_NUMBER() OVER (ORDER BY day) AS grp FROM d) SELECT MIN(day) AS streak_start, MAX(day) AS streak_end, COUNT(*) AS days_in_streak FROM numbered GROUP BY grp ORDER BY streak_start",
            ("agent_id",),
            {"agent_id": "agent_a"},
            {"streak_start": "2026-10-01", "streak_end": "2026-10-03", "days_in_streak": 3},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-session-idle-gap-alerts",
            "gap_and_island_sessions",
            "Gap-and-island long idle gap detector",
            "Lists transitions where an agent was idle for at least min_idle_sec seconds.",
            "WITH lagged AS (SELECT run_id, agent_id, epoch_sec, LAG(epoch_sec) OVER (PARTITION BY agent_id ORDER BY epoch_sec) AS prev_sec FROM agent_runs) SELECT run_id, agent_id, (epoch_sec - prev_sec) AS idle_sec FROM lagged WHERE prev_sec IS NOT NULL AND (epoch_sec - prev_sec) >= :min_idle_sec ORDER BY idle_sec DESC",
            ("min_idle_sec",),
            {"min_idle_sec": 1000},
            {"run_id": "r07", "agent_id": "agent_b", "idle_sec": 6850},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-session-agent-handoff-transitions",
            "gap_and_island_sessions",
            "Gap-and-island cross-agent handoff transitions",
            "Counts chronological transitions from one agent_id to another.",
            "WITH seq AS (SELECT agent_id AS from_agent, LEAD(agent_id) OVER (ORDER BY epoch_sec, run_id) AS to_agent FROM agent_runs WHERE epoch_sec >= :min_epoch) SELECT from_agent, to_agent, COUNT(*) AS handoffs FROM seq WHERE to_agent IS NOT NULL AND from_agent <> to_agent GROUP BY from_agent, to_agent ORDER BY handoffs DESC, from_agent ASC, to_agent ASC",
            ("min_epoch",),
            {"min_epoch": 1000},
            {"from_agent": "agent_a", "to_agent": "agent_b", "handoffs": 3},
            5,
        ),
        SQLQueryRecipeSpec(
            "sql-session-cost-per-session-island",
            "gap_and_island_sessions",
            "Gap-and-island total spend per global work window",
            "Buckets all runs into global work islands separated by gaps > gap_threshold_sec.",
            "WITH step1 AS (SELECT run_id, epoch_sec, cost_usd, CASE WHEN epoch_sec - LAG(epoch_sec) OVER (ORDER BY epoch_sec) <= :gap_threshold_sec THEN 0 ELSE 1 END AS new_win FROM agent_runs), step2 AS (SELECT run_id, cost_usd, SUM(new_win) OVER (ORDER BY epoch_sec) AS win_id FROM step1) SELECT win_id, COUNT(*) AS runs, ROUND(SUM(cost_usd), 2) AS window_cost FROM step2 GROUP BY win_id ORDER BY win_id",
            ("gap_threshold_sec",),
            {"gap_threshold_sec": 500},
            {"win_id": 1, "runs": 5, "window_cost": 3.1},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-session-failure-cluster-islands",
            "gap_and_island_sessions",
            "Gap-and-island failure vs success island summary",
            "Aggregates contiguous islands of identical succeeded status with total token load.",
            "WITH tagged AS (SELECT run_id, epoch_sec, succeeded, tokens_in, ROW_NUMBER() OVER (ORDER BY epoch_sec) - ROW_NUMBER() OVER (PARTITION BY succeeded ORDER BY epoch_sec) AS grp FROM agent_runs) SELECT succeeded, COUNT(*) AS island_size, SUM(tokens_in) AS island_tokens_in FROM tagged WHERE tokens_in >= :min_tokens GROUP BY succeeded, grp ORDER BY MIN(epoch_sec)",
            ("min_tokens",),
            {"min_tokens": 100},
            {"succeeded": 1, "island_size": 5, "island_tokens_in": 15500},
            4,
        ),
        # --- Category 5: dag_rollups (10 recipes) ---
        SQLQueryRecipeSpec(
            "sql-dag-recursive-critical-path",
            "dag_rollups",
            "DAG recursive CTE critical path duration",
            "Computes cumulative estimated seconds from root to leaf along every path in dag_id.",
            "WITH RECURSIVE paths AS (SELECT task_id, parent_id, est_seconds AS path_seconds, task_id AS path_trace FROM dag_tasks WHERE dag_id = :dag_id AND parent_id IS NULL UNION ALL SELECT c.task_id, c.parent_id, p.path_seconds + c.est_seconds, p.path_trace || '->' || c.task_id FROM dag_tasks c JOIN paths p ON c.parent_id = p.task_id WHERE c.dag_id = :dag_id) SELECT task_id, path_seconds, path_trace FROM paths ORDER BY path_seconds DESC, task_id ASC",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"task_id": "t4", "path_seconds": 180, "path_trace": "t1->t2->t4"},
            5,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-subtree-cost-rollup",
            "dag_rollups",
            "DAG recursive subtree spend rollup",
            "Computes the total actual_cost_usd of a root task and all of its descendants.",
            "WITH RECURSIVE sub AS (SELECT task_id, actual_cost_usd FROM dag_tasks WHERE task_id = :root_task_id UNION ALL SELECT c.task_id, c.actual_cost_usd FROM dag_tasks c JOIN sub s ON c.parent_id = s.task_id) SELECT COUNT(*) AS subtree_nodes, ROUND(SUM(actual_cost_usd), 2) AS subtree_cost_usd FROM sub",
            ("root_task_id",),
            {"root_task_id": "t1"},
            {"subtree_nodes": 5, "subtree_cost_usd": 0.65},
            1,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-layer-concurrency-width",
            "dag_rollups",
            "DAG topological layer width and cost summary",
            "Counts parallel tasks and total estimated seconds per topological layer_idx.",
            "SELECT layer_idx, COUNT(*) AS layer_width, SUM(est_seconds) AS layer_est_sec, ROUND(SUM(actual_cost_usd), 2) AS layer_cost FROM dag_tasks WHERE dag_id = :dag_id GROUP BY layer_idx ORDER BY layer_idx",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"layer_idx": 0, "layer_width": 1, "layer_est_sec": 30, "layer_cost": 0.05},
            3,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-status-breakdown-by-dag",
            "dag_rollups",
            "DAG task status completion breakdown",
            "Summarizes completed, failed, and running node counts for a specified DAG.",
            "SELECT status, COUNT(*) AS task_count, ROUND(SUM(actual_cost_usd), 2) AS status_cost FROM dag_tasks WHERE dag_id = :dag_id GROUP BY status ORDER BY status",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"status": "COMPLETED", "task_count": 4, "status_cost": 0.5},
            2,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-leaf-node-finder",
            "dag_rollups",
            "DAG terminal leaf node extractor",
            "Finds all terminal leaf tasks in a DAG that have no child dependents.",
            "SELECT t.task_id, t.layer_idx, t.status FROM dag_tasks t LEFT JOIN dag_tasks c ON c.parent_id = t.task_id WHERE t.dag_id = :dag_id AND c.task_id IS NULL ORDER BY t.task_id",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"task_id": "t4", "layer_idx": 2, "status": "COMPLETED"},
            2,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-root-node-summary",
            "dag_rollups",
            "DAG entry root node inventory",
            "Lists all root tasks (parent_id IS NULL) across DAGs with at least min_est_seconds.",
            "SELECT task_id, dag_id, status, est_seconds FROM dag_tasks WHERE parent_id IS NULL AND est_seconds >= :min_est_seconds ORDER BY task_id",
            ("min_est_seconds",),
            {"min_est_seconds": 10},
            {"task_id": "t1", "dag_id": "dag_alpha", "status": "COMPLETED", "est_seconds": 30},
            2,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-fanout-degree-ranking",
            "dag_rollups",
            "DAG parent fan-out degree ranking",
            "Counts direct child dependents per parent task within a DAG.",
            "SELECT p.task_id, COUNT(c.task_id) AS child_count FROM dag_tasks p LEFT JOIN dag_tasks c ON c.parent_id = p.task_id WHERE p.dag_id = :dag_id GROUP BY p.task_id ORDER BY child_count DESC, p.task_id ASC",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"task_id": "t1", "child_count": 2},
            5,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-parent-readiness-barrier-check",
            "dag_rollups",
            "DAG child readiness check against parent status",
            "Verifies whether each child task's parent has reached COMPLETED status.",
            "SELECT c.task_id AS child_id, p.task_id AS parent_id, p.status AS parent_status, CASE WHEN p.status = 'COMPLETED' THEN 1 ELSE 0 END AS parent_ready FROM dag_tasks c JOIN dag_tasks p ON c.parent_id = p.task_id WHERE c.dag_id = :dag_id ORDER BY c.task_id",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"child_id": "t2", "parent_id": "t1", "parent_status": "COMPLETED", "parent_ready": 1},
            4,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-ancestor-chain-depth",
            "dag_rollups",
            "DAG recursive ancestor depth verification",
            "Computes exact hop depth from root for every node in a DAG and compares with layer_idx.",
            "WITH RECURSIVE depth_cte AS (SELECT task_id, layer_idx, 0 AS computed_depth FROM dag_tasks WHERE dag_id = :dag_id AND parent_id IS NULL UNION ALL SELECT c.task_id, c.layer_idx, d.computed_depth + 1 FROM dag_tasks c JOIN depth_cte d ON c.parent_id = d.task_id WHERE c.dag_id = :dag_id) SELECT task_id, layer_idx, computed_depth FROM depth_cte ORDER BY task_id",
            ("dag_id",),
            {"dag_id": "dag_alpha"},
            {"task_id": "t1", "layer_idx": 0, "computed_depth": 0},
            5,
        ),
        SQLQueryRecipeSpec(
            "sql-dag-portfolio-completion-ratio",
            "dag_rollups",
            "DAG portfolio completion rate and spend",
            "Aggregates completion ratio and total spend across all DAGs with at least min_nodes.",
            "SELECT dag_id, COUNT(*) AS total_nodes, ROUND(AVG(CASE WHEN status = 'COMPLETED' THEN 1.0 ELSE 0.0 END), 2) AS completion_ratio, ROUND(SUM(actual_cost_usd), 2) AS total_cost FROM dag_tasks GROUP BY dag_id HAVING COUNT(*) >= :min_nodes ORDER BY dag_id",
            ("min_nodes",),
            {"min_nodes": 2},
            {"dag_id": "dag_alpha", "total_nodes": 5, "completion_ratio": 0.8, "total_cost": 0.65},
            2,
        ),
    ]
    return tuple(specs)


SQL_QUERY_RECIPE_SPECS: tuple[SQLQueryRecipeSpec, ...] = _build_specs()


def _render_implement_py(spec: SQLQueryRecipeSpec) -> bytes:
    code = f'''"""Deterministic SQLite analytical query recipe: {spec.component_id}."""
from __future__ import annotations

import re
import sqlite3
import math
from typing import Any

COMPONENT_ID = {spec.component_id!r}
CATEGORY = {spec.category!r}
SQL_QUERY = {spec.sql!r}
REQUIRED_PARAMS = {spec.param_names!r}
DEFAULT_PARAMS = {spec.default_params!r}
FIXTURE_SCRIPT = {SHARED_FIXTURE_DDL_AND_SEED!r}

_UNSAFE_PARAM_RE = re.compile(r"(?i)(?:--|;|/\\*|\\*/|\\b(?:drop|alter|attach|detach|pragma|vacuum)\\b)")


def _validate_params(params: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(params, dict):
        raise ValueError("params_must_be_dict")
    missing = [name for name in REQUIRED_PARAMS if name not in params]
    if missing:
        raise ValueError(f"missing_required_params: {{missing}}")
    extra = [name for name in params if name not in REQUIRED_PARAMS]
    if extra:
        raise ValueError(f"unexpected_params: {{extra}}")
    cleaned: dict[str, Any] = {{}}
    for key, val in params.items():
        if val is None or isinstance(val, bool):
            raise ValueError(f"invalid_param_type: {{key}}")
        if isinstance(val, str):
            if len(val) == 0 or len(val) > 128 or _UNSAFE_PARAM_RE.search(val):
                raise ValueError(f"unsafe_or_invalid_string_param: {{key}}")
            cleaned[key] = val
        elif isinstance(val, (int, float)):
            if not math.isfinite(val) or abs(val) > 1000000:
                raise ValueError(f"numeric_param_out_of_bounds: {{key}}")
            cleaned[key] = val
        else:
            raise ValueError(f"unsupported_param_type: {{key}}")
    return cleaned


def create_fixture_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(FIXTURE_SCRIPT)
    return conn


def run_query(
    params: dict[str, Any] | None = None,
    connection: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
    effective = dict(DEFAULT_PARAMS) if params is None else _validate_params(params)
    if params is None:
        effective = _validate_params(effective)
    owns_conn = connection is None
    conn = create_fixture_connection() if owns_conn else connection
    assert conn is not None
    try:
        cursor = conn.cursor()
        cursor.row_factory = sqlite3.Row
        cursor.execute(SQL_QUERY, effective)
        rows = cursor.fetchmany(1025)
        if len(rows) > 1024:
            raise ValueError("result_row_limit_exceeded")
        return [dict(row) for row in rows]
    finally:
        if owns_conn:
            conn.close()
'''
    return code.encode("utf-8")


def _render_test_implement_py(spec: SQLQueryRecipeSpec) -> bytes:
    first_param = spec.param_names[0]
    code = f'''"""Unit tests for {spec.component_id}."""
from __future__ import annotations

import unittest

from implement import DEFAULT_PARAMS, run_query


class SQLRecipeTests(unittest.TestCase):
    def test_default_fixture_query_matches_expected(self) -> None:
        rows = run_query(DEFAULT_PARAMS)
        self.assertEqual(len(rows), {spec.expected_row_count})
        self.assertEqual(rows[0], {spec.expected_first_row!r})

    def test_rejects_missing_or_unsafe_parameters(self) -> None:
        with self.assertRaises(ValueError):
            run_query({{}})
        bad = dict(DEFAULT_PARAMS)
        bad[{first_param!r}] = "x'; DROP TABLE agent_runs; --"
        with self.assertRaises(ValueError):
            run_query(bad)

    def test_known_wrong_control_detected(self) -> None:
        rows = run_query(DEFAULT_PARAMS)
        with self.assertRaises(AssertionError):
            self.assertEqual(rows[0], {{"__known_wrong__": True}})


if __name__ == "__main__":
    unittest.main()
'''
    return code.encode("utf-8")


def _render_skill_md(spec: SQLQueryRecipeSpec) -> bytes:
    params_list = ", ".join(f"`:{p}`" for p in spec.param_names)
    text = (
        f"---\n"
        f"name: {spec.component_id}\n"
        f"description: {spec.description}\n"
        f"---\n\n"
        f"# {spec.title}\n\n"
        f"Category: `{spec.category}`.\n"
        f"Bound parameters: {params_list}.\n\n"
        f"## SQL Query\n\n"
        f"```sql\n{spec.sql}\n```\n"
    )
    return text.encode("utf-8")


def _render_integration_md(spec: SQLQueryRecipeSpec, harness_name: str) -> bytes:
    text = (
        f"# {spec.title} ({harness_name} integration)\n\n"
        f"Import `run_query` from `implement.py` in `{harness_name}` to execute the "
        f"parameterized analytical SQLite query with bound parameter checks.\n"
    )
    return text.encode("utf-8")


def execute_sql_query_recipe(component_id: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Execute a SQL query recipe component against its in-memory SQLite fixture."""
    comp = build_sql_query_recipe_component(component_id)
    namespace: dict[str, Any] = {}
    exec(compile(comp["file_bodies"]["implement.py"].decode("utf-8"), "implement.py", "exec"), namespace)
    return namespace["run_query"](params)


def build_sql_query_recipe_component(spec_or_id: SQLQueryRecipeSpec | str) -> dict[str, Any]:
    """Build a local package preview, not a library admission record for a SQL query recipe."""
    if isinstance(spec_or_id, str):
        spec_map = {item.component_id: item for item in SQL_QUERY_RECIPE_SPECS}
        if spec_or_id not in spec_map:
            raise KeyError(f"unknown_sql_query_recipe: {spec_or_id!r}")
        spec = spec_map[spec_or_id]
    else:
        spec = spec_or_id
    if not isinstance(spec, SQLQueryRecipeSpec) or spec not in SQL_QUERY_RECIPE_SPECS:
        raise ValueError("unregistered_factory_spec")

    attribution = (
        f"# Attribution\n\n"
        f"Generated deterministically by `{FACTORY_ID}` version `{FACTORY_VERSION}` on {GENERATED_ON}.\n"
        f"Engine: Python standard library `sqlite3` (public-domain SQLite engine).\n"
        f"Licence: MIT.\n"
    ).encode("utf-8")

    raw_files = [
        ("implement.py", _render_implement_py(spec), "text/x-python", "skill_script"),
        ("test_implement.py", _render_test_implement_py(spec), "text/x-python", "skill_reference"),
        ("SKILL.md", _render_skill_md(spec), "text/markdown", "skill_definition"),
        ("integrate/claude-code.md", _render_integration_md(spec, "claude_code"), "text/markdown", "skill_reference"),
        ("integrate/codex.md", _render_integration_md(spec, "codex"), "text/markdown", "skill_reference"),
        ("integrate/cursor.md", _render_integration_md(spec, "cursor"), "text/markdown", "skill_reference"),
        ("integrate/opencode.md", _render_integration_md(spec, "opencode"), "text/markdown", "skill_reference"),
        ("LICENSE", MIT_LICENSE_TEXT.encode("utf-8"), "text/plain", "other"),
        ("ATTRIBUTION.md", attribution, "text/markdown", "other"),
    ]

    entries: list[CataloguePackageFile] = []
    file_bodies: dict[str, bytes] = {}
    for path, data, mtype, role in raw_files:
        file_bodies[path] = data
        entries.append(CataloguePackageFile(path, sha256_hex(data), len(data), mtype, role))

    package = CataloguePackage(tuple(entries), PACKAGE_BODY)
    return {
        "build_state": "local_package_preview",
        "admission_ready": False,
        "factory_id": FACTORY_ID,
        "component_id": spec.component_id,
        "category": spec.category,
        "title": spec.title,
        "param_names": list(spec.param_names),
        "description": spec.description,
        "licence": "MIT",
        "catalogue_package": package.to_dict(),
        "package_digest": package.package_digest,
        "file_bodies": file_bodies,
        "approved": False,
        "published": False,
        "effects_granted": [],
        "lifecycle": "candidate",
        "qualification": "not_independently_reviewed",
    }


def verify_sql_query_recipe_component(component: dict[str, Any]) -> dict[str, Any]:
    """Execute generated implement.py against in-memory SQLite and verify rows, parameter refusal, and known-wrong control."""
    comp_id = component["component_id"]
    spec = {item.component_id: item for item in SQL_QUERY_RECIPE_SPECS}[comp_id]
    canonical = build_sql_query_recipe_component(comp_id)
    if component != canonical:
        raise ValueError("noncanonical_factory_package")
    namespace: dict[str, Any] = {}
    exec(compile(canonical["file_bodies"]["implement.py"].decode("utf-8"), "implement.py", "exec"), namespace)
    run_fn = namespace["run_query"]

    rows = run_fn(spec.default_params)
    pos_ok = len(rows) == spec.expected_row_count and rows[0] == spec.expected_first_row

    neg_ok = True
    try:
        run_fn({})
        neg_ok = False
    except ValueError:
        pass

    bad_params = dict(spec.default_params)
    bad_params[spec.param_names[0]] = "1; DROP TABLE agent_runs; --"
    try:
        run_fn(bad_params)
        neg_ok = False
    except ValueError:
        pass

    known_wrong_ok = rows[0] != {"__known_wrong__": True}
    passed = bool(pos_ok and neg_ok and known_wrong_ok)
    return {
        "component_id": comp_id,
        "category": spec.category,
        "passed": passed,
        "row_count": len(rows),
        "positive_fixture_passed": pos_ok,
        "negative_injection_refused": neg_ok,
        "known_wrong_control_passed": known_wrong_ok,
    }


def build_all_sql_query_recipe_components() -> list[dict[str, Any]]:
    """Build all 50 deterministic SQLite analytical query recipe components."""
    return [build_sql_query_recipe_component(spec) for spec in SQL_QUERY_RECIPE_SPECS]


__all__ = [
    "FACTORY_ID",
    "FACTORY_VERSION",
    "CATEGORIES",
    "SQLQueryRecipeSpec",
    "SQL_QUERY_RECIPE_SPECS",
    "execute_sql_query_recipe",
    "build_sql_query_recipe_component",
    "verify_sql_query_recipe_component",
    "build_all_sql_query_recipe_components",
]
