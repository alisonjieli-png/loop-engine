// Real OpenCode protocol exercise with a local scripted model, not model-quality evidence.
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import http from "node:http";
import { spawn } from "node:child_process";

const manifest = JSON.parse(readFileSync("/workspace/instance-plan.json", "utf8"));
const digest = (value) => createHash("sha256").update(value).digest("hex");
const requests = [];
let taskTurns = 0;
const server = http.createServer(async (request, response) => {
  const chunks = [];
  for await (const chunk of request) chunks.push(chunk);
  const raw = Buffer.concat(chunks);
  let body;
  try { body = JSON.parse(raw.toString("utf8")); }
  catch { response.writeHead(400).end(); return; }
  const tools = (body.tools ?? []).map((item) => item.function?.name ?? "");
  const messages = body.messages ?? [];
  const packet = JSON.stringify(messages);
  const observation = { record_type: "opencode_fixture_model_request/v1",
    request_number: requests.length + 1, packet_digest: digest(raw), tools,
    model: body.model, streamed: body.stream === true,
    selected_skill_seen: packet.includes("SELECTED_SKILL_BODY_73"),
    core_skill_seen: packet.includes("CORE_SKILL_BODY_41"),
    core_context_seen: packet.includes("CORE_CONTEXT_IMMUTABLE_17"),
    step_context_seen: packet.includes("STEP_CONTEXT_BODY_29") };
  requests.push(observation);
  process.stderr.write(JSON.stringify(observation) + "\n");
  if (requests.length > 8 || body.model !== "fixture-model") {
    response.writeHead(429, { "content-type": "application/json" });
    response.end(JSON.stringify({ error: { message: "Fixture protocol allowance exhausted." } }));
    return;
  }
  const turn = tools.length ? ++taskTurns : 0;
  let delta, reason;
  if (turn >= 1 && turn <= 3) {
    const tool = turn === 3 ? "read" : "skill";
    const args = turn === 1 ? { name: "core-check" }
      : turn === 2 ? { name: "step-check" } : { filePath: "/workspace/context/step.txt" };
    delta = { role: "assistant", content: null, tool_calls: [{ index: 0,
      id: `fixture-tool-${turn}`, type: "function", function: { name: tool, arguments: JSON.stringify(args) } }] };
    reason = "tool_calls";
  } else {
    delta = { role: "assistant", content: turn === 0 ? "Fixture task"
      : JSON.stringify({ status: "candidate", answer: 5, core_digest: manifest.core_digest }) };
    reason = "stop";
  }
  const base = { id: `fixture-completion-${requests.length}`, object: "chat.completion.chunk",
    created: 1, model: "fixture-model" };
  if (body.stream) {
    response.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-cache" });
    response.write(`data: ${JSON.stringify({ ...base, choices: [{ index: 0, delta, finish_reason: null }] })}\n\n`);
    response.write(`data: ${JSON.stringify({ ...base, choices: [{ index: 0, delta: {}, finish_reason: reason }] })}\n\n`);
    response.end("data: [DONE]\n\n");
  } else {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ ...base, object: "chat.completion",
      choices: [{ index: 0, message: delta, finish_reason: reason }] }));
  }
});
await new Promise((resolve) => server.listen(18871, "127.0.0.1", resolve));
const config = {
  $schema: "https://opencode.ai/config.json", autoupdate: false, share: "disabled",
  model: "loop_fixture/fixture-model", small_model: "loop_fixture/fixture-model",
  disabled_providers: ["opencode"], enabled_providers: ["loop_fixture"],
  permission: manifest.permissions, instructions: ["/workspace/context/core.txt"],
  provider: { loop_fixture: { npm: "@ai-sdk/openai-compatible", name: "Local protocol fixture",
    options: { baseURL: "http://127.0.0.1:18871/v1", apiKey: "not-a-real-credential" },
    models: { "fixture-model": { name: "Scripted fixture", tool_call: true,
      limit: { context: 65536, output: 8192 } } } } },
  agent: { "loop-step": { mode: "primary", prompt: "Perform the exact bounded fixture task.",
    permission: manifest.permissions }, title: { disable: true }, summary: { disable: true },
    compaction: { disable: true } },
  compaction: { auto: false, prune: false }, lsp: false, formatter: false,
};
const harnessProcess = spawn("/usr/local/bin/opencode", ["run", "--format", "json", "--agent", "loop-step",
  "--model", "loop_fixture/fixture-model", "--dir", "/workspace"], {
  cwd: "/workspace", stdio: ["pipe", "pipe", "pipe"],
  env: { ...process.env, XDG_CONFIG_HOME: "/tmp/config", XDG_CACHE_HOME: "/tmp/cache",
    XDG_DATA_HOME: "/tmp/data", XDG_STATE_HOME: "/tmp/state",
    OPENCODE_DISABLE_AUTOUPDATE: "true", OPENCODE_DISABLE_MODELS_FETCH: "true",
    OPENCODE_DISABLE_DEFAULT_PLUGINS: "true", OPENCODE_DISABLE_LSP_DOWNLOAD: "true",
    OPENCODE_DISABLE_SHARE: "true", OPENCODE_DISABLE_EXTERNAL_SKILLS: "true",
    OPENCODE_DISABLE_CLAUDE_CODE: "true", OPENCODE_CONFIG_CONTENT: JSON.stringify(config) },
});
harnessProcess.stdout.pipe(process.stdout);
harnessProcess.stderr.pipe(process.stderr);
harnessProcess.stdin.end("Load core-check and step-check skills, read context/step.txt, and return its sum as candidate JSON.");
const timer = setTimeout(() => {
  harnessProcess.kill("SIGTERM");
  setTimeout(() => harnessProcess.kill("SIGKILL"), 2000).unref();
}, 90000);
harnessProcess.on("error", (error) => { process.stderr.write(error.name + "\n"); });
harnessProcess.on("exit", (code, signal) => {
  clearTimeout(timer);
  server.closeAllConnections();
  server.close();
  process.stderr.write(JSON.stringify({ record_type: "opencode_fixture_execution/v1",
    exit_code: code, signal, requests: requests.length, task_turns: taskTurns,
    real_provider_calls: 0, usage_is_fixture: true,
    core_skill_seen: requests.some((item) => item.core_skill_seen),
    core_context_seen: requests.every((item) => item.core_context_seen),
    selected_skill_seen: requests.some((item) => item.selected_skill_seen),
    step_context_seen: requests.some((item) => item.step_context_seen) }) + "\n");
  process.exit(code ?? 1);
});
