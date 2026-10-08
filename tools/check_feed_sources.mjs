/* Read-only browser acceptance for source collections, against a local fixture or a deployed release.
   No account, provider request, source download or catalogue mutation. DOM-only negative controls are discarded. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname);
const [target,outputArgument]=process.argv.slice(2);
if(!target||!outputArgument)throw new Error("Use: check_feed_sources.mjs --local|HTTPS_ORIGIN NEW_OUTPUT.json");
const output=resolve(outputArgument),pictures=["-desktop.png","-mobile.png"].map(suffix=>output.replace(/\.json$/,suffix));
if(!output.endsWith(".json")||[output,...pictures].some(existsSync))throw new Error("Use a new JSON report and screenshot paths");
const expected=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/feed_source_collections.json"),"utf8"));
const checks=[],errors=[],external=[];
const check=(name,passed,detail)=>checks.push({name,passed:Boolean(passed),...(detail?{detail}:{})});
let child,browser,origin;
try{
  if(target==="--local"){
    const program=`from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
with TemporaryDirectory(prefix="feed-sources-browser-") as folder:
    fixture=HttpDomainFixture(Path(folder))
    with running_http(fixture,display_name="Baltor") as (base,service):
        print(json.dumps({"origin":base}),flush=True)
        sys.stdin.readline()
`;
    child=spawn(process.env.PYTHON||"python3",["-u","-c",program],{cwd:root,
      env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","pipe"]});
    const lines=createInterface({input:child.stdout});
    origin=await new Promise((accept,reject)=>{
      const timer=setTimeout(()=>reject(new Error("Local fixture start timed out")),15000);
      lines.once("line",line=>{clearTimeout(timer);try{accept(JSON.parse(line).origin);}catch(error){reject(error);}});
      child.once("exit",code=>{clearTimeout(timer);reject(new Error("Local fixture exited: "+code));});
    });
  }else{
    const parsed=new URL(target);
    if(parsed.protocol!=="https:"||parsed.username||parsed.password||parsed.pathname!=="/"||parsed.search||parsed.hash)
      throw new Error("Use an HTTPS origin without a path, credential or query");
    origin=parsed.origin;
  }
  browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  const states=[];
  for(const [index,viewport] of [{width:1440,height:1000},{width:390,height:844}].entries()){
    const context=await browser.newContext({viewport,reducedMotion:"reduce"});
    await context.route("**/*",route=>{if(new URL(route.request().url()).origin===origin)return route.continue();
      external.push(new URL(route.request().url()).origin);return route.abort();});
    const page=await context.newPage();
    page.on("pageerror",error=>errors.push(String(error.message)));
    const answer=await page.goto(origin+"/feeds",{waitUntil:"networkidle"});
    const facts=()=>page.evaluate(()=>({
      title:document.querySelector("h1")?.textContent||"",h1:document.querySelectorAll("h1").length,
      overflow:document.documentElement.scrollWidth-innerWidth,
      ids:[...document.querySelectorAll(".feed-source-card")].map(node=>node.id.replace("collection-","")),
      limits:document.querySelector("#source-collections")?.innerText||"",
      links:[...document.querySelectorAll('#source-collections a[href^="/feeds/"]')].map(node=>node.getAttribute("href")),
      checked:document.querySelector("#source-collections time")?.getAttribute("datetime")||"",
      canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||""
    }));
    const state=await facts();states.push(state);
    check("feeds_page_answers_"+viewport.width,answer.status()===200);
    check("named_collections_match_packaged_directory_"+viewport.width,
      JSON.stringify(state.ids)===JSON.stringify(expected.collections.map(item=>item.id)));
    check("curated_scope_and_checked_date_are_visible_"+viewport.width,
      state.checked===expected.source_docs_checked_on&&/not live digests/.test(state.limits)&&/no daily refresh/.test(state.limits));
    check("page_has_one_customer_heading_and_no_sideways_scroll_"+viewport.width,
      state.h1===1&&state.title==="Updates your agents can use."&&state.overflow<=1);
    check("page_keeps_canonical_identity_"+viewport.width,state.canonical==="https://baltor.ai/feeds");
    const card=page.locator("#collection-hardware-fit");
    await card.locator("summary").click();
    check("agent_task_opens_without_an_account_"+viewport.width,
      await card.locator("details").getAttribute("open")!==null&&(await card.innerText()).includes("Separate memory estimates"));
    await page.evaluate(()=>scrollTo(0,0));
    await page.screenshot({path:pictures[index],fullPage:false,animations:"disabled"});
    if(index===0){
      for(const path of state.links){
        const response=await context.request.get(origin+path);
        check("download_"+path,response.status()===200&&response.headers()["cache-control"]==="public, max-age=300");
        if(path.endsWith(".json")){
          const body=await response.json();
          check("source_reference_not_live_result_"+path,body._baltor?.refresh_mode==="release_curated"
            &&body._baltor?.data_scope==="source_descriptions_only"&&body.items.length>0
            &&body.items.every(item=>!Object.hasOwn(item,"date_published")));
        }
      }
      await page.locator(".feed-source-card").first().evaluate(node=>node.remove());
      const removed=await facts();
      check("removed_collection_is_detected",JSON.stringify(removed.ids)!==JSON.stringify(expected.collections.map(item=>item.id)));
      await page.goto(origin+"/feeds",{waitUntil:"networkidle"});
      await page.locator("#source-collections time").evaluate(node=>node.remove());
      check("removed_freshness_label_is_detected",(await facts()).checked!==expected.source_docs_checked_on);
    }
    await context.close();
  }
  check("no_third_party_requests",external.length===0);
  check("no_browser_errors",errors.length===0);
}catch(error){errors.push(String(error.message||error));check("browser_run_completed",false);}
finally{
  if(browser)await browser.close();
  if(child){child.stdin.end("stop\n");if(child.exitCode===null)await new Promise(accept=>{
    const timer=setTimeout(()=>{child.kill("SIGTERM");accept();},5000);
    child.once("exit",()=>{clearTimeout(timer);accept();});
  });}
}
const result={record_type:"feed_source_browser_acceptance/v1",origin:origin||target,observed_at:new Date().toISOString(),
  credentials_used:false,external_mutations:false,upstream_source_calls:0,checks,errors,external,
  passed:checks.filter(item=>item.passed).length,total:checks.length,all_passed:checks.every(item=>item.passed)&&errors.length===0};
writeFileSync(output,JSON.stringify(result,null,2)+"\n");
console.log(JSON.stringify({output,passed:result.passed,total:result.total,all_passed:result.all_passed,errors}));
process.exitCode=result.all_passed?0:1;
