// GLB container codec: read and write the binary glTF 2.0 container (a 12-byte header, a JSON chunk and an optional
// binary chunk) with strict validation and a reason code on every refusal. Original Baltor implementation written
// from the binary container layout of the glTF 2.0 specification; works on ArrayBuffers and typed arrays in a page,
// a worker or Node, and needs no three.js.

/** The container constants of glTF 2.0 binary files. */
export const GLB_FORMAT = Object.freeze({
  magic: 0x46546c67,
  version: 2,
  jsonChunkType: 0x4e4f534a,
  binChunkType: 0x004e4942,
  headerBytes: 12,
  chunkHeaderBytes: 8,
  alignment: 4,
});

const SPACE = 0x20;
const BYTE_ORDER_MARK = String.fromCharCode(0xfeff);
const MAXIMUM_BIN_PADDING = 3;

/** A refused container: code is a stable reason (magic, version, length_mismatch, chunk_truncated, ...). */
export class GlbError extends Error {
  constructor(code, message) {
    super(`${code}: ${message}`);
    this.name = 'GlbError';
    this.code = code;
  }
}

function asBytes(data, name) {
  if (data instanceof ArrayBuffer) return new Uint8Array(data);
  if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
  throw new TypeError(`${name} must be an ArrayBuffer or a typed array`);
}

function padded(length) {
  return Math.ceil(length / GLB_FORMAT.alignment) * GLB_FORMAT.alignment;
}

function chunkName(type) {
  if (type === GLB_FORMAT.jsonChunkType) return 'JSON';
  if (type === GLB_FORMAT.binChunkType) return 'BIN';
  return `0x${type.toString(16).padStart(8, '0')}`;
}

function decodeJson(bytes) {
  let text;
  try {
    text = new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes);
  } catch (error) {
    throw new GlbError('json_not_utf8', 'the JSON chunk is not valid UTF-8');
  }
  if (text.startsWith(BYTE_ORDER_MARK)) throw new GlbError('json_bom', 'the JSON chunk starts with a byte order mark');
  let value;
  try {
    value = JSON.parse(text);
  } catch (error) {
    throw new GlbError('json_invalid', `the JSON chunk does not parse (${error.message})`);
  }
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new GlbError('json_not_object', 'the JSON chunk does not hold a glTF object');
  }
  return value;
}

/** True when the data starts with a glTF 2.0 binary header; never throws. */
export function isGlb(data) {
  let bytes;
  try {
    bytes = asBytes(data, 'data');
  } catch (error) {
    return false;
  }
  if (bytes.byteLength < GLB_FORMAT.headerBytes) return false;
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  return view.getUint32(0, true) === GLB_FORMAT.magic && view.getUint32(4, true) === GLB_FORMAT.version;
}

/**
 * Read a GLB container. Returns {json, binary, version, byteLength, chunks}: json is the parsed glTF object, binary
 * the BIN chunk as a Uint8Array view into the input (null when there is none, possibly with up to 3 padding bytes
 * beyond buffers[0].byteLength), chunks every chunk's {type, name, byteOffset, byteLength}. Chunks of unknown types
 * after the first two are listed and otherwise ignored, as the specification asks. Throws GlbError on any violation.
 */
