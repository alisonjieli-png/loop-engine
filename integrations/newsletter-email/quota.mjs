// Atomic private-ingress admission; not a scheduler or a publication decision.
// Adapted to Cloudflare's documented storage.transaction contract:
// https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/#transaction
export const DAILY_MESSAGES = 100;
export const LIFETIME_MESSAGES = 4096;
export const LIFETIME_BYTES = 1024 * 1024 * 1024;
export const MAXIMUM_RAW_BYTES = 2 * 1024 * 1024;
export const RECORD_RESERVATION_BYTES = 8192;
const REQUEST_BYTES = 1024;
const RESULT = 'newsletter_admission_result/v1';

class Refusal extends Error {
  constructor(code, status = 400) { super(code); this.status = status; }
}
function exact(value, keys) {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
    && Object.keys(value).sort().join(',') === keys.slice().sort().join(',');
}
function input(value) {
  if (!exact(value, ['record_type', 'delivery_id', 'raw_sha256', 'raw_bytes'])
      || value.record_type !== 'newsletter_admission/v1'
      || typeof value.delivery_id !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(value.delivery_id)
      || typeof value.raw_sha256 !== 'string' || !/^[0-9a-f]{64}$/.test(value.raw_sha256)
      || !Number.isSafeInteger(value.raw_bytes) || value.raw_bytes < 1 || value.raw_bytes > MAXIMUM_RAW_BYTES)
    throw new Refusal('newsletter_admission_shape');
}
function counter(value, kind, countLimit, byteLimit) {
  if (value === undefined) return {record_type: kind, count: 0, bytes: 0};
  if (!exact(value, ['record_type', 'count', 'bytes']) || value.record_type !== kind
      || !Number.isSafeInteger(value.count) || value.count < 0 || value.count > countLimit
      || !Number.isSafeInteger(value.bytes) || value.bytes < 0 || value.bytes > byteLimit
      || (value.count === 0) !== (value.bytes === 0)
      || value.bytes < value.count * (RECORD_RESERVATION_BYTES + 1)
      || value.bytes > value.count * (RECORD_RESERVATION_BYTES + MAXIMUM_RAW_BYTES))
    throw new Refusal('newsletter_admission_state_unqualified', 503);
  return value;
}
function priorResult(value, request) {
  if (!exact(value, ['record_type', 'accepted', 'delivery_id', 'raw_sha256', 'raw_bytes',
                     'reservation_bytes', 'recorded_at', 'duplicate'])
      || value.record_type !== RESULT || value.accepted !== true || value.duplicate !== false
      || typeof value.recorded_at !== 'string' || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value.recorded_at)
      || !Number.isFinite(Date.parse(value.recorded_at))
      || value.reservation_bytes !== value.raw_bytes + RECORD_RESERVATION_BYTES)
    throw new Refusal('newsletter_admission_state_unqualified', 503);
  input({record_type: 'newsletter_admission/v1', delivery_id: value.delivery_id,
    raw_sha256: value.raw_sha256, raw_bytes: value.raw_bytes});
  if (['delivery_id', 'raw_sha256', 'raw_bytes'].some(name => value[name] !== request[name]))
    throw new Refusal('newsletter_delivery_conflict', 409);
  return {...value, duplicate: true};
}

export async function reserve(storage, request, now = () => new Date()) {
  input(request);
  if (typeof storage?.transaction !== 'function') throw new Refusal('newsletter_atomic_storage_required', 503);
  const recordedAt = now().toISOString(), day = recordedAt.slice(0, 10);
  return storage.transaction(async transaction => {
    const key = 'delivery/' + request.delivery_id;
    const existing = await transaction.get(key);
    if (existing !== undefined) return priorResult(existing, request);
    const total = counter(await transaction.get('total/v1'), 'newsletter_total/v1', LIFETIME_MESSAGES, LIFETIME_BYTES);
    const dayKey = 'day/' + day;
    const daily = counter(await transaction.get(dayKey), 'newsletter_day/v1', DAILY_MESSAGES, LIFETIME_BYTES);
    if (daily.count > total.count || daily.bytes > total.bytes)
      throw new Refusal('newsletter_admission_state_unqualified', 503);
    const bytes = request.raw_bytes + RECORD_RESERVATION_BYTES;
    if (daily.count >= DAILY_MESSAGES || total.count >= LIFETIME_MESSAGES || bytes > LIFETIME_BYTES - total.bytes)
      throw new Refusal('newsletter_admission_exhausted', 429);
    const result = {record_type: RESULT, accepted: true, delivery_id: request.delivery_id,
      raw_sha256: request.raw_sha256, raw_bytes: request.raw_bytes, reservation_bytes: bytes,
      recorded_at: recordedAt, duplicate: false};
    // All three writes belong to one durable transaction. No external I/O,
    // refund, expiry or retry is performed by its callback. Unknown outcomes
    // retain the reservation; reconciliation may replay only this exact ID.
    await transaction.put({[key]: result,
      'total/v1': {record_type: total.record_type, count: total.count + 1, bytes: total.bytes + bytes},
      [dayKey]: {record_type: daily.record_type, count: daily.count + 1, bytes: daily.bytes + bytes}});
    return result;
  });
}

async function boundedBody(request) {
  if (!request.body) throw new Refusal('newsletter_admission_body');
  const reader = request.body.getReader(), parts = [];
  let total = 0;
  try {
    for (;;) {
      const {value, done} = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > REQUEST_BYTES) throw new Refusal('newsletter_admission_body');
      parts.push(value);
    }
  } catch (error) { await reader.cancel(); throw error; }
  finally { reader.releaseLock(); }
  const raw = new Uint8Array(total);
  let offset = 0;
  for (const part of parts) {raw.set(part, offset); offset += part.byteLength;}
  const text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(raw);
  const value = JSON.parse(text);
  // The internal caller writes JSON.stringify. This also rejects duplicate
  // keys and non-canonical ambiguous payloads before durable writes.
  if (JSON.stringify(value) !== text) throw new Refusal('newsletter_admission_body');
  return value;
}

export async function quotaFetch(storage, request, now = () => new Date()) {
  try {
    if (request.method !== 'POST' || request.url !== 'https://newsletter-admission.invalid/reserve'
        || request.headers.get('content-type') !== 'application/json')
      throw new Refusal('newsletter_admission_route');
    const result = await reserve(storage, await boundedBody(request), now);
    return Response.json(result, {headers: {'Cache-Control': 'private, no-store'}});
  } catch (error) {
    return Response.json({record_type: RESULT, accepted: false,
      code: error instanceof Refusal ? error.message : 'newsletter_admission_uncertain'},
    {status: error instanceof Refusal ? error.status : 503, headers: {'Cache-Control': 'private, no-store'}});
  }
}
