"""Independent local staff-work guards; synthetic identities, no remote providers."""
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

import httpx
from loop_engine.core.service_runtime import staff_work,dot_pages,feedback,http as service_http
from loop_engine.core.service_runtime.feedback_checks import prepared
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.records import (ServiceCommitUnknown,ServiceRuntimeError,
    ServiceRuntimeConfig,TenantRegistration,TenantKeyIssue,ACCESS_MANAGE_SCOPE,digest)
from loop_engine.core.service_runtime.runtime import ServiceRuntime
from loop_engine.core.service_runtime.storage import ServiceCatalogBinding
from loop_engine.core.service_runtime.account_administration import AccountAdministration
from loop_engine.core.service_runtime.account_policy import ServiceAccountPolicy,StaffMember
from loop_engine.core.service_runtime.protocol_checks import _protocol_client
from tools import test_oauth_http as oauth_fixtures


def work_fields(identity):
    brief=dot_pages.load_record('context')
    return {'request_id':identity,'brief':'context','brief_revision':dot_pages.revision(brief),
            'task_id':brief['tasks'][0]['id'],'kind':'test_result','title':'Synthetic peer result',
            'message':'PRIVATE_WORK_FIXTURE','links':['https://example.invalid/proof?x=1#part'],
            'files':[{'name':'proof.py','content':'\ufeff# café\r\nraise RuntimeError("inert attachment")\n'}],'reply_to':''}


def record_id(runtime,actor,identity):
    return staff_work.PREFIX+digest([runtime.config.namespace,actor,identity])


def head(runtime,actor,identity):
    with runtime._catalog.store() as store:return store.get(record_id(runtime,actor,identity))


