/* Compare the two offers in the real rendered page. Local mode uses a temporary
   service fixture. An optional exact HTTPS origin is read-only, without accounts.
   Zoom cases emulate the effective CSS viewport and pixel density, not browser UI.
   Usage: PYTHON=... node tools/check_offering_launch.mjs NEW_DIRECTORY [HTTPS_ORIGIN] */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,mkdirSync,writeFileSync,readFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {resolve} from "node:path";
import {setRequestedAppearance,readRequestedAppearance,appearanceProblems,appearanceKnownWrongControls} from "./browser_appearance_checks.mjs";
import {offeringProblems,heroProblems,heroCheckRejectsItsKnownWrongCases} from "./homepage_audience_checks.mjs";

const root=resolve(new URL("..",import.meta.url).pathname),output=resolve(process.argv[2]||"");
let base=process.argv[3];
if(!process.argv[2]||existsSync(output)||base&&(!base.startsWith("https://")||new URL(base).origin!==base))throw Error("New output directory and optional exact HTTPS origin required");
mkdirSync(output,{mode:0o700});
const checks=[],views=[],errors=[],blocked=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const files=["src/loop_engine/core/service_runtime/web_assets/index.html","src/loop_engine/core/service_runtime/web_assets/service.css",
 "src/loop_engine/core/service_runtime/web_pages.py","src/loop_engine/core/service_runtime/library_page.py","src/loop_engine/core/service_runtime/catalogue_feed.py"];
const sourceDigests=Object.fromEntries(files.map(path=>[path,createHash("sha256").update(readFileSync(resolve(root,path))).digest("hex")]));
const profiles=[{name:"desktop-80",width:1800,height:1125,scale:.8},{name:"desktop-100",width:1440,height:900,scale:1},
 {name:"desktop-125",width:1152,height:720,scale:1.25},{name:"tablet",width:1024,height:768,scale:1},
 {name:"phone",width:390,height:844,scale:1},{name:"phone-narrow",width:320,height:740,scale:1},
 {name:"phone-landscape",width:844,height:390,scale:1}];
const inside=(box,width)=>box&&box.width>0&&box.left>=-1&&box.right<=width+1;
const headerFits=state=>inside(state.header,state.width)&&inside(state.brand,state.width)
 &&state.headerControls.every(box=>inside(box,state.width));
