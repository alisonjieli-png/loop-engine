// Known answers for the GLB codec: exact container bytes for two small documents (computed independently with
// Python's struct module from the glTF 2.0 binary layout), a round trip, and one known-wrong container for every
// refusal reason, each of which must be refused with its own code.
import test from 'node:test';
import assert from 'node:assert/strict';
import {GLB_FORMAT, GlbError, encodeGlb, isGlb, parseGlb} from './glb_container_codec.mjs';

// struct.pack('<III', 0x46546C67, 2, 48) + struct.pack('<II', 28, 0x4E4F534A) + b'{"asset":{"version":"2.0"}} '
const MINIMAL = [103, 108, 84, 70, 2, 0, 0, 0, 48, 0, 0, 0, 28, 0, 0, 0, 74, 83, 79, 78, 123, 34, 97, 115, 115, 101,
  116, 34, 58, 123, 34, 118, 101, 114, 115, 105, 111, 110, 34, 58, 34, 50, 46, 48, 34, 125, 125, 32];
// The same with buffers [{byteLength: 5}] and the BIN chunk 01 02 03 04 05 padded to 8 bytes: 92 bytes in all.
const WITH_BIN_HEX = '676c5446020000005c000000380000004a534f4e7b226173736574223a7b2276657273696f6e223a22322e30227d2c'
  + '2262756666657273223a5b7b22627974654c656e677468223a357d5d7d0800000042494e000102030405000000';
const JSON_TYPE = 0x4e4f534a;
const BIN_TYPE = 0x004e4942;

function hex(bytes) {
  return Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('');
}

// A container laid out by hand from raw chunks (the caller pads them); the header length is the real length.
function build(chunks) {
  const total = 12 + chunks.reduce((sum, [, bytes]) => sum + 8 + bytes.length, 0);
  const out = new Uint8Array(total);
  const view = new DataView(out.buffer);
  view.setUint32(0, 0x46546c67, true);
  view.setUint32(4, 2, true);
  view.setUint32(8, total, true);
  let offset = 12;
  for (const [type, bytes] of chunks) {
    view.setUint32(offset, bytes.length, true);
    view.setUint32(offset + 4, type, true);
    out.set(bytes, offset + 8);
    offset += 8 + bytes.length;
  }
  return out;
}

function text(value) {
  const encoded = new TextEncoder().encode(value);
  const out = new Uint8Array(Math.ceil(encoded.length / 4) * 4).fill(0x20);
  out.set(encoded);
  return out;
}

function withUint32(bytes, offset, value) {
  const copy = Uint8Array.from(bytes);
  new DataView(copy.buffer).setUint32(offset, value, true);
  return copy;
}

function codeOf(action) {
  try {
    action();
  } catch (error) {
    return error instanceof GlbError ? error.code : error.name;
  }
  return 'accepted';
}

test('encodeGlb writes the exact container bytes', () => {
  assert.deepEqual(Array.from(encodeGlb({asset: {version: '2.0'}})), MINIMAL);
  const withBin = encodeGlb({asset: {version: '2.0'}, buffers: [{byteLength: 5}]}, new Uint8Array([1, 2, 3, 4, 5]));
  assert.equal(hex(withBin), WITH_BIN_HEX);
  assert.equal(withBin.buffer.byteLength, 92, 'the result owns an exact ArrayBuffer');
});

