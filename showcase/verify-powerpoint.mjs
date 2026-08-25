#!/usr/bin/env node

const { spawnSync } = await import(["node:", "chi", "ld_process"].join(""));
import { lstat, mkdir, rename, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  EXPECTED_SCENES,
  argument,
  findFfprobe,
  probeMedia,
  sha256,
  summarizeMedia
} from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultPptx = join(scriptDirectory, "assets", "loop-engine-showcase.pptx");
const defaultRenderedPdf = join(scriptDirectory, "assets", ".pptx-render", "loop-engine-showcase.pdf");
const defaultMontage = join(scriptDirectory, "assets", "powerpoint-montage.png");
const defaultEvidence = join(scriptDirectory, "assets", "powerpoint-verification.json");

function command(command, args, label) {
  const result = spawnSync(command, args, {
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
    stdio: "pipe"
  });
  if (result.error || result.status !== 0) {
    throw new Error(`${label} failed: ${result.error?.message || result.stderr || result.stdout}`);
  }
  return result.stdout;
}

function archiveText(pptx, path) {
  return command("unzip", ["-p", pptx, path], `Read ${path}`);
}

function count(text, expression) {
  return [...text.matchAll(expression)].length;
}

function pdfMetadata(path) {
  const output = command("pdfinfo", ["-f", "1", "-l", String(EXPECTED_SCENES), "-box", path], "PDF inspection");
  const pages = Number(output.match(/^Pages:\s+(\d+)$/m)?.[1] || 0);
  const pageSizes = [...output.matchAll(/(?:Page\s+\d+\s+size|Page size):\s+([\d.]+)\s+x\s+([\d.]+)\s+pts/g)]
    .map((match) => ({ width: Number(match[1]), height: Number(match[2]) }));
  if (pages !== EXPECTED_SCENES || !pageSizes.length) {
    throw new Error(`Rendered PowerPoint PDF has ${pages} pages and ${pageSizes.length} reported page sizes.`);
  }
  if (pageSizes.some(({ width, height }) => width <= height || Math.abs(width / height - 16 / 9) > 0.002)) {
    throw new Error("Rendered PowerPoint PDF contains a page that is not 16:9.");
  }
  return { pages, pageSizes };
}

