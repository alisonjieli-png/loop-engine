/* Browser checks of the model directory pages: /models, /endpoints, /can-i-run and their detail pages.
   tools/check_service_workspace.mjs runs them against its first real loopback service and adds their served files and pages
   to its word rules. Each check compares the page with an answer computed separately: the page's can-I-run result with the
   service's own Python formula for every hardware preset, and the page's search and order with the Python order. The removed-
   guard controls change the served page script in memory only, for one control run, and each must fail its named check. */
import {spawnSync} from "node:child_process";
import {existsSync,readFileSync} from "node:fs";
import {resolve} from "node:path";
import {registerListingText,withoutListingText} from "./listing_text.mjs";

const root=resolve(new URL("..",import.meta.url).pathname);
export const MODEL_DIRECTORY_PAGES=["/models","/endpoints","/can-i-run"];
export const MODEL_DIRECTORY_FILES=["/assets/model-directory.css","/assets/model-directory.js","/assets/model-directory/search-index.json","/assets/model-directory/fit-index.json"];
const SCREENSHOTS=["-models-desktop.png","-models-mobile.png","-endpoints-desktop.png","-endpoints-mobile.png","-can-i-run-desktop.png","-can-i-run-mobile.png","-model-page-desktop.png","-model-page-mobile.png"];
/* The two indexes hold only listing rows under "rows": names, makers and licences other publishers wrote, and numbers. The pages
   mark every listing field with data-listing-text. Everything else is read by the word rules. */
for(const path of MODEL_DIRECTORY_FILES.filter(path=>path.endsWith(".json")))registerListingText(path,{fields:["rows"]});
for(const path of MODEL_DIRECTORY_PAGES)registerListingText(path,{page:true});

/* The answers the pages must give, computed by the service's own Python modules from the same packaged files. */
const EXPECTED=`import json, sys
from loop_engine.core.service_runtime import model_directory as records, model_directory_format as fmt, model_directory_hub as hub
from loop_engine.core.service_runtime.web_site_map import load_site_map
directory = records.load_directory()
hardware = directory.hardware
presets = {}
for preset in hardware["presets"]:
    for context in (8192, 32768):
        found, unknown = hub.fit_results(directory.models, hub.device_from_preset(preset, hardware["system_memory_default"]), context)
        presets[preset["id"] + "@" + str(context)] = {"results": [[item.slug, item.quantization, item.fit.context, item.fit.kind] for item in found], "unknown": unknown}
query = "qwen"
matching = [row for row in directory.models if query in (row["name"] + " " + row["maker"] + " " + row["slug"]).lower()]
licence = next(row for row in fmt.order_models(directory.models) if "licence" not in row["facts"] and row["prices"])
stale = next((row for row in directory.models if any(records.price_is_stale(price, sys.argv[1]) for price in row["prices"])), None)
sample = next(row for row in fmt.order_models(directory.models) if row["quantizations"] and row["prices"] and "architecture" in row["facts"])
print(json.dumps({"presets": presets, "preset_ids": [item["id"] for item in hardware["presets"]], "query": query,
                  "query_order": [row["slug"] for row in fmt.order_models(matching)],
                  "first_page": [row["slug"] for row in fmt.order_models(directory.models)][:40],
                  "names": {row["slug"]: row["name"] for row in directory.models},
                  "unknown_licence": licence["slug"], "stale": stale["slug"] if stale else "", "sample": sample["slug"],
                  "endpoints": [row["slug"] for row in fmt.order_endpoints(directory.endpoints)], "models": len(directory.models),
                  "canonical_origin": records.SCHEME + "://" + load_site_map().canonical_hostname}))
`;

function expectedAnswers(){
  const today=new Date().toISOString().slice(0,10);
  const python=process.env.PYTHON||(existsSync(resolve(root,".venv/bin/python"))?resolve(root,".venv/bin/python"):"python3");
  const run=spawnSync(python,["-c",EXPECTED,today],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},encoding:"utf8",maxBuffer:256*1024*1024});
  if(run.status!==0)throw new Error("The directory's own answers could not be computed: "+run.stderr.slice(-800));
  return JSON.parse(run.stdout);
}

