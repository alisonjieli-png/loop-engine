/* Passive browser preparation for tools/overnight_queue.py and its v2 status.
   A prepared command grants no execution authority. Files stay in the browser. */
export const STATUS_VERSION="overnight_queue_status/v2";
export const MAX_REPORT_BYTES=4*1024*1024;
export const MAX_MANIFEST_BYTES=1024*1024;
const encoder=new TextEncoder();
const positive=(value,name)=>{
  const number=Number(value);
  if(!Number.isSafeInteger(number)||number<1)throw Error(name+" must be a positive whole number.");
  return number;
};
const path=(value,name)=>{
  if(typeof value!=="string"||!value.startsWith("/")||/[\x00-\x1f\x7f]/.test(value))
    throw Error(name+" needs an absolute path on your worker.");
  return value;
};
export const shellQuote=value=>"'"+String(value).replaceAll("'","'\\''")+"'";

export function prepareQueue(input){
  if(typeof input.tasks!=="string")throw Error("Add one task path per line.");
  const tasks=input.tasks.split(/\r?\n/).map(value=>value.trim()).filter(Boolean);
  if(!tasks.length)throw Error("Add at least one task path.");
  tasks.forEach(value=>path(value,"Each task"));
  if(new Set(tasks).size!==tasks.length)throw Error("Use each task path once.");
  const manifest=tasks.join("\n")+"\n";
  if(encoder.encode(manifest).length>MAX_MANIFEST_BYTES)throw Error("The task manifest exceeds the worker's 1 MiB limit.");
  const root=path(input.checkout,"Checkout"),runs=path(input.runs,"Run folder"),workspace=path(input.workspace,"Workspace folder");
  const calls=positive(input.calls,"Calls per task"),budget=positive(input.budget,"Queue call budget");
  const timeout=positive(input.timeout,"Task timeout"),deadline=positive(input.deadline,"Queue time limit");
  const command=["PYTHONPATH=src .venv/bin/python tools/overnight_queue.py",shellQuote(root+"/baltor-tasks.txt"),
    "--runs-dir",shellQuote(runs),"--workspace-root",shellQuote(workspace),
    "--max-calls-per-task",calls,"--queue-call-budget",budget,
    "--task-timeout",timeout,"--queue-timeout",deadline].join(" ");
  return {manifest,taskCount:tasks.length,command:"cd "+shellQuote(root)+" &&\n"+command,
    statusCommand:"cd "+shellQuote(root)+" &&\n"+command+" --status",calls,budget,timeout,deadline};
}

export function readQueueStatus(text){
  if(typeof text!=="string"||encoder.encode(text).length>MAX_REPORT_BYTES)throw Error("Choose a status file up to 4 MiB.");
  let value;
  try{value=JSON.parse(text);}catch{throw Error("Choose the JSON output of the queue's --status command.");}
  if(!value||value.record_type!==STATUS_VERSION||!Array.isArray(value.attempts))
    throw Error("This viewer reads the worker's overnight_queue_status/v2 record.");
  for(const name of ["calls_allocated","call_budget"])
    if(!Number.isSafeInteger(value[name])||value[name]<0)throw Error("The status has an invalid "+name+" value.");
  if(value.calls_allocated>value.call_budget)throw Error("Reserved calls exceed the recorded budget. Inspect the worker record.");
  if(!Number.isFinite(value.deadline)||value.deadline<0||value.deadline>8.64e12)throw Error("The status needs a valid queue deadline.");
  if(value.observed_model_calls!==null&&(!Number.isSafeInteger(value.observed_model_calls)||value.observed_model_calls<0))
    throw Error("Observed model usage must be a count or null.");
  const statuses=new Set(["reserved","finished","unknown","reconciled"]);
  const attempts=value.attempts.map(row=>{
    if(!row||typeof row!=="object"||!statuses.has(row.queue_status)||typeof row.task_file!=="string"||
      !Number.isSafeInteger(row.allocation)||row.allocation<0||
      (row.exit!==null&&row.exit!==undefined&&!Number.isSafeInteger(row.exit)))
      throw Error("An attempt has an unsupported status or invalid fields.");
    return {task:row.task_file,status:row.queue_status,allocated:row.allocation,exit:row.exit??null};
  });
  return {allocated:value.calls_allocated,budget:value.call_budget,observed:value.observed_model_calls,
    deadline:value.deadline,attempts};
}
