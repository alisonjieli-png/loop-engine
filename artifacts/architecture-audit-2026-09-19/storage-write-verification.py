"""Owning checks and in-process mutants for the assigned storage repairs.

Only test fixtures use temporary directories. Mutants replace Python callables
in memory and are restored after each check. No repository source is rewritten.
"""
from __future__ import annotations

import contextlib
import hashlib
import importlib
import inspect
import json
import textwrap
from pathlib import Path
from unittest.mock import patch


MODULES = (
    "loop_engine.catalog.stores.in_memory",
    "loop_engine.catalog.stores.sqlite_store",
    "loop_engine.catalog.stores.duckdb_store",
    "loop_engine.catalog.versioning",
    "loop_engine.core.shared_memory_scopes",
    "loop_engine.catalog.capabilities",
)


def result_for(module):
    try:
        checks = module.self_test()["tests"]
        failed = [item.get("name", item.get("test", "unnamed"))
                  for item in checks if item.get("passed") is not True]
        return {"module": module.__name__, "checks": len(checks), "failed": failed}
    except Exception as exc:
        return {"module": module.__name__, "checks": None,
                "failed": [type(exc).__name__ + ": " + str(exc)]}


def replaced_function(original, old, new):
    source = textwrap.dedent(inspect.getsource(original))
    if source.count(old) != 1:
        raise RuntimeError("mutant target is not unique: " + old)
    namespace = {}
    exec(compile(source.replace(old, new), "<storage-contract-mutant>", "exec"),
         original.__globals__, namespace)
    return namespace[original.__name__]


def main():
    modules = {name: importlib.import_module(name) for name in MODULES}
    baseline = [result_for(module) for module in modules.values()]
    if any(row["failed"] for row in baseline):
        print(json.dumps({"baseline": baseline, "mutants": [], "passed": False}, indent=2))
        return 1
    memory = modules[MODULES[0]]
    sqlite = modules[MODULES[1]]
    duckdb = modules[MODULES[2]]
    versioning = modules[MODULES[3]]
    shared = modules[MODULES[4]]
    mutants = []

    def exercise(name, module, owner, attribute, replacement):
        with patch.object(owner, attribute, replacement):
            result = result_for(module)
        mutants.append({"name": name, "detected": bool(result["failed"]),
                        "failing_checks": result["failed"]})

    exercise("remove_in_memory_write_serialization", memory, memory, "RLock",
             contextlib.nullcontext)
    exercise("remove_in_memory_absence_precondition", memory,
             memory.EphemeralRecordStore, "put", replaced_function(
                 memory.EphemeralRecordStore.put,
                 '"exists" in precondition and current is not None', "False"))
    for module, owner, expression in (
        (memory, memory.EphemeralRecordStore, 'and (not isinstance(prepared.get("record_version"), str)'),
        (sqlite, sqlite.SQLiteRecordStore, 'and (not isinstance(values[1], str)'),
        (duckdb, duckdb.DuckDBRecordStore, 'and (not isinstance(values[1], str)'),
    ):
        exercise("allow_same_version_guarded_update:" + module.__name__, module,
                 owner, "put", replaced_function(owner.put, expression,
                                                   expression.replace("and (", "and False and (", 1)))
    exercise("remove_duckdb_failed_transaction_rollback", duckdb,
             duckdb.DuckDBRecordStore, "_rollback", lambda self: None)
    exercise("remove_revision_digest_validation", versioning, versioning,
             "_restored_revision", replaced_function(
                 versioning._restored_revision,
                 'or content_digest(restored) != attributes.get("revision_digest")', "or False"))
    exercise("remove_revision_absence_guard", versioning, versioning, "revise",
             replaced_function(versioning.revise,
                               '_confirmed_put(store, record, {"exists": False})',
                               '_confirmed_put(store, record, None)'))
    original_confirmed = versioning._confirmed_put

    def accept_missing_acknowledgment(store, record, precondition):
        acknowledgment = store.put(record, precondition=precondition)
        if store.get(record["record_id"]) != record:
            raise versioning.VersioningError("readback mismatch")
        return acknowledgment

    exercise("ignore_revision_write_acknowledgment", versioning, versioning,
             "_confirmed_put", accept_missing_acknowledgment)
    exercise("ignore_revision_readback", versioning, versioning,
             "_confirmed_put", replaced_function(
                 original_confirmed, 'actual = store.get(record["record_id"])',
                 'return\n    actual = store.get(record["record_id"])'))
    exercise("remove_shared_absence_guard", shared, shared.SharedMemory, "write",
             replaced_function(shared.SharedMemory.write,
                               '({"exists": False} if expected_version is None',
                               '(None if expected_version is None'))
    exercise("permit_shared_numeric_version_rollback", shared, shared.SharedMemory, "write",
             replaced_function(shared.SharedMemory.write,
                               'if (re.fullmatch(r"\\d+(?:\\.\\d+)*", version)',
                               'if (False and re.fullmatch(r"\\d+(?:\\.\\d+)*", version)'))
    exercise("ignore_shared_readback", shared, shared.SharedMemory, "write",
             replaced_function(shared.SharedMemory.write,
                               'if not isinstance(actual, dict) or any(actual.get(key) != value for key, value in stamped.items()):',
                               'if False:'))
    capabilities = modules[MODULES[5]]
    exercise("allow_truthy_operation_capabilities", capabilities,
             capabilities.StoreCapabilities, "supports", replaced_function(
                 capabilities.StoreCapabilities.supports,
                 'return self.operations.get(operation) is True',
                 'return bool(self.operations.get(operation))'))
    source_hashes = {
        str(Path(module.__file__).relative_to(Path.cwd())):
        hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for module in modules.values()}
    passed = all(row["detected"] for row in mutants)
    print(json.dumps({"record_type": "storage_write_verification/v1",
                      "baseline": baseline, "mutants": mutants,
                      "source_sha256": source_hashes,
                      "passed": passed}, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
