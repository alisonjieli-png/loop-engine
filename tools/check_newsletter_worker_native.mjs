// Offline workerd proof with real local SQLite/R2 storage. Not SMTP or live R2.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath, pathToFileURL} from 'node:url';

const [miniflarePath, output] = process.argv.slice(2);
if (!miniflarePath || !output || !path.isAbsolute(miniflarePath) || !path.isAbsolute(output))
  throw Error('usage: node tools/check_newsletter_worker_native.mjs /absolute/miniflare/dist/src/index.js /new/private/output');
await mkdir(output, {mode: 0o700});
const {Miniflare} = await import(pathToFileURL(miniflarePath));
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../integrations/newsletter-email');
const report = {record_type: 'newsletter_native_storage_check/v1', at: new Date().toISOString(),
  source_sha256: {}, checks: [], live_provider_calls: 0, smtp_deliveries: 0, external_fetches: 0};
for (const filename of ['cloudflare.mjs', 'worker.mjs', 'quota.mjs'])
  report.source_sha256[filename] = createHash('sha256').update(await readFile(path.join(root, filename))).digest('hex');
const fixture = `
import {receive, RECIPIENT} from './worker.mjs';
export {NewsletterAdmission} from './cloudflare.mjs';
export default {async fetch(request, env) {
  const raw = new TextEncoder().encode('From: sender@example.org\\r\\nContent-Type: text/plain\\r\\n\\r\\nPrivate fixture only.');
  const message = {to: RECIPIENT, from: 'sender@example.org', rawSize: raw.byteLength,
    raw: new ReadableStream({start(c) {c.enqueue(raw); c.close();}}),
    setReject(reason) {this.rejection = reason;}};
  const held = await receive(message, env, {identity: () => new URL(request.url).searchParams.get('id') || 'native-one',
    now: () => new Date('2026-10-13T23:00:00Z')});
  return Response.json({result: held || null, rejected: message.rejection || null});
}};`;
const options = {
  cf: false,
  modulesRoot: root,
  modules: [{type: 'ESModule', path: path.join(root, 'native-fixture.mjs'), contents: fixture},
    ...['cloudflare.mjs', 'worker.mjs', 'quota.mjs'].map(name => ({type: 'ESModule', path: path.join(root, name)}))],
  compatibilityDate: '2026-05-01',
  bindings: {NEWSLETTER_RECIPIENT: 'newsletters@inbox.agentfeeds.si'},
  durableObjects: {NEWSLETTER_ADMISSION: {className: 'NewsletterAdmission', useSQLite: true}},
  durableObjectsPersist: path.join(output, 'durable'), r2Persist: path.join(output, 'r2'),
  r2Buckets: ['NEWSLETTER_QUARANTINE'],
  outboundService: () => {report.external_fetches++; throw Error('external network forbidden');},
};
const request = id => ({method: 'POST', headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({record_type: 'newsletter_admission/v1', delivery_id: id,
    raw_sha256: 'a'.repeat(64), raw_bytes: 100})});
let mf;
try {
  mf = new Miniflare(options);
  const initial = await (await mf.dispatchFetch('https://fixture.invalid/')).json();
  assert.equal(initial.rejected, null);
  assert.match(initial.result.raw_sha256, /^[0-9a-f]{64}$/);
  const bucket = await mf.getR2Bucket('NEWSLETTER_QUARANTINE');
  const receipt = await (await bucket.get(initial.result.receipt_key)).json();
  const raw = new Uint8Array(await (await bucket.get(receipt.raw_key)).arrayBuffer());
  assert.equal(createHash('sha256').update(raw).digest('hex'), receipt.raw_sha256);
  assert.equal(receipt.publication_approved, false);
  report.checks.push('actual_worker_to_sqlite_admission_to_exact_r2_raw_and_receipt');
  assert.equal((await bucket.list()).objects.length, 2);
  const again = await (await mf.dispatchFetch('https://fixture.invalid/')).json();
  assert.deepEqual(again, initial);
  assert.equal((await bucket.list()).objects.length, 2);
  report.checks.push('exact_worker_replay_verifies_immutable_objects');
  const namespace = await mf.getDurableObjectNamespace('NEWSLETTER_ADMISSION');
  const stub = namespace.get(namespace.idFromName('newsletter-admission-v1'));
  const results = await Promise.all(Array.from({length: 120}, async (_, n) => {
    const response = await stub.fetch('https://newsletter-admission.invalid/reserve', request('parallel-' + n));
    return {status: response.status, value: await response.json()};
  }));
  assert.equal(results.filter(row => row.status === 200).length, 99);
  assert.equal(results.filter(row => row.status === 429).length, 21);
  report.checks.push('120_concurrent_requests_respect_100_total_daily_admissions');
  const rejected = await (await mf.dispatchFetch('https://fixture.invalid/?id=over-limit')).json();
  assert.equal(rejected.rejected, 'newsletter_admission_limit');
  assert.equal((await bucket.list()).objects.length, 2);
  report.checks.push('exhausted_admission_writes_no_r2_objects');
  await mf.dispose(); mf = undefined;
  mf = new Miniflare(options);
  const reopened = await mf.getDurableObjectNamespace('NEWSLETTER_ADMISSION');
  const persistent = reopened.get(reopened.idFromName('newsletter-admission-v1'));
  const limit = await persistent.fetch('https://newsletter-admission.invalid/reserve', request('after-restart'));
  assert.equal(limit.status, 429);
  const accepted = results.find(row => row.status === 200).value;
  const duplicate = await persistent.fetch('https://newsletter-admission.invalid/reserve', request(accepted.delivery_id));
  assert.equal(duplicate.status, 200);
  assert.equal((await duplicate.json()).duplicate, true);
  const reopenedBucket = await mf.getR2Bucket('NEWSLETTER_QUARANTINE');
  assert.equal((await reopenedBucket.list()).objects.length, 2);
  report.checks.push('fresh_workerd_reopens_same_sqlite_counter_and_private_r2_objects');
  assert.equal(report.external_fetches, 0);
  report.checks.push('zero_external_fetches');
  report.passed = true;
} catch (error) {
  report.passed = false;
  report.failure = {name: error.name, message: String(error.message).slice(0, 2048)};
  process.exitCode = 1;
} finally {
  if (mf) await mf.dispose();
  await writeFile(path.join(output, 'result.json'), JSON.stringify(report, null, 2) + '\n', {flag: 'wx', mode: 0o600});
  console.log(JSON.stringify({passed: report.passed, checks: report.checks.length, evidence: path.join(output, 'result.json')}));
}
