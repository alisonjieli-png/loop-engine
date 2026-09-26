"""Summarise customer feedback into a dated aggregate and into idea suggestions for the generation lanes.

Kind: development tool. It reads the three feedback records of a hosted
service, `catalogue_item_rating/v1`, `material_request/v1` and
`search_gap/v1`, and writes two things:

- a dated aggregate, `feedback_report/v1`, under `artifacts/feedback/`, for
  the weekly number: counts only, with no rating note, no request text, no
  account identity and no search text, so the file can live in the public
  repository;
- a suggestion file, `harness_idea_batch/v1`, whose ideas are
  `harness_idea_record/v1` records the generation lanes can take. A request
  for material becomes one idea, and a search gap becomes one idea. A request
  carries the customer's own words, so the suggestion file is written outside
  the report folder's tracked files, under `ideas/`, which is ignored by git.

The mapping from a request or a gap to an idea is deterministic and written
here, in `idea_from_request` and `idea_from_gap`, with the facets chosen from
the idea matrix's own vocabularies, so a suggestion is a valid idea record
before a lane ever reads it. Nothing here calls a model, approves an item or
serves anything.

Run it against a service database:

    PYTHONPATH=src:tools python tools/feedback_report.py --database /data/service.db --output artifacts/feedback

Or against an exported list of records, one JSON object for each record:

    PYTHONPATH=src:tools python tools/feedback_report.py --records rows.json --output artifacts/feedback
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness_idea_matrix import (  # noqa: E402
    DATATYPES, FACET_DIMENSIONS, FILE_KINDS, IDEA_BATCH_RECORD_TYPE, IDEA_RECORD_TYPE, MATRIX_RECORD_TYPE, OPERATIONS,
    USE_CASES,
)

REPORT_RECORD_TYPE = "feedback_report/v1"
RATING_SCHEMA, REQUEST_SCHEMA, GAP_SCHEMA = "catalogue_item_rating/v1", "material_request/v1", "search_gap/v1"
RATING_KIND, REQUEST_KIND, GAP_KIND = "catalogue_item_rating", "material_request", "search_gap"
SCHEMAS = {RATING_KIND: RATING_SCHEMA, REQUEST_KIND: REQUEST_SCHEMA, GAP_KIND: GAP_SCHEMA}
DEFAULT_OUTPUT = Path("artifacts/feedback")
IDEAS_FOLDER = "ideas"
LIFECYCLE = "candidate"
IDENTITY = re.compile(r"^[a-z][a-z0-9-]{2,63}$")
#: The words of a request that choose each facet. The first match in reading order wins; without one the
#: default at the end of each table applies. Every value is a member of the idea matrix's own vocabulary.
OPERATION_WORDS = (("dedup", "deduplication"), ("reconcil", "reconciliation"), ("classif", "classification"),
                   ("extract", "extraction"), ("pars", "parsing"), ("format", "formatting"), ("review", "reviewing"),
                   ("monitor", "monitoring"), ("plan", "planning"), ("verif", "verification"), ("test", "verification"),
                   ("detect", "detection"), ("explain", "explanation"), ("clean", "standardization"),
                   ("normali", "normalization"), ("valid", "validation"), ("refus", "validation"),
                   ("check", "validation"), ("match", "matching"), ("rout", "routing"), ("count", "counting"))
DATATYPE_WORDS = (("csv", "csv_table"), ("json", "json_object"), ("sql", "sql_table"), ("yaml", "yaml_config"),
                  ("toml", "toml_config"), ("markdown", "markdown_document"), ("log", "log_lines"),
                  ("pdf", "pdf_document"), ("html", "html_page"), ("image", "image"), ("date", "date_and_time"),
                  ("email", "email_address"), ("url", "url"), ("address", "postal_address"), ("path", "file_path"))
USE_CASE_WORDS = (("terraform", "devops"), ("deploy", "devops"), ("kubernetes", "devops"), ("secur", "security_review"),
                  ("complian", "compliance_audit"), ("kaggle", "machine_learning"), ("model", "machine_learning"),
                  ("benchmark", "benchmarking"), ("support", "customer_support"), ("research", "research_analysis"),
                  ("document", "documentation"), ("data", "data_cleaning"), ("test", "quality_assurance"),
                  ("commit", "software_development"), ("review", "software_development"),
                  ("code", "software_development"))
FILE_KIND_WORDS = (("hook", "hook"), ("rule", "rules"), ("subagent", "subagent"), ("agent", "subagent"),
                   ("plugin", "plugin_manifest"), ("workflow", "workflow"), ("routing", "harness_routing"),
                   ("skill", "skill"))
DEFAULTS = {"operation": "transformation", "datatype": "text", "use_case": "agentic_task", "file_kind": "skill"}
KNOWN_WRONG = ("A file that claims to cover the request but performs none of its steps, names an effect it cannot "
               "perform by itself, or copies material whose licence does not allow it.")


class FeedbackReportError(ValueError):
    """A record, a path or an argument this tool refuses, with its reason."""


def _pick(text, table, default):
    lowered = text.lower()
    for word, value in table:
        if word in lowered:
            return value
    return default


def facets_for(text):
    """The four facets of an idea, chosen from a customer's words by the tables above."""
    return {"operation": _pick(text, OPERATION_WORDS, DEFAULTS["operation"]),
            "datatype": _pick(text, DATATYPE_WORDS, DEFAULTS["datatype"]),
            "use_case": _pick(text, USE_CASE_WORDS, DEFAULTS["use_case"]),
            "file_kind": _pick(text, FILE_KIND_WORDS, DEFAULTS["file_kind"])}


