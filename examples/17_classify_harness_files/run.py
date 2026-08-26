"""Classify real repository sources into the four intelligence layers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from loop_engine.core.harness_intelligence_bridge import (
    HarnessMemoryItem,
    import_harness_memory_as_loop,
)


REPOSITORY_DIRECTORY = Path(__file__).resolve().parents[2]


def _digest(path: Path) -> str:
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256()
    for item_file in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(item_file.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(item_file.read_bytes()).digest())
    return digest.hexdigest()


def _preview(path: Path) -> str:
    if not path.is_file():
        return f"Repository tree under {path.relative_to(REPOSITORY_DIRECTORY)}"
    text = path.read_text(encoding="utf-8", errors="replace")
    return " ".join(text.split())[:240]


def main() -> None:
    writing_context = REPOSITORY_DIRECTORY / "humanizer-context.md"
    package = REPOSITORY_DIRECTORY / "src" / "loop_engine"
    saved_run = (
        REPOSITORY_DIRECTORY / "docs" / "evidence" / "runs"
        / "titanic-warm-20260823" / "manifest.json"
    )
    sources = (
        ("writing-context", "markdown", "Loop Engine writing context",
         writing_context),
        ("loop-engine-package", "repository", "Loop Engine package", package),
        ("saved-run", "run_trace", "Saved Loop Engine run", saved_run),
        ("owner-writing-rules", "user_instruction",
         "Owner writing rules", writing_context),
    )
    items = tuple(HarnessMemoryItem(
        item_id=item_id,
        kind=kind,
        title=title,
        source_harness="loop_engine_repository",
        raw_ref=f"repo:{path.relative_to(REPOSITORY_DIRECTORY).as_posix()}",
        content_preview=_preview(path),
        metadata={"sha256": _digest(path)},
        tags=("real_repository_source",),
    ) for item_id, kind, title, path in sources)

    imported = import_harness_memory_as_loop(items)
    print(json.dumps({
        "record_type": "harness_file_classification/v1",
        "loop_id": imported.loop_id,
        "candidate_count": len(imported.candidates),
        "by_layer": dict(imported.by_layer),
        "candidates": [{
            "title": candidate.item.title,
            "source": candidate.item.raw_ref,
            "layer": candidate.public_layer,
            "lifecycle": candidate.lifecycle,
            "digest": candidate.digest,
        } for candidate in imported.candidates],
    }, indent=2))


if __name__ == "__main__":
    main()
