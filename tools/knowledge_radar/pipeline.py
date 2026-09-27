"""The radar's daily run: staged, resumable, and idempotent for one day's work identity.

```text
day folder <library>/radar/<day>/
├── run.json            the run's work identity, revision, registry digest and options (written once)
├── run.lock            held while a process works on the day; a second trigger answers already_running
├── journal.jsonl       one line per stage start, finish, skip and resume
├── stages/<stage>.done a stage that finished; a resumed run skips it and reads its files
├── plan.json           knowledge_radar_plan/v1
├── sources/<question>/<binding>.json   each source answer, written once; never fetched again on resume
├── requests.jsonl      every network request of the run (library_network_request/v1)
├── links.json          the link check of every seed link
├── checks/<question>.json              knowledge_radar_source_check/v1 per binding, with its outcome
├── briefs/<question>.json and .md      knowledge_radar_brief/v1 and the rendered SKILL.md, or a notice
├── proposals.json      harness_candidate_batch_proposals/v2 for the existing preparation factory
├── catalogue/          the candidate catalogue the factory wrote (exclusive; never rewritten)
├── prechecks.json, sandbox.json, vetting.json  the separate vetting dimensions of every package
├── graph.json          invalidation edges: which source, table or asset each package depends on
├── failures.json       scoped, expiring negative results (a source that could not be read today)
├── feed/               radar-index.json, radar-feed.json (JSON Feed 1.1), radar.xml (RSS 2.0)
└── run-report.json     counts, the answer state of every question and the next steps
<library>/radar/state/  only the final stage writes it: the last successful checks and four
                        freshness times per source binding
```

Stages: plan, collect, links, diff, brief, package, vet, feed, record. The run
holds no model authority and makes no model call. Network reads need the
run's explicit grant and each engine's source contract.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from loop_engine.core.library_ingestion.request_log import RequestBudget, RequestLog

from . import brief as briefs
from . import feed as feeds
from . import packages, planner, vetting
from .engines import FAILED, EngineAnswer, RadarEngineError, ReadContext, default_registry
from .engines_network import RadarNetwork
from .records import (
    CHECK_OUTCOMES,
    CHECKED_OUTCOMES,
    STORED,
    SourceCheck,
    read_check,
    read_contracts,
    read_observation,
    read_registry,
)

RUN_RECORD_TYPE = "knowledge_radar_run/v1"
ANSWER_RECORD_TYPE = "knowledge_radar_source_answer/v1"
REPORT_RECORD_TYPE = "knowledge_radar_run_report/v1"
STATE_RECORD_TYPE = "knowledge_radar_state/v1"
FAILURE_RECORD_TYPE = "knowledge_radar_failure/v1"
EDGE_RECORD_TYPE = "knowledge_radar_dependency_edge/v1"
STAGES = ("plan", "collect", "links", "diff", "brief", "package", "vet", "feed", "record")
REGISTRY = Path("tools/knowledge_radar/questions-v1.json")
CONTRACTS = Path("tools/knowledge_radar/source-contracts-v1.json")
NETWORK_ENGINES = frozenset(("github_search", "github_advisories", "github_releases", "owner_directory",
                             "huggingface_models", "arxiv_listing", "openalex_works", "endoflife_calendar",
                             "federal_register"))


class RadarRunError(RuntimeError):
    """The run refused to start or to continue, with a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class RunRequest:
    repository: Path
    library: Path
    as_of: str
    output: "Path | None" = None
    collector_state: "Path | None" = None
    network_allowed: bool = False
    writes_allowed: bool = False
    maximum_requests: int = 400
    only: tuple = ()
    link_checks: bool = True
    sandbox_tests: bool = True
    demand: "Path | None" = None
    stop_after: str = ""
    gh: str = "gh"

    @property
    def day_folder(self) -> Path:
        return Path(self.output) if self.output else Path(self.library) / self.as_of

    @property
    def state_folder(self) -> Path:
        return Path(self.library) / "state"


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, value, *, exclusive: bool = False) -> None:
    """Write a JSON file whole: to a temporary name first, then renamed, so a reader never sees half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    if exclusive:
        with path.open("xb") as stream:
            stream.write(body)
        return
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes(body)
    os.replace(temporary, path)


def read_json(path: Path):
    return json.loads(Path(path).read_bytes())


def revision_of(repository: Path) -> str:
    result = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True,
                            timeout=30, check=False)
    if result.returncode != 0:
        raise RadarRunError("radar_revision_unreadable", "the repository revision could not be read")
    return result.stdout.strip()


@dataclass
class Run:
    request: RunRequest
    registry: object = None
    contracts: dict = field(default_factory=dict)
    folder: Path = None
    revision: str = ""
    journal: Path = None
    network: object = None

    # Journal and stage markers ---------------------------------------------------------------------------

    def log(self, stage: str, event: str, detail: str = "") -> None:
        with self.journal.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"at": now_utc(), "stage": stage, "event": event, "detail": detail[:500]}) + "\n")

    def done(self, stage: str) -> bool:
        return (self.folder / "stages" / f"{stage}.done").is_file()

    def mark(self, stage: str, detail: dict) -> None:
        write_json(self.folder / "stages" / f"{stage}.done", {"stage": stage, "at": now_utc(), **detail})

    # Stage helpers ---------------------------------------------------------------------------------------

    def plan_record(self) -> dict:
        return read_json(self.folder / "plan.json")

    def selected(self) -> list:
        return [self.registry.question(row["question_id"]) for row in self.plan_record()["selected"]]

    def previous_checks(self, question) -> list:
        path = self.request.state_folder / "checks" / f"{question.id}.json"
        if not path.is_file():
            return []
        try:
            rows = read_json(path)
            return [read_check(row) if row else None for row in rows]
        except (OSError, ValueError):
            return []

    def state(self) -> dict:
        path = self.request.state_folder / "questions.json"
        if not path.is_file():
            return {}
        value = read_json(path)
        return value.get("questions", {}) if isinstance(value, dict) else {}


def _evidence(request: RunRequest) -> dict:
    """The change time of each local source, so a question re-runs when a source it reads changed."""
    evidence = {}
    repository = Path(request.repository)
    for engine, path, key in (("model_directory", "src/loop_engine/core/service_runtime/web_assets/model-directory/manifest.json", "built_at"),
                              ("endpoint_directory", "src/loop_engine/core/service_runtime/web_assets/model-directory/manifest.json", "built_at"),
                              ("mcp_directory", "src/loop_engine/core/service_runtime/web_assets/directory/manifest.json", "generated_at")):
        try:
            evidence[engine] = str(read_json(repository / path).get(key) or "")
        except (OSError, ValueError):
            evidence[engine] = ""
    if request.collector_state:
        try:
            evidence["collector_state"] = str(read_json(Path(request.collector_state) / "combined-latest.json").get("finished_at") or "")
        except (OSError, ValueError):
            evidence["collector_state"] = ""
    return evidence


def _asset_digests(repository: Path, registry) -> dict:
    digests = {}
    for question in registry.active():
        names = sorted(set(question.assets.values()))
        if not names:
            continue
        hasher = hashlib.sha256()
        for name in names:
            folder = Path(repository) / packages.ASSETS_PATH / name
            for path in sorted(folder.rglob("*")) if folder.is_dir() else ():
                if path.is_file() and "__pycache__" not in path.parts:
                    hasher.update(path.relative_to(folder).as_posix().encode() + b"\0" + path.read_bytes())
        digests[question.id] = hasher.hexdigest()
    return digests


def stage_plan(run: Run) -> dict:
    demand = {}
    if run.request.demand:
        value = read_json(run.request.demand)
        demand = {key: value for key, value in value.items() if isinstance(value, (int, float))} if isinstance(value, dict) else {}
    record = planner.plan(run.registry, run.state(), run.request.as_of, evidence=_evidence(run.request), demand=demand,
                          only=tuple(run.request.only) or None,
                          asset_digests=_asset_digests(run.request.repository, run.registry))
    write_json(run.folder / "plan.json", record)
    return {"selected": len(record["selected"]), "deferred": len(record["deferred"])}


def _read_binding(run: Run, engines, metadata, question, index: int, binding) -> dict:
    checked_at = now_utc()
    contract = run.contracts.get(binding.engine)
    if contract is None:
        answer = EngineAnswer(FAILED, f"no source contract names {binding.engine}")
    elif binding.engine in NETWORK_ENGINES and run.network is None:
        answer = EngineAnswer(FAILED, "the run holds no network authority")
    else:
        context = ReadContext(question, binding, checked_at, run.request.as_of, contract, Path(run.request.repository),
                              run.request.collector_state, run.network)
        try:
            answer = engines.engine(binding.engine).read(context)
        except RadarEngineError as error:
            answer = EngineAnswer(FAILED, str(error))
        except Exception as error:  # noqa: BLE001 - an engine that fails is recorded, never trusted
            answer = EngineAnswer(FAILED, f"the engine failed: {type(error).__name__}")
    guards = set()
    for text in answer.guard_texts:
        guards |= {hashlib.sha256(shingle.encode()).hexdigest() for shingle in vetting.shingles(text)}
    engine = metadata.engines.get(binding.engine)
    return {"record_type": ANSWER_RECORD_TYPE, "question_id": question.id, "binding_index": index,
            "engine_id": binding.engine, "engine_version": getattr(engine, "engine_version", "unknown"),
            "section": binding.section, "status": answer.status, "reason": answer.reason, "requests": answer.requests,
            "checked_at": checked_at, "observations": [item.to_dict() for item in answer.observations],
            "excluded": [list(item) for item in answer.excluded], "guard_shingles": sorted(guards)}


def stage_collect(run: Run) -> dict:
    engines = default_registry(network_allowed=run.network is not None)
    metadata = default_registry(network_allowed=True)
    read = skipped = 0
    for question in run.selected():
        for index, binding in enumerate(question.sources):
            path = run.folder / "sources" / question.id / f"{index:02d}.json"
            if path.is_file():
                skipped += 1
                continue
            write_json(path, _read_binding(run, engines, metadata, question, index, binding))
            read += 1
    if run.network is not None:
        write_json(run.folder / "requests-summary.json", run.network.log.summary())
    return {"read": read, "resumed_from_disk": skipped}


def _answers(run: Run, question) -> list:
    return [read_json(run.folder / "sources" / question.id / f"{index:02d}.json") for index in range(len(question.sources))]


def stage_links(run: Run) -> dict:
    results = {}
    if run.request.link_checks and run.network is not None:
        for question in run.selected():
            for answer in _answers(run, question):
                if answer["engine_id"] != "curated_seed":
                    continue
                for claim in answer["observations"]:
                    addresses = [claim["url"]] + [value for name, value in sorted(claim["facts"].items())
                                                  if name.startswith("link_") and isinstance(value, str)]
                    for address in addresses:
                        if address in results:
                            continue
                        parts = address.split("/", 3)
                        host, path = parts[2], "/" + (parts[3] if len(parts) > 3 else "")
                        try:
                            response = run.network.get("seed_link_check", host, path.split("#", 1)[0] or "/")
                            status = response.status
                        except Exception as error:  # noqa: BLE001 - recorded as unchecked, never as resolved
                            status, error_name = None, type(error).__name__
                        else:
                            error_name = ""
                        results[address] = {"status": status, "checked_at": now_utc(),
                                            "resolved": status is not None and 200 <= status < 400,
                                            "gone": status in (404, 410), "error": error_name}
    write_json(run.folder / "links.json", {"record_type": "knowledge_radar_link_checks/v1",
                                           "performed": bool(run.request.link_checks and run.network is not None),
                                           "links": results})
    return {"checked": len(results), "resolved": sum(1 for row in results.values() if row["resolved"])}


def _apply_links(claim: dict, links: dict, question) -> dict:
    """A seed claim is verified only when its own link resolved in this run's link check."""
    if claim["engine_id"] != "curated_seed":
        return claim
    check = links.get(claim["url"])
    if check and check["resolved"]:
        return {**claim, "last_verified_at": check["checked_at"], "review_after": question.review_after(check["checked_at"])}
    return claim


