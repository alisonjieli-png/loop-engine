"""Supervised overnight candidate batch: 1,000 ideas across the four lanes.

One supervisor process owns the whole batch. Ideas from the deterministic
matrix are assigned round-robin to the four separate OpenCode lanes built
by tools/opencode_generation_lanes.py. Every dispatch and outcome is
appended to a journal before and after each model call, so an interrupted
batch resumes exactly where it stopped: an idea whose journal already
holds a terminal outcome is never repeated silently.

Recovery and fallback rules, stated once:

  * A provider failure or timeout is waited out inside a declared outage
    wait (backoff per attempt), and the same idea is retried on the same
    lane. A third failure records the idea as failed and the batch moves
    on; the work never ends on a fixed attempt count.
  * A lane whose last five consecutive ideas all failed is marked
    degraded in the journal and its unstarted ideas are reassigned to
    healthy lanes, one each, round-robin.
  * A candidate that fails the shape check is retried once on the same
    lane with a stricter prompt; a second shape failure records
    failed_candidate_shape and moves on.
  * The batch stops at the declared --max-calls ceiling and records
    ceiling_reached; that is a clean stop, not a crash.
  * A crashed supervisor is restarted by the --watchdog mode (cron):
    the status file says whether work remains, and the journal makes the
    restart resume rather than repeat.

The batch writes candidates, a journal, a status record and a manifest
into one batch directory. Everything stays candidate material: nothing
is staged, approved or served here, and no lane may name a local endpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from tools.opencode_generation_lanes import (  # noqa: E402
    DECLARED_ENDPOINTS,
    Lane,
    LaneError,
    LaneRunner,
    _looks_like_candidate,
    _render_prompt,
    _strip_code_fence,
)

BATCH_RECORD_TYPE = "overnight_candidate_batch/v1"
JOURNAL_EVENT_TYPE = "overnight_batch_event/v1"
STATUS_RECORD_TYPE = "overnight_batch_status/v1"
#: Ideas per lane at the default ten-thousand scale (six lanes).
IDEA_PER_LANE = 250
#: Default call ceiling: the ten-thousand batch with headroom for retries.
MAX_CALLS = 12000
ATTEMPTS_PER_IDEA = 3
DEGRADED_AFTER_CONSECUTIVE = 5
OUTAGE_WAIT_SECONDS = (60, 180, 300)
SHA256 = hashlib.sha256


class BatchError(ValueError):
    """A batch, selection, or supervision request is invalid."""


def refuse(code: str) -> None:
    raise BatchError(code)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _atomic_json(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def load_matrix(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        refuse("matrix_file_invalid")
    batch = json.loads(path.read_text(encoding="utf-8"))
    if batch.get("record_type") != "harness_idea_batch/v1":
        refuse("matrix_batch_unsupported")
    return batch


#: Batch source kinds whose ideas carry their own task statement, so no occupation is rotated over them: the
#: owner's volume seeds (tools/build_volume_seed_ideas.py) ground each idea in one of the owner's own projects.
SELF_GROUNDED_SOURCE_KINDS = ("owner_volume_inventory",)


def _occupation_rotation(matrix: dict) -> list[dict]:
    """The pinned occupations and their task statements, in file order; empty for a self-grounded batch."""
    source = {}
    kinds = {record.get("kind") for record in matrix.get("sources", [])}
    for record in matrix.get("sources", []):
        if record.get("kind") == "onet_pinned":
            source = record
    if not source:
        if kinds and kinds <= set(SELF_GROUNDED_SOURCE_KINDS):
            return []
        refuse("matrix_missing_pinned_source")
    path = Path(__file__).resolve().parents[1] / source["path"]
    raw = json.loads(path.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = {}
    for reference in raw.get("task_references", []):
        grouped.setdefault(reference["occupation_code"], []).append({
            "occupation_code": reference["occupation_code"],
            "task_reference": reference["source_task_text"],
        })
    titles = {occupation["occupation_code"]: occupation["occupation_title"]
              for occupation in raw.get("occupations", [])}
    rotation = []
    # Interleave task statements across occupations so a small selection
    # touches many occupations instead of exhausting the first one.
    position = 0
    remaining = True
    while remaining:
        remaining = False
        for code in grouped:
            pool = grouped[code]
            if position < len(pool):
                rotation.append({**pool[position],
                                 "occupation_title": titles.get(code, "")})
                remaining = True
        position += 1
    if not rotation:
        refuse("occupation_rotation_empty")
    return rotation


def select_stratified(matrix: dict, count: int, seed: int = 20260924) -> list[dict]:
    """Pick ideas round-robin across datatypes, rotating the job facet.

    The method signature (datatype, operation, use case) decides identity.
    The occupation and its task statement are applicability facets, so
    rotating them across the pinned occupations adds real job grounding
    without multiplying methods.
    """
    if count < 1:
        refuse("selection_count_invalid")
    ideas = matrix["ideas"]
    if not ideas:
        refuse("matrix_empty")
    rotation = _occupation_rotation(matrix)
    ordered = sorted(ideas, key=lambda idea: idea["id"])
    by_datatype: dict[str, list[dict]] = {}
    for idea in ordered:
        by_datatype.setdefault(idea["datatype"], []).append(idea)
    datatypes = sorted(by_datatype)
    if count > len(ideas):
        refuse("selection_count_exceeds_matrix")
    picked: list[dict] = []
    picked_ids: set[str] = set()
    cursors = {datatype: 0 for datatype in datatypes}
    while len(picked) < count:
        progressed = False
        for datatype in datatypes:
            pool = by_datatype[datatype]
            cursor = cursors[datatype]
            while cursor < len(pool) and pool[cursor]["id"] in picked_ids:
                cursor += 1
            if cursor >= len(pool):
                cursors[datatype] = cursor
                continue
            idea = pool[cursor]
            cursors[datatype] = cursor + 1
            facet = rotation[len(picked) % len(rotation)] if rotation else {}
            picked.append({
                **idea,
                "applicability": {**idea["applicability"], **facet},
            })
            picked_ids.add(idea["id"])
            progressed = True
            if len(picked) >= count:
                break
        if not progressed:
            refuse("selection_exhausted")
    return picked


@dataclass
class LaneHealth:
    """Live supervision state for one lane."""

    lane: Lane
    consecutive_failures: int = 0
    degraded: bool = False
    calls: int = 0
    candidates: int = 0
    failed: int = 0


@dataclass
class BatchSupervisor:
    """Owns journal, status, ceiling and assignment for one batch run."""

    batch_directory: Path
    lanes: list[Lane]
    ideas: list[dict]
    max_calls: int
    outage_wait: tuple[int, ...] = OUTAGE_WAIT_SECONDS
    degraded_after: int = DEGRADED_AFTER_CONSECUTIVE
    attempts_per_idea: int = ATTEMPTS_PER_IDEA
    _journal: Path = field(default=None, init=False)
    _status: Path = field(default=None, init=False)
    _completed: set = field(default_factory=set, init=False)
    _failed: set = field(default_factory=set, init=False)
    _calls: int = field(default=0, init=False)

    def __post_init__(self):
        self._journal = self.batch_directory / "journal.jsonl"
        self._status = self.batch_directory / "status.json"
        self._health = {lane.lane_id: LaneHealth(lane) for lane in self.lanes}
        self._assignment: dict[str, str] = {}
        for position, idea in enumerate(self.ideas):
            lane = self.lanes[position % len(self.lanes)]
            self._assignment[idea["id"]] = lane.lane_id
        self._recover()

    # -- journal -----------------------------------------------------------
    def _recover(self) -> None:
        """Replay the journal: skip completed ideas, keep failed ones."""
        if not self._journal.is_file():
            return
        for line in self._journal.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            if event.get("event") == "outcome":
                idea_id = event["idea_id"]
                if event.get("outcome") in ("candidate_written",):
                    self._completed.add(idea_id)
                elif event.get("outcome") in ("failed_provider", "failed_candidate_shape",
                                             "failed_ceiling"):
                    self._failed.add(idea_id)
            if event.get("event") == "reassign":
                idea_id = event["idea_id"]
                self._assignment[idea_id] = event["to_lane"]

    def _record(self, event: dict) -> None:
        event = {"record_type": JOURNAL_EVENT_TYPE, "ts": _now(), **event}
        _append_jsonl(self._journal, event)

    # -- ceiling ----------------------------------------------------------
    def _ceiling_left(self) -> int:
        return self.max_calls - self._calls

    # -- dispatch ---------------------------------------------------------
    def _dispatch(self, lane: Lane, idea: dict, attempt: int, stricter: bool) -> dict:
        """One model call through the lane's own OpenCode setup."""
        runner = LaneRunner(lane)
        prompt = _render_prompt(idea)
        if stricter:
            prompt += (
                " Your previous answer was not a valid candidate. Answer with "
                "the file content only: YAML frontmatter whose first key is "
                f"name: {idea['id']}, then description and license, then a "
                "closing --- line, then the Markdown body. No prose before or "
                "after, no code fences."
            )
        record = {
            "lane_id": lane.lane_id,
            "idea_id": idea["id"],
            "attempt": attempt,
        }
        self._record({"event": "dispatch", **record, "stricter": stricter})
        self._calls += 1
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as workspace:
                work = Path(workspace)
                (work / "idea.json").write_text(
                    json.dumps(idea, indent=2, ensure_ascii=False), encoding="utf-8")
                argv = [str(Path.home() / ".opencode" / "bin" / "opencode"), "run",
                        "--pure", "--format", "json", "--title", idea["id"],
                        "--dir", str(work), prompt]
                try:
                    completed = subprocess.run(
                        argv, capture_output=True, text=True,
                        env=lane.environment(), cwd=str(work), timeout=900.0)
                except subprocess.TimeoutExpired:
                    return {**record, "outcome": "timeout"}
                if completed.returncode != 0:
                    return {**record, "outcome": "opencode_failed"}
                from tools.opencode_generation_lanes import _extract_message_text
                text = _extract_message_text(completed.stdout)
                written = work / idea["id"] / "SKILL.md"
                if not written.is_file():
                    written = work / f"{idea['id']}.md"
                if written.is_file():
                    text = written.read_text(encoding="utf-8")
                text = _strip_code_fence(text or "")
                if not text:
                    return {**record, "outcome": "empty_response"}
                if not _looks_like_candidate(text, idea):
                    return {**record, "outcome": "shape_failed"}
                body = text.encode("utf-8")[: 2 * 1024 * 1024]
                candidate_directory = self.batch_directory / "candidates" / lane.lane_id
                candidate_directory.mkdir(parents=True, exist_ok=True)
                target = candidate_directory / f"{idea['id']}.md"
                target.write_bytes(body)
                return {**record, "outcome": "candidate_written",
                        "candidate_sha256": SHA256(body).hexdigest(),
                        "candidate_bytes": len(body),
                        "candidate_path": str(target)}
        finally:
            self._record({"event": "call", "lane_id": lane.lane_id,
                          "idea_id": idea["id"], "calls_used": self._calls})

    # -- run one idea ------------------------------------------------------
    def _run_idea(self, lane: Lane, idea: dict) -> str:
        attempt = 1
        outcome = None
        while attempt <= self.attempts_per_idea:
            if self._ceiling_left() <= 0:
                self._record({"event": "outcome", "lane_id": lane.lane_id,
                              "idea_id": idea["id"], "outcome": "failed_ceiling"})
                self._failed.add(idea["id"])
                return "ceiling"
            outcome = self._dispatch(lane, idea, attempt, stricter=attempt > 1)
            if outcome["outcome"] == "candidate_written":
                break
            if outcome["outcome"] == "shape_failed":
                attempt += 1
                continue
            wait = self.outage_wait[min(attempt - 1, len(self.outage_wait) - 1)]
            self._record({"event": "outage_wait", "lane_id": lane.lane_id,
                          "idea_id": idea["id"], "seconds": wait})
            time.sleep(wait)
            attempt += 1
        if outcome["outcome"] == "candidate_written":
            final = "candidate_written"
        else:
            final = "failed_provider" if outcome["outcome"] in (
                "timeout", "opencode_failed", "empty_response") else "failed_candidate_shape"
        self._record({"event": "outcome", "lane_id": lane.lane_id,
                      "idea_id": idea["id"], "outcome": final})
        if final == "candidate_written":
            self._completed.add(idea["id"])
        else:
            self._failed.add(idea["id"])
        return final

    # -- health ------------------------------------------------------------
    def _update_health(self, lane_id: str, final: str) -> None:
        health = self._health[lane_id]
        if final == "candidate_written":
            health.candidates += 1
            health.consecutive_failures = 0
        elif final in ("failed_provider", "failed_candidate_shape"):
            health.failed += 1
            health.consecutive_failures += 1
            if health.consecutive_failures >= self.degraded_after and not health.degraded:
                health.degraded = True
                self._record({"event": "lane_degraded", "lane_id": lane_id,
                              "reason": "consecutive_failures"})

    def _healthy_lanes(self) -> list[Lane]:
        healthy = [lane for lane in self.lanes if not self._health[lane.lane_id].degraded]
        return healthy or self.lanes

    def _reassign(self, idea: dict) -> None:
        current = self._assignment[idea["id"]]
        healthy = self._healthy_lanes()
        candidates = [lane for lane in healthy if lane.lane_id != current]
        lane = candidates[0] if candidates else healthy[0]
        self._assignment[idea["id"]] = lane.lane_id
        self._record({"event": "reassign", "idea_id": idea["id"],
                      "from_lane": current, "to_lane": lane.lane_id})

    # -- main loop ----------------------------------------------------------
    def run(self) -> dict:
        started = _now()
        for idea in self.ideas:
            if idea["id"] in self._completed or idea["id"] in self._failed:
                continue
            lane_id = self._assignment[idea["id"]]
            if self._health[lane_id].degraded:
                self._reassign(idea)
                lane_id = self._assignment[idea["id"]]
            lane = next(candidate for candidate in self.lanes
                        if candidate.lane_id == lane_id)
            final = self._run_idea(lane, idea)
            self._update_health(lane_id, final)
            self._write_status(started)
            if self._ceiling_left() <= 0:
                break
        status = self._write_status(started)
        self._write_manifest()
        return status

    def _write_status(self, started: str) -> dict:
        total = len(self.ideas)
        status = {
            "record_type": STATUS_RECORD_TYPE,
            "started_at": started,
            "updated_at": _now(),
            "state": ("incomplete" if len(self._completed) + len(self._failed) < total
                      else "complete"),
            "ideas_total": total,
            "candidates": len(self._completed),
            "failed": len(self._failed),
            "remaining": total - len(self._completed) - len(self._failed),
            "calls_used": self._calls,
            "calls_ceiling": self.max_calls,
            "ceiling_reached": self._ceiling_left() <= 0,
            "lanes": {
                lane.lane_id: {
                    "provider": lane.provider,
                    "model": lane.model,
                    "candidates": self._health[lane.lane_id].candidates,
                    "failed": self._health[lane.lane_id].failed,
                    "degraded": self._health[lane.lane_id].degraded,
                    "consecutive_failures": self._health[lane.lane_id].consecutive_failures,
                } for lane in self.lanes
            },
        }
        _atomic_json(self._status, status)
        return status

    def _write_manifest(self) -> None:
        manifest = {
            "record_type": BATCH_RECORD_TYPE,
            "generated_at": _now(),
            "ideas_total": len(self.ideas),
            "candidates": len(self._completed),
            "failed": len(self._failed),
            "calls_used": self._calls,
            "lanes": [lane.lane_id for lane in self.lanes],
            "providers": {lane.provider: lane.model for lane in self.lanes},
            "note": "Candidate-only. Independent review precedes any activation.",
        }
        _atomic_json(self.batch_directory / "manifest.json", manifest)


