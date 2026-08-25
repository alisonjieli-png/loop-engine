#!/usr/bin/env node

import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { showcaseData } from "../showcase-data.js";
import {
  EXPECTED_SCENES,
  MAX_DURATION_SECONDS,
  MIN_DURATION_SECONDS,
  argument,
  attachErrorCapture,
  findBrowser,
  findFfprobe,
  launchBrowser,
  openShowcase,
  probeMedia,
  sha256,
  summarizeMedia,
  uniqueErrors,
  validateVideo
} from "../tools/media-common.mjs";

const testDirectory = dirname(fileURLToPath(import.meta.url));
const showcaseDirectory = join(testDirectory, "..");

async function exists(path) {
  try {
    await access(path);
    return true;
  } catch {
    return false;
  }
}

function currentScene(state) {
  return Number(
    state?.sceneIndex ?? state?.slideIndex ?? state?.currentScene ?? state?.index ?? NaN
  );
}

function isPlaying(state) {
  return Boolean(state?.playing ?? state?.isPlaying);
}

async function state(page) {
  return page.evaluate(() => {
    const api = window.__LOOP_SHOWCASE_API__;
    if (!api || typeof api.getState !== "function") {
      throw new Error("window.__LOOP_SHOWCASE_API__.getState() is unavailable.");
    }
    return api.getState();
  });
}

async function waitForScene(page, expected) {
  await page.waitForFunction((index) => {
    const apiState = window.__LOOP_SHOWCASE_API__?.getState?.() || {};
    const actual = Number(
      apiState.sceneIndex ??
      apiState.slideIndex ??
      apiState.currentScene ??
      apiState.index ??
      document.body.dataset.currentScene
    );
    return actual === index;
  }, expected, { timeout: 5000 });
}

async function verifyMediaWhenPresent() {
  const assets = join(showcaseDirectory, "assets");
  const paths = {
    mp4: join(assets, "loop-engine-architecture.mp4"),
    webm: join(assets, "loop-engine-architecture.webm"),
    evidence: join(assets, "media-evidence.json")
  };
  const presence = Object.fromEntries(
    await Promise.all(Object.entries(paths).map(async ([name, path]) => [name, await exists(path)]))
  );
  if (!presence.mp4 && !presence.webm && !presence.evidence) {
    return { state: "not generated", checked: false };
  }
  assert.deepEqual(presence, { mp4: true, webm: true, evidence: true },
    "MP4, WebM, and media-evidence.json must appear together");
  const ffprobe = findFfprobe();
  const evidence = JSON.parse(await readFile(paths.evidence, "utf8"));
  assert.equal(evidence.recordType, "loop_engine_showcase_media_evidence/v2");
  assert.equal(evidence.timeline.scenes, EXPECTED_SCENES);
  assert.ok(
    evidence.timeline.durationSeconds >= MIN_DURATION_SECONDS &&
    evidence.timeline.durationSeconds <= MAX_DURATION_SECONDS
  );
  const mp4 = summarizeMedia(probeMedia(ffprobe, paths.mp4));
  const webm = summarizeMedia(probeMedia(ffprobe, paths.webm));
  validateVideo(mp4, "Saved MP4", {
    durationSeconds: evidence.timeline.durationSeconds,
    videoCodec: "h264",
    audioCodec: "aac"
  });
  validateVideo(webm, "Saved WebM", {
    durationSeconds: evidence.timeline.durationSeconds,
    videoCodec: "vp8",
    audioCodec: "opus"
  });
  assert.equal(await sha256(paths.mp4), evidence.outputs.mp4.sha256);
  assert.equal(await sha256(paths.webm), evidence.outputs.webm.sha256);
  assert.equal(evidence.outputs.mp4.fullDecodePassed, true);
  assert.equal(evidence.outputs.webm.fullDecodePassed, true);
  return { state: "verified", checked: true, mp4, webm };
}

