"""Compare catalogue ranking policies over judged queries on one complete catalogue release; read only.

Kind: local measurement tool. It reads one complete catalogue bundle (version 1, or a complete segmented version 2
bundle such as a reconciled publication bundle) through the service's own validators, builds the service's own
in-memory search index once (`catalogue_search.ReleaseSearchIndex`; the disk engine the host serves ranks exactly
as it does), and asks `catalogue_search.authorized_hits` every judged query once for each ranking policy, as an
account that receives every listed item. It reads no body, calls no model or provider and writes only its outputs,
which belong outside this public repository.

```text
Comparison
├── population   every item of the bundle, checked against the content digest its header states
├── judgements   catalogue_search_judgements/v1 files; a query is measurable when one of its relevant identities is
│                listed in the release, and its split is the one the file records
├── policies     the baseline first, then the candidate, then the measured alternatives; one index for all of them
├── metrics      recall at 1, 5 and 10 and the mean reciprocal rank within the first ten, by file and split
├── movements    each (query, identity) pair the baseline places in its first ten: lost, moved down, moved up
├── time         each search's wall time; the process's peak resident memory
└── verdict      ship_candidate only when the candidate loses no expected hit the baseline finds, in any file, and
                 raises the regression file's mean reciprocal rank on its development and its held-back split;
                 otherwise keep_baseline, with the rows that decide it
```

The verdict rule is fixed here, before any measurement, and the regression file's held-back split is read only in
the report: a policy is chosen on development rows.

`--replay` writes the small fixture the repository's checks replay without the catalogue
(`tools/test_catalogue_search_ranking.py`): for every measurable query, the lexical candidates that can reach the
first ten under any policy of this family, the first-ten answers of the baseline and the candidate, and the
digests that bind them to the release and the judgements. `--entries-cache` keeps the validated search entries of a
bundle in one private file bound to the bundle's header and content digests, so a second comparison does not
re-read every item line.

    python tools/compare_catalogue_ranking.py --bundle /abs/reconciled-bundle --accept-license MIT \\
        --judgements examples/30_search_quality/relevance-judgements.json \\
        --regression examples/30_search_quality/live-catalogue-regressions.json \\
        --report /abs/outside/report.json
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from dataclasses import asdict, replace
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from types import SimpleNamespace

REPOSITORY = Path(__file__).resolve().parents[1]
for _folder in (REPOSITORY / "src", REPOSITORY / "tools"):
    if str(_folder) not in sys.path:
        sys.path.insert(0, str(_folder))

from loop_engine.core.service_runtime import catalogue_search  # noqa: E402
from loop_engine.core.service_runtime.catalogue_bundle import read_bundle, strict_json  # noqa: E402
from loop_engine.core.service_runtime.catalogue_releases import content_digest  # noqa: E402
from loop_engine.core.service_runtime.catalogue_schema import CatalogueAttributeSchema  # noqa: E402
from loop_engine.core.service_runtime.catalogue_search import (  # noqa: E402
    BOUNDED_TIER_BOOST, HYBRID_MODE, LEXICAL_MODE, RANKING_ENGINES, RANKING_POLICIES, IndexEntry, ReleaseSearchIndex,
    authorized_hits)
from loop_engine.core.service_runtime.catalogue_segments import (  # noqa: E402
    SEGMENTED_BUNDLE_RECORD_TYPE, bundle_record_type, read_segmented_bundle, segment_entries)
from loop_engine.core.service_runtime.catalogue_tiers import COMMUNITY_TIER, VERIFIED_TIER  # noqa: E402

REPORT_VERSION = "catalogue_ranking_comparison/v1"
REPLAY_VERSION = "catalogue_ranking_replay/v1"
CACHE_VERSION = "catalogue_ranking_entries_cache/v1"
SHIP, KEEP = "ship_candidate", "keep_baseline"
TOP_N = 10
CUT_OFFS = (1, 5, 10)
SPLITS = ("development", "held_back")
#: Lexical candidates kept per tier in a replay fixture. Within one tier every policy of this family keeps the
#: index's order, so at most the first ten of each tier reach a first-ten answer; two more are a margin.
REPLAY_ROWS_PER_TIER = 12
BASELINE, CANDIDATE = "strict_tier_order", "bounded_tier_boost"
_STRICT = RANKING_POLICIES[BASELINE]
#: The alternatives measured beside the candidate. Each is a declared variation of the served policy, so the
#: difference between two columns of the report is a declared difference.
ALTERNATIVES = {
    "strict_floor_0_35": replace(_STRICT, lexical_score_floor_ratio=0.35),
    "strict_floor_0_5": replace(_STRICT, lexical_score_floor_ratio=0.5),
    "tie_breaker_only": replace(_STRICT, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=0.0),
    "bounded_boost_0_5": replace(_STRICT, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=0.5),
    "bounded_boost_2": replace(_STRICT, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=2.0),
    "bounded_boost_4": replace(_STRICT, lexical_tier_order=BOUNDED_TIER_BOOST, lexical_verified_boost=4.0),
    "field_weighted_lexical": RANKING_ENGINES["field_weighted_lexical"],
    "phrase_and_symbol_boost": RANKING_ENGINES["phrase_and_symbol_boost"],
    "gated_relevance_fusion": RANKING_ENGINES["gated_relevance_fusion"],
    "flexible_lsh_fallback": RANKING_ENGINES["flexible_lsh_fallback"],
}
#: A measured alternative that no policy field can express: verified candidates keep their precedence only
#: within this share of the query's best lexical score, and every other candidate is ordered by score.
BAND_ALTERNATIVES = {"verified_band_0_5": 0.5, "verified_band_0_75": 0.75}
DEFAULT_LICENSES = ("MIT",)


def _peak_kib():
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _host_policies(accepted_licenses):
    from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
    return {"license_policy": HostLicensePolicy(tuple(accepted_licenses)), "family_policy": HostFamilyPolicy()}


def _bundle_items(folder, accepted_licenses):
    """The bundle's validated items in identity order, its schema, item count and stated content digest.

    A version 2 bundle is read one segment and one item line at a time, so the package file lists of a large
    release are never held together. Each line passes every check the publisher applies.
    """
    folder = Path(folder)
    policies = _host_policies(accepted_licenses)
    if bundle_record_type(folder) == SEGMENTED_BUNDLE_RECORD_TYPE:
        bundle = read_segmented_bundle(folder, **policies)

        def items():
            for ref in bundle.segments:
                document = bundle.carried_segment(ref.digest)
                if document is None:
                    raise ValueError("compare a complete bundle: a segment of the release is not carried")
                for identity, version in segment_entries(document, ref.digest):
                    entry = bundle.carried_item(version)
                    if entry is None or entry.identity != identity:
                        raise ValueError("compare a complete bundle: an item line of the release is not carried")
                    yield entry
        return bundle.digest, bundle.schema, bundle.release_items, bundle.content_digest, items()
    bundle = read_bundle(folder, verify_blobs=False, **policies)
    stated = content_digest(bundle.schema.digest, tuple((entry.identity, entry.version) for entry in bundle.items))
    return bundle.digest, bundle.schema, len(bundle.items), stated, iter(bundle.items)


def load_entries(folder, accepted_licenses):
    """The index entries a store view builds for every item of one bundle, as `plan_catalogue_change` builds them."""
    from plan_catalogue_change import index_entry
    header_digest, schema, count, stated, items = _bundle_items(folder, accepted_licenses)
    entries, pairs, previous = [], [], None
    for entry in items:
        if previous is not None and entry.identity <= previous:
            raise ValueError("the bundle's items are not in identity order")
        previous = entry.identity
        entries.append(index_entry(entry, schema))
        pairs.append((entry.identity, entry.version))
    digest = content_digest(schema.digest, tuple(pairs))
    if len(pairs) != count or digest != stated:
        raise ValueError("the bundle's items differ from the count and content digest its header states")
    return {"bundle_digest": header_digest, "schema": schema, "content_digest": digest,
            "entries": tuple(entries), "versions": tuple(version for _identity, version in pairs)}


def write_entries_cache(path, loaded):
    """Write the validated entries once, to a new private file, with the digests that bind them."""
    path = Path(path)
    _outside_repository(path)
    lines, checksum = [], hashlib.sha256()
    for entry, version in zip(loaded["entries"], loaded["versions"]):
        line = (json.dumps([entry.identity, version, entry.tier, entry.runnable, entry.text, entry.values],
                           ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        checksum.update(line)
        lines.append(line)
    header = {"record_type": CACHE_VERSION, "bundle_digest": loaded["bundle_digest"],
              "content_digest": loaded["content_digest"], "schema": loaded["schema"].to_dict(),
              "items": len(lines), "lines_sha256": checksum.hexdigest()}
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(json.dumps(header, sort_keys=True).encode("utf-8") + b"\n")
        stream.writelines(lines)


def read_entries_cache(path, bundle_folder):
    """Read a cache written by `write_entries_cache`, refused unless it matches the bundle it names."""
    raw = Path(path).read_bytes()
    first, _, body = raw.partition(b"\n")
    header = strict_json(first, "ranking_cache_invalid")
    if not isinstance(header, dict) or header.get("record_type") != CACHE_VERSION:
        raise ValueError(f"the entries cache is not a {CACHE_VERSION} record")
    if hashlib.sha256(body).hexdigest() != header["lines_sha256"]:
        raise ValueError("the entries cache changed after it was written")
    bundle_header = Path(bundle_folder) / "bundle.json"
    if hashlib.sha256(bundle_header.read_bytes()).hexdigest() != header["bundle_digest"]:
        raise ValueError("the entries cache belongs to another bundle")
    schema = CatalogueAttributeSchema.from_dict(header["schema"])
    entries, versions = [], []
    for line in body.splitlines():
        identity, version, tier, runnable, text, values = json.loads(line)
        entries.append(IndexEntry(identity, text, values, tier, runnable))
        versions.append(version)
    digest = content_digest(schema.digest, tuple(zip((entry.identity for entry in entries), versions)))
    if len(entries) != header["items"] or digest != header["content_digest"]:
        raise ValueError("the entries cache differs from the content digest it states")
    return {"bundle_digest": header["bundle_digest"], "schema": schema, "content_digest": digest,
            "entries": tuple(entries), "versions": tuple(versions)}


def read_judgements(path):
    """One catalogue_search_judgements/v1 file: its digest and its rows, each with a split."""
    from plan_catalogue_change import read_judgements as read_rows
    digest, rows = read_rows(path)
    for row in rows:
        if row.get("split") not in SPLITS:
            raise ValueError(f"each judged query names its split, one of {SPLITS}")
    return digest, rows


class _PolicyIndex:
    """One built index answered under another ranking policy: the index, pools and filters are shared."""

    def __init__(self, index, policy, *, rank_cache=None, record_into=None):
        self._index, self.policy = index, policy
        self._rank_cache, self._record_into = rank_cache, record_into

    def rank(self, query, *, mode=LEXICAL_MODE, pool=10, eligible=None):
        key = (query, mode, pool, None if eligible is None else len(eligible),
               self.policy.lexical_pool_multiplier, self.policy.lexical_tier_pool_multiplier)
        if self._rank_cache is not None and key in self._rank_cache:
            return self._rank_cache[key]
        result = self._index.rank(query, mode=mode, pool=pool, eligible=eligible)
        if self._record_into is not None:
            self._record_into[key] = result
        return result

    def __getattr__(self, name):
        return getattr(self._index, name)


def band_fusion(share):
    """The `verified_band` alternative: tier precedence only within `share` of the best lexical score."""
    def fuse(pools, allowed, policy, top_n):
        if set(pools) != {LEXICAL_MODE}:
            return ORIGINAL_FUSE(pools, allowed, policy, top_n)
        floor = catalogue_search.lexical_relevance_floor(pools, allowed, policy)
        rows = [(identity, score) for identity, score in pools[LEXICAL_MODE]
                if identity in allowed and (floor is None or score >= floor)]
        if not rows:
            return []
        best = max(score for _identity, score in rows)

        def precedent(row):
            tier = allowed[row[0]].get("library_tier", VERIFIED_TIER) if isinstance(allowed[row[0]], dict) else VERIFIED_TIER
            return tier == VERIFIED_TIER and row[1] >= share * best
        ordered = sorted(enumerate(rows), key=lambda pair: (not precedent(pair[1]), pair[0]))
        offset = policy.reciprocal_rank_offset
        return [(identity, round(1.0 / (offset + rank), 5), [LEXICAL_MODE])
                for rank, (_position, (identity, _score)) in enumerate(ordered[:top_n])]
    return fuse


ORIGINAL_FUSE = catalogue_search.fuse


@contextmanager
def observed_fusion(replacement=None):
    """Record the pools and rows `authorized_hits` fuses last, and optionally fuse them another way.

    `authorized_hits` looks `fuse` up in its own module at call time, so the measurement observes the exact
    candidates the service fuses without a second copy of its candidate logic. The original is restored after.
    """
    seen = []

    def recording(pools, allowed, policy, top_n):
        seen.append((pools, allowed))
        return (replacement or ORIGINAL_FUSE)(pools, allowed, policy, top_n)
    catalogue_search.fuse = recording
    try:
        yield seen
    finally:
        catalogue_search.fuse = ORIGINAL_FUSE


def search(index, tiers, schema, policy, query, *, mode=LEXICAL_MODE, top_n=TOP_N, fusion=None,
           rank_cache=None, record_into=None):
    """The identities the service answers first, the fused pools, and the wall time in milliseconds."""
    view = SimpleNamespace(schema=schema,
                           search_index=lambda: _PolicyIndex(index, policy, rank_cache=rank_cache,
                                                             record_into=record_into))

    def everyone(candidates):
        return {identity: {"library_tier": tiers[identity]} for identity in candidates}
    with observed_fusion(fusion) as seen:
        started = time.perf_counter()
        hits, _rows = authorized_hits(view, {"query": query, "top_n": top_n, "mode": mode}, everyone)
        elapsed = (time.perf_counter() - started) * 1000.0
    return [identity for identity, _score, _modes in hits], (seen[-1] if seen else ({}, {})), elapsed


def _first_rank(order, relevant):
    return next((position for position, identity in enumerate(order, 1) if identity in relevant), 0)


def metrics(rows, answers, listed):
    """Recall at 1, 5 and 10 and mean reciprocal rank over the measurable rows of one group."""
    measurable = [row for row in rows if any(identity in listed for identity in row["relevant"])]
    unanswerable = [row for row in rows if not row["relevant"]]
    ranks = [_first_rank(answers[row["query"]], set(row["relevant"])) for row in measurable]
    count = len(measurable)
    value = {"queries": len(rows), "measurable": count,
             "unanswerable": len(unanswerable),
             "unanswerable_answered": sum(1 for row in unanswerable if answers[row["query"]])}
    for cut in CUT_OFFS:
        value[f"recall_at_{cut}"] = round(sum(1 for rank in ranks if 0 < rank <= cut) / count, 4) if count else None
    value["mean_reciprocal_rank"] = round(sum(1.0 / rank for rank in ranks if rank) / count, 4) if count else None
    return value


def movements(rows, baseline, candidate, listed):
    """Each listed (query, identity) pair: lost and gained from the first ten, moved down and up within it."""
    result = {"lost": [], "gained": [], "moved_down": [], "moved_up": [], "unchanged_in_first_ten": 0}
    for row in rows:
        before, after = baseline[row["query"]], candidate[row["query"]]
        for identity in row["relevant"]:
            if identity not in listed:
                continue
            old = before.index(identity) + 1 if identity in before else None
            new = after.index(identity) + 1 if identity in after else None
            entry = {"query": row["query"], "identity": identity, "split": row["split"], "before": old, "after": new}
            if old and not new:
                result["lost"].append(entry)
            elif new and not old:
                result["gained"].append(entry)
            elif old and new and new > old:
                result["moved_down"].append(entry)
            elif old and new and new < old:
                result["moved_up"].append(entry)
            elif old:
                result["unchanged_in_first_ten"] += 1
    return result


def _timing(values):
    ordered = sorted(values)
    if not ordered:
        return {}
    def at(share):
        return round(ordered[min(len(ordered) - 1, math.ceil(share * len(ordered)) - 1)], 2)
    return {"searches": len(ordered), "p50_ms": round(statistics.median(ordered), 2), "p95_ms": at(0.95),
            "max_ms": round(ordered[-1], 2)}


def verdict(groups, moves):
    """The fixed rule: no regression recall@10 loss, higher regression MRR on both splits, and bank MRR >= 0.60."""
    reasons = []
    for name in ("bank", "regression"):
        if (groups[name]["all"][CANDIDATE]["unanswerable_answered"]
                > groups[name]["all"][BASELINE]["unanswerable_answered"]):
            reasons.append(f"{name} answered more unanswerable queries than the baseline")
    for split in SPLITS:
        before_r10 = groups["regression"][split][BASELINE]["recall_at_10"]
        after_r10 = groups["regression"][split][CANDIDATE]["recall_at_10"]
        if before_r10 is not None and after_r10 is not None and after_r10 < before_r10:
            reasons.append(f"the regression {split} recall at 10 falls ({before_r10} to {after_r10})")
        before = groups["regression"][split][BASELINE]["mean_reciprocal_rank"]
        after = groups["regression"][split][CANDIDATE]["mean_reciprocal_rank"]
        if before is None or after is None or not after > before:
            reasons.append(f"the regression {split} mean reciprocal rank does not rise ({before} to {after})")
        bank_after = groups["bank"][split][CANDIDATE]["mean_reciprocal_rank"]
        if bank_after is None or bank_after < 0.6:
            reasons.append(f"the bank {split} mean reciprocal rank falls below 0.60 ({bank_after})")
    if len(moves["bank"]["lost"]) > 20:
        reasons.append(f"{len(moves['bank']['lost'])} starter-only hits leave the first ten")
    return (KEEP if reasons else SHIP), reasons


def replay_rows(pools, allowed):
    """The lexical rows that can reach a first-ten answer under any policy of this family, in the index's order."""
    kept, per_tier = [], {}
    for identity, score in pools.get(LEXICAL_MODE, []):
        if identity not in allowed:
            continue
        tier = allowed[identity]["library_tier"]
        per_tier[tier] = per_tier.get(tier, 0) + 1
        # The first row holds the best score, so the replayed floor is the same; it is first in its tier too.
        if per_tier[tier] <= REPLAY_ROWS_PER_TIER:
            kept.append([identity, score, tier])
    return kept


