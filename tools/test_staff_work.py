"""Private work-log contracts over real managed records and loopback HTTP."""
from contextlib import ExitStack
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import asyncio
import json
import subprocess
import tempfile
import unittest
from unittest import mock

import httpx

from loop_engine.core.service_runtime import dot_pages, staff_work, http as service_http
from loop_engine.core.service_runtime.feedback_checks import prepared
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from loop_engine.core.service_runtime.records import ServiceCommitUnknown, ServiceRuntimeError

ROOT = Path(__file__).resolve().parents[1]
PAGING = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const code=fs.readFileSync('src/loop_engine/core/service_runtime/web_assets/staff-work.js','utf8');
const nodes={},paths=[],answers=[];
const $=id=>nodes[id]??={hidden:false,disabled:false,value:'',textContent:'',children:[],listeners:{},
 replaceChildren(...parts){this.children=parts;},append(...parts){this.children.push(...parts);},
 addEventListener(type,listener){this.listeners[type]=listener;},reset(){},focus(){}};
const context=vm.createContext({window:{},document:{getElementById:$},URLSearchParams});
vm.runInContext(code,context);
context.window.BaltorStaffWork.create({request:async path=>{paths.push(path);return answers.shift();},
 element:(tag,text)=>({tag,text,append(){},addEventListener(){}}),current:()=>({connected:true,allowed:true})});
const result=(page,count,more,extra={})=>({record_type:'service_staff_work_result/v1',page,limit:2,matches:5,has_next:more,
 complete:true,unreadable:[],items:Array.from({length:count},(_,i)=>({id:'staff-work:'+page+i,title:'t',kind:'research',
 task_id:'x',file_count:0})),...extra});
