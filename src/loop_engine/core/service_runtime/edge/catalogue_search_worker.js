// Baltor catalogue search at the edge: engine (d) of the catalogue_search_index slot.
//
// One Cloudflare Worker answers one published release's search from a D1 database (FTS5, filters and the
// public fields of each hit) and a KV namespace (the 512 float32 hash-vector columns). Python builds both
// (catalogue_d1_index.export_index) from the same functions the in-memory engine uses; this file ranks exactly
// as catalogue_search.ReleaseSearchIndex ranks and fuses exactly as catalogue_search.fuse fuses. Every
// vocabulary, limit, label and refusal sentence comes from the build record's profile, which Python wrote from
// the service's own constants; nothing below restates them.
//
// Bindings: DB (D1), VECTORS (KV), KEYS (JSON list of {id, public_key, scopes}: Ed25519 public keys allowed to
// sign requests; no secret is held here). Routes: GET /v1/ping (unsigned), GET /v1/index, POST /v1/rank,
// POST /api/v1/retrieval (scope search), POST /v1/admin/vectors (scope admin).
//
// The same module runs under Node's SQLite in the conformance kit (local_worker_host.mjs), so it uses only web
// standard APIs.

const TOKEN = /[a-z0-9]+/g;
const VECTOR_DIMENSIONS = 512;
const SIGNATURE_CONTEXT = "baltor-edge-search/v1";
const SIGNATURE_WINDOW_SECONDS = 300;
const QUERY_RECORD = "catalogue_search_index_query/v1";
const POOLS_RECORD = "catalogue_search_index_pools/v1";
const BUILD_RECORD = "catalogue_d1_index_build/v1";
const INDEX_FORMAT = "catalogue_d1_index/v1";
const MAXIMUM_VECTOR_UPLOAD_BYTES = 96 * 1024 * 1024;
const BUILD_TTL_MS = 60_000;

// ------------------------------------------------------------------------------------------ pure functions ----

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

const ENCODER = new TextEncoder();

/** zlib.crc32 of the UTF-8 bytes of a string, as an unsigned 32-bit number. */
export function crc32(text) {
  const bytes = ENCODER.encode(text);
  let crc = 0xffffffff;
  for (let i = 0; i < bytes.length; i++) crc = CRC_TABLE[(crc ^ bytes[i]) & 0xff] ^ (crc >>> 8);
  return (crc ^ 0xffffffff) >>> 0;
}

/** The words of a text, as core.retrieval._tokens and catalogue_search._TOKEN read them. */
export function tokens(text) {
  return String(text ?? "").toLowerCase().match(TOKEN) || [];
}

/** core.retrieval.hash_vector: nonzero (dimension, weight) pairs in increasing dimension, bit for bit. */
export function hashVector(text) {
  const counts = new Float64Array(VECTOR_DIMENSIONS);
  for (const token of tokens(text)) {
    counts[crc32(`tok:${token}`) % VECTOR_DIMENSIONS] += 2.0;
    const padded = `##${token}##`;
    for (let i = 0; i < padded.length - 2; i++) counts[crc32(`3g:${padded.slice(i, i + 3)}`) % VECTOR_DIMENSIONS] += 1.0;
  }
  // Whole-number counts: every square and every partial sum is exact, so the order of addition cannot matter.
  let sum = 0;
  for (let d = 0; d < VECTOR_DIMENSIONS; d++) sum += counts[d] * counts[d];
  const norm = Math.sqrt(sum) || 1.0;
  const weights = [];
  for (let d = 0; d < VECTOR_DIMENSIONS; d++) if (counts[d]) weights.push([d, counts[d] / norm]);
  return weights;
}

/** Python's round(x, digits): the exact binary value rounded half to even, as float.__round__ does. */
export function pyRound(x, digits) {
  if (!Number.isFinite(x) || x === 0) return x;
  const negative = x < 0;
  const fixed = Math.abs(x).toFixed(100);
  const [whole, fraction] = fixed.split(".");
  const kept = whole + fraction.slice(0, digits);
  const rest = fraction.slice(digits);
  let up = false;
  if (rest[0] > "5") up = true;
  else if (rest[0] === "5") up = /[1-9]/.test(rest.slice(1)) || (Number(kept[kept.length - 1]) % 2 === 1);
  let digitsText = kept;
  if (up) {
    const chars = digitsText.split("");
    let i = chars.length - 1;
    while (i >= 0) {
      if (chars[i] === "9") { chars[i] = "0"; i--; } else { chars[i] = String(Number(chars[i]) + 1); break; }
    }
    digitsText = (i < 0 ? "1" : "") + chars.join("");
  }
  const point = digitsText.length - digits;
  const value = Number(`${digitsText.slice(0, point) || "0"}.${digitsText.slice(point)}`);
  return negative ? -value : value;
}

