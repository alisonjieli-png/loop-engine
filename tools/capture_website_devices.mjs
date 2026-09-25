/* Responsive lab for the Baltor website. Read-only: it loads signed-out pages, scrolls, opens the phone menu, the
   disclosures and the tab sets, takes screenshots and measures layout. It submits no form, signs in to nothing and
   sends no credential. Screenshots stay outside the repository; the metrics record is written once under a new name.

   node tools/capture_website_devices.mjs --base ORIGIN --out NEW_SCREENSHOT_FOLDER --metrics NEW_METRICS_JSON
     [--hosts ORIGIN,ORIGIN] [--devices id,id] [--pages /,/pricing] [--page-set release_20|target_site_map|all]
     [--engines chromium,webkit,firefox] [--concurrency 2] [--no-scroll-shots] [--no-full-page] [--compare OLD_METRICS_JSON]
   node tools/capture_website_devices.mjs --benchmark URL,URL --out NEW_FOLDER --metrics NEW_JSON [--devices id,id]

   The device list, budgets and thresholds are in tools/website_devices.json. The guide is docs/guides/website-responsive-lab.md. */
import {chromium, firefox, webkit} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync, writeFileSync, existsSync, mkdirSync, readdirSync} from "node:fs";
import {resolve, dirname, join, relative} from "node:path";
import {execFileSync} from "node:child_process";
import {createHash} from "node:crypto";

const repoRoot = resolve(dirname(new URL(import.meta.url).pathname), "..");
const deviceListPath = resolve(repoRoot, "tools/website_devices.json");
const deviceList = JSON.parse(readFileSync(deviceListPath, "utf8"));
if (deviceList.record_type !== "website_device_list/v1") throw new Error("Unsupported device list version.");

/* Command line. */
const argv = process.argv.slice(2);
const option = (name, fallback = null) => { const at = argv.indexOf("--" + name); return at >= 0 && at + 1 < argv.length ? argv[at + 1] : fallback; };
const flag = name => argv.includes("--" + name);
const list = value => (value || "").split(",").map(item => item.trim()).filter(Boolean);
const base = option("base");
const benchmark = list(option("benchmark"));
const outRoot = option("out") ? resolve(option("out")) : null;
const metricsPath = option("metrics") ? resolve(option("metrics")) : null;
if ((!base && !benchmark.length) || !outRoot || !metricsPath) {
  throw new Error("Use --base ORIGIN (or --benchmark URL,URL), --out NEW_FOLDER and --metrics NEW_JSON. See the header of this file.");
}
for (const url of [base, ...list(option("hosts")), ...benchmark].filter(Boolean)) {
  const parsed = new URL(url);
  if (!["https:", "http:"].includes(parsed.protocol)) throw new Error("Only http and https addresses are read: " + url);
}
if (existsSync(metricsPath)) throw new Error("Refusing to overwrite an existing metrics record: " + metricsPath);
if (existsSync(outRoot) && readdirSync(outRoot).length) throw new Error("Refusing to reuse a screenshot folder that is not empty: " + outRoot);
mkdirSync(outRoot, {recursive: true});
mkdirSync(dirname(metricsPath), {recursive: true});

const thresholds = deviceList.thresholds;
const budgets = deviceList.budgets;
const concurrency = Math.max(1, Number(option("concurrency", "2")));
const scrollShots = !flag("no-scroll-shots");
const fullPageShots = !flag("no-full-page");

/* Device configurations: every base device on Chromium, then the special cases. */
const baseDevices = new Map(deviceList.devices.map(device => [device.id, device]));
const configurations = [
  ...deviceList.devices.map(device => ({...device, engine: "chromium", base_device: device.id})),
  ...deviceList.special_cases.map(special => {
    const device = baseDevices.get(special.base);
    if (!device) throw new Error("A special case names an unknown base device: " + special.id);
    return {...device, ...special, id: special.id, engine: special.engine || "chromium", base_device: device.id, group: "special case"};
  }),
];
const wantedDevices = list(option("devices"));
const wantedEngines = list(option("engines"));
const selected = configurations.filter(config => (!wantedDevices.length || wantedDevices.includes(config.id) || wantedDevices.includes(config.base_device) && !config.special_case_only)
  && (!wantedEngines.length || wantedEngines.includes(config.engine)));
if (wantedDevices.length) {
  // A named special case is kept only when asked for by its own id, so "--devices phone-390x844" means the plain device.
  for (let index = selected.length - 1; index >= 0; index -= 1) {
    const config = selected[index];
    if (config.group === "special case" && !wantedDevices.includes(config.id)) selected.splice(index, 1);
  }
}
if (!selected.length) throw new Error("No device configuration matches the selection.");

const pageSet = option("page-set", "release_20");
const pagePaths = list(option("pages")).length ? list(option("pages"))
  : pageSet === "all" ? [...deviceList.pages.release_20, ...deviceList.pages.target_site_map] : deviceList.pages[pageSet];
if (!pagePaths) throw new Error("Unknown page set: " + pageSet);

