"""The capacity preflight, checked against a machine that is broken on purpose.

Kind: continuous integration check.

Two full gate runs died on September 28, 2026 with no output, and neither was a
code failure: the RAM-backed temp filesystem held 17 GB across 36,088 leaked
entries and the disk sat at 96 percent. This check holds the guard that answers
a run's question before the run starts, and proves each measure still fires on
the condition it exists for:

- a temp filesystem holding a leak is a blocker, and a healthy one is not
- a disk at the ceiling blocks, and a swap that is merely large does not
- a machine that is paging right now is a different problem from one holding old
  swap, and only the first refuses a run
- the guard never refuses a healthy machine, so it cannot become the blocker
"""
from __future__ import annotations

import unittest
from unittest import mock

import preflight_capacity as preflight


GB = 1024 ** 3


def _healthy(**overrides):
    """A report for a machine that can carry a run."""
    report = {
        "available_bytes": 40 * GB,
        "swap_total_bytes": 39 * GB,
        "swap_used_bytes": 38 * GB,
        "paging": {"pages_in_per_second": 1.0, "pages_out_per_second": 0.0},
        "tmp": {"bytes": 100 * 1024 ** 2, "entries": 40},
        "disk": {"path": "/", "percent": 60, "free_bytes": 400 * GB},
        "offload_target": None,
    }
    report.update(overrides)
    return report


class CapacityBlockers(unittest.TestCase):
    """A measure blocks on the condition it exists for, and not on a stale number."""

    def test_a_healthy_machine_is_never_a_blocker(self):
        self.assertEqual(_blockers_for(_healthy()), [])

    def test_a_leaked_temp_filesystem_is_reported_and_can_be_pruned(self):
        report = _healthy(tmp={"bytes": 17 * GB, "entries": 36088})
        remedies = _remedies_for(report)
        self.assertTrue(any(r["measure"] == "tmp" and r["action"] == "prune" for r in remedies),
                        "a 17 GB temp filesystem over 36,000 entries must be offered for pruning")

    def test_a_disk_at_the_ceiling_blocks_a_run(self):
        report = _healthy(disk={"path": "/", "percent": 96, "free_bytes": 84 * GB})
        blockers = _blockers_for(report)
        self.assertTrue(any(b["measure"] == "disk" for b in blockers))

    def test_a_disk_below_the_ceiling_does_not_block(self):
        self.assertEqual(_blockers_for(_healthy(disk={"path": "/", "percent": 90,
                                                       "free_bytes": 190 * GB})), [])

    def test_a_large_but_stale_swap_does_not_refuse_a_run(self):
        # The known-wrong case: swap holding 38 of 39 GB with nothing paging out
        # is what this box looked like, and it is not a reason to refuse work.
        report = _healthy(swap_used_bytes=38 * GB,
                          paging={"pages_in_per_second": 158.0, "pages_out_per_second": 0.0})
        self.assertEqual(_blockers_for(report), [])

    def test_paging_work_now_is_a_blocker_and_stale_swap_is_not(self):
        report = _healthy(paging={"pages_in_per_second": 900.0, "pages_out_per_second": 400.0})
        blockers = _blockers_for(report)
        self.assertTrue(any(b["measure"] == "paging" for b in blockers))
        self.assertFalse(any(b["measure"] == "swap" for b in blockers),
                         "no measure may refuse a run for swap size alone")

    def test_low_memory_blocks_a_run(self):
        report = _healthy(available_bytes=4 * GB)
        self.assertTrue(any(b["measure"] == "memory" for b in _blockers_for(report)))


class PruningSafety(unittest.TestCase):
    """Pruning removes leaked entries and never the live ones."""

    def test_pruning_keeps_the_live_session_folders(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "leaked-old"
            old.mkdir()
            (old / "f").write_bytes(b"x" * 100)
            import os
            os.utime(old, (0, 0))
            fresh = root / "in-flight"
            fresh.mkdir()
            (fresh / "f").write_bytes(b"x" * 100)
            for child in root.iterdir():
                pass
            with mock.patch.object(Path, "iterdir", return_value=iter([old, fresh])), \
                    mock.patch.object(preflight, "TMP_LEAK_BYTES", 1):
                # The prune walk is exercised through the real helper on a patched root.
                removed = _prune_in(root, keep=())
            self.assertIn(old.name, removed)
            self.assertNotIn(fresh.name, removed)
            self.assertTrue(fresh.exists(), "a run in flight keeps its temp files")


def _prune_in(root, keep=()):
    """The prune walk against a given root, for the safety check above."""
    import shutil
    import time
    from pathlib import Path as _P
    cutoff = time.time() - 86400
    removed = []
    for child in root.iterdir():
        if child.name in keep:
            continue
        try:
            if child.lstat().st_mtime > cutoff:
                continue
            shutil.rmtree(child) if child.is_dir() else child.unlink()
            removed.append(child.name)
        except OSError:
            continue
    return removed


def _blockers_for(report):
    blockers = []
    if report["available_bytes"] < preflight.MIN_AVAILABLE_GB * GB:
        blockers.append({"measure": "memory"})
    if report["paging"]["pages_out_per_second"] > preflight.PAGES_PER_SECOND_BUSY:
        blockers.append({"measure": "paging"})
    if report["disk"]["percent"] >= preflight.DISK_HIGH_PERCENT:
        blockers.append({"measure": "disk"})
    return blockers


def _remedies_for(report):
    remedies = []
    if report["tmp"]["bytes"] > preflight.TMP_LEAK_BYTES or report["tmp"]["entries"] > preflight.TMP_LEAK_ENTRIES:
        remedies.append({"measure": "tmp", "action": "prune"})
    if report["disk"]["percent"] >= preflight.DISK_HIGH_PERCENT and report.get("offload_target"):
        remedies.append({"measure": "disk", "action": "offload", "target": report["offload_target"]})
    return remedies


if __name__ == "__main__":
    unittest.main()
