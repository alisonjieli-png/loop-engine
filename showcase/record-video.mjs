#!/usr/bin/env node

import { open } from "node:fs/promises";
import {
  mkdir,
  mkdtemp,
  readFile,
  rename,
  rm,
  stat,
  unlink,
  writeFile
} from "node:fs/promises";
import { basename, dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  EXPECTED_SCENES,
  MAX_DURATION_SECONDS,
  MIN_DURATION_SECONDS,
  VIDEO_FRAME_RATE,
  VIDEO_HEIGHT,
  VIDEO_WIDTH,
  argument,
  attachErrorCapture,
  fileEvidence,
  findBrowser,
  findFfmpeg,
  findFfprobe,
  launchBrowser,
  openShowcase,
  probeMedia,
  run,
  sha256,
  summarizeMedia,
  uniqueErrors,
  validateVideo
} from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultAssetsDirectory = join(scriptDirectory, "assets");
const lockPath = join(scriptDirectory, ".media-export.lock");

async function acquireExclusiveWriter() {
  try {
    const handle = await open(lockPath, "wx", 0o600);
    await handle.writeFile(`${JSON.stringify({
      pid: process.pid,
      startedAt: new Date().toISOString(),
      command: "record-video.mjs"
    }, null, 2)}\n`);
    return handle;
  } catch (error) {
    if (error.code !== "EEXIST") {
      throw error;
    }
    let owner = "The lock contents could not be read.";
    try {
      owner = (await readFile(lockPath, "utf8")).trim();
    } catch {
      // The exact read failure is less useful than the exclusive-writer refusal.
    }
    throw new Error(
      `A media exporter already owns ${lockPath}. Do not run two writers.\n${owner}`
    );
  }
}

async function releaseExclusiveWriter(handle) {
  if (handle) {
    await handle.close();
  }
  try {
    await unlink(lockPath);
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }
}

function normalizedTiming(slides, durationSeconds) {
  if (!Array.isArray(slides) || slides.length !== EXPECTED_SCENES) {
    throw new Error(
      `The player exposed ${Array.isArray(slides) ? slides.length : 0} timed slides; expected ${EXPECTED_SCENES}.`
    );
  }
  let cursorMs = 0;
  const normalized = slides.map((slide, index) => {
    const durationMs = Number(
      slide.durationMs ??
      (Number.isFinite(Number(slide.durationSeconds)) ? Number(slide.durationSeconds) * 1000 : NaN) ??
      NaN
    );
    const startMs = Number.isFinite(Number(slide.startMs))
      ? Number(slide.startMs)
      : Number.isFinite(Number(slide.startSeconds))
        ? Number(slide.startSeconds) * 1000
        : cursorMs;
    const endMs = Number.isFinite(Number(slide.endMs))
      ? Number(slide.endMs)
      : Number.isFinite(Number(slide.endSeconds))
        ? Number(slide.endSeconds) * 1000
        : startMs + durationMs;
    if (!Number.isFinite(startMs) || !Number.isFinite(durationMs) || durationMs <= 0 || !Number.isFinite(endMs)) {
      throw new Error(
        `Slide ${index + 1} does not expose a valid start and duration. ` +
        "Each __showcase.slides entry must provide durationMs and may provide startMs."
      );
    }
    if (startMs < cursorMs - 2) {
      throw new Error(`Slide ${index + 1} starts before the previous slide finishes.`);
    }
    cursorMs = endMs;
    return {
      index,
      id: String(slide.id || slide.key || `scene-${index + 1}`),
      title: String(slide.title || slide.heading || `Scene ${index + 1}`),
      startSeconds: startMs / 1000,
      durationSeconds: durationMs / 1000,
      sampleSeconds: Math.min(
        durationSeconds - 0.05,
        Math.max(0.05, (startMs + Math.min(durationMs * 0.55, Math.max(500, durationMs - 250))) / 1000)
      )
    };
  });
  if (Math.abs(cursorMs / 1000 - durationSeconds) > 1) {
    throw new Error(
      `Slide timing totals ${cursorMs / 1000} seconds but the player declares ${durationSeconds} seconds.`
    );
  }
  return normalized;
}

