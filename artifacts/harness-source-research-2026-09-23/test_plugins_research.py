"""Focused offline controls for plugin research identity, score and evidence semantics."""
import json
from decimal import Decimal
from pathlib import Path
import unittest
from unittest.mock import patch
import plugins_build_ranked as build
import plugins_rank_research as discovery


def candidate(identity,repo='owner/repository',logical=''):
 row={'artifact_id':identity,'full_name':repo,'manifest_source':(logical+'/' if logical else '')+'plugin.json',
      'bundle_path':logical,'fetch_state':'done','content_hash':'a'*24,'repo_pushed_at':'2026-09-20T00:00:00Z',
      'archived':'0','license':'MIT','stars':'20','has_root_manifest':'1','manifest_paths':'[]','source_ids':''}
 return {'research_id':identity,'repository':repo,'logical_path':logical,'row':row,'members':[row], 'conformance':None}

class ResearchControls(unittest.TestCase):
 def test_native_projection_has_same_logical_root(self):
  self.assertEqual(discovery.logical_path('plugins/demo/.cursor-plugin'),'plugins/demo')
  self.assertEqual(discovery.logical_path('.claude-plugin'),'')
  self.assertEqual(discovery.logical_path('plugins/demo'),'plugins/demo')
 def test_duplicate_manifest_keys_are_not_object_evidence(self):
  with self.assertRaises(ValueError):build.strict_json(b'{"name":"one","name":"two"}')
 def test_unpaired_surrogate_is_not_valid_metadata_text(self):
  with self.assertRaises(UnicodeError):build.strict_json(b'{"name":"\\ud800"}')
 def test_short_git_keyword_does_not_match_digital(self):
  row=build.base_score(candidate('x','owner/digital-marketing'),{})
  self.assertNotIn('code_development',row['themes'])
  self.assertIn('business_product',row['themes'])
 def test_repository_owner_does_not_create_domain(self):
  row=build.base_score(candidate('x','testing-data-security/repository'),{})
  self.assertEqual(row['themes'],['general_agent_workflow'])
 def test_same_repo_current_manifest_is_not_counted_twice(self):
  rows=[candidate('a','one/repo','a'),candidate('b','one/repo','b'),candidate('c','two/repo','a')]
  primary={x['research_id']:{'verified_body':'f'*64} for x in rows}
  with patch.object(build,'details',return_value=({},'primary_manifest_object_observed')):
   selected,_=build.choose(rows,primary,count=2)
  self.assertEqual(len(selected),2)
  self.assertEqual(len({x['repository'] for x in selected}),2)
 def test_same_repo_manifest_name_groups_native_variants(self):
  rows=[candidate('a','one/repo','a'),candidate('b','one/repo','b'),candidate('c','two/repo','a')]
  primary={x['research_id']:{'verified_body':str(i)*64} for i,x in enumerate(rows)}
  with patch.object(build,'details',return_value=({'name':'shared-logical-plugin'},'primary_manifest_object_observed')):
   selected,_=build.choose(rows,primary,count=3)
  self.assertEqual(len(selected),2)
 def test_public_observation_requires_exact_bytes_not_boolean_only(self):
  entry={'repository':'owner/repo','path':'plugin.json','revision':'a'*40,'verified_body':'b'*64,'status':200}
  state={'primary':{'p':entry},'heads':{'owner/repo':{'revision':'a'*40}}}
  public={'observations':{'p':{'same_bytes_anonymously_available':True,'status':200,'expected_digest':'b'*64,'body_digest':'c'*64,'source_url':'https://raw.githubusercontent.com/owner/repo/'+'a'*40+'/plugin.json'}}}
  safe,heads=build.public_primary(state,public)
  self.assertNotIn('verified_body',safe['p'])
  self.assertIsNone(safe['p']['revision'])
  self.assertEqual(heads,{})
 def test_score_is_exact_sum_and_caps_repository_concentration(self):
  rows=[candidate(str(i),'one/repo',str(i)) for i in range(12)]+[candidate('z','two/repo')]
  selected,_=build.choose(rows,{},count=20)
  self.assertEqual(sum(row['repository']=='one/repo' for row in selected),8)
  for row in selected:
   self.assertEqual(Decimal(str(row['priority_score'])),sum(Decimal(str(v)) for v in row['score_components'].values()))
 def test_metadata_only_is_unreviewed_unverified_and_not_license_verified(self):
  row=build.base_score(candidate('x'),{});row['score_components']['selection_diversity']=15;row['priority_score']=sum(row['score_components'].values())
  row['row'].update(is_fork='0',language='Python')
  record=build.public_record(row,1,{'artifact_snapshot_digest':'a'*64})
  self.assertEqual(record['qualification_status'],'unreviewed')
  self.assertEqual(record['compatibility_status'],'unverified')
  self.assertIs(record['license_verified'],False)
  self.assertIsNone(record['upstream_revision'])
  self.assertIsNone(record['upstream_blob_sha'])
  self.assertEqual(record['source_snapshot_kind'],'agentpluginzoo_artifacts_csv')

if __name__=='__main__':unittest.main(verbosity=2)
