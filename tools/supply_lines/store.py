"""Write supplied candidates into the import store, through the importer's own write path.

The import store (tools/licensed_import/storage.py) keeps bodies by digest in
its body store and records in its catalogue store, in atomic batches with
exact preconditions. The supply lines use the same `ImportStore`: bodies go
through `put_bodies`, records through `apply`, candidate records are built by
`candidate_store_record` in the namespace `library.supply`, and every fetched
fact byte is kept in the store's quarantine. One state record per line lists
the current version of every supplied component, so a changed package is a new
version and the old one is superseded, and a component a complete run no longer
supplies is withdrawn. History is never deleted.
"""
from __future__ import annotations

from pathlib import Path

from loop_engine.core.library_ingestion.record_rules import now_utc

from licensed_import.storage import (
    SUPERSEDED_LIFECYCLE, SUPPLY_NAMESPACE, ImportStore, candidate_store_record, record_version, relabelled)
from licensed_import.records import WITHDRAWN_LIFECYCLE

from .records import STATE_RECORD_TYPE, read_supply_candidate, state_record_id


def _state_store_record(payload: dict, record_id: str) -> dict:
    return {"record_id": record_id, "record_version": record_version(payload), "intelligence_layer": "",
            "source_collection": "learned", "artifact_kind": "supply_line_state", "lifecycle": "source_state",
            "namespace": SUPPLY_NAMESPACE, "attributes": {"line": payload["line"], "components": len(payload["packages"])},
            "payload": payload}


class SupplyStore:
    """The import store, written in the supply namespace only when writes are authorized."""

    def __init__(self, root, *, writes_authorized: bool) -> None:
        if writes_authorized is not True:
            raise PermissionError("writing supplied candidates needs --authorize-store-writes")
        self.store = ImportStore(Path(root), writes_authorized=True)

    def close(self) -> None:
        self.store.close()

    def keep_facts(self, facts: dict) -> int:
        """Every fetched fact byte in the store's quarantine, by digest; the count kept."""
        for data in facts.values():
            self.store.quarantine.put(data)
        return len(facts)

    def write(self, line: str, built, *, complete: bool, scope: str = "") -> dict:
        """Store each (payload, bodies) of one line; supersede changed versions, withdraw what a complete run lost.

        The state (and so what a complete run may withdraw) is the line's own, or its scope's when a line has
        several modes."""
        state_id = state_record_id(line, scope)
        current_state = self.store.get(state_id)
        previous = dict((current_state or {}).get("payload", {}).get("packages", {}))
        packages, records, expected, bodies = {}, [], {}, {}
        unchanged = written = superseded = withdrawn = 0
        for payload, payload_bodies in built:
            read_supply_candidate(payload)
            key = payload["upstream_key"]
            packages[key] = payload["record_id"]
            if self.store.get(payload["record_id"]) is not None:
                unchanged += 1
                continue
            earlier = previous.get(key)
            if earlier and earlier != payload["record_id"]:
                old = self.store.get(earlier)
                if old is not None and old["lifecycle"] == "candidate":
                    payload = {**payload, "version": {"previous_record_id": earlier}}
                    updated = relabelled(old, SUPERSEDED_LIFECYCLE)
                    expected[earlier] = old["record_version"]
                    records.append(updated)
                    superseded += 1
            records.append(candidate_store_record(payload, namespace=SUPPLY_NAMESPACE))
            bodies.update(payload_bodies)
            written += 1
        if complete:
            for key, old_id in sorted(previous.items()):
                if key in packages:
                    continue
                old = self.store.get(old_id)
                if old is not None and old["lifecycle"] == "candidate":
                    expected[old_id] = old["record_version"]
                    records.append(relabelled(old, WITHDRAWN_LIFECYCLE))
                    withdrawn += 1
        else:
            packages = {**previous, **packages}
        packages = dict(sorted(packages.items()))
        if current_state is None or current_state["payload"].get("packages") != packages:
            # The state is rewritten only when the components it lists changed: an unchanged run writes nothing.
            state = {"record_type": STATE_RECORD_TYPE, "line": line, "written_at": now_utc(), "complete": complete,
                     "packages": packages, **({"scope": scope} if scope else {})}
            if current_state is not None:
                expected[state_id] = current_state["record_version"]
            records.append(_state_store_record(state, state_id))
        body_result = self.store.put_bodies(bodies) if bodies else {"written": 0, "already_present": 0}
        if records:
            self.store.apply(records, expected=expected)
        return {"line": line, **({"scope": scope} if scope else {}), "written": written, "unchanged": unchanged,
                "superseded": superseded,
                "withdrawn": withdrawn, "bodies": body_result, "components": len(packages)}