class StaffWorkPeerTests(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack();self.addCleanup(self.stack.close)
        self.folder=Path(self.stack.enter_context(tempfile.TemporaryDirectory(prefix='staff-work-peer-')))
        self.fixture=prepared(self.folder/'domain');self.runtime=self.fixture.runtime
        self.base,self.app=self.stack.enter_context(running_http(self.fixture))
        self.client=self.stack.enter_context(httpx.Client(base_url=self.base,trust_env=False,timeout=20))

    def post(self,identity='one',tenant='operator',**changes):
        return self.client.post(staff_work.PATH,headers=self.fixture.headers(tenant),
            json={'record_type':staff_work.REQUEST_VERSION,**work_fields(identity),**changes})

    def mcp(self,name,arguments,tenant='operator'):
        async def run():
            async with _protocol_client(self.base,self.fixture,'2026-07-28',tenant=tenant) as client:
                return await client.call_tool(name,arguments)
        return asyncio.run(run())

    def test_create_exact_replay_conflict_reply_and_file_bytes(self):
        created=self.post();self.assertEqual(created.status_code,200,created.text)
        value=created.json()['result'];self.assertFalse(value['repeated']);self.assertFalse(value['promotes_intelligence'])
        replay=self.post().json()['result'];self.assertTrue(replay['repeated']);self.assertEqual(replay['id'],value['id'])
        self.assertEqual(self.post(message='changed').status_code,400)
        held=self.client.get(staff_work.PATH,headers=self.fixture.headers('operator'),params={'id':value['id']}).json()['result']
        file=held['document']['files'][0];original=work_fields('one')['files'][0]['content']
        self.assertEqual(file['content'],original);self.assertEqual(file['bytes'],len(original.encode()))
        self.assertEqual(file['sha256'],hashlib.sha256(original.encode()).hexdigest())
        reply=self.post('reply',reply_to=value['id'],files=[]).json()['result']
        self.assertNotEqual(reply['id'],value['id'])
        self.assertEqual(held['record_version'],'1')
        self.assertEqual(self.post('forged',actor='someone-else').status_code,400)

    def test_ordinary_authority_denied_before_larger_body_is_read(self):
        with mock.patch.object(self.app,'_body',side_effect=AssertionError('unauthorized body read')):
            self.assertEqual(self.post('customer',tenant='alpha').status_code,403)
        self.assertEqual(self.client.get(staff_work.PATH).status_code,401)
        self.assertEqual(self.client.get(staff_work.PATH,headers=self.fixture.headers('beta')).status_code,403)
        self.assertTrue(self.mcp('staff_work_submit',work_fields('customer-mcp'),'alpha').is_error)

    def test_mcp_closed_read_schema_and_http_query_match(self):
        self.assertEqual(self.post().status_code,200)
        for value in (None,[],{},False,0,''):
            with self.subTest(value=value):self.assertTrue(self.mcp('staff_work_read',{'task_id':value}).is_error)
        self.assertFalse(self.mcp('staff_work_read',{}).is_error)
        self.assertEqual(self.client.get(staff_work.PATH,headers=self.fixture.headers('operator'),params=[('day','2026-10-01'),('day','2026-10-02')]).status_code,400)

    def test_brief_revalidated_at_head_write_and_removed_guard_control(self):
        original=staff_work._AuthorizedCatalog.put
        brief=dot_pages.load_record('context');changed={**brief,'summary':brief['summary']+' new revision'}
        def race(store,record,**kwargs):
            with mock.patch.object(dot_pages,'load_record',return_value=changed):return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',race):
            self.assertEqual(self.post('stale-race').status_code,400)
        self.assertIsNone(head(self.runtime,'operator','stale-race'))
        def unsafe(store,record,**kwargs):
            store.before_write=None
            with mock.patch.object(dot_pages,'load_record',return_value=changed):return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',unsafe):
            self.assertEqual(self.post('known-wrong-stale').status_code,200)
        self.assertIsNotNone(head(self.runtime,'operator','known-wrong-stale'))

    def test_key_revocation_at_head_write_and_removed_guard_control(self):
        original=staff_work._AuthorizedCatalog.put
        def race(store,record,**kwargs):
            self.runtime.revoke_key('operator',self.fixture.keys['operator'].key_id)
            return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',race):self.assertEqual(self.post('revoked').status_code,401)
        self.assertIsNone(head(self.runtime,'operator','revoked'))
        self.fixture.keys['operator']=self.runtime.issue_key(TenantKeyIssue('operator','replacement synthetic key'))
        def unsafe(store,record,**kwargs):
            self.runtime.revoke_key('operator',self.fixture.keys['operator'].key_id)
            store.authorize=lambda _store:()
            return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',unsafe):self.assertEqual(self.post('known-wrong-revoked').status_code,401)
        self.assertIsNotNone(head(self.runtime,'operator','known-wrong-revoked'))

    def test_unknown_commit_reconciles_without_duplicate(self):
        commit=ServiceCatalogBinding.commit
        def lost(binding,store,records,guards,removals=()):
            answer=commit(binding,store,records,guards,removals)
            if any(row.get('source_collection')=='staff_work' for row in records):raise ServiceCommitUnknown()
            return answer
        with mock.patch.object(ServiceCatalogBinding,'commit',lost):response=self.post('unknown')
        self.assertEqual(response.status_code,503)
        self.assertEqual(response.json()['effect_commitment'],'not_asserted')
        self.assertFalse(response.json()['automatic_retry'])
        self.assertIsNotNone(head(self.runtime,'operator','unknown'))
        replay=self.post('unknown');self.assertEqual(replay.status_code,200);self.assertTrue(replay.json()['result']['repeated'])

    def test_concurrent_same_identity_is_one_head(self):
        original=staff_work._AuthorizedCatalog.put;barrier=threading.Barrier(2)
        def together(store,record,**kwargs):barrier.wait(10);return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',together),ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda _:self.post('concurrent'),range(2)))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        self.assertTrue(self.post('concurrent').json()['result']['repeated'])

    def test_larger_profile_is_route_specific_and_utf8_byte_bounded(self):
        files=[{'name':str(n)+'.txt','content':'x'*65536} for n in range(4)]
        answer=self.post('full-limit',files=files);self.assertEqual(answer.status_code,200,answer.text)
        selected=self.client.get(staff_work.PATH,headers=self.fixture.headers('operator'),params={'id':answer.json()['result']['id']})
        self.assertEqual(selected.status_code,200);self.assertEqual(len(selected.json()['result']['document']['files']),4)
        self.assertEqual(self.post('unicode-over',files=[{'name':'wide.txt','content':'😀'*17000}]).status_code,400)
        self.assertEqual(self.post('traversal',files=[{'name':'../escape.py','content':'inert'}]).status_code,400)
        self.assertEqual(self.post('nul',files=[{'name':'nul.txt','content':'\0'}]).status_code,400)
        ordinary=self.client.post('/api/v1/provisioning',headers=self.fixture.headers('alpha'),json={
            'record_type':'service_provisioning_request/v2','operation':'search','query':'x'*65536})
        self.assertEqual(ordinary.status_code,413)

    def test_private_content_never_enters_public_brief(self):
        before={name:dot_pages.revision(dot_pages.load_record(name)) for name in ('context','feedback')}
        self.assertEqual(self.post().status_code,200)
        for name,expected in before.items():
            response=self.client.get('/dot-'+name+'.json')
            self.assertEqual(response.status_code,200);self.assertNotIn('PRIVATE_WORK_FIXTURE',response.text)
            self.assertEqual(dot_pages.revision(response.json()),expected)


class StaffWorkBrowserAuthorityPeerTests(unittest.TestCase):
    def setUp(self):
        self.case=oauth_fixtures.HttpOAuthIntegration('test_origin_browser_and_admin_guards')
        self.addCleanup(self.case.doCleanups);self.case.setUp()
        self.admin=AccountAdministration(self.case.fixture.runtime,ServiceAccountPolicy(staff=(
            StaffMember('superadmin',email='synthetic@example.invalid'),)),self.case.identity_base+'/auth/v1')
        self.case.app.account_administration=self.admin

    def post(self,identity,headers=None):
        return self.case.client.post(staff_work.PATH,headers=headers or self.case.browser_headers,
            json={'record_type':staff_work.REQUEST_VERSION,**work_fields(identity)})

    def test_browser_staff_not_inherited_by_same_identity_oauth(self):
        self.assertEqual(self.post('browser').status_code,200)
        token=self.case.issue()['access_token'];headers=self.case.bearer(token)
        self.assertEqual(self.post('oauth',headers).status_code,403)
        self.assertEqual(self.case.client.get(staff_work.PATH,headers=headers).status_code,403)
        async def check():
            async with _protocol_client(self.case.base,oauth_fixtures.Credentials(token),'2026-07-28') as client:
                self.assertTrue((await client.call_tool('staff_work_submit',work_fields('oauth-mcp'))).is_error)
        asyncio.run(check())

    def test_demotion_before_write_prevents_head(self):
        original=staff_work._AuthorizedCatalog.put
        def demote(store,record,**kwargs):
            self.admin.policy=ServiceAccountPolicy(staff=(StaffMember('analytics',email='synthetic@example.invalid'),))
            return original(store,record,**kwargs)
        with mock.patch.object(staff_work._AuthorizedCatalog,'put',demote):self.assertEqual(self.post('demote').status_code,403)
        self.assertIsNone(head(self.case.fixture.runtime,self.case.tenant,'demote'))

    def test_private_read_rechecks_role_after_serialization(self):
        identity=self.post('read-race').json()['result']['id'];original=service_http._json_bytes
        def demote(value):
            encoded=original(value)
            if value.get('result',{}).get('document'):
                self.admin.policy=ServiceAccountPolicy(staff=(StaffMember('analytics',email='synthetic@example.invalid'),))
            return encoded
        with mock.patch.object(service_http,'_json_bytes',demote):
            response=self.case.client.get(staff_work.PATH,headers=self.case.browser_headers,params={'id':identity})
        self.assertEqual(response.status_code,403);self.assertNotIn('PRIVATE_WORK_FIXTURE',response.text)


class StaffWorkNamespacePeerTests(unittest.TestCase):
    def test_same_logical_actor_request_in_other_host_namespace_is_independent(self):
        with tempfile.TemporaryDirectory() as folder:
            rows=[];bindings=[]
            for namespace in ('peer-one','peer-two'):
                runtime=ServiceRuntime(ServiceRuntimeConfig(str(Path(folder)/'service.db'),namespace=namespace,writes_authorized=True))
                runtime.register_tenant(TenantRegistration('operator','private:'+namespace,(ACCESS_MANAGE_SCOPE,)))
                key=runtime.issue_key(TenantKeyIssue('operator','namespace fixture'))
                principal=runtime.authenticate_key(key.key);service=feedback.ServiceFeedback(runtime)
                authorize=lambda store,service=service,principal=principal:service._authorize_staff_view(store,principal,None,None)
                rows.append(staff_work.submit(runtime,authorize,'operator',work_fields('same-request')))
                bindings.append((runtime,authorize))
            self.assertNotEqual(rows[0]['id'],rows[1]['id'])
            with self.assertRaises(ServiceRuntimeError):staff_work.read(*bindings[0],{'id':rows[1]['id']})


if __name__=='__main__':unittest.main()
