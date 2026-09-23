"""Inventory exact bytes of this isolated candidate batch; never approve them.

Run `python3 make_manifest.py --write --base-revision REVISION` after editing
the package and review-note files. Run `python3 make_manifest.py --check` to
detect a changed, missing, extra, or symlinked file. The native format and
the method itself require separate validation and independent review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGES = ROOT / "packages"
NOTES = ROOT / "review-notes"
MANIFEST = ROOT / "manifest.json"
GROUPS = ("data", "project", "software")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
RECORD_TYPE = "first_party_harness_candidate_batch_manifest/v1"


def _files(path: Path) -> list[Path]:
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"directory missing or symlinked: {path}")
    children = sorted(path.iterdir())
    if any(child.is_symlink() for child in children):
        raise ValueError(f"symlink in {path}")
    return children


def _digest(path: Path) -> tuple[str, int]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"file missing or symlinked: {path}")
    data = path.read_bytes()
    if not data or len(data) > 100_000:
        raise ValueError(f"empty or overlarge file: {path}")
    return hashlib.sha256(data).hexdigest(), len(data)


def inventory() -> list[dict]:
    if [path.name for path in _files(PACKAGES)] != list(GROUPS):
        raise ValueError("package groups differ from the declared batch layout")
    _files(NOTES)
    entries = []
    slugs = set()
    for group in GROUPS:
        for folder in _files(PACKAGES / group):
            if not folder.is_dir() or not SLUG.fullmatch(folder.name):
                raise ValueError(f"invalid package directory: {folder}")
            slug = folder.name
            if slug in slugs:
                raise ValueError(f"duplicate logical package name: {slug}")
            slugs.add(slug)
            if [path.name for path in _files(folder)] != ["SKILL.md"]:
                raise ValueError(f"package must hold only SKILL.md in this text batch: {folder}")
            skill = folder / "SKILL.md"
            note = NOTES / f"{slug}.md"
            skill_digest, skill_bytes = _digest(skill)
            note_digest, note_bytes = _digest(note)
            entries.append({
                "name": slug,
                "group": group,
                "package_path": skill.relative_to(ROOT).as_posix(),
                "package_sha256": skill_digest,
                "package_bytes": skill_bytes,
                "review_note_path": note.relative_to(ROOT).as_posix(),
                "review_note_sha256": note_digest,
                "review_note_bytes": note_bytes,
                "state": "candidate_only",
            })
    note_names = {path.name for path in _files(NOTES)}
    expected = {f"{slug}.md" for slug in slugs}
    if note_names != expected:
        raise ValueError(f"review-note mismatch: extra={sorted(note_names - expected)}, missing={sorted(expected - note_names)}")
    return sorted(entries, key=lambda row: row["name"])


def render(base_revision: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", base_revision):
        raise ValueError("base revision must be a full Git object ID")
    entries = inventory()
    if not entries:
        raise ValueError("candidate batch is empty")
    record = {
        "record_type": RECORD_TYPE,
        "prepared_from_repository_revision": base_revision,
        "approval_state": "none",
        "rights_state": "pending_independent_review",
        "effect_qualification": "none",
        "benefit_evidence": "unmeasured",
        "package_count": len(entries),
        "entries": entries,
    }
    return json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main() -> int:
    global ROOT, PACKAGES, NOTES, MANIFEST
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--write", action="store_true")
    choice.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, help="candidate batch root; defaults to this script's folder")
    parser.add_argument("--base-revision", help="full Git revision used as the research starting point")
    args = parser.parse_args()
    try:
        if args.root is not None:
            selected = args.root.absolute()
            if selected.is_symlink() or not selected.is_dir():
                raise ValueError("batch root is missing or symlinked")
            ROOT = selected
            PACKAGES = ROOT / "packages"
            NOTES = ROOT / "review-notes"
            MANIFEST = ROOT / "manifest.json"
        if args.write:
            if not args.base_revision:
                raise ValueError("--write requires --base-revision")
            rendered = render(args.base_revision)
            temporary = MANIFEST.with_suffix(".json.tmp")
            temporary.write_text(rendered, encoding="utf-8")
            temporary.replace(MANIFEST)
            print(f"wrote {MANIFEST} with {len(inventory())} candidates")
        else:
            if args.base_revision:
                raise ValueError("--base-revision applies only to --write")
            stored = json.loads(MANIFEST.read_text(encoding="utf-8"))
            if stored.get("record_type") != RECORD_TYPE:
                raise ValueError("unsupported manifest record type")
            rendered = render(stored["prepared_from_repository_revision"])
            if MANIFEST.read_text(encoding="utf-8") != rendered:
                raise ValueError("manifest does not match current exact bytes")
            print(f"checked {MANIFEST} with {stored['package_count']} candidates")
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.exit(1, f"candidate batch refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
