"""Fixture-only second-phase check: a reviewer skipped for control authorship is unmeasured."""
import json
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'src')]
from candidate_review import calibration,native_profile,panel
from candidate_review.ledger import ReviewLedger
from candidate_review.reviewers.fixture import FixtureReviewer
from test_candidate_review_native_calibration import loaded,decision
from test_candidate_review_native import fixture,load_request
from test_candidate_review_panel import _configuration,_installation,_bound_fixture_script

chosen,pairs,criteria,instructions=loaded()
labels={item.identity:item.expected_decision for item in chosen.items}
config=native_profile.configuration(_configuration([_installation(name,family)for name,family in
    [('a-openai','openai'),('b-zhipu','zhipu'),('c-alibaba','alibaba'),('d-minimax','minimax')]]))
reviewers={}
for installation in config.installations:
    callback=lambda prompt,number:decision(prompt,labels.get(prompt.identity,'approve'))
    reviewers[installation.installation_id]=FixtureReviewer(installation,_bound_fixture_script(callback,installation.model))
with tempfile.TemporaryDirectory() as directory:
    worker=panel.ReviewPanel(config,criteria,instructions,reviewers,native_profile.engines(config),ReviewLedger(Path(directory)/'ledger.jsonl'))
    calibration_result=worker.run(panel.PanelRunRequest('calibration',tuple(r for _,r in pairs),{},20,3000000,True,
        fixture_run=True,ask_every_eligible_reviewer=True))
    evaluated=calibration.evaluate(chosen,calibration_result)
    fixture(Path(directory)/'candidate');catalogue,request,_=load_request(Path(directory)/'candidate')
    candidate=worker.run(panel.PanelRunRequest('candidate',(request,),catalogue.population_bodies(),4,1000000,True,
        fixture_run=True,excluded_installations=evaluated['excluded']))
print(json.dumps({'model_calls':0,'fixture_only':True,
    'calibration_openai_calls':sum(c['installation_id']=='a-openai'for c in calibration_result.calls),
    'calibration_ineligible':calibration_result.ineligible,'evaluated_excluded':evaluated['excluded'],
    'calibration_status_for_openai':evaluated['installations'].get('a-openai'),
    'candidate_openai_calls':sum(c['installation_id']=='a-openai'for c in candidate.calls),
    'candidate_outcome':candidate.items[0].outcome,'candidate_reviewers':[v['reviewer_id']for v in candidate.items[0].verdicts]},indent=2))
