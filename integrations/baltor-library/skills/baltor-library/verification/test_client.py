"""Offline transport fixtures only. No request can reach a socket."""
import importlib.util,io,json,os,sys,unittest
from email.message import Message
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
path=Path(os.environ.get('BALTOR_CLIENT_UNDER_TEST',ROOT/'scripts/baltor.py'))
spec=importlib.util.spec_from_file_location('baltor_client',path);client=importlib.util.module_from_spec(spec);sys.modules[spec.name]=client;spec.loader.exec_module(client)
TOKEN='fixture-credential-not-a-real-key'
def config():return {'record_type':'baltor_library_client_configuration/v2','origin':'https://baltor.example','credential_environment':'TEST_BALTOR_ACCESS','authority_effects':['reads_fs']}
def capabilities():return {'record_type':'service_capabilities/v1','api_version':'v1','retrieval':{'request_record_type':'service_retrieval_request/v2','modes':['lexical'],'returns_bodies':False},'library':{'provisioning_request_record_types':['service_provisioning_request/v1','service_provisioning_request/v2'],'step_effects':['reads_fs','writes_fs','reads_secret','network','spawns_process']},'delivery':{'download_endpoint':'/api/v1/download','package_files':'download_by_path','body_format':'utf8_text','download_bytes':8*1024*1024},'limits':{'search_results':50,'request_bytes':65536,'response_bytes':16*1024*1024}}
def envelope(result,operation='capabilities',version='service_http_result/v1'):return json.dumps({'record_type':version,'operation':operation,'result':result}).encode()
class Response(io.BytesIO):
 def __init__(self,body,headers=None,status=200,url=None):
  super().__init__(body);self.status=status;self.headers=Message();self.url=url
  for k,v in (headers or {'Content-Type':'application/json'}).items():
   for part in (v if isinstance(v,list) else [v]):self.headers[k]=part
 def geturl(self):return self.url or 'https://baltor.example/api/v1/capabilities'
class Transport:
 def __init__(self,*responses):self.responses=list(responses);self.requests=[]
 def open(self,request,timeout):
  self.requests.append(request)
  if not self.responses:raise AssertionError('Unexpected extra request')
  response=self.responses.pop(0)
  if isinstance(response,Exception):raise response
  if response.url is None:response.url=request.full_url
  return response
class ContractTests(unittest.TestCase):
 def test_current_service_envelope_allows_handshake(self):
  transport=Transport(Response(envelope(capabilities())))
  c=client.Client(config(),TOKEN,transport)
  self.assertEqual(c.handshake()['api_version'],'v1')
  self.assertIsNone(transport.requests[0].get_header('Authorization'))

import ast
import copy
import tempfile
from unittest import mock

def file_entry(path,data,role='skill_reference',media='text/plain'):
 return {'path':path,'digest':client.sha(data),'size_bytes':len(data),'media_type':media,'role':role}
