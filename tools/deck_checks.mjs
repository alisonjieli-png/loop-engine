/* Browser checks of the deck at /deck, run by tools/check_service_workspace.mjs against its loopback service.

   The owner asked on September 24, 2026 for a deck served at deck.baltor.ai. Every number on it must carry a source
   note and the page must name no retired or invitation wording, so both rules are read here from the rendered page,
   hidden slides included, and each has removed-guard controls that serve changed bytes in memory and must fail it.
   tools/test_deck_page.py holds the same number rule over the packaged file, checks every number against the record
   it names, and compares its copy of the rule with the one exported here. The other checks drive the deck the way a
   reader does: the arrow keys, a swipe, the overview, a slide's own address, and a phone and a desktop window. */
import {existsSync,readFileSync} from "node:fs";
import {resolve} from "node:path";

/* A number on a slide: digits, with the separators a written number uses, or a number word. "one" is left out
   because it is also a pronoun; a claim that needs it is written with its numeral. */
export const deckNumberPattern=String.raw`(?<![A-Za-z0-9])\d+(?:[.,:]\d+)*`;
export const deckNumberWords=["two","three","four","five","six","seven","eight","nine","ten","eleven","twelve","twenty","thirty","forty","fifty",
  "sixty","seventy","eighty","ninety","hundred","hundreds","thousand","thousands","million","millions","billion","billions","dozen","dozens",
  "half","twice","double","triple"];
const numberPattern=new RegExp(deckNumberPattern+"|\\b(?:"+deckNumberWords.join("|")+")\\b","gi");
const deckPaths={page:"/deck",css:"/assets/deck.css",script:"/assets/deck.js",card:"/assets/deck-card.png"};
const slideIds=["cover","problem","what","how","live","measured","plan","business","why-now","contact"];
export const deckScreenshotSuffixes=[...slideIds.map((id,index)=>`-deck-1440-${String(index+1).padStart(2,"0")}-${id}.png`),
  ...slideIds.map((id,index)=>`-deck-390-${String(index+1).padStart(2,"0")}-${id}.png`)];

/* Read inside the page: every number of every slide, hidden slides included, and where its source note is. */
function numberProblems(pattern){
  const found=[],matcher=new RegExp(pattern.source,pattern.flags);
  for(const slide of document.querySelectorAll("[data-slide]")){
    const walker=document.createTreeWalker(slide,NodeFilter.SHOW_TEXT);
    for(let node=walker.nextNode();node;node=walker.nextNode()){
      const parent=node.parentElement;
      if(!parent||parent.closest(".deck-source"))continue;
      for(const match of node.textContent.matchAll(matcher)){
        const fact=parent.closest("[data-fact]"),notes=fact&&slide.contains(fact)?fact.querySelectorAll(".deck-source"):[];
        const note=notes.length===1?notes[0]:null;
        if(!fact||!slide.contains(fact))found.push({slide:slide.id,number:match[0],problem:"no data-fact element holds it"});
        else if(!note)found.push({slide:slide.id,number:match[0],problem:"its fact holds "+notes.length+" source notes, not one"});
        else if(!note.querySelector("a[href]")||!note.textContent.trim())found.push({slide:slide.id,number:match[0],problem:"its source note links no record"});
        else if(!(fact.dataset.evidence||"").trim())found.push({slide:slide.id,number:match[0],problem:"its fact names no record in data-evidence"});
      }
    }
  }
  return found;
}
/* Read inside the page: the words a reader meets, whether shown now or on another slide, and the head a shared link shows. */
function deckWords(){
  const head=[...document.querySelectorAll('meta[name="description"], meta[property^="og:"], meta[name^="twitter:"]')]
    .map(meta=>meta.getAttribute("content")||"").filter(value=>!/^https?:/.test(value));
  const labels=[...document.querySelectorAll("[aria-label], img[alt]")].map(item=>item.getAttribute("aria-label")||item.getAttribute("alt")||"");
  return [document.title,...head,...labels,document.body.textContent].join("\n").replace(/\s+/g," ");
}
const wordProblems=(text,words)=>[["retired access word",words.retiredAccessWords],["invitation word",words.invitationWords],["runtime word",words.publicVocabulary]]
  .filter(([,rule])=>rule.test(text)).map(([rule,pattern])=>({rule,found:text.match(pattern)[0]}));