/* The targets: every page on the base origin, the root of every extra hostname, or the benchmark addresses. */
const slug = path => path === "/" ? "home" : path.replace(/^\//, "").replace(/[^a-z0-9._-]+/gi, "-");
const targets = benchmark.length
  ? benchmark.map(url => ({kind: "benchmark", url, page: "bench-" + new URL(url).hostname + (new URL(url).pathname === "/" ? "" : "-" + slug(new URL(url).pathname)), path: new URL(url).pathname}))
  : [...pagePaths.map(path => ({kind: "page", url: new URL(path, base).href, page: slug(path), path})),
     ...list(option("hosts")).map(origin => ({kind: "host-root", url: new URL("/", origin).href, page: "host-" + new URL(origin).hostname, path: "/"}))];

const engines = {chromium, firefox, webkit};
const revision = (() => { try { return execFileSync("git", ["-C", repoRoot, "rev-parse", "HEAD"], {encoding: "utf8"}).trim(); } catch { return null; } })();

/* Everything below runs inside the page. It returns plain data. */
const installObservers = () => {
  window.__lab = {cls: 0, shifts: [], lcp: null, supported: (PerformanceObserver.supportedEntryTypes || []).slice()};
  try {
    new PerformanceObserver(entries => {
      for (const entry of entries.getEntries()) {
        if (entry.hadRecentInput) continue;
        window.__lab.cls += entry.value;
        window.__lab.shifts.push({value: Number(entry.value.toFixed(4)), at_ms: Math.round(entry.startTime), scroll_y: Math.round(scrollY),
          sources: (entry.sources || []).slice(0, 3).map(source => source.node && source.node.nodeType === 1 ? (source.node.id ? "#" + source.node.id : source.node.tagName.toLowerCase() + (source.node.className && typeof source.node.className === "string" ? "." + source.node.className.trim().split(/\s+/).join(".") : "")) : "text")});
      }
    }).observe({type: "layout-shift", buffered: true});
  } catch (error) { window.__lab.layout_shift_unsupported = true; }
  try {
    new PerformanceObserver(entries => {
      const last = entries.getEntries().at(-1);
      if (last) window.__lab.lcp = {at_ms: Math.round(last.startTime), size: last.size,
        element: last.element ? (last.element.id ? "#" + last.element.id : last.element.tagName.toLowerCase() + (typeof last.element.className === "string" && last.element.className ? "." + last.element.className.trim().split(/\s+/).join(".") : "")) : null};
    }).observe({type: "largest-contentful-paint", buffered: true});
  } catch (error) { window.__lab.lcp_unsupported = true; }
};

const measurePage = ({thresholds, budgets, isHome, touch, phone}) => {
  const view = [...document.querySelectorAll("main [data-view]")].find(node => !node.hidden) || document.querySelector("main") || document.body;
  // Content of a closed disclosure keeps layout boxes in some engines, but nobody can see it; only its summary counts.
  const insideClosedDisclosure = node => { const closed = node.closest("details:not([open])"); return !!closed && node !== closed && !node.closest("summary"); };
  const visible = node => { if (!node || !node.getClientRects().length || insideClosedDisclosure(node)) return false; const style = getComputedStyle(node); return style.visibility !== "hidden" && style.display !== "none" && Number(style.opacity) > 0; };
  const describe = node => {
    if (!node || node.nodeType !== 1) return "text";
    const parts = [];
    for (let current = node, depth = 0; current && current.nodeType === 1 && depth < 4; current = current.parentElement, depth += 1) {
      let part = current.tagName.toLowerCase();
      if (current.id) { parts.unshift(part + "#" + current.id); break; }
      if (typeof current.className === "string" && current.className.trim()) part += "." + current.className.trim().split(/\s+/).slice(0, 2).join(".");
      else if (current.dataset && Object.keys(current.dataset).length) { const key = Object.keys(current.dataset)[0]; part += "[data-" + key.replace(/[A-Z]/g, letter => "-" + letter.toLowerCase()) + "]"; }
      parts.unshift(part);
    }
    return parts.join(" > ");
  };
  const text = node => (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim();
  const rect = node => { const box = node.getBoundingClientRect(); return {x: Math.round(box.left), y: Math.round(box.top + scrollY), w: Math.round(box.width), h: Math.round(box.height)}; };
  const width = document.documentElement.clientWidth, height = innerHeight;
  const pageHeight = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight);

  /* Horizontal overflow: the outermost elements that reach past the window, outside any scrolling or clipping box. */
  const clipsX = node => { const value = getComputedStyle(node).overflowX; return value !== "visible"; };
  const offenders = [];
  for (const node of document.body.querySelectorAll("*")) {
    if (!visible(node) || node.closest(".sr-only, [hidden]")) continue;
    const box = node.getBoundingClientRect();
    if (box.right <= width + 1 && box.left >= -1) continue;
    let clipped = false;
    for (let parent = node.parentElement; parent && parent !== document.body; parent = parent.parentElement) if (clipsX(parent)) { clipped = true; break; }
    if (clipped) continue;
    const parent = node.parentElement, parentBox = parent && parent.getBoundingClientRect();
    if (parent && parent !== document.body && (parentBox.right > width + 1 || parentBox.left < -1) && !clipsX(parent)) continue;
    offenders.push({element: describe(node), left: Math.round(box.left), right: Math.round(box.right), width: Math.round(box.width)});
  }

  /* Boxes that clip or scroll their own content. */
  const clippedBoxes = [], scrollRegions = [];
  for (const node of view.querySelectorAll("*")) {
    if (!visible(node)) continue;
    const style = getComputedStyle(node);
    const overX = node.scrollWidth > node.clientWidth + 1, overY = node.scrollHeight > node.clientHeight + 1;
    if (!overX && !overY) continue;
    if (!text(node) || node.closest(".sr-only")) continue;
    if ((overX && ["auto", "scroll"].includes(style.overflowX)) || (overY && ["auto", "scroll"].includes(style.overflowY))) {
      scrollRegions.push({element: describe(node), scroll_width: node.scrollWidth, client_width: node.clientWidth, scroll_height: node.scrollHeight, client_height: node.clientHeight});
    } else if ((overX && ["hidden", "clip"].includes(style.overflowX)) || (overY && ["hidden", "clip"].includes(style.overflowY)) || style.textOverflow === "ellipsis") {
      clippedBoxes.push({element: describe(node), scroll_width: node.scrollWidth, client_width: node.clientWidth, scroll_height: node.scrollHeight, client_height: node.clientHeight});
    }
  }

  /* Text lines, from the rectangles of each text node. */
  const lines = [];
  const walker = document.createTreeWalker(view, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  let textNodeIndex = 0;
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.nodeValue.trim() || !node.parentElement || !visible(node.parentElement) || node.parentElement.closest(".sr-only, [hidden], template, script, style")) continue;
    textNodeIndex += 1;
    range.selectNodeContents(node);
    for (const box of range.getClientRects()) if (box.width > 0.5 && box.height > 0.5) lines.push({id: textNodeIndex, parent: node.parentElement, left: box.left, right: box.right, top: box.top + scrollY, bottom: box.bottom + scrollY});
  }
  const header = document.querySelector("header"), footer = document.querySelector("footer");
  for (const extra of [header, footer]) {
    if (!extra) continue;
    const extraWalker = document.createTreeWalker(extra, NodeFilter.SHOW_TEXT);
    for (let node = extraWalker.nextNode(); node; node = extraWalker.nextNode()) {
      if (!node.nodeValue.trim() || !node.parentElement || !visible(node.parentElement) || node.parentElement.closest(".sr-only, [hidden]")) continue;
      textNodeIndex += 1;
      range.selectNodeContents(node);
      for (const box of range.getClientRects()) if (box.width > 0.5 && box.height > 0.5) lines.push({id: textNodeIndex, parent: node.parentElement, left: box.left, right: box.right, top: box.top + scrollY, bottom: box.bottom + scrollY});
    }
  }

  /* Overlapping text: two different text nodes whose line boxes share more than half of the smaller height. */
  const overlaps = [];
  const sorted = lines.slice().sort((a, b) => a.top - b.top);
  for (let i = 0; i < sorted.length && overlaps.length < 40; i += 1) {
    for (let j = i + 1; j < sorted.length && sorted[j].top < sorted[i].bottom; j += 1) {
      const a = sorted[i], b = sorted[j];
      if (a.id === b.id || a.parent.contains(b.parent) && a.parent === b.parent) continue;
      const overlapX = Math.min(a.right, b.right) - Math.max(a.left, b.left), overlapY = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (overlapX > 2 && overlapY > 0.5 * Math.min(a.bottom - a.top, b.bottom - b.top)) overlaps.push({a: describe(a.parent), b: describe(b.parent), y: Math.round(a.top), overlap_px: [Math.round(overlapX), Math.round(overlapY)]});
    }
  }

  /* Text size: anything under the smallest size, and running text under the phone body size. */
  const smallText = new Map(), smallBody = new Map();
  const bodyTags = new Set(["P", "LI", "DD", "TD", "BLOCKQUOTE", "FIGCAPTION", "SUMMARY"]);
  for (const line of lines) {
    const element = line.parent, style = getComputedStyle(element), size = parseFloat(style.fontSize);
    if (size < thresholds.smallest_text_css_px) smallText.set(element, {element: describe(element), font_px: size, text: text(element).slice(0, 60)});
    const block = element.closest("p, li, dd, td, blockquote, figcaption, summary");
    if (phone && block && bodyTags.has(block.tagName) && text(block).length >= 40 && !block.closest("pre, code, .caption, .badge, .status-tag, .eyebrow, footer, header, .step-demo") && size < thresholds.phone_body_text_css_px) {
      smallBody.set(block, {element: describe(block), font_px: size, characters: text(block).length});
    }
  }

  /* Characters per line for running text. */
  const longLines = [];
  let maxCharactersPerLine = 0;
  for (const block of view.querySelectorAll("p, li, dd, blockquote")) {
    if (!visible(block) || block.closest("pre, nav, .sr-only")) continue;
    const content = text(block);
    if (content.length < 40) continue;
    const tops = [];
    for (const line of lines) if (block.contains(line.parent)) { if (!tops.some(top => Math.abs(top - line.top) < 3)) tops.push(line.top); }
    if (!tops.length) continue;
    const perLine = Math.round(content.length / tops.length);
    maxCharactersPerLine = Math.max(maxCharactersPerLine, perLine);
    if (perLine > thresholds.max_characters_per_line) longLines.push({element: describe(block), characters_per_line: perLine, lines: tops.length, width_px: Math.round(block.getBoundingClientRect().width)});
  }

  /* Interactive controls: tap targets on touch screens and controls that overlap each other. */
  const controls = [...document.querySelectorAll("a[href], button, input:not([type=hidden]), select, textarea, summary, [role=tab], [role=button]")]
    .filter(node => visible(node) && !node.closest(".sr-only, [hidden]") && !node.classList.contains("skip"));
  const smallTargets = [];
  if (touch) {
    for (const node of controls) {
      const box = node.getBoundingClientRect();
      if (box.width >= thresholds.tap_target_css_px && box.height >= thresholds.tap_target_css_px) continue;
      const inline = node.tagName === "A" && getComputedStyle(node).display === "inline" && !!node.closest("p, li, dd, td, span.caption") && text(node.closest("p, li, dd, td") || node).length > text(node).length + 20;
      smallTargets.push({element: describe(node), label: (text(node) || node.getAttribute("aria-label") || "").slice(0, 50), width: Math.round(box.width), height: Math.round(box.height), inline_in_text: inline});
    }
  }
  const overlappingControls = [];
  for (let i = 0; i < controls.length; i += 1) for (let j = i + 1; j < controls.length; j += 1) {
    const a = controls[i], b = controls[j];
    if (a.contains(b) || b.contains(a) || (a.tagName === "LABEL" && a.htmlFor && b.id === a.htmlFor) || (b.tagName === "LABEL" && b.htmlFor && a.id === b.htmlFor)) continue;
    const boxA = a.getBoundingClientRect(), boxB = b.getBoundingClientRect();
    const overlapX = Math.min(boxA.right, boxB.right) - Math.max(boxA.left, boxB.left), overlapY = Math.min(boxA.bottom, boxB.bottom) - Math.max(boxA.top, boxB.top);
    if (overlapX > 2 && overlapY > 2) overlappingControls.push({a: describe(a), b: describe(b), overlap_px: [Math.round(overlapX), Math.round(overlapY)]});
  }

  /* Media that does not scale: wider than the window or than its own container. */
  const media = [];
  for (const node of document.querySelectorAll("img, video, iframe, canvas, svg:not(button svg):not(a svg)")) {
    if (!visible(node)) continue;
    const box = node.getBoundingClientRect(), parent = node.parentElement, parentBox = parent ? parent.getBoundingClientRect() : null;
    if (box.right > width + 1 || (parentBox && box.width > parentBox.width + 1)) media.push({element: describe(node), width: Math.round(box.width), container_width: parentBox ? Math.round(parentBox.width) : null});
  }

  /* Contrast of every text line against the colour painted behind it. */
  const parseColour = value => { const match = value.match(/rgba?\(([^)]+)\)/); if (!match) return null; const parts = match[1].split(/[ ,/]+/).filter(Boolean).map(Number); return {r: parts[0], g: parts[1], b: parts[2], a: parts.length > 3 ? parts[3] : 1}; };
  const blend = (top, bottom) => ({r: top.r * top.a + bottom.r * (1 - top.a), g: top.g * top.a + bottom.g * (1 - top.a), b: top.b * top.a + bottom.b * (1 - top.a), a: 1});
  const luminance = colour => { const channel = value => { const scaled = value / 255; return scaled <= 0.03928 ? scaled / 12.92 : Math.pow((scaled + 0.055) / 1.055, 2.4); }; return 0.2126 * channel(colour.r) + 0.7152 * channel(colour.g) + 0.0722 * channel(colour.b); };
  const background = element => {
    const layers = [];
    let image = false;
    for (let node = element; node; node = node.parentElement) {
      const style = getComputedStyle(node), colour = parseColour(style.backgroundColor);
      if (style.backgroundImage !== "none" && !(colour && colour.a === 1)) image = true;
      if (colour && colour.a > 0) { layers.push(colour); if (colour.a === 1) break; }
    }
    let result = {r: 255, g: 255, b: 255, a: 1};
    for (const layer of layers.reverse()) result = blend(layer, result);
    return {colour: result, image};
  };
  const contrastFailures = new Map();
  let contrastChecked = 0;
  for (const line of lines) {
    const element = line.parent;
    if (contrastFailures.has(element) || element.closest("button:disabled, input:disabled, select:disabled, [aria-disabled=true]")) continue;
    const style = getComputedStyle(element), foreground = parseColour(style.color);
    if (!foreground) continue;
    const behind = background(element), paint = blend(foreground, behind.colour);
    const light = Math.max(luminance(paint), luminance(behind.colour)), dark = Math.min(luminance(paint), luminance(behind.colour));
    const ratio = (light + 0.05) / (dark + 0.05), size = parseFloat(style.fontSize), weight = Number(style.fontWeight) || 400;
    const large = size >= 24 || (size >= 18.66 && weight >= 700);
    contrastChecked += 1;
    if (ratio < (large ? 3 : 4.5)) contrastFailures.set(element, {element: describe(element), text: text(element).slice(0, 50), ratio: Number(ratio.toFixed(2)), required: large ? 3 : 4.5, colour: style.color, behind: `rgb(${Math.round(behind.colour.r)}, ${Math.round(behind.colour.g)}, ${Math.round(behind.colour.b)})`, over_image: behind.image});
  }

  /* Empty vertical runs: stretches of the page with no text line, control, image or card edge. */
  const spans = lines.map(line => [line.top, line.bottom]);
  for (const node of document.querySelectorAll("img, svg, video, canvas, iframe, input, select, textarea, button, pre, .button, .panel, .problem, .how-step, .kind, .step-demo, .plan-summary, .faq-list, .library-facts, .start-card, .notice, .layer-card, .boundary-zone, .friction-grid article")) {
    if (!visible(node)) continue;
    const box = node.getBoundingClientRect();
    if (box.height > 0) spans.push([box.top + scrollY, box.bottom + scrollY]);
  }
  spans.sort((a, b) => a[0] - b[0]);
  const emptyRuns = [];
  let reach = spans.length ? spans[0][1] : 0;
  for (const [top, bottom] of spans) {
    if (top - reach >= thresholds.empty_run_report_css_px) emptyRuns.push({from_y: Math.round(reach), to_y: Math.round(top), height: Math.round(top - reach), share_of_screen: Number(((top - reach) / height).toFixed(2))});
    reach = Math.max(reach, bottom);
  }

  /* The first screen: the headline, the lead line, the primary action and, on the homepage, the price. */
  const place = node => { if (!node || !visible(node)) return null; const box = node.getBoundingClientRect(); return {top: Math.round(box.top + scrollY), bottom: Math.round(box.bottom + scrollY), in_first_screen: box.top + scrollY >= 0 && box.bottom + scrollY <= height, starts_in_first_screen: box.top + scrollY < height}; };
  const h1 = [...view.querySelectorAll("h1")].find(visible);
  const lead = [...view.querySelectorAll(".hero-subhead, .lede, .intro, .page-intro p:not(.eyebrow), .reading > p:not(.eyebrow)")].find(visible);
  const primary = [...view.querySelectorAll(".button.primary, button.primary")].find(visible) || [...document.querySelectorAll("header .button.primary")].find(visible);
  const priceNode = [...view.querySelectorAll(".hero-split, .plan-amount, .plan-price, .plan-summary-price")].find(visible);
  const firstScreen = {h1: place(h1), lead: place(lead), primary_action: place(primary), price: isHome ? place(priceNode) : null,
    primary_label: primary ? text(primary).slice(0, 60) : null, h1_text: h1 ? text(h1).slice(0, 90) : null};
  const needed = [...budgets.first_screen_holds, ...(isHome ? budgets.homepage_first_screen_also_holds : [])];
  firstScreen.missing = needed.filter(key => !(firstScreen[key] && firstScreen[key].in_first_screen));

  /* Fixed or sticky boxes that cover the top of the window. */
  const covering = [...document.querySelectorAll("body *")].filter(node => { const position = getComputedStyle(node).position; return (position === "fixed" || position === "sticky") && visible(node); })
    .map(node => ({element: describe(node), position: getComputedStyle(node).position, top: Math.round(node.getBoundingClientRect().top), height: Math.round(node.getBoundingClientRect().height)}));

  return {
    view: view.dataset ? view.dataset.view || null : null, title: document.title,
    viewport: {width, height, device_pixel_ratio: devicePixelRatio},
    page_height_px: pageHeight, page_height_screens: Number((pageHeight / height).toFixed(2)),
    root_font_px: parseFloat(getComputedStyle(document.documentElement).fontSize),
    theme: document.documentElement.dataset.theme || "system", body_background: getComputedStyle(document.body).backgroundColor,
    horizontal_overflow: {document_scroll_width: document.documentElement.scrollWidth, overflows: document.documentElement.scrollWidth > width + 1, offenders: offenders.slice(0, 20)},
    clipped_boxes: clippedBoxes.slice(0, 20), scroll_regions: scrollRegions.slice(0, 20),
    overlapping_text: overlaps.slice(0, 20), overlapping_controls: overlappingControls.slice(0, 20),
    small_tap_targets: smallTargets.slice(0, 60), small_tap_target_count: smallTargets.length, small_tap_target_count_excluding_inline: smallTargets.filter(item => !item.inline_in_text).length,
    text_under_smallest: [...smallText.values()].slice(0, 30), phone_body_text_under_minimum: [...smallBody.values()].slice(0, 30),
    max_characters_per_line: maxCharactersPerLine, long_lines: longLines.slice(0, 20),
    media_not_scaling: media.slice(0, 20),
    contrast: {text_lines_checked: contrastChecked, failures: [...contrastFailures.values()].slice(0, 40), failure_count: contrastFailures.size},
    empty_runs: emptyRuns.sort((a, b) => b.height - a.height).slice(0, 12),
    first_screen: firstScreen, fixed_or_sticky: covering,
    header: header ? {position: getComputedStyle(header).position, height: Math.round(header.getBoundingClientRect().height), share_of_screen: Number((header.getBoundingClientRect().height / height).toFixed(3))} : null,
  };
};

