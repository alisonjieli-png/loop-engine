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
for (const path of [output,...["-desktop.png","-mobile-dark.png","-admin.png","-task-desktop.png","-task-mobile.png","-boundaries.png","-connect-desktop.png","-connect-mobile.png","-connect-claude-code.png","-pricing-desktop.png","-pricing-mobile.png","-privacy-desktop.png","-privacy-mobile.png","-browse-desktop.png","-browse-mobile.png"].map(suffix=>output.replace(/\.json$/,suffix))]) {
  if (existsSync(path)) throw new Error("Refusing to overwrite an existing browser evidence artifact: " + path);
}
/* Connection recipes. The reviewed record is read from the source tree before any process starts, so the page is compared with the record and not with itself. */
const recipeRecord=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/client-recipes.json"),"utf8"));
/* The catalogue browser is read from the source tree as well, and a named check compares it with the
   bytes the service serves. Every ordinary page in this run loads the module from the service itself.
   A removed-guard control, and only such a control, answers that one address with changed bytes, in
   memory and never in the source file. */
const browseSource=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/catalogue-browser.js"),"utf8");
const routeBrowseAsset=(target,mutation)=>{
  const state={applied:false,errors:[]};
  if(!mutation)return state;
  target.route("**/assets/catalogue-browser.js",route=>{
    const body=browseSource.split(mutation.find).join(mutation.replacement);
    state.applied=body!==browseSource;
    route.fulfill({status:200,contentType:"text/javascript",body});
  });
  return state;
};
/* A one-shot hold on the measurement of downloaded bytes, installed only in the checks that name it.
   The page, the service, the bytes and the digest stay real; only the moment the measurement finishes is
   held, so a sign-out can land inside the window the guard in fetchBody defends. Nothing else changes. */
const holdDigestScript=()=>{
  const measure=crypto.subtle.digest.bind(crypto.subtle);
  let release=null;
  window.__digestArmed=false;window.__digestHeld=false;
  window.__armDigestHold=()=>{window.__digestArmed=true;window.__digestHeld=false;};
  window.__releaseDigest=()=>{const go=release;release=null;if(go)go();};
  crypto.subtle.digest=async (...given)=>{
    const value=await measure(...given);
    if(window.__digestArmed){window.__digestArmed=false;window.__digestHeld=true;await new Promise(resolve=>{release=resolve;});}
    return value;};
};
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
from loop_engine.core.service_runtime.waitlist import ServiceWaitlist,WaitlistPolicy
from loop_engine.core.service_runtime.records import ACCESS_MANAGE_SCOPE,TenantKeyIssue,TenantRegistration
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft,item_from_body
from loop_engine.core.provisioning_server import ProvisioningGrant,ProvisioningItemBinding
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
with ExitStack() as stack:
    root=Path(stack.enter_context(TemporaryDirectory(prefix="service-browser-")))
    (root/"intelligence").mkdir(); (root/"billing").mkdir(); (root/"accounts").mkdir(); (root/"signups").mkdir(); (root/"browse").mkdir()
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
    account.runtime.register_tenant(TenantRegistration("operator","operator:private",(ACCESS_MANAGE_SCOPE,)))
    account_operator=account.runtime.issue_key(TenantKeyIssue("operator","browser waiting list operator"))
    waiting=ServiceWaitlist(account.runtime,WaitlistPolicy(writes_authorized=True,accepted_for_each_source=3))
    account_base,_=stack.enter_context(running_http(account,application_factory=lambda config:ServiceHttpApplication(account.runtime,account.provisioning,config,browser_identity=identity,client_access=manager,waitlist=waiting),display_name="Baltor"))
    # A fourth real service whose own configuration opens email sign-up, so the page is compared with a service that reports registration, not with a rewritten reply.
    signups=HttpDomainFixture(root/"signups",operator_access=False)
    signup_identity=BrowserIdentityAdapter(signups.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-signups",registration_enabled=True,email_signup_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",starter_bindings=(signups.bindings["skill.alpha"],),transport=lambda _:user)
    signup_base,_=stack.enter_context(running_http(signups,application_factory=lambda config:ServiceHttpApplication(signups.runtime,signups.provisioning,config,browser_identity=signup_identity),display_name="Baltor"))
    # A fifth real service whose catalogue spans the persistent groups, so browsing is compared with a real
    # reply from a real service. One of the four groups is left empty on purpose, one item is granted
    # without its body, one item names no licence, and two items name the development tool they were
    # written for. One item declares an effect. A browser holds no authority to run anything, so the real
    # service withholds that item from every reply and the page must say so without blaming a filter.
    browse=HttpDomainFixture(root/"browse")
    published=[
        (HarnessIntelligenceDraft("context.review","skill","Review the supplied inputs before work starts","context_intelligence","fixture:context.review/v1","MIT",(),("claude-code",)),"CONTEXT_REVIEW_BODY",True),
        (HarnessIntelligenceDraft("context.brief","instruction_file","Write the brief for one step","context_intelligence","fixture:context.brief/v1","CC-BY-4.0"),"CONTEXT_BRIEF_BODY",True),
        (HarnessIntelligenceDraft("code.normalise","reusable_code","Normalise a supplied table of values","code_intelligence","fixture:code.normalise/v1","Apache-2.0",(),("codex",)),"CODE_NORMALISE_BODY",True),
        (HarnessIntelligenceDraft("code.verify","tool","Check an import against its declared contract","code_intelligence","fixture:code.verify/v1","MIT"),"CODE_VERIFY_BODY",False),
        (HarnessIntelligenceDraft("history.retry","instruction_file","What an earlier attempt at this task did","runtime_history_solution_intelligence","fixture:history.retry/v1","MIT"),"HISTORY_RETRY_BODY",True),
        (HarnessIntelligenceDraft("local.notes","instruction_file","Notes your own setup already holds","harness_local","fixture:local.notes/v1","",(),(),"metadata_only","installed"),"LOCAL_NOTES_BODY",True),
        (HarnessIntelligenceDraft("code.deploy","tool","Start a reviewed deployment command","code_intelligence","fixture:code.deploy/v1","MIT",("spawns_process",)),"CODE_DEPLOY_BODY",True)]
    for draft,body,_allowed in published:
        item=item_from_body(draft,body)
        browse.catalogue.register(item); browse.bodies[item.identity]=body
        browse.bindings[item.identity]=ProvisioningItemBinding.from_item(item)
    browse.runtime.set_grants("alpha",tuple(ProvisioningGrant("alpha",browse.bindings[draft.identity],allowed) for draft,_body,allowed in published))
    browse_base,_=stack.enter_context(running_http(browse,display_name="Baltor"))
    print(json.dumps({"base":base,"token":held.keys["alpha"].key,"admin_token":held.admin_key.key,"billing_base":billing_base,"billing_token":billing.keys["alpha"].key,"account_base":account_base,"signup_base":signup_base,"browse_base":browse_base,"browse_token":browse.keys["alpha"].key,"identity_origin":provider,"identity_token":identity_token,"identity_user":user,"account_admin_token":account_operator.key}),flush=True)
    sys.stdin.readline()
