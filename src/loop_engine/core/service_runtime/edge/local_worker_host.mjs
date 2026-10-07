// Runs one of the Baltor edge Workers on this machine for the conformance kits: D1 through Node's SQLite, KV
// through a folder of files, static assets through an export folder, the Worker's own fetch handler behind a
// loopback HTTP listener.
//
//   node local_worker_host.mjs --worker WORKER.js [--db INDEX.sqlite] [--kv FOLDER [--kv-binding VECTORS]]
//                              [--keys KEYS.json] [--assets EXPORT_FOLDER] [--vars VARS.json]
//
// It prints `LISTENING <port>` once it accepts requests and serves until it is stopped. It binds the loopback
// address only and writes only into the KV folder it was given; a Worker that fetches its origin reaches only the
// origin named in --vars. The request's Host header becomes the hostname the Worker sees, as at the edge.
// Rows-read accounting is D1's own and is reported here as zero.
import { createServer } from "node:http";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const args = Object.fromEntries(process.argv.slice(2).reduce((pairs, value, index, all) =>
  (index % 2 === 0 ? [...pairs, [value.replace(/^--/, ""), all[index + 1]]] : pairs), []));
if (!args.worker) { console.error("missing --worker"); process.exit(2); }

const env = args.vars ? JSON.parse(readFileSync(args.vars, "utf-8")) : {};

if (args.db) {
  const { DatabaseSync } = await import("node:sqlite");
  const database = new DatabaseSync(args.db, { readOnly: true });
  class Statement {
    constructor(sql) { this.sql = sql; this.params = []; }
    bind(...params) { this.params = params; return this; }
    async all() {
      const rows = database.prepare(this.sql).all(...this.params).map((row) => ({ ...row }));
      return { results: rows, success: true, meta: { rows_read: 0, rows_written: 0, duration: 0 } };
    }
    async first() {
      const row = database.prepare(this.sql).get(...this.params);
      return row ? { ...row } : null;
    }
  }
  env.DB = { prepare: (sql) => new Statement(sql) };
}

if (args.kv) {
  const keyFile = (key) => join(args.kv, key.replace(/[^0-9A-Za-z]/g, "_") + ".bin");
  env[args["kv-binding"] || "VECTORS"] = {
    async get(key, options) {
      const path = keyFile(key);
      if (!existsSync(path)) return null;
      const bytes = readFileSync(path);
      const type = options?.type;
      if (type === "arrayBuffer") return bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
      if (type === "json") return JSON.parse(bytes.toString("utf-8"));
      return bytes.toString("utf-8");
    },
    async put(key, value) {
      const data = typeof value === "string" ? Buffer.from(value, "utf-8")
        : Buffer.from(value instanceof ArrayBuffer ? new Uint8Array(value) : value);
      writeFileSync(keyFile(key), data);
    },
  };
}

if (args.keys) env.KEYS = readFileSync(args.keys, "utf-8");

if (args.assets) {
  // The static assets binding: __edge/manifest.json and __edge/files/<sha256> of one export folder.
  env.ASSETS = {
    async fetch(request) {
      const path = new URL(request.url).pathname;
      const local = path === "/__edge/manifest.json" ? join(args.assets, "manifest.json")
        : /^\/__edge\/files\/[0-9a-f]{64}$/.test(path) ? join(args.assets, "files", path.split("/").pop()) : null;
      if (!local || !existsSync(local)) return new Response("not found", { status: 404 });
      return new Response(readFileSync(local), { status: 200 });
    },
  };
}

const worker = await import(pathToFileURL(args.worker).href);

const server = createServer(async (incoming, outgoing) => {
  try {
    const chunks = [];
    for await (const chunk of incoming) chunks.push(chunk);
    const body = Buffer.concat(chunks);
    const headers = new Headers();
    for (const [name, value] of Object.entries(incoming.headers)) {
      if (Array.isArray(value)) for (const item of value) headers.append(name, item);
      else if (value !== undefined) headers.set(name, value);
    }
    const host = (incoming.headers.host || "localhost").split(":")[0];
    const request = new Request(`http://${host}${incoming.url}`, {
      method: incoming.method, headers,
      body: incoming.method === "GET" || incoming.method === "HEAD" ? undefined : body,
    });
    const response = await worker.default.fetch(request, env);
    const payload = Buffer.from(await response.arrayBuffer());
    outgoing.writeHead(response.status, Object.fromEntries(response.headers.entries()));
    outgoing.end(payload);
  } catch (error) {
    outgoing.writeHead(500, { "content-type": "text/plain" });
    outgoing.end("local host failure");
  }
});

server.listen(0, "127.0.0.1", () => {
  process.stdout.write(`LISTENING ${server.address().port}\n`);
});
