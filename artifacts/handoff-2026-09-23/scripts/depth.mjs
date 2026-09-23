import { chromium } from "playwright-core";
const base = process.argv[2] || "https://baltor.ai";
const routes = ["/", "/how-it-works", "/pricing", "/connect", "/docs", "/examples", "/security", "/privacy", "/signup", "/login"];
const sizes = [[1440, 900], [390, 844]];
const browser = await chromium.launch();
const out = [];
for (const [w, h] of sizes) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await ctx.newPage();
  for (const r of routes) {
    await page.goto(base + r, { waitUntil: "networkidle" }).catch(() => {});
    await page.waitForTimeout(400);
    const m = await page.evaluate(() => {
      const view = [...document.querySelectorAll("[data-view]")].find(v => !v.hidden && v.getClientRects().length);
      const H = document.documentElement.scrollHeight;
      const y = el => el ? Math.round(el.getBoundingClientRect().top + scrollY) : null;
      const price = [...(view || document).querySelectorAll("*")].find(e => e.children.length === 0 && /\$29/.test(e.textContent));
      const footer = document.querySelector("footer");
      const bands = view ? [...view.children].filter(c => c.getClientRects().length).map(c => ({ tag: c.tagName.toLowerCase(), cls: (c.className || "").toString().slice(0, 40), h: Math.round(c.getBoundingClientRect().height), padT: parseFloat(getComputedStyle(c).paddingTop), padB: parseFloat(getComputedStyle(c).paddingBottom), head: (c.querySelector("h1,h2")?.textContent || "").replace(/\s+/g, " ").trim().slice(0, 50) })) : [];
      return { H, footerTop: y(footer), priceY: y(price), h2s: [...(view || document).querySelectorAll("h2")].length, words: (view?.innerText || "").split(/\s+/).filter(Boolean).length, bands };
    });
    out.push({ route: r, w, h, screens: +(m.H / h).toFixed(1), ...m });
  }
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(out));