/** catalogue_search.fuse: reciprocal rank fusion over the authorized candidates, tiers first. */
export function fuse(pools, allowed, offset, topN, tierOrder) {
  const fused = new Map();
  for (const name of Object.keys(pools)) {
    let rank = 0;
    for (const [identity] of pools[name]) {
      if (!allowed.has(identity)) continue;
      let entry = fused.get(identity);
      if (!entry) { entry = [0.0, new Set()]; fused.set(identity, entry); }
      entry[0] += 1.0 / (offset + rank);
      entry[1].add(name);
      rank++;
    }
  }
  const tierRank = (identity) => {
    const row = allowed.get(identity);
    return row && row.tier in tierOrder ? tierOrder[row.tier] : 0;
  };
  const ordered = [...fused.entries()].sort((a, b) =>
    tierRank(a[0]) - tierRank(b[0]) || b[1][0] - a[1][0] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0));
  return ordered.slice(0, topN).map(([identity, [score, modes]]) => [identity, pyRound(score, 5), [...modes].sort()]);
}

/** The best `limit` of (score, position) by descending score, then ascending position: heapq.nsmallest. */
function best(scores, size, limit, floor, keep) {
  const heap = []; // a max-heap on the order key, holding the best `limit` seen so far
  const worse = (a, b) => (a[0] !== b[0] ? a[0] < b[0] : a[1] > b[1]); // a ranks below b
  const swap = (i, j) => { const t = heap[i]; heap[i] = heap[j]; heap[j] = t; };
  for (let p = 0; p < size; p++) {
    const score = scores[p];
    if (!(score > floor) || (keep && !keep[p])) continue;
    const row = [score, p];
    if (heap.length < limit) {
      heap.push(row);
      let i = heap.length - 1;
      while (i > 0) { const up = (i - 1) >> 1; if (worse(heap[i], heap[up])) { swap(i, up); i = up; } else break; }
    } else if (worse(heap[0], row)) {
      heap[0] = row;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < heap.length && worse(heap[l], heap[m])) m = l;
        if (r < heap.length && worse(heap[r], heap[m])) m = r;
        if (m === i) break;
        swap(i, m); i = m;
      }
    }
  }
  return heap.sort((a, b) => (a[0] !== b[0] ? b[0] - a[0] : a[1] - b[1]));
}

// ---------------------------------------------------------------------------------------------- refusals ----

class Refusal extends Error {
  constructor(code, status) { super(code); this.code = code; this.status = status; }
}

function refusalResponse(error, profile) {
  const code = error instanceof Refusal ? error.code : "search_index_unavailable";
  const stated = profile?.refusals?.[code];
  // The status the service gives a code wins; the thrown status serves only before the profile is read.
  const status = stated?.status ?? (error instanceof Refusal && error.status ? error.status : 503);
  const reference = crypto.randomUUID().replace(/-/g, "");
  const record = {
    record_type: profile?.error_record_type ?? "service_http_error/v1",
    error: { code, message: stated?.message ?? "The request could not be answered.",
             next_action: stated?.next_action ?? "Try again later." },
    effect_commitment: "not_asserted", automatic_retry: false, request_reference: reference,
  };
  return json(record, status);
}

function json(value, status = 200, headers = {}) {
  return new Response(JSON.stringify(value), {
    status, headers: { "content-type": "application/json", "cache-control": "no-store", ...headers },
  });
}

// ------------------------------------------------------------------------------------------- signatures ----

