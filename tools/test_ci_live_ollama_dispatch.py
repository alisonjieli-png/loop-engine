"""The manual live Ollama job runs only when a person asks for it, never in a run that a data refresh dispatches.

The job "manual live Ollama orientation for five text scenarios" of .github/workflows/ci.yml calls a model
provider with the repository's Ollama key. Until September 27, 2026 its condition was
github.event_name == 'workflow_dispatch'. The model directory and MCP directory refresh workflows dispatch
ci.yml after each data commit (gh workflow run ci.yml --ref main), so every refresh started the live job, which
failed with zero model calls and turned main red: 4 of 4 dispatched runs failed from September 26. The job now
also requires the boolean dispatch input live_ollama, whose default is false.

The rules read the workflows as data and evaluate the job's condition the way GitHub Actions evaluates an
expression, for each event that starts ci.yml: a push, a pull request, every dispatch of ci.yml that another
workflow of this repository makes, and a person's dispatch with the input set. An expression form the evaluator
does not know is reported, never guessed. Each rule has a known-wrong control, the old condition among them.
"""
from __future__ import annotations

import math
from pathlib import Path
import re
import shlex
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"
LIVE_JOB = "live-ollama"
LIVE_INPUT = "live_ollama"
#: The workflows that dispatched ci.yml when the fault was found. The dispatch reader must find both, so that a
#: change in how they dispatch cannot make the rule pass by finding nothing.
KNOWN_DISPATCHERS = {"model-directory.yml", "mcp-directory.yml"}
#: A command line that dispatches ci.yml, by file name or by the workflow's name.
DISPATCH_COMMAND = re.compile(r"gh\s+workflow\s+run\s+(?:ci\.yml|\"CI\"|'CI'|CI)(?=\s|$)(?P<rest>[^\n]*)")
#: A dispatch made from a script step, which this reader cannot read field by field.
SCRIPT_DISPATCH = re.compile(r"createWorkflowDispatch")


class ExpressionError(ValueError):
    """An expression form this evaluator does not implement."""


_TOKEN = re.compile(r"""\s*(?:
    (?P<string>'(?:[^']|'')*')
  | (?P<number>\d+(?:\.\d+)?)
  | (?P<operator>==|!=|&&|\|\||!|\(|\))
  | (?P<name>[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*)*)
)""", re.VERBOSE)
#: Status functions GitHub allows in a job condition, for a job that needs no other job.
_STATUS_FUNCTIONS = {"success": True, "always": True, "failure": False, "cancelled": False}


def _tokens(text: str) -> list:
    body = text.strip()
    if body.startswith("${{") and body.endswith("}}"):
        body = body[3:-2]
    found, position = [], 0
    while position < len(body):
        if body[position:].strip() == "":
            break
        match = _TOKEN.match(body, position)
        if match is None:
            raise ExpressionError(f"unknown text at {body[position:]!r}")
        kind = match.lastgroup
        found.append((kind, match.group(kind)))
        position = match.end()
    return found


def _number(value) -> float:
    """GitHub's coercion of a value to a number, for a comparison of two different types."""
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return 0.0
        try:
            return float(text)
        except ValueError:
            return math.nan
    return math.nan


def _equal(left, right) -> bool:
    """GitHub's loose equality: same types compare directly (strings without case), other pairs as numbers."""
    if isinstance(left, str) and isinstance(right, str):
        return left.casefold() == right.casefold()
    if isinstance(left, bool) and isinstance(right, bool):
        return left == right
    if left is None and right is None:
        return True
    if isinstance(left, (dict, list)) or isinstance(right, (dict, list)):
        return left is right
    first, second = _number(left), _number(right)
    return not (math.isnan(first) or math.isnan(second)) and first == second


def truthy(value) -> bool:
    """GitHub's truthiness: false, 0, the empty string, null and NaN are false; every other value is true."""
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return not (value == 0 or math.isnan(value))
    if isinstance(value, str):
        return value != ""
    return True


