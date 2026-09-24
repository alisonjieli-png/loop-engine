/* Read-only browser acceptance of the deployed public site. No credentials. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,existsSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

const origin=process.argv[2],output=resolve(process.argv[3]||"");
if(!origin||new URL(origin).origin!==origin||!origin.startsWith("https://")||!process.argv[3]||existsSync(output))throw new Error("Use an exact HTTPS origin and a new report path.");
const root=resolve(new URL("..",import.meta.url).pathname);
const checks=[],errors=[],external=[],navigation=[];
const check=(name,passed)=>checks.push({name,passed:passed===true});
/* One plain-word rule for the public pages. tools/check_service_workspace.mjs carries the same line, and a named check there compares the two. */
const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
/* The words of an invitation-only service, which the owner retired on September 23, 2026. tools/check_service_workspace.mjs
   carries the same line, and a named check there compares the two. */
const liveInvitation=/\binvit(?:e|es|ed|ing|ations?)\b|small groups|waiting list|\bsearch(?:ing)? is free\b|being built|being prepared|\bplanned\b/i;
/* The owner's decisions of September 23, 2026, written once as rules that the journey below and its known-wrong cases share.
   tools/check_service_workspace.mjs holds the same decisions against a local service. */
const heroHarnesses=["Claude Code","Codex","OpenCode","Pi","Baltor Harness"];
const heroProblems=copy=>[...(/\bharness\b/i.test(copy.headline+" "+copy.subhead)&&/\bskills\b/i.test(copy.subhead)&&/\btools\b/i.test(copy.subhead)&&/where (?:your|the|each) harness reads/i.test(copy.subhead)?[]:["the hero does not say what Baltor is and where the files go"]),
  ...(/\bby hand\b/i.test(copy.subhead)?[]:["the hero does not name the work it removes"]),...(/fresh harness|harness (?:for|per) (?:each|every) step|one harness per step/i.test(copy.text)?["the hero promises a fresh harness for each step"]:[])];
const heroCheckRejectsItsKnownWrongCases=copy=>{const earlier={headline:"Supercharge your developers and AI agents.",subhead:"Big tasks go better in small steps. Baltor is designed to give each step a fresh harness that holds only what that step needs."};
  return heroProblems({...earlier,text:earlier.headline+" "+earlier.subhead}).length===3&&heroProblems({headline:"The perfect harness setup for every task.",subhead:"Baltor finds skills, instructions and tools and puts each file where your harness reads it.",text:""}).length===1
    &&heroProblems({...copy,text:copy.text+" Each step runs in a fresh harness."}).some(problem=>problem.includes("fresh harness"));};
const categoryProblems=state=>[...(/^Harness and agent optimized operation\.$/m.test(state.footer)?[]:["the footer does not carry the category line in full"]),...(JSON.stringify(state.harnesses)===JSON.stringify(heroHarnesses)?[]:["the hero names "+JSON.stringify(state.harnesses)])];
const statesThePlanAndPrice=text=>/^Baltor Pro \$29 a month\b/.test(text)&&!/United States dollars|per month/i.test(text);
const cardStatusWords=/available now|being built|\bplanned\b|coming soon|packages coming/i;
const cardProblems=(cards,order)=>[...(JSON.stringify(cards.map(card=>card.name))!==JSON.stringify(order)?["the cards are "+JSON.stringify(cards.map(card=>card.name))]:[]),
  ...cards.filter(card=>!card.shown||!card.title).map(card=>card.name+" is not shown under its own heading"),...cards.filter(card=>card.tags>0||cardStatusWords.test(card.text)).map(card=>card.name+" carries a status")];
const useCaseTitles={overnight:"Solve complex problems overnight",efficiency:"More efficient operation",learning:"Learning and optimization, built in"};
const useCaseProblems=cards=>[...cardProblems(cards,["overnight","efficiency","learning"]),...cards.filter(card=>useCaseTitles[card.name]!==card.title||JSON.stringify(card.links)!==JSON.stringify(["/"+card.name])).map(card=>card.name+" is titled or linked another way")];
const heroActionProblems=state=>[...(JSON.stringify(state.primary)===JSON.stringify([["hero-primary","Get started","/get-started"]])?[]:["the hero's primary actions are "+JSON.stringify(state.primary)]),
  ...(JSON.stringify(state.secondary)===JSON.stringify([["hero-setup","Get set up","/setup"]])?[]:["the hero's secondary actions are "+JSON.stringify(state.secondary)]),...(state.journey===1?[]:[state.journey+" hero links lead into the access journey"]),
  ...(/\bGet started\b[^.]*\baccount\b/i.test(state.paths)&&/\bGet set up\b[^.]*\bconnect/i.test(state.paths)?[]:["the line under the actions reads "+JSON.stringify(state.paths)])];
const pricingFacts=["One plan","Baltor Pro","$29 a month","one downloaded item","Cancel from your account page."];
const pricingProblems=text=>[...pricingFacts.filter(fact=>!text.includes(fact)).map(fact=>"missing "+fact),...(/\bsearch(?:ing)? is free\b/i.test(text)?["free search"]:[]),...(/\binvited\b/i.test(text)?["free invited accounts"]:[]),
  ...(/United States dollars|per month/i.test(text)?["another way of writing the price"]:[])];
const paymentWords={accountFirst:{badge:"Available now",note:"Create your account, then subscribe from your account page. Cancel any time."},
  open:{badge:"Available now",note:"Subscribe from your account page, and cancel any time."},closed:{badge:"Baltor Pro",note:"Subscribe from your account page once your account is ready."}};
