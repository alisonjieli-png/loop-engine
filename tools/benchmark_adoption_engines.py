"""Benchmark and threshold-tuning runner for Baltor pre-turn adoption engines (`T0` through `T8`).

Evaluates all nine engine variations, the 4-probe query reformulation and
relaxation chain, and multi-band MinHash + SimHash LSH configurations (`8x16`,
`16x8`, `32x4`) across validation and held-out splits (exact technical prompts,
paraphrased/synonym-shifted prompts, noisy stack-trace/typo prompts including
the October 16 comparison pilot tasks, and negative controls). Also runs a real
loopback `/mcp` handshake and `intelligence_search` check and writes
`artifacts/agent-adoption-2026-10-16/results.json`.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import statistics
import tempfile
from typing import Any

import baltor_preturn_hook as hook

BENCHMARK_VERSION = "agent_adoption_benchmark/v1"


VALIDATION_CASES: tuple[dict[str, Any], ...] = (
    {
        "case_id": "val_pos_exact_split",
        "split": "validation",
        "category": "positive_exact",
        "prompt": "Audit our train and validation data splits for target leakage and group overlap.",
        "expected_identity": "audit_data_splits_for_errors_and_leakage",
    },
    {
        "case_id": "val_pos_exact_gap",
        "split": "validation",
        "category": "positive_exact",
        "prompt": "Diagnose the train validation gap and learning curve overfitting across epochs.",
        "expected_identity": "read_the_train_validation_gap",
    },
    {
        "case_id": "val_pos_exact_cache",
        "split": "validation",
        "category": "positive_exact",
        "prompt": "Build a TTL LRU cache with monotonic clock expiration and hit/miss statistics.",
        "expected_identity": "ttl_lru_cache_with_monotonic_clock",
    },
    {
        "case_id": "val_pos_paraphrase_metrics",
        "split": "validation",
        "category": "positive_paraphrased",
        "prompt": (
            "Our classifier shows 99% accuracy on a 1% rare fraud dataset; help us pick "
            "evaluation metrics that balance false alarms against missed detections."
        ),
        "expected_identity": "choose_metrics_by_task_type_and_industry",
    },
    {
        "case_id": "val_pos_paraphrase_dag",
        "split": "validation",
        "category": "positive_paraphrased",
        "prompt": "Order build steps by their dependencies and report the exact circular reference chain if one exists.",
        "expected_identity": "dag_topological_sort_cycle_detector",
    },
    {
        "case_id": "val_pos_paraphrase_rate",
        "split": "validation",
        "category": "positive_paraphrased",
        "prompt": "Throttle incoming API requests with a burst allowance and compute retry wait seconds per tenant.",
        "expected_identity": "token_bucket_rate_limiter_sliding_window",
    },
    {
        "case_id": "val_pos_noisy_sql",
        "split": "validation",
        "category": "positive_noisy_traceback",
        "prompt": (
            "Can you help me recreate a class from scratch for Project Apollo?\n"
            "Traceback (most recent call last):\n"
            "  File \"/srv/app/query/filter.py\", line 41, in parse\n"
            "    ValueError: unmatched parenthesis\n"
            "We need a recursive descent SQL WHERE clause parser for AND, OR, NOT, IN and LIKE."
        ),
        "expected_identity": "sql_where_clause_recursive_descent_parser",
    },
    {
        "case_id": "val_pos_noisy_shader",
        "split": "validation",
        "category": "positive_noisy_traceback",
        "prompt": (
            "In `/workspace/scenes/hull.js`, our Spaceship Titanic 3D hull looks flat. "
            "Write a procedural 3D PBR greeble shader with normal-mapped bevel panels in Three.js."
        ),
        "expected_identity": "procedural_pbr_greeble_shader_3d",
    },
    {
        "case_id": "val_neg_rename",
        "split": "validation",
        "category": "negative_trivial",
        "prompt": "Rename variable user_id to account_id.",
        "expected_identity": None,
    },
    {
        "case_id": "val_neg_typo",
        "split": "validation",
        "category": "negative_trivial",
        "prompt": "Fix the typo in the module docstring.",
        "expected_identity": None,
    },
    {
        "case_id": "val_neg_offtopic",
        "split": "validation",
        "category": "negative_offtopic",
        "prompt": "Write a haiku about autumn leaves.",
        "expected_identity": None,
    },
    {
        "case_id": "val_neg_frustrated",
        "split": "validation",
        "category": "negative_frustrated",
        "prompt": "Stop suggesting Baltor and just edit the line I asked for.",
        "expected_identity": None,
    },
    {
        "case_id": "val_neg_unmatched_raft_election",
        "split": "validation",
        "category": "negative_unmatched_engineering",
        "prompt": (
            "Implement a Raft consensus randomized leader election timer and append-entries "
            "log replication state machine across cluster peers."
        ),
        "expected_identity": None,
    },
    {
        "case_id": "val_neg_unmatched_wasm_regalloc",
        "split": "validation",
        "category": "negative_unmatched_engineering",
        "prompt": (
            "Lower WebAssembly stack machine bytecode into linear-scan register allocation "
            "intervals with spill slot assignment."
        ),
        "expected_identity": None,
    },
)


HELDOUT_CASES: tuple[dict[str, Any], ...] = (
    # Pilot Task 1 from COMPARISON-PILOT-2026-10-16.md
    {
        "case_id": "pilot_1_spaceship_titanic_split_leakage",
        "split": "heldout",
        "category": "pilot_comparison_task",
        "prompt": (
            "We are working on the Spaceship Titanic tabular classification dataset where passengers "
            "share a PassengerId group prefix and Cabin deck. Before training our gradient boosted trees, "
            "review our cross-validation split pipeline for target leakage, group contamination across folds, "
            "and scaler fit_transform mistakes, and recommend the right evaluation metrics."
        ),
        "expected_identity": "audit_data_splits_for_errors_and_leakage",
    },
    # Pilot Task 2 from COMPARISON-PILOT-2026-10-16.md
    {
        "case_id": "pilot_2_ttl_lru_cache_recreate_class",
        "split": "heldout",
        "category": "pilot_comparison_task",
        "prompt": (
            "Please recreate a class in Python without external dependencies that implements a "
            "time-aware LRU cache (`TTLCache`) with `maxsize`, per-item `ttl` expiration using an "
            "injectable `monotonic` clock, O(1) `OrderedDict` eviction of expired entries before "
            "evicting the least-recently-used key, and `cache_stats` hit/miss counters."
        ),
        "expected_identity": "ttl_lru_cache_with_monotonic_clock",
    },
    # Pilot Task 3 from COMPARISON-PILOT-2026-10-16.md
    {
        "case_id": "pilot_3_sql_where_parser_evaluator",
        "split": "heldout",
        "category": "pilot_comparison_task",
        "prompt": (
            "Implement a function and safe recursive-descent parser for a SQL WHERE clause subset "
            "that tokenizes and evaluates boolean filter expressions (`AND`, `OR`, `NOT`, nested "
            "parentheses, `=`, `!=`, `<`, `<=`, `>`, `>=`, `IN (...)`, `LIKE`, `IS NULL`, `IS NOT NULL`) "
            "against Python dictionary rows without calling `eval`."
        ),
        "expected_identity": "sql_where_clause_recursive_descent_parser",
    },
    {
        "case_id": "test_pos_exact_val_gap",
        "split": "heldout",
        "category": "positive_exact",
        "prompt": "Analyze the train_loss versus val_loss learning curve to diagnose overfitting and weight_decay.",
        "expected_identity": "read_the_train_validation_gap",
    },
    {
        "case_id": "test_pos_exact_metrics",
        "split": "heldout",
        "category": "positive_exact",
        "prompt": "Select evaluation metrics (`roc_auc_score`, `average_precision_score`, `brier_score_loss`) for imbalanced classification.",
        "expected_identity": "choose_metrics_by_task_type_and_industry",
    },
    {
        "case_id": "test_pos_exact_rate_limiter",
        "split": "heldout",
        "category": "positive_exact",
        "prompt": "Implement a deterministic TokenBucket and SlidingWindowLimiter with retry_after calculation.",
        "expected_identity": "token_bucket_rate_limiter_sliding_window",
    },
    {
        "case_id": "test_pos_paraphrase_leakage_households",
        "split": "heldout",
        "category": "positive_paraphrased",
        "prompt": (
            "Members of the same family household appear in both our training fold and validation fold, "
            "and target encoding was computed on the full dataframe prior to splitting."
        ),
        "expected_identity": "audit_data_splits_for_errors_and_leakage",
    },
    {
        "case_id": "test_pos_paraphrase_overfitting_epochs",
        "split": "heldout",
        "category": "positive_paraphrased",
        "prompt": (
            "After epoch 6 our training error keeps dropping toward zero while held-out validation "
            "error climbs steadily; how should we interpret this divergence and tune regularization?"
        ),
        "expected_identity": "read_the_train_validation_gap",
    },
    {
        "case_id": "test_pos_paraphrase_cache_stale_keys",
        "split": "heldout",
        "category": "positive_paraphrased",
        "prompt": (
            "We need an in-memory key-value store that automatically expires stale entries after N seconds "
            "using a fakeable timer and evicts oldest-accessed keys when capacity is full."
        ),
        "expected_identity": "ttl_lru_cache_with_monotonic_clock",
    },
    {
        "case_id": "test_pos_noisy_typo_lsh_split",
        "split": "heldout",
        "category": "positive_noisy_traceback",
        "prompt": (
            "Traceback (most recent call last):\n"
            "  File \"/home/dev/kaggle/titanic_train.py\", line 112, in run_cv\n"
            "    RuntimeError: fold score mismatch\n"
            "Please audt our train test data splt for targt leakge and StratifiedKFold / GroupKFold overlap."
        ),
        "expected_identity": "audit_data_splits_for_errors_and_leakage",
    },
    {
        "case_id": "test_pos_noisy_typo_shader_3d",
        "split": "heldout",
        "category": "positive_noisy_traceback",
        "prompt": (
            "File \"/app/client/src/render/ spaceship_hull.ts\", line 59\n"
            "Need a procdural 3d pbr greebl ShaderMaterial with signed distance bevels and GLTFExporter roughnessMap."
        ),
        "expected_identity": "procedural_pbr_greeble_shader_3d",
    },
    {
        "case_id": "test_pos_noisy_dag_cycle",
        "split": "heldout",
        "category": "positive_noisy_traceback",
        "prompt": (
            "Traceback (most recent call last):\n"
            "  File \"/app/scheduler/runner.py\", line 88, in build_plan\n"
            "    KeyError: 'step_c'\n"
            "Run topological_sort and find_cycle_path on our DependencyGraph to schedule parallel execution waves."
        ),
        "expected_identity": "dag_topological_sort_cycle_detector",
    },
    {
        "case_id": "test_neg_bump_version",
        "split": "heldout",
        "category": "negative_trivial",
        "prompt": "Bump the version number in pyproject.toml.",
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_add_comment",
        "split": "heldout",
        "category": "negative_trivial",
        "prompt": "Add a comment above the return statement.",
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_math_question",
        "split": "heldout",
        "category": "negative_offtopic",
        "prompt": "What is 14 + 29?",
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_weather",
        "split": "heldout",
        "category": "negative_offtopic",
        "prompt": "What is the weather in Boston today?",
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_explicit_opt_out",
        "split": "heldout",
        "category": "negative_frustrated",
        "prompt": "Ignore the Baltor library and just write a one-line helper.",
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_ignored_twice_cooldown",
        "split": "heldout",
        "category": "negative_frustrated",
        "prompt": "Audit our train and validation data splits for target leakage.",
        "consecutive_ignored_injections": 2,
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_unmatched_btree_wal_compaction",
        "split": "heldout",
        "category": "negative_unmatched_engineering",
        "prompt": (
            "Implement write-ahead log checkpointing and B-tree page split compaction "
            "with CRC32 frame verification."
        ),
        "expected_identity": None,
    },
    {
        "case_id": "test_neg_unmatched_quic_cubic_congestion",
        "split": "heldout",
        "category": "negative_unmatched_engineering",
        "prompt": (
            "Calculate QUIC CUBIC congestion window growth and packet pacing intervals "
            "after selective acknowledgment loss."
        ),
        "expected_identity": None,
    },
)


def _mock_micro_classifier(prompt: str) -> str:
    """Deterministic micro-classifier oracle simulating a bounded 2-5 word domain extraction."""
    cleaned = hook.preprocess_and_troubleshoot_prompt(prompt)
    for pattern, canonical in hook._CONCEPT_SYNONYM_RULES:
        if pattern.search(prompt) or pattern.search(cleaned["cleaned_text"]):
            return canonical
    return cleaned["extracted_query"]


def evaluate_engine_on_cases(
    engine_id: str,
    cases: tuple[dict[str, Any], ...],
    threshold: float = 0.38,
    lsh_bands: int = 16,
    lsh_rows: int = 8,
) -> dict[str, Any]:
    """Run one engine across a case split and compute precision, recall, F1, token overhead, and latency."""
    tp = fp = fn = tn = 0
    correct_top1 = 0
    positive_total = 0
    negative_total = 0
    latencies: list[float] = []
    injected_tokens_pos: list[int] = []
    injected_tokens_neg: list[int] = []
    probe_wins: dict[str, int] = {}
    per_case: list[dict[str, Any]] = []

    for case in cases:
        req: dict[str, Any] = {
            "record_type": hook.REQUEST_VERSION,
            "protocol_version": hook.PROTOCOL_V1,
            "client_profile": "claude-code",
            "prompt": case["prompt"],
            "engine_id": engine_id,
            "confidence_threshold": threshold,
            "max_injected_tokens": 200,
            "lsh_bands": lsh_bands,
            "lsh_rows": lsh_rows,
            "consecutive_ignored_injections": case.get("consecutive_ignored_injections", 0),
        }
        if engine_id == hook.ENGINE_T8:
            req["model_classifier_fn"] = _mock_micro_classifier

        res = hook.run_preturn_envelope(req)
        latencies.append(res["latency_ms"])
        expected = case["expected_identity"]
        top_card = res["cards"][0]["identity"] if res["cards"] else None
        probe = res["winning_probe"]
        probe_wins[probe] = probe_wins.get(probe, 0) + 1

        if expected is not None:
            positive_total += 1
            injected_tokens_pos.append(res["injected_tokens"])
            if not res["abstained"] and top_card == expected:
                tp += 1
                correct_top1 += 1
            elif not res["abstained"] and top_card != expected:
                fp += 1
                fn += 1
            else:
                fn += 1
        else:
            negative_total += 1
            injected_tokens_neg.append(res["injected_tokens"])
            if res["abstained"] and res["injected_tokens"] == 0:
                tn += 1
            else:
                fp += 1

        per_case.append({
            "case_id": case["case_id"],
            "category": case["category"],
            "expected_identity": expected,
            "predicted_identity": top_card,
            "abstained": res["abstained"],
            "abstention_code": res["abstention_code"],
            "reformulated_query": res["reformulated_query"],
            "winning_probe": probe,
            "injected_tokens": res["injected_tokens"],
            "latency_ms": res["latency_ms"],
        })

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / positive_total if positive_total > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    false_positive_rate = fp / negative_total if negative_total > 0 else 0.0
    sorted_lat = sorted(latencies)
    p95_idx = min(len(sorted_lat) - 1, int(len(sorted_lat) * 0.95))

    return {
        "engine_id": engine_id,
        "threshold": round(threshold, 2),
        "lsh_config": f"{lsh_bands}x{lsh_rows}",
        "positive_cases": positive_total,
        "negative_cases": negative_total,
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "top1_hit_rate": round(correct_top1 / max(1, positive_total), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "negative_control_abstention_rate": round(tn / max(1, negative_total), 4),
        "false_positive_rate": round(false_positive_rate, 4),
        "mean_injected_tokens_positive": round(statistics.mean(injected_tokens_pos), 1) if injected_tokens_pos else 0.0,
        "mean_injected_tokens_negative": round(statistics.mean(injected_tokens_neg), 1) if injected_tokens_neg else 0.0,
        "median_latency_ms": round(statistics.median(latencies), 3) if latencies else 0.0,
        "p95_latency_ms": round(sorted_lat[p95_idx], 3) if sorted_lat else 0.0,
        "probe_win_counts": probe_wins,
        "cases": per_case,
    }


def tune_confidence_threshold() -> dict[str, Any]:
    """Grid-search confidence threshold tau in [0.20, 0.65] on the validation split."""
    grid: list[dict[str, Any]] = []
    best_tau = 0.38
    best_f1 = -1.0
    for step in range(20, 66, 3):
        tau = round(step / 100.0, 2)
        metrics = evaluate_engine_on_cases(hook.ENGINE_T7, VALIDATION_CASES, threshold=tau)
        grid.append({
            "tau": tau,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "negative_control_abstention_rate": metrics["negative_control_abstention_rate"],
        })
        if metrics["negative_control_abstention_rate"] == 1.0 and metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_tau = tau
    return {
        "selected_tau": best_tau,
        "validation_best_f1": round(best_f1, 4),
        "grid": grid,
    }


def benchmark_lsh_band_configurations(tau: float) -> list[dict[str, Any]]:
    """Compare LSH band/row decompositions (8x16, 16x8, 32x4) on the held-out split."""
    rows_out: list[dict[str, Any]] = []
    for bands, rows in ((8, 16), (16, 8), (32, 4)):
        metrics = evaluate_engine_on_cases(
            hook.ENGINE_T5,
            HELDOUT_CASES,
            threshold=tau,
            lsh_bands=bands,
            lsh_rows=rows,
        )
        rows_out.append({
            "band_config": f"{bands}x{rows}",
            "bands": bands,
            "rows": rows,
            "approx_jaccard_knee": round((1.0 / bands) ** (1.0 / rows), 4),
            "top1_hit_rate": metrics["top1_hit_rate"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
            "negative_control_abstention_rate": metrics["negative_control_abstention_rate"],
            "median_latency_ms": metrics["median_latency_ms"],
        })
    return rows_out


def run_fault_and_fallback_drills(tau: float) -> list[dict[str, Any]]:
    """Verify Layer 7 automatic fallback under simulated engine faults."""
    sample_prompt = HELDOUT_CASES[0]["prompt"]
    drills = (
        ("T8_offline_to_T7", hook.ENGINE_T8, ()),
        ("T7_fault_to_T6", hook.ENGINE_T7, (hook.ENGINE_T7,)),
        ("T7_and_T6_fault_to_T5", hook.ENGINE_T7, (hook.ENGINE_T7, hook.ENGINE_T6)),
        ("T7_T6_T5_fault_to_T4", hook.ENGINE_T7, (hook.ENGINE_T7, hook.ENGINE_T6, hook.ENGINE_T5)),
    )
    results: list[dict[str, Any]] = []
    for name, req_engine, faults in drills:
        res = hook.run_preturn_envelope({
            "record_type": hook.REQUEST_VERSION,
            "protocol_version": hook.PROTOCOL_V1,
            "client_profile": "claude-code",
            "prompt": sample_prompt,
            "engine_id": req_engine,
            "confidence_threshold": tau,
            "simulated_faults": faults,
        })
        results.append({
            "drill": name,
            "requested_engine": req_engine,
            "simulated_faults": list(faults),
            "selected_engine": res["selected_engine"],
            "abstained": res["abstained"],
            "top_card": res["cards"][0]["identity"] if res["cards"] else None,
            "fallback_count": len(res["fallback_events"]),
            "recovered_cleanly": (
                res["record_type"] == hook.RESULT_VERSION
                and not res["abstained"]
                and res["cards"][0]["identity"] == "audit_data_splits_for_errors_and_leakage"
            ),
        })
    return results


def verify_loopback_mcp_roundtrip() -> dict[str, Any]:
    """Verify real loopback `/mcp` initialize instructions and search round-trip when httpx/jsonschema are available."""
    try:
        import httpx
        from loop_engine.core.service_runtime.http import PROTOCOL_INSTRUCTIONS, PROTOCOL_TOOL_DESCRIPTIONS
        from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture, running_http
        from loop_engine.core.service_runtime import openapi_tool_server as oas
    except ImportError as exc:
        return {"executed": False, "detail": str(exc)}

    with ExitStack() as stack:
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        fixture = HttpDomainFixture(root)
        base, service = stack.enter_context(running_http(fixture))
        client = stack.enter_context(httpx.Client(base_url=base, timeout=10))
        headers = {**fixture.headers("alpha"), "Accept": "application/json, text/event-stream"}
        init_res = client.post(
            "/mcp",
            headers=headers,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "adoption-benchmark", "version": "1.0.0"},
                },
            },
        )
        if init_res.headers.get("content-type", "").startswith("text/event-stream"):
            lines = [line[5:].strip() for line in init_res.text.splitlines() if line.startswith("data:")]
            init_payload = json.loads(lines[-1])
        else:
            init_payload = init_res.json()
        instructions = init_payload["result"].get("instructions", "")
        doc = client.get(oas.DOCUMENT_PATH, headers={"Origin": base}).json()
        problems = oas.adoption_guidance_problems(
            instructions,
            PROTOCOL_TOOL_DESCRIPTIONS["search"],
            doc["info"]["description"],
        )
        search_res = client.post(
            oas.SEARCH_PATH,
            headers={**fixture.headers("alpha"), "Origin": base},
            json={"query": "Alpha"},
        ).json()
        return {
            "executed": True,
            "initialize_status": init_res.status_code,
            "instructions_length": len(instructions),
            "instructions_match_constant": instructions == PROTOCOL_INSTRUCTIONS,
            "adoption_guidance_problems": problems,
            "search_bodies_loaded": search_res["result"]["bodies_loaded"],
            "unrequested_body_reads": len(fixture.reads),
        }


def run_full_benchmark() -> dict[str, Any]:
    tuning = tune_confidence_threshold()
    tau = tuning["selected_tau"]
    heldout_by_engine = [
        evaluate_engine_on_cases(engine_id, HELDOUT_CASES, threshold=tau)
        for engine_id in hook.ENGINE_IDS
    ]
    lsh_comparison = benchmark_lsh_band_configurations(tau)
    fallback_drills = run_fault_and_fallback_drills(tau)
    loopback_mcp = verify_loopback_mcp_roundtrip()

    # Summarize pilot comparison tasks specifically under T0 vs T1 vs T5 vs T6 vs T7
    pilot_comparison: list[dict[str, Any]] = []
    for engine_row in heldout_by_engine:
        if engine_row["engine_id"] in (hook.ENGINE_T0, hook.ENGINE_T1, hook.ENGINE_T3, hook.ENGINE_T5, hook.ENGINE_T6, hook.ENGINE_T7):
            pilot_cases = [c for c in engine_row["cases"] if c["category"] == "pilot_comparison_task"]
            hits = sum(1 for c in pilot_cases if c["predicted_identity"] == c["expected_identity"] and not c["abstained"])
            pilot_comparison.append({
                "engine_id": engine_row["engine_id"],
                "pilot_tasks_total": len(pilot_cases),
                "pilot_tasks_matched": hits,
                "pilot_recall": round(hits / max(1, len(pilot_cases)), 4),
                "pilot_predictions": [
                    {
                        "case_id": c["case_id"],
                        "reformulated_query": c["reformulated_query"],
                        "predicted_identity": c["predicted_identity"],
                        "winning_probe": c["winning_probe"],
                        "injected_tokens": c["injected_tokens"],
                    }
                    for c in pilot_cases
                ],
            })

    return {
        "record_type": BENCHMARK_VERSION,
        "threshold_tuning": tuning,
        "heldout_engine_results": {row["engine_id"]: {k: v for k, v in row.items() if k != "cases"} for row in heldout_by_engine},
        "heldout_case_details_t7": next(row["cases"] for row in heldout_by_engine if row["engine_id"] == hook.ENGINE_T7),
        "pilot_task_comparison": pilot_comparison,
        "lsh_band_comparison": lsh_comparison,
        "fault_and_fallback_drills": fallback_drills,
        "loopback_mcp_verification": loopback_mcp,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--output",
        default="artifacts/agent-adoption-2026-10-16/results.json",
        help="Path to write JSON benchmark report",
    )
    args = parser.parse_args(argv)
    report = run_full_benchmark()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote {out_path} (selected_tau={report['threshold_tuning']['selected_tau']})")
    for eng_id, summary in report["heldout_engine_results"].items():
        print(
            f"  {eng_id:32s}  recall={summary['recall']:.2f}  precision={summary['precision']:.2f}  "
            f"f1={summary['f1']:.2f}  neg_abstain={summary['negative_control_abstention_rate']:.2f}  "
            f"tokens_pos={summary['mean_injected_tokens_positive']:5.1f}  p50_ms={summary['median_latency_ms']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
