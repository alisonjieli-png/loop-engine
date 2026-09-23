"""Read the explicitly selected frozen successor; use fixture reviewers only."""
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT=Path(sys.argv[1]).resolve()
sys.path[:0]=[str(ROOT),str(ROOT/'tools'),str(ROOT/'src')]
from candidate_review import review_record
from candidate_review.records import CandidateReviewError,digest,VERDICT_RECORD
from test_candidate_review_native_calibration import calibrated_native_record

def check(record):
    try:review_record.read_panel_review_record(record,allow_fixture=True)
    except CandidateReviewError as error:return {'accepted':False,'code':error.code}
    return {'accepted':True}

failed=calibrated_native_record(bypass_failed_reviewer=True)
changed=deepcopy(failed)
changed['calibration']['excluded'].pop('b-zhipu')
changed['ineligible_reviewers']=[row for row in changed['ineligible_reviewers']if row['installation_id']!='b-zhipu']
good=calibrated_native_record()
wrong_prompt=deepcopy(good)
call=wrong_prompt['calibration']['calls'][0]
call['prompt_sha256']='0'*64
call['review_key']=digest({'installation_sha256':call['installation_sha256'],
    'request_sha256':call['request_sha256'],'prompt_sha256':call['prompt_sha256'],
    'record_type':VERDICT_RECORD,'request_record_type':call['request_record_type']})
for verdict in wrong_prompt['calibration']['verdicts']:
    if (verdict['run_id'],verdict['sequence'])==(call['run_id'],call['sequence']):verdict['review_key']=call['review_key']
print(json.dumps({'model_calls':0,'fixture_only':True,'source_root':str(ROOT),
    'consistent_failed_reviewer':check(failed),'remove_both_exclusion_lists':check(changed),
    'retained_false_approvals':changed['calibration']['installations']['b-zhipu']['false_approvals'],
    'valid_record':check(good),'unmeasured_author_status':good['calibration']['installations']['a-openai']['status'],
    'unmeasured_author_candidate_calls':sum(c['installation_id']=='a-openai'for c in good['calls']),
    'rebound_fake_prompt_digest':check(wrong_prompt)},indent=2))
