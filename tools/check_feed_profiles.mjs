/* Real HTTP browser export checks. Fault controls affect only this browser's response. */
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync, readFileSync, writeFileSync} from "node:fs";
import {resolve} from "node:path";
const {chromium} = await import(process.env.BALTOR_PLAYWRIGHT_MODULE || "../showcase/node_modules/playwright-core/index.mjs");
const root = resolve(new URL("..", import.meta.url).pathname);
const [target, outputArgument] = process.argv.slice(2);
if (!target || !outputArgument) throw new Error("Use check_feed_profiles.mjs --local|HTTPS_ORIGIN NEW_REPORT.json");
const output = resolve(outputArgument);
if (!output.endsWith(".json") || existsSync(output)) throw new Error("Use a new JSON report path");
const checks = [], errors = [], requests = [];
const check = (name, passed) => checks.push({name, passed: Boolean(passed)});
let child, browser, origin;
try {
  if (target === "--local") {
    const program = `from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with TemporaryDirectory(prefix="feed-profile-browser-") as folder:
    case=Fixture(Path(folder))
    case.publish([case.line("private_fixture_body","PRIVATE BODY REMAINS PRIVATE")])
    fixture=type("Served",(),{"runtime":case.runtime,"provisioning":case.binding()})()
    with running_http(fixture,display_name="Baltor") as (base,service):
        print(json.dumps({"origin":base}),flush=True)
        sys.stdin.readline()
`;
    child = spawn(process.env.PYTHON || "python3", ["-u", "-c", program], {cwd: root,
      env: {...process.env, PYTHONPATH: resolve(root, "src"), PYTHONDONTWRITEBYTECODE: "1"}, stdio: ["pipe", "pipe", "pipe"]});
    const lines = createInterface({input: child.stdout});
    origin = await new Promise((accept, reject) => {
      const timer = setTimeout(() => reject(new Error("Fixture start timed out")), 15000);
      lines.once("line", line => {clearTimeout(timer); try {accept(JSON.parse(line).origin);} catch(error) {reject(error);}});
      child.once("exit", code => {clearTimeout(timer); reject(new Error("Fixture exited: " + code));});
    });
  } else {
    const url = new URL(target);
    if (url.protocol !== "https:" || url.pathname !== "/" || url.search || url.hash || url.username || url.password) throw new Error("Use a plain HTTPS origin");
    origin = url.origin;
  }
  browser = await chromium.launch({executablePath: "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
  for (const viewport of [{width: 1440, height: 1000}, {width: 390, height: 844}]) {
    const context = await browser.newContext({viewport, acceptDownloads: true, reducedMotion: "reduce"});
    await context.addCookies([{name: "profile_cookie_probe", value: "noncredential", url: origin}]);
    let mode = "real", seenBody;
    await context.route("**/*", async route => {
      const request = route.request(), url = new URL(request.url());
      if (url.origin !== origin) {errors.push("outside_request"); return route.abort();}
      if (url.pathname !== "/api/v1/feeds/profile") return route.continue();
      requests.push({method: request.method(), cookie: Boolean((await request.allHeaders()).cookie)});
      if (mode === "corrupt") {
        const result = structuredClone(seenBody);
        result.result.files[0].content += " changed";
        return route.fulfill({status: 200, contentType: "application/json", body: JSON.stringify(result)});
      }
      if (mode === "failure") return route.fulfill({status: 503, contentType: "application/json", body: "{}"});
      const response = await route.fetch();
      seenBody = await response.json();
      return route.fulfill({response});
    });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", message => {
      if (message.type() === "error" && !message.text().startsWith("Failed to load resource:")) errors.push(message.text());
    });
    await page.goto(origin + "/feeds", {waitUntil: "networkidle"});
    await page.locator(".feed-profile-editor > summary").click();
    const form = page.locator("#feed-profile-form");
    const build = form.getByRole("button", {name: "Build reading profile"});
    const status = page.locator("#feed-profile-status");
    const ready = () => page.waitForFunction(() => !document.querySelector('#feed-profile-form [type="submit"]').disabled);
    await form.locator('[name="agent_label"]').fill("Coding reviewer");
    await form.locator('[name="collection_ids"]').selectOption(["coding-benchmarks"]);
    await build.click();
    await page.locator('#feed-profile-downloads a[download="profile.json"]').waitFor({state: "visible"});
    const initial = seenBody.result;
    for (const path of ["profile.json", "READING.md"]) {
      const promise = page.waitForEvent("download");
      await page.locator(`#feed-profile-downloads a[download="${path}"]`).click();
      const download = await promise;
      check("exact_" + path + "_" + viewport.width,
        readFileSync(await download.path(), "utf8") === initial.files.find(file => file.path === path).content);
    }
    await form.locator('[name="agent_label"]').fill("Finance researcher");
    check("changed_selection_invalidates_downloads_" + viewport.width, await page.locator("#feed-profile-downloads").isHidden());
    await form.locator('[name="collection_ids"]').selectOption(["finance-research"]);
    await form.locator("details > summary").click();
    await form.locator('[name="excluded_source_ids"]').selectOption(["sec-edgar"]);
    await build.click();
    await page.locator('#feed-profile-downloads a[download="profile.json"]').waitFor({state: "visible"});
    check("second_agent_has_only_selected_source_" + viewport.width,
      seenBody.result.profile.request.agent_label === "Finance researcher" &&
      JSON.stringify(seenBody.result.profile.sources.map(item => item.id)) === '["fred"]' &&
      initial.profile.request.agent_label === "Coding reviewer");
    check("no_horizontal_scroll_" + viewport.width, await page.evaluate(() => document.documentElement.scrollWidth - innerWidth <= 1));
    await page.locator("#feed-profile").screenshot({path: output.replace(/\.json$/, `-${viewport.width}.png`), animations: "disabled"});
    await page.evaluate(() => { document.documentElement.dataset.theme = "dark"; });
    check("dark_theme_fits_" + viewport.width, await page.evaluate(() => document.documentElement.scrollWidth - innerWidth <= 1));
    await page.locator("#feed-profile").screenshot({path: output.replace(/\.json$/, `-${viewport.width}-dark.png`), animations: "disabled"});
    mode = "corrupt";
    await build.click(); await ready();
    check("corrupted_file_produces_no_download_" + viewport.width,
      await page.locator("#feed-profile-downloads").isHidden() && (await status.innerText()).includes("could not be prepared"));
    mode = "failure";
    await build.click(); await ready();
    check("failed_request_keeps_user_selections_" + viewport.width,
      await form.locator('[name="agent_label"]').inputValue() === "Finance researcher" && await page.locator("#feed-profile-downloads").isHidden());
    await form.getByRole("button", {name: "Start another agent"}).click();
    check("reset_clears_downloads_" + viewport.width,
      await form.locator('[name="agent_label"]').inputValue() === "" && await page.locator("#feed-profile-downloads").isHidden());
    check("no_browser_storage_" + viewport.width, await page.evaluate(() => localStorage.length === 0 && sessionStorage.length === 0));
    await context.close();
  }
  check("requests_omit_credentials", requests.length > 0 && requests.every(item => item.method === "POST" && !item.cookie));
} catch (error) {errors.push(error.message); check("completed", false);}
finally {
  if (browser) await browser.close();
  if (child) {child.stdin.end("stop\n"); if (child.exitCode === null) await new Promise(accept => {
    const timer = setTimeout(() => {child.kill("SIGTERM"); accept();}, 5000);
    child.once("exit", () => {clearTimeout(timer); accept();});
  });}
}
const report = {record_type: "feed_profile_browser_acceptance/v1", origin, checks, errors, requests,
  passed: checks.filter(item => item.passed).length, total: checks.length,
  all_passed: checks.every(item => item.passed) && errors.length === 0,
  scope: "Client-owned exports only; no account mutation, upstream reads or hosted schedule."};
writeFileSync(output, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({output, passed: report.passed, total: report.total, errors}));
process.exitCode = report.all_passed ? 0 : 1;
