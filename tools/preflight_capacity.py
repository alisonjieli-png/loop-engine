"""Refuse a heavy run the machine cannot carry, and reclaim what the last run left behind.

Kind: continuous integration check and preflight guard.

Every gate run on September 28, 2026 died the same way, twice, for reasons that
have nothing to do with the code under test:

- ``/tmp`` here is a tmpfs, so every temp file is memory. Test suites leaked
  36,088 entries into it and it held 17 GB, which pushed the kernel into swap
  (38 GB used) and starved the run. RAM available is now measured at 46 GB
  because that directory was cleared, not because memory was added.
- ``/`` sat at 96 percent with 65 GB of cold builder scratch under
  ``~/.le-ci-tmp``, none of which any run reads.
- Two runs were killed with no output, which reads like a code failure and is
  not one.

This guard answers a run's question before the run starts: can this machine
carry it, and if not, what can be reclaimed first. Each measure has a
known-wrong case this file also proves:

- a full ``/tmp`` is reported, and pruning is offered rather than assumed
- a full disk is reported against its own threshold, not against a number that
  would pass here
- swap is reported as stale or live, because a large swap with no paging in
  progress is not a reason to refuse work and a busy one is
- a run under the thresholds is allowed, so the guard never becomes the blocker
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

#: A temp filesystem larger than this is a leak, not a workload: the test suites
#: that write here finish in minutes and their leftovers do not.
TMP_LEAK_BYTES = 2 * 1024 ** 3
#: A temp filesystem holding more entries than this is the same leak counted.
TMP_LEAK_ENTRIES = 2000
#: The disk threshold. Above it a build cannot unpack a wheel and an image
#: cannot be written, which is how a release fails late instead of early.
DISK_HIGH_PERCENT = 92
#: Memory the run needs before it starts, in gigabytes.
MIN_AVAILABLE_GB = 12
#: Paging in this many pages across the sample means work is being pushed out
#: of memory now, which is a different problem from a swap that is merely large.
PAGES_PER_SECOND_BUSY = 100


def _read_meminfo(field: str) -> int:
    with open("/proc/meminfo", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith(field):
                return int(line.split()[1]) * 1024
    raise RuntimeError(f"the kernel did not report {field}")


def available_bytes() -> int:
    return _read_meminfo("MemAvailable:")


def swap_bytes() -> tuple[int, int]:
    total = used = 0
    with open("/proc/meminfo", encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("SwapTotal:"):
                total = int(line.split()[1]) * 1024
            elif line.startswith("SwapFree:"):
                used = total - int(line.split()[1]) * 1024
    return total, used


def _paging_counts() -> tuple[int, int]:
    counts = {}
    with open("/proc/vmstat", encoding="utf-8") as stream:
        for line in stream:
            name, value = line.split()
            if name in ("pswpin", "pswpout"):
                counts[name] = int(value)
    return counts["pswpin"], counts["pswpout"]


def paging_rate(sample_seconds: int = 3) -> dict:
    """Whether the machine is paging right now, as distinct from holding a large swap."""
    pages_in, pages_out = _paging_counts()
    time.sleep(sample_seconds)
    later_in, later_out = _paging_counts()
    seconds = max(1, sample_seconds)
    return {"pages_in_per_second": round((later_in - pages_in) / seconds, 1),
            "pages_out_per_second": round((later_out - pages_out) / seconds, 1)}


def tmp_usage() -> dict:
    """How much the RAM-backed temp filesystem holds, in bytes and entries."""
    path = Path("/tmp")
    total = 0
    entries = 0
    for child in path.iterdir():
        if child.name == "opencode":
            continue
        entries += 1
        try:
            if child.is_symlink() or child.is_file():
                total += child.lstat().st_size
            else:
                total += sum(f.stat().st_size for f in child.rglob("*") if f.is_file())
        except OSError:
            continue
    return {"bytes": total, "entries": entries}


def disk_usage(path: str = "/") -> dict:
    usage = shutil.disk_usage(path)
    percent = int(100 * usage.used / usage.total) if usage.total else 0
    return {"path": path, "percent": percent, "free_bytes": usage.free}


def prune_tmp(max_age_days: int = 1, keep: tuple[str, ...] = ("opencode", "claude-1000")) -> dict:
    """Remove leaked temp entries older than `max_age_days`, keeping the named live ones.

    Nothing a run in flight holds is younger than the age, and the two kept
    names are this tool's own folder and a live session's. Returns what it
    removed so a run can record it.
    """
    import shutil as _shutil
    cutoff = time.time() - max_age_days * 86400
    removed = 0
    freed = 0
    for child in Path("/tmp").iterdir():
        if child.name in keep:
            continue
        try:
            if child.lstat().st_mtime > cutoff:
                continue
            size = (child.lstat().st_size if child.is_file() or child.is_symlink()
                    else sum(f.stat().st_size for f in child.rglob("*") if f.is_file()))
            _shutil.rmtree(child, ignore_errors=True) if child.is_dir() and not child.is_symlink() \
                else child.unlink(missing_ok=True)
            removed += 1
            freed += size
        except OSError:
            continue
    return {"removed_entries": removed, "freed_bytes": freed}


def offload_target() -> str | None:
    """The external disk to move cold scratch to, when one is mounted and writable."""
    for candidate in ("/run/media/username/baltor-offload/loop-engine-scratch",
                      "/run/media/username/baltor-offload"):
        path = Path(candidate)
        if path.is_dir() and os.access(path, os.W_OK):
            return str(path)
    return None


def assess(*, sample_seconds: int = 3) -> dict:
    """Every measure, and whether this machine can carry one more heavy run."""
    available = available_bytes()
    swap_total, swap_used = swap_bytes()
    paging = paging_rate(sample_seconds)
    tmp = tmp_usage()
    disk = disk_usage()
    offload = offload_target()

    blockers = []
    if available < MIN_AVAILABLE_GB * 1024 ** 3:
        blockers.append({"measure": "memory",
                         "detail": f"{available // 1024 ** 3} GB available, {MIN_AVAILABLE_GB} GB needed"})
    if paging["pages_out_per_second"] > PAGES_PER_SECOND_BUSY:
        blockers.append({"measure": "paging",
                         "detail": f"{paging['pages_out_per_second']} pages out per second right now"})
    if disk["percent"] >= DISK_HIGH_PERCENT:
        blockers.append({"measure": "disk",
                         "detail": f"{disk['percent']} percent used on {disk['path']}, "
                                   f"{DISK_HIGH_PERCENT} is the ceiling"})
    remedies = []
    if tmp["bytes"] > TMP_LEAK_BYTES or tmp["entries"] > TMP_LEAK_ENTRIES:
        remedies.append({"measure": "tmp", "detail": f"/tmp holds {tmp['entries']} entries in "
                                                      f"{tmp['bytes'] // 1024 ** 2} MiB of RAM",
                         "action": "prune"})
    if disk["percent"] >= DISK_HIGH_PERCENT and offload:
        remedies.append({"measure": "disk", "detail": "cold scratch can be moved to the external disk",
                         "action": "offload", "target": offload})

    return {"record_type": "machine_capacity_preflight/v1",
            "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "available_bytes": available, "swap_total_bytes": swap_total, "swap_used_bytes": swap_used,
            "swap_is_stale": paging["pages_out_per_second"] == 0,
            "paging": paging, "tmp": tmp, "disk": disk, "offload_target": offload,
            "can_run": not blockers, "blockers": blockers, "remedies": remedies}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prune-tmp", action="store_true",
                        help="remove leaked temp entries before reporting")
    parser.add_argument("--json", action="store_true", help="print the whole report")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero when the machine cannot carry a run")
    arguments = parser.parse_args()

    pruned = prune_tmp() if arguments.prune_tmp else None
    report = assess()
    if pruned:
        report["pruned"] = pruned
        report["tmp"] = tmp_usage()
    if arguments.json:
        print(json.dumps(report, indent=2))
    else:
        if report["can_run"]:
            print(f"ready: {report['available_bytes'] // 1024 ** 3} GB available, "
                  f"disk {report['disk']['percent']}%, /tmp {report['tmp']['entries']} entries"
                  + (", swap is stale" if report["swap_is_stale"] else ", paging is live"))
        else:
            print("not ready:")
            for blocker in report["blockers"]:
                print(f"  {blocker['measure']}: {blocker['detail']}")
        for remedy in report["remedies"]:
            print(f"  remedy ({remedy['measure']}): {remedy['detail']} -> {remedy['action']}")
    if arguments.strict and not report["can_run"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