/* One capture: one page on one device configuration. */
async function capture(browser, config, target) {
  const record = {engine: config.engine, device: config.id, base_device: config.base_device, group: config.group, page: target.page, kind: target.kind, url: target.url,
    started_at: new Date().toISOString(), console_errors: [], page_errors: [], failed_requests: [], shots: {}, interactions: {}, anchors: [], scroll: null};
  const folder = join(outRoot, config.engine, config.id, target.page);
  mkdirSync(folder, {recursive: true});
  const shot = async (page, name, options = {}) => { const path = join(folder, name + ".png"); await page.screenshot({path, scale: "css", caret: "initial", ...options}); record.shots[name] = relative(outRoot, path); };
  const contextOptions = {viewport: {width: config.width, height: config.height}, deviceScaleFactor: config.scale, hasTouch: !!config.touch,
    colorScheme: config.color_scheme || "light", reducedMotion: config.reduced_motion ? "reduce" : "no-preference", serviceWorkers: "block"};
  if (config.engine !== "firefox") contextOptions.isMobile = !!config.mobile;
  // The injected text-size style is inline markup, which the site's style-src policy refuses, so only that case bypasses the policy.
  if (config.text_scale) contextOptions.bypassCSP = true;
  const context = await browser.newContext(contextOptions);
  await context.addInitScript(installObservers);
  if (config.text_scale) {
    // The served page fixes the root text size in pixels, so a larger text setting is emulated by overriding it in the served markup.
    await context.route("**/*", async route => {
      if (route.request().resourceType() !== "document") return route.continue();
      const response = await route.fetch();
      const body = (await response.text()).replace("</head>", `<style data-lab-text-scale>html{font-size:${config.text_scale * 100}% !important}</style></head>`);
      await route.fulfill({response, body});
    });
  }
  const page = await context.newPage();
  page.on("console", message => { if (message.type() === "error") record.console_errors.push(message.text().slice(0, 300)); });
  page.on("pageerror", error => record.page_errors.push(String(error.message || error).slice(0, 300)));
  page.on("requestfailed", request => record.failed_requests.push({url: request.url().slice(0, 200), error: request.failure()?.errorText || null}));
  page.on("response", response => { if (response.status() >= 400) record.failed_requests.push({url: response.url().slice(0, 200), status: response.status(), type: response.request().resourceType()}); });
  if (config.throttle) {
    const profile = deviceList.throttle_profiles[config.throttle];
    const session = await context.newCDPSession(page);
    await session.send("Network.enable");
    await session.send("Network.emulateNetworkConditions", {offline: false, latency: profile.latency_ms, downloadThroughput: profile.download_kbps * 1000 / 8, uploadThroughput: profile.upload_kbps * 1000 / 8});
    await session.send("Emulation.setCPUThrottlingRate", {rate: profile.cpu_slowdown});
    record.throttle = {profile: config.throttle, ...profile};
  }
  const phone = config.width <= thresholds.phone_max_width_css_px;
  const measure = () => page.evaluate(measurePage, {thresholds, budgets, isHome: target.kind !== "benchmark" && target.path === "/", touch: !!config.touch, phone});
  try {
    const started = Date.now();
    const response = await page.goto(target.url, {waitUntil: "load", timeout: config.throttle ? 120000 : 45000});
    record.status = response ? response.status() : null;
    record.final_url = page.url();
    await page.waitForLoadState("networkidle", {timeout: config.throttle ? 30000 : 8000}).catch(() => {});
    await page.evaluate(() => document.fonts && document.fonts.ready).catch(() => {});
    record.load_ms = Date.now() - started;
    record.degraded = record.failed_requests.some(item => ["document", "stylesheet", "script", "font"].includes(item.type) || item.error);
    if (record.degraded) throw new Error("degraded load: " + JSON.stringify(record.failed_requests.slice(0, 3)));
    if (config.site_theme) {
      record.os_dark_preference_applied = await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme);
      const toggle = page.locator("#theme");
      for (let attempt = 0; attempt < 3 && await toggle.count(); attempt += 1) {
        if (await page.evaluate(() => document.documentElement.dataset.theme) === config.site_theme) break;
        await toggle.click();
      }
      record.site_theme = await page.evaluate(() => document.documentElement.dataset.theme || "system");
      // The appearance switch sits in the footer, so pressing it scrolls there; the first screen is taken from the top again.
      await page.evaluate(() => scrollTo(0, 0));
    }
    await page.waitForTimeout(250);
    // WebKit logs one style-src refusal for each screenshot the lab takes, so the errors of the page itself are the ones before the first.
    record.console_errors_before_screenshots = record.console_errors.slice();
    await shot(page, "first-screen");
    record.metrics = await measure();
    if (fullPageShots) await shot(page, "full-page", {fullPage: true});

    /* The scroll run. */
    const scroll = {steps: [], header_share_max: 0, fixed_share_max: 0};
    const pageHeight = record.metrics.page_height_px, step = Math.max(40, Math.floor(config.height * thresholds.scroll_step_share_of_screen));
    for (let y = 0, index = 0; ; y += step, index += 1) {
      const scrolled = await page.evaluate(top => { scrollTo(0, top); return scrollY; }, y);
      await page.waitForTimeout(120);
      const cover = await page.evaluate(() => {
        let covered = 0;
        for (const node of document.querySelectorAll("body *")) {
          const style = getComputedStyle(node);
          if (style.position !== "fixed" && style.position !== "sticky") continue;
          const box = node.getBoundingClientRect();
          if (box.height && box.top <= 1 && box.bottom > 0 && box.width >= innerWidth * 0.5) covered = Math.max(covered, Math.min(box.bottom, innerHeight));
        }
        const header = document.querySelector("header"), headerBox = header ? header.getBoundingClientRect() : null;
        return {covered_px: Math.round(covered), header_visible_px: headerBox ? Math.round(Math.max(0, Math.min(headerBox.bottom, innerHeight) - Math.max(headerBox.top, 0))) : 0};
      });
      const entry = {index, scroll_y: Math.round(scrolled), covered_share: Number((cover.covered_px / config.height).toFixed(3)), header_share: Number((cover.header_visible_px / config.height).toFixed(3))};
      if (scrollShots) { await shot(page, "scroll-" + String(index).padStart(2, "0")); entry.shot = record.shots["scroll-" + String(index).padStart(2, "0")]; }
      scroll.steps.push(entry);
      if (index > 0) scroll.header_share_max = Math.max(scroll.header_share_max, entry.header_share);
      scroll.fixed_share_max = Math.max(scroll.fixed_share_max, entry.covered_share);
      if (scrolled + config.height >= pageHeight - 2 || index > 80) break;
    }
    scroll.screens_scrolled = scroll.steps.length;
    record.scroll = scroll;
    record.layout_shift = await page.evaluate(() => window.__lab ? {cls: Number(window.__lab.cls.toFixed(4)), shifts: window.__lab.shifts.slice(0, 12), lcp: window.__lab.lcp, layout_shift_supported: !window.__lab.layout_shift_unsupported && window.__lab.supported.includes("layout-shift"), lcp_supported: !window.__lab.lcp_unsupported && window.__lab.supported.includes("largest-contentful-paint")} : null);
    await page.evaluate(() => scrollTo(0, 0));

    /* In-page anchors: jump to each and check the target is not under a fixed or sticky box. */
    const anchors = await page.evaluate(() => [...new Set([...document.querySelectorAll("a[href*='#']")].filter(link => link.getClientRects().length > 0).filter(link => { try { const url = new URL(link.href); return url.pathname === location.pathname && url.hash.length > 1; } catch { return false; } }).map(link => new URL(link.href).hash.slice(1)))]);
    for (const id of anchors.slice(0, 12)) {
      const result = await page.evaluate(async id => {
        const target = document.getElementById(id);
        if (!target) return {id, found: false};
        location.hash = "#" + id;
        await new Promise(done => setTimeout(done, 250));
        const box = target.getBoundingClientRect();
        let covered = 0;
        for (const node of document.querySelectorAll("body *")) { const style = getComputedStyle(node); if (style.position !== "fixed" && style.position !== "sticky") continue; const other = node.getBoundingClientRect(); if (other.top <= 1 && other.bottom > 0 && !node.contains(target) && !target.contains(node) && other.width >= innerWidth * 0.5) covered = Math.max(covered, other.bottom); }
        const heading = target.matches("h1, h2, h3") ? target : target.querySelector("h1, h2, h3");
        const headingTop = heading ? heading.getBoundingClientRect().top : box.top;
        return {id, found: true, target_top: Math.round(box.top), heading_top: Math.round(headingTop), covered_px: Math.round(covered), heading_hidden: headingTop < covered - 1, target_in_view: box.top < innerHeight && box.bottom > 0};
      }, id);
      record.anchors.push(result);
      await page.evaluate(() => { history.replaceState(null, "", location.pathname); scrollTo(0, 0); });
    }

    /* The phone menu. */
    const menuButton = page.locator("#menu-button");
    if (await menuButton.count() && await menuButton.isVisible()) {
      await menuButton.click();
      await page.waitForTimeout(200);
      await shot(page, "menu-open");
      const menu = await page.evaluate(() => {
        const nav = document.getElementById("main-nav"), open = !!nav && getComputedStyle(nav).display !== "none";
        const items = nav ? [...nav.querySelectorAll("a, button")].filter(node => !node.hidden) : [];
        return {open, items: items.map(node => { const box = node.getBoundingClientRect(); return {label: (node.innerText || "").trim().slice(0, 40), width: Math.round(box.width), height: Math.round(box.height), top: Math.round(box.top), bottom: Math.round(box.bottom), visible: box.width > 0 && box.height > 0 && getComputedStyle(node).visibility !== "hidden", in_window: box.top >= 0 && box.bottom <= innerHeight}; }), menu_bottom: nav ? Math.round(nav.getBoundingClientRect().bottom) : null, window_height: innerHeight};
      });
      await page.keyboard.press("Escape");
      await page.waitForTimeout(120);
      menu.closed_by_escape = await page.evaluate(() => document.getElementById("menu-button").getAttribute("aria-expanded") === "false");
      if (!menu.closed_by_escape) { await menuButton.click(); await page.waitForTimeout(120); }
      menu.closed = await page.evaluate(() => getComputedStyle(document.getElementById("main-nav")).display === "none");
      menu.every_item_visible = menu.items.every(item => item.visible);
      menu.every_item_in_window = menu.items.every(item => item.in_window);
      record.interactions.menu = menu;
    }

    /* Disclosures: open each closed one in the shown view once, then measure the page again. */
    const opened = await page.evaluate(() => { const view = [...document.querySelectorAll("main [data-view]")].find(node => !node.hidden) || document.body; const closed = [...view.querySelectorAll("details:not([open])")].filter(node => node.getClientRects().length); closed.forEach(node => { node.open = true; }); return closed.length; });
    if (opened) {
      await page.waitForTimeout(150);
      const after = await measure();
      record.interactions.disclosures = {opened, horizontal_overflow: after.horizontal_overflow.overflows, offenders: after.horizontal_overflow.offenders.slice(0, 5), clipped_boxes: after.clipped_boxes.length, page_height_screens: after.page_height_screens};
      await page.evaluate(() => { const first = document.querySelector("main [data-view]:not([hidden]) details[open]"); if (first) first.scrollIntoView({block: "start"}); });
      await shot(page, "disclosures-open");
      await page.evaluate(() => scrollTo(0, 0));
    }

    /* Tab sets: select each tab once. */
    const tabSets = await page.locator("main [data-view]:not([hidden]) [role=tablist]").count();
    record.interactions.tab_sets = [];
    for (let set = 0; set < tabSets; set += 1) {
      const tabList = page.locator("main [data-view]:not([hidden]) [role=tablist]").nth(set);
      if (!await tabList.isVisible()) continue;
      const tabs = tabList.locator("[role=tab]"), count = await tabs.count(), results = [];
      for (let index = 0; index < count; index += 1) {
        await tabs.nth(index).scrollIntoViewIfNeeded();
        await tabs.nth(index).click();
        await page.waitForTimeout(150);
        const state = await page.evaluate(() => ({overflow: document.documentElement.scrollWidth > document.documentElement.clientWidth + 1}));
        const size = await tabs.nth(index).boundingBox();
        results.push({tab: ((await tabs.nth(index).innerText()) || "").replace(/\s+/g, " ").trim().slice(0, 40), selected: await tabs.nth(index).getAttribute("aria-selected"), horizontal_overflow: state.overflow, width: size ? Math.round(size.width) : null, height: size ? Math.round(size.height) : null});
        await shot(page, `tabs-${set}-${index}`);
      }
      record.interactions.tab_sets.push({set, tabs: results});
    }
  } catch (error) {
    record.error = String(error.message || error).slice(0, 500);
  } finally {
    await context.close().catch(() => {});
  }
  record.finished_at = new Date().toISOString();
  return record;
}

