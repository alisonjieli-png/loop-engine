"""Named negative controls fail when their local guard is bypassed in memory."""
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import preview
from test_preview import PreviewTests, request

MUTANTS = (
    ("mandatory_role", "_roles_supported", lambda *args: True, "test_unsupported_mandatory_role_refuses"),
    ("same_target", "_paths_disjoint", lambda *args: None, "test_two_packages_claim_same_target_refuses"),
    ("parent_file", "_paths_disjoint", lambda *args: None, "test_parent_file_collision_refuses"),
    ("payload_bytes", "_payloads_bound", lambda item: dict(item.payloads), "test_same_size_payload_change_refuses"),
    ("current_state", "_snapshots_match", lambda *args: True, "test_stale_expected_current_refuses"),
    ("worker_authority", "_effects_within", lambda *args: True, "test_worker_effects_cannot_expand"),
    ("post_preview_state", "_snapshots_match", lambda *args: True, "test_revalidation_refuses_changes_after_preview"),
)
rows=[]
for name,guard,replacement,test in MUTANTS:
    stream=io.StringIO()
    with patch.object(preview,guard,replacement):
        result=unittest.TextTestRunner(stream=stream,verbosity=0).run(unittest.TestSuite([PreviewTests(test)]))
    rows.append({"mutant":name,"guard":guard,"check":test,"detected":not result.wasSuccessful(),
                 "failures":len(result.failures),"errors":len(result.errors)})
selected=request(); compiled=preview.BaltorPreviewEngine().compile(selected)
print(json.dumps({"record_type":"working_directory_compiler_experiment_checks/v1",
                  "mutants":rows,"all_detected":all(row["detected"]for row in rows),
                  "example":{"status":compiled.status,"digest":compiled.digest,
                             "files":[f.reference()for f in compiled.files],
                             "native_qualified":compiled.native_qualified,"writes_performed":compiled.writes_performed},
                  "model_calls":0,"workspace_writes":0,"admitted_profiles":0},indent=2))
raise SystemExit(0 if all(row["detected"]for row in rows)else 1)
