/* Public feed specimen acceptance. Initial observations use real HTTP; fault cases intercept only this browser's reads. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync} from "node:fs";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname);
const [target,outputArgument]=process.argv.slice(2);
if(!target||!outputArgument)throw new Error("Use: check_feed_specimen.mjs --local|HTTPS_ORIGIN NEW_REPORT.json");
const output=resolve(outputArgument),pictures=["-live-desktop.png","-live-mobile.png","-decision-desktop.png","-decision-mobile.png"]
  .map(suffix=>output.replace(/\.json$/,suffix));
if(!output.endsWith(".json")||[output,...pictures].some(existsSync))throw new Error("Refusing to overwrite evidence");
const checks=[],errors=[],outside=[],feedRequests=[],privateRequests=[];
const check=(name,passed,detail)=>checks.push({name,passed:Boolean(passed),...(detail?{detail}:{})});
let child,browser,origin,observedNotice=null;
try{
  if(target==="--local"){
    const program=`from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with TemporaryDirectory(prefix="feed-specimen-browser-") as folder:
    case=Fixture(Path(folder))
    case.publish([case.line("private_fixture_package","NEVER SHOW THIS PRIVATE BODY")])
    fixture=type("Served",(),{"runtime":case.runtime,"provisioning":case.binding()})()
    with running_http(fixture,display_name="Baltor") as (base,service):
        print(json.dumps({"origin":base}),flush=True)
        sys.stdin.readline()
`;
    child=spawn(process.env.PYTHON||"python3",["-u","-c",program],{cwd:root,
      env:{...process.env,PYTHONPATH:resolve(root,"src"),PYTHONDONTWRITEBYTECODE:"1"},stdio:["pipe","pipe","pipe"]});
    const lines=createInterface({input:child.stdout});
    origin=await new Promise((accept,reject)=>{
      const timer=setTimeout(()=>reject(new Error("Fixture start timed out")),15000);
      lines.once("line",line=>{clearTimeout(timer);try{accept(JSON.parse(line).origin);}catch(error){reject(error);}});
      child.once("exit",code=>{clearTimeout(timer);reject(new Error("Fixture exited: "+code));});
    });
  }else{
    const url=new URL(target);
    if(url.protocol!=="https:"||url.pathname!=="/"||url.search||url.hash||url.username||url.password)throw new Error("Use a plain HTTPS origin");
    origin=url.origin;
  }
  browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  for(const [index,viewport] of [{width:1440,height:1000},{width:390,height:844}].entries()){
    const context=await browser.newContext({viewport,reducedMotion:"reduce",acceptDownloads:true});
    await context.addCookies([{name:"feed_specimen_probe",value:"noncredential_probe",url:origin}]);
    let mode="real",synthetic=null;
    await context.route("**/*",async route=>{
      const request=route.request(),url=new URL(request.url());
      if(url.origin!==origin){outside.push(url.origin);return route.abort();}
      if(url.pathname.startsWith("/api/v1/account/")){privateRequests.push(url.pathname);return route.fulfill({status:401,body:"{}"});}
      if(url.pathname!=="/feeds/catalogue.json")return route.continue();
      feedRequests.push({mode,cookiePresent:Boolean((await request.allHeaders()).cookie)});
      if(mode==="real")return route.continue();
      if(mode==="unavailable")return route.fulfill({status:503,contentType:"application/json",body:'{"error":{"code":"catalogue_feed_updating"}}'});
      if(mode==="redirect")return route.fulfill({status:302,headers:{Location:"/api/v1/account/identity"},body:""});
      if(mode==="timeout"){await new Promise(accept=>setTimeout(accept,12000));return route.abort().catch(()=>{});}
      return route.fulfill({status:200,contentType:"application/feed+json",body:JSON.stringify(synthetic)});
    });
    const page=await context.newPage();page.on("pageerror",error=>errors.push(String(error.message)));
    const responsePromise=page.waitForResponse(response=>response.url()===origin+"/feeds/catalogue.json");
    await page.goto(origin+"/feeds",{waitUntil:"networkidle"});
    const response=await responsePromise,raw=await response.text(),feed=JSON.parse(raw),record=feed.items?.[0]?._baltor;
    if(!record)throw new Error("The real anonymous catalogue feed did not provide a snapshot");
    observedNotice=record.notice_id;
    const settled=()=>page.waitForFunction(()=>["ready","unavailable"].includes(document.getElementById("catalogue-specimen")?.dataset.state),null,{timeout:14000});
    const facts=()=>page.evaluate(()=>({state:document.getElementById("catalogue-specimen")?.dataset.state,
      notice:document.getElementById("catalogue-specimen")?.dataset.noticeId,
      shown:!document.getElementById("catalogue-specimen-content")?.hidden,
      packages:document.getElementById("catalogue-specimen-packages")?.textContent,
      files:document.getElementById("catalogue-specimen-files")?.textContent,
      changed:document.getElementById("catalogue-specimen-changed")?.textContent,
      status:document.getElementById("catalogue-specimen-status")?.textContent,
      links:["catalogue-snapshot-json","catalogue-snapshot-markdown"].map(id=>document.getElementById(id)?.getAttribute("href")),
      sideways:document.documentElement.scrollWidth-innerWidth,
      privateText:document.body.innerText.includes("NEVER SHOW THIS PRIVATE BODY")}));
    await settled();const initial=await facts();
    check("real_notice_visible_"+viewport.width,initial.state==="ready"&&initial.shown&&initial.notice===record.notice_id);
    check("display_matches_actual_snapshot_"+viewport.width,initial.packages===record.packages.toLocaleString("en-US")
      &&initial.files===record.distinct_files.toLocaleString("en-US")&&initial.changed===record.state_changed_at);
    check("no_private_body_or_horizontal_page_overflow_"+viewport.width,!initial.privateText&&initial.sideways<=1);
    check("decision_comparison_needs_no_sideways_scroll_"+viewport.width,
      await page.locator("#decision-specimen .md-table-wrap").evaluate(node=>node.scrollWidth-node.clientWidth<=1));
    // Isolated component captures omit fixed navigation. DOM hiding avoids bypassing the page's style policy.
    await page.locator("header").evaluate(node=>{node.hidden=true;});
    await page.locator("#catalogue-specimen").screenshot({path:pictures[index],animations:"disabled"});
    await page.locator("#decision-specimen").screenshot({path:pictures[index+2],animations:"disabled"});
    await page.locator("header").evaluate(node=>{node.hidden=false;});
    check("research_specimen_is_labeled_and_measurements_are_unknown_"+viewport.width,
      /curated example/i.test(await page.locator("#decision-specimen").innerText())
      &&/Workload measurements: not collected/.test(await page.locator("#decision-specimen").innerText()));
    if(index===0){
      synthetic=structuredClone(feed);const next=synthetic.items[0]._baltor;
      next.catalogue_state_revision++;next.notice_id=next.release_id+":"+next.catalogue_state_revision;synthetic.items[0].id=next.notice_id;
      mode="synthetic";
      const before=feedRequests.length;
      for(const [id,extension] of [["catalogue-snapshot-json","json"],["catalogue-snapshot-markdown","md"]]){
        const downloadPromise=page.waitForEvent("download");await page.locator("#"+id).click();
        const download=await downloadPromise,body=readFileSync(await download.path(),"utf8");
        check("same_snapshot_download_"+extension,extension==="json"?body===raw:
          body.includes("`"+record.release_id+"`")&&body.includes("Catalogue state revision: "+record.catalogue_state_revision+"\n")
            &&body.includes(record.state_changed_at)&&body.includes(record.packages.toLocaleString("en-US")+" packages"));
      }
      check("snapshot_downloads_do_not_refetch_a_newer_notice",feedRequests.length===before);
      await page.locator("#catalogue-specimen-refresh").click();await settled();
      check("a_newer_valid_state_is_accepted",(await facts()).notice===next.notice_id);
      synthetic=structuredClone(feed);
      await page.locator("#catalogue-specimen-refresh").click();await settled();
      const stale=await facts();
      check("an_older_state_is_not_displayed_as_current",stale.state==="unavailable"&&!stale.shown
        &&stale.packages===""&&stale.files===""&&stale.links.every(value=>value===null));
      mode="unavailable";await page.locator("#catalogue-specimen-refresh").click();await settled();
      const failed=await facts();
      check("failed_refresh_is_not_zero_or_stale_data",failed.state==="unavailable"&&!failed.shown
        &&failed.packages===""&&failed.files===""&&/not an empty catalogue/.test(failed.status));
      mode="synthetic";synthetic=structuredClone(feed);const zero=synthetic.items[0]._baltor;
      zero.catalogue_state_revision+=2;zero.notice_id=zero.release_id+":"+zero.catalogue_state_revision;zero.packages=0;zero.distinct_files=0;
      synthetic.items[0].id=zero.notice_id;
      synthetic.items[0].content_text=synthetic.items[0].content_text.replace(/^[\d,]+ packages and [\d,]+ distinct files/,"0 packages and 0 distinct files");
      await page.locator("#catalogue-specimen-refresh").click();await settled();
      const empty=await facts();check("valid_zero_population_remains_distinct_from_failure",empty.state==="ready"&&empty.packages==="0"&&empty.files==="0");
      mode="redirect";await page.locator("#catalogue-specimen-refresh").click();await settled();
      check("redirect_is_refused_without_reading_an_account",(await facts()).state==="unavailable"&&privateRequests.length===0);
      mode="timeout";await page.locator("#catalogue-specimen-refresh").click();await settled();
      check("deadline_recovers_to_an_explicit_failure",(await facts()).state==="unavailable"&&await page.locator("#catalogue-specimen-refresh").isEnabled());
    }
    await context.close();
  }
  check("all_feed_requests_omit_cookies",feedRequests.length>0&&feedRequests.every(request=>!request.cookiePresent));
  check("no_private_or_third_party_requests",privateRequests.length===0&&outside.length===0);
  check("no_browser_errors",errors.length===0);
}catch(error){errors.push(String(error.message||error));check("specimen_acceptance_completed",false);}
finally{
  if(browser)await browser.close();
  if(child){child.stdin.end("stop\n");if(child.exitCode===null)await new Promise(accept=>{
    const timer=setTimeout(()=>{child.kill("SIGTERM");accept();},5000);
    child.once("exit",()=>{clearTimeout(timer);accept();});
  });}
}
const result={record_type:"feed_specimen_browser_acceptance/v1",origin:origin||target,observed_at:new Date().toISOString(),
  observed_notice:observedNotice,credentials_used:false,external_mutations:false,upstream_source_calls:0,
  fault_control_scope:"Later cases replace this browser's feed responses only. They are not live catalogue publications.",
  checks,errors,outside,feedRequests,privateRequests,passed:checks.filter(item=>item.passed).length,total:checks.length,
  all_passed:checks.every(item=>item.passed)&&errors.length===0};
writeFileSync(output,JSON.stringify(result,null,2)+"\n");
console.log(JSON.stringify({output,passed:result.passed,total:result.total,all_passed:result.all_passed,errors}));
process.exitCode=result.all_passed?0:1;
