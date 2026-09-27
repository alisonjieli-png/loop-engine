"""Fresh signup keeps private state and never repeats uncertain creation effects.

The real journal and fresh-only command run against synthetic browser/mail
adapters. No network, provider credential or live account is used.
"""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

CHECKS = r'''
import {readFileSync,writeFileSync,existsSync,mkdtempSync,statSync,chmodSync,rmSync,symlinkSync,mkdirSync} from "node:fs";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {pathToFileURL} from "node:url";
import {randomUUID,randomBytes} from "node:crypto";
import assert from "node:assert/strict";
const root=process.argv[2],{runFreshOnly,readFreshState,FreshJourneyError,isConfirmationSender}=await import(pathToFileURL(join(root,"tools/fresh_account_journey.mjs")));
const origin="https://baltor.ai",privatePassword="synthetic-password-only",privateInbox="synthetic-inbox-only",privateToken="synthetic-token-only";
const account={authentication_mode:"browser_identity",tenant_id:"observed-fixture-tenant",entitlement:"metadata",access_source:"none"};
const folders=[],results=[];
const folder=()=>{const value=mkdtempSync(join(tmpdir(),"fresh-journey-check-"));folders.push(value);return value;};
const test=async(name,run)=>{try{await run();results.push({name,passed:true});}catch(error){results.push({name,passed:false,reason:error.message});}};
await test("current_mail_sender_is_accepted_and_lookalike_domains_are_refused",async()=>{
 for(const address of ["accounts@mail.baltor.ai","accounts@auth.baltor.ai","accounts@baltor.ai"])assert.equal(isConfirmationSender(address),true);
 for(const address of ["accounts@mail.baltor.ai.evil.invalid","accounts@notbaltor.ai","accounts@other.baltor.ai",null,""])assert.equal(isConfirmationSender(address),false);
});
const fixture=()=>{
 const path=join(folder(),"state.json"),calls={prepare:0,createInbox:0,authorizeInbox:0,signup:0,waitForLink:0,confirm:0,signin:0};
 const observed=stage=>{const state=readFreshState(path,origin);assert.equal(state.stage,stage);assert.equal(state.fresh.password,privatePassword);assert.equal(statSync(path).mode&0o777,0o600);};
 const actions={prepare:async()=>{calls.prepare++;return {fresh:{address:"baltor-check-fixture@inbox.invalid",password:privatePassword},mailbox:{address:"baltor-check-fixture@inbox.invalid",password:privateInbox}};},
 createInbox:async()=>{calls.createInbox++;observed("mailbox_create_pending");return {id:"observed-fixture-mailbox"};},
 authorizeInbox:async()=>{calls.authorizeInbox++;observed("mailbox_created");return privateToken;},
 signup:async()=>{calls.signup++;observed("signup_pending");},
 waitForLink:async()=>{calls.waitForLink++;observed("signup_sent");return origin+"/auth/confirm?token_hash=synthetic-link-only";},
 confirm:async()=>{calls.confirm++;observed("confirmation_pending");return account;},
 signin:async()=>{calls.signin++;observed("signin_pending");return account;}};
 return {path,calls,actions,run:(resume,extra={})=>runFreshOnly({statePath:path,origin,resume,actions,...extra})};
};
await test("state_precedes_effects_and_fresh_only_ends_successfully_without_a_free_plan",async()=>{
 const f=fixture(),report=await f.run(false);assert.equal(report.stage,"complete");assert.deepEqual(report.account,account);
 for(const value of [privatePassword,privateInbox,privateToken,"synthetic-link-only"])assert.ok(!JSON.stringify(report).includes(value));
 assert.equal(f.calls.createInbox,1);assert.equal(f.calls.signup,1);assert.equal(f.calls.confirm,1);assert.equal(f.calls.signin,1);
 assert.ok(!existsSync(f.path+".lock"));assert.ok(!("confirmation_link" in readFreshState(f.path,origin)));
});
await test("resume_after_sent_email_reuses_the_same_inbox_account_and_email",async()=>{
 const f=fixture(),wait=f.actions.waitForLink;f.actions.waitForLink=async()=>{throw new Error(privateToken);};
 await assert.rejects(f.run(false),e=>e.code==="fresh_step_failed"&&e.stage==="signup_sent"&&!e.message.includes(privateToken));
 f.actions.waitForLink=wait;assert.equal((await f.run(true)).stage,"complete");
 assert.equal(f.calls.prepare,1);assert.equal(f.calls.createInbox,1);assert.equal(f.calls.signup,1);
});
await test("unknown_creation_signup_and_confirmation_are_never_repeated",async()=>{
 for(const [operation,pending] of [["createInbox","mailbox_create_pending"],["signup","signup_pending"],["confirm","confirmation_pending"]]){
  const f=fixture(),original=f.actions[operation];f.actions[operation]=async()=>{await original();throw new Error(privatePassword);};
  await assert.rejects(f.run(false),e=>e.stage===pending);
  const before={...f.calls};await assert.rejects(f.run(true),e=>e.code==="unknown_effect_requires_reconciliation"&&e.stage===pending);assert.deepEqual(f.calls,before);
 }
});
await test("known_created_mailbox_and_confirmed_customer_resume_without_recreating",async()=>{
 for(const operation of ["authorizeInbox","signin"]){
  const f=fixture(),original=f.actions[operation];f.actions[operation]=async()=>{throw new Error("temporary");};
  await assert.rejects(f.run(false));f.actions[operation]=original;assert.equal((await f.run(true)).stage,"complete");
  assert.equal(f.calls.createInbox,1);assert.equal(f.calls.signup,1);assert.equal(f.calls.confirm,1);
 }
});
await test("existing_state_needs_explicit_resume_and_complete_resume_has_no_effects",async()=>{
 const f=fixture(),first=await f.run(false),before={...f.calls};await assert.rejects(f.run(false),e=>e.code==="existing_state_requires_resume");
 const resumed=await f.run(true);assert.equal(resumed.completed_at,first.completed_at);assert.deepEqual(f.calls,before);
});
await test("closed_registration_creates_nothing_but_an_existing_customer_can_resume",async()=>{
 const f=fixture();await assert.rejects(f.run(false,{registrationOpen:false}),e=>e.code==="registration_closed");assert.equal(f.calls.prepare,0);assert.equal(f.calls.createInbox,0);
 const g=fixture(),wait=g.actions.waitForLink;g.actions.waitForLink=async()=>null;
 await assert.rejects(g.run(false),e=>e.code==="confirmation_email_not_received");g.actions.waitForLink=wait;
 assert.equal((await g.run(true,{registrationOpen:false})).stage,"complete");assert.equal(g.calls.signup,1);
});
await test("state_permissions_origin_and_confirmation_origin_are_enforced",async()=>{
 const f=fixture();await f.run(false);chmodSync(f.path,0o644);await assert.rejects(f.run(true),e=>e.code==="private_state_permissions_required");chmodSync(f.path,0o600);
 assert.throws(()=>readFreshState(f.path,"https://other.invalid"),e=>e.code==="private_state_binding_refused");
 const g=fixture();g.actions.waitForLink=async()=>"https://other.invalid/auth/confirm?secret=synthetic";
 await assert.rejects(g.run(false),e=>e.code==="confirmation_address_refused");assert.equal(g.calls.confirm,0);
});
await test("fresh_signin_must_observe_the_confirmed_account",async()=>{
 const f=fixture();f.actions.signin=async()=>({...account,tenant_id:"different-fixture"});await assert.rejects(f.run(false),e=>e.code==="fresh_signin_account_mismatch");assert.equal(readFreshState(f.path,origin).stage,"signin_pending");
});
await test("resumed_confirmation_link_is_checked_again_before_disclosing_password",async()=>{
 const f=fixture();await f.run(false);const state=readFreshState(f.path,origin);
 state.stage="confirmation_ready";state.confirmation_link="https://outside.invalid/auth/confirm?token=synthetic";
 writeFileSync(f.path,JSON.stringify(state));const before={...f.calls};
 await assert.rejects(f.run(true),e=>e.code==="confirmation_address_refused"&&e.stage==="confirmation_ready");
 assert.deepEqual(f.calls,before);
});
await test("private_path_and_parent_checks_precede_every_external_effect",async()=>{
 const f=fixture();await assert.rejects(runFreshOnly({statePath:"relative-state.json",origin,actions:f.actions}),e=>e.code==="private_state_path_required");
 assert.equal(f.calls.prepare,0);
 const open=folder();chmodSync(open,0o755);
 await assert.rejects(runFreshOnly({statePath:join(open,"state.json"),origin,actions:f.actions}),e=>e.code==="private_parent_permissions_required");
 assert.equal(f.calls.prepare,0);chmodSync(open,0o700);
 const outer=folder(),target=folder();mkdirSync(join(target,"private"),{mode:0o700});symlinkSync(target,join(outer,"linked"));
 await assert.rejects(runFreshOnly({statePath:join(outer,"linked/private/state.json"),origin,actions:f.actions}),e=>e.code==="private_state_symlink_refused");
 assert.equal(f.calls.prepare,0);
});
await test("oversized_private_state_is_refused_before_resume_effects",async()=>{
 const f=fixture();await f.run(false);writeFileSync(f.path," ".repeat(65537));
 const before={...f.calls};await assert.rejects(f.run(true),e=>e.code==="private_state_too_large");assert.deepEqual(f.calls,before);
});
await test("actual_fresh_only_command_saves_credentials_and_never_enters_other_journeys",async()=>{
 const directory=folder(),statePath=join(directory,"state.json"),reportPath=join(directory,"report.json"),counts={mailbox:0,signup:0,confirmation:0,signin:0};
 const fakeFetch=async(url,options={})=>{
  const result=value=>({ok:true,json:async()=>value});
  if(url===origin+"/api/v1/account/identity")return result({result:{signup_available:true}});
  if(url===origin+"/api/v1/capabilities")return result({result:{website:{registration_available:true}}});
  if(url==="https://api.mail.tm/domains")return result({"hydra:member":[{domain:"inbox.invalid"}]});
  if(url==="https://api.mail.tm/accounts"){counts.mailbox++;assert.equal(readFreshState(statePath,origin).stage,"mailbox_create_pending");return result({id:"fixture-mailbox"});}
  if(url==="https://api.mail.tm/token")return result({token:privateToken});
  if(url==="https://api.mail.tm/messages")return result({"hydra:member":[{id:"fixture-message"}]});
  if(url==="https://api.mail.tm/messages/fixture-message")return result({from:{address:"accounts@mail.baltor.ai"},subject:"Confirm",text:origin+"/auth/confirm?token_hash=synthetic-link-only"});
  throw new Error("unexpected_network_destination");
 };
 const guards=[];
 const page=()=>{let current=origin+"/";return {on(){},goto:async url=>{current=url;},waitForSelector:async()=>{},waitForFunction:async()=>{},waitForTimeout:async()=>{},fill:async()=>{},url:()=>current,
  locator:()=>({textContent:async()=>"",isVisible:async()=>false}),evaluate:async()=>account,
  click:async selector=>{if(selector==="#funnel-signup-button")counts.signup++;else if(selector==="#confirm-button"){counts.confirmation++;current=origin+"/get-started";}else if(selector==="#email-login-button"){counts.signin++;current=origin+"/app";}else throw new Error("unexpected_browser_effect");}};};
 const chromium={launch:async()=>({newContext:async()=>({route:async(_pattern,guard)=>guards.push(guard),newPage:async()=>page()}),close:async()=>{}})};
 const source=readFileSync(join(root,"tools/check_live_account_journeys.mjs"),"utf8").replace(/^import .*;\n/gm,"").replaceAll("import.meta.url",JSON.stringify(pathToFileURL(join(root,"tools/check_live_account_journeys.mjs")).href));
 const AsyncFunction=Object.getPrototypeOf(async function(){}).constructor;let exitCode=null;
 const fakeProcess={argv:["node","check",origin,reportPath,"--fresh-only"],env:{HOME:directory,BALTOR_JOURNEY_STATE:statePath},exit:value=>{exitCode=value;}};
 await new AsyncFunction("chromium","existsSync","writeFileSync","readFileSync","resolve","randomUUID","randomBytes","FreshJourneyError","runFreshOnly","isConfirmationSender","process","fetch","console",source)
  (chromium,existsSync,writeFileSync,readFileSync,(await import("node:path")).resolve,randomUUID,randomBytes,FreshJourneyError,runFreshOnly,isConfirmationSender,fakeProcess,fakeFetch,{log(){}});
 const report=JSON.parse(readFileSync(reportPath,"utf8")),state=readFreshState(statePath,origin);
 assert.equal(exitCode,0);assert.equal(report.all_passed,true);assert.equal(report.fresh_only,true);assert.equal(state.stage,"complete");
 assert.deepEqual(counts,{mailbox:1,signup:1,confirmation:1,signin:1});
 for(const value of [state.fresh.password,state.mailbox.password,state.mailbox.token])assert.ok(!JSON.stringify(report).includes(value));
 for(const path of ["/api/v1/admin/accounts","/api/v1/billing/checkout","/api/v1/billing/portal","/auth/v1/signup","/api/v1/account/access"]){let refused=false;await guards[0]({request:()=>({url:()=>origin+path,method:()=>"POST"}),abort:()=>{refused=true;},continue:()=>{}});assert.ok(refused);}
 let readContinued=false;await guards[0]({request:()=>({url:()=>origin+"/api/v1/account/access",method:()=>"GET"}),abort:()=>{},continue:()=>{readContinued=true;}});assert.ok(readContinued);
});
for(const directory of folders)rmSync(directory,{recursive:true,force:true});
console.log(JSON.stringify({checks:results,passed:results.filter(row=>row.passed).length,total:results.length}));
process.exitCode=results.every(row=>row.passed)?0:1;
'''


@unittest.skipUnless(NODE, "node is not installed")
class FreshAccountJourneyTests(unittest.TestCase):
    def test_resumable_fresh_only_flow_and_its_effect_boundaries(self):
        done = subprocess.run([NODE, "--input-type=module", "-", str(ROOT)], input=CHECKS,
                              text=True, capture_output=True, timeout=30)
        self.assertIn(done.returncode, (0, 1), done.stderr)
        self.assertTrue(done.stdout.strip(), done.stderr)
        result = json.loads(done.stdout)
        self.assertEqual(result["total"], 13)
        for row in result["checks"]:
            with self.subTest(check=row["name"]):
                self.assertTrue(row["passed"], row.get("reason"))
        self.assertEqual(done.returncode, 0)


if __name__ == "__main__":
    unittest.main()
