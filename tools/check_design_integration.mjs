/* Rendered design and local Run Desk checks. Fixtures hold no real account or provider credentials. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,mkdirSync,writeFileSync,readFileSync} from "node:fs";
import {resolve} from "node:path";
import {setRequestedAppearance,readRequestedAppearance,appearanceProblems} from "./browser_appearance_checks.mjs";

const root=resolve(new URL("..",import.meta.url).pathname),output=resolve(process.argv[2]||"");
if(!process.argv[2]||existsSync(output))throw Error("Use a new evidence directory.");
mkdirSync(output,{mode:0o700});
const checks=[],views=[],errors=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const boot=`from tempfile import TemporaryDirectory
from pathlib import Path
import json,sys
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
with TemporaryDirectory() as folder:
 fixture=HttpDomainFixture(Path(folder))
 with running_http(fixture,display_name="Baltor") as (base,app):
  print(json.dumps({"base":base}),flush=True)
  sys.stdin.readline()
`;
const child=spawn(process.env.PYTHON||"python3",["-u","-c",boot],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","pipe"]});
let browser,stderr="";child.stderr.on("data",data=>{stderr=(stderr+data.toString()).slice(-3000);});
try{
 const base=await new Promise((done,fail)=>{const lines=createInterface({input:child.stdout});const timeout=setTimeout(()=>fail(Error("fixture timeout "+stderr)),20000);
  lines.once("line",line=>{clearTimeout(timeout);done(JSON.parse(line).base);});child.once("exit",code=>{clearTimeout(timeout);fail(Error("fixture exited "+code+" "+stderr));});});
 browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
 const paths=["/","/pricing","/overnight","/setup","/account","/for/designers","/for/coding-agents","/for/protocol-and-client","/gallery","/feeds/setup","/harness-files"];
 for(const width of [1440,390])for(const theme of ["light","dark"]){
  const context=await browser.newContext({viewport:{width,height:900},reducedMotion:"reduce",colorScheme:theme});
  await setRequestedAppearance(context,base,theme);
  await context.route("**/*",route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
  const page=await context.newPage();page.on("pageerror",error=>errors.push(String(error)));
  for(const path of paths){
   const response=await page.goto(base+path);await page.evaluate(()=>document.fonts.ready);
   const state=await page.evaluate(()=>({height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth-innerWidth,
    font:getComputedStyle(document.body).fontFamily,bands:[...document.querySelectorAll('[data-view="home"]>.home-band')].map(node=>({name:node.dataset.band,height:Math.round(node.getBoundingClientRect().height),ground:getComputedStyle(node).backgroundColor})),
    brokenImages:[...document.images].filter(image=>image.getClientRects().length&&image.complete&&!image.naturalWidth).map(image=>image.src)}));
   const where={path,width,theme};views.push({...where,...state});
   check("page_and_images_load",response.status()===200&&state.brokenImages.length===0,where);
   check("shared_typography_and_viewport",state.font.includes("Geist")&&state.overflow<=1,{...where,overflow:state.overflow});
   check("requested_theme",appearanceProblems(await readRequestedAppearance(page),theme).length===0,where);
   if(path==="/"&&width===1440)check("homepage_under_4000_pixels",state.height<=4000,{...where,height:state.height,bands:state.bands});
   if(["/","/pricing","/overnight","/setup","/gallery"].includes(path))await page.screenshot({path:resolve(output,width+"-"+theme+"-"+(path==="/"?"home":path.slice(1))+".png"),fullPage:width===1440});
  }
  await context.close();
 }
 const enlargedContext=await browser.newContext({viewport:{width:320,height:1000}}),enlargedPage=await enlargedContext.newPage();
 await enlargedPage.goto(base+"/overnight");await enlargedPage.evaluate(()=>document.documentElement.style.fontSize="200%");
 check("run_desk_fits_enlarged_text_at_320_pixels",await enlargedPage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await enlargedContext.close();
 const context=await browser.newContext({viewport:{width:1440,height:900}}),page=await context.newPage();
 await page.goto(base+"/overnight");
 await page.locator('[name="tasks"]').fill("/work/tasks/first.txt");
 await page.locator('#run-desk-form button[type="submit"]').click();
 check("run_desk_prepares_worker_arguments",(await page.locator("#run-desk-command").textContent()).includes("--queue-call-budget 24")&&!await page.locator("#run-desk-download").isDisabled());
 await page.locator('[name="tasks"]').fill("/work/tasks/changed.txt");
 const staleGuard=async target=>await target.locator("#run-desk-download").isDisabled()&&(await target.locator("#run-desk-command").textContent())==="";
 check("editing_invalidates_the_prepared_manifest",await staleGuard(page));
 const status={record_type:"overnight_queue_status/v2",calls_allocated:12,call_budget:24,observed_model_calls:null,deadline:1791583200,
  attempts:[{task_file:'<img src=x onerror="alert(1)">',queue_status:"unknown",allocation:12,exit:null}]};
 await page.locator("#run-desk-report").setInputFiles({name:"status.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify(status))});
 await page.waitForFunction(()=>document.querySelector("#run-desk-attempts tr"));
 check("reports_keep_unknown_usage_and_render_text_safely",(await page.locator("#run-desk-summary").textContent()).includes("not measured")&&await page.locator("#run-desk-attempts img").count()===0&&(await page.locator("#run-desk-attempts").textContent()).includes("unknown"));
 await page.locator("#run-desk-report").setInputFiles({name:"old.json",mimeType:"application/json",buffer:Buffer.from(JSON.stringify({...status,record_type:"overnight_queue_status/v1"}))});
 await page.waitForFunction(()=>document.querySelector("#run-desk-summary").textContent.includes("reads the worker"));
 check("old_report_is_refused_and_previous_rows_cleared",await page.locator("#run-desk-attempts tr").count()===0);
 const script=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/run-desk.js"),"utf8");
 const wrong=script.replace('form.addEventListener("input",()=>{','form.addEventListener("unused-event",()=>{');
 check("stale_guard_control_is_applied",wrong!==script);
 await page.route("**/assets/run-desk.js*",route=>route.fulfill({status:200,contentType:"text/javascript",body:wrong}));
 await page.reload();await page.locator('[name="tasks"]').fill("/work/one.txt");await page.locator('#run-desk-form button[type="submit"]').click();
 await page.locator('[name="tasks"]').fill("/work/two.txt");check("removed_stale_manifest_guard_is_detected",!await staleGuard(page));
 await page.goto(base+"/gallery");await page.locator('[data-kind-filter="geometry-4d"]').click();
 check("gallery_filter_tracks_the_selected_kind",new URL(page.url()).searchParams.get("kind")==="geometry-4d"&&await page.locator('.gl-kind:not([hidden])').count()===1);
 await page.locator('[data-kind-filter=""]').click();check("gallery_filter_returns_all_groups",await page.locator('.gl-kind:not([hidden])').count()>1);
 await context.close();
 check("browser_errors",errors.length===0,{errors});
}catch(error){errors.push(String(error));check("runner_finished",false,{error:String(error)});}
finally{if(browser)await browser.close();child.stdin.end();child.kill();}
const result={record_type:"website_design_integration_checks/v1",checks,views,errors,passed:checks.filter(row=>row.passed).length,total:checks.length,all_passed:checks.every(row=>row.passed),external_calls:0};
writeFileSync(resolve(output,"report.json"),JSON.stringify(result,null,2)+"\n",{flag:"wx"});
console.log(JSON.stringify({output,passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(row=>!row.passed)}));
process.exitCode=result.all_passed?0:1;
