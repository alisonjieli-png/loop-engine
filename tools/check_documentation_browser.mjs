/* Documentation acceptance on a real loopback service. No credentials leave the fixture.
   Optional second argument is a live public origin: read-only pages only, no local controls. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync,mkdirSync} from "node:fs";
import {resolve,dirname} from "node:path";
const root=resolve(new URL("..",import.meta.url).pathname), assets=resolve(root,"src/loop_engine/core/service_runtime/web_assets");
const output=resolve(process.argv[2] || "artifacts/site-docs-browser.json"), live=process.argv[3] || "";
if(live&&(new URL(live).origin!==live||!live.startsWith("https://")))throw new Error("Live checks require an exact HTTPS origin");
if(existsSync(output))throw new Error("Evidence already exists: "+output);
mkdirSync(dirname(output),{recursive:true});
const index=JSON.parse(readFileSync(resolve(assets,"documentation-index.json"),"utf8")), entries=index.sections.flatMap(s=>s.pages);
const checks=[],screenshots=[],errors=[],blocked=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
let child,browser,base=live;
const source=readFileSync(resolve(assets,"documentation.js"),"utf8");
const boot=`from pathlib import Path
from tempfile import TemporaryDirectory
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
import json,sys
with TemporaryDirectory(prefix="docs-browser-") as folder:
    with running_http(HttpDomainFixture(Path(folder)),display_name="Baltor") as (base,_):
        print(json.dumps({"base":base}),flush=True)
        sys.stdin.readline()
`;
const contrastProblems=target=>target.evaluate(()=>{
  const parse=color=>{const found=color.match(/rgba?\(([^)]+)\)/);if(!found)return null;const part=found[1].split(",").map(Number);return {r:part[0],g:part[1],b:part[2],a:part.length>3?part[3]:1};};
  const channel=value=>{value/=255;return value<=0.03928?value/12.92:Math.pow((value+0.055)/1.055,2.4);};
  const light=color=>0.2126*channel(color.r)+0.7152*channel(color.g)+0.0722*channel(color.b);
  const blend=(top,bottom)=>({r:top.r*top.a+bottom.r*(1-top.a),g:top.g*top.a+bottom.g*(1-top.a),b:top.b*top.a+bottom.b*(1-top.a),a:1});
  const ground=node=>{const layers=[];for(let item=node;item;item=item.parentElement){const color=parse(getComputedStyle(item).backgroundColor);if(color&&color.a>0){layers.push(color);if(color.a>=1)break;}}
    return layers.reverse().reduce((below,layer)=>blend(layer,below),{r:255,g:255,b:255,a:1});};
  const ratio=(one,two)=>{const [high,low]=[light(one),light(two)].sort((x,y)=>y-x);return (high+0.05)/(low+0.05);};
  const problems=[],seen=new Set(),walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode.parentElement;if(!walker.currentNode.textContent.trim()||!node||seen.has(node))continue;seen.add(node);
    const style=getComputedStyle(node);if(!node.getClientRects().length||style.visibility==="hidden"||node.closest("[hidden]"))continue;
    const colour=parse(style.color),below=ground(node);if(!colour)continue;
    const size=parseFloat(style.fontSize),large=size>=24||(parseInt(style.fontWeight,10)>=700&&size>=18.66),need=large?3:4.5,have=ratio(colour.a<1?blend(colour,below):colour,below);
    if(have<need-0.01)problems.push({text:walker.currentNode.textContent.trim().slice(0,40),ratio:Math.round(have*100)/100,need});
  }
  return problems;});

const settle=page=>page.waitForFunction(()=>document.querySelector('#docs-cards li') || (document.querySelector('#docs-status')?.textContent || '').includes('could not be loaded') || (document.querySelector('#docs-status')?.textContent || '').includes('nothing from it') || document.querySelector('#docs-article h2') || document.querySelector('[data-docs-refused]') || document.querySelector('#docs-article .docs-note')?.textContent.includes('documentation list'));
const isAsset=(url,path)=>url.origin===new URL(base).origin&&url.pathname===path&&(!url.search||/^\?v=[a-f0-9]{64}$/.test(url.search));
try{
 if(!live){child=spawn(resolve(root,".venv/bin/python"),["-u","-c",boot],{cwd:root,env:{...process.env,PYTHONPATH:"src"},stdio:["pipe","pipe","pipe"]});
  base=await new Promise((accept,reject)=>{const lines=createInterface({input:child.stdout});const timer=setTimeout(()=>reject(new Error("fixture startup deadline")),15000);lines.once("line",line=>{clearTimeout(timer);accept(JSON.parse(line).base)});child.once("exit",code=>reject(new Error("fixture stopped: "+code)));});}
 browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 await context.route("**/*",route=>new URL(route.request().url()).origin===new URL(base).origin?route.continue():(blocked.push(route.request().url()),route.abort()));
 const page=await context.newPage();page.on("pageerror",e=>errors.push(String(e)));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900});
  for(const entry of [{id:"index",address:"/docs"},...entries.filter(e=>e.body)]){
   await page.goto(base+entry.address);await settle(page);await page.evaluate(()=>document.fonts.ready);
   const facts=await page.evaluate(()=>{const visible=n=>n&&n.getClientRects().length>0;
    const summary=document.getElementById("docs-page-summary"),toc=document.getElementById("docs-toc");
    return {height:document.documentElement.scrollHeight,width:document.documentElement.scrollWidth,viewport:innerWidth,
     cards:[...document.querySelectorAll('#docs-cards li')].map(n=>n.dataset.docsPage),
     header:[...document.querySelectorAll('header')].filter(visible).length,footer:[...document.querySelectorAll('footer')].filter(visible).length,
     title:document.getElementById('docs-page-title').textContent,summary:summary.textContent,
     summaryLines:summary.getBoundingClientRect().height/parseFloat(getComputedStyle(summary).lineHeight),
     titleTop:document.getElementById('docs-page-title').getBoundingClientRect().top,tocTop:toc.getBoundingClientRect().top,tocVisible:visible(toc),
     article:document.getElementById('docs-article').textContent,retired:/\bpilots?\b|\bbetas?\b|early access/i.test(document.querySelector('[data-view="docs"]').innerText)};
   });
   check(`${entry.id}_${width}_layout`,facts.width<=width&&facts.header===1&&facts.footer===1&&!facts.retired,facts);
   if(entry.body)check(`${entry.id}_${width}_content`,facts.title===entry.title&&facts.summary===entry.summary&&facts.article.length>200&&facts.titleTop<900&&
    (width!==1440||(facts.summaryLines<=1.1&&(facts.height<=2700||(facts.tocVisible&&facts.tocTop<900)))),{title:facts.title,summaryLines:facts.summaryLines,height:facts.height,tocTop:facts.tocTop});
   else check(`index_${width}_order`,JSON.stringify(facts.cards)===JSON.stringify(entries.map(e=>e.id))&&(width!==1440||facts.height<=1800),{cards:facts.cards,height:facts.height});
   const file=output.replace(/\.json$/,`-${entry.id}-${width}.png`);if(existsSync(file))throw new Error("Screenshot already exists: "+file);
   await page.screenshot({path:file,fullPage:false});screenshots.push({page:entry.address,width,height:facts.height,path:file});
  }
 }
 await page.setViewportSize({width:1440,height:900});
 for(const entry of entries.filter(e=>e.body)){
  await page.goto(base+"/docs");await settle(page);await page.evaluate(()=>{window.__docsNavigationSentinel="preserved";});
  await page.locator(`[data-docs-page="${entry.id}"] a`).click();await page.waitForFunction(title=>document.getElementById('docs-page-title').textContent===title,entry.title);await page.waitForSelector('#docs-article h2');
  check(`${entry.id}_card_opens_same_document`,await page.evaluate(()=>window.__docsNavigationSentinel==="preserved")&&new URL(page.url()).pathname===entry.address);
  await page.locator('#docs-page a[href="/docs"]').first().click();await page.waitForSelector('#docs-cards li');
  check(`${entry.id}_back_preserves_document`,await page.evaluate(()=>window.__docsNavigationSentinel==="preserved")&&new URL(page.url()).pathname==="/docs");
 }
 await page.goto(base+"/docs/getting-set-up");await page.waitForFunction(()=>document.body.dataset.page==="setup");check("setup_alias_opens_guide",true);
 const indexResponse=await page.request.get(base+"/assets/documentation-index.json");
 check("served_index_matches_versioned_source",indexResponse.ok()&&(indexResponse.headers()["content-type"]||"").startsWith("application/json")&&await indexResponse.text()===readFileSync(resolve(assets,"documentation-index.json"),"utf8"));
 const missing=await page.request.get(base+"/docs/absent");check("unknown_doc_route_is_not_served",missing.status()===404);
 for(const entry of entries.filter(e=>e.body)){const response=await page.request.get(base+entry.body);check(`${entry.id}_served_exact_body`,response.ok()&&(response.headers()["content-type"]||"").startsWith("text/html")&&await response.text()===readFileSync(resolve(assets,"docs",entry.id+".html"),"utf8"));}
 if(!live){
  const mutations=[
   ["unknown_version",r=>r.record_type="website_documentation_index/v99"],
   ["foreign_address",r=>r.sections[0].pages[0].address="https://foreign.invalid/capture"],
   ["foreign_body",r=>r.sections[0].pages[1].body="https://foreign.invalid/body"],
   ["duplicate_identity",r=>r.sections[0].pages[1].id=r.sections[0].pages[0].id],
   ["unknown_field",r=>r.sections[0].pages[1].execute=true],
   ["invalid_review_date",r=>r.reviewed_at="2026-02-31"],
   ["untyped_alias",r=>r.sections[0].pages[0].aliases=[{}]],
   ["null_alias",r=>r.sections[0].pages[0].aliases=null],
  ];
  for(const [name,mutate] of mutations){const p=await context.newPage(),record=structuredClone(index);mutate(record);
   await p.route(url=>isAsset(url,"/assets/documentation-index.json"),route=>route.fulfill({contentType:"application/json",body:JSON.stringify(record)}));
   await p.goto(base+"/docs");await settle(p);check(`refuses_index_${name}`,await p.locator('#docs-cards li').count()===0&&await p.locator('#docs-status').innerText()!=="");await p.close();}
  for(const [name,body] of [["forbidden_element","<h2 id=\"safe\">Allowed heading</h2><form>Forbidden</form>"],["head_script","<script>window.__badDocumentation=true</script><h2 id=\"safe\">Allowed heading</h2>"],["event_attribute","<h2 id=\"safe\" onclick=\"alert(1)\">Allowed heading</h2>"],["foreign_link_missing_rel","<h2 id=\"safe\">Allowed heading</h2><a href=\"https://foreign.invalid/\">Bad link</a>"]]){
   const p=await context.newPage();await p.route(url=>isAsset(url,entries.find(e=>e.body).body),route=>route.fulfill({contentType:"text/html",body}));
   await p.goto(base+entries.find(e=>e.body).address);await settle(p);check(`refuses_body_${name}`,await p.locator('[data-docs-refused="body"]').count()===1&&await p.locator('#docs-article h2').count()===0);await p.close();
  }
  for(const [name,find,replace,body,selector] of [
   ["head",'if (parsed.head.childNodes.length) throw new Refused("unexpected document head");','', '<script>window.__badDocumentation=true</script><h2 id="safe">Allowed heading</h2>', '#docs-article h2'],
   ["element",'!Object.hasOwn(ALLOWED, node.tagName)','false','<h2 id="safe">Allowed heading</h2><form>Forbidden</form>','#docs-article form']]){
   if(!source.includes(find))throw new Error("Missing mutation anchor: "+name);
   const p=await context.newPage();await p.route(url=>isAsset(url,"/assets/documentation.js"),route=>route.fulfill({contentType:"text/javascript",body:source.replace(find,replace)}));
   await p.route(url=>isAsset(url,entries.find(e=>e.body).body),route=>route.fulfill({contentType:"text/html",body}));
   await p.goto(base+entries.find(e=>e.body).address);await settle(p);check(`removed_${name}_guard_exposes_wrong_body`,await p.locator(selector).count()===1&&await p.locator('[data-docs-refused="body"]').count()===0);await p.close();
  }
  const p=await context.newPage();await p.route(url=>isAsset(url,"/assets/documentation.js"),route=>route.fulfill({contentType:"text/javascript",body:source.replace('record.record_type !== INDEX_VERSION','false')}));
  await p.route(url=>isAsset(url,"/assets/documentation-index.json"),route=>route.fulfill({contentType:"application/json",body:JSON.stringify({...index,record_type:"website_documentation_index/v99"})}));
  await p.goto(base+"/docs");await settle(p);check("removed_version_guard_exposes_wrong_index",await p.locator('#docs-cards li').count()===entries.length);await p.close();
 }
 for(const theme of ["light","dark"]){
  await page.evaluate(value=>{document.documentElement.dataset.theme=value;localStorage.setItem("baltor-theme",value);},theme);
  for(const entry of [{id:"index",address:"/docs"},...entries.filter(e=>e.body)]){
   await page.goto(base+entry.address);await settle(page);await page.evaluate(value=>document.documentElement.dataset.theme=value,theme);
   const problems=await contrastProblems(page);check(`${entry.id}_${theme}_text_contrast`,problems.length===0,{problems});
  }
 }
 await page.evaluate(()=>{document.documentElement.dataset.theme="light";const p=document.createElement("p");p.style.cssText="color:#bbb;background:white";p.textContent="Known wrong contrast";document.body.append(p);});
 const contrastControl=await contrastProblems(page);check("contrast_guard_detects_low_contrast",contrastControl.some(row=>row.text==="Known wrong contrast"));
 check("no_unexpected_script_errors",errors.length===0,{errors});check("no_external_requests",blocked.length===0,{blocked});
}catch(error){check("suite_completes",false,{error:String(error)});}finally{await browser?.close();child?.stdin.end("\n");}
const report={record_type:"documentation_browser_check/v1",scope:live?"read-only-public-origin":"loopback-fixture",checks,screenshots,passed:checks.length>0&&checks.every(c=>c.passed)};
writeFileSync(output,JSON.stringify(report,null,2)+"\n");console.log(JSON.stringify({output,checks:checks.length,failed:checks.filter(c=>!c.passed).map(c=>c.name)}));process.exitCode=report.passed?0:1;
