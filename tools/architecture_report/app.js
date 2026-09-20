/* Read-only presentation. No fetch, remote account operation, or task mutation. */
(() => {
  "use strict";
  const data = JSON.parse(document.getElementById("report-data").textContent);
  const $ = id => document.getElementById(id);
  const esc = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const pretty = value => JSON.stringify(value, null, 2);
  const words = value => String(value ?? "").replaceAll("_", " ");
  const badgeNames = {local:"Local implementation",partial:"Partly integrated",owner:"Needs owner setup",proposed:"Proposed",external:"External service"};
  const badge = state => '<span class="badge '+esc(state)+'">'+esc(badgeNames[state] || words(state))+'</span>';
  const empty = text => '<p class="empty">'+esc(text)+'</p>';
  const table = (columns, rows) => '<div class="table-scroll"><table><thead><tr>'+columns.map(c=>'<th scope="col">'+esc(c)+'</th>').join("")+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(c=>'<td>'+esc(c)+'</td>').join("")+'</tr>').join("")+'</tbody></table></div>';
  const files = data.files || [], byPath = new Map(files.map(file=>[file.path,file]));
  const byComponent = new Map((data.components || []).map(row=>[row.path,row]));
  const architecture = data.architecture?.views || [];
  const sourceIndexes = new Map(files.map(file=>[file.path,[file.path,file.module,...file.symbols.map(x=>x.name)].join(" ").toLowerCase()]));
  const plan = data.roadmap || {}, steps = plan.steps || [];
  const finished = new Set(["offline_verified","live_qualified","published","superseded"]);
  let page = "development", viewId = data.architecture?.default_view || "system", selectedFile = "src/loop_engine/loop/recursive_loop.py", visibleFiles = 100;
  let layoutGeneration = 0, lastLayout = null, lastWidth = 0;
  let elk = null;

  function openPage(name, updateHash = true) {
    if (!$("page-"+name)) return;
    const changed=page!==name;
    page = name;
    for (const section of document.querySelectorAll(".page")) section.hidden = section.id !== "page-"+name;
    for (const button of document.querySelectorAll("[data-page]")) button.setAttribute("aria-pressed", String(button.dataset.page === name));
    if (updateHash) history.replaceState(null, "", "#"+name);
    if (name === "architecture" && (changed || !lastLayout)) drawArchitecture(viewId);
    if (name === "source") { drawFiles(); showFile(byPath.has(selectedFile) ? selectedFile : files[0]?.path); }
    document.body.dataset.page = name;
  }

  function showPanel(target, title, body) {
    target.hidden = false;
    target.innerHTML = '<button type="button" class="close" aria-label="Close details">Close</button><h3>'+esc(title)+'</h3>'+body;
    target.querySelector(".close").addEventListener("click",()=>{target.hidden = true;});
  }

  function componentDetail(component) {
    showPanel($("diagram-detail"), component.title,
      '<p>'+badge(component.state)+' · '+esc(component.owner)+'</p><p>'+esc(component.detail)+'</p>'+
      (component.source ? '<button type="button" class="text-button" data-inspect-source>Inspect '+esc(component.source)+'</button>' : ""));
    const button = $("diagram-detail").querySelector("[data-inspect-source]");
    if (button) button.addEventListener("click",()=>{selectedFile=component.source;openPage("source");});
    for (const card of $("architecture-graph").querySelectorAll(".component")) card.setAttribute("aria-expanded",String(card.dataset.component===component.id));
  }

  function svgElement(name, attributes = {}) {
    const element = document.createElementNS("http://www.w3.org/2000/svg",name);
    for (const [key,value] of Object.entries(attributes)) element.setAttribute(key,value);
    return element;
  }

  async function drawArchitecture(id) {
    const view = architecture.find(item=>item.id===id);
    if (!view || page !== "architecture") return;
    viewId = id;
    $("architecture-area").value=id;
    const generation = ++layoutGeneration, host = $("architecture-graph");
    host.setAttribute("aria-busy","true");host.classList.remove("stacked");host.replaceChildren();
    $("diagram-detail").hidden = true;
    $("diagram-level").textContent=view.level;$("architecture-heading").textContent=view.title;
    $("diagram-description").textContent=view.description;
    for (const button of document.querySelectorAll("[data-level]")) button.setAttribute("aria-pressed",String(button.dataset.level===id));
    const names = new Map(view.components.map(component=>[component.id,component.title]));
    $("connections").innerHTML=view.edges.map(edge=>'<li><b>'+esc(names.get(edge.from))+' → '+esc(names.get(edge.to))+'</b><br>'+esc(edge.label)+(edge.state?' · '+esc(edge.state):"")+'</li>').join("");
    const width=host.getBoundingClientRect().width;
    lastWidth=width;
    const cards=new Map();
    for(const component of view.components){
      const button=document.createElement("button");button.type="button";button.className="component";
      button.dataset.component=component.id;button.dataset.zone=component.zone;button.setAttribute("aria-expanded","false");
      button.style.width=(id==="high"?270:228)+"px";button.style.visibility="hidden";
      button.innerHTML='<span class="owner">'+esc(component.owner)+'</span><strong>'+esc(component.title)+'</strong><span class="copy">'+esc(component.summary)+'</span>'+badge(component.state);
      button.addEventListener("click",()=>componentDetail(component));host.appendChild(button);cards.set(component.id,button);
    }
    const stack = reason => {
      if(generation!==layoutGeneration)return;
      host.classList.add("stacked");host.style.height="auto";
      for(const card of cards.values())card.style.visibility="visible";
      host.dataset.layoutEngine="stacked";host.setAttribute("aria-busy","false");
      host.dataset.settledAt=performance.now();
      $("diagram-layout-note").textContent=reason+" All connections are listed below. These are software components, not executable Loop vertices.";
      lastLayout={view:id,engine:"stacked",nodes:view.components.length,edges:view.edges.length};
    };
    if(width<680){stack("Components are stacked for this screen width.");return;}
    if(!elk){stack("Automatic diagram layout is unavailable; no content is omitted.");return;}
    try{
      const graph=await elk.layout({id:"map",children:view.components.map(component=>({id:component.id,
        width:cards.get(component.id).getBoundingClientRect().width,height:Math.ceil(cards.get(component.id).getBoundingClientRect().height)})),
        edges:view.edges.map((edge,index)=>({id:"edge-"+index,sources:[edge.from],targets:[edge.to]})),
        layoutOptions:{"elk.algorithm":"layered","elk.direction":view.direction,"elk.edgeRouting":"ORTHOGONAL",
          "elk.padding":"[top=20,left=20,bottom=20,right=20]","elk.spacing.nodeNode":"32",
          "elk.layered.spacing.nodeNodeBetweenLayers":"62","elk.layered.considerModelOrder.strategy":"NODES_AND_EDGES"}});
      if(generation!==layoutGeneration || page!=="architecture")return;
      if(graph.width>width){stack("The full-width diagram is stacked here to keep labels readable.");return;}
      const offset=(width-graph.width)/2;
      const svg=svgElement("svg",{width,height:graph.height,viewBox:`0 0 ${width} ${graph.height}`,"aria-hidden":"true"});
      const defs=svgElement("defs"),marker=svgElement("marker",{id:"arrow",markerWidth:8,markerHeight:8,refX:7,refY:4,orient:"auto",markerUnits:"userSpaceOnUse"});
      marker.appendChild(svgElement("path",{d:"M 0 0 L 8 4 L 0 8 Z",class:"arrow"}));defs.appendChild(marker);svg.appendChild(defs);
      for(const edge of graph.edges || []){
        const index=Number(edge.id.split("-")[1]),definition=view.edges[index];
        for(const section of edge.sections || []){
          const points=[section.startPoint,...(section.bendPoints||[]),section.endPoint].map(point=>({x:point.x+offset,y:point.y}));
          svg.appendChild(svgElement("path",{class:"edge "+(definition.state||""),d:points.map((point,i)=>(i?"L ":"M ")+point.x+" "+point.y).join(" "),"marker-end":"url(#arrow)"}));
          let longest=0,middle=null;
          for(let i=1;i<points.length;i++){const length=Math.hypot(points[i].x-points[i-1].x,points[i].y-points[i-1].y);if(length>longest){longest=length;middle={x:(points[i].x+points[i-1].x)/2,y:(points[i].y+points[i-1].y)/2};}}
          if(middle && longest>32){svg.appendChild(svgElement("circle",{cx:middle.x,cy:middle.y,r:10,class:"edge-number-bg"}));const text=svgElement("text",{x:middle.x,y:middle.y+4,class:"edge-number"});text.textContent=index+1;svg.appendChild(text);}
        }
      }
      host.prepend(svg);host.style.height=graph.height+"px";
      for(const node of graph.children){const card=cards.get(node.id);Object.assign(card.style,{left:(node.x+offset)+"px",top:node.y+"px",height:node.height+"px",visibility:"visible"});}
      host.dataset.layoutEngine="elk";host.setAttribute("aria-busy","false");
      host.dataset.settledAt=performance.now();
      $("diagram-layout-note").textContent="Numbered connections match the list below. Arrows describe software relationships, not a live trace or proof that every path ran together. Dashed lines are optional or proposed. Layout runs inside this file.";
      lastLayout={view:id,engine:"elk",nodes:view.components.length,edges:view.edges.length};
    }catch(error){stack("Automatic layout could not complete; the readable component view is shown.");}
  }

  function drawWebsites(){
    const comparison=data.website_comparison||{},query=$("website-search").value.toLowerCase().trim(),cohort=$("website-cohort").value;
    const rows=(comparison.rows||[]).filter(row=>(cohort==="all"||row.cohort===cohort)&&JSON.stringify([row.name,row.positioning,row.lesson]).toLowerCase().includes(query));
    $("website-count").textContent=rows.length+" of "+(comparison.rows||[]).length+" signed-out pages · "+(comparison.observed_at||"No observation")+". Select a company for the source and review.";
    const columns=comparison.columns||[];
    $("website-detail").hidden=true;
    if(!rows.length){$("website-table").innerHTML=empty("No matching website in this sample.");return;}
    $("website-table").innerHTML='<table class="matrix" style="width:1250px"><thead><tr><th scope="col">Company or reference</th>'+columns.map(column=>'<th scope="col">'+esc(column.label)+'</th>').join("")+'</tr></thead><tbody>'+rows.map((row,index)=>'<tr class="'+(row.cohort==="own_product"?"engine-row":"")+'"><th scope="row"><button type="button" data-website-row="'+index+'">'+esc(row.name)+'</button></th>'+columns.map(column=>'<td>'+ (row.page_signals[column.id].state==="link_observed"?"Link":"Unknown")+'</td>').join("")+'</tr>').join("")+'</tbody></table>';
    for(const button of $("website-table").querySelectorAll("button"))button.addEventListener("click",()=>{
      const row=rows[Number(button.dataset.websiteRow)],safeLink=url=>url?.startsWith("https://")?'<a href="'+esc(url)+'" target="_blank" rel="noopener noreferrer">'+esc(url)+'</a>':"No source";
      const links=columns.map(column=>'<h4>'+esc(column.label)+'</h4><p>'+row.page_signals[column.id].links.map(link=>esc(link.label)+": "+safeLink(link.url)).join("<br>")+'</p>').join("");
      showPanel($("website-detail"),row.name,'<p>'+safeLink(row.final_url||row.requested_url)+'</p><p><strong>Positioning:</strong> '+esc(row.positioning)+'</p><p><strong>Go-to-market signals:</strong> '+esc(row.distribution)+'</p><p><strong>Design review:</strong> '+esc(row.visual_review)+'</p><p><strong>Apply to Baltor:</strong> '+esc(row.lesson)+'</p><p class="caption">Signed-out page, '+esc(row.observed_at)+'. Links below were observed, not fully qualified.</p>'+links);
    });
  }
  function drawFeatures(){
    const comparison=data.historical_comparison || {}, selected=(comparison.tables||[])[Number($("feature-family").value)||0];
    if(!selected){$("feature-table").innerHTML=empty("No historical comparison is recorded.");return;}
    const featureQuery=$("feature-search").value.trim().toLowerCase(),companyQuery=$("company-search").value.trim().toLowerCase();
    const columns=selected.columns.map((name,index)=>({name,index})).filter(column=>column.index>0 && column.name.toLowerCase().includes(featureQuery));
    const rows=selected.rows.filter(row=>row[0].toLowerCase().includes(companyQuery));
    $("feature-count").textContent=`${rows.length} company rows · ${columns.length} of ${selected.columns.length-1} features in ${selected.title}. Select a cell for its definition and source note. Scroll the table horizontally for more columns.`;
    $("feature-detail").hidden=true;
    if(!columns.length || !rows.length){$("feature-table").innerHTML=empty("No matching companies or features. Change either filter.");return;}
    const classes={Y:"yes",P:"partial",N:"absent","?":"unknown"};
    $("feature-table").innerHTML='<table class="matrix" style="width:'+(220+155*columns.length)+'px"><thead><tr><th scope="col">Company</th>'+columns.map(column=>'<th scope="col">'+esc(column.name)+'</th>').join("")+'</tr></thead><tbody>'+rows.map((row,rowIndex)=>'<tr class="'+(row[0].startsWith("Loop Engine")?"engine-row":"")+'"><td>'+esc(row[0])+'</td>'+columns.map(column=>'<td><button type="button" class="'+classes[row[column.index]]+'" data-row="'+rowIndex+'" data-column="'+column.index+'" aria-label="'+esc(row[0]+", "+column.name+": "+row[column.index])+'">'+esc(row[column.index])+'</button></td>').join("")+'</tr>').join("")+'</tbody></table>';
    for(const button of $("feature-table").querySelectorAll("button"))button.addEventListener("click",()=>{
      const row=rows[Number(button.dataset.row)],feature=selected.columns[Number(button.dataset.column)];
      const notes=comparison.notes?.[row[0]] || "";
      const exact=notes.split("; ").filter(part=>part.startsWith(feature+": ")).map(part=>part.slice(feature.length+2)).join("; ");
      showPanel($("feature-detail"),row[0]+" · "+feature,'<p><strong>'+esc(row[Number(button.dataset.column)])+'</strong> · Original snapshot, 18 September 2026</p><p>'+esc(comparison.definitions?.[feature] || "No definition in the retained source.")+'</p><p><strong>Source note:</strong> '+esc(exact || "No separate note for this cell was included. The full original comparison is embedded below.")+'</p>');
    });
    const vendors=selected.rows.filter(row=>!row[0].startsWith("Loop Engine") && row[0]!=="Overmind, Lemma");
    $("feature-totals").innerHTML=table(["Feature","Y","P","N","?"],selected.columns.slice(1).map((name,index)=>[name,...["Y","P","N","?"].map(value=>vendors.filter(row=>row[index+1]===value).length)]));
  }

  function drawWork(){
    const current=new Set([...(plan.launch_order||[]),...(plan.improvement_order||[])]);
    const order=new Map([...current].map((id,index)=>[id,index]));
    const status=$("work-status").value,query=$("work-search").value.trim().toLowerCase();
    const selected=steps.filter(step=>($("work-scope").value==="all" || current.has(step.id)) &&
      (status==="all" || (status==="open" ? !finished.has(step.status) : step.status===status)) &&
      (!query || [step.id,step.title,step.acceptance,step.evidence,step.next_local_work,...(step.boundary||[])].join(" ").toLowerCase().includes(query)))
      .sort((a,b)=>(order.get(a.id)??1000)-(order.get(b.id)??1000));
    $("work-count").textContent=`${selected.length} matching steps. “Building” is not “verified”; earlier component statuses do not establish a completed release.`;
    $("work-items").innerHTML=selected.length ? selected.map(step=>'<details class="work-item"><summary><span class="step-id">'+esc(step.id)+'</span><span class="step-title">'+esc(step.title)+'</span>'+badge(step.status)+'</summary><div class="work-body">'+
      [["Next local work",step.next_local_work],["Acceptance",step.acceptance],["Current evidence",step.evidence],["Dependencies",(step.depends_on||[]).join(", ")||"None"],["Checks",(step.verify||[]).join("; ")],["Adversarial check",step.adversarial],["Owning components",(step.boundary||[]).join(", ")]].filter(row=>row[1]).map(([label,value])=>'<p><strong>'+esc(label)+':</strong> '+esc(value)+'</p>').join("")+'</div></details>').join("") : empty("No work matches these filters.");
  }

  function drawFiles(){
    const query=$("source-search").value.trim().toLowerCase(),folder=$("source-folder").value;
    const selected=files.filter(file=>(!folder || file.folder===folder) && (!query || sourceIndexes.get(file.path).includes(query)));
    $("source-count").textContent=`${selected.length} matching files · showing ${Math.min(visibleFiles,selected.length)}`;
    $("source-files").replaceChildren();
    for(const file of selected.slice(0,visibleFiles)){const button=document.createElement("button");button.type="button";button.className="source-file";button.textContent=file.path;button.setAttribute("aria-current",String(file.path===selectedFile));button.addEventListener("click",()=>showFile(file.path));$("source-files").appendChild(button);}
    $("more-files").hidden=visibleFiles>=selected.length;
    if(!selected.length)$("source-files").innerHTML=empty("No files match this search.");
  }

  function showFile(path){
    const file=byPath.get(path);if(!file){$("source-detail").innerHTML=empty("This source path is not in the measured inventory.");return;}
    selectedFile=path;const component=byComponent.get(path),id="file:"+path;
    const incoming=data.edges.filter(edge=>edge.target===id),outgoing=data.edges.filter(edge=>edge.source===id);
    const checks=component?.offline_checks;
    const relationships=rows=>table(["Relationship","Source","Target","Evidence"],rows.map(edge=>[edge.relation,edge.source.replace(/^file:/,""),edge.target.replace(/^file:/,""),edge.evidence+(edge.line?" · line "+edge.line:"")]));
    $("source-detail").innerHTML='<h3>'+esc(path)+'</h3><p class="description">'+esc(file.description || file.exclusion || "Source metadata")+'</p>'+table(["Evidence axis","Recorded state"],[
      ["Structural inspection",file.inspection],["Focused semantic review",file.semantic_review],
      ["Static import paths",component?.static_import_paths?.join(", ") || "Not in measured closures"],
      ["Module-owned checks",checks?`${checks.passed} passed; ${checks.failed} failed; ${checks.not_tested} not tested`:"Not recorded for this source identity"],
      ["Observed invocation",component?.observed_invocation || "Not measured by structural inspection"],
      ["Size",`${file.lines || 0} lines; ${file.symbols.length} symbols; ${file.tests.length} declared checks`]])+
      '<details open><summary>Incoming relationships ('+incoming.length+')</summary>'+relationships(incoming)+'</details><details open><summary>Outgoing relationships ('+outgoing.length+')</summary>'+relationships(outgoing)+'</details>'+
      '<details><summary>Classes, functions, fields and signatures ('+file.symbols.length+')</summary>'+table(["Symbol","Line","Shape"],file.symbols.map(symbol=>[symbol.kind+" "+symbol.name,symbol.line,JSON.stringify(symbol.kind==="class"?{bases:symbol.bases,fields:symbol.fields}:{arguments:symbol.arguments,returns:symbol.returns})]))+'</details>'+
      '<details><summary>Record shapes and module references</summary><p class="caption">Literals can occur in writers, readers or rejection tests. Their presence does not establish supported versions.</p><pre>'+esc(pretty(file.record_types))+'</pre></details>'+
      '<details><summary>Declared tests and focused review notes</summary><pre>'+esc(pretty({tests:file.tests,reviews:file.reviews||[]}))+'</pre></details>';
    drawFiles();
  }

  function initialize(){
    if(typeof ELK!=="undefined")elk=new ELK();
    window.LoopDevelopment.init(data);
    window.LoopHosting.init(data.hosting);
    for(const groupName of [...new Set(architecture.map(view=>view.group))]){
      const group=document.createElement("optgroup");group.label=groupName;
      for(const view of architecture.filter(row=>row.group===groupName)){const option=document.createElement("option");option.value=view.id;option.textContent=view.title;group.append(option);}
      $("architecture-area").append(group);
    }
    $("architecture-area").value=viewId;
    $("architecture-area").addEventListener("change",()=>drawArchitecture($("architecture-area").value));
    $("architecture-coverage").textContent=architecture.length+" architecture views cover the whole engine. Client/server is one section. Each component links to its source; arrows are structural relationships, not proof of an observed run.";
    const history=data.historical_comparison || {};
    $("summary").innerHTML=[[data.counts.component_rows,"mapped Python files"],[history.feature_count,"historical feature columns"],[(plan.launch_order||[]).length+(plan.improvement_order||[]).length,"continuation steps"],[data.counts.review_questions,"review questions"]].filter(row=>row[0]!==undefined).map(([number,label])=>'<span><strong>'+Number(number).toLocaleString()+'</strong>'+esc(label)+'</span>').join("");
    $("active-count").textContent=steps.filter(step=>step.status==="building" && step.id.startsWith("S-6.")).length;
    $("generated-at").textContent="Generated "+data.generated_at+" · working-tree source "+data.source_revision.slice(0,12);
    $("plan-freshness").textContent="Roadmap updated "+(plan.updated_at||"not recorded")+". This embedded snapshot refreshes when the repository report is regenerated, not when a browser checkbox changes.";
    const continuation=steps.filter(step=>(plan.launch_order||[]).includes(step.id)||(plan.improvement_order||[]).includes(step.id));
    $("work-summary").innerHTML=["building","ready","proposed","offline_verified"].map(state=>'<span><strong>'+continuation.filter(step=>step.status===state).length+'</strong>'+esc(words(state))+'</span>').join("");
    $("release-gates").innerHTML=(plan.gates||[]).map(gate=>'<div class="gate"><span>'+esc(gate.state)+'</span><div><p>'+esc(gate.title)+'</p><p class="caption">'+esc(gate.steps.join(", "))+'</p></div></div>').join("");
    $("owner-decisions").innerHTML=(plan.decisions||[]).map(decision=>'<div class="gate"><span>'+esc(words(decision.id))+" · "+esc(decision.state)+'</span><div><p>'+esc(decision.requirement)+'</p><p class="caption">Independent work: '+esc(decision.independent_work)+'</p></div></div>').join("");
    $("activity").innerHTML=(plan.activity||[]).map(row=>'<div class="gate"><span>'+esc(row.at)+'</span><div><p>'+esc(row.outcome)+'</p><p class="caption">'+esc(row.evidence)+'</p></div></div>').join("");
    for(const [index,section] of (history.tables||[]).entries()){const option=document.createElement("option");option.value=index;option.textContent=section.title;$("feature-family").appendChild(option);}
    $("comparison-tables").innerHTML='<p class="caption">'+esc(data.comparison?.limits||"")+'</p>'+(data.comparison?.tables||[]).map(section=>'<h3>'+esc(section.title)+'</h3>'+table(section.columns,section.rows)).join("");
    for(const folder of [...new Set(files.map(file=>file.folder))].sort()){const option=document.createElement("option");option.value=folder;option.textContent=folder;$("source-folder").appendChild(option);}
    const measured=data.check_evidence?.counts;
    $("evidence-state").textContent="Whole-source offline check evidence: "+words(data.check_evidence?.state||"not_recorded")+". "+(measured?`${measured.passed} of ${measured.passed+measured.failed} executed checks passed; ${measured.not_tested} optional checks were not tested. `:"")+"Local protocol and durable-domain checkpoints are separate scoped records. No provider qualification is inferred.";
    $("evidence-limits").textContent="Imports are not observed calls. Source parsing is not a semantic review of every file. Local fixtures are not live provider qualification. Historical comparison cells are not current completion claims. Missing usage, cost and evidence remain unknown.";
    $("entry-points").innerHTML=Object.entries(data.entry_points||{}).map(([name,row])=>'<p><strong>'+esc(words(name))+'</strong>: '+row.reached_modules+' of '+row.shipped_modules+' shipped modules in the static import closure. Observed invocation is not measured here.</p>').join("");
    $("question-count").textContent=(data.questions||[]).length+" retained review questions. An answer does not necessarily close the gap.";
    const openCounterexamples=(data.questions||[]).filter(row=>row.status==="open_confirmed_counterexample");
    if(openCounterexamples.length){$("known-issues").hidden=false;$("known-issues").textContent="Known open counterexamples: "+openCounterexamples.length+". "+openCounterexamples.map(row=>row.answer).join(" ")+" The passing offline suite does not cover every possible failure.";}
    $("questions").innerHTML=(data.questions||[]).map(row=>'<details class="question"><summary>'+esc(row.id+" · "+(row.question||row.title||row.status||"Review finding"))+'</summary><pre>'+esc(pretty(row))+'</pre></details>').join("");
    $("identities").textContent=pretty({source_revision:data.source_revision,population_digest:data.population_digest,plan_sha256:plan.source_sha256,comparison_sha256:history.source_sha256,check_evidence:data.check_evidence});
    const documents=data.documents || {};
    $("sol-pi-research").textContent=documents.sol_pi_review?.text || "Research not recorded in this snapshot.";
    $("decision-research").innerHTML=["decision_tools","circuit_review","semif_review"].filter(key=>documents[key]).map(key=>'<details class="subsection"><summary>'+esc(documents[key].title)+'</summary><pre>'+esc(documents[key].text)+'</pre></details>').join("");
    $("harness-layout").innerHTML='<p class="description">Implemented scaffolding, not a promise of native loading. Instructions describe authority; they never grant it.</p><pre>instance/\n├── AGENTS.md                 composed briefing and digest\n├── harness-specific alias   when the configured adapter declares it\n├── task.json                typed assignment and permissions\n├── provisioning.json        offers, withheld items and exact identities\n├── contracts/               created empty\n└── artifacts/               created empty</pre><p class="caption">Large bodies are not included by default. Selected skill/context materialization and proof of actual native loading remain integration work.</p><details class="subsection"><summary>Templates, context organization and remaining checks</summary><pre>'+esc(documents.harness_layout?.text || "Not recorded")+'</pre></details>';
    for(const [id,key] of [["owner-checklist","owner_checklist"],["execution-plan","execution_plan"],["original-comparison","original_comparison"],["retrieval-research","retrieval_research"]])$(id).textContent=documents[key]?.text || "Not recorded in this report.";
    for(const [id,keys] of [["architecture-notes",["runtime_guide","practitioner_guide","solution_guide","intelligence_guide","capabilities_guide","improvement_guide","configuration_dimensions","wrapper_direction","client_server","retrieval_architecture"]],["checkpoint-notes",["durable_checkpoint","http_checkpoint","session_checkpoint"]]])$(id).innerHTML=keys.filter(key=>documents[key]).map(key=>'<details class="subsection"><summary>'+esc(documents[key].title)+'</summary><pre>'+esc(documents[key].text)+'</pre></details>').join("");
    $("publication-notes").innerHTML=["publication_review","public_content","frontier_positioning"].filter(key=>documents[key]).map(key=>'<details class="subsection"><summary>'+esc(documents[key].title)+'</summary><pre>'+esc(documents[key].text)+'</pre></details>').join("");
    for(const button of document.querySelectorAll("[data-page],[data-open-page]"))button.addEventListener("click",()=>openPage(button.dataset.page||button.dataset.openPage));
    for(const button of document.querySelectorAll("[data-level]"))button.addEventListener("click",()=>drawArchitecture(button.dataset.level));
    for(const id of ["feature-family","feature-search","company-search"])$(id).addEventListener("input",drawFeatures);
    for(const id of ["website-search","website-cohort"])$(id).addEventListener("input",drawWebsites);
    drawWebsites();
    const candidates=data.candidate_review?.records||[];
    $("candidate-count").textContent=candidates.length+" candidates · "+new Set(candidates.map(row=>row.intelligence_layer)).size+" persistent layers · "+new Set(candidates.map(row=>row.attributes.family)).size+" content families. Independent qualification: not completed.";
    $("candidate-table").innerHTML='<table><thead><tr><th scope="col">Title</th><th scope="col">Layer</th><th scope="col">Content family</th><th scope="col">State</th></tr></thead><tbody>'+candidates.map((row,index)=>'<tr><th scope="row"><button type="button" data-candidate="'+index+'">'+esc(row.payload.title)+'</button></th><td>'+esc(row.intelligence_layer)+'</td><td>'+esc(row.attributes.family)+'</td><td>Candidate only</td></tr>').join("")+'</tbody></table>';
    for(const button of $("candidate-table").querySelectorAll("button"))button.addEventListener("click",()=>{const row=candidates[Number(button.dataset.candidate)];showPanel($("candidate-detail"),row.payload.title,'<p>'+esc(row.payload.text)+'</p><p class="caption">License review and independent qualification remain required. Source files may have changed after staging; the recorded digest must be checked before admission.</p><pre>'+esc(JSON.stringify(row,null,2))+'</pre>');});
    for(const id of ["work-scope","work-status","work-search"])$(id).addEventListener("input",drawWork);
    for(const id of ["source-search","source-folder"])$(id).addEventListener("input",()=>{visibleFiles=100;drawFiles();});
    $("more-files").addEventListener("click",()=>{visibleFiles+=100;drawFiles();});
    $("theme").addEventListener("change",()=>{document.documentElement.dataset.theme=$("theme").value;try{localStorage.setItem("loop-system-map-theme",$("theme").value);}catch(error){}});
    try{const theme=localStorage.getItem("loop-system-map-theme");if(["light","dark","system"].includes(theme)){$("theme").value=theme;document.documentElement.dataset.theme=theme;}}catch(error){}
    for(const button of document.querySelectorAll("[data-download]"))button.addEventListener("click",()=>{
      const name=button.dataset.download,archive=data.archives?.[name];if(!archive)return;
      const bytes=Uint8Array.from(atob(archive),character=>character.charCodeAt(0));const url=URL.createObjectURL(new Blob([bytes],{type:"application/gzip"}));
      const anchor=document.createElement("a");anchor.href=url;anchor.download="loop-engine-"+name+".json.gz";anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    });
    window.addEventListener("hashchange",()=>openPage(location.hash.slice(1),false));
    new ResizeObserver(()=>{const width=$("architecture-graph").getBoundingClientRect().width;if(page==="architecture"&&Math.abs(width-lastWidth)>1)drawArchitecture(viewId);}).observe($("architecture-graph"));
    const initial=location.hash.slice(1);
    drawFeatures();drawWork();openPage($("page-"+initial)?initial:"development",false);
    window.LoopSystemMap={openPage,drawArchitecture,showFile,state:()=>({page,view:viewId,views:architecture.map(row=>row.id),layout:lastLayout,featureTables:(history.tables||[]).length,featureColumns:history.feature_count,steps:steps.length,files:files.length})};
    document.body.dataset.ready="true";
  }
  if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",initialize);else initialize();
})();
