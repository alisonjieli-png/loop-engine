/* Screenshots of the Baltor app's view for the OpenAI directory, from real tool results.

   node tools/capture_chatgpt_app_screens.mjs CASES.json OUTPUT_DIR [--check]

   CASES.json is written by tools/check_chatgpt_app_live.py: the view's HTML exactly as the service's
   resources/read returned it (or the packaged file, which the record names), and one case per starter prompt with
   the tool's input and its structuredContent. A small host page plays the MCP Apps host side of the 2026-01-26
   bridge (ui/initialize, tool-input, tool-result, size-changed) around the unmodified view in a sandboxed iframe,
   shows the starter prompt above it as the conversation would, and saves one PNG per case, exactly 706 pixels wide
   and between 400 and 860 pixels tall (OpenAI submission rules). Each case is also opened at a phone width of 390
   pixels, where the view must not scroll sideways. Nothing is fetched: the view declares no outside domain, and the
   page refuses every network request. With --check, no file is written and only the measurements are reported. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {mkdirSync, readFileSync, writeFileSync} from "node:fs";
import {resolve} from "node:path";

const [casesPath, outputDir] = process.argv.slice(2);
const checkOnly = process.argv.includes("--check");
if (!casesPath || !outputDir) throw new Error("Use CASES.json OUTPUT_DIR [--check].");
const input = JSON.parse(readFileSync(casesPath, "utf8"));
if (input.record_type !== "chatgpt_app_screen_cases/v1" || typeof input.view_html !== "string" || !Array.isArray(input.cases))
  throw new Error("The cases file is not chatgpt_app_screen_cases/v1.");
const WIDTH = 706, MIN_HEIGHT = 400, MAX_HEIGHT = 860;

const hostPage = (prompt, theme) => `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;background:${theme === "dark" ? "#212121" : "#ffffff"};font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
.wrap{padding:16px 16px 20px;display:flex;flex-direction:column;gap:12px}
.you{align-self:flex-end;max-width:80%;background:${theme === "dark" ? "#303030" : "#f1f1f1"};color:${theme === "dark" ? "#f3f4f6" : "#16181d"};border-radius:18px;padding:10px 14px;font-size:15px;line-height:1.4}
.app{display:flex;align-items:center;gap:8px;font-size:13px;color:${theme === "dark" ? "#c4c8cf" : "#4b5563"}}
.app img{width:20px;height:20px;border-radius:5px}
iframe{border:1px solid ${theme === "dark" ? "#3c3f45" : "#dfe2e7"};border-radius:14px;width:100%;height:120px;display:block;background:transparent}
</style></head><body><div class="wrap"><div class="you" id="you"></div><div class="app"><img id="mark" alt="">Baltor</div>
<iframe id="view" sandbox="allow-scripts" title="Baltor view"></iframe></div></body></html>`;

const browser = await chromium.launch({executablePath: "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
const results = [];
try {
  for (const [index, item] of input.cases.entries()) {
    for (const [width, theme, label] of [[WIDTH, "light", "desktop"], [390, "light", "phone"]]) {
      const context = await browser.newContext({viewport: {width, height: 900}, deviceScaleFactor: 1, colorScheme: theme});
      await context.route("**/*", route => route.request().url().startsWith("data:") ? route.continue() : route.abort());
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", error => errors.push(String(error)));
      await page.setContent(hostPage(item.prompt, theme));
      const sent = await page.evaluate(async ({html, prompt, mark, toolInput, toolResult, theme, followUp}) => {
        document.getElementById("you").textContent = prompt;
        document.getElementById("mark").src = mark;
        const frame = document.getElementById("view");
        const log = [];
        window.__calls = [];
        let resolveDone;
        const done = new Promise(resolve => { resolveDone = resolve; });
        window.addEventListener("message", event => {
          if (event.source !== frame.contentWindow) return;
          const message = event.data || {};
          log.push(message.method || "response");
          if (message.method === "ui/initialize") {
            frame.contentWindow.postMessage({jsonrpc: "2.0", id: message.id, result: {protocolVersion: "2026-01-26",
              hostInfo: {name: "baltor-screen-host", version: "1.0.0"}, hostCapabilities: {serverTools: {}, openLinks: {}},
              hostContext: {theme, displayMode: "inline", availableDisplayModes: ["inline"],
                            containerDimensions: {width: frame.clientWidth, maxHeight: 2000}, platform: "web", locale: "en-US"}}}, "*");
          } else if (message.method === "ui/notifications/initialized") {
            frame.contentWindow.postMessage({jsonrpc: "2.0", method: "ui/notifications/tool-input", params: {arguments: toolInput}}, "*");
            frame.contentWindow.postMessage({jsonrpc: "2.0", method: "ui/notifications/tool-result",
              params: {content: [{type: "text", text: JSON.stringify(toolResult)}], structuredContent: toolResult, isError: false}}, "*");
          } else if (message.method === "tools/call") {
            window.__calls.push(message.params);
            frame.contentWindow.postMessage(followUp ? {jsonrpc: "2.0", id: message.id, result: {content: [{type: "text",
              text: JSON.stringify(followUp)}], structuredContent: followUp, isError: false}}
              : {jsonrpc: "2.0", id: message.id, error: {code: -32601, message: "No follow-up answer in this case"}}, "*");
          } else if (message.method === "ui/notifications/size-changed" && message.params && message.params.height > 40) {
            frame.style.height = Math.ceil(message.params.height) + "px";
            resolveDone(message.params);
          }
        });
        frame.srcdoc = html;
        const size = await Promise.race([done, new Promise(resolve => setTimeout(() => resolve(null), 8000))]);
        return {log, size};
      }, {html: input.view_html, prompt: item.prompt, mark: input.mark_data_url || "", toolInput: item.tool_input,
          toolResult: item.structured_content, theme, followUp: item.follow_up || null});
      await page.waitForTimeout(400);
      const measured = await page.evaluate(() => ({height: Math.ceil(document.querySelector(".wrap").getBoundingClientRect().bottom),
        frameHeight: document.getElementById("view").getBoundingClientRect().height}));
      const viewOverflow = await page.frames()[1]?.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1).catch(() => null);
      const row = {case: index + 1, label, width, theme, prompt: item.prompt, tool: item.tool, messages: sent.log,
                   reported_size: sent.size, page_height: measured.height, view_scrolls_sideways: viewOverflow, errors};
      if (label === "desktop" && item.follow_up) {
        /* The view's own action: "Show files" on the first card asks the host for get_package over the bridge, and the
           view must show that package. Done after the screenshot below is taken, on a copy of the page state. */
        row.follow_up_pending = true;
      }
      if (label === "desktop") {
        const height = Math.min(MAX_HEIGHT, Math.max(MIN_HEIGHT, measured.height));
        await page.setViewportSize({width: WIDTH, height});
        row.screenshot = {width: WIDTH, height, clipped: measured.height > MAX_HEIGHT};
        if (!checkOnly) {
          mkdirSync(outputDir, {recursive: true});
          const path = resolve(outputDir, `screenshot-${index + 1}.png`);
          await page.screenshot({path, clip: {x: 0, y: 0, width: WIDTH, height}});
          row.screenshot.path = path;
        }
      }
      if (row.follow_up_pending) {
        delete row.follow_up_pending;
        const view = page.frameLocator("#view");
        await view.getByRole("button", {name: /^Show the files of /}).first().click();
        const shown = await view.getByText("Files and SHA-256 digests").waitFor({timeout: 8000}).then(() => true, () => false);
        const calls = await page.evaluate(() => window.__calls);
        const first = (item.structured_content.results || [])[0] || {};
        row.follow_up = {calls: calls.length, package_shown: shown,
          asked_for_the_first_result: calls.length === 1 && calls[0].name === "get_package"
            && calls[0].arguments?.identity === first.identity && calls[0].arguments?.expected_digest === first.expected_digest};
      }
      results.push(row);
      await context.close();
    }
  }
} finally {
  await browser.close();
}
const failures = results.filter(row => row.errors.length || !row.messages.includes("ui/initialize")
  || !row.messages.includes("ui/notifications/size-changed") || row.view_scrolls_sideways === true
  || (row.follow_up && !(row.follow_up.package_shown && row.follow_up.asked_for_the_first_result)));
const report = {record_type: "chatgpt_app_screens/v1", view_source: input.view_source, cases: results,
                all_passed: failures.length === 0};
writeFileSync(1, JSON.stringify(report) + "\n");
if (failures.length) process.exitCode = 1;
