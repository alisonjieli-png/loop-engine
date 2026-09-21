/* Dated hosting guidance. Reading this page performs no provisioning. */
window.LoopHosting = (() => {
  "use strict";
  const $=id=>document.getElementById(id);
  const make=(tag,text,cls)=>{const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;};
  function link(url,label="Official source"){
    const node=make("a",label),parsed=new URL(url);
    if(parsed.protocol!=="https:")throw new Error("Hosting sources must use HTTPS");
    node.href=url;node.target="_blank";node.rel="noopener noreferrer";return node;
  }
  function grid(id,columns,rows,source){
    const value=make("table"),head=make("tr"),body=make("tbody"),thead=make("thead");
    for(const name of columns){const cell=make("th",name);cell.scope="col";head.append(cell);}thead.append(head);value.append(thead);
    for(const row of rows){const tr=make("tr");for(const text of row.values)tr.append(make("td",text));
      if(source){const td=make("td");td.append(link(row.source));tr.append(td);}body.append(tr);}
    value.append(body);$(id).replaceChildren(value);
  }
  const table=(id,columns,rows)=>grid(id,columns,rows,true);
  function init(data){
    if(!data)return;
    $("hosting-title").textContent=data.title;
    $("hosting-recommendation").textContent=data.recommendation;
    $("hosting-status").textContent=data.status;
    $("hosting-assumptions").textContent=data.assumptions;
    $("hosting-checked").textContent="Provider state read "+data.checked_at+", without changing anything. Recheck the selected region and invoice estimate before creating paid resources.";
    $("hosting-live-note").textContent=data.live_state_note;
    grid("hosting-live",["Subject","What is true today","Standing","Where this was checked"],
      data.live_state.map(row=>({values:[row.subject,row.fact,row.standing,row.checked]})),false);
    const corrections=make("ol");
    for(const row of data.corrections){
      const item=make("li");
      item.append(make("p","No longer true: "+row.was,"owner-safety"),make("p","Correct today: "+row.now));
      corrections.append(item);
    }
    $("hosting-corrections").replaceChildren(corrections);
    $("hosting-operations").replaceChildren(...data.operations.map(row=>{
      const section=make("article",undefined,"hosting-procedure");section.append(make("h4",row.title));
      const list=make("ol");for(const step of row.steps)list.append(make("li",step));section.append(list);return section;}));
    grid("hosting-outages",["Provider","What breaks first","What keeps working","What to do"],
      data.outages.map(row=>({values:[row.provider,row.first,row.keeps,row.action]})),false);
    table("hosting-stack",["Responsibility","Recommended choice","Why","State today","Source"],data.stack.map(row=>({values:[row.part,row.choice,row.why,row.initial],source:row.source})));
    table("hosting-costs",["Item","Monthly example","Conditions","Source"],data.costs.map(row=>({values:[row.item,row.monthly,row.conditions],source:row.source})));
    table("hosting-alternatives",["Option","Fit","Trade-off","Source"],data.alternatives.map(row=>({values:[row.choice,row.fit,row.tradeoff],source:row.source})));
    $("hosting-regions").textContent=data.regions;
    $("hosting-region-sources").replaceChildren(...data.region_sources.map(url=>link(url,new URL(url).hostname)));
    $("hosting-today").replaceChildren();
    for(const row of data.do_now){
      const section=make("article",undefined,"hosting-action");section.append(make("h3",row.title),link(row.url,"Open the dashboard or official instructions"));
      const list=make("ol");for(const instruction of row.steps)list.append(make("li",instruction));section.append(list);
      section.append(make("p","Send back: "+row.send,"handoff-line"),make("p","Wait for engineering: "+row.wait,"owner-safety"));$("hosting-today").append(section);
    }
    for(const [id,values] of [["hosting-engineering",data.engineering],["hosting-wait",data.wait_for]]){const list=make("ol");for(const text of values)list.append(make("li",text));$(id).replaceChildren(list);}
    $("hosting-connection").textContent=data.connection_note;$("hosting-connection-source").replaceChildren(link(data.connection_source));
    $("hosting-cost-note").textContent=data.cost_note;$("hosting-cost-sources").replaceChildren(...data.cost_sources.map(url=>link(url,new URL(url).hostname)));
  }
  return {init};
})();