/* Contact sheets: one per page, the first screens of every device in a grid, each labelled with its size. */
async function contactSheets(browser, records) {
  const folder = join(outRoot, "contact-sheets");
  mkdirSync(folder, {recursive: true});
  const pages = [...new Set(records.map(record => record.page))];
  const written = [];
  const context = await browser.newContext({viewport: {width: 1800, height: 1000}, deviceScaleFactor: 1});
  const sheet = await context.newPage();
  for (const pageName of pages) {
    const rows = records.filter(record => record.page === pageName && record.shots["first-screen"]);
    const tiles = rows.map(record => {
      const label = `${record.device} · ${record.engine}` + (record.metrics ? ` · ${record.metrics.page_height_screens} screens` + (record.metrics.first_screen.missing.length ? ` · not in first screen: ${record.metrics.first_screen.missing.join(", ")}` : "") : "") + (record.error ? " · error" : "");
      return `<figure><img src="../${record.shots["first-screen"]}"><figcaption>${label.replace(/[<&]/g, "")}</figcaption></figure>`;
    }).join("");
    const html = `<!doctype html><meta charset="utf-8"><title>${pageName}</title><style>body{margin:16px;font:13px system-ui,sans-serif;background:#e9ecf1;color:#0a1020}h1{font-size:18px;margin:0 0 12px}main{display:flex;flex-wrap:wrap;gap:14px;align-items:flex-start}figure{margin:0;background:#fff;padding:6px;border:1px solid #c5ccd6;border-radius:6px}img{display:block;height:300px;width:auto;border:1px solid #dde2ea}figcaption{max-width:420px;margin-top:5px;font-size:12px;line-height:1.35}</style><h1>${pageName}: first screen on each device (base ${(base || "benchmark").replace(/[<&]/g, "")})</h1><main>${tiles}</main>`;
    const htmlPath = join(folder, pageName + ".html");
    writeFileSync(htmlPath, html);
    await sheet.goto("file://" + htmlPath);
    await sheet.waitForLoadState("load");
    const pngPath = join(folder, pageName + ".png");
    await sheet.screenshot({path: pngPath, fullPage: true});
    written.push(relative(outRoot, pngPath));
  }
  await context.close();
  return written;
}

