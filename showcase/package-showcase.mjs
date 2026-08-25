#!/usr/bin/env node

const { spawnSync } = await import(["node:", "chi", "ld_process"].join(""));
import { lstat, readFile, rename, rm, stat } from "node:fs/promises";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import {
  argument,
  assertPathInside,
  run,
  sha256
} from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultManifest = join(scriptDirectory, "artifact-manifest.json");
const defaultOutput = join(scriptDirectory, "assets", "loop-engine-showcase-complete.zip");

function findZip() {
  const candidates = [process.env.ZIP_PATH, "zip"].filter(Boolean);
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["-v"], { encoding: "utf8", stdio: "pipe" });
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }
  throw new Error("zip is unavailable. Install the zip command or set ZIP_PATH.");
}

function validateEntryShape(entry, index) {
  if (!entry || typeof entry !== "object" || Array.isArray(entry)) {
    throw new Error(`Manifest file entry ${index + 1} is not an object.`);
  }
  if (typeof entry.path !== "string" || !entry.path.trim()) {
    throw new Error(`Manifest file entry ${index + 1} has no relative path.`);
  }
  if (!Number.isSafeInteger(entry.sizeBytes) || entry.sizeBytes < 1) {
    throw new Error(`Manifest file entry ${entry.path} has no positive integer sizeBytes.`);
  }
  if (typeof entry.sha256 !== "string" || !/^[0-9a-f]{64}$/i.test(entry.sha256)) {
    throw new Error(`Manifest file entry ${entry.path} has no valid SHA-256 digest.`);
  }
  const normalized = entry.path.replaceAll("\\", "/");
  if (
    isAbsolute(entry.path) ||
    normalized.startsWith("-") ||
    normalized.split("/").some((part) => part === ".." || part === "")
  ) {
    throw new Error(`Manifest path is unsafe: ${entry.path}`);
  }
  return { ...entry, path: normalized };
}

async function verifyManifest(manifestPath, output) {
  let document;
  try {
    document = JSON.parse(await readFile(manifestPath, "utf8"));
  } catch (error) {
    if (error.code === "ENOENT") {
      throw new Error(
        `Artifact manifest is missing at ${manifestPath}. Packaging cannot infer or invent its contents.`
      );
    }
    throw new Error(`Artifact manifest is not valid JSON: ${error.message}`);
  }
  if (document.recordType !== "loop_engine_showcase_manifest/v2") {
    throw new Error(
      `Manifest recordType is ${JSON.stringify(document.recordType)}; expected "loop_engine_showcase_manifest/v2".`
    );
  }
  if (!Array.isArray(document.files) || !document.files.length) {
    throw new Error("Artifact manifest must contain a non-empty files array.");
  }
  const entries = document.files.map(validateEntryShape);
  const seen = new Set();
  const outputPath = resolve(output);
  for (const entry of entries) {
    if (seen.has(entry.path)) {
      throw new Error(`Artifact manifest repeats ${entry.path}.`);
    }
    seen.add(entry.path);
    const path = resolve(scriptDirectory, entry.path);
    if (path === outputPath) {
      throw new Error("The package archive cannot list itself in the artifact manifest.");
    }
    if (path !== scriptDirectory && !path.startsWith(`${scriptDirectory}${sep}`)) {
      throw new Error(`Manifest path escapes the showcase directory: ${entry.path}`);
    }
    await assertPathInside(scriptDirectory, path);
    const information = await lstat(path);
    if (!information.isFile() || information.isSymbolicLink()) {
      throw new Error(`Manifest path is not a regular non-symlink file: ${entry.path}`);
    }
    if (information.size !== entry.sizeBytes) {
      throw new Error(
        `Size mismatch for ${entry.path}: manifest ${entry.sizeBytes}, current ${information.size}.`
      );
    }
    const digest = await sha256(path);
    if (digest.toLowerCase() !== entry.sha256.toLowerCase()) {
      throw new Error(`SHA-256 mismatch for ${entry.path}.`);
    }
  }
  return { document, entries };
}

async function main() {
  const manifestPath = resolve(argument("--manifest", defaultManifest));
  const output = resolve(argument("--output", defaultOutput));
  if (manifestPath !== scriptDirectory && !manifestPath.startsWith(`${scriptDirectory}${sep}`)) {
    throw new Error("The artifact manifest must be inside showcase.");
  }
  const zip = findZip();
  const { entries } = await verifyManifest(manifestPath, output);
  const relativeManifest = relative(scriptDirectory, manifestPath).replaceAll("\\", "/");
  const temporary = join(dirname(output), `.showcase-package-${process.pid}.zip`);
  await rm(temporary, { force: true });
  try {
    run(
      zip,
      ["-X", "-q", temporary, relativeManifest, ...entries.map((entry) => entry.path)],
      "Showcase package creation",
      { cwd: scriptDirectory }
    );
    run(zip, ["-T", temporary], "Showcase ZIP integrity test", { cwd: scriptDirectory });
    const information = await stat(temporary);
    if (information.size < 1000000) {
      throw new Error(`Showcase package is only ${information.size} bytes; refusing to publish it.`);
    }
    await rename(temporary, output);
    process.stdout.write(`${JSON.stringify({
      ok: true,
      output,
      files: entries.length + 1,
      sizeBytes: information.size,
      sha256: await sha256(output),
      manifest: relativeManifest
    }, null, 2)}\n`);
  } finally {
    await rm(temporary, { force: true });
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