function base64ToBytes(text) {
  const normal = text.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normal + "=".repeat((4 - (normal.length % 4)) % 4);
  const binary = atob(padded);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function sha256Hex(bytes) {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return [...digest].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function authorize(request, env, scope, body, now) {
  const header = request.headers.get("authorization") || "";
  const parts = header.split(" ");
  if (parts.length !== 5 || parts[0] !== "Baltor-Signature" || parts[1] !== "v1") throw new Refusal("unauthorized", 401);
  const [, , keyId, stamp, signature] = parts;
  let keys;
  try { keys = JSON.parse(env.KEYS || "[]"); } catch { throw new Refusal("unauthorized", 401); }
  const key = Array.isArray(keys) ? keys.find((entry) => entry && entry.id === keyId) : undefined;
  const timestamp = Number(stamp);
  if (!key || !Array.isArray(key.scopes) || !key.scopes.includes(scope) || !/^[0-9]{1,12}$/.test(stamp)
      || Math.abs(now / 1000 - timestamp) > SIGNATURE_WINDOW_SECONDS) throw new Refusal("unauthorized", 401);
  const url = new URL(request.url);
  const message = ENCODER.encode([SIGNATURE_CONTEXT, request.method.toUpperCase(), url.pathname + url.search,
    String(timestamp), await sha256Hex(body)].join("\n"));
  let valid = false;
  try {
    const publicKey = await crypto.subtle.importKey("raw", base64ToBytes(key.public_key), { name: "Ed25519" }, false,
      ["verify"]);
    valid = await crypto.subtle.verify({ name: "Ed25519" }, publicKey, base64ToBytes(signature), message);
  } catch { valid = false; }
  if (!valid) throw new Refusal("unauthorized", 401);
}

// ------------------------------------------------------------------------------------------- the index ----

let heldBuild = null;

async function currentBuild(env, timing) {
  const now = Date.now();
  if (heldBuild && now - heldBuild.at < BUILD_TTL_MS) return heldBuild.build;
  const row = await query(env, timing, "SELECT value FROM catalogue_index WHERE key = 'build'", [], "first");
  if (!row) throw new Refusal("search_index_unavailable", 503);
  const build = JSON.parse(row.value);
  if (build.record_type !== BUILD_RECORD || build.format !== INDEX_FORMAT) throw new Refusal("search_index_unavailable", 503);
  heldBuild = { build, at: now };
  return build;
}

async function query(env, timing, sql, params, shape = "all") {
  const started = Date.now();
  const statement = env.DB.prepare(sql).bind(...params);
  let result;
  try {
    result = shape === "first" ? await statement.first() : await statement.all();
  } catch {
    throw new Refusal("search_index_unavailable", 503);
  } finally {
    timing.d1 += Date.now() - started;
    timing.queries += 1;
  }
  if (shape === "first") return result;
  timing.rowsRead += result?.meta?.rows_read ?? 0;
  return result.results;
}

async function identitiesOf(env, timing, positions) {
  if (!positions.length) return new Map();
  const rows = await query(env, timing,
    "SELECT position, identity, tier, effects FROM entries WHERE position IN (SELECT value FROM json_each(?1))",
    [JSON.stringify(positions)]);
  const held = new Map();
  for (const row of rows) held.set(row.position, row);
  if (held.size !== new Set(positions).size) throw new Refusal("search_index_unavailable", 503);
  return held;
}

async function lexical(env, timing, build, text, pool, keep) {
  const terms = tokens(text);
  if (!terms.length || !build.entries) return { rows: [], exhausted: true };
  const match = terms.slice(0, build.lexical_terms).map((term) => `"${term}"`).join(" OR ");
  const limit = keep ? build.entries : pool;
  const rows = await query(env, timing,
    "SELECT rowid AS position, bm25(entries_text) AS score FROM entries_text WHERE entries_text MATCH ?1 " +
    "ORDER BY bm25(entries_text), rowid LIMIT ?2", [match, limit]);
  const kept = keep ? rows.filter((row) => keep[row.position]) : rows;
  const chosen = keep ? kept.slice(0, pool) : kept;
  return { rows: chosen.map((row) => [row.position, -row.score]),
           exhausted: keep ? kept.length <= pool : rows.length < limit };
}

async function vector(env, timing, build, text, pool, keep) {
  const weights = hashVector(text);
  if (!weights.length || !build.entries) return { rows: [], exhausted: true };
  const started = Date.now();
  const columns = await Promise.all(weights.map(([dimension]) =>
    env.VECTORS.get(`${build.build_id}/${String(dimension).padStart(3, "0")}`, { type: "arrayBuffer", cacheTtl: 86400 })));
  timing.kv += Date.now() - started;
  timing.columns += columns.length;
  const scores = new Float64Array(build.entries);
  for (let i = 0; i < weights.length; i++) {
    const buffer = columns[i];
    if (!buffer || buffer.byteLength !== 4 * build.entries) throw new Refusal("search_index_unavailable", 503);
    const column = new Float32Array(buffer);
    const weight = weights[i][1];
    // As the in-memory engine: the first dimension's products, then each later dimension added in order.
    if (i === 0) for (let p = 0; p < build.entries; p++) scores[p] = column[p] * weight;
    else for (let p = 0; p < build.entries; p++) scores[p] += column[p] * weight;
  }
  const top = best(scores, build.entries, pool + 1, build.policy.hash_similarity_floor, keep);
  return { rows: top.slice(0, pool).map(([score, position]) => [position, score]), exhausted: top.length <= pool };
}

async function eligibleMask(env, timing, build, conditions) {
  let chosen = null;
  for (const [name, operator, operand] of conditions) {
    const declared = build.filters[name];
    const mask = new Uint8Array(build.entries);
    if (operator === "any_of") {
      if (!declared || declared.kind !== "keyword") throw new Refusal("search_filter_not_allowed", 400);
      const buckets = [...new Set(operand.map((value) => crc32(String(value)) % declared.buckets))];
      const rows = await query(env, timing,
        "SELECT bucket, data FROM keyword_postings WHERE attribute = ?1 AND bucket IN (SELECT value FROM json_each(?2))",
        [name, JSON.stringify(buckets)]);
      const tables = rows.map((row) => JSON.parse(row.data));
      for (const value of operand) for (const table of tables) for (const p of table[value] || []) mask[p] = 1;
    } else if (operator === "range") {
      if (!declared || declared.kind !== "range") throw new Refusal("search_filter_not_allowed", 400);
      const rows = await query(env, timing,
        "SELECT chunk, data FROM range_postings WHERE attribute = ?1 ORDER BY chunk", [name]);
      const pairs = rows.flatMap((row) => JSON.parse(row.data));
      const [low, high] = operand;
      const below = (value, bound) => (typeof value === "number" ? value < bound : value < bound);
      let start = 0, end = pairs.length;
      if (low !== null && low !== undefined) { let lo = 0, hi = pairs.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (below(pairs[mid][0], low)) lo = mid + 1; else hi = mid; } start = lo; }
      if (high !== null && high !== undefined) { let lo = 0, hi = pairs.length; while (lo < hi) { const mid = (lo + hi) >> 1; if (below(high, pairs[mid][0])) hi = mid; else lo = mid + 1; } end = lo; }
      for (let i = start; i < end; i++) mask[pairs[i][1]] = 1;
    } else {
      throw new Refusal("search_filter_invalid", 400);
    }
    if (chosen) for (let p = 0; p < build.entries; p++) chosen[p] &= mask[p];
    else chosen = mask;
  }
  return chosen;
}

/** ReleaseSearchIndex.rank over positions: the lexical pool, and for hybrid search the vector pool. */
async function rankPositions(env, timing, build, text, mode, pool, keep) {
  const lex = await lexical(env, timing, build, text, pool, keep);
  const pools = { lexical: lex.rows };
  let exhausted = lex.exhausted;
  if (mode === "hybrid") {
    const vec = await vector(env, timing, build, text, pool, keep);
    pools.vector = vec.rows;
    exhausted = exhausted && vec.exhausted;
  }
  return { pools, exhausted };
}

async function rankIdentities(env, timing, build, text, mode, pool, keep) {
  const { pools, exhausted } = await rankPositions(env, timing, build, text, mode, pool, keep);
  const positions = [...new Set(Object.values(pools).flatMap((rows) => rows.map(([position]) => position)))];
  const rows = await identitiesOf(env, timing, positions);
  const named = {};
  for (const name of Object.keys(pools)) named[name] = pools[name].map(([position, score]) => [rows.get(position).identity, score]);
  return { pools: named, exhausted, rows };
}

// ----------------------------------------------------------------------------------- the account profile ----

/** Text Python's str.strip() would leave empty: only characters str.isspace() accepts. */
const PY_BLANK = /^[\t\n\x0b\x0c\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]*$/u;
const PY_SPACE = /^[\t\n\x0b\x0c\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]|[\t\n\x0b\x0c\r\x1c-\x1f \x85\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]$/u;
const NOT_PRINTABLE = /[\p{Cc}\p{Cf}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}]|(?! )\p{Zs}/u;