def stage_diff(run: Run) -> dict:
    metadata = default_registry(network_allowed=True)
    links = read_json(run.folder / "links.json")["links"]
    counts = {outcome: 0 for outcome in CHECK_OUTCOMES}
    for question in run.selected():
        previous = run.previous_checks(question)
        rows = []
        for index, answer in enumerate(_answers(run, question)):
            observations = tuple(read_observation(_apply_links(claim, links, question)) for claim in answer["observations"])
            engine = metadata.engines.get(answer["engine_id"])
            prior = previous[index] if index < len(previous) else None
            result = EngineAnswer(answer["status"], answer["reason"], observations, answer["requests"])
            outcome, changes = briefs.check_outcome(result, prior, getattr(engine, "material_facts", ()))
            kept = observations if outcome in CHECKED_OUTCOMES or outcome == "partially_checked" else ()
            check = SourceCheck(question.id, answer["engine_id"], answer["engine_version"], answer["section"], outcome,
                                answer["reason"], kept, answer["requests"], answer["checked_at"], changes)
            counts[outcome] += 1
            rows.append(check.to_dict())
        write_json(run.folder / "checks" / f"{question.id}.json", rows)
    return counts


def stage_brief(run: Run) -> dict:
    built = notices = refused = 0
    for question in run.selected():
        if not any(kind in STORED for kind in question.delivery):
            continue
        checks = [read_check(row) for row in read_json(run.folder / "checks" / f"{question.id}.json")]
        sections = briefs.build_sections(question, checks, run.previous_checks(question), run.request.as_of)
        excluded = [tuple(item) for answer in _answers(run, question) for item in answer["excluded"]]
        record = briefs.build_brief(question, sections, run.request.as_of, excluded=excluded)
        if record["state"] != briefs.CURRENT:
            write_json(run.folder / "briefs" / f"{question.id}.json",
                       briefs.notice(question, run.request.as_of, record["decision"]))
            notices += 1
            continue
        rendered = briefs.render_skill(question, record, packages.files_meaning(question))
        guards = {digest for answer in _answers(run, question) for digest in answer["guard_shingles"]}
        titles = [claim["title"] for section in record["sections"] for claim in section["claims"] + section["carried_claims"]]
        allowed = {hashlib.sha256(shingle.encode()).hexdigest() for title in titles for shingle in vetting.shingles(title)}
        texts = rendered + "\n" + json.dumps(record, ensure_ascii=False)
        shared = {hashlib.sha256(shingle.encode()).hexdigest() for shingle in vetting.shingles(texts)} & guards
        record["copied_text_check"] = "failed" if shared - allowed else "passed"
        write_json(run.folder / "briefs" / f"{question.id}.json", record)
        (run.folder / "briefs" / f"{question.id}.md").write_text(rendered, encoding="utf-8")
        if record["copied_text_check"] == "failed":
            refused += 1
        else:
            built += 1
    return {"briefs": built, "notices": notices, "copied_text_refused": refused}


