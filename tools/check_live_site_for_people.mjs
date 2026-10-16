/* What a person sees on the live site, read-only and without credentials.

   The owner, September 25, 2026: "For releases you may want to adjust the logic, to be more flexible, reasonable, and human
   oriented tests rather than something too strict." This check decides whether a release stays live. It asks what a visitor
   would notice, page by page from the typed site map, at desktop and phone width: the page opens, its heading shows, no script
   error fires, nothing scrolls sideways on a phone, no text is squeezed into a column a person cannot read (added on
   October 16, 2026, after a case study's steps wrapped one or two letters to a line), and every link on it leads somewhere.
   It keeps the initial 1.5-second
   observation, then allows a bounded wait for actual content. Screenshots cover desktop/light and phone/dark, every failed
   view, and any initial not-ready state. It does not compare copy word for word; tools/check_hosted_website.mjs keeps those
   detailed rules and runs beside this one as advice.

   Usage: node tools/check_live_site_for_people.mjs <the site's exact secure origin> <new report folder> */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,existsSync,mkdirSync} from "node:fs";
import {resolve} from "node:path";
import {setRequestedAppearance,readRequestedAppearance,appearanceProblems,appearanceKnownWrongControls} from "./browser_appearance_checks.mjs";
import {observePageReadiness,readinessProblems,shouldCaptureView,SQUEEZED_TEXT,squeezedTextCandidates,squeezedTextProblems} from "./live_site_readiness.mjs";

const origin=process.argv[2],folder=resolve(process.argv[3]||"");
if(!origin||!origin.startsWith("https://")||new URL(origin).origin!==origin||!process.argv[3]||existsSync(folder))
  throw new Error("Use an exact HTTPS origin and a new report folder.");
mkdirSync(folder,{recursive:true});
const root=resolve(new URL("..",import.meta.url).pathname);
const siteMap=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_site_map.json"),"utf8"));
/* Pages a visitor can reach: linked from the header, the footer or another page. Old addresses kept for earlier links are
   opened too, because a person can still follow one, and so are the pages reached by their address only (the changelog,
   the feature list and the open work of September 26, 2026), which the site map lists with no place that links to them.
   Pages behind sign-in are opened as a signed-out visitor sees them. */
const pages=siteMap.pages.filter(page=>!page.address.startsWith("/auth/"));
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
    await setRequestedAppearance(context,origin,scheme);
    for(const {address,view} of pages){
      const page=await context.newPage(),scriptErrors=[];
      page.on("pageerror",error=>scriptErrors.push(String(error.message||error).slice(0,200)));
      page.on("console",message=>{if(message.type()==="error"&&!/favicon|Failed to load resource/i.test(message.text()))scriptErrors.push(message.text().slice(0,200));});
      const where=`${address} (${sizeName}, ${scheme})`;
      const firstProblem=problems.length,openedAt=performance.now();
      const shot=`${address==="/"?"home":address.replace(/^\//,"").replace(/[^a-z0-9]+/gi,"-")}-${sizeName}-${scheme}.png`;
      let status=0,initialScreenshot=null;
      try{status=(await page.goto(origin+address,{waitUntil:"load",timeout:45000}))?.status()||0;}catch(error){note(where,"did not open: "+String(error.message).slice(0,120));}
      const navigationLoadMs=performance.now()-openedAt;
      if(status!==200)note(where,"answered "+status);
      // Keep the 1.5-second observation. Async documentation also needs a bounded content-readiness wait.
      const {seen,readiness}=await observePageReadiness(page,{documentation:view==="docs"?(address==="/docs"?"index":"page"):null,
        onInitialNotReady:async()=>{
          initialScreenshot=shot.replace(/\.png$/,"-initial.png");
          await page.screenshot({path:resolve(folder,initialScreenshot),fullPage:false,timeout:5000})
            .catch(error=>{initialScreenshot=null;note(where,"could not capture initial state: "+String(error.message).slice(0,120));});
        }});
      for(const problem of readinessProblems(seen))note(where,problem);
      if(readiness.timed_out)note(where,`did not become ready within ${readiness.timeout_after_initial_ms} ms after the initial observation`);
      else if(readiness.errors.length)note(where,"could not read readiness: "+readiness.errors.join(" | "));
      if(sizeName==="phone"&&seen.sideways>2)note(where,`scrolls sideways by ${seen.sideways} pixels on a phone`);
      const squeezed=await page.evaluate(squeezedTextCandidates,SQUEEZED_TEXT).catch(error=>{note(where,"could not read the text columns: "+String(error.message).slice(0,120));return [];});
      for(const problem of squeezedTextProblems(squeezed))note(where,problem);
      if(scriptErrors.length)note(where,"script errors: "+scriptErrors.slice(0,3).join(" | "));
      const appearance=await readRequestedAppearance(page).catch(()=>({theme:"unreadable"}));
      for(const problem of appearanceProblems(appearance,scheme))note(where,problem);
      if(appearanceProblems(appearance,scheme).length===0&&!appearanceKnownWrongControls(appearance,scheme))note(where,"appearance guard accepts a known-wrong choice or contrast");
      if(scheme==="light"&&sizeName==="desktop"){
        for(const href of seen.links){const answer=await linkCheck(context,href);if(answer!==200)note(where,`links to ${href.replace(origin,"")}, which answers ${answer}`);}
      }
      const screenshot=shouldCaptureView({size:sizeName,scheme,failed:problems.length>firstProblem})?shot:null;
      if(screenshot)await page.screenshot({path:resolve(folder,screenshot),fullPage:false,timeout:5000})
        .catch(error=>note(where,"could not capture final state: "+String(error.message).slice(0,120)));
      rows.push({address,size:sizeName,scheme,appearance,status,heading:seen.heading.slice(0,120),script_errors:scriptErrors.length,
        navigation_load_ms:navigationLoadMs,readiness,initial_screenshot:initialScreenshot,screenshot});
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
  const openedAt=performance.now();
  try{status=(await page.goto(new URL("/",`${new URL(origin).protocol}//${hostname}`).href,{waitUntil:"load",timeout:45000}))?.status()||0;}catch{status=0;}
  const navigationLoadMs=performance.now()-openedAt;
  const {seen,readiness}=await observePageReadiness(page),heading=seen.heading;
  if(status!==200||!heading)note(hostname,`root answered ${status}${heading?"":" with no main heading"}`);
  if(readiness.timed_out||readiness.errors.length)note(hostname,"root did not complete bounded readiness");
  let screenshot=null;
  if(status!==200||!heading||readiness.timed_out||readiness.errors.length){
    screenshot=`host-${hostname.replace(/[^a-z0-9]+/gi,"-")}-failed.png`;
    await page.screenshot({path:resolve(folder,screenshot),fullPage:false,timeout:5000})
      .catch(error=>note(hostname,"could not capture failed root: "+String(error.message).slice(0,120)));
  }
  rows.push({hostname,status,heading:heading.slice(0,120),navigation_load_ms:navigationLoadMs,readiness,screenshot});
  await page.close();
}
await browser.close();
const report={record_type:"live_site_for_people_check/v1",origin,checked_at:new Date().toISOString(),pages:pages.length,
  hostnames:hostnames.length,views:rows.length,links_checked:linkStatus.size,problems,passed:problems.length===0,rows};
writeFileSync(resolve(folder,"report.json"),JSON.stringify(report,null,1));
console.log(JSON.stringify({passed:report.passed,pages:report.pages,views:report.views,hostnames:report.hostnames,
  links_checked:report.links_checked,problems:problems.slice(0,20),folder}));
process.exitCode=report.passed?0:1;
