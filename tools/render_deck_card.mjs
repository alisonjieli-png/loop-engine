/* Draw the picture a shared link to the deck shows: src/loop_engine/core/service_runtime/web_assets/deck-card.png,
   1200 by 630 pixels, in the website's typefaces, colours and mark. It carries no number, because a picture cannot
   carry the source note every number on the deck has. Run it again after the deck's headline changes:

     node tools/render_deck_card.mjs

   It opens no network connection: the typefaces and the mark are read from the packaged web assets. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";

const root = resolve(new URL("..", import.meta.url).pathname);
const assets = resolve(root, "src/loop_engine/core/service_runtime/web_assets");
const font = name => "data:font/woff2;base64," + readFileSync(resolve(assets, name)).toString("base64");
const mark = "data:image/svg+xml;base64," + readFileSync(resolve(assets, "baltor-mark.svg")).toString("base64");
const deck = readFileSync(resolve(assets, "deck.html"), "utf8");
const headline = deck.match(/<h1 id="cover-title">([^<]+)<\/h1>/)?.[1];
if (!headline) throw new Error("The deck has no cover headline to draw.");
if (/\d/.test(headline)) throw new Error("The card carries no number, and the headline has one: " + headline);
const page = `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:Geist;src:url(${font("geist.woff2")}) format("woff2");font-weight:100 900}
@font-face{font-family:"Geist Mono";src:url(${font("geist-mono.woff2")}) format("woff2");font-weight:100 900}
*{box-sizing:border-box}html,body{margin:0}
body{width:1200px;height:630px;display:grid;grid-template-columns:1fr 430px;gap:56px;align-items:center;padding:64px 72px;
  font-family:Geist,sans-serif;color:#0A1020;background:#F5F6F8;background-image:radial-gradient(#D5DAE2 1.2px,transparent 1.2px);background-size:24px 24px}
.brand{display:flex;align-items:center;gap:16px;font-size:40px;font-weight:700;letter-spacing:-.02em}
.brand img{width:64px;height:64px;border-radius:14px}
.eyebrow{margin:40px 0 0;color:#2E5BFF;font-size:17px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1{margin:14px 0 0;font-size:56px;line-height:1.05;letter-spacing:-.035em;font-weight:700}
.site{margin:28px 0 0;color:#3A4456;font-size:22px;font-weight:600}
.folder{padding:30px;border-radius:18px;background:#060A14;color:#C9D2E3;box-shadow:0 24px 60px rgba(10,16,32,.18)}
.folder p{margin:0}.caption{color:#FFFFFF;font-weight:650;font-size:18px}
pre{margin:18px 0;font:500 16px/1.75 "Geist Mono",monospace;white-space:pre}.dim{color:#A3AEC2}
.check{color:#7FD3A6;font-weight:600;font-size:17px}
</style></head><body>
<div><div class="brand"><img src="${mark}" alt="">Baltor</div>
<p class="eyebrow">Harness and agent optimized operation</p><h1>${headline}</h1><p class="site">baltor.ai</p></div>
<div class="folder"><p class="caption">An example working folder for one step</p>
<pre><span class="dim">working-folder/</span>
├── AGENTS.md
├── .agents/skills/split-address-lines/
│   └── SKILL.md
└── .mcp.json</pre><p class="check">✓ Each file is checked against its digest</p></div>
</body></html>`;
const browser = await chromium.launch({executablePath: process.env.LOOP_WEBSITE_BROWSER || "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
try {
  const tab = await browser.newPage({viewport: {width: 1200, height: 630}, deviceScaleFactor: 1});
  await tab.route("**/*", route => (route.request().url().startsWith("data:") ? route.continue() : route.abort()));
  await tab.setContent(page, {waitUntil: "load"});
  await tab.evaluate(() => document.fonts.ready);
  const output = resolve(assets, "deck-card.png");
  await tab.screenshot({path: output, type: "png"});
  console.log(JSON.stringify({output, width: 1200, height: 630, headline}));
} finally {
  await browser.close();
}
