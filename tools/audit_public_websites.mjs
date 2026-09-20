/* Signed-out public-page inventory. No accounts, submissions or product claims. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,existsSync,mkdirSync} from "node:fs";
import {resolve,dirname,basename} from "node:path";

const [manifestPath,outputPath,authorization]=process.argv.slice(2);
if(!manifestPath||!outputPath||authorization!=="--authorize-public-page-reads")throw new Error("Manifest, new output path and explicit public-read authority are required.");
const output=resolve(outputPath),shots=resolve(dirname(output),basename(output,".json")+"-screenshots");
if(existsSync(output)||existsSync(shots))throw new Error("Existing evidence will not be overwritten.");
const manifest=JSON.parse(readFileSync(manifestPath,"utf8"));
if(manifest.record_type!=="website_comparison_population/v1"||manifest.sites.length>40||manifest.sites.some(row=>!(/^[a-z0-9_-]+$/.test(row.id))||!row.url?.startsWith("https://")))throw new Error("Unsupported population.");
mkdirSync(shots);
const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const rows=[];
async function inspect(site){
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce",serviceWorkers:"block"});
  const page=await context.newPage();const row={id:site.id,name:site.name,cohort:site.cohort,requested_url:site.url,observed_at:new Date().toISOString(),scope:"signed_out_homepage_only",state:"unavailable",error:null};
  try{
    const response=await page.goto(site.url,{waitUntil:"domcontentloaded",timeout:25000});
    await page.waitForLoadState("load",{timeout:8000}).catch(()=>{});
    row.status=response?.status()??null;row.final_url=page.url();
    if(row.status!==200){row.error="http_status";return row;}
    row.state="public_page_observed";
    Object.assign(row,await page.evaluate(()=>{
      const visible=el=>!!el.getClientRects().length&&getComputedStyle(el).visibility!=="hidden";
      const compact=text=>text.replace(/\s+/g," ").trim();
      const links=[...document.querySelectorAll("a[href]")].filter(visible).map(a=>({label:compact(a.innerText||a.getAttribute("aria-label")||"").slice(0,90),url:a.href})).filter(a=>a.label&&a.url.startsWith("https://"));
      return {title:document.title,h1:[...document.querySelectorAll("h1")].filter(visible).map(x=>compact(x.innerText).slice(0,180)),
        headings:[...document.querySelectorAll("h2")].filter(visible).slice(0,12).map(x=>compact(x.innerText).slice(0,100)),
        links:[...new Map(links.map(x=>[x.label+"|"+x.url,x])).values()].slice(0,90),
        desktop_overflow:document.documentElement.scrollWidth>innerWidth+1,
        rendered_body_color:getComputedStyle(document.body).backgroundColor,
        rendered_body_font:getComputedStyle(document.body).fontFamily,
        visible_form_count:[...document.querySelectorAll("form")].filter(visible).length};
    }));
    if(site.screenshot){row.screenshot=basename(shots)+"/"+site.id+".png";await page.screenshot({path:resolve(shots,site.id+".png")});}
    await page.setViewportSize({width:390,height:844});
    row.mobile_overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1);
    row.mobile_menu_controls=await page.locator('button[aria-label*="menu" i],button[aria-label*="navigation" i]').count();
  }catch(error){row.error=error.name;row.state="unavailable";}
  finally{await context.close();}
  return row;
}
try{
  // Two independent signed-out tabs, one ordinary page load per site.
  for(let index=0;index<manifest.sites.length;index+=2){
    for(const row of await Promise.all(manifest.sites.slice(index,index+2).map(inspect))){rows.push(row);console.log(JSON.stringify({id:row.id,state:row.state,status:row.status,links:row.links?.length??0}));}
  }
}finally{await browser.close();}
const result={record_type:"public_website_observations/v1",observed_at:new Date().toISOString(),population:manifest.sites.map(x=>x.id),observations:rows,
  limits:["Signed-out public pages only; links are discovered, not destination qualification", "No sign-ups, purchases, native client connections or authenticated product flows were attempted", "Design observations are not conversion, accessibility certification or feature-quality rankings", "A blocked or failed page is unknown, not an absent capability", "Viewport findings are this browser observation, not a universal device result"]};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
