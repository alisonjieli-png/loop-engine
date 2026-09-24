"""Merge the prepared proposals of one generation run into one factory input.

The generator prepares each method in its own folder; the review panel reads
one prepared batch. This reads the run's journal, takes the saved
``proposals.json`` of every completion with status ``candidate_prepared``,
checks each file against the digest the journal recorded, and writes one
``harness_candidate_batch_proposals/v2`` input with the union of their pinned
sources. The existing preparation factory then builds the batch from it;
package digests are content-addressed and do not change.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main(run: Path, output: Path) -> int:
    if output.exists():
        raise SystemExit("output exists; use a new name")
    merged, sources = None, {}
    prepared = []
    for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        data = row["data"]
        if row["kind"] != "complete" or data["status"] != "candidate_prepared":
            continue
        raw = (run / data["proposal_path"]).read_bytes()
        if hashlib.sha256(raw).hexdigest() != data["proposal_sha256"]:
            raise SystemExit("a saved proposal differs from its journal digest: " + row["method_id"])
        value = json.loads(raw)
        if merged is None:
            merged = {key: value[key] for key in ("record_type", "source_revision", "license")}
        elif any(merged[key] != value[key] for key in ("record_type", "source_revision", "license")):
            raise SystemExit("proposals disagree on contract, revision or licence")
        for name, pinned in value["sources"].items():
            if sources.setdefault(name, pinned) != pinned:
                raise SystemExit("proposals pin one source at two digests: " + name)
        prepared.extend(value["proposals"])
    if merged is None:
        raise SystemExit("the run prepared no candidate")
    merged.update(sources=sources, proposals=prepared)
    output.write_text(json.dumps(merged, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"output": str(output), "proposals": len(prepared),
                      "identities": [item["id"] for item in prepared]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), Path(sys.argv[2])))
