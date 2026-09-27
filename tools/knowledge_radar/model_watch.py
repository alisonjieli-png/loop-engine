"""Hourly change detection for new model releases: cheap checks, expensive work only on a material change.

The owner, September 27, 2026: "Some things such as model drops, brand new
models, Gemini 4, etc may need hourly checks since these are super
important". The hourly tick reads each watched listing once, keys every
model by its identity, and compares a fingerprint of its material facts with
the last successful snapshot. It never reads a model card, never compares
models and never rebuilds a brief. When a model appears, disappears or
changes, it records the change and marks the questions that read that
listing for re-evaluation; the next radar run answers only those.

```text
tick (hourly)
├── read each watched binding of the registry's hourly question, through the same engines,
│   sending back the validators (ETag, Last-Modified) of the last complete read
├── a 304 answer is a validated "no change": the snapshot stays, the success time moves
├── outcome per source: checked with no relevant change, checked with a material change,
│   partially checked, could not check, source disappeared or access changed
├── snapshot: replaced only after a complete read; a partial or incomplete read adds and
│   changes, never removes
├── four freshness times per source: last attempted retrieval, last successful retrieval,
│   last material change, last successful evaluation (written by the daily run, never here)
└── on a material change: a change record, and one invalidation per question that reads the source
```

A failed read never becomes "no change": the snapshot and the success time
stay as they were, and the outcome names the failure. The first successful
read records a baseline and marks nothing, because a baseline is not a release.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .engines import FAILED, GONE, NOT_MODIFIED, OK, PARTIAL, RadarEngineError, ReadContext, default_registry

CHANGE_RECORD_TYPE = "knowledge_radar_model_change/v1"
TICK_RECORD_TYPE = "knowledge_radar_model_watch_tick/v1"
SNAPSHOT_RECORD_TYPE = "knowledge_radar_model_snapshot/v1"
INVALIDATION_RECORD_TYPE = "knowledge_radar_invalidation/v1"
WATCHED_QUESTION = "models_new_releases"
MAXIMUM_INVALIDATIONS = 2000


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


MATERIAL_FACTS = ("model_id", "provider", "input_price", "output_price", "context", "max_output", "structured_output",
                  "tool_calling", "reasoning", "open_weights", "deprecation_date", "gated")


def fingerprint(observation) -> str:
    """The digest of the facts whose change is material; a count such as downloads is not one of them."""
    material = {"title": observation.title, "licence": observation.licence, "event_at": observation.event_at,
                "effective_until": observation.effective_until,
                **{name: observation.facts.get(name) for name in MATERIAL_FACTS}}
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode("utf-8")).hexdigest()


def _read(path: Path, default):
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError):
        return default


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.write_bytes((json.dumps(value, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def outcome_of(status: str, previous: "dict | None", current: dict, complete: bool = True) -> "tuple[str, dict]":
    """The check outcome and the change lists. Removal counts only after a complete read.

    A 304 answer to the validators of the last complete read is the one kind of "no change" that needs no
    body: the source itself confirmed it. Without an earlier snapshot a 304 proves nothing.
    """
    if status == FAILED:
        return "could_not_check", {}
    if status == GONE:
        return "source_disappeared_or_access_changed", {}
    if status == NOT_MODIFIED:
        if previous is None:
            return "could_not_check", {}
        return "checked_no_relevant_change", {"baseline": False, "added": [], "removed": [], "changed": [],
                                              "validated": True}
    if previous is None:
        baseline = {"baseline": True, "added": [], "removed": [], "changed": []}
        return ("partially_checked" if status == PARTIAL else "checked_material_change"), baseline
    added = sorted(key for key in current if key not in previous)
    changed = sorted(key for key in current if key in previous and previous[key] != current[key])
    removed = sorted(key for key in previous if key not in current) if status == OK and complete else []
    changes = {"baseline": False, "added": added, "removed": removed, "changed": changed}
    if status == PARTIAL:
        return "partially_checked", changes
    return ("checked_material_change" if added or removed or changed else "checked_no_relevant_change"), changes


def dependents(registry, engine_id: str) -> list:
    """The questions that read a source: the invalidation edges from that source to the briefs built on it."""
    return sorted(question.id for question in registry.active()
                  if any(binding.engine == engine_id for binding in question.sources))


def tick(registry, contracts, repository: Path, library: Path, network, *, now: "str | None" = None) -> dict:
    """One hourly check of every watched source. Writes only under <library>/state/model-watch and <library>/model-watch."""
    moment = now or now_utc()
    state = Path(library) / "state" / "model-watch"
    state.mkdir(parents=True, exist_ok=True)
    lock = os.open(state / "watch.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return {"record_type": TICK_RECORD_TYPE, "status": "already_running", "at": moment}
        question = registry.question(WATCHED_QUESTION)
        engines = default_registry(network_allowed=network is not None)
        results, invalidations = [], []
        for index, binding in enumerate(question.sources):
            key = f"{index:02d}:{binding.engine}"
            snapshot_path = state / f"{binding.engine}-{index:02d}.json"
            snapshot = _read(snapshot_path, {})
            freshness = dict(snapshot.get("freshness") or {})
            freshness["last_attempted_retrieval"] = moment
            previous = snapshot.get("fingerprints") if snapshot.get("record_type") == SNAPSHOT_RECORD_TYPE else None
            validators = snapshot.get("validators") if previous is not None and isinstance(snapshot.get("validators"), dict) else {}
            complete = True
            if network is None or binding.engine not in engines.engines:
                status, reason, observations = FAILED, "the watch holds no network authority", ()
            else:
                context = ReadContext(question, binding, moment, moment[:10], contracts[binding.engine],
                                      Path(repository), None, network)
                # Send back only the validators of this binding's last complete read.
                network.conditional = dict(validators)
                network.observed_validators = {}
                try:
                    answer = engines.engine(binding.engine).read(context)
                    status, reason, observations = answer.status, answer.reason, answer.observations
                    complete = answer.complete
                except RadarEngineError as error:
                    status, reason, observations = FAILED, str(error), ()
                except Exception as error:  # noqa: BLE001 - a failing engine is recorded, never trusted
                    status, reason, observations = FAILED, f"the engine failed: {type(error).__name__}", ()
                finally:
                    network.conditional = {}
            current = {item.key: fingerprint(item) for item in observations}
            titles = {item.key: item.title for item in observations}
            outcome, changes = outcome_of(status, previous, current, complete)
            if status in (OK, PARTIAL) or (status == NOT_MODIFIED and previous is not None):
                freshness["last_successful_retrieval"] = moment
                whole = status == OK and complete
                merged = previous if status == NOT_MODIFIED else (
                    dict(current) if whole or previous is None else {**previous, **current})
                if changes.get("added") or changes.get("changed") or changes.get("removed") or changes.get("baseline"):
                    freshness["last_material_change"] = moment
                # Validators are kept only from a complete read, so a later 304 always means "same as a whole list".
                kept = dict(network.observed_validators) if network is not None and (whole or status == NOT_MODIFIED) else {}
                _write(snapshot_path, {"record_type": SNAPSHOT_RECORD_TYPE, "engine_id": binding.engine,
                                       "section": binding.section, "fingerprints": merged,
                                       "titles": {**(snapshot.get("titles") or {}), **titles}, "freshness": freshness,
                                       "validators": {**(validators if status == NOT_MODIFIED else {}), **kept}})
            else:
                # The snapshot and its success time stay as they were; only the attempt is recorded.
                _write(snapshot_path, {**snapshot, "freshness": freshness} if snapshot else
                       {"record_type": "knowledge_radar_model_snapshot_attempt/v1", "engine_id": binding.engine,
                        "freshness": freshness})
            material = (not changes.get("baseline")) and any(changes.get(name) for name in ("added", "removed", "changed"))
            result = {"source": key, "engine_id": binding.engine, "status": status, "outcome": outcome, "reason": reason,
                      "observations": len(observations), "freshness": freshness,
                      "validated_by_source": bool(changes.get("validated")),
                      "added": [titles.get(item, item) for item in changes.get("added", [])][:50],
                      "removed": [(snapshot.get("titles") or {}).get(item, item) for item in changes.get("removed", [])][:50],
                      "changed": [titles.get(item, item) for item in changes.get("changed", [])][:50],
                      "baseline": bool(changes.get("baseline"))}
            results.append(result)
            if material:
                for question_id in dependents(registry, binding.engine):
                    invalidations.append({"record_type": INVALIDATION_RECORD_TYPE, "question_id": question_id,
                                          "at": moment, "source": key,
                                          "reason": f"model watch: {len(changes['added'])} new, {len(changes['removed'])} "
                                                    f"removed, {len(changes['changed'])} changed on {binding.engine}"})
        if invalidations:
            path = state / "invalidations.json"
            known = _read(path, {"record_type": "knowledge_radar_invalidations/v1", "invalidations": []})
            known["invalidations"] = (known.get("invalidations", []) + invalidations)[-MAXIMUM_INVALIDATIONS:]
            _write(path, known)
        record = {"record_type": TICK_RECORD_TYPE, "status": "complete", "at": moment, "sources": results,
                  "invalidated": sorted({row["question_id"] for row in invalidations}), "model_calls": 0}
        log = Path(library) / "model-watch" / moment[:10] / "ticks.jsonl"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
        if record["invalidated"]:
            _write(Path(library) / "model-watch" / moment[:10] / f"change-{moment.replace(':', '')}.json",
                   {"record_type": CHANGE_RECORD_TYPE, **record})
        return record
    finally:
        os.close(lock)


def latest_invalidations(library: Path) -> dict:
    """The latest invalidation time per question, for the daily planner."""
    known = _read(Path(library) / "state" / "model-watch" / "invalidations.json", {})
    latest = {}
    for row in known.get("invalidations", []) if isinstance(known, dict) else []:
        if isinstance(row, dict) and isinstance(row.get("question_id"), str) and isinstance(row.get("at"), str):
            latest[row["question_id"]] = max(latest.get(row["question_id"], ""), row["at"])
    return latest
