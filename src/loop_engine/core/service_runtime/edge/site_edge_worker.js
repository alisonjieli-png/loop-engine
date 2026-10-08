// Baltor's website at the edge: the static_content_network engine of the web_page_delivery slot, in front of
// the origin as the content_network_proxy engine of the edge_proxy slot.
//
// Every page and asset the service would send an anonymous reader is a file of one export
// (static_site_export.py), served here with the exact headers the service sends; every other request goes to the
// origin unchanged. While the origin cannot answer (a release that rebuilds its catalogue view, a stopped
// machine), pages keep serving and a request that needs the origin gets the service's own unavailable page or
// refusal record with Retry-After.
//
// Bindings: ORIGIN (the origin's https origin), ORIGIN_MODE ("all" passes every method on canonical hosts;
// "read_only" and aliased preview hosts pass GET and HEAD only), EXPORT_ID, and
// either ASSETS (Workers static assets holding __edge/manifest.json and __edge/files/<sha256>) or SITE (a KV
// namespace holding <export>/manifest and <export>/f/<sha256>). HOST_ALIASES (JSON) maps hostnames that are not
// in the site map, such as a workers.dev name, to the hostname whose pages they show; such a hostname is also
// marked noindex, so a copy never competes with the canonical site.
//
// LOADER_KEYS (JSON list of Ed25519 public keys with the admin scope) switches on POST /__edge/admin/files, which
// writes one export into SITE when no static assets upload is available; production deploys the export as static
// assets from continuous integration and binds no LOADER_KEYS, so the route answers 404 there. The signature
// scheme is catalogue_search_worker.js's, kept inline so each Worker stays one module.

const MANIFEST_TTL_MS = 60_000;
// These transport ceilings exceed the origin's normal 64 KiB and staff 512 KiB
// request limits. The origin still owns route-specific validation. Count actual
// streamed bytes here before any forward; Content-Length is only an early check.
const MAXIMUM_PROXY_BODY_BYTES = 1_048_576;
const MAXIMUM_LOADER_BODY_BYTES = 10_485_760;
let held = null;

async function boundedBody(request, maximum) {
  const declared = request.headers.get("content-length");
  if (declared !== null && (!/^[0-9]+$/.test(declared) || Number(declared) > maximum)) return null;
  if (!request.body) return new Uint8Array();
  const reader = request.body.getReader();
  const chunks = [];
  let size = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > maximum) {
        await reader.cancel();
        return null;
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const body = new Uint8Array(size);
  let at = 0;
  for (const chunk of chunks) { body.set(chunk, at); at += chunk.byteLength; }
  return body;
}

function oversizedBody() {
  return textResponse(JSON.stringify({ record_type: "service_http_error/v1",
    error: { code: "request_too_large", message: "The request exceeds the edge transport limit.",
      next_action: "Send a smaller request within the service's published limits." },
    effect_commitment: "not_asserted", automatic_retry: false }), 413,
    { "content-type": "application/json", "cache-control": "no-store" });
}

function textResponse(body, status, headers) {
  return new Response(body, { status, headers });
}

// The static assets binding takes an absolute address but serves by path only, so the request's own origin is used.
async function loadManifest(env, origin) {
  const now = Date.now();
  if (held && held.exportId === env.EXPORT_ID && now - held.at < MANIFEST_TTL_MS) return held.manifest;
  let manifest = null;
  if (env.ASSETS) {
    const response = await env.ASSETS.fetch(new Request(new URL("/__edge/manifest.json", origin)));
    if (response.ok) manifest = await response.json();
  } else if (env.SITE) {
    manifest = await env.SITE.get(`${env.EXPORT_ID}/manifest`, { type: "json", cacheTtl: 300 });
  }
  if (!manifest || manifest.record_type !== "site_edge_manifest/v1" || manifest.export_id !== env.EXPORT_ID) return null;
  held = { manifest, exportId: env.EXPORT_ID, at: now };
  return manifest;
}

async function fileBytes(env, digest, origin) {
  if (env.ASSETS) {
    const response = await env.ASSETS.fetch(new Request(new URL(`/__edge/files/${digest}`, origin)));
    return response.ok ? new Uint8Array(await response.arrayBuffer()) : null;
  }
  const buffer = await env.SITE.get(`${env.EXPORT_ID}/f/${digest}`, { type: "arrayBuffer", cacheTtl: 86400 });
  return buffer ? new Uint8Array(buffer) : null;
}

const ENCODER = new TextEncoder();
const DECODER = new TextDecoder();

/** web_pages.with_page_head writes the root meta tag last, just before the head closes; so does the edge. */
export function withRootMeta(bytes, address) {
  const text = DECODER.decode(bytes);
  const matches = text.match(/<\/head\s*>/gi) || [];
  if (matches.length !== 1) throw new Error("a page with a head has exactly one closing head tag");
  const index = text.search(/<\/head\s*>/i);
  return ENCODER.encode(`${text.slice(0, index)}  <meta name="baltor-root-address" content="${address}">\n${text.slice(index)}`);
}

