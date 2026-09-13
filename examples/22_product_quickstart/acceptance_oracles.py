"""Task-owned oracle fixtures; observations execute against frozen real subjects.

Only criterion identifiers are bound from the runtime's verifier packet. Expected
values and programs are authored here, never copied from candidate observations.
These model replies test the complete verification mechanism, not model quality.
"""
from __future__ import annotations

import json
from dataclasses import replace

from loop_engine.code_nodes.solution_model_port import (
    FixtureModelExecutionRequest, fixture_model_execution,
)


_PRELUDE = """import json, shutil, subprocess, sys, tempfile
from pathlib import Path
subject = Path('subject').resolve()
"""

_PROBES = {
    "expenses": (_PRELUDE + """with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    data = [{'category':'Food','amount':2.5}, {'category':'Travel','amount':-3}, {'category':'Food','amount':7.5}]
    (root/'input.json').write_text(json.dumps(data))
    subprocess.run([sys.executable,str(subject/'expense_report.py'),str(root/'input.json'),str(root/'report.md')],check=True,capture_output=True)
    print(json.dumps((root/'report.md').read_text().strip()))
""", "# Expense report\n\n- Food: 10.00\n- Travel: -3.00"),
    "inventory": (_PRELUDE + """import csv
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    shutil.copy2(subject/'transform.py',root/'transform.py')
    (root/'inputs').mkdir()
    (root/'inputs/inventory.csv').write_text('sku,product_name,quantity\\nSKU-A,   sIlVer  PaRt,5\\nSKU-B,BETA,6\\n')
    subprocess.run([sys.executable,'transform.py'],cwd=root,check=True,capture_output=True)
    with (root/'cleaned.csv').open(newline='') as stream:
        rows=list(csv.DictReader(stream))
    print(json.dumps({'rows':rows,'summary':(root/'summary.md').read_text().strip()}))
""", {"rows": [
        {"sku": "SKU-A", "product_name": "Silver Part", "quantity": "5", "low_stock": "yes"},
        {"sku": "SKU-B", "product_name": "Beta", "quantity": "6", "low_stock": "no"}],
        "summary": "# Inventory summary\n\nRows: 2\n\nLow stock: 1"}),
    "documents": (_PRELUDE + """with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    shutil.copy2(subject/'index_docs.py',root/'index_docs.py')
    (root/'inputs/docs').mkdir(parents=True)
    (root/'inputs/docs/gamma.md').write_text('# Gamma manual\\n\\nA new document.\\n\\n## Usage\\n')
    subprocess.run([sys.executable,'index_docs.py'],cwd=root,check=True,capture_output=True)
    print(json.dumps((root/'index.md').read_text().strip()))
""", "# Document index\n\n## Gamma manual\n\nPath: inputs/docs/gamma.md\n\nHeadings: Usage\n\nSummary: A new document."),
    "repair": (_PRELUDE + """import importlib.util
spec=importlib.util.spec_from_file_location('observed_calc',subject/'repaired_package/calc.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
print(json.dumps([module.add(2,7),module.add(-3,2),module.add(1.5,2.5)]))
""", [9, -1, 4.0]),
}


def probe_answers(case: str) -> tuple[dict, ...]:
    source, expected = _PROBES[case]
    plan = {"status": "ready", "notes": "Probe new inputs against the frozen implementation.",
            "files": [{"path": "checks/probe.py", "purpose": "Observe the actual subject on independent inputs."}],
            "cases": [{"case_id": "independent-inputs", "criterion_refs": [],
                       "purpose": "Observe task behavior independently of producer verification.",
                       "argv": ["python", "checks/probe.py"], "timeout_seconds": 30,
                       "comparison": "json_equal", "expected": expected}]}
    review = {"valid": True, "criterion_refs": [], "issues": [],
              "notes": "The fixture oracle executes the frozen implementation on separate inputs."}
    return tuple({"acceptance_fixture_for": kind, "response": response} for kind, response in (
        ("independent_probe_design/v1", plan),
        ("independent_probe_file/v1", {"path": "checks/probe.py", "content": source}),
        ("independent_probe_review/v1", review)))


def bind_response(answer: str, prompt: str) -> str:
    value = json.loads(answer)
    if not isinstance(value, dict) or "acceptance_fixture_for" not in value:
        return answer
    packet = json.loads(prompt)
    if packet.get("record_type") != value["acceptance_fixture_for"]:
        raise ValueError("acceptance fixture does not match the actual verifier phase")
    criteria = packet.get("registered_acceptance_criteria")
    if not isinstance(criteria, dict) or not criteria:
        raise ValueError("actual verifier packet must contain registered criteria")
    response = value["response"]
    if value["acceptance_fixture_for"] == "independent_probe_design/v1":
        for case in response["cases"]:
            case["criterion_refs"] = list(criteria)
    elif value["acceptance_fixture_for"] == "independent_probe_review/v1":
        response["criterion_refs"] = list(criteria)
    return json.dumps(response)


def model_execution(answers: tuple[str, ...]):
    """Bind task-owned fixture replies behind the canonical ModelGateway."""
    execution = fixture_model_execution(FixtureModelExecutionRequest(
        answers=answers, max_model_calls=len(answers)))
    provider = execution.gateway.providers["fixture"]
    base = provider.adapter

    class BoundFixture:
        DEFAULT_MODEL = base.DEFAULT_MODEL
        output_capability_for = staticmethod(base.output_capability_for)
        verify = staticmethod(base.verify)
        live_models = staticmethod(base.live_models)

        @staticmethod
        def chat_maxout(prompt, **kwargs):
            result = base.chat_maxout(prompt, **kwargs)
            result.text = bind_response(result.text, prompt)
            return result

    execution.gateway.providers["fixture"] = replace(provider, adapter=BoundFixture)
    return execution


def negative_answers(answers: tuple[str, ...], control: str) -> tuple[str, ...]:
    """Plant a producer-self-test blind spot or an undeclared dependency."""
    rows = [json.loads(answer) for answer in answers]
    changed = 0
    for row in rows:
        if control == "wrong_math" and row.get("path") == "expense_report.py":
            original = row["content"]
            row["content"] = original.replace('float(row["amount"])', 'abs(float(row["amount"]))')
            changed += row["content"] != original
        elif control == "undeclared_dependency" and row.get("record_type") == "generated_project_candidate/v1":
            original = row["expected_artifacts"]
            row["expected_artifacts"] = [item for item in original if item["path"] != "sample.json"]
            changed += len(row["expected_artifacts"]) != len(original)
    if changed != 1:
        raise ValueError("negative acceptance control did not change exactly one fixture boundary")
    if control == "undeclared_dependency":
        # Freezing refuses before verifier model work; later semantic replies
        # must still match their real phases instead of consuming oracle plans.
        rows = [row for row in rows if "acceptance_fixture_for" not in row]
    return tuple(json.dumps(row) for row in rows)
