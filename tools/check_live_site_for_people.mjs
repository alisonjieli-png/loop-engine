/* What a person sees on the live site, read-only and without credentials.

   The owner, September 25, 2026: "For releases you may want to adjust the logic, to be more flexible, reasonable, and human
   oriented tests rather than something too strict." This check decides whether a release stays live. It asks what a visitor
   would notice, page by page from the typed site map, at desktop and phone width: the page opens, its heading shows, no script
   error fires, nothing scrolls sideways on a phone, and every link on it leads somewhere. It saves a screenshot of each page in
   light and dark for a person to look at. It does not compare copy word for word; tools/check_hosted_website.mjs keeps those
   detailed rules and runs beside this one as advice.

   Usage: node tools/check_live_site_for_people.mjs <the site's exact secure origin> <new report folder> */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,existsSync,mkdirSync} from "node:fs";
import {resolve} from "node:path";

const origin=process.argv[2],folder=resolve(process.argv[3]||"");
if(!origin||!origin.startsWith("https://")||new URL(origin).origin!==origin||!process.argv[3]||existsSync(folder))
  throw new Error("Use an exact HTTPS origin and a new report folder.");
mkdirSync(folder,{recursive:true});
const root=resolve(new URL("..",import.meta.url).pathname);
const siteMap=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_site_map.json"),"utf8"));
/* Pages a visitor can reach: linked from the header, the footer or another page. Old addresses kept for earlier links are
   opened too, because a person can still follow one. Pages behind sign-in are opened as a signed-out visitor sees them. */
const pages=siteMap.pages.filter(page=>!page.address.startsWith("/auth/")).map(page=>page.address);
const hostnames=(siteMap.hostnames||[]).map(item=>item.hostname).filter(Boolean);
const problems=[],rows=[],linkStatus=new Map();
const note=(where,problem)=>problems.push({where,problem});

const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const sizes={desktop:{width:1366,height:900},phone:{width:390,height:844}};
const linkCheck=async(context,href)=>{
  if(linkStatus.has(href))return linkStatus.get(href);
  let status=0;
  try{status=(await context.request.get(href,{maxRedirects:5,timeout:30000})).status();}catch{status=0;}
  linkStatus.set(href,status);return status;
};
for(const [sizeName,viewport] of Object.entries(sizes)){
  for(const scheme of ["light","dark"]){
    const context=await browser.newContext({viewport,colorScheme:scheme,userAgent:"Baltor live check for people"});
    for(const address of pages){
      const page=await context.newPage(),scriptErrors=[];
      page.on("pageerror",error=>scriptErrors.push(String(error.message||error).slice(0,200)));
      page.on("console",message=>{if(message.type()==="error"&&!/favicon|Failed to load resource/i.test(message.text()))scriptErrors.push(message.text().slice(0,200));});
      const where=`${address} (${sizeName}, ${scheme})`;
      let status=0;
      /* A person reads the page once it has loaded; a page that keeps fetching (the directory loads its rows in parts) is not
         waited on until every request stops, only for a short moment after the load. */
      try{status=(await page.goto(origin+address,{waitUntil:"load",timeout:45000}))?.status()||0;await page.waitForTimeout(1500);}catch(error){note(where,"did not open: "+String(error.message).slice(0,120));}
      if(status!==200)note(where,"answered "+status);
      const seen=await page.evaluate(()=>{
        const visible=node=>!!node&&node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden";
        const heading=[...document.querySelectorAll("h1")].find(visible);
        const scroller=document.scrollingElement||document.documentElement;
        const links=[...document.querySelectorAll("a[href]")].filter(visible).map(link=>link.href).filter(href=>href.startsWith(location.origin));
        return {heading:heading?heading.textContent.replace(/\s+/g," ").trim():"",sideways:scroller.scrollWidth-window.innerWidth,
          links:[...new Set(links.map(href=>href.split("#")[0]))]};
      }).catch(()=>({heading:"",sideways:0,links:[]}));
      if(!seen.heading)note(where,"shows no main heading");
      if(sizeName==="phone"&&seen.sideways>2)note(where,`scrolls sideways by ${seen.sideways} pixels on a phone`);
      if(scriptErrors.length)note(where,"script errors: "+scriptErrors.slice(0,3).join(" | "));
      if(scheme==="light"&&sizeName==="desktop"){
        for(const href of seen.links){const answer=await linkCheck(context,href);if(answer!==200)note(where,`links to ${href.replace(origin,"")}, which answers ${answer}`);}
      }
      const shot=`${address==="/"?"home":address.replace(/^\//,"").replace(/[^a-z0-9]+/gi,"-")}-${sizeName}-${scheme}.png`;
      if((sizeName==="desktop"&&scheme==="light")||(sizeName==="phone"&&scheme==="dark"))
        await page.screenshot({path:resolve(folder,shot),fullPage:false}).catch(()=>{});
      rows.push({address,size:sizeName,scheme,status,heading:seen.heading.slice(0,120),script_errors:scriptErrors.length});
      await page.close();
    }
    await context.close();
  }
}
/* Each hostname of the site map opens its own page at its root. */
const hostContext=await browser.newContext({viewport:sizes.desktop});
for(const hostname of hostnames){
  const page=await hostContext.newPage();
  let status=0;
  try{status=(await page.goto(new URL("/",`${new URL(origin).protocol}//${hostname}`).href,{waitUntil:"load",timeout:45000}))?.status()||0;await page.waitForTimeout(1500);}catch{status=0;}
  const heading=await page.evaluate(()=>document.querySelector("h1")?.textContent.trim()||"").catch(()=>"");
  if(status!==200||!heading)note(hostname,`root answered ${status}${heading?"":" with no main heading"}`);
  rows.push({hostname,status,heading:heading.slice(0,120)});
  await page.close();
}
await browser.close();
const report={record_type:"live_site_for_people_check/v1",origin,checked_at:new Date().toISOString(),pages:pages.length,
  hostnames:hostnames.length,views:rows.length,links_checked:linkStatus.size,problems,passed:problems.length===0,rows};
writeFileSync(resolve(folder,"report.json"),JSON.stringify(report,null,1));
console.log(JSON.stringify({passed:report.passed,pages:report.pages,views:report.views,hostnames:report.hostnames,
  links_checked:report.links_checked,problems:problems.slice(0,20),folder}));
process.exitCode=report.passed?0:1;
