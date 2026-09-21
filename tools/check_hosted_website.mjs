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
  check("live_page_has_four_intelligence_layers",await page.locator("[data-intelligence-layer]").count()===4);
  check("live_homepage_leads_with_reusable_solutions",(await page.locator('[data-view="home"] h1').innerText()).includes("reusable solutions")&&await page.locator('[data-view="home"] .boundary-figure').count()===0);
  check("live_default_appearance_is_light",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  check("live_homepage_covers_five_optimization_problems",await page.locator("[data-friction]").count()===5);
  check("live_homepage_opens_with_the_owner_category_line",await page.locator('[data-view="home"] .hero .eyebrow').evaluate(node=>node.textContent.trim())==="Harness and agent optimized operation");
  check("live_homepage_shows_the_three_step_strip",JSON.stringify(await page.locator("[data-start-step]").evaluateAll(items=>items.map(item=>item.dataset.startStep).sort()))===JSON.stringify(["ask","connect","keep"]));
  check("live_homepage_says_what_an_account_gives_you",JSON.stringify(await page.locator("[data-offer]").evaluateAll(items=>items.map(item=>item.dataset.offer).sort()))===JSON.stringify(["downloads","recipes","search","usage"]));
  check("live_homepage_offers_one_primary_action",await page.locator('[data-view="home"] .hero .button.primary').count()===1&&["invited","open"].includes(await page.locator("#hero-primary").getAttribute("data-access-state")));
  await page.locator('header a[data-page="pricing"]').click();
  const livePricing=await page.locator('[data-view="pricing"]').innerText();
  const pricingFacts=["Baltor Pro","29 US dollars","each month","Search is free.","one downloaded item","Invited beta users are free."];
  check("live_pricing_view_states_every_published_fact",new URL(page.url()).pathname==="/pricing"&&pricingFacts.every(fact=>livePricing.includes(fact)));
  check("live_pricing_view_reports_the_payment_state_from_the_service",["Payment open","Payment not open"].includes(await page.locator("#pricing-state").innerText()));
  const plainWords=text=>!internalTerms.test(text);
  check("live_pricing_view_avoids_internal_runtime_names",plainWords(livePricing));
  check("plain_word_check_rejects_a_page_that_names_the_runtime",["Built on Loop Engine.","Every step is a Loop node.","See the role profiles.","Read the role profile.","Read the runtime classification."].every(claim=>!plainWords(livePricing+"\n"+claim)));
  const deepPricing=await page.request.get(origin+"/pricing",{maxRedirects:0});
  check("live_pricing_address_is_served_directly",deepPricing.status()===200&&(deepPricing.headers()["content-type"]||"").startsWith("text/html"));
  /* The deployed page is compared with what the deployed service reports, never with its own wording. */
  const liveCapabilities=(await (await page.request.get(origin+"/api/v1/capabilities",{maxRedirects:0})).json()).result;
  const liveVersion=liveCapabilities.record_type==="service_capabilities/v1";
  const purchaseWords={source:"\\b(?:buy|purchase|checkout|subscribe|subscription|pay|payment|card)\\b",flags:"i"};
  const livePurchase=await page.locator('[data-view="pricing"]').evaluate((node,pattern)=>{
    const rule=new RegExp(pattern.source,pattern.flags);
    return [...node.querySelectorAll("button, a, form, input[type=submit], input[type=button]")]
      .map(item=>[item.tagName.toLowerCase()+(item.id?"#"+item.id:""),(item.textContent||"")+" "+(item.getAttribute("aria-label")||"")+" "+(item.getAttribute("value")||"")])
      .filter(([,text])=>rule.test(text)).map(([place])=>place);
  },purchaseWords);
  check("live_pricing_view_offers_no_purchase_control_while_checkout_is_closed",
    (liveVersion&&liveCapabilities.billing.checkout===true)||livePurchase.length===0);
  const liveKeys=await page.locator("#plan-keys-detail").evaluate(node=>node.textContent);
  const claimsKeys=liveKeys.startsWith("Create and revoke a key");
  check("live_personal_key_wording_follows_the_reported_capability",
    claimsKeys===(liveVersion&&liveCapabilities.website.client_access_available===true));
  await page.goto(origin+"/");await page.waitForFunction(()=>document.querySelector(".boundary-zone"));
  for(const asset of ["service.js","client-access.js","architecture-story.js","service.css","architecture.css","client-recipes.json","supabase-client.js"]){
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
  const anonymous=await page.request.get(origin+"/api/v1/admin/access",{maxRedirects:0});
  check("deployed_administration_still_requires_credentials",anonymous.status()===401);
  check("no_browser_runtime_errors",errors.length===0);
  check("no_unexpected_third_party_requests",external.length===0);
}catch(error){checks.push({name:"hosted_browser_journey_completed",passed:false,error:String(error)});}
finally{await browser.close();}
const result={record_type:"hosted_website_acceptance/v1",origin,observed_at:new Date().toISOString(),checks,passed:checks.filter(x=>x.passed).length,total:checks.length,all_passed:checks.every(x=>x.passed),errors,external,navigation,navigation_limits:"One headless browser navigation per route from the development workstation; not field Core Web Vitals or an availability guarantee",credentials_used:false,external_mutations:false};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"});console.log(JSON.stringify({passed:result.passed,total:result.total,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed)}));process.exitCode=result.all_passed?0:1;
