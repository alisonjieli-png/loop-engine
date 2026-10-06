"""Copy catalogue bodies from the service volume to the object store engine, through the body store edge.

Kind: operator tool for the day the R2 body engine of the `catalogue_body_store` slot is adopted
(`src/loop_engine/core/service_runtime/service_engine_body_store.py`). It reads every body from a volume body store
(`VolumeBodyStore`, which checks size and SHA-256 on every read) and writes it with the destination engine's own
`put(payload, expected_digest=...)`, so each object is created once under its digest, verified by the store's
write-once rule and read back. Nothing here bypasses the edge.

```text
Mirror
├── source        a volume body store root, every object under sha256/<first two>/<digest>, or only the files
│                 one pinned complete native catalogue bundle lists (version 1 or segmented version 2)
├── destination   the engine a catalogue_body_store_engine/v1 record names (the same record the host file
│                 will carry), opened for writing only with --authorize-object-store-writes
├── inventory     one ListObjectsV2 listing per two-hex-digit prefix, so a rerun skips what is stored and
│                 memory holds one prefix's keys at a time; a write run verifies existing bytes too;
│                 --inventory none contacts nothing in a dry run
├── copy          the missing bodies of one prefix by at most --workers threads (4 by default), each prefix
│                 finished before the next, so the reported last digest is a safe point to resume from
├── resume        objects go in digest order; --start-after DIGEST continues after the last one reported,
│                 and never advances past a failed object; a rerun without it verifies stored objects again
└── report        catalogue_body_mirror_report/v1: objects, bytes, already present, planned or written,
                  refusals by reason, R2 operations by class and their list price
```

R2 list prices read October 5, 2026 (https://developers.cloudflare.com/r2/pricing/, last updated October 1, 2026):
Class A (PutObject, ListObjects) $4.50 per million, Class B (GetObject, HeadObject) $0.36 per million, with one
million Class A and ten million Class B free each month, and storage $0.015 per GB-month after 10 GB-month free.
A written object costs one PUT and one GET (the read back), an object found by its 412 one PUT and one GET, and
each listing page one Class A operation.

Usage:
  mirror_catalogue_bodies.py --source-root /data/catalogue-bodies --body-store-record record.json
                             [--bundle FOLDER --bundle-digest SHA256 --accept-license LABEL]
                             [--start-after DIGEST] [--limit N] [--inventory list|none]
                             [--workers N] [--authorize-object-store-writes] [--report FILE]

Without --authorize-object-store-writes it is a dry run: it writes nothing and reports what it would write. The
record names credentials only as env: references; the report never holds a credential.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from itertools import groupby
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from loop_engine.core.service_runtime.catalogue_packages import VolumeBodyStore  # noqa: E402
from loop_engine.core.service_runtime.records import ServiceRuntimeError  # noqa: E402

REPORT_RECORD_TYPE = "catalogue_body_mirror_report/v1"
PRICES = {"class_a_per_million_usd": 4.50, "class_b_per_million_usd": 0.36, "storage_per_gb_month_usd": 0.015,
          "free_class_a_per_month": 1_000_000, "free_class_b_per_month": 10_000_000, "free_gb_month": 10,
          "source": "R2 pricing page, last updated October 1, 2026 (named in this tool's docstring)",
          "read_on": "2026-10-05"}
#: R2 operation classes of the requests the engine counts.
OPERATION_CLASS = {"PUT": "class_a", "LIST": "class_a", "GET": "class_b"}
_DIGEST = re.compile(r"[0-9a-f]{64}")
_PREFIX = re.compile(r"[0-9a-f]{2}")
#: Copies in flight at once. R2 allows one write a second to the same key; keys here are distinct digests.
MAXIMUM_WORKERS = 32


def volume_objects(root):
    """Every (digest, size) of a volume body store, in digest order, without following a link or reading a body."""
    base = Path(root) / "sha256"
    found = []
    if not base.is_dir() or base.is_symlink():
        return found
    for prefix in sorted(entry.name for entry in os.scandir(base)
                         if _PREFIX.fullmatch(entry.name) and entry.is_dir(follow_symlinks=False)):
        for entry in os.scandir(base / prefix):
            if _DIGEST.fullmatch(entry.name) and entry.name[:2] == prefix and entry.is_file(follow_symlinks=False):
                found.append((entry.name, entry.stat(follow_symlinks=False).st_size))
    return sorted(found)


def bundle_objects(folder, *, expected_digest, accepted_licenses=("MIT",)):
    """Exact file membership of a pinned complete v1 or segmented v2 bundle.

    The canonical readers validate rights, approvals, records and hashes.
    Segmented metadata is streamed; missing carried membership is refused
    before any destination operation, never treated as an empty delta.
    """
    from loop_engine.core.service_runtime.catalogue_segments import (ContentDigest, SegmentedBundle,
                                                                     read_any_bundle, segment_entries)
    from loop_engine.core.service_runtime.http_entrypoint import HostFamilyPolicy, HostLicensePolicy
    if not isinstance(expected_digest, str) or not _DIGEST.fullmatch(expected_digest):
        raise ValueError("bundle scope needs its exact header digest")
    bundle = read_any_bundle(Path(folder), license_policy=HostLicensePolicy(tuple(accepted_licenses)),
                             family_policy=HostFamilyPolicy(), verify_blobs=False)
    if bundle.digest != expected_digest:
        raise ValueError("bundle header differs from the selected digest")

    def entries():
        if not isinstance(bundle, SegmentedBundle):
            yield from bundle.items
            return
        content = ContentDigest(bundle.schema.digest)
        previous = None
        for ref in bundle.segments:
            document = bundle.carried_segment(ref.digest)
            if document is None:
                raise ValueError("mirror scope needs complete carried segments")
            pairs = segment_entries(document, ref.digest)
            if pairs[0][0] != ref.first or len(pairs) != ref.count:
                raise ValueError("a carried segment differs from its release membership")
            for identity, version in pairs:
                if previous is not None and identity <= previous:
                    raise ValueError("mirror scope segments overlap")
                entry = bundle.carried_item(version)
                if entry is None or entry.identity != identity:
                    raise ValueError("mirror scope needs every exact carried item version")
                content.add(identity, version)
                previous = identity
                yield entry
        if content.count != bundle.release_items or content.hexdigest() != bundle.content_digest:
            raise ValueError("mirror membership differs from the pinned release")

    found = {}
    for item in entries():
        for entry in item.package.files:
            if found.setdefault(entry.digest, entry.size_bytes) != entry.size_bytes:
                raise ValueError("one digest is listed with two sizes")
    return sorted(found.items())


def _inventory(destination, prefix):
    """The stored (key -> size) under one two-digit prefix of the destination."""
    return dict(destination.stored_objects(f"sha256/{prefix}/"))


def _copy(source, destination, digest, size):
    """Read one body verified from the source and create it once in the destination.

    Returns (created, refusal): (True, None) when this call created the object, (False, None) when the store
    already held the same bytes, and (None, code) when the source or the destination refused."""
    try:
        payload = source.read(digest, size)
        return destination.put(payload, expected_digest=digest, durable=False)["written"], None
    except ServiceRuntimeError as error:
        return None, error.code


def _verify_existing(destination, digest, size):
    """A matching inventory length does not prove bytes; verify through the same reader."""
    try:
        destination.read(digest, size)
        return False, None
    except ServiceRuntimeError as error:
        return None, error.code


def mirror(source, destination, objects, *, write, inventory=True, start_after="", limit=None, workers=1,
           clock=time.monotonic):
    """Copy `objects` from `source` to `destination` and return the report fields that do not name either.

    Objects go in digest order, one two-digit prefix at a time: the prefix is listed once, then its missing
    bodies are copied or verified by at most `workers` threads. The write-mode
    `last_digest` never advances beyond a refusal; later successful copies are
    retained but cannot hide a gap from a resumed run.
    """
    if type(workers) is not int or not 1 <= workers <= MAXIMUM_WORKERS:
        raise ValueError(f"workers is a whole number from 1 to {MAXIMUM_WORKERS}")
    if type(write) is not bool or type(inventory) is not bool:
        raise ValueError("write and inventory authority are explicit Booleans")
    if start_after and (not isinstance(start_after, str) or not _DIGEST.fullmatch(start_after)):
        raise ValueError("the resume point is an exact digest")
    if limit is not None and (type(limit) is not int or limit < 1):
        raise ValueError("the limit is a positive whole number")
    started = clock()
    before = dict(destination.operation_counts())
    counts = {"objects": 0, "bytes": 0, "already_present": 0, "planned": 0, "planned_bytes": 0, "written": 0,
              "written_bytes": 0}
    refused, last, chosen, cursor_blocked = {}, start_after, [], False
    for digest, size in sorted(objects):
        if start_after and digest <= start_after:
            continue
        if limit is not None and len(chosen) >= limit:
            break
        chosen.append((digest, size))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mirror") as pool:
        for prefix, group in groupby(chosen, key=lambda row: row[0][:2]):
            rows = list(group)
            held = _inventory(destination, prefix) if inventory else {}
            jobs = []
            for digest, size in rows:
                counts["objects"] += 1
                counts["bytes"] += size
                if held.get(VolumeBodyStore.object_key(digest)) == size:
                    if write:
                        jobs.append((digest, size, True))
                    else:
                        counts["already_present"] += 1
                elif not write:
                    counts["planned"] += 1
                    counts["planned_bytes"] += size
                else:
                    jobs.append((digest, size, False))
            outcomes = pool.map(lambda row: _verify_existing(destination, row[0], row[1]) if row[2]
                                else _copy(source, destination, row[0], row[1]), jobs)
            for (digest, size, _held), (created, refusal) in zip(jobs, outcomes):
                if refusal is not None:
                    refused[refusal] = refused.get(refusal, 0) + 1
                    cursor_blocked = True
                elif created:
                    counts["written"] += 1
                    counts["written_bytes"] += size
                else:
                    counts["already_present"] += 1
                if not cursor_blocked:
                    last = digest
            if not write:
                last = rows[-1][0]
    if write:
        destination.sync()
    after = destination.operation_counts()
    by_kind = {kind: after.get(kind, 0) - before.get(kind, 0) for kind in sorted(set(after) | set(before))}
    operations = {"class_a": 0, "class_b": 0}
    for kind, amount in by_kind.items():
        operations[OPERATION_CLASS.get(kind, "class_a")] += amount
    return {**counts, "refused_by_reason": dict(sorted(refused.items())), "last_digest": last, "workers": workers,
            "existing_bytes_verified": write, "verified_objects": counts["written"] + counts["already_present"] if write else 0,
            "resume_cursor_blocked_by_failure": cursor_blocked,
            "operations": {**operations, "by_kind": by_kind},
            "list_price_usd": _price(operations["class_a"], operations["class_b"]),
            "a_write_run_would_send": {"class_a": counts["planned"], "class_b": counts["planned"],
                                       "list_price_usd": _price(counts["planned"], counts["planned"])["total"]},
            "storage_estimate": _storage(counts["bytes"]),
            "seconds": round(clock() - started, 3)}


def _price(class_a, class_b):
    a = class_a * PRICES["class_a_per_million_usd"] / 1_000_000
    b = class_b * PRICES["class_b_per_million_usd"] / 1_000_000
    return {"class_a": round(a, 6), "class_b": round(b, 6), "total": round(a + b, 6),
            "allowance_basis": "This run alone; other account usage and provider billing rounding are not included.",
            "inside_the_monthly_free_operations": (class_a <= PRICES["free_class_a_per_month"]
                                                   and class_b <= PRICES["free_class_b_per_month"])}


def _storage(size):
    gigabytes = size / 1_000_000_000
    return {"gb": round(gigabytes, 6), "list_price_usd_per_month": round(gigabytes * PRICES["storage_per_gb_month_usd"], 6),
            "inside_the_monthly_free_storage": gigabytes <= PRICES["free_gb_month"]}


def _record(path):
    with open(path, encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("the body store record is one JSON object")
    return value


def main(argv=None, *, secret_resolver=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--source-root", required=True, help="the volume body store root, such as /data/catalogue-bodies")
    parser.add_argument("--body-store-record", required=True, help="a file holding the catalogue_body_store_engine/v1 record")
    parser.add_argument("--bundle", help="copy only the files in this complete native bundle")
    parser.add_argument("--bundle-digest", help="exact SHA-256 of the selected bundle header")
    parser.add_argument("--accept-license", action="append", default=[], help="exact accepted licence label for bundle scope")
    parser.add_argument("--start-after", default="", help="continue after this digest")
    parser.add_argument("--limit", type=int, help="consider at most this many objects")
    parser.add_argument("--inventory", choices=("list", "none"), default="list",
                        help="list the destination per prefix first (list), or assume it holds nothing (none)")
    parser.add_argument("--authorize-object-store-writes", action="store_true",
                        help="write to the object store; without it the run is a dry run")
    parser.add_argument("--workers", type=int, default=4, help=f"copies in flight at once, 1 to {MAXIMUM_WORKERS}")
    parser.add_argument("--report", help="also write the report to this file")
    args = parser.parse_args(argv)
    if bool(args.bundle) != bool(args.bundle_digest):
        parser.error("--bundle and --bundle-digest are required together")
    from loop_engine.core.service_runtime.service_engine_body_store import (OBJECT_STORAGE_ENGINE, open_body_store,
                                                                           read_host_record)
    if args.start_after and not _DIGEST.fullmatch(args.start_after):
        parser.error("--start-after names a digest")
    if args.limit is not None and args.limit < 1:
        parser.error("--limit is a positive number")
    if not 1 <= args.workers <= MAXIMUM_WORKERS:
        parser.error(f"--workers is from 1 to {MAXIMUM_WORKERS}")
    record = read_host_record(_record(args.body_store_record))
    if record["engine"] != OBJECT_STORAGE_ENGINE:
        parser.error("the destination record names the object store engine")
    write = bool(args.authorize_object_store_writes)
    if write and args.inventory == "none":
        parser.error("a write run lists the destination first; --inventory none is for dry runs")
    destination = open_body_store(record, write=write, secret_resolver=secret_resolver)
    source = VolumeBodyStore(str(Path(args.source_root).resolve()))
    objects = (bundle_objects(args.bundle, expected_digest=args.bundle_digest,
                              accepted_licenses=tuple(args.accept_license) or ("MIT",))
               if args.bundle else volume_objects(source.root))
    try:
        result = mirror(source, destination, objects, write=write, inventory=args.inventory == "list",
                        start_after=args.start_after, limit=args.limit, workers=args.workers)
    finally:
        destination.close()
    report = {"record_type": REPORT_RECORD_TYPE, "mode": "write" if write else "dry_run",
              "source": {"engine": "service_volume_files", "root": str(source.root),
                         "scope": "bundle" if args.bundle else "every_object",
                         "bundle": str(Path(args.bundle).resolve()) if args.bundle else None,
                         "objects_listed": len(objects), "bytes_listed": sum(size for _digest, size in objects)},
              "destination": {"engine": record["engine"], "bucket": record["bucket"],
                              "origin": destination.location.origin},
              "inventory": args.inventory, "start_after": args.start_after or None, "limit": args.limit,
              **result, "prices": PRICES}
    text = json.dumps(report, indent=2, sort_keys=True)
    print(text)
    if args.report:
        Path(args.report).write_text(text + "\n", encoding="utf-8")
    return 1 if result["refused_by_reason"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
