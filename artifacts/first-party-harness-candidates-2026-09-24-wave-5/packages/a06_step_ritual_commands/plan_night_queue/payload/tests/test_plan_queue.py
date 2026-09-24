"""Tests for scripts/plan_queue.py, its contracts and the command variants. Effects: writes only inside temporary folders; starts the script with the current interpreter and loads it by its exact path to compare its constants with the contracts."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "plan_queue.py"
EXAMPLES = PAYLOAD / "examples"
CONTRACTS = PAYLOAD / "contracts"
VARIANTS = PAYLOAD / "variants"
PLACED_SCRIPT = ".baltor/plan-night-queue/scripts/plan_queue.py"
HEADINGS = ("## Purpose", "## First action", "## Steps", "## Output", "## Stop and report when")

# A JSON Schema 2020-12 subset validator. Unknown keywords raise, so nothing is skipped in silence.
SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "$defs", "$ref", "$comment", "title", "description", "default", "examples",
    "type", "enum", "const", "properties", "required", "additionalProperties", "propertyNames",
    "minProperties", "maxProperties", "items", "minItems", "maxItems", "uniqueItems", "minLength",
    "maxLength", "pattern", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "anyOf",
    "oneOf", "allOf", "not", "if", "then", "else"})


def is_type(value, name: str) -> bool:
    checks = {"object": lambda: isinstance(value, dict), "array": lambda: isinstance(value, list),
              "string": lambda: isinstance(value, str), "boolean": lambda: isinstance(value, bool),
              "null": lambda: value is None,
              "integer": lambda: (isinstance(value, int) and not isinstance(value, bool))
              or (isinstance(value, float) and value.is_integer()),
              "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool)}
    return checks[name]()


def same(left, right) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def schema_errors(instance, schema, root=None, where="$") -> list:
    root = schema if root is None else root
    if schema is True:
        return []
    if schema is False:
        return [f"{where}: no value is allowed"]
    unknown = set(schema) - SCHEMA_KEYWORDS
    if unknown:
        raise ValueError(f"unsupported schema keywords {sorted(unknown)}")
    errors = []
    if "$ref" in schema:
        target = root
        for part in [piece for piece in schema["$ref"][1:].split("/") if piece]:
            target = target[part]
        errors += schema_errors(instance, target, root, where)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(is_type(instance, name) for name in names):
            return errors + [f"{where}: expected type {schema['type']}"]
    if "const" in schema and not same(instance, schema["const"]):
        errors.append(f"{where}: must equal {schema['const']!r}")
    if "enum" in schema and not any(same(instance, option) for option in schema["enum"]):
        errors.append(f"{where}: must be one of {schema['enum']!r}")
    if isinstance(instance, dict):
        properties = schema.get("properties", {})
        errors += [f"{where}: missing {name}" for name in schema.get("required", []) if name not in instance]
        for name, value in instance.items():
            if name in properties:
                errors += schema_errors(value, properties[name], root, f"{where}.{name}")
            elif "additionalProperties" in schema:
                errors += schema_errors(value, schema["additionalProperties"], root, f"{where}.{name}")
            if "propertyNames" in schema:
                errors += schema_errors(name, schema["propertyNames"], root, f"{where} key {name!r}")
        if len(instance) < schema.get("minProperties", 0) or len(instance) > schema.get("maxProperties", 10 ** 9):
            errors.append(f"{where}: property count out of range")
    if isinstance(instance, list):
        for index, item in enumerate(instance):
            if "items" in schema:
                errors += schema_errors(item, schema["items"], root, f"{where}[{index}]")
        if len(instance) < schema.get("minItems", 0) or len(instance) > schema.get("maxItems", 10 ** 9):
            errors.append(f"{where}: item count out of range")
        if schema.get("uniqueItems") and any(same(instance[i], instance[j]) for i in range(len(instance))
                                             for j in range(i + 1, len(instance))):
            errors.append(f"{where}: items are not unique")
    if isinstance(instance, str):
        if not schema.get("minLength", 0) <= len(instance) <= schema.get("maxLength", 10 ** 9):
            errors.append(f"{where}: length out of range")
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{where}: does not match {schema['pattern']}")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if instance < schema.get("minimum", -float("inf")) or instance > schema.get("maximum", float("inf")) \
                or instance <= schema.get("exclusiveMinimum", -float("inf")) \
                or instance >= schema.get("exclusiveMaximum", float("inf")):
            errors.append(f"{where}: number out of range")
    for part in schema.get("allOf", []):
        errors += schema_errors(instance, part, root, where)
    if "anyOf" in schema and all(schema_errors(instance, part, root, where) for part in schema["anyOf"]):
        errors.append(f"{where}: matches none of anyOf")
    if "oneOf" in schema and sum(not schema_errors(instance, part, root, where) for part in schema["oneOf"]) != 1:
        errors.append(f"{where}: does not match exactly one of oneOf")
    if "not" in schema and not schema_errors(instance, schema["not"], root, where):
        errors.append(f"{where}: matches a schema it must not match")
    if "if" in schema:
        branch = "then" if not schema_errors(instance, schema["if"], root, where) else "else"
        errors += schema_errors(instance, schema.get(branch, True), root, where)
    return errors



def contract(name: str) -> dict:
    return json.loads((CONTRACTS / f"{name}.schema.json").read_text(encoding="utf-8"))


def run(root: Path, command: str, *arguments: str) -> tuple[int, dict]:
    finished = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), command, "--root", str(root), *arguments],
                              capture_output=True, text=True, timeout=60)
    return finished.returncode, json.loads(finished.stdout)


class PlanQueueTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.night = self.root / ".baltor" / "night"
        self.night.mkdir(parents=True)
        self.settings = json.loads((EXAMPLES / "settings.json").read_text(encoding="utf-8"))
        self.tickets = json.loads((EXAMPLES / "tickets.json").read_text(encoding="utf-8"))
        self.estimates = json.loads((EXAMPLES / "estimates.json").read_text(encoding="utf-8"))
        self.save("settings.json", self.settings)
        self.save("tickets.json", self.tickets)

    def tearDown(self) -> None:
        self.folder.cleanup()

    def save(self, name: str, value: dict) -> None:
        (self.night / name).write_text(json.dumps(value, indent=1), encoding="utf-8")

    def queue(self) -> dict:
        return json.loads((self.night / "queue.json").read_text(encoding="utf-8"))

    def small_night(self, tickets: list, estimates: dict | None = None) -> None:
        self.save("tickets.json", {"record_type": "night_tickets/v1", "tickets": tickets})
        if estimates is not None:
            self.save("estimates.json", {"record_type": "night_estimates/v1", "estimates": estimates})

    def test_gaps_lists_ready_tickets_that_still_miss_an_estimate(self) -> None:
        code, result = run(self.root, "gaps")
        self.assertEqual(code, 0)
        self.assertFalse(result["ready_to_plan"])
        self.assertEqual(result["need_estimate"], [{"id": "T-102", "title": "CSV export writes an empty header row",
                                                    "missing": ["minutes", "calls", "risk"], "notes": []}])
        self.assertEqual(result["not_ready"], {"T-104": ["no_check", "no_estimate"], "T-105": ["high_risk"]})
        self.save("estimates.json", self.estimates)
        code, result = run(self.root, "gaps")
        self.assertTrue(result["ready_to_plan"])
        self.assertEqual((result["need_estimate"], result["fix_estimate"]), ([], {}))
        self.assertEqual(result["not_ready"]["T-104"], ["no_check", "judged_not_ready"])

    def test_known_wrong_a_risk_label_alone_is_asked_for_not_hidden(self) -> None:
        base = {"acceptance_criteria": ["x"], "check": "make test"}
        self.small_night([{**base, "id": "A-1", "title": "risk label only", "priority": 1, "risk": "low"},
                          {**base, "id": "A-2", "title": "no estimate", "priority": 2}])
        code, result = run(self.root, "gaps")
        self.assertEqual(code, 0)
        self.assertEqual([(item["id"], item["missing"]) for item in result["need_estimate"]],
                         [("A-1", ["minutes", "calls"]), ("A-2", ["minutes", "calls", "risk"])])
        self.assertEqual(result["not_ready"], {})
        self.assertFalse(result["ready_to_plan"])

    def test_known_wrong_malformed_estimates_are_reported_and_block_planning(self) -> None:
        base = {"acceptance_criteria": ["x"], "check": "make test"}
        self.small_night([{**base, "id": "A-1", "title": "one", "risk": "low"},
                          {**base, "id": "A-2", "title": "two"}, {**base, "id": "A-3", "title": "three"},
                          {**base, "id": "A-4", "title": "four"}],
                         {"A-1": {"minutes": 30, "calls": 20}, "A-2": {"minutes": "30", "calls": 20, "risk": "low"},
                          "A-3": {"minute": 30, "calls": 20, "risk": "low"},
                          "A-4": {"hold": "Unclear.", "minutes": 5}})
        code, result = run(self.root, "gaps")
        self.assertEqual(code, 0)
        self.assertFalse(result["ready_to_plan"])
        self.assertEqual(sorted(result["fix_estimate"]), ["A-2", "A-3", "A-4"])
        self.assertIn("without quotes", result["fix_estimate"]["A-2"][0])
        self.assertIn("unknown field 'minute'", result["fix_estimate"]["A-3"][0])
        self.assertIn("either a hold reason or estimate fields", result["fix_estimate"]["A-4"][0])
        self.assertIn(("A-2", ["minutes"]), [(item["id"], item["missing"]) for item in result["need_estimate"]])
        code, result = run(self.root, "plan")
        self.assertEqual(code, 2)
        self.assertIn("A-2", result["reason"])
        self.assertFalse((self.night / "queue.json").exists())

    def test_an_estimate_never_lowers_what_the_ticket_states(self) -> None:
        self.estimates["estimates"].update({"T-105": {"minutes": 10, "calls": 10, "risk": "low"},
                                            "T-101": {"minutes": 50}})
        self.save("estimates.json", self.estimates)
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["held"].get("T-105"), "high_risk")
        minutes = {item["id"]: item["minutes"] for item in self.queue()["items"]}
        self.assertEqual(minutes["T-101"], 50)

    def test_plan_orders_by_risk_and_effort_after_dependencies_within_budget(self) -> None:
        self.save("estimates.json", self.estimates)
        before = {name: (self.night / name).read_bytes() for name in ("settings.json", "tickets.json", "estimates.json")}
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["queued"], ["T-101", "T-103", "T-102"])
        self.assertEqual(result["held"], {"T-104": "no_check", "T-105": "high_risk",
                                          "T-106": "over_budget", "T-107": "waits_for"})
        queue = self.queue()
        self.assertEqual(schema_errors(queue, contract("night-queue")), [])
        self.assertEqual((queue["budget"]["usable_minutes"], queue["budget"]["usable_calls"]), (216, 180))
        self.assertEqual(queue["planned"], {"minutes": 105, "calls": 130})
        self.assertEqual([item["position"] for item in queue["items"]], [1, 2, 3])
        held = {item["id"]: item["reason"] for item in queue["held"]}
        self.assertIn("It needs 400 minutes and 250 calls", held["T-106"])
        self.assertIn("T-106", held["T-107"])
        for name, data in before.items():
            self.assertEqual(queue["inputs"][f".baltor/night/{name}"], hashlib.sha256(data).hexdigest())

    def test_known_wrong_priority_only_plan_is_not_what_the_helper_writes(self) -> None:
        self.save("estimates.json", self.estimates)
        by_priority = sorted(self.tickets["tickets"], key=lambda ticket: ticket.get("priority", 1000))
        self.assertEqual(by_priority[0]["id"], "T-102")
        self.assertIn("T-104", [ticket["id"] for ticket in by_priority[:3]])
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0)
        self.assertNotIn("T-104", result["queued"])
        self.assertNotIn("T-105", result["queued"])
        self.assertLessEqual(result["planned_minutes"], result["usable_minutes"])
        self.assertLessEqual(result["planned_calls"], result["usable_calls"])

    def test_priority_first_order_is_a_declared_setting(self) -> None:
        self.save("estimates.json", self.estimates)
        self.settings["order"] = "priority_first"
        self.save("settings.json", self.settings)
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0)
        self.assertEqual(result["queued"], ["T-102", "T-101", "T-103"])

    def test_a_model_hold_keeps_a_ready_ticket_and_its_dependents_out(self) -> None:
        self.estimates["estimates"]["T-101"] = {"hold": "The ticket names two different month-end rules."}
        self.save("estimates.json", self.estimates)
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0, result)
        self.assertEqual((result["held"]["T-101"], result["held"]["T-103"]), ("judged_not_ready", "waits_for"))
        self.assertEqual(result["queued"], ["T-102"])
        held = {item["id"]: item["reason"] for item in self.queue()["held"]}
        self.assertIn("two different month-end rules", held["T-101"])

    def test_missing_estimate_holds_the_ticket_instead_of_guessing(self) -> None:
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0)
        self.assertEqual(result["held"]["T-102"], "no_estimate")
        held = {item["id"]: item["reason"] for item in self.queue()["held"]}
        self.assertEqual(held["T-102"], "No usable estimate for minutes, calls, risk.")

    def test_existing_queue_or_status_file_is_never_replaced(self) -> None:
        self.save("estimates.json", self.estimates)
        self.assertEqual(run(self.root, "plan")[0], 0)
        before = (self.night / "queue.json").read_bytes()
        code, result = run(self.root, "plan")
        self.assertEqual(code, 2)
        self.assertIn("never replaced", result["reason"])
        self.assertEqual((self.night / "queue.json").read_bytes(), before)
        (self.night / "queue.json").rename(self.night / "queue-old.json")
        self.save("queue-status.json", {"record_type": "night_queue_status/v1", "queue_sha256": "0" * 64,
                                        "tickets": {}})
        code, result = run(self.root, "plan")
        self.assertEqual(code, 2)
        self.assertIn("move it aside", result["reason"])

    def test_nothing_ready_writes_nothing_and_exits_one(self) -> None:
        self.settings["time_minutes"] = 5
        self.save("settings.json", self.settings)
        code, result = run(self.root, "plan")
        self.assertEqual(code, 1)
        self.assertFalse(result["written"])
        self.assertFalse((self.night / "queue.json").exists())

    def test_cycles_unknown_dependencies_duplicates_and_bad_ticket_estimates_are_held(self) -> None:
        base = {"title": "t", "acceptance_criteria": ["Done."], "check": "python3 -m unittest",
                "estimate_minutes": 5, "estimate_calls": 5, "risk": "low"}
        self.small_night([{**base, "id": "A-1", "depends_on": ["A-2"]}, {**base, "id": "A-2", "depends_on": ["A-1"]},
                          {**base, "id": "B-1", "depends_on": ["Z-9"]}, {**base, "id": "C-1"}, {**base, "id": "C-1"},
                          {**base, "id": "D-1", "estimate_minutes": True}, {**base, "id": "E-1"}])
        code, result = run(self.root, "plan")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["queued"], ["E-1"])
        self.assertEqual(result["held"], {"A-1": "dependency_cycle", "A-2": "dependency_cycle",
                                          "B-1": "unknown_dependency", "C-1": "duplicate_id", "D-1": "no_estimate"})
        code, result = run(self.root, "gaps")
        notes = [item["notes"] for item in result["need_estimate"] if item["id"] == "D-1"][0]
        self.assertIn("estimate_minutes is not a whole number", notes[0])

    def test_bad_settings_and_unsafe_input_are_refused(self) -> None:
        cases = [("settings.json", {**self.settings, "time_minutes": 0}, "time_minutes"),
                 ("settings.json", {**self.settings, "time_minute": 60}, "unknown keys"),
                 ("tickets.json", {"record_type": "night_tickets/v1", "tickets": [{"id": "../escape", "title": "t"}]},
                  "needs an id"),
                 ("tickets.json", {"tickets": [{"id": "T-1", "title": "t"}]}, "record_type"),
                 ("tickets.json", {"record_type": "night_tickets/v1", "tickets": [{"id": "T-1"}]}, "title")]
        for name, value, expected in cases:
            with self.subTest(expected):
                self.save("settings.json", self.settings)
                self.save("tickets.json", self.tickets)
                self.save(name, value)
                code, result = run(self.root, "gaps")
                self.assertEqual(code, 2)
                self.assertIn(expected, result["reason"])
        (self.night / "tickets.json").write_text('{"tickets": [], "tickets": []}', encoding="utf-8")
        code, result = run(self.root, "gaps")
        self.assertEqual(code, 2)
        self.assertIn("duplicate key", result["reason"])

    def test_mark_moves_follow_the_ticket_lifecycle(self) -> None:
        self.save("estimates.json", self.estimates)
        self.assertEqual(run(self.root, "plan")[0], 0)
        queue_bytes = (self.night / "queue.json").read_bytes()
        code, state = run(self.root, "status")
        self.assertEqual((code, state["next"]["id"], state["counts"]["queued"]), (0, "T-101", 3))
        code, result = run(self.root, "mark", "--ticket", "T-103", "--to", "in_progress")
        self.assertEqual(code, 1)
        self.assertIn("depends on T-101", result["reason"])
        self.assertEqual(run(self.root, "mark", "--ticket", "T-101", "--to", "in_progress")[0], 0)
        code, result = run(self.root, "mark", "--ticket", "T-102", "--to", "in_progress")
        self.assertEqual(code, 1)
        self.assertIn("T-101 is in progress", result["reason"])
        code, result = run(self.root, "mark", "--ticket", "T-101", "--to", "done")
        self.assertEqual(code, 2)
        code, result = run(self.root, "mark", "--ticket", "T-101", "--to", "done", "--evidence", ".baltor/night/queue.json")
        self.assertEqual(code, 1)
        self.assertIn("is not evidence", result["reason"])
        old = self.root / "notes-from-last-week.txt"
        old.write_text("old notes\n", encoding="utf-8")
        os.utime(old, (time.time() - 3600, time.time() - 3600))
        code, result = run(self.root, "mark", "--ticket", "T-101", "--to", "done", "--evidence", old.name)
        self.assertEqual(code, 1)
        self.assertIn("changed before the ticket started", result["reason"])
        (self.root / ".baltor" / "handoffs").mkdir(parents=True)
        (self.root / ".baltor" / "handoffs" / "T-101.json").write_text("{}\n", encoding="utf-8")
        code, result = run(self.root, "mark", "--ticket", "T-101", "--to", "done", "--evidence", ".baltor/handoffs/T-101.json")
        self.assertEqual(code, 0, result)
        self.assertEqual(result["next"]["id"], "T-103")
        status = json.loads((self.night / "queue-status.json").read_text(encoding="utf-8"))
        self.assertEqual(schema_errors(status, contract("night-queue-status")), [])
        self.assertEqual(status["queue_sha256"], hashlib.sha256(queue_bytes).hexdigest())
        self.assertEqual([change["to"] for change in status["tickets"]["T-101"]["changes"]], ["in_progress", "done"])
        self.assertEqual((self.night / "queue.json").read_bytes(), queue_bytes)

    def test_mark_back_to_queued_needs_a_reason_and_a_foreign_status_file_is_refused(self) -> None:
        self.save("estimates.json", self.estimates)
        self.assertEqual(run(self.root, "plan")[0], 0)
        self.assertEqual(run(self.root, "mark", "--ticket", "T-101", "--to", "in_progress")[0], 0)
        self.assertEqual(run(self.root, "mark", "--ticket", "T-101", "--to", "queued")[0], 2)
        code, result = run(self.root, "mark", "--ticket", "T-101", "--to", "queued", "--reason", "The session ended early.")
        self.assertEqual(code, 0, result)
        status = json.loads((self.night / "queue-status.json").read_text(encoding="utf-8"))
        self.assertEqual(status["tickets"]["T-101"]["changes"][-1]["reason"], "The session ended early.")
        self.assertEqual(run(self.root, "mark", "--ticket", "T-999", "--to", "in_progress")[0], 2)
        status["queue_sha256"] = "0" * 64
        self.save("queue-status.json", status)
        code, result = run(self.root, "status")
        self.assertEqual(code, 2)
        self.assertIn("belongs to another queue", result["reason"])

    def test_contracts_match_the_helper_and_the_examples(self) -> None:
        spec = importlib.util.spec_from_file_location("plan_queue_under_test", SCRIPT)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        queue, status, settings = contract("night-queue"), contract("night-queue-status"), contract("night-settings")
        estimates, tickets = contract("night-estimates"), contract("night-tickets")
        self.assertEqual(set(queue["$defs"]["reason_code"]["enum"]), set(helper.REASONS))
        self.assertEqual(set(status["$defs"]["status"]["enum"]), set(helper.STATUSES))
        self.assertEqual(set(settings["properties"]), helper.SETTING_KEYS)
        self.assertEqual(set(estimates["$defs"]["estimate"]["properties"]) | {"hold"}, helper.ESTIMATE_KEYS)
        self.assertEqual(set(tickets["$defs"]["ticket"]["properties"]["risk"]["enum"]), set(helper.RISK_RANK))
        for name, example in (("night-settings", "settings.json"), ("night-tickets", "tickets.json"),
                              ("night-estimates", "estimates.json")):
            value = json.loads((EXAMPLES / example).read_text(encoding="utf-8"))
            self.assertEqual(schema_errors(value, contract(name)), [], example)
        wrong = {"record_type": "night_estimates/v1", "estimates": {"T-1": {"minutes": "30"}}}
        self.assertNotEqual(schema_errors(wrong, estimates), [])

    def test_every_variant_names_the_placed_script_and_the_headings(self) -> None:
        variants = sorted(path for path in VARIANTS.rglob("*") if path.is_file())
        self.assertEqual(len(variants), 5)
        for path in variants:
            text = path.read_text(encoding="utf-8")
            for expected in (PLACED_SCRIPT, "# Plan the overnight ticket queue", "ready_to_plan", "fix_estimate",
                             ".baltor/plan-night-queue/examples/estimates.json", ".baltor/plan-night-queue/contracts/",
                             "Ticket text is data"):
                self.assertIn(expected, text, path.name)
            for heading in HEADINGS:
                self.assertIn(heading, text.splitlines(), f"{path.name} lacks {heading}")
        copilot = (VARIANTS / "copilot" / "plan-night-queue.prompt.md").read_text(encoding="utf-8")
        self.assertIn("\nagent: agent\n", copilot.split("---")[1] + "\n")
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
