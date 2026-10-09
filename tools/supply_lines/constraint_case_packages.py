"""Group case data with its unchanged schema and shared local replay files."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile

from . import constraint_case_runtime as runtime
from . import schema_check
from .openapi_operations import run_tests
from .packaging import PackageFile, SupplyPackage, build
from .records import GENERATED, JSON_SCHEMAS, LICENCE_TEXT, UPSTREAM_VERBATIM, upstream_key

GENERATOR_VERSION = "1.1.0"
PRODUCER_FAMILY = "openai"
RUNNER_BYTES = Path(runtime.__file__).read_bytes()
VALIDATOR_BYTES = Path(schema_check.__file__).read_bytes()
SKILL_BYTES = b'''---
name: replay-isolated-constraint-cases
description: Replay a bundled API contract's positive baselines and isolated invalid-input cases. Use to test a validator, investigate one schema failure, or select a regression fixture; not to invoke the API or prove live provider compatibility.
license: MIT
---

# Replay isolated constraint cases

Read `constraint-group.json` to identify the exact schema, baselines and case
members. A case changes one value or removes one required field. Its expected
error names the validator, schema path and data path. Rejecting a different
field is not a passing result.

Run `python constraint_case_runtime.py .` in the package folder. Add
`--independent` only when jsonschema is already available. The command checks
resource digests before replay and reports whether the independent oracle ran.
It makes no network request and installs nothing.

Run `python -m unittest test_constraint_cases` for the package checks, including
a deliberately wrong expected target. Report passing cases, exact failures and
whether the independent oracle ran. Keep a missing dependency or changed digest
as a failure to reproduce; do not replace it with a claimed pass.

Use a selected case as a regression fixture only with its bound schema and
baseline. Keep source revision and licence information when transferring it.
These synthetic cases test schema behavior. They do not establish API access,
successful remote execution, account permissions or a current endpoint version.
'''
README_BYTES = b'''# Isolated API constraint cases

Use these cases to check one constraint failure at a time. Each case names an
exact schema and valid baseline, one JSON field/value edit, and the expected
validator, schema path and data path. The group manifest names the parent
contract and every case file.

Run `python constraint_case_runtime.py .` for local replay with the shipped
checker. If jsonschema is already installed, add `--independent` to repeat
the independent oracle check. The generator used both checkers; a replay
without that flag reports that it did not run the independent oracle.

`python -m unittest test_constraint_cases` replays every case and checks that
a wrong expectation is refused. Resource digests must match before replay.
The schemas, baseline files, runner and licences are shared by digest.

These are synthetic schema tests, not captured customer data or evidence of
API execution. They make no provider call and authorize no API operation.
Source revision and use conditions remain those of the parent contract.
'''
TEST_BYTES = b'''"""Replay every baseline/edit pair; reject a wrong expected error."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import constraint_case_runtime as runtime

class ConstraintCases(unittest.TestCase):
    def setUp(self):
        self.payloads = runtime.load_folder(HERE)
        self.group = runtime.read_group(self.payloads)

    def test_every_case_replays(self):
        for entry in self.group["cases"]:
            case = runtime.resource(self.payloads, {key: entry[key] for key in ("path", "sha256")})
            result = runtime.replay(case, self.payloads)
            self.assertTrue(result["baseline_valid"] and result["isolated_violation"])

    def test_wrong_error_target_fails(self):
        entry = self.group["cases"][0]
        case = deepcopy(runtime.resource(self.payloads, {key: entry[key] for key in ("path", "sha256")}))
        case["expected"]["shipped_path"] = "$.__wrong_target__"
        with self.assertRaises(ValueError):
            runtime.replay(case, self.payloads)

if __name__ == "__main__":
    unittest.main()
