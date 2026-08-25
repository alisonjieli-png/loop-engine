#!/usr/bin/env node

import fs from "node:fs";
import vm from "node:vm";
import { pathToFileURL } from "node:url";

const [sourcePath, outputPath] = process.argv.slice(2);

if (!sourcePath || !outputPath) {
  throw new Error("usage: node tools/export-slide-data.mjs <showcase-data.js> <output.json>");
}

function pickData(moduleValue) {
  const direct = [
    moduleValue?.showcaseData,
    moduleValue?.SHOWCASE_DATA,
    moduleValue?.slides,
    moduleValue?.scenes,
    moduleValue?.default,
  ];
  for (const value of direct) {
    if (value && (Array.isArray(value) || typeof value === "object")) return value;
  }
  return null;
}

async function loadData() {
  try {
    const imported = await import(`${pathToFileURL(sourcePath).href}?pptx=${Date.now()}`);
    const value = pickData(imported);
    if (value) return value;
  } catch {
    // Browser-only data files are handled below without modifying the source file.
  }

  let source = fs.readFileSync(sourcePath, "utf8");
  source = source
    .replace(/^\s*export\s+default\s+/gm, "globalThis.__defaultExport = ")
    .replace(/^\s*export\s+(?=(?:const|let|var|class|function)\s+)/gm, "");
  source += `\n;globalThis.__pptxData =
    typeof showcaseData !== "undefined" ? showcaseData :
    typeof SHOWCASE_DATA !== "undefined" ? SHOWCASE_DATA :
    typeof slides !== "undefined" ? slides :
    typeof scenes !== "undefined" ? scenes :
    globalThis.__defaultExport;
  `;
  const context = { console };
  context.globalThis = context;
  context.window = context;
  vm.createContext(context);
  vm.runInContext(source, context, { filename: sourcePath });
  return context.__pptxData;
}

const data = await loadData();
if (!data) throw new Error(`No showcase data export was found in ${sourcePath}`);
fs.writeFileSync(outputPath, `${JSON.stringify(data, null, 2)}\n`, "utf8");