async function readRecordingContract(page) {
  const contract = await page.evaluate(() => {
    const publicApi = window.__showcase || {};
    const rawSlides = Array.isArray(publicApi.slides)
      ? publicApi.slides
      : Array.from(document.querySelectorAll("[data-scene-index]")).map((element) => ({
          id: element.getAttribute("data-scene-id") || "",
          title: element.textContent.trim(),
          startMs: Number(element.getAttribute("data-start-ms")),
          durationMs: Number(element.getAttribute("data-duration-ms"))
        }));
    return {
      sceneCount: Number(
        window.__LOOP_SHOWCASE_SCENE_COUNT__ ?? publicApi.slides?.length ?? rawSlides.length
      ),
      durationSeconds: Number(
        window.__LOOP_SHOWCASE_DURATION_SECONDS__ ??
        (Number.isFinite(Number(publicApi.durationMs)) ? Number(publicApi.durationMs) / 1000 : NaN)
      ),
      slides: rawSlides.map((slide) => ({
        id: slide.id,
        key: slide.key,
        title: slide.title,
        heading: slide.heading,
        startMs: slide.startMs,
        startSeconds: slide.startSeconds,
        endMs: slide.endMs,
        endSeconds: slide.endSeconds,
        durationMs: slide.durationMs,
        durationSeconds: slide.durationSeconds
      }))
    };
  });
  if (contract.sceneCount !== EXPECTED_SCENES) {
    throw new Error(`Recording refused: player has ${contract.sceneCount} scenes; expected ${EXPECTED_SCENES}.`);
  }
  if (
    !Number.isFinite(contract.durationSeconds) ||
    contract.durationSeconds < MIN_DURATION_SECONDS ||
    contract.durationSeconds > MAX_DURATION_SECONDS
  ) {
    throw new Error(
      `Recording refused: timeline duration ${contract.durationSeconds} is outside ${MIN_DURATION_SECONDS}-${MAX_DURATION_SECONDS} seconds.`
    );
  }
  return {
    ...contract,
    timeline: normalizedTiming(contract.slides, contract.durationSeconds)
  };
}

function transcodeVideos(ffmpeg, rawWebm, webm, mp4, durationSeconds) {
  const commonVideo = [
    "-vf", `fps=${VIDEO_FRAME_RATE},scale=${VIDEO_WIDTH}:${VIDEO_HEIGHT}:flags=lanczos,format=yuv420p`,
    "-t", durationSeconds.toFixed(3),
    "-map_metadata", "-1"
  ];
  run(ffmpeg, [
    "-hide_banner", "-loglevel", "error", "-y",
    "-i", rawWebm,
    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
    "-map", "0:v:0", "-map", "1:a:0",
    ...commonVideo,
    "-c:v", "libvpx",
    "-deadline", "good",
    "-cpu-used", "4",
    "-crf", "20",
    "-b:v", "0",
    "-c:a", "libopus",
    "-b:a", "64k",
    "-shortest",
    webm
  ], "WebM export");
  run(ffmpeg, [
    "-hide_banner", "-loglevel", "error", "-y",
    "-i", rawWebm,
    "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
    "-map", "0:v:0", "-map", "1:a:0",
    ...commonVideo,
    "-c:v", "libx264",
    "-preset", "slow",
    "-profile:v", "high",
    "-crf", "18",
    "-movflags", "+faststart",
    "-c:a", "aac",
    "-b:a", "96k",
    "-shortest",
    mp4
  ], "H.264 MP4 export");
}

