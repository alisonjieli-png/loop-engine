#!/usr/bin/env node

import { lstat, mkdir, rename, rm, stat, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { argument, sha256 } from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultOutput = join(scriptDirectory, "artifact-manifest.json");
const includedPaths = [
  "README.md",
  "index.html",
  "styles.css",
  "showcase-data.js",
  "render.js",
  "player.js",
  "record-video.mjs",
  "export-pdf.mjs",
  "export-captions.mjs",
  "build-powerpoint.py",
  "verify-powerpoint.mjs",
  "create-artifact-manifest.mjs",
  "package-showcase.mjs",
  "package.json",
  "package-lock.json",
  "tools/export-slide-data.mjs",
  "tools/media-common.mjs",
  "tests/player-smoke.mjs",
  "tests/visual-audit.mjs",
  "assets/loop-engine-architecture.mp4",
  "assets/loop-engine-architecture.webm",
  "assets/loop-engine-showcase.pptx",
  "assets/loop-engine-showcase.pdf",
  "assets/loop-engine-showcase.srt",
  "assets/poster.png",
  "assets/contact-sheet.png",
  "assets/powerpoint-montage.png",
  "assets/media-evidence.json",
  "assets/powerpoint-verification.json"
];

async function entry(relativePath) {
  const path = join(scriptDirectory, relativePath);
  const information = await lstat(path);
  if (!information.isFile() || information.isSymbolicLink()) {
    throw new Error(`Package input is not a regular non-symlink file: ${relativePath}`);
  }
  return {
    path: relativePath,
    sizeBytes: information.size,
    sha256: await sha256(path)
  };
}

async function main() {
  const output = resolve(argument("--output", defaultOutput));
  const temporary = `${output}.tmp-${process.pid}`;
  const files = [];
  for (const relativePath of includedPaths) {
    files.push(await entry(relativePath));
  }
  const manifest = {
    recordType: "loop_engine_showcase_manifest/v2",
    generatedAt: new Date().toISOString(),
    sourceOfLabels: "showcase-data.js",
    packagePolicy: {
      fixedAllowlist: true,
      excludes: ["node_modules", "temporary files", "raw recordings"]
    },
    files
  };
  await mkdir(dirname(output), { recursive: true });
  await rm(temporary, { force: true });
  try {
    await writeFile(temporary, `${JSON.stringify(manifest, null, 2)}\n`, "utf8");
    await rename(temporary, output);
  } finally {
    await rm(temporary, { force: true });
  }
  const information = await stat(output);
  process.stdout.write(`${JSON.stringify({
    ok: true,
    output,
    files: files.length,
    sizeBytes: information.size,
    sha256: await sha256(output)
  }, null, 2)}\n`);
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
