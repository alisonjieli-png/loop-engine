'use strict';
/* Offline account autoload checks. Only the DOM surface and deferred requests are fixtures;
   the module under test is the source passed by test_client_access_autoload.py. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
// The Python owner sends the real page module, or one named removed-guard variant, on stdin.
const sourcePath = 'client-access.js';
const source = fs.readFileSync(0, 'utf8');
const checks = [];
const check = (name, action) => {
  try { action(); checks.push({name, passed:true}); }
  catch (error) { checks.push({name, passed:false, detail:error.message}); }
};
const flush = async () => { for (let i=0;i<8;i++) await Promise.resolve(); };
function fixture() {
  const nodes = new Map(), reads = [], calls = [];
  const node = id => {
    if (!nodes.has(id)) nodes.set(id, {
      id, hidden:false, disabled:false, value:'', textContent:'', type:'', dataset:{},
      addEventListener(){}, replaceChildren(){}, querySelectorAll(){return [];}, append(){},
      click(){ if (!this.disabled) reads.push(id); }
    });
    return nodes.get(id);
  };
  const view = {hidden:false};
  let state = {connected:false, mode:'host_key', generation:1, known:false, available:false};
  const context = {window:{}, document:{getElementById:node, querySelector:()=>view},
    MutationObserver:class {observe(){}}, console};
  vm.runInNewContext(source, context, {filename:sourcePath});
  const api = context.window.BaltorClientAccess.create({
    request:path => new Promise((resolve,reject)=>calls.push({path,resolve,reject})),
    element:()=>node('generated'), message(){}, current:()=>state
  });
  const ready = value => { for (const id of ['refresh-usage','refresh-billing']) node(id).disabled = !value; };
  ready(false);
  return {api, node, calls, reads, ready,
    state:patch => {state={...state,...patch};},
    reply:(index,count=0) => calls[index].resolve({record_type:'service_client_access_options/v1',
      active_tokens:count, maximum_active_tokens:5, retained_token_records:count,
      maximum_token_records:100, writes_authorized:true, allowed_scopes:[], tokens:[], total_records:count})};
}
(async () => {
  // The retained token exists while /session is still in flight. Capabilities can win that race.
  const earlyCapabilities = fixture();
  earlyCapabilities.state({connected:true, known:true, available:true});
  earlyCapabilities.api.connectionChanged();
  check('capabilities_before_session_waits_for_readiness',()=>{
    assert.deepEqual(earlyCapabilities.reads,[]); assert.equal(earlyCapabilities.calls.length,0);
  });
  earlyCapabilities.state({mode:'browser_identity'}); earlyCapabilities.ready(true);
  earlyCapabilities.api.connectionChanged(); earlyCapabilities.api.connectionChanged();
  check('capabilities_before_session_loads_usage_and_billing_once',()=>assert.deepEqual(earlyCapabilities.reads,['refresh-usage','refresh-billing']));
  check('capabilities_before_session_loads_client_tokens_once',()=>assert.equal(earlyCapabilities.calls.length,1));
  if (earlyCapabilities.calls.length) earlyCapabilities.reply(0,1);
  await flush(); earlyCapabilities.api.connectionChanged();
  check('settled_account_reads_do_not_repeat',()=>{
    assert.deepEqual(earlyCapabilities.reads,['refresh-usage','refresh-billing']); assert.equal(earlyCapabilities.calls.length,1);
  });

  // /session may arrive first instead: read the account, then load client tokens once capability is known.
  const earlySession = fixture();
  earlySession.state({connected:true, mode:'browser_identity'}); earlySession.ready(true);
  earlySession.api.connectionChanged();
  check('session_before_capabilities_loads_usage_and_billing_once',()=>assert.deepEqual(earlySession.reads,['refresh-usage','refresh-billing']));
  check('unknown_capability_does_not_request_client_tokens',()=>assert.equal(earlySession.calls.length,0));
  earlySession.state({known:true, available:true}); earlySession.api.connectionChanged(); earlySession.api.connectionChanged();
  check('late_capability_loads_client_tokens_once',()=>assert.equal(earlySession.calls.length,1));
  if (earlySession.calls.length) earlySession.reply(0,2);
  await flush(); earlySession.api.connectionChanged();
  check('late_capability_does_not_repeat_other_account_reads',()=>assert.deepEqual(earlySession.reads,['refresh-usage','refresh-billing']));

  // An old request may settle after sign-out and after the new generation has started loading.
  const generations = fixture();
  generations.state({connected:true, mode:'browser_identity', known:true, available:true}); generations.ready(true);
  generations.api.connectionChanged();
  generations.state({connected:false, mode:'host_key', generation:2}); generations.ready(false);
  generations.api.reset(); generations.api.connectionChanged();
  check('sign_out_clears_client_token_tile',()=>assert.equal(generations.node('account-tile-keys').textContent,'Not loaded'));
  check('sign_out_does_not_start_account_reads',()=>{
    assert.equal(generations.reads.length,2); assert.equal(generations.calls.length,1);
  });
  generations.state({connected:true, mode:'browser_identity'}); generations.ready(true);
  generations.api.connectionChanged();
  check('new_generation_starts_its_own_client_token_request',()=>assert.equal(generations.calls.length,2));
  check('new_generation_reads_usage_and_billing_once',()=>assert.deepEqual(generations.reads,['refresh-usage','refresh-billing','refresh-usage','refresh-billing']));
  const newLoad = generations.api.refresh();
  generations.reply(0,99); await flush();
  check('old_generation_does_not_render_its_result',()=>assert.equal(generations.node('account-tile-keys').textContent,'Not loaded'));
  check('old_generation_cleanup_does_not_clear_new_pending_request',()=>assert.equal(generations.api.refresh(),newLoad));
  if (generations.calls[1]) generations.reply(1,3);
  await flush(); generations.api.connectionChanged();
  check('new_generation_result_is_rendered_without_duplicate_read',()=>{
    assert.equal(generations.node('account-tile-keys').textContent,'3 active'); assert.equal(generations.calls.length,2);
  });
  const failed=checks.filter(item=>!item.passed);
  console.log(JSON.stringify({source:sourcePath,sha256:crypto.createHash('sha256').update(source).digest('hex'),
    checked_at:new Date().toISOString(),passed:checks.length-failed.length,total:checks.length,checks},null,2));
  process.exitCode=failed.length?1:0;
})().catch(error=>{console.error(error);process.exitCode=2;});
