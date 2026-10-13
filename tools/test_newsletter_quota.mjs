import assert from 'node:assert/strict';
import test from 'node:test';
import {reserve, quotaFetch, DAILY_MESSAGES, LIFETIME_BYTES, LIFETIME_MESSAGES,
  RECORD_RESERVATION_BYTES, MAXIMUM_RAW_BYTES} from '../integrations/newsletter-email/quota.mjs';

// Transaction simulator exercises atomic intent and rollback semantics.
// Real Cloudflare SQLite persistence remains a separate deployment check.
class Storage {
  records = new Map(); tail = Promise.resolve(); writes = 0; fail = false; unknown = false;
  transaction(fn) {
    const next = this.tail.then(async () => {
      const copy = structuredClone(this.records);
      const result = await fn({get: async key => structuredClone(copy.get(key)), put: async entries => {
        this.writes++; for (const [key, value] of Object.entries(entries)) copy.set(key, structuredClone(value));
        if (this.fail) throw Error('simulated storage failure');
      }});
      this.records = copy;
      if (this.unknown) throw Error('simulated lost confirmation');
      return result;
    });
    this.tail = next.catch(() => {});
    return next;
  }
}
const now = () => new Date('2026-10-13T23:00:00.000Z');
const body = (id = 'delivery-one', bytes = 100) => ({record_type: 'newsletter_admission/v1',
  delivery_id: id, raw_sha256: 'a'.repeat(64), raw_bytes: bytes});
const request = (value = body(), changes = {}) => new Request('https://newsletter-admission.invalid/reserve', {
  method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(value), ...changes});

test('admission commits identity and both counters before answering', async () => {
  const store = new Storage(), result = await reserve(store, body(), now);
  assert.equal(result.accepted, true); assert.equal(store.records.size, 3); assert.equal(store.writes, 1);
  assert.equal(store.records.get('total/v1').bytes, 100 + RECORD_RESERVATION_BYTES);
  assert.equal(result.recorded_at, now().toISOString());
});
test('exact duplicate is idempotent and conflict changes no record', async () => {
  const store = new Storage(); await reserve(store, body(), now);
  assert.equal((await reserve(store, body(), now)).duplicate, true); assert.equal(store.writes, 1);
  for (const changed of [{...body(), raw_bytes: 101}, {...body(), raw_sha256: 'b'.repeat(64)}])
    await assert.rejects(reserve(store, changed, now), /delivery_conflict/);
  assert.equal(store.writes, 1);
});
test('parallel requests cannot overrun the UTC daily ceiling', async () => {
  const store = new Storage();
  const answers = await Promise.allSettled(Array.from({length: DAILY_MESSAGES + 30}, (_, n) => reserve(store, body('d-' + n), now)));
  assert.equal(answers.filter(value => value.status === 'fulfilled').length, DAILY_MESSAGES);
  assert.equal(store.records.get('total/v1').count, DAILY_MESSAGES);
});
test('new UTC day retains the lifetime counter and prior records', async () => {
  const store = new Storage();
  for (let n = 0; n < DAILY_MESSAGES; n++) await reserve(store, body('d-' + n), now);
  await reserve(store, body('next-day'), () => new Date('2026-10-14T00:00:00Z'));
  assert.equal(store.records.get('total/v1').count, DAILY_MESSAGES + 1);
  assert.equal(store.records.get('day/2026-10-13').count, DAILY_MESSAGES);
});
test('global byte ceiling rejects before writing despite remaining daily allowance', async () => {
  const store = new Storage();
  store.records.set('total/v1', {record_type: 'newsletter_total/v1', count: 1000, bytes: LIFETIME_BYTES - 1});
  await assert.rejects(reserve(store, body(), now), /admission_exhausted/);
  assert.equal(store.writes, 0);
});
test('global record ceiling bounds tiny-message metadata growth', async () => {
  const store = new Storage();
  store.records.set('total/v1', {record_type: 'newsletter_total/v1', count: LIFETIME_MESSAGES,
    bytes: LIFETIME_MESSAGES * (RECORD_RESERVATION_BYTES + 1)});
  await assert.rejects(reserve(store, body(), now), /admission_exhausted/);
  assert.equal(store.writes, 0);
});
test('invalid versions fields bytes and identities fail before a transaction write', async () => {
  for (const value of [null, {...body(), record_type: 'newsletter_admission/v2'}, {...body(), extra: true},
    {...body(), raw_bytes: true}, {...body(), raw_bytes: 0}, {...body(), raw_bytes: MAXIMUM_RAW_BYTES + 1},
    {...body(), delivery_id: '../escape'}, {...body(), raw_sha256: 'bad'}]) {
    const store = new Storage(); await assert.rejects(reserve(store, value, now)); assert.equal(store.writes, 0);
  }
});
test('malformed durable state is not reset', async () => {
  for (const value of [null, {count: 0}, {record_type: 'newsletter_total/v1', count: 1, bytes: 0},
    {record_type: 'newsletter_total/v1', count: -1, bytes: 10}, {record_type: 'newsletter_total/v1', count: 0, bytes: 10}]) {
    const store = new Storage(); store.records.set('total/v1', value);
    await assert.rejects(reserve(store, body(), now), /state_unqualified/); assert.equal(store.writes, 0);
  }
});
test('known failed transaction writes nothing and returns no admission', async () => {
  const store = new Storage(); store.fail = true;
  const result = await quotaFetch(store, request(), now);
  assert.equal(result.status, 503); assert.equal((await result.json()).accepted, false); assert.equal(store.records.size, 0);
});
test('unknown commit retains reservation and exact reconciliation does not recharge', async () => {
  const store = new Storage(); store.unknown = true;
  assert.equal((await quotaFetch(store, request(), now)).status, 503);
  assert.equal(store.records.get('total/v1').count, 1);
  store.unknown = false;
  assert.equal((await reserve(store, body(), now)).duplicate, true);
  assert.equal(store.records.get('total/v1').count, 1);
});
test('duplicate JSON keys, oversized payload and wrong route refuse without writes', async () => {
  const requests = [request(body(), {body: '{"record_type":"x",' + JSON.stringify(body()).slice(1)}),
    request(body(), {body: ' '.repeat(2000)}), new Request('https://newsletter-admission.invalid/reset'),
    request(body(), {headers: {'Content-Type': 'text/plain'}})];
  for (const req of requests) {const store = new Storage(); assert.notEqual((await quotaFetch(store, req, now)).status, 200); assert.equal(store.writes, 0);}
});
test('accepted wire is closed and private', async () => {
  const response = await quotaFetch(new Storage(), request(), now);
  assert.equal(response.status, 200); assert.equal(response.headers.get('cache-control'), 'private, no-store');
  assert.equal((await response.json()).record_type, 'newsletter_admission_result/v1');
});
