/* Browser checks of the directory page at /directory, run by tools/check_service_workspace.mjs on its loopback service.

   Every check reads the page the service serves, in a real browser, as a visitor who is not signed in. Each rule has a
   known-wrong case beside it: a decision function is also given a known-wrong state and must refuse it, or the page
   script is served with one guard removed, in memory only, and the named checks must fail. Nothing here changes a
   source file.

   The commercial rules are held here because the page is where a reader meets them: ordering, filtering and inclusion
   never read a commercial field (every field is changed and the order and membership stay the same); a commercial link
   shows its disclosure label beside it and carries rel="sponsored noopener"; a sponsored placement sits in its own
   labelled band, never in the list; and the served data ships no active commercial link. */
import {readFileSync} from "node:fs";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname);
const pageScript=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/directory.js"),"utf8");
/* The canonical address of the page, from the site map record, so this check names no host of its own. */
const siteMapRecord=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_site_map.json"),"utf8"));
const canonicalAddress=address=>"https://"+siteMapRecord.canonical_hostname+address;
const MANIFEST="/assets/directory/manifest.json",ROWS=/^\/assets\/directory\/rows-(\d+)\.json$/;
const RELATIONSHIP_FIELDS=["kind","program_name","program_terms_address","disclosure_label","outbound_link","canonical_address","status","reviewed_at"];
const NONE=Object.fromEntries(RELATIONSHIP_FIELDS.map(name=>[name,name==="kind"||name==="status"?"none":""]));
const LABELS={affiliate:"Affiliate link",referral:"Affiliate link",sponsored:"Sponsored"};
/* The same seven relationships as commercial_relationship.invariance_variants("example.org"): none, then each kind pending and active. */
const variants=[NONE,...["affiliate","referral","sponsored"].flatMap(kind=>["pending_owner","active"].map(status=>({kind,program_name:kind+" programme "+status,
  program_terms_address:"https://"+kind+".example.org/terms/"+status,disclosure_label:LABELS[kind],outbound_link:"https://"+kind+".example.org/go/"+status,
  canonical_address:"https://"+kind+".example.org/product",status,reviewed_at:"2026-09-24"})))];

/* Decisions, kept apart from the page so each can be given a known-wrong state. */
export const metadataProblems=state=>[...(state.title==="Baltor | MCP server and agent API directory"?[]:["the title is "+JSON.stringify(state.title)]),
  ...(state.canonical===canonicalAddress("/directory")?[]:["the canonical address is "+JSON.stringify(state.canonical)]),
  ...(state.description.length>=60?[]:["the page has no description for search engines"]),
  ...(state.h1===1?[]:[state.h1+" h1 headings"]),
  ...(state.graph.includes("CollectionPage")&&state.graph.includes("Dataset")?[]:["the structured data is "+JSON.stringify(state.graph)])];
export const sameOrder=(first,second)=>JSON.stringify(first)===JSON.stringify(second);
export const commercialLinkProblems=links=>links.length===0?["no commercial link is shown"]:links.flatMap(link=>[
  ...(link.rel==="sponsored noopener"?[]:["a commercial link has rel "+JSON.stringify(link.rel)]),
  ...(link.label==="Affiliate link"||link.label==="Sponsored"?[]:["a commercial link has no disclosure label beside it"])]);
export const sponsoredProblems=state=>[...(state.band&&state.heading==="Sponsored"?[]:["no labelled sponsored band"]),
  ...(state.inBand>0?[]:["the placement is not in the band"]),...(state.inList===0?[]:["a sponsored link sits inside the ranked list"])];

async function loadDirectory(browser,base,{routes=[],viewport={width:1440,height:900},path="/directory",errors,localOnly}){
  const context=await browser.newContext({viewport,reducedMotion:"reduce"});
  await context.route("**/*",localOnly);
  for(const [test,handler] of routes)await context.route(test,handler);
  const page=await context.newPage();
  page.on("pageerror",error=>errors.push(String(error.message||error)));
  const requests=[];page.on("request",request=>requests.push(new URL(request.url()).pathname));
  const started=Date.now();
  await page.goto(base+path,{waitUntil:"load"});
  await page.waitForFunction(()=>["ready","failed"].includes(document.documentElement.dataset.directory),null,{timeout:60000});
  return {context,page,requests,ready_ms:Date.now()-started};
}