function layout(){
 const shown=node=>node&&node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden"&&!node.closest("[hidden]");
 const box=node=>node?.getBoundingClientRect().toJSON()||null;
 const header=document.querySelector(".header"),home=document.querySelector('[data-view="home"]:not([hidden])');
 const h1=[...document.querySelectorAll("h1")].find(shown);
 const active=[...document.querySelectorAll("[data-view]")].find(shown);
 const offerings=home?[...home.querySelectorAll("[data-offering]")].map(node=>({id:node.dataset.offering,title:node.querySelector("h2").innerText.replace(/\s+/g," ").trim(),
   href:node.querySelector("a").getAttribute("href"),text:node.innerText.replace(/\s+/g," "),price:box(node.querySelector(".offering-price"))})):[];
 return {width:innerWidth,height:innerHeight,pageHeight:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth-innerWidth,
  header:box(header),brand:box(header?.querySelector(".brand")),headerControls:[...(header?.querySelectorAll("a,button")||[])].filter(shown).map(box),
  heading:box(h1),primary:box(home?.querySelector("#hero-primary")),offerings,visibleText:active?.innerText||"",
  heroCopy:home?{headline:home.querySelector("h1").innerText,subhead:home.querySelector(".hero-subhead").innerText,text:home.querySelector(".hero-copy").innerText}:null,
  packageHeadlineCount:home?.querySelectorAll("[data-library-count]").length||0,
  setup:home?.querySelector("#hero-setup")?.getAttribute("href"),start:home?.querySelector("#hero-primary")?.getAttribute("href")};
}
let child,browser;
try{
 if(!base){
  const program=`from tempfile import TemporaryDirectory
from pathlib import Path
import json,sys
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
with TemporaryDirectory() as folder:
 fixture=HttpDomainFixture(Path(folder))
 with running_http(fixture,display_name="Baltor") as (base,app):
  print(json.dumps({"base":base}),flush=True)
  sys.stdin.readline()
`;
  child=spawn(process.env.PYTHON||"python3",["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","pipe"]});
  let stderr="";child.stderr.on("data",data=>{stderr=(stderr+data.toString()).slice(-2000);});
  base=await new Promise((done,fail)=>{const lines=createInterface({input:child.stdout});const timer=setTimeout(()=>fail(Error("fixture timeout "+stderr)),20000);
   lines.once("line",line=>{clearTimeout(timer);done(JSON.parse(line).base);});child.once("exit",code=>{clearTimeout(timer);fail(Error("fixture exited "+code+" "+stderr));});});
 }
 browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
 for(const profile of profiles)for(const theme of ["light","dark"]){
  const context=await browser.newContext({viewport:{width:profile.width,height:profile.height},deviceScaleFactor:profile.scale,reducedMotion:"reduce",colorScheme:theme});
  await setRequestedAppearance(context,base,theme);
  await context.route("**/*",route=>{
   const request=route.request(),allowed=new URL(request.url()).origin===base&&["GET","HEAD"].includes(request.method());
   if(!allowed)blocked.push({method:request.method(),origin:new URL(request.url()).origin});
   return allowed?route.continue():route.abort();
  });
  const page=await context.newPage();page.on("pageerror",error=>errors.push({profile:profile.name,theme,message:String(error)}));
  const paths=["/",...(["desktop-100","phone"].includes(profile.name)?["/pricing","/feeds","/library"]:[])];
  for(const path of paths){
   const where={profile:profile.name,theme,path};
   const response=await page.goto(base+path);await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>scrollTo(0,0));
   await page.waitForFunction(theme=>document.documentElement.dataset.theme===theme,theme);
   const state=await page.evaluate(layout),appearance=await readRequestedAppearance(page);
   check("served_page",response?.status()===200,where);
   check("actual_requested_appearance_and_sampled_contrast",appearanceProblems(appearance,theme).length===0,{...where,appearance});
   check("ignored_theme_wrong_ground_and_low_contrast_controls",appearanceKnownWrongControls(appearance,theme),where);
   check("header_and_all_visible_controls_stay_inside_viewport",headerFits(state),{...where,header:state.header,brand:state.brand});
   check("page_has_no_horizontal_overflow",state.overflow<=1,{...where,overflow:state.overflow});
   check("headline_is_not_hidden_by_header",inside(state.heading,state.width)&&state.heading.top>=state.header.bottom-1,where);
   if(path==="/"){
    check("short_outcome_hero_keeps_audiences_and_product",heroProblems(state.heroCopy).length===0&&heroCheckRejectsItsKnownWrongCases(state.heroCopy),where);
    check("both_offers_show_price_period_consent_and_scope",offeringProblems(state.offerings).length===0,{...where,offers:state.offerings});
    check("known_wrong_missing_feed_price_or_consent_is_refused",offeringProblems(state.offerings.map(row=>({...row,text:row.text.replace("$4.99 a month","")}))).length>0
      &&offeringProblems(state.offerings.map(row=>({...row,text:row.text.replace("No automatic charge","")}))).length>0,where);
    check("homepage_marketing_counts_files_not_packages",state.packageHeadlineCount===0&&!/\bpackages?\b/i.test(state.visibleText),where);
    check("existing_access_and_setup_paths_are_preserved",state.start==="/get-started"&&state.setup==="/setup",where);
    if(profile.height>=700)check("headline_and_primary_fit_first_screen",state.heading.bottom<=state.height&&state.primary.bottom<=state.height,where);
    if(profile.width>=1100)check("both_offer_prices_fit_first_screen",state.offerings.length===2&&state.offerings.every(item=>item.price.bottom<=state.height),where);
    await page.evaluate(()=>scrollTo(0,200));check("header_remains_inside_after_scroll",headerFits(await page.evaluate(layout)),where);await page.evaluate(()=>scrollTo(0,0));
    if(profile.name==="desktop-100"){
     await page.locator(".header").evaluate(node=>{node.style.transform="translateX(-200px)";});
     check("known_wrong_clipped_header_is_refused",!headerFits(await page.evaluate(layout)),where);
     await page.locator(".header").evaluate(node=>node.style.removeProperty("transform"));
    }
    if(profile.name==="phone-narrow"){
     const number=page.locator("[data-library-file-count]");
     const previous=await number.textContent();
     const measure=()=>number.evaluate(node=>{
       const range=document.createRange();range.selectNodeContents(node);
       return {parent:node.parentElement.getBoundingClientRect().toJSON(),lines:[...range.getClientRects()].map(rect=>rect.toJSON())};
     });
     const fits=value=>value.lines.length===1&&value.lines.every(line=>line.left>=value.parent.left-1&&line.right<=value.parent.right+1);
     // Display fixture only. Do not mutate any service population or preserve
     // a screenshot that could be mistaken for a ten-million served count.
     await number.evaluate(node=>{node.textContent="10,000,000";});
     await number.scrollIntoViewIfNeeded();const measured=await measure();
     check("ten_million_display_fits_one_line_at_320_pixels",fits(measured),{...where,fixture_only:true,measured});
     await number.evaluate(node=>{node.textContent="10,000,000".repeat(10);});
     check("number_bound_rejects_known_wrong_overflow",!fits(await measure()),where);
     await number.evaluate((node,text)=>{node.textContent=text;},previous);await page.evaluate(()=>scrollTo(0,0));
    }
   }
   if(path==="/pricing"||path==="/feeds")check("feed_price_free_end_date_and_opt_in_are_explicit",/\$4\.99\s+a month/.test(state.visibleText)
    &&/Free through December 31, 2026 \(Eastern\)/.test(state.visibleText)&&/No automatic charge/.test(state.visibleText)&&/opt-in/.test(state.visibleText)
    &&/in development/.test(state.visibleText)&&/\$29\s+a month/.test(state.visibleText),where);
   if(path==="/library")check("library_hero_does_not_advertise_package_counts",!/\bpackages?\b/i.test(await page.locator(".lib-hero").innerText()),where);
   const filename=`${profile.name}-${theme}-${path==="/"?"home":path.slice(1)}.png`;
   await page.screenshot({path:resolve(output,filename),fullPage:false});
   if(path==="/"&&profile.name==="desktop-100")await page.screenshot({path:resolve(output,filename.replace(".png","-full.png")),fullPage:true});
   views.push({...where,state,appearance,screenshot:filename});
  }
  await context.close();
 }
 check("no_page_script_errors",errors.length===0,{errors});
}catch(error){check("completed_matrix",false,{message:String(error)});}
finally{
 if(browser)await browser.close();
 if(child&&child.exitCode===null){const ended=new Promise(done=>child.once("exit",done));child.stdin.end("\n");await ended;}
 const report={record_type:"offering_launch_check/v1",origin:base,sourceDigests,checks,views,errors,blocked,
  passed:checks.length>0&&checks.every(item=>item.passed),limits:["Headless Chromium with emulated viewport and density; not the owner's browser session.","No account, checkout, paid enrollment, provider request or deployment performed."]};
 writeFileSync(resolve(output,"report.json"),JSON.stringify(report,null,2)+"\n");
 console.log(JSON.stringify({output,passed:checks.filter(item=>item.passed).length,total:checks.length,all_passed:report.passed,failures:checks.filter(item=>!item.passed)}));
 if(!report.passed)process.exitCode=1;
}