async function main() {
  assert.equal(showcaseData.slides.length, EXPECTED_SCENES);
  const durationSeconds = showcaseData.slides.reduce(
    (total, slide) => total + Number(slide.durationSeconds),
    0
  );
  assert.ok(durationSeconds >= MIN_DURATION_SECONDS && durationSeconds <= MAX_DURATION_SECONDS);
  assert.equal(showcaseData.meta.title, "Loop Engine");
  assert.equal(showcaseData.meta.subtitle, "Loops are all you need.");
  const requiredIds = [
    "architecture-overview",
    "loop-object",
    "deterministic-mode",
    "hybrid-mode",
    "non-deterministic-mode",
    "practitioner-profile",
    "intelligence-overview",
    "solution-canvas",
    "static-architecture",
    "worked-task-overview",
    "worked-verify-record",
    "practitioner-improvement-profile"
  ];
  const ids = new Set(showcaseData.slides.map((slide) => slide.id));
  for (const id of requiredIds) {
    assert.ok(ids.has(id), `Missing required slide: ${id}`);
  }
  const sharedGroups = [
    "Intelligence Search and Retrieval",
    "Web Research",
    "Custom Plugins",
  ];
  const overview = showcaseData.slides.find((slide) => slide.id === "architecture-overview");
  const staticSlide = showcaseData.slides.find((slide) => slide.id === "static-architecture");
  const sharedAccess = showcaseData.slides.find((slide) => slide.id === "shared-access");
  assert.deepEqual(overview.visual.staticArchitecture.items, sharedGroups);
  assert.equal(overview.visual.improvement, undefined);
  assert.deepEqual(staticSlide.visual.groups, sharedGroups);
  assert.deepEqual(sharedAccess.visual.context.items, sharedGroups);
  const publicCopy = JSON.stringify(showcaseData);
  assert.ok(!/[—–]/u.test(publicCopy), "Public showcase copy contains an em dash or en dash");
  const retiredAccountingWord = ["rece", "ipts?"].join("");
  const retiredHistoryLabel = ["chron", "icles?"].join("");
  const retiredTopologyLabel = ["chi", "ld(?:ren)?"].join("");
  assert.ok(
    !new RegExp(`\\b${retiredAccountingWord}\\b`, "iu").test(publicCopy),
    "Public showcase copy uses a retired accounting metaphor",
  );
  assert.ok(
    !new RegExp(`\\b${retiredHistoryLabel}\\b`, "iu").test(publicCopy),
    "Public showcase copy uses a retired history label",
  );
  assert.ok(
    !new RegExp(`\\b${retiredTopologyLabel}\\b`, "iu").test(publicCopy),
    "Public showcase copy uses a retired topology label",
  );

  const baseUrl = argument("--base-url", "http://127.0.0.1:8082").replace(/\/$/, "");
  const browserExecutable = await findBrowser();
  const errors = [];
  const browser = await launchBrowser(browserExecutable);
  try {
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
      colorScheme: "light",
      reducedMotion: "no-preference"
    });
    const page = await context.newPage();
    attachErrorCapture(page, errors, "player");
    await openShowcase(page, `${baseUrl}/`);
    const runtimeContract = await page.evaluate(() => ({
      scenes: window.__LOOP_SHOWCASE_SCENE_COUNT__,
      duration: window.__LOOP_SHOWCASE_DURATION_SECONDS__,
      entries: document.querySelectorAll("[data-scene-index]").length,
      activeEntries: document.querySelectorAll('[data-scene-index][aria-current="true"]').length,
      stage: Boolean(document.querySelector("#showcase-stage")),
      controls: [
        "play-pause",
        "previous-scene",
        "next-scene",
        "restart",
        "timeline-scrubber",
        "speed-select",
        "reduced-motion"
      ].filter((id) => !document.getElementById(id))
    }));
    assert.equal(runtimeContract.scenes, EXPECTED_SCENES);
    assert.ok(runtimeContract.duration >= MIN_DURATION_SECONDS);
    assert.ok(runtimeContract.duration <= MAX_DURATION_SECONDS);
    assert.equal(runtimeContract.entries, EXPECTED_SCENES);
    assert.equal(runtimeContract.activeEntries, 1);
    assert.equal(runtimeContract.stage, true);
    assert.deepEqual(runtimeContract.controls, [], `Missing controls: ${runtimeContract.controls.join(", ")}`);
    assert.equal(currentScene(await state(page)), 0);

    await page.locator("#next-scene").click();
    await waitForScene(page, 1);
    await page.locator("#previous-scene").click();
    await waitForScene(page, 0);

    await page.locator('[data-scene-index="9"]').click();
    await waitForScene(page, 9);
    await page.evaluate(() => document.activeElement?.blur());
    await page.keyboard.press("ArrowRight");
    await waitForScene(page, 10);
    await page.keyboard.press("ArrowLeft");
    await waitForScene(page, 9);
    await page.keyboard.press("Home");
    await waitForScene(page, 0);

    await page.locator("#play-pause").click();
    await page.waitForTimeout(120);
    assert.equal(isPlaying(await state(page)), true, "Play did not enter the playing state");
    await page.evaluate(() => document.activeElement?.blur());
    await page.keyboard.press("Space");
    await page.waitForTimeout(80);
    assert.equal(isPlaying(await state(page)), false, "Space did not pause playback");

    await page.evaluate(() => window.__LOOP_SHOWCASE_API__.setProgress(0.5));
    const scrubbed = await state(page);
    assert.ok(currentScene(scrubbed) >= 11 && currentScene(scrubbed) <= 15, "Scrub did not reach timeline midpoint");
    const scrubber = page.locator("#timeline-scrubber");
    const scrubberContract = await scrubber.evaluate((element) => ({
      type: element.type,
      min: Number(element.min),
      max: Number(element.max),
      value: Number(element.value)
    }));
    assert.equal(scrubberContract.type, "range");
    assert.ok(scrubberContract.value > scrubberContract.min);
    assert.ok(scrubberContract.value < scrubberContract.max);

    const speed = page.locator("#speed-select");
    assert.deepEqual(await speed.locator("option").allTextContents(), ["0.5x", "1x", "1.5x", "2x"]);
    await speed.selectOption("1.5");
    assert.equal(Number((await state(page)).speed), 1.5);

    await page.evaluate(() => window.__LOOP_SHOWCASE_API__.setReducedMotion(true));
    assert.equal(Boolean((await state(page)).reducedMotion), true);
    await page.locator("#restart").click();
    await waitForScene(page, 0);

    await context.close();
  } finally {
    await browser.close();
  }
  const browserErrors = uniqueErrors(errors);
  assert.deepEqual(browserErrors, [], `Browser errors:\n${browserErrors.join("\n")}`);
  const media = await verifyMediaWhenPresent();
  process.stdout.write(`${JSON.stringify({
    ok: true,
    scenes: EXPECTED_SCENES,
    durationSeconds,
    controls: "verified",
    keyboard: "verified",
    scrub: "verified",
    reducedMotion: "verified",
    consoleErrors: 0,
    media
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
