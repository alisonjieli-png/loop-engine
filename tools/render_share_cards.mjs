/* Draw the pictures a shared link to the homepage and the October 9, 2026 guide pages shows, 1200 by 630 pixels each,
   in the website's typefaces, colours and mark:

     share-card.png                 the homepage and every view of the one-page site
     share-card-feeds.png           /feeds/setup, Use Agent Feeds
     share-card-harness-files.png   /harness-files, Harness Files
     share-card-gallery.png         /gallery, with six renders from the gallery record
     share-card-deterministic-skills.png, share-card-tools.png, share-card-corner-cases.png
                                    the three showcase hostnames, each with the headline and first groups its
                                    showcase record names and its own hostname

   Name card files after the command to draw only those:  node tools/render_share_cards.mjs share-card-tools.png

   Each headline is read from the page that shows it, so a card cannot drift from its page. A card carries no number,
   because a picture cannot carry a source note. Run it again after a headline changes:

     node tools/render_share_cards.mjs

   It opens no network connection: the typefaces, the mark and the renders are read from the packaged web assets. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";

const root = resolve(new URL("..", import.meta.url).pathname);
const runtime = resolve(root, "src/loop_engine/core/service_runtime");
const assets = resolve(runtime, "web_assets");
const data = (name, type) => `data:${type};base64,` + readFileSync(resolve(assets, name)).toString("base64");
const font = name => data(name, "font/woff2");
const mark = data("baltor-mark.svg", "image/svg+xml");
const escape = text => text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const index = readFileSync(resolve(assets, "index.html"), "utf8");
const guides = readFileSync(resolve(runtime, "offering_guides.py"), "utf8");
const galleryPage = readFileSync(resolve(runtime, "gallery_page.py"), "utf8");
const found = (text, pattern, what) => {
  const value = text.match(pattern)?.[1];
  if (!value) throw new Error("No headline found for " + what);
  if (/\d/.test(value)) throw new Error("A card carries no number, and the headline of " + what + " has one: " + value);
  return value;
};
const homeHeadline = found(index, /<section data-view="home"[\s\S]*?<h1[^>]*>([^<]+)<\/h1>/, "the homepage");
const feedsHeadline = found(guides, /"Agent Feeds", "([^"]+)", "feeds-setup-title"/, "/feeds/setup");
const filesHeadline = found(guides, /"Harness Files", "([^"]+)", "harness-files-title"/, "/harness-files");
const galleryHeadline = found(galleryPage, /<h1 id="gallery-title">([^<]+)<\/h1>/, "/gallery");
const gallery = JSON.parse(readFileSync(resolve(assets, "gallery/gallery.json"), "utf8"));
/* One render from each kind with renders, in the gallery's own order, then the second of each until there are six. */
const shown = gallery.items.filter(item => item.preview && item.tier !== "private");
const byKind = gallery.kinds.map(kind => shown.filter(item => item.kind === kind.id)).filter(group => group.length);
const picked = [...byKind.map(group => group[0]), ...byKind.map(group => group[1]).filter(Boolean)].slice(0, 6);
const renders = picked.map(item => ({title: item.title, src: data("gallery/" + item.preview.file, "image/webp")}));
if (renders.length < 6) throw new Error("The gallery has fewer than six renders to draw.");

const style = `
@font-face{font-family:Geist;src:url(${font("geist.woff2")}) format("woff2");font-weight:100 900}
@font-face{font-family:"Geist Mono";src:url(${font("geist-mono.woff2")}) format("woff2");font-weight:100 900}
*{box-sizing:border-box}html,body{margin:0}
body{width:1200px;height:630px;display:grid;grid-template-columns:1fr 470px;gap:56px;align-items:center;padding:64px 72px;
  font-family:Geist,sans-serif;color:#201610;background:#FEFBF8;
  background-image:radial-gradient(#E4D9D1 1.2px,transparent 1.2px);background-size:24px 24px}
.brand{display:flex;align-items:center;gap:16px;font-size:40px;font-weight:650;letter-spacing:-.02em}
.brand img{width:64px;height:64px}
.eyebrow{margin:40px 0 0;color:#BD4600;font-size:17px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
h1{margin:14px 0 0;font-size:54px;line-height:1.06;letter-spacing:-.035em;font-weight:650;text-wrap:balance}
.line{margin:22px 0 0;color:#544B45;font-size:22px;line-height:1.4}
.site{margin:22px 0 0;color:#BD4600;font-size:22px;font-weight:700}
.panel{padding:30px;border-radius:18px;background:#110B08;color:#E1DDD8;box-shadow:0 24px 60px rgba(44,30,20,.22)}
.panel p{margin:0}.caption{color:#FFFFFF;font-weight:650;font-size:18px}
pre{margin:18px 0 0;font:500 16px/1.75 "Geist Mono",monospace;white-space:pre-wrap}.dim{color:#A99E96}.hot{color:#FB9D59}
.offers{list-style:none;margin:6px 0 0;padding:0;display:grid;gap:14px}
.offers li{padding:16px 18px;border:1px solid #3A2F28;border-radius:12px}
.offers strong{display:block;color:#FFFFFF;font-size:21px;font-weight:650}.offers span{color:#C5BCB4;font-size:17px}
.check{margin-top:16px!important;color:#9BD8A8;font-weight:600;font-size:17px}
.mosaic{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.mosaic img{width:100%;aspect-ratio:1/1;border-radius:12px;display:block;object-fit:cover;border:1px solid #3A2F28}`;
const card = (eyebrow, headline, line, panel, site = "baltor.ai") => `<!doctype html><html><head><meta charset="utf-8"><style>${style}</style></head><body>
<div><div class="brand"><img src="${mark}" alt="">Baltor</div><p class="eyebrow">${escape(eyebrow)}</p><h1>${escape(headline)}</h1>
<p class="line">${escape(line)}</p><p class="site">${escape(site)}</p></div><div class="panel">${panel}</div></body></html>`;

