'use strict';
/* Offline checks of the account page's saved feeds section. Only the DOM surface and deferred requests are fixtures;
   the module under test is the source passed on stdin by test_customer_feeds_page.py, the real file or one named
   removed-guard variant. Nothing here connects to a service. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const sourcePath = 'customer-feeds.js';
const source = fs.readFileSync(0, 'utf8');
const checks = [];
const check = (name, action) => {
  try { action(); checks.push({name, passed:true}); }
  catch (error) { checks.push({name, passed:false, detail:error.message}); }
};
const flush = async () => { for (let i = 0; i < 12; i++) await Promise.resolve(); };
function makeNode(tag, id) {
  return {tag, id, hidden:false, disabled:false, value:'', textContent:'', type:'', className:'', dataset:{}, children:[], handlers:{},
    attributes:{}, addEventListener(type, handler) { this.handlers[type] = handler; }, setAttribute(name, value) { this.attributes[name] = value; },
    append(...items) { this.children.push(...items); }, replaceChildren(...items) { this.children = [...items]; },
    click() { if (!this.disabled && this.handlers.click) return this.handlers.click(); }};
}
function texts(node) { return [node.textContent, ...node.children.flatMap(texts)].filter(Boolean); }
function fixture(initial) {
  const nodes = new Map(), calls = [];
  const byId = id => { if (!nodes.has(id)) nodes.set(id, makeNode('div', id)); return nodes.get(id); };
  let uuid = 0, state = {connected:false, mode:'host_key', generation:1, available:false, ...initial};
  const context = {window:{}, console, confirm:() => true, setTimeout:() => 0,
    crypto:{randomUUID:() => 'request-' + (++uuid)}, Blob:class {}, URL:{createObjectURL:() => 'blob:x', revokeObjectURL() {}},
    document:{getElementById:byId, createElement:tag => makeNode(tag, '')}};
  vm.runInNewContext(source, context, {filename:sourcePath});
  const element = (tag, text, className = '') => { const item = makeNode(tag, ''); item.textContent = text; item.className = className; return item; };
  const api = context.window.BaltorCustomerFeeds.create({
    request:(path, body) => new Promise((resolve, reject) => calls.push({path, body, resolve, reject})),
    element, message:(id, text) => { byId(id).textContent = text; }, current:() => state});
  return {api, node:byId, calls, state:patch => { state = {...state, ...patch}; }};
}
const OVERVIEW = {record_type:'customer_feed_overview/v1', limits:{maximum_definitions:20},
  templates:[{template:'topic:Compare models', title:'Compare models', settings:{template:'topic:Compare models',
    streams:['source_references'], topics:['Compare models'], format:'json', max_items:100, max_age_days:30}}],
  definitions:[{feed_id:'f'.repeat(32), revision:'r1', name:'<img src=x onerror=alert(1)>', definition_version:1,
    state:'active', settings:{format:'json'}}],
  assignments:[], agent_keys:[{key_id:'k1', label:'Coding agent', state:'active', reads_feeds:true}]};
(async () => {
  const off = fixture({connected:true, mode:'browser_identity', available:false});
  off.api.connectionChanged();
  check('hidden_and_silent_until_the_service_offers_saved_feeds', () => {
    assert.equal(off.node('account-feeds').hidden, true); assert.equal(off.calls.length, 0);
  });
  const signedOut = fixture({available:true});
  signedOut.api.connectionChanged();
  check('signed_out_shows_the_section_without_reading_anything', () => {
    assert.equal(signedOut.node('account-feeds').hidden, false); assert.equal(signedOut.calls.length, 0);
    assert.equal(signedOut.node('feeds-controls').hidden, true);
  });
  const keyed = fixture({connected:true, mode:'host_key', available:true});
  keyed.api.connectionChanged();
  check('a_service_key_connection_never_manages_feeds', () => assert.equal(keyed.calls.length, 0));
  const page = fixture({connected:true, mode:'browser_identity', available:true});
  page.api.connectionChanged(); page.api.connectionChanged();
  check('a_browser_session_reads_its_feed_settings_once', () => {
    assert.equal(page.calls.length, 1); assert.equal(page.calls[0].path, '/api/v1/account/feeds'); assert.equal(page.calls[0].body, undefined);
  });
  page.calls[0].resolve(OVERVIEW); await flush();
  check('saved_feeds_are_drawn_as_text', () => {
    assert.equal(page.node('feeds-controls').hidden, false);
    assert.ok(texts(page.node('feed-list')).includes('<img src=x onerror=alert(1)>'));
    assert.ok(!/innerHTML|outerHTML|insertAdjacentHTML|document\.write/.test(source));
  });
  page.node('feed-name').value = 'Model releases';
  const submit = () => page.node('feed-definition-form').handlers.submit({preventDefault() {}});
  submit(); await flush();
  const first = page.calls[1];
  first.reject(Object.assign(new Error('lost'), {status:503})); await flush();
  page.calls[2].resolve(OVERVIEW); await flush();
  submit(); await flush();
  const retried = page.calls[3];
  check('a_retry_of_the_same_feed_repeats_its_request_identity', () => {
    assert.equal(first.body.operation, 'create_definition'); assert.equal(retried.body.request_id, first.body.request_id);
  });
  retried.resolve({record_type:'customer_feed_result/v1', committed:true}); await flush();
  page.calls[4].resolve(OVERVIEW); await flush();
  submit(); await flush();
  check('a_new_feed_after_success_has_a_new_request_identity', () => {
    assert.notEqual(page.calls[5].body.request_id, first.body.request_id);
  });
  page.calls[5].resolve({record_type:'customer_feed_result/v1', committed:true}); await flush();
  page.calls[6].resolve(OVERVIEW); await flush();
  page.state({connected:false, mode:'host_key', generation:2}); page.api.reset();
  check('signing_out_clears_the_saved_feeds', () => {
    assert.equal(page.node('feed-list').children.length, 0); assert.equal(page.node('feeds-controls').hidden, true);
  });
  const failed = checks.filter(item => !item.passed);
  console.log(JSON.stringify({source:sourcePath, sha256:crypto.createHash('sha256').update(source).digest('hex'),
    passed:checks.length - failed.length, total:checks.length, checks}, null, 2));
  process.exitCode = failed.length ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 2; });