def build_index(loaded, *, build_vectors=True):
    """The service's in-memory index of the loaded entries, each identity's tier, and the build seconds."""
    started = time.monotonic()
    index = ReleaseSearchIndex(loaded["entries"], loaded["schema"], build_vectors=build_vectors)
    return index, {entry.identity: entry.tier for entry in loaded["entries"]}, round(time.monotonic() - started, 1)


def compare(loaded, built, judgement_files, *, release_id="", modes=(LEXICAL_MODE,), progress=None):
    """Run every policy over every judged query and return the report and the replay fixture."""
    started = time.monotonic()
    entries, schema = loaded["entries"], loaded["schema"]
    index, tiers, built_seconds = built
    listed = set(tiers)
    policies = {BASELINE: RANKING_POLICIES[BASELINE], CANDIDATE: RANKING_POLICIES[CANDIDATE], **ALTERNATIVES}
    fusions = {name: None for name in policies}
    for name, share in BAND_ALTERNATIVES.items():
        policies[name], fusions[name] = RANKING_POLICIES[BASELINE], band_fusion(share)
    report = {"record_type": REPORT_VERSION, "catalogue_release": release_id or None,
              "content_digest": loaded["content_digest"], "bundle_digest": loaded["bundle_digest"],
              "items": len(entries), "items_by_tier": {tier: sum(1 for value in tiers.values() if value == tier)
                                                        for tier in (VERIFIED_TIER, COMMUNITY_TIER)},
              "index_build_seconds": built_seconds, "top_n": TOP_N, "baseline": BASELINE, "candidate": CANDIDATE,
              "policies": {name: {**asdict(policy), **({"verified_band": BAND_ALTERNATIVES[name]}
                                                       if name in BAND_ALTERNATIVES else {})}
                           for name, policy in policies.items()},
              "judgements": [{"name": name, "path": str(path), "sha256": digest, "rows": len(rows)}
                             for name, (path, digest, rows) in judgement_files.items()],
              "modes": {}}
    replay = {"record_type": REPLAY_VERSION, "catalogue_release": release_id or None,
              "content_digest": loaded["content_digest"], "items": len(entries), "top_n": TOP_N,
              "mode": LEXICAL_MODE, "baseline": BASELINE, "candidate": CANDIDATE,
              "policies": {name: asdict(RANKING_POLICIES[name]) for name in (BASELINE, CANDIDATE)},
              "judgements": {name: digest for name, (_path, digest, _rows) in judgement_files.items()},
              "queries": []}
    for mode in modes:
        answers, timings, captured, shared_rank_cache = {}, {}, {}, {}
        for name, policy in policies.items():
            if mode != LEXICAL_MODE and name not in (BASELINE, CANDIDATE):
                continue
            answers[name], timings[name] = {}, []
            use_cache = shared_rank_cache if name not in (BASELINE, CANDIDATE) else None
            record_into = shared_rank_cache if name == CANDIDATE else None
            for file_name, (_path, _digest, rows) in judgement_files.items():
                for row in rows:
                    order, fused, elapsed = search(index, tiers, schema, policy, row["query"], mode=mode,
                                                   fusion=fusions[name], rank_cache=use_cache,
                                                   record_into=record_into)
                    answers[name][row["query"]] = order
                    timings[name].append(elapsed)
                    if name in (BASELINE, CANDIDATE):
                        captured.setdefault(row["query"], {})[name] = fused
            if progress:
                progress(f"{mode} {name}: {len(timings[name])} searches")
        groups, moves = {}, {}
        for file_name, (_path, _digest, rows) in judgement_files.items():
            groups[file_name] = {}
            for split in (*SPLITS, "all"):
                chosen = [row for row in rows if split == "all" or row["split"] == split]
                groups[file_name][split] = {name: metrics(chosen, answers[name], listed) for name in answers}
            moves[file_name] = {name: movements(rows, answers[BASELINE], answers[name], listed)
                                for name in answers if name != BASELINE}
        candidate_moves = {name: moves[name][CANDIDATE] for name in moves}
        decided, reasons = verdict(groups, candidate_moves) if mode == LEXICAL_MODE else (None, [])
        report["modes"][mode] = {
            "groups": groups,
            "movements": {name: {other: {key: (value if isinstance(value, int) else len(value))
                                         for key, value in moves[name][other].items()}
                                 for other in moves[name]} for name in moves},
            "candidate_movements": candidate_moves,
            "timing_ms": {name: _timing(values) for name, values in timings.items()},
            "answers": {name: answers[name] for name in (BASELINE, CANDIDATE)},
            **({"verdict": decided, "verdict_reasons": reasons} if decided else {})}
        if mode == LEXICAL_MODE:
            replay["verdict"], replay["verdict_reasons"] = decided, reasons
            for file_name, (_path, _digest, rows) in judgement_files.items():
                for row in rows:
                    if not any(identity in listed for identity in row["relevant"]):
                        continue
                    pools, allowed = captured[row["query"]][CANDIDATE]
                    base_pools, _base_allowed = captured[row["query"]][BASELINE]
                    if base_pools != pools:
                        raise ValueError("the baseline and the candidate fused different candidates")
                    entry = {"file": file_name, "query": row["query"], "split": row["split"],
                             "relevant": row["relevant"], "pool": replay_rows(pools, allowed),
                             "answers": {name: answers[name][row["query"]] for name in (BASELINE, CANDIDATE)}}
                    replayed = replay_answers(entry)
                    if replayed != entry["answers"]:
                        raise ValueError(f"the trimmed candidates do not replay the answers for {row['query']!r}")
                    replay["queries"].append(entry)
    report["peak_resident_kib"] = _peak_kib()
    report["seconds"] = round(time.monotonic() - started, 1)
    return report, replay


