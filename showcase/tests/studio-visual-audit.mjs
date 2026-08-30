#!/usr/bin/env node

import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
  argument,
  attachErrorCapture,
  findBrowser,
  launchBrowser,
  uniqueErrors
} from "../tools/media-common.mjs";

const baseUrl = argument("--base-url", "http://127.0.0.1:8765").replace(/\/$/, "");
const runId = argument("--run-id", "studio-browser-fixture");
const requestedScreenshotDirectory = argument("--screenshot-dir", "");
const viewports = [
  { width: 1280, height: 800, label: "desktop" },
  { width: 390, height: 844, label: "mobile" }
];

const routes = [
  ["/app", "Operations"],
  ["/app/runs", "Runs"],
  [`/app/runs/${runId}/overview`, "Product result"],
  [`/app/runs/${runId}/result`, "COMPLETED_VERIFIED"],
  [`/app/runs/${runId}/tree`, "loop1"],
  [`/app/runs/${runId}/runtime`, "Spawned tasks"],
  [`/app/runs/${runId}/canvas`, "solution.component"],
  [`/app/runs/${runId}/playback`, "key event"],
  [`/app/runs/${runId}/calls`, "zero semantic calls"],
  ["/app/intelligence", "Four intelligence layers"],
  ["/app/context", "Context Intelligence"],
  ["/app/nodes", "Code Intelligence"],
  ["/app/solutions", "Solution library"],
  ["/app/improvements", "Improvements"],
  ["/app/runtime", "Runtime inventory"]
];

async function inspectRoute(page, route, expected, viewport) {
  await page.goto(`${baseUrl}${route}`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => document.querySelector("#status")?.textContent?.startsWith("live"));
  const state = await page.evaluate(() => {
    const main = document.querySelector("#main");
    const nav = document.querySelector("#nav");
    const search = document.querySelector("#q");
    return {
      text: main?.textContent || "",
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      mainWidth: main?.getBoundingClientRect().width || 0,
      navWidth: nav?.getBoundingClientRect().width || 0,
      searchLabel: search?.getAttribute("aria-label") || "",
      activeNavigation: document.querySelectorAll("#nav a.on").length,
      status: document.querySelector("#status")?.textContent || ""
    };
  });
  assert.ok(state.text.includes(expected), `${viewport.label} ${route}: missing ${expected}`);
  assert.ok(!state.text.includes("Not found"), `${viewport.label} ${route}: rendered Not found`);
  assert.ok(!state.text.startsWith("Error"), `${viewport.label} ${route}: rendered Error`);
  assert.ok(state.documentWidth <= state.viewportWidth + 1,
    `${viewport.label} ${route}: horizontal overflow ${state.documentWidth} > ${state.viewportWidth}`);
  assert.ok(state.mainWidth > 250, `${viewport.label} ${route}: main content is too narrow`);
  assert.ok(state.navWidth > 100, `${viewport.label} ${route}: navigation is unavailable`);
  assert.equal(state.searchLabel, "Filter the current page");
  assert.equal(state.activeNavigation, 1);
  assert.ok(state.status.startsWith("live"));
}

async function main() {
  const browserExecutable = await findBrowser();
  const browser = await launchBrowser(browserExecutable);
  const errors = [];
  const screenshots = requestedScreenshotDirectory
    ? requestedScreenshotDirectory
    : await mkdtemp(join(tmpdir(), "loop-engine-studio-audit-"));
  if (requestedScreenshotDirectory) await mkdir(screenshots, { recursive: true });
  try {
    for (const viewport of viewports) {
      const context = await browser.newContext({
        viewport: { width: viewport.width, height: viewport.height },
        colorScheme: "light",
        reducedMotion: "reduce"
      });
      const page = await context.newPage();
      attachErrorCapture(page, errors, viewport.label);
      for (const [route, expected] of routes) {
        await inspectRoute(page, route, expected, viewport);
      }
      await page.goto(`${baseUrl}/app/runs/${runId}/playback`, { waitUntil: "networkidle" });
      await page.locator("button[aria-label='next event']").click();
      assert.match(await page.locator("#pos").textContent(), /^2 \/ /);
      const screenshot = join(screenshots, `${viewport.label}.png`);
      await page.screenshot({ path: screenshot, fullPage: true, animations: "disabled" });
      assert.ok((await stat(screenshot)).size > 5000,
        `${viewport.label}: Studio screenshot is unexpectedly small`);
      await context.close();
    }
  } finally {
    await browser.close();
    if (!requestedScreenshotDirectory) {
      await rm(screenshots, { recursive: true, force: true });
    }
  }
  const browserErrors = uniqueErrors(errors);
  assert.deepEqual(browserErrors, [], `Browser errors:\n${browserErrors.join("\n")}`);
  process.stdout.write(`${JSON.stringify({
    ok: true,
    routes: routes.length,
    viewports: viewports.map((item) => item.label),
    inspectedViews: routes.length * viewports.length,
    horizontalOverflow: 0,
    browserErrors: 0,
    screenshots: requestedScreenshotDirectory || "temporary"
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
