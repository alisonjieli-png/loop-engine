/* Browser acceptance for the generated, offline, read-only system map. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,mkdtempSync,copyFileSync,unlinkSync,rmdirSync} from "node:fs";
import {createHash} from "node:crypto";
import {tmpdir} from "node:os";
import {join,resolve,basename} from "node:path";
import {pathToFileURL} from "node:url";
import {gunzipSync} from "node:zlib";

const root=resolve(new URL("..",import.meta.url).pathname);
const file=join(root,"artifacts/architecture-audit-2026-09-19/loop-engine-system-map.html");
const output=resolve(process.argv[2] || join(root,"artifacts/architecture-audit-2026-09-19/system-map-browser-attempt-1.json"));
const imagePrefix=basename(output,".json");
const hash=path=>createHash("sha256").update(readFileSync(path)).digest("hex");
const reportHash=hash(file),planHash=hash(join(root,"docs/roadmap/roadmap.yaml"));
const checks=[],errors=[],requests=[],screenshots=[];
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const context=await browser.newContext({offline:true,viewport:{width:1440,height:1100},acceptDownloads:true,reducedMotion:"reduce"});
const page=await context.newPage();
page.on("pageerror",error=>errors.push(error.message));
page.on("request",request=>requests.push(request.url()));
const ready=async()=>page.waitForFunction(()=>document.body.dataset.ready==="true");
const settled=async()=>page.waitForFunction(()=>{
  const graph=document.getElementById("architecture-graph");
  return graph.getAttribute("aria-busy")==="false"&&performance.now()-Number(graph.dataset.settledAt)>70;
});
const measure=()=>page.evaluate(()=>{
  const cards=[...document.querySelectorAll("#architecture-graph .component")];
  const rects=cards.map(element=>element.getBoundingClientRect());
  const overlaps=[];
  for(let i=0;i<rects.length;i++)for(let j=i+1;j<rects.length;j++){
    const a=rects[i],b=rects[j];
    if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)overlaps.push([i,j]);
  }
  const clipped=cards.filter(element=>element.scrollHeight>element.clientHeight+2 || element.scrollWidth>element.clientWidth+2).length;
  return {width:innerWidth,overflow:document.documentElement.scrollWidth>innerWidth+1,overlaps,clipped,
    cards:cards.length,layout:window.LoopSystemMap.state().layout,
    minimumText:Math.min(...cards.flatMap(card=>[...card.querySelectorAll("span,strong")].map(element=>parseFloat(getComputedStyle(element).fontSize))))};
});
try{
  await page.goto(pathToFileURL(file).href);await ready();
  check("development_log_is_the_default_working_surface",await page.locator("#page-development").isVisible());
  check("three_launch_benefits_are_drafts_with_required_evidence",await page.locator("#launch-benefits article").count()===3&&(await page.locator("#launch-benefits").textContent()).includes("qualification required")&&(await page.locator("#launch-benefits").textContent()).includes("Local execution alone does not prove local inference"));
  const delivery=await page.locator("#report-data").evaluate(element=>JSON.parse(element.textContent).roadmap.delivery_batches);
  check("delivery_packages_embed_all_actions_and_failure_controls",await page.locator("#delivery-packages > details").count()===delivery.length&&delivery.length>=16&&await page.locator("#delivery-packages li").count()===delivery.reduce((n,row)=>n+row.actions.length,0)&&(await page.locator("#delivery-packages").textContent()).includes("Failure control:"));
  check("delivery_cases_keep_proof_levels_owners_and_rollback_visible",await page.locator("#delivery-packages .verification-case").count()===delivery.reduce((n,row)=>n+row.verification_cases.length,0)&&delivery.every(row=>row.owning_paths.length&&row.rollback)&&(await page.locator("#delivery-packages").textContent()).includes("not recorded passes"));
  const handoffText=(await page.locator("#developer-handoff-text").textContent()).replace(/\s+/g," ");
  const separatesDeploymentFromRegistration=text=>text.includes("code and plain-language website are deployed")&&text.includes("Public account registration remains disabled")&&text.includes("Model-call authority remains");
  check("handoff_separates_deployed_code_from_enabled_customer_behavior",separatesDeploymentFromRegistration(handoffText));
  check("handoff_guard_rejects_false_registration_claim",!separatesDeploymentFromRegistration(handoffText.replace("Public account registration remains disabled","Public account registration is enabled")));
  const developerDownload=page.waitForEvent("download");await page.click("#download-developer-handoff");
  check("developer_download_matches_the_embedded_repository_handoff",readFileSync(await(await developerDownload).path(),"utf8")===readFileSync(join(root,"docs/context/FABLE-5-1-HANDOFF-2026-09-20.md"),"utf8"));
  await page.evaluate(()=>window.LoopSystemMap.openPage("owner"));
  check("all_fifteen_owner_tasks_have_instructions_and_handoff_fields",await page.locator("#owner-items .owner-item").count()===15&&(await page.locator("#owner-items").innerText()).includes("Send back:"));
  const gatesBefore=await page.locator("#release-gates").innerText();
  await page.locator('[data-owner-action="OWNER-01"]').check();
  check("owner_marks_are_preparation_not_software_completion",(await page.locator("#owner-progress").innerText()).startsWith("1 of 15")&&(await page.locator("#release-gates").innerText())===gatesBefore);
  await page.reload();await ready();
  check("owner_marks_survive_reload",await page.locator('[data-owner-action="OWNER-01"]').isChecked());
  check("changed_checklist_instructions_invalidate_old_marks",await page.evaluate(()=>Object.keys(window.LoopDevelopment.readState({record_type:"owner_preparation/v1",prepared:{"OWNER-01":"old-digest"}})).length===0));
  await page.locator("#import-preparation").setInputFiles({name:"bad.json",mimeType:"application/json",buffer:Buffer.from('{"record_type":"owner_preparation/v1","prepared":[]}')});
  await page.waitForFunction(()=>document.getElementById("owner-transfer-status").textContent.includes("Nothing was imported"));
  check("malformed_owner_import_preserves_existing_marks",await page.locator('[data-owner-action="OWNER-01"]').isChecked());
  const preparationDownload=page.waitForEvent("download");await page.click("#export-preparation");
  const preparation=JSON.parse(readFileSync(await (await preparationDownload).path(),"utf8"));
  check("owner_export_contains_only_bound_preparation_marks",preparation.record_type==="owner_preparation/v1"&&Object.keys(preparation.prepared).join() === "OWNER-01"&&preparation.meaning.includes("not_verified_or_authorized"));
  await page.selectOption("#owner-phase","after_endpoint");
  check("owner_checklist_filters_later_setup",await page.locator("#owner-items .owner-item").count()===1);
  await page.selectOption("#owner-phase","engineering");
  const expectedEngineering=await page.locator("#report-data").evaluate(element=>JSON.parse(element.textContent).roadmap.owner_actions.filter(row=>row.phase==="engineering").map(row=>row.id).sort());
  const visibleEngineering=await page.locator("#owner-items [data-owner-action]").evaluateAll(elements=>elements.map(element=>element.dataset.ownerAction).sort());
  const matchesEngineering=ids=>expectedEngineering.length>0&&JSON.stringify(ids)===JSON.stringify(expectedEngineering);
  check("routine_setup_is_owned_by_engineering",matchesEngineering(visibleEngineering)&&(await page.locator("#owner-items").innerText()).includes("Resend"));
  check("engineering_filter_rejects_an_omitted_prepared_provider",!matchesEngineering(visibleEngineering.slice(1)));
  await page.selectOption("#owner-phase","all");
  await page.locator('[data-owner-action="OWNER-01"]').uncheck();
  await page.locator("#owner-items .owner-item .text-button").first().click();
  check("full_setup_guide_is_readable_without_a_companion_file",await page.locator("#owner-guide").isVisible()&&(await page.locator("#owner-guide-text").innerText()).includes("## 1. Set up hosting"));
  await page.click("#close-owner-guide");
  for(const width of [1440,736,390,320]){
    await page.setViewportSize({width,height:1100});
    for(const section of ["owner","development","hosting"]){
      await page.evaluate(name=>window.LoopSystemMap.openPage(name),section);
      check(`development_layout_${width}_${section}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
  }
  await page.setViewportSize({width:1440,height:1100});
  await page.evaluate(()=>window.LoopSystemMap.openPage("architecture"));await settled();
  const state=await page.evaluate(()=>window.LoopSystemMap.state());
  check("whole_engine_is_the_default_architecture_not_client_server",state.view==="system"&&state.views.length===18);
  await page.selectOption("#architecture-area","runtime");await settled();
  check("architecture_selector_reaches_internal_runtime",(await page.locator("#architecture-heading").innerText()).includes("runtime"));
  await page.evaluate(()=>window.LoopSystemMap.openPage("hosting"));
  check("hosting_has_six_concrete_owner_steps_and_sources",await page.locator(".hosting-action").count()===6&&(await page.locator("#hosting-title").innerText()).includes("Fly.io")&&(await page.locator("#hosting-stack").innerText()).includes("pgvector"));
  const hostingStatus=await page.locator("#hosting-status").innerText();
  const retainsIntegrationLimits=text=>text.includes("SQLite")&&text.includes("shared storage, billing and complete native task execution are not qualified")&&text.includes("not a qualified paid release");
  check("hosting_preparation_does_not_claim_database_integration",retainsIntegrationLimits(hostingStatus));
  check("hosting_guard_rejects_false_integration_success",!retainsIntegrationLimits(hostingStatus.replace("are not qualified","are qualified")));
  await page.evaluate(()=>window.LoopSystemMap.openPage("architecture"));await settled();
  check("all_six_original_tables_and_measured_feature_count_are_embedded",state.featureTables===6&&state.featureColumns===77,state);
  check("complete_roadmap_and_source_inventory_are_embedded",state.steps>=106&&state.files>2000,state);
  for(const theme of ["light","dark"]){
    await page.selectOption("#theme",theme);
    for(const width of [1440,1024,736,390,320]){
      await page.setViewportSize({width,height:1100});
      for(const view of state.views){
        await page.evaluate(async id=>{window.LoopSystemMap.openPage("architecture");await window.LoopSystemMap.drawArchitecture(id);},view);
        await settled();const observed=await measure();
        check(`layout_${theme}_${width}_${view}`,!observed.overflow&&!observed.overlaps.length&&!observed.clipped&&observed.minimumText>=11&&observed.cards>=3,observed);
      }
    }
  }
  await page.setViewportSize({width:1440,height:1100});await page.selectOption("#theme","light");
  await page.evaluate(()=>window.LoopSystemMap.drawArchitecture("high"));await settled();
  check("desktop_uses_the_embedded_ELK_layout_engine",(await measure()).layout.engine==="elk");
  await page.locator(".component").first().focus();await page.keyboard.press("Enter");
  check("component_details_are_keyboard_accessible",await page.locator("#diagram-detail").isVisible());
  for(const [view,name] of [["system","whole-system"],["runtime","runtime"],["intelligence","intelligence"],["high","client-server"],["low","request-path"]]){
    await page.evaluate(id=>window.LoopSystemMap.drawArchitecture(id),view);await settled();
    const path=join(root,`artifacts/architecture-audit-2026-09-19/${imagePrefix}-${name}-1440.png`);
    await page.screenshot({path,fullPage:true});screenshots.push(path);
  }
  await page.evaluate(()=>window.LoopSystemMap.openPage("hosting"));
  const hostingScreenshot=join(root,`artifacts/architecture-audit-2026-09-19/${imagePrefix}-hosting-1440.png`);
  await page.screenshot({path:hostingScreenshot,fullPage:true});screenshots.push(hostingScreenshot);
  await page.evaluate(()=>window.LoopSystemMap.openPage("features"));
  await page.evaluate(()=>window.LoopSystemMap.openPage("development"));
  await page.locator("#candidate-count").evaluate(element=>{element.closest("details").open=true;});
  check("candidate_intelligence_is_embedded_with_its_actual_lifecycle",await page.locator("#candidate-table tbody tr").count()===12&&(await page.locator("#candidate-count").innerText()).includes("4 persistent layers"));
  await page.locator("#candidate-table button").first().click();
  check("candidate_details_keep_source_identity_and_review_limits",(await page.locator("#candidate-detail").innerText()).includes("sha256")&&(await page.locator("#candidate-detail").innerText()).includes("qualification remain required"));
  await page.evaluate(()=>window.LoopSystemMap.openPage("features"));
  check("current_website_comparison_covers_all_sampled_pages",await page.locator("#website-table tbody tr").count()===24);
  await page.fill("#website-search","SenseLab");
  check("website_comparison_filter_finds_named_reference",await page.locator("#website-table tbody tr").count()===1);
  await page.locator("#website-table button").click();
  check("website_review_exposes_scope_source_and_action",(await page.locator("#website-detail").innerText()).includes("https://www.sense-lab.ai/")&&(await page.locator("#website-detail").innerText()).includes("authenticated onboarding was not tested"));
  await page.fill("#website-search","");await page.selectOption("#website-cohort","historical_comparison");
  check("website_comparison_keeps_original_known_population",await page.locator("#website-table tbody tr").count()===19);
  await page.selectOption("#website-cohort","all");
  for(let family=0;family<6;family++){
    await page.selectOption("#feature-family",String(family));
    check("historical_family_"+family+"_preserves_21_rows",await page.locator("#feature-table tbody tr").count()===21);
  }
  await page.selectOption("#feature-family","1");await page.fill("#feature-search","One task working folder");
  await page.locator("#feature-table button").first().click();
  check("partial_cell_and_its_source_note_are_inspectable",(await page.locator("#feature-table button").first().textContent())==="P"&&(await page.locator("#feature-detail").innerText()).includes("Original snapshot"));
  await page.fill("#company-search","no-such-company");
  check("empty_matrix_filter_is_explicit",(await page.locator("#feature-table").innerText()).includes("No matching"));
  await page.fill("#company-search","");await page.fill("#feature-search","");
  const matrixScreenshot=join(root,`artifacts/architecture-audit-2026-09-19/${imagePrefix}-matrix-1440.png`);
  await page.screenshot({path:matrixScreenshot,fullPage:true});screenshots.push(matrixScreenshot);
  await page.evaluate(()=>window.LoopSystemMap.openPage("work"));await page.selectOption("#work-status","building");
  check("worklist_filters_active_work_without_marking_it_verified",await page.locator(".work-item").count()>0&&await page.locator(".work-item .badge:not(.building)").count()===0);
  await page.locator(".work-item summary").first().click();
  check("work_item_has_acceptance_and_evidence",(await page.locator(".work-item[open]").innerText()).includes("Acceptance:")&&(await page.locator(".work-item[open]").innerText()).includes("Current evidence:"));
  const workScreenshot=join(root,`artifacts/architecture-audit-2026-09-19/${imagePrefix}-worklist-1440.png`);
  await page.screenshot({path:workScreenshot,fullPage:true});screenshots.push(workScreenshot);
  await page.evaluate(()=>window.LoopSystemMap.openPage("source"));await page.fill("#source-search","service_runtime/http.py");
  check("source_lookup_finds_the_real_serving_file",await page.locator(".source-file").count()===1);
  await page.locator(".source-file").click();
  check("source_details_distinguish_imports_from_observed_calls",(await page.locator("#source-detail").innerText()).includes("Observed invocation"));
  await page.evaluate(()=>window.LoopSystemMap.openPage("architecture"));await page.evaluate(()=>window.LoopSystemMap.drawArchitecture("high"));await settled();
  await page.evaluate(()=>{const cards=document.querySelectorAll(".component");cards[1].style.left=cards[0].style.left;cards[1].style.top=cards[0].style.top;});
  check("overlap_control_rejects_a_deliberately_broken_layout",(await measure()).overlaps.length>0);
  await page.evaluate(()=>window.LoopSystemMap.drawArchitecture("high"));await settled();
  await page.evaluate(()=>{document.querySelector(".component").style.height="30px";});
  check("clipping_control_rejects_a_deliberately_broken_layout",(await measure()).clipped>0);
  await page.evaluate(()=>window.LoopSystemMap.drawArchitecture("high"));await settled();
  const mobile=await context.newPage();await mobile.setViewportSize({width:390,height:1000});
  mobile.on("pageerror",error=>errors.push(error.message));mobile.on("request",request=>requests.push(request.url()));
  await mobile.goto(pathToFileURL(file).href);
  await mobile.waitForFunction(()=>document.body.dataset.ready==="true");
  await mobile.evaluate(()=>window.LoopSystemMap.openPage("architecture"));
  await mobile.waitForFunction(()=>document.body.dataset.ready==="true"&&document.getElementById("architecture-graph").getAttribute("aria-busy")==="false");
  await mobile.selectOption("#theme","dark");
  const mobileScreenshot=join(root,`artifacts/architecture-audit-2026-09-19/${imagePrefix}-mobile-dark.png`);
  await mobile.screenshot({path:mobileScreenshot,fullPage:true});screenshots.push(mobileScreenshot);
  check("fresh_mobile_capture_matches_the_actual_mobile_viewport",readFileSync(mobileScreenshot).readUInt32BE(16)===390&&await mobile.evaluate(()=>document.documentElement.scrollWidth===innerWidth));
  await mobile.close();
  const downloadEvent=page.waitForEvent("download");await page.locator('[data-download="graph"]').click();
  const download=await downloadEvent;const stream=await download.createReadStream();const chunks=[];for await(const chunk of stream)chunks.push(chunk);
  const graph=JSON.parse(gunzipSync(Buffer.concat(chunks)).toString("utf8"));
  check("complete_graph_download_works_from_embedded_bytes",graph.entities.length>100000&&graph.relationships.length>100000);
  const temporary=mkdtempSync(join(tmpdir(),"loop-map-offline-")),copy=join(temporary,"standalone.html");
  try{
    copyFileSync(file,copy);await page.goto(pathToFileURL(copy).href);await ready();
    await page.evaluate(()=>window.LoopSystemMap.openPage("architecture"));await settled();
    check("one_copied_file_works_offline_without_companion_assets",(await page.evaluate(()=>window.LoopSystemMap.state())).featureColumns===77&&(await measure()).cards===9);
  }finally{unlinkSync(copy);rmdirSync(temporary);}
  check("no_remote_resource_or_data_request_was_made",requests.every(url=>!/^https?:/.test(url)),{requests});
  check("no_browser_runtime_errors",errors.length===0,{errors});
  check("report_and_roadmap_are_not_mutated_by_UI_controls",hash(file)===reportHash&&hash(join(root,"docs/roadmap/roadmap.yaml"))===planHash);
}catch(error){check("browser_acceptance_completed",false,{error:String(error)});}
finally{await browser.close();}
const result={record_type:"system_map_browser_checks/v1",checks,passed:checks.filter(row=>row.passed).length,total:checks.length,
  all_passed:checks.every(row=>row.passed),source_sha256:reportHash,roadmap_sha256:planHash,screenshots,errors,remote_requests:requests.filter(url=>/^https?:/.test(url))};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});
process.stdout.write(JSON.stringify({output,passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(row=>!row.passed)})+"\n");
process.exitCode=result.all_passed?0:1;
