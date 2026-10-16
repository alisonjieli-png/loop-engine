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

/* Text a person cannot read because its column is too narrow. On October 16, 2026 the launch audit found the four steps of
   /case-studies/sign-up-protection wrapped one or two letters to a line at every width: a two-column grid placed each step's
   text, an anonymous grid item, in the 2rem number column. Every page opened, kept its heading and had no script error, so
   no check noticed. A run of ordinary text that wraps into at least five lines of fewer than six characters each is refused;
   code, pictures and visually hidden text are not read. */
export const SQUEEZED_TEXT={minimumCharacters:24,minimumLines:5,charactersPerLineBelow:6};
export const isSqueezed=({characters,lines})=>characters>=SQUEEZED_TEXT.minimumCharacters&&lines>=SQUEEZED_TEXT.minimumLines
  &&characters/lines<SQUEEZED_TEXT.charactersPerLineBelow;

/* Runs in the page: each visible text node long enough to judge, with its length and its number of line boxes. */
export function squeezedTextCandidates({minimumCharacters,minimumLines}){
  const shown=node=>!!node&&node.getClientRects().length>0&&!node.closest("[hidden]")&&getComputedStyle(node).visibility!=="hidden";
  const found=[],walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  for(let node=walker.nextNode();node&&found.length<20;node=walker.nextNode()){
    const text=node.textContent.replace(/\s+/g," ").trim(),parent=node.parentElement;
    if(text.length<minimumCharacters||!parent||!shown(parent)
      ||parent.closest("pre,code,kbd,samp,script,style,svg,textarea,[aria-hidden='true'],.sr-only,.deck-visually-hidden"))continue;
    const range=document.createRange();range.selectNodeContents(node);
    const lines=new Set([...range.getClientRects()].filter(box=>box.width>0&&box.height>0).map(box=>Math.round(box.top))).size;
    if(lines>=minimumLines)found.push({text:text.slice(0,60),characters:text.length,lines});
  }
  return found;
}

export const squeezedTextProblems=candidates=>candidates.filter(isSqueezed)
  .map(item=>`squeezes "${item.text}" into ${item.lines} lines of about ${Math.max(1,Math.round(item.characters/item.lines))} characters`);

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