def evaluate(expression: str, context: dict):
    """The value of a GitHub Actions expression over a context, for the forms a job condition here uses."""
    tokens = _tokens(expression)
    position = 0

    def peek():
        return tokens[position] if position < len(tokens) else (None, None)

    def take():
        nonlocal position
        token = peek()
        position += 1
        return token

    def lookup(path: str):
        value = context
        for part in path.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        return value

    def primary():
        kind, text = take()
        if kind == "operator" and text == "(":
            value = either()
            if take() != ("operator", ")"):
                raise ExpressionError("an opening parenthesis is not closed")
            return value
        if kind == "string":
            return text[1:-1].replace("''", "'")
        if kind == "number":
            return float(text)
        if kind == "name":
            if peek() == ("operator", "("):
                take()
                if take() != ("operator", ")") or text not in _STATUS_FUNCTIONS:
                    raise ExpressionError(f"the function {text!r} is not implemented here")
                return _STATUS_FUNCTIONS[text]
            words = {"true": True, "false": False, "null": None}
            return words[text] if text in words else lookup(text)
        raise ExpressionError(f"unexpected {text!r}")

    def negation():
        if peek() == ("operator", "!"):
            take()
            return not truthy(negation())
        return primary()

    def comparison():
        value = negation()
        while peek() in (("operator", "=="), ("operator", "!=")):
            operator = take()[1]
            other = negation()
            value = _equal(value, other) if operator == "==" else not _equal(value, other)
        return value

    def both():
        value = comparison()
        while peek() == ("operator", "&&"):
            take()
            other = comparison()
            value = other if truthy(value) else value
        return value

    def either():
        value = both()
        while peek() == ("operator", "||"):
            take()
            other = both()
            value = value if truthy(value) else other
        return value

    result = either()
    if position != len(tokens):
        raise ExpressionError(f"unexpected {tokens[position][1]!r} after the expression")
    return result


def workflow_triggers(data: dict) -> dict:
    """The `on` mapping; YAML 1.1 reads the bare key `on` as true."""
    triggers = data.get(True, data.get("on")) or {}
    return triggers if isinstance(triggers, dict) else {}


def dispatch_context(declared: dict, fields: dict) -> dict:
    """The context of a workflow_dispatch run of a workflow that declares these inputs, given these fields.

    A boolean input is a boolean in the `inputs` context and the text "true" or "false" in
    github.event.inputs; a field that is not given takes the declared default.
    """
    inputs, event_inputs = {}, {}
    for name, spec in (declared or {}).items():
        spec = spec or {}
        raw = fields.get(name, spec.get("default"))
        if spec.get("type") == "boolean":
            value = raw if isinstance(raw, bool) else str(raw).strip().lower() == "true"
            inputs[name], event_inputs[name] = value, "true" if value else "false"
        else:
            value = "" if raw is None else str(raw)
            inputs[name], event_inputs[name] = value, value
    return {"github": {"event_name": "workflow_dispatch", "event": {"inputs": event_inputs}}, "inputs": inputs}


def dispatches_of_ci(workflow_texts: dict) -> tuple:
    """({workflow file: [fields of each dispatch of ci.yml]}, [problems]) over the other workflows' texts."""
    found, problems = {}, []
    for name, text in sorted(workflow_texts.items()):
        if name == CI.name:
            continue
        if SCRIPT_DISPATCH.search(text):
            problems.append(f"{name} dispatches a workflow from a script, which this check cannot read")
        for match in DISPATCH_COMMAND.finditer(text):
            fields, words = {}, shlex.split(match.group("rest"), comments=True)
            index = 0
            while index < len(words):
                word = words[index]
                if word in ("-f", "-F", "--field", "--raw-field") and index + 1 < len(words):
                    key, _, value = words[index + 1].partition("=")
                    fields[key] = value
                    index += 2
                elif word in ("-r", "--ref", "-R", "--repo") and index + 1 < len(words):
                    index += 2
                elif word.startswith(("--field=", "--raw-field=", "--ref=", "--repo=")):
                    if word.startswith(("--field=", "--raw-field=")):
                        key, _, value = word.split("=", 1)[1].partition("=")
                        fields[key] = value
                    index += 1
                else:
                    problems.append(f"{name} dispatches ci.yml with {word!r}, which this check cannot read")
                    index += 1
            found.setdefault(name, []).append(fields)
    return found, problems