function makeContactSheet(ffmpeg, mp4, contactSheet, framesDirectory, timeline) {
  for (const scene of timeline) {
    const frame = join(framesDirectory, `frame-${String(scene.index).padStart(2, "0")}.png`);
    run(ffmpeg, [
      "-hide_banner", "-loglevel", "error", "-y",
      "-i", mp4,
      "-ss", scene.sampleSeconds.toFixed(3),
      "-frames:v", "1",
      "-vf", "scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2:white",
      frame
    ], `Extract contact-sheet frame ${scene.index + 1}`);
  }
  run(ffmpeg, [
    "-hide_banner", "-loglevel", "error", "-y",
    "-framerate", "1",
    "-start_number", "0",
    "-i", join(framesDirectory, "frame-%02d.png"),
    "-vf", "tile=7x4:nb_frames=26:padding=8:margin=8:color=white",
    "-frames:v", "1",
    contactSheet
  ], "26-frame contact sheet export");
}

async function sourceHashes() {
  const names = [
    "index.html",
    "styles.css",
    "showcase-data.js",
    "render.js",
    "player.js",
    "record-video.mjs"
  ];
  const hashes = {};
  for (const name of names) {
    try {
      hashes[name] = await sha256(join(scriptDirectory, name));
    } catch (error) {
      if (error.code !== "ENOENT") {
        throw error;
      }
    }
  }
  return hashes;
}

async function publish(stagingPath, finalPath) {
  await mkdir(dirname(finalPath), { recursive: true });
  await rename(stagingPath, finalPath);
}