def stage_package(run: Run) -> dict:
    repository = Path(run.request.repository)
    licence = (repository / "LICENSE").read_bytes()
    registry_sha, contracts_sha = sha256_file(repository / REGISTRY), sha256_file(repository / CONTRACTS)
    proposals, problems, tools_done = [], [], set()
    for question in run.selected():
        path = run.folder / "briefs" / f"{question.id}.json"
        table = None
        if path.is_file():
            record = read_json(path)
            if record.get("record_type") == "knowledge_radar_brief/v1" and record["copied_text_check"] == "passed":
                checks = [{key: row[key] for key in ("engine_id", "engine_version", "section", "outcome", "checked_at",
                                                     "requests")} for row in read_json(run.folder / "checks" / f"{question.id}.json")]
                proposal, table = packages.brief_proposal(question, record, licence=licence, revision=run.revision,
                                                          registry_sha256=registry_sha, contracts_sha256=contracts_sha,
                                                          checks=checks)
                proposals.append(proposal)
        for kind, asset in sorted(question.assets.items()):
            if kind == "tool" and asset in tools_done:
                continue
            try:
                proposals.append(packages.asset_proposal(repository, asset, as_of=run.request.as_of,
                                                         table=table if kind == "decision_helper" else None,
                                                         question=question))
                tools_done.add(asset)
            except packages.PackagingError as error:
                problems.append({"question_id": question.id, "asset": asset, "reason": str(error)})
    write_json(run.folder / "packaging-problems.json", problems)
    if not proposals:
        return {"proposals": 0, "problems": len(problems)}
    record = packages.proposals_record(repository, run.revision, proposals)
    write_json(run.folder / "proposals.json", record)
    catalogue = run.folder / "catalogue"
    if not catalogue.exists():
        from tools.prepare_harness_candidates import PreparationError, PreparationRequest, prepare
        try:
            report = prepare(PreparationRequest(repository, run.folder / "proposals.json", catalogue, True))
        except PreparationError as error:
            raise RadarRunError("radar_preparation_refused", str(error)) from None
        write_json(run.folder / "preparation-report.json", report)
    return {"proposals": len(proposals), "problems": len(problems)}


