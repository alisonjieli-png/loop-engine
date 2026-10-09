"""Critical path schedule: earliest and latest dates, float and the critical path from tasks and dependencies.

The forward pass gives each task its earliest start and finish, the backward pass its latest start and finish, and
total float is the difference. Tasks with zero total float are critical. With a start date the day offsets become
calendar dates, counting every day or only Monday to Friday minus declared holidays. A pure function of its JSON
input; the command line reads standard input and writes standard output.
"""
from __future__ import annotations

import datetime

from kit_schema import KitRefusal, check, parse_date, run_cli

REFUSALS = {
    "input_invalid": "the input does not match the input schema",
    "input_not_json": "standard input is not a JSON document",
    "duplicate_task_id": "two tasks share an id",
    "unknown_dependency": "a task depends on an id that is not in the task list",
    "self_dependency": "a task lists itself as a dependency",
    "dependency_cycle": "the dependencies form a cycle, so no schedule exists",
    "fractional_duration_with_dates": "calendar dates were requested but a duration is not a whole number of days",
    "invalid_date": "the start date or a holiday is not a real calendar date",
}
_TASK = {"type": "object", "required": ["id", "duration"], "additionalProperties": False,
         "properties": {"id": {"type": "string", "minLength": 1, "maxLength": 64},
                        "name": {"type": "string", "maxLength": 200},
                        "duration": {"type": "number", "minimum": 0, "maximum": 100000},
                        "depends_on": {"type": "array", "items": {"type": "string"}, "maxItems": 200}}}
INPUT_SCHEMA = {
    "type": "object", "required": ["tasks"], "additionalProperties": False,
    "properties": {
        "tasks": {"type": "array", "minItems": 1, "maxItems": 2000, "items": {"$ref": "#/$defs/task"},
                  "description": "tasks with an id, a duration in days and the ids they depend on (finish to start)"},
        "start_date": {"type": "string", "description": "optional YYYY-MM-DD project start for calendar dates"},
        "calendar": {"enum": ["calendar_days", "working_days"],
                     "description": "count every day, or Monday to Friday without holidays (default calendar_days)"},
        "holidays": {"type": "array", "items": {"type": "string"}, "maxItems": 400,
                     "description": "YYYY-MM-DD dates skipped by the working_days calendar"},
    },
    "$defs": {"task": _TASK},
}
_ROW = {"type": "object", "required": ["id", "duration", "earliest_start", "earliest_finish", "latest_start",
                                       "latest_finish", "total_float", "free_float", "critical"],
        "properties": {"id": {"type": "string"}, "name": {"type": "string"}, "duration": {"type": "number"},
                       "earliest_start": {"type": "number"}, "earliest_finish": {"type": "number"},
                       "latest_start": {"type": "number"}, "latest_finish": {"type": "number"},
                       "total_float": {"type": "number"}, "free_float": {"type": "number"},
                       "critical": {"type": "boolean"}, "start_date": {"type": "string", "format": "date"},
                       "finish_date": {"type": "string", "format": "date"}}}
OUTPUT_SCHEMA = {
    "type": "object", "required": ["project_duration", "critical_path", "critical_tasks", "order", "schedule"],
    "properties": {
        "project_duration": {"type": "number", "description": "days from project start to the last finish"},
        "critical_path": {"type": "array", "items": {"type": "string"},
                          "description": "one chain of zero-float tasks from start to finish"},
        "critical_tasks": {"type": "array", "items": {"type": "string"},
                           "description": "every task with zero total float"},
        "order": {"type": "array", "items": {"type": "string"}, "description": "a dependency-respecting order"},
        "schedule": {"type": "array", "items": _ROW, "description": "one row per task, in input order"},
        "project_start_date": {"type": "string", "format": "date"},
        "project_finish_date": {"type": "string", "format": "date"},
    },
}
_EPSILON = 1e-9


def _number(value: float) -> float:
    value = round(value, 6)
    return int(value) if float(value).is_integer() else value


def topological_order(tasks: list) -> list:
    """Task ids in an order where every task follows its dependencies; ties keep input order."""
    position = {task["id"]: index for index, task in enumerate(tasks)}
    waiting = {task["id"]: len(set(task.get("depends_on", []))) for task in tasks}
    successors = {task["id"]: [] for task in tasks}
    for task in tasks:
        for dependency in sorted(set(task.get("depends_on", [])), key=position.get):
            successors[dependency].append(task["id"])
    ready = sorted((identity for identity, count in waiting.items() if count == 0), key=position.get)
    order = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for successor in successors[current]:
            waiting[successor] -= 1
            if waiting[successor] == 0:
                ready.append(successor)
                ready.sort(key=position.get)
    if len(order) != len(tasks):
        stuck = sorted((identity for identity, count in waiting.items() if count > 0), key=position.get)
        raise KitRefusal("dependency_cycle", "tasks in or after a cycle: " + ", ".join(stuck[:10]))
    return order


