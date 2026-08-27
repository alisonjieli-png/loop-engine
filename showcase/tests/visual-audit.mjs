#!/usr/bin/env node

import assert from "node:assert/strict";
import { mkdtemp, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { showcaseData } from "../showcase-data.js";
import {
  EXPECTED_SCENES,
  argument,
  attachErrorCapture,
  findBrowser,
  launchBrowser,
  openShowcase,
  uniqueErrors
} from "../tools/media-common.mjs";

const viewports = [
  { width: 1920, height: 1080, label: "1920x1080" },
  { width: 1280, height: 720, label: "1280x720" }
];
const keyScenes = new Set([0, 1, 2, 8, 10, 13, 18, 20, 21, 22, 24, 25]);

const canvasAuditScript = () => {
  window.__LOOP_CANVAS_TEXT_AUDIT__ = [];
  const original = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function patchedFillText(text, x, y, maxWidth) {
    const value = String(text);
    const metrics = this.measureText(value);
    const declaredMaximum = Number(maxWidth);
    const naturalWidth = Number(metrics.width || 0);
    const fontSizeMatch = String(this.font).match(/([0-9]+(?:\.[0-9]+)?)px/);
    const fontSize = Number(fontSizeMatch?.[1] || 16);
    const ascent = Number(metrics.actualBoundingBoxAscent || fontSize * 0.8);
    const descent = Number(metrics.actualBoundingBoxDescent || fontSize * 0.2);
    const drawnWidth = Number.isFinite(declaredMaximum) && declaredMaximum > 0
      ? Math.min(naturalWidth, declaredMaximum)
      : naturalWidth;
    let left = Number(x);
    if (this.textAlign === "center") left -= drawnWidth / 2;
    if (this.textAlign === "right" || this.textAlign === "end") left -= drawnWidth;
    let top = Number(y) - ascent;
    if (this.textBaseline === "top" || this.textBaseline === "hanging") top = Number(y);
    if (this.textBaseline === "middle") top = Number(y) - fontSize / 2;
    const bottom = top + ascent + descent;
    const transform = this.getTransform();
    const points = [
      new DOMPoint(left, top).matrixTransform(transform),
      new DOMPoint(left + drawnWidth, bottom).matrixTransform(transform)
    ];
    window.__LOOP_CANVAS_TEXT_AUDIT__.push({
      text: value,
      left: Math.min(points[0].x, points[1].x),
      right: Math.max(points[0].x, points[1].x),
      top: Math.min(points[0].y, points[1].y),
      bottom: Math.max(points[0].y, points[1].y),
      canvasWidth: this.canvas.width,
      canvasHeight: this.canvas.height,
      alpha: this.globalAlpha
    });
    return Number.isFinite(declaredMaximum)
      ? original.call(this, text, x, y, maxWidth)
      : original.call(this, text, x, y);
  };
};

async function waitForScene(page, expected) {
  await page.waitForFunction((index) => {
    const state = window.__LOOP_SHOWCASE_API__?.getState?.() || {};
    return Number(state.sceneIndex) === index;
  }, expected, { timeout: 5000 });
}

async function auditViewport(browser, baseUrl, viewport, screenshotDirectory, errors) {
  const context = await browser.newContext({
    viewport: { width: viewport.width, height: viewport.height },
    deviceScaleFactor: 1,
    colorScheme: "light",
    reducedMotion: "reduce"
  });
  const page = await context.newPage();
  await page.addInitScript(canvasAuditScript);
  attachErrorCapture(page, errors, viewport.label);
  await openShowcase(page, `${baseUrl}/`);
  const results = [];
  for (let sceneIndex = 0; sceneIndex < EXPECTED_SCENES; sceneIndex += 1) {
    await page.evaluate((index) => {
      window.__LOOP_CANVAS_TEXT_AUDIT__ = [];
      window.__LOOP_SHOWCASE_API__.goToScene(index);
    }, sceneIndex);
    await waitForScene(page, sceneIndex);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const audit = await page.evaluate(() => {
      const canvas = document.querySelector("#showcase-stage canvas, #showcase-stage");
      const stage = document.getElementById("showcase-stage");
      const stageRect = stage?.getBoundingClientRect();
      const state = window.__LOOP_SHOWCASE_API__.getState();
      const calls = window.__LOOP_CANVAS_TEXT_AUDIT__ || [];
      const clippedText = calls.filter((call) =>
        call.alpha > 0.001 &&
        (
          call.left < -1 ||
          call.top < -1 ||
          call.right > call.canvasWidth + 1 ||
          call.bottom > call.canvasHeight + 1
        )
      );
      const controls = [
        "play-pause",
        "previous-scene",
        "next-scene",
        "restart",
        "timeline-scrubber",
        "speed-select",
        "reduced-motion"
      ].map((id) => {
        const element = document.getElementById(id);
        const rect = element?.getBoundingClientRect();
        return {
          id,
          exists: Boolean(element),
          width: rect?.width || 0,
          height: rect?.height || 0,
          left: rect?.left || 0,
          right: rect?.right || 0
        };
      });
      return {
        sceneIndex: state.sceneIndex,
        sceneId: state.sceneId,
        canvasWidth: canvas?.width || 0,
        canvasHeight: canvas?.height || 0,
        canvasTextCalls: calls.length,
        clippedText,
        stage: stageRect ? {
          left: stageRect.left,
          right: stageRect.right,
          width: stageRect.width,
          height: stageRect.height
        } : null,
        documentWidth: document.documentElement.scrollWidth,
        viewportWidth: window.innerWidth,
        controls,
        activeEntries: document.querySelectorAll('[data-scene-index][aria-current="true"]').length,
        bodyScene: Number(document.body.dataset.currentScene),
        caption: document.getElementById("scene-caption")?.textContent?.trim() ||
          document.querySelector("[aria-live]")?.textContent?.trim() || ""
      };
    });
    assert.equal(audit.sceneIndex, sceneIndex, `${viewport.label}: wrong active scene`);
    assert.equal(audit.bodyScene, sceneIndex + 1, `${viewport.label}: body scene marker differs`);
    assert.equal(audit.activeEntries, 1, `${viewport.label}: expected one active scene-list entry`);
    assert.equal(audit.canvasWidth, 1920, `${viewport.label}: internal canvas width`);
    assert.equal(audit.canvasHeight, 1080, `${viewport.label}: internal canvas height`);
    assert.ok(audit.canvasTextCalls > 3, `${viewport.label} scene ${sceneIndex + 1} drew too little text`);
    assert.deepEqual(
      audit.clippedText,
      [],
      `${viewport.label} scene ${sceneIndex + 1} drew text outside the canvas: ${JSON.stringify(audit.clippedText)}`
    );
    assert.ok(audit.stage, `${viewport.label}: stage is missing`);
    assert.ok(audit.stage.left >= -1, `${viewport.label}: stage starts outside viewport`);
    assert.ok(audit.stage.right <= viewport.width + 1, `${viewport.label}: stage exceeds viewport width`);
    assert.ok(audit.stage.width >= Math.min(880, viewport.width * 0.69), `${viewport.label}: stage is too small`);
    assert.ok(
      audit.documentWidth <= audit.viewportWidth + 1,
      `${viewport.label}: document has horizontal overflow (${audit.documentWidth} > ${audit.viewportWidth})`
    );
    for (const control of audit.controls) {
      assert.equal(control.exists, true, `${viewport.label}: missing #${control.id}`);
      const minimumControlSize = control.id === "timeline-scrubber"
        ? 12
        : control.id === "reduced-motion"
          ? 16
          : 20;
      assert.ok(
        control.width >= minimumControlSize && control.height >= minimumControlSize,
        `${viewport.label}: #${control.id} is too small`
      );
      assert.ok(control.left >= -1 && control.right <= viewport.width + 1,
        `${viewport.label}: #${control.id} clips horizontally`);
    }
    assert.ok(audit.caption.length > 10, `${viewport.label}: scene caption is empty`);
    if (keyScenes.has(sceneIndex)) {
      const screenshot = join(
        screenshotDirectory,
        `${viewport.label}-scene-${String(sceneIndex + 1).padStart(2, "0")}.png`
      );
      await page.locator("#showcase-stage").screenshot({ path: screenshot, animations: "disabled" });
      const information = await stat(screenshot);
      assert.ok(information.size > 10000, `${viewport.label} scene ${sceneIndex + 1} screenshot is too small`);
    }
    results.push({
      scene: sceneIndex + 1,
      id: audit.sceneId,
      canvasTextCalls: audit.canvasTextCalls,
      clippedText: 0
    });
  }
  await context.close();
  return results;
}

async function main() {
  assert.equal(showcaseData.slides.length, EXPECTED_SCENES);
  const baseUrl = argument("--base-url", "http://127.0.0.1:8082").replace(/\/$/, "");
  const browserExecutable = await findBrowser();
  const screenshotDirectory = await mkdtemp(join(tmpdir(), "loop-engine-showcase-audit-"));
  const errors = [];
  const browser = await launchBrowser(browserExecutable);
  const reports = {};
  try {
    for (const viewport of viewports) {
      reports[viewport.label] = await auditViewport(
        browser,
        baseUrl,
        viewport,
        screenshotDirectory,
        errors
      );
    }
  } finally {
    await browser.close();
    await rm(screenshotDirectory, { recursive: true, force: true });
  }
  const browserErrors = uniqueErrors(errors);
  assert.deepEqual(browserErrors, [], `Browser errors:\n${browserErrors.join("\n")}`);
  process.stdout.write(`${JSON.stringify({
    ok: true,
    scenes: EXPECTED_SCENES,
    viewports: viewports.map((item) => item.label),
    inspectedSceneViews: EXPECTED_SCENES * viewports.length,
    keySlideScreenshotsInspected: keyScenes.size * viewports.length,
    canvasTextClipping: 0,
    horizontalOverflow: 0,
    consoleErrors: 0,
    reports
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
