/* Local transport/playback check of the packaged, separately reviewed originals.
   It never writes an approval, publishes media, signs in or calls an external service.
   Usage: PYTHON=... node tools/check_gallery_original_media.mjs NEW_DIRECTORY */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,mkdirSync,writeFileSync,readFileSync} from "node:fs";
import {createHash} from "node:crypto";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname),output=resolve(process.argv[2]||"");
if(!process.argv[2]||existsSync(output))throw Error("A new report directory is required.");
mkdirSync(output,{mode:0o700});
const checks=[],errors=[],blocked=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const sourceDigests=Object.fromEntries(["gallery_media.py","gallery_random.py","web_assets/gallery-random.js","web_assets/gallery-media/media.json"].map(name=>
  [name,createHash("sha256").update(readFileSync(resolve(root,"src/loop_engine/core/service_runtime",name))).digest("hex")]));
const SCRIPT=`from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json, sys
from loop_engine.core.service_runtime import gallery_media
data = gallery_media.media_record()
before = gallery_media.media_assets()
for item in data['items']:
    if item['review']['status'] != 'approved':
        assert gallery_media.PREFIX + item['preview']['file'] not in before
        assert gallery_media.PREFIX + item['source']['archive']['file'] not in before
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.http_test_fixtures import running_http
with ExitStack() as stack:
    folder=Path(stack.enter_context(TemporaryDirectory(prefix='gallery-original-local-')))
    (folder/'intelligence').mkdir()
    held=prepared(folder/'intelligence')
    factory=lambda config: ServiceHttpApplication(held.runtime,held.provisioning,config,access_administration=held.administration)
    base,_=stack.enter_context(running_http(held,application_factory=factory,display_name='Baltor'))
    print(json.dumps({'base':base,'local_transport_only':True}),flush=True)
    sys.stdin.readline()
`;
let child,browser;
try {
  child=spawn(process.env.PYTHON||"python3",["-c",SCRIPT],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},stdio:["pipe","pipe","pipe"]});
  let stderr="";child.stderr.on("data",chunk=>{stderr+=chunk;});
  const {base}=await new Promise((done,fail)=>{
    const lines=createInterface({input:child.stdout}),timer=setTimeout(()=>fail(Error("Fixture timeout: "+stderr)),30000);
    lines.once("line",line=>{clearTimeout(timer);lines.close();done(JSON.parse(line));});
    child.once("exit",code=>{clearTimeout(timer);fail(Error("Fixture exit "+code+": "+stderr));});
  });
  browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  for(const viewport of [{width:1440,height:900},{width:390,height:844}]) {
    const context=await browser.newContext({viewport,reducedMotion:"reduce"});
    await context.route("**/*",route=>{
      const request=route.request(),allowed=new URL(request.url()).origin===base&&["GET","HEAD"].includes(request.method());
      if(!allowed)blocked.push({url:request.url(),method:request.method()});
      return allowed?route.continue():route.abort();
    });
    const page=await context.newPage();page.on("pageerror",error=>errors.push(String(error)));
    for(const [kind,tag,title]of [["video","video","Copper Current"],["music","audio","First Light"]]) {
      const where={kind,width:viewport.width};
      const response=await page.goto(base+"/random/"+kind);
      await page.waitForFunction(()=>document.querySelector("[data-asset-card]")&&!document.querySelector("[data-asset-card]").hidden);
      check("media page and source identity are explicit",response.status()===200
        &&(await page.locator("[data-asset-title]").textContent())===title
        &&(await page.locator("[data-asset-access]").textContent()).includes("not a library item"),where);
      check("only preview is not falsely randomized",await page.locator("[data-show-another]").isDisabled(),where);
      check("media does not autoplay",await page.locator(tag).evaluate(node=>node.paused&&!node.autoplay),where);
      await page.locator(tag).evaluate(node=>{node.muted=true;}); // Technical playback, not a listening review.
      const box=await page.locator(tag).boundingBox();
      await page.locator(tag).click({position:{x:Math.min(30,box.width/2),y:Math.max(10,box.height-20)}});
      await page.locator(tag).evaluate(node=>node.play());
      await page.waitForFunction(tag=>document.querySelector(tag).currentTime>0.2,tag);
      const playback=await page.locator(tag).evaluate(node=>({duration:node.duration,time:node.currentTime,ready:node.readyState}));
      check("native browser decodes and progresses",playback.ready>=2&&playback.time>0.2&&Math.abs(playback.duration-12)<0.1,{...where,playback});
      await page.locator(tag).evaluate(node=>node.pause());
      const source=await page.locator("[data-asset-source]").getAttribute("href");
      const expected=await page.locator("[data-asset-version]").textContent();
      const zip=await context.request.get(base+source),body=await zip.body();
      check("public editable source ZIP has exact reviewed bytes",source.startsWith("/assets/gallery-media/")
        &&zip.status()===200&&zip.headers()["content-type"].includes("application/zip")
        &&createHash("sha256").update(body).digest("hex")===expected&&body.length<262144,where);
      check("explicit MIT preview and source licence",(await page.locator("[data-asset-licence]").textContent())==="MIT"
        &&(await page.locator("[data-asset-source-licence]").textContent())==="MIT",where);
      check("phone and desktop stay within viewport",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),where);
      await page.screenshot({path:resolve(output,kind+"-"+viewport.width+".png"),fullPage:true});
      const permalink=await page.locator("[data-asset-permalink]").getAttribute("href");
      await page.goto(base+permalink);
      await page.waitForFunction(()=>!document.querySelector("[data-asset-card]").hidden);
      check("media permalink restores exact title",(await page.locator("[data-asset-title]").textContent())===title,where);
    }
    await context.close();
  }
  check("no external or effectful browser request",blocked.length===0,{blocked});
  check("no browser script error",errors.length===0,{errors});
} catch(error) {errors.push(String(error));check("fixture qualification completed",false,{error:String(error)});}
finally {
  if(browser)await browser.close();if(child)child.stdin.end("\n");
  const report={record_type:"private_original_media_browser_check/v1",observed_at:new Date().toISOString(),sourceDigests,
    in_memory_review_fixture_only:false,publication_approval:false,listening_performed:false,
    checks,errors,blocked,passed:checks.every(row=>row.passed)};
  writeFileSync(resolve(output,"report.json"),JSON.stringify(report,null,2)+"\n",{flag:"wx"});
  console.log(JSON.stringify({passed:report.passed,checks:checks.length,failed:checks.filter(row=>!row.passed),output}));
  process.exitCode=report.passed?0:1;
}