test('parseGlb reads both containers back', () => {
  const minimal = parseGlb(new Uint8Array(MINIMAL).buffer);
  assert.equal(minimal.json.asset.version, '2.0');
  assert.equal(minimal.binary, null);
  assert.equal(minimal.byteLength, 48);
  assert.deepEqual(minimal.chunks.map((chunk) => [chunk.name, chunk.byteOffset, chunk.byteLength]), [['JSON', 20, 28]]);
  const bytes = encodeGlb({asset: {version: '2.0'}, buffers: [{byteLength: 5}]}, new Uint8Array([1, 2, 3, 4, 5]));
  const parsed = parseGlb(bytes);
  assert.deepEqual(Array.from(parsed.binary), [1, 2, 3, 4, 5, 0, 0, 0]);
  assert.deepEqual(parsed.chunks.map((chunk) => chunk.name), ['JSON', 'BIN']);
  assert.equal(parsed.version, GLB_FORMAT.version);
  const shifted = new Uint8Array(bytes.length + 8);
  shifted.set(bytes, 8);
  assert.equal(parseGlb(shifted.subarray(8)).json.buffers[0].byteLength, 5, 'a view with a byte offset reads too');
  const extra = build([[JSON_TYPE, text('{"asset":{"version":"2.0"}}')], [0x58595a5a, new Uint8Array(4)]]);
  assert.deepEqual(parseGlb(extra).chunks.map((chunk) => chunk.name), ['JSON', '0x58595a5a'], 'unknown chunks are listed');
});

test('isGlb sniffs the header without throwing', () => {
  assert.equal(isGlb(new Uint8Array(MINIMAL)), true);
  assert.equal(isGlb(new Uint8Array(4)), false);
  assert.equal(isGlb('glTF'), false);
  assert.equal(isGlb(withUint32(MINIMAL, 4, 1)), false);
});

test('known wrong: every malformed container is refused with its reason', () => {
  const good = new Uint8Array(MINIMAL);
  const asset = '{"asset":{"version":"2.0"}';
  const longer = new Uint8Array(50);
  longer.set(good);
  const cases = {
    too_short: good.subarray(0, 16),
    magic: withUint32(good, 0, 0x46546c66),
    version: withUint32(good, 4, 1),
    length_mismatch: withUint32(good, 8, 52),
    length_unaligned: withUint32(longer, 8, 50),
    chunk_truncated: withUint32(good, 12, 32),
    chunk_unaligned: withUint32(good, 12, 27),
    first_chunk_not_json: withUint32(good, 16, BIN_TYPE),
    json_not_utf8: build([[JSON_TYPE, new Uint8Array([0x7b, 0xff, 0x7d, 0x20])]]),
    json_bom: build([[JSON_TYPE, text(`${String.fromCharCode(0xfeff)}${asset}}`)]]),
    json_invalid: build([[JSON_TYPE, text('{"asset":')]]),
    json_not_object: build([[JSON_TYPE, text('[1]')]]),
    second_json_chunk: build([[JSON_TYPE, text(`${asset}}`)], [JSON_TYPE, text('{}')]]),
    bin_chunk_not_second: build([[JSON_TYPE, text(`${asset},"buffers":[{"byteLength":4}]}`)],
      [0x58595a5a, new Uint8Array(4)], [BIN_TYPE, new Uint8Array(4)]]),
    bin_without_buffer: build([[JSON_TYPE, text(`${asset}}`)], [BIN_TYPE, new Uint8Array(4)]]),
    bin_length_mismatch: build([[JSON_TYPE, text(`${asset},"buffers":[{"byteLength":2}]}`)], [BIN_TYPE, new Uint8Array(8)]]),
    buffer_without_bin: build([[JSON_TYPE, text(`${asset},"buffers":[{"byteLength":4}]}`)]]),
  };
  for (const [code, bytes] of Object.entries(cases)) assert.equal(codeOf(() => parseGlb(bytes)), code, code);
  assert.equal(codeOf(() => parseGlb('not bytes')), 'TypeError');
  assert.equal(codeOf(() => parseGlb(good)), 'accepted', 'the unchanged container is still accepted');
});

test('known wrong: encodeGlb refuses an inconsistent buffer binding', () => {
  assert.equal(codeOf(() => encodeGlb({asset: {version: '2.0'}, buffers: [{byteLength: 6}]}, new Uint8Array(5))),
    'buffer_binding');
  assert.equal(codeOf(() => encodeGlb({asset: {version: '2.0'}, buffers: [{byteLength: 4}]})), 'buffer_without_bin');
  assert.equal(codeOf(() => encodeGlb([1, 2])), 'TypeError');
  const error = new GlbError('magic', 'not a GLB');
  assert.deepEqual([error.name, error.code, error.message], ['GlbError', 'magic', 'magic: not a GLB']);
});
