/* Loopback-only browser qualification of public random previews. It creates no
   account, source download, provider request, media or publication.
   Usage: PYTHON=/qualified/python node tools/check_gallery_random.mjs NEW_DIRECTORY */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync, mkdirSync, readFileSync, writeFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {resolve} from "node:path";
import {setRequestedAppearance, readRequestedAppearance, appearanceProblems} from "./browser_appearance_checks.mjs";

const root = resolve(new URL("..", import.meta.url).pathname);
const output = resolve(process.argv[2] || "");
if (!process.argv[2] || existsSync(output)) throw Error("A new report directory is required.");
mkdirSync(output, {mode: 0o700});
const checks = [], errors = [], blocked = [];
const check = (name, passed, detail = {}) => checks.push({name, passed: passed === true, detail});
const sourcePaths = ["gallery_records.py", "gallery_media.py", "gallery_random.py", "gallery_page.py",
  "web_assets/gallery-random.js", "web_assets/gallery-random.css", "web_assets/gallery-media/media.json"];
const sourceDigests = Object.fromEntries(sourcePaths.map(path => [path, createHash("sha256")
  .update(readFileSync(resolve(root, "src/loop_engine/core/service_runtime", path))).digest("hex")]));
const SERVICE = `from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json, sys
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with ExitStack() as stack:
    folder = Path(stack.enter_context(TemporaryDirectory(prefix="gallery-random-check-")))
    (folder / "intelligence").mkdir()
    held = prepared(folder / "intelligence")
    factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config, access_administration=held.administration)
    base, _ = stack.enter_context(running_http(held, application_factory=factory, display_name="Baltor"))
    print(json.dumps({"base": base}), flush=True)
    sys.stdin.readline()
`;
const measured = () => {
  const shown = node => node && !node.hidden && node.getBoundingClientRect().width > 0 && node.getBoundingClientRect().height > 0;
  const main = document.querySelector("main");
  const heading = [...main.querySelectorAll("h1")].filter(shown);
  const action = document.querySelector("[data-show-another]");
  const rect = action?.getBoundingClientRect();
  return {width: innerWidth, height: innerHeight, overflow: document.documentElement.scrollWidth - innerWidth,
    headings: heading.length, headingTop: heading[0]?.getBoundingClientRect().top,
    headerBottom: document.querySelector("header")?.getBoundingClientRect().bottom || 0,
    action: shown(action) ? {width: rect.width, height: rect.height, bottom: rect.bottom} : null,
    title: document.querySelector("[data-asset-title]")?.textContent,
    source: document.querySelector("[data-asset-source]")?.getAttribute("href"),
    asset: new URLSearchParams(location.search).get("asset"),
    loaded: document.querySelector("[data-asset-media] img")?.naturalWidth > 0,
    cardShown: shown(document.querySelector("[data-asset-card]")),
    unavailable: shown(document.querySelector("[data-asset-unavailable]")),
    licence: document.querySelector("[data-asset-licence]")?.textContent,
    sourceLicence: document.querySelector("[data-asset-source-licence]")?.textContent};
};
const layoutOkay = state => state.overflow <= 1 && state.headings === 1 && state.headingTop >= state.headerBottom - 1;
let service, browser;
try {
  service = spawn(process.env.PYTHON || "python3", ["-c", SERVICE], {
    cwd: root, env: {...process.env, PYTHONPATH: resolve(root, "src")}, stdio: ["pipe", "pipe", "pipe"]});
  let stderr = "";
  service.stderr.on("data", data => { stderr += data; });
  const base = await new Promise((done, fail) => {
    const lines = createInterface({input: service.stdout});
    const timer = setTimeout(() => fail(Error("Fixture timeout: " + stderr)), 30000);
    lines.once("line", line => { clearTimeout(timer); lines.close(); done(JSON.parse(line).base); });
    service.once("exit", code => { clearTimeout(timer); fail(Error("Fixture exited " + code + ": " + stderr)); });
  });
  browser = await chromium.launch({executablePath: process.env.LOOP_WEBSITE_BROWSER || "/opt/google/chrome/chrome",
    headless: true, args: ["--no-sandbox"]});
  const contextFor = async options => {
    const context = await browser.newContext({reducedMotion: "reduce", ...options});
    await context.route("**/*", route => {
      const request = route.request();
      const allowed = new URL(request.url()).origin === base && ["GET", "HEAD"].includes(request.method());
      if (!allowed) blocked.push({method: request.method(), url: request.url()});
      return allowed ? route.continue() : route.abort();
    });
    return context;
  };
  for (const viewport of [{width:1440,height:900}, {width:1024,height:768}, {width:860,height:900},
                           {width:390,height:844}, {width:844,height:390}]) {
    for (const theme of ["light", "dark"]) {
      const context = await contextFor({viewport, colorScheme: theme});
      await setRequestedAppearance(context, base, theme);
      const page = await context.newPage();
      page.on("pageerror", error => errors.push(String(error)));
      const response = await page.goto(base + "/random/image");
      await page.waitForFunction(() => new URLSearchParams(location.search).has("asset"));
      await page.locator("[data-asset-media] img").evaluate(node => node.decode());
      await page.evaluate(() => document.fonts.ready);
      const state = await page.evaluate(measured), where = {...viewport, theme};
      check("page and selected public image load", response.status() === 200 && state.loaded, where);
      check("responsive heading and bounds", layoutOkay(state), {...where, state});
      check("known-wrong hidden heading and horizontal overflow are rejected",
        !layoutOkay({...state, headings:0}) && !layoutOkay({...state, overflow:20}), where);
      check("action is a usable touch target", state.action?.width >= 44 && state.action?.height >= 44, where);
      if (viewport.height >= 700) check("selection action appears in first screen", state.action?.bottom <= state.height, where);
      check("source and preview licences stay distinct", state.licence === "Not separately recorded" && state.sourceLicence === "MIT", where);
      const appearance = await readRequestedAppearance(page);
      check("actual theme and sampled contrast", appearanceProblems(appearance, theme).length === 0, {where, appearance});
      const button = page.locator("[data-show-another]");
      await button.focus();
      await page.keyboard.press("Enter");
      await page.waitForFunction(previous => new URLSearchParams(location.search).get("asset") !== previous, state.asset);
      check("keyboard selection retains focus", await button.evaluate(node => document.activeElement === node), where);
      const second = await page.evaluate(measured);
      check("another avoids the previous identity", second.asset !== state.asset, where);
      const permalink = await page.locator("[data-asset-permalink]").getAttribute("href");
      await page.goto(base + permalink);
      await page.waitForFunction(id => document.querySelector("[data-asset-permalink]")?.getAttribute("href")?.includes(id), second.asset);
      const restored = await page.evaluate(measured);
      check("permanent link restores exact selection", restored.asset === second.asset && restored.title === second.title, where);
      const source = await context.request.get(base + restored.source);
      check("editable source links to existing gallery", source.status() === 200 && (await source.text()).includes("Get it in your harness"), where);
      if ([1440,390].includes(viewport.width)) await page.screenshot({path:resolve(output, `${viewport.width}-${theme}.png`), fullPage:true});
      await context.close();
    }
  }
  const context = await contextFor({viewport:{width:390,height:844}});
  const page = await context.newPage();
  page.on("pageerror", error => errors.push(String(error)));
  for (const kind of ["video", "music"]) {
    const response = await page.goto(base + "/random/" + kind);
    await page.waitForFunction(() => document.querySelector("[data-selection-status]").textContent.length > 0);
    check("empty kind is honest: " + kind, response.status() === 200 && await page.locator("[data-asset-unavailable]").isVisible()
      && await page.locator("[data-asset-media]").count() === 0 && !(await page.locator("[data-show-another]").isVisible()));
    check("empty kind mobile layout: " + kind, layoutOkay(await page.evaluate(measured)));
  }
  for (const query of ["?asset=retired-version", "?asset=one&asset=two"]) {
    await page.goto(base + "/random/image" + query);
    await page.waitForFunction(() => document.querySelector("[data-asset-card]").hidden);
    check("stale or ambiguous selection does not fall back", (await page.evaluate(measured)).unavailable, {query});
    await page.locator("[data-show-another]").click();
    check("unavailable selection has a working recovery action", (await page.evaluate(measured)).cardShown);
  }
  const first = new URL(page.url()).searchParams.get("asset");
  await page.locator("[data-show-another]").click();
  await page.goBack();
  check("browser back restores prior asset", new URL(page.url()).searchParams.get("asset") === first);
  const stable = await page.locator("[data-asset-permalink]").getAttribute("href");
  await page.route("**/assets/gallery/*.webp", route => route.abort());
  await page.goto(base + stable);
  await page.waitForFunction(() => document.querySelector("[data-selection-status]").textContent.startsWith("Preview unavailable."));
  check("failed media has an explicit state and no broken save action", !(await page.locator("[data-asset-download]").isVisible()));
  for (const path of ["/random/no-such-kind", "/random/image/private"]) {
    check("invalid route gives standard 404", (await page.goto(base + path)).status() === 404, {path});
  }
  const refused = await context.request.post(base + "/api/v1/download", {data:{record_type:"service_provisioning_request/v1", operation:"read", identity:"fixture"}});
  check("source download still requires existing authorization", [401,403].includes(refused.status()), {status:refused.status()});
  const head = await context.request.head(base + "/random");
  check("head route has no body", head.status() === 200 && (await head.body()).length === 0);
  await context.close();
  const plain = await contextFor({javaScriptEnabled:false, viewport:{width:390,height:844}});
  const plainPage = await plain.newPage();
  await plainPage.goto(base + "/random/image?asset=retired-version");
  check("no-script sample never impersonates an exact selection", await plainPage.locator("[data-sample-preview] img").isVisible()
    && (await plainPage.locator("[data-sample-preview]").innerText()).includes("not the selection in your address")
    && !(await plainPage.locator("[data-asset-card]").isVisible()) && !(await plainPage.locator("[data-show-another]").isVisible()));
  await plain.close();
  check("no browser script errors", errors.length === 0, {errors});
  check("no external or effectful request", blocked.length === 0, {blocked});
} catch (error) {
  errors.push(String(error));
  check("qualification completed", false, {error:String(error)});
} finally {
  if (browser) await browser.close();
  if (service) service.stdin.end("\n");
  const report = {record_type:"gallery_random_browser_check/v1", observed_at:new Date().toISOString(),
    sourceDigests, checks, errors, blocked, passed:checks.every(item => item.passed)};
  writeFileSync(resolve(output,"report.json"), JSON.stringify(report,null,2) + "\n", {flag:"wx"});
  console.log(JSON.stringify({passed:report.passed, checks:checks.length, failed:checks.filter(item => !item.passed), output}));
  process.exitCode = report.passed ? 0 : 1;
}