def _require(row, kind):
    if not isinstance(row, dict) or row.get("record_type") != SCHEMAS[kind]:
        raise FeedbackReportError(f"a {kind} record is {SCHEMAS[kind]}")
    return row


def _idea(identity, facets, task_reference, brief, provenance):
    for name, vocabulary in (("operation", OPERATIONS), ("datatype", DATATYPES), ("use_case", USE_CASES),
                             ("file_kind", FILE_KINDS)):
        if facets[name] not in vocabulary:
            raise FeedbackReportError(f"{name} {facets[name]!r} is outside the idea matrix vocabulary")
    if not IDENTITY.match(identity):
        raise FeedbackReportError(f"idea identity {identity!r} is not a short lowercase token")
    signature = hashlib.sha256(json.dumps([identity, facets, task_reference], sort_keys=True).encode()).hexdigest()
    return {"record_type": IDEA_RECORD_TYPE, "id": identity, "file_kind": facets["file_kind"],
            "datatype": facets["datatype"], "operation": facets["operation"], "use_case": facets["use_case"],
            "lifecycle": LIFECYCLE,
            "applicability": {"occupation_code": "", "occupation_title": "", "task_reference": task_reference,
                              "facet_dimensions": list(FACET_DIMENSIONS), "facet": {},
                              "feedback": provenance},
            "method_signature": signature, "brief": brief, "known_wrong": KNOWN_WRONG}


def idea_from_request(row):
    """One request for material becomes one candidate idea in the customer's own words.

    The account identity is not carried into the idea; the request is named by
    the digest of its request identity, which the service already stores.
    """
    _require(row, REQUEST_KIND)
    description = " ".join(str(row.get("description", "")).split())
    if not description:
        raise FeedbackReportError("a request for material has a description")
    facets = facets_for(description)
    identity = "req-" + hashlib.sha256(str(row.get("request_id_digest", "")).encode()).hexdigest()[:12]
    return _idea(identity, facets,
                 "A customer of the hosted library asked for material with these words: " + description[:400],
                 (f"Write an original {facets['file_kind'].replace('_', ' ')} that gives a coding harness what this "
                  "customer asked for: " + description[:400] + " Name its inputs, its steps, the effects it needs and "
                  "the check that shows it worked."),
                 {"source": REQUEST_KIND, "request_id_digest": row.get("request_id_digest", ""),
                  "at": row.get("at"), "state": row.get("state", "")})