const click=async id=>{await $(id).listeners.click();},note=()=>$('dot-work-list-note').textContent;
(async()=>{
 $('dot-work-day').value='2026-10-05';
 answers.push(result(1,2,true));await click('dot-work-refresh');
 assert.match(paths.at(-1),/page=1/);assert.equal(note(),'Reports 1 to 2 of 5, newest first.');
 assert.equal($('dot-work-newer').hidden,true);assert.equal($('dot-work-older').hidden,false);
 $('dot-work-day').value='2026-10-04';
 answers.push(result(2,2,true));await click('dot-work-older');
 assert.match(paths.at(-1),/day=2026-10-05&page=2/);assert.equal(note(),'Reports 3 to 4 of 5, newest first.');
 assert.equal($('dot-work-newer').hidden,false);
 answers.push(result(3,1,false));await click('dot-work-older');
 assert.equal($('dot-work-older').hidden,true);assert.equal(note(),'Reports 5 to 5 of 5, newest first.');
 answers.push(result(2,2,true));await click('dot-work-newer');assert.match(paths.at(-1),/page=2/);
 answers.push(result(1,1,false,{matches:1,complete:false}));await click('dot-work-refresh');
 assert.match(paths.at(-1),/day=2026-10-04&page=1/);assert.match(note(),/may not be listed/);
 answers.push(result(1,1,false,{matches:1,complete:false,unreadable:['staff-work:bad']}));await click('dot-work-refresh');
 assert.match(note(),/1 saved report\(s\) could not be read/);
 answers.push(result(2,0,false));await click('dot-work-refresh');
 assert.equal($('dot-work-status').textContent,'The saved reports could not be read.');
 assert.equal(note(),'');assert.equal($('dot-work-older').hidden,true);assert.equal($('dot-work-newer').hidden,true);
 console.log('staff work paging controls passed');
})().catch(error=>{console.error(error);process.exitCode=1;});
'''


class StaffWorkBrowserPaging(unittest.TestCase):
    def test_actual_renderer_pages_and_states_completeness(self):
        # Known-wrong control: the earlier renderer had no page controls and
        # called a first page "All matching reports are shown". Older pages
        # the listing on screen even after the day input changes.
        result = subprocess.run(['node', '-e', PAGING], cwd=ROOT, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('staff work paging controls passed', result.stdout)


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

    def test_request_limit_changes_keep_stored_reports_readable(self):
        # Known-wrong control: when the stored policy embedded these limits,
        # each change below made the earlier report, its day and its replay fail.
        receipt=self.post().json()['result']
        for name,value in (('MAX_FILES',32),('MAX_FILE_BYTES',131072),('MAX_MESSAGE',32000),
                           ('KINDS',staff_work.KINDS+('fix',)),('LIST_LIMIT',200)):
            with self.subTest(name=name),mock.patch.object(staff_work,name,value):
                self.assertEqual(self.get({'id':receipt['id']}).status_code,200)
                listing=self.get().json()['result']
                self.assertEqual([row['id'] for row in listing['items']],[receipt['id']])
                self.assertTrue(listing['complete'])
                self.assertTrue(self.post().json()['result']['repeated'])
        with mock.patch.object(staff_work,'KINDS',staff_work.KINDS+('fix',)):
            self.assertEqual(self.post(self.fields(request_id='new-kind',kind='fix')).status_code,200)

    def test_stored_contracts_are_frozen(self):
        # Release 62 stored live reports under staff_work/v1 in this default namespace.
        self.assertEqual(self.fixture.runtime.config.namespace,'hosted-service')
        policies={contract[0]:staff_work._service(self.fixture.runtime,lambda store:(),contract).policy
                  for contract in staff_work.CONTRACTS}
        self.assertEqual({name:policy.digest for name,policy in policies.items()},
            {'staff_work/v2':'9b3ef715f10470c41309e659f0a1cab4bfbdb8ccbb1d2adde11e1f486a8933c8',
             'staff_work/v1':'97242a432c7621aefaf704476b032c0f181748f8b7fea3faf75baf7b2f59ec57'})

    def test_reports_stored_under_the_first_contract_stay_readable(self):
        with mock.patch.object(staff_work,'CONTRACTS',staff_work.CONTRACTS[1:]):
            first=self.post().json()['result']['id']
        with self.fixture.runtime._catalog.store() as store:
            self.assertEqual(store.get(first)['payload']['policy_digest'],
                             '97242a432c7621aefaf704476b032c0f181748f8b7fea3faf75baf7b2f59ec57')
        self.assertEqual(self.get({'id':first}).json()['result']['document']['title'],'Synthetic report')
        self.assertEqual([row['id'] for row in self.get().json()['result']['items']],[first])
        self.assertTrue(self.post().json()['result']['repeated'])
        self.assertEqual(self.post(self.fields(request_id='reply',kind='review',reply_to=first)).status_code,200)

    def test_listing_pages_newest_first_past_one_page(self):
        # Known-wrong control: the listing kept the first stored rows (the
        # oldest), sorted only those and had no way to reach the rest.
        with mock.patch.object(staff_work,'LIST_LIMIT',4):
            for number in range(9):
                self.post(self.fields(request_id=f'r-{number}',title=f'report {number}',links=[],files=[]))
            pages=[self.get({'task_id':'customer-journeys'}).json()['result']]
            self.assertEqual([row['title'] for row in pages[0]['items']],['report 8','report 7','report 6','report 5'])
            pages+=[self.get({'task_id':'customer-journeys','page':page}).json()['result'] for page in ('2','3')]
        self.assertEqual([[row['title'][-1] for row in page['items']] for page in pages],
                         [['8','7','6','5'],['4','3','2','1'],['0']])
        self.assertEqual([(page['page'],page['has_next'],page['matches'],page['complete']) for page in pages],
                         [(1,True,9,True),(2,True,9,True),(3,False,9,True)])
        for wrong in ('0','-1','x','1.5','',' 1','123456'):
            with self.subTest(page=wrong):self.assertEqual(self.get({'page':wrong}).status_code,400)
        self.assertEqual(self.get({'id':pages[0]['items'][0]['id'],'page':'1'}).status_code,400)

    def test_listing_states_when_the_stored_query_bound_is_reached(self):
        bounded=(('staff_work/v2',staff_work._SHAPE,5),staff_work.CONTRACTS[1])
        with mock.patch.object(staff_work,'CONTRACTS',bounded):
            for number in range(5):
                self.post(self.fields(request_id=f'r-{number}',links=[],files=[]))
                listing=self.get().json()['result']
                self.assertEqual((listing['matches'],listing['complete']),(number+1,number<4))

    def test_unreadable_report_is_named_without_failing_the_listing(self):
        good=self.post().json()['result']['id']
        foreign=self.post(self.fields(request_id='foreign')).json()['result']['id']
        damaged=self.post(self.fields(request_id='damaged')).json()['result']['id']
        with self.fixture.runtime._catalog.store(write=True) as store:
            head=store.get(foreign);head['payload']['policy_digest']='0'*64;store.put(head)
            body=store.get(damaged)['payload']['revision_ref']['digest']
        for path in (self.root/'domain'/'staff-work-revisions').rglob(body):path.unlink()
        listing=self.get().json()['result']
        self.assertEqual([row['id'] for row in listing['items']],[good])
        self.assertEqual(listing['unreadable'],sorted([foreign,damaged]))
        self.assertFalse(listing['complete'])
        self.assertEqual(self.get({'id':foreign}).json()['error']['code'],'work_record_unavailable')


if __name__ == '__main__':
    unittest.main()