/* Routes that answer the manifest and the row files with every row's commercial relationship changed. */
async function changedData(page,base,assign){
  const manifest=await (await page.request.get(base+MANIFEST)).json();
  const parts={};
  for(const part of manifest.parts)parts[part.address]=await (await page.request.get(base+part.address)).json();
  const position=manifest.columns.indexOf("commercial");
  const changedManifest={...manifest,commercial_relationships:variants};
  const routes=[[url=>new URL(url).pathname===MANIFEST,route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(changedManifest)})]];
  for(const [address,part] of Object.entries(parts)){
    const rows=part.rows.map(row=>{const changed=[...row];changed[position]=assign(row[0]);return changed;});
    routes.push([url=>new URL(url).pathname===address,route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({...part,rows})})]);
  }
  return {manifest,routes};
}

const scriptRoute=mutation=>{const state={applied:false};
  const route=[url=>new URL(url).pathname==="/assets/directory.js",route=>{const body=pageScript.split(mutation.find).join(mutation.replacement);
    state.applied=body!==pageScript;route.fulfill({status:200,contentType:"text/javascript",body});}];
  return {state,route};};

/* The order and the membership a reader sees for the default view and a few filters. */
async function views(page){
  const read=()=>page.evaluate(()=>window.BaltorDirectory.shown());
  const result={all:await read()};
  await page.fill("#directory-query","server");await page.waitForTimeout(400);result.search=await read();
  await page.fill("#directory-query","");await page.waitForTimeout(400);
  await page.locator(".directory-chip[data-category]:not([data-category=''])").first().click();result.chip=await read();
  await page.locator(".directory-chip[data-category='']").click();
  await page.selectOption("#filter-auth","key");result.auth=await read();
  await page.selectOption("#filter-auth","");await page.selectOption("#filter-order","name");result.name=await read();
  return result;
}