def stage_vet(run: Run) -> dict:
    catalogue = run.folder / "catalogue"
    if not (catalogue / "items.json").is_file():
        write_json(run.folder / "vetting.json", {})
        return {"packages": 0}
    repository = Path(run.request.repository)
    prechecks = vetting.native_prechecks(catalogue, repository)
    write_json(run.folder / "prechecks.json", prechecks)
    proposals = {row["id"]: row for row in read_json(run.folder / "proposals.json")["proposals"]}
    links = read_json(run.folder / "links.json")
    sandbox, records = {}, {}
    for identity, proposal in proposals.items():
        outcome = prechecks.get(identity, {"refused": True, "reasons": ["missing"]})
        inspected = "failed" if outcome.get("refused") else "passed"
        if proposal["family"] == "knowledge_radar_brief":
            question = run.registry.question(proposal["symbols"][0])
            record = read_json(run.folder / "briefs" / f"{question.id}.json")
            findings = vetting.claim_findings(record) + vetting.schema_findings(record, briefs.BRIEF_SCHEMA, "brief")
            if "data_file" in question.delivery:
                table, schema = briefs.build_table(question, record)
                findings += vetting.schema_findings(table, schema, "table")
            seeds = [claim for section in record["sections"] for claim in section["claims"] if claim["engine_id"] == "curated_seed"]
            gone = [claim["url"] for claim in seeds if links["links"].get(claim["url"], {}).get("gone")]
            unresolved = [claim["url"] for claim in seeds if not links["links"].get(claim["url"], {}).get("resolved")]
            source_identity = "failed" if gone else ("not_done" if unresolved else "passed")
            notes = [f"{code}: {detail}" for code, detail in findings]
            if unresolved:
                notes.append(f"{len(unresolved)} seed links were not verified by a link check in this run")
            records[identity] = vetting.vetting_record(
                identity, source_identity=source_identity, claims="failed" if findings else "passed",
                inspected=inspected, tested="not_applicable", notes=notes + list(outcome.get("reasons", [])))
            continue
        declaration, _bodies = packages.read_asset(repository, proposal["symbols"][0])
        if run.request.sandbox_tests:
            result = vetting.sandbox_test(catalogue / "packages" / identity, declaration["test"])
        else:
            result = {"status": "not_done", "reason": "sandbox tests were not requested for this run"}
        sandbox[identity] = result
        records[identity] = vetting.vetting_record(
            identity, source_identity="not_applicable", claims="not_applicable", inspected=inspected,
            tested=result["status"], notes=list(outcome.get("reasons", [])) + ([result.get("reason")] if result.get("reason") else []))
    write_json(run.folder / "sandbox.json", sandbox)
    write_json(run.folder / "vetting.json", records)
    failed = sum(1 for record in records.values() if "failed" in record["dimensions"].values())
    return {"packages": len(records), "with_a_failed_dimension": failed}