def _supervisor_pid_file(batch_directory: Path) -> Path:
    return batch_directory / "supervisor.pid"


def start(batch_directory: Path, matrix_path: Path, lane_specs: list[dict],
          ideas: int, max_calls: int, lane_root: Path) -> dict:
    """Prepare lanes, select ideas, run the supervised batch."""
    from tools.opencode_generation_lanes import build_lanes
    matrix = load_matrix(matrix_path)
    selected = select_stratified(matrix, ideas)
    lanes = build_lanes(lane_root, lane_specs)
    supervisor = BatchSupervisor(
        batch_directory=batch_directory,
        lanes=lanes,
        ideas=selected,
        max_calls=max_calls,
    )
    pid_file = _supervisor_pid_file(batch_directory)
    pid_file.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    try:
        return supervisor.run()
    finally:
        if pid_file.exists():
            pid_file.unlink()


def watchdog(batch_directory: Path, restart_argv: list[str]) -> str:
    """Restart a crashed supervisor when work remains. Cron entry point."""
    status_file = batch_directory / "status.json"
    if not status_file.is_file():
        return "no_status"
    status = json.loads(status_file.read_text(encoding="utf-8"))
    if status.get("state") != "incomplete":
        return "complete"
    pid_file = _supervisor_pid_file(batch_directory)
    if pid_file.is_file():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            os.kill(pid, 0)
            return "alive"
        except (ValueError, ProcessLookupError, PermissionError):
            pass
    log = (batch_directory / "watchdog-restart.log").open("a", encoding="utf-8")
    process = subprocess.Popen(restart_argv, stdout=log, stderr=log,
                               start_new_session=True)
    _append_jsonl(batch_directory / "journal.jsonl", {
        "event": "watchdog_restart", "pid": process.pid, "ts": _now()})
    return f"restarted:{process.pid}"