/* What one rendered page says about itself, read in the page. */
const pageFacts=target=>target.evaluate(()=>{
  const ld=[...document.querySelectorAll('script[type="application/ld+json"]')].map(node=>{try{return JSON.parse(node.textContent);}catch(_){return null;}});
  const view=document.querySelector("[data-view]");
  return {title:document.title,canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||"",
    description:document.querySelector('meta[name="description"]')?.getAttribute("content")||"",h1:[...document.querySelectorAll("h1")].length,
    ld:ld.map(item=>item&&item["@type"]),view:view?.dataset.view||"",header:Boolean(document.querySelector("header nav")),
    footerGroups:[...document.querySelectorAll("footer nav")].map(nav=>nav.getAttribute("aria-label")),
    disclosure:document.getElementById("paid-links")?.innerText||"",order:document.querySelector(".md-order")?.innerText||"",
    paid:[...document.querySelectorAll('a[rel~="sponsored"]')].length,overflow:document.documentElement.scrollWidth-innerWidth,
    height:document.documentElement.scrollHeight,unlabelled:[...document.querySelectorAll('[data-listing-text]')].filter(node=>!node.closest("main")).length};
});

export async function runModelDirectoryChecks({browser,base,check,mutants,errors,localOnly,screenshot}){
  for(const suffix of SCREENSHOTS)if(existsSync(screenshot(suffix)))throw new Error("Refusing to overwrite an existing browser evidence artifact: "+screenshot(suffix));
  const expected=expectedAnswers();
  /* The registration is narrow: listing rows of the two indexes and marked elements of the three pages are left out of the word
     rules, and a word in an index's envelope, in an unmarked part of a page or in an unregistered file is still read. */
  const planted=(envelope,listing)=>JSON.stringify({record_type:"model_directory_search_index/v1"+envelope,fields:["slug","name"],rows:[["x",listing]]});
  const reads=(path,text)=>/\bbetas?\b|\binvit/i.test(withoutListingText(path,text));
  check("model_directory_listing_text_rule_reads_everything_but_its_registered_rows",
    !reads("/assets/model-directory/search-index.json",planted("","zephyr-7b-beta"))&&reads("/assets/model-directory/search-index.json",planted(" beta","x"))
    &&!reads("/assets/model-directory/fit-index.json",planted("","Invite model"))&&reads("/assets/model-directory/unregistered.json",planted("","zephyr-7b-beta"))
    &&!reads("/models",'<li><span data-listing-text>zephyr-7b-beta</span></li>')&&reads("/models",'<h2>Private beta</h2><span data-listing-text>x</span>'));
  const titles={"/models":"Baltor | Models, open and hosted","/endpoints":"Baltor | Endpoints and local runtimes","/can-i-run":"Baltor | Can I run it?"};
  /* The canonical origin comes from the typed site map's hostname, through the same Python answer. */
  const canonicalOrigin=expected.canonical_origin;
  const outside=[];
  const open=async (viewport,mutation=null,state={applied:false})=>{
    const context=await browser.newContext({viewport,reducedMotion:"reduce"});
    await context.route("**/*",route=>{const url=new URL(route.request().url());if(url.origin!==new URL(base).origin){outside.push(url.origin);return route.abort();}
      if(mutation&&url.pathname==="/assets/model-directory.js")return route.fetch().then(async response=>{const source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);
        state.applied=changed!==source;return route.fulfill({response,body:changed});});
      return localOnly?localOnly(route):route.continue();});
    const page=await context.newPage();page.on("pageerror",error=>{if(!mutation)errors.push("model directory: "+String(error.message||error));});
    return {context,page};
  };
  const load=async (page,address)=>{const response=await page.goto(base+address,{waitUntil:"load"});await page.waitForLoadState("networkidle",{timeout:15000}).catch(()=>{});return response;};

  /* The three pages and one model and one endpoint page, at a desktop and a phone. */
  const facts={},pictures=[];
  for(const [label,viewport] of [["desktop",{width:1440,height:900}],["mobile",{width:390,height:844}]]){
    const {context,page:first}=await open(viewport);
    await first.close();
    for(const address of [...MODEL_DIRECTORY_PAGES,"/models/"+expected.sample,"/endpoints/"+expected.endpoints[0]]){
      /* A fresh tab for each page, closed after it is read, keeps one long run from piling up renderer memory. */
      const page=await context.newPage();page.on("pageerror",error=>errors.push("model directory: "+String(error.message||error)));
      const response=await load(page,address);
      facts[address+"@"+label]={status:response.status(),...await pageFacts(page)};
      const name=address==="/models/"+expected.sample?"model-page":address.startsWith("/endpoints/")?null:address.slice(1);
      await page.close();
      /* A very tall full-page picture can end the renderer on a busy machine, so the picture keeps the top of the page, taken in a
         fresh tab, and a second, shorter attempt follows a crash. A picture that still fails is a named failure, not a stop. */
      if(name){
        let taken=false;
        for(const limit of [3600,1800]){
          const shot=await context.newPage();
          try{await load(shot,address);const height=await shot.evaluate(()=>document.documentElement.scrollHeight);
            await shot.screenshot({path:screenshot("-"+name+"-"+label+".png"),fullPage:true,animations:"disabled",clip:{x:0,y:0,width:viewport.width,height:Math.min(height,limit)}});taken=true;}
          catch(_){}
          await shot.close().catch(()=>{});
          if(taken)break;
        }
        pictures.push([name+"-"+label,taken]);
      }
    }
    await context.close();
  }
  check("model_directory_pictures_are_taken_at_1440_and_390",pictures.length===8&&pictures.every(([,taken])=>taken),{pictures});
  const pageProblems=Object.entries(facts).flatMap(([key,item])=>{const address=key.split("@")[0],problems=[];
    if(item.status!==200)problems.push(key+" answered "+item.status);
    if(titles[address]&&item.title!==titles[address])problems.push(key+" is titled "+item.title);
    if(item.canonical!==canonicalOrigin+address)problems.push(key+" names the canonical address "+item.canonical);
    if(item.h1!==1)problems.push(key+" shows "+item.h1+" h1 headings");
    if(!item.ld.length||item.ld.some(type=>!type))problems.push(key+" has no readable structured data");
    if(!item.header||item.footerGroups.length<4)problems.push(key+" lacks the shared header or footer");
    if(!item.disclosure.includes("No link in this directory is a paid link"))problems.push(key+" lacks the paid links section");
    if(item.paid!==0)problems.push(key+" shows "+item.paid+" paid links while every row has no relationship");
    if(item.overflow>1)problems.push(key+" scrolls sideways by "+item.overflow);
    if(item.description.length<50)problems.push(key+" has no page description");
    return problems;});
  check("model_directory_pages_answer_with_their_own_title_canonical_structured_data_and_one_h1",pageProblems.length===0,{problems:pageProblems});
  const descriptions=new Set(Object.entries(facts).filter(([key])=>key.endsWith("@desktop")).map(([,item])=>item.title+"|"+item.description));
  check("model_directory_pages_have_distinct_titles_and_descriptions",descriptions.size===5,{distinct:descriptions.size});
  check("model_directory_lists_say_how_they_are_ordered",["/models@desktop","/endpoints@desktop","/can-i-run@desktop"].every(key=>/Payment never changes/.test(facts[key].order)),
    {orders:Object.fromEntries(["/models@desktop","/endpoints@desktop","/can-i-run@desktop"].map(key=>[key,facts[key].order]))});

  /* The model page: an unknown licence says Unknown, and a price older than the stale limit shows its date and the mark. */
  const {context:detailContext,page:detail}=await open({width:1440,height:900});
  await load(detail,"/models/"+expected.unknown_licence);
  const licenceText=await detail.evaluate(()=>{const term=[...document.querySelectorAll(".md-dl dt")].find(node=>node.textContent==="Licence");return term?.nextElementSibling?.textContent||"";});
  check("a_model_without_a_licence_shows_unknown",licenceText.trim()==="Unknown",{model:expected.unknown_licence,shown:licenceText});
  if(expected.stale){
    await load(detail,"/models/"+expected.stale);
    const stale=await detail.evaluate(()=>[...document.querySelectorAll("#prices tbody tr")].map(row=>({date:row.querySelector("time")?.getAttribute("datetime")||"",mark:Boolean(row.querySelector(".md-stale"))})));
    const today=new Date().toISOString().slice(0,10),old=row=>(Date.parse(today)-Date.parse(row.date))/86400000>30;
    check("a_stale_price_is_shown_with_its_date",stale.length>0&&stale.every(row=>/^\d{4}-\d{2}-\d{2}$/.test(row.date)&&row.mark===old(row))&&stale.some(row=>row.mark),{model:expected.stale,rows:stale.slice(0,8)});
  }else check("a_stale_price_is_shown_with_its_date",false,{reason:"no packaged price is older than the stale limit, so the check has no case"});
  await detailContext.close();

  /* The model list: the first page, then a search, in the Python order. */
  const listScenario=async (page,note)=>{
    await load(page,"/models");
    const first=await page.$$eval("[data-models-list] .md-row-link",links=>links.map(link=>link.getAttribute("href").slice("/models/".length)));
    note("model_directory_first_page_is_in_the_stated_order",JSON.stringify(first)===JSON.stringify(expected.first_page));
    await page.fill('[data-models-filter] input[name="q"]',expected.query);
    await page.waitForFunction(query=>document.querySelector("[data-models-count]").textContent.includes("that match"),expected.query,{timeout:15000}).catch(()=>{});
    while(await page.locator("[data-models-more]").isVisible())await page.click("[data-models-more]");
    const found=await page.$$eval("[data-models-list] .md-row-link",links=>links.map(link=>link.getAttribute("href").slice("/models/".length)));
    note("model_directory_search_matches_the_python_order",JSON.stringify(found)===JSON.stringify(expected.query_order));
    return {first:first.length,found:found.length};
  };

  /* The hardware check: every preset at two context lengths gives the answer the Python formula gives, in the page. */
  const fitScenario=async (page,note)=>{
    const requests=[];page.on("request",request=>requests.push(new URL(request.url()).pathname));
    await load(page,"/can-i-run");
    const server=await page.$$eval("[data-fit-results] tr th a",links=>links.map(link=>link.getAttribute("href").slice("/models/".length)));
    const firstPreset=expected.presets[expected.preset_ids.includes("rtx-5090")?"rtx-5090@8192":expected.preset_ids[0]+"@8192"];
    note("can_i_run_page_renders_the_first_preset_without_the_script",JSON.stringify(server)===JSON.stringify(firstPreset.results.slice(0,server.length).map(item=>item[0]))&&server.length>0);
    await page.waitForFunction(()=>window.baltorFit&&window.baltorFit.ready(),null,{timeout:20000});
    const mismatches=[];
    for(const id of expected.preset_ids)for(const context of [8192,32768]){
      await page.selectOption('[data-fit-form] select[name="preset"]',id);
      await page.selectOption('[data-fit-form] select[name="context"]',String(context));
      const shown=await page.evaluate(()=>{const outcome=window.baltorFit.compute();return {results:outcome.found.map(item=>[item.model.slug,item.name,item.fit.context,item.fit.kind]),unknown:outcome.unknownCount};});
      const want=expected.presets[id+"@"+context];
      if(JSON.stringify(shown.results)!==JSON.stringify(want.results)||shown.unknown!==want.unknown)mismatches.push({preset:id,context,shown:shown.results.length,expected:want.results.length,
        first:(shown.results.find((item,index)=>JSON.stringify(item)!==JSON.stringify(want.results[index]))||null)});
    }
    note("can_i_run_matches_the_python_formula_on_every_preset",mismatches.length===0);
    const leaves=requests.filter(path=>!["/can-i-run","/api/v1/capabilities","/assets/model-directory/fit-index.json"].includes(path)&&!path.startsWith("/assets/"));
    note("can_i_run_sends_nothing_about_the_hardware",leaves.length===0);
    return {presets:expected.preset_ids.length,mismatches:mismatches.slice(0,5),other_requests:leaves};
  };

  const scenarios={list:listScenario,fit:fitScenario};
  const details={};
  for(const [name,scenario] of Object.entries(scenarios)){
    const {context,page}=await open({width:1440,height:900});
    details[name]=await scenario(page,(check_name,passed)=>check(check_name,passed,details[name]||{}));
    await context.close();
  }
  check("model_directory_pages_request_nothing_from_another_origin",outside.length===0,{origins:[...new Set(outside)]});

  /* Removed-guard controls: each changes the served page script in memory only, and its named check must fail. */
  const controls=[
    {name:"model_directory_fit_without_the_factor_for_keys_and_values",scenario:"fit",find:"? 2 * model.layers * model.kv_heads",replacement:"? model.layers * model.kv_heads",
     expected:["can_i_run_matches_the_python_formula_on_every_preset"]},
    {name:"model_directory_fit_without_the_runtime_overhead",scenario:"fit",find:"formula.overhead_fixed_bytes + formula.overhead_weight_fraction * weights",replacement:"0",
     expected:["can_i_run_matches_the_python_formula_on_every_preset"]},
    {name:"model_directory_search_ordered_by_name",scenario:"list",find:"|| orders.providers;",replacement:"&& orders.name;",
     expected:["model_directory_search_matches_the_python_order"]},
    {name:"model_directory_search_that_ignores_the_maker",scenario:"list",find:'(row.name + " " + row.maker + " " + row.slug)',replacement:"row.name",
     expected:["model_directory_search_matches_the_python_order"]}];
  for(const control of controls){
    const failed=new Set(),state={applied:false};let problem="";
    try{const {context,page}=await open({width:1440,height:900},control,state);await scenarios[control.scenario](page,(name,passed)=>{if(passed!==true)failed.add(name);});await context.close();}
    catch(error){problem=String(error.message||error).slice(0,300);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=state.applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied:state.applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied:state.applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  return {pages:Object.keys(facts).length,models:expected.models,presets:expected.preset_ids.length,details};
}
