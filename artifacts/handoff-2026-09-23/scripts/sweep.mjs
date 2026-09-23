import { chromium } from "playwright-core";
const base = process.argv[2] || "https://baltor.ai";
const pages = ["/", "/how-it-works", "/pricing", "/connect", "/docs"];
const widths = [[320,568],[360,800],[375,667],[390,844],[412,915],[430,932],[844,390],[600,960],[768,1024],[820,1180],[1024,768],[1180,820],[1280,800],[1366,768],[1440,900],[1536,864],[1920,1080],[2560,1440]];
const browser = await chromium.launch();
const rows = [];
for (const [w,h] of widths) {
  const mobile = w < 900 && h > w || w <= 430;
  const ctx = await browser.newContext({ viewport:{width:w,height:h}, isMobile: w <= 932 && (h > w || w <= 430 || h <= 430), hasTouch: w <= 1180, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  for (const p of pages) {
    await page.goto(base + p, { waitUntil: "networkidle" }).catch(()=>{});
    await page.waitForTimeout(300);
    const m = await page.evaluate(() => {
      const W = innerWidth, H = innerHeight;
      const view = [...document.querySelectorAll("[data-view]")].find(v => !v.hidden && v.getClientRects().length) || document.body;
      const vis = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el); return r.width > 0 && r.height > 0 && s.visibility !== "hidden" && s.display !== "none"; };
      const over = [...document.querySelectorAll("body *")].filter(e => vis(e) && e.getBoundingClientRect().right > W + 1 && !e.closest("pre,.table-scroll,[data-scroll-x]")).slice(0, 4).map(e => (e.tagName.toLowerCase() + (e.id ? "#" + e.id : "") + (e.className && typeof e.className === "string" ? "." + e.className.split(" ")[0] : "")) + ":" + Math.round(e.getBoundingClientRect().right - W));
      const header = document.querySelector("header");
      const hr = header ? header.getBoundingClientRect() : null;
      const navLinks = [...document.querySelectorAll("header nav a, header nav button")].filter(vis);
      const rowsN = new Set(navLinks.map(a => Math.round(a.getBoundingClientRect().top / 8))).size;
      const menuBtn = document.querySelector(".menu-button"); const menuVisible = menuBtn ? vis(menuBtn) : false;
      const h1 = view.querySelector("h1"); const h1b = h1 ? Math.round(h1.getBoundingClientRect().bottom) : null;
      const cta = [...document.querySelectorAll("header .button.primary, [data-view]:not([hidden]) .button.primary, [data-view]:not([hidden]) button.primary")].filter(vis).map(e => Math.round(e.getBoundingClientRect().top)).sort((a,b)=>a-b)[0] ?? null;
      const ctaInView = [...document.querySelectorAll("[data-view]:not([hidden]) .button.primary, [data-view]:not([hidden]) button.primary")].filter(vis).some(e => { const r = e.getBoundingClientRect(); return r.top >= 0 && r.bottom <= H; });
      const taps = [...document.querySelectorAll("a, button, input, select, summary")].filter(vis).filter(e => { const r = e.getBoundingClientRect(); return r.height < 44 && !e.closest("p, li p, td, .caption, .footer-bottom p"); });
      const texts = [...view.querySelectorAll("p, li, dd, td, span, a, label")].filter(e => vis(e) && e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2));
      const fs = texts.map(e => parseFloat(getComputedStyle(e).fontSize));
      const minFs = fs.length ? Math.min(...fs) : null;
      const smallBody = [...view.querySelectorAll("p")].filter(e => vis(e) && parseFloat(getComputedStyle(e).fontSize) < 15 && e.textContent.trim().length > 60).length;
      const longLines = [...view.querySelectorAll("p")].filter(e => vis(e) && e.textContent.trim().length > 120 && e.getBoundingClientRect().width / (parseFloat(getComputedStyle(e).fontSize) * 0.5) > 90).length;
      return { H: document.documentElement.scrollHeight, overflow: document.documentElement.scrollWidth - W, over, headerH: hr ? Math.round(hr.height) : null, headerFixed: header ? ["fixed","sticky"].includes(getComputedStyle(header).position) : false, navRows: rowsN, navShown: navLinks.length, menuVisible, h1Bottom: h1b, ctaInView, tapsSmall: taps.length, minFs, smallBody, longLines };
    });
    rows.push({ w, h, p, screens: +(m.H / h).toFixed(1), ...m });
  }
  await ctx.close();
}
await browser.close();
console.log(JSON.stringify(rows));
