/* Deterministic loopback checks. Held responses are released by the observation, not a timing guess. */
import {readFileSync} from "node:fs";
import {observePageReadiness,visiblePageState,readinessProblems,shouldCaptureView,INITIAL_OBSERVATION_MS} from "./live_site_readiness.mjs";

export async function runDocumentationReadinessChecks({browser,base,check,screenshotPrefix=null}){
  if(!["127.0.0.1","localhost","[::1]"].includes(new URL(base).hostname))throw new Error("Readiness controls require a loopback fixture.");
  const context=await browser.newContext({viewport:{width:390,height:844},colorScheme:"light"}),blocked=[],errors=[];
  await context.route("**/*",route=>new URL(route.request().url()).origin===base&&route.request().method()==="GET"
    ?route.continue():(blocked.push(route.request().url()),route.abort()));
  await context.addInitScript(()=>localStorage.setItem("baltor.appearance","light"));
  const path="/docs/searching-and-retrieving",bodyPath="/assets/docs/searching-and-retrieving.html";
  const index=JSON.parse(readFileSync(new URL("../src/loop_engine/core/service_runtime/web_assets/documentation-index.json",import.meta.url),"utf8"));
  const asset=path=>url=>url.origin===base&&url.pathname===path;
  const read=page=>page.evaluate(visiblePageState,{documentation:"page"});
  const state=page=>page.evaluate(()=>{
    const status=document.getElementById("docs-page-status"),article=document.getElementById("docs-article");
    return {message:status.textContent,visible:status.getClientRects().length>0,role:status.getAttribute("role"),
      live:status.getAttribute("aria-live"),outside_busy_article:!article.contains(status),busy:article.getAttribute("aria-busy"),
      state:article.dataset.docsState,title:document.getElementById("docs-page-title").textContent};
  });
  const hold=async(page,routePath)=>{
    let release;const gate=new Promise(done=>{release=done;}),held={release:()=>release(),requests:0};
    await page.route(asset(routePath),async route=>{held.requests++;await gate;await route.continue().catch(()=>{});});
    return held;
  };
  const withPage=async action=>{const page=await context.newPage();page.on("pageerror",error=>errors.push(String(error)));try{await action(page);}finally{await page.close();}};
  const shot=async(page,name)=>{if(screenshotPrefix)await page.screenshot({path:`${screenshotPrefix}-${name}.png`,timeout:5000});};
  try{
    await withPage(async page=>{
      const held=await hold(page,"/assets/documentation-index.json");
      try{
        await page.goto(base+path);await page.locator("#docs-page-status").waitFor({state:"visible"});
        const pending=await state(page);
        check("docs_pending_index_has_accessible_visible_status",pending.visible&&pending.role==="status"&&pending.live==="polite"
          &&pending.outside_busy_article&&pending.busy==="true"&&pending.state==="loading"&&pending.message==="Loading the documentation list.",pending);
        await shot(page,"index-pending");
        const result=await observePageReadiness(page,{documentation:"page",onInitialNotReady:async()=>held.release()});
        check("docs_delayed_index_preserves_1500ms_observation_then_loads",!result.readiness.initial.ready&&result.readiness.initial_observed_ms>=INITIAL_OBSERVATION_MS
          &&result.readiness.late&&!result.readiness.timed_out&&result.seen.ready&&result.seen.heading==="Searching and retrieving",result.readiness);
        check("docs_fixed_sleep_wrong_control_rejects_successful_delayed_page",readinessProblems({...result.seen,...result.readiness.initial}).includes("shows no main heading")&&readinessProblems(result.seen).length===0);
        check("docs_index_wait_does_not_retry_fetch",held.requests===1,{requests:held.requests});
        check("docs_index_response_timing_is_retained",result.readiness.index_fetches.length===1
          &&result.readiness.index_fetches.every(row=>Number.isFinite(row.duration_ms)&&row.duration_ms>0),result.readiness.index_fetches);
        const loaded=await state(page);
        check("docs_loaded_state_clears_status_and_busy",!loaded.visible&&loaded.message===""&&loaded.busy===null&&loaded.state==="ready",loaded);
        await shot(page,"loaded");
      }finally{held.release();}
    });
    await withPage(async page=>{
      const held=await hold(page,bodyPath);
      try{
        await page.goto(base+path);await page.waitForFunction(()=>document.getElementById("docs-page-title").textContent==="Searching and retrieving");
        const pending=await state(page);
        check("docs_pending_body_keeps_title_and_announces_loading",pending.title==="Searching and retrieving"&&pending.visible&&pending.message==="Loading this page."&&pending.busy==="true",pending);
        const result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,onInitialNotReady:async()=>held.release()});
        check("docs_heading_only_wrong_control_cannot_accept_pending_body",Boolean(result.readiness.initial.heading)&&!result.readiness.initial.ready&&result.readiness.late&&result.seen.ready,result.readiness);
      }finally{held.release();}
    });
    for(const [name,routePath,answer,refusal] of [
      ["index_http", "/assets/documentation-index.json",{status:503,contentType:"application/json",body:"{}"},"index-load"],
      ["index_contract", "/assets/documentation-index.json",{contentType:"application/json",body:JSON.stringify({...index,record_type:"website_documentation_index/v99"})},"index"],
      ["body_http",bodyPath,{status:503,contentType:"text/html",body:"Unavailable"},"load"],
      ["body_contract",bodyPath,{contentType:"text/html",body:'<h2 id="wrong">Wrong body</h2><form>Refuse this</form>'},"body"]
    ])await withPage(async page=>{
      await page.route(asset(routePath),route=>route.fulfill(answer));await page.goto(base+path);
      await page.locator(`[data-docs-refused="${refusal}"]`).waitFor();
      const current=await state(page),result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,timeoutMs:500});
      check(`docs_${name}_is_explicit_failure_not_loaded_content`,current.state==="error"&&current.busy===null&&current.visible
        &&current.message==="This documentation page could not be loaded."&&!result.seen.ready&&result.seen.terminal_failure&&!result.readiness.timed_out
        &&readinessProblems(result.seen).some(problem=>problem.includes("documentation content is not ready")),{current,readiness:result.readiness});
      if(name==="index_http")await shot(page,"index-refused");
    });
    for(const [name,routePath] of [["index","/assets/documentation-index.json"],["body",bodyPath]])await withPage(async page=>{
      const held=await hold(page,routePath);
      try{
        await page.goto(base+path);await page.locator("#docs-page-status").waitFor({state:"visible"});
        if(name==="body")await page.waitForFunction(()=>document.getElementById("docs-page-title").textContent==="Searching and retrieving");
        const result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,timeoutMs:150});
        check(`docs_never_ready_${name}_times_out_without_retry`,result.readiness.timed_out&&!result.seen.ready&&result.seen.content_state==="loading"
          &&held.requests===1&&result.readiness.final_observed_ms<3000,result.readiness);
      }finally{held.release();}
    });
    await withPage(async page=>{
      await page.route(asset(bodyPath),route=>route.fulfill({contentType:"text/html",body:" "}));await page.goto(base+path);
      await page.waitForFunction(()=>document.getElementById("docs-article").dataset.docsState==="ready");
      const result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,timeoutMs:150});
      check("docs_ready_label_cannot_accept_empty_body",result.readiness.timed_out&&!result.seen.content_present&&!result.seen.ready&&Boolean(result.seen.heading),result.readiness);
    });
    await withPage(async page=>{
      await page.goto(base+path);await page.waitForFunction(visiblePageState,{documentation:"page",waitForReady:true});
      await page.locator("#docs-article").evaluate(article=>{
        const placeholder=document.createElement("p");placeholder.className="docs-note";placeholder.textContent="Loading this page.";
        article.replaceChildren(placeholder);
      });
      const result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,timeoutMs:150});
      check("docs_ready_label_cannot_accept_loading_placeholder",result.readiness.timed_out&&!result.seen.content_present&&!result.seen.ready
        &&result.seen.content_state==="ready"&&Boolean(result.seen.heading),result.readiness);
    });
    for(const [name,mutate] of [
      ["empty",node=>node.textContent=""],["removed",node=>node.remove()],["hidden",node=>node.hidden=true]
    ])await withPage(async page=>{
      await page.goto(base+path);await page.waitForFunction(visiblePageState,{documentation:"page",waitForReady:true});
      await page.locator("#docs-page-title").evaluate(mutate);
      const result=await observePageReadiness(page,{documentation:"page",initialDelayMs:0,timeoutMs:150});
      check(`docs_${name}_heading_wrong_control_fails_final_assertion`,result.readiness.timed_out&&!result.seen.ready
        &&readinessProblems(result.seen).includes("shows no main heading"),result.readiness);
      if(name==="empty"){
        check("docs_failed_phone_light_view_is_screenshotted",shouldCaptureView({size:"phone",scheme:"light",failed:true})&&!shouldCaptureView({size:"phone",scheme:"light",failed:false}));
        await shot(page,"missing-heading");
      }
    });
    await withPage(async page=>{
      await page.goto(base+path);await page.waitForFunction(visiblePageState,{documentation:"page",waitForReady:true});
      const held=await hold(page,"/assets/docs/your-account.html");
      try{
        await page.locator('#docs-nav a[href="/docs/your-account"]').click();
        await page.waitForFunction(()=>document.getElementById("docs-page-title").textContent==="Your account");
        await page.locator(`#docs-nav a[href="${path}"]`).click();
        await page.waitForFunction(visiblePageState,{documentation:"page",waitForReady:true});
        held.release();await page.waitForTimeout(50);
        const current=await read(page);
        check("docs_pending_navigation_cannot_restore_stale_or_empty_cached_body",current.ready&&current.heading==="Searching and retrieving"
          &&await page.locator("#docs-article #find-free-public-good-files").count()===1,current);
      }finally{held.release();}
    });
    check("docs_readiness_controls_make_no_external_or_non_get_requests",blocked.length===0,{blocked});
    check("docs_readiness_controls_have_no_script_errors",errors.length===0,{errors});
  }finally{await context.close();}
}
