"""Check candidate-only native instruction layouts without starting a model."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SLUGS = ("repair-one-failing-test", "profile-one-csv")
CLIENTS = ("codex", "claude", "opencode", "pi")
PLACEHOLDER = re.compile(r"\{\{([A-Z][A-Z0-9_]*)\}\}")


def check() -> list[str]:
    errors: list[str] = []
    identities: set[str] = set()
    for slug in SLUGS:
        folder = ROOT / slug
        note = json.loads((folder / "review-note.json").read_text())
        identity = note["candidate_id"]
        if identity in identities:
            errors.append(f"{slug}: duplicate candidate identity")
        identities.add(identity)
        if note["state"] != "candidate_only" or note["independent_review"] != "pending":
            errors.append(f"{slug}: unexpected approval state")
        if note["logical_item_count"] != 1:
            errors.append(f"{slug}: client renderings counted as separate items")
        for field in ("model_loaded", "model_used", "verified_customer_outcome"):
            if note[field] is not None:
                errors.append(f"{slug}: unsupported {field} claim")

        required = set(note["render_contract"]["required_placeholders"])
        canonical = (folder / "codex/work/AGENTS.md").read_bytes()
        found = set(PLACEHOLDER.findall(canonical.decode("utf-8")))
        if found != required:
            errors.append(f"{slug}: render placeholders {sorted(found)} != {sorted(required)}")

        expected_files = set()
        for client in CLIENTS:
            path = folder / client / "work/AGENTS.md"
            expected_files.add(path.relative_to(folder).as_posix())
            if not path.is_file() or path.is_symlink():
                errors.append(f"{slug}: missing or linked {client} brief")
            elif path.read_bytes() != canonical:
                errors.append(f"{slug}: {client} brief differs from canonical")
        claude = folder / "claude/work/CLAUDE.md"
        expected_files.add(claude.relative_to(folder).as_posix())
        if claude.read_text().count("@AGENTS.md") != 1:
            errors.append(f"{slug}: Claude local AGENTS import missing or repeated")
        if re.findall(r"@[A-Za-z0-9_./-]+", claude.read_text()) != ["@AGENTS.md"]:
            errors.append(f"{slug}: Claude has an extra or escaping import")
        if not (claude.parent / "AGENTS.md").is_file():
            errors.append(f"{slug}: Claude import target missing")

        listed = note["files_sha256"]
        if set(listed) != expected_files:
            errors.append(f"{slug}: exact-byte file inventory differs")
        for relative in expected_files:
            path = folder / relative
            if path.is_symlink() or not path.is_file():
                errors.append(f"{slug}: missing or linked native file {relative}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if listed.get(relative) != digest:
                errors.append(f"{slug}: digest changed for {relative}")
        for path in folder.rglob("*"):
            if path.is_symlink():
                errors.append(f"{slug}: symlink {path.relative_to(folder)}")
            if path.is_file() and path.name in {"CODEX.md", "opencode.json", ".mcp.json"}:
                errors.append(f"{slug}: unqualified extra native file {path.name}")
            if path.is_file() and path.relative_to(folder).as_posix() not in expected_files | {"review-note.json"}:
                errors.append(f"{slug}: unexpected package file {path.relative_to(folder)}")
    return errors


if __name__ == "__main__":
    issues = check()
    if issues:
        raise SystemExit("\n".join(issues))
    print("2 candidate task briefs, 10 native files, 2 local Claude imports and exact digests checked")