export async function runDirectoryChecks({browser,base,check,mutants,errors,localOnly,screenshot}){
  const {page,context,requests,ready_ms}=await loadDirectory(browser,base,{errors,localOnly});
  const manifest=await (await page.request.get(base+MANIFEST)).json();
  const state=await page.evaluate(()=>{let graph=[];try{graph=JSON.parse(document.querySelector('script[type="application/ld+json"]').textContent)["@graph"].map(item=>item["@type"]);}catch(_){graph=[];}
    return {title:document.title,canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||"",description:document.querySelector('meta[name="description"]')?.getAttribute("content")||"",
      h1:document.querySelectorAll("h1").length,graph,loaded:document.documentElement.dataset.directory,count:document.querySelector("#directory-count").textContent,
      rows:document.querySelectorAll("#directory-list [data-row]").length,total:window.BaltorDirectory?.total()||0,
      paidLink:Boolean(document.querySelector('a[href="#paid-links"]')?.checkVisibility()),paidSection:Boolean(document.getElementById("paid-links")),
      commercialLinks:document.querySelectorAll("[data-commercial-link]").length,sponsoredHidden:document.getElementById("directory-sponsored").hidden};});
  check("directory_page_is_served_with_its_title_canonical_address_and_structured_data",metadataProblems(state).length===0,{problems:metadataProblems(state)});
  check("directory_metadata_check_rejects_a_page_without_structured_data_or_canonical",metadataProblems({...state,graph:[]}).length===1&&metadataProblems({...state,canonical:canonicalAddress("/mcp-directory")}).length===1);
  check("directory_loads_every_row_the_manifest_names",state.loaded==="ready"&&state.total===manifest.row_count&&state.count==="Showing all "+manifest.row_count.toLocaleString("en-US")+" listings.",
    {total:state.total,manifest:manifest.row_count,count:state.count,ready_ms});
  check("directory_draws_only_the_rows_in_view",state.rows>0&&state.rows<120&&manifest.row_count>1000,{drawn:state.rows,rows:manifest.row_count});
  check("directory_is_read_without_signing_in",requests.every(path=>path==="/directory"||path.startsWith("/assets/")||path==="/api/v1/capabilities"),{requests:[...new Set(requests)]});
  check("directory_links_its_paid_links_section",state.paidLink&&state.paidSection);
  check("directory_ships_no_commercial_link_today",state.commercialLinks===0&&state.sponsoredHidden&&manifest.commercial_relationships.length===1
    &&JSON.stringify(manifest.commercial_relationships[0])===JSON.stringify(NONE),{relationships:manifest.commercial_relationships.length});
  /* The served first rows and the rows the script draws are the same rows in the same order. */
  const served=await (await page.request.get(base+"/directory")).text();
  const servedIds=[...served.matchAll(/<div class="directory-row" role="listitem" id="([^"]+)" data-row>/g)].map(found=>found[1].replace(/&amp;/g,"&"));
  const drawnIds=(await page.evaluate(()=>window.BaltorDirectory.shown())).slice(0,servedIds.length);
  check("directory_served_rows_are_the_first_rows_the_script_draws",servedIds.length>0&&sameOrder(servedIds,drawnIds),{served:servedIds.slice(0,5),drawn:drawnIds.slice(0,5)});
  check("row_order_check_rejects_two_rows_swapped",servedIds.length>1&&!sameOrder(servedIds,[servedIds[1],servedIds[0],...servedIds.slice(2)]));
  /* Search, chips and a direct link to one row. */
  await page.fill("#directory-query","postgres");await page.waitForTimeout(400);
  const searched=await page.evaluate(()=>({shown:window.BaltorDirectory.shown().length,count:document.querySelector("#directory-count").textContent,address:location.search}));
  await page.fill("#directory-query","");await page.waitForTimeout(400);
  const chip=page.locator(".directory-chip[data-category]:not([data-category=''])").first();
  const chipCategory=await chip.getAttribute("data-category");await chip.click();
  const chipped=await page.evaluate(()=>({shown:window.BaltorDirectory.shown().length,pressed:document.querySelector(".directory-chip[aria-pressed='true']")?.dataset.category}));
  const expected=manifest.categories.find(entry=>entry.id===chipCategory)?.rows;
  check("directory_search_narrows_the_list_and_names_it_in_the_address",searched.shown>0&&searched.shown<manifest.row_count&&searched.address.includes("q=postgres"),searched);
  check("directory_category_chip_shows_exactly_its_category",chipped.shown===expected&&chipped.pressed===chipCategory,{...chipped,expected});
  await page.locator(".directory-chip[data-category='']").click();
  const firstLink=page.locator("#directory-list .row-link").first();
  const identity=(await firstLink.getAttribute("href")).slice(1);
  await firstLink.click();
  const opened=await page.evaluate(()=>({open:document.getElementById("directory-detail").open,title:document.getElementById("detail-title").textContent,hash:decodeURIComponent(location.hash.slice(1))}));
  await page.locator("#detail-close").click();
  const direct=await loadDirectory(browser,base,{errors,localOnly,path:"/directory#"+encodeURIComponent(identity)});
  const target=await direct.page.evaluate(id=>{const row=document.getElementById(id);return {shown:Boolean(row?.checkVisibility()),target:row?.classList.contains("is-target")};},identity);
  await direct.context.close();
  check("directory_row_link_opens_the_listing_and_names_it_in_the_address",opened.open&&opened.hash===identity&&opened.title.length>0,opened);
  check("directory_address_with_a_row_shows_that_row",target.shown&&target.target,target);
  /* The second address serves the same page. */
  const second=await page.request.get(base+"/mcp-directory");
  check("directory_second_address_serves_the_same_page",second.status()===200&&(await second.text())===served);
  /* 1440 and 390 pixels: no sideways scrolling, and the full page for the report. */
  const wide=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,height:document.documentElement.scrollHeight}));
  await page.screenshot({path:screenshot("-directory-desktop.png"),fullPage:true});
  await context.close();
  const phone=await loadDirectory(browser,base,{errors,localOnly,viewport:{width:390,height:844}});
  const narrow=await phone.page.evaluate(()=>({overflow:document.documentElement.scrollWidth-innerWidth,height:document.documentElement.scrollHeight,
    rowHeight:getComputedStyle(document.getElementById("directory-list")).getPropertyValue("--row-height").trim(),
    clipped:[...document.querySelectorAll("#directory-list [data-row]")].slice(0,4).some(row=>[...row.querySelectorAll("a, p")].some(node=>node.getBoundingClientRect().bottom>row.getBoundingClientRect().bottom+1))}));
  await phone.page.screenshot({path:screenshot("-directory-mobile.png"),fullPage:true});
  await phone.context.close();
  check("directory_reads_at_1440_and_390_without_sideways_scrolling",wide.overflow<=1&&narrow.overflow<=1&&!narrow.clipped,{wide,narrow});
  /* Listing text is marked only inside listing rows, the listing detail and the sponsored band. */
  const marks=await (async()=>{const view=await loadDirectory(browser,base,{errors,localOnly});
    const found=await view.page.evaluate(()=>[...document.querySelectorAll("[data-listing-text]")].filter(node=>!node.closest("[data-row], #directory-detail, #directory-sponsored-list")).map(node=>node.tagName));
    await view.context.close();return found;})();
  check("directory_marks_listing_text_only_inside_listings",marks.length===0,{outside:marks});
  /* Commercial fields never change the order or the membership. */
  const baseline=await (async()=>{const view=await loadDirectory(browser,base,{errors,localOnly});const found=await views(view.page);await view.context.close();return found;})();
  const invariance=async(mutation,note)=>{
    const probe=await loadDirectory(browser,base,{errors,localOnly});
    const {routes}=await changedData(probe.page,base,identityValue=>{let sum=0;for(const character of identityValue)sum=(sum*31+character.charCodeAt(0))%9973;return sum%variants.length;});
    await probe.context.close();
    const script=mutation?scriptRoute(mutation):null;
    const view=await loadDirectory(browser,base,{errors,localOnly,routes:script?[...routes,script.route]:routes});
    const seen=await views(view.page);await view.context.close();
    const same=Object.keys(baseline).every(name=>sameOrder(baseline[name],seen[name]));
    note("directory_order_and_membership_ignore_every_commercial_field",same,{views:Object.fromEntries(Object.keys(baseline).map(name=>[name,sameOrder(baseline[name],seen[name])]))});
    return script?.state;
  };
  await invariance(null,check);
  /* A commercial link, when a row carries an active affiliate relationship, and a sponsored placement, in its own band. */
  const withRelationships=async(mutation,note)=>{
    const probe=await loadDirectory(browser,base,{errors,localOnly});
    const ids=await probe.page.evaluate(()=>window.BaltorDirectory.shown().slice(0,2));
    const {routes}=await changedData(probe.page,base,identityValue=>identityValue===ids[0]?2:identityValue===ids[1]?6:0);
    await probe.context.close();
    const script=mutation?scriptRoute(mutation):null;
    const view=await loadDirectory(browser,base,{errors,localOnly,routes:script?[...routes,script.route]:routes});
    const found=await view.page.evaluate(([first,second])=>{
      const inRow=[...document.getElementById(first)?.querySelectorAll("[data-commercial-link]")||[]].map(link=>({rel:link.getAttribute("rel")||"",
        label:link.nextElementSibling?.matches("[data-disclosure-label]")&&link.nextElementSibling.checkVisibility()?link.nextElementSibling.textContent:""}));
      const band=document.getElementById("directory-sponsored");
      return {links:inRow,sponsored:{band:!band.hidden&&band.checkVisibility(),heading:band.querySelector("h2")?.textContent||"",
        inBand:band.querySelectorAll("[data-commercial-link][rel='sponsored noopener']").length,
        inList:document.getElementById(second)?.querySelectorAll("[data-commercial-link]").length??0}};},ids);
    await view.context.close();
    note("directory_commercial_link_shows_its_label_and_sponsored_rel",commercialLinkProblems(found.links).length===0,{links:found.links});
    note("directory_sponsored_placement_sits_in_its_own_band",sponsoredProblems(found.sponsored).length===0,found.sponsored);
    return script?.state;
  };
  await withRelationships(null,check);
  check("commercial_link_check_rejects_a_missing_label_and_a_plain_rel",commercialLinkProblems([{rel:"sponsored noopener",label:""}]).length===1
    &&commercialLinkProblems([{rel:"noopener",label:"Affiliate link"}]).length===1&&commercialLinkProblems([]).length===1);
  check("sponsored_check_rejects_a_placement_inside_the_list",sponsoredProblems({band:true,heading:"Sponsored",inBand:1,inList:1}).length===1
    &&sponsoredProblems({band:false,heading:"",inBand:0,inList:0}).length===2);
  /* Removed-guard controls: the page script with one rule removed, served in memory for one scenario. */
  const controls=[
    {name:"directory_ranking_reads_the_commercial_field",scenario:invariance,find:"return b.sourceCount - a.sourceCount",replacement:"return (b.commercial - a.commercial) || b.sourceCount - a.sourceCount",
     expected:["directory_order_and_membership_ignore_every_commercial_field"]},
    {name:"directory_inclusion_reads_the_commercial_field",scenario:invariance,find:"    return tokens.every(token => row.haystack.includes(token));",
     replacement:"    if (row.commercial) return false;\n    return tokens.every(token => row.haystack.includes(token));",expected:["directory_order_and_membership_ignore_every_commercial_field"]},
    {name:"directory_commercial_link_without_its_label",scenario:withRelationships,find:'"Go to the product"), " ",\n        element("span", {class: "paid-label", "data-disclosure-label": true}, relation.disclosure_label));\n      facts.append(paid);',
     replacement:'"Go to the product"));\n      facts.append(paid);',expected:["directory_commercial_link_shows_its_label_and_sponsored_rel"]},
    {name:"directory_sponsored_link_inside_the_list",scenario:withRelationships,find:"if (relation && showsCommercialLink(relation)) {\n      const paid = element(\"p\"",
     replacement:"if (relation && (showsCommercialLink(relation) || isSponsoredPlacement(relation))) {\n      const paid = element(\"p\"",expected:["directory_sponsored_placement_sits_in_its_own_band"]}];
  for(const control of controls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{applied=(await control.scenario({find:control.find,replacement:control.replacement},note))?.applied===true;}catch(error){problem=String(error.message||error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  return {ready_ms,rows:manifest.row_count,desktop_height:wide.height,phone_height:narrow.height};
}