function boundedText(value, limit) {
  return typeof value === "string" && !PY_SPACE.test(value) && [...value].length > 0 && [...value].length <= limit
    && !NOT_PRINTABLE.test(value);
}

function validDate(value) {
  if (typeof value !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  if (year < 1 || month < 1 || month > 12 || day < 1) return false;
  const leap = (year % 4 === 0 && year % 100 !== 0) || year % 400 === 0;
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1];
  return day <= days;
}

/** CatalogueAttribute.value for the scalar types a filter compares. */
function attributeValue(attribute, raw, limits) {
  const kind = attribute.type;
  if (kind === "text" && boundedText(raw, 2000)) return raw;
  if (kind === "keyword" && boundedText(raw, limits.maximum_keyword_characters)) return raw;
  if (kind === "choice" && typeof raw === "string" && attribute.choices.includes(raw)) return raw;
  if (kind === "number" && typeof raw === "number" && Number.isFinite(raw) && Math.abs(raw) <= limits.maximum_number) return raw;
  if (kind === "date" && validDate(raw)) return raw;
  throw new Refusal("attribute_value_invalid", 400);
}

/** CatalogueAttributeSchema.filter_request: typed conditions, or a refusal before anything is ranked. */
function filterRequest(schema, filters, limits) {
  if (filters === undefined) return [];
  if (filters === null || typeof filters !== "object" || Array.isArray(filters)
      || Object.keys(filters).length > limits.maximum_filters) throw new Refusal("search_filter_invalid", 400);
  const byName = new Map(schema.attributes.map((attribute) => [attribute.name, attribute]));
  const operators = new Set(["equals", "any_of", "at_least", "at_most"]);
  const conditions = [];
  for (const name of Object.keys(filters).sort()) {
    const declared = byName.get(name);
    if (!declared || declared.visibility !== "public" || !declared.filterable) throw new Refusal("search_filter_not_allowed", 400);
    const condition = filters[name];
    const keys = condition && typeof condition === "object" && !Array.isArray(condition) ? Object.keys(condition) : null;
    const range = declared.type === "number" || declared.type === "date";
    if (!keys || !keys.length || keys.some((key) => !operators.has(key))
        || (keys.includes("equals") && keys.length !== 1) || (keys.includes("any_of") && keys.length !== 1)
        || ((keys.includes("at_least") || keys.includes("at_most")) && !range)) throw new Refusal("search_filter_invalid", 400);
    const scalar = declared.type === "keyword_list" ? { ...declared, type: "keyword" } : declared;
    if (keys.includes("any_of")) {
      const wanted = condition.any_of;
      if (!Array.isArray(wanted) || !wanted.length || wanted.length > limits.maximum_list_values) throw new Refusal("search_filter_invalid", 400);
      conditions.push([name, "any_of", wanted.map((value) => attributeValue(scalar, value, limits))]);
    } else if (keys.includes("equals")) {
      conditions.push([name, "any_of", [attributeValue(scalar, condition.equals, limits)]]);
    } else {
      const low = "at_least" in condition ? attributeValue(scalar, condition.at_least, limits) : null;
      const high = "at_most" in condition ? attributeValue(scalar, condition.at_most, limits) : null;
      conditions.push([name, "range", [low, high]]);
    }
  }
  return conditions;
}

