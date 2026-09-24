"""Tests for scripts/experiment_ledger.py, its contracts and the command variants. Effects: writes only inside temporary folders; starts the script with the current interpreter and loads it by its exact path to compare its constants with the contracts."""
from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PAYLOAD = Path(__file__).resolve().parent.parent
SCRIPT = PAYLOAD / "scripts" / "experiment_ledger.py"
EXAMPLES = PAYLOAD / "examples"
CONTRACTS = PAYLOAD / "contracts"
VARIANTS = PAYLOAD / "variants"
PLACED_SCRIPT = ".baltor/pick-next-experiment/scripts/experiment_ledger.py"
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


class ExperimentLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.folder = tempfile.TemporaryDirectory()
        self.root = Path(self.folder.name)
        self.experiments = self.root / ".baltor" / "experiments"
        self.experiments.mkdir(parents=True)
        self.ledger = self.experiments / "ledger.jsonl"
        self.ledger.write_text((EXAMPLES / "ledger.jsonl").read_text(encoding="utf-8"), encoding="utf-8")
        (self.experiments / "notes.md").write_text((EXAMPLES / "notes.md").read_text(encoding="utf-8"), encoding="utf-8")
        self.proposal = json.loads((EXAMPLES / "proposal.json").read_text(encoding="utf-8"))

    def tearDown(self) -> None:
        self.folder.cleanup()

    def propose(self, value: dict) -> tuple[int, dict]:
        (self.experiments / "proposal.json").write_text(json.dumps(value), encoding="utf-8")
        return run(self.root, "propose")

    def lines(self) -> list[dict]:
        return [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines() if line.strip()]

    def config_of(self, experiment: str) -> dict:
        return dict(next(line for line in self.lines() if line.get("id") == experiment and "config" in line)["config"])

    def rewrite_header(self, **changes) -> None:
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        header = {**json.loads(lines[0]), **changes}
        header = {key: value for key, value in header.items() if value is not None}
        self.ledger.write_text("\n".join([json.dumps(header), *lines[1:]]) + "\n", encoding="utf-8")

    def test_summary_names_the_best_run_what_varied_and_the_fold_spread(self) -> None:
        code, summary = run(self.root, "summary")
        self.assertEqual(code, 0, summary)
        self.assertEqual(summary["best"]["id"], "E-003")
        self.assertEqual([item["id"] for item in summary["top"]], ["E-003", "E-002", "E-001"])
        self.assertEqual(summary["by_status"], {"planned": 0, "running": 0, "done": 3, "failed": 1})
        self.assertEqual(summary["varied_keys"]["max_depth"], [6, 10])
        self.assertEqual(summary["constant_keys"]["learning_rate"], 0.1)
        self.assertEqual(summary["failed"], [{"id": "E-004", "notes": "Ran out of memory on fold 3."}])
        self.assertEqual((summary["minutes_used"], summary["notes_file"]), (57.0, ".baltor/experiments/notes.md"))
        self.assertEqual((summary["lead"], summary["best"]["fold_spread"]), (0.007, 0.017))
        self.assertTrue(summary["lead_within_fold_spread"])
        self.assertIn("subsample", summary["known_keys"])

    def test_example_proposal_is_appended_as_planned(self) -> None:
        code, result = self.propose(self.proposal)
        self.assertEqual(code, 0, result)
        self.assertEqual((result["id"], result["changed_keys"]), ("E-005", ["learning_rate", "n_estimators"]))
        added = self.lines()[-1]
        self.assertEqual((added["status"], added["base"], added["fingerprint"]), ("planned", "E-003", result["fingerprint"]))
        self.assertEqual(schema_errors(added, contract("experiment-ledger-line")), [])
        code, summary = run(self.root, "summary")
        self.assertEqual(summary["open"][0]["id"], "E-005")

    def test_known_wrong_repeat_with_reordered_keys_and_float_counts_is_refused(self) -> None:
        before = self.ledger.read_bytes()
        repeat = {**self.proposal, "change": "Set n_estimators back to 300.0.",
                  "config": {"seed": 7, "folds": "group_5", "features": "base_plus_dates", "max_depth": 6,
                             "n_estimators": 300.0, "learning_rate": 0.1, "model": "gradient_boosting"}}
        code, result = self.propose(repeat)
        self.assertEqual((code, result["appended"], result["repeat_of"]), (1, False, "E-002"))
        self.assertEqual(self.ledger.read_bytes(), before)

    def test_known_wrong_a_dummy_key_does_not_make_a_new_experiment(self) -> None:
        before = self.ledger.read_bytes()
        dummy = {**self.proposal, "change": "Run E-003 again with attempt set to 2.",
                 "config": {**self.config_of("E-003"), "attempt": 2}}
        code, result = self.propose(dummy)
        self.assertEqual(code, 1)
        self.assertIn("are not settings of this ledger", "\n".join(result["findings"]))
        self.assertEqual(self.ledger.read_bytes(), before)
        declared = {**self.proposal, "change": "Set subsample to 0.8 from E-003.",
                    "config": {**self.config_of("E-003"), "subsample": 0.8}}
        self.rewrite_header(config_keys=None)
        self.assertEqual(self.propose(declared)[0], 1)
        self.ledger.write_bytes(before)
        code, result = self.propose(declared)
        self.assertEqual((code, result["changed_keys"]), (0, ["subsample"]))

    def test_change_must_name_every_changed_key(self) -> None:
        code, result = self.propose({**self.proposal, "change": "Halve the learning rate from E-003."})
        self.assertEqual(code, 1)
        self.assertIn("does not name ['n_estimators']", "\n".join(result["findings"]))

    def test_failed_configurations_and_ignored_keys_count_as_repeats(self) -> None:
        code, result = self.propose({**self.proposal, "change": "Set max_depth to 10.", "config": self.config_of("E-004")})
        self.assertEqual((code, result["repeat_of"]), (1, "E-004"))
        self.assertIn("status failed", "\n".join(result["findings"]))
        relabeled = {**self.proposal, "change": "Rerun E-003 with a new run_label.",
                     "config": {**self.config_of("E-003"), "run_label": "second try"}}
        code, result = self.propose(relabeled)
        self.assertEqual((code, result["repeat_of"]), (1, "E-003"))

    def test_a_failed_configuration_can_be_retried_after_an_outside_fix(self) -> None:
        retry = {**self.proposal, "change": "Run max_depth 10 again now that memory is larger.",
                 "config": self.config_of("E-004"), "retry_of": "E-004",
                 "environment_change": "The machine for this run has 64 GB of memory instead of 16 GB."}
        self.assertEqual(schema_errors(retry, contract("experiment-proposal")), [])
        code, result = self.propose({key: value for key, value in retry.items() if key != "environment_change"})
        self.assertEqual(code, 1)
        self.assertIn("a retry needs environment_change", "\n".join(result["findings"]))
        code, result = self.propose(retry)
        self.assertEqual((code, result["id"], result["retry_of"]), (0, "E-005", "E-004"))
        self.assertEqual(self.lines()[-1]["retry_of"], "E-004")
        code, result = self.propose({**retry, "retry_of": "E-005"})
        self.assertEqual(code, 1)
        self.assertIn("only a failed run can be retried; it is planned", "\n".join(result["findings"]))
        code, result = self.propose({**self.proposal, "retry_of": "E-004", "environment_change": "More memory."})
        self.assertIn("this one never ran", "\n".join(result["findings"]))

    def test_record_moves_an_experiment_and_feeds_the_summary(self) -> None:
        self.assertEqual(self.propose(self.proposal)[0], 0)
        self.assertEqual(run(self.root, "record", "--id", "E-005", "--status", "running")[0], 0)
        code, result = run(self.root, "record", "--id", "E-005", "--status", "done")
        self.assertEqual((code, result["reason"]), (1, "a done run needs --score"))
        code, result = run(self.root, "record", "--id", "E-005", "--status", "done", "--score", "0.401",
                           "--fold-scores", "0.398,0.4,0.405", "--minutes", "38")
        self.assertEqual(code, 0, result)
        code, summary = run(self.root, "summary")
        self.assertEqual((summary["best"]["id"], summary["minutes_used"]), ("E-005", 95.0))
        self.assertEqual(summary["by_status"]["done"], 4)
        code, result = run(self.root, "record", "--id", "E-005", "--status", "failed", "--notes", "late crash")
        self.assertEqual(code, 1)
        self.assertEqual(run(self.root, "record", "--id", "E-999", "--status", "running")[0], 2)
        for line in self.lines():
            self.assertEqual(schema_errors(line, contract("experiment-ledger-line")), [], line)

    def test_incomplete_proposal_lists_every_finding(self) -> None:
        broken = {**self.proposal, "base": "E-999", "ending_rule": "Stop when it looks worse.", "ending rule": "x",
                  "expected_effect": {"metric": "accuracy", "direction": "better", "size": 0.1},
                  "cost": {"minutes": 0, "model_calls": -1}}
        code, result = self.propose(broken)
        self.assertEqual(code, 1)
        findings = "\n".join(result["findings"])
        for expected in ("base 'E-999'", "ending_rule", "ledger metric rmse", "direction must be", "cost.minutes",
                         "cost.model_calls", "unknown field 'ending rule'"):
            self.assertIn(expected, findings)

    def test_budget_and_wide_changes(self) -> None:
        self.rewrite_header(budget_minutes=80)
        code, result = self.propose(self.proposal)
        self.assertEqual(code, 1)
        self.assertIn("budget is 80 minutes", "\n".join(result["findings"]))
        self.rewrite_header(budget_minutes=600)
        wide = {**self.proposal, "change": "Change learning_rate, n_estimators, max_depth and features at once.",
                "config": {**self.proposal["config"], "max_depth": 8, "features": "base_plus_dates_v2"}}
        code, result = self.propose(wide)
        self.assertEqual(code, 0, result)
        self.assertEqual(len(result["changed_keys"]), 4)
        self.assertTrue(result["warnings"])

    def test_missing_headerless_or_broken_ledgers_are_refused(self) -> None:
        lines = self.ledger.read_text(encoding="utf-8").splitlines()
        update = {"record_type": "experiment_update/v1", "status": "running", "at": "2026-09-23T22:10:00Z"}
        cases = [(lines[1:], "header"), ([lines[0], lines[1], "{not json", lines[2]], "line 3"),
                 ([lines[0], lines[1], lines[1]], "repeats the id E-001"),
                 ([*lines, json.dumps({**update, "id": "E-777"})], "which no earlier line lists"),
                 ([*lines, json.dumps({**update, "id": "E-003"})], "from done to 'running'"),
                 ([json.dumps({**json.loads(lines[0]), "budget": 5}), *lines[1:]], "unknown keys")]
        for content, expected in cases:
            with self.subTest(expected):
                self.ledger.write_text("\n".join(content) + "\n", encoding="utf-8")
                code, result = run(self.root, "summary")
                self.assertEqual(code, 2)
                self.assertIn(expected, result["reason"])
        self.ledger.unlink()
        code, result = run(self.root, "propose")
        self.assertEqual(code, 2)
        self.assertIn("no ledger", result["reason"])

    def test_contracts_match_the_helper_and_the_examples(self) -> None:
        spec = importlib.util.spec_from_file_location("experiment_ledger_under_test", SCRIPT)
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        line, proposal = contract("experiment-ledger-line"), contract("experiment-proposal")
        self.assertEqual(set(line["$defs"]["header"]["properties"]), helper.HEADER_KEYS)
        self.assertEqual(set(line["$defs"]["update"]["properties"]), helper.UPDATE_KEYS)
        self.assertEqual(set(proposal["properties"]), helper.PROPOSAL_KEYS)
        self.assertEqual(tuple(line["$defs"]["experiment"]["properties"]["status"]["enum"]), helper.STATUSES)
        for text in (EXAMPLES / "ledger.jsonl").read_text(encoding="utf-8").splitlines():
            self.assertEqual(schema_errors(json.loads(text), line), [], text)
        self.assertEqual(schema_errors(self.proposal, proposal), [])
        self.assertNotEqual(schema_errors({**self.proposal, "retry_of": "E-004"}, proposal), [])

    def test_every_variant_names_the_placed_script_and_the_headings(self) -> None:
        variants = sorted(path for path in VARIANTS.rglob("*") if path.is_file())
        self.assertEqual(len(variants), 5)
        for path in variants:
            text = path.read_text(encoding="utf-8")
            for expected in (PLACED_SCRIPT, "# Pick the next experiment", "known_keys", "retry_of",
                             "lead_within_fold_spread", ".baltor/pick-next-experiment/examples/proposal.json"):
                self.assertIn(expected, text, path.name)
            for heading in HEADINGS:
                self.assertIn(heading, text.splitlines(), f"{path.name} lacks {heading}")
        markers = {"claude_code": "$ARGUMENTS", "opencode": "$ARGUMENTS", "gemini_cli": "{{args}}"}
        for harness in ("claude_code", "opencode", "gemini_cli", "copilot", "cursor"):
            text = next((VARIANTS / harness).iterdir()).read_text(encoding="utf-8")
            for marker in ("$ARGUMENTS", "{{args}}"):
                self.assertEqual(marker in text, markers.get(harness) == marker, f"{harness} {marker}")
        copilot = (VARIANTS / "copilot" / "pick-next-experiment.prompt.md").read_text(encoding="utf-8")
        self.assertIn("\nagent: agent\n", copilot.split("---")[1] + "\n")
        self.assertTrue(SCRIPT.is_file())


if __name__ == "__main__":
    unittest.main()