def idea_from_gap(row):
    """One hour of searches that found nothing becomes one candidate idea shaped by the declared filters.

    The gap holds no search text and no account, so the idea is shaped by the
    filters alone: the kind of file when a filter names one, and the step
    functions and other attribute values as the task words.
    """
    _require(row, GAP_KIND)
    filters = row.get("filters") if isinstance(row.get("filters"), dict) else {}
    words = []
    for name in sorted(filters):
        for value in filters[name] if isinstance(filters[name], list) else []:
            words.append(f"{name} {str(value).split(':', 1)[-1]}")
    text = "; ".join(words) or "no filter"
    facets = facets_for(text)
    kinds = [str(value).split(":", 1)[-1] for value in filters.get("harness_kind", [])]
    if kinds and kinds[0] in FILE_KINDS:
        facets["file_kind"] = kinds[0]
    identity = "gap-" + hashlib.sha256(json.dumps([row.get("hour"), row.get("mode"), filters, row.get("library_tiers")],
                                                  sort_keys=True).encode()).hexdigest()[:12]
    searches = row.get("searches", 0)
    return _idea(identity, facets,
                 f"In the hour {row.get('hour')}, {searches} search{'es' if searches != 1 else ''} of the hosted library "
                 f"in {row.get('mode')} mode found nothing with these filters: {text}.",
                 (f"Write an original {facets['file_kind'].replace('_', ' ')} for the kind of step these filters "
                  f"describe: {text}. Name its inputs, its steps, the effects it needs and the check that shows it "
                  "worked."),
                 {"source": GAP_KIND, "hour": row.get("hour"), "mode": row.get("mode"), "searches": searches,
                  "library_tiers": row.get("library_tiers", [])})