function hostOf(request, env) {
  const host = (new URL(request.url).hostname || "").toLowerCase().replace(/\.$/, "");
  let aliases = {};
  try { aliases = JSON.parse(env.HOST_ALIASES || "{}"); } catch { aliases = {}; }
  return { host: aliases[host] || host, aliased: host in aliases };
}

function markAliased(headers, aliased) {
  if (!aliased) return;
  const prior = headers.get("x-robots-tag") || "";
  if (!prior.split(",").some((part) => part.trim().toLowerCase() === "noindex")) {
    headers.set("x-robots-tag", prior ? `${prior}, noindex` : "noindex");
  }
}

async function staticAnswer(request, env, manifest, path, host, aliased) {
  if (request.method !== "GET" && request.method !== "HEAD") return null;
  if (manifest.origin_prefixes.some((prefix) => path.startsWith(prefix)) || manifest.origin_addresses.includes(path)) return null;
  const root = manifest.roots[host] ?? "/";
  const address = path === "/" ? root : path;
  const entry = manifest.files[address];
  if (!entry) return null;
  // Source-feed query parameters are refused by the origin, even with a
  // matching validator. Do not turn an invalid request into a cached feed.
  if (entry.class === "feed_source" && new URL(request.url).search) return null;
  let bytes = await fileBytes(env, entry.sha256, new URL(request.url).origin);
  if (!bytes) return null;
  if (entry.head && root !== "/") bytes = withRootMeta(bytes, root);
  const kind = manifest.classes[entry.class];
  const headers = new Headers(kind.headers);
  headers.set("content-type", entry.media_type);
  markAliased(headers, aliased);
  headers.set("x-baltor-edge", `static ${manifest.export_id.slice(0, 12)}`);
  if (kind.etag) {
    const etag = `"${entry.sha256}"`;
    headers.set("etag", etag);
    const wanted = request.headers.get("if-none-match") || "";
    if (wanted.split(",").some((part) => part.trim() === "*" || part.trim().replace(/^W\//, "") === etag)) {
      return textResponse(null, 304, headers);
    }
  }
  if (request.method === "HEAD") {
    headers.set("content-length", String(bytes.length));
    return textResponse(null, 200, headers);
  }
  return textResponse(bytes, 200, headers);
}

async function unavailable(request, env, manifest, aliased) {
  const stated = manifest.unavailable;
  const wantsPage = (request.headers.get("accept") || "").includes("text/html");
  if (wantsPage) {
    const entry = manifest.files[stated.page];
    const bytes = entry ? await fileBytes(env, entry.sha256, new URL(request.url).origin) : null;
    const headers = new Headers(manifest.classes.page.headers);
    headers.set("content-type", "text/html; charset=utf-8");
    headers.set("retry-after", String(stated.retry_after_seconds));
    headers.set("x-baltor-edge", "origin_unavailable");
    markAliased(headers, aliased);
    return textResponse(request.method === "HEAD" ? null : bytes, stated.status, headers);
  }
  const record = { record_type: "service_http_error/v1",
    error: { code: stated.code, message: stated.message, next_action: stated.next_action },
    effect_commitment: "not_asserted", automatic_retry: false,
    request_reference: crypto.randomUUID().replace(/-/g, "") };
  return textResponse(JSON.stringify(record), stated.status, { "content-type": "application/json",
    "cache-control": "no-store", "x-content-type-options": "nosniff", "retry-after": String(stated.retry_after_seconds),
    "x-baltor-edge": "origin_unavailable" });
}

const HOP_BY_HOP = ["connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer",
  "transfer-encoding", "upgrade", "host"];

async function toOrigin(request, env, manifest, aliased) {
  if ((aliased || env.ORIGIN_MODE !== "all") && request.method !== "GET" && request.method !== "HEAD") {
    const record = { record_type: "service_http_error/v1",
      error: { code: "edge_prototype_read_only", message: "This edge prototype passes only reads to the origin.",
               next_action: "Use the service's own address for this request." },
      effect_commitment: "not_asserted", automatic_retry: false };
    return textResponse(JSON.stringify(record), 403, { "content-type": "application/json", "cache-control": "no-store" });
  }
  const url = new URL(request.url);
  // Assign only path and query, never resolve a user path as a network-path URL:
  // new URL("//other-host/path", ORIGIN) would leak credentials to that host.
  const target = new URL(env.ORIGIN);
  target.pathname = url.pathname;
  target.search = url.search;
  target.hash = "";
  const headers = new Headers(request.headers);
  for (const name of (headers.get("connection") || "").split(",")) {
    if (name.trim()) headers.delete(name.trim());
  }
  for (const name of HOP_BY_HOP) headers.delete(name);
  let response;
  try {
    const body = request.method === "GET" || request.method === "HEAD" ? undefined
      : await boundedBody(request, MAXIMUM_PROXY_BODY_BYTES);
    if (body === null) return oversizedBody();
    response = await fetch(new Request(target.toString(), { method: request.method, headers, body, redirect: "manual" }));
  } catch {
    return unavailable(request, env, manifest, aliased);
  }
  // A platform's own failure page, never the service's refusal record: the origin's proxy answering 502 to 504
  // while the machine restarts, or Cloudflare answering 520 to 530 when it cannot reach or resolve the origin.
  const fromService = (response.headers.get("content-type") || "").includes("application/json");
  const platformFailure = [502, 503, 504].includes(response.status) || (response.status >= 520 && response.status <= 530);
  if (platformFailure && !fromService) return unavailable(request, env, manifest, aliased);
  const answer = new Response(response.body, response);
  // Dynamic responses may contain accounts, scoped results, or OAuth state.
  answer.headers.set("cache-control", "no-store");
  answer.headers.set("x-baltor-edge", "origin");
  markAliased(answer.headers, aliased);
  return answer;
}

async function sha256Hex(bytes) {
  const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
  return [...digest].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function base64ToBytes(text) {
  const normal = text.replace(/-/g, "+").replace(/_/g, "/");
  const binary = atob(normal + "=".repeat((4 - (normal.length % 4)) % 4));
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

async function signedByAdmin(request, env, body) {
  const parts = (request.headers.get("authorization") || "").split(" ");
  if (parts.length !== 5 || parts[0] !== "Baltor-Signature" || parts[1] !== "v1") return false;
  const [, , keyId, stamp, signature] = parts;
  let keys = [];
  try { keys = JSON.parse(env.LOADER_KEYS || "[]"); } catch { return false; }
  const key = keys.find((entry) => entry && entry.id === keyId && (entry.scopes || []).includes("admin"));
  if (!key || !/^[0-9]{1,12}$/.test(stamp) || Math.abs(Date.now() / 1000 - Number(stamp)) > 300) return false;
  const url = new URL(request.url);
  const message = ENCODER.encode(["baltor-edge-search/v1", request.method.toUpperCase(), url.pathname + url.search,
    stamp, await sha256Hex(body)].join("\n"));
  try {
    const publicKey = await crypto.subtle.importKey("raw", base64ToBytes(key.public_key), { name: "Ed25519" }, false, ["verify"]);
    return await crypto.subtle.verify({ name: "Ed25519" }, publicKey, base64ToBytes(signature), message);
  } catch { return false; }
}

/** Write one export into SITE: "BALTORS1", a JSON header naming each file's key, size and digest, then the bytes. */
async function loadFiles(request, env) {
  const body = await boundedBody(request, MAXIMUM_LOADER_BODY_BYTES);
  if (body === null) return oversizedBody();
  if (!(await signedByAdmin(request, env, body))) return textResponse("unauthorized", 401, { "content-type": "text/plain" });
  if (DECODER.decode(body.slice(0, 8)) !== "BALTORS1" || body.length < 12) return textResponse("invalid", 400, {});
  const length = new DataView(body.buffer, body.byteOffset + 8, 4).getUint32(0, true);
  let header;
  try { header = JSON.parse(DECODER.decode(body.slice(12, 12 + length))); } catch { return textResponse("invalid", 400, {}); }
  let offset = 12 + length;
  const checked = [];
  for (const file of header.files || []) {
    const bytes = body.slice(offset, offset + file.bytes);
    offset += file.bytes;
    const isManifest = file.key === `${header.export_id}/manifest`;
    if (bytes.length !== file.bytes || (!isManifest && file.key !== `${header.export_id}/f/${await sha256Hex(bytes)}`)) {
      return textResponse("a file differs from its digest", 400, {});
    }
    if (isManifest && JSON.parse(DECODER.decode(bytes)).export_id !== header.export_id) return textResponse("invalid", 400, {});
    checked.push([file.key, bytes]);
  }
  if (offset !== body.length) return textResponse("invalid", 400, {});
  for (const [key, bytes] of checked) await env.SITE.put(key, bytes);
  return textResponse(JSON.stringify({ record_type: "site_edge_load/v1", written: checked.length }), 200,
    { "content-type": "application/json" });
}

export async function handle(request, env) {
  const url = new URL(request.url);
  if (url.pathname === "/__edge/admin/files") {
    if (!env.LOADER_KEYS || !env.SITE || request.method !== "POST") return textResponse("not found", 404, {});
    return loadFiles(request, env);
  }
  const { host, aliased } = hostOf(request, env);
  const manifest = await loadManifest(env, url.origin);
  if (url.pathname === "/__edge/status" && request.method === "GET") {
    return textResponse(JSON.stringify({ record_type: "site_edge_status/v1", export_id: env.EXPORT_ID,
      manifest_loaded: Boolean(manifest), files: manifest ? Object.keys(manifest.files).length : 0,
      origin_mode: env.ORIGIN_MODE || "read_only" }), 200, { "content-type": "application/json", "cache-control": "no-store" });
  }
  if (!manifest) return toOrigin(request, env, { unavailable: { page: "", code: "service_unavailable", status: 503,
    message: "The website could not be loaded.", next_action: "Try again shortly.", retry_after_seconds: 30 },
    files: {}, classes: { page: { headers: {} } } }, aliased);
  const answer = await staticAnswer(request, env, manifest, url.pathname, host, aliased);
  return answer || toOrigin(request, env, manifest, aliased);
}

export default {
  async fetch(request, env) {
    return handle(request, env);
  },
};