const cards = [
  ["share-card.png", card("Harness and agent optimized operation", homeHeadline,
    "Research, ready files and overnight tools for the AI agents you already run.",
    `<ul class="offers"><li><strong>Agent Feeds</strong><span>Sources your agent checks before it decides</span></li>
     <li><strong>Harness Files</strong><span>Files your harness downloads at an exact version</span></li>
     <li><strong>Overnight / AFK Work</strong><span>A local queue that keeps moving while you are away</span></li></ul>`)],
  ["share-card-feeds.png", card("Agent Feeds", feedsHeadline,
    "Pick a decision, copy one link, and your agent reads the sources before it chooses.",
    `<p class="caption">One line in AGENTS.md</p><pre><span class="dim">Before choosing a coding model, read</span>
<span class="hot">baltor.ai/feeds/collections/coding-benchmarks.md</span>
<span class="dim">and follow its decision checklist.</span></pre><p class="check">Markdown, JSON Feed and RSS. No key needed.</p>`)],
  ["share-card-harness-files.png", card("Harness Files", filesHeadline,
    "Skills, instruction files, tools, hooks and settings for the harness you already use.",
    `<p class="caption">An example folder for one step</p><pre><span class="dim">project/</span>
├── CLAUDE.md
├── .claude/skills/find-duplicates/
│   └── SKILL.md
├── .mcp.json
└── .baltor/step.lock.json</pre><p class="check">Each file checked against its checksum</p>`)],
  ["share-card-gallery.png", card("Gallery", galleryHeadline,
    "Godot shaders, procedural textures, meshes and Blender tools, each with the render its check recorded.",
    `<div class="mosaic">${renders.map(item => `<img src="${item.src}" alt="">`).join("")}</div>`)],
];
/* The showcase hostnames: each card's headline and groups come from the showcase record, and its hostname from the site
   map's canonical section for the host, so a card cannot name a hostname or a group the pages do not have. */
const showcase = JSON.parse(readFileSync(resolve(assets, "library-sites/hosts.json"), "utf8"));
const siteMapRecord = JSON.parse(readFileSync(resolve(runtime, "web_site_map.json"), "utf8"));
const showcaseFiles = {"deterministic-skills": "share-card-deterministic-skills.png", "harness-tools": "share-card-tools.png",
  "corner-cases": "share-card-corner-cases.png"};
for (const host of showcase.hosts) {
  const section = siteMapRecord.hostnames.find(row => row.canonical_section && row.address === host.address);
  if (!section) throw new Error("No canonical section holds " + host.address);
  if (/\d/.test(host.headline)) throw new Error("A card carries no number, and the headline of " + host.id + " has one");
  const groups = host.categories.slice(0, 3).map(category => `<li><strong>${escape(category.title)}</strong></li>`).join("");
  cards.push([showcaseFiles[host.id], card(host.name, host.headline, host.lede.split(". ")[0] + ".",
    `<p class="caption">Browse by job</p><ul class="offers">${groups}</ul>`, section.hostname)]);
}
const only = process.argv.slice(2);
const browser = await chromium.launch({executablePath: process.env.LOOP_WEBSITE_BROWSER || "/opt/google/chrome/chrome", headless: true, args: ["--no-sandbox"]});
try {
  const tab = await browser.newPage({viewport: {width: 1200, height: 630}, deviceScaleFactor: 1});
  await tab.route("**/*", route => (route.request().url().startsWith("data:") ? route.continue() : route.abort()));
  const written = [];
  for (const [name, page] of cards) {
    if (only.length && !only.includes(name)) continue;
    await tab.setContent(page, {waitUntil: "load"});
    await tab.evaluate(() => document.fonts.ready);
    await tab.screenshot({path: resolve(assets, name), type: "png"});
    written.push(name);
  }
  console.log(JSON.stringify({written, width: 1200, height: 630, headlines: [homeHeadline, feedsHeadline, filesHeadline, galleryHeadline]}));
} finally {
  await browser.close();
}