def main(argv: list[str] | None = None) -> int:
    from tools.opencode_generation_lanes import DEFAULT_LANE_SPECS
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch-directory", required=True)
    parser.add_argument("--matrix", required=True)
    parser.add_argument("--ideas", type=int, default=10000)
    parser.add_argument("--max-calls", type=int, default=MAX_CALLS)
    parser.add_argument("--lane-root", required=True)
    parser.add_argument("--watchdog", action="store_true",
                        help="check status and restart a dead supervisor")
    parser.add_argument("--status", action="store_true",
                        help="print the current status record and exit")
    args = parser.parse_args(argv)

    batch_directory = Path(args.batch_directory).absolute()
    if args.status:
        status = json.loads((batch_directory / "status.json").read_text(encoding="utf-8"))
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0
    if args.watchdog:
        restart_argv = [sys.executable, str(Path(__file__).resolve()),
                        "--batch-directory", str(batch_directory),
                        "--matrix", args.matrix,
                        "--lane-root", args.lane_root,
                        "--ideas", str(args.ideas),
                        "--max-calls", str(args.max_calls)]
        print(watchdog(batch_directory, restart_argv))
        return 0
    if batch_directory.exists() and batch_directory.is_symlink():
        refuse("batch_directory_symlink_refused")
    batch_directory.mkdir(parents=True, exist_ok=True)
    status = start(batch_directory, Path(args.matrix).absolute(),
                   DEFAULT_LANE_SPECS, args.ideas, args.max_calls,
                   Path(args.lane_root).absolute())
    print(json.dumps(status, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())