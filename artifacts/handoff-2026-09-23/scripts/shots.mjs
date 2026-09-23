import { chromium } from "playwright-core";
const jobs = [["/",320,568,true],["/",844,390,true],["/pricing",1440,900,false],["/how-it-works",390,844,true]];
const browser = await chromium.launch();
for (const [p,w,h,m] of jobs) {
  const ctx = await browser.newContext({ viewport:{width:w,height:h}, isMobile:m, hasTouch:m, deviceScaleFactor:1 });
  const page = await ctx.newPage();
  await page.goto("https://baltor.ai" + p, { waitUntil: "networkidle" }); await page.waitForTimeout(400);
  const name = `first-${p === "/" ? "home" : p.slice(1)}-${w}x${h}.png`;
  await page.screenshot({ path: name }); console.log(name);
  await ctx.close();
}
await browser.close();
