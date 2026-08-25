#!/usr/bin/env node

const { spawnSync } = await import(["node:", "chi", "ld_process"].join(""));
import { open } from "node:fs/promises";
import { mkdir, mkdtemp, readFile, rename, rm, stat, unlink } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  EXPECTED_SCENES,
  argument,
  attachErrorCapture,
  findBrowser,
  launchBrowser,
  openShowcase,
  run,
  uniqueErrors
} from "./tools/media-common.mjs";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const defaultOutput = join(scriptDirectory, "assets", "loop-engine-showcase.pdf");
const lockPath = join(scriptDirectory, ".pdf-export.lock");

async function acquireLock() {
  try {
    const handle = await open(lockPath, "wx", 0o600);
    await handle.writeFile(`${JSON.stringify({
      pid: process.pid,
      startedAt: new Date().toISOString(),
      command: "export-pdf.mjs"
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
      // The exclusive-writer refusal remains exact without the optional detail.
    }
    throw new Error(`A PDF exporter already owns ${lockPath}.\n${owner}`);
  }
}

async function releaseLock(handle) {
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

function findPdfinfo() {
  const candidates = [process.env.PDFINFO_PATH, "pdfinfo"].filter(Boolean);
  for (const candidate of candidates) {
    const result = spawnSync(candidate, ["-v"], { encoding: "utf8", stdio: "pipe" });
    if (!result.error && result.status === 0) {
      return candidate;
    }
  }
  throw new Error(
    "pdfinfo is unavailable. Install Poppler's pdfinfo command or set PDFINFO_PATH before exporting the PDF."
  );
}

function validatePdf(pdfinfo, path) {
  const result = run(
    pdfinfo,
    ["-f", "1", "-l", String(EXPECTED_SCENES), "-box", path],
    "PDF metadata verification"
  );
  const output = `${result.stdout}\n${result.stderr}`;
  const pagesMatch = output.match(/^Pages:\s+(\d+)$/m);
  const pages = pagesMatch ? Number(pagesMatch[1]) : 0;
  if (pages !== EXPECTED_SCENES) {
    throw new Error(`PDF has ${pages || "an unknown number of"} pages; expected ${EXPECTED_SCENES}.`);
  }
  const pageSizes = [...output.matchAll(/(?:Page\s+\d+\s+size|Page size):\s+([\d.]+)\s+x\s+([\d.]+)\s+pts/g)]
    .map((match) => ({ width: Number(match[1]), height: Number(match[2]) }));
  if (!pageSizes.length) {
    throw new Error("pdfinfo did not report a page size for the exported deck.");
  }
  const wrongSize = pageSizes.find(
    ({ width, height }) => Math.abs(width / height - 16 / 9) > 0.002 || width <= height
  );
  if (wrongSize) {
    throw new Error(`PDF page is ${wrongSize.width} by ${wrongSize.height} points, not 16:9.`);
  }
  return { pages, pageSizes };
}

async function main() {
  const lock = await acquireLock();
  let stagingDirectory = "";
  let browser;
  try {
    const baseUrl = argument("--base-url", "http://127.0.0.1:8082").replace(/\/$/, "");
    const output = resolve(argument("--output", defaultOutput));
    const browserExecutable = await findBrowser();
    const pdfinfo = findPdfinfo();
    await mkdir(dirname(output), { recursive: true });
    stagingDirectory = await mkdtemp(join(dirname(output), ".pdf-staging-"));
    const stagingPdf = join(stagingDirectory, "loop-engine-showcase.pdf");
    const errors = [];

    browser = await launchBrowser(browserExecutable);
    const context = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
      deviceScaleFactor: 1,
      colorScheme: "light",
      reducedMotion: "reduce"
    });
    const page = await context.newPage();
    attachErrorCapture(page, errors, "PDF");
    await openShowcase(page, `${baseUrl}/?print=1`, { waitUntil: "networkidle", readyTimeout: 45000 });
    await page.emulateMedia({ media: "print", reducedMotion: "reduce" });
    const printContract = await page.evaluate(() => ({
      exposedScenes: Number(
        window.__LOOP_SHOWCASE_SCENE_COUNT__ ?? window.__showcase?.slides?.length ?? 0
      ),
      printPages: document.querySelectorAll("[data-print-slide], .print-slide, .print-page").length,
      horizontalOverflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
    }));
    if (printContract.exposedScenes !== EXPECTED_SCENES) {
      throw new Error(
        `Print mode exposes ${printContract.exposedScenes} scenes; expected ${EXPECTED_SCENES}.`
      );
    }
    if (printContract.printPages !== EXPECTED_SCENES) {
      throw new Error(
        `Print mode rendered ${printContract.printPages} slide pages; expected ${EXPECTED_SCENES}.`
      );
    }
    if (printContract.horizontalOverflow) {
      throw new Error("Print mode has horizontal document overflow.");
    }
    await page.pdf({
      path: stagingPdf,
      printBackground: true,
      width: "13.333333in",
      height: "7.5in",
      margin: { top: "0", right: "0", bottom: "0", left: "0" },
      preferCSSPageSize: true,
      tagged: true,
      outline: true
    });
    await context.close();
    const browserErrors = uniqueErrors(errors);
    if (browserErrors.length) {
      throw new Error(`Browser errors were recorded during PDF export:\n${browserErrors.join("\n")}`);
    }
    const information = await stat(stagingPdf);
    if (information.size < 100000) {
      throw new Error(`PDF is only ${information.size} bytes; refusing to publish it.`);
    }
    const verification = validatePdf(pdfinfo, stagingPdf);
    await rename(stagingPdf, output);
    process.stdout.write(`${JSON.stringify({
      ok: true,
      output,
      sizeBytes: information.size,
      pages: verification.pages,
      aspectRatio: "16:9"
    }, null, 2)}\n`);
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    if (stagingDirectory) {
      await rm(stagingDirectory, { recursive: true, force: true });
    }
    await releaseLock(lock);
  }
}

main().catch((error) => {
  process.stderr.write(`${error.stack || error.message || error}\n`);
  process.exitCode = 1;
});