def _package_for(question, proposals: dict) -> "str | None":
    for identity, proposal in proposals.items():
        if proposal["family"] == "knowledge_radar_brief" and proposal["symbols"][0] == question.id:
            return identity
    for identity, proposal in proposals.items():
        if proposal["symbols"][0] in question.assets.values():
            return identity
    return None


def stage_feed(run: Run) -> dict:
    proposals = {}
    if (run.folder / "proposals.json").is_file():
        proposals = {row["id"]: row for row in read_json(run.folder / "proposals.json")["proposals"]}
    vetted = read_json(run.folder / "vetting.json") if (run.folder / "vetting.json").is_file() else {}
    prechecked = read_json(run.folder / "prechecks.json") if (run.folder / "prechecks.json").is_file() else {}
    selected = {row["question_id"] for row in run.plan_record()["selected"]}
    earlier = run.state()
    rows = []
    for question in run.registry.questions:
        record, as_of = None, run.request.as_of
        path = run.folder / "briefs" / f"{question.id}.json"
        if path.is_file():
            record = read_json(path)
        identity = _package_for(question, proposals) if question.id in selected else None
        if question.id in selected or question.status != "active":
            state = feeds.answer_state(question, record, vetted.get(identity) if identity else None,
                                       prechecked.get(identity) if identity else None)
        else:
            # Not due today: the answer of the run that last built it stands until its own valid-until day.
            prior = earlier.get(question.id) or {}
            identity, as_of = prior.get("package_identity"), prior.get("last_built_as_of") or as_of
            state = "candidate_available" if identity else "needs_research"
        brief_record = record if record and record.get("record_type") == "knowledge_radar_brief/v1" else {}
        rows.append({"question_id": question.id, "title": question.title, "question": question.question,
                     "area": question.area, "answer_state": state, "as_of": as_of,
                     "valid_until": brief_record.get("valid_until"), "confidence": brief_record.get("confidence"),
                     "sections": len(brief_record.get("sections", [])) if brief_record else None,
                     "claims": sum(len(section["claims"]) for section in brief_record.get("sections", [])) if brief_record else None,
                     "package_identity": identity, "delivery": list(question.delivery),
                     "review_requirement": question.review_requirement, "gap_reason": question.gap_reason})
    index = feeds.index_record(run.registry, run.request.as_of, rows)
    (run.folder / "feed").mkdir(parents=True, exist_ok=True)
    (run.folder / "feed" / "radar-index.json").write_bytes(feeds.dumps(index))
    (run.folder / "feed" / "radar-feed.json").write_bytes(feeds.dumps(feeds.json_feed(index)))
    (run.folder / "feed" / "radar.xml").write_text(feeds.rss(index), encoding="utf-8")
    return index["answer_states"]


