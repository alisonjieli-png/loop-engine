import {prepareQueue,readQueueStatus,MAX_REPORT_BYTES} from "./run-desk-core.js";

const form=document.getElementById("run-desk-form");
if(form){
  const message=document.getElementById("run-desk-message"),command=document.getElementById("run-desk-command"),
    statusCommand=document.getElementById("run-desk-status-command"),download=document.getElementById("run-desk-download");
  let prepared=null;
  form.addEventListener("input",()=>{
    prepared=null;download.disabled=true;command.textContent="";statusCommand.textContent="";
    message.textContent="Prepare the queue again to apply your changes.";
  });
  form.addEventListener("submit",event=>{
    event.preventDefault();
    try{
      prepared=prepareQueue(Object.fromEntries(new FormData(form)));
      command.textContent=prepared.command;statusCommand.textContent=prepared.statusCommand;
      download.disabled=false;
      message.textContent=prepared.taskCount+" task paths prepared. Save the manifest in your checkout, review the command, then run it on your worker.";
    }catch(error){prepared=null;download.disabled=true;command.textContent="";statusCommand.textContent="";message.textContent=error.message;}
  });
  download.addEventListener("click",()=>{
    if(!prepared)return;
    const link=document.createElement("a"),url=URL.createObjectURL(new Blob([prepared.manifest],{type:"text/plain;charset=utf-8"}));
    link.href=url;link.download="baltor-tasks.txt";link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  const file=document.getElementById("run-desk-report"),summary=document.getElementById("run-desk-summary"),body=document.getElementById("run-desk-attempts");
  let readGeneration=0;
  file.addEventListener("change",async()=>{
    const generation=++readGeneration,chosen=file.files?.[0];
    body.replaceChildren();summary.textContent="Choose a queue status report to inspect its attempts.";
    if(!chosen)return;
    try{
      if(chosen.size>MAX_REPORT_BYTES)throw Error("Choose a status file up to 4 MiB.");
      const result=readQueueStatus(await chosen.text());if(generation!==readGeneration)return;
      summary.textContent="Calls reserved: "+result.allocated+" of "+result.budget+". Observed model calls: "+
        (result.observed===null?"not measured":result.observed)+". Queue deadline: "+new Date(result.deadline*1000).toLocaleString()+".";
      for(const row of result.attempts){
        const tr=document.createElement("tr");
        for(const value of [row.task,row.status,String(row.allocated),row.exit===null?"Awaiting an outcome":String(row.exit)]){
          const td=document.createElement("td");td.textContent=value;tr.append(td);
        }
        body.append(tr);
      }
    }catch(error){if(generation===readGeneration)summary.textContent=error.message;}
  });
}
