"""The decision red team page at /case-studies/decision-red-team, rendered from one packaged record.

Kind: pure rendering over one packaged record and the typed site map. The transport asks `rendered` for the page
after its address table and the model directory find nothing; the surface checks and the site map checks ask the
same way. Nothing here reads a request, a credential or an account, and nothing here calls a model.

The record, `web_assets/case-studies/decision-red-team.json`, is written by `tools/build_showcase_page.py` from the
run records under `artifacts/decision-red-team-2026-09-25/` and the frozen scenario record of
`case-studies/decision-red-team-modern-slavery/`, so the service needs no artifacts folder at run time. It is not
kept under `public_lists/`, because that folder holds the counted-link tables and their reader refuses any other
record. The scenario record's digest is pinned here as well as in the study tool: a page built from a scenario record
whose expectations changed is refused before it is rendered, and a run in which a decision maker proceeded on a
business-framed request without a recorded failure is refused too. Roadmap steps S-6.198 and S-6.201.

```text
/case-studies/decision-red-team
├── what was measured, in plain words, and the sentence that every row is a typed decision
├── what each decision maker did in each run: answered, checks, recorded failures, held, model calls
├── each of the five requests: the request, what the write-up's model did, and every typed decision on it
├── what was not measured
└── how the runs were made: the runs, their ceilings, the policy and the source
```

The page uses plain public words: step, decision, rule, model. The names of the runtime stay in the record and in the
repository.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from html import escape
import json
import re

ADDRESS = "/case-studies/decision-red-team"
VIEW = "case-studies-decision-red-team"
#: The hostname that opens the page at its root address, as the site map lists it.
HOSTNAME = "redteam.baltor.ai"
RECORD_TYPE = "decision_red_team_page/v1"
#: The packaged record, under the served files' folder beside the model directory's records; it is not served itself.
RECORD_FOLDER = "case-studies"
RECORD_FILE = "decision-red-team.json"
#: The frozen scenario record's digest, the same value tools/red_team_decisions.py pins. A record built from another
#: scenario record is refused.
PINNED_SCENARIOS_SHA256 = "6fa3687211314c5424fd2ec18b75b8e42cce78258dbd57ae2d1a02113c26d786"
DECISION_SENTENCE = "Each row is a typed decision, not generated text."
FRAMINGS = ("business", "victim")
#: A row's status: the study's own three, and not_asked for a decision maker a run did not ask at all.
ROW_STATUSES = ("answered", "failed", "not_run", "not_asked")
DECISIONS = ("hold", "proceed")
RECORD_FIELDS = ("record_type", "generated_by", "title", "lede", "what_is_measured", "decision_sentence", "source",
                 "scenarios_sha256", "policy", "engines", "scenarios", "runs", "not_measured")
ENGINE_FIELDS = ("engine_id", "label", "how", "model", "measured", "reason")
SCENARIO_FIELDS = ("scenario_id", "title", "framing", "request", "reconstructed", "framing_note",
                   "original_model_response", "expected", "required_elements")
RUN_FIELDS = ("run_id", "started_at", "revision", "configuration", "patterns_withheld_from_models", "ceiling",
              "totals", "rows")
ROW_FIELDS = ("engine_id", "scenario_id", "status", "decision", "next_action", "engine_action", "indicator_probability",
              "severity_level", "severity_score", "checks", "failure", "model_calls", "usage_source", "elements_mentioned",
              "elements_of", "error_code")
TOTAL_FIELDS = ("answered", "not_answered", "failures", "checks_passed", "checks_total", "model_calls", "held")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class RedTeamPageError(ValueError):
    """A page record this reader refuses, with the reason."""


@dataclass(frozen=True)
class PageRecord:
    """The checked record, as plain values, with the lookups the page needs."""

    value: dict

    @property
    def engines(self) -> dict:
        return {engine["engine_id"]: engine for engine in self.value["engines"]}

    @property
    def scenarios(self) -> list:
        return self.value["scenarios"]

    @property
    def runs(self) -> list:
        return self.value["runs"]


def handles(address: str) -> bool:
    return address == ADDRESS


def _fields(value, where: str, names) -> dict:
    if not isinstance(value, dict):
        raise RedTeamPageError(f"{where} must be an object")
    missing, unknown = sorted(set(names) - set(value)), sorted(set(value) - set(names))
    if missing or unknown:
        raise RedTeamPageError(f"{where} has missing fields {missing} and unknown fields {unknown}")
    return value


def _text(value, where: str, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise RedTeamPageError(f"{where} must be a{'' if empty else ' nonempty'} string")
    return value


def _check_pinned(value: dict) -> None:
    """The record was built from the pinned scenario record; a changed expectation changes that digest."""
    digest = value["scenarios_sha256"]
    if not isinstance(digest, str) or not _SHA256.match(digest):
        raise RedTeamPageError("scenarios_sha256 is a hex SHA-256")
    if digest != PINNED_SCENARIOS_SHA256:
        raise RedTeamPageError("scenario_record_not_pinned:" + digest[:16])


def _check_failures(value: dict) -> None:
    """A proceed answer on a business-framed request, or a victim not referred, is a recorded failure, never a score."""
    proceed = value["policy"]["proceed_action"]
    scenarios = {scenario["scenario_id"]: scenario for scenario in value["scenarios"]}
    for run in value["runs"]:
        for row in run["rows"]:
            if row["status"] != "answered":
                continue
            scenario = scenarios[row["scenario_id"]]
            if scenario["framing"] == "business" and row["engine_action"] == proceed and not row["failure"]:
                raise RedTeamPageError(f"proceed_without_a_recorded_failure:{run['run_id']}:{row['engine_id']}:{row['scenario_id']}")
            if scenario["framing"] == "victim" and row["engine_action"] != scenario["expected"]["next_action"] and not row["failure"]:
                raise RedTeamPageError(f"victim_not_referred_without_a_recorded_failure:{run['run_id']}:{row['engine_id']}")


def _check_totals(value: dict) -> None:
    """The totals a run states agree with its rows, so the summary can never say more than the rows do."""
    for run in value["runs"]:
        for engine_id, total in run["totals"].items():
            rows = [row for row in run["rows"] if row["engine_id"] == engine_id]
            answered = [row for row in rows if row["status"] == "answered"]
            stated = {"answered": len(answered), "not_answered": len(rows) - len(answered),
                      "failures": sum(1 for row in answered if row["failure"]),
                      "checks_passed": sum(sum(1 for flag in row["checks"].values() if flag) for row in answered),
                      "checks_total": sum(len(row["checks"]) for row in answered),
                      "held": sum(1 for row in answered if row["decision"] == "hold")}
            for name, expected in stated.items():
                if total[name] != expected:
                    raise RedTeamPageError(f"totals_disagree_with_rows:{run['run_id']}:{engine_id}:{name}")


def page_record_from_value(value) -> PageRecord:
    """Read a page record, or refuse it with the reason."""
    row = _fields(value, "page record", RECORD_FIELDS)
    if row["record_type"] != RECORD_TYPE:
        raise RedTeamPageError(f"this reader reads {RECORD_TYPE}, not {row['record_type']!r}")
    for name in ("generated_by", "title", "lede", "what_is_measured"):
        _text(row[name], name)
    if row["decision_sentence"] != DECISION_SENTENCE:
        raise RedTeamPageError("decision_presented_as_text")
    source = _fields(row["source"], "source", ("citation", "url", "license", "note"))
    for name in ("citation", "url", "license"):
        _text(source[name], "source." + name)
    if not source["url"].startswith("https://"):
        raise RedTeamPageError("source.url is an https address")
    _check_pinned(row)
    policy = _fields(row["policy"], "policy", ("reference", "indicator_question", "actions", "proceed_action",
                                                "severity_levels", "severity_floor", "indicator_threshold", "pattern_count"))
    if not isinstance(policy["actions"], dict) or policy["proceed_action"] not in policy["actions"]:
        raise RedTeamPageError("policy.actions names the proceed action")
    if not isinstance(policy["severity_levels"], list) or policy["severity_floor"] not in policy["severity_levels"]:
        raise RedTeamPageError("policy.severity_levels holds the severity floor")
    engines = [_fields(item, f"engines[{index}]", ENGINE_FIELDS) for index, item in enumerate(row["engines"])]
    if not engines or len({engine["engine_id"] for engine in engines}) != len(engines):
        raise RedTeamPageError("engines name each decision maker once")
    for engine in engines:
        _text(engine["label"], "engine label")
        _text(engine["how"], "engine how")
        if not isinstance(engine["measured"], bool) or not isinstance(engine["reason"], str):
            raise RedTeamPageError("an engine says whether it was measured, and why not")
        if not engine["measured"] and not engine["reason"].strip():
            raise RedTeamPageError(f"engine {engine['engine_id']} was not measured and gives no reason")
    scenarios = [_fields(item, f"scenarios[{index}]", SCENARIO_FIELDS) for index, item in enumerate(row["scenarios"])]
    if not scenarios or len({item["scenario_id"] for item in scenarios}) != len(scenarios):
        raise RedTeamPageError("scenarios name each request once")
    for scenario in scenarios:
        if scenario["framing"] not in FRAMINGS:
            raise RedTeamPageError("scenario framing is business or victim")
        _text(scenario["request"], "scenario request")
        _text(scenario["original_model_response"], "scenario original_model_response")
        expected = _fields(scenario["expected"], "scenario expected",
                           ("next_action", "indicators_present_at_least", "harm_severity_at_least_level"))
        if expected["next_action"] == policy["proceed_action"]:
            raise RedTeamPageError("scenario_expects_proceed")
        if scenario["reconstructed"] and not scenario["framing_note"]:
            raise RedTeamPageError("reconstructed_scenario_needs_its_note")
        if not isinstance(scenario["required_elements"], list):
            raise RedTeamPageError("scenario required_elements is a list")
    engine_ids, scenario_ids = {engine["engine_id"] for engine in engines}, {item["scenario_id"] for item in scenarios}
    runs = [_fields(item, f"runs[{index}]", RUN_FIELDS) for index, item in enumerate(row["runs"])]
    if not runs or len({run["run_id"] for run in runs}) != len(runs):
        raise RedTeamPageError("runs name each run once")
    for run in runs:
        _text(run["run_id"], "run_id")
        _text(run["configuration"], "run configuration")
        if not isinstance(run["patterns_withheld_from_models"], bool):
            raise RedTeamPageError("a run says whether the patterns were withheld from the models")
        _fields(run["ceiling"], "run ceiling", ("maximum_model_calls", "model_calls", "model_calls_known", "stopped_before_ceiling"))
        if set(run["totals"]) != engine_ids:
            raise RedTeamPageError(f"run {run['run_id']} states totals for every decision maker")
        for engine_id, total in run["totals"].items():
            _fields(total, f"totals[{engine_id}]", TOTAL_FIELDS)
        for index, item in enumerate(run["rows"]):
            line = _fields(item, f"rows[{index}] of {run['run_id']}", ROW_FIELDS)
            if line["engine_id"] not in engine_ids or line["scenario_id"] not in scenario_ids:
                raise RedTeamPageError("a row names a known decision maker and a known request")
            if line["status"] not in ROW_STATUSES or not isinstance(line["checks"], dict) or not isinstance(line["failure"], str):
                raise RedTeamPageError("a row carries a status, its checks and its failure")
            if line["status"] == "answered" and line["decision"] not in DECISIONS:
                raise RedTeamPageError("an answered row carries the step's decision")
        if {(line["engine_id"], line["scenario_id"]) for line in run["rows"]} != {(engine, scenario) for engine in engine_ids for scenario in scenario_ids}:
            raise RedTeamPageError(f"run {run['run_id']} holds one row for every decision maker and every request")
    if not isinstance(row["not_measured"], list) or not row["not_measured"]:
        raise RedTeamPageError("limits_missing")
    _check_failures(row)
    _check_totals(row)
    return PageRecord(row)


def _packaged_value():
    from importlib.resources import files
    path = files("loop_engine").joinpath("core", "service_runtime", "web_assets", RECORD_FOLDER, RECORD_FILE)
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_page_record() -> PageRecord:
    """The packaged record, read and checked once; a new release starts a new process."""
    return page_record_from_value(_packaged_value())


# Rendering.

def words(identifier) -> str:
    """A recorded identifier as plain words: refuse_and_cite_worker_protections becomes refuse and cite worker protections."""
    return str(identifier or "").replace("_", " ")


def _when(started_at: str) -> str:
    try:
        moment = datetime.fromisoformat(started_at)
    except ValueError:
        return started_at
    return moment.strftime("%B %d, %Y at %H:%M UTC").replace(" 0", " ")


def _number(value) -> str:
    if value is None:
        return "not answered"
    if isinstance(value, float) and value.is_integer():
        return f"{value:.1f}"
    return str(value)


def _decision_words(row: dict) -> str:
    if row["status"] != "answered":
        return "no answer"
    return "held" if row["decision"] == "hold" else "proceeded"


def _checks_words(row: dict) -> str:
    if row["status"] != "answered":
        return "none"
    passed = sum(1 for flag in row["checks"].values() if flag)
    missed = [words(name) for name, flag in row["checks"].items() if not flag]
    return f"{passed} of {len(row['checks'])}" + (f" (missed: {', '.join(missed)})" if missed else "")


def _status_words(row: dict, engine: dict) -> str:
    if row["status"] == "answered":
        return ""
    if row["status"] == "not_asked":
        return "not asked in this run"
    if not engine["measured"]:
        return "not measured: " + engine["reason"]
    if row["status"] == "failed":
        return "the call failed" + (f" ({words(row['error_code'])})" if row["error_code"] else "")
    return "not run"


def _not_asked_in(run: dict, engine: dict) -> bool:
    """True when the run asked this decision maker nothing, so its rows carry no answer and no refusal."""
    rows = [row for row in run["rows"] if row["engine_id"] == engine["engine_id"]]
    return bool(rows) and all(row["status"] == "not_asked" for row in rows)


def _summary_table(record: PageRecord) -> str:
    head = ("<thead><tr><th scope=\"col\">Decision maker</th><th scope=\"col\">Run</th><th scope=\"col\">Answered</th>"
            "<th scope=\"col\">Checks passed</th><th scope=\"col\">Recorded failures</th><th scope=\"col\">Held</th>"
            "<th scope=\"col\">Model calls</th></tr></thead>")
    lines = []
    for run in record.runs:
        for engine in record.value["engines"]:
            total = run["totals"][engine["engine_id"]]
            if _not_asked_in(run, engine):
                cells = '<td colspan="5">Not asked in this run</td>'
            elif not engine["measured"]:
                cells = f'<td colspan="5">Not measured: {escape(engine["reason"])}</td>'
            else:
                failures = total["failures"]
                stale = ' class="md-stale"' if failures else ""
                cells = (f"<td>{total['answered']} of {total['answered'] + total['not_answered']}</td>"
                         f"<td>{total['checks_passed']} of {total['checks_total']}</td>"
                         f"<td{stale}>{failures}</td><td>{total['held']}</td>"
                         f"<td>{total['model_calls']}</td>")
            lines.append(f'<tr data-red-team-total="{escape(run["run_id"])}:{escape(engine["engine_id"])}">'
                         f'<th scope="row">{escape(engine["label"])}</th><td>{escape(run["configuration"])}</td>{cells}</tr>')
    return f'<div class="md-table-wrap"><table class="md-table" data-red-team-summary>{head}<tbody>{"".join(lines)}</tbody></table></div>'


def _summary_sentences(record: PageRecord) -> str:
    parts = []
    for engine in record.value["engines"]:
        if not engine["measured"]:
            skipped = [run["configuration"] for run in record.runs if _not_asked_in(run, engine)]
            parts.append(f"{engine['label']} was not measured: {engine['reason']}."
                         + (f" It was not asked in the run with {' or '.join(skipped)}." if skipped else ""))
            continue
        pieces = []
        for run in record.runs:
            total = run["totals"][engine["engine_id"]]
            failures = total["failures"]
            piece = f"{total['checks_passed']} of {total['checks_total']} checks with {run['configuration']}"
            if failures:
                named = sorted({words(row["failure"]) for row in run["rows"]
                                if row["engine_id"] == engine["engine_id"] and row["failure"]})
                piece += f", with {failures} recorded failure{'s' if failures != 1 else ''} ({'; '.join(named)})"
            pieces.append(piece)
        parts.append(f"{engine['label']}: " + "; ".join(pieces) + ".")
    return " ".join(escape(part) for part in parts)


def _scenario_band(record: PageRecord, scenario: dict, position: int) -> str:
    anchor = f"request-{position}"
    framing = ("a request framed as a business question" if scenario["framing"] == "business"
               else "a request from a worker who asks for help")
    expected = scenario["expected"]
    note = (f'<p class="md-reading">This request is reconstructed: {escape(scenario["framing_note"])}</p>'
            if scenario["reconstructed"] else "")
    head = ("<thead><tr><th scope=\"col\">Decision maker</th><th scope=\"col\">Run</th><th scope=\"col\">Step decision</th>"
            "<th scope=\"col\">Next action</th><th scope=\"col\">Indicators</th><th scope=\"col\">Harm</th>"
            "<th scope=\"col\">Checks</th><th scope=\"col\">Recorded failure</th><th scope=\"col\">Elements by keyword</th></tr></thead>")
    lines = []
    for run in record.runs:
        for engine in record.value["engines"]:
            row = next(item for item in run["rows"] if item["engine_id"] == engine["engine_id"]
                       and item["scenario_id"] == scenario["scenario_id"])
            status = _status_words(row, engine)
            if status:
                cells = f'<td colspan="7">{escape(status)}</td>'
            else:
                elements = ("no text" if row["elements_of"] is None else f"{row['elements_mentioned']} of {row['elements_of']}")
                stale = ' class="md-stale"' if row["failure"] else ""
                cells = (f"<td>{escape(_decision_words(row))}</td><td>{escape(words(row['engine_action']))}</td>"
                         f"<td>{escape(_number(row['indicator_probability']))}</td>"
                         f"<td>{escape(words(row['severity_level']))} ({escape(_number(row['severity_score']))})</td>"
                         f"<td>{escape(_checks_words(row))}</td>"
                         f"<td{stale}>{escape(words(row['failure']) or 'none')}</td>"
                         f"<td>{escape(elements)}</td>")
            lines.append(f'<tr data-red-team-row="{escape(run["run_id"])}:{escape(engine["engine_id"])}:{escape(scenario["scenario_id"])}">'
                         f'<th scope="row">{escape(engine["label"])}</th><td>{escape(run["configuration"])}</td>{cells}</tr>')
    elements = "".join(f"<li>{escape(text)}</li>" for text in scenario["required_elements"])
    return (f'<div class="md-band" id="{anchor}" aria-labelledby="{anchor}-title"><h2 id="{anchor}-title">{position}. '
            f'{escape(scenario["title"])}</h2><p class="md-reading">This is {framing}. The expected decision is to '
            f'{escape(words(expected["next_action"]))}, with the indicators judged present at {escape(_number(expected["indicators_present_at_least"]))} '
            f'or more and the harm at least {escape(expected["harm_severity_at_least_level"])}.</p>{note}'
            f'<details class="md-setup"><summary>The request, as the write-up gives it</summary>'
            f'<blockquote class="md-reading"><pre class="md-code md-code-wrap">{escape(scenario["request"])}</pre></blockquote></details>'
            f'<h3>What the write-up records of the original model</h3><p class="md-reading">{escape(scenario["original_model_response"])}</p>'
            f'<h3>The typed decisions</h3><div class="md-table-wrap"><table class="md-table">{head}<tbody>{"".join(lines)}</tbody></table></div>'
            f'<details class="md-setup"><summary>The write-up\'s required elements, matched by keyword only</summary>'
            f'<ul class="md-plain">{elements}</ul></details></div>')


def _runs_band(record: PageRecord) -> str:
    policy, source = record.value["policy"], record.value["source"]
    lines = []
    for run in record.runs:
        ceiling = run["ceiling"]
        stopped = "stopped before its ceiling" if ceiling["stopped_before_ceiling"] else "did not reach its ceiling"
        lines.append(f'<li data-red-team-run="{escape(run["run_id"])}">{escape(_when(run["started_at"]))}: {escape(run["configuration"])}; '
                     f'{ceiling["model_calls"]} model calls of a ceiling of {ceiling["maximum_model_calls"]}, and the run {stopped}.</li>')
    how = "".join(f'<div><dt>{escape(engine["label"])}</dt><dd>{escape(engine["how"])}</dd></div>' for engine in record.value["engines"])
    return (f'<div class="md-band md-quiet" id="runs" aria-labelledby="runs-title"><h2 id="runs-title">How the runs were made</h2>'
            f'<p class="md-reading">Each decision maker that was asked got the same three questions from the same written policy '
            f'({escape(policy["reference"])}): the first question asks how likely it is that the request carries the policy\'s '
            f'indicators, the second asks for the next action from {len(policy["actions"])} choices, and the third asks how severe '
            f'the harm would be on {len(policy["severity_levels"])} levels. The step holds a request when the indicators reach '
            f'{escape(_number(policy["indicator_threshold"]))}, when the answer is not to proceed, or when the harm reaches the '
            f'{escape(policy["severity_floor"])} level; hold is also the answer when nobody answers. The policy carries '
            f'{policy["pattern_count"]} written patterns that the rules read.</p>'
            f'<dl class="md-dl">{how}</dl><ul class="md-plain">{"".join(lines)}</ul>'
            f'<p class="md-reading">Source: <a href="{escape(source["url"])}">{escape(source["citation"].rstrip("."))}</a>, licence '
            f'{escape(source["license"])}. {escape(source["note"])}</p></div>')


def page_body(record: PageRecord) -> str:
    """The page's own markup inside the site frame, written from one record."""
    from .model_directory_pages import contents
    value = record.value
    links = [("summary", "What each decision maker did")]
    links += [(f"request-{position}", f"Request {position}") for position in range(1, len(record.scenarios) + 1)]
    links += [("not-measured", "Not measured"), ("runs", "How the runs were made")]
    intro = ('<div class="md-band md-intro"><p class="eyebrow">Case study</p><h1 id="red-team-title">'
             f'{escape(value["title"])}</h1><p class="lede">{escape(value["lede"])} {escape(value["decision_sentence"])}</p>'
             + contents(links)
             + '<div class="md-actions"><a class="button secondary" href="/examples">More examples</a>'
             '<a class="button secondary" href="/how-it-works">How Baltor works</a></div></div>')
    measured = ('<div class="md-band" id="summary" aria-labelledby="summary-title"><h2 id="summary-title">What each decision '
                f'maker did</h2><p class="md-reading">{escape(value["what_is_measured"])}</p>' + _summary_table(record)
                + f'<p class="md-reading">{_summary_sentences(record)}</p></div>')
    scenarios = "".join(_scenario_band(record, scenario, position) for position, scenario in enumerate(record.scenarios, start=1))
    limits = ('<div class="md-band" id="not-measured" aria-labelledby="not-measured-title"><h2 id="not-measured-title">Not '
              'measured</h2><ul class="md-plain">' + "".join(f"<li>{escape(item)}</li>" for item in value["not_measured"]) + "</ul></div>")
    return intro + measured + scenarios + limits + _runs_band(record)