const shown=page=>page.evaluate(()=>[...document.querySelectorAll("[data-slide]")].filter(slide=>!slide.hidden).map(slide=>slide.id));

export async function runDeckChecks({root,browser,base,localOnly,check,mutants,output,safeError,errors,words}){
  /* The canonical origin comes from the typed site map, the one record of the website's hostnames. */
  const siteMap=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_site_map.json"),"utf8"));
  const canonicalOrigin=new URL("https://"+siteMap.canonical_hostname).origin;
  for(const suffix of deckScreenshotSuffixes)if(existsSync(output.replace(/\.json$/,suffix)))throw new Error("Refusing to overwrite an existing deck screenshot: "+suffix);
  const opened=[];
  const open=async ({width=1440,height=900,touch=false,mutation=null,hash=""}={})=>{
    const context=await browser.newContext({viewport:{width,height},hasTouch:touch,isMobile:touch,reducedMotion:"reduce"});
    opened.push(context);
    const state={applied:false,errors:[],responses:[]};
    await context.route("**/*",localOnly);
    if(mutation)await context.route(url=>url.origin===new URL(base).origin&&url.pathname===mutation.path,async route=>{
      const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);
      state.applied=changed!==source;await route.fulfill({response,body:changed});});
    const page=await context.newPage();
    page.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    page.on("response",response=>state.responses.push(response));
    await page.goto(base+deckPaths.page+hash,{waitUntil:"load"});
    await page.evaluate(()=>document.fonts.ready.then(()=>true));
    return {page,state,close:()=>context.close().catch(()=>{})};
  };

  /* The page, its three files and the picture a shared link shows. */
  const first=await open(),served={};
  for(const [name,path] of Object.entries(deckPaths)){const response=await first.page.request.get(base+path);served[name]={status:response.status(),type:(response.headers()["content-type"]||"").split(";")[0],body:await response.body()};}
  await first.close();
  const card=served.card.body,cardSize=card.length>24&&card.subarray(1,4).toString()==="PNG"?[card.readUInt32BE(16),card.readUInt32BE(20)]:null;
  check("deck_page_and_its_files_are_served",served.page.status===200&&served.page.type==="text/html"&&served.css.type==="text/css"&&served.script.type==="text/javascript"
    &&served.card.type==="image/png"&&JSON.stringify(cardSize)==="[1200,630]",{statuses:Object.fromEntries(Object.entries(served).map(([name,item])=>[name,item.status+" "+item.type])),card:cardSize});

  const {page}=await open();
  const head=await page.evaluate(()=>{const meta=selector=>document.querySelector(selector)?.getAttribute("content")||"";
    return {title:document.title,description:meta('meta[name="description"]'),canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||"",
      ogTitle:meta('meta[property="og:title"]'),ogDescription:meta('meta[property="og:description"]'),ogImage:meta('meta[property="og:image"]'),ogUrl:meta('meta[property="og:url"]'),
      card:meta('meta[name="twitter:card"]'),views:[...document.querySelectorAll("[data-view]")].map(view=>view.dataset.view),
      h1:[...document.querySelectorAll("h1")].filter(item=>item.getClientRects().length).length};});
  check("deck_page_carries_a_description_and_a_social_card",head.title===siteMap.display_name+" | Deck"&&head.description.length>=80&&head.canonical===canonicalOrigin+deckPaths.page
    &&head.ogTitle!==""&&head.ogDescription!==""&&head.ogImage===canonicalOrigin+deckPaths.card&&head.ogUrl===head.canonical&&head.card==="summary_large_image"
    &&JSON.stringify(head.views)==='["deck"]'&&head.h1===1,head);

  /* The two rules of the owner's request, read from the rendered page. */
  const checkNumbers=async (target,note)=>{const found=await target.evaluate(numberProblems,numberPattern);note("deck_every_number_has_a_source_note",found.length===0,{problems:found.slice(0,12)});};
  const checkWords=async (target,note)=>{const found=wordProblems(await target.evaluate(deckWords),words);note("deck_names_no_retired_or_invitation_wording",found.length===0,{problems:found});};
  await checkNumbers(page,check);await checkWords(page,check);
  const slideCount=await page.evaluate(()=>document.querySelectorAll("[data-slide]").length);
  check("deck_holds_the_slides_it_names",slideCount===slideIds.length&&JSON.stringify(await page.evaluate(()=>[...document.querySelectorAll("[data-slide]")].map(slide=>slide.id)))===JSON.stringify(slideIds),{slides:slideCount});

  /* The keys, a slide's own address and the overview. */
  const checkKeys=async (target,note)=>{
    const seen=[await shown(target)];
    for(const key of ["ArrowRight","ArrowRight","ArrowLeft","End","Home","PageDown","Space"]){await target.keyboard.press(key);seen.push(await shown(target));}
    const hash=await target.evaluate(()=>location.hash);
    note("deck_moves_with_the_keyboard",JSON.stringify(seen)===JSON.stringify([["cover"],["problem"],["what"],["problem"],["contact"],["cover"],["problem"],["what"]])&&hash==="#what",{seen,hash});
  };
  await checkKeys(page,check);
  {const {page:direct,close}=await open({hash:"#why-now"});
    check("deck_opens_the_slide_its_address_names",JSON.stringify(await shown(direct))==='["why-now"]'&&await direct.locator("#deck-position").textContent()==="9 / 10");
    await close();}
  await page.keyboard.press("o");
  const overview=await page.evaluate(()=>({open:!document.getElementById("deck-overview").hidden,links:[...document.querySelectorAll("#deck-overview-list a")].map(link=>link.getAttribute("href"))}));
  await page.locator('#deck-overview-list a[href="#plan"]').click();
  const afterPick={slides:await shown(page),open:await page.evaluate(()=>!document.getElementById("deck-overview").hidden),hash:await page.evaluate(()=>location.hash)};
  await page.locator("#deck-overview-button").click();await page.keyboard.press("Escape");
  const afterEscape=await page.evaluate(()=>!document.getElementById("deck-overview").hidden);
  check("deck_overview_lists_every_slide_and_opens_one",overview.open&&JSON.stringify(overview.links)===JSON.stringify(slideIds.map(id=>"#"+id))
    &&JSON.stringify(afterPick.slides)==='["plan"]'&&!afterPick.open&&afterPick.hash==="#plan"&&!afterEscape,{overview,afterPick,afterEscape});

  /* A swipe on a phone: sideways moves the deck, upward and downward scroll the page. */
  const swipe=async (target,from,to)=>{const session=await target.context().newCDPSession(target);
    await session.send("Input.dispatchTouchEvent",{type:"touchStart",touchPoints:[{x:from[0],y:from[1]}]});
    for(let step=1;step<=6;step++)await session.send("Input.dispatchTouchEvent",{type:"touchMove",touchPoints:[{x:from[0]+(to[0]-from[0])*step/6,y:from[1]+(to[1]-from[1])*step/6}]});
    await session.send("Input.dispatchTouchEvent",{type:"touchEnd",touchPoints:[]});await target.waitForTimeout(80);};
  const checkSwipe=async (target,note)=>{
    const seen=[await shown(target)];
    await swipe(target,[320,420],[60,430]);seen.push(await shown(target));
    await swipe(target,[320,420],[60,430]);seen.push(await shown(target));
    await swipe(target,[60,420],[330,425]);seen.push(await shown(target));
    await swipe(target,[200,600],[210,300]);seen.push(await shown(target));
    note("deck_moves_with_a_swipe",JSON.stringify(seen)===JSON.stringify([["cover"],["problem"],["what"],["problem"],["problem"]]),{seen});
  };
  const phone=await open({width:390,height:844,touch:true});
  await checkSwipe(phone.page,check);

  /* Readable at 1440 and 390: every slide fits a desktop window with its controls in view, and no slide on a phone
     moves sideways or sets text smaller than the website's smallest size. */
  const measureSlides=async (target,width)=>{const rows=[];
    for(const [index,id] of slideIds.entries()){
      await target.evaluate(slide=>{location.hash=slide;},id);await target.waitForFunction(slide=>!document.getElementById(slide).hidden,id);
      rows.push(await target.evaluate(id=>{const frame=document.getElementById("deck-frame").getBoundingClientRect(),slide=document.getElementById(id);
        const texts=[...slide.querySelectorAll("*")].filter(item=>[...item.childNodes].some(node=>node.nodeType===3&&node.textContent.trim())&&item.getClientRects().length);
        /* Text in the diagram is drawn at the scale of its picture, so its size is read as a reader sees it. */
        const size=item=>{const svg=item.closest("svg"),scale=svg&&svg.viewBox.baseVal&&svg.viewBox.baseVal.width?svg.getBoundingClientRect().width/svg.viewBox.baseVal.width:1;
          return parseFloat(getComputedStyle(item).fontSize)*scale;};
        const smallest=texts.reduce((least,item)=>Math.min(least,size(item)),99);
        /* Body text: every paragraph but a source note and an eyebrow label, which the design standards set at 12 to 13 pixels. */
        const body=[...slide.querySelectorAll("p")].filter(item=>!item.closest(".deck-source, .deck-eyebrow")&&item.getClientRects().length)
          .reduce((least,item)=>Math.min(least,parseFloat(getComputedStyle(item).fontSize)),99);
        return {id,frame_bottom:Math.round(frame.bottom+scrollY),window:innerHeight,sideways:document.documentElement.scrollWidth-innerWidth,smallest_text:smallest,smallest_paragraph:body};},id));
      const path=output.replace(/\.json$/,`-deck-${width}-${String(index+1).padStart(2,"0")}-${id}.png`);
      if(width===1440)await target.screenshot({path});
      else{const tall=Math.max(844,rows.at(-1).frame_bottom);await target.setViewportSize({width:390,height:tall});await target.screenshot({path});await target.setViewportSize({width:390,height:844});}
    }
    return rows;};
  const desktop=await measureSlides(page,1440),phoneRows=await measureSlides(phone.page,390);
  check("deck_slides_fit_a_desktop_window_with_the_controls_in_view",desktop.every(row=>row.frame_bottom<=row.window&&row.sideways<=0&&row.smallest_text>=12),{slides:desktop});
  check("deck_slides_are_readable_on_a_phone",phoneRows.every(row=>row.sideways<=0&&row.smallest_text>=12&&row.smallest_paragraph>=15),{slides:phoneRows});
  check("deck_screenshots_every_slide_at_1440_and_390",deckScreenshotSuffixes.every(suffix=>existsSync(output.replace(/\.json$/,suffix))),{files:deckScreenshotSuffixes.length});
  const firstScreen=async target=>target.evaluate(()=>{const inView=item=>{if(!item)return false;const box=item.getBoundingClientRect();return box.top>=0&&box.bottom<=innerHeight&&box.width>0;};
    return {h1:inView(document.querySelector("h1")),action:inView(document.querySelector("header .primary"))};});
  const readFirstScreen=async viewport=>{const view=await open(viewport);try{return await firstScreen(view.page);}finally{await view.close();}};
  const firstDesktop=await readFirstScreen({}),firstPhone=await readFirstScreen({width:390,height:844});
  check("deck_first_screen_shows_the_heading_and_an_action",firstDesktop.h1&&firstDesktop.action&&firstPhone.h1&&firstPhone.action,{desktop:firstDesktop,phone:firstPhone});

  /* Fast loading: one fresh visit, counted by what the browser actually fetched. */
  const visit=await open();await visit.page.waitForLoadState("networkidle");
  const fetched=[];for(const response of visit.state.responses){const url=new URL(response.url());fetched.push({path:url.pathname,status:response.status(),bytes:(await response.body().catch(()=>Buffer.alloc(0))).length,origin:url.origin});}
  const bytes=fetched.reduce((sum,item)=>sum+item.bytes,0),own=fetched.filter(item=>/^\/(deck|assets\/deck\.(css|js))$/.test(item.path)).reduce((sum,item)=>sum+item.bytes,0);
  check("deck_loads_fast",fetched.length<=12&&bytes<=420000&&own<=90000&&fetched.every(item=>item.status===200&&item.origin===new URL(base).origin),{requests:fetched.length,bytes,deck_files_bytes:own,files:fetched.map(item=>item.path+" "+item.bytes)});
  await visit.close();await phone.close();

  /* Removed-guard controls: changed bytes served in memory, each of which must fail the check it names. */
  const controls=[
    {name:"deck_plant_a_number_without_a_source",path:deckPaths.page,find:'<p class="deck-cover-note">',replacement:'<p>Used by 500 teams.</p><p class="deck-cover-note">',run:checkNumbers,expected:["deck_every_number_has_a_source_note"]},
    {name:"deck_plant_a_number_word_without_a_source",path:deckPaths.page,find:'<p class="deck-cover-note">',replacement:'<p>Ten times cheaper than a model call.</p><p class="deck-cover-note">',run:checkNumbers,expected:["deck_every_number_has_a_source_note"]},
    {name:"deck_drop_the_fact_mark_of_a_number",path:deckPaths.page,find:'<article class="deck-tile" data-fact data-evidence="artifacts/architecture-audit-2026-09-19/pilot-release-24.json#/fly_release ',replacement:'<article class="deck-tile" data-evidence="artifacts/architecture-audit-2026-09-19/pilot-release-24.json#/fly_release ',run:checkNumbers,expected:["deck_every_number_has_a_source_note"]},
    {name:"deck_drop_every_source_note",path:deckPaths.page,find:'class="deck-source"',replacement:'class="deck-caption"',run:checkNumbers,expected:["deck_every_number_has_a_source_note"]},
    {name:"deck_write_a_retired_word",path:deckPaths.page,find:'<p class="deck-cover-note">',replacement:'<p>Join the private beta.</p><p class="deck-cover-note">',run:checkWords,expected:["deck_names_no_retired_or_invitation_wording"]},
    {name:"deck_write_an_invitation_word_on_a_hidden_slide",path:deckPaths.page,find:"<p><strong>Live payments</strong>",replacement:"<p>Request an invitation; accounts open in small groups.</p><p><strong>Live payments</strong>",run:checkWords,expected:["deck_names_no_retired_or_invitation_wording"]},
    {name:"deck_write_a_runtime_word",path:deckPaths.page,find:'<p class="deck-cover-note">',replacement:'<p>Built on the Loop Engine runtime.</p><p class="deck-cover-note">',run:checkWords,expected:["deck_names_no_retired_or_invitation_wording"]},
    {name:"deck_drop_the_arrow_keys",path:deckPaths.script,find:'case "ArrowRight": case "PageDown": go(1); break;',replacement:"",run:checkKeys,expected:["deck_moves_with_the_keyboard"]},
    {name:"deck_drop_the_swipe",path:deckPaths.script,find:"go(dx < 0 ? 1 : -1)",replacement:"void dx",run:checkSwipe,touch:true,expected:["deck_moves_with_a_swipe"]}];
  for(const control of controls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    let session=null;
    try{session=await open({width:control.touch?390:1440,height:control.touch?844:900,touch:Boolean(control.touch),mutation:control});applied=session.state.applied;await control.run(session.page,note);}
    catch(error){problem=safeError(error);}
    finally{if(session)await session.close();}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  for(const context of opened)await context.close().catch(()=>{});
}

