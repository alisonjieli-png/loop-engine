"""Merge prepared proposals from several generation runs into one factory input.

Each argument after the output is RUN_FOLDER or RUN_FOLDER:METHOD_TO_SKIP[,METHOD...].
Every prepared completion's saved proposals.json is checked against the digest
its journal recorded. The runs must share the proposal contract, source
revision and licence; a source pinned at two digests is refused. The existing
factory then builds one batch; package digests are content-addressed.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def main(output: Path, specs: list[str]) -> int:
    if output.exists():
        raise SystemExit("output exists; use a new name")
    merged, sources, proposals, taken = None, {}, [], []
    for spec in specs:
        folder, _separator, skipped = spec.partition(":")
        skip = set(filter(None, skipped.split(",")))
        run = Path(folder)
        for line in (run / "journal.jsonl").read_text(encoding="utf-8").splitlines():
            row = json.loads(line)
            data = row["data"]
            if row["kind"] != "complete" or data["status"] != "candidate_prepared" or row["method_id"] in skip:
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
            proposals.extend(value["proposals"])
            taken.append({"run": run.name, "method_id": row["method_id"], "attempt": row["attempt"],
                          "package_digest": data["package_digest"]})
    if merged is None:
        raise SystemExit("no prepared candidate was selected")
    identities = [item["id"] for item in proposals]
    if len(identities) != len(set(identities)):
        raise SystemExit("one method was selected twice")
    merged.update(sources=sources, proposals=proposals)
    output.write_text(json.dumps(merged, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print(json.dumps({"output": str(output), "proposals": len(proposals), "taken": taken}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1]), sys.argv[2:]))