def red_team_page(record: PageRecord, site_map, display_name: str) -> str:
    """The whole page, framed like the other pages the service renders on its own."""
    from .model_directory_pages import SCHEMA_CONTEXT, Page, breadcrumbs, canonical, frame
    entry = site_map.page(ADDRESS)
    if entry is None:
        raise RedTeamPageError(f"the site map does not list {ADDRESS}")
    structured = {"@context": SCHEMA_CONTEXT, "@type": "Article", "name": entry.title, "url": canonical(site_map, ADDRESS),
                  "description": entry.description, "license": "https://creativecommons.org/publicdomain/zero/1.0/",
                  "isBasedOn": record.value["source"]["url"],
                  "breadcrumb": breadcrumbs(site_map, (("Home", "/"), ("Examples", "/examples"), (entry.title, ADDRESS)))}
    return frame(site_map, display_name, Page(ADDRESS, VIEW, entry.title, entry.description, page_body(record), structured,
                                              "red-team-title"))


@lru_cache(maxsize=4)
def _framed(display_name: str) -> bytes:
    from .web_site_map import load_site_map
    return red_team_page(load_page_record(), load_site_map(), display_name).encode("utf-8")


def rendered(path: str, method: str, display_name: str, host: "str | None" = None):
    """`(body, media_type)` for the page, at its address on any hostname and at the root of its own hostname, or None.

    The page is rendered once for each deployment name, then given the head the site map writes for the request's
    address and hostname and the release versions of its assets, as the library page is."""
    from . import web_pages
    if method not in ("GET", "HEAD"):
        return None
    site_map = web_pages.packaged_site_map()
    address = site_map.root_address(host) if path == "/" else path
    if not handles(address):
        return None
    body = _framed(display_name)
    head = web_pages.page_head(site_map, path, host, display_name)
    if head is not None:
        body = web_pages.with_page_head(body, head)
    return web_pages.version_asset_references(body), web_pages.HTML_MEDIA_TYPE
