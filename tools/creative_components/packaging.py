"""Construct original proposals for the native factory; no new store or runtime.

Discovery cards contain contracts and digests, never source bodies. Existing
preparation checks pin source revision and reject changed or uncommitted files.
"""
from __future__ import annotations

import ast
import base64
import hashlib
import inspect
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from . import primitives
from .catalogue import CASES, input_property

SOURCES = ("tools/creative_components/primitives.py", "tools/creative_components/catalogue.py",
           "tools/creative_components/packaging.py")

RUNNER = '''"""JSON-in/JSON-out launcher for the declared operation; no arbitrary dispatch."""
import json
import sys
from implementation import OPERATION

if __name__ == "__main__":
    # A bounded numeric request, not a file or script to execute.
    raw = sys.stdin.buffer.read(65537)
    if len(raw) > 65536:
        raise ValueError("input exceeds 64 KiB")
    arguments = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    if not isinstance(arguments, dict):
        raise ValueError("input must be an object")
    result = OPERATION(**arguments)
    print(json.dumps({"result": result}, allow_nan=False))
'''

CHECKS = '''"""Known answers, malformed arguments and a broken-implementation control."""
import json
import math
from pathlib import Path
import unittest
from implementation import OPERATION

CASES = json.loads((Path(__file__).parent / "verification" / "fixtures.json").read_text())

def equal(test, actual, expected):
    if isinstance(expected, list):
        test.assertIsInstance(actual, list)
        test.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            equal(test, a, b)
    else:
        test.assertTrue(math.isfinite(actual))
        test.assertAlmostEqual(actual, expected, places=9)

def verify(test, operation):
    for row in CASES["accepted"]:
        equal(test, operation(**row["arguments"]), row["expected"])

class ComponentTests(unittest.TestCase):
    def test_known_answers(self):
        verify(self, OPERATION)

    def test_invalid_values(self):
        for arguments in CASES["rejected"]:
            with self.subTest(arguments=arguments), self.assertRaises((ValueError, TypeError)):
                OPERATION(**arguments)

    def test_every_port_refuses_nonfinite_and_wrong_types(self):
        arguments = CASES["accepted"][0]["arguments"]
        for name in arguments:
            for value in (None, True, "1", float("nan"), float("inf")):
                with self.subTest(name=name, value=value), self.assertRaises((ValueError, TypeError)):
                    OPERATION(**{**arguments, name: value})

    def test_constant_zero_implementation_fails(self):
        with self.assertRaises(AssertionError):
            verify(self, lambda **arguments: 0)

if __name__ == "__main__":
    unittest.main()
'''


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def implementation(name):
    """Copy only the selected original function and its local helper closure."""
    text = inspect.getsource(primitives)
    tree = ast.parse(text)
    definitions = {entry.name: entry for entry in tree.body if isinstance(entry, ast.FunctionDef)}
    selected, pending = set(), [name]
    while pending:
        current = pending.pop()
        if current in selected:
            continue
        selected.add(current)
        pending.extend(entry.id for entry in ast.walk(definitions[current])
                       if isinstance(entry, ast.Name) and entry.id in definitions and entry.id not in selected)
    bodies = [ast.get_source_segment(text, entry) for identity, entry in definitions.items() if identity in selected]
    return ("# Original Baltor implementation; see references/provenance.json.\nimport math\n\n\n" +
            "\n\n\n".join(bodies) + f"\n\nOPERATION = {name}\n").encode()


def file_record(path, data, role, media_type):
    return {"path": path, "digest": hashlib.sha256(data).hexdigest(), "size_bytes": len(data),
            "media_type": media_type, "role": role, "content_base64": base64.b64encode(data).decode()}


