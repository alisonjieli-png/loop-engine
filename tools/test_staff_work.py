"""Private work-log contracts over real managed records and loopback HTTP."""
from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import asyncio
import json
import tempfile
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime import dot_pages, staff_work, http as service_http
from loop_engine.core.service_runtime.feedback_checks import prepared
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from loop_engine.core.service_runtime.records import ServiceCommitUnknown, ServiceRuntimeError


class StaffWork(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.fixture = prepared(self.root/'domain')
        self.base, self.app = self.stack.enter_context(running_http(self.fixture))
        self.client = self.stack.enter_context(httpx.Client(base_url=self.base, trust_env=False, timeout=20))

    def fields(self, **changes):
        return {'request_id':'test-one', 'brief':'context',
                'brief_revision':dot_pages.revision(dot_pages.load_record('context')),
                'task_id':'customer-journeys', 'kind':'test_result', 'title':'Synthetic report',
                'message':'A synthetic finding, not customer data.', 'links':['https://example.org/source'],
                'files':[{'name':'scripts/example.py', 'content':'print("synthetic")\r\n'}], 'reply_to':'', **changes}

    def post(self, fields=None, tenant='operator'):
        return self.client.post(staff_work.PATH, headers=self.fixture.headers(tenant),
            json={'record_type':staff_work.REQUEST_VERSION, **(self.fields() if fields is None else fields)})

    def get(self, fields=None, tenant='operator'):
        return self.client.get(staff_work.PATH, headers=self.fixture.headers(tenant), params=fields or {})

    def test_create_replay_detail_and_listing(self):
        first = self.post(); self.assertEqual(first.status_code, 200, first.text)
        receipt = first.json()['result']
        self.assertTrue(receipt['committed']); self.assertFalse(receipt['promotes_intelligence'])
        repeat = self.post().json()['result']
        self.assertTrue(repeat['repeated']); self.assertEqual(receipt['id'], repeat['id'])
        detail = self.get({'id':receipt['id']}).json()['result']['document']
        file = detail['files'][0]
        self.assertEqual(file['content'], self.fields()['files'][0]['content'])
        self.assertEqual(file['sha256'], sha256(file['content'].encode()).hexdigest())
        self.assertEqual(len(self.get().json()['result']['items']), 1)
        self.assertFalse((self.root/'domain'/'scripts'/'example.py').exists())

    def test_reports_are_managed_immutable_revisions(self):
        receipt = self.post().json()['result']
        with self.fixture.runtime._catalog.store() as store:
            head = store.get(receipt['id'])
        self.assertEqual(head['payload']['record_type'], 'managed_record_head/v1')
        self.assertEqual(head['lifecycle'], 'candidate')
        self.assertEqual(head['source_collection'], 'staff_work')
        self.assertTrue(list((self.root/'domain'/'staff-work-revisions').rglob('*')))

    def test_conflicting_request_does_not_replace_original(self):
        receipt = self.post().json()['result']
        response = self.post(self.fields(message='Changed report'))
        self.assertEqual(response.json()['error']['code'], 'work_request_identity_conflict')
        self.assertEqual(self.get({'id':receipt['id']}).json()['result']['document']['message'], self.fields()['message'])

    def test_reply_preserves_parent_and_current_task(self):
        parent = self.post().json()['result']['id']
        self.assertEqual(self.post(self.fields(request_id='reply', kind='review', reply_to=parent)).status_code, 200)
        wrong = self.post(self.fields(request_id='wrong-reply', task_id='creative-proof', reply_to=parent))
        self.assertEqual(wrong.json()['error']['code'], 'work_reply_target_invalid')
        self.assertEqual(len(self.get().json()['result']['items']), 2)

    def test_stale_new_request_refuses_but_exact_old_replay_survives(self):
        fields = self.fields(); self.assertEqual(self.post(fields).status_code, 200)
        original = dot_pages.load_record('context')
        with mock.patch.object(dot_pages, 'load_record', return_value={**original, 'summary':'New revision'}):
            self.assertTrue(self.post(fields).json()['result']['repeated'])
            bad = self.post({**fields,'request_id':'new'})
            self.assertEqual(bad.json()['error']['code'], 'work_brief_changed')

    def test_anonymous_and_ordinary_accounts_cannot_read_or_submit(self):
        self.assertEqual(self.client.get(staff_work.PATH).status_code, 401)
        self.assertEqual(self.get(tenant='alpha').status_code, 403)
        self.assertEqual(self.post(tenant='alpha').status_code, 403)
        self.assertFalse((self.root/'domain'/'staff-work-revisions').exists())

    def test_unknown_versions_and_authority_fields_refuse(self):
        for extra in ({'actor':'operator'}, {'tenant_id':'alpha'}, {'namespace':'other'}, {'record_type':'future/v99'}):
            response = self.post(self.fields(**extra))
            self.assertEqual(response.status_code, 400)
        self.assertEqual(self.get().json()['result']['items'], [])

    def test_attachment_paths_and_binary_content_refuse(self):
        for name in ('/etc/passwd','../outside','a/../outside','a\\outside','a//b','.', 'x\ny'):
            with self.subTest(name=name):
                self.assertEqual(self.post(self.fields(files=[{'name':name,'content':'x'}])).status_code,400)
        self.assertEqual(self.post(self.fields(files=[{'name':'x.bin','content':'\x00'}])).status_code,400)
        self.assertEqual(self.post(self.fields(files=[{'name':'x.py','content':'x'}]*2)).status_code,400)

    def test_utf8_bound_and_crlf_bom_are_preserved(self):
        content = '\ufeffhello\r\n雪'
        receipt = self.post(self.fields(files=[{'name':'unicode.txt','content':content}])).json()['result']
        file = self.get({'id':receipt['id']}).json()['result']['document']['files'][0]
        self.assertEqual(file['content'], content)
        self.assertEqual(file['bytes'], len(content.encode('utf-8')))
        too_big = self.fields(request_id='large', files=[{'name':'x.txt','content':'雪'*21846}])
        self.assertEqual(self.post(too_big).json()['error']['code'], 'work_submission_limit')

    def test_scoped_transport_accepts_full_file_without_expanding_normal_requests(self):
        fields = self.fields(files=[{'name':'large.txt','content':'a'*65536}])
        response = self.post(fields); self.assertEqual(response.status_code,200,response.text)
        ordinary = self.client.post('/api/v1/provisioning', headers=self.fixture.headers(),
                                   json={'record_type':'service_provisioning_request/v2','operation':'request_material','request_id':'x','description':'a'*66000})
        self.assertEqual(ordinary.status_code,413)
        forbidden = self.post(fields, tenant='alpha')
        self.assertEqual(forbidden.status_code,403)

    def test_limits_and_unknown_read_fields_refuse(self):
        for fields in ({'day':'2026-1-1'}, {'task_id':''}, {'other':'x'}, {'id':'elsewhere:abc'}, {'id':'staff-work:'+'0'*64,'day':'2026-10-01'}):
            self.assertEqual(self.get(fields).status_code,400)
        self.assertEqual(self.client.get(staff_work.PATH+'?day=2026-10-01&day=2026-10-02',headers=self.fixture.headers('operator')).status_code,400)
        for fields in (self.fields(files=[{'name':str(i),'content':'x'} for i in range(17)]),self.fields(message='x'*16001)):
            self.assertEqual(self.post(fields).status_code,400)

    def test_links_are_metadata_only_and_disallow_credentials(self):
        for value in ('http://example.org','https://user:password@example.org','file:///tmp/x','javascript:alert(1)'):
            self.assertEqual(self.post(self.fields(links=[value])).status_code,400)
        with mock.patch('urllib.request.urlopen', side_effect=AssertionError('No URL fetch')):
            self.assertEqual(self.post(self.fields(links=['https://example.invalid/no-fetch'])).status_code,200)

    def test_authorization_is_checked_at_commit(self):
        original = staff_work._AuthorizedCatalog.put
        def revoke(store, *args, **kwargs):
            self.fixture.runtime.revoke_key('operator', self.fixture.operator_key.key_id)
            return original(store, *args, **kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog, 'put', revoke):
            self.assertEqual(self.post().status_code,401)
        from loop_engine.catalog.query import IntelligenceQuery
        with self.fixture.runtime._catalog.store() as store:
            self.assertEqual(store.query(IntelligenceQuery(source_collections=('staff_work',))), [])

    def test_brief_change_at_commit_refuses(self):
        original = staff_work._AuthorizedCatalog.put
        record = dot_pages.load_record('context')
        def stale(store, *args, **kwargs):
            with mock.patch.object(dot_pages, 'load_record', return_value={**record,'summary':'changed at commit'}):
                return original(store, *args, **kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog, 'put', stale):
            self.assertEqual(self.post().json()['error']['code'],'work_brief_changed')
        self.assertEqual(self.get().json()['result']['items'],[])

    def test_private_read_rechecks_after_serialization(self):
        self.post(); original = service_http._json_bytes; done=[]
        def encode(value):
            result = original(value)
            if not done and value.get('result',{}).get('record_type')==staff_work.RESULT_VERSION:
                done.append(True); self.fixture.runtime.revoke_key('operator',self.fixture.operator_key.key_id)
            return result
        with mock.patch.object(service_http, '_json_bytes', encode):
            response=self.get()
        self.assertEqual(response.status_code,401)
        self.assertNotIn('Synthetic report',response.text)

    def test_mcp_reports_and_malformed_filters(self):
        async def run():
            for mode in ('legacy','2026-07-28'):
                async with _protocol_client(self.base,self.fixture,mode,tenant='operator') as client:
                    result=await client.call_tool('staff_work_submit',self.fields())
                    self.assertFalse(result.is_error)
                    for wrong in ([],None,False,0):
                        result=await client.call_tool('staff_work_read',{'task_id':wrong})
                        self.assertTrue(result.is_error)
            async with _protocol_client(self.base,self.fixture,'2026-07-28',tenant='alpha') as client:
                self.assertTrue((await client.call_tool('staff_work_read',{})).is_error)
        asyncio.run(run())

    def test_host_limits_are_validated(self):
        for field in ('maximum_staff_work_request_bytes','maximum_staff_work_response_bytes'):
            for value in (0,True,1.5,1048577):
                with self.assertRaises(ValueError): replace(self.app.configuration,**{field:value})

    def test_managed_metadata_fits_after_near_limit_encoded_upload(self):
        fields=self.fields(title='x',message='x',links=[],files=[{'name':str(i)+'.txt','content':'\n'*65536} for i in range(4)])
        def encoded():
            return json.dumps({'record_type':staff_work.REQUEST_VERSION,**fields},separators=(',',':'),ensure_ascii=False).encode()
        maximum=self.app.configuration.maximum_staff_work_request_bytes
        over=len(encoded())-maximum+2
        fields['files'][-1]['content']=fields['files'][-1]['content'][:-(over+1)//2]
        raw=encoded();self.assertLessEqual(len(raw),maximum)
        answer=self.client.post(staff_work.PATH,headers={**self.fixture.headers('operator'),'Content-Type':'application/json'},content=raw)
        self.assertEqual(answer.status_code,200,answer.text)
        self.assertEqual(self.get({'id':answer.json()['result']['id']}).status_code,200)


if __name__ == '__main__':
    unittest.main()