function enumList(value, allowed, minimum) {
  return Array.isArray(value) && value.length >= minimum && new Set(value.map((x) => JSON.stringify(x))).size === value.length
    && value.every((item) => typeof item === "string" && allowed.includes(item));
}

/** ServiceHttpApplication._validate_search, then effect_selection with the step effects header. */
function validateSearch(payload, profile, headers, floats = new Set()) {
  if (payload === null || typeof payload !== "object" || Array.isArray(payload)) throw new Refusal("object_required", 400);
  const allowed = new Set([...profile.request_fields, "record_type"]);
  if (Object.keys(payload).some((key) => !allowed.has(key))) throw new Refusal("unknown_request_field", 400);
  if (payload.record_type !== profile.request_record_type) throw new Refusal("unsupported_version", 400);
  const query = payload.query;
  if (typeof query !== "string" || PY_BLANK.test(query) || ENCODER.encode(query).length > profile.maximum_query_bytes) throw new Refusal("invalid_query", 400);
  if (!profile.modes.includes("mode" in payload ? payload.mode : "lexical")) throw new Refusal("unsupported_retrieval_mode", 400);
  const topN = "top_n" in payload ? payload.top_n : 10;
  if (typeof topN !== "number" || !Number.isInteger(topN) || floats.has(payload) || topN < 1
      || topN > profile.maximum_search_results) throw new Refusal("invalid_search_limit", 400);
  if ("filters" in payload && (payload.filters === null || typeof payload.filters !== "object" || Array.isArray(payload.filters))) throw new Refusal("search_filter_invalid", 400);
  if ("authority_effects" in payload && !enumList(payload.authority_effects, profile.effects, 0)) throw new Refusal("invalid_request", 400);
  if ("library_tiers" in payload && !enumList(payload.library_tiers, profile.library_tiers, 1)) throw new Refusal("invalid_request", 400);
  const fields = { ...payload };
  delete fields.record_type;
  const raw = headers.get(profile.step_effects_header);
  let headerEffects = [];
  if (raw !== null) {
    const names = raw.split(",").map((part) => part.trim());
    if (!names.length || names.some((name) => !name) || new Set(names).size !== names.length
        || names.some((name) => !profile.step_effects.includes(name))) throw new Refusal("invalid_step_effects", 400);
    headerEffects = names;
  }
  if ("authority_effects" in fields) return { fields, step: [...fields.authority_effects] };
  return { fields: { ...fields, authority_effects: [...profile.effects] },
           step: headerEffects.length ? headerEffects : [...profile.default_step_effects] };
}