def package(files,form='package'):
 rows=sorted([file_entry(path,data) for path,data in files.items()],key=lambda row:row['path'])
 raw=json.dumps({'record_type':'catalogue_package/v1','files':rows},sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
 return {'body_form':form,'package_digest':client.sha(raw),'files':rows},raw

def search_record(digest,summary,ident='sample',allowed=True):
 return {'record_type':'service_retrieval_result/v1','bodies_loaded':False,'hits':[{'reference':{'record_type':'provisioning_item_binding/v1','identity':ident,'source_layer':'harness_local','source_ref':'fixture','body_digest':digest,'descriptor_digest':'3'*64},'body_allowed':allowed,'package':summary,'declared_effects':['reads_fs'],'library_tier':'verified'}]}
def binary(data,digest=None,version='service_download/v1'):
 return Response(data,{'Content-Type':'application/octet-stream','X-Loop-Engine-Record-Type':version,'X-Content-SHA256':digest or client.sha(data)})
def manifest(digest,size,allowed=True,ident='sample',version='provisioning_manifest/v3'):
 return Response(envelope({'record_type':version,'identity':ident,'digest':digest,'size_bytes':size,'body_allowed':allowed,'declared_effects':['reads_fs'],'library_tier':'verified'},'manifest'))
def ready(*responses,cfg=None):
 t=Transport(Response(envelope(capabilities())),*responses);c=client.Client(cfg or config(),TOKEN,t);c.handshake();return c,t

def assert_refusal(test,code,call):
 with test.assertRaises(client.Refusal) as caught:call()
 test.assertEqual(caught.exception.code,code)
 return caught.exception

class OfflineTests(unittest.TestCase):
 def setUp(self):
  self.socket_guard=mock.patch('socket.create_connection',side_effect=AssertionError('Network forbidden in offline tests'));self.socket_guard.start()
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup();self.socket_guard.stop()
 def test_versions_and_operations_refuse_without_followup(self):
  for version,op in [('service_result/v1','capabilities'),('service_http_result/v2','capabilities'),('service_http_result/v1','other')]:
   with self.subTest(version=version,op=op):
    t=Transport(Response(envelope(capabilities(),op,version)));c=client.Client(config(),TOKEN,t)
    assert_refusal(self,'service_envelope_unsupported',c.handshake);self.assertEqual(len(t.requests),1)
 def test_capability_changes_refuse_before_private_request(self):
  for field,value,code in [('retrieval',{'request_record_type':'service_retrieval_request/v3'},'retrieval_version'),('delivery',{},'delivery_unsupported'),('library',{'provisioning_request_record_types':[]},'provisioning_version'),('limits',{},'limits_invalid')]:
   with self.subTest(field=field):
    cap=capabilities();cap[field]=value;t=Transport(Response(envelope(cap)));c=client.Client(config(),TOKEN,t)
    assert_refusal(self,code,c.handshake);self.assertEqual(len(t.requests),1)
 def test_configuration_rejects_literal_secret_and_bad_origins(self):
  cfg=config();cfg['token']=TOKEN
  assert_refusal(self,'configuration_shape',lambda:client.validate_configuration(cfg))
  for origin in ['http://baltor.example','https://name:secret@baltor.example','https://baltor.example/','https://baltor.example?token=x','https://baltor.example\\evil']:
   cfg=config();cfg['origin']=origin
   assert_refusal(self,'https_origin_required',lambda:client.validate_configuration(cfg))
 def test_missing_token_refuses_authenticated_exchange(self):
  t=Transport();c=client.Client(config(),'',t)
  assert_refusal(self,'credential_missing_or_invalid',lambda:c.exchange('/api/v1/retrieval',{}));self.assertFalse(t.requests)
 def test_duplicate_json_and_nonfinite_refused(self):
  for raw in [b'{"a":1,"a":2}',b'{"x":NaN}',b'{"x":Infinity}']:
   with self.subTest(raw=raw):
    with self.assertRaises(client.Refusal):client.parse_json(raw)
 def test_json_response_media_type_is_checked(self):
  t=Transport(Response(envelope(capabilities()),{'Content-Type':'text/html'}));c=client.Client(config(),TOKEN,t)
  assert_refusal(self,'json_media_type_required',c.handshake)
 def test_explicit_empty_effects_are_preserved(self):
  cfg=config();cfg['authority_effects']=[];result={'record_type':'service_retrieval_result/v1','bodies_loaded':False,'hits':[]}
  c,t=ready(Response(envelope(result,'retrieval')),cfg=cfg);self.assertEqual(c.search('review dataset',3),result)
  sent=json.loads(t.requests[-1].data);self.assertEqual(sent['authority_effects'],[]);self.assertNotIn('library_tiers',sent);self.assertEqual(sent['record_type'],'service_retrieval_request/v2');self.assertEqual(len(t.requests),2)
 def test_search_loaded_bodies_and_wrong_result_version_are_refused(self):
  for result in [{'record_type':'service_retrieval_result/v1','bodies_loaded':True,'hits':[]},{'record_type':'service_retrieval_result/v9','bodies_loaded':False,'hits':[]}]:
   c,t=ready(Response(envelope(result,'retrieval')));assert_refusal(self,'retrieval_result_invalid',lambda:c.search('query',1));self.assertEqual(len(t.requests),2)
 def test_search_duplicate_identity_is_refused(self):
  row=search_record('1'*64,None);row['hits'].append(copy.deepcopy(row['hits'][0]))
  c,_=ready(Response(envelope(row,'retrieval')));assert_refusal(self,'reference_invalid',lambda:c.search('query',2))
 def test_escaped_credential_is_not_returned(self):
  value=capabilities();value['note']=TOKEN
  raw=envelope(value).replace(TOKEN.encode(),b'\\u0066'+TOKEN[1:].encode());self.assertNotIn(TOKEN.encode(),raw)
  c=client.Client(config(),TOKEN,Transport(Response(raw)));assert_refusal(self,'credential_echo_refused',c.handshake)
 def test_error_codes_are_useful_without_server_messages(self):
  raw=json.dumps({'record_type':'service_http_error/v1','error':{'code':'body_forbidden','message':'PRIVATE SERVER MESSAGE'},'request_reference':'ref_abc123','automatic_retry':False}).encode()
  c,_=ready(Response(raw,status=403));error=assert_refusal(self,'service_refused:body_forbidden',lambda:c.manifest('sample','1'*64))
  self.assertEqual(error.reference,'ref_abc123');self.assertNotIn('PRIVATE',json.dumps(error.details()))
 def test_redirect_is_not_followed(self):
  c,t=ready(Response(envelope(capabilities()),url='https://other.example/'))
  assert_refusal(self,'redirect_refused',lambda:c.result('/api/v1/provisioning',{'operation':'manifest'}));self.assertEqual(len(t.requests),2)
  assert_refusal(self,'redirect_refused',lambda:client.NoRedirect().redirect_request(None,None,None,None,None,None))
 def test_request_size_refuses_before_post(self):
  c,t=ready();c.capabilities['limits']['request_bytes']=10
  assert_refusal(self,'request_too_large',lambda:c.search('query',1));self.assertEqual(len(t.requests),1)
 def test_multi_file_download_is_exact_and_idempotency_identity_is_stable(self):
  files={'SKILL.md':b'# Example\n','assets/raw.bin':b'\x00\xff\x01'};summary,doc=package(files);digest=client.sha(doc)
  c,t=ready(manifest(digest,len(doc)),binary(doc),*[binary(files[row['path']]) for row in summary['files']])
  out=self.base/'result';receipt=client.fetch(c,'sample',digest,'logical-123',out,search_record(digest,summary))
  self.assertTrue(receipt['complete']);self.assertFalse(receipt['installed']);self.assertFalse(receipt['executed']);self.assertEqual(receipt['usage_commitment'],'not_asserted')
  for name,data in files.items():self.assertEqual((out/'payload'/name).read_bytes(),data)
  sent=[json.loads(r.data) for r in t.requests if r.full_url.endswith('/download')]
  self.assertEqual(len(sent),3);self.assertEqual({r['request_id'] for r in sent},{'logical-123'});self.assertEqual({r['expected_digest'] for r in sent},{digest});self.assertFalse(t.responses)
 def test_file_body_json_that_looks_like_package_is_never_expanded(self):
  data=b'{"record_type":"catalogue_package/v1","files":[{"path":"../../escape"}]}'
  summary,_=package({'reference.json':data},'file');digest=client.sha(data);c,t=ready(manifest(digest,len(data)),binary(data))
  receipt=client.fetch(c,'sample',digest,'one-file',self.base/'out',search_record(digest,summary))
  self.assertEqual((self.base/'out/payload/reference.json').read_bytes(),data);self.assertEqual(len(t.requests),3);self.assertEqual(receipt['files'][0]['path'],'reference.json')
 def test_null_package_metadata_keeps_opaque_body(self):
  data=b'{"record_type":"catalogue_package/v99","files":[]}'
  digest=client.sha(data);c,t=ready(manifest(digest,len(data)),binary(data))
  result=client.fetch(c,'sample',digest,'opaque',self.base/'out',search_record(digest,None))
  self.assertEqual(result['files'][0]['role'],'unassigned');self.assertFalse((self.base/'out/payload').exists());self.assertEqual(len(t.requests),3)
 def test_missing_package_summary_is_refused(self):
  value=search_record('1'*64,None);del value['hits'][0]['package'];c,t=ready()
  assert_refusal(self,'reference_invalid',lambda:client.fetch(c,'sample','1'*64,'req',self.base/'out',value));self.assertEqual(len(t.requests),1)
 def test_stale_manifest_stops_before_metered_download(self):
  c,t=ready(manifest('2'*64,4));assert_refusal(self,'manifest_binding_mismatch',lambda:client.fetch(c,'sample','1'*64,'req',self.base/'out',search_record('1'*64,None)))
  self.assertEqual(len(t.requests),2);self.assertFalse((self.base/'out').exists())
 def test_changed_selection_stops_before_manifest(self):
  summary,doc=package({'a':b'hello'});c,t=ready()
  assert_refusal(self,'selection_package_mismatch',lambda:client.fetch(c,'sample','1'*64,'req',self.base/'out',search_record('1'*64,summary)));self.assertEqual(len(t.requests),1)
 def test_unsafe_package_paths_and_roles_refuse(self):
  for path in ['../escape','/absolute','.git/config','.GiT/config','a//b','a/./b','a\\b']:
   with self.subTest(path=path):
    summary,_=package({path:b'a'});assert_refusal(self,'package_path',lambda:client.package_entries(summary))
  for files in [{'A':b'a','a':b'b'},{'a':b'a','a/b':b'b'}]:
   summary,_=package(files);assert_refusal(self,'package_path_collision',lambda:client.package_entries(summary))
  summary,_=package({'a':b'x'});summary['files'][0]['media_type']='not-a-media-type';assert_refusal(self,'package_role',lambda:client.package_entries(summary))
 def test_entire_file_tree_is_checked_before_download(self):
  summary,doc=package({'a':b'a','z/../bad':b'b'});c,t=ready()
  assert_refusal(self,'package_path',lambda:client.fetch(c,'sample',client.sha(doc),'req',self.base/'out',search_record(client.sha(doc),summary)));self.assertEqual(len(t.requests),1)
 def test_host_download_ceiling_blocks_before_usage_request(self):
  summary,doc=package({'a':b'a'*2000});digest=client.sha(doc);c,t=ready(manifest(digest,len(doc)));c.capabilities['delivery']['download_bytes']=1000
  assert_refusal(self,'download_exceeds_host_limit',lambda:client.fetch(c,'sample',digest,'req',self.base/'out',search_record(digest,summary)));self.assertEqual(len(t.requests),2);self.assertFalse((self.base/'out').exists())
 def test_wrong_duplicate_or_truncated_downloads_do_not_finish(self):
  data=b'correct';digest=client.sha(data)
  choices=[binary(b'wrong!!',digest),binary(data[:-1],digest),binary(data+b'!',digest),binary(data,digest,version='service_download/v2'),Response(data,{'Content-Type':'application/octet-stream','X-Loop-Engine-Record-Type':'service_download/v1','X-Content-SHA256':[digest,digest]})]
  for i,response in enumerate(choices):
   with self.subTest(i=i):
    c,t=ready(manifest(digest,len(data)),response)
    with self.assertRaises(client.Refusal):client.fetch(c,'sample',digest,'same-id',self.base/str(i),search_record(digest,None))
    failure=json.loads((self.base/str(i)/'failure.json').read_text());self.assertFalse(failure['complete']);self.assertEqual(failure['request_id'],'same-id');self.assertEqual(failure['usage_commitment'],'not_asserted');self.assertFalse((self.base/str(i)/'receipt.json').exists());self.assertEqual(len(t.requests),3)
 def test_partial_failure_and_explicit_retry_keep_logical_id(self):
  files={'a':b'first','b':b'second'};summary,doc=package(files);digest=client.sha(doc)
  c,t=ready(manifest(digest,len(doc)),binary(doc),binary(files['a']),OSError('transport with private details'))
  assert_refusal(self,'transport_failed',lambda:client.fetch(c,'sample',digest,'logical-77',self.base/'failed',search_record(digest,summary)))
  failed=json.loads((self.base/'failed/failure.json').read_text());self.assertEqual(len(failed['files']),1);self.assertFalse(failed['complete']);self.assertNotIn('private details',json.dumps(failed));self.assertEqual(len(t.requests),5)
  later,again=ready(manifest(digest,len(doc)),binary(doc),binary(files['a']),binary(files['b']))
  done=client.fetch(later,'sample',digest,'logical-77',self.base/'retry',search_record(digest,summary));self.assertTrue(done['complete'])
  self.assertEqual({json.loads(r.data)['request_id'] for r in t.requests+again.requests if r.full_url.endswith('/download')},{'logical-77'})
 def test_failed_path_response_does_not_claim_no_usage(self):
  summary,doc=package({'a':b'a'});digest=client.sha(doc);raw=json.dumps({'record_type':'service_http_error/v1','error':{'code':'package_file_not_found'}}).encode()
  c,t=ready(manifest(digest,len(doc)),binary(doc),Response(raw,status=404))
  assert_refusal(self,'service_refused:package_file_not_found',lambda:client.fetch(c,'sample',digest,'one-logical',self.base/'out',search_record(digest,summary)))
  self.assertEqual(json.loads((self.base/'out/failure.json').read_text())['usage_commitment'],'not_asserted');self.assertEqual(len(t.requests),4)
 def test_existing_output_is_not_overwritten(self):
  out=self.base/'out';out.mkdir();(out/'sentinel').write_text('keep');data=b'hello';digest=client.sha(data);c,t=ready(manifest(digest,len(data)))
  assert_refusal(self,'output_exists',lambda:client.fetch(c,'sample',digest,'req',out,search_record(digest,None)));self.assertEqual((out/'sentinel').read_text(),'keep');self.assertEqual(len(t.requests),2)
 def test_symlink_ancestry_and_preexisting_payload_link_cannot_escape(self):
  outside=self.base/'outside';outside.mkdir();link=self.base/'link';link.symlink_to(outside,target_is_directory=True)
  with self.assertRaises(client.Refusal):
   with client.new_output(link/'out'):pass
  self.assertFalse((outside/'out').exists())
  with client.new_output(self.base/'safe') as out:
   (self.base/'safe/payload').symlink_to(outside,target_is_directory=True)
   assert_refusal(self,'output_write_failed',lambda:out.write('payload/escape',b'x'))
   assert_refusal(self,'output_path_invalid',lambda:out.write('../escape',b'x'))
  self.assertFalse((outside/'escape').exists());self.assertFalse((self.base/'escape').exists())
 def test_selected_access_refusal_makes_no_manifest_request(self):
  c,t=ready();assert_refusal(self,'selected_body_not_allowed',lambda:client.fetch(c,'sample','1'*64,'req',self.base/'out',search_record('1'*64,None,allowed=False)));self.assertEqual(len(t.requests),1)
 def test_argument_error_does_not_echo_a_secret(self):
  stderr=io.StringIO()
  with mock.patch('sys.stderr',stderr):code=client.main(['--token',TOKEN])
  self.assertEqual(code,2);self.assertNotIn(TOKEN,stderr.getvalue());self.assertIn('arguments_invalid',stderr.getvalue())
 def test_credential_in_query_refuses_before_post(self):
  c,t=ready();assert_refusal(self,'credential_echo_refused',lambda:c.search(TOKEN,1));self.assertEqual(len(t.requests),1)

class CliTests(unittest.TestCase):
 def test_search_cli_uses_env_reference_and_outputs_reusable_selection(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'config.json';path.write_text(json.dumps(config()))
   result=search_record('1'*64,None);transport=Transport(Response(envelope(capabilities())),Response(envelope(result,'retrieval')))
   original=client.Client
   output=type('Capture',(),{'buffer':io.BytesIO()})()
   with mock.patch.dict(os.environ,{'TEST_BALTOR_ACCESS':TOKEN}),mock.patch.object(client,'Client',side_effect=lambda cfg,key:original(cfg,key,transport)),mock.patch('sys.stdout',output):
    code=client.main(['--config',str(path),'search','query','--limit','1'])
   self.assertEqual(code,0);self.assertEqual(json.loads(output.buffer.getvalue()),result);self.assertNotIn(TOKEN.encode(),output.buffer.getvalue())
 def test_missing_credential_stops_cli_before_transport(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'config.json';path.write_text(json.dumps(config()));error=io.StringIO()
   with mock.patch.dict(os.environ,{'TEST_BALTOR_ACCESS':''}),mock.patch.object(client,'Client') as constructor,mock.patch('sys.stderr',error):
    code=client.main(['--config',str(path),'search','query'])
   self.assertEqual(code,2);constructor.assert_not_called();self.assertIn('credential_missing_or_invalid',error.getvalue())
 def test_download_flag_is_required_before_transport(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'config.json';path.write_text(json.dumps(config()));error=io.StringIO()
   with mock.patch.dict(os.environ,{'TEST_BALTOR_ACCESS':TOKEN}),mock.patch.object(client,'Client') as constructor,mock.patch('sys.stderr',error):
    code=client.main(['--config',str(path),'fetch','--identity','sample','--digest','1'*64,'--selection',str(Path(temp)/'selection.json'),'--request-id','req','--output',str(Path(temp)/'out')])
   self.assertEqual(code,2);constructor.assert_not_called();self.assertIn('download_authority_required',error.getvalue())

class UnifiedDefaultTests(unittest.TestCase):
 def test_unified_config_and_all_requests_omit_tier_selector(self):
  cfg=config();cfg.pop('library_tiers',None);cfg['record_type']='baltor_library_client_configuration/v2'
  data=b'hello';digest=client.sha(data);result=search_record(digest,None)
  t=Transport(Response(envelope(capabilities())),Response(envelope(result,'retrieval')),manifest(digest,len(data)),binary(data))
  c=client.Client(cfg,TOKEN,t);c.handshake();c.search('query',1);c.manifest('sample',digest);self.assertEqual(c.download('sample',digest,'req',digest,len(data)),data)
  for request in t.requests[1:]:
   sent=json.loads(request.data);self.assertNotIn('library_tiers',sent);self.assertEqual(sent['authority_effects'],cfg['authority_effects'])
 def test_retired_configuration_version_is_refused(self):
  cfg=config();cfg.pop('library_tiers',None);cfg['record_type']='baltor_library_client_configuration/v1'
  assert_refusal(self,'configuration_version',lambda:client.validate_configuration(cfg))

class IndependentFindingRegressions(unittest.TestCase):
 def test_binding_version_and_descriptor_are_checked(self):
  for field,value in [('record_type','provisioning_item_binding/v2'),('record_type',None),('descriptor_digest','bad')]:
   answer=search_record('1'*64,None);answer['hits'][0]['reference'][field]=value
   c,_=ready(Response(envelope(answer,'retrieval')))
   with self.subTest(field=field,value=value),self.assertRaises(client.Refusal):c.search('query',1)
 def test_unknown_wire_tier_or_unrequested_effect_is_refused(self):
  for field,value in [('library_tier','unknown'),('declared_effects',['spawns_process'])]:
   cfg=config();answer=search_record('1'*64,None);answer['hits'][0][field]=value
   c,_=ready(Response(envelope(answer,'retrieval')),cfg=cfg)
   with self.subTest(field=field),self.assertRaises(client.Refusal):c.search('query',1)
 def test_printable_credential_with_json_escapes_cannot_be_echoed(self):
  key='synthetic-quote-"-backslash-\\-credential'
  for value in [{'echo':key},{key:'value'}, {'nested':[{'value':key}]}]:
   answer=capabilities();answer.update(value);c=client.Client(config(),key,Transport(Response(envelope(answer))))
   with self.subTest(value_type=list(value)),self.assertRaises(client.Refusal):c.handshake()

if __name__=='__main__':unittest.main()