/* Budgets and a short summary for each page. */
function summarise(records) {
  const pages = {};
  for (const record of records) {
    const row = pages[record.page] ||= {captures: 0, degraded_after_retries: 0, retried: 0, errors: 0, overflow_devices: [], first_screen_misses: [], max_height_screens: 0, height_px_at_1440: null, small_tap_targets_max: 0, contrast_failures_max: 0, console_errors: 0, max_characters_per_line: 0, cls_max: 0};
    row.captures += 1;
    if (record.earlier_attempts) row.retried += 1;
    if (record.degraded) { row.degraded_after_retries += 1; continue; }
    if (record.error || !record.metrics) { row.errors += 1; continue; }
    const metrics = record.metrics;
    if (metrics.horizontal_overflow.overflows) row.overflow_devices.push(record.device);
    if (metrics.first_screen.missing.length) row.first_screen_misses.push({device: record.device, missing: metrics.first_screen.missing});
    row.max_height_screens = Math.max(row.max_height_screens, metrics.page_height_screens);
    if (record.device === "desktop-1440x900") row.height_px_at_1440 = metrics.page_height_px;
    row.small_tap_targets_max = Math.max(row.small_tap_targets_max, metrics.small_tap_target_count_excluding_inline);
    row.contrast_failures_max = Math.max(row.contrast_failures_max, metrics.contrast.failure_count);
    row.console_errors += record.console_errors.length + record.page_errors.length;
    row.max_characters_per_line = Math.max(row.max_characters_per_line, metrics.max_characters_per_line);
    row.cls_max = Math.max(row.cls_max, record.layout_shift?.cls || 0);
  }
  for (const [name, row] of Object.entries(pages)) {
    if (name === "home" || name.startsWith("host-")) row.budget = {rule: `homepage at most ${budgets.homepage_max_css_px_at_1440} px at 1440`, within: row.height_px_at_1440 === null ? null : row.height_px_at_1440 <= budgets.homepage_max_css_px_at_1440};
    else if (!name.startsWith("bench-")) row.budget = {rule: `at most ${budgets.other_pages_max_screens} screens on every device`, within: row.max_height_screens <= budgets.other_pages_max_screens};
  }
  return pages;
}