def stage_record(run: Run) -> dict:
    """The only stage that writes the shared state, and only after every earlier stage finished."""
    state_folder = run.request.state_folder
    state = run.state()
    vetted = read_json(run.folder / "vetting.json") if (run.folder / "vetting.json").is_file() else {}
    proposals = {}
    if (run.folder / "proposals.json").is_file():
        proposals = {row["id"]: row for row in read_json(run.folder / "proposals.json")["proposals"]}
    digests = _asset_digests(run.request.repository, run.registry)
    edges, failures = [], []
    finished = now_utc()
    for question in run.selected():
        rows = read_json(run.folder / "checks" / f"{question.id}.json")
        previous = run.previous_checks(question)
        kept = []
        entry = dict(state.get(question.id) or {})
        freshness = entry.get("freshness") or {}
        for index, row in enumerate(rows):
            binding = question.sources[index]
            key = f"{index:02d}:{binding.engine}:{planner.digest(binding.to_dict())[:12]}"
            times = dict(freshness.get(key) or {})
            times["last_attempted_retrieval"] = row["checked_at"]
            if row["outcome"] in CHECKED_OUTCOMES or row["outcome"] == "partially_checked":
                times["last_successful_retrieval"] = row["checked_at"]
                kept.append(row)
            else:
                # A failed read keeps the last successful check as the baseline; it never becomes "no change".
                kept.append(previous[index].to_dict() if index < len(previous) and previous[index] else None)
                failures.append({"record_type": FAILURE_RECORD_TYPE, "scope": {"question_id": question.id,
                                 "binding": key, "engine_id": row["engine_id"]}, "outcome": row["outcome"],
                                 "reason": row["reason"], "observed_at": row["checked_at"],
                                 "expires": question.review_after(row["checked_at"]),
                                 "meaning": "this source could not be read on this day; it says nothing about the "
                                            "source's quality and expires on the date named"})
            if row["outcome"] == "checked_material_change":
                times["last_material_change"] = row["checked_at"]
            freshness[key] = times
            edges.append({"record_type": EDGE_RECORD_TYPE, "from": f"source:{key}", "to": f"brief:{question.id}",
                          "relation": "claims_read_from"})
        identity = _package_for(question, proposals)
        record = vetted.get(identity) if identity else None
        evaluated = record is not None and "failed" not in record["dimensions"].values()
        for times in freshness.values():
            if evaluated:
                times["last_successful_evaluation"] = finished
        for kind, asset in question.assets.items():
            relation = "reads_table_of" if kind == "decision_helper" else "implemented_by"
            edges.append({"record_type": EDGE_RECORD_TYPE, "from": f"asset:{asset}", "to": f"question:{question.id}",
                          "relation": relation})
        edges.append({"record_type": EDGE_RECORD_TYPE, "from": f"registry:{question.id}",
                      "to": f"brief:{question.id}", "relation": "declared_by"})
        entry.update({"last_built_as_of": run.request.as_of, "last_built_at": finished, "last_run_folder": str(run.folder),
                      "package_identity": identity, "asset_digest": digests.get(question.id), "freshness": freshness})
        state[question.id] = entry
        write_json(state_folder / "checks" / f"{question.id}.json", kept)
    write_json(state_folder / "questions.json", {"record_type": STATE_RECORD_TYPE, "updated_at": finished,
                                                 "questions": state})
    write_json(run.folder / "graph.json", {"record_type": "knowledge_radar_graph/v1", "edges": edges})
    write_json(run.folder / "failures.json", {"record_type": "knowledge_radar_failures/v1", "failures": failures})
    return {"questions": len(run.selected()), "failures": len(failures), "edges": len(edges)}


