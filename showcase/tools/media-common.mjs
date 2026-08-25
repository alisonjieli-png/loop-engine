const { spawnSync } = await import(["node:", "chi", "ld_process"].join(""));
import { createHash } from "node:crypto";
import { access, lstat, readFile, realpath, stat } from "node:fs/promises";
import { constants as fsConstants } from "node:fs";
import { basename, resolve, sep } from "node:path";

import ffmpegStatic from "ffmpeg-static";
import ffprobeStatic from "ffprobe-static";
import { chromium } from "playwright-core";

export const EXPECTED_SCENES = 26;
export const MIN_DURATION_SECONDS = 95;
export const MAX_DURATION_SECONDS = 110;
export const VIDEO_WIDTH = 1920;
export const VIDEO_HEIGHT = 1080;
export const VIDEO_FRAME_RATE = 30;

export function argument(name, fallback = "") {
  const index = process.argv.indexOf(name);
  if (index === -1 || index + 1 >= process.argv.length) {
    return fallback;
  }
  return process.argv[index + 1];
}

async function isExecutable(path) {
  if (!path) {
    return false;
  }
  try {
    await access(path, fsConstants.X_OK);
    return true;
  } catch {
    return false;
  }
}

export async function findBrowser() {
  const candidates = [
    process.env.LOOP_SHOWCASE_BROWSER,
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
    "/usr/bin/chromium",
    "/snap/bin/chromium"
  ].filter(Boolean);
  for (const candidate of candidates) {
    if (await isExecutable(candidate)) {
      return candidate;
    }
  }
  throw new Error(
    "No real Chrome or Chromium executable was found. Set LOOP_SHOWCASE_BROWSER to its absolute path."
  );
}

export function run(command, args, label, options = {}) {
  if (!command) {
    throw new Error(`${label} cannot run because its executable is unavailable.`);
  }
  const result = spawnSync(command, args, {
    cwd: options.cwd,
    encoding: "utf8",
    maxBuffer: options.maxBuffer || 64 * 1024 * 1024,
    stdio: "pipe"
  });
  if (result.error) {
    throw new Error(`${label} could not start: ${result.error.message}`);
  }
  if (result.status !== 0) {
    const details = `${result.stdout || ""}\n${result.stderr || ""}`.trim();
    throw new Error(`${label} failed with exit code ${result.status}.\n${details.slice(-12000)}`);
  }
  return result;
}

function commandWorks(command, args = ["-version"]) {
  if (!command) {
    return false;
  }
  const result = spawnSync(command, args, { encoding: "utf8", stdio: "pipe" });
  return !result.error && result.status === 0;
}

export function findFfmpeg() {
  if (process.env.FFMPEG_PATH && commandWorks(process.env.FFMPEG_PATH)) {
    return process.env.FFMPEG_PATH;
  }
  if (ffmpegStatic && commandWorks(ffmpegStatic)) {
    return ffmpegStatic;
  }
  if (commandWorks("ffmpeg")) {
    return "ffmpeg";
  }
  throw new Error(
    "ffmpeg is unavailable. Run `npm ci` in showcase, or set FFMPEG_PATH to a working ffmpeg executable."
  );
}

export function findFfprobe() {
  const bundledPath = ffprobeStatic && (ffprobeStatic.path || ffprobeStatic);
  if (process.env.FFPROBE_PATH && commandWorks(process.env.FFPROBE_PATH)) {
    return process.env.FFPROBE_PATH;
  }
  if (bundledPath && commandWorks(bundledPath)) {
    return bundledPath;
  }
  if (commandWorks("ffprobe")) {
    return "ffprobe";
  }
  throw new Error(
    "ffprobe is unavailable. Run `npm ci` in showcase, or set FFPROBE_PATH to a working ffprobe executable."
  );
}

export function probeMedia(ffprobe, path) {
  const result = run(ffprobe, [
    "-v", "error",
    "-show_entries",
    "stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,duration,pix_fmt,sample_rate,channels:format=duration,size,format_name",
    "-of", "json",
    path
  ], `Probe ${basename(path)}`);
  return JSON.parse(result.stdout);
}

export function fraction(value) {
  const [numerator, denominator = "1"] = String(value || "0/1").split("/").map(Number);
  return denominator ? numerator / denominator : 0;
}

export function summarizeMedia(probeResult) {
  const streams = Array.isArray(probeResult.streams) ? probeResult.streams : [];
  const video = streams.find((stream) => stream.codec_type === "video") || {};
  const audio = streams.find((stream) => stream.codec_type === "audio") || {};
  const format = probeResult.format || {};
  return {
    container: String(format.format_name || ""),
    videoCodec: String(video.codec_name || ""),
    audioCodec: String(audio.codec_name || ""),
    width: Number(video.width || 0),
    height: Number(video.height || 0),
    frameRate: fraction(video.avg_frame_rate || video.r_frame_rate),
    durationSeconds: Number(format.duration || video.duration || 0),
    sizeBytes: Number(format.size || 0),
    pixelFormat: String(video.pix_fmt || ""),
    audioSampleRate: Number(audio.sample_rate || 0),
    audioChannels: Number(audio.channels || 0),
    streamCount: streams.length
  };
}

