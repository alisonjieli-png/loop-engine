"""Exercise wide proposals against real deterministic Solution Canvas controls.

These disclosed arithmetic fixtures are not a task-database benchmark or a
model-quality claim. Each trial compiles and executes a Canvas, records Run
History and an exact evaluation, and feeds measured results to later search.
The complete task catalog is inventoried separately without admitting it.
"""
from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import PackageNotFoundError, version as installed_version
import json
from pathlib import Path
import random
import subprocess
import sys
import time
import tracemalloc

from loop_engine import LoopLedger, SolutionLoopSpec, SolutionSpec
from loop_engine.code_nodes.solution_compiler import compile_solution, render_canvas, run_compiled
from loop_engine.core.run_history import RunHistory
from loop_engine.generation import (
    ConfigurationAxis, ConfigurationSpace, GridSearchAdapter, RandomSearchAdapter,
    SearchObjective, SearchObservation, SearchRequest, SearchServices, SearchTask,
    propose_configurations)
from loop_engine.generation.search_optuna import (
    BayesianSearchSettings, EvolutionarySearchSettings, CovarianceSearchSettings, OptunaSearchAdapter)
from loop_engine.generation.space import content_digest
from .systematic_records import CampaignProjection


def scale(values, parameters):
    return [value * parameters["factor"] for value in values]


def shift(values, parameters):
    return [value + parameters["offset"] for value in values]


REGISTRY = {"wide-control.scale": scale, "wide-control.shift": shift}


def verify_observation(observation):
    try:
        evaluation = json.loads(Path(observation.evaluation_ref).read_text())
        path = Path(observation.history_ref)
        history = RunHistory.load(str(path.parent), path.name)
        return (history.verify_chain()["intact"]
            and history.event_log[-1].event_digest == observation.history_digest
            and content_digest(evaluation) == observation.evaluation_digest
            and evaluation["trial_id"] == observation.trial_id
            and evaluation["trial_occurrence_ref"] == observation.trial_occurrence_ref
            and evaluation["task_digest"] == observation.task.digest
            and evaluation["configuration_index"] == observation.configuration_index
            and tuple(evaluation["objective_values"]) == observation.values)
    except (OSError, ValueError, KeyError, IndexError):
        return False