/* Differences from an earlier metrics record, for the same engine, device and page. */
function compare(records, previousPath) {
  const previous = JSON.parse(readFileSync(previousPath, "utf8"));
  const key = record => [record.engine, record.device, record.page].join("|");
  const before = new Map((previous.captures || []).map(record => [key(record), record]));
  const changes = [];
  for (const record of records) {
    const old = before.get(key(record));
    if (!old || !old.metrics || !record.metrics) { changes.push({key: key(record), state: old ? "not comparable" : "new capture"}); continue; }
    const delta = {key: key(record),
      height_screens: [old.metrics.page_height_screens, record.metrics.page_height_screens],
      overflow: [old.metrics.horizontal_overflow.overflows, record.metrics.horizontal_overflow.overflows],
      small_tap_targets: [old.metrics.small_tap_target_count_excluding_inline, record.metrics.small_tap_target_count_excluding_inline],
      contrast_failures: [old.metrics.contrast.failure_count, record.metrics.contrast.failure_count],
      first_screen_missing: [old.metrics.first_screen.missing, record.metrics.first_screen.missing]};
    delta.regressed = delta.overflow[1] && !delta.overflow[0] || delta.small_tap_targets[1] > delta.small_tap_targets[0] || delta.contrast_failures[1] > delta.contrast_failures[0] || delta.first_screen_missing[1].length > delta.first_screen_missing[0].length || delta.height_screens[1] > delta.height_screens[0] * 1.1;
    changes.push(delta);
  }
  const gone = [...before.keys()].filter(name => !records.some(record => key(record) === name));
  return {previous: previousPath, previous_observed_at: previous.observed_at, changes, captures_missing_now: gone};
}