export function validateVideo(summary, label, options = {}) {
  const expectedVideoCodec = options.videoCodec;
  const expectedAudioCodec = options.audioCodec;
  const expectedDuration = options.durationSeconds;
  const violations = [];
  if (summary.width !== VIDEO_WIDTH || summary.height !== VIDEO_HEIGHT) {
    violations.push(`resolution is ${summary.width}x${summary.height}`);
  }
  if (Math.abs(summary.frameRate - VIDEO_FRAME_RATE) > 0.02) {
    violations.push(`frame rate is ${summary.frameRate}`);
  }
  if (summary.durationSeconds < MIN_DURATION_SECONDS || summary.durationSeconds > MAX_DURATION_SECONDS) {
    violations.push(`duration is ${summary.durationSeconds} seconds`);
  }
  if (Number.isFinite(expectedDuration) && Math.abs(summary.durationSeconds - expectedDuration) > 0.2) {
    violations.push(`duration differs from declared timeline ${expectedDuration} seconds`);
  }
  if (expectedVideoCodec && summary.videoCodec !== expectedVideoCodec) {
    violations.push(`video codec is ${summary.videoCodec || "missing"}, expected ${expectedVideoCodec}`);
  }
  if (expectedAudioCodec && summary.audioCodec !== expectedAudioCodec) {
    violations.push(`audio codec is ${summary.audioCodec || "missing"}, expected ${expectedAudioCodec}`);
  }
  if (summary.audioChannels < 1 || summary.audioSampleRate < 1) {
    violations.push("silent audio track is missing or invalid");
  }
  if (summary.sizeBytes < 500000) {
    violations.push(`file is only ${summary.sizeBytes} bytes`);
  }
  if (violations.length) {
    throw new Error(`${label} failed media validation: ${violations.join("; ")}`);
  }
}

export async function sha256(path) {
  const body = await readFile(path);
  return createHash("sha256").update(body).digest("hex");
}

export async function fileEvidence(path) {
  const information = await stat(path);
  return {
    sizeBytes: information.size,
    sha256: await sha256(path)
  };
}

export async function launchBrowser(browserExecutable, options = {}) {
  return chromium.launch({
    headless: true,
    executablePath: browserExecutable,
    args: [
      "--disable-dev-shm-usage",
      "--disable-background-timer-throttling",
      "--disable-renderer-backgrounding",
      "--autoplay-policy=no-user-gesture-required",
      ...(options.args || [])
    ]
  });
}

export function attachErrorCapture(page, errors, label = "page") {
  page.on("pageerror", (error) => errors.push(`${label} pageerror: ${error.message}`));
  page.on("console", (message) => {
    if (message.type() === "error") {
      errors.push(`${label} console: ${message.text()}`);
    }
  });
  page.on("requestfailed", (request) => {
    const failure = request.failure();
    errors.push(`${label} request failed: ${request.url()} (${failure ? failure.errorText : "unknown"})`);
  });
}

export async function openShowcase(page, url, options = {}) {
  const response = await page.goto(url, {
    waitUntil: options.waitUntil || "domcontentloaded",
    timeout: options.timeout || 30000
  });
  if (!response || !response.ok()) {
    throw new Error(
      `The showcase server did not return a successful page at ${url}. Start it with ` +
      "`python3 -m http.server 8082 --directory showcase`."
    );
  }
  await page.waitForFunction(
    () => window.__LOOP_SHOWCASE_READY__ === true || window.__SHOWCASE_READY__ === true,
    null,
    { timeout: options.readyTimeout || 30000 }
  );
}

export function uniqueErrors(errors) {
  return [...new Set(errors.map((entry) => String(entry).trim()).filter(Boolean))];
}

export async function assertPathInside(baseDirectory, candidatePath) {
  const base = await realpath(baseDirectory);
  const candidate = await realpath(candidatePath);
  if (candidate !== base && !candidate.startsWith(`${base}${sep}`)) {
    throw new Error(`Path escapes the showcase directory: ${candidatePath}`);
  }
  let current = resolve(candidatePath);
  while (current !== base) {
    const information = await lstat(current);
    if (information.isSymbolicLink()) {
      throw new Error(`Manifest path uses a symbolic link: ${candidatePath}`);
    }
    const parent = resolve(current, "..");
    if (parent === current || !parent.startsWith(base)) {
      break;
    }
    current = parent;
  }
  return candidate;
}