def live_job_problems(ci_text: str, workflow_texts: dict) -> list:
    """What lets the live Ollama job start without a person asking for it, or stops a person starting it."""
    problems = []
    data = yaml.safe_load(ci_text)
    dispatch = workflow_triggers(data).get("workflow_dispatch") or {}
    declared = dispatch.get("inputs") or {}
    spec = declared.get(LIVE_INPUT)
    if not spec:
        problems.append(f"ci.yml declares no {LIVE_INPUT} dispatch input")
    elif spec.get("type") != "boolean" or spec.get("default") is not False:
        problems.append(f"the {LIVE_INPUT} input is not a boolean whose default is false")
    job = (data.get("jobs") or {}).get(LIVE_JOB)
    if job is None:
        return problems + [f"ci.yml has no {LIVE_JOB} job"]
    condition = job.get("if")
    if condition is None or isinstance(condition, bool):
        return problems + [f"the {LIVE_JOB} job has no expression condition, so it does not wait for a person"]
    dispatches, reading_problems = dispatches_of_ci(workflow_texts)
    problems += reading_problems
    scenarios = [
        ("a push to main", {"github": {"event_name": "push", "event": {}}, "inputs": {}}, False),
        ("a pull request", {"github": {"event_name": "pull_request", "event": {}}, "inputs": {}}, False),
        ("a dispatch with no inputs", dispatch_context(declared, {}), False),
        (f"a person's dispatch with {LIVE_INPUT} true", dispatch_context(declared, {LIVE_INPUT: "true"}), True),
    ]
    for name, field_sets in sorted(dispatches.items()):
        for fields in field_sets:
            unknown = sorted(set(fields) - set(declared))
            if unknown:
                problems.append(f"{name} dispatches ci.yml with inputs it does not declare: {', '.join(unknown)}")
            scenarios.append((f"the dispatch of ci.yml in {name}", dispatch_context(declared, fields), False))
    for label, context, expected in scenarios:
        try:
            started = truthy(evaluate(str(condition), context))
        except ExpressionError as error:
            return problems + [f"the {LIVE_JOB} condition uses a form this check cannot evaluate: {error}"]
        if started != expected:
            problems.append(f"{label} {'starts' if started else 'does not start'} the {LIVE_JOB} job")
    return problems


def read_workflows() -> dict:
    return {path.name: path.read_text(encoding="utf-8") for path in sorted(WORKFLOWS.glob("*.yml"))}


class ExpressionEvaluatorTests(unittest.TestCase):
    """The evaluator follows GitHub's documented rules on the forms it implements."""

    def test_the_text_false_is_true_and_null_equals_false(self):
        self.assertTrue(truthy(evaluate("'false'", {})))
        self.assertTrue(evaluate("null == false", {}))
        self.assertFalse(truthy(evaluate("inputs.missing", {"inputs": {}})))

    def test_strings_compare_without_case_and_other_types_as_numbers(self):
        self.assertTrue(evaluate("github.event_name == 'WORKFLOW_DISPATCH'",
                                 {"github": {"event_name": "workflow_dispatch"}}))
        self.assertTrue(evaluate("true == 1", {}))
        self.assertFalse(evaluate("true == 'true'", {}))

    def test_the_logical_operators_and_the_wrapper(self):
        self.assertEqual(evaluate("${{ !(false || null) && 'x' }}", {}), "x")
        self.assertTrue(evaluate("success() && !cancelled()", {}))

    def test_an_unknown_form_is_refused_not_guessed(self):
        for expression in ("contains(github.ref, 'main')", "github.event_name ==", "a ~ b", "(true"):
            with self.subTest(expression=expression), self.assertRaises(ExpressionError):
                evaluate(expression, {"github": {}})