/* Run every selected configuration against every target, a few at a time per engine. */
const results = [];
const engineVersions = {};
const byEngine = new Map();
for (const config of selected) { if (!byEngine.has(config.engine)) byEngine.set(config.engine, []); byEngine.get(config.engine).push(config); }
let contactSheetPaths = [];
for (const [engineName, configs] of byEngine) {
  const browser = await engines[engineName].launch({headless: true});
  engineVersions[engineName] = browser.version();
  const jobs = configs.flatMap(config => targets.map(target => ({config, target})));
  let next = 0;
  const worker = async () => {
    while (next < jobs.length) {
      const job = jobs[next++];
      let record = await capture(browser, job.config, job.target);
      for (let attempt = 2; record.degraded && attempt <= 3; attempt += 1) {
        // The live service answered 503 to some asset requests under parallel loads; wait and load the page again.
        const earlier = {failed_requests: record.failed_requests, error: record.error};
        await new Promise(done => setTimeout(done, 4000 * attempt));
        record = await capture(browser, job.config, job.target);
        record.earlier_attempts = [...(record.earlier_attempts || []), earlier];
        record.attempt = attempt;
      }
      results.push(record);
      const metrics = record.metrics;
      console.log(JSON.stringify({engine: record.engine, device: record.device, page: record.page, status: record.status ?? null, error: record.error || null,
        screens: metrics?.page_height_screens ?? null, overflow: metrics?.horizontal_overflow.overflows ?? null, missing: metrics?.first_screen.missing ?? null}));
    }
  };
  await Promise.all(Array.from({length: Math.min(concurrency, jobs.length)}, worker));
  await browser.close();
}
{
  const browser = await chromium.launch({headless: true});
  try { contactSheetPaths = await contactSheets(browser, results); } finally { await browser.close(); }
}
results.sort((a, b) => [a.page, a.engine, a.device].join("|").localeCompare([b.page, b.engine, b.device].join("|")));
const output = {
  record_type: "website_responsive_metrics/v1",
  observed_at: new Date().toISOString(),
  base: base || null, hosts: list(option("hosts")), benchmark: benchmark.length ? benchmark : undefined,
  tool: {path: "tools/capture_website_devices.mjs", repository_revision: revision, device_list_sha256: createHash("sha256").update(readFileSync(deviceListPath)).digest("hex")},
  engines: engineVersions,
  selection: {devices: selected.map(config => config.id), engines: [...byEngine.keys()], pages: targets.map(target => target.page), scroll_shots: scrollShots, full_page_shots: fullPageShots},
  screenshot_root: outRoot, contact_sheets: contactSheetPaths,
  budgets, thresholds,
  summary: summarise(results),
  comparison: option("compare") ? compare(results, resolve(option("compare"))) : undefined,
  captures: results,
  limits: [
    "Headless engines on one Linux workstation with emulated viewports; not physical phones or tablets. WebKit stands in for Safari and is not Safari itself.",
    "Signed-out pages only. Nothing was submitted and no account, key or payment path was used.",
    "Text at 200 percent is emulated by overriding the root text size in the served markup, because the page fixes it in pixels.",
    "Contrast is computed against the nearest painted background colour; text over an image or gradient is marked over_image and is not certified.",
    "Characters per line are the text length divided by the number of line boxes, an estimate.",
    "Layout shift and largest contentful paint come from the engine's performance observers; engines without them report unsupported, not zero.",
    "A timing from this workstation is not a field measurement."
  ],
};
writeFileSync(metricsPath, JSON.stringify(output, null, 1) + "\n", {flag: "wx"});
console.log(JSON.stringify({captures: results.length, errors: results.filter(record => record.error).length, metrics: metricsPath, contact_sheets: join(outRoot, "contact-sheets")}));
