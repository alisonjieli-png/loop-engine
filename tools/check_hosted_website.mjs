/* Read-only browser acceptance of the deployed public site. No credentials. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {readFileSync,writeFileSync,existsSync} from "node:fs";
import {resolve} from "node:path";
import {createHash} from "node:crypto";

const origin=process.argv[2],output=resolve(process.argv[3]||"");
if(!origin||new URL(origin).origin!==origin||!origin.startsWith("https://")||!process.argv[3]||existsSync(output))throw new Error("Use an exact HTTPS origin and a new report path.");
const root=resolve(new URL("..",import.meta.url).pathname);
const checks=[],errors=[],external=[],navigation=[];
const check=(name,passed)=>checks.push({name,passed:passed===true});
/* One plain-word rule for the public pages. tools/check_service_workspace.mjs carries the same line, and a named check there compares the two. */
const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
const hash=value=>createHash("sha256").update(value).digest("hex");
const browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
await context.route("**/*",route=>{if(new URL(route.request().url()).origin===origin)route.continue();else{external.push(new URL(route.request().url()).origin);route.abort();}});
const page=await context.newPage();page.on("pageerror",error=>errors.push(error.message));
try{
  const home=await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector(".boundary-zone")&&document.querySelector("#service-status").textContent.includes("Service available"));
  check("HTTPS_homepage_is_available",home.status()===200);
  check("live_page_has_four_intelligence_layers",await page.locator('[data-view="about"] [data-intelligence-layer]').count()===4);
  const liveHeadline=await page.locator('[data-view="home"] h1').innerText();
  const namesTheReader=text=>/\byour\b/i.test(text)&&/\bdevelopers?\b/i.test(text)&&/\bagents?\b/i.test(text);
  const namesTheStep=text=>/\beach step\b/i.test(text);
  check("live_homepage_headline_names_the_developer_and_the_agent",namesTheReader(liveHeadline)&&await page.locator('[data-view="home"] .boundary-figure').count()===0);
  check("headline_check_rejects_a_headline_that_names_neither",["Turn complex problems into reusable solutions.","Harness and agent optimized operation.","Supercharge your workflow."].every(claim=>!namesTheReader(claim))&&namesTheReader("Supercharge your developers and AI agents"));
  check("live_homepage_subhead_names_the_unit_of_work",namesTheStep(await page.locator('[data-view="home"] .hero-subhead').innerText()));
  check("live_default_appearance_is_light",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  check("live_how_it_works_covers_five_optimization_problems",await page.locator('[data-view="about"] [data-friction]').count()===5);
  check("live_homepage_opens_with_the_owner_category_line",await page.locator('[data-view="home"] .hero .eyebrow').evaluate(node=>node.textContent.trim())==="Harness and agent optimized operation");
  const livePositioning=await page.locator('[data-view="home"] .hero-positioning').innerText();
  const explainsTheCategoryLine=text=>/harness and agent optimized operation/i.test(text)&&/\ba harness is\b/i.test(text)&&/each step/i.test(text);
  check("live_owner_category_line_is_explained_in_plain_words",explainsTheCategoryLine(livePositioning));
  check("category_line_explanation_check_rejects_a_bare_phrase",!explainsTheCategoryLine("Harness and agent optimized operation.")&&explainsTheCategoryLine(livePositioning));
  check("live_homepage_states_the_free_and_paid_split",(await page.locator('[data-view="home"] .hero-split').innerText()).startsWith("Free to install. Paid access to the library."));
  check("live_homepage_shows_the_three_step_strip",JSON.stringify(await page.locator("[data-start-step]").evaluateAll(items=>items.map(item=>item.dataset.startStep).sort()))===JSON.stringify(["ask","connect","keep"]));
  check("live_homepage_says_what_an_account_gives_you",JSON.stringify(await page.locator("[data-offer]").evaluateAll(items=>items.map(item=>item.dataset.offer).sort()))===JSON.stringify(["downloads","recipes","search","usage"]));
  check("live_homepage_offers_one_primary_action",await page.locator('[data-view="home"] .hero .button.primary').count()===1&&await page.locator('[data-view="home"] .hero .button.primary').getAttribute("href")==="/connect"&&["waiting","open"].includes(await page.locator("#hero-primary").getAttribute("data-access-state")));
  /* The six benefits. Every detail is in the page source, and pointing at a title, moving keyboard focus to it and
     pressing it each open that one and close the others. */
  const liveBenefits=["material","reuse","model","export","review","resume"];
  const liveShown=target=>target.locator("[data-benefit]").evaluateAll(items=>items.filter(item=>getComputedStyle(item.querySelector("[data-benefit-detail]")).display!=="none").map(item=>item.dataset.benefit));
  check("live_homepage_lists_six_benefits",JSON.stringify(await page.locator("[data-benefit]").evaluateAll(items=>items.map(item=>item.dataset.benefit)))===JSON.stringify(liveBenefits));
  const livePressed=[],liveFocused=[],liveHovered=[];
  for(const name of [...liveBenefits].reverse()){await page.locator('[data-benefit-title="'+name+'"]').dispatchEvent("click");livePressed.push(JSON.stringify(await liveShown(page))===JSON.stringify([name]));}
  await page.locator('[data-benefit-title="'+liveBenefits[liveBenefits.length-1]+'"]').dispatchEvent("click");
  await page.locator('[data-benefit-title="'+liveBenefits[0]+'"]').focus();
  for(const name of liveBenefits){liveFocused.push(await page.evaluate(()=>document.activeElement?.dataset.benefitTitle||"")===name&&JSON.stringify(await liveShown(page))===JSON.stringify([name]));await page.keyboard.press("Tab");}
  for(const name of liveBenefits){await page.locator('[data-benefit="'+name+'"]').hover();liveHovered.push(JSON.stringify(await liveShown(page))===JSON.stringify([name]));}
  check("live_press_shows_only_that_benefit",livePressed.length===6&&livePressed.every(Boolean));
  check("live_keyboard_focus_alone_opens_each_benefit",liveFocused.length===6&&liveFocused.every(Boolean));
  check("live_pointing_at_a_benefit_opens_it",liveHovered.length===6&&liveHovered.every(Boolean));
  check("live_get_started_is_the_first_navigation_item",JSON.stringify(await page.locator("header nav a").evaluateAll(items=>items.slice(0,2).map(item=>item.textContent.trim())))===JSON.stringify(["Get started","How it works"]));
  await page.locator('header a[data-page="pricing"]').click();
  const livePricing=await page.locator('[data-view="pricing"]').innerText();
  const pricingFacts=["Baltor Pro","29 United States dollars","each month","Search is free.","one downloaded item","Invited accounts are free."];
  check("live_pricing_view_states_every_published_fact",new URL(page.url()).pathname==="/pricing"&&pricingFacts.every(fact=>livePricing.includes(fact)));
  /* The badge follows two reported facts: invitation only while account creation is closed, whatever checkout reports;
     payment open only when account creation and checkout are both open; otherwise payment not open. */
  const livePublic=(await (await page.request.get(origin+"/api/v1/capabilities")).json()).result;
  const expectedPayment=facts=>facts.website.registration_available!==true?"Invitation only":facts.billing.checkout===true?"Payment open":"Payment not open";
  check("live_pricing_view_reports_the_payment_state_from_the_service",livePublic.record_type==="service_capabilities/v1"&&await page.locator("#pricing-state").innerText()===expectedPayment(livePublic));
  check("payment_state_rule_rejects_payment_open_beside_the_waiting_list",expectedPayment({website:{registration_available:false},billing:{checkout:true}})==="Invitation only"&&expectedPayment({website:{registration_available:true},billing:{checkout:true}})==="Payment open");
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
  await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector(".boundary-zone"));
  for(const asset of ["service.js","client-access.js","catalogue-browser.js","architecture-story.js","service.css","architecture.css","client-recipes.json","supabase-client.js"]){
    const response=await page.request.get(origin+"/assets/"+asset,{maxRedirects:0});
    check("deployed_bytes_match_tested_source_"+asset,response.status()===200&&hash(await response.body())===hash(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets",asset))));
  }
  await page.locator("#hero-how-it-works").click();
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
  await page.goto(origin+"/connect");await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled);
  check("guided_setup_uses_deployed_origin",(await page.locator("#client-configuration").innerText()).includes(origin+"/mcp"));
  check("anonymous_connection_check_is_not_faked",await page.locator("#test-protocol").isDisabled()&&(await page.locator("#protocol-result").innerText()).includes("Not tested"));
  await page.selectOption("#client-choice","opencode");
  check("deployed_recipe_keeps_service_secret_as_reference",JSON.parse(await page.locator("#client-configuration").innerText()).mcp.baltor.headers.Authorization==="Bearer {env:BALTOR_SERVICE_TOKEN}");
  await page.goto(origin+"/examples");await page.click("#try-example");
  check("deployed_example_prepares_an_explicit_search",new URL(page.url()).pathname==="/app"&&await page.inputValue("#query")==="review inputs"&&await page.locator("#query").isDisabled());
  for(const path of ["/","/connect","/examples","/security","/app"]){
    await page.goto(origin+path,{waitUntil:"load"});
    navigation.push({path,...await page.evaluate(()=>{const entry=performance.getEntriesByType("navigation")[0];return {response_start_ms:entry.responseStart,dom_content_loaded_ms:entry.domContentLoadedEventEnd,load_ms:entry.loadEventEnd,transfer_bytes:entry.transferSize,resource_count:performance.getEntriesByType("resource").length};})});
  }
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/","/how-it-works","/pricing","/login","/admin","/connect","/examples","/security"]){
      await page.goto(origin+path);
      check(`live_layout_${width}_${path}`,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    }
  }
  /* The retired trial words, read from the deployed pages themselves. The served assets are already compared byte for
     byte with the tested source above, so this pass covers the markup and anything the deployed service substitutes. */
  const liveRetired=/\bpilots?\b|\bbetas?\b|early access/i;
  const liveRetiredProblems=[];
  for(const path of ["/","/how-it-works","/pricing","/connect","/signup","/login","/examples","/security","/app","/account","/docs"]){
    await page.goto(origin+path);
    const shown=await page.evaluate(()=>[document.querySelector("header").innerText,[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.innerText).join("\n"),document.querySelector("footer").innerText].join("\n"));
    if(liveRetired.test(shown))liveRetiredProblems.push(path+": "+shown.match(liveRetired)[0]);
  }
  check("no_live_customer_page_describes_the_product_as_a_trial",liveRetiredProblems.length===0);
  check("live_retired_word_check_rejects_a_known_wrong_page",["Join the private pilot.","Beta users get early access.","A pilot user can search."].every(claim=>liveRetired.test(claim))&&!liveRetired.test("Accounts open in small groups. Join the waiting list."));
  const anonymous=await page.request.get(origin+"/api/v1/admin/access",{maxRedirects:0});
  check("deployed_administration_still_requires_credentials",anonymous.status()===401);
  check("no_browser_runtime_errors",errors.length===0);
  check("no_unexpected_third_party_requests",external.length===0);
}catch(error){checks.push({name:"hosted_browser_journey_completed",passed:false,error:String(error)});}
finally{await browser.close();}
const result={record_type:"hosted_website_acceptance/v1",origin,observed_at:new Date().toISOString(),checks,passed:checks.filter(x=>x.passed).length,total:checks.length,all_passed:checks.every(x=>x.passed),errors,external,navigation,navigation_limits:"One headless browser navigation per route from the development workstation; not field Core Web Vitals or an availability guarantee",credentials_used:false,external_mutations:false};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});console.log(JSON.stringify({passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed)}));process.exitCode=result.all_passed?0:1;
