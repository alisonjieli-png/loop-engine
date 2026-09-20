/* Real browser + HTTP + durable-domain checks. Providers are local fixtures.
   Removed-guard controls change the served page script in memory only, never a source file. */
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync} from "node:fs";
import {createHash,randomBytes} from "node:crypto";
import {resolve} from "node:path";

const root=resolve(new URL("..",import.meta.url).pathname);
const output=resolve(process.argv[2] || "artifacts/architecture-audit-2026-09-19/service-workspace-browser-1.json");
for (const path of [output,...["-desktop.png","-mobile-dark.png","-admin.png","-task-desktop.png","-task-mobile.png","-boundaries.png","-connect-desktop.png","-connect-mobile.png","-connect-claude-code.png"].map(suffix=>output.replace(/\.json$/,suffix))]) {
  if (existsSync(path)) throw new Error("Refusing to overwrite an existing browser evidence artifact: " + path);
}
/* Connection recipes. The reviewed record is read from the source tree before any process starts, so the page is compared with the record and not with itself. */
const recipeRecord=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/client-recipes.json"),"utf8"));
const program=`from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys,time
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.stripe_session_checks import fixture
from loop_engine.core.service_runtime.stripe_session_transport_checks import _application
from loop_engine.core.service_runtime.http_test_fixtures import running_key_set
from loop_engine.core.service_runtime.browser_identity import BrowserIdentityAdapter,BrowserIdentityConfiguration
from loop_engine.core.service_runtime.access import ServiceAccessAdministration,ServiceClientAccessPolicy
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
with ExitStack() as stack:
    root=Path(stack.enter_context(TemporaryDirectory(prefix="service-browser-")))
    (root/"intelligence").mkdir(); (root/"billing").mkdir(); (root/"accounts").mkdir()
    held=prepared(root/"intelligence")
    factory=lambda config:ServiceHttpApplication(held.runtime,held.provisioning,config,access_administration=held.administration)
    base,_=stack.enter_context(running_http(held,application_factory=factory,display_name="Baltor"))
    billing=fixture(root/"billing")
    billing_base,_=stack.enter_context(running_http(billing,application_factory=lambda config:_application(billing,config)))
    account=HttpDomainFixture(root/"accounts",operator_access=False)
    provider,public_keys=stack.enter_context(running_key_set())
    private_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    public_keys["keys"]=[{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())),"kid":"browser-test","alg":"RS256","use":"sig"}]
    subject="7b2fd7e8-168a-49c5-87c2-d52b79df1a94"
    identity_token=jwt.encode({"iss":provider+"/auth/v1","aud":"authenticated","sub":subject,"exp":int(time.time())+1800,"iat":int(time.time()),"role":"authenticated","is_anonymous":False},private_key,algorithm="RS256",headers={"kid":"browser-test"})
    user={"id":subject,"email":"account-test@example.invalid","role":"authenticated","is_anonymous":False,"email_confirmed_at":"2026-01-01T00:00:00Z"}
    identity=BrowserIdentityAdapter(account.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-customers",registration_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",starter_bindings=(account.bindings["skill.alpha"],),transport=lambda _:user)
    manager=ServiceAccessAdministration(account.runtime,ServiceClientAccessPolicy(writes_authorized=True))
    account_base,_=stack.enter_context(running_http(account,application_factory=lambda config:ServiceHttpApplication(account.runtime,account.provisioning,config,browser_identity=identity,client_access=manager),display_name="Baltor"))
    print(json.dumps({"base":base,"token":held.keys["alpha"].key,"admin_token":held.admin_key.key,"billing_base":billing_base,"billing_token":billing.keys["alpha"].key,"account_base":account_base,"identity_origin":provider,"identity_token":identity_token,"identity_user":user}),flush=True)
    sys.stdin.readline()
`;
const child=spawn(resolve(root,".venv/bin/python"),["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:"src"},stdio:["pipe","pipe","pipe"]});
const lines=createInterface({input:child.stdout});
const fixture=await new Promise((resolve,reject)=>{ const timer=setTimeout(()=>reject(new Error("Fixture startup deadline")),15000); lines.once("line",line=>{clearTimeout(timer);resolve(JSON.parse(line));}); child.once("exit",code=>{clearTimeout(timer);reject(new Error("Fixture stopped before startup: "+code));}); });
const checks=[],errors=[],network=[]; let browser;
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const secrets=[fixture.token,fixture.billing_token,fixture.admin_token,fixture.identity_token];
const safeError=error=>secrets.reduce((text,secret)=>text.replaceAll(secret,"[redacted]"),String(error));
const endpointMark="{{ENDPOINT}}",mutants=[];
const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
const withEndpoint=(value,endpoint)=>value===endpointMark?endpoint:Array.isArray(value)?value.map(item=>withEndpoint(item,endpoint)):value&&typeof value==="object"?Object.fromEntries(Object.entries(value).map(([key,item])=>[key,withEndpoint(item,endpoint)])):value;
const ordered=value=>Array.isArray(value)?value.map(ordered):value&&typeof value==="object"?Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])])):value;
const sameValue=(left,right)=>JSON.stringify(ordered(left))===JSON.stringify(ordered(right));
const textLeaves=(value,key="",found=[])=>{if(typeof value==="string")found.push([key,value]);else if(value&&typeof value==="object")for(const [name,item] of Object.entries(value))textLeaves(item,Array.isArray(value)?key:name,found);return found;};
const readToml=text=>{const result={};let table=result;for(const line of text.split("\n")){if(!line.trim())continue;const header=line.match(/^\[([A-Za-z0-9_.-]+)\]$/);if(header){table=result;for(const part of header[1].split("."))table=table[part]??={};continue;}const entry=line.match(/^([A-Za-z0-9_-]+) = (.+)$/);if(!entry)throw new Error("Unreadable configuration line");table[entry[1]]=JSON.parse(entry[2]);}return result;};
// Key-shaped text: a long unbroken run of key characters, a shorter run that mixes letters and digits, or a bearer value that is not an environment reference.
const keyShaped=text=>/[A-Za-z0-9_-]{32,}/.test(text)||(text.match(/[A-Za-z0-9_-]{20,}/g)||[]).some(run=>/\d/.test(run)&&/[A-Za-z]/.test(run))||/\bbearer\s+(?![{$])\S/i.test(text);
const changedRecipe=(id,change)=>{const record=structuredClone(recipeRecord);change(record.recipes.find(recipe=>recipe.id===id),record);return record;};
async function openConnect(context,base,{served,mutation}={}){
  const page=await context.newPage(),state={applied:false,errors:[],policy:""};
  page.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
  await page.addInitScript(()=>{window.policyViolations=[];addEventListener("securitypolicyviolation",event=>window.policyViolations.push(event.violatedDirective));});
  if(served)await page.route("**/assets/client-recipes.json",route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(served)}));
  if(mutation)await page.route("**/assets/service.js",async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
  state.policy=(await page.goto(base+"/connect")).headers()["content-security-policy"]||"";
  await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled||document.querySelector("#setup-message").textContent!=="");
  return {page,state};
}
async function checkShownRecipe(page,base,record,recipe,note){
  const endpoint=base+"/mcp",variable=record.credential_variable,id=recipe.id,content=selector=>page.locator(selector).evaluate(node=>node.textContent);
  await page.selectOption("#client-choice",id);
  const shown=await content("#client-configuration"),expected=withEndpoint(recipe.configuration,endpoint);
  let parsed=null;try{parsed=recipe.format==="toml"?readToml(shown):JSON.parse(shown);}catch(_){}
  note("recipe_renders_"+id,parsed!==null&&sameValue(parsed,expected)&&(recipe.format!=="json"||shown===JSON.stringify(expected,null,2))&&await content("#configuration-location")===recipe.configuration_location&&await content("#client-configuration-note")===recipe.configuration_note&&await content("#client-version-note")===recipe.version_note&&await page.locator("#client-choice option:checked").innerText()===recipe.name);
  const view=await page.locator('[data-view="setup"]').innerText(),scrub=text=>text.replaceAll(endpoint,"").replaceAll(variable,"");
  note("recipe_contains_no_key_"+id,shown.includes(variable)&&!keyShaped(scrub(shown))&&!keyShaped(scrub(view))&&!secrets.some(secret=>view.includes(secret)||shown.includes(secret)));
  const addresses=shown.match(/[a-z][a-z0-9+.-]*:\/\/[^\s"']+/gi)||[],targets=textLeaves(parsed||{}).filter(([key])=>key==="url").map(([,text])=>text);
  note("recipe_uses_current_origin_"+id,targets.length===1&&targets[0]===endpoint&&!shown.includes("{{")&&addresses.every(address=>address===endpoint||address===recipe.configuration.$schema),{addresses:addresses.length});
  await page.evaluate(()=>navigator.clipboard.writeText("nothing copied yet"));
  await page.click("#copy-configuration");
  await page.waitForFunction(()=>document.querySelector("#copy-configuration").textContent==="Configuration copied"||document.querySelector("#setup-message").textContent.includes("Clipboard unavailable"));
  const copied=await page.evaluate(()=>navigator.clipboard.readText());
  note("recipe_copy_matches_displayed_text_"+id,copied===shown&&copied===await content("#client-configuration")&&shown.length>0,{copied_length:copied.length,shown_length:shown.length});
  note("recipe_states_how_to_check_and_revoke_"+id,recipe.verification_command.length>0&&await content("#client-verify-command")===recipe.verification_command&&await content("#client-verify-note")===recipe.verification_note&&/revoke/i.test(record.revocation_note)&&await content("#client-revoke-note")===record.revocation_note&&await content("#client-removal-note")===recipe.removal_note&&await page.locator("#client-revoke-note").isVisible()&&await page.locator("#client-removal-note").isVisible());
  note("recipe_cites_its_source_"+id,recipe.source_url.startsWith("https://")&&await page.locator("#client-source").getAttribute("href")===recipe.source_url&&(await page.locator("#client-source").getAttribute("rel")).includes("noopener"));
  note("connect_view_uses_plain_words_"+id,!internalTerms.test(view));
  return view;
}
/* A known-wrong record must be refused before anything from it is displayed. A page without the rule shows it, and the ordinary recipe checks then fail. */
async function checkRefusedRecord(context,base,note,wrong,mutation){
  const {page,state}=await openConnect(context,base,{served:wrong.served,mutation});
  const refusal=await page.locator("#setup-message").evaluate(node=>node.dataset.refusal||""),closed=await page.locator("#client-choice").isDisabled()&&await page.locator("#copy-configuration").isDisabled();
  note(wrong.name,closed&&refusal===wrong.reason&&!(await page.content()).includes(wrong.planted)&&await page.locator("#client-revoke-note").evaluate(node=>node.textContent)===recipeRecord.revocation_note,{refusal,closed});
  if(!closed)await checkShownRecipe(page,base,wrong.served,wrong.served.recipes.find(recipe=>recipe.id===wrong.id),note);
  await page.close();return state;
}
const localOnly=route=>{const url=route.request().url(); if([fixture.base,fixture.billing_base,fixture.account_base,fixture.identity_origin].some(origin=>url.startsWith(origin+"/")))route.continue(); else {network.push(new URL(url).origin);route.abort();}};
try {
  browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,reducedMotion:"reduce"});
  await context.route("**/*",localOnly);
  const page=await context.newPage(); page.on("pageerror",error=>errors.push(safeError(error.message)));
  await page.goto(fixture.base+"/"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  check("public_landing_has_real_routes_and_configured_brand",(await page.title()).startsWith("Baltor |")&&await page.locator('[data-view="home"]').isVisible());
  check("all_four_persistent_intelligence_layers_are_visible",await page.locator("[data-intelligence-layer]").count()===4&&await page.getByRole("heading",{name:"Context Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"Code Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"Runtime History and Solution Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"User Feedback Intelligence",exact:true}).isVisible());
  check("homepage_leads_with_reusable_solutions_not_deployment",(await page.locator('[data-view="home"] h1').innerText()).includes("reusable solutions")&&!(await page.locator('[data-view="home"] h1').innerText()).toLowerCase().match(/local|harness|agent/)&&await page.locator('[data-view="home"] .boundary-figure').count()===0);
  check("homepage_explains_token_value_without_invented_savings",(await page.locator(".hero-value").innerText()).includes("token budget")&&(await page.locator(".benefit-limits").innerText()).includes("No percentage reduction"));
  check("light_is_default_even_when_operating_system_is_dark",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  await page.emulateMedia({colorScheme:"dark"});await page.reload();
  check("operating_system_does_not_override_explicit_light_default",await page.evaluate(()=>document.documentElement.dataset.theme==="light"&&getComputedStyle(document.body).backgroundColor==="rgb(255, 255, 255)"));
  await page.emulateMedia({colorScheme:"light"});
  check("all_five_owner_pain_points_are_present",JSON.stringify(await page.locator("[data-friction]").evaluateAll(items=>items.map(item=>item.dataset.friction).sort()))===JSON.stringify(["context","expertise","learning","model","reuse"]));
  check("optimization_message_does_not_guarantee_daily_improvement",(await page.locator(".optimization-callout").innerText()).includes("Model selection, context sizing, tool choice and code reuse")&&(await page.locator(".benefit-limits").innerText()).includes("guaranteed daily performance gain"));
  await page.locator("#hero-how-it-works").click();
  check("technical_layer_definitions_remain_in_documentation",(await page.locator('[data-view="docs"] [data-layer-notes]').textContent()).includes("not a fifth persistent layer")&&(await page.locator('[data-view="docs"] [data-layer-notes]').textContent()).includes("temporary note board"));
  const boundary=page.locator('[data-view="about"] .boundary-figure');
  check("hosted_service_and_local_execution_have_distinct_responsibilities",(await boundary.locator(".service-zone").innerText()).includes("Check your access")&&(await boundary.locator(".client-zone").innerText()).includes("Set the goal and limits")&&await boundary.locator(".boundary-zone").count()===2);
  check("client_server_exchange_names_sent_and_returned_data",(await boundary.locator(".boundary-exchange").innerText()).includes("Relevant help or a selected file")&&(await boundary.locator(".boundary-exchange").innerText()).includes("Matching results or the permitted download"));
  check("external_model_connection_is_separate_from_intelligence_service",(await boundary.locator(".provider-lane").innerText()).includes("Model keys stay in your environment"));
  check("benefits_are_explicit_without_invented_benchmark_numbers",await page.locator(".friction-grid article").count()===5&&!(await page.locator(".friction-section").innerText()).match(/\d+\s*%/));
  await boundary.screenshot({path:output.replace(/\.json$/,"-boundaries.png")});
  check("homepage_deep_link_opens_task_explorer",new URL(page.url()).pathname==="/how-it-works"&&new URL(page.url()).hash==="#task-breakdown"&&await page.locator("#task-breakdown").isVisible());
  const architectureRequests=[]; const requestListener=request=>architectureRequests.push(request.url()); page.on("request",requestListener);
  const expected=[['inspect','field-definitions.md','five minutes'],['decide','eligible-capabilities.json','two minutes'],['build','selected-normalizer.py','fifteen minutes'],['verify','import-verifier.py','no model requests']];
  for(const [id,file,limit] of expected){
    await page.click("#assignment-"+id);
    check("assignment_selects_its_own_context_"+id,(await page.locator("#assignment-materials").innerText()).includes(file)&&await page.locator("#assignment-"+id).getAttribute("aria-selected")==="true"&&(await page.locator("#assignment-contract").textContent()).includes(limit));
    check("public_step_avoids_internal_runtime_terms_"+id,!/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile|typed contract|governed|harness/i.test(await page.locator('[data-view="about"]').textContent()));
  }
  check("public_footer_has_no_engine_branding",!(await page.locator("footer").textContent()).includes("Loop Engine"));
  check("complete_runtime_definition_preserved_in_technical_docs",(await page.locator('[data-view="docs"] .complete-definition').textContent()).includes("A discrete cognitive or act step Loop node is an independently governed")&&(await page.locator('[data-view="docs"] .complete-definition').textContent()).includes("protection against duplicate delivery"));
  check("verifier_does_not_receive_builders_entire_context",!(await page.locator("#assignment-materials").innerText()).includes("selected-normalizer.py")&&(await page.locator("#assignment-withheld").innerText()).includes("Permission to change the candidate"));
  await page.locator("#assignment-verify").focus(); await page.keyboard.press("Home");
  check("assignment_tabs_support_keyboard_home",await page.locator("#assignment-inspect").getAttribute("aria-selected")==="true");
  await page.keyboard.press("ArrowRight"); check("assignment_tabs_support_keyboard_arrows",await page.locator("#assignment-decide").getAttribute("aria-selected")==="true");
  await page.keyboard.press("End"); check("assignment_tabs_support_keyboard_end",await page.locator("#assignment-verify").getAttribute("aria-selected")==="true");
  page.off("request",requestListener); check("illustrative_step_selection_launches_no_network_or_model_work",architectureRequests.length===0,{requests:architectureRequests.length});
  check("architecture_keeps_live_evidence_separate_from_illustration",(await page.locator('[data-view="about"]').innerText()).includes("not a recorded customer result")&&(await page.locator('[data-view="about"]').innerText()).includes("still being tested from start to finish")&&(await page.locator('[data-view="about"]').innerText()).includes("not established token savings or overnight task completion"));
  await page.locator("#task-breakdown").screenshot({path:output.replace(/\.json$/,"-task-desktop.png")});
  await page.setViewportSize({width:390,height:1000}); await page.click("#assignment-build");
  check("selected_assignment_has_no_mobile_overflow",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.locator("#task-breakdown").screenshot({path:output.replace(/\.json$/,"-task-mobile.png")});
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(fixture.base+"/signup");
  check("unfinished_signup_is_explicit_and_collects_no_email",await page.locator('[data-view="signup"]').isVisible()&&await page.locator('[data-view="signup"] form:visible').count()===0);
  await page.goto(fixture.base+"/app");
  check("anonymous_workspace_has_real_setup_and_no_active_search",await page.locator("#query").isDisabled()&&await page.locator("#workspace-access-link").isVisible());
  await page.goto(fixture.base+"/connect"); await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled);
  check("guided_setup_uses_current_origin_and_no_embedded_token",(await page.locator("#client-configuration").innerText()).includes(fixture.base+"/mcp")&&!(await page.locator("#client-configuration").innerText()).includes(fixture.token));
  check("anonymous_protocol_test_is_disabled",await page.locator("#test-protocol").isDisabled());
  await page.screenshot({path:output.replace(/\.json$/,"-connect-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:output.replace(/\.json$/,"-connect-mobile.png"),fullPage:true});await page.setViewportSize({width:1440,height:1000});
  await page.selectOption("#client-choice","opencode");
  const recipe=JSON.parse(await page.locator("#client-configuration").innerText());
  check("client_selection_changes_real_secret_free_configuration",recipe.mcp.baltor.url===fixture.base+"/mcp"&&recipe.mcp.baltor.oauth===false&&recipe.mcp.baltor.headers.Authorization==="Bearer {env:BALTOR_SERVICE_TOKEN}");
  /* Connection recipes: every reviewed recipe, the known-wrong records, the serving origins and the removed-guard controls. */
  const recipeContext=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
  await recipeContext.grantPermissions(["clipboard-read","clipboard-write"]);await recipeContext.route("**/*",localOnly);
  const variable=recipeRecord.credential_variable,plantedKey="le_"+randomBytes(32).toString("base64url"),otherOrigin=fixture.billing_base+"/mcp";
  check("no_key_check_separates_keys_from_variable_references",keyShaped(fixture.token)&&keyShaped("Bearer "+plantedKey)&&keyShaped("Bearer secret")&&!keyShaped("Bearer {env:"+variable+"}")&&!keyShaped("Bearer ${"+variable+"}")&&!keyShaped(variable));
  const {page:recipePage,state:recipeState}=await openConnect(recipeContext,fixture.base);
  check("connect_view_offers_the_three_reviewed_recipes",recipeRecord.recipes.length===3&&["codex","opencode","claude-code"].every(id=>recipeRecord.recipes.some(item=>item.id===id))&&JSON.stringify(await recipePage.locator("#client-choice option").evaluateAll(items=>items.map(item=>item.value)))===JSON.stringify(recipeRecord.recipes.map(item=>item.id)));
  const namedVariables=new Set();
  for(const item of recipeRecord.recipes)for(const word of (await checkShownRecipe(recipePage,fixture.base,recipeRecord,item,check)).match(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g)||[])namedVariables.add(word);
  check("every_recipe_and_the_token_instructions_name_one_variable",namedVariables.size===1&&namedVariables.has(variable)&&recipeRecord.recipes.every(item=>textLeaves(item.configuration).some(([,text])=>text.includes(variable))),{names:[...namedVariables]});
  const entryNames=(value,parent="",found=[])=>{if(value&&typeof value==="object"&&!Array.isArray(value)){if(typeof value.url==="string")found.push(parent);for(const [name,item] of Object.entries(value))entryNames(item,name,found);}return found;};
  check("every_recipe_names_the_same_server_entry",recipeRecord.recipes.every(item=>JSON.stringify(entryNames(item.configuration))===JSON.stringify(["baltor"])&&item.removal_note.includes("baltor")&&item.removal_note.includes(variable)));
  await recipePage.selectOption("#client-choice","claude-code");
  const claude=JSON.parse(await recipePage.locator("#client-configuration").innerText()).mcpServers.baltor;
  check("claude_code_recipe_is_a_project_file_with_an_environment_reference",claude.type==="http"&&claude.url===fixture.base+"/mcp"&&JSON.stringify(claude.headers)===JSON.stringify({Authorization:"Bearer ${"+variable+"}"})&&(await recipePage.locator("#configuration-location").innerText()).includes(".mcp.json")&&await recipePage.locator("#client-verify-command").innerText()==="claude mcp list");
  await recipePage.screenshot({path:output.replace(/\.json$/,"-connect-claude-code.png"),fullPage:true});
  await recipePage.selectOption("#client-choice","codex");
  const codexText=await recipePage.locator("#client-configuration").innerText();
  check("codex_recipe_is_a_table_that_names_the_variable",codexText.startsWith("[mcp_servers.baltor]\n")&&codexText.includes('bearer_token_env_var = "'+variable+'"')&&codexText.includes('url = "'+fixture.base+'/mcp"'));
  check("copying_a_recipe_stores_nothing_in_the_browser",await recipePage.evaluate(()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie==="")&&(await recipeContext.cookies()).length===0);
  const connectMarkup=await (await recipePage.request.get(fixture.base+"/connect")).text();
  check("connect_page_keeps_inline_code_forbidden",["default-src 'none'","script-src 'self'","style-src 'self'"].every(part=>recipeState.policy.includes(part))&&!recipeState.policy.includes("unsafe-inline")&&!/<style[\s>]|\sstyle\s*=|<script(?![^>]*\ssrc=)[^>]*>|\son[a-z]+\s*=/i.test(connectMarkup)&&await recipePage.evaluate(()=>window.policyViolations.length)===0,{policy:recipeState.policy});
  const fits=[];
  for(const item of recipeRecord.recipes){
    await recipePage.selectOption("#client-choice",item.id);await recipePage.setViewportSize({width:320,height:1000});
    fits.push(await recipePage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await recipePage.evaluate(()=>document.documentElement.style.fontSize="200%");
    fits.push(await recipePage.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await recipePage.evaluate(()=>document.documentElement.style.fontSize="");await recipePage.setViewportSize({width:1440,height:1000});
  }
  check("every_recipe_fits_a_small_screen_and_enlarged_text",fits.length===2*recipeRecord.recipes.length&&fits.every(Boolean),{fits});
  await recipePage.goto(fixture.base+"/");
  check("homepage_and_footer_use_plain_words",!internalTerms.test(await recipePage.locator('[data-view="home"]').innerText())&&!internalTerms.test(await recipePage.locator("footer").innerText()));
  await recipePage.close();
  const wrongCredentials=[
    {name:"recipe_with_embedded_key_is_refused_before_display",id:"claude-code",reason:"credential_rule",planted:plantedKey,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.headers.Authorization="Bearer "+plantedKey;})},
    {name:"recipe_with_key_in_place_of_the_variable_name_is_refused",id:"codex",reason:"credential_rule",planted:plantedKey,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.bearer_token_env_var=plantedKey;})},
    {name:"recipe_with_key_as_a_default_value_is_refused",id:"claude-code",reason:"credential_rule",planted:plantedKey,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.headers.Authorization="Bearer ${"+variable+":-"+plantedKey+"}";})},
    {name:"recipe_with_key_in_a_command_is_refused",id:"opencode",reason:"credential_rule",planted:plantedKey,served:changedRecipe("opencode",item=>{item.verification_command=variable+"="+plantedKey+" "+item.verification_command;})},
    {name:"recipe_with_short_literal_bearer_value_is_refused",id:"opencode",reason:"credential_rule",planted:"Bearer secret",served:changedRecipe("opencode",item=>{item.configuration.mcp.baltor.headers.Authorization="Bearer secret";})},
  ];
  const wrongAddresses=[
    {name:"recipe_with_fixed_address_is_refused_before_display",id:"codex",reason:"address_rule",planted:otherOrigin,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.url=otherOrigin;})},
    {name:"recipe_with_unknown_placeholder_is_refused",id:"claude-code",reason:"address_rule",planted:"{{ORIGIN}}",served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.url="{{ORIGIN}}/mcp";})},
  ];
  const unsupportedRecords=[
    {name:"older_recipe_record_version_is_refused",id:"codex",reason:"unsupported_record",planted:"website_client_recipes/v1",served:changedRecipe("codex",(_,record)=>{record.record_type="website_client_recipes/v1";})},
    {name:"recipe_without_revocation_steps_is_refused",id:"claude-code",reason:"unsupported_record",planted:"claude mcp list",served:changedRecipe("claude-code",item=>{delete item.removal_note;})},
    {name:"recipe_that_cannot_be_written_as_a_table_is_refused",id:"codex",reason:"unsupported_record",planted:"enabled = null",served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.enabled=null;})},
  ];
  for(const wrong of [...wrongCredentials,...wrongAddresses,...unsupportedRecords])await checkRefusedRecord(recipeContext,fixture.base,check,wrong);
  const wrongShown=JSON.stringify(withEndpoint(wrongCredentials[0].served.recipes.find(item=>item.id==="claude-code").configuration,fixture.base+"/mcp"),null,2);
  check("no_key_check_fails_for_a_recipe_with_an_embedded_key",keyShaped(wrongShown.replaceAll(fixture.base+"/mcp","").replaceAll(variable,""))&&wrongShown.includes(plantedKey));
  const followed=[];
  for(const origin of [fixture.billing_base,fixture.account_base]){
    const {page:other}=await openConnect(recipeContext,origin);
    for(const item of recipeRecord.recipes){
      await other.selectOption("#client-choice",item.id);
      const text=await other.locator("#client-configuration").evaluate(node=>node.textContent),value=item.format==="toml"?readToml(text):JSON.parse(text),targets=textLeaves(value).filter(([key])=>key==="url");
      followed.push(targets.length===1&&targets[0][1]===origin+"/mcp"&&!text.includes(fixture.base));
    }
    await other.close();
  }
  check("recipes_follow_the_origin_that_serves_the_page",followed.length===2*recipeRecord.recipes.length&&followed.every(Boolean),{origins:3,followed});
  /* Removed-guard controls. The served script is changed in memory only. Each control must make its named checks fail. */
  const refusedWithout=wrongRecords=>async(note,mutation)=>{const states=[];for(const wrong of wrongRecords)states.push(await checkRefusedRecord(recipeContext,fixture.base,note,wrong,mutation));return states;};
  const controls=[
    {name:"remove_recipe_credential_rule",find:'return "credential_rule";',required:[...wrongCredentials.map(wrong=>wrong.name),"recipe_contains_no_key_claude-code","recipe_contains_no_key_codex","recipe_contains_no_key_opencode"],run:refusedWithout(wrongCredentials)},
    {name:"remove_recipe_address_rule",find:'return "address_rule";',required:[...wrongAddresses.map(wrong=>wrong.name),"recipe_uses_current_origin_codex","recipe_uses_current_origin_claude-code"],run:refusedWithout(wrongAddresses)},
    {name:"accept_unsupported_recipe_records",find:'return "unsupported_record";',required:[...unsupportedRecords.map(wrong=>wrong.name),"recipe_states_how_to_check_and_revoke_claude-code"],run:refusedWithout(unsupportedRecords)},
    {name:"copy_other_text_than_shown",find:'writeText($("client-configuration").textContent)',replacement:'writeText("")',required:recipeRecord.recipes.map(item=>"recipe_copy_matches_displayed_text_"+item.id),run:async(note,mutation)=>{const {page:changed,state}=await openConnect(recipeContext,fixture.base,{mutation});for(const item of recipeRecord.recipes)await checkShownRecipe(changed,fixture.base,recipeRecord,item,note);await changed.close();return [state];}},
  ];
  for(const control of controls){
    const failed=new Set();let applied=false,problem="";
    try{const states=await control.run((name,passed)=>{if(passed!==true)failed.add(name);},{find:control.find,replacement:control.replacement??"void 0;"});applied=states.length>0&&states.every(state=>state.applied);}catch(error){problem=safeError(error);}
    const detected=applied&&!problem&&control.required.every(name=>failed.has(name));
    mutants.push({name:control.name,applied,detected,required_checks:control.required,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  await recipeContext.close();
  await page.locator('[data-view="setup"] a[data-after-login]').click();
  await page.fill("#access-token","WRONG_LOCAL_TEST_KEY"); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-message").textContent.includes("refused"));
  check("wrong_key_does_not_enter_the_workspace",await page.locator("#query").isDisabled()&&await page.locator("#access-token").inputValue()==="");
  await page.fill("#access-token",fixture.token); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  check("real_durable_tenant_authentication_reaches_the_workspace",(await page.locator("#identity-facts").innerText()).includes("alpha")&&await page.locator("#access-token").inputValue()==="");
  check("credentials_are_not_persisted_in_browser_storage",await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
  check("sign_in_returns_to_requested_setup_page",new URL(page.url()).pathname==="/connect");
  const protocolMethods=[]; const trackProtocol=request=>{if(new URL(request.url()).pathname==="/mcp")protocolMethods.push(request.postDataJSON()?.method);};page.on("request",trackProtocol);
  await page.click("#test-protocol"); await page.waitForFunction(()=>!document.querySelector("#test-protocol").disabled);
  check("protocol_connection_check_reports_actual_success",(await page.locator("#protocol-result").innerText()).includes("Service connection passed"),{message:await page.locator("#protocol-result").innerText()});
  check("browser_runs_real_initialize_notification_and_tools_list",JSON.stringify(protocolMethods)===JSON.stringify(["initialize","notifications/initialized","tools/list"])&&await page.locator("#protocol-tools li").count()===5);
  check("browser_check_does_not_claim_native_harness_qualification",(await page.locator("#protocol-result").innerText()).includes("Native client loading is not tested"));
  await page.route("**/mcp",async route=>{const body=route.request().postDataJSON();if(body?.method==="initialize")await route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({jsonrpc:"2.0",id:"wrong-request",result:{protocolVersion:"2025-11-25"}})});else await route.continue();});
  await page.click("#test-protocol");await page.waitForFunction(()=>document.querySelector("#protocol-result").textContent.includes("did not match"));
  check("mismatched_protocol_response_never_becomes_success",await page.locator("#protocol-tools li").count()===0&&!(await page.locator("#protocol-result").innerText()).includes("passed"));await page.unroute("**/mcp");page.off("request",trackProtocol);
  await page.locator('footer a[data-page="examples"]').click(); await page.click("#try-example");
  check("first_example_prepares_query_without_submitting",new URL(page.url()).pathname==="/app"&&await page.inputValue("#query")==="review inputs"&&await page.locator("#results .result").count()===0);
  await page.fill("#query","Alpha"); await page.click("#search-button"); await page.waitForFunction(()=>document.querySelector("#search-message").textContent.includes("No bodies loaded"));
  check("browser_search_reaches_the_real_authorized_retriever",await page.locator(".result").count()===2&&!(await page.locator("#results").innerText()).includes("skill.beta"));
  const downloadEvent=page.waitForEvent("download"); await page.locator(".result button").first().click(); const download=await downloadEvent;
  const stream=await download.createReadStream(); const chunks=[]; for await (const chunk of stream) chunks.push(chunk);
  check("browser_download_checks_actual_bytes_against_the_selected_digest",Buffer.concat(chunks).toString()==="APPROVED_ALPHA_BODY"&&(await page.locator(".result").first().innerText()).includes("Digest verified"));
  await page.locator('header a[data-page="account"]').click();
  check("account_route_retains_same_in_memory_connection",(await page.locator("#account-facts").innerText()).includes("alpha"));
  await page.click("#refresh-usage"); await page.waitForFunction(()=>document.querySelector("#usage").textContent.includes("record_type"));
  check("usage_is_read_from_durable_service_state",JSON.parse(await page.locator("#usage").textContent()).records===1);
  await page.click("#refresh-billing"); await page.waitForFunction(()=>document.querySelector("#billing").textContent.includes("unavailable"));
  check("unconfigured_billing_is_not_a_fake_purchase_flow",await page.locator("#billing button").count()===0);
  await page.locator('header a[data-page="workspace"]').click();
  await page.route("**/api/v1/retrieval",async route=>{const response=await route.fetch(); const body=await response.json(); body.result.hits[0].purpose='<img src=x onerror="window.poisoned=true">'; await route.fulfill({response,json:body});});
  await page.click("#search-button"); await page.waitForFunction(()=>document.querySelector("#results").textContent.includes("onerror"));
  check("retrieved_metadata_is_text_not_executable_HTML",await page.locator("#results img").count()===0&&await page.evaluate(()=>window.poisoned!==true));
  await page.unroute("**/api/v1/retrieval");
  await page.route("**/api/v1/download",async route=>{const response=await route.fetch(); await route.fulfill({response,body:"CORRUPTED_LOCAL_FIXTURE"});});
  await page.locator(".result button").first().click(); await page.waitForFunction(()=>document.querySelector(".result").textContent.includes("Nothing was saved"));
  check("changed_download_is_refused_by_the_browser",(await page.locator(".result").first().innerText()).includes("do not match")); await page.unroute("**/api/v1/download");
  for(const width of [1440,820,390,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/","/login","/signup","/account","/admin","/app","/docs","/how-it-works","/connect","/examples","/security"]){
      await page.goto(fixture.base+path);
      const measurement=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(x=>!x.hidden).length}));
      check(`responsive_${width}_${path}`,!measurement.overflow&&measurement.views===1,measurement);
    }
  }
  for(const width of [1440,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/","/how-it-works","/connect","/examples","/security"]){
      await page.goto(fixture.base+path); await page.evaluate(()=>document.documentElement.style.fontSize="200%");
      const enlarged=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,items:[...document.querySelectorAll("body *")].filter(item=>{const box=item.getBoundingClientRect();return box.width&&box.right>innerWidth+1;}).slice(0,12).map(item=>({tag:item.tagName,id:item.id,className:String(item.className)}))}));
      check(`enlarged_text_${width}_${path}`,!enlarged.overflow,enlarged);
      await page.evaluate(()=>document.documentElement.style.fontSize="");
    }
  }
  await page.goto(fixture.base+"/login"); await page.fill("#access-token",fixture.token); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await page.fill("#query","Alpha"); await page.click("#search-button"); await page.waitForSelector(".result");
  await page.locator('header a[data-page="login"]').click(); await page.click("#disconnect");
  check("disconnect_clears_identity_results_and_controls",await page.locator(".result").count()===0&&await page.locator("#query").isDisabled()&&await page.locator("#identity-facts").innerText()==="");
  await page.goto(fixture.billing_base+"/login"); await page.fill("#access-token",fixture.billing_token); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await page.locator('header a[data-page="account"]').click();
  await page.click("#refresh-billing"); await page.waitForSelector("#billing button");
  check("configured_billing_offers_only_host_defined_plans",await page.locator("#billing button").count()===3&&(await page.locator("#billing").innerText()).includes("Basic service"));
  await page.getByRole("button",{name:"Choose Basic service",exact:true}).click(); await page.waitForSelector("#billing-message a");
  check("checkout_uses_the_real_domain_with_a_local_provider_fixture",(await page.locator("#billing-message a").getAttribute("href")).startsWith("https://checkout.stripe.com/"));
  await page.getByRole("button",{name:"Manage subscription",exact:true}).click(); await page.waitForFunction(()=>document.querySelector("#billing-message a")?.textContent.includes("portal"));
  check("portal_uses_the_real_domain_without_navigating_to_a_provider",(await page.locator("#billing-message a").getAttribute("href")).startsWith("https://billing.stripe.com/"));
  await page.goto(fixture.base+"/login"); await page.fill("#access-token",fixture.admin_token); await page.click("#connect-button"); await page.waitForSelector("#admin-controls:not([hidden])");
  check("email_free_administrator_login_reaches_dashboard",new URL(page.url()).pathname==="/admin"&&await page.locator("#issue-access").isVisible());
  await page.fill("#token-label","Browser harness trial"); await page.fill("#token-hours","1"); await page.click("#issue-access-button"); await page.waitForSelector("#issued-access:not([hidden])");
  const generated=await page.inputValue("#issued-token"); secrets.push(generated);
  const generatedSession=await page.request.get(fixture.base+"/api/v1/session",{headers:{Authorization:"Bearer "+generated}});
  check("dashboard_creates_real_usable_test_token",generatedSession.status()===200&&(await page.locator("#access-list").innerText()).includes("Browser harness trial"));
  check("generated_secret_not_in_page_text_or_browser_storage",!(await page.locator("body").innerText()).includes(generated)&&await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
  await page.click("#clear-token"); check("one_time_token_clear_removes_secret",await page.inputValue("#issued-token")==="");
  page.once("dialog",dialog=>dialog.accept()); await page.getByRole("button",{name:"Revoke Browser harness trial",exact:true}).click(); await page.waitForFunction(()=>document.querySelector("#admin-message").textContent==="Token revoked.");
  const revokedSession=await page.request.get(fixture.base+"/api/v1/session",{headers:{Authorization:"Bearer "+generated}});
  check("dashboard_revocation_refuses_next_service_call",revokedSession.status()===401&&(await page.locator("#access-list").innerText()).includes("revoked"));
  await page.setViewportSize({width:1440,height:1000}); await page.screenshot({path:output.replace(/\.json$/,"-admin.png"),fullPage:true});
  let releasePublic;const publicGate=new Promise(resolve=>{releasePublic=resolve;});let heldPublic=0;
  await page.route(/\/(?:api\/v1\/capabilities|assets\/client-recipes\.json)$/,async route=>{heldPublic++;await publicGate;await route.continue().catch(()=>{});});
  await page.goto(fixture.base+"/login");await page.waitForFunction(()=>document.querySelector("#connect-button")!==null);
  await page.fill("#access-token",fixture.token);await page.click("#connect-button");await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  releasePublic();await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available")||document.querySelector("#service-status").textContent.includes("Service unavailable"));
  await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled||document.querySelector("#setup-message").textContent.includes("could not"));
  check("sign_in_during_public_configuration_loading_preserves_setup",heldPublic===2&&!await page.locator("#client-choice").isDisabled()&&!await page.locator("#test-protocol").isDisabled(),{heldPublic});
  await page.unroute(/\/(?:api\/v1\/capabilities|assets\/client-recipes\.json)$/);
  let releasePrivate,heldPrivate=false;const privateGate=new Promise(resolve=>{releasePrivate=resolve;});
  await page.route("**/mcp",async route=>{if(route.request().postDataJSON()?.method==="tools/list"){heldPrivate=true;await privateGate;}await route.continue().catch(()=>{});});
  await page.locator('header a[data-page="setup"]').click();await page.click("#test-protocol");
  await new Promise((resolve,reject)=>{const deadline=setTimeout(()=>{clearInterval(poll);reject(new Error("No held authenticated request"));},5000);const poll=setInterval(()=>{if(heldPrivate){clearInterval(poll);clearTimeout(deadline);resolve();}},10);});
  const aborted=page.waitForEvent("requestfailed",{predicate:request=>new URL(request.url()).pathname==="/mcp"});
  await page.locator('header a[data-page="login"]').click();await page.click("#disconnect");await aborted;releasePrivate();
  check("sign_out_still_aborts_credential_bound_protocol_requests",await page.locator("#protocol-tools li").count()===0&&await page.locator("#test-protocol").isDisabled()&&(await page.locator("#protocol-result").innerText()).startsWith("Not tested"));
  await page.unroute("**/mcp");
  await page.route(fixture.identity_origin+"/auth/v1/token**",route=>route.fulfill({status:200,contentType:"application/json",headers:{"Access-Control-Allow-Origin":fixture.account_base,"Access-Control-Allow-Headers":"*","Access-Control-Allow-Methods":"POST, OPTIONS"},body:JSON.stringify({access_token:fixture.identity_token,refresh_token:"local-fixture-refresh",expires_in:1800,token_type:"bearer",user:fixture.identity_user})}));
  await page.route(fixture.identity_origin+"/auth/v1/logout**",route=>route.fulfill({status:204,headers:{"Access-Control-Allow-Origin":fixture.account_base,"Access-Control-Allow-Headers":"*"}}));
  await page.goto(fixture.account_base+"/login");await page.waitForSelector("#email-login:not([hidden])");
  await page.fill("#login-email",fixture.identity_user.email);await page.fill("#login-password","local-browser-fixture-password");await page.click("#email-login-button");
  await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await page.locator('header a[data-page="account"]').click();await page.click("#refresh-client-access");
  await page.waitForSelector("#client-access-controls:not([hidden])");
  check("verified_customer_can_open_personal_token_controls",await page.locator("#create-client-token").isEnabled()&&await page.locator("#client-token-scopes input").count()===3);
  await page.fill("#client-token-label","My laptop");await page.fill("#client-token-minutes","60");await page.click("#create-client-token");
  await page.waitForSelector("#client-issued:not([hidden])");
  const personalToken=await page.inputValue("#client-issued-token");secrets.push(personalToken);
  const personalSession=await page.request.get(fixture.account_base+"/api/v1/session",{headers:{Authorization:"Bearer "+personalToken}});
  check("customer_dashboard_creates_real_personal_access",personalSession.status()===200&&(await personalSession.json()).result.principal.tenant_id.startsWith("browser-customers."));
  check("customer_token_secret_stays_out_of_text_and_browser_storage",!(await page.locator("body").innerText()).includes(personalToken)&&await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0));
  check("customer_token_cannot_manage_more_credentials",(await page.request.get(fixture.account_base+"/api/v1/account/access",{headers:{Authorization:"Bearer "+personalToken}})).status()===403);
  await page.click("#clear-client-token");check("customer_can_clear_the_one_time_secret",await page.inputValue("#client-issued-token")==="");
  page.once("dialog",dialog=>dialog.accept());await page.getByRole("button",{name:"Revoke My laptop",exact:true}).click();
  await page.waitForFunction(()=>document.querySelector("#client-access-list").textContent.includes("revoked"));
  check("customer_dashboard_revokes_real_client_access",(await page.request.get(fixture.account_base+"/api/v1/session",{headers:{Authorization:"Bearer "+personalToken}})).status()===401);
  for(const width of [1440,390,320]){
    await page.setViewportSize({width,height:1000});
    check("customer_controls_fit_"+width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  }
  await page.evaluate(()=>document.documentElement.style.fontSize="200%");
  check("customer_controls_support_enlarged_text",await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
  await page.evaluate(()=>document.documentElement.style.fontSize="");
  let releaseCustomer,customerResponseHeld=false;const customerGate=new Promise(resolve=>{releaseCustomer=resolve;});
  await page.route("**/api/v1/account/access",async route=>{if(route.request().method()==="GET"){const response=await route.fetch();customerResponseHeld=true;await customerGate;await route.fulfill({response}).catch(()=>{});}else await route.continue();});
  await page.click("#refresh-client-access");
  await new Promise((resolve,reject)=>{const end=setTimeout(()=>{clearInterval(poll);reject(new Error("Customer response was not held"));},5000);const poll=setInterval(()=>{if(customerResponseHeld){clearInterval(poll);clearTimeout(end);resolve();}},10);});
  await page.locator('header a[data-page="login"]').click();await page.click("#disconnect");releaseCustomer();
  check("customer_sign_out_clears_tokens_before_delayed_reply",await page.locator("#client-access-controls").isHidden()&&await page.inputValue("#client-issued-token")===""&&await page.locator("#refresh-client-access").isDisabled());
  await page.unroute("**/api/v1/account/access");
  await page.goto(fixture.base+"/"); await page.setViewportSize({width:1440,height:1000});
  await page.screenshot({path:output.replace(/\.json$/,"-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:1000}); await page.click("#theme");
  check("dark_appearance_remains_an_explicit_option",await page.evaluate(()=>document.documentElement.dataset.theme==="dark"));
  await page.screenshot({path:output.replace(/\.json$/,"-mobile-dark.png"),fullPage:true});
  check("no_browser_runtime_errors",errors.length===0,{errors});
  check("no_external_provider_requests",network.length===0,{network});
}catch(error){check("browser_journey_completed",false,{error:safeError(error)});}
finally{
  if(browser)await browser.close(); child.stdin.end("\n");
  await new Promise(resolve=>{if(child.exitCode!==null)return resolve();const timer=setTimeout(()=>{child.kill("SIGTERM");resolve();},5000);child.once("exit",()=>{clearTimeout(timer);resolve();});}); lines.close();
}
const paths=[...['http.py','records.py','access.py','access_checks.py','http_entrypoint.py','runtime.py','browser_identity.py','browser_identity_checks.py'].map(name=>"src/loop_engine/core/service_runtime/"+name),...['index.html','service.css','service.js','client-access.js','architecture-story.js','architecture.css','client-recipes.json'].map(name=>"src/loop_engine/core/service_runtime/web_assets/"+name)];
const result={record_type:"service_workspace_browser_checks/v1",scope:"real browser and loopback service; provider fixtures only",external_provider_calls:0,checks,passed:checks.filter(x=>x.passed).length,total:checks.length,mutants,mutants_detected:mutants.filter(x=>x.detected).length,all_passed:checks.every(x=>x.passed)&&mutants.every(x=>x.detected),source_sha256:Object.fromEntries(paths.map(path=>[path,createHash("sha256").update(readFileSync(resolve(root,path))).digest("hex")]))};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"}); console.log(JSON.stringify({passed:result.passed,total:result.total,mutants_detected:result.mutants_detected,mutants:mutants.length,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed),output})); process.exitCode=result.all_passed?0:1;