async function main() {
  const writer = await acquireExclusiveWriter();
  let stagingDirectory = "";
  let browser;
  try {
    const baseUrl = argument("--base-url", "http://127.0.0.1:8082").replace(/\/$/, "");
    const assetsDirectory = resolve(argument("--output-dir", defaultAssetsDirectory));
    const expectedSourceSha256 = argument("--expected-source-sha256", "").trim().toLowerCase();
    const sourcePath = join(scriptDirectory, "showcase-data.js");
    const sourceSha256AtStart = await sha256(sourcePath);
    if (expectedSourceSha256 && sourceSha256AtStart !== expectedSourceSha256) {
      throw new Error(
        `Showcase source SHA-256 is ${sourceSha256AtStart}; expected ${expectedSourceSha256}.`
      );
    }
    const ffmpeg = findFfmpeg();
    const ffprobe = findFfprobe();
    const browserExecutable = await findBrowser();
    await mkdir(assetsDirectory, { recursive: true });
    stagingDirectory = await mkdtemp(join(assetsDirectory, ".media-staging-"));
    const framesDirectory = join(stagingDirectory, "frames");
    await mkdir(framesDirectory, { recursive: true });

    const rawWebm = join(stagingDirectory, "recording.raw.webm");
    const webm = join(stagingDirectory, "loop-engine-architecture.webm");
    const mp4 = join(stagingDirectory, "loop-engine-architecture.mp4");
    const poster = join(stagingDirectory, "poster.png");
    const contactSheet = join(stagingDirectory, "contact-sheet.png");
    const evidencePath = join(stagingDirectory, "media-evidence.json");
    const browserErrors = [];

    browser = await launchBrowser(browserExecutable);
    const context = await browser.newContext({
      viewport: { width: VIDEO_WIDTH, height: VIDEO_HEIGHT },
      deviceScaleFactor: 1,
      acceptDownloads: true,
      colorScheme: "light",
      reducedMotion: "no-preference"
    });
    const page = await context.newPage();
    attachErrorCapture(page, browserErrors, "recording");
    const downloadPromise = page.waitForEvent("download", { timeout: 240000 });
    await openShowcase(page, `${baseUrl}/?record=1`, { readyTimeout: 45000 });
    const contract = await readRecordingContract(page);
    const timeoutMs = Math.ceil((contract.durationSeconds + 90) * 1000);
    const outcome = await Promise.race([
      downloadPromise.then((download) => ({ download })),
      page.waitForFunction(
        () => Boolean(window.__LOOP_SHOWCASE_RECORD_ERROR__ || window.__SHOWCASE_ERROR__),
        null,
        { timeout: timeoutMs }
      ).then(async () => ({
        error: await page.evaluate(
          () => window.__LOOP_SHOWCASE_RECORD_ERROR__ || window.__SHOWCASE_ERROR__
        )
      }))
    ]);
    if (outcome.error) {
      throw new Error(`Browser recording failed: ${outcome.error}`);
    }
    const downloadFailure = await outcome.download.failure();
    if (downloadFailure) {
      throw new Error(`Browser recording download failed: ${downloadFailure}`);
    }
    await outcome.download.saveAs(rawWebm);
    await page.waitForFunction(
      () =>
        window.__LOOP_SHOWCASE_DONE__ === true ||
        window.__SHOWCASE_DONE__ === true ||
        Boolean(window.__LOOP_SHOWCASE_RECORD_ERROR__ || window.__SHOWCASE_ERROR__),
      null,
      { timeout: 45000 }
    );
    const recordError = await page.evaluate(
      () => window.__LOOP_SHOWCASE_RECORD_ERROR__ || window.__SHOWCASE_ERROR__ || ""
    );
    if (recordError) {
      throw new Error(`Browser recording failed: ${recordError}`);
    }
    browserErrors.push(...await page.evaluate(() => window.__LOOP_SHOWCASE_ERRORS__ || []));

    const posterPage = await context.newPage();
    attachErrorCapture(posterPage, browserErrors, "poster");
    await openShowcase(posterPage, `${baseUrl}/?print=1&scene=0`);
    const stage = posterPage.locator("#showcase-stage, #architecture-stage").first();
    if (await stage.count() !== 1) {
      throw new Error("Poster export could not find #showcase-stage.");
    }
    const posterDataUrl = await stage.evaluate((canvas) => canvas.toDataURL("image/png"));
    if (!posterDataUrl.startsWith("data:image/png;base64,")) {
      throw new Error("Poster export did not return a PNG data URL from the 1920x1080 Canvas.");
    }
    await writeFile(poster, Buffer.from(posterDataUrl.split(",", 2)[1], "base64"));
    await context.close();

    const errors = uniqueErrors(browserErrors);
    if (errors.length) {
      throw new Error(`Browser errors were recorded:\n${errors.join("\n")}`);
    }
    const rawInformation = await stat(rawWebm);
    if (rawInformation.size < 500000) {
      throw new Error(`The real browser recording is only ${rawInformation.size} bytes.`);
    }
    const rawSummary = summarizeMedia(probeMedia(ffprobe, rawWebm));
    if (!rawSummary.videoCodec || rawSummary.width !== VIDEO_WIDTH || rawSummary.height !== VIDEO_HEIGHT) {
      throw new Error(
        `Raw browser recording is not a ${VIDEO_WIDTH}x${VIDEO_HEIGHT} video stream: ` +
        JSON.stringify(rawSummary)
      );
    }
    // Chrome's MediaRecorder sometimes leaves the WebM segment duration unset.
    // A missing raw-container duration is not accepted as proof. The published
    // encodes below must still match the declared timeline within 0.2 seconds,
    // include the required streams, and pass strict full decoding.
    if (
      rawSummary.durationSeconds > 0 &&
      (
        rawSummary.durationSeconds < MIN_DURATION_SECONDS - 1 ||
        rawSummary.durationSeconds > MAX_DURATION_SECONDS + 3
      )
    ) {
      throw new Error(`Raw browser recording duration is ${rawSummary.durationSeconds} seconds.`);
    }

    transcodeVideos(ffmpeg, rawWebm, webm, mp4, contract.durationSeconds);
    const webmSummary = summarizeMedia(probeMedia(ffprobe, webm));
    const mp4Summary = summarizeMedia(probeMedia(ffprobe, mp4));
    validateVideo(webmSummary, "WebM", {
      durationSeconds: contract.durationSeconds,
      videoCodec: "vp8",
      audioCodec: "opus"
    });
    validateVideo(mp4Summary, "MP4", {
      durationSeconds: contract.durationSeconds,
      videoCodec: "h264",
      audioCodec: "aac"
    });
    run(
      ffmpeg,
      ["-hide_banner", "-loglevel", "error", "-xerror", "-i", webm, "-f", "null", "-"],
      "WebM strict full decode"
    );
    run(
      ffmpeg,
      ["-hide_banner", "-loglevel", "error", "-xerror", "-i", mp4, "-f", "null", "-"],
      "MP4 strict full decode"
    );
    makeContactSheet(ffmpeg, mp4, contactSheet, framesDirectory, contract.timeline);

    const posterSummary = summarizeMedia(probeMedia(ffprobe, poster));
    if (posterSummary.width !== VIDEO_WIDTH || posterSummary.height !== VIDEO_HEIGHT) {
      throw new Error(`Poster is ${posterSummary.width}x${posterSummary.height}; expected 1920x1080.`);
    }
    const contactSummary = summarizeMedia(probeMedia(ffprobe, contactSheet));
    if (contactSummary.width < 2200 || contactSummary.height < 700) {
      throw new Error(
        `Contact sheet is unexpectedly small at ${contactSummary.width}x${contactSummary.height}.`
      );
    }
    const sourceSha256AtPublish = await sha256(sourcePath);
    if (sourceSha256AtPublish !== sourceSha256AtStart) {
      throw new Error(
        `Showcase source changed during export: ${sourceSha256AtStart} -> ${sourceSha256AtPublish}.`
      );
    }

    const evidence = {
      recordType: "loop_engine_showcase_media_evidence/v2",
      generatedAt: new Date().toISOString(),
      recordingMode: "?record=1",
      exclusiveWriter: true,
      frozenSource: {
        file: "showcase-data.js",
        sha256: sourceSha256AtPublish,
        expectedSha256: expectedSourceSha256 || null,
        unchangedDuringExport: true
      },
      rawCapture: {
        ...rawSummary,
        containerDurationDeclared: rawSummary.durationSeconds > 0
      },
      sourceSha256: await sourceHashes(),
      browser: {
        executable: basename(browserExecutable),
        errors
      },
      tools: {
        playwrightCore: "1.62.1",
        ffmpegStatic: "5.3.0",
        ffprobeStatic: "3.1.0"
      },
      timeline: {
        scenes: EXPECTED_SCENES,
        durationSeconds: contract.durationSeconds,
        framesPerSecond: VIDEO_FRAME_RATE,
        expectedFrames: Math.round(contract.durationSeconds * VIDEO_FRAME_RATE),
        audio: "silent",
        sceneSamples: contract.timeline
      },
      outputs: {
        webm: {
          file: "loop-engine-architecture.webm",
          ...webmSummary,
          ...await fileEvidence(webm),
          fullDecodePassed: true
        },
        mp4: {
          file: "loop-engine-architecture.mp4",
          ...mp4Summary,
          ...await fileEvidence(mp4),
          fullDecodePassed: true
        },
        poster: {
          file: "poster.png",
          width: posterSummary.width,
          height: posterSummary.height,
          ...await fileEvidence(poster),
          sourceScene: 1
        },
        contactSheet: {
          file: "contact-sheet.png",
          width: contactSummary.width,
          height: contactSummary.height,
          ...await fileEvidence(contactSheet),
          frames: EXPECTED_SCENES,
          sampleRule: "one midpoint frame extracted from the encoded MP4 for every timed slide"
        }
      }
    };
    await writeFile(evidencePath, `${JSON.stringify(evidence, null, 2)}\n`, "utf8");

    const finalNames = [
      "loop-engine-architecture.webm",
      "loop-engine-architecture.mp4",
      "poster.png",
      "contact-sheet.png"
    ];
    for (const name of finalNames) {
      await publish(join(stagingDirectory, name), join(assetsDirectory, name));
    }
    await publish(evidencePath, join(assetsDirectory, "media-evidence.json"));
    process.stdout.write(`${JSON.stringify({
      ok: true,
      evidence: join(assetsDirectory, "media-evidence.json"),
      durationSeconds: contract.durationSeconds,
      scenes: EXPECTED_SCENES,
      outputs: evidence.outputs
    }, null, 2)}\n`);
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    if (stagingDirectory) {
      await rm(stagingDirectory, { recursive: true, force: true });
    }
    await releaseExclusiveWriter(writer);
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