def replay_answers(entry):
    """The first-ten answers of the baseline and the candidate, fused again from one replay entry's rows."""
    pools = {LEXICAL_MODE: [(identity, score) for identity, score, _tier in entry["pool"]]}
    allowed = {identity: {"library_tier": tier} for identity, _score, tier in entry["pool"]}
    return {name: [identity for identity, _score, _modes in
                   ORIGINAL_FUSE(pools, allowed, RANKING_POLICIES[name], TOP_N)] for name in (BASELINE, CANDIDATE)}


def compare_observed(loaded, built, observed_path):
    """Replay a recorded live search diagnostic with the baseline policy and say which answers match."""
    index, tiers, _seconds = built
    record = json.loads(Path(observed_path).read_text(encoding="utf-8"))
    rows = []
    for searched in record["searches"]:
        mode, top_n = record.get("mode", LEXICAL_MODE), record.get("top_n", TOP_N)
        order, _fused, _elapsed = search(index, tiers, loaded["schema"], RANKING_POLICIES[BASELINE],
                                         searched["query"], mode=mode, top_n=top_n)
        live = [hit["identity"] for hit in searched["hits"]]
        rows.append({"query": searched["query"], "live": live, "offline": order, "same": live == order})
    return {"observed": str(observed_path), "sha256": _sha256(observed_path),
            "same": sum(1 for row in rows if row["same"]), "searches": len(rows), "rows": rows}