STAGE_FUNCTIONS = {"plan": stage_plan, "collect": stage_collect, "links": stage_links, "diff": stage_diff,
                   "brief": stage_brief, "package": stage_package, "vet": stage_vet, "feed": stage_feed,
                   "record": stage_record}


def _report(run: Run) -> dict:
    index = read_json(run.folder / "feed" / "radar-index.json") if (run.folder / "feed" / "radar-index.json").is_file() else {}
    vetted = read_json(run.folder / "vetting.json") if (run.folder / "vetting.json").is_file() else {}
    prechecked = read_json(run.folder / "prechecks.json") if (run.folder / "prechecks.json").is_file() else {}
    dimensions = {}
    for record in vetted.values():
        for name, value in record["dimensions"].items():
            dimensions.setdefault(name, {}).setdefault(value, 0)
            dimensions[name][value] += 1
    stages = {stage: read_json(run.folder / "stages" / f"{stage}.done") for stage in STAGES if run.done(stage)}
    return {"record_type": REPORT_RECORD_TYPE, "as_of": run.request.as_of, "revision": run.revision,
            "folder": str(run.folder), "stages": stages,
            "questions_declared": len(run.registry.questions), "questions_active": len(run.registry.active()),
            "questions_selected": len(run.plan_record()["selected"]) if (run.folder / "plan.json").is_file() else 0,
            "packages": len(vetted), "prechecks_passed": sum(1 for row in prechecked.values() if not row["refused"]),
            "prechecks_refused": sum(1 for row in prechecked.values() if row["refused"]),
            "vetting_dimensions": dimensions, "answer_states": index.get("answer_states", {}),
            "model_calls": 0, "approved": 0, "published": 0,
            "next": "Independent review of the candidate catalogue through tools/review_catalogue_candidates.py "
                    "--content-profile native-original by a model family other than anthropic; strict review "
                    "(two families, sources on every claim) for packages whose review_requirement says so."}