def schedule_passes(tasks: list) -> dict:
    """Earliest and latest start and finish, total and free float, for tasks already checked for references."""
    by_id = {task["id"]: task for task in tasks}
    order = topological_order(tasks)
    successors = {identity: [] for identity in by_id}
    for task in tasks:
        for dependency in set(task.get("depends_on", [])):
            successors[dependency].append(task["id"])
    early = {}
    for identity in order:
        start = max((early[dependency][1] for dependency in set(by_id[identity].get("depends_on", []))), default=0.0)
        early[identity] = (start, start + float(by_id[identity]["duration"]))
    duration = max(finish for _start, finish in early.values())
    late = {}
    for identity in reversed(order):
        finish = min((late[successor][0] for successor in successors[identity]), default=duration)
        late[identity] = (finish - float(by_id[identity]["duration"]), finish)
    rows = {}
    for identity in by_id:
        free_until = min((early[successor][0] for successor in successors[identity]), default=duration)
        total = late[identity][0] - early[identity][0]
        rows[identity] = {"earliest_start": early[identity][0], "earliest_finish": early[identity][1],
                          "latest_start": late[identity][0], "latest_finish": late[identity][1],
                          "total_float": total, "free_float": free_until - early[identity][1],
                          "critical": abs(total) < _EPSILON}
    return {"order": order, "duration": duration, "rows": rows, "successors": successors}


def critical_chain(tasks: list, passes: dict) -> list:
    """One chain of critical tasks from a start task to the project finish, choosing input order on ties."""
    position = {task["id"]: index for index, task in enumerate(tasks)}
    rows = passes["rows"]
    starts = [identity for identity in passes["order"] if rows[identity]["critical"]
              and abs(rows[identity]["earliest_start"]) < _EPSILON]
    if not starts:
        return []
    chain = [min(starts, key=position.get)]
    while True:
        current = rows[chain[-1]]
        nexts = [successor for successor in passes["successors"][chain[-1]] if rows[successor]["critical"]
                 and abs(rows[successor]["earliest_start"] - current["earliest_finish"]) < _EPSILON]
        if not nexts:
            return chain
        chain.append(min(nexts, key=position.get))


def working_day_dates(start: datetime.date, count: int, calendar: str, holidays: set) -> list:
    """The first ``count`` days the calendar counts, from ``start`` on."""
    days, current = [], start
    while len(days) < count:
        if calendar == "calendar_days" or (current.weekday() < 5 and current not in holidays):
            days.append(current)
        current += datetime.timedelta(days=1)
    return days


def run(payload: dict) -> dict:
    check(payload, INPUT_SCHEMA)
    tasks = payload["tasks"]
    ids = [task["id"] for task in tasks]
    repeated = sorted({identity for identity in ids if ids.count(identity) > 1})
    if repeated:
        raise KitRefusal("duplicate_task_id", ", ".join(repeated[:10]))
    known = set(ids)
    for task in tasks:
        for dependency in task.get("depends_on", []):
            if dependency == task["id"]:
                raise KitRefusal("self_dependency", task["id"])
            if dependency not in known:
                raise KitRefusal("unknown_dependency", f"{task['id']} depends on {dependency}")
    passes = schedule_passes(tasks)
    result = {"project_duration": _number(passes["duration"]), "critical_path": critical_chain(tasks, passes),
              "critical_tasks": [identity for identity in ids if passes["rows"][identity]["critical"]],
              "order": passes["order"], "schedule": []}
    dates = None
    if "start_date" in payload:
        start = parse_date(payload["start_date"])
        holidays = {parse_date(text) for text in payload.get("holidays", [])}
        if start is None or None in holidays:
            raise KitRefusal("invalid_date", "start_date and holidays are YYYY-MM-DD calendar dates")
        if any(not float(task["duration"]).is_integer() for task in tasks):
            raise KitRefusal("fractional_duration_with_dates", "use whole days when asking for dates")
        calendar = payload.get("calendar", "calendar_days")
        dates = working_day_dates(start, int(passes["duration"]) + 1, calendar, holidays)
        result["project_start_date"] = dates[0].isoformat()
        result["project_finish_date"] = dates[max(int(passes["duration"]) - 1, 0)].isoformat()
    for task in tasks:
        row = passes["rows"][task["id"]]
        out = {"id": task["id"], "duration": _number(float(task["duration"]))}
        if "name" in task:
            out["name"] = task["name"]
        out.update({key: (_number(value) if not isinstance(value, bool) else value) for key, value in row.items()})
        if dates is not None:
            first = int(row["earliest_start"])
            last = first + max(int(task["duration"]) - 1, 0)
            out["start_date"], out["finish_date"] = dates[first].isoformat(), dates[last].isoformat()
        result["schedule"].append(out)
    return result


def main(argv=None, stdin=None, stdout=None) -> int:
    return run_cli(run, argv, stdin, stdout)


if __name__ == "__main__":
    raise SystemExit(main())
