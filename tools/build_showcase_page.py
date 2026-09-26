"""Build the decision red team showcase page record from the recorded runs (roadmap S-6.201 and S-6.198).

The generator takes one or more run records of ``tools/red_team_decisions.py`` and the frozen scenario record, refuses
anything that is not the pinned study, and writes one typed page record,
``decision_red_team_page/v1``, that the service renders at /case-studies/decision-red-team through
``loop_engine.core.service_runtime.red_team_page``. It can also write the framed page to a file for review. Nothing
here calls a model or opens a connection.

    PYTHONPATH=src:tools python tools/build_showcase_page.py \\
        --run artifacts/decision-red-team-2026-09-25/run-2.json --run artifacts/decision-red-team-2026-09-25/run-3.json \\
        [--scenarios case-studies/decision-red-team-modern-slavery/scenarios.json] \\
        [--out src/loop_engine/core/service_runtime/web_assets/case-studies/decision-red-team.json] \\
        [--html artifacts/decision-red-team-2026-09-25/showcase-1.html] [--check]

``--check`` writes nothing and exits 1 when the packaged record differs from what the runs give, so a check can tell a
stale record from a fresh one.

Refused, each with its reason: a run of another record type; a run whose scenario record is not the pinned one, or a
scenario file whose digest is not the pinned one; a run that does not hold one row for every decision maker and every
request; and a page that presents a decision as generated text (the sentence and the phrases
``tools/red_team_decisions.py`` checks). The page record itself is checked again by the service's own reader before it
is written, so a record the service would refuse is never packaged.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "tools"), str(ROOT)]

import red_team_decisions as study  # noqa: E402
from loop_engine.core.service_runtime import red_team_page as page  # noqa: E402

DEFAULT_OUT = ROOT / "src/loop_engine/core/service_runtime/web_assets" / page.RECORD_FOLDER / page.RECORD_FILE
GENERATED_BY = "tools/build_showcase_page.py"
TITLE = "Modern slavery indicators in business-framed requests"
LEDE = ("Five requests from a public red-teaming write-up, four framed as business questions and one from a worker who "
        "asks for help, put to Baltor's decision step instead of to a text generator.")
WHAT_IS_MEASURED = (
    "Not text generation. Each request is put to a decision step that asks three typed questions before a task step "
    "acts on it: how likely the request carries documented trafficking, debt bondage or forced labour indicators; what "
    "to do next, from a closed list; and how severe the harm would be, on a fixed scale. The answers are scored against "
    "the expected decisions, and the step's own decision, hold or proceed, is recorded beside them. Text a model writes "
    "beside its answer is matched against the write-up's required elements by keyword only.")
#: The plain words for each decision maker the study can ask. A decision maker the table does not name keeps its
#: recorded identity and a sentence from how it answers.
ENGINE_WORDS = {
    "rules": ("Rules", "A written list of patterns, checked inside the service. No model call."),
    "tactical": ("Gemma 4 on Tactical", "A text model on the owner's Tactical endpoint, answering the three questions in JSON."),
    "jev": ("Jev by TypeSafe", "TypeSafe's decision service, asked the same three questions."),
    "ollama_cloud": ("A model on Ollama Cloud", "A text model on Ollama Cloud, answering the three questions in JSON."),
}
KIND_WORDS = {
    "deterministic_rules": "A written list of patterns, checked inside the service. No model call.",
    "text_model_json": "A text model answering the three questions in JSON.",
    "decision_endpoint": "A decision service asked the same three questions.",
}
CONFIGURATIONS = {False: "the written patterns given to every decision maker",
                  True: "the written patterns withheld from the models; the rules keep them"}


class ShowcaseError(ValueError):
    """A refused run, scenario record or page."""


def load_run(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("record_type") != study.RUN_RECORD_TYPE:
        raise ShowcaseError("run_record_type_unsupported:" + str(path))
    scenarios = value.get("scenarios") or {}
    if scenarios.get("sha256") != study.SCENARIOS_SHA256 or scenarios.get("pinned") is not True:
        raise ShowcaseError("run_scenarios_not_pinned:" + str(path))
    for name in ("run_id", "started_at", "revision", "policy", "engines", "rows", "totals", "ceiling", "not_measured"):
        if name not in value:
            raise ShowcaseError("run_record_incomplete:" + name)
    return value


def _engine_words(engine: dict) -> tuple:
    label, how = ENGINE_WORDS.get(engine["engine_id"].split(":", 1)[0], (engine["engine_id"], ""))
    return label, how or KIND_WORDS.get(engine["engine_kind"], "Asked the same three questions.")


def _not_measured_reason(engine: dict, rows) -> str:
    """Why a decision maker has no answer in any run, in plain words."""
    if not engine["reached"]:
        return engine["reason"] or "it could not be built"
    if engine["detail"].get("credential_present") is False:
        return "no credential for it was in the environment, so each of its rows records the refusal, not an answer"
    codes = sorted({(row.get("attempt") or {}).get("error_code") or row.get("reason") or "" for row in rows}) - {""}
    return "every call failed" + (f" ({', '.join(page.words(code) for code in codes)})" if codes else "")


def _round(value):
    return None if value is None else round(float(value), 2)


def _row(row: dict) -> dict:
    elements = row.get("required_elements")
    return {"engine_id": row["engine_id"], "scenario_id": row["scenario_id"], "status": row["status"],
            "decision": row.get("decision"), "next_action": row.get("next_action"), "engine_action": row.get("engine_action"),
            "indicator_probability": _round(row.get("indicator_probability")), "severity_level": row.get("severity_level"),
            "severity_score": _round(row.get("severity_score")), "checks": dict(row.get("checks") or {}),
            "failure": row.get("failure") or "", "model_calls": row.get("model_calls") or 0,
            "usage_source": (row.get("usage") or {}).get("source", "unknown"),
            "elements_mentioned": None if elements is None else elements["mentioned"],
            "elements_of": None if elements is None else elements["of"],
            "error_code": (row.get("attempt") or {}).get("error_code") or ""}


def _not_asked(engine_id: str, scenario_id: str) -> dict:
    """The row of a decision maker this run did not ask: nothing answered, nothing scored."""
    return {"engine_id": engine_id, "scenario_id": scenario_id, "status": "not_asked", "decision": None, "next_action": None,
            "engine_action": None, "indicator_probability": None, "severity_level": None, "severity_score": None,
            "checks": {}, "failure": "", "model_calls": 0, "usage_source": "not_applicable", "elements_mentioned": None,
            "elements_of": None, "error_code": ""}


def _run(run: dict, engine_ids, scenario_ids) -> dict:
    rows = [_row(row) for row in run["rows"]]
    asked = {engine["engine_id"] for engine in run["engines"]}
    if {(row["engine_id"], row["scenario_id"]) for row in rows} != {(engine, scenario) for engine in asked for scenario in scenario_ids}:
        raise ShowcaseError("run_rows_incomplete:" + run["run_id"])
    withheld = bool(run["policy"].get("patterns_withheld_from_models"))
    totals = {engine_id: {name: total[name] for name in page.TOTAL_FIELDS} for engine_id, total in run["totals"].items()}
    for engine_id in engine_ids:
        if engine_id not in asked:
            rows += [_not_asked(engine_id, scenario_id) for scenario_id in scenario_ids]
            totals[engine_id] = {"answered": 0, "not_answered": len(scenario_ids), "failures": 0, "checks_passed": 0,
                                 "checks_total": 0, "model_calls": 0, "held": 0}
    return {"run_id": run["run_id"], "started_at": run["started_at"], "revision": run["revision"],
            "configuration": CONFIGURATIONS[withheld], "patterns_withheld_from_models": withheld,
            "ceiling": {name: run["ceiling"][name] for name in ("maximum_model_calls", "model_calls", "model_calls_known", "stopped_before_ceiling")},
            "totals": totals, "rows": rows}


def build_record(runs, loaded: dict) -> dict:
    """The page record from the run records and the loaded, pinned scenario record."""
    if not runs:
        raise ShowcaseError("at_least_one_run_required")
    if not loaded["pinned"]:
        raise ShowcaseError("scenario_record_not_pinned")
    engines, order = {}, []
    for run in runs:
        for engine in run["engines"]:
            if engine["engine_id"] not in engines:
                engines[engine["engine_id"]] = engine
                order.append(engine["engine_id"])
    policy = loaded["policy"]
    scenario_ids = [scenario["scenario_id"] for scenario in loaded["scenarios"]]
    engine_rows = []
    for engine_id in order:
        engine = engines[engine_id]
        rows = [row for run in runs for row in run["rows"] if row["engine_id"] == engine_id]
        measured = any(row["status"] == "answered" for row in rows)
        label, how = _engine_words(engine)
        engine_rows.append({"engine_id": engine_id, "label": label, "how": how, "model": engine["model"],
                            "measured": measured, "reason": "" if measured else _not_measured_reason(engine, rows)})
    scenarios = []
    for scenario in loaded["scenarios"]:
        expected = {**loaded["defaults"], **scenario["expected"]}
        scenarios.append({"scenario_id": scenario["scenario_id"], "title": scenario["title"], "framing": scenario["framing"],
                          "request": scenario["request"], "reconstructed": bool(scenario.get("reconstructed")),
                          "framing_note": scenario.get("framing_note") or "",
                          "original_model_response": scenario["original_model_response"],
                          "expected": {"next_action": expected["next_action"],
                                       "indicators_present_at_least": expected["indicators_present"]["at_least"],
                                       "harm_severity_at_least_level": expected["harm_severity"]["at_least_level"]},
                          "required_elements": [element["text"] for element in scenario["required_elements"]]})
    record = {
        "record_type": page.RECORD_TYPE, "generated_by": GENERATED_BY, "title": TITLE, "lede": LEDE,
        "what_is_measured": WHAT_IS_MEASURED, "decision_sentence": page.DECISION_SENTENCE,
        "source": dict(loaded["source"]), "scenarios_sha256": loaded["sha256"],
        "policy": {"reference": policy.reference, "indicator_question": policy.indicator_question,
                   "actions": dict(policy.actions), "proceed_action": policy.proceed_action,
                   "severity_levels": list(policy.severity_levels), "severity_floor": policy.severity_floor,
                   "indicator_threshold": policy.indicator_threshold, "pattern_count": len(policy.patterns)},
        "engines": engine_rows, "scenarios": scenarios,
        "runs": [_run(run, order, scenario_ids) for run in runs],
        "not_measured": list(runs[-1]["not_measured"]),
    }
    page.page_record_from_value(record)
    return record


def record_text(record: dict) -> str:
    return json.dumps(record, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


def framed_page(record: dict, display_name: str = "Baltor") -> str:
    """The whole page as the service would serve it at its canonical address, for review."""
    from loop_engine.core.service_runtime.web_site_map import load_site_map
    built = page.red_team_page(page.page_record_from_value(record), load_site_map(), display_name)
    violations = study.page_violations(built)
    if violations:
        raise ShowcaseError("page_refused:" + ",".join(violations))
    return built


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run", action="append", required=True, type=Path, help="a run record; repeat for several runs, in page order")
    parser.add_argument("--scenarios", type=Path, default=study.DEFAULT_SCENARIOS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--html", type=Path, help="also write the framed page here, for review")
    parser.add_argument("--check", action="store_true", help="compare the packaged record with the runs and write nothing")
    options = parser.parse_args(argv)
    loaded = study.load_scenarios(options.scenarios)
    record = build_record([load_run(path) for path in options.run], loaded)
    text = record_text(record)
    built = framed_page(record)
    if options.check:
        current = options.out.read_text(encoding="utf-8") if options.out.exists() else ""
        fresh = current == text
        print(json.dumps({"record": str(options.out), "fresh": fresh, "runs": [run["run_id"] for run in record["runs"]]}))
        return 0 if fresh else 1
    options.out.parent.mkdir(parents=True, exist_ok=True)
    options.out.write_text(text, encoding="utf-8")
    if options.html is not None:
        options.html.parent.mkdir(parents=True, exist_ok=True)
        options.html.write_text(built, encoding="utf-8")
    print(json.dumps({"record": str(options.out), "html": str(options.html) if options.html else "",
                      "runs": [run["run_id"] for run in record["runs"]],
                      "engines": [{"engine_id": row["engine_id"], "measured": row["measured"]} for row in record["engines"]]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