def _outside_repository(path):
    path = Path(path)
    if (not path.is_absolute() or path.resolve() == REPOSITORY or REPOSITORY in path.resolve().parents):
        raise ValueError("write comparison outputs to absolute files outside the repository")


def write_new(path, record):
    """Write one record once, to a new file outside this public repository."""
    _outside_repository(path)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(record, stream, indent=1, sort_keys=True, ensure_ascii=False)
        stream.write("\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bundle", type=Path, required=True, help="a complete catalogue bundle folder")
    parser.add_argument("--accept-license", action="append", default=[])
    parser.add_argument("--entries-cache", type=Path, help="read this cache when it exists, otherwise write it")
    parser.add_argument("--release-id", default="", help="the release the bundle published, as recorded")
    parser.add_argument("--prepare-only", action="store_true",
                        help="validate the bundle and write --entries-cache, then stop before any search")
    parser.add_argument("--judgements", type=Path, help="the fixed judged query bank")
    parser.add_argument("--regression", type=Path, help="the regression judgements")
    parser.add_argument("--mode", action="append", choices=(LEXICAL_MODE, HYBRID_MODE), default=[])
    parser.add_argument("--observed", type=Path, help="a recorded live search diagnostic to reproduce")
    parser.add_argument("--report", type=Path, help="a new file outside the repository")
    parser.add_argument("--replay", type=Path, help="a new file outside the repository for the replay fixture")
    options = parser.parse_args(argv)
    if options.prepare_only and options.entries_cache is None:
        parser.error("--prepare-only writes --entries-cache")
    if not options.prepare_only and None in (options.judgements, options.regression, options.report):
        parser.error("a comparison names --judgements, --regression and --report")
    try:
        for path in (options.report, options.replay, options.entries_cache):
            if path is not None:
                _outside_repository(path)
        if options.entries_cache is not None and options.entries_cache.exists():
            loaded = read_entries_cache(options.entries_cache, options.bundle)
        else:
            loaded = load_entries(options.bundle, tuple(options.accept_license) or DEFAULT_LICENSES)
            if options.entries_cache is not None:
                write_entries_cache(options.entries_cache, loaded)
        if options.prepare_only:
            print(json.dumps({"record_type": CACHE_VERSION, "items": len(loaded["entries"]),
                              "content_digest": loaded["content_digest"], "peak_resident_kib": _peak_kib()}))
            return 0
        files = {}
        for name, path in (("bank", options.judgements), ("regression", options.regression)):
            digest, rows = read_judgements(path)
            files[name] = (path, digest, rows)
        modes_to_run = tuple(options.mode) or (LEXICAL_MODE,)
        built = build_index(loaded, build_vectors=HYBRID_MODE in modes_to_run)
        report, replay = compare(loaded, built, files, release_id=options.release_id,
                                 modes=modes_to_run,
                                 progress=lambda line: print(line, file=sys.stderr, flush=True))
        if options.observed is not None:
            report["observed"] = compare_observed(loaded, built, options.observed)
        write_new(options.report, report)
        if options.replay is not None:
            write_new(options.replay, replay)
    except (OSError, ValueError) as error:
        print(json.dumps({"record_type": REPORT_VERSION, "refused": True, "message": str(error)}))
        return 2
    lexical = report["modes"][LEXICAL_MODE]
    print(json.dumps({"record_type": REPORT_VERSION, "verdict": lexical["verdict"],
                      "reasons": lexical["verdict_reasons"], "report": str(options.report),
                      "items": report["items"], "seconds": report["seconds"],
                      "peak_resident_kib": report["peak_resident_kib"]}, sort_keys=True))
    return 0 if lexical["verdict"] == SHIP else 1


if __name__ == "__main__":
    raise SystemExit(main())