/** catalogue_tiers.narrowed for the profile's default library setting. */
function communityChoice(profile, tiers) {
  if (tiers === undefined) return profile.community_default;
  if (!tiers.includes(profile.verified_tier)) throw new Refusal("library_tiers_invalid", 400);
  return tiers.includes(profile.community_tier) ? profile.community_default : profile.community_excluded;
}

/** provisioning_server.in_library: whether an approved item belongs to what this community choice may be offered. */
function inLibrary(profile, row, effects, community) {
  if (row.tier === profile.verified_tier) return true;
  if (row.tier !== profile.community_tier || !profile.community_choices.includes(community)) return false;
  if (community === profile.community_included) return true;
  return community === profile.community_without_runnable && !effects.includes(profile.runnable_effect);
}

async function retrieval(env, timing, build, parsed, headers) {
  const profile = build.profile;
  if (!profile || !build.hits) throw new Refusal("route_unavailable", 404);
  const { fields, step } = validateSearch(parsed.value, profile, headers, parsed.floats);
  const community = communityChoice(profile, fields.library_tiers);
  delete fields.library_tiers;
  const conditions = filterRequest(build.schema, fields.filters, profile.filters);
  const keep = conditions.length ? await eligibleMask(env, timing, build, conditions) : null;
  const topN = "top_n" in fields ? fields.top_n : 10;
  const mode = "mode" in fields ? fields.mode : "lexical";
  const authority = fields.authority_effects;
  let pool = Math.max(1, topN * build.policy.candidate_pool_multiplier);
  const total = Math.max(1, build.entries);
  let hits, allowed;
  for (;;) {
    const ranked = await rankIdentities(env, timing, build, fields.query, mode, pool, keep);
    allowed = new Map();
    for (const row of ranked.rows.values()) {
      const effects = JSON.parse(row.effects);
      if (inLibrary(profile, row, effects, community) && effects.every((effect) => authority.includes(effect))) {
        allowed.set(row.identity, { tier: row.tier, position: row.position });
      }
    }
    hits = fuse(ranked.pools, allowed, build.policy.reciprocal_rank_offset, topN, profile.tier_order);
    if (hits.length >= topN || ranked.exhausted || pool >= total) break;
    pool = Math.min(total, pool * 4);
  }
  const stored = await query(env, timing,
    "SELECT position, hit FROM entries WHERE position IN (SELECT value FROM json_each(?1))",
    [JSON.stringify(hits.map(([identity]) => allowed.get(identity).position))]);
  const byPosition = new Map(stored.map((row) => [row.position, JSON.parse(row.hit)]));
  const answered = hits.map(([identity, score, modes]) => {
    const fixed = byPosition.get(allowed.get(identity).position);
    if (!fixed || fixed.reference.identity !== identity) throw new Refusal("search_index_unavailable", 503);
    return { reference: fixed.reference, purpose: fixed.purpose, kind: fixed.kind, size_bytes: fixed.size_bytes,
             license: fixed.license, declared_effects: fixed.declared_effects, harness_styles: fixed.harness_styles,
             score, modes, qualification_basis: fixed.qualification_basis, library_tier: fixed.library_tier,
             library_tier_label: fixed.library_tier_label, body_allowed: profile.body_allowed,
             attributes: fixed.attributes, package: fixed.package,
             effects_to_declare: fixed.declared_effects.filter((effect) => effect !== "pure" && !step.includes(effect)) };
  });
  const result = { record_type: profile.result_record_type, hits: answered, step_effects: step,
                   step_effects_header: profile.step_effects_header, mode, bodies_loaded: false,
                   backend: profile.backend, catalogue_release: build.release_id || null,
                   limitations: profile.limitations };
  if (!answered.length) result.ask_for_material = profile.ask_for_material;
  return { record_type: profile.envelope_record_type, operation: "retrieval", result };
}

