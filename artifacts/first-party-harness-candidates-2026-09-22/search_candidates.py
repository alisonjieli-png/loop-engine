"""Search this local, unapproved candidate batch for reviewer triage.

The tool rebuilds an in-memory SQLite FTS5 index only after checking the
canonical manifest against every package and review-note byte. Review notes
are searchable here for local triage, but the returned cards contain neither
their text nor the native skill body. Search is not approval or service access.

Examples:
    python3 search_candidates.py --name audit-measurement-units
    python3 search_candidates.py "check units before adding invoice lines" --group data
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GROUPS = ("data", "project", "software")
EFFECTS = ("none", "file_write", "shell_command", "network", "model_call", "spending", "external_mutation")
RECORD_TYPE = "first_party_harness_candidate_batch_manifest/v1"
TERMS = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset({
    "a", "about", "after", "against", "an", "and", "are", "as", "at", "be", "before",
    "around", "between", "by", "can", "check", "do", "does", "during", "find",
    "for", "from", "have", "how", "i", "in", "instead", "into", "is",
    "it", "my", "not", "of", "on", "or", "our", "out", "should",
    "that", "the", "their", "then", "this", "to", "use", "using", "was",
    "we", "were", "what", "when", "which", "why", "with", "without",
    "would", "you",
})
MAX_RESULTS = 10
MAX_QUERY_LENGTH = 500
MAX_TERMS = 16
MIN_TOTAL_COVERAGE = 0.60
MIN_DETAIL_COVERAGE = 0.60
MIN_PRIMARY_SCORE = 1.00
MIN_DETAIL_SCORE = 0.55
MIN_RELATIVE_TO_BEST_SCORE = 0.75


class CandidateSearchError(ValueError):
    """The candidate batch or query cannot be searched safely."""


def _content(path: Path) -> tuple[bytes, str, int]:
    if path.is_symlink() or not path.is_file():
        raise CandidateSearchError(f"missing or symlinked file: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > 100_000:
        raise CandidateSearchError(f"empty or overlarge candidate file: {path}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise CandidateSearchError(f"candidate file is not UTF-8: {path}") from error
    return raw, hashlib.sha256(raw).hexdigest(), len(raw)


def _skill_text(body: str, slug: str) -> tuple[str, str]:
    """Read frontmatter and body without treating either as instructions."""
    lines = body.splitlines()
    if len(lines) < 5 or lines[0] != "---":
        raise CandidateSearchError(f"invalid skill frontmatter: {slug}")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise CandidateSearchError(f"unterminated skill frontmatter: {slug}") from error
    fields: dict[str, str] = {}
    for line in lines[1:end]:
        key, separator, value = line.partition(":")
        if not separator or key not in {"name", "description"} or key in fields:
            raise CandidateSearchError(f"unsupported skill frontmatter: {slug}")
        fields[key] = value.strip()
    if set(fields) != {"name", "description"} or fields["name"] != slug:
        raise CandidateSearchError(f"skill name differs from package directory: {slug}")
    description = fields["description"]
    if not description or len(description) > 1024:
        raise CandidateSearchError(f"invalid skill description: {slug}")
    return description, "\n".join(lines[end + 1:])


def _task_note(note: str) -> str:
    """Keep task evidence and discovery phrases, not administrative notes."""
    labels = (
        "applicability", "typed input", "conceptual input", "conceptual output",
        "known-good", "known-wrong", "good case", "limitations",
        "search phrasing",
    )
    return "\n".join(
        line for line in note.splitlines()
        if line.startswith("- ") and line[2:].casefold().startswith(labels)
    )


def _validated_entries(root: Path) -> tuple[list[dict], dict[str, tuple[str, str, str]], str]:
    manifest = root / "manifest.json"
    if manifest.is_symlink() or not manifest.is_file():
        raise CandidateSearchError("candidate manifest is missing or symlinked")
    raw = manifest.read_bytes()
    if len(raw) > 1_000_000:
        raise CandidateSearchError("candidate manifest is overlarge")
    try:
        stored = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CandidateSearchError("candidate manifest is not valid UTF-8 JSON") from error
    if not isinstance(stored, dict) or stored.get("record_type") != RECORD_TYPE:
        raise CandidateSearchError("unsupported candidate manifest record type")
    revision = stored.get("prepared_from_repository_revision")
    if not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise CandidateSearchError("invalid manifest base revision")
    # Load the trusted batch inventory code from this tool's own directory,
    # then point its path constants at the supplied fixture or live batch.
    # This reuses its authoritative renderer without executing a script found
    # in an arbitrary candidate directory or maintaining a second schema.
    source = ROOT / "make_manifest.py"
    spec = importlib.util.spec_from_file_location("_local_candidate_manifest", source)
    if spec is None or spec.loader is None:
        raise CandidateSearchError("candidate manifest renderer unavailable")
    manifest_tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(manifest_tool)
    manifest_tool.ROOT = root
    manifest_tool.PACKAGES = root / "packages"
    manifest_tool.NOTES = root / "review-notes"
    manifest_tool.MANIFEST = manifest
    try:
        canonical = manifest_tool.render(revision).encode("utf-8")
    except (OSError, ValueError, KeyError) as error:
        raise CandidateSearchError(f"candidate manifest inventory refused: {error}") from error
    if raw != canonical:
        raise CandidateSearchError("manifest does not match current exact package and review-note bytes")
    entries = stored["entries"]
    indexed_text: dict[str, tuple[str, str, str]] = {}
    for entry in entries:
        slug = entry["name"]
        skill_raw, skill_hash, skill_size = _content(root / entry["package_path"])
        note_raw, note_hash, note_size = _content(root / entry["review_note_path"])
        if (skill_hash != entry["package_sha256"] or skill_size != entry["package_bytes"]
                or note_hash != entry["review_note_sha256"] or note_size != entry["review_note_bytes"]):
            raise CandidateSearchError("candidate bytes changed after manifest validation")
        description, body = _skill_text(skill_raw.decode("utf-8"), slug)
        indexed_text[slug] = (description, body, _task_note(note_raw.decode("utf-8")))
    return entries, indexed_text, hashlib.sha256(raw).hexdigest()


def _query_terms(query: str) -> list[str]:
    if not isinstance(query, str) or len(query) > MAX_QUERY_LENGTH:
        raise CandidateSearchError("query exceeds the 500-character pilot limit")
    terms = list(dict.fromkeys(
        token for token in TERMS.findall(query.casefold())
        if len(token) >= 3 and token not in STOPWORDS
    ))
    if len(terms) > MAX_TERMS:
        raise CandidateSearchError("query has more than 16 meaningful terms")
    return terms


def _card(entry: dict, description: str, manifest_sha256: str) -> dict:
    return {
        "name": entry["name"],
        "group": entry["group"],
        "description": description,
        "package_path": entry["package_path"],
        "review_note_path": entry["review_note_path"],
        "package_sha256": entry["package_sha256"],
        "review_note_sha256": entry["review_note_sha256"],
        "manifest_sha256": manifest_sha256,
        "state": "candidate_only",
    }


def _open_fts_index() -> sqlite3.Connection:
    db = None
    try:
        db = sqlite3.connect(":memory:")
        db.execute(
            "CREATE VIRTUAL TABLE docs USING fts5(name, description, body, note, "
            "tokenize='porter unicode61 remove_diacritics 2')"
        )
        return db
    except sqlite3.OperationalError as error:
        if db is not None:
            db.close()
        raise CandidateSearchError(f"SQLite FTS5 is unavailable: {error}") from error


def search_candidates(
    *, query: str | None = None, name: str | None = None,
    group: str | None = None, limit: int = 5, required_effect: str = "none",
    root: Path = ROOT,
) -> dict:
    """Return candidate metadata cards after revalidating exact batch bytes."""
    if (query is None) == (name is None):
        raise CandidateSearchError("supply exactly one query or exact name")
    if group is not None and group not in GROUPS:
        raise CandidateSearchError("unknown candidate group")
    if not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise CandidateSearchError("limit must be between 1 and 10")
    if required_effect not in EFFECTS:
        raise CandidateSearchError("unknown required effect")
    root = Path(root).resolve()
    entries, texts, manifest_sha256 = _validated_entries(root)
    by_name = {entry["name"]: entry for entry in entries}
    base = {
        "record_type": "local_candidate_search_result/v1",
        "scope": "local_candidate_batch_only",
        "approval_state": "none",
        "effect_qualification": "none",
        "requested_effect": required_effect,
        "scope_warning": "Candidate search does not grant loading, execution, or effect authority.",
        "outcome": "no_match",
        "matches": [],
    }
    if required_effect != "none":
        base["scope_warning"] = (
            "No candidate in this batch has a qualified effect; the requested effect cannot be matched."
        )
        if name is not None:
            base["exact_name"] = name
        else:
            base["query"] = query
        return base
    if name is not None:
        db = _open_fts_index()
        db.close()
        base["exact_name"] = name
        entry = by_name.get(name)
        if entry and (group is None or entry["group"] == group):
            base["outcome"] = "matches"
            base["matches"] = [_card(entry, texts[name][0], manifest_sha256)]
        return base

    assert query is not None
    base["query"] = query
    base["relevance_floor"] = {
        "min_total_term_fraction": MIN_TOTAL_COVERAGE,
        "min_detail_term_fraction": MIN_DETAIL_COVERAGE,
        "min_primary_weighted_score": MIN_PRIMARY_SCORE,
        "min_detail_weighted_score": MIN_DETAIL_SCORE,
        "min_relative_to_best_weighted_score": MIN_RELATIVE_TO_BEST_SCORE,
        "requires_distinctive_term": True,
    }
    terms = _query_terms(query)
    if not terms:
        return base
    minimum_total_hits = 1 if len(terms) == 1 else max(2, math.ceil(MIN_TOTAL_COVERAGE * len(terms)))
    base["relevance_floor"]["min_total_terms"] = minimum_total_hits
    base["relevance_floor"]["min_detail_terms"] = max(3, math.ceil(MIN_DETAIL_COVERAGE * len(terms)))
    db = _open_fts_index()
    try:
        for entry in entries:
            description, body, note = texts[entry["name"]]
            db.execute(
                "INSERT INTO docs (name, description, body, note) VALUES (?, ?, ?, ?)",
                (entry["name"], description, body, note),
            )
        # Terms are ASCII letters/digits only and quoted as literals. The MATCH
        # expression and every SQL value are bound parameters, never raw SQL.
        match = " OR ".join(f'"{term}"' for term in terms)
        rows = db.execute(
            "SELECT rowid, bm25(docs, 4.0, 3.0, 1.0, 0.8) FROM docs "
            "WHERE docs MATCH ? ORDER BY bm25(docs, 4.0, 3.0, 1.0, 0.8) LIMIT ?",
            (match, len(entries)),
        ).fetchall()
        fields = ("name", "description", "body", "note")
        weights = {"name": 4.0, "description": 3.0, "body": 1.0, "note": 0.8}
        # Ask FTS5 which query terms matched in each field. This uses the
        # same English stemming for retrieval and the relevance floor.
        hit_fields: dict[int, dict[str, set[str]]] = {}
        document_frequency: dict[str, set[int]] = {term: set() for term in terms}
        for term in terms:
            for field in fields:
                field_query = f'{field}:"{term}"'
                for (rowid,) in db.execute("SELECT rowid FROM docs WHERE docs MATCH ?", (field_query,)):
                    hit_fields.setdefault(rowid, {}).setdefault(term, set()).add(field)
                    document_frequency[term].add(rowid)
        ranked = []
        for rowid, bm25_value in rows:
            entry = entries[rowid - 1]
            if group is not None and entry["group"] != group:
                continue
            description = texts[entry["name"]][0]
            matched = hit_fields.get(rowid, {})
            total_hits = set(matched)
            primary_hits = {term for term, locations in matched.items()
                            if locations & {"name", "description"}}
            body_hits = {term for term, locations in matched.items() if "body" in locations}
            note_hits = {term for term, locations in matched.items() if "note" in locations}
            total_coverage = len(total_hits) / len(terms)
            primary_coverage = len(primary_hits) / len(terms)
            weighted = sum(max(weights[field] for field in locations)
                           for locations in matched.values()) / len(terms)
            distinctive = any(
                len(document_frequency[term]) <= max(2, len(entries) // 3)
                for term in total_hits
            )
            primary_pass = (len(total_hits) >= minimum_total_hits
                            and bool(primary_hits) and weighted >= MIN_PRIMARY_SCORE)
            detail_pass = (len(total_hits) >= base["relevance_floor"]["min_detail_terms"]
                           and bool(body_hits) and bool(note_hits)
                           and weighted >= MIN_DETAIL_SCORE)
            if not distinctive or not (primary_pass or detail_pass):
                continue
            card = _card(entry, description, manifest_sha256)
            card.update({
                "matched_terms": sorted(total_hits),
                "term_coverage": round(total_coverage, 3),
                "name_description_term_coverage": round(primary_coverage, 3),
                "weighted_score": round(weighted, 3),
                "match_basis": "native_metadata" if primary_pass else "body_and_review_note",
            })
            ranked.append((-weighted, bm25_value, entry["name"], card))
        ranked.sort(key=lambda item: item[:3])
        if ranked:
            best_score = -ranked[0][0]
            ranked = [item for item in ranked
                      if -item[0] >= best_score * MIN_RELATIVE_TO_BEST_SCORE]
            for item in ranked:
                item[3]["relative_to_best_score"] = round((-item[0]) / best_score, 3)
        base["matches"] = [item[3] for item in ranked[:limit]]
        if base["matches"]:
            base["outcome"] = "matches"
        return base
    except sqlite3.Error as error:
        raise CandidateSearchError(f"candidate search failed: {error}") from error
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="natural-language local candidate query")
    parser.add_argument("--name", help="exact candidate name")
    parser.add_argument("--root", type=Path, default=ROOT,
                        help="candidate batch root; defaults to this script's folder")
    parser.add_argument("--group", choices=GROUPS, help="limit results to one package group")
    parser.add_argument("--limit", type=int, default=5, help="maximum result cards, 1 to 10")
    parser.add_argument("--required-effect", choices=EFFECTS, default="none",
                        help="typed required effect; only none is qualified in this candidate batch")
    args = parser.parse_args()
    try:
        result = search_candidates(query=args.query, name=args.name, group=args.group,
                                   limit=args.limit, required_effect=args.required_effect,
                                   root=args.root)
    except (CandidateSearchError, OSError) as error:
        parser.exit(2, f"candidate search refused: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