def run(request: RunRequest) -> dict:
    """Run or resume one day's radar work. Returns the run report, or already_running/already_complete."""
    if not request.writes_allowed:
        raise RadarRunError("radar_writes_not_authorized", "the run writes a day folder only with explicit authority")
    repository = Path(request.repository).resolve()
    registry = read_registry(read_json(repository / REGISTRY))
    contracts = read_contracts(read_json(repository / CONTRACTS))
    revision = revision_of(repository)
    options = {"network_allowed": request.network_allowed, "maximum_requests": request.maximum_requests,
               "only": list(request.only), "link_checks": request.link_checks, "sandbox_tests": request.sandbox_tests,
               "collector_state": str(request.collector_state or "")}
    identity = planner.digest({"as_of": request.as_of, "revision": revision, "registry": sha256_file(repository / REGISTRY),
                               "contracts": sha256_file(repository / CONTRACTS), "options": options})
    folder = request.day_folder.absolute()
    folder.parent.mkdir(parents=True, exist_ok=True)
    folder.mkdir(exist_ok=True)
    run_file = folder / "run.json"
    if run_file.is_file():
        existing = read_json(run_file)
        if existing.get("work_identity") != identity:
            raise RadarRunError("radar_day_folder_taken",
                                f"{folder} holds another run's work; choose a new output folder name")
    else:
        write_json(run_file, {"record_type": RUN_RECORD_TYPE, "work_identity": identity, "as_of": request.as_of,
                              "revision": revision, "registry_version": registry.registry_version, "options": options,
                              "started_at": now_utc()}, exclusive=True)
    lock = os.open(folder / "run.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running", "folder": str(folder)}
        current = Run(request, registry, contracts, folder, revision, folder / "journal.jsonl")
        if all(current.done(stage) for stage in STAGES):
            current.log("run", "duplicate_trigger", "every stage was already done; nothing was written")
            return {"status": "already_complete", "folder": str(folder)}
        if request.network_allowed:
            current.network = RadarNetwork(RequestBudget(request.maximum_requests, maximum_pause_seconds=180, reserve=50),
                                           RequestLog(folder / "requests.jsonl"), contracts, gh=request.gh)
        resumed = any(current.done(stage) for stage in STAGES)
        current.log("run", "resume" if resumed else "start", identity)
        for stage in STAGES:
            if current.done(stage):
                current.log(stage, "skip", "done in an earlier process")
                continue
            current.log(stage, "start")
            detail = STAGE_FUNCTIONS[stage](current)
            current.mark(stage, {"detail": detail})
            current.log(stage, "done", json.dumps(detail)[:400])
            if request.stop_after == stage:
                current.log("run", "stopped", f"stopped after {stage} as requested")
                return {"status": "stopped", "after": stage, "folder": str(folder)}
        report = _report(current)
        write_json(folder / "run-report.json", report)
        current.log("run", "finish")
        return {"status": "complete", **report}
    finally:
        os.close(lock)
