/* Shared by the live route check and its local, controlled browser checks. */
export const INITIAL_OBSERVATION_MS=1500, READINESS_TIMEOUT_MS=10000;

/* Runs in the page. A loading/error title is not evidence that documentation loaded. */
export function visiblePageState({documentation=null,waitForReady=false}={}){
  const visible=node=>!!node&&node.getClientRects().length>0&&!node.closest("[hidden]")&&getComputedStyle(node).visibility!=="hidden";
  const heading=[...document.querySelectorAll("h1")].find(visible);
  const scroller=document.scrollingElement||document.documentElement;
  const links=[...document.querySelectorAll("a[href]")].filter(visible).map(link=>link.href).filter(href=>href.startsWith(location.origin));
  const article=document.getElementById("docs-article"),cards=document.querySelectorAll("#docs-cards li");
  let contentState="not_required",contentPresent=true,refusals=[];
  if(documentation==="page"){
    refusals=[...document.querySelectorAll("#docs-article [data-docs-refused]")].map(node=>node.dataset.docsRefused);
    contentState=article?.dataset.docsState||"unavailable";
    contentPresent=visible(article)&&article.getAttribute("aria-busy")!=="true"&&refusals.length===0
      &&[...article.children].some(node=>visible(node)&&node.textContent.trim()&&!node.matches(".docs-note,[data-docs-refused]"));
  }else if(documentation==="index"){
    contentPresent=[...cards].some(visible);
    contentState=contentPresent?"ready":"unavailable";
  }
  const state={heading:heading?heading.textContent.replace(/\s+/g," ").trim():"",sideways:scroller.scrollWidth-innerWidth,
    links:[...new Set(links.map(href=>href.split("#")[0]))],documentation,content_state:contentState,
    content_present:contentPresent,refusals};
  state.ready=Boolean(state.heading)&&contentPresent&&(!documentation||contentState==="ready");
  state.terminal_failure=Boolean(documentation)&&["error","missing"].includes(contentState);
  return waitForReady?state.ready||state.terminal_failure:state;
}

export function readinessProblems(state){
  const problems=[];
  if(!state.heading)problems.push("shows no main heading");
  if(state.documentation&&(state.content_state!=="ready"||!state.content_present))
    problems.push(`documentation content is not ready (${state.content_state})`);
  return problems;
}

export const shouldCaptureView=({size,scheme,failed})=>failed||(size==="desktop"&&scheme==="light")||(size==="phone"&&scheme==="dark");

export async function observePageReadiness(page,{documentation=null,initialDelayMs=INITIAL_OBSERVATION_MS,
  timeoutMs=READINESS_TIMEOUT_MS,onInitialNotReady=async()=>{}}={}){
  if(!Number.isInteger(initialDelayMs)||initialDelayMs<0||initialDelayMs>INITIAL_OBSERVATION_MS
    ||!Number.isInteger(timeoutMs)||timeoutMs<1||timeoutMs>READINESS_TIMEOUT_MS)
    throw new Error("Readiness intervals must stay within the declared bounds.");
  const started=performance.now(),errors=[];
  const read=async()=>page.evaluate(visiblePageState,{documentation}).catch(error=>{
    errors.push(String(error.message||error).slice(0,200));
    return {heading:"",sideways:0,links:[],documentation,content_state:"unreadable",content_present:false,ready:false,terminal_failure:false};
  });
  await page.waitForTimeout(initialDelayMs);
  const initial=await read(),initialAt=performance.now()-started,deadline=performance.now()+timeoutMs;
  if(!initial.ready)await onInitialNotReady(initial);
  let timedOut=false;
  if(!initial.ready&&!initial.terminal_failure){
    try{await page.waitForFunction(visiblePageState,{documentation,waitForReady:true},{timeout:Math.max(1,deadline-performance.now())});}
    catch(error){timedOut=error.name==="TimeoutError";errors.push(String(error.message||error).slice(0,200));}
  }
  const seen=await read(),finishedAt=performance.now()-started;
  const indexFetches=await page.evaluate(()=>performance.getEntriesByType("resource")
    .filter(entry=>new URL(entry.name).pathname==="/assets/documentation-index.json")
    .map(entry=>({start_ms:entry.startTime,duration_ms:entry.duration,response_end_ms:entry.responseEnd}))).catch(()=>[]);
  const compact=state=>({heading:state.heading,ready:state.ready,content_state:state.content_state,content_present:state.content_present});
  return {seen,readiness:{initial_delay_ms:initialDelayMs,timeout_after_initial_ms:timeoutMs,
    initial_observed_ms:initialAt,final_observed_ms:finishedAt,late:!initial.ready&&seen.ready,
    timed_out:timedOut,initial:compact(initial),final:compact(seen),index_fetches:indexFetches,errors}};
}
