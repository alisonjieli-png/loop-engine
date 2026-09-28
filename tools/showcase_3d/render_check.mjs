/* Render a folder's index.html in headless Chrome with no network except a local server.
   Usage: node render_check.mjs FOLDER SCREENSHOT.png REPORT.json TIMEOUT_MS PLAYWRIGHT_CORE_INDEX CHROME_BINARY */
import {createServer} from "node:http";
import {readFile, writeFile} from "node:fs/promises";
import {resolve, extname, normalize} from "node:path";
import {pathToFileURL} from "node:url";

const [folder, shot, reportPath, timeoutText, playwrightIndex, chromeBinary] = process.argv.slice(2);
const {chromium} = await import(pathToFileURL(playwrightIndex).href);
const root = resolve(folder), timeout = Number(timeoutText || 30000);
const types = {".html": "text/html", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css",
  ".json": "application/json", ".png": "image/png", ".jpg": "image/jpeg", ".glb": "model/gltf-binary", ".gltf": "model/gltf+json"};
const server = createServer(async (request, response) => {
  const path = decodeURIComponent(request.url.split("?")[0].split("#")[0]);
  if (path === "/favicon.ico") { response.writeHead(204); return response.end(); }
  const file = normalize(resolve(root, "." + (path.endsWith("/") ? path + "index.html" : path)));
  if (!file.startsWith(root)) { response.writeHead(403); return response.end(); }
  try { const body = await readFile(file); response.writeHead(200, {"Content-Type": types[extname(file)] || "application/octet-stream"}); response.end(body); }
  catch { response.writeHead(404); response.end(); }
});
await new Promise(done => server.listen(0, "127.0.0.1", done));
const origin = `http://127.0.0.1:${server.address().port}`;
/* checker_errors are failures of this check itself (for example a screenshot the browser could not capture under
   load); they are kept apart from the page's own errors so that a checker fault is never graded as the page's. */
const report = {rendered: false, console_errors: [], page_errors: [], checker_errors: [], blocked_requests: [],
  canvas_fraction: 0, screenshot_attempts: 0};
const browser = await chromium.launch({executablePath: chromeBinary, headless: true,
  args: ["--no-sandbox", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]});
try {
  const context = await browser.newContext({viewport: {width: 960, height: 640}});
  await context.route("**/*", route => {
    const url = route.request().url();
    if (url.startsWith(origin)) return route.continue();
    report.blocked_requests.push(url.slice(0, 160)); return route.abort();
  });
  const page = await context.newPage();
  page.on("console", message => { if (message.type() === "error") report.console_errors.push(message.text().slice(0, 200)); });
  page.on("pageerror", error => report.page_errors.push(String(error).slice(0, 200)));
  await page.goto(origin + "/index.html", {waitUntil: "load", timeout: 30000});
  report.rendered = await page.waitForFunction(() => window.__rendered === true, null, {timeout}).then(() => true).catch(() => false);
  await page.waitForTimeout(1500);
  report.canvas_fraction = await page.evaluate(() => {
    const canvas = document.querySelector("canvas"); if (!canvas) return 0;
    const box = canvas.getBoundingClientRect();
    return Math.round(1000 * Math.max(0, box.width) * Math.max(0, box.height) / (innerWidth * innerHeight)) / 1000;
  });
  for (let attempt = 1; attempt <= 3; attempt++) {
    report.screenshot_attempts = attempt;
    try { await page.screenshot({path: shot}); break; }
    catch (error) {
      if (attempt === 3) report.checker_errors.push("screenshot: " + String(error).slice(0, 200));
      else await page.waitForTimeout(3000);
    }
  }
} catch (error) { report.checker_errors.push("render: " + String(error).slice(0, 200)); }
await browser.close(); server.close();
await writeFile(reportPath, JSON.stringify(report, null, 1));