def trial(root, projection, request, proposal, identity):
    directory = root / identity
    directory.mkdir()
    config = proposal["configuration"]
    spec = SolutionSpec(identity, permitted_loop_modes=("deterministic",), loops=(
        SolutionLoopSpec("scale", "wide-control.scale", params={"factor": config["factor"]}),
        SolutionLoopSpec("shift", "wide-control.shift", params={"offset": config["offset"]})))
    compiled = compile_solution(spec, REGISTRY)
    if compiled["plan"] is None:
        raise ValueError("control Canvas did not compile")
    projection.export_object(directory / "canvas.json", compiled["plan"])
    projection.export_object(directory / "canvas-view.json", render_canvas(compiled["plan"]))
    inputs = [-1, 0, 2, 5]
    ledger, trace = LoopLedger(), []
    output = run_compiled(compiled["plan"], REGISTRY, inputs, ledger=ledger, trace=trace)
    expected = [3 * value + 7 for value in inputs]
    loss = sum((left - right) ** 2 for left, right in zip(output, expected))
    history = RunHistory.from_ledger(ledger.events, run_id=identity)
    history.commit()
    history.save(str(directory / "runs"))
    occurrence = "loop:" + str(trace[0]["runtime_loop_id"])
    evaluation = {"record_type": "wide_control_evaluation/v1", "trial_id": identity,
        "trial_occurrence_ref": occurrence, "task_digest": request.task.digest,
        "configuration_index": proposal["configuration_index"],
        "graph_digest": compiled["digest"], "inputs": inputs, "outputs": output,
        "expected": expected, "objective_values": [float(loss)],
        "control_requirement_met": loss == 0, "data_partition": "search_feedback",
        "runtime_trace": trace, "provider_calls_made": 0,
        "source_file": str(Path(__file__).resolve()),
        "source_digest": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    projection.export_object(directory / "evaluation.json", evaluation)
    observation = SearchObservation(identity, request.task, request.space.digest,
        proposal["configuration_index"], request.objectives, (float(loss),), "completed",
        occurrence, str(directory / "runs" / identity), history.event_log[-1].event_digest,
        str(directory / "evaluation.json"), content_digest(evaluation), "search_feedback")
    if not verify_observation(observation):
        raise ValueError("observation did not bind its history and evaluation")
    projection.record("search_observation", identity, observation.to_dict())
    return observation, directory / "canvas.json"


def replay(path):
    ledger, trace = LoopLedger(), []
    inputs = [-3, 4, 17]
    output = run_compiled(json.loads(path.read_text()), REGISTRY, inputs, ledger=ledger, trace=trace)
    print(json.dumps({"record_type": "wide_control_replay/v1", "inputs": inputs,
        "outputs": output, "expected": [3 * value + 7 for value in inputs],
        "control_requirement_met": output == [3 * value + 7 for value in inputs],
        "runtime_events": len(ledger.events), "provider_calls_made": 0}))


def run(args):
    root = args.root.resolve()
    root.mkdir(exist_ok=False)
    projection = CampaignProjection(root / "projection.duckdb")
    try:
        repository = Path(__file__).resolve().parents[2]
        watched = sorted(set((repository / "src/loop_engine/generation").rglob("*.py"))
                         | set((repository / "src/loop_engine/code_nodes").glob("solution_*.py"))
                         | {Path(__file__).resolve()})
        sources = {str(path.relative_to(repository)): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in watched}
        projection.export_object(root / "control-source-manifest.json", {
            "scope": "search, Solution Canvas modules, and control runner", "files": sources})
        raw = args.task_catalog.read_bytes()
        catalog = json.loads(raw)
        inventory = {"record_type": "wide_task_pool_inventory/v1", "source": str(args.task_catalog),
            "source_digest": hashlib.sha256(raw).hexdigest(), "task_count": len(catalog["tasks"]),
            "task_sample_limit": None, "entries": [{"task_id": row["id"],
                "task_record_digest": content_digest(row), "job_family": row["job_family"],
                "collection_status": row["status"], "admission": "not_qualified_by_this_control",
                "attempted_by_this_control": False} for row in catalog["tasks"]]}
        projection.record("task_pool", "all-catalog-records", inventory)
        projection.export_object(root / "task-pool.json", inventory)
        tracemalloc.start()
        began = time.monotonic()
        large = ConfigurationSpace("large-address-control", "1.0.0", (
            ConfigurationAxis("a", "integer_range", minimum=0, maximum=999999999),
            ConfigurationAxis("b", "integer_range", minimum=0, maximum=999)))
        generator = random.Random(9132026)
        for _ in range(args.address_probes):
            index = generator.randrange(large.cardinality)
            if large.index_of(large.configuration_at(index)) != index:
                raise ValueError("address round trip failed")
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        address = {"represented_configurations_decimal": str(large.cardinality),
            "address_round_trips": args.address_probes, "peak_traced_bytes": peak,
            "elapsed_seconds": time.monotonic() - began, "task_executions": 0}
        projection.export_object(root / "address-control.json", address)
        space = ConfigurationSpace("linear-canvas-control", "1.0.0", (
            ConfigurationAxis("factor", "integer_range", minimum=0, maximum=9),
            ConfigurationAxis("offset", "integer_range", minimum=0, maximum=9)))
        task = SearchTask("linear-control", content_digest("y=3*x+7"),
                          "linear-control@1.0.0", "squared-error-control@1.0.0")
        objectives = (SearchObjective("squared-error@1.0.0", "minimize"),)
        adapters = (GridSearchAdapter(), RandomSearchAdapter(),
            OptunaSearchAdapter(BayesianSearchSettings(4, 24)),
            OptunaSearchAdapter(EvolutionarySearchSettings(4, 0.9, 0.2)),
            OptunaSearchAdapter(CovarianceSearchSettings(4, None)))
        summaries = []
        missing = []
        for package in ("optuna", "cmaes"):
            try:
                installed_version(package)
            except PackageNotFoundError:
                missing.append(package)
        requires = {2: ["optuna"], 3: ["optuna"], 4: ["optuna", "cmaes"]}
        for method, adapter in enumerate(adapters):
            absent = [package for package in requires.get(method, []) if package in missing]
            if absent:
                # An optimizer that is not installed is a recorded outcome of
                # this control, not a crash that loses the summary.
                summaries.append({"method": adapter.adapter_ref,
                                  "status": "optimizer_unavailable_not_exercised",
                                  "missing_optional_dependencies": absent, "trials": 0})
                continue
            observations, cursor, candidates = [], 0, []
            for number in range(args.trials_per_method):
                request = SearchRequest(space, task, objectives, batch_size=1, draw_limit=100,
                    seed=9132026 + number, observations=tuple(observations), cursor=cursor)
                result = propose_configurations(request, SearchServices(adapter, verify_observation))
                batch = result["value"]
                identity = f"method-{method}-trial-{number}"
                projection.record("proposal", identity, result)
                projection.export_object(root / (identity + "-proposal.json"), result)
                if not batch["proposals"]:
                    summaries.append({"method": adapter.adapter_ref, "status": "proposal_batch_empty",
                                      "proposals": len(observations), "record": identity})
                    break
                observation, path = trial(root, projection, request, batch["proposals"][0], identity)
                observations.append(observation)
                candidates.append((observation.values[0], path))
                cursor = batch["next_cursor"] or 0
            if not candidates:
                continue
            best_loss, best = min(candidates, key=lambda value: value[0])
            completed = subprocess.run([sys.executable, "-m", "embodiment_lab.wide_search_controls",
                "--replay", str(best)], capture_output=True, text=True, check=True)
            fresh = json.loads(completed.stdout)
            projection.export_object(root / f"method-{method}-fresh-input.json", fresh)
            summaries.append({"method": adapter.adapter_ref, "trials": len(observations),
                "best_loss": best_loss, "fresh_input_control_met": fresh["control_requirement_met"],
                "best_canvas": str(best.relative_to(root)), "provider_calls_made": 0})
        summary = {"record_type": "wide_search_controls/v1", "task_catalog_records": inventory["task_count"],
            "task_catalog_sample_limit": None, "address_control": address, "methods": summaries,
            "provider_calls_made": 0, "real_task_database_tasks_executed": 0,
            "scope": "deterministic disclosed Canvas controls, not a task-database benchmark",
            "watched_sources_unchanged": all(hashlib.sha256((repository / path).read_bytes()).hexdigest() == digest
                                              for path, digest in sources.items())}
        projection.record("summary", root.name, summary)
        projection.export_object(root / "summary.json", summary)
        print(json.dumps(summary, indent=2))
    finally:
        projection.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--task-catalog", type=Path)
    parser.add_argument("--trials-per-method", type=int)
    parser.add_argument("--address-probes", type=int)
    parser.add_argument("--replay", type=Path)
    args = parser.parse_args()
    if args.replay:
        replay(args.replay)
    elif (args.root is None or args.task_catalog is None or not args.trials_per_method
          or args.trials_per_method < 1 or not args.address_probes or args.address_probes < 1):
        parser.error("root, task-catalog, positive trials-per-method and address-probes are required")
    else:
        run(args)
