/* Local browser checks for one shared appearance across full-page navigation. No external requests or real accounts. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync, mkdirSync, writeFileSync} from "node:fs";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname), output=resolve(process.argv[2]||"");
if(!process.argv[2]||existsSync(output))throw new Error("Supply a new private evidence directory.");
mkdirSync(output,{mode:0o700});
const python=process.env.PYTHON||resolve(root,".venv/bin/python");
const program=`from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with ExitStack() as stack:
    folder=Path(stack.enter_context(TemporaryDirectory(prefix="site-appearance-")))
    (folder/"intelligence").mkdir()
    held=prepared(folder/"intelligence")
    factory=lambda config: ServiceHttpApplication(held.runtime,held.provisioning,config,access_administration=held.administration)
    base,_=stack.enter_context(running_http(held,application_factory=factory,display_name="Baltor"))
    print(json.dumps({"base":base}),flush=True)
    sys.stdin.readline()
`;
const child=spawn(python,["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","pipe"]});
let errors="";child.stderr.on("data",chunk=>{errors+=chunk;});
const base=await new Promise((done,fail)=>{
  const lines=createInterface({input:child.stdout});
  lines.once("line",line=>{try{done(JSON.parse(line).base);}catch(error){fail(error);}});
  child.once("exit",code=>fail(new Error("Fixture stopped: "+code+" "+errors)));
});
const checks=[],surfaces=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,...detail});
const paths=["/","/pricing","/feeds","/directory","/models","/public-good","/deck"];
function appearance(){
  const root=document.documentElement,style=getComputedStyle(root),header=document.querySelector(".header");
  const probe=document.createElement("span");document.body.append(probe);
  const token=name=>{probe.style.color="var(--"+name+")";return getComputedStyle(probe).color;};
  const hero=document.querySelector('[data-view="home"]:not([hidden]) .band-hero');
  const primary=header?.querySelector(".primary"), snapshot={theme:root.dataset.theme||"system",label:document.getElementById("theme")?.textContent,
    accent:token("accent"),primary:primary?getComputedStyle(primary).backgroundColor:null,
    offeringEyebrows:[...document.querySelectorAll('[data-view="home"]:not([hidden]) .offering-card .eyebrow')].map(item=>getComputedStyle(item).color),
    nightAccent:token("night-accent"),evidenceLinks:[...document.querySelectorAll('[data-view="home"]:not([hidden]) [data-hero-evidence-link]')].map(item=>getComputedStyle(item).color),
    paper:token("paper"),ink:token("ink"),audienceCards:[...document.querySelectorAll('[data-view="home"]:not([hidden]) .audience-card')].map(item=>({
      background:getComputedStyle(item).backgroundColor,ink:getComputedStyle(item).color,label:getComputedStyle(item.querySelector(".audience-label")).color})),
    button:token("button"),ground:token("ground"),hero:hero?getComputedStyle(hero).backgroundColor:null,
    overflow:document.documentElement.scrollWidth-innerWidth};
  probe.remove();return snapshot;
}
const sameTheme=state=>state.primary===state.button&&(!state.hero||state.hero===state.ground)
  &&state.offeringEyebrows.every(colour=>colour===state.accent)
  &&state.evidenceLinks.every(colour=>colour===state.nightAccent)
  &&state.audienceCards.every(card=>card.background===state.paper&&card.ink===state.ink&&card.label===state.accent);
let browser;
try{
  browser=await chromium.launch({executablePath:process.env.LOOP_WEBSITE_BROWSER||"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  const context=await browser.newContext({viewport:{width:1440,height:900},colorScheme:"light"});
  await context.route("**/*",route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();
  await page.goto(base);
  for(const theme of ["light","dark"]){
    if(theme==="dark")await page.locator("#theme").click();
    for(const viewport of [{width:1440,height:900},{width:390,height:844}]){
      await page.setViewportSize(viewport);
      for(const path of paths){
        const response=await page.goto(base+path);await page.locator("#theme").waitFor();
        const state=await page.evaluate(appearance),label=`${theme} ${viewport.width} ${path}`;
        check("appearance_persists_across_page_load",state.theme===theme&&state.label==="Appearance: "+theme,{surface:label});
        check("canonical_primary_and_home_ground",sameTheme(state),{surface:label,state});
        check("no_horizontal_overflow",state.overflow<=1,{surface:label,overflow:state.overflow});
        check("page_is_served",response.status()===200,{surface:label,status:response.status()});
        surfaces.push({path,viewport,theme,...state});
        await page.screenshot({path:resolve(output,`${theme}-${viewport.width}-${path==="/"?"home":path.slice(1)}.png`),fullPage:false});
        if(path==="/")await page.locator(".audience-grid").screenshot({path:resolve(output,`${theme}-${viewport.width}-home-audiences.png`)});
      }
    }
    await page.goto(base);
  }
  await page.locator("#theme").click();
  await page.emulateMedia({colorScheme:"dark"});
  await page.goto(base+"/models");
  check("system_choice_is_persisted",(await page.evaluate(appearance)).theme==="system");
  const dark=await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--ground"));
  await page.emulateMedia({colorScheme:"light"});
  check("system_choice_follows_os",dark!==await page.evaluate(()=>getComputedStyle(document.documentElement).getPropertyValue("--ground")));
  const second=await context.newPage();await second.goto(base+"/pricing");
  await page.locator("#theme").click();
  await second.waitForFunction(()=>document.getElementById("theme").textContent==="Appearance: light");
  check("another_open_tab_tracks_the_same_preference",(await second.evaluate(appearance)).theme==="light");
  await page.evaluate(()=>localStorage.setItem("baltor.appearance","unsupported"));await page.reload();
  check("unknown_saved_choice_falls_back",(await page.evaluate(appearance)).theme==="light");
  await page.goto(base);const valid=await page.evaluate(appearance);
  await page.locator('[data-view="home"] .band-hero').evaluate(item=>{item.style.background="var(--night)";});
  check("known_wrong_forced_night_hero_is_detected",sameTheme(valid)&&!sameTheme(await page.evaluate(appearance)));
  await page.reload();
  await page.locator(".header").evaluate(item=>{item.style.setProperty("--button","var(--night-button)");});
  check("known_wrong_dark_header_override_is_detected",!sameTheme(await page.evaluate(appearance)));
  await page.reload();await page.locator(".audience-card").first().evaluate(item=>{item.style.background="var(--night)";});
  check("known_wrong_forced_night_audience_card_is_detected",!sameTheme(await page.evaluate(appearance)));
  await page.evaluate(()=>localStorage.setItem("baltor.appearance","dark"));await page.goto(base+"/deck");
  const completeDeck=await page.evaluate(appearance);
  await page.locator('link[rel="stylesheet"][href^="/assets/architecture.css"]').evaluate(item=>item.remove());
  check("known_wrong_missing_deck_chrome_stylesheet_is_detected",sameTheme(completeDeck)&&!sameTheme(await page.evaluate(appearance)));
  const blocked=await browser.newContext();
  await blocked.route("**/*",route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  await blocked.addInitScript(()=>{Object.defineProperty(window,"localStorage",{get(){throw new Error("unavailable");}});});
  const fallback=await blocked.newPage();await fallback.goto(base);await fallback.locator("#theme").click();
  check("storage_refusal_keeps_the_control_usable",(await fallback.evaluate(appearance)).theme==="dark");
  await blocked.close();await context.close();
  const deckContext=await browser.newContext(),responses=[];
  await deckContext.route("**/*",route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const deckPage=await deckContext.newPage();deckPage.on("response",response=>responses.push(response));
  await deckPage.goto(base+"/deck");await deckPage.waitForLoadState("networkidle");
  const sizes=await Promise.all(responses.map(async response=>({path:new URL(response.url()).pathname,status:response.status(),bytes:(await response.body()).length})));
  const bytes=sizes.reduce((total,item)=>total+item.bytes,0);
  check("deck_with_shared_chrome_meets_existing_payload_budget",sizes.length<=12&&bytes<=420000&&sizes.every(item=>item.status===200),{bytes,files:sizes});
  await deckContext.close();
}finally{
  if(browser)await browser.close();child.stdin.end("\n");
  writeFileSync(resolve(output,"summary.json"),JSON.stringify({record_type:"site_appearance_check/v1",checks,surfaces,all_passed:checks.length>0&&checks.every(item=>item.passed)},null,2),{flag:"wx",mode:0o600});
}
console.log(JSON.stringify({checks:checks.length,passed:checks.filter(item=>item.passed).length,failures:checks.filter(item=>!item.passed),output}));
if(checks.some(item=>!item.passed))process.exitCode=1;