// ---------------------------------------------------------------------------------------------- routes ----

function depth(value, limit) {
  let deepest = 0;
  const stack = [[value, 1]];
  while (stack.length) {
    const [node, level] = stack.pop();
    if (node && typeof node === "object") {
      deepest = Math.max(deepest, level);
      if (deepest > limit) return deepest;
      for (const child of Object.values(node)) stack.push([child, level + 1]);
    }
  }
  return deepest;
}

/** Parse a request body. Numbers written with a fraction or an exponent are floats to Python, and a field that
 *  must be a whole number (`top_n`) is refused for them as the service refuses them; the holders of such fields
 *  are returned beside the value, read from the source text the parser exposes. */
function parseJson(bytes, profile) {
  let value;
  const floats = new Set();
  const integral = /^-?(0|[1-9][0-9]*)$/;
  try {
    value = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes), function (key, item, context) {
      if (typeof item === "number" && context && typeof context.source === "string" && !integral.test(context.source)) {
        floats.add(`${key}`);
        if (key === "top_n") floats.add(this);
      }
      return item;
    });
  } catch { throw new Refusal("invalid_json", 400); }
  if (depth(value, profile?.maximum_json_depth ?? 64) > (profile?.maximum_json_depth ?? 64)) throw new Refusal("nesting_limit_exceeded", 400);
  return { value, floats };
}

async function readBody(request, limit) {
  const stated = Number(request.headers.get("content-length") || "0");
  if (stated > limit) throw new Refusal("request_limit_exceeded", 413);
  const body = new Uint8Array(await request.arrayBuffer());
  if (body.length > limit) throw new Refusal("request_limit_exceeded", 413);
  return body;
}

async function rank(env, timing, build, payload) {
  const keys = payload && typeof payload === "object" && !Array.isArray(payload) ? Object.keys(payload).sort().join(",") : "";
  if (keys !== "build_id,conditions,mode,pool,query,record_type" || payload.record_type !== QUERY_RECORD) throw new Refusal("invalid_request", 400);
  if (payload.build_id !== build.build_id) throw new Refusal("search_index_changed", 409);
  if (typeof payload.query !== "string" || ENCODER.encode(payload.query).length > 4096
      || !["lexical", "hybrid"].includes(payload.mode) || !Number.isInteger(payload.pool) || payload.pool < 1) throw new Refusal("invalid_request", 400);
  const conditions = payload.conditions;
  if (conditions !== null && (!Array.isArray(conditions) || conditions.some((row) => !Array.isArray(row) || row.length !== 3
      || typeof row[0] !== "string" || !Array.isArray(row[2])))) throw new Refusal("invalid_request", 400);
  const keep = conditions && conditions.length ? await eligibleMask(env, timing, build, conditions) : null;
  const ranked = await rankIdentities(env, timing, build, payload.query, payload.mode, payload.pool, keep);
  return { record_type: POOLS_RECORD, build_id: build.build_id, mode: payload.mode, pools: ranked.pools, exhausted: ranked.exhausted };
}

