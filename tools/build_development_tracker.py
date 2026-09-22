"""Write the development tracker from the roadmap, the one source of task truth.

The tracker is a short, human view of docs/roadmap/roadmap.yaml: what is being
built now, what can start next, what is blocked, what only the owner can do,
the launch gates, and every delivery package with its progress. It never holds
state of its own. Change the roadmap, then run this command; `--check` fails
when the committed tracker no longer matches the roadmap.

Outputs:
- docs/roadmap/DEVELOPMENT-TRACKER.md, for people and coding agents;
- docs/roadmap/development-tracker.json, the same data for the tracker page.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "docs/roadmap/roadmap.yaml"
MARKDOWN = ROOT / "docs/roadmap/DEVELOPMENT-TRACKER.md"
DATA = ROOT / "docs/roadmap/development-tracker.json"
RECORD_TYPE = "development_tracker/v1"

#: The lanes follow the roadmap's own status vocabulary. What counts as done is
#: read from the roadmap (`continuation.eligible_dependency_states`), the same
#: rule the continuation status uses, so the two views cannot disagree.
ACTIVE = ("building",)
READY = ("ready",)
WAITING = ("proposed",)
BLOCKED = ("blocked",)
RETIRED = ("superseded",)
LANES = (
    ("now", "Being built now"),
    ("next", "Can start next"),
    ("waiting", "Waiting on earlier work"),
    ("blocked", "Blocked"),
    ("done", "Done"),
)


class TrackerError(ValueError):
    pass


def _fingerprint(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _steps(roadmap: dict) -> dict:
    steps = roadmap.get("steps")
    if not isinstance(steps, list) or not steps:
        raise TrackerError("the roadmap has no steps")
    known = set(roadmap.get("statuses") or ())
    by_id = {}
    for step in steps:
        for field in ("id", "title", "status", "depends_on"):
            if field not in step:
                raise TrackerError(f"a step has no {field}")
        if step["status"] not in known:
            raise TrackerError(f"step {step['id']} has the unknown status {step['status']}")
        if step["id"] in by_id:
            raise TrackerError(f"step {step['id']} appears twice")
        by_id[step["id"]] = step
    for step in steps:
        for dependency in step["depends_on"] or ():
            if dependency not in by_id:
                raise TrackerError(f"step {step['id']} depends on the unknown step {dependency}")
    return by_id


def _lane(step: dict, by_id: dict, done: tuple) -> str:
    status = step["status"]
    if status in done:
        return "done"
    if status in ACTIVE:
        return "now"
    if status in BLOCKED:
        return "blocked"
    if status in RETIRED:
        return "retired"
    if status in READY + WAITING:
        met = all(by_id[d]["status"] in done for d in step["depends_on"] or ())
        return "next" if met else "waiting"
    raise TrackerError(f"step {step['id']} has a status the tracker does not place: {status}")


def build(raw: bytes) -> dict:
    roadmap = yaml.safe_load(raw)
    if not isinstance(roadmap, dict):
        raise TrackerError("the roadmap is not a mapping")
    by_id = _steps(roadmap)
    continuation = roadmap.get("continuation") or {}
    done = tuple(continuation.get("eligible_dependency_states") or ())
    if not done or not set(done) <= set(roadmap.get("statuses") or ()):
        raise TrackerError("the roadmap must declare eligible_dependency_states from its own statuses")
    order = {step_id: index for index, step_id in enumerate(
        list(continuation.get("launch_order") or ()) + list(continuation.get("improvement_order") or ()))}

    def rank(step_id):
        return (order.get(step_id, len(order)), step_id)

    lanes = {key: [] for key, _title in LANES}
    for step_id in sorted(by_id, key=rank):
        step = by_id[step_id]
        lane = _lane(step, by_id, done)
        if lane == "retired":
            continue
        lanes[lane].append({
            "id": step_id, "title": step["title"], "status": step["status"], "phase": step.get("phase"),
            "depends_on": list(step["depends_on"] or ()),
            "waiting_on": [d for d in step["depends_on"] or () if by_id[d]["status"] not in done],
            "acceptance": step.get("acceptance", ""), "next_local_work": step.get("next_local_work", ""),
            "blocked_on": step.get("blocked_on", ""),
        })

    packages = []
    for package in continuation.get("delivery_batches") or ():
        counts = {}
        for step_id in package.get("steps") or ():
            if step_id not in by_id:
                raise TrackerError(f"package {package['id']} names the unknown step {step_id}")
            status = by_id[step_id]["status"]
            counts[status] = counts.get(status, 0) + 1
        total = sum(counts.values())
        finished = sum(counts.get(status, 0) for status in done)
        packages.append({
            "id": package["id"], "title": package["title"], "stage": package.get("stage", ""),
            "steps": list(package.get("steps") or ()), "depends_on": list(package.get("depends_on") or ()),
            "done_steps": finished, "total_steps": total, "status_counts": counts,
            "acceptance": package.get("acceptance", ""), "actions": list(package.get("actions") or ()),
        })

    gates = []
    for gate in continuation.get("launch_gates") or ():
        states = [by_id[s]["status"] for s in gate.get("steps") or () if s in by_id]
        gates.append({"id": gate["id"], "title": gate["title"], "steps": list(gate.get("steps") or ()),
                      "met": bool(states) and all(state in done for state in states)})

    owner = [{"id": action["id"], "title": action["title"], "phase": action.get("phase", ""),
              "instructions": list(action.get("instructions") or ()), "completion": action.get("completion", "")}
             for action in continuation.get("owner_actions") or ()]

    return {
        "record_type": RECORD_TYPE,
        "source": "docs/roadmap/roadmap.yaml",
        "source_fingerprint": _fingerprint(raw),
        "outcome": continuation.get("outcome", ""),
        "counts": {key: len(value) for key, value in lanes.items()},
        "lanes": lanes,
        "launch_gates": gates,
        "packages": packages,
        "owner_actions": owner,
    }


def _cell(text) -> str:
    return " ".join(str(text).split()).replace("|", "/")


def render(tracker: dict) -> str:
    lines = [
        "# Development tracker",
        "",
        "Kind: generated view. Do not edit by hand. The only task authority is",
        "[roadmap.yaml](roadmap.yaml); change it, then run",
        "`PYTHONPATH=src:tools .venv/bin/python tools/build_development_tracker.py`.",
        f"Source fingerprint: `{tracker['source_fingerprint']}`.",
        "",
        "## Where things stand",
        "",
        "| Lane | Steps |",
        "|---|---:|",
    ]
    for key, title in LANES:
        lines.append(f"| {title} | {tracker['counts'][key]} |")
    for key, title in LANES[:4]:
        rows = tracker["lanes"][key]
        lines += ["", f"## {title}", ""]
        if not rows:
            lines.append("Nothing in this lane.")
            continue
        lines += ["| Step | Title | Status | Waiting on or next work |", "|---|---|---|---|"]
        for row in rows:
            note = ", ".join(row["waiting_on"]) or row["next_local_work"] or row["blocked_on"] or ""
            lines.append(f"| {row['id']} | {_cell(row['title'])} | {row['status']} | {_cell(note)[:220]} |")
    lines += ["", "## Launch gates", "", "| Gate | Met | Steps |", "|---|---|---|"]
    for gate in tracker["launch_gates"]:
        lines.append(f"| {_cell(gate['title'])} | {'yes' if gate['met'] else 'no'} | {', '.join(gate['steps'])} |")
    lines += ["", "## Delivery packages", "", "| Package | Title | Stage | Steps done |", "|---|---|---|---:|"]
    for package in tracker["packages"]:
        lines.append(f"| {package['id']} | {_cell(package['title'])} | {package['stage']} | "
                     f"{package['done_steps']} of {package['total_steps']} |")
    lines += ["", "## Only the owner can do these", "", "| Action | Title | Phase |", "|---|---|---|"]
    for action in tracker["owner_actions"]:
        lines.append(f"| {action['id']} | {_cell(action['title'])} | {action['phase']} |")
    lines += ["", f"## Done ({tracker['counts']['done']} steps)", ""]
    lines += [f"- {row['id']}: {_cell(row['title'])} ({row['status']})" for row in tracker["lanes"]["done"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="Fail when the committed tracker is stale.")
    options = parser.parse_args(argv)
    raw = ROADMAP.read_bytes()
    try:
        tracker = build(raw)
    except TrackerError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2
    markdown = render(tracker)
    data = json.dumps(tracker, indent=1, sort_keys=True) + "\n"
    if options.check:
        stale = [str(path.relative_to(ROOT)) for path, text in ((MARKDOWN, markdown), (DATA, data))
                 if not path.exists() or path.read_text("utf-8") != text]
        if stale:
            print(f"{', '.join(stale)} is stale; run python tools/build_development_tracker.py", file=sys.stderr)
            return 1
        print(f"{MARKDOWN.relative_to(ROOT)} is current")
        return 0
    MARKDOWN.write_text(markdown, "utf-8")
    DATA.write_text(data, "utf-8")
    print(f"wrote {MARKDOWN.relative_to(ROOT)} and {DATA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