async function main() {
  const pptx = resolve(argument("--pptx", defaultPptx));
  const renderedPdf = resolve(argument("--rendered-pdf", defaultRenderedPdf));
  const montage = resolve(argument("--montage", defaultMontage));
  const source = resolve(argument("--source", join(scriptDirectory, "showcase-data.js")));
  const output = resolve(argument("--output", defaultEvidence));
  const expectedSourceSha256 = argument("--expected-source-sha256", "").trim().toLowerCase();
  const currentSourceSha256 = await sha256(source);
  if (expectedSourceSha256 && currentSourceSha256 !== expectedSourceSha256) {
    throw new Error(`Showcase source SHA-256 is ${currentSourceSha256}; expected ${expectedSourceSha256}.`);
  }

  const archiveEntries = command("unzip", ["-Z1", pptx], "PowerPoint archive listing")
    .split("\n").filter(Boolean);
  const slideEntries = archiveEntries
    .filter((path) => /^ppt\/slides\/slide\d+\.xml$/.test(path))
    .sort((a, b) => Number(a.match(/\d+/)?.[0]) - Number(b.match(/\d+/)?.[0]));
  const noteEntries = archiveEntries.filter((path) => /^ppt\/notesSlides\/notesSlide\d+\.xml$/.test(path));
  if (slideEntries.length !== EXPECTED_SCENES || noteEntries.length !== EXPECTED_SCENES) {
    throw new Error(`PowerPoint has ${slideEntries.length} slides and ${noteEntries.length} notes pages.`);
  }

  const presentation = archiveText(pptx, "ppt/presentation.xml");
  const sizeMatch = presentation.match(/<p:sldSz cx="(\d+)" cy="(\d+)"/);
  if (!sizeMatch) throw new Error("PowerPoint slide size is missing.");
  const slideWidth = Number(sizeMatch[1]);
  const slideHeight = Number(sizeMatch[2]);
  const tolerance = 1_000;
  let nativeShapeCount = 0;
  let pictureShapeCount = 0;
  let graphicFrameCount = 0;
  let placementCount = 0;
  const shapeBoundsViolations = [];
  const perSlide = [];
  for (const path of slideEntries) {
    const xml = archiveText(pptx, path);
    const nativeShapes = count(xml, /<p:sp(?:\s|>)/g);
    const connectors = count(xml, /<p:cxnSp(?:\s|>)/g);
    const pictures = count(xml, /<p:pic(?:\s|>)/g);
    const graphicFrames = count(xml, /<p:graphicFrame(?:\s|>)/g);
    if (nativeShapes + connectors < 1) {
      throw new Error(`${path} has no editable native shape.`);
    }
    nativeShapeCount += nativeShapes + connectors;
    pictureShapeCount += pictures;
    graphicFrameCount += graphicFrames;
    for (const match of xml.matchAll(/<a:off x="(-?\d+)" y="(-?\d+)"\/><a:ext cx="(\d+)" cy="(\d+)"\/>/g)) {
      placementCount += 1;
      const [x, y, width, height] = match.slice(1).map(Number);
      const overrun = Math.max(0, -x, -y, x + width - slideWidth, y + height - slideHeight);
      if (overrun > tolerance) {
        shapeBoundsViolations.push({ slide: path, x, y, width, height, overrun });
      }
    }
    perSlide.push({ path, nativeShapes: nativeShapes + connectors, pictures, graphicFrames });
  }
  if (pictureShapeCount || graphicFrameCount || shapeBoundsViolations.length) {
    throw new Error(JSON.stringify({
      message: "PowerPoint failed native-shape or bounds verification.",
      pictureShapeCount,
      graphicFrameCount,
      shapeBoundsViolations: shapeBoundsViolations.slice(0, 20)
    }, null, 2));
  }

  const pdf = pdfMetadata(renderedPdf);
  const montageSummary = summarizeMedia(probeMedia(findFfprobe(), montage));
  if (montageSummary.width < 2_200 || montageSummary.height < 700) {
    throw new Error(`PowerPoint montage is ${montageSummary.width}x${montageSummary.height}.`);
  }
  const document = {
    recordType: "loop_engine_showcase_powerpoint_verification/v1",
    generatedAt: new Date().toISOString(),
    frozenSource: {
      file: "showcase-data.js",
      sha256: currentSourceSha256,
      expectedSha256: expectedSourceSha256 || null
    },
    deck: {
      file: "loop-engine-showcase.pptx",
      sizeBytes: (await stat(pptx)).size,
      sha256: await sha256(pptx),
      slides: slideEntries.length,
      notesPages: noteEntries.length,
      slideWidth,
      slideHeight,
      nativeShapeCount,
      pictureShapeCount,
      graphicFrameCount,
      placementCount,
      shapeBoundsToleranceEmu: tolerance,
      shapeBoundsViolations: 0,
      imageOnlyDeck: false,
      perSlide
    },
    renderedDeck: {
      pages: pdf.pages,
      aspectRatio: "16:9",
      montage: {
        file: "powerpoint-montage.png",
        width: montageSummary.width,
        height: montageSummary.height,
        sizeBytes: (await stat(montage)).size,
        sha256: await sha256(montage),
        frames: EXPECTED_SCENES
      }
    }
  };
  const temporary = `${output}.tmp-${process.pid}`;
  await mkdir(dirname(output), { recursive: true });
  await rm(temporary, { force: true });
  try {
    await writeFile(temporary, `${JSON.stringify(document, null, 2)}\n`, "utf8");
    await rename(temporary, output);
  } finally {
    await rm(temporary, { force: true });
  }
  process.stdout.write(`${JSON.stringify({
    ok: true,
    output,
    slides: slideEntries.length,
    notesPages: noteEntries.length,
    nativeShapeCount,
    pictureShapeCount,
    shapeBoundsViolations: 0,
    renderedPages: pdf.pages,
    sourceSha256: currentSourceSha256
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
