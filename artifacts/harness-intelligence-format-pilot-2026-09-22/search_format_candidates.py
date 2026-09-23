"""Local metadata search over heterogeneous candidate packages.

The exact source-file manifest and logical candidate catalogue must agree
before any result is returned. This tool exposes metadata and digests only;
it has no customer grants, approval power, or executable invocation path.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sqlite3
from pathlib import Path, PurePosixPath

import make_format_manifest as source_manifest

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "candidate-items.json"
MANIFEST = ROOT / "manifest.json"
CATALOG_TYPE = "heterogeneous_harness_candidate_catalog/v1"
TERMS = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset({"a", "an", "and", "as", "at", "before", "by", "for", "from",
                       "how", "i", "in", "is", "it", "of", "on", "or", "our", "the",
                       "this", "to", "we", "when", "with", "you"})
SENSITIVE = re.compile(r"(?i)(bearer\s+\S+|api[_-]?key\s*[:=]\s*\S+|secret\s*[:=]\s*\S+|sk-[a-z0-9]{16,})")


class FormatCandidateSearchError(ValueError):
    """The local candidate catalogue cannot be searched without guessing."""


def _safe_text(value: object, field: str) -> str:
    if (not isinstance(value, str) or not value.strip()
            or any(ord(character) < 32 for character in value)
            or SENSITIVE.search(value)):
        raise FormatCandidateSearchError(f"unsafe or empty candidate metadata: {field}")
    return value


def _safe_path(value: object, field: str) -> str:
    path = _safe_text(value, field)
    parsed = PurePosixPath(path)
    if (parsed.is_absolute() or ".." in parsed.parts or "." in parsed.parts
            or "\\" in path or parsed.as_posix() != path):
        raise FormatCandidateSearchError(f"unsafe candidate path: {field}")
    return path


def _stem(value: str) -> str:
    if value.endswith("ies") and len(value) > 4:
        return value[:-3] + "y"
    if value.endswith("s") and not value.endswith("ss") and len(value) > 3:
        return value[:-1]
    return value


def _indexed_paths(item: dict, client: str | None) -> list[str]:
    selected = [item["delivery_variants"][client]] if client is not None else item["delivery_variants"].values()
    return list(dict.fromkeys([*item["source_files"],
                               *(path for group in selected for path in group)]))


def _check_variant_dependencies(paths: list[str], by_path: dict[str, dict]) -> None:
    selected = set(paths)
    for path in paths:
        if path.endswith("/CLAUDE.md"):
            body = (ROOT / path).read_text(encoding="utf-8")
            if "@AGENTS.md" in body:
                sibling = str(PurePosixPath(path).parent / "AGENTS.md")
                if sibling not in selected:
                    raise FormatCandidateSearchError("Claude instruction import missing from variant")
        if not path.endswith(".py") or "/scripts/" not in path:
            continue
        try:
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeError) as error:
            raise FormatCandidateSearchError(f"invalid candidate Python source: {path}") from error
        for node in ast.walk(tree):
            modules = []
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.append(node.module.split(".")[0])
            elif isinstance(node, ast.Import):
                modules.extend(alias.name.split(".")[0] for alias in node.names)
            for module in modules:
                sibling = str(PurePosixPath(path).parent / f"{module}.py")
                if sibling in by_path and sibling not in selected:
                    raise FormatCandidateSearchError(f"local Python dependency missing: {sibling}")


def _check_client_payload_path(item: dict, client: str, path: str) -> None:
    parts = PurePosixPath(path).parts
    identity_parts = item["id"].split(".")
    if len(identity_parts) != 4:
        raise FormatCandidateSearchError("candidate identity shape invalid")
    slug = identity_parts[2]
    kind = item["kind"]
    if kind == "native_step_instructions":
        valid = (len(parts) == 5 and parts[:2] == ("context", slug)
                 and parts[2:4] == (client, "work"))
    elif kind == "skill_with_python_tool":
        valid = (len(parts) >= 3 and parts[:2] == ("tools", slug))
    elif kind == "local_protocol_server_connection":
        valid = (len(parts) >= 6 and parts[:5] ==
                 ("connections", slug, "layouts", client, "work"))
    else:
        raise FormatCandidateSearchError("unknown candidate kind")
    if not valid:
        raise FormatCandidateSearchError(f"wrong client layout or package path: {path}")


def _read_record(path: Path, maximum: int = 200_000) -> tuple[dict, str]:
    if path.is_symlink() or not path.is_file():
        raise FormatCandidateSearchError(f"missing or symlinked record: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > maximum:
        raise FormatCandidateSearchError(f"empty or overlarge record: {path}")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise FormatCandidateSearchError(f"invalid JSON record: {path}") from error
    if not isinstance(data, dict):
        raise FormatCandidateSearchError(f"record must be an object: {path}")
    return data, hashlib.sha256(raw).hexdigest()


def validated_catalogue() -> tuple[list[dict], dict[str, dict], str, str]:
    manifest, manifest_digest = _read_record(MANIFEST, maximum=1_000_000)
    if manifest.get("record_type") != source_manifest.RECORD_TYPE:
        raise FormatCandidateSearchError("unsupported source manifest")
    try:
        canonical = source_manifest.render(manifest["prepared_from_repository_revision"], ROOT)
    except (OSError, ValueError, KeyError) as error:
        raise FormatCandidateSearchError(f"source inventory refused: {error}") from error
    if MANIFEST.read_text(encoding="utf-8") != canonical:
        raise FormatCandidateSearchError("source manifest differs from exact current files")
    by_path = {row["path"]: row for row in manifest["entries"]}
    catalog, catalog_digest = _read_record(CATALOG)
    if (set(catalog) != {"record_type", "state", "approval_state",
                         "customer_distribution_license", "items"}
            or catalog.get("record_type") != CATALOG_TYPE
            or catalog.get("state") != "candidate_only"
            or catalog.get("approval_state") != "none"
            or catalog.get("customer_distribution_license") != "pending"):
        raise FormatCandidateSearchError("unsupported logical candidate catalogue")
    items = catalog.get("items")
    if not isinstance(items, list) or len(items) != 6:
        raise FormatCandidateSearchError("expected six logical pilot candidates")
    names = set()
    file_owners = {}
    for item in items:
        required = {"id", "kind", "title", "description", "target_clients",
                    "activation", "effect_requirement", "source_files",
                    "delivery_variants", "review_note"}
        if not isinstance(item, dict) or set(item) != required:
            raise FormatCandidateSearchError("candidate item fields incomplete or unknown")
        identity = _safe_text(item["id"], "id")
        if identity in names:
            raise FormatCandidateSearchError("candidate identity or files invalid")
        names.add(identity)
        if (not isinstance(item["target_clients"], list)
                or not item["target_clients"]
                or any(not isinstance(client, str) for client in item["target_clients"])
                or len(set(item["target_clients"])) != len(item["target_clients"])
                or not isinstance(item["delivery_variants"], dict)
                or set(item["target_clients"]) != set(item["delivery_variants"])):
            raise FormatCandidateSearchError("target client metadata invalid")
        for client in item["target_clients"]:
            _safe_text(client, "target_client")
        if not isinstance(item["source_files"], list):
            raise FormatCandidateSearchError("source file list invalid")
        all_item_paths = list(item["source_files"])
        for client, variant_paths in item["delivery_variants"].items():
            if (not isinstance(variant_paths, list) or not variant_paths
                    or any(not isinstance(path, str) for path in variant_paths)):
                raise FormatCandidateSearchError(f"empty client variant: {client}")
            if len(set(variant_paths)) != len(variant_paths):
                raise FormatCandidateSearchError(f"duplicate file within client variant: {client}")
            all_item_paths.extend(variant_paths)
        for path in all_item_paths:
            path = _safe_path(path, "delivery_path")
            if path not in by_path or (path in file_owners and file_owners[path] != identity):
                raise FormatCandidateSearchError(f"missing or cross-item repeated deliverable: {path}")
            file_owners[path] = identity
        for path in item["source_files"]:
            if by_path[path]["file_role"] not in {"canonical_source", "delivery_payload"}:
                raise FormatCandidateSearchError(f"non-source candidate file: {path}")
        for client, variant_paths in item["delivery_variants"].items():
            for path in variant_paths:
                if by_path[path]["file_role"] != "delivery_payload":
                    raise FormatCandidateSearchError(f"non-payload delivery file: {path}")
                _check_client_payload_path(item, client, path)
            _check_variant_dependencies(variant_paths, by_path)
        note = _safe_path(item["review_note"], "review_note")
        if note not in by_path or by_path[note]["file_role"] != "review_only":
            raise FormatCandidateSearchError("review note role or file missing from exact manifest")
        for field in ("kind", "title", "description", "activation", "effect_requirement"):
            _safe_text(item[field], field)
    return items, by_path, manifest_digest, catalog_digest


def _card(item: dict, files: dict[str, dict], manifest_digest: str,
          catalog_digest: str, client: str | None,
          score: float | None = None) -> dict:
    card = {
        "id": item["id"],
        "kind": item["kind"],
        "title": item["title"],
        "description": item["description"],
        "target_clients": item["target_clients"],
        "activation": item["activation"],
        "effect_requirement": item["effect_requirement"],
        "source_files": [{"path": path, "sha256": files[path]["sha256"]}
                         for path in item["source_files"]],
        "review_note": {"path": item["review_note"],
                        "sha256": files[item["review_note"]]["sha256"]},
        "manifest_sha256": manifest_digest,
        "catalogue_sha256": catalog_digest,
        "state": "candidate_only",
    }
    if client is None:
        card["available_client_variants"] = item["target_clients"]
        card["variant_selection_required"] = True
    else:
        card["selected_client"] = client
        card["delivery_files"] = [
            {"path": path, "sha256": files[path]["sha256"]}
            for path in item["delivery_variants"][client]
        ]
        card["native_load"] = "unqualified"
    if score is not None:
        card["score"] = round(score, 3)
    return card


def search(*, query: str | None = None, item_id: str | None = None,
           kind: str | None = None, client: str | None = None, limit: int = 5) -> dict:
    if (query is None) == (item_id is None):
        raise FormatCandidateSearchError("supply exactly one query or exact item ID")
    if not 1 <= limit <= 10:
        raise FormatCandidateSearchError("limit must be between one and ten")
    items, files, manifest_digest, catalog_digest = validated_catalogue()
    eligible = [item for item in items
                if (kind is None or item["kind"] == kind)
                and (client is None or client in item["target_clients"])]
    result = {"record_type": "local_format_candidate_search_result/v1",
              "scope": "local_candidate_metadata_only", "approval_state": "none",
              "scope_warning": "Unreviewed metadata and source paths are for local developers only; no client authority or customer exposure.",
              "outcome": "no_match", "matches": []}
    if item_id is not None:
        result["exact_id"] = item_id
        selected = next((item for item in eligible if item["id"] == item_id), None)
        if selected is not None:
            result["outcome"] = "matches"
            result["matches"] = [_card(selected, files, manifest_digest, catalog_digest, client)]
        return result
    assert query is not None
    result["query"] = query
    if len(query) > 500:
        raise FormatCandidateSearchError("query too long")
    terms = list(dict.fromkeys(token for token in TERMS.findall(query.casefold())
                               if len(token) >= 3 and token not in STOPWORDS))
    if not terms or len(terms) > 16:
        return result
    stemmed_terms = set(map(_stem, terms))
    try:
        db = sqlite3.connect(":memory:")
        db.execute("CREATE VIRTUAL TABLE cards USING fts5(id, title, description, kind, clients, filenames, tokenize='porter unicode61')")
    except sqlite3.OperationalError as error:
        raise FormatCandidateSearchError(f"SQLite FTS5 unavailable: {error}") from error
    try:
        for item in eligible:
            db.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?)",
                       (item["id"], item["title"], item["description"], item["kind"],
                        " ".join(item["target_clients"]),
                        " ".join(_indexed_paths(item, client))))
        expression = " OR ".join(f'"{term}"' for term in terms)
        rows = db.execute("SELECT rowid FROM cards WHERE cards MATCH ?", (expression,)).fetchall()
        ranked = []
        for (rowid,) in rows:
            item = eligible[rowid - 1]
            primary = {_stem(token) for token in TERMS.findall(
                (item["id"] + " " + item["title"] + " " + item["description"]).casefold())}
            secondary = {_stem(token) for token in TERMS.findall(
                (item["kind"] + " " + " ".join(item["target_clients"]) + " "
                 + " ".join(_indexed_paths(item, client))).casefold())}
            strong = stemmed_terms & primary
            weak = stemmed_terms & secondary
            score = (2 * len(strong) + 0.25 * len(weak)) / len(stemmed_terms)
            if len(strong) < 1 or score < 0.7:
                continue
            ranked.append((-score, item["id"], item))
        ranked.sort()
        if ranked:
            best = -ranked[0][0]
            selected = [row for row in ranked if -row[0] >= 0.7 * best][:limit]
            result["matches"] = [_card(item, files, manifest_digest, catalog_digest,
                                       client, -negative)
                                 for negative, _, item in selected]
            result["outcome"] = "matches"
        return result
    except sqlite3.Error as error:
        raise FormatCandidateSearchError(f"candidate metadata search failed: {error}") from error
    finally:
        db.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?")
    parser.add_argument("--id", dest="item_id")
    parser.add_argument("--kind")
    parser.add_argument("--client")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()
    try:
        print(json.dumps(search(query=args.query, item_id=args.item_id,
                                kind=args.kind, client=args.client,
                                limit=args.limit), indent=2, sort_keys=True))
    except (FormatCandidateSearchError, OSError, ValueError) as error:
        parser.exit(2, f"mixed-format candidate search refused: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
