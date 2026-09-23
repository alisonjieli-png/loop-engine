"""Known-wrong checks for the adopted and optional engines, run offline.

The reference validator (skills-ref) must accept a rendered skill and refuse
a broken one; where it is not installed the check reports that fact with the
missing dependency instead of passing. The schema validator must accept the
rendered connection files, refuse an unknown key, and become ineligible when
a schema is missing or its digest changed. The model outline engine must
record every call with unknown usage kept unknown, refuse a sentence that
copies the source, pause within its bound on a rate limit and stop before
its call ceiling. The package check must read 200 as resolving, 404 as
missing and anything else as unknown. The scanner report mapping must block
a skill SkillSpector recommends against and mark a skill it did not report.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from .connection_rendering import render_connection
from .format_json_schema import ConnectionSchemaValidator
from .format_skills_ref import AgentSkillsReferenceValidator
from .outline_model import CallCeilingReached, ModelOutline
from .package_resolver import PackageResolver
from .provenance import read_outside_provenance
from .provenance_checks import fixture_provenance, fixture_registry_provenance
from .record_rules import bytes_digest
from .render_checks import UPSTREAM_SKILL, _entry
from .rendering_types import RenderRefused
from .scan_skillspector import SkillSpectorStatic, findings_from_report
from .skill_rendering import parse_skill, render_skill

_CODEX_SCHEMA = {"type": "object", "additionalProperties": False, "properties": {"mcp_servers": {
    "type": "object", "additionalProperties": {"type": "object", "additionalProperties": False, "properties": {
        "command": {"type": "string"}, "args": {"type": "array", "items": {"type": "string"}},
        "env_vars": {"type": "array", "items": {"type": "string"}}, "url": {"type": "string"},
        "http_headers": {"type": "object"}, "env_http_headers": {"type": "object"}}}}}}
_OPENCODE_SCHEMA = {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
                    "properties": {"mcp": {"type": "object", "additionalProperties": {
                        "type": "object", "required": ["type"], "additionalProperties": False, "properties": {
                            "type": {"enum": ["local", "remote"]}, "command": {"type": "array"},
                            "enabled": {"type": "boolean"}, "environment": {"type": "object"},
                            "url": {"type": "string"}, "headers": {"type": "object"}}}}}}


@dataclass
class _Reply:
    text: str = ""
    ok: bool = True
    model: str = "fixture-model"
    prompt_tokens: "int | None" = None
    eval_tokens: "int | None" = None
    usage_reported: bool = False
    error: str = ""
    retry_after_seconds: "float | None" = None


class _Transport:
    def __init__(self, statuses):
        self.statuses, self.asked = list(statuses), []

    def get(self, host, path, query=None):
        self.asked.append((host, path))
        return type("Answer", (), {"status": self.statuses.pop(0), "body": b""})()


def _schemas() -> dict:
    rows = {}
    for schema_id, schema in (("codex_config", _CODEX_SCHEMA), ("opencode_config", _OPENCODE_SCHEMA)):
        data = json.dumps(schema).encode()
        rows[schema_id] = {"bytes": data, "sha256": bytes_digest(data)}
    return rows


def self_test() -> dict:
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed), "detail": str(detail)[:300]})

    provenance = read_outside_provenance(fixture_provenance())
    package = render_skill(parse_skill(UPSTREAM_SKILL), provenance, licence_file=("LICENSE", b"MIT\n"))
    if AgentSkillsReferenceValidator.availability({})[0]:
        validator = AgentSkillsReferenceValidator()
        clean = validator.validate_skill(package.folder, package.main_text)
        broken = validator.validate_skill("another-folder", package.main_text)
        check("the_reference_validator_accepts_a_rendered_skill_and_refuses_a_broken_one",
              clean == [] and broken, (clean, broken))
    else:
        tests.append({"test": "the_reference_validator_accepts_a_rendered_skill_and_refuses_a_broken_one",
                      "passed": None, "not_tested": True, "outcome": "NOT_APPLICABLE",
                      "missing_optional_dependencies": ["skills_ref"],
                      "detail": "skills-ref needs Python 3.11 or later and is installed only in the tools environment"})

    schemas = _schemas()
    validator = ConnectionSchemaValidator(schemas)
    document = render_connection(_entry(), read_outside_provenance(fixture_registry_provenance())).document
    unknown = json.loads(json.dumps(document))
    for row in unknown["files"]:
        if row["harness"] == "codex":
            row["text"] += 'startup_timeout_seconds = 5\n'
    check("the_schema_validator_accepts_rendered_files_and_refuses_an_unknown_key",
          validator.validate_package(document) == [] and validator.validate_package(unknown),
          validator.validate_package(unknown))
    digests = {key: {"expected": row["sha256"], "observed": row["sha256"]} for key, row in schemas.items()}
    changed = {**digests, "codex_config": {"expected": "0" * 64, "observed": digests["codex_config"]["observed"]}}
    check("a_missing_schema_or_a_changed_digest_makes_the_schema_validator_ineligible",
          ConnectionSchemaValidator.availability({"schema_digests": digests}) == (True, "available")
          and ConnectionSchemaValidator.availability({}) == (False, "not_configured")
          and ConnectionSchemaValidator.availability({"schema_digests": changed})
          == (False, "schema_digest_changed"))

    candidate = {"candidate_key": "a" * 64, "kind": "skill", "native_format": "agent_skill",
                 "name": "review-code", "provenance": fixture_provenance(
                     licence_evidence={**fixture_provenance()["licence_evidence"], "decision": "outline_only",
                                       "governing_file": None, "spdx_expression": "NONE"})}
    source = "Read every changed line. Compare each change with the stated intent and flag surprises."
    replies = [_Reply("Helps an assistant check a code change against what its author meant.")]
    engine = ModelOutline("fixture-model", 3, chat=lambda *args, **kwargs: replies.pop(0), sleep=lambda s: None)
    outline = engine.outline(candidate, source)
    call = engine.calls[0]
    check("every_model_call_is_recorded_and_unknown_usage_stays_unknown",
          outline["model_calls"] == [call["call_digest"]] and call["usage"]["prompt_tokens"] is None
          and call["usage_reported"] is False and call["outcome"] == "ok"
          and call["model_requested"] == "fixture-model" and "prompt" not in json.dumps(outline).lower()
          .replace("prompt_digest", ""), call)

    copying = ModelOutline("fixture-model", 1, chat=lambda *args, **kwargs: _Reply(
        "Compare each change with the stated intent and flag surprises."), sleep=lambda s: None)
    try:
        copying.outline(candidate, source)
        copied = False
    except RenderRefused as error:
        copied = error.code == "outline_would_copy_source_text"
    asked = []
    try:
        copying.outline(candidate, source)
        stopped = False
    except CallCeilingReached:
        stopped = True
    check("a_sentence_that_copies_the_source_is_refused_and_the_ceiling_stops_before_a_call",
          copied and stopped and len(copying.calls) == 1 and not asked)

    slept = []
    limited = [_Reply(ok=False, error="HTTP 429 (retry after 2s): slow down", retry_after_seconds=2.0),
               _Reply("Helps an assistant review a code change for correctness.", prompt_tokens=10,
                      eval_tokens=12, usage_reported=True)]
    patient = ModelOutline("fixture-model", 5, maximum_pause_seconds=5.0,
                           chat=lambda *args, **kwargs: limited.pop(0), sleep=slept.append)
    patient.outline(candidate, source)
    check("a_rate_limited_call_pauses_within_its_bound_and_both_calls_are_recorded",
          slept == [2.0] and [row["outcome"] for row in patient.calls] == ["rate_limited", "ok"]
          and patient.calls[1]["usage"] == {"prompt_tokens": 10, "completion_tokens": 12})

    resolver = PackageResolver(_Transport([200, 404, 503]))
    verdicts = [resolver.resolves({"registry": "npm", "identifier": "@scope/a", "version": "1.0.0"}),
                resolver.resolves({"registry": "pypi", "identifier": "b", "version": "2.0"}),
                resolver.resolves({"registry": "npm", "identifier": "c", "version": "3.0.0"}),
                resolver.resolves({"registry": "oci", "identifier": "d", "version": "1"})]
    check("the_package_check_reads_200_as_resolving_404_as_missing_and_anything_else_as_unknown",
          verdicts == [True, False, None, None] and resolver.transport.asked[0][1] == "/@scope%2Fa/1.0.0"
          and resolver.transport.asked[1] == ("pypi.org", "/pypi/b/2.0/json"), verdicts)

    report = {"skills": [
        {"path": "item-000", "risk_score": 99, "risk_assessment": {"recommendation": "DO_NOT_INSTALL"},
         "issues": [{"id": "P1", "location": {"start_line": 7}}]},
        {"path": "item-001", "risk_score": 0, "risk_assessment": {"recommendation": "SAFE"}, "issues": []}]}
    mapped = findings_from_report(report, {"item-000": "bad", "item-001": "good", "item-002": "missing"},
                                  "skillspector_static")
    check("the_scanner_report_blocks_a_do_not_install_skill_and_marks_an_unreported_one",
          {row["rule"] for row in mapped["bad"]} == {"skillspector_do_not_install", "skillspector_P1"}
          and mapped["good"] == [] and mapped["missing"][0]["rule"] == "skillspector_package_not_reported"
          and SkillSpectorStatic.availability({}) == (False, "not_configured"), mapped)

    passed = sum(1 for item in tests if item["passed"] is True)
    executed = [item for item in tests if item.get("not_tested") is not True]
    return {"record_type": "library_optional_engine_test/v1", "tests": tests, "passed": passed,
            "total": len(executed), "all_passed": passed == len(executed)}