def ideas_from(rows):
    """The suggestion batch for the generation lanes, one idea for each request and each gap."""
    ideas = [idea_from_request(row) for row in rows.get(REQUEST_KIND, [])]
    ideas.extend(idea_from_gap(row) for row in rows.get(GAP_KIND, []))
    digest = hashlib.sha256(json.dumps(ideas, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"record_type": IDEA_BATCH_RECORD_TYPE,
            "matrix": {"record_type": MATRIX_RECORD_TYPE, "datatypes": len(DATATYPES), "operations": len(OPERATIONS),
                       "use_cases": len(USE_CASES), "facet_dimensions": list(FACET_DIMENSIONS)},
            "sources": [{"kind": "customer_feedback", "requests": len(rows.get(REQUEST_KIND, [])),
                         "search_gaps": len(rows.get(GAP_KIND, []))}],
            "ideas": ideas, "idea_count": len(ideas),
            "unique_method_signatures": len({idea["method_signature"] for idea in ideas}),
            "unique_ids": len({idea["id"] for idea in ideas}), "file_kinds": len(FILE_KINDS), "batch_sha256": digest}


def summarise(rows, day):
    """The dated aggregate: counts only, and nothing a customer wrote or is."""
    ratings = [_require(row, RATING_KIND) for row in rows.get(RATING_KIND, [])]
    requests = [_require(row, REQUEST_KIND) for row in rows.get(REQUEST_KIND, [])]
    gaps = [_require(row, GAP_KIND) for row in rows.get(GAP_KIND, [])]
    by_item = {}
    for row in ratings:
        entry = by_item.setdefault(row["item_identity"], {"item_identity": row["item_identity"], "useful": 0,
                                                          "not_useful": 0})
        entry[row["value"]] += 1
    return {"record_type": REPORT_RECORD_TYPE, "day": day,
            "ratings": {"useful": sum(1 for row in ratings if row["value"] == "useful"),
                        "not_useful": sum(1 for row in ratings if row["value"] == "not_useful"),
                        "with_a_note": sum(1 for row in ratings if row.get("note")),
                        "items_rated": len(by_item), "items": sorted(by_item.values(), key=lambda row: row["item_identity"])},
            "material_requests": {"total": len(requests),
                                  "open": sum(1 for row in requests if row.get("state") == "open"),
                                  "accounts": len({row.get("tenant_id") for row in requests})},
            "search_gaps": {"records": len(gaps), "searches": sum(row.get("searches", 0) for row in gaps),
                            "by_hour": dict(sorted(Counter({row["hour"]: 0 for row in gaps}).items())) and
                            {hour: sum(row.get("searches", 0) for row in gaps if row["hour"] == hour)
                             for hour in sorted({row["hour"] for row in gaps})},
                            "by_mode": dict(sorted(Counter(row.get("mode", "") for row in gaps).items()))},
            "what_this_is_not": ("Counts only. No rating note, request text, account identity or search text is "
                                 "in this file; search gaps never hold the text or the account at all.")}


def load_records(path):
    """Rows exported as one JSON list, each a stored record with its payload or the payload itself."""
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise FeedbackReportError("an export is a JSON list of records")
    rows = {RATING_KIND: [], REQUEST_KIND: [], GAP_KIND: []}
    for entry in value:
        payload = entry.get("payload") if isinstance(entry, dict) and isinstance(entry.get("payload"), dict) else entry
        if not isinstance(payload, dict):
            raise FeedbackReportError("a record is an object")
        for kind, schema in SCHEMAS.items():
            if payload.get("record_type") == schema:
                rows[kind].append(payload)
                break
        else:
            raise FeedbackReportError(f"unsupported record {payload.get('record_type')!r}")
    return rows


def load_database(path, namespace):
    from loop_engine.core.service_runtime.feedback import feedback_rows
    from loop_engine.core.service_runtime.records import ServiceRuntimeConfig
    from loop_engine.core.service_runtime.runtime import ServiceRuntime
    runtime = ServiceRuntime(ServiceRuntimeConfig(str(Path(path).resolve()), namespace=namespace))
    return feedback_rows(runtime)


def write(rows, output, day, *, ideas_path=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report_path = output / f"feedback-report-{day}.json"
    report = summarise(rows, day)
    report_path.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    batch = ideas_from(rows)
    ideas_path = Path(ideas_path) if ideas_path is not None else output / IDEAS_FOLDER / f"feedback-ideas-{day}.json"
    ideas_path.parent.mkdir(parents=True, exist_ok=True)
    ideas_path.write_text(json.dumps(batch, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"report": str(report_path), "ideas": str(ideas_path), "idea_count": batch["idea_count"],
            "ratings": report["ratings"]["useful"] + report["ratings"]["not_useful"],
            "material_requests": report["material_requests"]["total"], "search_gaps": report["search_gaps"]["records"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--database", help="the service database to read, opened read-only")
    source.add_argument("--records", help="a JSON list of exported feedback records")
    parser.add_argument("--namespace", default="hosted-service", help="the service namespace of the database")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="the folder that receives the dated report")
    parser.add_argument("--ideas", default=None, help="where to write the suggestion batch; default under output/ideas/")
    parser.add_argument("--day", default=time.strftime("%Y-%m-%d", time.gmtime()), help="the date of the report")
    arguments = parser.parse_args(argv)
    try:
        rows = load_database(arguments.database, arguments.namespace) if arguments.database else load_records(arguments.records)
        outcome = write(rows, arguments.output, arguments.day, ideas_path=arguments.ideas)
    except FeedbackReportError as error:
        print(json.dumps({"record_type": REPORT_RECORD_TYPE, "refused": str(error)}))
        return 1
    print(json.dumps(outcome, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
