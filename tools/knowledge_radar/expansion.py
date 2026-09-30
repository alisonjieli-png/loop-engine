"""Daily source-led conversations feeding the existing native candidate factory.

Discovery, production critique, native preparation and independent publication
remain separate. Every stage has an immutable managed record and a reserved
model dispatch. Interrupted or unknown calls are never silently repeated.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

from tools import prepare_harness_candidates as factory
from tools.generate_original_native_candidates import secret_present
from loop_engine.catalog.query import IntelligenceQuery
from loop_engine.catalog.stores.sqlite_store import SQLiteRecordStore
from loop_engine.loop.service_loop_envelope import ServiceLoopSpec, run_service_operation

from .community_store import CommunityStore
from .community_intake import public_url
from .expansion_contracts import FORMATS, validate
from .packages import file_record

POLICY_PATH = "tools/knowledge_radar/expansion-dimensions-v1.json"
SOURCES = (POLICY_PATH, "tools/knowledge_radar/expansion.py", "tools/knowledge_radar/expansion_contracts.py",
           "tools/knowledge_radar/expansion_model.py")
STAGES = ("opportunity", "interrogation", "production")
DOCUMENT = "community_expansion_work/v1"


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_policy(repository):
    value = json.loads((repository / POLICY_PATH).read_text())
    if value.get("record_type") != "community_expansion_policy/v1":
        raise ValueError("expansion_policy_version")
    for name in ("maximum_work_per_day", "maximum_model_dispatches_per_day", "reported_token_stop_after",
                 "maximum_prompt_bytes", "output_allocation_tokens", "timeout_seconds"):
        if type(value.get(name)) is not int or value[name] <= 0:
            raise ValueError("expansion_policy_limit")
    if not value.get("contexts") or not value.get("questions") or not value.get("dimensions"):
        raise ValueError("expansion_policy_dimensions")
    identities = set()
    for row in value["contexts"]:
        if set(row) != {"id", "industry", "use_case", "job_title", "job_description", "data_types", "signals", "formats"}:
            raise ValueError("expansion_context_shape")
        if row["id"] in identities or not re.fullmatch(r"[a-z][a-z0-9_]*", row["id"]):
            raise ValueError("expansion_context_identity")
        if not row["formats"] or not set(row["formats"]) <= set(FORMATS):
            raise ValueError("expansion_context_format")
        identities.add(row["id"])
    return value


def method_signature(opportunity):
    """Titles, roles, industries and output format cannot manufacture a method."""
    def normalize(value):
        if isinstance(value, list):
            return sorted(normalize(item) for item in value)
        return re.sub(r"\W+", " ", value.casefold()).strip()
    return digest({key: normalize(opportunity[key]) for key in
                   ("mechanism", "input_contract", "output_contract", "acceptance", "known_wrong")})


def choose_context(work, policy, use_counts):
    text = " ".join([work.get("source_title", ""), *work.get("candidate_component_work", []),
                     *work.get("tools_mentioned", [])]).lower()
    def rank(row):
        terms = [row["id"].replace("_", " "), *row["data_types"], *row["formats"]]
        matches = sum(term.replace("_", " ").lower() in text for term in terms)
        signal_matches = len(set(work.get("signal_hints", [])) & set(row["signals"]))
        return (-signal_matches, -matches, use_counts.get(row["id"], 0), row["id"])
    return min(policy["contexts"], key=rank)


def bound_sources(opportunity, work):
    allowed = {public_url(url) for url in [work["source_url"], *work.get("linked_sources", [])]}
    if any(public_url(url) not in allowed for url in opportunity["source_urls"]):
        raise ValueError("invented_source_reference")


def _write_new(path, value):
    if path.resolve() != path or any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError("expansion_output_path_not_plain")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    raw = canonical(value) + b"\n"
    with path.open("xb") as stream:
        stream.write(raw)


def prepare_candidate(repository, folder, opportunity, answer, work, policy, revision):
    """Use the existing complete-native package contract, without executing payloads."""
    validate("production", answer)
    paths = [row["path"] for row in answer["files"]]
    if "AGENTS.md" not in paths or any(path in paths for path in ("LICENSE", "provenance.json")):
        raise ValueError("candidate_entrypoint_or_reserved_path")
    for contract_path in ("contracts/input.schema.json", "contracts/output.schema.json"):
        matches = [row for row in answer["files"] if row["path"] == contract_path]
        if len(matches) != 1 or matches[0]["media_type"] not in ("application/json", "application/schema+json"):
            raise ValueError("candidate_contract_missing")
        schema = json.loads(matches[0]["content"])
        if not isinstance(schema, dict) or not schema:
            raise ValueError("candidate_contract_empty")
        Draft202012Validator.check_schema(schema)
    if opportunity["delivery_format"] in ("python_tool", "typescript_tool") and not any(
            row["role"] in ("skill_script", "executable_tool") for row in answer["files"]):
        raise ValueError("candidate_native_payload_missing")
    if opportunity["delivery_format"] == "n8n_workflow" and not any(
            row["path"].endswith(".json") and isinstance(json.loads(row["content"]), dict)
            and {"nodes", "connections"} <= set(json.loads(row["content"])) for row in answer["files"]
            if row["media_type"] == "application/json"):
        raise ValueError("native_workflow_missing")
    files = [file_record(row["path"], row["content"].encode(), row["role"], row["media_type"]) for row in answer["files"]]
    signature = method_signature(opportunity)
    provenance = {"record_type": "community_expansion_provenance/v1", "source_revision": revision,
                  "discovery_source": work["source_url"], "discovery_digest": work["source_digest"],
                  "source_claims": "unverified discovery metadata; not licensed source content",
                  "authoring": "original model-generated candidate", "model": policy["model"],
                  "producer_family": policy["producer_family"], "method_signature": signature,
                  "execution_tested": False, "independently_reviewed": False, "publication_approved": False}
    files += [file_record("provenance.json", canonical(provenance), "skill_reference", "application/json"),
              file_record("LICENSE", (repository / "LICENSE").read_bytes(), "other", "text/plain")]
    identity = "expansion_" + signature[:40]
    executable = any(row["role"] in ("skill_script", "executable_tool") for row in answer["files"])
    proposal = {"id": identity, "title": opportunity["title"], "purpose": opportunity["purpose"][:1024],
                "sources": list(SOURCES), "layer": "context", "family": "source_led_native_capability",
                "search_tags": list(dict.fromkeys(term[:160] for term in [opportunity["title"].lower(), opportunity["delivery_format"],
                                                  *opportunity["reuse_search_terms"]]))[:20],
                "tags": {"domain": ["source_led_capability"], "language": ["en"], "data_sensitivity": ["public"]},
                "symbols": [], "declared_effects": answer["declared_effects"],
                "kind": "tool" if executable else "instruction_file", "styles": ["codex", "opencode", "claude", "pi"],
                "dependencies": answer["dependencies"], "producer": {"producer_identity": policy["model"], "family": policy["producer_family"],
                                                    "method_identity": "community_expansion/production/v1"}, "files": files}
    document = {"record_type": "harness_candidate_batch_proposals/v2", "source_revision": revision,
                "license": {"expression": "MIT", "path": "LICENSE", "sha256": hashlib.sha256((repository / "LICENSE").read_bytes()).hexdigest()},
                "sources": {name: hashlib.sha256((repository / name).read_bytes()).hexdigest() for name in SOURCES},
                "proposals": [proposal]}
    target = folder / identity
    _write_new(target / "proposals.json", document)
    factory.prepare(factory.PreparationRequest(repository, target / "proposals.json", target / "catalogue", True))
    return {"identity": identity, "catalogue": str(target / "catalogue"), "files": len(files),
            "distinct_file_digests": sorted({row["digest"] for row in files}), "method_signature": signature,
            "next_stage": "independent_native_review", "publication_approved": False, "execution_tested": False}


@dataclass(frozen=True)
class ExpansionRequest:
    repository: Path
    library: Path
    maximum_work: int = 8
    writes_allowed: bool = False
    calls_allowed: bool = False
    candidate_store: Path | None = None


def search_existing(root, terms, maximum_scan=200000):
    """Bounded read-only metadata search, not an assertion that a candidate works."""
    if root is None:
        return {"status": "not_configured", "coverage_complete": False, "hits": []}
    database = Path(root).absolute() / "records.db"
    if not database.is_file() or database.resolve() != database:
        raise ValueError("reuse_catalogue_unavailable")
    words = set(re.findall(r"[a-z0-9]{3,}", " ".join(terms).casefold()))
    candidates, scanned, complete = [], 0, True
    store = SQLiteRecordStore(str(database), read_only=True)
    try:
        for row in store.stream(IntelligenceQuery(lifecycle=("candidate",), namespaces=("library.import", "library.supply"),
                                                 limit=maximum_scan + 1)):
            if scanned >= maximum_scan:
                complete = False
                break
            scanned += 1
            payload = row.get("payload") or {}
            title = str((row.get("attributes") or {}).get("title") or payload.get("name") or "")[:200]
            description = str(payload.get("description") or payload.get("purpose") or "")[:500]
            score = len(words & set(re.findall(r"[a-z0-9]{3,}", (title + " " + description).casefold())))
            if score:
                candidates.append({"identity": row["record_id"], "version": row["record_version"], "title": title,
                                   "description": description, "score": score, "state": "candidate_not_approval"})
                candidates.sort(key=lambda item: (-item["score"], item["identity"]))
                del candidates[8:]
    finally:
        store.close()
    return {"status": "searched", "scanned": scanned, "coverage_complete": complete,
            "method": "word overlap over current candidate metadata", "hits": candidates}


def run(request, *, turn=None, fixture_run=False, fixture_day=None):
    if (turn is not None or fixture_day is not None) and not fixture_run:
        raise ValueError("injected_expansion_engine_requires_fixture_marker")
    repository = Path(request.repository).absolute()
    policy = read_policy(repository)
    if type(request.maximum_work) is not int or request.maximum_work < 1:
        raise ValueError("expansion_work_limit")
    if not (request.writes_allowed and request.calls_allowed):
        return {"record_type": "community_expansion_report/v1", "status": "plan", "model_calls": 0,
                "maximum_work": min(request.maximum_work, policy["maximum_work_per_day"]),
                "stages": list(STAGES), "publication_approved": False}
    if request.candidate_store is None and not fixture_run:
        raise ValueError("existing_material_store_required_for_production")
    revision = factory._git(repository, "rev-parse", "HEAD").decode().strip()
    for name in SOURCES:
        factory._checked_source(repository, revision, name, hashlib.sha256((repository / name).read_bytes()).hexdigest())
    store = CommunityStore(request.library, writes_allowed=True)
    store.root.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = os.open(store.root / "expansion.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"status": "already_running", "publication_approved": False}
        day = fixture_day or datetime.now(timezone.utc).date().isoformat()
        budget_id = "community.expansion.budget." + day
        held = store.get(budget_id)
        budget = held["document"]["data"] if held else {"dispatches": 0, "reported_tokens": 0, "work_started": 0,
            "contexts": {}, "blocked": False, "limits": {name: policy[name] for name in
                ("maximum_work_per_day", "maximum_model_dispatches_per_day", "reported_token_stop_after")}}
        if budget.get("pending_dispatch"):
            budget["blocked"] = True
        outcomes, observed_calls, observed_tokens = [], 0, 0

        def save_budget():
            nonlocal held
            store.put(budget_id, "harness_budget", "expansion", "recorded", budget, expected=held)
            held = store.get(budget_id)

        rows = store.query(kind="research_brief", state="needs_research", limit=1000)
        for row in rows:
            if len(outcomes) >= request.maximum_work or budget["work_started"] >= min(policy["maximum_work_per_day"], budget["limits"]["maximum_work_per_day"]):
                break
            work = row["document"]["data"]
            if work.get("record_type") != "community_component_work_order/v1":
                continue
            if budget["blocked"]:
                break
            identity = "community.expansion.work." + digest({"identity": row["identity"], "version": row["version"]})
            prior = store.get(identity)
            if prior:
                # A completed record needs no second call; an interrupted one needs reconciliation.
                outcomes.append({"source": row["identity"], "status": "already_recorded", "state": prior["document"]["state"]})
                continue
            context = choose_context(work, policy, budget["contexts"])
            budget["work_started"] += 1
            budget["contexts"][context["id"]] = budget["contexts"].get(context["id"], 0) + 1
            save_budget()
            data = {"record_type": DOCUMENT, "source_record": row["identity"], "source_version": row["version"],
                    "source_revision": revision, "policy_digest": digest(policy), "context": context,
                    "day": day, "fixture_run": fixture_run, "stages": [], "publication_approved": False}
            store.put(identity, "research_brief", "expansion", "queued", data)
            status, package, answers = "failed", None, {}
            for stage in STAGES:
                limit = min(policy["maximum_model_dispatches_per_day"], budget["limits"]["maximum_model_dispatches_per_day"])
                token_stop = min(policy["reported_token_stop_after"], budget["limits"]["reported_token_stop_after"])
                if budget["dispatches"] >= limit or budget["reported_tokens"] >= token_stop or budget["blocked"]:
                    status = "budget_stopped"
                    break
                stage_id = identity + "." + stage
                payload = {"work": work, "dimensions": context, "questions": policy["questions"], "conversation": answers,
                           "source_state": "unverified lead", "publication_authority": False}
                if stage == "interrogation":
                    payload["existing_material"] = search_existing(request.candidate_store, answers["opportunity"]["reuse_search_terms"])
                    data["reuse_search"] = payload["existing_material"]
                if turn is None:
                    from .expansion_model import ExpansionTurn
                    turn = ExpansionTurn(policy, repository)
                budget["dispatches"] += 1
                budget["pending_dispatch"] = stage_id
                save_budget()
                store.put(stage_id, "run", "expansion", "queued", {"stage": stage, "input_digest": digest(payload),
                          "day": day, "source_revision": revision, "model": policy["model"]})
                try:
                    result = turn(stage, payload)
                except Exception:  # noqa: BLE001 - unknown external outcome must stop, without leaking prompt or keys
                    result = {"status": "outcome_unknown", "reason": "provider_outcome_unknown",
                              "physical_model_calls": None, "reported_tokens": None}
                calls, tokens = result.get("physical_model_calls"), result.get("reported_tokens")
                if type(calls) is not int or calls not in (0, 1) or type(tokens) is not int or tokens < 0:
                    budget["blocked"] = True
                else:
                    observed_calls += calls
                    observed_tokens += tokens
                    budget["reported_tokens"] += tokens
                    budget["pending_dispatch"] = ""
                save_budget()
                answer = result.get("answer")
                if answer is not None and secret_present(canonical(answer).decode()):
                    result = {key: value for key, value in result.items() if key != "answer"}
                    result.update(status="failed", reason="secret_pattern_in_answer")
                store.put(stage_id, "run", "expansion", "complete" if result["status"] == "complete" else "failed",
                          result, expected=store.get(stage_id))
                data["stages"].append(stage_id)
                if result["status"] != "complete" or budget["blocked"]:
                    status = result.get("reason") or "accounting_unknown"
                    break
                try:
                    answers[stage] = validate(stage, answer)
                    if stage == "opportunity":
                        bound_sources(answer, work)
                        if answer["delivery_format"] not in context["formats"]:
                            raise ValueError("delivery_format_outside_selected_context")
                    if stage == "interrogation":
                        bound_sources(answer["opportunity"], work)
                        if answer["opportunity"]["delivery_format"] not in context["formats"]:
                            raise ValueError("delivery_format_outside_selected_context")
                        if answer["decision"] != "build":
                            status = answer["decision"]
                            break
                        signature = method_signature(answer["opportunity"])
                        if store.get("community.expansion.method." + signature):
                            status = "duplicate_method"
                            break
                    if stage == "production":
                        opportunity = answers["interrogation"]["opportunity"]
                        spec = ServiceLoopSpec("community_candidate_preparation", "practitioner.code_execution",
                            "community_expansion_files/v1", "starter_catalogue_candidate_items/v3", ("reads_fs", "writes_fs"),
                            "Prepare one complete unreviewed native candidate.", "candidate_preparation_failed")
                        package = run_service_operation(store.runtime, spec, lambda _active: prepare_candidate(
                            repository, store.root / "candidates" / day / store.run_id,
                            opportunity, answer, work, policy, revision))
                        store.put("community.expansion.method." + package["method_signature"], "research_brief",
                                  "expansion_method", "complete", package)
                        status = "candidate_prepared"
                except Exception as error:  # noqa: BLE001 - candidate stays unapproved, preserve failed stage
                    status = "candidate_refused:" + type(error).__name__
                    break
            data.update(outcome=status, package=package)
            state = "complete" if status == "candidate_prepared" else "dismissed" if status in ("reuse", "duplicate_method") else "deferred"
            store.put(identity, "research_brief", "expansion", state, data, expected=store.get(identity))
            store.put(row["identity"], "research_brief", row["document"]["source_id"], state,
                      {**work, "expansion_record": identity, "expansion_outcome": status}, expected=row)
            outcomes.append({"source": row["identity"], "status": status, "package": package})
        report = {"record_type": "community_expansion_report/v1", "status": "accounting_blocked" if budget["blocked"] else "complete",
                  "day": day, "source_revision": revision, "fixture_run": fixture_run, "outcomes": outcomes,
                  "candidate_packages": sum(row["status"] == "candidate_prepared" for row in outcomes),
                  "physical_model_calls_observed": observed_calls, "reported_tokens_observed": observed_tokens,
                  "daily_dispatches_reserved": budget["dispatches"], "daily_reported_tokens": budget["reported_tokens"],
                  "accounting_complete": not budget["blocked"], "approved_packages": 0, "published_packages": 0,
                  "token_limit_scope": "reported-usage stop after a call, not an exact preflight total-token bound"}
        store.put("community.expansion.run." + store.run_id, "run", "expansion", "complete", report)
        return report
    finally:
        os.close(lock)