'''


def generate(parent, cases, baselines, *, revision, generated_on, staging, maximum_files=runtime.MAX_FILES):
    """Return ordinary supply candidates, with complete <=64-file closures.

    Groups stay within one parent contract; cases are ordered by property and
    constraint. A file bound can split that ordered family, never manufacture
    extra case jobs. Shared payload bytes remain byte-identical across groups.
    """
    if not 8 <= maximum_files <= runtime.MAX_FILES:
        raise ValueError("constraint_group_file_policy")
    if not cases:
        return []
    if len({row["job_id"] for row in cases}) != len(cases):
        raise ValueError("constraint_group_duplicate_case")
    payload = parent.candidate
    schema_bytes = parent.payloads["contract.schema.json"]
    if parent.payloads.get("schema_check.py") != VALIDATOR_BYTES:
        raise ValueError("constraint_parent_validator_version")
    schema = runtime.decode(schema_bytes)
    semantic = runtime.semantic_digest(schema)
    if schema.get("x-baltor-contract", {}).get("record_type") != "api_operation_contract_atom/v2":
        raise ValueError("constraint_parent_atom_version")
    licence_paths = set(payload["licence"]["texts"]) | set(payload["licence"].get("notices", []))
    parent_files = {row["path"]: row for row in payload["files"]}
    common = [PackageFile("contract.schema.json", schema_bytes, "other"),
              PackageFile("SKILL.md", SKILL_BYTES, "skill_definition"),
              PackageFile("schema_check.py", VALIDATOR_BYTES, "executable_tool"),
              PackageFile("constraint_case_runtime.py", RUNNER_BYTES, "executable_tool"),
              PackageFile("test_constraint_cases.py", TEST_BYTES, "executable_tool"),
              PackageFile("README.md", README_BYTES, "other")]
    for path in sorted(licence_paths):
        entry = parent_files[path]
        common.append(PackageFile(path, parent.payloads[path], "other", entry["origin"], entry.get("upstream"),
                                  notice=path in payload["licence"].get("notices", [])))
    cases = sorted(cases, key=lambda row: (json.dumps(row["expected"]["instance_path"]),
                                          json.dumps(row["expected"]["schema_path"]), row["job_id"]))
    # Each group includes only the baselines its cases actually reference.
    # Reserve the manifest and ATTRIBUTION.md before accepting another case.
    groups, selected, required_baselines = [], [], set()
    for case in cases:
        baseline = case["baseline"]
        path = baseline["path"]
        if path not in baselines or runtime.sha(baselines[path]) != baseline["sha256"]:
            raise ValueError("constraint_case_baseline_missing_or_changed")
        needed = required_baselines | {path}
        if selected and len(common) + len(selected) + 1 + len(needed) + 2 > maximum_files:
            groups.append((selected, required_baselines))
            selected, required_baselines, needed = [], set(), {path}
        if len(common) + len(selected) + 1 + len(needed) + 2 > maximum_files:
            raise ValueError("constraint_group_no_case_capacity")
        selected.append(case)
        required_baselines = needed
    if selected:
        groups.append((selected, required_baselines))
    outputs = []
    for selected, required_baselines in groups:
        group_baselines = {path: baselines[path] for path in sorted(required_baselines)}
        files = [*common, *(PackageFile(path, body, "other") for path, body in group_baselines.items())]
        entries = []
        for case in selected:
            path = "cases/" + case["job_id"] + ".json"
            body = runtime.encode(case)
            files.append(PackageFile(path, body, "other"))
            entries.append({"job_id": case["job_id"], "path": path, "sha256": runtime.sha(body)})
        group = {"record_type": runtime.GROUP_TYPE,
            "parent": {"record_id": parent.identity, "package_digest": parent.package.package_digest,
                       "schema_sha256": runtime.sha(schema_bytes), "semantic_sha256": semantic},
            "schema": {"path": "contract.schema.json", "sha256": runtime.sha(schema_bytes)},
            "baselines": [{"path": path, "sha256": runtime.sha(body)} for path, body in group_baselines.items()],
            "cases": entries, "case_job_set_sha256": runtime.fingerprint(sorted(row["job_id"] for row in selected)),
            "producer_family": PRODUCER_FAMILY}
        files.append(PackageFile(runtime.GROUP_FILE, runtime.encode(group), "other"))
        payloads = {file.path: file.data for file in files}
        runtime.read_group(payloads, replay_cases=True, independent=True)
        with tempfile.TemporaryDirectory(prefix="constraint-group-", dir=staging) as temporary:
            folder = Path(temporary)
            for path, body in payloads.items():
                target = folder / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
            passed, count, _tail = run_tests(folder, "constraint_cases")
        if not passed:
            raise ValueError("constraint_group_tests_failed")
        group_id = runtime.group_key(group)
        identity = "isolated_constraint_cases:" + group_id
        provenance = deepcopy(payload["provenance"])
        provenance["generator"] = {"identity": "tools/supply_lines/constraint_case_packages.py",
                                   "version": GENERATOR_VERSION, "code_revision": revision}
        built = build(SupplyPackage(line=JSON_SCHEMAS, identity=identity, key=upstream_key(JSON_SCHEMAS, identity),
            kind="contract_schema", native_format="api_constraint_cases_json", form="schema",
            name="constraint-cases-" + group_id[:24],
            description=f"Isolated constraint checks for {str(schema.get('title') or parent.identity)[:220]}; {len(selected)} case jobs.",
            files=files, licence_expression=payload["licence"]["spdx_expression"], provenance=provenance,
            placements=[{"harness": "reference", "path": "constraint-cases/" + group_id[:24] + "/",
                         "basis": "documented_layout", "scope": "project", "support": "unverified"}],
            effects=[("reads_fs", "reads_digest_bound_schema_baseline_and_case_files")], credentials=[],
            tests={"files": ["test_constraint_cases.py"], "command": "python -m unittest test_constraint_cases",
                   "result": "passed", "tests_run": count, "network": False,
                   "independent_case_checks": len(selected), "positive_baselines": len(group_baselines)},
            repository={**dict(payload.get("repository") or {}), "parent_contract": parent.identity,
                        "producer_family": PRODUCER_FAMILY}, generated_on=generated_on,
            comparison_text="\n".join(row["job_id"] for row in sorted(entries, key=lambda row: row["job_id"]))))
        if len(built[0]["package"]["files"]) > maximum_files:
            raise ValueError("constraint_group_file_bound")
        outputs.append(built)
    return outputs
