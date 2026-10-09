"""Shard manifest audit: compare the shards a dataset's index declares with the shards actually present.

The declared list is what a release manifest or shard index promises (path, SHA-256 and row count); the observed
list is what was found on disk, computed by whatever read the files. A declared path not observed is missing, an
observed path not declared is unexpected, a path present in both with another SHA-256 is a digest mismatch, and one
whose row counts both sides state and disagree is a row count mismatch. A path that passes both comparisons is
matched; the dataset is complete when nothing is missing, unexpected or mismatched. A pure function of its JSON
input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

from kit_schema import KitRefusal, check, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_path": "one list names a path twice",
}
_SHARD = {"type": "object", "required": ["path", "sha256"], "additionalProperties": False,
          "properties": {"path": {"type": "string", "minLength": 1},
                         "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                         "rows": {"type": ["integer", "null"], "minimum": 0}}}
_MISMATCH = {"type": "object", "required": ["path", "declared", "observed"]}
INPUT_SCHEMA = {
    "type": "object", "required": ["declared", "observed"], "additionalProperties": False,
    "properties": {
        "declared": {"type": "array", "maxItems": 100000, "items": _SHARD,
                     "description": "the shards the index or manifest declares"},
        "observed": {"type": "array", "maxItems": 100000, "items": _SHARD,
                     "description": "the shards found, with the SHA-256 and rows computed from their bytes"},
    },
}
OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["complete", "matched", "missing", "unexpected", "digest_mismatch", "row_count_mismatch"],
    "properties": {
        "complete": {"type": "boolean"},
        "matched": {"type": "integer", "minimum": 0},
        "missing": {"type": "array", "items": {"type": "string"}, "description": "declared paths not observed"},
        "unexpected": {"type": "array", "items": {"type": "string"}, "description": "observed paths not declared"},
        "digest_mismatch": {"type": "array", "items": _MISMATCH, "description": "declared and observed SHA-256"},
        "row_count_mismatch": {"type": "array", "items": _MISMATCH, "description": "declared and observed rows"},
    },
}


def _by_path(shards: list, side: str) -> dict:
    found = {}
    for shard in shards:
        if shard["path"] in found:
            raise KitRefusal("duplicate_path", f"{side}: {shard['path']}")
        found[shard["path"]] = shard
    return found


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    declared = _by_path(payload["declared"], "declared")
    observed = _by_path(payload["observed"], "observed")
    digest_mismatch, row_mismatch, matched = [], [], 0
    for path in sorted(set(declared) & set(observed)):
        want, have = declared[path], observed[path]
        same_digest = want["sha256"] == have["sha256"]
        rows_stated = want.get("rows") is not None and have.get("rows") is not None
        same_rows = not rows_stated or want["rows"] == have["rows"]
        if not same_digest:
            digest_mismatch.append({"path": path, "declared": want["sha256"], "observed": have["sha256"]})
        if not same_rows:
            row_mismatch.append({"path": path, "declared": want["rows"], "observed": have["rows"]})
        matched += same_digest and same_rows
    missing = sorted(set(declared) - set(observed))
    unexpected = sorted(set(observed) - set(declared))
    return {"complete": not (missing or unexpected or digest_mismatch or row_mismatch), "matched": matched,
            "missing": missing, "unexpected": unexpected, "digest_mismatch": digest_mismatch,
            "row_count_mismatch": row_mismatch}


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
