"""A file store for one ontology graph: compare-and-swap apply, enforced locks, approval and checked rollback.

```text
OntologyStore (one folder)
├── graphs/<sha256>.nt   each state ever held, as canonical N-Triples, immutable and named by its digest
├── state.json           ontology_store_state/v1: the current digest, the locked terms, a sequence number;
│                        replacing this one file is the only way a state changes
├── journal.jsonl        one line per lock, apply and rollback, appended and never rewritten
└── .lock                an exclusive lock held for every read-modify-write
apply_change(store, ontology_change_apply_request/v1)
├── the plan read strictly, its digest recomputed (plan_invalid)
├── an approval that names this plan's digest (approval_required, approval_mismatch)
├── under the lock: the current digest equals the plan's base digest (stale_base)
├── every term the store locks was checked by the plan, and none of them is touched (locked_term)
├── base minus removed plus added has the plan's proposed digest (plan_invalid)
└── the new graph written first, then the pointer; the result carries ontology_change_rollback/v1
rollback_change(store, ontology_change_rollback_request/v1)
└── the same guards in reverse: the current digest is the one the rollback replaces (stale_rollback),
    no locked term is asserted or retracted, and the restored graph has the recorded digest
```

Planning never writes here: ``plan_store_change`` reads the current graph and
locks and asks the envelope for a plan, which a person or a policy approves.
"""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from .contract import (
    APPLY_REQUEST_RECORD_TYPE, APPLY_RESULT_RECORD_TYPE, ROLLBACK_RECORD_TYPE, ROLLBACK_REQUEST_RECORD_TYPE,
    ROLLBACK_RESULT_RECORD_TYPE, OntologyChangeRefused, is_sha256, read_approval, read_locked_term, read_plan,
    read_triple, request_record, triples_list)
from .rdf_terms import canonical_ntriples, graph_digest, parse_ntriples

STATE_RECORD_TYPE = "ontology_store_state/v1"
JOURNAL_RECORD_TYPE = "ontology_store_journal_entry/v1"


