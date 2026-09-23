"""Search several isolated candidate batches for reviewer discovery only.

Every batch is checked against its exact manifest before results are
combined. This is not a hosted, grant-aware, or approved intelligence index.
The per-batch in-memory indexes are rebuilt for each query, so this tool is
appropriate for pilot review, not a ten-thousand-item production service.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from search_candidates import (
    MAX_RESULTS,
    CandidateSearchError,
    _validated_entries,
    search_candidates,
)


def inventory(roots: list[Path]) -> tuple[list[tuple[Path, str]], int]:
    if not roots or len(roots) > 20:
        raise CandidateSearchError("one to twenty candidate batch roots are required")
    seen_roots = set()
    names: dict[str, Path] = {}
    digests: dict[str, Path] = {}
    manifests = []
    for supplied in roots:
        if supplied.is_symlink() or not supplied.is_dir():
            raise CandidateSearchError(f"missing or symlinked batch root: {supplied}")
        root = supplied.resolve()
        if root in seen_roots:
            raise CandidateSearchError(f"batch root repeated: {root}")
        seen_roots.add(root)
        entries, _, manifest_digest = _validated_entries(root)
        manifests.append((root, manifest_digest))
        for entry in entries:
            name = entry["name"]
            body_digest = entry["package_sha256"]
            if name in names:
                raise CandidateSearchError(f"candidate name repeated across batches: {name}")
            if body_digest in digests:
                raise CandidateSearchError(
                    f"exact native body repeated across batches: {entry['package_path']}"
                )
            names[name] = root
            digests[body_digest] = root
    return manifests, len(names)


def search_all(
    *, roots: list[Path], query: str | None = None, name: str | None = None,
    limit: int = 5, required_effect: str = "none", check_only: bool = False,
) -> dict:
    manifests, count = inventory(roots)
    base = {
        "record_type": "local_multi_batch_candidate_search/v1",
        "scope": "local_candidate_batches_only",
        "approval_state": "none",
        "candidate_count": count,
        "batch_manifests": [
            {"root": str(root), "manifest_sha256": digest}
            for root, digest in manifests
        ],
    }
    if check_only:
        if query is not None or name is not None:
            raise CandidateSearchError("check-only cannot include a search query")
        base["outcome"] = "inventory_checked"
        return base
    if (query is None) == (name is None):
        raise CandidateSearchError("supply exactly one query or exact name")
    if not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise CandidateSearchError("limit must be between 1 and 10")
    cards = []
    for root, _ in manifests:
        result = search_candidates(query=query, name=name, limit=MAX_RESULTS,
                                   required_effect=required_effect, root=root)
        for card in result["matches"]:
            cards.append({**card, "batch_root": str(root)})
    if query is not None and cards:
        cards.sort(key=lambda card: (-card["weighted_score"], card["name"]))
        best = cards[0]["weighted_score"]
        cards = [card for card in cards if card["weighted_score"] >= 0.75 * best]
    base["outcome"] = "matches" if cards else "no_match"
    base["matches"] = cards[:limit]
    if query is not None:
        base["query"] = query
    else:
        base["exact_name"] = name
    base["requested_effect"] = required_effect
    base["limitations"] = (
        "Candidate-only metadata search. Per-batch lexical scores are compared "
        "for reviewer triage; no hosted relevance or account-grant claim."
    )
    return base


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", nargs="?", help="natural-language query")
    parser.add_argument("--name", help="exact candidate name")
    parser.add_argument("--root", type=Path, action="append", required=True,
                        help="candidate batch root; repeat for each batch")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--required-effect", default="none")
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    try:
        result = search_all(roots=args.root, query=args.query, name=args.name,
                            limit=args.limit, required_effect=args.required_effect,
                            check_only=args.check_only)
    except (CandidateSearchError, OSError, ValueError) as error:
        parser.exit(2, f"multi-batch candidate search refused: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
