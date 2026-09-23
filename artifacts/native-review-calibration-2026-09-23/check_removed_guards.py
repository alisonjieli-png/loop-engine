"""Native calibration guard controls, using fixed in-memory mutations and no provider calls."""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from candidate_review import calibration, native_calibration, review_record

spec=importlib.util.spec_from_file_location('mutation_helper',ROOT/'artifacts/candidate-review-integrity-2026-09-23/check_removed_guards.py');helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
def check(name):
 stream=io.StringIO();result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('test_candidate_review_native_calibration.NativeCalibrationTest.'+name))
 return {'passed':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors),'output':stream.getvalue()}
def main():
 cases=[('exact_package_label_binding',native_calibration,native_calibration.NativeCalibrationSet,'load',
  'row["package_digest"] != catalogue.item(identity)["reference"]["digest"]','False',
  'test_control_digest_mutation_is_refused'),
  ('false_approval_exclusion',calibration,calibration,'evaluate',
   'false_approvals = sorted(identity for identity in wrong if answers.get(identity) == APPROVE)','false_approvals = []',
   'test_approving_any_known_wrong_control_excludes_the_reviewer'),
  ('native_call_binding',review_record,review_record,'_read_calibration',
   'if (item is None or call["request_record_type"] != NATIVE_REQUEST\n                    or call["body_sha256"] != item["package_digest"]):','if False:',
   'test_export_refuses_changed_native_control_identity_and_unknown_item_versions'),
  ('excluded_reviewer_export',review_record,review_record,'read_panel_review_record',
   'if record["calibration"] is not None and any(decision["reviewer_id"] in record["calibration"]["excluded"]\n                                                     for decision in row["decisions"]):','if False:',
   'test_export_refuses_a_candidate_decision_from_a_failed_calibration_reviewer')]
 rows=[]
 for label,module,owner,name,before,after,test in cases:
  baseline=check(test);original=getattr(owner,name)
  replacement=helper.replacement(module,original,before,after)
  if isinstance(owner,type) and name=='load':replacement=classmethod(replacement.__func__ if isinstance(replacement,classmethod) else replacement)
  with mock.patch.object(owner,name,replacement):control=check(test)
  rows.append({'guard':label,'baseline':baseline,'control':control,'detected':baseline['passed'] and control['failures']>0 and control['errors']==0})
 original=native_calibration.NativeCalibrationSet.requests
 def leaked(self,*args):
  return tuple((item,request.replaced(item={**request.item,'expected_decision':item.expected_decision,'defect':item.defect})) for item,request in original(self,*args))
 for label,owner,name,replacement,test in [
  ('labels_outside_prompt',native_calibration.NativeCalibrationSet,'requests',leaked,'test_controls_are_complete_bound_packages_and_labels_never_enter_prompts'),
  ('version_refusal',native_calibration,'NATIVE_CALIBRATION_SET','candidate_native_review_calibration_set/v999','test_unknown_versions_and_unknown_label_fields_are_refused')]:
  baseline=check(test)
  with mock.patch.object(owner,name,replacement):control=check(test)
  rows.append({'guard':label,'baseline':baseline,'control':control,'detected':baseline['passed'] and control['failures']>0 and control['errors']==0})
 now=datetime.now(timezone.utc);record={'created_at':now.isoformat(),'provider_calls':0,'results':rows,'all_detected':all(row['detected'] for row in rows)}
 path=Path(__file__).parent/('removed-guards-'+now.strftime('%Y%m%dT%H%M%S%f')+'.json');path.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps({'path':str(path),'guards':len(rows),'all_detected':record['all_detected']}));return 0 if record['all_detected'] else 1
if __name__=='__main__':raise SystemExit(main())