def package_files(name, licence, revision, digests):
    domain, accepted, rejected = CASES[name]
    function = getattr(primitives, name)
    names = list(inspect.signature(function).parameters)
    body = implementation(name)
    example = accepted[0][1]
    output = {"type": "number"} if not isinstance(example, list) else {
        "type": "array", "items": {"type": "number"}, "minItems": len(example), "maxItems": len(example)}
    contract = {"$schema": Draft202012Validator.META_SCHEMA["$id"], "type": "object",
                "properties": {port: input_property(name, port) for port in names},
                "required": names, "additionalProperties": False}
    fixtures = {"accepted": [{"arguments": dict(zip(names, args)), "expected": expected}
                              for args, expected in accepted],
                "rejected": [dict(zip(names, args)) for args in rejected]}
    card = {"component": name, "version": "1.0.0", "purpose": inspect.getdoc(function),
            "domain": domain, "input": contract, "output": {"type": "object", "properties": {"result": output},
            "required": ["result"], "additionalProperties": False}, "implementation": {
                "path": "implementation.py", "sha256": hashlib.sha256(body).hexdigest(), "entrypoint": name},
            "dependencies": ["python>=3.10"], "effects": ["reads_fs", "spawns_process"],
            "pure_implementation": True, "qualification": "candidate_only",
            "limits": "Finite numeric inputs and finite representable outputs only. Floating-point tolerance, not cross-platform byte identity. No renderer or native engine qualification."}
    readme = (f"# {name.replace('_', ' ')}\n\n{inspect.getdoc(function)}\n\n"
              "Read contracts/operation.json first. Send its argument object to `python -B run.py` on standard input. "
              "The response is a JSON object with result. Non-finite outputs are refused. "
              "Run `python -B test_component.py` for the frozen examples and refusal controls.\n\n"
              "Compose the declared operation with existing components; change parameters rather than rewriting source. "
              "All coordinate values in one call use the same unit. Angle and time units are explicit in the contract. "
              "Coordinates and handedness follow the operation description. "
              "This candidate has no independent approval or measured creative benefit.\n").encode()
    files = [("implementation.py", body, "executable_tool", "text/x-python"),
             ("run.py", RUNNER.encode(), "executable_tool", "text/x-python"),
             ("test_component.py", CHECKS.encode(), "executable_tool", "text/x-python"),
             ("contracts/operation.json", json_bytes(card), "other", "application/json"),
             ("verification/fixtures.json", json_bytes(fixtures), "skill_asset", "application/json"),
             ("references/provenance.json", json_bytes({"source_revision": revision, "source_digests": digests,
                "authoring": "original_assistant_authored", "generator": "creative_components/v1"}),
              "other", "application/json"),
             ("AGENTS.md", readme, "instruction_file", "text/markdown"), ("LICENSE", licence, "other", "text/plain")]
    return [file_record(*entry) for entry in files]


def proposals(repository, revision):
    repository = Path(repository)
    executing_root = Path(__file__).resolve().parents[2]
    if any((repository / name).read_bytes() != (executing_root / name).read_bytes() for name in SOURCES):
        raise ValueError("selected repository differs from the executing creative generator")
    licence = (repository / "LICENSE").read_bytes()
    digests = {name: hashlib.sha256((repository / name).read_bytes()).hexdigest() for name in SOURCES}
    rows = []
    for name, (domain, _accepted, _rejected) in sorted(CASES.items()):
        rows.append({"id": f"creative_{name}", "title": name.replace("_", " ").capitalize(),
                     "purpose": inspect.getdoc(getattr(primitives, name)), "sources": list(SOURCES),
                     "layer": "code", "family": "creative_primitives", "kind": "tool",
                     "search_tags": [domain, "creative", "numeric"], "tags": {"language": ["en"]},
                     "symbols": [name], "declared_effects": ["reads_fs", "spawns_process"], "styles": ["codex"],
                     "dependencies": ["python>=3.10"], "producer": {
                         "producer_identity": "Baltor original creative component factory",
                         "family": "openai", "method_identity": "creative_components/v1"},
                     "files": package_files(name, licence, revision, digests)})
    return {"record_type": "harness_candidate_batch_proposals/v2", "source_revision": revision,
            "license": {"expression": "MIT", "path": "LICENSE", "sha256": hashlib.sha256(licence).hexdigest()},
            "sources": digests, "proposals": rows}
