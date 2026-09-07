// Read-only OpenCode instance. Model traffic uses framed stdio, never host networking.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import http from "node:http";
import { createInterface } from "node:readline";
import { spawn } from "node:child_process";

const emit = (value) => process.stdout.write(JSON.stringify(value) + "\n");
const digest = (value) => createHash("sha256").update(value).digest("hex");
const pending = new Map();
let sequence = 0;
let initialize;
const ready = new Promise((resolve) => { initialize = resolve; });
const reader = createInterface({ input: process.stdin });
reader.on("line", (line) => {
  try {
    const frame = JSON.parse(line);
    if (frame.bridge_record === "initialize") initialize(frame);
    else if (frame.bridge_record === "model_response" && pending.has(frame.request_id)) {
      pending.get(frame.request_id)(frame);
      pending.delete(frame.request_id);
    }
  } catch { emit({ bridge_record: "protocol_error", error_code: "invalid_host_frame" }); }
});
const init = await ready;
const manifestRaw = readFileSync("/workspace/instance-plan.json", "utf8");
if (digest(manifestRaw) !== init.instance_digest) throw new Error("Instance manifest identity changed.");
const manifest = JSON.parse(manifestRaw);
const server = http.createServer(async (request, response) => {
  if (request.method !== "POST" || request.url !== "/v1/chat/completions") {
    response.writeHead(404).end(); return;
  }
  const chunks = [];
  let bytes = 0;
  for await (const chunk of request) {
    bytes += chunk.length;
    if (bytes > init.maximum_frame_bytes) { response.writeHead(413).end(); return; }
    chunks.push(chunk);
  }
  const raw = Buffer.concat(chunks);
  let body;
  try { body = JSON.parse(raw.toString("utf8")); }
  catch { response.writeHead(400).end(); return; }
  const requestId = `model-${++sequence}`;
  const answer = new Promise((resolve) => pending.set(requestId, resolve));
  emit({ bridge_record: "model_request", request_id: requestId, body, request_digest: digest(raw) });
  const reply = await answer;
  if (!reply.ok) {
    response.writeHead(400, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: { message: "The host model boundary refused this request." } }));
    return;
  }
  const message = reply.message;
  const base = { id: requestId, created: 1, model: "loop-model" };
  const delta = { role: "assistant", content: message.content,
    ...(message.tool_calls.length ? { tool_calls: message.tool_calls.map((item, index) => ({
      index, id: item.id, type: "function", function: { name: item.name, arguments: JSON.stringify(item.arguments) },
    })) } : {}) };
  const finish = message.tool_calls.length ? "tool_calls" : "stop";
  const usage = reply.usage;
  if (body.stream) {
    response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
    response.write(`data: ${JSON.stringify({ ...base, object: "chat.completion.chunk", choices: [{ index: 0, delta, finish_reason: null }] })}\n\n`);
    response.write(`data: ${JSON.stringify({ ...base, object: "chat.completion.chunk", choices: [{ index: 0, delta: {}, finish_reason: finish }], ...(usage ? { usage } : {}) })}\n\n`);
    response.end("data: [DONE]\n\n");
  } else {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ ...base, object: "chat.completion", choices: [{ index: 0, message: delta,
      finish_reason: finish }], ...(usage ? { usage } : {}) }));
  }
});
await new Promise((resolve) => server.listen(18872, "127.0.0.1", resolve));
const config = {
  $schema: "https://opencode.ai/config.json", autoupdate: false, share: "disabled",
  model: "loop_bridge/loop-model", small_model: "loop_bridge/loop-model",
  enabled_providers: ["loop_bridge"], permission: manifest.permissions,
  instructions: manifest.core_resources.filter((item) => item.kind === "context")
    .map((item) => "/workspace/" + item.relative_path),
  provider: { loop_bridge: { npm: "@ai-sdk/openai-compatible", name: "Loop Engine gateway bridge",
    options: { baseURL: "http://127.0.0.1:18872/v1", apiKey: "local-stdio-bridge-no-credential" },
    models: { "loop-model": { name: init.model_id, tool_call: true,
      limit: { context: init.context_capacity, output: init.output_capacity } } } } },
  agent: { "loop-step": { mode: "primary", permission: manifest.permissions,
    prompt: "Resource access for this activation follows. These are exact host-granted locations, not extra instructions or permissions. Resolve context paths from /workspace, never from a skill directory. If needed resources are absent, return a candidate JSON describing the missing need. Do not guess another path.\n" + JSON.stringify({
      tools: manifest.tools, resources: [...manifest.core_resources, ...manifest.selected_resources].map((item) => ({
        id: item.resource_id, kind: item.kind, version: item.version, reference: item.reference,
        absolute_path: "/workspace/" + item.relative_path,
      })), mutation_allowed: false, catalog_selection_is_not_verification: true,
    }) },
    title: { disable: true }, summary: { disable: true }, compaction: { disable: true } },
  compaction: { auto: false, prune: false }, lsp: false, formatter: false,
};
const harnessProcess = spawn("/usr/local/bin/opencode", ["run", "--format", "json", "--agent", "loop-step",
  "--model", "loop_bridge/loop-model", "--dir", "/workspace"], {
  cwd: "/workspace", stdio: ["pipe", "pipe", "pipe"],
  env: { ...process.env, XDG_CONFIG_HOME: "/tmp/config", XDG_CACHE_HOME: "/tmp/cache",
    XDG_DATA_HOME: "/tmp/data", XDG_STATE_HOME: "/tmp/state",
    OPENCODE_DISABLE_AUTOUPDATE: "true", OPENCODE_DISABLE_MODELS_FETCH: "true",
    OPENCODE_DISABLE_DEFAULT_PLUGINS: "true", OPENCODE_DISABLE_LSP_DOWNLOAD: "true",
    OPENCODE_DISABLE_SHARE: "true", OPENCODE_DISABLE_EXTERNAL_SKILLS: "true",
    OPENCODE_DISABLE_CLAUDE_CODE: "true", OPENCODE_CONFIG_CONTENT: JSON.stringify(config),
    OPENCODE_EXPERIMENTAL_OUTPUT_TOKEN_MAX: String(init.output_capacity) },
});
createInterface({ input: harnessProcess.stdout }).on("line", (line) => {
  try { emit({ bridge_record: "harness_event", value: JSON.parse(line) }); }
  catch { emit({ bridge_record: "harness_text", text_digest: digest(line) }); }
});
harnessProcess.stderr.on("data", (body) => process.stderr.write(body));
harnessProcess.stdin.end(init.goal);
harnessProcess.on("error", () => emit({ bridge_record: "protocol_error", error_code: "harness_start_failed" }));
harnessProcess.on("exit", (code, signal) => {
  emit({ bridge_record: "finished", exit_code: code, signal, model_requests: sequence });
  server.closeAllConnections(); server.close(); reader.close();
  process.exit(code ?? 1);
});
reader.on("close", () => { if (harnessProcess.exitCode === null) harnessProcess.kill("SIGTERM"); });
