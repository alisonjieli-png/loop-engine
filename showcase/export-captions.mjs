#!/usr/bin/env node

import { mkdir, rename, rm, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { showcaseData } from "./showcase-data.js";
import { EXPECTED_SCENES, argument } from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultOutput = join(scriptDirectory, "assets", "loop-engine-showcase.srt");

function timestamp(milliseconds) {
  const total = Math.max(0, Math.round(milliseconds));
  const hours = Math.floor(total / 3_600_000);
  const minutes = Math.floor((total % 3_600_000) / 60_000);
  const seconds = Math.floor((total % 60_000) / 1_000);
  const remainder = total % 1_000;
  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, "0"))
    .join(":") + `,${String(remainder).padStart(3, "0")}`;
}

function clean(value) {
  return String(value || "").replaceAll("\r", "").trim();
}

function buildCaptions(slides) {
  if (!Array.isArray(slides) || slides.length !== EXPECTED_SCENES) {
    throw new Error(`Expected ${EXPECTED_SCENES} slides, found ${slides?.length || 0}.`);
  }
  let cursor = 0;
  const entries = slides.map((slide, index) => {
    const duration = Number(slide.durationSeconds) * 1_000;
    if (!Number.isFinite(duration) || duration <= 0) {
      throw new Error(`Slide ${index + 1} has an invalid duration.`);
    }
    const start = cursor;
    const end = start + duration;
    cursor = end;
    const lines = [clean(slide.title), clean(slide.caption)].filter(Boolean);
    if (!lines.length) {
      throw new Error(`Slide ${index + 1} has no caption text.`);
    }
    return `${index + 1}\n${timestamp(start)} --> ${timestamp(end)}\n${lines.join("\n")}\n`;
  });
  return { body: `${entries.join("\n")}\n`, durationMilliseconds: Math.round(cursor) };
}

async function main() {
  const output = resolve(argument("--output", defaultOutput));
  const temporary = `${output}.tmp-${process.pid}`;
  const { body, durationMilliseconds } = buildCaptions(showcaseData.slides);
  await mkdir(dirname(output), { recursive: true });
  await rm(temporary, { force: true });
  try {
    await writeFile(temporary, body, "utf8");
    await rename(temporary, output);
  } finally {
    await rm(temporary, { force: true });
  }
  process.stdout.write(`${JSON.stringify({
    ok: true,
    output,
    captions: showcaseData.slides.length,
    durationSeconds: durationMilliseconds / 1_000
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