const expectedPayment=facts=>facts.website.registration_available!==true?paymentWords.accountFirst:facts.billing.checkout===true?paymentWords.open:paymentWords.closed;
const setsUpEveryNamedHarness=(names,tabs)=>names.length>0&&names.every(name=>tabs.some(tab=>tab===name||tab.startsWith(name+" ")));
const hash=value=>createHash("sha256").update(value).digest("hex");
const assetDigests=new Map();
const assetDigest=path=>{if(!assetDigests.has(path)){const name=path==="/assets/third-party-notices.txt"?"THIRD-PARTY-NOTICES.md":path.slice("/assets/".length);assetDigests.set(path,hash(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets",name))));}return assetDigests.get(path);};
const sameOriginAsset=(value,path)=>{try{const url=new URL(value,origin);return url.origin===origin&&url.pathname===path&&!url.username&&!url.password&&!url.hash&&url.search==="?v="+assetDigest(path);}catch(_){return false;}};
/* The page this hostname shows at its root address, read through the typed reader of web_site_map.json, the one list of pages and
   hostnames. docs, status, examples and demo open their own page at the root since September 24, 2026; the homepage checks run
   where the root is the homepage, and every other check runs on every hostname. PYTHON names a qualified environment when the
   release worktree has no .venv of its own. */
const python=process.env.PYTHON||(existsSync(resolve(root,".venv/bin/python"))?resolve(root,".venv/bin/python"):"python3");
const siteMapRead=spawnSync(python,["-c","import json\nfrom loop_engine.core.service_runtime.web_site_map import as_plain_record, load_site_map\nprint(json.dumps(as_plain_record(load_site_map())))"],
  {cwd:root,env:{...process.env,PYTHONPATH:resolve(root,"src")},encoding:"utf8"});
if(siteMapRead.status!==0)throw new Error("The typed reader refused the site map:\n"+siteMapRead.stderr);
const siteMap=JSON.parse(siteMapRead.stdout),canonicalOrigin="https://"+siteMap.canonical_hostname;
const rootAddress=siteMap.hostnames.find(item=>item.hostname===new URL(origin).hostname)?.address||"/";
const rootPage=siteMap.pages.find(item=>item.address===rootAddress),rootIsHome=rootAddress==="/";
const pageTitle=entry=>siteMap.display_name+" | "+entry.title;
const opensItsPage=(shown,entry)=>Boolean(entry)&&JSON.stringify(shown.views)===JSON.stringify([entry.view])&&shown.title===pageTitle(entry)&&shown.canonical===canonicalOrigin+entry.address;
const shownPage=target=>target.evaluate(()=>({views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),title:document.title,
  canonical:document.querySelector('link[rel="canonical"]')?.getAttribute("href")||"",brand:document.querySelector("header a.brand")?.getAttribute("href")||""}));
/* The pages of September 24, 2026, checked on every hostname at their own addresses. */
const showcasePaths=["/demo","/demo/kaggle","/status","/examples","/case-studies/data-cleanup","/case-studies/pi-and-gemma-4","/case-studies/sign-up-protection","/for/coding-agents","/for/engineering-teams","/for/comparing-tools","/for/protocol-and-client"];
const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
await context.route("**/*",route=>{if(new URL(route.request().url()).origin===origin)route.continue();else{external.push(new URL(route.request().url()).origin);route.abort();}});
const page=await context.newPage();page.on("pageerror",error=>errors.push(error.message));
try{
  const home=await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector(".boundary-zone")&&document.querySelector("#service-status").textContent.includes("Service available"));
  check("HTTPS_homepage_is_available",home.status()===200);
  /* The root of this hostname opens the page the site map names for it, with that page's own title and canonical address, and serves
     exactly what that page's own address serves here. Where that page is not the homepage, the brand leads to the homepage on the
     canonical hostname. The known-wrong roots: another view, the homepage's title, and another canonical address. */
  const rootShown=await shownPage(page);
  const rootBytes=await (await page.request.get(origin+"/",{maxRedirects:0})).text(),ownBytes=await (await page.request.get(origin+rootAddress,{maxRedirects:0})).text();
  check("live_hostname_root_opens_the_page_the_site_map_names",opensItsPage(rootShown,rootPage)&&rootBytes===ownBytes&&(rootIsHome||rootShown.brand===canonicalOrigin+"/"));
  check("hostname_root_check_rejects_another_view_title_or_canonical_address",!opensItsPage({...rootShown,views:[...rootShown.views,"home"]},rootPage)
    &&!opensItsPage({...rootShown,title:siteMap.display_name+" | The perfect harness setup for every task x"},rootPage)&&!opensItsPage({...rootShown,canonical:canonicalOrigin+"/other"},rootPage));
  const namedAssets=await page.evaluate(()=>[...document.querySelectorAll("[src],link[href],footer a[href]")].flatMap(node=>[node.getAttribute("src"),node.getAttribute("href")]).filter(Boolean).filter(value=>{try{return new URL(value,location.href).pathname.startsWith("/assets/");}catch(_){return false;}}));
  check("live_asset_versions_bind_to_exact_packaged_bytes",namedAssets.length>0&&namedAssets.every(value=>sameOriginAsset(value,new URL(value,origin).pathname)));
  const versionedMark="/assets/baltor-mark.svg?v="+assetDigest("/assets/baltor-mark.svg");
  check("live_asset_identity_check_refuses_foreign_origins_stale_versions_and_extra_parameters",sameOriginAsset(versionedMark,"/assets/baltor-mark.svg")
    &&["/assets/baltor-mark.svg",versionedMark.replace(/v=./,"v=x"),versionedMark+"&extra=1",versionedMark+"#other","https://foreign.example.invalid"+versionedMark].every(value=>!sameOriginAsset(value,"/assets/baltor-mark.svg")));
  /* Every access action says "Get started" and opens the funnel at /get-started in every state the deployed service reports; the
     funnel adapts. The owner, September 23, 2026: "remove all mentions of invitation only, this should be consistent as if it is
     fully working". The funnel takes an address where the service reports registration open or keeps a request list. */
  const liveReport=(await (await page.request.get(origin+"/api/v1/capabilities",{maxRedirects:0})).json())?.result||{};
  const liveOpen=liveReport.record_type==="service_capabilities/v1"&&liveReport.website?.registration_available===true;
  const liveLabel="Get started",livePath="/get-started";
  const liveTakesAddresses=liveReport.record_type==="service_capabilities/v1"&&(liveReport.website?.registration_available===true||liveReport.website?.waitlist_available===true);
  check("live_page_has_four_intelligence_layers",await page.locator('[data-view="about"] [data-intelligence-layer]').count()===4);
  if(rootIsHome){
  /* The hero, as the owner decided on September 23, 2026: it says what Baltor is, the library of everything a harness can use,
     placed where the harness reads it, and the work it removes, done by hand; it no longer promises a fresh harness for each step. */
  const liveHero=await page.locator('[data-view="home"] .hero-copy').evaluate(node=>({headline:node.querySelector("h1")?.textContent.replace(/\s+/g," ").trim()||"",
    subhead:node.querySelector(".hero-subhead")?.textContent.replace(/\s+/g," ").trim()||"",text:node.textContent.replace(/\s+/g," ").trim()}));
  check("live_homepage_hero_says_what_baltor_is_and_the_pain_it_removes",heroProblems(liveHero).length===0&&await page.locator('[data-view="home"] .boundary-figure').count()===0);
  check("hero_check_rejects_the_earlier_lines_a_hero_without_the_pain_and_a_fresh_harness_promise",heroCheckRejectsItsKnownWrongCases(liveHero));
  check("live_default_appearance_is_light",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  check("live_how_it_works_covers_five_optimization_problems",await page.locator('[data-view="about"] [data-friction]').count()===5);
  const heroOpening=await page.locator('[data-view="home"] .hero-copy').evaluate(node=>({first:node.firstElementChild?.tagName,badges:node.querySelectorAll(".hero-chip").length}));
  const startsAtHeadline=value=>value.first==="H1"&&value.badges===0;
  check("live_homepage_opens_with_headline_without_category_badge",startsAtHeadline(heroOpening),heroOpening);
  check("category_badge_check_rejects_the_removed_pill",!startsAtHeadline({first:"P",badges:1})&&!startsAtHeadline({first:"H1",badges:1})&&startsAtHeadline({first:"H1",badges:0}));
  /* The owner's category line stays in full in the footer, and the hero names the five harnesses the owner named, in order. */
  const liveCategory=await page.evaluate(()=>({footer:[...document.querySelectorAll("footer .footer-brand p")].map(node=>node.textContent.replace(/\s+/g," ").trim()).join("\n"),
    harnesses:[...document.querySelectorAll('[data-view="home"] .hero-harnesses li')].filter(node=>node.getClientRects().length>0).map(node=>node.textContent.replace(/\s+/g," ").trim())}));
  check("live_owner_category_line_stays_in_full_and_the_hero_names_the_harnesses",categoryProblems(liveCategory).length===0);
  check("category_line_check_rejects_a_shortened_line_a_missing_harness_and_a_status",categoryProblems({...liveCategory,footer:"Optimized operation."}).length===1
    &&categoryProblems({...liveCategory,harnesses:heroHarnesses.filter(name=>name!=="Pi")}).length===1&&categoryProblems({...liveCategory,harnesses:heroHarnesses.map(name=>name==="Pi"?"Pi Planned":name)}).length===1);
  /* The price in the hero, "Baltor Pro $29 a month", the one way the design standards allow. */
  const liveHeroPrice=await page.evaluate(()=>document.querySelector('[data-view="home"] .hero-price')?.textContent.replace(/\s+/g," ").trim()||"");
  check("live_homepage_hero_states_the_plan_and_the_price",statesThePlanAndPrice(liveHeroPrice));
  check("hero_price_check_rejects_a_missing_price_and_another_way_of_writing_it",!statesThePlanAndPrice("")&&!statesThePlanAndPrice("Baltor Pro 29 United States dollars each month")&&!statesThePlanAndPrice("Baltor Pro $29 per month")&&statesThePlanAndPrice("Baltor Pro $29 a month for the whole library"));
  /* The bands of the design, in order, each set off from the next by a change of ground and a rule. */
  const liveBands=await page.locator('[data-view="home"]').evaluate(home=>{const bands=[...home.children],ground=node=>getComputedStyle(node).backgroundColor;
    return {names:bands.map(node=>node.dataset.band||""),apart:bands.slice(1).every((node,index)=>ground(node)!==ground(bands[index])&&parseFloat(getComputedStyle(node).borderTopWidth)>0)};});
  /* The design's order since September 24, 2026: the hero with the working directory one step gets, the three demonstrations, the
     library, the three use cases, trust, pricing, questions and the closing band. The Ask, get, place band left that day. */
  check("live_homepage_bands_follow_the_design_and_are_set_apart",JSON.stringify(liveBands.names)===JSON.stringify(["hero","demos","library","use-cases","trust","pricing","faq","closing"])&&liveBands.apart
    &&await page.locator('[data-band="hero"] #hero-directory').count()===1);
  check("live_homepage_says_what_an_account_gives_you",JSON.stringify(await page.locator("[data-offer]").evaluateAll(items=>items.map(item=>item.dataset.offer).sort()))===JSON.stringify(["downloads","keys","library","usage"]));
  /* No card on the homepage carries a status word since September 23, 2026: the six kinds, the three use cases and, since
     September 24, the three demonstrations, each in the design's order. The hero's directory carries the one tag, "Example
     layout". Each use case and each demonstration links its own page. */
  const liveCards=(selector,key)=>page.locator(selector).evaluateAll((items,key)=>items.map(item=>({name:item.dataset[key]||"",title:item.querySelector("h3")?.textContent.replace(/\s+/g," ").trim()||"",
    text:item.textContent.replace(/\s+/g," ").trim(),tags:item.querySelectorAll(".status-tag, [data-status]").length,links:[...item.querySelectorAll("a[href]")].map(link=>link.getAttribute("href")),shown:item.getClientRects().length>0})),key);
  const demoCardPages={simple:"/demo",overnight:"/overnight",kaggle:"/demo/kaggle"};
  const demoCardProblems=cards=>[...cardProblems(cards,Object.keys(demoCardPages)),...cards.filter(card=>JSON.stringify(card.links)!==JSON.stringify([demoCardPages[card.name]])).map(card=>card.name+" links another page")];
  const liveCardProblems=[...cardProblems(await liveCards("[data-kind]","kind"),["skills","instructions","tools","agents","hooks","servers"]),...demoCardProblems(await liveCards('[data-view="home"] [data-demo-card]',"demoCard")),
    ...useCaseProblems(await liveCards('[data-view="home"] [data-use-case]',"useCase"))];
  check("live_homepage_cards_carry_no_status_word_and_link_the_three_use_cases",liveCardProblems.length===0);
  check("card_check_rejects_a_status_word_and_a_missing_use_case",cardProblems([{name:"skills",title:"Skills",text:"Skills Available now",tags:1,links:[],shown:true}],["skills"]).length===1
    &&useCaseProblems([{name:"overnight",title:"Solve complex problems overnight",text:"",tags:0,links:["/overnight"],shown:true}]).length===1);
  /* The hero shows the working directory one step gets and no worked example, as the owner asked on September 24, 2026: no
     search, no reference, no digest and no download in the hero band. */
  const liveHeroDirectory=await page.evaluate(()=>{const band=document.querySelector('[data-view="home"] [data-band="hero"]');
    return {label:band?.querySelector("[data-hero-directory] [data-hero-label]")?.textContent.replace(/\s+/g," ").trim()||"",parts:[...(band?.querySelectorAll("[data-hero-part]")||[])].map(node=>node.dataset.heroPart),
      example:band?band.querySelectorAll("[data-step-demo], [data-demo-item], [data-demo-query], [data-demo-download], [data-task-demo]").length:0,text:band?.textContent.replace(/\s+/g," ")||""};});
  const showsNoWorkedExample=state=>state.label==="Example layout"&&JSON.stringify(state.parts)===JSON.stringify(["instructions","skills","tools","code"])&&state.example===0
    &&!/\bsearch:|\bsha256\b|Bytes match the digest/i.test(state.text);
  check("live_hero_shows_a_working_directory_and_no_worked_example",showsNoWorkedExample(liveHeroDirectory));
  check("hero_directory_check_rejects_a_worked_example_again",!showsNoWorkedExample({...liveHeroDirectory,example:1})&&!showsNoWorkedExample({...liveHeroDirectory,text:liveHeroDirectory.text+" search: split address lines sha256 53dc74e3"}));
  /* Two actions in the hero: Get started, the one primary action, and Get set up, the guide, with one line that says how they differ. */
  const liveHeroActions=await page.locator('[data-view="home"] .hero').evaluate(hero=>{const words=node=>node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),shown=node=>node.getClientRects().length>0;
    return {primary:[...hero.querySelectorAll(".button.primary")].filter(shown).map(node=>[node.id,words(node),node.getAttribute("href")]),secondary:[...hero.querySelectorAll(".button.secondary")].filter(shown).map(node=>[node.id,words(node),node.getAttribute("href")]),
      journey:[...hero.querySelectorAll("a[href]")].filter(node=>/^\/(?:get-started|waitlist|signup|connect)(?:$|[/?#])/.test(node.getAttribute("href"))).length,paths:hero.querySelector(".hero-paths")?.textContent.replace(/\s+/g," ").trim()||""};});
  check("live_homepage_offers_get_started_and_get_set_up_and_says_how_they_differ",heroActionProblems(liveHeroActions).length===0&&["waiting","open"].includes(await page.locator("#hero-primary").getAttribute("data-access-state")));
  check("hero_action_check_rejects_a_second_primary_and_a_missing_guide",heroActionProblems({...liveHeroActions,primary:[...liveHeroActions.primary,["planted","Request an invitation","/waitlist"]]}).length>=1&&heroActionProblems({...liveHeroActions,secondary:[]}).length===1);
  /* One primary action on the whole homepage and in the header, with the one label of the reported state. */
  const livePrimaries=await page.locator('header .button.primary, [data-view="home"] .button.primary, footer .button.primary').evaluateAll(items=>items.map(item=>[item.textContent.replace(/[↗→]/g,"").trim(),item.getAttribute("href"),Boolean(item.closest("header"))]));
  check("live_every_primary_action_carries_the_one_label",livePrimaries.length>=4&&livePrimaries.filter(([,,header])=>header).length===1&&livePrimaries.every(([label,href])=>label===liveLabel&&href===livePath));
  /* On a phone the header is one compact bar and the primary action stands in the first screen. Wherever the deployed service
     takes an address, one press on it shows the funnel's email field, #funnel-email, inside the first screen. */
  const phone=await context.newPage();phone.on("pageerror",error=>errors.push(error.message));
  await phone.setViewportSize({width:390,height:844});await phone.goto(origin+"/");
  await phone.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  const liveFirst=await phone.evaluate(()=>{const box=document.getElementById("hero-primary").getBoundingClientRect();return {top:box.top,bottom:box.bottom,viewport:innerHeight,header:document.querySelector("header").getBoundingClientRect().height};});
  check("live_phone_first_screen_holds_the_primary_action_under_a_compact_header",liveFirst.top>=0&&liveFirst.bottom<=liveFirst.viewport&&liveFirst.header<=80);
  if(liveTakesAddresses){
    await phone.locator("#hero-primary").click();
    await phone.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:10000}).catch(()=>{});
    const liveField=await phone.evaluate(()=>{const node=document.getElementById("funnel-email"),box=node?.getBoundingClientRect();return {path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),
      shown:Boolean(node&&node.getClientRects().length),top:box?.top??-1,bottom:box?.bottom??-1,viewport:innerHeight};});
    check("live_primary_action_lands_on_the_funnel_email_field",liveField.path==="/get-started"&&JSON.stringify(liveField.views)===JSON.stringify(["start"])&&liveField.shown&&liveField.top>=0&&liveField.bottom<=liveField.viewport);
  }
  await phone.close();
  }
  /* The signed-out top bar in the order of the site map, as the owner decided on September 23, 2026: How it works, Use cases,
     Library, Pricing, Docs, the guide Get set up and Sign in, then the primary action "Get started", which opens the funnel. The
     footer's Product group starts with Get started and Get set up, its Use cases group links the hub and the three use cases,
     and no footer link leads to /waitlist, which opens the funnel as an older address. */
  const liveBar=await page.locator("header nav a").evaluateAll(links=>links.filter(link=>!link.hidden).map(link=>[link.textContent.trim(),link.getAttribute("href")]));
  const livePages=["How it works","Use cases","Library","Pricing","Docs","Get set up","Sign in"];
  const barLists=bar=>JSON.stringify(bar.map(([name])=>name).filter(name=>livePages.includes(name)))===JSON.stringify(livePages)&&bar.some(([name,href])=>name==="Get set up"&&href==="/setup");
  check("live_top_bar_lists_the_pages_the_guide_and_the_get_started_action",barLists(liveBar)&&(await page.locator("#header-primary").innerText()).trim()==="Get started"&&await page.locator("#header-primary").getAttribute("href")==="/get-started");
  check("top_bar_check_rejects_a_bar_without_the_guide",!barLists(liveBar.filter(([name])=>name!=="Get set up"))&&!barLists([...liveBar].reverse()));
  const liveFooter=await page.evaluate(()=>({product:[...document.querySelectorAll("footer #footer-product a")].map(link=>link.getAttribute("href")),useCases:[...document.querySelectorAll("footer #footer-use-cases a")].map(link=>link.getAttribute("href")),
    all:[...document.querySelectorAll("footer a")].map(link=>(link.getAttribute("href")||"").split("#")[0])}));
  const footerHolds=footer=>footer.product.slice(0,2).join(" ")==="/get-started /setup"&&["/use-cases","/overnight","/efficiency","/learning"].every(href=>footer.useCases.includes(href))&&!footer.all.includes("/waitlist");
  check("live_footer_links_get_started_get_set_up_and_the_use_cases_and_not_the_waitlist",footerHolds(liveFooter));
  check("footer_check_rejects_a_waitlist_link_and_a_missing_use_case",!footerHolds({...liveFooter,all:[...liveFooter.all,"/waitlist"]})&&!footerHolds({...liveFooter,useCases:liveFooter.useCases.filter(href=>href!=="/learning")}));
  /* The connection entry on the homepage is written by the page script with the deployed address. */
  /* The homepage's connection entry left with its How it works band on September 24, 2026; Get set up writes each harness's entry
     with the deployed address, which guided_setup_uses_deployed_origin checks below. */
  await page.locator('header a[data-page="pricing"]').click();
  /* Read as a person reads it: the amount and "a month" stand on two lines of the plan card. */
  const livePricing=(await page.locator('[data-view="pricing"]').innerText()).replace(/\s+/g," ");
  check("live_pricing_view_states_every_published_fact",new URL(page.url()).pathname==="/pricing"&&pricingProblems(livePricing).length===0);
  check("pricing_fact_check_rejects_free_search_free_invited_accounts_and_another_price",pricingProblems(livePricing+"\nSearch is free.").length===1&&pricingProblems(livePricing+"\nInvited accounts are free.").length===1
    &&pricingProblems(livePricing.replaceAll("$29 a month","29 United States dollars each month")).length>=1);
  /* The pricing view's badge and note follow two reported facts, in the words of September 23, 2026: while account creation is
     closed it asks for the account first, whatever checkout reports; with account creation and checkout both open it says to
     subscribe from the account page; with account creation open and no checkout it offers no payment. */
  const livePublic=(await (await page.request.get(origin+"/api/v1/capabilities")).json()).result;
  const livePayment={badge:await page.locator("#pricing-state").innerText(),note:await page.locator("#pricing-payment-state").innerText()};
  check("live_pricing_view_reports_the_payment_state_from_the_service",livePublic.record_type==="service_capabilities/v1"&&JSON.stringify(livePayment)===JSON.stringify(expectedPayment(livePublic)));
  check("payment_state_rule_asks_for_the_account_first_while_account_creation_is_closed",JSON.stringify(expectedPayment({website:{registration_available:false},billing:{checkout:true}}))===JSON.stringify(paymentWords.accountFirst)
    &&JSON.stringify(expectedPayment({website:{registration_available:true},billing:{checkout:true}}))===JSON.stringify(paymentWords.open)&&JSON.stringify(expectedPayment({website:{registration_available:true},billing:{checkout:false}}))===JSON.stringify(paymentWords.closed));
  const plainWords=text=>!internalTerms.test(text);
  check("live_pricing_view_avoids_internal_runtime_names",plainWords(livePricing));
  check("plain_word_check_rejects_a_page_that_names_the_runtime",["Built on Loop Engine.","Every step is a Loop node.","See the role profiles.","Read the role profile.","Read the runtime classification."].every(claim=>!plainWords(livePricing+"\n"+claim)));
  const deepPricing=await page.request.get(origin+"/pricing",{maxRedirects:0});
  check("live_pricing_address_is_served_directly",deepPricing.status()===200&&(deepPricing.headers()["content-type"]||"").startsWith("text/html"));
  /* The deployed page is compared with what the deployed service reports, never with its own wording.
     A missing field or a missing element keeps its own check failing instead of ending the journey. */
  const liveCapabilities=(await (await page.request.get(origin+"/api/v1/capabilities",{maxRedirects:0})).json())?.result||{};
  const liveVersion=liveCapabilities.record_type==="service_capabilities/v1";
  const purchaseWords={source:"\\b(?:buy|purchase|checkout|subscribe|subscription|pay|payment|card)\\b",flags:"i"};
  const livePurchase=await page.locator('[data-view="pricing"]').evaluate((node,pattern)=>{
    const rule=new RegExp(pattern.source,pattern.flags);
    return [...node.querySelectorAll("button, a, form, input[type=submit], input[type=button]")]
      .map(item=>[item.tagName.toLowerCase()+(item.id?"#"+item.id:""),(item.textContent||"")+" "+(item.getAttribute("aria-label")||"")+" "+(item.getAttribute("value")||"")])
      .filter(([,text])=>rule.test(text)).map(([place])=>place);
  },purchaseWords);
  check("live_pricing_view_offers_no_purchase_control_while_checkout_is_closed",
    (liveVersion&&liveCapabilities.billing?.checkout===true)||livePurchase.length===0);
  const liveKeys=await page.locator("#plan-keys-detail").count()===1?await page.locator("#plan-keys-detail").evaluate(node=>node.textContent):"";
  const claimsKeys=liveKeys.startsWith("Create and revoke a key");
  check("live_personal_key_wording_follows_the_reported_capability",
    liveKeys!==""&&claimsKeys===(liveVersion&&liveCapabilities.website?.client_access_available===true));
  /* The terms of service the owner approved on September 23, 2026: served at their own address with the same words as
     docs/legal/TERMS-OF-SERVICE.md, the operator line and the date of the last change; linked from the shared footer and from
     the sentence above the button that creates an account; and no deployed page says any longer that they are not published. */
  const legalWords=file=>readFileSync(resolve(root,file),"utf8").replace(/\[([^\]]*)\]\([^)]*\)/g,"$1").replace(/`/g,"").replace(/\*\*/g,"").replace(/^#+\s/gm," ").replace(/^\|[-| :]+\|\s*$/gm," ").replace(/\|/g," ").replace(/^\s*- /gm," ").split(/\s+/).filter(Boolean);
  const termsWords=legalWords("docs/legal/TERMS-OF-SERVICE.md"),privacyWords=legalWords("docs/legal/PRIVACY-NOTICE.md");
  const sameWords=(shown,approved)=>shown.length>0&&JSON.stringify(shown)===JSON.stringify(approved);
  const termsOperator="Operator: Baltor.AI, 1428 Bryn Mawr St, Saxton, PA 16678, United States.",termsDate="Last changed: September 23, 2026";
  const unpublishedTerms=/terms of service:?\s+not yet published|terms(?: of service)? (?:are|is) (?:still )?(?:a draft|not (?:yet )?published)/i;
  const deepTerms=await page.request.get(origin+"/terms",{maxRedirects:0});
  check("live_terms_address_is_served_directly",deepTerms.status()===200&&(deepTerms.headers()["content-type"]||"").startsWith("text/html"));
  await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  const liveFooterTerms=await page.locator('footer a[href="/terms"]').evaluateAll(items=>items.map(item=>({text:item.textContent.trim(),page:item.dataset.page||""})));
  check("live_footer_links_the_terms_of_service",liveFooterTerms.length===1&&liveFooterTerms[0].text==="Terms of service"&&liveFooterTerms[0].page==="terms");
  if(liveFooterTerms.length===1)await page.locator('footer a[href="/terms"]').click();
  const liveTerms=await page.evaluate(()=>{const terms=document.querySelector("[data-terms-of-service]");return {path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),
    title:document.title,text:terms?terms.innerText:"",privacy:terms?terms.querySelectorAll('a[href="/privacy"]').length:0};});
  check("live_terms_open_from_the_footer_with_the_operator_and_the_date",liveTerms.path==="/terms"&&JSON.stringify(liveTerms.views)===JSON.stringify(["terms"])&&liveTerms.title.endsWith("| Terms of service")
    &&liveTerms.text.includes(termsOperator)&&liveTerms.text.includes(termsDate)&&liveTerms.privacy===1);
  check("live_terms_say_the_same_words_as_the_approved_text",sameWords(liveTerms.text.split(/\s+/).filter(Boolean),termsWords));
  check("terms_word_check_rejects_a_changed_word_and_a_missing_date",!sameWords(termsWords.map(word=>word==="three"?"twelve":word),termsWords)&&!sameWords(termsWords.filter(word=>word!=="Last"),termsWords)&&termsWords.join(" ").includes(termsDate));
  /* The sentence above the account creation button is part of the served form in both states. It is shown only while the
     deployed service reports that account creation is open, and then it must be visible. */
  const consentWords="By creating an account you agree to the terms of service and the privacy notice.";
  await page.goto(origin+"/signup");await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  if(liveOpen)await page.waitForFunction(()=>document.getElementById("email-signup")?.hidden===false,null,{timeout:10000}).catch(()=>{});
  const liveConsent=await page.evaluate(()=>{const form=document.getElementById("email-signup-form"),sentence=document.getElementById("signup-consent"),button=document.getElementById("email-signup-button");
    return {text:sentence?sentence.textContent.replace(/\s+/g," ").trim():"",inForm:Boolean(form&&sentence&&form.contains(sentence)),above:Boolean(sentence&&button&&(sentence.compareDocumentPosition(button)&Node.DOCUMENT_POSITION_FOLLOWING)),
      links:sentence?[...sentence.querySelectorAll("a")].map(link=>link.getAttribute("href")):[],shown:Boolean(sentence&&sentence.getClientRects().length>0)};});
  const consentHolds=(state,open)=>state.text===consentWords&&state.inForm&&state.above&&JSON.stringify(state.links)===JSON.stringify(["/terms","/privacy"])&&(!open||state.shown);
  check("live_account_form_names_and_links_the_terms_and_the_privacy_notice",consentHolds(liveConsent,liveOpen));
  check("consent_check_rejects_a_missing_link_a_sentence_below_the_button_and_a_hidden_sentence_while_open",!consentHolds({...liveConsent,links:["/privacy"]},false)
    &&!consentHolds({...liveConsent,above:false},false)&&!consentHolds({...liveConsent,shown:false},true));
  /* The deployed markup is read whole, hidden views included. */
  const liveMarkup=await (await page.request.get(origin+"/",{maxRedirects:0})).text();
  check("no_live_page_says_the_terms_are_unpublished",liveMarkup.includes("data-terms-of-service")&&!unpublishedTerms.test(liveMarkup));
  check("unpublished_terms_check_rejects_the_old_footer_note",unpublishedTerms.test("Terms of service: not yet published")&&unpublishedTerms.test("The terms are still a draft.")&&!unpublishedTerms.test("Terms of service"));
  /* Read-only signup/funnel checks: never submit a signup or call the identity provider. */
  await page.goto(origin+"/get-started");await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  const funnelState=await page.evaluate(()=>({view:document.body.dataset.page,state:document.getElementById("funnel")?.dataset.funnelState,
    form:!document.getElementById("funnel-signup-form")?.closest("[data-funnel-panel]")?.hidden,
    passwords:document.querySelectorAll('#funnel-signup-form input[type="password"],#email-signup-form input[type="password"]').length,
    consent:[...document.querySelectorAll('#funnel-consent a')].map(a=>a.getAttribute('href')),
    closedLink:document.getElementById('funnel-invite')?.getAttribute('href')}));
  /* Where the service takes an address, by registration or by its request list, the funnel shows the one account form; where it
     takes neither, it offers Sign in at /login. It never asks for a password and never says invitation or that search is free. */
  const funnelWords=await page.evaluate(()=>document.querySelector('[data-view="start"]')?.innerText||"");
  const funnelHolds=(state,takes)=>state.view==="start"&&state.state===(takes?"register":"invite")&&state.form===takes&&state.passwords===0&&
    JSON.stringify(state.consent)===JSON.stringify(["/terms","/privacy"])&&(takes||state.closedLink==="/login");
  check("live_signup_funnel_follows_registration_and_request_list_capabilities",funnelHolds(funnelState,liveTakesAddresses)&&!liveInvitation.test(funnelWords));
  check("signup_funnel_check_rejects_password_collection_and_missing_consent",!funnelHolds({...funnelState,passwords:1},liveTakesAddresses)&&!funnelHolds({...funnelState,consent:[]},liveTakesAddresses)&&!funnelHolds({...funnelState,state:"invite",form:false,closedLink:"/waitlist"},false));
  /* /waitlist opens the same funnel as an older address, and each use case the owner named opens its own page. */
  await page.goto(origin+"/waitlist");await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  check("live_waitlist_address_opens_the_get_started_funnel",await page.evaluate(()=>JSON.stringify([...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view)))==='["start"]'&&(await page.title()).endsWith("| Get started"));
  for(const [address,view,title] of [["/use-cases","use-cases","Use cases"],["/overnight","overnight","Solve complex problems overnight"],["/efficiency","efficiency","More efficient operation"],["/learning","learning","Learning and optimization, built in"]]){
    const direct=await page.request.get(origin+address,{maxRedirects:0});
    await page.goto(origin+address);
    check("live_use_case_page_opens_"+view,direct.status()===200&&(direct.headers()["content-type"]||"").startsWith("text/html")&&await page.evaluate(()=>JSON.stringify([...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view)))===JSON.stringify([view])
      &&(await page.title()).endsWith("| "+title));
  }
  await page.goto(origin+"/auth/confirm?token_hash=fixture-invalid&type=unsupported");
  await page.waitForFunction(()=>location.search===""&&document.body.dataset.page==="confirm");
  check("live_invalid_confirmation_clears_query_without_opening_a_password_form",await page.locator('#confirm-unusable').isVisible()&&await page.locator('#confirm-password-step').isHidden());
  await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector(".boundary-zone"));
  for(const asset of ["public-pages.js","public-pages.css","documentation-index.json","documentation.js","documentation.css","docs/what-baltor-is.html","docs/your-account.html","docs/searching-and-retrieving.html","docs/usage-and-what-you-pay-for.html","docs/troubleshooting.html","docs/serving-and-connections.html","service.js","client-access.js","catalogue-browser.js","architecture-story.js","service.css","architecture.css","client-recipes.json","supabase-client.js","geist.woff2","geist-mono.woff2","baltor-mark.svg","favicon-32.png","favicon-192.png","apple-touch-icon.png"]){
    const response=await page.request.get(origin+"/assets/"+asset,{maxRedirects:0});
    check("deployed_bytes_match_tested_source_"+asset,response.status()===200&&hash(await response.body())===hash(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets",asset))));
  }
  await page.goto(origin+"/how-it-works#task-breakdown");
  check("how_it_works_separates_client_and_server",await page.locator('[data-view="about"] .service-zone').isVisible()&&await page.locator('[data-view="about"] .client-zone').isVisible());
  const providerCopy=await page.locator('[data-view="about"] .provider-lane').innerText();
  const explainsProviderBoundary=text=>text.includes("Model keys stay in your environment")&&text.includes("A remote model may receive the information you allow");
  check("how_it_works_identifies_external_model_connection",explainsProviderBoundary(providerCopy));
  check("provider_boundary_check_rejects_wrong_secret_destination",!explainsProviderBoundary(providerCopy.replace("Model keys stay in your environment","Model keys are uploaded to the service")));
  check("live_public_explanation_avoids_internal_runtime_names",!internalTerms.test(await page.locator('[data-view="about"]').textContent())&&!(await page.locator("footer").innerText()).includes("Loop Engine"));
  await page.click("#assignment-build");
  check("live_task_explorer_changes_selected_context",(await page.locator("#assignment-materials").innerText()).includes("selected-normalizer.py"));
  await page.locator("#assignment-build").focus();await page.keyboard.press("End");
  check("live_task_explorer_supports_keyboard_selection",await page.locator("#assignment-verify").getAttribute("aria-selected")==="true");
  await page.goto(origin+"/connect");await page.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0);
  check("guided_setup_uses_deployed_origin",(await page.locator("#client-configuration").innerText()).includes(origin+"/mcp"));
  /* Every harness the hero names as one "Baltor sets up" has steps of its own on the guide, as the homepage's questions promise. */
  const liveTabs=await page.locator('#client-tabs [role="tab"]').evaluateAll(items=>items.map(item=>item.textContent.replace(/\s+/g," ").trim()));
  check("live_every_harness_the_hero_names_has_steps_on_the_guide",setsUpEveryNamedHarness(heroHarnesses,liveTabs));
  check("named_harness_check_rejects_a_harness_the_guide_does_not_set_up",!setsUpEveryNamedHarness(["Invented Harness"],liveTabs)&&setsUpEveryNamedHarness(["OpenCode"],["OpenCode 1.x"]));
  check("anonymous_connection_check_is_not_faked",await page.locator("#test-protocol").isDisabled()&&(await page.locator("#protocol-result").innerText()).includes("Not tested"));
  await page.locator("#client-tab-opencode").click();
  check("deployed_recipe_keeps_service_secret_as_reference",JSON.parse(await page.locator("#client-configuration").innerText()).mcp.baltor.headers.Authorization==="Bearer {env:BALTOR_SERVICE_TOKEN}");
  await page.goto(origin+"/examples");await page.click("#try-example");
  check("deployed_example_prepares_an_explicit_search",new URL(page.url()).pathname==="/app"&&await page.inputValue("#query")==="review inputs"&&await page.locator("#query").isDisabled());
  for(const path of ["/","/connect","/examples","/security","/app"]){
    await page.goto(origin+path,{waitUntil:"load"});
    navigation.push({path,...await page.evaluate(()=>{const entry=performance.getEntriesByType("navigation")[0];return {response_start_ms:entry.responseStart,dom_content_loaded_ms:entry.domContentLoadedEventEnd,load_ms:entry.loadEventEnd,transfer_bytes:entry.transferSize,resource_count:performance.getEntriesByType("resource").length};})});
  }
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/docs","/docs/what-baltor-is","/docs/your-account","/docs/searching-and-retrieving","/docs/usage-and-what-you-pay-for","/docs/troubleshooting","/docs/serving-and-connections","/","/use-cases","/overnight","/efficiency","/learning","/get-started","/how-it-works","/pricing","/login","/admin","/connect","/examples","/security","/terms",...showcasePaths]){
      await page.goto(origin+path);
      if(path.startsWith("/docs/"))await page.waitForSelector("#docs-article h2");
      check(`live_layout_${width}_${path}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
  }
  /* The retired trial words, read from the deployed pages themselves. The served assets are already compared byte for
     byte with the tested source above, so this pass covers the markup and anything the deployed service substitutes. */
  const liveRetired=/\bpilots?\b|\bbetas?\b|early access/i;
  const customerLanguage=text=>text.replaceAll(origin,"<service origin>");
  const liveRetiredProblems=[],liveInvitationProblems=[];
  /* A published legal text keeps the words the owner approved: the approved privacy notice says small groups and planned, and the
     approved terms said beta and search is free until the owner had them amended on September 23, 2026. This pass leaves out each
     legal text, and only while it is shown with exactly the approved words; docs/legal/README.md says why. A page without the shared header or footer, such as the page for an address the
     service does not serve, is read as far as it goes, so a missing page fails its own checks instead of ending the journey. */
  const readRetired=target=>target.evaluate(([terms,privacy])=>{
    const words=text=>text.split(/\s+/).filter(Boolean),same=(node,approved)=>node.getClientRects().length>0&&JSON.stringify(words(node.innerText))===JSON.stringify(approved);
    const exempt=[...[...document.querySelectorAll("[data-terms-of-service]")].filter(node=>same(node,terms)),...[...document.querySelectorAll("[data-privacy-notice]")].filter(node=>same(node,privacy))];
    exempt.forEach(node=>{node.hidden=true;});
    try{return [document.querySelector("header")?.innerText||"",[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.innerText).join("\n"),document.querySelector("footer")?.innerText||""].join("\n");}
    finally{exempt.forEach(node=>{node.hidden=false;});}
  },[termsWords,privacyWords]);
  for(const path of ["/docs/what-baltor-is","/docs/your-account","/docs/searching-and-retrieving","/docs/usage-and-what-you-pay-for","/docs/troubleshooting","/docs/serving-and-connections","/","/use-cases","/overnight","/efficiency","/learning","/get-started","/waitlist","/how-it-works","/pricing","/connect","/setup","/signup","/login","/examples","/security","/privacy","/terms","/app","/account","/docs",...showcasePaths]){
    await page.goto(origin+path);
    await page.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
    if(path.startsWith("/docs/"))await page.waitForSelector("#docs-article h2");
    const shown=customerLanguage(await readRetired(page));
    if(liveRetired.test(shown))liveRetiredProblems.push(path+": "+shown.match(liveRetired)[0]);
    if(liveInvitation.test(shown))liveInvitationProblems.push(path+": "+shown.match(liveInvitation)[0]);
  }
  /* The known-wrong page for that exemption: the deployed terms with a retired sentence written beside them, in this browser only. */
  await page.goto(origin+"/terms");
  await page.evaluate(()=>{const planted=document.createElement("p");planted.id="known-wrong-retired";planted.textContent="Join the private beta.";document.querySelector('[data-view="terms"]')?.prepend(planted);});
  const plantedRetired=customerLanguage(await readRetired(page));
  await page.evaluate(()=>document.getElementById("known-wrong-retired")?.remove());
  check("live_retired_word_exemption_still_reads_a_word_beside_the_terms",liveRetired.test(plantedRetired)&&plantedRetired.match(liveRetired)[0].toLowerCase()==="beta"&&!liveRetired.test(customerLanguage(await readRetired(page))));
  check("live_retired_word_check_allows_exact_service_origin_but_refuses_adjacent_claim",!liveRetired.test(customerLanguage(origin+"/mcp"))&&liveRetired.test(customerLanguage(origin+"/mcp Join the private pilot.")));
  check("no_live_customer_page_describes_the_product_as_a_trial",liveRetiredProblems.length===0);
  check("live_retired_word_check_rejects_a_known_wrong_page",["Join the private pilot.","Beta users get early access.","A pilot user can search."].every(claim=>liveRetired.test(claim))&&!liveRetired.test("Accounts open in small groups. Join the waiting list."));
  check("no_live_customer_page_uses_the_words_of_an_invitation_only_service",liveInvitationProblems.length===0);
  check("live_invitation_word_check_rejects_a_known_wrong_page",["Invitation only while we open in small groups.","Invited accounts are free.","Search is free.","Join the waiting list.","Being built","Planned"].every(claim=>liveInvitation.test(claim))
    &&["Get started","Create your account","The plan can change as you learn more."].every(claim=>!liveInvitation.test(claim)));
  /* The known-wrong page for the privacy exemption: a retired sentence written beside the deployed notice, in this browser only. */
  await page.goto(origin+"/privacy");
  await page.evaluate(()=>{const planted=document.createElement("p");planted.id="known-wrong-invitation";planted.textContent="Request an invitation.";document.querySelector('[data-view="privacy"]')?.prepend(planted);});
  const plantedInvitation=customerLanguage(await readRetired(page));
  await page.evaluate(()=>document.getElementById("known-wrong-invitation")?.remove());
  check("live_invitation_word_exemption_still_reads_a_word_beside_the_privacy_notice",liveInvitation.test(plantedInvitation)&&!liveInvitation.test(customerLanguage(await readRetired(page))));
  /* The pages of September 24, 2026 at their own addresses, each with its own title and canonical address; the two files written
     from the site map; HEAD answering like GET without a body; and the status page agreeing with the health record it reads. */
  for(const address of showcasePaths){
    const direct=await page.request.get(origin+address,{maxRedirects:0});await page.goto(origin+address);
    check("live_page_opens_with_its_own_title_and_canonical_address_"+address.slice(1).replace(/\//g,"-"),direct.status()===200&&opensItsPage(await shownPage(page),siteMap.pages.find(item=>item.address===address)));
  }
  const robots=await page.request.get(origin+"/robots.txt",{maxRedirects:0}),sitemap=await page.request.get(origin+"/sitemap.xml",{maxRedirects:0});
  const listed=[...(await sitemap.text()).matchAll(/<loc>([^<]+)<\/loc>/g)].map(found=>found[1]),listable=siteMap.pages.filter(item=>item.indexed).map(item=>canonicalOrigin+item.address);
  check("live_robots_and_sitemap_follow_the_site_map",robots.status()===200&&(await robots.text()).includes("Sitemap: "+canonicalOrigin+"/sitemap.xml")&&sitemap.status()===200&&JSON.stringify(listed)===JSON.stringify(listable));
  const headAnswer=await page.request.fetch(origin+"/",{method:"HEAD",maxRedirects:0}),getAnswer=await page.request.get(origin+"/",{maxRedirects:0});
  check("live_head_answers_like_get_without_a_body",headAnswer.status()===200&&(await headAnswer.body()).length===0&&headAnswer.headers()["content-type"]===getAnswer.headers()["content-type"]
    &&headAnswer.headers()["content-length"]===String((await getAnswer.body()).length));
  await page.goto(origin+"/status");await page.waitForFunction(()=>document.getElementById("status-summary")?.dataset.statusState!=="reading",null,{timeout:15000}).catch(()=>{});
  const liveHealth=(await (await page.request.get(origin+"/api/v1/health",{maxRedirects:0})).json())?.result||{};
  const statusShown=await page.evaluate(()=>({state:document.getElementById("status-summary")?.dataset.statusState||"",text:document.querySelector('[data-view="status"]')?.innerText||""}));
  const statusAgrees=(shown,health)=>health.record_type==="service_health/v2"&&Array.isArray(health.checks)&&shown.state===(!health.ready?"down":health.checks.every(item=>item.passed)?"working":"limited")
    &&!/\d\s*%|\buptime of\b/i.test(shown.text);
  check("live_status_page_agrees_with_the_health_record_and_shows_no_uptime_figure",statusAgrees(statusShown,liveHealth));
  check("status_check_rejects_a_green_page_while_not_ready_and_an_uptime_figure",!statusAgrees({...statusShown,state:"working"},{...liveHealth,ready:false})
    &&!statusAgrees({...statusShown,text:statusShown.text+" 99.9% uptime"},liveHealth));
  const anonymous=await page.request.get(origin+"/api/v1/admin/access",{maxRedirects:0});
  check("deployed_administration_still_requires_credentials",anonymous.status()===401);
  check("no_browser_runtime_errors",errors.length===0);
  check("no_unexpected_third_party_requests",external.length===0);
}catch(error){checks.push({name:"hosted_browser_journey_completed",passed:false,error:String(error)});}
finally{await browser.close();}
const result={record_type:"hosted_website_acceptance/v1",origin,observed_at:new Date().toISOString(),checks,passed:checks.filter(x=>x.passed).length,total:checks.length,all_passed:checks.every(x=>x.passed),errors,external,navigation,navigation_limits:"One headless browser navigation per route from the development workstation; not field Core Web Vitals or an availability guarantee",credentials_used:false,external_mutations:false};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});console.log(JSON.stringify({passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed)}));process.exitCode=result.all_passed?0:1;