async function loadVectors(env, timing, build, body) {
  const magic = new TextDecoder().decode(body.slice(0, 8));
  if (magic !== "BALTORV1" || body.length < 12) throw new Refusal("invalid_request", 400);
  const headerLength = new DataView(body.buffer, body.byteOffset + 8, 4).getUint32(0, true);
  let header;
  try { header = JSON.parse(new TextDecoder().decode(body.slice(12, 12 + headerLength))); } catch { throw new Refusal("invalid_request", 400); }
  if (header.build_id !== build.build_id) throw new Refusal("search_index_changed", 409);
  const digests = header.column_digests;
  if (!Array.isArray(digests) || digests.length !== VECTOR_DIMENSIONS
      || await sha256Hex(ENCODER.encode(digests.join("\n"))) !== build.vectors_digest
      || header.column_bytes !== 4 * build.entries || !Array.isArray(header.dimensions)
      || body.length !== 12 + headerLength + header.dimensions.length * header.column_bytes) throw new Refusal("invalid_request", 400);
  let offset = 12 + headerLength;
  const written = [];
  for (const dimension of header.dimensions) {
    if (!Number.isInteger(dimension) || dimension < 0 || dimension >= VECTOR_DIMENSIONS) throw new Refusal("invalid_request", 400);
    const column = body.slice(offset, offset + header.column_bytes);
    offset += header.column_bytes;
    if (await sha256Hex(column) !== digests[dimension]) throw new Refusal("invalid_request", 400);
    written.push([dimension, column]);
  }
  // Every column is checked before the first write, so a bad upload writes nothing.
  for (const [dimension, column] of written) {
    await env.VECTORS.put(`${build.build_id}/${String(dimension).padStart(3, "0")}`, column);
  }
  return { record_type: "catalogue_d1_vector_upload/v1", build_id: build.build_id, written: written.map(([d]) => d) };
}

export async function handle(request, env, now = Date.now()) {
  const started = Date.now();
  const timing = { d1: 0, kv: 0, queries: 0, rowsRead: 0, columns: 0 };
  const url = new URL(request.url);
  let profile = null;
  try {
    if (url.pathname === "/v1/ping" && request.method === "GET") return json({ record_type: "catalogue_edge_ping/v1", ok: true });
    const routes = { "/v1/index": ["GET", "search"], "/v1/rank": ["POST", "search"],
                     "/api/v1/retrieval": ["POST", "search"], "/v1/admin/vectors": ["POST", "admin"] };
    const route = routes[url.pathname];
    if (!route) throw new Refusal("route_unavailable", 404);
    if (request.method !== route[0]) throw new Refusal("method_not_allowed", 405);
    const limit = route[1] === "admin" ? MAXIMUM_VECTOR_UPLOAD_BYTES : 65_536;
    const body = route[0] === "POST" ? await readBody(request, limit) : new Uint8Array();
    await authorize(request, env, route[1], body, now);
    const build = await currentBuild(env, timing);
    profile = build.profile;
    let answer;
    if (url.pathname === "/v1/index") answer = build;
    else if (url.pathname === "/v1/admin/vectors") answer = await loadVectors(env, timing, build, body);
    else if (url.pathname === "/v1/rank") answer = await rank(env, timing, build, parseJson(body, profile).value);
    else answer = await retrieval(env, timing, build, parseJson(body, profile), request.headers);
    const total = Date.now() - started;
    return json(answer, 200, {
      "server-timing": `d1;dur=${timing.d1};desc="${timing.queries} queries", kv;dur=${timing.kv};desc="${timing.columns} columns", total;dur=${total}`,
      "x-baltor-rows-read": String(timing.rowsRead),
    });
  } catch (error) {
    return refusalResponse(error, profile);
  }
}

export default {
  async fetch(request, env) {
    return handle(request, env);
  },
};
