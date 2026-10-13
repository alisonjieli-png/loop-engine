// Private email ingress only. No fetch handler, forwarding, reply or models.
export const RECIPIENT = 'newsletters@inbox.agentfeeds.si';
export const MAXIMUM_RAW = 2 * 1024 * 1024;
export const PREFIX = 'newsletter-email/v1/';
const address = /^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$/;
const encoder = new TextEncoder();
const hex = buffer => [...new Uint8Array(buffer)].map(value => value.toString(16).padStart(2, '0')).join('');
const digest = async bytes => hex(await crypto.subtle.digest('SHA-256', bytes));

async function boundedRaw(message) {
  if (!Number.isSafeInteger(message.rawSize) || message.rawSize < 1 || message.rawSize > MAXIMUM_RAW)
    throw new Error('newsletter_raw_size_refused');
  const reader = message.raw.getReader(), chunks = [];
  let total = 0;
  try {
    while (true) {
      const {value, done} = await reader.read();
      if (done) break;
      if (!(value instanceof Uint8Array) || total + value.byteLength > MAXIMUM_RAW)
        throw new Error('newsletter_raw_size_refused');
      chunks.push(value); total += value.byteLength;
    }
  } catch (error) {
    await reader.cancel();
    throw error;
  } finally { reader.releaseLock(); }
  if (total !== message.rawSize) throw new Error('newsletter_raw_size_mismatch');
  const raw = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) { raw.set(chunk, offset); offset += chunk.byteLength; }
  return raw;
}

async function immutablePut(bucket, key, bytes, mediaType, sha256) {
  const stored = await bucket.put(key, bytes, {
    onlyIf: new Headers({'If-None-Match': '*'}), sha256,
    httpMetadata: {contentType: mediaType, cacheControl: 'private, no-store'},
    customMetadata: {record_type: 'newsletter_email/v1', sha256}
  });
  if (stored) {
    if (stored.key !== key || stored.size !== bytes.byteLength) throw new Error('newsletter_put_receipt_mismatch');
    return;
  }
  // A conditional duplicate is not an unknown write. Verify existing bytes
  // before acknowledging; an exception leaves the outcome for reconciliation.
  const prior = await bucket.get(key);
  if (!prior || prior.size !== bytes.byteLength || prior.size > MAXIMUM_RAW)
    throw new Error('newsletter_existing_object_refused');
  if (await digest(await prior.arrayBuffer()) !== sha256)
    throw new Error('newsletter_existing_object_digest_mismatch');
}

async function reserveAdmission(env, message, deliveryId, rawSha256) {
  if (!env.NEWSLETTER_ADMISSION || typeof env.NEWSLETTER_ADMISSION.getByName !== 'function')
    throw new Error('newsletter_admission_binding_required');
  const reservation = {record_type: 'newsletter_admission/v1', delivery_id: deliveryId,
    raw_sha256: rawSha256, raw_bytes: message.rawSize};
  // This is an internal Durable Object binding, not a public fetch or URL
  // chosen by mail. One reservation precedes every raw-object write.
  const reply = await env.NEWSLETTER_ADMISSION.getByName('newsletter-admission-v1').fetch(
    'https://newsletter-admission.invalid/reserve', {method: 'POST',
      headers: {'Content-Type': 'application/json'}, body: JSON.stringify(reservation)});
  if (reply.status === 429) {
    message.setReject('newsletter_admission_limit');
    return false;
  }
  if (reply.status !== 200) throw new Error('newsletter_admission_refused');
  const body = await reply.text();
  if (body.length > 4096) throw new Error('newsletter_admission_response_refused');
  let held;
  try {held = JSON.parse(body);} catch {throw new Error('newsletter_admission_response_refused');}
  if (!held || held.record_type !== 'newsletter_admission_result/v1' || held.accepted !== true ||
      held.delivery_id !== deliveryId || held.raw_sha256 !== rawSha256 || held.raw_bytes !== message.rawSize ||
      held.reservation_bytes !== message.rawSize + 8192 || typeof held.duplicate !== 'boolean' ||
      typeof held.recorded_at !== 'string' || !Number.isFinite(Date.parse(held.recorded_at)))
    throw new Error('newsletter_admission_response_refused');
  return true;
}

export async function receive(message, env, {now = () => new Date(), identity = () => crypto.randomUUID()} = {}) {
  if (message.to !== RECIPIENT || typeof message.from !== 'string' || /[\x00-\x20\x7f]/.test(message.from) || !address.test(message.from)) {
    message.setReject('newsletter_recipient_or_sender_refused');
    return;
  }
  if (!env.NEWSLETTER_QUARANTINE || env.NEWSLETTER_RECIPIENT !== RECIPIENT || !env.NEWSLETTER_ADMISSION)
    throw new Error('newsletter_private_binding_required');
  if (!Number.isSafeInteger(message.rawSize) || message.rawSize < 1 || message.rawSize > MAXIMUM_RAW) {
    message.setReject('newsletter_raw_size_refused');
    return;
  }
  const raw = await boundedRaw(message), rawSha256 = await digest(raw);
  const deliveryId = identity();
  if (!/^[A-Za-z0-9_-]{1,128}$/.test(deliveryId)) throw new Error('newsletter_delivery_id_refused');
  if (!await reserveAdmission(env, message, deliveryId, rawSha256)) return;
  const rawKey = PREFIX + 'raw/' + rawSha256;
  const receiptKey = PREFIX + 'receipts/' + deliveryId + '.json';
  const receipt = {
    record_type: 'newsletter_email/v1', delivery_id: deliveryId, recipient: RECIPIENT,
    envelope_sender: message.from, received_at: now().toISOString().replace(/\.\d{3}Z$/, 'Z'),
    ingress: 'cloudflare_email_worker/v1', raw_sha256: rawSha256,
    raw_bytes: raw.byteLength, raw_key: rawKey,
    source_semantics: 'private_email_not_public_feed', disposition: 'quarantined',
    sender_authentication: 'not_verified', publication_approved: false
  };
  const bytes = encoder.encode(JSON.stringify(receipt));
  await immutablePut(env.NEWSLETTER_QUARANTINE, rawKey, raw, 'message/rfc822', rawSha256);
  // Receipt last: it never advertises a raw object whose write was not confirmed.
  await immutablePut(env.NEWSLETTER_QUARANTINE, receiptKey, bytes, 'application/json', await digest(bytes));
  return {receipt_key: receiptKey, raw_sha256: rawSha256};
}

export default {async email(message, env) { await receive(message, env); }};