export function parseGlb(data) {
  const bytes = asBytes(data, 'data');
  const minimum = GLB_FORMAT.headerBytes + GLB_FORMAT.chunkHeaderBytes;
  if (bytes.byteLength < minimum) throw new GlbError('too_short', `a GLB holds at least ${minimum} bytes`);
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  if (view.getUint32(0, true) !== GLB_FORMAT.magic) throw new GlbError('magic', 'the data does not start with glTF');
  const version = view.getUint32(4, true);
  if (version !== GLB_FORMAT.version) throw new GlbError('version', `container version ${version}, expected 2`);
  const length = view.getUint32(8, true);
  if (length !== bytes.byteLength) {
    throw new GlbError('length_mismatch', `the header gives ${length} bytes, the data holds ${bytes.byteLength}`);
  }
  if (length % GLB_FORMAT.alignment !== 0) throw new GlbError('length_unaligned', `${length} is not a multiple of 4`);
  const chunks = [];
  let json = null;
  let binary = null;
  let offset = GLB_FORMAT.headerBytes;
  while (offset < length) {
    if (offset + GLB_FORMAT.chunkHeaderBytes > length) {
      throw new GlbError('chunk_truncated', `a chunk header at byte ${offset} runs past the end`);
    }
    const chunkLength = view.getUint32(offset, true);
    const type = view.getUint32(offset + 4, true);
    const start = offset + GLB_FORMAT.chunkHeaderBytes;
    const end = start + chunkLength;
    if (end > length) throw new GlbError('chunk_truncated', `chunk ${chunks.length} runs past the end`);
    if (chunkLength % GLB_FORMAT.alignment !== 0) {
      throw new GlbError('chunk_unaligned', `chunk ${chunks.length} has ${chunkLength} bytes, not a multiple of 4`);
    }
    const index = chunks.length;
    chunks.push({type, name: chunkName(type), byteOffset: start, byteLength: chunkLength});
    if (index === 0) {
      if (type !== GLB_FORMAT.jsonChunkType) throw new GlbError('first_chunk_not_json', 'the first chunk must be JSON');
      json = decodeJson(bytes.subarray(start, end));
    } else if (type === GLB_FORMAT.jsonChunkType) {
      throw new GlbError('second_json_chunk', `chunk ${index} is a second JSON chunk`);
    } else if (type === GLB_FORMAT.binChunkType) {
      if (index !== 1) throw new GlbError('bin_chunk_not_second', `the BIN chunk is chunk ${index}, not chunk 1`);
      binary = bytes.subarray(start, end);
    }
    offset = end;
  }
  const first = Array.isArray(json.buffers) ? json.buffers[0] : undefined;
  if (binary) {
    if (!first || first.uri !== undefined) {
      throw new GlbError('bin_without_buffer', 'a BIN chunk needs buffers[0] without a uri');
    }
    const extra = binary.byteLength - first.byteLength;
    if (!(extra >= 0 && extra <= MAXIMUM_BIN_PADDING)) {
      throw new GlbError('bin_length_mismatch', `buffers[0] has ${first.byteLength} bytes, the BIN chunk ${binary.byteLength}`);
    }
  } else if (first && first.uri === undefined) {
    throw new GlbError('buffer_without_bin', 'buffers[0] has no uri but the container has no BIN chunk');
  }
  return {json, binary, version, byteLength: length, chunks};
}

/**
 * Write a GLB container: the JSON chunk padded with spaces and, when binary is given, the BIN chunk padded with
 * zeros. buffers[0] must then have no uri and a byteLength equal to binary's length; without binary, a buffers[0]
 * without a uri is refused. Returns a Uint8Array that owns its ArrayBuffer.
 */
export function encodeGlb(json, binary = null) {
  if (!json || typeof json !== 'object' || Array.isArray(json)) throw new TypeError('json must be a glTF object');
  const bin = binary === null || binary === undefined ? null : asBytes(binary, 'binary');
  const first = Array.isArray(json.buffers) ? json.buffers[0] : undefined;
  if (bin) {
    if (!first || first.uri !== undefined || first.byteLength !== bin.byteLength) {
      throw new GlbError('buffer_binding', 'buffers[0] must have no uri and byteLength equal to the binary length');
    }
  } else if (first && first.uri === undefined) {
    throw new GlbError('buffer_without_bin', 'buffers[0] has no uri, so the binary data must be given');
  }
  const text = new TextEncoder().encode(JSON.stringify(json));
  const jsonLength = padded(text.length);
  const binLength = bin ? padded(bin.length) : 0;
  const total = GLB_FORMAT.headerBytes + GLB_FORMAT.chunkHeaderBytes + jsonLength
    + (bin ? GLB_FORMAT.chunkHeaderBytes + binLength : 0);
  const out = new Uint8Array(total);
  const view = new DataView(out.buffer);
  view.setUint32(0, GLB_FORMAT.magic, true);
  view.setUint32(4, GLB_FORMAT.version, true);
  view.setUint32(8, total, true);
  view.setUint32(12, jsonLength, true);
  view.setUint32(16, GLB_FORMAT.jsonChunkType, true);
  const jsonStart = GLB_FORMAT.headerBytes + GLB_FORMAT.chunkHeaderBytes;
  out.set(text, jsonStart);
  out.fill(SPACE, jsonStart + text.length, jsonStart + jsonLength);
  if (bin) {
    const at = jsonStart + jsonLength;
    view.setUint32(at, binLength, true);
    view.setUint32(at + 4, GLB_FORMAT.binChunkType, true);
    out.set(bin, at + GLB_FORMAT.chunkHeaderBytes);
  }
  return out;
}
