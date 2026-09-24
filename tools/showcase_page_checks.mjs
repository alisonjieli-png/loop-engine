/* The pages of September 24, 2026 in a real browser: the demonstration of one task, the service status, the examples gallery,
   the three case studies and the four audience pages, and the page each hostname shows at its root address.

   tools/check_service_workspace.mjs imports this module and calls runShowcasePageChecks once, with its own real browser, its
   loopback services and its check and removed-guard lists, so this file adds checks and controls to the one report and starts no
   service of its own. The site map and the layout standard are read through their typed reader, web_site_map.py.

   Each check below names what it proves. A removed-guard control serves changed bytes of public-pages.js or service.js in
   memory, for one browser context, and requires the named checks to fail; no source file is changed. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawnSync} from "node:child_process";
import {readFileSync} from "node:fs";
import {resolve} from "node:path";

/* Every page this module opens, in the order of the site map. */
export const showcasePaths=["/demo","/demo/kaggle","/status","/examples","/case-studies/data-cleanup","/case-studies/pi-and-gemma-4","/case-studies/sign-up-protection",
  "/for/coding-agents","/for/engineering-teams","/for/comparing-tools","/for/protocol-and-client"];
const slug=path=>path.slice(1).replace(/\//g,"-");
/* The screenshots this module writes beside the report, one for each page at 1440 and at 390 pixels. */
export const showcaseScreenshotSuffixes=showcasePaths.flatMap(path=>["-showcase-"+slug(path)+"-desktop.png","-showcase-"+slug(path)+"-mobile.png"]);

const READER=`import json
from loop_engine.core.service_runtime.web_site_map import as_plain_record, load_layout_standard, load_site_map
print(json.dumps({"site_map": as_plain_record(load_site_map()), "layout": as_plain_record(load_layout_standard())}))`;

/* The folder roots the demonstration offers for each harness, as tools/install_selected_material.py places a project skill.
   tools/test_showcase_pages.py compares the page script with the placement tool; this check compares the page with the script. */
const skillRoots={"claude-code":".claude/skills/","codex":".agents/skills/","opencode":".opencode/skills/","pi":".pi/skills/"};

export async function runShowcasePageChecks({root,python,browser,context,fixture,check,mutants,output,safeError,words,localOnly}){
  const read=spawnSync(python,["-c",READER],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},encoding:"utf8"});
  if(read.status!==0)throw new Error("The typed reader refused the website records:\n"+read.stderr);
  const {site_map:siteMap,layout}=JSON.parse(read.stdout);
  const canonicalOrigin="https://"+siteMap.canonical_hostname,pageAt=address=>siteMap.pages.find(item=>item.address===address);
  const base=fixture.base;
  const shownState=target=>target.evaluate(()=>({views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),
    title:document.title,canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||"",brand:document.querySelector("header a.brand")?.getAttribute("href")||"",
    h1:[...document.querySelectorAll("h1")].filter(node=>node.getClientRects().length>0).length,height:document.documentElement.scrollHeight,
    overflow:document.documentElement.scrollWidth>innerWidth+1}));
  const opensItsPage=(state,entry)=>Boolean(entry)&&JSON.stringify(state.views)===JSON.stringify([entry.view])&&state.title===siteMap.display_name+" | "+entry.title
    &&state.canonical===canonicalOrigin+entry.address&&state.h1===1;

  /* Each page at its own address: one view, one visible heading, its own title and its canonical address on the canonical hostname,
     within its scroll budget at 1440 by 900 and at 390 by 844, with a screenshot of each size beside the report. */
  const budgets=entry=>{const desktop=layout.page_height_max_px[entry.scroll_budget];if(!desktop)return null;
    return {desktop,phone:Math.floor(desktop/layout.viewports.desktop.height)*layout.phone_screens_factor*layout.viewports.phone.height};};
  const withinBudget=(heights,limits)=>!limits||(heights.desktop<=limits.desktop&&heights.phone<=limits.phone);
  const page=await context.newPage(),heights={};
  for(const path of showcasePaths){
    const direct=await page.request.get(base+path,{maxRedirects:0});
    await page.setViewportSize({width:layout.viewports.desktop.width,height:layout.viewports.desktop.height});
    await page.goto(base+path);await page.evaluate(()=>document.fonts.ready);
    const desktop=await shownState(page);
    await page.screenshot({path:output.replace(/\.json$/,"-showcase-"+slug(path)+"-desktop.png"),fullPage:true});
    await page.setViewportSize({width:layout.viewports.phone.width,height:layout.viewports.phone.height});
    await page.goto(base+path);await page.evaluate(()=>document.fonts.ready);
    const phone=await shownState(page);
    await page.screenshot({path:output.replace(/\.json$/,"-showcase-"+slug(path)+"-mobile.png"),fullPage:true});
    heights[path]={desktop:desktop.height,phone:phone.height};
    check("showcase_page_opens_with_its_own_title_and_canonical_address_"+slug(path),direct.status()===200&&(direct.headers()["content-type"]||"").startsWith("text/html")
      &&opensItsPage(desktop,pageAt(path))&&!phone.overflow,{desktop:{views:desktop.views,title:desktop.title,canonical:desktop.canonical,h1:desktop.h1},phone_overflow:phone.overflow});
  }
  const overBudget=showcasePaths.filter(path=>!withinBudget(heights[path],budgets(pageAt(path))));
  check("showcase_pages_stay_within_their_scroll_budgets",overBudget.length===0,{heights,over:overBudget});
  check("scroll_budget_check_rejects_a_page_one_screen_too_tall",!withinBudget({desktop:2701,phone:100},{desktop:2700,phone:5064})&&!withinBudget({desktop:100,phone:5065},{desktop:2700,phone:5064})
    &&withinBudget({desktop:2700,phone:5064},{desktop:2700,phone:5064}));
  await page.setViewportSize({width:1440,height:1000});

  /* The demonstration: one step at a time, moved by its list, by Previous and Next and by Play, which stops at the last step; the
     folder follows the harness the reader picks; every step reads when the script has not run. */
  const demoState=target=>target.evaluate(()=>{const demo=document.querySelector("[data-view]:not([hidden]) [data-task-demo]");
    return {shown:[...(demo?.querySelectorAll("[data-task-step]")||[])].filter(node=>node.getClientRects().length>0).map(node=>node.dataset.taskStep),
      current:[...(demo?.querySelectorAll("[data-task-go]")||[])].findIndex(node=>node.getAttribute("aria-current")==="step")+1,
      roots:[...new Set([...(demo?.querySelectorAll("[data-task-skill-root]")||[])].map(node=>node.textContent))],
      controls:Boolean(demo?.querySelector("[data-task-controls]")?.getClientRects().length),
      labels:[...(demo?.querySelectorAll("[data-task-step]")||[])].filter(node=>node.getClientRects().length>0).map(node=>[node.querySelector('.task-step-head [data-task-label]')?.textContent.trim()||"",
        node.querySelector('[data-task-stage="folder"] [data-task-label]')?.textContent.trim()||""]),
      steps:[...(demo?.querySelectorAll("[data-task-step]")||[])].map(node=>node.dataset.taskStep)};});
  const stepNames=async target=>(await demoState(target)).steps;
  const oneAtATime=(state,name)=>JSON.stringify(state.shown)===JSON.stringify([name]);
  const openDemo=async mutation=>{
    const opened=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"}),target=await opened.newPage(),state={applied:false};
    await opened.route("**/*",localOnly);target.on("pageerror",error=>state.error=safeError(error.message));
    await target.clock.install();
    if(mutation)await target.route(url=>url.origin===new URL(base).origin&&url.pathname===mutation.path,async route=>{const response=await route.fetch(),source=await response.text(),
      changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    await target.goto(base+"/demo");await target.waitForSelector("[data-task-controls]:not([hidden])",{timeout:10000}).catch(()=>{});
    return {opened,target,state};
  };
  const demoScenario=async (target,note)=>{
    const names=await stepNames(target);
    const first=await demoState(target);
    await target.locator('[data-view="demo"] [data-task-go="3"]').click();const third=await demoState(target);
    await target.locator('[data-view="demo"] [data-task-move="next"]').click();const fourth=await demoState(target);
    await target.locator('[data-view="demo"] [data-task-move="previous"]').click();const back=await demoState(target);
    note("demo_shows_one_step_at_a_time_and_moves_by_its_list",names.length===5&&first.controls&&oneAtATime(first,names[0])&&first.current===1&&oneAtATime(third,names[2])
      &&third.current===3&&oneAtATime(fourth,names[3])&&oneAtATime(back,names[2]),{first,third,fourth,back});
    await target.locator('[data-view="demo"] [data-task-go="1"]').click();await target.locator('[data-view="demo"] [data-task-play]').click();
    await target.clock.runFor(3600);const played=await demoState(target);
    await target.clock.runFor(3600*6);const ended=await demoState(target);
    note("demo_play_moves_through_the_steps_and_stops_at_the_last",oneAtATime(played,names[1])&&oneAtATime(ended,names[4])&&await target.locator('[data-view="demo"] [data-task-play]').getAttribute("aria-pressed")==="false",
      {played:played.shown,ended:ended.shown});
    await target.locator('[data-view="demo"] [data-task-harness="pi"]').click();const pi=await demoState(target);
    await target.locator('[data-view="demo"] [data-task-harness="codex"]').click();const codex=await demoState(target);
    note("demo_folder_follows_the_chosen_harness",JSON.stringify(pi.roots)===JSON.stringify([skillRoots.pi])&&JSON.stringify(codex.roots)===JSON.stringify([skillRoots.codex])
      &&first.roots.length===1&&first.roots[0]===skillRoots["claude-code"],{first:first.roots,pi:pi.roots,codex:codex.roots});
    note("demo_labels_each_step_recorded_and_its_folder_an_example",first.labels.length===1&&first.labels.every(([head,folder])=>head==="Recorded from this release's library"&&folder==="Example layout")
      &&!words.invitationWords.test(first.labels.flat().join(" ")),{labels:first.labels});
  };
  {const {opened,target}=await openDemo();await demoScenario(target,check);await opened.close();}
  {const plain=await browser.newContext({viewport:{width:1440,height:1000},javaScriptEnabled:false}),target=await plain.newPage();await plain.route("**/*",localOnly);
    const read={};
    for(const [address,steps] of [["/demo",5],["/demo/kaggle",6]]){await target.goto(base+address);const state=await demoState(target);
      read[address]={steps,shown:state.shown.length,controls:state.controls,labelled:state.labels.length===steps&&state.labels.every(([head,folder])=>head==="Recorded from this release's library"&&folder==="Example layout")};}
    check("demo_reads_every_step_when_the_script_has_not_run",Object.values(read).every(item=>item.shown===item.steps&&!item.controls&&item.labelled),read);
    await plain.close();}
  const demoControls=[
    {name:"show_every_demonstration_step_at_once",path:"/assets/public-pages.js",find:"panels.forEach((panel, place) => { panel.hidden = place !== current; });",replacement:"panels.forEach(panel => { panel.hidden = false; });",
      expected:["demo_shows_one_step_at_a_time_and_moves_by_its_list"]},
    {name:"send_the_pi_folder_to_another_root",path:"/assets/public-pages.js",find:'"pi": ".pi/skills/"',replacement:'"pi": ".pi/extensions/"',expected:["demo_folder_follows_the_chosen_harness"]},
    {name:"let_the_player_run_past_the_last_step",path:"/assets/public-pages.js",find:"if (current >= panels.length - 1) stop(); else select(current + 1, false);",
      replacement:"select((current + 1) % panels.length, false);",expected:["demo_play_moves_through_the_steps_and_stops_at_the_last"]}];
  for(const control of demoControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};let applied=false,problem="";
    try{const {opened,target,state}=await openDemo(control);applied=state.applied;await demoScenario(target,note);await opened.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }

  /* The status page: it shows what the service's own health and capabilities records say, read by the browser, and says so in words
     when the service is not ready, when a record is of another version and when a record disagrees with its own answer. It shows no
     uptime figure. The not-ready and wrong-version answers are the real record with one field changed, served in this browser only. */
  const statusState=target=>target.evaluate(()=>({state:document.getElementById("status-summary")?.dataset.statusState||"",word:document.getElementById("status-word")?.textContent||"",
    required:[...document.querySelectorAll("#status-required li")].map(item=>item.textContent.replace(/\s+/g," ").trim()),
    facts:Object.fromEntries([...document.querySelectorAll('[data-view="status"] dl dt')].map(term=>[term.textContent,term.nextElementSibling?.textContent.replace(/\s+/g," ").trim()||""])),
    text:document.querySelector('[data-view="status"]')?.innerText||""}));
  const realHealth=await (await page.request.get(base+"/api/v1/health")).json().catch(()=>({}));
  const realCapabilities=(await (await page.request.get(base+"/api/v1/capabilities")).json().catch(()=>({})))?.result||{};
  const expectedState=health=>health?.record_type!=="service_health/v2"?"unknown":!health.ready?"down":health.checks.every(item=>item.passed)?"working":"limited";
  const openStatus=async (health,mutation)=>{
    const opened=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"}),target=await opened.newPage(),state={applied:false};
    await opened.route("**/*",localOnly);
    if(health)await target.route(url=>url.origin===new URL(base).origin&&url.pathname==="/api/v1/health",route=>route.fulfill({status:health.status,contentType:"application/json",body:JSON.stringify(health.body)}));
    if(mutation)await target.route(url=>url.origin===new URL(base).origin&&url.pathname===mutation.path,async route=>{const response=await route.fetch(),source=await response.text(),
      changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    await target.goto(base+"/status");await target.waitForFunction(()=>document.getElementById("status-summary")?.dataset.statusState!=="reading",null,{timeout:10000}).catch(()=>{});
    return {opened,target,state};
  };
  const firstRequired=(realHealth.result?.checks||[]).findIndex(item=>item.required);
  const notReady={...realHealth,result:{...realHealth.result,ready:false,checks:(realHealth.result?.checks||[]).map((item,index)=>index===firstRequired?{...item,passed:false,code:"fixture_refusal"}:item)}};
  const statusScenario=async (note,mutation,tracker)=>{
    const read=async health=>{const {opened,target,state}=await openStatus(health,mutation);if(tracker&&state.applied)tracker.applied=true;const shown=await statusState(target);await opened.close();return shown;};
    const live=await read(null);
    note("status_page_reads_the_health_and_capabilities_records",live.state===expectedState(realHealth.result)&&live.required.length===(realHealth.result?.checks||[]).filter(item=>item.required).length
      &&live.required.every(item=>/^Passing /.test(item))&&live.facts["New accounts"]===(realCapabilities.website?.registration_available?"Open":"Closed")
      &&live.facts["Items"]===String(realHealth.result?.catalogue_release?.items??"Not reported"),{live:{state:live.state,required:live.required,facts:live.facts}});
    const down=await read({status:503,body:notReady});
    note("status_page_says_not_working_when_a_required_check_fails",down.state==="down"&&down.word==="Not working"&&down.required.some(item=>/^Failing /.test(item)),{down:{state:down.state,word:down.word}});
    const foreign=await read({status:200,body:{...realHealth,result:{...realHealth.result,record_type:"service_health/v3"}}});
    note("status_page_refuses_a_record_of_another_version",foreign.state==="unknown"&&foreign.word==="Could not be read"&&foreign.required.every(item=>/None reported/.test(item)),{foreign:{state:foreign.state,word:foreign.word}});
    const disagreeing=await read({status:200,body:notReady});
    note("status_page_refuses_a_record_that_disagrees_with_its_answer",disagreeing.state==="unknown",{disagreeing:disagreeing.state});
    note("status_page_shows_no_uptime_figure",![live,down,foreign].some(shown=>/\d\s*%|\buptime of\b/i.test(shown.text)));
  };
  await statusScenario(check);
  const statusControls=[
    {name:"read_a_health_record_of_any_version",find:"result.record_type !== HEALTH",replacement:"false",expected:["status_page_refuses_a_record_of_another_version"]},
    {name:"call_the_service_working_whatever_it_reports",find:'if (!health.ready) return {state: "down"',replacement:'if (false) return {state: "down"',expected:["status_page_says_not_working_when_a_required_check_fails"]},
    {name:"trust_a_record_that_disagrees_with_its_answer",find:"if ((answer.status === 200) !== result.ready || ![200, 503].includes(answer.status)) return null;",replacement:"",
      expected:["status_page_refuses_a_record_that_disagrees_with_its_answer"]}];
  for(const control of statusControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);},tracker={applied:false};let problem="";
    try{await statusScenario(note,{path:"/assets/public-pages.js",find:control.find,replacement:control.replacement},tracker);}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=tracker.applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied:tracker.applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied:tracker.applied,missed_checks:missed,...(problem?{problem}:{})});
  }

  /* Every page's head, as a search engine and a shared link read it before any script runs: its title and description carry no
     retired word, no word of an invitation-only service and no runtime word. */
  const heads=[];
  for(const entry of siteMap.pages){const markup=await (await page.request.get(base+entry.address)).text();
    heads.push([entry.address,(markup.match(/<title>([^<]*)<\/title>/)||[])[1]||"",(markup.match(/<meta name="description" content="([^"]*)">/)||[])[1]||""]);}
  const headProblems=list=>list.flatMap(([address,title,description])=>[title,description].filter(text=>words.retiredAccessWords.test(text)||words.invitationWords.test(text)||words.publicVocabulary.test(text))
    .map(text=>address+": "+text));
  check("every_page_head_uses_customer_words",heads.length===siteMap.pages.length&&heads.every(([,title,description])=>title&&description)&&headProblems(heads).length===0,{problems:headProblems(heads)});
  check("page_head_word_check_rejects_a_retired_an_invitation_and_a_runtime_word",["Join the private beta.","Request an invitation.","Built on Loop Engine."].every(text=>headProblems([["/",text,"x"]]).length===1));
  await page.close();

  /* The hostnames of the site map, each opened by name against one loopback service that answers them, in a browser of its own
     that resolves them to the loopback address. The root of docs, status, examples and demo opens its own page, and its brand
     leads to the homepage on the canonical hostname; baltor.ai, www and app open the homepage; every other address opens its own
     page on every hostname; and a hostname the site map does not name opens the homepage. */
  const port=new URL(fixture.surface_base).port,names=siteMap.hostnames.map(item=>item.hostname);
  const surfaceBrowser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox","--host-resolver-rules="+names.map(name=>"MAP "+name+" 127.0.0.1").join(",")]});
  const hostnameScenario=async (note,mutation,tracker)=>{
    const opened=await surfaceBrowser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
    await opened.route("**/*",route=>{const url=new URL(route.request().url());if(url.port===port&&(names.includes(url.hostname)||url.hostname==="127.0.0.1"))route.continue();else route.abort();});
    /* The changed script is built from the packaged source file, as a control of the catalogue browser is: a request the test runner
       made itself would resolve the hostname through the machine's own resolver and leave the loopback service. */
    if(mutation)await opened.route(url=>url.port===port&&url.pathname===mutation.path,async route=>{
      const source=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets",mutation.path.slice("/assets/".length)),"utf8");
      const changed=source.split(mutation.find).join(mutation.replacement);if(changed!==source)tracker.applied=true;
      await route.fulfill({status:200,contentType:"text/javascript",body:changed});});
    const target=await opened.newPage();
    for(const surface of siteMap.hostnames){
      await target.goto("http://"+surface.hostname+":"+port+"/");const state=await shownState(target);
      note("hostname_root_opens_its_own_page_"+surface.hostname,opensItsPage(state,pageAt(surface.address))&&state.brand===(surface.address==="/"?"/":canonicalOrigin+"/"),
        {views:state.views,title:state.title,canonical:state.canonical,brand:state.brand});
    }
    const docsHost=siteMap.hostnames.find(item=>item.address!=="/")?.hostname||"";
    await target.goto("http://"+docsHost+":"+port+"/pricing");const other=await shownState(target);
    await target.goto(fixture.surface_base+"/");const unnamed=await shownState(target);
    note("every_other_address_opens_its_own_page_on_a_surface_hostname",opensItsPage(other,pageAt("/pricing")),{views:other.views});
    note("a_hostname_the_site_map_does_not_name_opens_the_homepage",opensItsPage(unnamed,pageAt("/")),{views:unnamed.views});
    await opened.close();
  };
  await hostnameScenario(check);
  const hostnameControls=[{name:"forget_the_root_address_the_service_names",find:'const rootAddress = document.querySelector(\'meta[name="baltor-root-address"]\')?.getAttribute("content") || "/";',
    replacement:'const rootAddress = "/";',expected:siteMap.hostnames.filter(item=>item.address!=="/").map(item=>"hostname_root_opens_its_own_page_"+item.hostname)}];
  for(const control of hostnameControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);},tracker={applied:false};let problem="";
    try{await hostnameScenario(note,{path:"/assets/service.js",find:control.find,replacement:control.replacement},tracker);}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=tracker.applied&&!problem&&missed.length===0&&control.expected.length>=4;
    mutants.push({name:control.name,applied:tracker.applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied:tracker.applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  await surfaceBrowser.close();
}