`;
const child=spawn(resolve(root,".venv/bin/python"),["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:"src"},stdio:["pipe","pipe","pipe"]});
const lines=createInterface({input:child.stdout});
const fixture=await new Promise((resolve,reject)=>{ const timer=setTimeout(()=>reject(new Error("Fixture startup deadline")),15000); lines.once("line",line=>{clearTimeout(timer);resolve(JSON.parse(line));}); child.once("exit",code=>{clearTimeout(timer);reject(new Error("Fixture stopped before startup: "+code));}); });
const checks=[],errors=[],network=[]; let browser;
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const secrets=[fixture.token,fixture.billing_token,fixture.admin_token,fixture.browse_token,fixture.identity_token,fixture.account_admin_token];
const safeError=error=>secrets.reduce((text,secret)=>text.replaceAll(secret,"[redacted]"),String(error));
const endpointMark="{{ENDPOINT}}",mutants=[];
const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
/* Words a customer page may never carry. The first set is the runtime vocabulary, which belongs in the Documentation
   view and in the repository. The second set describes the product as a trial, which the owner retired: who may create
   an account is a matter of configuration, not of copy. Each rule is checked against a known-wrong page of its own. */
const publicVocabulary=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profiles?|\bPractitioner\b/i;
/* The retired set names all four phrases the style guide retires, so a page that never writes pilot or beta but still
   offers "early access" is reported. The hosted check reads the deployed pages with the same rule, and a copy that
   drifts between the two is a named failure below rather than a silent disagreement. */
const retiredAccessWords=/\bpilots?\b|\bbetas?\b|early access/i;
/* The six benefits. The titles, the detail sentence that proves the detail was rendered, and the state readers used by
   the interaction checks and by their removed-guard controls. */
const benefitNames=["material","reuse","model","export","review","resume"];
const benefitTitles=["Each step gets the material it needs","Reuse code instead of writing it again","Not every step needs a large model","Solutions you can run without us","A failed check is examined, not obeyed","Work that can stop and start again"];
const benefitSentences=["A search returns short references, not whole files.","Before a step writes new code, it can look for code that already does the job","Every model route says what kind of model it is","it can be written out as an installable package","A check can be wrong as well as the work it checks.","Long work gets interrupted"];
const shownBenefits=target=>target.locator("[data-benefit]").evaluateAll(items=>items.filter(item=>getComputedStyle(item.querySelector("[data-benefit-detail]")).display!=="none").map(item=>item.dataset.benefit));
const expandedBenefits=target=>target.locator("[data-benefit-title]").evaluateAll(items=>items.filter(item=>item.getAttribute("aria-expanded")==="true").map(item=>item.dataset.benefitTitle));
const only=name=>JSON.stringify([name]);
/* Hovering, keyboard focus and a press must each reveal one benefit and close the others. A touch screen and a
   keyboard therefore reach the same detail that a mouse reaches. Every rule here has a removed-guard control below. */
async function checkBenefitList(opened,note){
  const shownTitles=await opened.locator("[data-benefit-title] .benefit-name").allInnerTexts();
  note("homepage_lists_six_benefits_with_their_titles",JSON.stringify(shownTitles)===JSON.stringify(benefitTitles),{titles:shownTitles});
  /* A press. The event is sent straight to the title, so the pointer never moves and the focus never changes, and this
     measures the press by itself rather than the hover and the focus that a real click also performs. The order runs
     backwards from the benefit the page opens first, so the first press has to change something. */
  const pressed=[];
  for(const name of [...benefitNames].reverse()){
    await opened.locator('[data-benefit-title="'+name+'"]').dispatchEvent("click");
    pressed.push({name,shown:await shownBenefits(opened),expanded:await expandedBenefits(opened),detail:await opened.locator('[data-benefit-detail="'+name+'"]').innerText()});
  }
  note("pressing_a_benefit_shows_only_its_own_detail",pressed.length===6&&pressed.every(item=>JSON.stringify(item.shown)===only(item.name)&&JSON.stringify(item.expanded)===only(item.name)&&item.detail.includes(benefitSentences[benefitNames.indexOf(item.name)])),{pressed:pressed.map(item=>({name:item.name,shown:item.shown}))});
  /* Keyboard alone. The last benefit is opened first, so moving focus to the first one has to change something, and
     the rest are reached with the Tab key and nothing else. */
  const keyboard=[];
  await opened.locator('[data-benefit-title="'+benefitNames[benefitNames.length-1]+'"]').dispatchEvent("click");
  await opened.locator('[data-benefit-title="'+benefitNames[0]+'"]').focus();
  for(const name of benefitNames){
    keyboard.push({name,focused:await opened.evaluate(()=>document.activeElement?.dataset.benefitTitle||""),shown:await shownBenefits(opened)});
    await opened.keyboard.press("Tab");
  }
  note("keyboard_focus_alone_opens_each_benefit",keyboard.length===6&&keyboard.every(item=>item.focused===item.name&&JSON.stringify(item.shown)===only(item.name)),{keyboard});
  /* Pointing at one. The keyboard pass left the last benefit open, so pointing at the first has to change something. */
  const hovered=[];
  for(const name of benefitNames){
    await opened.locator('[data-benefit="'+name+'"]').hover();
    hovered.push({name,shown:await shownBenefits(opened)});
  }
  note("pointing_at_a_benefit_opens_it",hovered.length===6&&hovered.every(item=>JSON.stringify(item.shown)===only(item.name)),{hovered});
  const wiring=await opened.locator("[data-benefit]").evaluateAll(items=>items.map(item=>{
    const title=item.querySelector("[data-benefit-title]"),detail=item.querySelector("[data-benefit-detail]");
    return {name:item.dataset.benefit,controls:title.getAttribute("aria-controls"),detailId:detail.id,labelled:detail.getAttribute("aria-labelledby"),titleId:title.id,
      role:detail.getAttribute("role"),expanded:title.getAttribute("aria-expanded"),type:title.getAttribute("type"),heading:title.parentElement.tagName};}));
  note("every_benefit_title_is_a_button_that_names_its_own_detail",wiring.length===6&&wiring.every(item=>item.controls===item.detailId&&item.labelled===item.titleId&&item.role==="region"&&item.type==="button"&&item.heading==="H3"&&["true","false"].includes(item.expanded)),{wiring});
}
/* One call to action. The owner, September 22, 2026: "get started and join the waiting list are redundant". Every link or
   button that starts the access journey says "Get started" and opens the one Get started page. That page leads with the one
   action the service reports: account creation, the invitation request form, or the plain way to reach the operator. The
   labels the owner called redundant are reported anywhere. The invitation request is offered only by the form that leads the
   Get started page. Account creation is offered only while the service reports registration open, and then only on the Get
   started page and the account page. Each rule has a known-wrong page of its own in the journey below. The readers return
   empty values for a missing element, so a page without the new parts fails these checks by name instead of stopping. */
const getStartedLabel="Get started",getStartedPath="/connect",getStartedAddresses=["/connect","/get-started","/waitlist"];
const redundantAccessLabel=/join the waiting list|request access|early access/i,invitationAccessLabel=/ask for an invitation/i,creationAccessLabel=/create (?:your )?account|\bsign up\b/i;
/* The public pages a visitor can open without signing in. Each is scanned on three real services below. */
const accessJourneyPaths=["/","/pricing","/how-it-works","/connect","/signup","/examples","/security","/docs","/privacy","/login"];
const waitingNote="Accounts open in small groups. Get started to ask for an invitation; a person reads every request.";
const openNote="Account creation is open. Get started to create your account; search is free.";
const publicActions=target=>target.evaluate(()=>{
  const lead=document.getElementById("start-access"),shown=node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden";
  return [...document.querySelectorAll("header a, header button, footer a, [data-view]:not([hidden]) a, [data-view]:not([hidden]) button")].filter(shown)
    .map(node=>({id:node.id,text:node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),href:node.getAttribute("href")||"",
      lead:Boolean(lead&&lead.contains(node)),account:Boolean(node.closest('[data-view="signup"]'))}));
});
const accessActionProblems=(actions,registrationOpen)=>[
  ...actions.filter(action=>getStartedAddresses.includes(action.href.split("#")[0])&&action.text!==getStartedLabel).map(action=>"an action that opens the Get started page says "+JSON.stringify(action.text)),
  ...actions.filter(action=>action.text===getStartedLabel&&action.href!==getStartedPath).map(action=>"a Get started action opens "+JSON.stringify(action.href)),
  ...actions.filter(action=>redundantAccessLabel.test(action.text)).map(action=>"a second label for the same journey: "+JSON.stringify(action.text)),
  ...actions.filter(action=>invitationAccessLabel.test(action.text)&&!action.lead).map(action=>"an invitation request outside the Get started page: "+JSON.stringify(action.text)),
  ...actions.filter(action=>creationAccessLabel.test(action.text)&&(!registrationOpen||!(action.lead||action.account))).map(action=>(registrationOpen?"account creation offered outside the Get started and account pages: ":"account creation offered while registration is closed: ")+JSON.stringify(action.text))];
/* The Get started page leads with one panel: "register", "invite" or "operator". The reader says which panel is shown, whether
   the invitation form and the account action can be seen, and whether the panel is the first thing under the page heading. */
const startLead=target=>target.evaluate(()=>{
  const lead=document.getElementById("start-access"),seen=id=>{const node=document.getElementById(id);return Boolean(node&&node.getClientRects().length>0);};
  return {state:lead?.dataset.startAccess||"",shown:[...document.querySelectorAll("[data-start-state]")].filter(panel=>!panel.hidden).map(panel=>panel.dataset.startState),
    form:seen("waitlist-form"),register:seen("start-register"),signIn:seen("start-sign-in"),
    leads:Boolean(lead&&lead.parentElement?.dataset.view==="setup"&&lead.previousElementSibling?.classList.contains("page-heading"))};
});
const sameLead=(lead,state)=>lead.state===state&&JSON.stringify(lead.shown)===JSON.stringify([state])&&lead.form===(state==="invite")&&lead.register===(state==="register")&&lead.signIn&&lead.leads;
const openGetStarted=async target=>{await target.locator('header nav a[data-page="setup"]').click();return startLead(target);};

const withEndpoint=(value,endpoint)=>value===endpointMark?endpoint:Array.isArray(value)?value.map(item=>withEndpoint(item,endpoint)):value&&typeof value==="object"?Object.fromEntries(Object.entries(value).map(([key,item])=>[key,withEndpoint(item,endpoint)])):value;
const ordered=value=>Array.isArray(value)?value.map(ordered):value&&typeof value==="object"?Object.fromEntries(Object.keys(value).sort().map(key=>[key,ordered(value[key])])):value;
const sameValue=(left,right)=>JSON.stringify(ordered(left))===JSON.stringify(ordered(right));
const textLeaves=(value,key="",found=[])=>{if(typeof value==="string")found.push([key,value]);else if(value&&typeof value==="object")for(const [name,item] of Object.entries(value))textLeaves(item,Array.isArray(value)?key:name,found);return found;};
const readToml=text=>{const result={};let table=result;for(const line of text.split("\n")){if(!line.trim())continue;const header=line.match(/^\[([A-Za-z0-9_.-]+)\]$/);if(header){table=result;for(const part of header[1].split("."))table=table[part]??={};continue;}const entry=line.match(/^([A-Za-z0-9_-]+) = (.+)$/);if(!entry)throw new Error("Unreadable configuration line");table[entry[1]]=JSON.parse(entry[2]);}return result;};
// Key-shaped text. In the alphabet that is safe inside an address: a long unbroken run, or a shorter run that mixes letters and digits. In the standard base64
// alphabet: such a mixed run that also holds a plus sign or padding. Also a bearer value that is not an environment reference. A run that only slashes join
// is not reported, so a record type such as name/v2 and the path of an address are not keys.
const mixedRun=run=>/\d/.test(run)&&/[A-Za-z]/.test(run);
const keyShaped=text=>/[A-Za-z0-9_-]{32,}/.test(text)||(text.match(/[A-Za-z0-9_-]{20,}/g)||[]).some(mixedRun)||(text.match(/[A-Za-z0-9+\/=]{20,}/g)||[]).some(run=>/[+=]/.test(run)&&mixedRun(run))||/\bbearer\s+(?![{$])\S/i.test(text);
const changedRecipe=(id,change)=>{const record=structuredClone(recipeRecord);change(record.recipes.find(recipe=>recipe.id===id),record);return record;};
/* Source-level scan of a recipe record: every value and every field name, in a displayed field or not. A result names the place and never repeats the text,
   and a place never repeats a field name that is itself key-shaped. */
const recordTexts=(value,place="record",found=[])=>{
  if(value!==null&&typeof value==="object")Object.entries(value).forEach(([name,item],index)=>{const next=Array.isArray(value)?place+"["+name+"]":keyShaped(name)?place+".(field "+index+")":place+"."+name;if(!Array.isArray(value))found.push([next+" (field name)",name]);recordTexts(item,next,found);});
  else found.push([place,String(value)]);
  return found;
};
const placesWithKey=record=>{const variable=typeof record?.credential_variable==="string"?record.credential_variable:"";return [...(keyShaped(variable)?["record.credential_variable (the declared name is key-shaped)"]:[]),...recordTexts(record).filter(([,text])=>keyShaped(variable?text.replaceAll(variable,""):text)).map(([place])=>place)];};
/* The rules of one configuration, written once and used twice: for the reviewed record, where the address is the placeholder, and for the shown text, where it is this origin.
   credentials: a credential position holds a declared reference to the variable and nothing else. Such a position is every value inside a table of headers or of environment
   values, every value under a name that holds a credential, and every text that mentions the variable or a bearer value. A name holds a credential when one of its words says so.
   addresses: one server entry, reached through one chain of tables, holds the single url value, and that value is the address. Inside the entry the only tables are tables of
   headers or of environment values, and a configuration holds no list. Every other text is a reference, a plain setting word or the one top-level https $schema value, and every
   field name is a plain name. An address without slashes, with backslashes or under another name, and the arguments of a command, are therefore reported.
   A second, independent test asks the address parser that clients use: no text beside the address and the schema may parse as an absolute address.
   schemas: the page allows the one top-level https $schema value, because an editor reads it and the client never connects to it. The reviewed record is held to more
   than the page: that value must sit on the same host as the source address this recipe cites, so a reviewed record cannot send an editor to a host nobody reviewed.
   A vendor that serves its schema from another host needs a review decision, recorded by changing the record or this rule, not a silent exception.
   A result names places and never repeats a value. */
const parsesAsAddress=text=>[text,text.replaceAll("\\","/")].some(form=>{try{new URL(form);return true;}catch(_){return false;}});
const pathLeaves=(value,path=[],found=[])=>{if(value!==null&&typeof value==="object")for(const [name,item] of Object.entries(value))pathLeaves(item,Array.isArray(value)?path:[...path,name],found);else found.push({path,value});return found;};
const fieldNames=(value,found=[])=>{if(value!==null&&typeof value==="object")for(const [name,item] of Object.entries(value)){if(!Array.isArray(value))found.push(name);fieldNames(item,found);}return found;};
const listPlaces=(value,path=[],found=[])=>{if(Array.isArray(value))found.push(path);else if(value!==null&&typeof value==="object")for(const [name,item] of Object.entries(value))listPlaces(item,[...path,name],found);return found;};
const credentialWords=["authorization","auth","bearer","token","secret","password","passphrase","credential","credentials","key","apikey"];
const namesCredential=name=>name.replace(/([a-z0-9])([A-Z])/g,"$1 $2").toLowerCase().split(/[^a-z0-9]+/).some(word=>credentialWords.includes(word));
const credentialTableName=/^(?:.*headers|env|environment)$/i,plainWord=/^[A-Za-z][A-Za-z0-9_-]*$/,plainName=/^\$?[A-Za-z][A-Za-z0-9_-]*$/,plainCommand=/^[A-Za-z][A-Za-z0-9-]*(?: -{0,2}[A-Za-z][A-Za-z0-9-]*)*$/;
const soleServerEntry=value=>{let table=value;while(table&&!Object.keys(table).includes("url")){const inner=Object.values(table).filter(item=>item!==null&&typeof item==="object"&&!Array.isArray(item));table=inner.length===1?inner[0]:null;}return table;};
const configurationProblems=(configuration,address,variable)=>{
  const references=[variable,"Bearer {env:"+variable+"}","Bearer ${"+variable+"}"],leaves=pathLeaves(configuration||{}),label=name=>keyShaped(name)?"(field)":name,place=leaf=>leaf.path.map(label).join("."),entry=soleServerEntry(configuration);
  const credentialPosition=leaf=>leaf.path.some(name=>credentialTableName.test(name))||leaf.path.some(namesCredential)||(variable!==""&&String(leaf.value).includes(variable))||/\bbearer\b/i.test(String(leaf.value));
  const schemaLeaf=leaf=>leaf.path.length===1&&leaf.path[0]==="$schema"&&typeof leaf.value==="string"&&/^https:\/\/[^\s@\\]+$/.test(leaf.value);
  return {schemas:leaves.filter(schemaLeaf).map(leaf=>leaf.value),
    credentials:leaves.filter(leaf=>credentialPosition(leaf)&&!references.includes(leaf.value)).map(place),
    addresses:[...(entry?.url===address&&leaves.filter(leaf=>leaf.path.at(-1)==="url").length===1?[]:["(the single server entry and its one url value)"]),
      ...Object.entries(entry||{}).filter(([name,item])=>item!==null&&typeof item==="object"&&!Array.isArray(item)&&!credentialTableName.test(name)).map(([name])=>"(a table of other settings) "+label(name)),
      ...listPlaces(configuration||{}).map(path=>"(a list) "+path.map(label).join(".")),
      ...leaves.filter(leaf=>typeof leaf.value==="string"&&!(leaf.path.at(-1)==="url"&&leaf.value===address)&&!schemaLeaf(leaf)&&parsesAsAddress(leaf.value)).map(leaf=>"(parses as an address) "+place(leaf)),
      ...leaves.filter(leaf=>typeof leaf.value==="string"&&!credentialPosition(leaf)&&!(leaf.path.at(-1)==="url"&&leaf.value===address)&&!schemaLeaf(leaf)&&!plainWord.test(leaf.value)).map(place),
      ...fieldNames(configuration||{}).filter(name=>!plainName.test(name)).map(name=>"(field name) "+label(name))]};
};
const sameHost=(left,right)=>{try{return new URL(left).host!==""&&new URL(left).host===new URL(right).host;}catch(_){return false;}};
const recordProblems=record=>{
  const variable=typeof record?.credential_variable==="string"?record.credential_variable:"",found={keys:placesWithKey(record),addresses:[],commands:[],schemas:[]};
  (Array.isArray(record?.recipes)?record.recipes:[]).forEach((recipe,index)=>{const problems=configurationProblems(recipe?.configuration,endpointMark,variable),at=place=>"record.recipes["+index+"].configuration: "+place;found.keys.push(...problems.credentials.map(place=>at(place)+" (a credential position that does not hold a reference to the variable)"));found.addresses.push(...problems.addresses.map(at));if(!plainCommand.test(String(recipe?.verification_command)))found.commands.push("record.recipes["+index+"].verification_command");found.schemas.push(...problems.schemas.filter(address=>!sameHost(address,String(recipe?.source_url))).map(()=>"record.recipes["+index+"].configuration.$schema (not on the host of the cited source address)"));});
  return found;
};
const connectState=async page=>({shown:!await page.locator("#client-choice").isDisabled(),refusal:await page.locator("#setup-message").evaluate(node=>node.dataset.refusal||"")});
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
  // No key: the declared name is not key-shaped, no shown text is key-shaped, and every credential position of the shown configuration holds a reference to the variable.
  const problems=configurationProblems(parsed,endpoint,variable);
  note("recipe_contains_no_key_"+id,!keyShaped(variable)&&shown.includes(variable)&&!keyShaped(scrub(shown))&&!keyShaped(scrub(view))&&!secrets.some(secret=>view.includes(secret)||shown.includes(secret))&&problems.credentials.length===0,{places:problems.credentials});
  // Current origin: the shown configuration breaks no address rule with this origin as its address, holds no unfilled placeholder, and every address written with slashes
  // is this origin or the one schema address, which must sit on the host of the source address this recipe cites.
  const addresses=shown.match(/[a-z][a-z0-9+.-]*:\/\/[^\s"']+/gi)||[];
  note("recipe_uses_current_origin_"+id,parsed!==null&&problems.addresses.length===0&&!shown.includes("{{")&&addresses.every(address=>address===endpoint||(problems.schemas.includes(address)&&sameHost(address,String(recipe.source_url)))),{addresses:addresses.length,places:problems.addresses});
  await page.evaluate(()=>navigator.clipboard.writeText("nothing copied yet"));
  await page.click("#copy-configuration");
  await page.waitForFunction(()=>document.querySelector("#copy-configuration").textContent==="Configuration copied"||document.querySelector("#setup-message").textContent.includes("Clipboard unavailable"));
  const copied=await page.evaluate(()=>navigator.clipboard.readText());
  note("recipe_copy_matches_displayed_text_"+id,copied===shown&&copied===await content("#client-configuration")&&shown.length>0,{copied_length:copied.length,shown_length:shown.length});
  note("recipe_states_how_to_check_and_revoke_"+id,recipe.verification_command.length>0&&plainCommand.test(await content("#client-verify-command"))&&await content("#client-verify-command")===recipe.verification_command&&await content("#client-verify-note")===recipe.verification_note&&/revoke/i.test(record.revocation_note)&&await content("#client-revoke-note")===record.revocation_note&&await content("#client-removal-note")===recipe.removal_note&&await page.locator("#client-revoke-note").isVisible()&&await page.locator("#client-removal-note").isVisible());
  let source=null;try{source=new URL(recipe.source_url);}catch(_){}
  note("recipe_cites_its_source_"+id,recipe.source_url.startsWith("https://")&&source!==null&&source.username===""&&source.password===""&&await page.locator("#client-source").getAttribute("href")===recipe.source_url&&(await page.locator("#client-source").getAttribute("rel")).includes("noopener"));
  note("connect_view_uses_plain_words_"+id,!internalTerms.test(view));
  return view;
}
/* A known-wrong record must be refused before anything from it is displayed. A page without the rule shows it, and the ordinary recipe checks then fail. */
async function checkRefusedRecord(context,base,note,wrong,mutation){
  const {page,state}=await openConnect(context,base,{served:wrong.served,mutation});
  const {shown,refusal}=await connectState(page),closed=!shown&&await page.locator("#copy-configuration").isDisabled();
  note(wrong.name,closed&&refusal===wrong.reason&&!(await page.content()).includes(wrong.planted)&&await page.locator("#client-revoke-note").evaluate(node=>node.textContent)===recipeRecord.revocation_note,{refusal,closed});
  if(!closed)await checkShownRecipe(page,base,wrong.served,wrong.served.recipes.find(recipe=>recipe.id===wrong.id),note);
  await page.close();return state;
}
const localOnly=route=>{const url=route.request().url(); if([fixture.base,fixture.billing_base,fixture.account_base,fixture.signup_base,fixture.browse_base,fixture.identity_origin].some(origin=>url.startsWith(origin+"/")))route.continue(); else {network.push(new URL(url).origin);route.abort();}};
/* Planted values for the known-wrong records. Each is made for this run. The key in the standard base64 alphabet is broken by plus signs into pieces that the
   other alphabet never reports, and the short literal, the number and the shaped name are what a person could type by mistake. The header and the environment
   name that carry the short literal hold no word that names a credential, so only the rule for their table refuses them. */
const variable=recipeRecord.credential_variable,plantedKey="le_"+randomBytes(32).toString("base64url"),standardKey=randomBytes(24).toString("hex").match(/.{6}/g).map(part=>"K7"+part).join("+")+"==";
const shortLiteral="pilot"+randomBytes(3).toString("hex"),shapedName="LE_"+randomBytes(16).toString("hex").toUpperCase(),plantedNumber=100000000+randomBytes(4).readUInt32BE()%900000000;
try {
  /* The reviewed record is checked at source level before anything else, so a key or a foreign address in the record fails here by name, with its place, whatever the page does later. */
  const reviewedProblems=recordProblems(recipeRecord);
  check("reviewed_recipe_record_contains_no_key",reviewedProblems.keys.length===0,{places:reviewedProblems.keys});
  check("reviewed_recipe_record_uses_only_the_address_placeholder",reviewedProblems.addresses.length===0,{places:reviewedProblems.addresses});
  check("reviewed_recipe_record_gives_plain_check_commands",reviewedProblems.commands.length===0,{places:reviewedProblems.commands});
  check("reviewed_recipe_record_keeps_schema_addresses_on_its_cited_source_host",reviewedProblems.schemas.length===0,{places:reviewedProblems.schemas});
  const otherOrigin=fixture.billing_base+"/mcp",otherHost=new URL(otherOrigin).host,schemeOnly=otherOrigin.replace("://",":"),withBackslashes=otherOrigin.replace("://",":\\\\").replace("/mcp","\\mcp");
  const withUserInformation=text=>{const address=new URL(text);address.username="reviewer";address.password=shortLiteral;return address.href;};
  /* Known-wrong records. "display" names the check that must fail when a page without the rule shows the record. A record without it plants its text in a field that the page
     never shows, or breaks a second rule too, so that a page without the first rule still refuses it. */
  const noKey=id=>"recipe_contains_no_key_"+id,currentOrigin=id=>"recipe_uses_current_origin_"+id,reference="Bearer ${"+variable+"}";
  const wrongCredentials=[
    {name:"recipe_with_embedded_key_is_refused_before_display",id:"claude-code",reason:"credential_rule",display:noKey("claude-code"),planted:plantedKey,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.headers.Authorization="Bearer "+plantedKey;})},
    {name:"recipe_with_key_in_place_of_the_variable_name_is_refused",id:"codex",reason:"credential_rule",display:noKey("codex"),planted:plantedKey,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.bearer_token_env_var=plantedKey;})},
    {name:"recipe_with_key_as_a_default_value_is_refused",id:"claude-code",reason:"credential_rule",display:noKey("claude-code"),planted:plantedKey,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.headers.Authorization="Bearer ${"+variable+":-"+plantedKey+"}";})},
    {name:"recipe_with_key_in_a_command_is_refused",id:"opencode",reason:"credential_rule",planted:plantedKey,served:changedRecipe("opencode",item=>{item.verification_command=variable+"="+plantedKey+" "+item.verification_command;})},
    {name:"recipe_with_key_in_a_note_is_refused",id:"opencode",reason:"credential_rule",display:noKey("opencode"),planted:plantedKey,served:changedRecipe("opencode",item=>{item.verification_note+=" "+plantedKey;})},
    {name:"recipe_with_short_literal_bearer_value_is_refused",id:"opencode",reason:"credential_rule",display:noKey("opencode"),planted:"Bearer secret",served:changedRecipe("opencode",item=>{item.configuration.mcp.baltor.headers.Authorization="Bearer secret";})},
    {name:"recipe_with_literal_in_a_second_header_is_refused",id:"claude-code",reason:"credential_rule",display:noKey("claude-code"),planted:shortLiteral,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.headers["X-Pilot-Access"]=shortLiteral;})},
    {name:"recipe_with_short_literal_under_a_credential_name_is_refused",id:"codex",reason:"credential_rule",display:noKey("codex"),planted:shortLiteral,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.bearer_token=shortLiteral;})},
    {name:"recipe_with_number_under_a_credential_name_is_refused",id:"claude-code",reason:"credential_rule",display:noKey("claude-code"),planted:String(plantedNumber),served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.apiKey=plantedNumber;})},
    {name:"recipe_with_literal_in_an_environment_table_is_refused",id:"claude-code",reason:"credential_rule",display:noKey("claude-code"),planted:shortLiteral,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.env={SERVICE_ACCESS:shortLiteral};})},
    {name:"recipe_with_key_in_the_standard_alphabet_is_refused",id:"opencode",reason:"credential_rule",display:noKey("opencode"),planted:standardKey,served:changedRecipe("opencode",item=>{item.verification_note+=" "+standardKey;})},
    {name:"recipe_with_key_shaped_variable_name_is_refused",id:"codex",reason:"credential_rule",display:noKey("codex"),planted:shapedName,served:JSON.parse(JSON.stringify(recipeRecord).replaceAll(variable,shapedName))},
    {name:"record_with_key_in_a_field_that_is_not_displayed_is_refused",id:"codex",reason:"credential_rule",planted:plantedKey,served:changedRecipe("codex",(_,record)=>{record.reviewed_at=plantedKey;})},
    {name:"record_with_key_in_an_unknown_field_is_refused",id:"codex",reason:"credential_rule",planted:plantedKey,served:changedRecipe("codex",(_,record)=>{record.reviewer_note=plantedKey;})},
  ];
  const wrongAddresses=[
    {name:"recipe_with_fixed_address_is_refused_before_display",id:"codex",reason:"address_rule",display:currentOrigin("codex"),planted:otherOrigin,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.url=otherOrigin;})},
    {name:"recipe_with_unknown_placeholder_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:"{{ORIGIN}}",served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.url="{{ORIGIN}}/mcp";})},
    {name:"recipe_with_second_server_entry_at_a_scheme_only_address_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:otherHost,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.mirror={type:"http",url:schemeOnly,headers:{Authorization:reference}};})},
    {name:"recipe_with_placeholder_moved_off_the_url_name_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:otherHost,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.url=schemeOnly;item.configuration.mcpServers.baltor.description=endpointMark;})},
    {name:"recipe_with_second_server_entry_at_a_backslash_address_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:otherHost,served:changedRecipe("opencode",item=>{item.configuration.mcp.mirror={...item.configuration.mcp.baltor,url:withBackslashes};})},
    {name:"recipe_with_scheme_only_address_under_another_name_is_refused",id:"codex",reason:"address_rule",display:currentOrigin("codex"),planted:otherHost,served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.fallback=schemeOnly;})},
    {name:"recipe_with_second_server_entry_that_runs_a_command_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:"helper-tool",served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.helper={command:"helper-tool"};})},
    {name:"recipe_with_plain_host_name_as_its_address_is_refused",id:"codex",reason:"address_rule",display:currentOrigin("codex"),planted:"otherhost",served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.url="otherhost";})},
    {name:"recipe_with_the_placeholder_under_a_second_name_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:"mirror_url",served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.mirror_url=endpointMark;})},
    {name:"recipe_with_a_table_of_other_settings_inside_the_server_entry_is_refused",id:"claude-code",reason:"address_rule",display:currentOrigin("claude-code"),planted:"other_settings",served:changedRecipe("claude-code",item=>{item.configuration.mcpServers.baltor.other_settings={mode:"fast"};})},
    {name:"recipe_with_schema_address_inside_the_server_entry_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:otherHost,served:changedRecipe("opencode",item=>{item.configuration.mcp.baltor.$schema="https://"+otherHost+"/config.json";})},
    /* The same place, but on the host the recipe already cites, so only the rule that the schema address sits at the top of the configuration refuses it. The record above
       is refused by that rule and by the host rule together, so it cannot show the loss of either one on its own. */
    {name:"recipe_with_a_schema_address_of_its_cited_host_inside_the_server_entry_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:"server-schema.json",served:changedRecipe("opencode",item=>{item.configuration.mcp.baltor.$schema="https://"+new URL(item.source_url).host+"/server-schema.json";})},
    {name:"recipe_with_user_information_in_its_schema_address_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:shortLiteral,served:changedRecipe("opencode",item=>{item.configuration.$schema=withUserInformation(item.configuration.$schema);})},
  ];
  /* Known-wrong records for the one schema address. The page and this script both hold that address to the host of the source address the recipe cites, so a record that
     names another host, including a second host of the same vendor, is refused before anything is displayed. These records are kept out of wrongAddresses because a schema
     address is not one of the address places that the address pairing check below requires of every record it is given. */
  const citedSchemaAddress=recipeRecord.recipes.find(item=>item.id==="opencode").configuration.$schema,vendorSecondHost="files."+new URL(citedSchemaAddress).host;
  const wrongSchemas=[
    {name:"recipe_with_a_schema_address_on_another_host_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:otherHost,served:changedRecipe("opencode",item=>{item.configuration.$schema="https://"+otherHost+"/config.json";})},
    {name:"recipe_with_a_schema_address_on_a_second_host_of_the_cited_vendor_is_refused",id:"opencode",reason:"address_rule",display:currentOrigin("opencode"),planted:vendorSecondHost,served:changedRecipe("opencode",item=>{const address=new URL(item.configuration.$schema);address.host="files."+address.host;item.configuration.$schema=address.href;})},
  ];
  const unsupportedRecords=[
    {name:"older_recipe_record_version_is_refused",id:"codex",reason:"unsupported_record",planted:"website_client_recipes/v1",served:changedRecipe("codex",(_,record)=>{record.record_type="website_client_recipes/v1";})},
    {name:"recipe_without_revocation_steps_is_refused",id:"claude-code",reason:"unsupported_record",display:"recipe_states_how_to_check_and_revoke_claude-code",planted:"claude mcp list",served:changedRecipe("claude-code",item=>{delete item.removal_note;})},
    {name:"recipe_that_cannot_be_written_as_a_table_is_refused",id:"codex",reason:"unsupported_record",planted:"enabled = null",served:changedRecipe("codex",item=>{item.configuration.mcp_servers.baltor.enabled=null;})},
    {name:"recipe_with_a_list_of_command_arguments_is_refused",id:"claude-code",reason:"unsupported_record",display:currentOrigin("claude-code"),planted:"helper-package",served:changedRecipe("claude-code",item=>{Object.assign(item.configuration.mcpServers.baltor,{type:"stdio",command:"npx",args:["helper-package"]});})},
    {name:"recipe_with_a_command_line_that_is_not_plain_words_is_refused",id:"opencode",reason:"unsupported_record",display:"recipe_states_how_to_check_and_revoke_opencode",planted:"| sh",served:changedRecipe("opencode",item=>{item.verification_command+=" | sh";})},
    {name:"recipe_with_an_address_as_its_entry_name_is_refused",id:"claude-code",reason:"unsupported_record",display:currentOrigin("claude-code"),planted:otherHost,served:changedRecipe("claude-code",item=>{item.configuration.mcpServers={[otherOrigin]:item.configuration.mcpServers.baltor};})},
    {name:"recipe_with_user_information_in_its_source_address_is_refused",id:"claude-code",reason:"unsupported_record",display:"recipe_cites_its_source_claude-code",planted:shortLiteral,served:changedRecipe("claude-code",item=>{item.source_url=withUserInformation(item.source_url);})},
  ];
  const allWrong=[...wrongCredentials,...wrongAddresses,...wrongSchemas,...unsupportedRecords],wrongNamed=(...names)=>names.map(name=>{const wrong=allWrong.find(item=>item.name===name);if(!wrong)throw new Error("Unknown known-wrong record: "+name);return wrong;});
  /* Each source-level check is paired with the known-wrong records: it must report every one of them, and a place never repeats a planted text. */
  const keyRecords=[...wrongCredentials,{name:"record_with_key_as_a_field_name",served:changedRecipe("codex",(_,record)=>{record[plantedKey]="note";})},{name:"record_with_key_in_a_list",served:changedRecipe("codex",(_,record)=>{record.notes=["first",plantedKey];})}];
  const addressRecords=[...wrongAddresses,...wrongNamed("recipe_with_an_address_as_its_entry_name_is_refused","recipe_with_a_list_of_command_arguments_is_refused")];
  const commandRecords=wrongNamed("recipe_with_a_command_line_that_is_not_plain_words_is_refused","recipe_with_key_in_a_command_is_refused");
  /* The same two schema records, paired here at source level as well. The count is part of the assertion, so deleting a record fails this check instead of leaving it green. */
  const schemaRecords=wrongNamed("recipe_with_a_schema_address_on_another_host_is_refused","recipe_with_a_schema_address_on_a_second_host_of_the_cited_vendor_is_refused");
  const keyPlaces=keyRecords.map(wrong=>[wrong.name,recordProblems(wrong.served).keys]),addressPlaces=addressRecords.map(wrong=>[wrong.name,recordProblems(wrong.served).addresses]);
  const repeatsPlantedText=places=>[plantedKey,standardKey,shapedName].some(text=>JSON.stringify(places).includes(text));
  check("no_key_check_of_the_record_fails_for_every_known_wrong_record",keyPlaces.every(([,places])=>places.length>0)&&!repeatsPlantedText(keyPlaces),{records:keyPlaces.length,missed:keyPlaces.filter(([,places])=>places.length===0).map(([name])=>name)});
  check("address_check_of_the_record_fails_for_every_known_wrong_record",addressPlaces.every(([,places])=>places.length>0)&&!repeatsPlantedText(addressPlaces),{records:addressPlaces.length,missed:addressPlaces.filter(([,places])=>places.length===0).map(([name])=>name)});
  check("command_check_of_the_record_fails_for_every_known_wrong_record",commandRecords.every(wrong=>recordProblems(wrong.served).commands.length>0),{records:commandRecords.length});
  check("schema_check_of_the_record_fails_for_every_known_wrong_record",schemaRecords.length===2&&schemaRecords.every(wrong=>recordProblems(wrong.served).schemas.length>0)&&recordProblems(recipeRecord).schemas.length===0&&recipeRecord.recipes.some(item=>configurationProblems(item.configuration,endpointMark,variable).schemas.length===1),{records:schemaRecords.length});
  check("no_key_check_does_not_mistake_a_record_type_or_an_address_for_a_key",!keyShaped(recipeRecord.record_type)&&recipeRecord.recipes.every(item=>!keyShaped(item.source_url))&&keyShaped(standardKey)&&!keyShaped(shortLiteral));
  browser=await chromium.launch({executablePath:"/opt/google/chrome/chrome",headless:true,args:["--no-sandbox"]});
  const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,reducedMotion:"reduce"});
  await context.route("**/*",localOnly); routeBrowseAsset(context);
  const page=await context.newPage(); page.on("pageerror",error=>errors.push(safeError(error.message)));
  await page.goto(fixture.base+"/"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  check("public_landing_has_real_routes_and_configured_brand",(await page.title()).startsWith("Baltor |")&&await page.locator('[data-view="home"]').isVisible());
  /* The headline is the owner's line. It has to name the two readers it addresses, the developers and the agents they run.
     The sentence under it names the unit of work this product sells. Each rule has its own known-wrong case beside it. */
  const headline=await page.locator('[data-view="home"] h1').innerText();
  const namesTheReader=text=>/\byour\b/i.test(text)&&/\bdevelopers?\b/i.test(text)&&/\bagents?\b/i.test(text);
  const namesTheStep=text=>/\beach step\b/i.test(text);
  check("homepage_headline_names_the_developer_and_the_agent",namesTheReader(headline)&&await page.locator('[data-view="home"] .boundary-figure').count()===0,{headline});
  check("headline_check_rejects_a_headline_that_names_neither",["Turn complex problems into reusable solutions.","Harness and agent optimized operation.","Supercharge your workflow.","Material your coding tools can search.","Supercharge your agents."].every(claim=>!namesTheReader(claim))&&namesTheReader("Supercharge your developers and AI agents"));
  const subhead=await page.locator('[data-view="home"] .hero-subhead').innerText();
  check("homepage_subhead_names_the_unit_of_work",namesTheStep(subhead),{subhead});
  check("subhead_check_rejects_a_sentence_that_never_names_the_step",["Baltor is a library your coding tools can search.","Supercharge your developers and AI agents."].every(claim=>!namesTheStep(claim))&&namesTheStep("Give your AI agents what they need for each step."));
  check("homepage_says_the_model_keys_stay_with_the_customer",(await page.locator(".hero-value").innerText()).includes("Your model keys stay with you")&&(await page.locator(".hero-value").innerText()).includes("never asks you for a provider key")&&(await page.locator(".benefit-limits").innerText()).includes("No percentage reduction"));
  check("light_is_default_even_when_operating_system_is_dark",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  await page.emulateMedia({colorScheme:"dark"});await page.reload();
  check("operating_system_does_not_override_explicit_light_default",await page.evaluate(()=>document.documentElement.dataset.theme==="light"&&getComputedStyle(document.body).backgroundColor==="rgb(255, 255, 255)"));
  await page.emulateMedia({colorScheme:"light"});
  check("optimization_message_does_not_guarantee_daily_improvement",(await page.locator(".optimization-callout").innerText()).includes("Model selection, context sizing, tool choice and code reuse")&&(await page.locator(".benefit-limits").innerText()).includes("guaranteed daily performance gain"));
  /* Landing sections and the pricing view. The page is never allowed to agree with itself: every state that depends on the
     service is read from a real service reply on its own origin, and each published fact has a known-wrong case beside it. */
  /* The line above the headline is the owner's name for the positioning, written out in full. The word harness is
     jargon outside this repository, so a plain sentence has to sit beside the phrase and say what it means. A page
     that prints the phrase and leaves the reader to guess is the known-wrong case. */
  check("homepage_opens_with_the_owner_category_line",await page.locator('[data-view="home"] .hero .eyebrow').evaluate(node=>node.textContent.trim())==="Harness and agent optimized operation");
  const positioning=await page.locator('[data-view="home"] .hero-positioning').innerText();
  const explainsTheCategoryLine=text=>/harness and agent optimized operation/i.test(text)&&/\ba harness is\b/i.test(text)&&/each step/i.test(text);
  check("the_owner_category_line_is_explained_in_plain_words",explainsTheCategoryLine(positioning),{positioning});
  check("category_line_explanation_check_rejects_a_bare_phrase",["Harness and agent optimized operation.","Built for harness and agent optimized operation, one step at a time.","A harness is the program that runs your coding agent."].every(claim=>!explainsTheCategoryLine(claim))&&explainsTheCategoryLine(positioning));
  check("homepage_states_the_free_and_paid_split",(await page.locator('[data-view="home"] .hero-split').innerText()).startsWith("Free to install. Paid access to the library."));
  /* One primary action in the hero: "Get started", opening the Get started page. One secondary link beside it, and no second
     way into the same journey anywhere in the hero. */
  const heroPrimary=page.locator('[data-view="home"] .hero .button.primary');
  check("homepage_offers_one_primary_action_and_one_secondary",await heroPrimary.count()===1&&await heroPrimary.getAttribute("id")==="hero-primary"&&await heroPrimary.getAttribute("href")==="/connect"&&(await heroPrimary.innerText()).replace(/[↗]/g,"").trim()==="Get started"&&await page.locator("#hero-primary").isVisible()&&await page.locator("#hero-how-it-works").isVisible()&&await page.locator("#hero-how-it-works").getAttribute("href")==="/how-it-works#task-breakdown"&&await page.locator('[data-view="home"] .hero a[href^="/signup"], [data-view="home"] .hero a[href="/waitlist"]').count()===0);
  const homeFlow=await page.locator('[data-view="home"]').evaluate(home=>{
    const hero=home.querySelector('.product-hero'),start=home.querySelector('.start-strip'),offer=home.querySelector('.offer-section'),benefits=home.querySelector('.benefit-section');
    const before=(first,second)=>Boolean(first.compareDocumentPosition(second)&Node.DOCUMENT_POSITION_FOLLOWING);
    return {hasWorkflowRail:Boolean(hero.querySelector('.solution-preview')),startBeforeOffer:before(start,offer),offerBeforeBenefits:before(offer,benefits)};
  });
  const currentPathFirst=flow=>!flow.hasWorkflowRail&&flow.startBeforeOffer&&flow.offerBeforeBenefits;
  check("homepage_starts_with_the_current_customer_path",currentPathFirst(homeFlow),homeFlow);
  check("homepage_flow_check_rejects_the_workflow_rail_and_old_order",!currentPathFirst({...homeFlow,hasWorkflowRail:true})&&!currentPathFirst({...homeFlow,startBeforeOffer:false})&&!currentPathFirst({...homeFlow,offerBeforeBenefits:false}));
  /* The owner saw the hero as one narrow column with empty space on both sides. At desktop width the hero spans the
     page like every section below it, and the example sits beside the text. The example shows only the live path:
     one search, the references it returned, one download whose bytes match its digest. */
  const heroLayout=await page.locator('[data-view="home"]').evaluate(home=>{
    const hero=home.querySelector('.product-hero'),copy=hero.querySelector('.hero-copy'),example=hero.querySelector('.hero-example');
    const next=home.querySelector('.start-strip');
    const box=node=>node?node.getBoundingClientRect():{left:0,right:0,width:0,top:0};
    return {heroWidth:box(hero).width,pageWidth:box(next).width,copyRight:box(copy).right,exampleLeft:box(example).left,
      exampleTop:box(example).top,copyTop:box(copy).top,hasExample:Boolean(example),viewport:innerWidth,
      exampleText:example?example.innerText:""};
  });
  const heroFillsThePage=m=>m.viewport<1100||(m.hasExample&&m.heroWidth>=0.95*m.pageWidth&&m.exampleLeft>=m.copyRight-1);
  check("homepage_hero_spans_the_page_with_the_example_beside_it",heroFillsThePage(heroLayout),heroLayout);
  check("hero_layout_check_rejects_a_narrow_column_and_a_missing_example",
    !heroFillsThePage({...heroLayout,viewport:1440,heroWidth:820})&&!heroFillsThePage({...heroLayout,viewport:1440,hasExample:false})
    &&!heroFillsThePage({...heroLayout,viewport:1440,exampleLeft:heroLayout.copyRight-200}));
  const showsOnlyTheLivePath=text=>/\bsearch\b/.test(text)&&/\bdownload\b/.test(text)&&/sha256/.test(text)
    &&/Bytes match the digest/.test(text)&&!/workflow|illustration|reusable solution|coming soon/i.test(text);
  const exampleItems=await page.locator('[data-view="home"] .hero-example [data-example-item]').evaluateAll(items=>items.map(item=>item.dataset.exampleItem));
  check("hero_example_shows_only_the_live_search_and_download_path",showsOnlyTheLivePath(heroLayout.exampleText)&&exampleItems.length===3,{exampleItems});
  check("hero_example_check_rejects_a_workflow_illustration",
    !showsOnlyTheLivePath(heroLayout.exampleText+" Example workflow")&&!showsOnlyTheLivePath("Prepare a customer import. Illustration."));
  /* The example names real items. Each one must be an approved item of the released catalogue, so withdrawing an
     item forces the example to change instead of leaving the page naming something the library no longer serves. */
  const releasedIdentities=JSON.parse(readFileSync(resolve(root,"examples/29_intelligence_service/starter-catalogue/host-release/manifest.json"),"utf8")).items.map(item=>item.reference.identity);
  const namesOnlyReleasedItems=names=>names.length>0&&names.every(name=>releasedIdentities.includes(name));
  check("hero_example_names_only_released_catalogue_items",namesOnlyReleasedItems(exampleItems),{exampleItems});
  check("hero_example_item_check_rejects_an_item_the_library_does_not_serve",!namesOnlyReleasedItems([...exampleItems,"invented_item_nobody_approved"]));
  const startSteps=await page.locator("[data-start-step]").evaluateAll(items=>items.map(item=>item.dataset.startStep).sort()),startText=await page.locator(".start-strip").innerText();
  check("homepage_shows_a_three_step_strip",JSON.stringify(startSteps)===JSON.stringify(["ask","connect","keep"])&&["OpenCode","Codex","Claude Code"].every(client=>startText.includes(client)),{steps:startSteps});
  const offers=await page.locator("[data-offer]").evaluateAll(items=>items.map(item=>item.dataset.offer).sort()),offerText=await page.locator(".offer-section").innerText();
  check("homepage_says_what_an_account_gives_you",JSON.stringify(offers)===JSON.stringify(["downloads","recipes","search","usage"])&&["search","download","usage"].every(word=>offerText.toLowerCase().includes(word))&&["OpenCode","Codex","Claude Code"].every(client=>offerText.includes(client)),{offers});
  const teaserText=await page.locator(".pricing-teaser").innerText();
  check("homepage_states_the_plan_price_and_the_measured_unit",teaserText.includes("29 United States dollars each month")&&teaserText.includes("one downloaded item")&&teaserText.includes("invited accounts are free")&&await page.locator('.pricing-teaser a[data-page="pricing"]').getAttribute("href")==="/pricing");
  check("homepage_closes_with_an_action",await page.locator(".closing-callout #closing-primary").isVisible()&&await page.locator(".closing-callout .text-link").isVisible());
  const promiseWords=/\d+\s*%|\bguarantee\w*\b|\balways\b/gi,homeClaims=await page.locator('[data-view="home"]').evaluate(node=>{const clone=node.cloneNode(true);clone.querySelectorAll(".benefit-limits").forEach(item=>item.remove());return clone.textContent;});
  check("homepage_makes_no_unmeasured_promise",(homeClaims.match(promiseWords)||[]).length===0,{words:[...new Set(homeClaims.match(promiseWords)||[])]});
  check("promise_check_rejects_a_known_wrong_claim",["Cut your token spend by 40%","Always picks the right model","Guaranteed savings every day","A 3 % better result"].every(claim=>(claim.match(promiseWords)||[]).length>0));
  /* Owner decision of September 21, 2026. A benefit detail says what the product does, in the present tense, and it
     names a real limit of what exists today where there is one: the library holds a small first collection, and the
     ranking work is written but not connected to a live run. It does not apologise for a measurement nobody asked
     for. Both halves of that rule have a known-wrong case: a missing limit and a returned apology each get reported. */
  const benefitText=await page.locator(".benefit-section").evaluate(node=>node.textContent);
  const realLimits=["The library on our server holds a small first collection of reviewed items today","That part is not connected to a live run yet."];
  const measurementApologies=["We have not measured","Nobody has measured it yet","We have not run that as an experiment","it is an aim and not a result"];
  const benefitProblems=text=>[...realLimits.filter(sentence=>!text.includes(sentence)).map(sentence=>"missing real limit: "+sentence),
    ...measurementApologies.filter(sentence=>text.includes(sentence)).map(sentence=>"measurement apology: "+sentence)];
  check("benefit_details_state_the_real_limits_without_a_measurement_apology",benefitProblems(benefitText).length===0&&!/\d+\s*%/.test(benefitText),{problems:benefitProblems(benefitText)});
  check("benefit_detail_check_rejects_a_missing_limit_and_a_returned_apology",
    realLimits.every(sentence=>benefitProblems(benefitText.split(sentence).join("")).length===1)&&
    measurementApologies.every(sentence=>benefitProblems(benefitText+" "+sentence).length===1),
    {limits:realLimits.length,apologies:measurementApologies.length});
  await checkBenefitList(page,check);
  /* The detail text belongs to the page, not to the script. A browser that never receives the script shows all six. */
  const withoutScript=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
  await withoutScript.route("**/*",localOnly);
  await withoutScript.route("**/assets/service.js",route=>route.abort());
  const plain=await withoutScript.newPage();
  plain.on("pageerror",()=>{});
  await plain.goto(fixture.base+"/");
  const plainShown=await shownBenefits(plain),plainText=await plain.locator(".benefit-section").innerText();
  check("benefit_detail_reads_when_the_script_has_not_run",plainShown.length===6&&JSON.stringify(plainShown)===JSON.stringify(benefitNames)&&benefitSentences.every(sentence=>plainText.includes(sentence))&&benefitTitles.every(title=>plainText.includes(title)),{shown:plainShown});
  await plain.close();await withoutScript.close();
  /* Retired words and runtime words, read from every page a customer can open, including the shared header and footer.
     The Documentation view keeps the exact runtime terms, so it is scanned for the retired words only. */
  const servedRoutes=["/","/how-it-works","/pricing","/connect","/signup","/login","/examples","/security","/privacy","/app","/account","/docs"];
  /* The scan carries no exception. The one sentence that used to need one, on the account page, was rewritten with
     the rest of the retired words, so a retired word anywhere in what a customer reads is a named failure. */
  const vocabularyProblems=[];
  /* A page without the shared header or footer, such as the page for an address the service does not serve, is read
     as far as it goes, so an unserved address fails its own named checks instead of stopping the whole journey. */
  const readShownText=target=>target.evaluate(()=>[document.querySelector("header")?.innerText||"",[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.innerText).join("\n"),document.querySelector("footer")?.innerText||""].join("\n"));
  const scanShownText=(path,shownText)=>{
    if(retiredAccessWords.test(shownText))vocabularyProblems.push({path,rule:"retired access word",found:shownText.match(retiredAccessWords)[0]});
    if(path!=="/docs"&&publicVocabulary.test(shownText))vocabularyProblems.push({path,rule:"runtime word",found:shownText.match(publicVocabulary)[0]});
  };
  for(const path of servedRoutes){await page.goto(fixture.base+path);scanShownText(path,await readShownText(page));}
  /* The Get started page also answers at "/get-started", which the serving route table does not list yet, so that
     address is reached through the navigation. Every link on the website points at "/connect", which is served. */
  await page.goto(fixture.base+"/");
  await page.evaluate(()=>{history.pushState({},"","/get-started");dispatchEvent(new PopStateEvent("popstate"));});
  scanShownText("/get-started",await readShownText(page));
  /* Rendered text is not the whole surface. A message can sit in a script the browser fetches and appear only in a
     state this pass never reaches, and a class name can carry a retired word into the served stylesheet. Every file
     the browser fetches for a customer page is therefore read, not only the markup and the main script. */
  const servedFiles=["/","/assets/service.js","/assets/client-access.js","/assets/catalogue-browser.js","/assets/architecture-story.js","/assets/supabase-client.js","/assets/service.css","/assets/architecture.css","/assets/client-recipes.json","/assets/third-party-notices.txt"];
  /* The list is compared with the route table the service actually serves. The footer links to the open-source notices,
     so a customer reaches that file from every page, and a served asset added in the route table alone is a named
     failure here rather than a file nobody scans. The table lives in web_pages.py since September 21, 2026; this scan
     read http.py until September 22 and found no routes at all, which failed both checks below by name. */
  const routeTable=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_pages.py"),"utf8").match(/^WEB_ASSETS = \{$([\s\S]*?)^\}$/m);
  const assetRoutes=routeTable?[...routeTable[1].matchAll(/"(\/assets\/[^"]+)":/g)].map(found=>found[1]):[];
  const unscannedFor=list=>assetRoutes.filter(path=>!list.includes(path));
  check("every_served_asset_route_is_scanned_for_retired_words",assetRoutes.length>0&&unscannedFor(servedFiles).length===0,{routes:assetRoutes.length,unscanned:unscannedFor(servedFiles)});
  check("served_asset_coverage_check_rejects_a_route_left_out_of_the_scan",assetRoutes.length>0&&assetRoutes.every(path=>JSON.stringify(unscannedFor(servedFiles.filter(kept=>kept!==path)))===JSON.stringify([path])),{routes:assetRoutes.length});
  const servedTexts=[];
  for(const path of servedFiles)servedTexts.push([path,await (await page.request.get(fixture.base+path)).text()]);
  const retiredIn=(path,text)=>retiredAccessWords.test(text)?[{path:"the served file "+path,rule:"retired access word",found:text.match(retiredAccessWords)[0]}]:[];
  const servedFileProblems=servedTexts.flatMap(([path,text])=>retiredIn(path,text));
  check("no_customer_page_describes_the_product_as_a_trial",vocabularyProblems.filter(item=>item.rule==="retired access word").length===0,{problems:vocabularyProblems.filter(item=>item.rule==="retired access word")});
  check("no_customer_page_uses_the_runtime_vocabulary",vocabularyProblems.filter(item=>item.rule==="runtime word").length===0,{problems:vocabularyProblems.filter(item=>item.rule==="runtime word")});
  /* One known-wrong page for each retired phrase, including a page that never writes pilot or beta and still offers
     early access. An earlier rule read only pilot and beta and let that last page through. */
  const retiredKnownWrong=["Join the private pilot.","Beta users get early access.","A pilot user can search.","Our private beta is invitation only.","Request early access from your account page."];
  check("retired_word_check_rejects_a_known_wrong_page",retiredKnownWrong.every(claim=>retiredAccessWords.test(claim))&&!retiredAccessWords.test("Accounts open in small groups. Join the waiting list."),{pages:retiredKnownWrong.length});
  check("no_served_file_carries_a_retired_word",servedTexts.length===servedFiles.length&&servedFileProblems.length===0,{files:servedTexts.length,problems:servedFileProblems});
  check("served_file_scan_rejects_a_file_that_carries_a_retired_word",servedTexts.length===servedFiles.length&&["\n/* Join the private beta. */","\n/* Ask for early access. */"].every(planted=>servedTexts.every(([path,text])=>retiredIn(path,text+planted).length===1)),{files:servedTexts.length});
  check("runtime_word_check_rejects_a_known_wrong_page",["Built on Loop Engine.","Every step is a Loop node.","See the role profiles.","Read the runtime classification.","A Practitioner owns the task."].every(claim=>publicVocabulary.test(claim))&&!publicVocabulary.test("Each step gets the material it needs."));
  /* Get started is the first way into the product, and the page behind it walks through the three steps in order. */
  await page.goto(fixture.base+"/");
  const navItems=await page.locator("header nav a").evaluateAll(items=>items.map(item=>({label:item.textContent.trim(),href:item.getAttribute("href"),page:item.dataset.page})));
  const firstIsGetStarted=items=>items.length>1&&items[0].label==="Get started"&&items[0].page==="setup"&&!items.some(item=>item.label==="Connect");
  check("get_started_is_the_first_navigation_item",firstIsGetStarted(navItems)&&navItems[1].label==="How it works",{nav:navItems});
  check("navigation_order_check_rejects_a_wrong_first_item",[[{label:"How it works",page:"about"},{label:"Get started",page:"setup"}],[{label:"Connect",page:"setup"},{label:"Get started",page:"setup"}],[{label:"Get started",page:"setup"},{label:"Connect",page:"setup"}]].every(items=>!firstIsGetStarted(items)));
  await page.locator('header nav a[data-page="setup"]').click();
  const orderedSteps=await page.locator("[data-get-started-step]").evaluateAll(items=>items.map(item=>({step:item.dataset.getStartedStep,index:item.querySelector(".feature-index").textContent.trim(),title:item.querySelector("[data-get-started-title]").textContent.trim()})));
  /* The Get started page leads with access, because search and downloads need an account; the part you install and the
     connection follow. The first step is the panel the service's record chooses, so its title is the same in every state. */
  const namesThreeStepsInOrder=steps=>JSON.stringify(steps.map(item=>item.step))===JSON.stringify(["access","download","connect"])&&steps.every((item,index)=>item.index.startsWith("Step "+(index+1)+" / ")&&item.title.length>0);
  check("get_started_page_names_the_three_steps_in_order",new URL(page.url()).pathname==="/connect"&&namesThreeStepsInOrder(orderedSteps)&&await page.locator('[data-view="setup"]').isVisible(),{steps:orderedSteps});
  check("get_started_step_check_rejects_a_wrong_order_or_a_missing_step",[[orderedSteps[1],orderedSteps[0],orderedSteps[2]],[orderedSteps[0],orderedSteps[1]],[orderedSteps[0],orderedSteps[2],orderedSteps[1]]].every(steps=>!namesThreeStepsInOrder(steps))&&namesThreeStepsInOrder(orderedSteps));
  check("get_started_page_carries_the_copyable_connection_settings",await page.locator("#client-choice").count()===1&&await page.locator("#client-configuration").count()===1&&await page.locator("#copy-configuration").count()===1);
  // The Get started address opens the same page. The serving route table does not list it yet, so only the navigation reaches it.
  await page.evaluate(()=>{history.pushState({},"","/get-started");dispatchEvent(new PopStateEvent("popstate"));});
  check("get_started_address_opens_the_same_page",new URL(page.url()).pathname==="/get-started"&&await page.locator('[data-view="setup"]').isVisible()&&await page.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length)===1);
  await page.goto(fixture.base+"/");
  await page.locator('header a[data-page="pricing"]').click();
  check("pricing_view_opens_from_the_navigation",new URL(page.url()).pathname==="/pricing"&&await page.locator('[data-view="pricing"]').isVisible()&&await page.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length)===1&&(await page.title()).endsWith("| Pricing"));
  const pricingText=await page.locator('[data-view="pricing"]').innerText();
  const pricingFacts=[["plan name","Baltor Pro"],["price","29 United States dollars"],["period","each month"],["free search","Search is free."],["measured unit","one downloaded item"],["invited accounts","Invited accounts are free."]];
  const missingFacts=text=>pricingFacts.filter(([,fact])=>!text.includes(fact)).map(([name])=>name);
  check("pricing_view_states_every_published_fact",missingFacts(pricingText).length===0,{missing:missingFacts(pricingText)});
  check("pricing_fact_check_fails_when_one_fact_is_missing",pricingFacts.every(([name,fact])=>missingFacts(pricingText.split(fact).join("")).includes(name)),{facts:pricingFacts.length});
  check("pricing_view_offers_exactly_one_plan",await page.locator("[data-plan-point]").count()===5&&await page.locator('[data-view="pricing"] .plan-card').count()===1&&await page.locator('[data-view="pricing"] .button.primary').count()===1);
  /* While the service reports no checkout, the pricing view may not carry a control that starts a payment. The guide states that rule, so a check owns it. */
  const purchaseWords={source:"\\b(?:buy|purchase|checkout|subscribe|subscription|pay|payment|card)\\b",flags:"i"};
  const purchaseControls=async opened=>opened.locator('[data-view="pricing"]').evaluate((node,pattern)=>{
    const rule=new RegExp(pattern.source,pattern.flags);
    return [...node.querySelectorAll("button, a, form, input[type=submit], input[type=button]")]
      .map(item=>[item.tagName.toLowerCase()+(item.id?"#"+item.id:""),(item.textContent||"")+" "+(item.getAttribute("aria-label")||"")+" "+(item.getAttribute("value")||"")])
      .filter(([,text])=>rule.test(text)).map(([place])=>place);
  },purchaseWords);
  check("pricing_view_offers_no_purchase_control_while_checkout_is_closed",(await purchaseControls(page)).length===0,{controls:await purchaseControls(page)});
  await page.evaluate(()=>{const planted=document.createElement("a");planted.id="known-wrong-purchase";planted.className="button primary";planted.textContent="Subscribe now";document.querySelector('[data-view="pricing"] .plan-card .actions').append(planted);});
  const plantedPurchase=await purchaseControls(page);
  await page.evaluate(()=>document.getElementById("known-wrong-purchase").remove());
  check("purchase_control_check_rejects_a_pricing_view_that_offers_one",plantedPurchase.includes("a#known-wrong-purchase")&&(await purchaseControls(page)).length===0,{planted:plantedPurchase});
  check("pricing_view_uses_plain_words",!internalTerms.test(pricingText));
  check("plain_word_check_rejects_a_page_that_names_the_runtime",["Built on Loop Engine.","Every step is a Loop node.","See the role profiles.","Read the runtime classification."].every(claim=>internalTerms.test(pricingText+"\n"+claim)));
  const pricingFits=[];
  for(const width of [1440,820,390,360,320]){
    await page.setViewportSize({width,height:1000});
    for(const size of ["","200%"]){
      await page.evaluate(value=>document.documentElement.style.fontSize=value,size);
      pricingFits.push({width,size:size||"100%",...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length}))});
    }
    await page.evaluate(()=>document.documentElement.style.fontSize="");
  }
  check("pricing_view_fits_small_screens_and_enlarged_text",pricingFits.length===10&&pricingFits.every(item=>!item.overflow&&item.views===1),{problems:pricingFits.filter(item=>item.overflow||item.views!==1)});
  /* A published address must answer a bookmark, a shared link and a reload, not only an intercepted click inside the page. */
  const directPricing=await page.request.get(fixture.base+"/pricing",{maxRedirects:0});
  check("pricing_address_is_served_on_a_direct_visit",directPricing.status()===200&&(directPricing.headers()["content-type"]||"").startsWith("text/html"),
    {status:directPricing.status(),content_type:directPricing.headers()["content-type"]||"",
     needed_entry:'src/loop_engine/core/service_runtime/web_pages.py, WEB_ASSETS, add "/pricing": ("index.html", HTML_MEDIA_TYPE)'});
  const reloadedPricing=await context.newPage();
  reloadedPricing.on("pageerror",error=>errors.push(safeError(error.message)));
  await reloadedPricing.goto(fixture.base+"/pricing");
  const reloadedViews=await reloadedPricing.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view));
  await reloadedPricing.close();
  check("pricing_address_opens_the_pricing_view_after_a_reload",JSON.stringify(reloadedViews)===JSON.stringify(["pricing"]),{views:reloadedViews});
  await page.setViewportSize({width:1440,height:1000});await page.screenshot({path:output.replace(/\.json$/,"-pricing-desktop.png"),fullPage:true});
  await page.setViewportSize({width:360,height:1000});await page.screenshot({path:output.replace(/\.json$/,"-pricing-mobile.png"),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  /* The privacy notice the owner approved on September 22, 2026. It answers at its own address on a direct visit, it
     names the operator and the postal contact address, the shared footer links to it, and the page says the same
     words as the approved text in docs/legal/PRIVACY-NOTICE.md, read here from the source tree. Two removed-guard
     controls serve changed bytes in memory, never a source file: the homepage without the footer link, and the
     notice with one fact changed. Each must fail its own named check. */
  const privacyOperator="Baltor.AI",privacyAddress="1428 Bryn Mawr St, Saxton, PA 16678, United States";
  const privacyLink='<a href="/privacy" data-page="privacy">Privacy notice</a>';
  /* The Markdown is read as a reader sees it rendered: a code span or strong text is the same word without its marks. */
  const markdownWords=text=>text.replace(/`/g,"").replace(/\*\*/g,"").replace(/^#+\s/gm," ").replace(/^\|[-| :]+\|\s*$/gm," ").replace(/\|/g," ").replace(/^\s*- /gm," ").split(/\s+/).filter(Boolean);
  const approvedWords=markdownWords(readFileSync(resolve(root,"docs/legal/PRIVACY-NOTICE.md"),"utf8"));
  const sameWords=(shown,approved)=>shown.length>0&&JSON.stringify(shown)===JSON.stringify(approved);
  const namesTheOperator=text=>text.includes("Operator: "+privacyOperator+", "+privacyAddress+".")&&text.split(privacyAddress).length-1===2;
  const privacyState=async opened=>opened.evaluate(()=>{
    const notice=document.querySelector("[data-privacy-notice]"),shown=[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden);
    return {path:location.pathname,views:shown.map(item=>item.dataset.view),title:document.title,text:notice?notice.innerText:""};});
  const openAt=async (path,mutation)=>{
    const opened=await context.newPage(),state={applied:false,errors:[]};
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    if(mutation)await opened.route(url=>url.origin===new URL(fixture.base).origin&&url.pathname===mutation.path,async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    await opened.goto(fixture.base+path);
    await opened.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability");
    return {page:opened,state};
  };
  const checkPrivacyNotice=async (opened,note)=>{
    const state=await privacyState(opened);
    note("privacy_notice_opens_at_its_own_address",state.path==="/privacy"&&JSON.stringify(state.views)===JSON.stringify(["privacy"])&&state.title.endsWith("| Privacy notice"),{path:state.path,views:state.views,title:state.title});
    note("privacy_notice_names_the_operator_and_the_postal_contact_address",namesTheOperator(state.text),{operator:state.text.includes(privacyOperator),address:state.text.split(privacyAddress).length-1});
    const shownWords=state.text.split(/\s+/).filter(Boolean),differs=shownWords.findIndex((word,index)=>word!==approvedWords[index]);
    note("privacy_notice_says_the_same_words_as_the_approved_text",sameWords(shownWords,approvedWords),{shown:shownWords.length,approved:approvedWords.length,first_difference:differs<0?null:{index:differs,shown:shownWords[differs],approved:approvedWords[differs]}});
  };
  const checkFooterLink=async (opened,note)=>{
    const links=await opened.locator('footer a[href="/privacy"]').evaluateAll(items=>items.map(item=>({text:item.textContent.trim(),page:item.dataset.page,shown:item.offsetParent!==null})));
    if(links.length===1&&links[0].shown)await opened.locator('footer a[href="/privacy"]').click();
    const state=await privacyState(opened);
    note("the_footer_links_to_the_privacy_notice_from_the_homepage",links.length===1&&links[0].shown&&links[0].page==="privacy"&&state.path==="/privacy"&&JSON.stringify(state.views)===JSON.stringify(["privacy"])&&namesTheOperator(state.text),{links,path:state.path,views:state.views});
  };
  const directPrivacy=await page.request.get(fixture.base+"/privacy",{maxRedirects:0});
  check("privacy_notice_is_served_on_a_direct_visit",directPrivacy.status()===200&&(directPrivacy.headers()["content-type"]||"").startsWith("text/html"),{status:directPrivacy.status(),content_type:directPrivacy.headers()["content-type"]||""});
  {const {page:opened}=await openAt("/privacy");await checkPrivacyNotice(opened,check);
    await opened.screenshot({path:output.replace(/\.json$/,"-privacy-desktop.png"),fullPage:true});
    await opened.setViewportSize({width:360,height:1000});await opened.screenshot({path:output.replace(/\.json$/,"-privacy-mobile.png"),fullPage:true});await opened.close();}
  {const {page:opened}=await openAt("/");await checkFooterLink(opened,check);await opened.close();}
  check("privacy_checks_reject_a_page_without_the_operator_or_with_a_changed_word",!namesTheOperator(("Operator: "+privacyOperator+", "+privacyAddress+".").split(privacyOperator).join("Another operator"))
    &&!namesTheOperator("Operator: "+privacyOperator+", "+privacyAddress+".")&&!sameWords(approvedWords.map(word=>word==="five"?"thirty":word),approvedWords)&&!sameWords(approvedWords.slice(1),approvedWords)&&!sameWords([],[]));
  const privacyControls=[
    {name:"remove_the_privacy_link_from_the_footer",path:"/",find:privacyLink,replacement:"",run:checkFooterLink,expected:["the_footer_links_to_the_privacy_notice_from_the_homepage"]},
    {name:"change_one_fact_in_the_served_privacy_notice",path:"/privacy",find:"five days",replacement:"thirty days",run:checkPrivacyNotice,expected:["privacy_notice_says_the_same_words_as_the_approved_text"]},
    {name:"drop_the_postal_address_from_the_served_privacy_notice",path:"/privacy",find:privacyAddress,replacement:"our office",run:checkPrivacyNotice,expected:["privacy_notice_names_the_operator_and_the_postal_contact_address","privacy_notice_says_the_same_words_as_the_approved_text"]}];
  for(const control of privacyControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,state}=await openAt(control.path,{path:control.path,find:control.find,replacement:control.replacement});applied=state.applied;await control.run(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  const homeFits=[];
  for(const width of [1440,360]){await page.setViewportSize({width,height:1000});await page.goto(fixture.base+"/");homeFits.push({width,...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1}))});}
  check("homepage_fits_a_360_pixel_screen",homeFits.length===2&&homeFits.every(item=>!item.overflow),{measurements:homeFits});
  await page.setViewportSize({width:1440,height:1000});
  /* The capabilities the service can report, for account creation, for a waiting list, for payment and for personal keys,
     each read from a real service, with the removed-guard controls for both directions and for the record version the page
     was written against. Every public action says "Get started" in every state. The state shows in the note under the hero
     action and in the one panel that leads the Get started page. */
  const expectedAccess={waiting:{state:"waiting",href:"/connect",label:"Get started",note:waitingNote},open:{state:"open",href:"/connect",label:"Get started",note:openNote}};
  const accessActions=target=>target.evaluate(()=>({note:document.getElementById("hero-access-note")?.textContent||"",
    actions:[...document.querySelectorAll("[data-access-state]")].map(item=>({id:item.id,state:item.dataset.accessState,href:item.getAttribute("href"),label:item.querySelector("[data-access-label]")?.textContent||""})).sort((left,right)=>left.id<right.id?-1:1)}));
  const sameAccess=(found,want)=>found.actions.length===3&&found.actions.every(action=>action.state===want.state&&action.href===want.href&&action.label===want.label)&&found.note===want.note;
  /* A capabilities record whose version this page was not written against may have renamed a field or given it a different meaning.
     "version" serves the real reply of a real service with its record type changed, so the careful state is checked against a known-wrong version. */
  const openPublic=async (base,mutation,version)=>{
    const opened=await context.newPage(),state={applied:false,errors:[]};
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    if(mutation)await opened.route("**/assets/service.js",async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    if(version)await opened.route("**/api/v1/capabilities",async route=>{const response=await route.fetch(),body=await response.json();body.result.record_type=version;await route.fulfill({response,json:body});});
    await opened.goto(base+"/");
    await opened.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
    return {page:opened,state};
  };
  const paymentState=async opened=>{await opened.locator('header a[data-page="pricing"]').click();return {badge:await opened.locator("#pricing-state").innerText(),shown:await opened.locator("#pricing-payment-state").innerText()};};
  /* The personal-key wording is published in two places. Both follow the reported capability; neither is written as a fact in the page. */
  const keyWording={
    open:{offer:"You can also create and revoke a key for each device from your account page.",
          plan:"Create and revoke a key for every client you connect, from your account page."},
    closed:{offer:"Creating and revoking a key for each device from your account page is being prepared. Today the person who runs the service issues your key.",
            plan:"Creating and revoking a key for every client you connect, from your account page, is being prepared. Today the person who runs the service issues your key."}};
  const keyState=async opened=>({offer:await opened.locator("#offer-usage-keys").evaluate(node=>node.textContent),plan:await opened.locator("#plan-keys-detail").evaluate(node=>node.textContent)});
  const sameKeys=(keys,want)=>keys.offer===want.offer&&keys.plan===want.plan;
  /* The waiting list is an offer, and the pricing page lists unfinished work that names its form. Both follow the reported
     capability, read only from the record version this page was written against, so the page never offers the form and calls it
     unfinished at once, and a record version it was not written for offers nothing. */
  const waitlistWording={pending:{offered:false,unfinished:"Public account creation, the waiting list form and complete native client onboarding are not finished."},
                         offered:{offered:true,unfinished:"Public account creation and complete native client onboarding are not finished."}};
  const waitlistClaims=async opened=>{await paymentState(opened);return opened.evaluate(()=>{
    const shown=id=>{const node=document.getElementById(id);return node?!node.hidden:null;},unfinished=document.getElementById("pricing-in-progress");
    return {form:shown("waitlist-form"),signup_link:shown("signup-waitlist-link"),pending_note:shown("waiting-list-pending"),
      unfinished:unfinished?unfinished.innerText.split(". ")[0]+".":null};});};
  const sameWaitlistClaims=(claims,want)=>claims.form===want.offered&&claims.signup_link===want.offered
    &&claims.pending_note===!want.offered&&claims.unfinished===want.unfinished;
  const carefulState=async (opened,note,name)=>{
    const actions=await accessActions(opened),keys=await keyState(opened),payment=await paymentState(opened),lead=await openGetStarted(opened);
    note(name,sameAccess(actions,expectedAccess.waiting)&&payment.badge==="Payment not open"&&sameKeys(keys,keyWording.closed)&&sameLead(lead,"operator"),{actions,payment,keys,lead});
  };
  /* The actions a visitor reaches first: the homepage, the pricing view and the Get started page, in that order. */
  const journeyActionProblems=async (opened,registrationOpen)=>{
    const problems=[];
    for(const selector of [null,'header a[data-page="pricing"]','header nav a[data-page="setup"]']){if(selector)await opened.locator(selector).click();problems.push(...accessActionProblems(await publicActions(opened),registrationOpen));}
    return problems;
  };
  const scenarios={
    closed_service:{origin:"base",run:async (opened,note)=>{
      const actions=await accessActions(opened),keys=await keyState(opened);
      note("public_actions_say_get_started_while_registration_is_closed",sameAccess(actions,expectedAccess.waiting),actions);
      note("personal_key_claim_is_held_back_when_the_service_reports_no_client_access",sameKeys(keys,keyWording.closed),keys);
      const journey=await journeyActionProblems(opened,false);
      note("no_public_action_offers_a_second_label_or_account_creation_while_registration_is_closed",journey.length===0,{problems:journey});
      const lead=await startLead(opened);
      note("get_started_leads_with_the_operator_when_the_service_offers_neither",sameLead(lead,"operator"),lead);
      const payment=await paymentState(opened);
      note("pricing_view_says_payment_is_closed_when_the_service_reports_no_checkout",payment.badge==="Payment not open"&&payment.shown.includes("not open yet"),payment);
      const claims=await waitlistClaims(opened);
      note("unfinished_work_names_the_waiting_list_form_while_the_service_offers_no_list",sameWaitlistClaims(claims,waitlistWording.pending),claims);
    }},
    waitlist_offered:{origin:"account_base",run:async (opened,note)=>{
      const journey=await journeyActionProblems(opened,false);
      note("no_public_action_offers_a_second_label_or_account_creation_while_a_list_is_kept",journey.length===0,{problems:journey});
      const lead=await startLead(opened);
      note("get_started_leads_with_the_invitation_form_when_the_service_keeps_a_list",sameLead(lead,"invite"),lead);
      const claims=await waitlistClaims(opened);
      note("unfinished_work_drops_the_waiting_list_form_once_the_service_offers_a_list",sameWaitlistClaims(claims,waitlistWording.offered),claims);
    }},
    unsupported_version_waitlist:{origin:"account_base",version:"service_capabilities/v2",run:async (opened,note)=>{
      const claims=await waitlistClaims(opened),lead=await openGetStarted(opened);
      note("unsupported_capabilities_version_keeps_the_careful_state_over_the_waiting_list",sameWaitlistClaims(claims,waitlistWording.pending)&&sameLead(lead,"operator"),{claims,lead});
    }},
    open_registration:{origin:"signup_base",run:async (opened,note)=>{
      const actions=await accessActions(opened);
      note("public_actions_say_get_started_while_registration_is_open",sameAccess(actions,expectedAccess.open),actions);
      const journey=await journeyActionProblems(opened,true);
      note("no_public_action_offers_account_creation_outside_the_get_started_and_account_pages",journey.length===0,{problems:journey});
      const lead=await startLead(opened);
      note("get_started_leads_with_account_creation_when_registration_is_open",sameLead(lead,"register"),lead);
    }},
    open_checkout:{origin:"billing_base",run:async (opened,note)=>{
      const payment=await paymentState(opened);
      note("pricing_view_says_payment_is_open_when_the_service_reports_checkout",payment.badge==="Payment open"&&payment.shown.includes("Payment is open"),payment);
    }},
    client_access:{origin:"account_base",run:async (opened,note)=>{
      const keys=await keyState(opened);
      note("personal_key_claim_appears_when_the_service_reports_client_access",sameKeys(keys,keyWording.open),keys);
    }},
    unsupported_version_registration:{origin:"signup_base",version:"service_capabilities/v2",
      run:(opened,note)=>carefulState(opened,note,"unsupported_capabilities_version_keeps_the_careful_state_over_registration")},
    unsupported_version_checkout:{origin:"billing_base",version:"service_capabilities/v2",
      run:(opened,note)=>carefulState(opened,note,"unsupported_capabilities_version_keeps_the_careful_state_over_checkout")},
    unsupported_version_client_access:{origin:"account_base",version:"service_capabilities/v2",
      run:(opened,note)=>carefulState(opened,note,"unsupported_capabilities_version_keeps_the_careful_state_over_client_access")}};
  const publicOrigins=["base","signup_base","billing_base","account_base"];
  const reported=[];
  for(const name of publicOrigins){const value=(await (await page.request.get(fixture[name]+"/api/v1/capabilities")).json()).result;reported.push({name,record_type:value.record_type,registration:value.website.registration_available,checkout:value.billing.checkout,client_access:value.website.client_access_available});}
  check("the_public_states_are_reported_by_real_services",JSON.stringify(reported)===JSON.stringify([
    {name:"base",record_type:"service_capabilities/v1",registration:false,checkout:false,client_access:false},
    {name:"signup_base",record_type:"service_capabilities/v1",registration:true,checkout:false,client_access:false},
    {name:"billing_base",record_type:"service_capabilities/v1",registration:false,checkout:true,client_access:false},
    {name:"account_base",record_type:"service_capabilities/v1",registration:false,checkout:false,client_access:true}]),{reported});
  for(const name of Object.keys(scenarios)){
    const scenario=scenarios[name],{page:opened}=await openPublic(fixture[scenario.origin],null,scenario.version);
    await scenario.run(opened,check);await opened.close();
  }
  /* Every public page on three real services: one that offers neither registration nor a list, one that keeps a waiting list,
     and one with registration open. The known-wrong page after it plants one wrong action at a time into the real homepage. */
  const actionScan=[];
  for(const [name,registrationOpen] of [["base",false],["account_base",false],["signup_base",true]]){
    const scanned=await context.newPage();scanned.on("pageerror",error=>errors.push(safeError(error.message)));
    for(const path of accessJourneyPaths){
      await scanned.goto(fixture[name]+path);
      await scanned.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability");
      actionScan.push({origin:name,path,problems:accessActionProblems(await publicActions(scanned),registrationOpen)});
    }
    await scanned.close();
  }
  check("every_public_page_offers_one_call_to_action_and_nothing_the_service_cannot_honour",actionScan.length===3*accessJourneyPaths.length&&actionScan.every(item=>item.problems.length===0),{problems:actionScan.filter(item=>item.problems.length)});
  const knownWrong=await context.newPage();knownWrong.on("pageerror",error=>errors.push(safeError(error.message)));
  await knownWrong.goto(fixture.base+"/");await knownWrong.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
  const plantedAction=async (text,href,place)=>{
    const planted=await knownWrong.evaluate(([text,href,place])=>{const target=document.querySelector(place);if(!target)return false;const link=document.createElement("a");link.id="known-wrong-action";link.href=href;link.textContent=text;target.append(link);return true;},[text,href,place]);
    const problems=accessActionProblems(await publicActions(knownWrong),false);
    await knownWrong.evaluate(()=>document.getElementById("known-wrong-action")?.remove());
    return planted?problems:["(the known-wrong action could not be planted)","(so this case proves nothing)"];
  };
  const secondLabel=await plantedAction("Join the waiting list","/waitlist",'[data-view="home"] .hero-actions');
  const creationWhileClosed=await plantedAction("Create your account","/signup",'[data-view="home"] .closing-actions');
  const invitationOutside=await plantedAction("Ask for an invitation","/connect",'[data-view="home"] .pricing-teaser-side');
  await knownWrong.close();
  check("access_action_check_rejects_a_second_label_account_creation_and_an_invitation_outside_its_form",secondLabel.length===2&&creationWhileClosed.length===1&&invitationOutside.length===2,{secondLabel,creationWhileClosed,invitationOutside});
  const versionGate="if (value.record_type === CAPABILITIES_RECORD_TYPE) {";
  const waitlistGate="const open = value?.record_type === CAPABILITIES_RECORD_TYPE && value.website?.waitlist_available === true;";
  const registrationLead='website.registration_available === true ? "register"',invitationLead='website.waitlist_available === true ? "invite"';
  const publicControls=[
    {name:"always_offer_sign_up",scenario:"closed_service",find:"applyAccessState(value.website.registration_available === true);",replacement:"applyAccessState(true);",expected:["public_actions_say_get_started_while_registration_is_closed"]},
    {name:"never_offer_sign_up",scenario:"open_registration",find:"applyAccessState(value.website.registration_available === true);",replacement:"applyAccessState(false);",expected:["public_actions_say_get_started_while_registration_is_open"]},
    {name:"bring_back_the_waiting_list_label",scenario:"closed_service",find:'waiting:{label:"Get started"',replacement:'waiting:{label:"Join the waiting list"',expected:["public_actions_say_get_started_while_registration_is_closed","no_public_action_offers_a_second_label_or_account_creation_while_registration_is_closed"]},
    {name:"always_lead_with_account_creation",scenario:"closed_service",find:registrationLead,replacement:'true ? "register"',expected:["get_started_leads_with_the_operator_when_the_service_offers_neither","no_public_action_offers_a_second_label_or_account_creation_while_registration_is_closed"]},
    {name:"never_lead_with_account_creation",scenario:"open_registration",find:registrationLead,replacement:'false ? "register"',expected:["get_started_leads_with_account_creation_when_registration_is_open"]},
    {name:"never_lead_with_the_invitation_form",scenario:"waitlist_offered",find:invitationLead,replacement:'false ? "invite"',expected:["get_started_leads_with_the_invitation_form_when_the_service_keeps_a_list"]},
    {name:"always_say_payment_is_open",scenario:"closed_service",find:"applyPaymentState(value.billing.checkout === true);",replacement:"applyPaymentState(true);",expected:["pricing_view_says_payment_is_closed_when_the_service_reports_no_checkout"]},
    {name:"never_say_payment_is_open",scenario:"open_checkout",find:"applyPaymentState(value.billing.checkout === true);",replacement:"applyPaymentState(false);",expected:["pricing_view_says_payment_is_open_when_the_service_reports_checkout"]},
    {name:"always_claim_personal_keys",scenario:"closed_service",find:"applyClientAccessState(value.website.client_access_available === true);",replacement:"applyClientAccessState(true);",expected:["personal_key_claim_is_held_back_when_the_service_reports_no_client_access"]},
    {name:"never_claim_personal_keys",scenario:"client_access",find:"applyClientAccessState(value.website.client_access_available === true);",replacement:"applyClientAccessState(false);",expected:["personal_key_claim_appears_when_the_service_reports_client_access"]},
    {name:"ignore_the_capabilities_record_version",scenario:"unsupported_version_registration",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_registration"]},
    {name:"ignore_the_record_version_over_payment",scenario:"unsupported_version_checkout",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_checkout"]},
    {name:"ignore_the_record_version_over_personal_keys",scenario:"unsupported_version_client_access",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_client_access"]},
    {name:"ignore_the_record_version_over_the_waiting_list",scenario:"unsupported_version_waitlist",find:waitlistGate,replacement:"const open = value?.website?.waitlist_available === true;",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_the_waiting_list"]},
    {name:"keep_calling_the_offered_waiting_list_form_unfinished",scenario:"waitlist_offered",find:'$("in-progress-waitlist").hidden = open;',replacement:'$("in-progress-waitlist").hidden = false;',expected:["unfinished_work_drops_the_waiting_list_form_once_the_service_offers_a_list"]},
    {name:"keep_saying_the_offered_waiting_list_form_is_being_built",scenario:"waitlist_offered",find:'$("waiting-list-pending").hidden = open;',replacement:'$("waiting-list-pending").hidden = false;',expected:["unfinished_work_drops_the_waiting_list_form_once_the_service_offers_a_list"]},
    {name:"stop_naming_the_waiting_list_form_as_unfinished_before_it_is_offered",scenario:"closed_service",find:'$("in-progress-waitlist").hidden = open;',replacement:'$("in-progress-waitlist").hidden = true;',expected:["unfinished_work_names_the_waiting_list_form_while_the_service_offers_no_list"]}];
  for(const control of publicControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);},scenario=scenarios[control.scenario];
    let applied=false,problem="";
    try{const {page:changed,state}=await openPublic(fixture[scenario.origin],{find:control.find,replacement:control.replacement},scenario.version);applied=state.applied;await scenario.run(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  /* Removed-guard controls for the benefit list. The served script is changed in memory only, never a source file.
     Each control takes away one way of reaching a detail, or the rule that closes the others, and must fail a named
     check. Together they show that a mouse, a keyboard and a touch screen each have their own path to the detail. */
  const benefitControls=[
    {name:"never_open_a_benefit_on_a_press",find:'title.addEventListener("click", () => openBenefit(name));',expected:["pressing_a_benefit_shows_only_its_own_detail"]},
    {name:"never_open_a_benefit_on_keyboard_focus",find:'title.addEventListener("focus", () => openBenefit(name));',expected:["keyboard_focus_alone_opens_each_benefit"]},
    {name:"never_open_a_benefit_when_it_is_pointed_at",find:'benefitItem(title).addEventListener("mouseenter", () => openBenefit(name));',expected:["pointing_at_a_benefit_opens_it"]},
    {name:"leave_every_benefit_open_at_once",find:"benefitDetail(title).hidden = !open;",replacement:"benefitDetail(title).hidden = false;",expected:["pressing_a_benefit_shows_only_its_own_detail","keyboard_focus_alone_opens_each_benefit","pointing_at_a_benefit_opens_it"]},
    {name:"stop_saying_which_benefit_is_open",find:'title.setAttribute("aria-expanded", String(open));',expected:["pressing_a_benefit_shows_only_its_own_detail"]}];
  for(const control of benefitControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,state}=await openPublic(fixture.base,{find:control.find,replacement:control.replacement??"void 0;"});applied=state.applied;await checkBenefitList(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  /* The careful state must be what the service serves, not only what the page script reaches. A visitor without JavaScript reads the served text. */
  const servedHome=await (await page.request.get(fixture.base+"/")).text();
  /* The careful access state is the operator's panel leading the Get started page, with the invitation form and the account
     action held back, and the note under the hero action written for closed registration. */
  const carefulDefaults=["Payment not open","Payment is not open yet. Nothing on this page charges you today, and invited accounts stay free.",
    "Payment is not open yet. Nothing on this page charges you today.",'data-start-access="operator"',waitingNote,keyWording.closed.offer,keyWording.closed.plan];
  const unsettled=/Checking payment|Checking whether payment is open/;
  const carefulProblems=text=>[...carefulDefaults.filter(value=>!text.includes(value)),...(unsettled.test(text)?["an unsettled placeholder"]:[])];
  check("served_page_defaults_to_the_careful_public_state",carefulProblems(servedHome).length===0,{problems:carefulProblems(servedHome)});
  const wrongDefault=servedHome.split(carefulDefaults[0]).join("Checking payment").split(carefulDefaults[1]).join("Checking whether payment is open.");
  check("careful_default_check_rejects_a_served_page_that_never_settles",carefulProblems(wrongDefault).length>=3,{problems:carefulProblems(wrongDefault)});
  /* One plain-word rule, used by the workspace check and by the hosted check. A copy that drifts is a named failure, not a silent disagreement. */
  const namedRule=(path,name)=>{const found=readFileSync(resolve(root,path),"utf8").match(new RegExp("^\\s*const "+name+"=(\\/.+\\/i);$","m"));return found?found[1]:"";};
  const ruleSource=path=>namedRule(path,"internalTerms");
  const workspaceRule=ruleSource("tools/check_service_workspace.mjs"),hostedRule=ruleSource("tools/check_hosted_website.mjs");
  check("both_public_page_checks_use_one_plain_word_rule",workspaceRule!==""&&workspaceRule===hostedRule&&workspaceRule===String(internalTerms),{workspace:workspaceRule,hosted:hostedRule});
  check("plain_word_rule_comparison_rejects_a_drifted_copy",workspaceRule!==workspaceRule.replace("role profile","role profiles")&&workspaceRule!==workspaceRule.replace("| Engine","")&&internalTerms.test("See the role profiles.")&&internalTerms.test("Read the role profile."));
  /* The retired words are read twice as well, here from the source tree and in the hosted check from the deployed
     pages. The two rules had drifted: this one carried pilot and beta only while the hosted one also carried early
     access, so a homepage offering early access passed here and was caught only after a deployment. */
  const workspaceRetired=namedRule("tools/check_service_workspace.mjs","retiredAccessWords"),hostedRetired=namedRule("tools/check_hosted_website.mjs","liveRetired");
  check("both_public_page_checks_use_one_retired_word_rule",workspaceRetired!==""&&workspaceRetired===hostedRetired&&workspaceRetired===String(retiredAccessWords),{workspace:workspaceRetired,hosted:hostedRetired});
  const droppedBranch=workspaceRetired.replace("|early access","");
  check("retired_word_rule_comparison_rejects_a_drifted_copy",droppedBranch!==workspaceRetired&&!new RegExp(droppedBranch.slice(1,-2),"i").test("Request early access from your account page.")&&retiredAccessWords.test("Request early access from your account page."),{dropped:droppedBranch});
  await page.goto(fixture.base+"/");
  await page.locator("#hero-how-it-works").click();
  /* The four persistent layers and the five customer problems moved off the homepage, which sells, on to How it works,
     which explains. Both are still shown to a customer, and both are checked where they now live. */
  check("all_four_persistent_intelligence_layers_are_visible",await page.locator('[data-view="about"] [data-intelligence-layer]').count()===4&&await page.getByRole("heading",{name:"Context Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"Code Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"Runtime History and Solution Intelligence",exact:true}).isVisible()&&await page.getByRole("heading",{name:"User Feedback Intelligence",exact:true}).isVisible());
  check("all_five_owner_pain_points_are_present",JSON.stringify(await page.locator('[data-view="about"] [data-friction]').evaluateAll(items=>items.map(item=>item.dataset.friction).sort()))===JSON.stringify(["context","expertise","learning","model","reuse"])&&await page.locator(".friction-section").isVisible());
  check("the_homepage_no_longer_carries_the_explanation_sections",await page.locator('[data-view="home"] [data-intelligence-layer]').count()===0&&await page.locator('[data-view="home"] [data-friction]').count()===0);
  check("technical_layer_definitions_remain_in_documentation",(await page.locator('[data-view="docs"] [data-layer-notes]').textContent()).includes("not a fifth persistent layer")&&(await page.locator('[data-view="docs"] [data-layer-notes]').textContent()).includes("temporary note board"));
  const boundary=page.locator('[data-view="about"] .boundary-figure');
  check("hosted_service_and_local_execution_have_distinct_responsibilities",(await boundary.locator(".service-zone").innerText()).includes("Check your access")&&(await boundary.locator(".client-zone").innerText()).includes("Set the goal and limits")&&await boundary.locator(".boundary-zone").count()===2);
  check("client_server_exchange_names_sent_and_returned_data",(await boundary.locator(".boundary-exchange").innerText()).includes("Relevant help or a selected file")&&(await boundary.locator(".boundary-exchange").innerText()).includes("Matching results or the permitted download"));
  check("external_model_connection_is_separate_from_intelligence_service",(await boundary.locator(".provider-lane").innerText()).includes("Model keys stay in your environment"));
  check("benefits_are_explicit_without_invented_benchmark_numbers",await page.locator(".friction-grid article").count()===5&&!(await page.locator(".friction-section").innerText()).match(/\d+\s*%/)&&!(await page.locator('[data-view="about"]').innerText()).match(/\d+\s*%/));
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
  /* The page may refuse the reviewed record. The wait accepts that state, the refusal is reported by name with its code, and the checks that need a shown recipe are skipped by name. */
  await page.goto(fixture.base+"/connect"); await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled||document.querySelector("#setup-message").textContent!=="");
  const reviewedState=await connectState(page),skipped={skipped:"the page did not show the reviewed recipe record",refusal:reviewedState.refusal||"unavailable"};
  check("reviewed_recipe_record_is_accepted_by_the_page",reviewedState.shown&&reviewedState.refusal==="",{refusal:reviewedState.refusal});
  check("guided_setup_uses_current_origin_and_no_embedded_token",(await page.locator("#client-configuration").innerText()).includes(fixture.base+"/mcp")&&!(await page.locator("#client-configuration").innerText()).includes(fixture.token));
  check("anonymous_protocol_test_is_disabled",await page.locator("#test-protocol").isDisabled());
  await page.screenshot({path:output.replace(/\.json$/,"-connect-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:output.replace(/\.json$/,"-connect-mobile.png"),fullPage:true});await page.setViewportSize({width:1440,height:1000});
  if(reviewedState.shown){
    await page.selectOption("#client-choice","opencode");
    const recipe=JSON.parse(await page.locator("#client-configuration").innerText());
    check("client_selection_changes_real_secret_free_configuration",recipe.mcp.baltor.url===fixture.base+"/mcp"&&recipe.mcp.baltor.oauth===false&&recipe.mcp.baltor.headers.Authorization==="Bearer {env:BALTOR_SERVICE_TOKEN}");
  }else check("client_selection_changes_real_secret_free_configuration",false,skipped);
  /* Connection recipes: every reviewed recipe, the known-wrong records, the serving origins and the removed-guard controls. */
  const checkConnectionRecipes=async()=>{
  const recipeContext=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
  await recipeContext.grantPermissions(["clipboard-read","clipboard-write"]);await recipeContext.route("**/*",localOnly);routeBrowseAsset(recipeContext);
  check("no_key_check_separates_keys_from_variable_references",keyShaped(fixture.token)&&keyShaped("Bearer "+plantedKey)&&keyShaped("Bearer secret")&&!keyShaped("Bearer {env:"+variable+"}")&&!keyShaped("Bearer ${"+variable+"}")&&!keyShaped(variable));
  let sameAddress=null;try{sameAddress=[schemeOnly,withBackslashes].every(text=>new URL(text).href===otherOrigin);}catch(_){sameAddress=false;}
  check("known_wrong_addresses_reach_another_host_in_a_client_address_parser",sameAddress===true&&otherOrigin!==fixture.base+"/mcp",{forms:2});
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
  check("known_wrong_records_have_distinct_names",new Set(allWrong.map(wrong=>wrong.name)).size===allWrong.length,{records:allWrong.length});
  for(const wrong of allWrong)await checkRefusedRecord(recipeContext,fixture.base,check,wrong);
  const wrongShown=JSON.stringify(withEndpoint(wrongCredentials[0].served.recipes.find(item=>item.id==="claude-code").configuration,fixture.base+"/mcp"),null,2);
  check("no_key_check_fails_for_a_recipe_with_an_embedded_key",keyShaped(wrongShown.replaceAll(fixture.base+"/mcp","").replaceAll(variable,""))&&wrongShown.includes(plantedKey));
  const followed=[],servingOrigins=[fixture.billing_base,fixture.account_base];
  for(const origin of servingOrigins){
    const {page:other}=await openConnect(recipeContext,origin);
    for(const item of recipeRecord.recipes){
      await other.selectOption("#client-choice",item.id);
      const text=await other.locator("#client-configuration").evaluate(node=>node.textContent),value=item.format==="toml"?readToml(text):JSON.parse(text),targets=textLeaves(value).filter(([key])=>key==="url");
      followed.push(targets.length===1&&targets[0][1]===origin+"/mcp"&&!text.includes(fixture.base));
    }
    await other.close();
  }
  /* The count of origins is part of the assertion, so removing one of them fails this check instead of leaving it green with a smaller denominator. */
  check("recipes_follow_the_origin_that_serves_the_page",servingOrigins.length===2&&followed.length===servingOrigins.length*recipeRecord.recipes.length&&followed.every(Boolean),{origins:servingOrigins.length,recipes:recipeRecord.recipes.length,followed});
  /* Removed-guard controls. The served script is changed in memory only. A control is detected only when every one of its records fails its own named checks:
     the refusal check, and the display check when the record plants its text in a shown field. The first three controls remove a whole rule. Each later control
     removes one clause of a rule and serves the records that only this clause refuses, so a clause cannot be deleted while another clause hides the loss. */
  const collect=()=>{const failed=new Set();return {failed,note:(name,passed)=>{if(passed!==true)failed.add(name);}};};
  const refusedWithout=wrongRecords=>async mutation=>{const runs=[];for(const wrong of wrongRecords){const {failed,note}=collect(),state=await checkRefusedRecord(recipeContext,fixture.base,note,wrong,mutation);runs.push({state,failed,expected:[wrong.name,...(wrong.display?[wrong.display]:[])]});}return runs;};
  const controls=[
    {name:"remove_recipe_credential_rule",find:'return "credential_rule";',run:refusedWithout(wrongCredentials)},
    {name:"remove_recipe_address_rule",find:'return "address_rule";',run:refusedWithout(wrongAddresses)},
    {name:"accept_unsupported_recipe_records",find:'return "unsupported_record";',run:refusedWithout(unsupportedRecords)},
    {name:"copy_other_text_than_shown",find:'writeText($("client-configuration").textContent)',replacement:'writeText("")',run:async mutation=>{const {failed,note}=collect(),{page:changed,state}=await openConnect(recipeContext,fixture.base,{mutation});for(const item of recipeRecord.recipes)await checkShownRecipe(changed,fixture.base,recipeRecord,item,note);await changed.close();return [{state,failed,expected:recipeRecord.recipes.map(item=>"recipe_copy_matches_displayed_text_"+item.id)}];}},
    {name:"scan_only_the_displayed_fields_for_keys",find:'recipeStrings(record).some(',replacement:'recipeStrings([record.revocation_note, record.recipes]).some(',run:refusedWithout(wrongNamed("record_with_key_in_a_field_that_is_not_displayed_is_refused","record_with_key_in_an_unknown_field_is_refused"))},
    {name:"accept_a_key_shaped_variable_name",find:'tokenShaped(variable) || ',replacement:'',run:refusedWithout(wrongNamed("recipe_with_key_shaped_variable_name_is_refused"))},
    {name:"look_for_keys_in_one_alphabet_only",find:'|| (text.match(/[A-Za-z0-9+\\/=]{20,}/g) || []).some(run => /[+=]/.test(run) && mixedRun(run))',replacement:'',run:refusedWithout(wrongNamed("recipe_with_key_in_the_standard_alphabet_is_refused"))},
    {name:"treat_header_values_as_ordinary_text",find:'item.path.some(name => credentialTable.test(name)) || ',replacement:'',run:refusedWithout(wrongNamed("recipe_with_literal_in_a_second_header_is_refused","recipe_with_literal_in_an_environment_table_is_refused"))},
    {name:"accept_a_literal_under_a_credential_name",find:'item.path.some(namesCredential) || ',replacement:'',run:refusedWithout(wrongNamed("recipe_with_short_literal_under_a_credential_name_is_refused","recipe_with_number_under_a_credential_name_is_refused"))},
    {name:"accept_an_address_that_is_not_the_placeholder",find:'entry.url !== endpointPlaceholder',replacement:'false',run:refusedWithout(wrongNamed("recipe_with_plain_host_name_as_its_address_is_refused"))},
    {name:"accept_the_placeholder_under_a_second_name",find:'values.filter(item => item.key === "url" || item.text.includes("{{")).length !== 1',replacement:'false',run:refusedWithout(wrongNamed("recipe_with_the_placeholder_under_a_second_name_is_refused"))},
    {name:"accept_any_table_inside_the_server_entry",find:'Object.entries(entry).some(([name, item]) => isTable(item) && !credentialTable.test(name))',replacement:'false',run:refusedWithout(wrongNamed("recipe_with_a_table_of_other_settings_inside_the_server_entry_is_refused"))},
    {name:"accept_a_list_in_a_configuration",find:'!settingsOnly(recipe.configuration)',replacement:'false',run:refusedWithout(wrongNamed("recipe_with_a_list_of_command_arguments_is_refused"))},
    {name:"accept_any_command_line",find:'!plainCommand.test(recipe.verification_command) || ',replacement:'',run:refusedWithout(wrongNamed("recipe_with_a_command_line_that_is_not_plain_words_is_refused"))},
    {name:"accept_more_than_one_server_entry",find:'if (inner.length !== 1) return null;',replacement:'',run:refusedWithout(wrongNamed("recipe_with_second_server_entry_that_runs_a_command_is_refused"))},
    {name:"accept_any_text_beside_the_address",find:'!settingWord.test(item.text)',replacement:'false',run:refusedWithout(wrongNamed("recipe_with_scheme_only_address_under_another_name_is_refused"))},
    {name:"accept_a_schema_address_anywhere",find:'item.path.length === 1 && ',replacement:'',run:refusedWithout(wrongNamed("recipe_with_a_schema_address_of_its_cited_host_inside_the_server_entry_is_refused"))},
    {name:"accept_any_schema_address",find:'item.key === "$schema" && plainHttps(item.text)',replacement:'item.key === "$schema"',run:refusedWithout(wrongNamed("recipe_with_user_information_in_its_schema_address_is_refused"))},
    {name:"accept_a_schema_address_on_another_host",find:' && sameHost(item.text, recipe.source_url)',replacement:'',run:refusedWithout(wrongSchemas)},
  ];
  for(const control of controls){
    let runs=[],problem="";
    try{runs=await control.run({find:control.find,replacement:control.replacement??"void 0;"});}catch(error){problem=safeError(error);}
    const applied=runs.length>0&&runs.every(run=>run.state.applied),missed=runs.flatMap(run=>run.expected.filter(name=>!run.failed.has(name)));
    const detected=applied&&!problem&&missed.length===0,failedChecks=[...new Set(runs.flatMap(run=>[...run.failed]))].sort();
    mutants.push({name:control.name,applied,detected,required_checks:[...new Set(runs.flatMap(run=>run.expected))],missed_checks:missed,failed_checks:failedChecks,...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,records:runs.length,missed_checks:missed,failed_checks:failedChecks,...(problem?{problem}:{})});
  }
  await recipeContext.close();
  };
  if(reviewedState.shown)await checkConnectionRecipes();else check("connection_recipe_checks_ran",false,skipped);
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
    for(const path of ["/","/login","/signup","/pricing","/account","/admin","/app","/docs","/how-it-works","/connect","/examples","/security","/privacy","/waitlist"]){
      await page.goto(fixture.base+path);
      const measurement=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(x=>!x.hidden).length}));
      check(`responsive_${width}_${path}`,!measurement.overflow&&measurement.views===1,measurement);
    }
  }
  for(const width of [1440,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/","/how-it-works","/pricing","/connect","/examples","/security","/privacy"]){
      await page.goto(fixture.base+path); await page.evaluate(()=>document.documentElement.style.fontSize="200%");
      const enlarged=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length,items:[...document.querySelectorAll("body *")].filter(item=>{const box=item.getBoundingClientRect();return box.width&&box.right>innerWidth+1;}).slice(0,12).map(item=>({tag:item.tagName,id:item.id,className:String(item.className)}))}));
      check(`enlarged_text_${width}_${path}`,!enlarged.overflow&&enlarged.views===1,enlarged);
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
  await page.waitForFunction(()=>!document.querySelector("#client-choice").disabled||document.querySelector("#setup-message").textContent!=="");
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
  /* The waiting list is offered only where the service keeps one. The first service has none; the account service has one. The
     form leads the Get started page, which every page reaches through the "Get started" item of the navigation, and the older
     address /waitlist opens the same page. */
  await page.setViewportSize({width:1440,height:1000});
  await page.goto(fixture.base+"/waitlist"); await page.waitForFunction(()=>document.querySelector("#waitlist-state").textContent!=="Checking availability");
  check("a_service_without_a_waiting_list_makes_no_offer",await page.locator('[data-view="setup"]').isVisible()&&await page.locator("#waitlist-form").isHidden()&&await page.locator("#start-invite").isHidden()&&await page.locator("#waitlist-closed").isVisible()&&await page.locator("#waitlist-discount").isHidden());
  await page.goto(fixture.base+"/signup");
  check("a_service_without_a_waiting_list_does_not_offer_it_on_the_registration_page",await page.locator("#signup-waitlist-link").isHidden());
  await page.goto(fixture.account_base+"/pricing"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
  await page.locator('header nav a[data-page="setup"]').click();
  check("a_service_with_a_waiting_list_leads_the_get_started_page_with_the_form",new URL(page.url()).pathname==="/connect"&&await page.locator("#waitlist-form").isVisible()&&await page.locator("#waitlist-closed").isHidden()&&sameLead(await startLead(page),"invite"));
  await page.goto(fixture.account_base+"/waitlist"); await page.waitForSelector("#waitlist-form",{state:"visible"});
  check("the_waiting_list_address_opens_the_same_get_started_page",new URL(page.url()).pathname==="/waitlist"&&await page.locator('[data-view="setup"]').isVisible()&&await page.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length)===1&&(await page.title()).endsWith("| Get started"));
  check("the_discount_is_named_only_where_checkout_takes_a_code",await page.locator("#waitlist-discount").isHidden(),{discount_code:(await (await page.request.get(fixture.account_base+"/api/v1/capabilities")).json()).result.billing.discount_code});
  await page.fill("#waitlist-email","browser.request@example.invalid"); await page.fill("#waitlist-note","My agents rebuild the same checks on every task.");
  await page.click("#waitlist-button"); await page.waitForFunction(()=>document.querySelector("#waitlist-message").textContent.startsWith("Thank you"));
  check("a_visitor_leaves_an_address_and_is_told_a_person_will_read_it",await page.locator("#waitlist-form").isHidden()&&(await page.locator("#waitlist-state").innerText())==="Request received"&&!(await page.locator("#waitlist-message").innerText()).includes("browser.request@example.invalid"));
  const listed=await page.request.get(fixture.account_base+"/api/v1/admin/waitlist",{headers:{Authorization:"Bearer "+fixture.account_admin_token}});
  const entries=listed.status()===200?(await listed.json()).result.entries:[];
  check("the_address_the_visitor_typed_reached_the_service_record",listed.status()===200&&entries.length===1&&entries[0].email==="browser.request@example.invalid"&&entries[0].state==="waiting",{status:listed.status(),entries:entries.length});
  await page.goto(fixture.account_base+"/waitlist"); await page.waitForSelector("#waitlist-form:not([hidden])");
  await page.fill("#waitlist-email","browser.request@example.invalid"); await page.click("#waitlist-button");
  await page.waitForFunction(()=>document.querySelector("#waitlist-message").textContent.includes("already on the list"));
  check("a_second_request_from_the_same_address_is_told_the_truth",await page.locator("#waitlist-form").isVisible());
  /* Browsing the four groups. The page is never allowed to agree with itself: every group, count and
     filtered list is compared with a real reply from the same service, read with the same credential
     through a separate request. The known-wrong cases sit beside the states they refuse. */
  const plainContext=await browser.newContext();
  const servedAsset=await plainContext.request.get(fixture.browse_base+"/assets/catalogue-browser.js");
  const servedAssetText=servedAsset.status()===200?await servedAsset.text():"";
  check("catalogue_browser_asset_is_served",servedAsset.status()===200&&(servedAsset.headers()["content-type"]||"").includes("javascript")&&servedAssetText===browseSource,
    {status:servedAsset.status(),same_bytes_as_the_source_file:servedAssetText===browseSource});
  /* Every internal address the page names, asked for over the running service. A script the service does
     not serve is worse than a broken link: the request falls through to the interface router and comes
     back as a refusal, so the page loads and then quietly does nothing. That is exactly how the browsing
     module first shipped. The addresses are read from the page the service sent, so a script, stylesheet
     or image added later is covered on the day it is added, with no list to keep up to date here. */
  const internalAddresses=text=>[...new Set([...text.matchAll(/(?:href|src)="(\/[^"#?]*)"/g)].map(found=>found[1]))]
    .filter(value=>!value.startsWith("/api/")&&!value.startsWith("/.well-known/")&&value!=="/mcp");
  const servedPage=await plainContext.request.get(fixture.browse_base+"/app");
  const pageText=servedPage.status()===200?await servedPage.text():"";
  const namedScripts=[...new Set([...pageText.matchAll(/src="(\/[^"#?]*)"/g)].map(found=>found[1]))];
  const answered=[];
  for(const address of internalAddresses(pageText)) answered.push({address,status:(await plainContext.request.get(fixture.browse_base+address)).status()});
  check("every_address_the_page_names_is_answered_by_the_service",
    answered.length>=2&&namedScripts.includes("/assets/catalogue-browser.js")&&answered.every(item=>item.status===200),
    {refused:answered.filter(item=>item.status!==200),named:answered.length,scripts:namedScripts.length});
  /* The known-wrong case for the reading above. A reading that looked at link targets only, or a service
     that answered every address with 200, would pass that check without proving anything. Here the same
     reading is given a page that names one more script, and that address is asked for over the same
     service, which must refuse it. */
  const plantedAddress="/assets/an-address-this-service-does-not-serve.js";
  const plantedPage=pageText.replace("</head>",'<script defer src="'+plantedAddress+'"></script></head>');
  const plantedStatus=(await plainContext.request.get(fixture.browse_base+plantedAddress)).status();
  check("an_address_the_page_names_but_the_service_refuses_is_found",
    internalAddresses(plantedPage).includes(plantedAddress)
    &&!internalAddresses(pageText).includes(plantedAddress)&&plantedStatus!==200,
    {status:plantedStatus,planted_is_read:internalAddresses(plantedPage).includes(plantedAddress)});
  await plainContext.close();
  const browseList=async (target,fields={})=>(await (await target.request.post(fixture.browse_base+"/api/v1/provisioning",
    {headers:{Authorization:"Bearer "+fixture.browse_token,"Content-Type":"application/json"},
     data:{record_type:"service_provisioning_request/v1",operation:"list",...fields}})).json()).result;
  /* The harness family comes first and is named for what it is: files a development tool reads as they are.
     It was named "Already on your own machine" until September 22, 2026, which was not true of a delivered file. */
  const layerNames=[["harness_local","Files for your development tools"],["context_intelligence","Guidance and methods"],
    ["code_intelligence","Reusable code and tools"],["runtime_history_solution_intelligence","What worked before"],
    ["user_feedback_intelligence","Your own instructions"]];
  const expectedGroups=(items,filtered)=>layerNames.map(([layer,name])=>{
    const held=items.filter(row=>row.source_layer===layer);
    return {layer,name,count:held.length+(held.length===1?" item":" items"),
      empty:held.length?"":(filtered?"Nothing in this group matches your filters.":"Nothing is published in this group yet."),
      identities:held.map(row=>row.identity)};
  }).filter(group=>group.layer!=="harness_local"||group.identities.length>0);
  const browseGroups=target=>target.locator("#browse-groups .browse-group").evaluateAll(items=>items.map(item=>({
    layer:item.dataset.layer,name:item.querySelector("h3").textContent,count:item.querySelector(".badge").textContent,
    empty:item.querySelector(".browse-empty")?.textContent||"",
    identities:[...item.querySelectorAll(".browse-item")].map(button=>button.dataset.identity)})));
  const browseDetail=target=>target.locator("#browse-detail dl").evaluate(node=>{
    const pairs=[];
    for(const item of node.children){if(item.tagName==="DT")pairs.push([item.textContent,""]);else pairs[pairs.length-1][1]=item.textContent;}
    return Object.fromEntries(pairs);});
  const browseStatus=page=>page.locator('#browse-detail p[role="status"]').evaluate(node=>node.textContent);
  const settleBrowse=page=>page.waitForFunction(()=>!document.querySelector("#refresh-browse").disabled);
  const loadBrowse=async page=>{await page.click("#refresh-browse");await settleBrowse(page);};
  const openItem=async (page,identity)=>{
    await page.locator('.browse-item[data-identity="'+identity+'"]').click();
    await page.waitForFunction(id=>{const panel=document.querySelector("#browse-detail");
      return panel.querySelector("p.caption")?.textContent===id&&!panel.textContent.includes("Checking this item");},identity);};
  const refusedBrowse=async (page,note,name,planted)=>{
    const groups=await browseGroups(page),message=await page.locator("#browse-message").innerText();
    note(name,groups.length===0&&await page.locator("#browse-count").innerText()==="Nothing shown"
      &&message.startsWith("This service answered with a catalogue record this page was not written for")
      &&!(await page.locator(".browse").innerText()).includes(planted),{groups:groups.length,message});};
  async function openBrowseWorkspace(mutation,holdDigest=false){
    const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true,reducedMotion:"reduce"});
    await context.route("**/*",localOnly);
    if(holdDigest)await context.addInitScript(holdDigestScript);
    const state=routeBrowseAsset(context,mutation);
    const opened=await context.newPage();
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    await opened.goto(fixture.browse_base+"/login");
    await opened.fill("#access-token",fixture.browse_token);
    await opened.click("#connect-button");
    await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
    await opened.waitForFunction(()=>!document.querySelector("#refresh-browse").disabled);
    return {context,page:opened,state};
  }
  const browseScenarios={
    catalogue:async (opened,note)=>{
      await loadBrowse(opened);
      const reply=await browseList(opened),groups=await browseGroups(opened),want=expectedGroups(reply.items,false);
      note("browse_shows_the_four_groups_with_plain_names",reply.items.length===6&&groups.length===5
        &&JSON.stringify(groups.map(item=>[item.layer,item.name]))===JSON.stringify(want.map(item=>[item.layer,item.name])),
        {shown:groups.map(item=>item.name)});
      note("browse_counts_and_membership_match_the_service_reply",JSON.stringify(groups)===JSON.stringify(want)
        &&await opened.locator("#browse-count").innerText()==="6 items",{groups,want});
      const emptyGroup=groups.find(item=>item.layer==="user_feedback_intelligence");
      note("browse_says_plainly_when_a_group_holds_nothing",emptyGroup!==undefined&&emptyGroup.count==="0 items"
        &&emptyGroup.identities.length===0&&emptyGroup.empty==="Nothing is published in this group yet.",{group:emptyGroup});
      /* The service withheld one item because it declares an effect, and no filter was chosen. Naming the
         filters here would tell the reader to change something that is not the reason. */
      const unfilteredMessage=await opened.locator("#browse-message").innerText();
      note("browse_names_every_reason_material_is_not_offered",reply.withheld.length===1
        &&reply.withheld[0].reason.includes("spawns_process")
        &&unfilteredMessage.includes("1 item is not offered here, because of this account's permissions or a declared effect this page holds no authority for.")
        &&!unfilteredMessage.includes("did not match the filters"),{message:unfilteredMessage,withheld:reply.withheld});
      await openItem(opened,"context.review");
      const detail=await browseDetail(opened),listed=reply.items.find(row=>row.identity==="context.review");
      note("browse_detail_states_purpose_licence_size_digest_and_effects",
        detail["What it is for"]===listed.purpose&&detail["Exact reference"]===listed.identity
        &&detail["Where it comes from"]===listed.source_ref&&detail.Licence===listed.license
        &&detail.Size===listed.size_bytes+" bytes"&&detail.Digest===listed.digest&&/^[0-9a-f]{64}$/.test(detail.Digest)
        &&detail["Declared effects"]==="None declared"&&detail["Written for"]==="claude-code"
        &&detail["The file itself"].startsWith("You may fetch it"),{detail});
      const saving=opened.waitForEvent("download");
      await opened.click("#browse-download");
      const saved=await saving,stream=await saved.createReadStream(),chunks=[];
      for await (const chunk of stream) chunks.push(chunk);
      note("browse_download_matches_the_selected_digest",Buffer.concat(chunks).toString()==="CONTEXT_REVIEW_BODY"
        &&createHash("sha256").update("CONTEXT_REVIEW_BODY").digest("hex")===listed.digest
        &&(await browseStatus(opened)).includes("Digest verified"));
      await openItem(opened,"code.verify");
      note("browse_detail_says_when_the_file_is_not_granted",(await browseDetail(opened))["The file itself"]==="Not granted to this account."
        &&await opened.locator("#browse-download").count()===0
        &&(await browseStatus(opened))==="This account may read the details above, not the file.");
      await openItem(opened,"local.notes");
      note("browse_detail_states_an_unstated_licence_honestly",(await browseDetail(opened)).Licence==="Not stated"
        &&(await browseDetail(opened))["Written for"]==="No tool named, so it suits every tool");
      const view=await opened.locator('[data-view="workspace"] .browse').innerText();
      note("browse_view_uses_plain_words",!internalTerms.test(view)&&!/\bPractitioner\b/i.test(view),{});
      note("browse_shows_descriptions_and_no_file_body",view.includes("No file was fetched.")
        &&!["CONTEXT_REVIEW_BODY","CODE_NORMALISE_BODY","LOCAL_NOTES_BODY","HISTORY_RETRY_BODY"].some(body=>view.includes(body)));
      note("browse_stores_nothing_in_the_browser",await opened.evaluate(()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie==="")
        &&!view.includes(fixture.browse_token));
      await opened.locator("#browse-style").focus();
      await opened.keyboard.press("Tab");
      const afterOne=await opened.evaluate(()=>document.activeElement.id);
      await opened.keyboard.press("Tab");
      const reached=await opened.evaluate(()=>({className:String(document.activeElement.className),identity:document.activeElement.dataset.identity}));
      await opened.keyboard.press("Enter");
      await opened.waitForFunction(id=>document.querySelector("#browse-detail p.caption")?.textContent===id,reached.identity);
      note("browse_opens_an_item_with_the_keyboard",afterOne==="refresh-browse"&&reached.className==="browse-item"
        &&await opened.locator('.browse-item[data-identity="'+reached.identity+'"]').getAttribute("aria-current")==="true",{afterOne,reached});
      await opened.setViewportSize({width:1440,height:1000});
      // A removed-guard control runs this same scenario against a changed module. The saved pictures must
      // show the page as it is, so only the unchanged run writes them.
      const unchangedRun=note===check;
      if(unchangedRun)await opened.screenshot({path:output.replace(/\.json$/,"-browse-desktop.png"),fullPage:true});
      const browseFits=[];
      for(const width of [1440,820,390,320]){
        await opened.setViewportSize({width,height:1000});
        for(const size of ["","200%"]){
          await opened.evaluate(value=>document.documentElement.style.fontSize=value,size);
          browseFits.push({width,size:size||"100%",...await opened.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,
            items:[...document.querySelectorAll('[data-view="workspace"] .browse *')].filter(item=>{const box=item.getBoundingClientRect();return box.width&&box.right>innerWidth+1;})
              .slice(0,8).map(item=>({tag:item.tagName,id:item.id,className:String(item.className)}))}))});
        }
        await opened.evaluate(()=>document.documentElement.style.fontSize="");
      }
      await opened.setViewportSize({width:390,height:1000});
      if(unchangedRun)await opened.screenshot({path:output.replace(/\.json$/,"-browse-mobile.png"),fullPage:true});
      await opened.setViewportSize({width:1440,height:1000});
      note("browse_fits_small_screens_and_enlarged_text",browseFits.length===8&&browseFits.every(item=>!item.overflow),
        {problems:browseFits.filter(item=>item.overflow)});
    },
    kind_filter:async (opened,note)=>{
      await loadBrowse(opened);
      await opened.selectOption("#browse-kind","reusable_code");await settleBrowse(opened);
      const reply=await browseList(opened,{kinds:["reusable_code"]}),groups=await browseGroups(opened);
      note("browse_filters_by_kind_through_the_service",reply.items.length===1&&reply.items[0].identity==="code.normalise"
        &&JSON.stringify(groups)===JSON.stringify(expectedGroups(reply.items,true))
        &&await opened.locator("#browse-count").innerText()==="1 of 6 items",{groups});
      note("browse_says_a_filter_hid_a_group_rather_than_calling_it_unpublished",
        groups.find(item=>item.layer==="context_intelligence")?.empty==="Nothing in this group matches your filters.");
      note("browse_names_the_filters_among_the_reasons_when_one_is_set",
        (await opened.locator("#browse-message").innerText()).includes(
          "did not match the filters, this account's permissions, or a declared effect this page holds no authority for."),
        {message:await opened.locator("#browse-message").innerText()});
    },
    /* Pressing "Load the catalogue" asks the service for every item. A control that still named a filter
       would describe a request the service never received, and a full group would read as an empty one. */
    refresh_after_filter:async (opened,note)=>{
      await loadBrowse(opened);
      await opened.selectOption("#browse-kind","reusable_code");await settleBrowse(opened);
      await opened.selectOption("#browse-style","codex");await settleBrowse(opened);
      const filtered=(await browseGroups(opened)).flatMap(item=>item.identities);
      await loadBrowse(opened);
      const reply=await browseList(opened),groups=await browseGroups(opened);
      const kindValue=await opened.inputValue("#browse-kind"),styleValue=await opened.inputValue("#browse-style");
      note("browse_refresh_shows_the_request_it_actually_sent",kindValue===""&&styleValue===""
        &&filtered.length===1&&JSON.stringify(groups)===JSON.stringify(expectedGroups(reply.items,false))
        &&await opened.locator("#browse-count").innerText()===reply.items.length+" items"
        &&groups.flatMap(item=>item.identities).length===reply.items.length,
        {kindValue,styleValue,filtered,shown:groups.flatMap(item=>item.identities)});
      note("browse_refresh_offers_every_filter_choice_again",
        await opened.locator("#browse-kind option").count()===5&&await opened.locator("#browse-style option").count()===3
        &&!(await opened.locator("#browse-kind").isDisabled()),
        {kinds:await opened.locator("#browse-kind option").allInnerTexts()});
    },
    /* The service decides. The request that leaves this page names a revision that is not the published
       one, so the real service refuses it with its own short code, and the reader must be told what to do
       about it in words rather than shown the code. The same refusal is asked for separately, over the
       same credential, so the code the page had to translate is recorded and not assumed. */
    stale_selection:async (opened,note)=>{
      await loadBrowse(opened);
      const staleDigest="0".repeat(64);
      const direct=await opened.request.post(fixture.browse_base+"/api/v1/provisioning",
        {headers:{Authorization:"Bearer "+fixture.browse_token,"Content-Type":"application/json"},
         data:{record_type:"service_provisioning_request/v1",operation:"manifest",identity:"context.review",expected_digest:staleDigest}});
      const code=(await direct.json())?.error?.code||"";
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="manifest")return route.continue();
        await route.continue({postData:JSON.stringify({...sent,expected_digest:staleDigest})});});
      await openItem(opened,"context.review");
      const status=await browseStatus(opened);
      note("browse_states_a_service_refusal_in_plain_words",direct.status()>=400&&code==="item_unavailable"
        &&status==="This item is no longer available to this account. Load the catalogue again to see what is there now."
        &&!status.includes(code)&&!/[a-z]_[a-z]/.test(status)
        &&await opened.locator("#browse-detail dl").count()===0
        &&await opened.locator("#browse-download").count()===0,{status,code,refused:direct.status()});
      await opened.unroute("**/api/v1/provisioning");
    },
    tool_filter:async (opened,note)=>{
      await loadBrowse(opened);
      await opened.selectOption("#browse-style","codex");await settleBrowse(opened);
      const reply=await browseList(opened,{style:"codex"}),groups=await browseGroups(opened);
      const identities=groups.flatMap(item=>item.identities);
      note("browse_filters_by_development_tool_through_the_service",reply.items.length===5
        &&JSON.stringify(groups)===JSON.stringify(expectedGroups(reply.items,true))
        &&identities.includes("code.normalise")&&identities.includes("context.brief")&&!identities.includes("context.review"),
        {identities});
    },
    changed_download:async (opened,note)=>{
      await loadBrowse(opened);await openItem(opened,"context.review");
      /* Bytes that are not the revision the reader selected, with a service report that agrees with those
         bytes. Only the comparison against the listed digest can tell this answer from a correct one. */
      const wrongBody="CORRUPTED_LOCAL_FIXTURE",wrongDigest=createHash("sha256").update(wrongBody).digest("hex");
      await opened.route("**/api/v1/download",async route=>{const response=await route.fetch();
        await route.fulfill({response,headers:{...response.headers(),"x-content-sha256":wrongDigest},body:wrongBody});});
      const saving=opened.waitForEvent("download",{timeout:1500}).then(()=>false,()=>true);
      await opened.click("#browse-download");
      await opened.waitForFunction(()=>document.querySelector('#browse-detail p[role="status"]').textContent!=="Fetching the selected revision…");
      const nothingSaved=await saving;
      note("browse_refuses_changed_download_bytes_and_saves_nothing",nothingSaved
        &&(await browseStatus(opened)).includes("do not match the selected item")
        &&(await browseStatus(opened)).includes("Nothing was saved."),{status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/download");
    },
    reported_digest:async (opened,note)=>{
      await loadBrowse(opened);await openItem(opened,"context.review");
      /* The bytes are the real ones; only the digest the service reports for them is changed. A page that
         measures the bytes but trusts the reported digest cannot tell these two answers apart. */
      await opened.route("**/api/v1/download",async route=>{const response=await route.fetch();
        await route.fulfill({response,headers:{...response.headers(),"x-content-sha256":"0".repeat(64)}});});
      const saving=opened.waitForEvent("download",{timeout:1500}).then(()=>false,()=>true);
      await opened.click("#browse-download");
      await opened.waitForFunction(()=>document.querySelector('#browse-detail p[role="status"]').textContent!=="Fetching the selected revision…");
      const nothingSaved=await saving;
      note("browse_refuses_a_download_whose_reported_digest_disagrees",nothingSaved
        &&(await browseStatus(opened)).includes("Nothing was saved."),{status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/download");
    },
    changed_item:async (opened,note)=>{
      await loadBrowse(opened);
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="manifest")return route.continue();
        const response=await route.fetch(),value=await response.json();
        value.result.digest="0".repeat(64);
        await route.fulfill({response,json:value});});
      await openItem(opened,"context.review");
      note("browse_refuses_an_item_that_changed_since_the_list",
        (await browseStatus(opened))==="This item changed since the list was loaded. Load the catalogue again before fetching it."
        &&await opened.locator("#browse-download").count()===0
        &&await opened.locator("#browse-detail dl").count()===0,{status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/provisioning");
    },
    wrong_item_version:async (opened,note)=>{
      await loadBrowse(opened);
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="manifest")return route.continue();
        const response=await route.fetch(),value=await response.json();
        value.result.record_type="provisioning_manifest/v3";
        await route.fulfill({response,json:value});});
      await openItem(opened,"context.review");
      note("browse_refuses_an_item_record_version_it_was_not_written_for",
        (await browseStatus(opened)).includes("an unsupported item version")
        &&await opened.locator("#browse-detail dl").count()===0
        &&await opened.locator("#browse-download").count()===0,{status:await browseStatus(opened)});
      await opened.unroute("**/api/v1/provisioning");
    },
    wrong_version:async (opened,note)=>{
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="list")return route.continue();
        const response=await route.fetch(),value=await response.json();
        value.result.record_type="provisioning_list/v3";
        await route.fulfill({response,json:value});});
      await loadBrowse(opened);
      await refusedBrowse(opened,note,"browse_refuses_a_catalogue_record_version_it_was_not_written_for","context.review");
      await opened.unroute("**/api/v1/provisioning");
    },
    unknown_group:async (opened,note)=>{
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="list")return route.continue();
        const response=await route.fetch(),value=await response.json();
        value.result.items[0].source_layer="mystery_intelligence";
        await route.fulfill({response,json:value});});
      await loadBrowse(opened);
      await refusedBrowse(opened,note,"browse_refuses_a_catalogue_that_names_a_group_it_does_not_know","context.review");
      note("browse_names_the_reason_it_refused_a_catalogue",(await opened.locator("#browse-message").innerText()).includes("a group this page does not know"));
      await opened.unroute("**/api/v1/provisioning");
    },
    /* The count of held-back material is read out of the reply, so its shape is checked like every other
       field the page reads. A number where a list belongs is a record this page was not written for. */
    withheld_shape:async (opened,note)=>{
      await opened.route("**/api/v1/provisioning",async route=>{
        const sent=route.request().postDataJSON();
        if(sent?.operation!=="list")return route.continue();
        const response=await route.fetch(),value=await response.json();
        value.result.withheld=value.result.withheld.length;
        await route.fulfill({response,json:value});});
      await loadBrowse(opened);
      await refusedBrowse(opened,note,"browse_refuses_a_catalogue_that_counts_held_back_material_the_wrong_way","context.review");
      await opened.unroute("**/api/v1/provisioning");
    },
    /* A download whose bytes are measured after the reader signs out. The service answered the connection
       that has ended, so no file may reach the disk. The measurement is held by the check, because the
       sign-out otherwise cancels the request before any bytes exist. */
    held_download:async (opened,note)=>{
      await loadBrowse(opened);await openItem(opened,"context.review");
      await opened.evaluate(()=>window.__armDigestHold());
      const saving=opened.waitForEvent("download",{timeout:2500}).then(()=>false,()=>true);
      await opened.click("#browse-download");
      await opened.waitForFunction(()=>window.__digestHeld===true,null,{timeout:8000});
      await opened.locator('header a[data-page="login"]').click();
      await opened.click("#disconnect");
      await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Not connected");
      await opened.evaluate(()=>window.__releaseDigest());
      const nothingSaved=await saving;
      note("browse_sign_out_stops_a_download_that_finishes_afterwards",nothingSaved
        &&await opened.locator("#browse-groups .browse-group").count()===0
        &&await opened.locator("#browse-count").innerText()==="Sign in to browse"
        &&await opened.locator("#browse-detail dl").count()===0,
        {nothingSaved,message:await opened.locator("#browse-message").innerText()});
    },
    delayed_reply:async (opened,note)=>{
      await loadBrowse(opened);await openItem(opened,"context.review");
      let release;const gate=new Promise(resolve=>{release=resolve;});let held=false;
      await opened.route("**/api/v1/provisioning",async route=>{
        if(route.request().postDataJSON()?.operation==="list"){held=true;await gate;}
        await route.continue().catch(()=>{});});
      await opened.click("#refresh-browse");
      await new Promise((resolve,reject)=>{const deadline=setTimeout(()=>{clearInterval(poll);reject(new Error("No held catalogue request"));},5000);
        const poll=setInterval(()=>{if(held){clearInterval(poll);clearTimeout(deadline);resolve();}},10);});
      await opened.locator('header a[data-page="login"]').click();
      await opened.click("#disconnect");
      await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Not connected");
      release();
      const signedOut="Sign in to browse the material published for your account.";
      await opened.waitForFunction(text=>document.querySelector("#browse-message").textContent!==text,signedOut,{timeout:1200}).catch(()=>{});
      note("browse_sign_out_clears_a_delayed_catalogue_reply",
        await opened.locator("#browse-groups .browse-group").count()===0
        &&await opened.locator("#browse-count").innerText()==="Sign in to browse"
        &&await opened.locator("#browse-message").innerText()===signedOut
        &&await opened.locator("#browse-detail dl").count()===0
        &&await opened.locator("#browse-kind").isDisabled()&&await opened.locator("#refresh-browse").isDisabled(),
        {message:await opened.locator("#browse-message").innerText()});
      await opened.unroute("**/api/v1/provisioning");
    }};
  // The held measurement is installed only where a check names it, so every other browse check runs in an
  // unchanged page served entirely by the service.
  const browseHoldsDigest=new Set(["held_download"]);
  for(const name of Object.keys(browseScenarios)){
    const {context:browseContext,page:browsePage}=await openBrowseWorkspace(null,browseHoldsDigest.has(name));
    await browseScenarios[name](browsePage,check);
    await browseContext.close();
  }
  /* Removed-guard controls for browsing. The served module is changed in memory only. A control is
     detected when every check it names fails with the guard removed. */
  const browseControls=[
    {name:"accept_any_catalogue_record_version",scenario:"wrong_version",find:"value.record_type !== listVersion",replacement:"false",
     expected:["browse_refuses_a_catalogue_record_version_it_was_not_written_for"]},
    {name:"accept_a_group_the_page_does_not_know",scenario:"unknown_group",
     find:'if (!knownLayers.has(row.source_layer)) return "a group this page does not know";',replacement:"",
     expected:["browse_refuses_a_catalogue_that_names_a_group_it_does_not_know","browse_names_the_reason_it_refused_a_catalogue"]},
    {name:"trust_the_downloaded_bytes",scenario:"changed_download",find:"measured !== row.digest || ",replacement:"",
     expected:["browse_refuses_changed_download_bytes_and_saves_nothing"]},
    {name:"trust_the_reported_download_digest",scenario:"reported_digest",find:" || measured !== result.digest",replacement:"",
     expected:["browse_refuses_a_download_whose_reported_digest_disagrees"]},
    {name:"ignore_an_item_that_changed_since_the_list",scenario:"changed_item",find:"if (value.digest !== row.digest) {",replacement:"if (false) {",
     expected:["browse_refuses_an_item_that_changed_since_the_list"]},
    {name:"accept_any_item_record_version",scenario:"wrong_item_version",find:"value.record_type !== manifestVersion",replacement:"false",
     expected:["browse_refuses_an_item_record_version_it_was_not_written_for"]},
    /* The guard this removes is the one the scenario reaches. Signing out cancels the request that is in
       flight, so the catalogue reply arrives as a cancellation and the guard in the failure path decides
       whether the signed-out page is written to. The matching guard on the success path of the same
       function stays in place and has no control, because the shared request boundary already refuses a
       reply whose connection changed before this module is given it, and no page action can reach it. */
    {name:"keep_a_delayed_catalogue_reply_after_sign_out",scenario:"delayed_reply",
     find:'if (epoch !== current().generation) return;\n        message("browse-message", error.name === "AbortError"',
     replacement:'message("browse-message", error.name === "AbortError"',
     expected:["browse_sign_out_clears_a_delayed_catalogue_reply"]},
    {name:"save_a_download_that_finished_after_sign_out",scenario:"held_download",
     find:"if (epoch !== current().generation || result.epoch !== current().generation) return;",replacement:"",
     expected:["browse_sign_out_stops_a_download_that_finishes_afterwards"]},
    {name:"show_a_filter_the_service_was_not_asked_to_apply",scenario:"refresh_after_filter",
     find:"function options(select, values, plainName, chosen) {",
     replacement:"function options(select, values, plainName, chosen) { chosen = select.value;",
     expected:["browse_refresh_shows_the_request_it_actually_sent"]},
    {name:"show_a_service_refusal_as_its_code",scenario:"stale_selection",
     find:"return named && refusals[named[1]] ? refusals[named[1]] : text;",replacement:"return text;",
     expected:["browse_states_a_service_refusal_in_plain_words"]},
    {name:"count_held_back_material_from_a_shape_the_page_was_not_written_for",scenario:"withheld_shape",
     find:"|| !Array.isArray(value.withheld) ",replacement:"",
     expected:["browse_refuses_a_catalogue_that_counts_held_back_material_the_wrong_way"]},
    {name:"blame_the_filters_when_no_filter_was_set",scenario:"catalogue",
     find:'" not offered here, because of this account\'s permissions or a declared effect this page holds no authority for. "',
     replacement:'" not offered here. "',
     expected:["browse_names_every_reason_material_is_not_offered"]},
    {name:"leave_the_declared_effect_out_of_the_filtered_reason",scenario:"kind_filter",
     find:'" did not match the filters, this account\'s permissions, or a declared effect this page holds no authority for. "',
     replacement:'" did not match the filters or this account\'s permissions. "',
     expected:["browse_names_the_filters_among_the_reasons_when_one_is_set"]},
    {name:"hide_a_group_that_holds_nothing",scenario:"catalogue",find:"if (group.outside && !held.length) continue;",replacement:"if (!held.length) continue;",
     expected:["browse_shows_the_four_groups_with_plain_names","browse_counts_and_membership_match_the_service_reply","browse_says_plainly_when_a_group_holds_nothing"]},
    {name:"ignore_the_kind_filter",scenario:"kind_filter",find:"kind ? {kinds:[kind]} : {}",replacement:"{}",
     expected:["browse_filters_by_kind_through_the_service","browse_says_a_filter_hid_a_group_rather_than_calling_it_unpublished"]},
    {name:"ignore_the_development_tool_filter",scenario:"tool_filter",find:"style ? {style} : {}",replacement:"{}",
     expected:["browse_filters_by_development_tool_through_the_service"]}];
  for(const control of browseControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{
      const {context:changedContext,page:changedPage,state}=await openBrowseWorkspace(
        {find:control.find,replacement:control.replacement},browseHoldsDigest.has(control.scenario));
      applied=state.applied;
      await browseScenarios[control.scenario](changedPage,note);
      await changedContext.close();
    }catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
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
const paths=[...['http.py','records.py','access.py','access_checks.py','http_entrypoint.py','runtime.py','browser_identity.py','browser_identity_checks.py'].map(name=>"src/loop_engine/core/service_runtime/"+name),...['index.html','service.css','service.js','client-access.js','catalogue-browser.js','architecture-story.js','architecture.css','client-recipes.json'].map(name=>"src/loop_engine/core/service_runtime/web_assets/"+name)];
/* Version 2 of this report carries the removed-guard controls, and all_passed is true only when every check passed and every control was detected. Version 1 had neither. */
const result={record_type:"service_workspace_browser_checks/v2",scope:"real browser and loopback service; provider fixtures only; every page asset is served by the service",external_provider_calls:0,
  /* What the check supplied instead of the running system, named on the face of the report. Offered,
     fetched, loaded and used are separate facts, and so is substituted. */
  harness_substitutions:["a removed-guard control answers /assets/catalogue-browser.js with changed bytes, in memory, for that control run only",
    "the held download checks wrap crypto.subtle.digest in the page so one measurement can be held, which puts the sign-out inside the window the guard defends"],
  checks,passed:checks.filter(x=>x.passed).length,total:checks.length,mutants,mutants_detected:mutants.filter(x=>x.detected).length,all_passed:checks.every(x=>x.passed)&&mutants.every(x=>x.detected),source_sha256:Object.fromEntries(paths.map(path=>[path,createHash("sha256").update(readFileSync(resolve(root,path))).digest("hex")]))};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"}); console.log(JSON.stringify({passed:result.passed,total:result.total,mutants_detected:result.mutants_detected,mutants:mutants.length,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed),output})); process.exitCode=result.all_passed?0:1;