def _write_atomically(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".tmp")
    with open(temporary, "w", encoding="utf-8") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _instant() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class OntologyStore:
    """One ontology graph kept as content-addressed states behind one atomic pointer."""

    def __init__(self, folder):
        self.folder = Path(folder)
        if not (self.folder / "state.json").is_file():
            raise OntologyChangeRefused("store_corrupt", f"no ontology store at {self.folder}", "apply")

    @classmethod
    def create(cls, folder, triples, locked_terms=()) -> "OntologyStore":
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        if any(folder.iterdir()):
            raise OntologyChangeRefused("store_corrupt", "a new store needs an empty folder", "apply")
        (folder / "graphs").mkdir()
        digest = cls._write_graph(folder, triples)
        locks = sorted({read_locked_term(term) for term in locked_terms})
        _write_atomically(folder / "state.json", json.dumps(
            {"record_type": STATE_RECORD_TYPE, "digest": digest, "locked_terms": locks, "sequence": 0}) + "\n")
        (folder / "journal.jsonl").touch()
        return cls(folder)

    @staticmethod
    def _write_graph(folder: Path, triples) -> str:
        digest = graph_digest(triples)
        path = folder / "graphs" / f"{digest}.nt"
        if not path.exists():
            _write_atomically(path, canonical_ntriples(triples))
        return digest

    @contextmanager
    def exclusive(self):
        with open(self.folder / ".lock", "a+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def state(self) -> dict:
        try:
            state = json.loads((self.folder / "state.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise OntologyChangeRefused("store_corrupt", "state.json is unreadable", "apply") from None
        if (not isinstance(state, dict) or state.get("record_type") != STATE_RECORD_TYPE
                or set(state) != {"record_type", "digest", "locked_terms", "sequence"}
                or not is_sha256(state["digest"])):
            raise OntologyChangeRefused("store_corrupt", "state.json is not ontology_store_state/v1", "apply")
        return state

    def digest(self) -> str:
        return self.state()["digest"]

    def triples(self, digest: "str | None" = None) -> frozenset:
        """The graph of the current state (or a named past one), its digest checked on every read."""
        digest = digest or self.digest()
        path = self.folder / "graphs" / f"{digest}.nt"
        try:
            triples = parse_ntriples(path.read_text(encoding="utf-8"))
        except OSError:
            raise OntologyChangeRefused("store_corrupt", f"no graph file for {digest}", "apply") from None
        if graph_digest(triples) != digest:
            raise OntologyChangeRefused("store_corrupt", f"the graph file for {digest} was changed", "apply")
        return triples

    def journal(self) -> list:
        lines = (self.folder / "journal.jsonl").read_text(encoding="utf-8").splitlines()
        return [json.loads(line) for line in lines if line]

    def _commit(self, state: dict, digest: str, entry: dict, locked_terms=None) -> None:
        sequence = state["sequence"] + 1
        locks = state["locked_terms"] if locked_terms is None else locked_terms
        with open(self.folder / "journal.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"record_type": JOURNAL_RECORD_TYPE, "sequence": sequence, "at": _instant(),
                                     **entry}, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _write_atomically(self.folder / "state.json", json.dumps(
            {"record_type": STATE_RECORD_TYPE, "digest": digest, "locked_terms": locks, "sequence": sequence}) + "\n")

    def lock(self, terms, reason: str) -> list:
        """Lock IRIs: no later change may assert, retract or change an entailment about them."""
        if type(reason) is not str or not reason.strip() or len(reason) > 400:
            raise OntologyChangeRefused("request_invalid", "a lock names its reason", "apply")
        with self.exclusive():
            state = self.state()
            locks = sorted(set(state["locked_terms"]) | {read_locked_term(term) for term in terms})
            self._commit(state, state["digest"], {"operation": "lock", "terms": locks, "reason": reason}, locks)
        return locks


def _keys(value, fields, name, code, stage):
    if not isinstance(value, dict) or set(value) != set(fields):
        raise OntologyChangeRefused(code, f"{name} has exactly the fields {list(fields)}", stage)
    return value


def plan_store_change(store: OntologyStore, *, added=(), removed=(), profile: str = "owl-rl", host=None,
                      include_traces: bool = True, max_listed: int = 200):
    """Plan a change to the store's current graph, checking every term the store locks."""
    from .component import plan_change
    state = store.state()
    request = request_record(canonical_ntriples(store.triples()), state["digest"], added=added, removed=removed,
                             profile=profile, ontology_format="ntriples", include_traces=include_traces,
                             max_listed=max_listed, locked_terms=state["locked_terms"])
    return plan_change(request, host)


def _locked_problem(locks, triples) -> str:
    for term in locks:
        for triple in triples:
            if term in triple:
                return f"the change asserts or retracts a triple naming the locked term {term}"
    return ""


def apply_change(store: OntologyStore, request) -> dict:
    """Apply an approved plan by compare-and-swap; the result records what a rollback replaces."""
    record = _keys(request, ("record_type", "plan", "approval"), "apply request", "plan_invalid", "apply")
    if record["record_type"] != APPLY_REQUEST_RECORD_TYPE:
        raise OntologyChangeRefused("plan_invalid", "unsupported apply request version", "apply")
    plan = read_plan(record["plan"])
    approval = read_approval(record["approval"], plan)
    added = {read_triple(item) for item in plan["change"]["added"]}
    removed = {read_triple(item) for item in plan["change"]["removed"]}
    with store.exclusive():
        state = store.state()
        if state["digest"] != plan["base_digest"]:
            raise OntologyChangeRefused("stale_base", f"the store holds {state['digest']}, the plan was made for "
                                                      f"{plan['base_digest']}; plan again", "apply")
        unchecked = sorted(set(state["locked_terms"]) - set(plan["locks"]["checked"]))
        if unchecked:
            raise OntologyChangeRefused("locked_term", f"the plan did not check the locked term {unchecked[0]}",
                                        "apply")
        touched = [item for item in plan["locks"]["touched"] if item["term"] in state["locked_terms"]]
        if touched:
            raise OntologyChangeRefused("locked_term", f"the change touches the locked term {touched[0]['term']} "
                                                       f"({', '.join(touched[0]['how'])})", "apply")
        problem = _locked_problem(state["locked_terms"], added | removed)
        if problem:
            raise OntologyChangeRefused("locked_term", problem, "apply")
        current = store.triples(state["digest"])
        proposed = (current - removed) | added
        if not removed <= current or added & current or graph_digest(proposed) != plan["proposed_digest"]:
            raise OntologyChangeRefused("plan_invalid", "the change does not lead to the plan's proposed digest",
                                        "apply")
        OntologyStore._write_graph(store.folder, proposed)
        rollback = {"record_type": ROLLBACK_RECORD_TYPE, "plan_digest": plan["plan_digest"],
                    "replaces_digest": plan["proposed_digest"], "restores_digest": plan["base_digest"],
                    "remove": triples_list(added), "restore": triples_list(removed)}
        store._commit(state, plan["proposed_digest"], {
            "operation": "apply", "plan_digest": plan["plan_digest"], "approval_ref": approval,
            "before": plan["base_digest"], "after": plan["proposed_digest"], "rollback": rollback})
    return {"record_type": APPLY_RESULT_RECORD_TYPE, "applied": True, "plan_digest": plan["plan_digest"],
            "previous_digest": plan["base_digest"], "new_digest": plan["proposed_digest"], "approval_ref": approval,
            "rollback": rollback}


def _read_rollback(value) -> dict:
    record = _keys(value, ("record_type", "plan_digest", "replaces_digest", "restores_digest", "remove",
                           "restore"), "rollback", "rollback_invalid", "rollback")
    if record["record_type"] != ROLLBACK_RECORD_TYPE or not all(
            is_sha256(record[name]) for name in ("plan_digest", "replaces_digest", "restores_digest")):
        raise OntologyChangeRefused("rollback_invalid", "not an ontology_change_rollback/v1 record", "rollback")
    for name in ("remove", "restore"):
        if not isinstance(record[name], list):
            raise OntologyChangeRefused("rollback_invalid", f"{name} is a list of triples", "rollback")
    return record


def rollback_change(store: OntologyStore, request) -> dict:
    """Restore the state an apply replaced, only while the store still holds what that apply wrote."""
    record = _keys(request, ("record_type", "rollback", "approval"), "rollback request", "rollback_invalid",
                   "rollback")
    if record["record_type"] != ROLLBACK_REQUEST_RECORD_TYPE:
        raise OntologyChangeRefused("rollback_invalid", "unsupported rollback request version", "rollback")
    rollback = _read_rollback(record["rollback"])
    approval = read_approval(record["approval"], {"plan_digest": rollback["plan_digest"]}, stage="rollback")
    remove = {read_triple(item) for item in rollback["remove"]}
    restore = {read_triple(item) for item in rollback["restore"]}
    with store.exclusive():
        state = store.state()
        if state["digest"] != rollback["replaces_digest"]:
            raise OntologyChangeRefused("stale_rollback", f"the store holds {state['digest']}, not the state "
                                                          f"{rollback['replaces_digest']} this rollback replaces",
                                        "rollback")
        problem = _locked_problem(state["locked_terms"], remove | restore)
        if problem:
            raise OntologyChangeRefused("locked_term", problem, "rollback")
        current = store.triples(state["digest"])
        restored = (current - remove) | restore
        if not remove <= current or restore & current or graph_digest(restored) != rollback["restores_digest"]:
            raise OntologyChangeRefused("rollback_mismatch", "the rollback does not restore its recorded digest",
                                        "rollback")
        OntologyStore._write_graph(store.folder, restored)
        store._commit(state, rollback["restores_digest"], {
            "operation": "rollback", "plan_digest": rollback["plan_digest"], "approval_ref": approval,
            "before": rollback["replaces_digest"], "after": rollback["restores_digest"]})
    return {"record_type": ROLLBACK_RESULT_RECORD_TYPE, "rolled_back": True, "plan_digest": rollback["plan_digest"],
            "previous_digest": rollback["replaces_digest"], "new_digest": rollback["restores_digest"],
            "approval_ref": approval}