class LiveOllamaDispatchTests(unittest.TestCase):
    def setUp(self):
        self.workflows = read_workflows()
        self.ci = self.workflows[CI.name]

    def test_only_a_persons_dispatch_starts_the_live_job(self):
        self.assertEqual(live_job_problems(self.ci, self.workflows), [])

    def test_the_refresh_workflows_are_read_as_dispatchers_that_pass_no_live_input(self):
        dispatches, problems = dispatches_of_ci(self.workflows)
        self.assertEqual(problems, [])
        self.assertTrue(KNOWN_DISPATCHERS <= set(dispatches), sorted(dispatches))
        for name in KNOWN_DISPATCHERS:
            for fields in dispatches[name]:
                self.assertNotIn(LIVE_INPUT, fields, name)

    def test_known_wrong_the_condition_before_september_27_starts_it_on_every_refresh(self):
        changed = self.ci.replace(
            "if: github.event_name == 'workflow_dispatch' && inputs.live_ollama == true",
            "if: github.event_name == 'workflow_dispatch'", 1)
        self.assertNotEqual(changed, self.ci)
        problems = live_job_problems(changed, self.workflows)
        for name in KNOWN_DISPATCHERS:
            self.assertIn(f"the dispatch of ci.yml in {name} starts the {LIVE_JOB} job", problems)
        self.assertIn(f"a dispatch with no inputs starts the {LIVE_JOB} job", problems)

    def test_known_wrong_the_text_form_of_the_input_starts_it_because_false_is_true(self):
        changed = self.ci.replace("&& inputs.live_ollama == true", "&& github.event.inputs.live_ollama", 1)
        self.assertNotEqual(changed, self.ci)
        problems = live_job_problems(changed, self.workflows)
        self.assertIn(f"a dispatch with no inputs starts the {LIVE_JOB} job", problems)

    def test_known_wrong_a_default_of_true_is_found(self):
        changed = re.sub(r"(      live_ollama:\n(?:        .*\n)*?        default: )false", r"\1true", self.ci, count=1)
        self.assertNotEqual(changed, self.ci)
        problems = live_job_problems(changed, self.workflows)
        self.assertIn(f"the {LIVE_INPUT} input is not a boolean whose default is false", problems)
        self.assertIn(f"a dispatch with no inputs starts the {LIVE_JOB} job", problems)

    def test_known_wrong_a_refresh_that_sets_the_input_is_found(self):
        workflows = dict(self.workflows)
        name = sorted(KNOWN_DISPATCHERS)[0]
        workflows[name] = workflows[name].replace("gh workflow run ci.yml --ref main",
                                                  "gh workflow run ci.yml --ref main -f live_ollama=true", 1)
        self.assertNotEqual(workflows[name], self.workflows[name])
        self.assertIn(f"the dispatch of ci.yml in {name} starts the {LIVE_JOB} job",
                      live_job_problems(self.ci, workflows))

    def test_known_wrong_a_condition_no_person_can_meet_is_found(self):
        changed = self.ci.replace("inputs.live_ollama == true", "inputs.live_ollama == 'yes'", 1)
        self.assertNotEqual(changed, self.ci)
        self.assertIn(f"a person's dispatch with {LIVE_INPUT} true does not start the {LIVE_JOB} job",
                      live_job_problems(changed, self.workflows))

    def test_known_wrong_an_unreadable_dispatch_is_reported(self):
        workflows = dict(self.workflows)
        workflows["extra.yml"] = "jobs:\n  a:\n    steps:\n      - run: gh workflow run ci.yml --json < inputs.json\n"
        problems = live_job_problems(self.ci, workflows)
        self.assertTrue(any("extra.yml dispatches ci.yml with '--json'" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
