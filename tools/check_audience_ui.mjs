/* Focused first-party UI verification; no external account, telemetry or form submission. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";
import {checkAudiences,heroProblems,heroCheckRejectsItsKnownWrongCases,audienceDestinations} from "./homepage_audience_checks.mjs";

const root=resolve(new URL("..",import.meta.url).pathname),output=resolve(process.argv[2]||"");
if(!output.endsWith(".json")||existsSync(output))throw new Error("A new report filename is required");
for(const suffix of ["-home-desktop.png","-home-phone.png","-designers-desktop.png","-designers-phone.png"])
  if(existsSync(output.replace(/\.json$/,suffix)))throw new Error("Existing screenshot must not be overwritten");
const source=`from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json, sys
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with ExitStack() as stack:
    folder = Path(stack.enter_context(TemporaryDirectory(prefix="audience-ui-")))
    (folder / "intelligence").mkdir()
    held = prepared(folder / "intelligence")
    factory = lambda config: ServiceHttpApplication(held.runtime, held.provisioning, config, access_administration=held.administration)
    base, _ = stack.enter_context(running_http(held, application_factory=factory, display_name="Baltor"))
    print(json.dumps({"base": base}), flush=True)
    sys.stdin.readline()
`;
const service=spawn(resolve(root,".venv/bin/python"),["-u","-c",source],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","inherit"]});
const lines=createInterface({input:service.stdout});
const fixture=await new Promise((accept,reject)=>{const timer=setTimeout(()=>reject(new Error("Fixture did not start")),60000);
  service.on("exit",code=>{clearTimeout(timer);reject(new Error("Fixture exited "+code));});lines.once("line",line=>{clearTimeout(timer);accept(JSON.parse(line));});});
const checks=[],errors=[];const check=(name,passed)=>checks.push({name,passed:passed===true});
const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
try{
  for(const [device,width,height] of [["desktop",1440,1000],["phone",390,844]]){
    const context=await browser.newContext({viewport:{width,height},reducedMotion:"reduce"});
    await context.route("**/*",route=>new URL(route.request().url()).origin===fixture.base?route.continue():route.abort());
    const page=await context.newPage();page.on("pageerror",error=>errors.push(error.message));
    const response=await page.goto(fixture.base);await page.waitForFunction(()=>document.querySelector("#service-status")?.textContent.includes("Service available"));
    check(device+"_home_available",response.status()===200);
    const copy=await page.locator(".hero-copy").evaluate(node=>({headline:node.querySelector("h1").textContent,subhead:node.querySelector(".hero-subhead").textContent,text:node.textContent}));
    check(device+"_shared_product_and_three_audiences",heroProblems(copy).length===0&&heroCheckRejectsItsKnownWrongCases(copy));
    await checkAudiences(page,(name,passed)=>check(device+"_"+name,passed));
    check(device+"_no_home_overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
    await page.screenshot({path:output.replace(/\.json$/,"-home-"+device+".png"),fullPage:false});
    for(const [id,path] of Object.entries(audienceDestinations)){
      await page.locator('[data-audience="'+id+'"] [data-audience-target]').click();
      check(device+"_"+id+"_navigation",new URL(page.url()).pathname===path&&await page.locator("[data-view]:visible h1").count()===1);
      check(device+"_"+id+"_direct_route",(await page.request.get(fixture.base+path)).status()===200);
      if(id==="designers"){
        await page.locator('[data-view="for-designers"] img').first().scrollIntoViewIfNeeded();
        const images=await page.locator('[data-view="for-designers"] img').evaluateAll(items=>items.map(item=>({complete:item.complete,width:item.naturalWidth,alt:item.alt})));
        check(device+"_original_previews_load",images.length===2&&images.every(row=>row.complete&&row.width>0&&row.alt));
        check(device+"_designer_page_has_no_overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
        await page.screenshot({path:output.replace(/\.json$/,"-designers-"+device+".png"),fullPage:true});
      }
      await page.goto(fixture.base);
    }
    await context.close();
  }
}finally{await browser.close();service.stdin.end("\n");lines.close();}
check("no_page_errors",errors.length===0);
const result={record_type:"audience_ui_check/v1",checks,errors,passed:checks.filter(row=>row.passed).length,total:checks.length,all_passed:checks.every(row=>row.passed)};
writeFileSync(output,JSON.stringify(result,null,2)+"\n");console.log(JSON.stringify({passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(row=>!row.passed)}));
process.exitCode=result.all_passed?0:1;
