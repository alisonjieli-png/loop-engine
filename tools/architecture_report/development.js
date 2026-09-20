/* Local preparation checklist. Never grants authority or changes roadmap status. */
window.LoopDevelopment = (() => {
  "use strict";
  const STORAGE = "loop-engine-owner-preparation-v1";
  const VERSION = "owner_preparation/v1";
  const phases = {now:"Consent or decision needed",after_endpoint:"After the endpoint is ready",before_public:"Before public access",before_charging:"Before charging",optional:"Optional",prepared:"Account prepared",engineering:"Engineering owned"};
  const $ = id => document.getElementById(id);
  const el = (tag, text, cls) => {const value=document.createElement(tag);if(text!==undefined)value.textContent=text;if(cls)value.className=cls;return value;};
  let actions=[], documents={}, prepared={}, storageAvailable=true;
  function readState(value){
    if(!value || value.record_type!==VERSION || !value.prepared || typeof value.prepared!=="object" || Array.isArray(value.prepared))return {};
    return Object.fromEntries(actions.filter(row=>value.prepared[row.id]===row.content_digest).map(row=>[row.id,row.content_digest]));
  }
  function state(){return {record_type:VERSION,prepared:{...prepared},meaning:"owner_marked_prepared_not_verified_or_authorized"};}
  function persist(){try{localStorage.setItem(STORAGE,JSON.stringify(state()));}catch(error){storageAvailable=false;}}
  function saveDownload(name, content, type="text/plain"){
    const url=URL.createObjectURL(new Blob([content],{type})),anchor=el("a");anchor.href=url;anchor.download=name;anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function showGuide(path){
    const document=Object.values(documents).find(row=>row.path===path);
    $("owner-guide").hidden=false;$("owner-guide-title").textContent=document?.title || "Guide unavailable";
    $("owner-guide-text").textContent=document?.text || "No guide was recorded.";
    $("owner-guide").scrollIntoView({behavior:"instant",block:"start"});
  }
  function draw(){
    const filter=$("owner-phase").value, hide=$("owner-hide-prepared").checked;
    const selected=actions.filter(row=>(filter==="all"||filter===row.phase)&&(!hide||prepared[row.id]!==row.content_digest));
    $("owner-items").replaceChildren();
    for(const row of selected){
      const item=el("article",undefined,"owner-item"),heading=el("div",undefined,"owner-item-heading"),label=el("label",undefined,"preparation-check");
      const input=el("input");input.type="checkbox";input.checked=prepared[row.id]===row.content_digest;input.dataset.ownerAction=row.id;
      input.setAttribute("aria-label","Mark prepared: "+row.title);
      input.addEventListener("change",()=>{if(input.checked)prepared[row.id]=row.content_digest;else delete prepared[row.id];persist();draw();(document.querySelector('[data-owner-action="'+row.id+'"]')||$("owner-hide-prepared")).focus({preventScroll:true});});
      label.append(input,el("span","Prepared"));const titles=el("div");titles.append(el("p",row.id+" · "+phases[row.phase],"caption"),el("h3",row.title));heading.append(titles,label);item.append(heading);
      const details=el("details");details.open=row.phase==="now"&&!input.checked;details.append(el("summary","Instructions and what to send back"));
      const list=el("ol");for(const text of row.instructions)list.append(el("li",text));details.append(list);
      const fields=el("p");fields.append(el("strong","Send back: "),document.createTextNode(row.return_fields.join("; ")+". References only, never secret values."));details.append(fields);
      details.append(el("p","Prepared when: "+row.completion),el("p",row.safety,"owner-safety"));
      if(row.depends_on.length)details.append(el("p","Preparation order: "+row.depends_on.join(", ")+". Engineering readiness is separate.","caption"));
      details.append(el("p","Engineering work: "+row.steps.join(", "),"caption"));
      const guide=el("button","Read the complete guide","text-button");guide.type="button";guide.addEventListener("click",()=>showGuide(row.guide));details.append(guide);item.append(details);$("owner-items").append(item);
    }
    if(!selected.length)$("owner-items").append(el("p","No tasks match these filters.","empty"));
    $("owner-progress").textContent=Object.keys(prepared).length+" of "+actions.length+" marked prepared by you. This does not change release gates or authorize any action.";
    $("owner-storage").textContent=storageAvailable?"Checkmarks stay in this browser. Export them before switching browsers or moving the file. No keys or account details are collected here.":"Browser storage is unavailable. Checkmarks last only for this open page; export them to keep a copy.";
  }
  function init(data){
    actions=data.roadmap?.owner_actions||[];documents=data.documents||{};
    const plan=data.roadmap||{};
    $("delivery-planning-note").textContent=plan.delivery_planning_note||"Planning detail, not completion evidence.";
    $("launch-benefits").replaceChildren();
    for(const row of plan.launch_benefits||[]){
      const item=el("article",undefined,"owner-item");
      item.append(el("p","Launch message draft · qualification required","caption"),el("h3",row.title),el("p",row.draft));
      const detail=el("details");detail.append(el("summary","Evidence needed before making this claim"),el("p",row.evidence_needed),el("p","Owning work: "+row.steps.join(", "),"caption"));item.append(detail);$("launch-benefits").append(item);
    }
    $("delivery-packages").replaceChildren();
    const batches=plan.delivery_batches||[],actionCount=batches.reduce((n,row)=>n+row.actions.length,0),caseCount=batches.reduce((n,row)=>n+(row.verification_cases||[]).length,0);
    $("delivery-planning-note").textContent=(plan.delivery_planning_note||"Planning only.")+" "+batches.length+" packages, "+actionCount+" implementation actions and "+caseCount+" required verification cases. Counts are planning coverage, not completion.";
    const steps=Object.fromEntries((plan.steps||[]).map(row=>[row.id,row]));
    for(const row of plan.delivery_batches||[]){
      const item=el("details",undefined,"subsection");item.append(el("summary",row.id+" · "+row.title));
      item.append(el("p","Owning work: "+row.steps.map(id=>id+" ("+(steps[id]?.status||"unknown")+")").join(", "),"caption"));
      item.append(el("p","Acceptance dependencies: "+(row.depends_on.join(", ")||"none")+". Independent preparation can proceed earlier.","caption"));
      item.append(el("p","Owning boundaries: "+row.owning_paths.join("; "),"caption"));
      const list=el("ol");for(const action of row.actions)list.append(el("li",action));
      item.append(list,el("p","Complete when: "+row.acceptance),el("p","Failure control: "+row.adversarial),el("p","Authority: "+row.authority_note,"owner-safety"),el("p","Rollback or safe stop: "+row.rollback));
      const verification=el("details",undefined,"verification-cases");verification.append(el("summary",row.verification_cases.length+" required verification cases"),el("p","These are acceptance requirements, not recorded passes."));
      for(const test of row.verification_cases){const card=el("article",undefined,"verification-case");card.append(el("h4",test.id+" · "+test.proof_level.replaceAll("_"," ")),el("p",test.scenario),el("p","Pass condition: "+test.pass_condition),el("p","Negative control: "+test.negative_control));verification.append(card);}
      item.append(verification);$("delivery-packages").append(item);
    }
    $("developer-handoff-text").textContent=documents.developer_handoff?.text||"Handoff not recorded.";
    $("download-developer-handoff").addEventListener("click",()=>saveDownload("baltor-fable-handoff.md",documents.developer_handoff?.text||"Handoff not recorded."));
    try{prepared=readState(JSON.parse(localStorage.getItem(STORAGE)||"null"));}catch(error){storageAvailable=false;}
    $("owner-phase").addEventListener("change",draw);$("owner-hide-prepared").addEventListener("change",draw);
    $("export-preparation").addEventListener("click",()=>saveDownload("loop-engine-owner-preparation.json",JSON.stringify(state(),null,2),"application/json"));
    $("import-preparation").addEventListener("change",async event=>{
      const file=event.target.files[0];if(!file)return;
      try{
        if(file.size>65536)throw new Error("Too large");
        const value=JSON.parse(await file.text());
        if(value.record_type!==VERSION || !value.prepared || Array.isArray(value.prepared) || typeof value.prepared!=="object")throw new Error("Wrong shape");
        const loaded=readState(value);prepared={...prepared,...loaded};persist();draw();
        $("owner-transfer-status").textContent="Imported "+Object.keys(loaded).length+" matching preparation marks. Unknown or changed tasks were ignored.";
      }catch(error){$("owner-transfer-status").textContent="This is not a supported preparation file. Nothing was imported.";}
      event.target.value="";
    });
    $("download-owner-handoff").addEventListener("click",()=>saveDownload("loop-engine-owner-handoff.txt",[
      "Loop Engine owner handoff", "Use account identifiers and secret-reference names only. Never paste secret values.",
      "Preparation is not spending, deployment, publication or live-payment approval.", "",
      ...actions.flatMap(row=>[row.id+" · "+row.title,...row.return_fields.map(field=>field+": "),""])
    ].join("\n")));
    $("close-owner-guide").addEventListener("click",()=>{$("owner-guide").hidden=true;});
    const counts=data.check_evidence?.counts,gates=data.roadmap?.gates||[];
    $("development-evidence").textContent=counts?`${counts.passed} of ${counts.passed+counts.failed} executed checks passed; ${counts.not_tested} optional checks untested. Source evidence: ${data.check_evidence.state.replaceAll("_"," ")}.`:"The current source has no matching full-suite evidence.";
    $("development-gates").textContent=gates.filter(row=>row.state.startsWith("Recorded pass")).length+" of "+gates.length+" release gates have a recorded pass. A working diagnostic deployment is not a qualified paid release.";
    $("development-log").replaceChildren();
    for(const row of [...(data.roadmap?.activity||[])].sort((a,b)=>Date.parse(b.at)-Date.parse(a.at))){
      const label=String(row.event).replaceAll("_"," ");
      const item=el("article",undefined,"log-entry");item.append(el("p",row.at,"caption"),el("h3",label.charAt(0).toUpperCase()+label.slice(1)),el("p",row.outcome),el("p",row.evidence,"caption"));$("development-log").append(item);
    }
    $("development-guides").replaceChildren();
    for(const document of Object.values(documents)){
      const item=el("details",undefined,"subsection");item.append(el("summary",document.title),el("pre",document.text));$("development-guides").append(item);
    }
    draw();
  }
  return {init,state,readState};
})();
