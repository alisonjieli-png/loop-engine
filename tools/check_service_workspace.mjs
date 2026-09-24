/* Real browser + HTTP + durable-domain checks. Providers are local fixtures.
   Removed-guard controls change the served page script in memory only, never a source file. */
import {runSignupSessionBoundaries} from "./signup_session_boundary_checks.mjs";
import {runShowcasePageChecks,showcasePaths,showcaseScreenshotSuffixes} from "./showcase_page_checks.mjs";
import {runDirectoryChecks} from "./directory_browser_checks.mjs";
import {chromium} from "../showcase/node_modules/playwright-core/index.mjs";
import {spawn} from "node:child_process";
import {createInterface} from "node:readline";
import {existsSync,readFileSync,writeFileSync} from "node:fs";
import {createHash,randomBytes} from "node:crypto";
import {resolve} from "node:path";
import {runDeckChecks} from "./deck_checks.mjs";
import {LISTING_TEXT_ATTRIBUTE,listingTextPages,listingTextRegistration,registerListingText,withoutListingText} from "./listing_text.mjs";

const root=resolve(new URL("..",import.meta.url).pathname);
/* Version queries are exact content identities, not permission to match arbitrary queries or origins. */
const assetDigests=new Map();
const assetDigest=path=>{if(!assetDigests.has(path)){const name=path==="/assets/third-party-notices.txt"?"THIRD-PARTY-NOTICES.md":path.slice("/assets/".length);assetDigests.set(path,createHash("sha256").update(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets",name))).digest("hex"));}return assetDigests.get(path);};
const sameOriginAsset=(value,origin,path,requireVersion=true)=>{try{const url=new URL(value,origin);return url.origin===origin&&url.pathname===path&&!url.username&&!url.password&&!url.hash&&(url.search===""?!requireVersion:url.search==="?v="+assetDigest(path));}catch(_){return false;}};
const assetRoute=(path,origin)=>url=>(origin?[origin]:serviceOrigins).some(base=>sameOriginAsset(url.href,base,path,false));
const output=resolve(process.argv[2] || "artifacts/architecture-audit-2026-09-19/service-workspace-browser-1.json");
for (const path of [output,...["-desktop.png","-mobile-dark.png","-admin.png","-task-desktop.png","-task-mobile.png","-boundaries.png","-connect-desktop.png","-connect-mobile.png","-connect-claude-code.png","-pricing-desktop.png","-pricing-mobile.png","-privacy-desktop.png","-privacy-mobile.png","-terms-desktop.png","-terms-mobile.png","-consent-desktop.png","-browse-desktop.png","-browse-mobile.png","-start-open-desktop.png","-start-open-mobile.png","-start-closed-desktop.png","-start-closed-mobile.png",...showcaseScreenshotSuffixes,"-directory-desktop.png","-directory-mobile.png"].map(suffix=>output.replace(/\.json$/,suffix))]) {
  if (existsSync(path)) throw new Error("Refusing to overwrite an existing browser evidence artifact: " + path);
}
/* Connection recipes. The reviewed record is read from the source tree before any process starts, so the page is compared with the record and not with itself. */
const recipeRecord=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/client-recipes.json"),"utf8"));
/* The review records that the Security page's "How review works" section describes, read from the source tree, so the page is
   compared with the records and never with itself: the served catalogue's review record and the review panel's policy. */
const catalogueReviews=JSON.parse(readFileSync(resolve(root,"examples/29_intelligence_service/starter-catalogue/reviews.json"),"utf8"));
const reviewPanelPolicy=JSON.parse(readFileSync(resolve(root,"tools/candidate_review/resources/panel.json"),"utf8")).policy;
/* The catalogue browser is read from the source tree as well, and a named check compares it with the
   bytes the service serves. Every ordinary page in this run loads the module from the service itself.
   A removed-guard control, and only such a control, answers that one address with changed bytes, in
   memory and never in the source file. */
const browseSource=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/catalogue-browser.js"),"utf8");
const routeBrowseAsset=(target,mutation)=>{
  const state={applied:false,errors:[]};
  if(!mutation)return state;
  target.route(assetRoute("/assets/catalogue-browser.js"),route=>{
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
from dataclasses import replace
from datetime import datetime,timedelta,timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import json,sys,time,uuid
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
from loop_engine.core.service_runtime.access_checks import prepared
from loop_engine.core.service_runtime.http import ServiceHttpApplication
from loop_engine.core.service_runtime.stripe_session_checks import fixture
from loop_engine.core.service_runtime.stripe_session_transport_checks import _application
from loop_engine.core.service_runtime.http_test_fixtures import running_key_set
from loop_engine.core.service_runtime.browser_identity import BrowserIdentityAdapter,BrowserIdentityConfiguration
from loop_engine.core.service_runtime.account_email import AccountEmailAdapter
from loop_engine.core.service_runtime.account_email_checks import serving_identity_project,_settings as account_settings,_secrets as account_secrets
from loop_engine.core.service_runtime.account_email import ProviderAnswer
from loop_engine.core.service_runtime.account_origin_checks import MarkingIdentityProjectStandIn as IdentityProjectStandIn
from loop_engine.core.service_runtime.account_origin import ACCOUNT_MARK,ACCOUNT_MARKER,AccountOrigins,SupabaseIdentityAdministration,record_origin
from loop_engine.core.service_runtime.account_administration import AccountAdministration
from loop_engine.core.service_runtime.account_policy import ServiceAccountPolicy
from loop_engine.core.service_runtime.free_monthly import consider_founding_offer,grant_rows
from loop_engine.core.service_runtime.request_limits import SOCKET_PEER_SOURCE,ServiceRequestLimits
from loop_engine.core.service_runtime.access import ServiceAccessAdministration,ServiceClientAccessPolicy
from loop_engine.core.service_runtime.waitlist import ServiceWaitlist,WaitlistPolicy
from loop_engine.core.service_runtime.records import ACCESS_MANAGE_SCOPE,TenantKeyIssue,TenantRegistration
from loop_engine.core.harness_intelligence import HarnessIntelligenceDraft,item_from_body
from loop_engine.core.provisioning_server import ProvisioningGrant,ProvisioningItemBinding
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
with ExitStack() as stack:
    root=Path(stack.enter_context(TemporaryDirectory(prefix="service-browser-")))
    (root/"intelligence").mkdir(); (root/"billing").mkdir(); (root/"accounts").mkdir(); (root/"signups").mkdir(); (root/"browse").mkdir(); (root/"selling").mkdir(); (root/"confirm").mkdir()
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
    # Every identity these services honour came through Baltor's sign-up: the provider's mark is in its app_metadata, and each
    # service that signs it in holds the second mark, written below with the same function the sign-up and the marking command use.
    user={"id":subject,"email":"account-test@example.invalid","role":"authenticated","is_anonymous":False,"email_confirmed_at":"2026-01-01T00:00:00Z","app_metadata":{ACCOUNT_MARKER:ACCOUNT_MARK}}
    identity=BrowserIdentityAdapter(account.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-customers",registration_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",starter_bindings=(account.bindings["skill.alpha"],),transport=lambda _:user)
    record_origin(account.runtime,provider+"/auth/v1",subject,"signup")
    manager=ServiceAccessAdministration(account.runtime,ServiceClientAccessPolicy(writes_authorized=True))
    account.runtime.register_tenant(TenantRegistration("operator","operator:private",(ACCESS_MANAGE_SCOPE,)))
    account_operator=account.runtime.issue_key(TenantKeyIssue("operator","browser waiting list operator"))
    waiting=ServiceWaitlist(account.runtime,WaitlistPolicy(writes_authorized=True,accepted_for_each_source=3))
    account_base,_=stack.enter_context(running_http(account,application_factory=lambda config:ServiceHttpApplication(account.runtime,account.provisioning,config,browser_identity=identity,client_access=manager,waitlist=waiting),display_name="Baltor"))
    # Account creation is open only where this service sends the sign-up link itself, so every service that reports registration open carries an
    # account email adapter. Its two transports are one identity project stand-in, and its client address source is stated, as the adapter requires.
    stated=ServiceRequestLimits(client_address_source=SOCKET_PEER_SOURCE,failures_allowed=100,window_seconds=600)
    def account_email(config,project,origin,runtime):
        origins=AccountOrigins(runtime,origin+"/auth/v1",SupabaseIdentityAdministration(origin,allow_network=True,transport=project.admin))
        return AccountEmailAdapter(account_settings(identity_origin=origin,mail_origin=origin,allow_loopback=True,attempts_for_each_address=200,attempts_for_each_email=20),account_secrets,public_base_url=config.public_base_url,address_limits=config.request_limits,display_name=config.display_name,identity_transport=project.generate_link,mail_transport=project.send_mail,account_origins=origins)
    quiet_project=IdentityProjectStandIn()
    # A fourth real service whose own configuration opens email sign-up, so the page is compared with a service that reports registration, not with a rewritten reply.
    signups=HttpDomainFixture(root/"signups",operator_access=False)
    # Like the live host, it keeps ten founding places, all free, so the public pages state the founding offer.
    signup_identity=BrowserIdentityAdapter(signups.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-signups",registration_enabled=True,email_signup_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",starter_bindings=(signups.bindings["skill.alpha"],),transport=lambda _:user,founding_accounts=10)
    signup_base,_=stack.enter_context(running_http(signups,application_factory=lambda config:ServiceHttpApplication(signups.runtime,signups.provisioning,config,browser_identity=signup_identity,account_email=account_email(config,quiet_project,provider,signups.runtime)),display_name="Baltor",request_limits=stated))
    record_origin(signups.runtime,provider+"/auth/v1",subject,"signup")
    # A sixth real service that opens email sign-up and takes payment, so the one public state that says payment is open is compared with a service that reports both, not with a rewritten reply.
    selling=fixture(root/"selling")
    selling_identity=BrowserIdentityAdapter(selling.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-selling",registration_enabled=True,email_signup_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",transport=lambda _:user)
    checkout_signup_base,_=stack.enter_context(running_http(selling,application_factory=lambda config:replace(_application(selling,config),browser_identity=selling_identity,account_email=account_email(config,quiet_project,provider,selling.runtime)),display_name="Baltor",request_limits=stated))
    record_origin(selling.runtime,provider+"/auth/v1",subject,"signup")
    # A seventh real service for the whole sign-up journey. Its browser identity and its account email speak to one identity project stand-in, served
    # over a loopback socket, so the address the Get started page sends, the link in the message, the password the confirmation page sets and the
    # sign-in that follows all meet the same project. The stand-in keeps the first password of an address that is not confirmed, as the probe of
    # September 23, 2026 observed, and its public sign-up plays the provider's own route that the owner is closing.
    confirm=HttpDomainFixture(root/"confirm",operator_access=False)
    stand_in_key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    def stand_in_session(project,user):
        return jwt.encode({"iss":project.issuer,"aud":"authenticated","sub":user["id"],"exp":int(time.time())+1800,"iat":int(time.time()),"role":"authenticated","is_anonymous":False,"email":user["email"],"session_id":str(uuid.uuid4())},stand_in_key,algorithm="RS256",headers={"kid":"stand-in"})
    project=IdentityProjectStandIn(session_factory=stand_in_session)
    confirm_identity_origin=stack.enter_context(serving_identity_project(project,[{**json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(stand_in_key.public_key())),"kid":"stand-in","alg":"RS256","use":"sig"}]))
    confirm_identity=BrowserIdentityAdapter(confirm.runtime,BrowserIdentityConfiguration(confirm_identity_origin,"fixture:publishable","browser-confirm",registration_enabled=True,email_signup_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",starter_bindings=(confirm.bindings["skill.alpha"],))
    # Like the live service, it lets a signed-in customer create client tokens, so Get set up can lead a signed-in person to them.
    confirm_access=ServiceAccessAdministration(confirm.runtime,ServiceClientAccessPolicy(writes_authorized=True))
    confirm_base,_=stack.enter_context(running_http(confirm,application_factory=lambda config:ServiceHttpApplication(confirm.runtime,confirm.provisioning,config,browser_identity=confirm_identity,account_email=account_email(config,project,confirm_identity_origin,confirm.runtime),client_access=confirm_access),display_name="Baltor",request_limits=stated))
    # An invited account on the billing service: an operator grant, the way an invitation gives paid access. The other account has none.
    billing.runtime.set_operator_entitlement("beta",valid_until=int(time.time())+30*86400,evidence_ref="browser fixture invitation")
    # A third account holds free monthly Baltor Pro, written by the same rows a superadmin grant commits.
    billing.runtime.register_tenant(TenantRegistration("gamma","tenant:gamma"))
    free_key=billing.runtime.issue_key(TenantKeyIssue("gamma","browser fixture free monthly"))
    with billing.runtime._catalog.store(write=True) as store:
        rows,guards,_detail=grant_rows(billing.runtime,store,"gamma",int(time.time()),"browser fixture")
        billing.runtime._catalog.commit(store,rows,guards)
    # A fourth account holds the founding offer, taken the way a new account takes it when it opens.
    billing.runtime.register_tenant(TenantRegistration("delta","tenant:delta"))
    founding_key=billing.runtime.issue_key(TenantKeyIssue("delta","browser fixture founding offer"))
    consider_founding_offer(billing.runtime,"delta",10)
    # An eighth real service for staff administration: a superadmin, named by provider identity in its accounts policy, and one
    # customer. Both came through Baltor's sign-up, and the provider's user list for them is a stand-in transport.
    (root/"staff").mkdir()
    staff=HttpDomainFixture(root/"staff",operator_access=False)
    staff_subject,customer_subject="4c3b2a19-8f7e-4d6c-9b5a-0e1f2a3b4c5d","5d4c3b2a-9f8e-4e7d-8c6b-1f2e3a4b5c6d"
    staff_people={staff_subject:"staff-test@example.invalid",customer_subject:"customer-test@example.invalid"}
    staff_users={person:{"id":person,"email":address,"role":"authenticated","is_anonymous":False,"email_confirmed_at":"2026-01-01T00:00:00Z","app_metadata":{ACCOUNT_MARKER:ACCOUNT_MARK}} for person,address in staff_people.items()}
    def staff_user(request):
        return staff_users[jwt.decode(request.access_token,options={"verify_signature":False})["sub"]]
    # The staff service's identity project is a stand-in with an administration interface and an outbox, so a superadmin's
    # sign-up link creates a real marked account there. The two people above are seeded into it, confirmed and marked.
    staff_project=IdentityProjectStandIn()
    for person,address in staff_people.items():
        staff_project._new_user(address,"browser-fixture-unused-password").update(id=person,confirmed_at=datetime.now(timezone.utc)-timedelta(days=1),app_metadata={ACCOUNT_MARKER:ACCOUNT_MARK})
    staff_identity=BrowserIdentityAdapter(staff.runtime,BrowserIdentityConfiguration(provider,"fixture:publishable","browser-staff",registration_enabled=True,allow_network=True,allow_loopback=True),lambda _:"sb_publishable_browser_fixture",transport=staff_user)
    staff_tokens={}
    for person in staff_people:
        record_origin(staff.runtime,provider+"/auth/v1",person,"signup")
        staff_tokens[person]=jwt.encode({"iss":provider+"/auth/v1","aud":"authenticated","sub":person,"exp":int(time.time())+1800,"iat":int(time.time()),"role":"authenticated","is_anonymous":False},private_key,algorithm="RS256",headers={"kid":"browser-test"})
        staff_identity.activate(staff_tokens[person])
    staff_administration=AccountAdministration(staff.runtime,ServiceAccountPolicy(staff=({"role":"superadmin","provider_user_id":staff_subject,"name":"Staff Tester"},)),provider+"/auth/v1",origins=AccountOrigins(staff.runtime,provider+"/auth/v1",SupabaseIdentityAdministration(provider,allow_network=True,transport=staff_project.admin)),identity_secret=lambda:"sb_secret_browser_fixture")
    staff_base,_=stack.enter_context(running_http(staff,application_factory=lambda config:ServiceHttpApplication(staff.runtime,staff.provisioning,config,browser_identity=staff_identity,account_administration=staff_administration,account_email=account_email(config,staff_project,provider,staff.runtime)),display_name="Baltor",request_limits=stated))
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
    # A service that also answers every hostname of the site map, with this socket's port, so a browser that resolves those names to
    # the loopback address opens each hostname's own page at its root. The names come from the typed site map, never a copy.
    from loop_engine.core.service_runtime.web_site_map import load_site_map
    (root/"surfaces").mkdir(); surfaces=HttpDomainFixture(root/"surfaces")
    surface_base,_=stack.enter_context(running_http(surfaces,display_name="Baltor",hostnames=tuple(item.hostname for item in load_site_map().hostnames)))
    print(json.dumps({"base":base,"token":held.keys["alpha"].key,"admin_token":held.admin_key.key,"billing_base":billing_base,"billing_token":billing.keys["alpha"].key,"account_base":account_base,"signup_base":signup_base,"checkout_signup_base":checkout_signup_base,"browse_base":browse_base,"browse_token":browse.keys["alpha"].key,"identity_origin":provider,"identity_token":identity_token,"identity_user":user,"account_admin_token":account_operator.key,"confirm_base":confirm_base,"confirm_identity_origin":confirm_identity_origin,"billing_invited_token":billing.keys["beta"].key,"billing_free_monthly_token":free_key.key,"billing_founding_token":founding_key.key,"staff_base":staff_base,"staff_token":staff_tokens[staff_subject],"staff_user":staff_users[staff_subject],"surface_base":surface_base}),flush=True)
    sys.stdin.readline()
`;
/* The Python that runs the fixture services: PYTHON when it is set, so a worktree without its own environment can name a
   qualified one, and the checkout's .venv otherwise. */
const child=spawn(process.env.PYTHON||resolve(root,".venv/bin/python"),["-u","-c",program],{cwd:root,env:{...process.env,PYTHONPATH:"src"},stdio:["pipe","pipe","pipe"]});
const lines=createInterface({input:child.stdout});
const fixture=await new Promise((resolve,reject)=>{ const timer=setTimeout(()=>reject(new Error("Fixture startup deadline")),15000); lines.once("line",line=>{clearTimeout(timer);resolve(JSON.parse(line));}); child.once("exit",code=>{clearTimeout(timer);reject(new Error("Fixture stopped before startup: "+code));}); });
const serviceOrigins=[fixture.base,fixture.billing_base,fixture.account_base,fixture.signup_base,fixture.checkout_signup_base,fixture.browse_base];
const checks=[],errors=[],network=[]; let browser,directoryResult=null;
/* The first screen as served without the page script, measured once and compared again by a removed-guard control. */
let servedHeroBoxes={};
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const secrets=[fixture.token,fixture.billing_token,fixture.admin_token,fixture.browse_token,fixture.identity_token,fixture.account_admin_token,fixture.billing_invited_token,fixture.billing_free_monthly_token,fixture.billing_founding_token,fixture.staff_token];
const safeError=error=>secrets.reduce((text,secret)=>text.replaceAll(secret,"[redacted]"),String(error));
const endpointMark="{{ENDPOINT}}",mutants=[];
const internalTerms=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profile/i;
/* The Baltor Harness recipe names the command and package a customer types, loop-engine, exactly as written. That lowercase
   name is not prose, so it is taken out before the plain-words rule reads a recipe; Loop Engine in words is still refused. */
const withoutProgramName=text=>text.replace(/(?<![A-Za-z])loop-engine(?![A-Za-z])/g,"");
/* Words a customer page may never carry. The first set is the runtime vocabulary, which belongs in the Documentation
   view and in the repository. The second set describes the product as a trial, which the owner retired: who may create
   an account is a matter of configuration, not of copy. Each rule is checked against a known-wrong page of its own. */
const publicVocabulary=/\bLoop(?:s|[ -]node| Engine)?\b|runtime classification|role profiles?|\bPractitioner\b/i;
/* The retired set names all four phrases the style guide retires, so a page that never writes pilot or beta but still
   offers "early access" is reported. The hosted check reads the deployed pages with the same rule, and a copy that
   drifts between the two is a named failure below rather than a silent disagreement. */
const retiredAccessWords=/\bpilots?\b|\bbetas?\b|early access/i;
/* The words of an invitation-only service, which the owner retired on September 23, 2026: "remove all mentions of invitation
   only, this should be consistent as if it is fully working" and "We also need to get rid of 'search is free'". No page a
   customer can open says invite, invited or invitation, small groups, waiting list, search is free, being built, being prepared
   or planned, in any state the service reports. The privacy notice and the terms of service keep the words the owner approved,
   so the reading leaves out each of them only while it is shown with exactly the approved words. The hosted check reads the
   deployed pages with the same rule, and a named check below compares the two copies. */
const invitationWords=/\binvit(?:e|es|ed|ing|ations?)\b|small groups|waiting list|\bsearch(?:ing)? is free\b|being built|being prepared|\bplanned\b/i;
/* The Markdown of a published notice is read as a reader sees it rendered: a code span, strong text or a link is the same
   words without its marks. */
const markdownWords=text=>text.replace(/\[([^\]]*)\]\([^)]*\)/g,"$1").replace(/`/g,"").replace(/\*\*/g,"").replace(/^#+\s/gm," ").replace(/^\|[-| :]+\|\s*$/gm," ").replace(/\|/g," ").replace(/^\s*- /gm," ").split(/\s+/).filter(Boolean);
const sameWords=(shown,approved)=>shown.length>0&&JSON.stringify(shown)===JSON.stringify(approved);
/* The terms of service the owner approved on September 23, 2026, read from the source tree, so the served page is compared
   with the approved text and never with itself. */
const approvedTermsWords=markdownWords(readFileSync(resolve(root,"docs/legal/TERMS-OF-SERVICE.md"),"utf8"));
/* The privacy notice the owner approved on September 22, 2026, read the same way. It says small groups, invite and planned, and it
   keeps those words while it is exactly the approved text. */
const approvedPrivacyWords=markdownWords(readFileSync(resolve(root,"docs/legal/PRIVACY-NOTICE.md"),"utf8"));
/* A published legal text keeps the words the owner approved. The approved terms said beta in sections 2 and 6 until the owner
   had them amended on the evening of September 23, 2026, and the approved privacy notice still says small groups and planned. The
   word rules therefore leave out each legal text, and only while it is exactly the approved text: every other word of a page or
   a served file is read, and a legal text with one changed word is read whole. docs/legal/README.md records the reason. */
const termsBlock=/<article id="terms-of-service" data-terms-of-service>[\s\S]*?<\/article>/;
/* Words of served markup as a reader sees them: an inline element such as a link, a code span or strong text joins the words
   around it, and every other tag separates words, so "(<code>iad</code>)" reads "(iad)" as the rendered notice does. */
const markupWords=markup=>markup.replace(/<\/?(?:a|b|code|em|i|span|strong|time)\b[^>]*>/g,"").replace(/<[^>]*>/g," ").replace(/&#39;|&apos;/g,"'").replace(/&amp;/g,"&").split(/\s+/).filter(Boolean);
const withoutApprovedBlock=(markup,block,approved)=>{const found=markup.match(block);return found&&sameWords(markupWords(found[0]),approved)?markup.replace(found[0],""):markup;};
const withoutApprovedTerms=(markup,approved=approvedTermsWords)=>withoutApprovedBlock(markup,termsBlock,approved);
/* A statement that the terms of service are not published. The owner approved and published them on September 23, 2026.
   The hosted check reads the deployed pages with the same rule, and a named check below compares the two copies. */
const unpublishedTerms=/terms of service:?\s+not yet published|terms(?: of service)? (?:are|is) (?:still )?(?:a draft|not (?:yet )?published)/i;
/* One call to action. The owner, September 22, 2026: "get started and join the waiting list are redundant"; September 23:
   "I think we need to have 'Get Setup' which is a guide on how to get setup and 'get started' is the sign up and
   registration/pay funnel", and later the same day: "remove all mentions of invitation only". So every link or button that
   starts the access journey says "Get started" and opens /get-started, the funnel, in every state: the funnel adapts, so no
   label switches. /waitlist is the funnel's older address, so a link to it opens the journey too. One page keeps a page link of
   its own, by its own name: the guide, "Get set up" at /setup, in the header, the footer and the hero. The labels the owner
   called redundant and an invitation request are reported anywhere, and account creation is offered only while the service
   takes new accounts, by registration or by its request list, and then only in the funnel, in the card that leads the guide and
   on the account pages. Each rule has a known-wrong page of its own in the journey below. The readers return empty values for a
   missing element, so a page without the new parts fails these checks by name instead of stopping. */
const accessLabels={closed:"Get started",open:"Get started"},accessPaths={closed:"/get-started",open:"/get-started"},accessAddresses=["/get-started","/waitlist"];
const getStartedPage="/setup";
/* The page link by its own name: the guide. The signed-out header marks its entry apart from the signed-in one, so each place
   names the link it holds. */
const pageLinkNames={"get-set-up":["Get set up","/setup"],"get-set-up-guide":["Get set up","/setup"]};
const isPageLink=action=>Boolean(action.pageLink&&pageLinkNames[action.pageLink]&&action.text===pageLinkNames[action.pageLink][0]&&action.href===pageLinkNames[action.pageLink][1]);
const stateLabel=registrationOpen=>registrationOpen?accessLabels.open:accessLabels.closed,statePath=registrationOpen=>registrationOpen?accessPaths.open:accessPaths.closed;
const opensTheJourney=href=>accessAddresses.includes(href.split("#")[0]);
const redundantAccessLabel=/join the waiting list|request access|early access/i,invitationAccessLabel=/invitation/i,creationAccessLabel=/create (?:your )?account|\bsign up\b/i;
/* The public pages a visitor can open without signing in, including the three use cases the owner named on September 23, 2026
   and their hub. Each is scanned on three real services below. */
const useCasePaths=["/use-cases","/overnight","/efficiency","/learning"];
const accessJourneyPaths=["/",...useCasePaths,"/pricing","/how-it-works","/setup","/get-started","/waitlist","/signup","/examples","/security","/docs","/privacy","/terms","/login",...showcasePaths];
/* The access card that leads the guide and the card of the Get started funnel are the journey itself. */
const publicActions=target=>target.evaluate(()=>{
  const lead=document.getElementById("start-access"),card=document.getElementById("waitlist-card"),funnel=document.querySelector('[data-view="start"] .funnel-card'),shown=node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden";
  return [...document.querySelectorAll("header a, header button, footer a, [data-view]:not([hidden]) a, [data-view]:not([hidden]) button")].filter(shown)
    .map(node=>{const href=node.getAttribute("href")||"",target=href.startsWith("#")?document.getElementById(href.slice(1)):null;
      /* A link within the page to the card that leads the guide, such as the guide's own list of steps, belongs to that card. */
      const toLead=Boolean(lead&&target&&(lead===target||lead.contains(target)));
      return {id:node.id,text:node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),href,
        lead:Boolean((lead&&lead.contains(node))||(card&&card.contains(node))||(funnel&&funnel.contains(node))||toLead),account:Boolean(node.closest('[data-view="signup"]')),pageLink:node.dataset.nav||""};});
});
/* A text link may give the label as the answer to a short question, as the sign-in page's "No account yet? Get started." does.
   Any other wording of a link into the journey is a second label. */
const saysTheLabel=(text,label)=>text===label||new RegExp("^[A-Z][^.?!]{0,40}\\? "+label+"\\.$").test(text);
/* takesAccounts: the service reports registration open, or keeps the request list the funnel's form writes to. Either way the
   funnel offers its one account form, so account creation may be offered in the journey itself and on the account pages. */
const accessActionProblems=(actions,registrationOpen,takesAccounts=registrationOpen)=>{const label=stateLabel(registrationOpen),path=statePath(registrationOpen);return [
  ...actions.filter(action=>opensTheJourney(action.href)&&!saysTheLabel(action.text,label)).map(action=>"an action that opens the sign-up funnel says "+JSON.stringify(action.text)),
  ...actions.filter(action=>action.pageLink&&!isPageLink(action)).map(action=>"a page link says "+JSON.stringify(action.text)+" and opens "+JSON.stringify(action.href)),
  ...actions.filter(action=>action.text===label&&!action.lead&&action.href!==path).map(action=>"a "+JSON.stringify(label)+" action opens "+JSON.stringify(action.href)),
  ...actions.filter(action=>redundantAccessLabel.test(action.text)).map(action=>"a second label for the same journey: "+JSON.stringify(action.text)),
  ...actions.filter(action=>invitationAccessLabel.test(action.text)).map(action=>"an invitation request, which the owner retired on September 23, 2026: "+JSON.stringify(action.text)),
  ...actions.filter(action=>creationAccessLabel.test(action.text)&&(!takesAccounts||!(action.lead||action.account))).map(action=>(takesAccounts?"account creation offered outside the funnel, the guide's lead and the account pages: ":"account creation offered while the service takes no new accounts: ")+JSON.stringify(action.text))];};
/* The guide, Get set up, leads with one panel: "register", "invite" or "operator". The reader says which panel is shown, whether
   the panel's link to the Get started funnel and the account action can be seen, and whether the panel is the first thing under
   the page heading. The form that takes an address lives in the funnel, so it is never seen here. */
const startLead=target=>target.evaluate(()=>{
  const lead=document.getElementById("start-access"),seen=id=>{const node=document.getElementById(id);return Boolean(node&&node.getClientRects().length>0);};
  return {state:lead?.dataset.startAccess||"",shown:[...document.querySelectorAll("[data-start-state]")].filter(panel=>!panel.hidden).map(panel=>panel.dataset.startState),
    form:seen("waitlist-form"),inviteLink:seen("start-invite-link"),register:seen("start-register"),signIn:seen("start-sign-in"),
    leads:Boolean(lead&&document.querySelector('[data-view="setup"] [data-get-started-step]')===lead)};
});
const sameLead=(lead,state)=>lead.state===state&&JSON.stringify(lead.shown)===JSON.stringify([state])&&lead.form===false&&lead.inviteLink===(state==="invite")&&lead.register===(state==="register")&&lead.signIn&&lead.leads;
/* At phone width the header links fold into a menu, so the suite opens the menu first, as a visitor would. The Get started
   action stays in the header bar at every width. */
const headerLink=async (target,name)=>{
  const link=target.locator('header nav a[data-page="'+name+'"]');
  if(!await link.isVisible()&&await target.locator("header .menu-button").isVisible())await target.locator("header .menu-button").click();
  await link.click();
};
/* Signing out from the header, as a signed-in person would. The header offers Sign out, not Sign in, once the page holds a
   sign-in, and at phone width the entry sits in the folded menu. */
const signOutFromHeader=async target=>{
  const button=target.locator("#header-sign-out");
  if(!await button.isVisible()&&await target.locator("header .menu-button").isVisible())await target.locator("header .menu-button").click();
  await button.click();
};
const menuState=target=>target.evaluate(()=>({links:[...document.querySelectorAll("header nav a")].filter(node=>node.getClientRects().length>0).map(node=>node.textContent.trim()),
  primary:Boolean(document.getElementById("header-primary")?.getClientRects().length),open:document.getElementById("menu-button")?.getAttribute("aria-expanded")==="true",
  focusMark:getComputedStyle(document.querySelector("header .menu-button")||document.body).outlineStyle,path:location.pathname}));
/* The signed-out menu, in the order of the site map's signed-out header: the pages, the guide and Sign in. */
const menuLinks=["How it works","Use cases","Library","Pricing","Docs","Get set up","Sign in"];
const menuWorks=states=>states.closed.links.length===0&&states.closed.primary&&!states.closed.open
  &&JSON.stringify(states.pressed.links)===JSON.stringify(menuLinks)&&states.pressed.open&&states.pressed.primary
  &&!states.escaped.open&&states.escaped.links.length===0
  &&JSON.stringify(states.keyed.links)===JSON.stringify(menuLinks)&&states.keyed.focusMark!=="none"
  &&states.chosen.path==="/pricing"&&!states.chosen.open&&states.chosen.links.length===0&&states.chosen.primary;
/* The guide is in the signed-out header since September 23, 2026, and in the footer, the hero and the funnel. The footer's link
   is the one every page carries in every sign-in state, so the journey opens the guide from there. */
const openGuide=async target=>{await target.locator('footer a[data-nav="get-set-up"]').click();};
const openGetStarted=async target=>{await openGuide(target);return startLead(target);};
/* One press on the hero's primary action, and where the funnel's email field then stands in the window. The live review of
   September 22 asked for one action that lands on a visible email field with no page or press in between; since September 23 the
   field is #funnel-email in the Get started funnel itself, with no second page behind it. */
const pressThePrimaryAction=async (target,width,height)=>{
  const label=((await target.locator("#hero-primary").textContent())||"").replace(/[↗→]/g,"").trim();
  await target.locator("#hero-primary").click();
  await target.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:5000}).catch(()=>{});
  return {width,height,label,...await target.evaluate(()=>{const node=document.getElementById("funnel-email"),box=node?node.getBoundingClientRect():null;
    return {path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),
      shown:Boolean(node&&node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden"),top:box?Math.round(box.top):-1,bottom:box?Math.round(box.bottom):-1,viewport:innerHeight};})};
};
const landsOnTheField=item=>item.label===accessLabels.closed&&item.path===accessPaths.closed&&JSON.stringify(item.views)===JSON.stringify(["start"])&&item.shown&&item.top>=0&&item.bottom<=item.viewport;
/* The first screen on a phone: where the hero's primary action stands, how tall the header is, and whether the page scrolls sideways. */
const firstScreen=target=>target.evaluate(()=>{const box=document.getElementById("hero-primary")?.getBoundingClientRect()||{top:-1,bottom:-1};
  return {top:Math.round(box.top),bottom:Math.round(box.bottom),viewport:innerHeight,width:innerWidth,header:Math.round(document.querySelector("header")?.getBoundingClientRect().height||0),overflow:document.documentElement.scrollWidth>innerWidth+1};});
const phoneFirstScreen=item=>item.top>=0&&item.bottom<=item.viewport&&item.header>0&&item.header<=80;
/* Visual structure. The owner, September 22, 2026: "there is too much white, no clear seperations or off white or best
   practices or horizontal breaks seperating sections". The page ground is not plain white, every top-level part of the
   homepage is a band, and each band is set off from the one above it by a change of ground and by a visible rule, as the design
   draws it. A colour that is fully transparent is read through to the colour behind it, and a rule counts only when it
   differs from both grounds. */
const homeBands=target=>target.evaluate(()=>{
  const home=document.querySelector('[data-view="home"]');
  const transparent=color=>color==="transparent"||/rgba\([^)]*,\s*0\)$/.test(color);
  const painted=node=>{for(let current=node;current;current=current.parentElement){const color=getComputedStyle(current).backgroundColor;if(!transparent(color))return color;}return "rgb(255, 255, 255)";};
  const edge=(node,side,grounds)=>{const style=getComputedStyle(node),color=style["border"+side+"Color"];return parseFloat(style["border"+side+"Width"])>0&&style["border"+side+"Style"]!=="none"&&!transparent(color)&&!grounds.includes(color)?color:"";};
  const bands=home?[...home.children].filter(node=>getComputedStyle(node).display!=="none"&&node.getBoundingClientRect().height>0):[];
  return {count:bands.length,ground:painted(document.body),pairs:bands.slice(1).map((node,index)=>{const above=bands[index],grounds=[painted(above),painted(node)];
    return {above:above.dataset.band||above.className,below:node.dataset.band||node.className,grounds,rule:edge(above,"Bottom",grounds)||edge(node,"Top",grounds)};})};
});
const bandProblems=measured=>[...(measured.count<6?["the homepage has "+measured.count+" bands, fewer than six"]:[]),...(["","rgb(255, 255, 255)"].includes(measured.ground)?["the page ground is plain white"]:[]),
  ...measured.pairs.filter(pair=>pair.grounds[0]===pair.grounds[1]).map(pair=>pair.above+" and "+pair.below+" share one ground"),
  ...measured.pairs.filter(pair=>pair.rule==="").map(pair=>pair.above+" meets "+pair.below+" with no rule")];
/* The pricing band on a wide screen. The heading column and the plan card sit side by side, and the heading starts at the top of
   the card, so no empty area opens above the heading beside the taller card. The review of September 23 found the column centred
   beside the card. On a phone the two stack, and the reader reports the card below the heading instead of beside it. */
const pricingColumns=target=>target.evaluate(async ()=>{await document.fonts.ready;const band=document.querySelector('[data-band="pricing"]'),box=selector=>band?.querySelector(selector)?.getBoundingClientRect()||null;
  const title=box(".pricing-teaser > .section-title"),card=box(".pricing-teaser > .plan-summary");
  return {width:innerWidth,titleTop:title?Math.round(title.top):null,titleLeft:title?Math.round(title.left):null,cardTop:card?Math.round(card.top):null,cardLeft:card?Math.round(card.left):null};});
const headingMeetsTheCard=measured=>measured.titleTop!==null&&measured.cardTop!==null&&measured.cardLeft>measured.titleLeft&&Math.abs(measured.titleTop-measured.cardTop)<=1;
/* The primary buttons a visitor can see: in the header, in the footer and in the page that is shown. */
const primaryActions=target=>target.evaluate(()=>[...document.querySelectorAll("header .button.primary, footer .button.primary, [data-view]:not([hidden]) .button.primary")]
  .filter(node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden")
  .map(node=>({id:node.id,text:node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),href:node.getAttribute("href")||"",header:Boolean(node.closest("header"))})));
const primaryProblems=(actions,registrationOpen=false)=>[...(actions.length?[]:["no primary action is shown"]),
  ...actions.filter(action=>action.text!==stateLabel(registrationOpen)||action.href!==statePath(registrationOpen)).map(action=>"a primary action says "+JSON.stringify(action.text)+" and opens "+JSON.stringify(action.href))];
/* The hero since September 24, 2026: no worked example, only the working directory one step gets. The owner: "instead of
   showing a simple example, we should show the directory structure emphasize that it is built on demand efficiently, no manual
   searches, no manual setup". The figure names the four parts a step's directory holds, the instruction file with only that step's
   context, the skill it needs, its protocol server settings and reused code, says it is an example layout, and says the files were
   placed with no manual search and no manual setup. What works today stays apart from what is built but not shipped: a person's
   agent searches and Baltor places the chosen files, while assembling a directory for every step is what the local engine is built
   to do, so a sentence about assembling or building for each step says "built to". A worked example anywhere in the hero, a
   search, its references, its digests or a download, is the known-wrong page; the demonstrations show those. */
const heroDirectoryParts=["instructions","skills","tools","code"];
/* A sentence that assembles or builds something for each or every step, or for this step, without saying the engine is built to. */
const perStepClaim=text=>text.split(/(?<=[.!?])\s+/).filter(sentence=>/\b(?:assembl|build|built)\w*\b[^.!?]*\b(?:each|every|this|one)\s+(?:step|subtask)\b/i.test(sentence)&&!/\bbuilt to\b/i.test(sentence));
const heroDirectory=target=>target.evaluate(()=>{
  const band=document.querySelector('[data-view="home"] [data-band="hero"]'),figure=band?.querySelector("[data-hero-directory]"),shown=node=>Boolean(node&&node.getClientRects().length>0);
  return {shown:shown(figure),parts:figure?[...figure.querySelectorAll("[data-hero-part]")].map(node=>node.dataset.heroPart):[],
    label:figure?.querySelector("[data-hero-label]")?.textContent.replace(/\s+/g," ").trim()||"",
    note:figure?.querySelector("[data-hero-note]")?.textContent.replace(/\s+/g," ").trim()||"",
    example:band?band.querySelectorAll("[data-step-demo], [data-demo-item], [data-demo-query], [data-demo-download], [data-demo-stage], [data-task-demo]").length:0,
    text:band?.textContent.replace(/\s+/g," ")||""};});
const heroDirectoryProblems=state=>[...(state.shown?[]:["the hero shows no working directory"]),
  ...(JSON.stringify(state.parts)===JSON.stringify(heroDirectoryParts)?[]:["the directory holds the parts "+JSON.stringify(state.parts)]),
  ...(state.label==="Example layout"&&!invitationWords.test(state.label)?[]:["the directory is labelled "+JSON.stringify(state.label)]),
  ...(/no manual search/i.test(state.text)&&/no manual setup/i.test(state.text)?[]:["the hero does not say the files are placed with no manual search and no manual setup"]),
  ...(perStepClaim(state.text).length===0&&/\bbuilt to\b/i.test(state.note)?[]:["the hero states assembly for each step as a current capability: "+JSON.stringify(perStepClaim(state.text))]),
  ...(state.example===0&&!/\bsearch:|\bsha256\b|Bytes match the digest|Recorded from this release/i.test(state.text)?[]:["the hero shows a worked example again"])];
/* The demonstration pages show each step's search and download, recorded from this release's library: the names, kinds, licences,
   sizes and digests are compared with this release's packaged manifest, read from the source tree, and each step downloads the
   reference its search chose. tools/test_showcase_pages.py compares the order of each search with a real search of that library. */
const demoFacts=(target,view)=>target.evaluate(view=>{
  const fact=(node,name)=>node?.querySelector('[data-fact="'+name+'"]')?.textContent.trim()||"";
  return [...document.querySelectorAll('[data-view="'+view+'"] [data-task-step]')].map(step=>({items:[...step.querySelectorAll("[data-demo-item]")].map(node=>({identity:node.dataset.demoItem,
    kind:fact(node,"kind"),licence:fact(node,"licence"),size:fact(node,"size"),digest:fact(node,"digest"),chosen:node.classList.contains("is-chosen")})),
    download:step.querySelector("[data-demo-download]")?.dataset.demoDownload||""}));},view);
const releasedManifest=JSON.parse(readFileSync(resolve(root,"examples/29_intelligence_service/starter-catalogue/host-release/manifest.json"),"utf8"));
const releasedReferences=Object.fromEntries(releasedManifest.items.map(item=>[item.reference.identity,item.reference])),releasedItemCount=releasedManifest.items.length;
const kilobytes=size=>(size/1000).toFixed(1)+" KB";
const shownDigestProblem=(place,shown,expected)=>/^[0-9a-f]{8,64}$/.test(shown)&&typeof expected==="string"&&expected.startsWith(shown)?"":place+" shows sha256 "+(shown||"(nothing)")+" and this release has "+(expected||"no such item");
const demoFactProblems=steps=>[...(steps.length?[]:["the demonstration shows no step"]),...steps.flatMap((facts,step)=>[
  ...(facts.items.length?[]:["step "+(step+1)+" shows no search result"]),
  ...facts.items.flatMap((item,index)=>{const released=releasedReferences[item.identity],place="step "+(step+1)+", search result "+(index+1)+" ("+item.identity+")";
    if(!released)return [place+" is not an item of this release's library"];
    return [...(item.kind!==released.kind?[place+" shows the kind "+item.kind]:[]),...(item.licence!==released.license?[place+" shows the licence "+item.licence]:[]),
      ...(item.size!==kilobytes(released.size_bytes)?[place+" shows "+item.size+" and this release has "+kilobytes(released.size_bytes)]:[]),shownDigestProblem(place,item.digest,released.digest)].filter(Boolean);}),
  ...(facts.download&&facts.items[0]?.identity===facts.download&&facts.items[0]?.chosen?[]:["step "+(step+1)+" does not download the reference its search chose"])])];
/* The homepage cards since September 23, 2026: the six kinds of harness material and the three use cases the owner named, and
   since September 24 the three demonstrations, each in the design's order and each under its own heading. The owner removed the status words from
   them the same day, so no card carries a status tag and no card says Available now, Being built, Planned, Coming soon or that
   packages are coming. The two labels of the demonstration are the only tags the homepage keeps. A card that claims or disclaims
   a state is the known-wrong case. Each use case links to its own page. */
const kindOrder=["skills","instructions","tools","agents","hooks","servers"],useCaseOrder=["overnight","efficiency","learning"],demoCardOrder=["simple","overnight","kaggle"];
const demoCardPages={simple:"/demo",overnight:"/overnight",kaggle:"/demo/kaggle"};
const useCaseTitles={overnight:"Solve complex problems overnight",efficiency:"More efficient operation",learning:"Learning and optimization, built in"};
const homeCards=(target,selector,key)=>target.evaluate(([selector,key])=>[...document.querySelectorAll(selector)].map(node=>({name:node.dataset[key]||"",
  title:node.querySelector("h3")?.textContent.replace(/\s+/g," ").trim()||"",text:node.textContent.replace(/\s+/g," ").trim(),tags:node.querySelectorAll(".status-tag, [data-status]").length,
  links:[...node.querySelectorAll("a[href]")].map(link=>link.getAttribute("href")),shown:node.getClientRects().length>0})),[selector,key]);
const cardStatusWords=/available now|being built|\bplanned\b|coming soon|packages coming/i;
const cardProblems=(cards,order)=>[...(JSON.stringify(cards.map(card=>card.name))!==JSON.stringify(order)?["the cards are "+JSON.stringify(cards.map(card=>card.name))]:[]),
  ...cards.filter(card=>!card.shown||!card.title).map(card=>card.name+" is not shown under its own heading"),
  ...cards.filter(card=>card.tags>0||cardStatusWords.test(card.text)).map(card=>card.name+" carries a status: "+JSON.stringify(card.text.slice(0,80)))];
const useCaseProblems=cards=>[...cardProblems(cards,useCaseOrder),
  ...cards.filter(card=>useCaseTitles[card.name]!==card.title||JSON.stringify(card.links)!==JSON.stringify(["/"+card.name])).map(card=>card.name+" is titled "+JSON.stringify(card.title)+" and links "+JSON.stringify(card.links))];
/* No layout shift from late script. The first screen is measured as served, with the page script held back, and again once
   the script has run and the service has answered. Nothing measured here may move by more than one pixel. The fonts are
   waited for in both pages, so a font that arrives late is not mistaken for the script. */
const heroBoxes=target=>target.evaluate(async ()=>{await document.fonts.ready;return Object.fromEntries(['[data-view="home"] h1',"#hero-primary","#hero-setup","#hero-access-note",".hero-price",".hero-harnesses","#hero-directory",'[data-band="demos"]'].map(selector=>{
  const node=document.querySelector(selector);if(!node)return [selector,null];const box=node.getBoundingClientRect();
  return [selector,[Math.round(box.left),Math.round(box.top+scrollY),Math.round(box.width),Math.round(box.height)]];}));});
/* Text contrast, as WCAG AA sets it: 4.5 to 1 for body text and 3 to 1 for large text, measured against the solid grounds
   painted behind the text, with a translucent ground blended over the one below it. */
const contrastProblems=target=>target.evaluate(()=>{
  const parse=color=>{const found=color.match(/rgba?\(([^)]+)\)/);if(!found)return null;const part=found[1].split(",").map(Number);return {r:part[0],g:part[1],b:part[2],a:part.length>3?part[3]:1};};
  const channel=value=>{value/=255;return value<=0.03928?value/12.92:Math.pow((value+0.055)/1.055,2.4);};
  const light=color=>0.2126*channel(color.r)+0.7152*channel(color.g)+0.0722*channel(color.b);
  const blend=(top,bottom)=>({r:top.r*top.a+bottom.r*(1-top.a),g:top.g*top.a+bottom.g*(1-top.a),b:top.b*top.a+bottom.b*(1-top.a),a:1});
  const ground=node=>{const layers=[];for(let item=node;item;item=item.parentElement){const color=parse(getComputedStyle(item).backgroundColor);if(color&&color.a>0){layers.push(color);if(color.a>=1)break;}}
    return layers.reverse().reduce((below,layer)=>blend(layer,below),{r:255,g:255,b:255,a:1});};
  const ratio=(one,two)=>{const [high,low]=[light(one),light(two)].sort((x,y)=>y-x);return (high+0.05)/(low+0.05);};
  const problems=[],seen=new Set(),walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  while(walker.nextNode()){
    const node=walker.currentNode.parentElement;if(!walker.currentNode.textContent.trim()||!node||seen.has(node))continue;seen.add(node);
    const style=getComputedStyle(node);if(!node.getClientRects().length||style.visibility==="hidden"||node.closest("[hidden]"))continue;
    const colour=parse(style.color),below=ground(node);if(!colour)continue;
    const size=parseFloat(style.fontSize),large=size>=24||(parseInt(style.fontWeight,10)>=700&&size>=18.66),need=large?3:4.5,have=ratio(colour.a<1?blend(colour,below):colour,below);
    if(have<need-0.01)problems.push({text:walker.currentNode.textContent.trim().slice(0,40),ratio:Math.round(have*100)/100,need});
  }
  return problems;});
/* The focus mark of each of the first stops the keyboard reaches: every one carries a visible outline at least two pixels wide. */
const focusMarks=async (target,stops)=>{const marks=[];await target.evaluate(()=>{document.activeElement?.blur();scrollTo(0,0);});
  /* A press on the appearance switch leaves the keyboard's starting point at the foot of the page, so the keyboard first comes
     round to the skip link, which is where the count starts. */
  for(let press=0;press<4&&!await target.evaluate(()=>Boolean(document.activeElement?.classList.contains("skip")));press++)await target.keyboard.press("Tab");
  for(let index=0;index<stops;index++){if(index)await target.keyboard.press("Tab");marks.push(await target.evaluate(()=>{const node=document.activeElement,style=node?getComputedStyle(node):null;
    const label=node?.id?document.querySelector('label[for="'+node.id+'"]'):null,shown=label&&getComputedStyle(label).outlineStyle!=="none"?getComputedStyle(label):style;
    return {name:(node?.id||node?.textContent||node?.tagName||"").trim().slice(0,30),outline:shown?shown.outlineStyle:"none",width:shown?parseFloat(shown.outlineWidth):0};}));}
  return marks;};
const unmarkedStops=marks=>marks.filter(mark=>mark.outline==="none"||mark.width<2);
const boxesMoved=(served,after)=>Object.keys(served).filter(key=>!served[key]||!after[key]||served[key].some((value,index)=>Math.abs(value-after[key][index])>1));
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
const connectState=async page=>({shown:await page.locator('#client-tabs [role="tab"]').count()>0,refusal:await page.locator("#setup-message").evaluate(node=>node.dataset.refusal||"")});
async function openConnect(context,base,{served,mutation}={}){
  const page=await context.newPage(),state={applied:false,errors:[],policy:""};
  page.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
  await page.addInitScript(()=>{window.policyViolations=[];addEventListener("securitypolicyviolation",event=>window.policyViolations.push(event.violatedDirective));});
  if(served)await page.route(assetRoute("/assets/client-recipes.json",base),route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify(served)}));
  if(mutation)await page.route(assetRoute("/assets/service.js",base),async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
  state.policy=(await page.goto(base+"/connect")).headers()["content-security-policy"]||"";
  await page.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0||document.querySelector("#setup-message").textContent!=="");
  return {page,state};
}
async function checkShownRecipe(page,base,record,recipe,note){
  const endpoint=base+"/mcp",variable=record.credential_variable,id=recipe.id,content=selector=>page.locator(selector).evaluate(node=>node.textContent);
  await page.locator("#client-tab-"+id).click();
  const shown=await content("#client-configuration"),expected=withEndpoint(recipe.configuration,endpoint);
  let parsed=null;try{parsed=recipe.format==="toml"?readToml(shown):JSON.parse(shown);}catch(_){}
  note("recipe_renders_"+id,parsed!==null&&sameValue(parsed,expected)&&(recipe.format!=="json"||shown===JSON.stringify(expected,null,2))&&await content("#configuration-location")===recipe.configuration_location&&await content("#client-configuration-note")===recipe.configuration_note&&await content("#client-version-note")===recipe.version_note&&JSON.stringify(await page.locator('#client-tabs [role="tab"][aria-selected="true"]').allInnerTexts())===JSON.stringify([recipe.name]));
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
  note("connect_view_uses_plain_words_"+id,!internalTerms.test(withoutProgramName(view)));
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
const localOnly=route=>{const url=route.request().url(); if([fixture.base,fixture.billing_base,fixture.account_base,fixture.signup_base,fixture.checkout_signup_base,fixture.browse_base,fixture.identity_origin,fixture.confirm_base,fixture.confirm_identity_origin,fixture.staff_base].some(origin=>url.startsWith(origin+"/")))route.continue(); else {network.push(new URL(url).origin);route.abort();}};
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
  /* The brand mark, traced from variation 52 of the owner's logo sheet of September 23, 2026: the header shows it as an image
     with an empty text alternative, because the name follows it, and the page names it as its icon. Each file is served with
     its exact media type. */
  const markState=await page.evaluate(()=>{const mark=document.querySelector("header .brand img.brand-mark");
    return {src:mark?.getAttribute("src")||"",alt:mark?.getAttribute("alt"),loaded:Boolean(mark&&mark.complete&&mark.naturalWidth>0),named:document.querySelector("header .brand")?.getAttribute("aria-label")||"",
      icons:[...document.querySelectorAll('link[rel="icon"], link[rel="apple-touch-icon"]')].map(link=>[link.getAttribute("rel"),link.getAttribute("type")||"",link.getAttribute("href")])};});
  const iconTypes={"/assets/baltor-mark.svg":"image/svg+xml","/assets/favicon-32.png":"image/png","/assets/favicon-192.png":"image/png","/assets/apple-touch-icon.png":"image/png"};
  const servedTypes={};
  for(const path of Object.keys(iconTypes)){const response=await page.request.get(fixture.base+path);servedTypes[path]=response.status()===200?(response.headers()["content-type"]||""):"status "+response.status();}
  const markProblems=(state,types)=>[...(sameOriginAsset(state.src,fixture.base,"/assets/baltor-mark.svg")&&state.alt===""&&state.loaded&&state.named.endsWith(" home")?[]:["the header mark is not the versioned brand mark image with an empty alternative"]),
    ...(state.icons.some(([rel,type,href])=>rel==="icon"&&type==="image/svg+xml"&&sameOriginAsset(href,fixture.base,"/assets/baltor-mark.svg"))&&state.icons.some(([rel,,href])=>rel==="apple-touch-icon"&&sameOriginAsset(href,fixture.base,"/assets/apple-touch-icon.png"))?[]:["the page does not name its versioned icons"]),
    ...Object.entries(iconTypes).filter(([path,type])=>!(types[path]||"").startsWith(type)).map(([path])=>path+" is served as "+types[path])];
  check("brand_mark_is_shown_named_and_served",markProblems(markState,servedTypes).length===0,{mark:markState,served:servedTypes,problems:markProblems(markState,servedTypes)});
  check("mark_check_rejects_a_missing_icon_a_wrong_media_type_and_a_repeated_name",markProblems({...markState,icons:[]},servedTypes).length===1
    &&markProblems(markState,{...servedTypes,"/assets/favicon-32.png":"text/plain"}).length===1&&markProblems({...markState,alt:"Baltor logo"},servedTypes).length===1);
  const versionedMark="/assets/baltor-mark.svg?v="+assetDigest("/assets/baltor-mark.svg");
  check("asset_identity_check_rejects_stale_versions_foreign_origins_and_extra_query_fields",sameOriginAsset(versionedMark,fixture.base,"/assets/baltor-mark.svg")
    &&["/assets/baltor-mark.svg",versionedMark.replace(/v=./,"v=x"),versionedMark+"&extra=1",versionedMark+"&v="+assetDigest("/assets/baltor-mark.svg"),versionedMark+"#other","https://foreign.example.invalid"+versionedMark].every(value=>!sameOriginAsset(value,fixture.base,"/assets/baltor-mark.svg"))
    &&!assetRoute("/assets/baltor-mark.svg",fixture.base)(new URL("https://foreign.example.invalid"+versionedMark)));
  /* The tile shows nothing outside its rounded corners. The first tracing carried white fragments of the sheet's paper there,
     which showed as white corners on a dark ground and in a dark browser tab. The bytes each address serves are drawn on a
     canvas at the file's own size in a blank page, because the service's page policy admits images from its own origin only,
     and every light pixel outside the rounded tile is counted. The known-wrong mark is the served mark with one white corner
     added, drawn the same way. */
  const lightOutsideTheTile=async sources=>{
    const drawn=[];
    for(const [name,address,size,planted] of sources){
      const response=await page.request.get(fixture.base+address),bytes=await response.body();
      const body=address.endsWith(".svg")?Buffer.from(bytes.toString("utf8").replace("<svg ",'<svg width="'+size+'" height="'+size+'" ').replace("</svg>",planted+"</svg>")):bytes;
      drawn.push([name,"data:"+(address.endsWith(".svg")?"image/svg+xml":"image/png")+";base64,"+body.toString("base64"),size,response.status()]);
    }
    const blank=await context.newPage();
    try{return await blank.evaluate(async drawn=>{
      const counts={};
      for(const [name,source,size,status] of drawn){
        if(status!==200){counts[name]="status "+status;continue;}
        const image=new Image();image.src=source;await image.decode();
        const canvas=document.createElement("canvas");canvas.width=size;canvas.height=size;
        const drawing=canvas.getContext("2d");drawing.drawImage(image,0,0,size,size);
        const pixels=drawing.getImageData(0,0,size,size).data,radius=0.22*size;let light=0;
        for(let y=0;y<size;y++)for(let x=0;x<size;x++){
          const cx=x+.5,cy=y+.5,ax=cx<radius?radius:cx>size-radius?size-radius:null,ay=cy<radius?radius:cy>size-radius?size-radius:null;
          if(ax===null||ay===null||Math.hypot(cx-ax,cy-ay)<=radius-1)continue;
          const at=(y*size+x)*4;if(pixels[at+3]>64&&Math.min(pixels[at],pixels[at+1],pixels[at+2])>180)light++;
        }
        counts[name]=light;
      }
      return counts;
    },drawn);}finally{await blank.close();}
  };
  const tileCorners=await lightOutsideTheTile([["baltor-mark.svg","/assets/baltor-mark.svg",200,""],["favicon-32.png","/assets/favicon-32.png",32,""],
    ["favicon-192.png","/assets/favicon-192.png",192,""],["apple-touch-icon.png","/assets/apple-touch-icon.png",180,""]]);
  const plantedCorner=await lightOutsideTheTile([["baltor-mark.svg with a white corner","/assets/baltor-mark.svg",200,'<path d="M0 0H110V110H0Z" fill="#FFFFFF"/>']]);
  check("brand_mark_and_icons_show_nothing_outside_the_rounded_tile",Object.keys(tileCorners).length===4&&Object.values(tileCorners).every(count=>count===0),{light_pixels_outside_the_tile:tileCorners});
  check("tile_corner_check_rejects_a_mark_with_a_white_corner",Object.values(plantedCorner)[0]>0,{light_pixels_outside_the_tile:plantedCorner});
  /* The typefaces come from this service, not from a font host: the page policy allows fonts from its own origin only, and every
     request to another origin is refused and reported by this suite. Both faces the design names are in use on the homepage. */
  const typefaces=await page.evaluate(async()=>{await document.fonts.ready;return [...new Set([...document.fonts].filter(face=>face.status==="loaded").map(face=>face.family.replace(/["']/g,"")))];});
  const bothFaces=families=>["Geist","Geist Mono"].every(family=>families.includes(family));
  check("website_typefaces_load_from_this_service",bothFaces(typefaces),{typefaces});
  check("typeface_check_rejects_a_page_without_the_code_face",!bothFaces(typefaces.filter(family=>family!=="Geist Mono"))&&!bothFaces([]));
  /* The hero, as the owner decided on September 23, 2026: it says what Baltor is, the library of everything a harness can use,
     placed where the harness reads it, and the pain it removes, the searching, sorting and copying done by hand. "One harness per
     step" left the hero the same day; it is a runtime option that the overnight page describes. Each rule has its own known-wrong case
     beside it: the owner's earlier lines, a hero that names only one of the two, and a hero that promises a fresh harness again. */
  const heroCopy=await page.locator('[data-view="home"] .hero-copy').evaluate(node=>({headline:node.querySelector("h1")?.textContent.replace(/\s+/g," ").trim()||"",
    subhead:node.querySelector(".hero-subhead")?.textContent.replace(/\s+/g," ").trim()||"",text:node.textContent.replace(/\s+/g," ").trim()}));
  const saysWhatBaltorIs=copy=>/\bharness\b/i.test(copy.headline+" "+copy.subhead)&&/\bskills\b/i.test(copy.subhead)&&/\btools\b/i.test(copy.subhead)&&/where (?:your|the|each) harness reads/i.test(copy.subhead);
  const saysThePain=copy=>/\bby hand\b/i.test(copy.subhead);
  const keepsThePerStepOptionOut=copy=>!/fresh harness|harness (?:for|per) (?:each|every) step|one harness per step/i.test(copy.text);
  const heroProblems=copy=>[...(saysWhatBaltorIs(copy)?[]:["the hero does not say what Baltor is and where the files go"]),...(saysThePain(copy)?[]:["the hero does not name the work it removes"]),
    ...(keepsThePerStepOptionOut(copy)?[]:["the hero promises a fresh harness for each step"])];
  check("homepage_hero_says_what_baltor_is_and_the_pain_it_removes",heroProblems(heroCopy).length===0&&await page.locator('[data-view="home"] .boundary-figure').count()===0,{...heroCopy,problems:heroProblems(heroCopy)});
  const earlierHero={headline:"Supercharge your developers and AI agents.",subhead:"Big tasks go better in small steps. Baltor is designed to give each step a fresh harness that holds only what that step needs, aiming to limit context drift and help smaller models do more of the work."};
  check("hero_check_rejects_the_earlier_lines_a_hero_without_the_pain_and_a_fresh_harness_promise",heroProblems({...earlierHero,text:earlierHero.headline+" "+earlierHero.subhead}).length===3
    &&heroProblems({headline:"The perfect harness setup for every task.",subhead:"Baltor finds skills, instructions and tools and puts each file where your harness reads it.",text:"The perfect harness setup for every task."}).length===1
    &&heroProblems({headline:"Stop copying files by hand.",subhead:"Nobody has to search, sort or copy them by hand.",text:"Stop copying files by hand."}).length===1
    &&heroProblems({...heroCopy,text:heroCopy.text+" Each step runs in a fresh harness."}).length===1);
  /* The model keys stay with the customer: the trust band says Baltor never asks for a model key, the footer says so on every page,
     and the closing caption claims no percentage. */
  const keyPromise=await page.evaluate(()=>({trust:document.querySelector('[data-band="trust"]')?.textContent.replace(/\s+/g," ")||"",footer:document.querySelector("footer .footer-bottom")?.textContent.replace(/\s+/g," ")||"",
    limits:document.querySelector('[data-view="home"] .benefit-limits')?.textContent.replace(/\s+/g," ")||""}));
  const keepsTheKeysPromise=state=>state.trust.includes("Baltor never asks for a model key")&&state.footer.includes("Your model keys stay with you")&&state.limits.includes("Savings depend on the task");
  check("homepage_says_the_model_keys_stay_with_the_customer",keepsTheKeysPromise(keyPromise),keyPromise);
  check("model_key_check_rejects_a_page_that_drops_the_promise",!keepsTheKeysPromise({...keyPromise,trust:keyPromise.trust.replace("Baltor never asks for a model key","")})&&!keepsTheKeysPromise({...keyPromise,footer:""})&&!keepsTheKeysPromise({...keyPromise,limits:""}));
  check("light_is_default_even_when_operating_system_is_dark",await page.evaluate(()=>document.documentElement.dataset.theme==="light"));
  /* The light ground is an off-white, not white, so the rule reads the ground the page paints in a light system setting and
     requires the same light ground in a dark one. Every channel of a light ground is at least 230. */
  const lightGround=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
  const isLight=color=>{const channels=(color.match(/\d+(?:\.\d+)?/g)||[]).slice(0,3).map(Number);return channels.length===3&&channels.every(value=>value>=230);};
  await page.emulateMedia({colorScheme:"dark"});await page.reload();
  check("operating_system_does_not_override_explicit_light_default",await page.evaluate(()=>document.documentElement.dataset.theme==="light")&&isLight(lightGround)&&await page.evaluate(()=>getComputedStyle(document.body).backgroundColor)===lightGround,{ground:lightGround});
  check("light_ground_check_rejects_a_dark_ground",!isLight("rgb(12, 20, 36)")&&isLight("rgb(243, 245, 250)"));
  await page.emulateMedia({colorScheme:"light"});
  /* The closing caption says that savings depend on the task, the model and the setup, and promises no number and no gain. On
     September 24, 2026 the owner retired captions that describe Baltor's own review of its words, so the caption no longer says
     what is not claimed; the promise check below still refuses a number, a guarantee or "always" anywhere on the homepage. */
  const limitsText=await page.locator('[data-band="closing"] .benefit-limits').innerText();
  const claimsNoGain=text=>/\bSavings depend on the task\b/i.test(text)&&!/\d+\s*%|\bguarantee\w*\b|\balways\b/i.test(text);
  check("benefit_limits_do_not_guarantee_daily_improvement",claimsNoGain(limitsText),{limits:limitsText});
  check("benefit_limit_check_rejects_a_caption_that_promises_a_gain",!claimsNoGain("Guaranteed daily gains on every task.")&&!claimsNoGain("")
    &&!claimsNoGain("Savings depend on the task, and a 40% gain is guaranteed.")&&claimsNoGain(limitsText));
  /* Landing sections and the pricing view. The page is never allowed to agree with itself: every state that depends on the
     service is read from a real service reply on its own origin, and each published fact has a known-wrong case beside it. */
  /* The owner removed the category pill above the headline on September 23, and the opening starts directly at the heading
     (docs/verification/HOMEPAGE-BADGE-AND-ASSET-DELIVERY-2026-09-23.md). The redesign of the same day did not change that
     decision, so a label above the headline is still refused here. */
  const heroOpening=await page.locator('[data-view="home"] .hero-copy').evaluate(node=>({first:node.firstElementChild?.tagName,badges:node.querySelectorAll(".hero-chip").length}));
  const startsAtHeadline=value=>value.first==="H1"&&value.badges===0;
  check("homepage_opens_with_headline_without_category_badge",startsAtHeadline(heroOpening),heroOpening);
  check("category_badge_check_rejects_the_removed_pill",!startsAtHeadline({first:"P",badges:1})&&!startsAtHeadline({first:"H1",badges:1})&&startsAtHeadline({first:"H1",badges:0}));
  /* The owner's category line, "harness and agent optimized operation", stays on every page, written out in full in the footer's
     brand column, and the hero explains the word harness by naming the harnesses Baltor sets up: exactly the five the owner named
     on September 23, 2026, in that order, with no status word beside any of them. */
  const heroHarnesses=["Claude Code","Codex","OpenCode","Pi","Baltor Harness"];
  const categoryState=await page.evaluate(()=>({footer:[...document.querySelectorAll("footer .footer-brand p")].map(node=>node.textContent.replace(/\s+/g," ").trim()).join("\n"),
    harnesses:[...document.querySelectorAll('[data-view="home"] .hero-harnesses li')].filter(node=>node.getClientRects().length>0).map(node=>node.textContent.replace(/\s+/g," ").trim())}));
  const categoryProblems=state=>[...(/^Harness and agent optimized operation\.$/m.test(state.footer)?[]:["the footer does not carry the category line in full"]),
    ...(JSON.stringify(state.harnesses)===JSON.stringify(heroHarnesses)?[]:["the hero names "+JSON.stringify(state.harnesses)])];
  check("the_owner_category_line_stays_in_full_and_the_hero_names_the_harnesses",categoryProblems(categoryState).length===0,{...categoryState,problems:categoryProblems(categoryState)});
  check("category_line_check_rejects_a_shortened_line_a_missing_harness_a_status_and_a_new_order",categoryProblems({...categoryState,footer:"Optimized operation."}).length===1
    &&categoryProblems({...categoryState,harnesses:heroHarnesses.filter(name=>name!=="Pi")}).length===1&&categoryProblems({...categoryState,harnesses:heroHarnesses.map(name=>name==="Pi"?"Pi Planned":name)}).length===1
    &&categoryProblems({...categoryState,harnesses:[...heroHarnesses].reverse()}).length===1);
  /* The price in the hero, as the owner decided on September 23, 2026: "Baltor Pro $29 a month", written the one way the design
     standards allow. */
  const heroPrice=await page.evaluate(()=>document.querySelector('[data-view="home"] .hero-price')?.textContent.replace(/\s+/g," ").trim()||"");
  const statesThePlanAndPrice=text=>/^Baltor Pro \$29 a month\b/.test(text)&&!/United States dollars|per month/i.test(text);
  check("homepage_hero_states_the_plan_and_the_price",statesThePlanAndPrice(heroPrice),{price:heroPrice});
  check("hero_price_check_rejects_a_missing_price_and_another_way_of_writing_it",!statesThePlanAndPrice("")&&!statesThePlanAndPrice("Baltor Pro")&&!statesThePlanAndPrice("Baltor Pro 29 United States dollars each month")
    &&!statesThePlanAndPrice("Baltor Pro $29 per month")&&statesThePlanAndPrice("Baltor Pro $29 a month for the whole library"));
  /* Two actions in the hero, as the owner decided on September 23, 2026: Get started, the one primary action, which opens the
     funnel, and Get set up, the secondary action, which opens the guide, with one line under them that says how the two differ.
     No second way into the access journey anywhere in the hero. */
  const readHeroActions=target=>target.locator('[data-view="home"] .hero').evaluate(hero=>{const words=node=>node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),shown=node=>node.getClientRects().length>0;
    return {primary:[...hero.querySelectorAll(".button.primary")].filter(shown).map(node=>[node.id,words(node),node.getAttribute("href")]),
      secondary:[...hero.querySelectorAll(".button.secondary")].filter(shown).map(node=>[node.id,words(node),node.getAttribute("href")]),
      journey:[...hero.querySelectorAll("a[href]")].filter(node=>/^\/(?:get-started|waitlist|signup|connect)(?:$|[/?#])/.test(node.getAttribute("href"))).length,
      paths:hero.querySelector(".hero-paths")?.textContent.replace(/\s+/g," ").trim()||""};});
  const heroActions=await readHeroActions(page);
  const heroActionProblems=state=>[...(JSON.stringify(state.primary)===JSON.stringify([["hero-primary",accessLabels.closed,accessPaths.closed]])?[]:["the hero's primary actions are "+JSON.stringify(state.primary)]),
    ...(JSON.stringify(state.secondary)===JSON.stringify([["hero-setup","Get set up","/setup"]])?[]:["the hero's secondary actions are "+JSON.stringify(state.secondary)]),
    ...(state.journey===1?[]:[state.journey+" hero links lead into the access journey"]),
    ...(state.paths===""?[]:["the hero repeats its buttons in a line of text: "+JSON.stringify(state.paths)])];
  check("homepage_hero_offers_get_started_and_get_set_up_and_says_how_they_differ",heroActionProblems(heroActions).length===0,{...heroActions,problems:heroActionProblems(heroActions)});
  check("hero_action_check_rejects_a_second_primary_a_missing_guide_and_a_missing_explanation",heroActionProblems({...heroActions,primary:[...heroActions.primary,["planted","Request an invitation","/waitlist"]],journey:heroActions.journey+1}).length===2
    &&heroActionProblems({...heroActions,secondary:[]}).length===1&&heroActionProblems({...heroActions,secondary:[["hero-see-step","See one step work","#step-demo"]]}).length===1
    &&heroActionProblems({...heroActions,paths:"Get started creates your account. Get set up connects your harness."}).length===1);
  /* Filler the owner retired on September 24, 2026: lines that repeat the buttons or describe our checks instead of the visitor's benefit. */
  const retiredFiller=["creates your account.","connects your harness.","Bytes match the digest","Recorded from this release's library"];
  const fillerProblems=text=>retiredFiller.filter(phrase=>text.includes(phrase));
  const homeText=await page.locator('[data-view="home"]').evaluate(home=>home.textContent.replace(/\s+/g," "));
  check("homepage_carries_no_retired_filler_phrases",fillerProblems(homeText).length===0,{found:fillerProblems(homeText)});
  check("filler_check_rejects_a_returned_phrase",fillerProblems(homeText+" Bytes match the digest").length===1);
  /* The single call to action. Every primary button a visitor can see on the homepage, in the header and in the footer carries
     the one label of the reported state and opens the page behind it, and the header carries exactly one of them. */
  const homePrimaries=await primaryActions(page);
  check("homepage_primary_actions_all_carry_the_one_label",primaryProblems(homePrimaries).length===0&&homePrimaries.filter(action=>action.header).length===1&&homePrimaries.length>=4,{actions:homePrimaries,problems:primaryProblems(homePrimaries)});
  check("primary_action_check_rejects_a_second_label_and_a_second_address",primaryProblems([...homePrimaries,{id:"planted",text:"Join the waiting list",href:accessPaths.closed,header:false}]).length===1&&primaryProblems([...homePrimaries,{id:"planted",text:accessLabels.closed,href:"/signup#waiting-list",header:false}]).length===1&&primaryProblems([...homePrimaries,{id:"planted",text:"Request an invitation",href:"/waitlist",header:false}]).length===1&&primaryProblems([]).length===1);
  /* The design's order since September 24, 2026: the hero with the working directory beside the copy, the three demonstrations,
     the library, the three use cases, trust, pricing, questions and the closing band. The Ask, get, place band left the homepage
     that day with a dated removal row: the hero shows the directory and the demonstrations show each run start to finish. */
  const bandOrder=["hero","demos","library","use-cases","trust","pricing","faq","closing"];
  const homeFlow=await page.locator('[data-view="home"]').evaluate(home=>({bands:[...home.children].map(node=>node.dataset.band||node.tagName.toLowerCase()),directoryIn:document.getElementById("hero-directory")?.closest("[data-band]")?.dataset.band||""}));
  const followsTheDesign=flow=>JSON.stringify(flow.bands)===JSON.stringify(bandOrder)&&flow.directoryIn==="hero";
  check("homepage_bands_follow_the_design_order",followsTheDesign(homeFlow),homeFlow);
  check("band_order_check_rejects_a_moved_band_a_returned_band_and_a_directory_outside_the_hero",!followsTheDesign({...homeFlow,bands:[bandOrder[0],bandOrder[2],bandOrder[1],...bandOrder.slice(3)]})
    &&!followsTheDesign({...homeFlow,bands:bandOrder.slice(1)})&&!followsTheDesign({...homeFlow,bands:[bandOrder[0],"how",...bandOrder.slice(1)]})&&!followsTheDesign({...homeFlow,directoryIn:"demos"}));
  /* The working directory of one step sits beside the copy in the hero on a wide screen, as the owner decided on September 24,
     2026, so the first look shows what a step gets. The known-wrong layouts put it below the copy and leave it out. */
  const heroLayout=await page.locator('[data-view="home"]').evaluate(home=>{
    const hero=home.querySelector(".product-hero"),copy=hero?.querySelector(".hero-copy"),example=hero?.querySelector(".hero-directory");
    const box=node=>node?node.getBoundingClientRect():{left:0,right:0,top:0,bottom:0};
    return {copyTop:Math.round(box(copy).top),copyBottom:Math.round(box(copy).bottom),copyRight:Math.round(box(copy).right),exampleTop:Math.round(box(example).top),
      exampleBottom:Math.round(box(example).bottom),exampleLeft:Math.round(box(example).left),hasExample:Boolean(example),hasCopy:Boolean(copy),viewport:innerWidth};
  });
  const directoryBesideTheCopy=m=>m.hasExample&&m.hasCopy&&m.viewport>=1100&&m.exampleLeft>=m.copyRight-1&&m.exampleTop<m.copyBottom&&m.exampleBottom>m.copyTop;
  check("homepage_directory_sits_beside_the_copy_in_the_hero",directoryBesideTheCopy(heroLayout),heroLayout);
  check("hero_layout_check_rejects_a_directory_below_the_copy_or_missing",!directoryBesideTheCopy({...heroLayout,exampleTop:heroLayout.copyBottom+24,exampleBottom:heroLayout.copyBottom+624,exampleLeft:heroLayout.copyRight-600})
    &&!directoryBesideTheCopy({...heroLayout,hasExample:false}));
  /* One harness per step is a runtime option since September 23, 2026: the overnight page says it can be turned on for long runs and
     off for quick ones, since the homepage's How it works band left on September 24, and the hero does not promise it. */
  const optionText=await page.locator('[data-view="overnight"]').evaluate(node=>node.textContent.replace(/\s+/g," "));
  const describesTheOption=text=>/one harness per step/i.test(text)&&/turn it on/i.test(text)&&/\boff\b/i.test(text);
  check("overnight_page_describes_one_harness_per_step_as_an_option",describesTheOption(optionText)&&keepsThePerStepOptionOut(heroCopy),{text:optionText.slice(0,600)});
  check("per_step_option_check_rejects_a_band_without_the_option_and_a_promise_in_its_place",!describesTheOption("Ask, get, place.")&&!describesTheOption("Every step runs in one harness per step.")&&describesTheOption(optionText));
  /* The hero's secondary action opens the guide, Get set up, a page of its own. */
  await page.locator("#hero-setup").click();
  const heroGuide=await page.evaluate(()=>({path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),title:document.title}));
  check("hero_get_set_up_opens_the_guide",heroGuide.path==="/setup"&&JSON.stringify(heroGuide.views)===JSON.stringify(["setup"])&&heroGuide.title.endsWith("| Get set up"),heroGuide);
  await page.goto(fixture.base+"/"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  /* The hero shows the working directory one step gets and no worked example, as the owner decided on September 24, 2026. The
     known-wrong heroes: the one-step demonstration back in it, a search with its digests, a directory without its protocol server
     settings, and a directory that no longer says it was built without manual search or setup. */
  const hero=await heroDirectory(page);
  check("homepage_hero_shows_a_directory_not_a_worked_example",heroDirectoryProblems(hero).length===0,{parts:hero.parts,label:hero.label,note:hero.note,example:hero.example,problems:heroDirectoryProblems(hero)});
  check("hero_directory_check_rejects_a_worked_example_a_missing_part_and_missing_words",heroDirectoryProblems({...hero,example:1}).length===1
    &&heroDirectoryProblems({...hero,text:hero.text+" search: split address lines, sha256 53dc74e3"}).length===1
    &&heroDirectoryProblems({...hero,parts:hero.parts.filter(part=>part!=="tools")}).length===1
    &&heroDirectoryProblems({...hero,text:hero.text.replace(/no manual setup/ig,"")}).length===1);
  /* The known-wrong heroes of the owner's constraint of September 24, 2026: assembly for each step stated as what Baltor does today,
     as a label and as a sentence, and a note that no longer says the engine is built to do it. */
  check("per_step_assembly_check_rejects_a_current_capability_claim",["Assembled for this step.","Baltor assembles a directory like this for every step.","Built on demand for each step."].every(claim=>heroDirectoryProblems({...hero,text:hero.text+" "+claim}).length===1)
    &&heroDirectoryProblems({...hero,note:hero.note.replace("is built to assemble","assembles")}).length>=1&&perStepClaim("The local engine is built to assemble a directory like this for every step.").length===0);
  /* The three demonstrations under the hero, as the owner asked on September 24, 2026: a simple task, a long task that runs
     overnight and a Kaggle solution, each linking to the page that shows it start to finish. */
  const demoCards=await homeCards(page,'[data-view="home"] [data-demo-card]',"demoCard");
  const demoCardProblems=cards=>[...cardProblems(cards,demoCardOrder),...cards.filter(card=>JSON.stringify(card.links)!==JSON.stringify([demoCardPages[card.name]])).map(card=>card.name+" links "+JSON.stringify(card.links))];
  check("homepage_links_three_demonstrations_start_to_finish",demoCardProblems(demoCards).length===0,{problems:demoCardProblems(demoCards)});
  check("demonstration_card_check_rejects_a_missing_card_and_another_address",demoCardProblems(demoCards.slice(1)).length>=1
    &&demoCardProblems(demoCards.map(card=>card.name==="kaggle"?{...card,links:["/examples"]}:card)).length===1);
  /* The demonstration pages print each step's search and download, recorded from this release's library. */
  const demoPages=[["/demo","demo"],["/demo/kaggle","demo-kaggle"]],shownFacts={};
  for(const [address,view] of demoPages){await page.goto(fixture.base+address);shownFacts[view]=await demoFacts(page,view);}
  check("demo_names_sizes_and_digests_agree_with_this_release_manifest",demoPages.every(([,view])=>demoFactProblems(shownFacts[view]).length===0),
    {problems:Object.fromEntries(demoPages.map(([,view])=>[view,demoFactProblems(shownFacts[view])]))});
  const firstStep=shownFacts.demo[0]||{items:[],download:""},oneDigestChanged=structuredClone(shownFacts.demo);
  if(oneDigestChanged[0]?.items[1])oneDigestChanged[0].items[1].digest=oneDigestChanged[0].items[1].digest.replace(/.$/,last=>last==="0"?"1":"0");
  check("demo_digest_check_rejects_a_digest_this_release_does_not_serve",firstStep.items.length>=2&&demoFactProblems(oneDigestChanged).length===1
    &&demoFactProblems([{...firstStep,download:firstStep.items[1]?.identity||""},...shownFacts.demo.slice(1)]).length===1,{problems:demoFactProblems(oneDigestChanged)});
  const releasedIdentities=Object.keys(releasedReferences);
  const namesOnlyReleasedItems=names=>names.length>0&&names.every(name=>releasedIdentities.includes(name));
  const shownIdentities=Object.values(shownFacts).flat().flatMap(step=>step.items.map(item=>item.identity));
  check("demo_names_only_released_catalogue_items",namesOnlyReleasedItems(shownIdentities),{items:shownIdentities});
  check("demo_item_check_rejects_an_item_the_library_does_not_serve",!namesOnlyReleasedItems([...shownIdentities,"invented_item_nobody_approved"]));
  /* Harness material is any file a harness reads: the library band names the scripts, the tools and code, the hooks and the protocol
     server settings beside the instruction files, and the hero's directory holds protocol server settings and reused code. */
  await page.goto(fixture.base+"/"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available"));
  const libraryText=await page.locator('[data-band="library"]').innerText();
  const namesFilesBeyondMarkdown=text=>/\bscripts\b/i.test(text)&&/tools and code/i.test(text)&&/\bhooks\b/i.test(text)&&/protocol server/i.test(text);
  check("library_names_files_beyond_markdown",namesFilesBeyondMarkdown(libraryText)&&hero.parts.includes("tools")&&hero.parts.includes("code"));
  check("library_word_check_rejects_a_band_that_names_only_instruction_files",!namesFilesBeyondMarkdown("Instruction files such as AGENTS.md and CLAUDE.md.")&&namesFilesBeyondMarkdown(libraryText));
  /* No motion of its own. With reduced motion requested, nothing on the homepage animates or moves by a transition. */
  const moving=await page.evaluate(()=>[...document.querySelectorAll('[data-view="home"], [data-view="home"] *')].filter(node=>{const style=getComputedStyle(node);return (style.animationName!=="none"&&parseFloat(style.animationDuration)>0)||parseFloat(style.transitionDuration)>0;}).length);
  check("homepage_has_no_motion_of_its_own",moving===0,{moving});
  /* The library count is this release's: the number of items in the packaged manifest. */
  const shownCount=await page.locator("[data-library-count]").innerText();
  const countAgrees=shown=>shown.trim()===String(releasedItemCount);
  check("library_count_agrees_with_this_release_manifest",countAgrees(shownCount),{shown:shownCount,released:releasedItemCount});
  check("library_count_check_rejects_a_count_this_release_does_not_hold",!countAgrees(String(releasedItemCount+1))&&!countAgrees("10,000")&&countAgrees(String(releasedItemCount)));
  /* The six kinds of harness material and the three use cases, in the design's order, each under its own heading and none with a
     status word, as the owner decided on September 23, 2026. */
  const kindCards=await homeCards(page,"[data-kind]","kind"),useCaseCards=await homeCards(page,'[data-view="home"] [data-use-case]',"useCase");
  check("library_names_the_six_kinds_without_a_status_word",cardProblems(kindCards,kindOrder).length===0,{problems:cardProblems(kindCards,kindOrder)});
  check("kind_check_rejects_a_kind_called_available_a_missing_kind_and_a_new_order",cardProblems(kindCards.map(card=>card.name==="instructions"?{...card,tags:1,text:card.text+" Available now"}:card),kindOrder).length===1
    &&cardProblems(kindCards.filter(card=>card.name!=="hooks"),kindOrder).length===1&&cardProblems([...kindCards].reverse(),kindOrder).length===1);
  check("homepage_links_the_three_use_cases_the_owner_named",useCaseProblems(useCaseCards).length===0,{problems:useCaseProblems(useCaseCards),cards:useCaseCards.map(({text,...rest})=>rest)});
  check("use_case_check_rejects_a_missing_case_another_page_another_title_and_a_status",useCaseProblems(useCaseCards.filter(card=>card.name!=="learning")).length===1
    &&useCaseProblems(useCaseCards.map(card=>card.name==="overnight"?{...card,links:["/context"]}:card)).length===1&&useCaseProblems(useCaseCards.map(card=>card.name==="efficiency"?{...card,title:"Less in each request"}:card)).length===1
    &&useCaseProblems(useCaseCards.map(card=>card.name==="learning"?{...card,text:card.text+" Planned"}:card)).length===1);
  /* Owner decision of September 21, 2026: the page says what the product does and names a real limit where there is one, and it
     does not apologise for a measurement nobody asked for. The homepage and the three use-case pages carry no apology and no
     percentage; the problems they answer now live on the use-case pages. */
  const measurementApologies=["We have not measured","Nobody has measured it yet","We have not run that as an experiment","it is an aim and not a result"];
  const apologyProblems=text=>[...measurementApologies.filter(sentence=>text.includes(sentence)).map(sentence=>"measurement apology: "+sentence),...(/\d+\s*%/.test(text)?["a percentage"]:[])];
  const claimText=await page.locator('[data-view="home"]').evaluate(node=>node.textContent),useCaseText={};
  for(const view of ["use-cases","overnight","efficiency","learning"])useCaseText[view]=await page.locator('[data-view="'+view+'"]').evaluate(node=>node.textContent).catch(()=>"");
  const apologies=[["home",claimText],...Object.entries(useCaseText)].flatMap(([view,text])=>apologyProblems(text).map(problem=>view+": "+problem));
  check("homepage_and_use_cases_carry_no_measurement_apology_and_no_percentage",apologies.length===0&&Object.values(useCaseText).every(text=>text.length>0),{problems:apologies});
  check("apology_check_rejects_a_returned_apology_and_a_percentage",measurementApologies.every(sentence=>apologyProblems(claimText+" "+sentence).length===1)&&apologyProblems(claimText+" Saves 40% of tokens.").length===1);
  /* The bands. The page ground is an off-white, and each band is set off from the next by a change of ground and by a rule. The
     known-wrong pages paint two neighbouring bands alike, take their rules away, and paint the ground white, each on its own,
     through the style object, which the page policy allows, and then put everything back. */
  const bands=await homeBands(page);
  check("homepage_sets_every_band_apart_on_an_off_white_ground",bandProblems(bands).length===0,{problems:bandProblems(bands),count:bands.count,ground:bands.ground});
  /* The planted changes touch the last two bands, where the closing band has no band below it, so each change makes exactly one
     problem whatever grounds the bands above alternate between. */
  const plantBands=change=>page.evaluate(change=>{const bands=[...(document.querySelector('[data-view="home"]')?.children||[])].filter(node=>getComputedStyle(node).display!=="none"&&node.getBoundingClientRect().height>0);if(bands.length<3)return false;const [upper,lower]=[bands.at(-2),bands.at(-1)];
    if(change==="ground")lower.style.backgroundColor=getComputedStyle(upper).backgroundColor;if(change==="rules"){upper.style.borderBottom="0";lower.style.borderTop="0";}if(change==="white")document.body.style.backgroundColor="#ffffff";return true;},change);
  const restoreBands=()=>page.evaluate(()=>{for(const node of [document.body,...(document.querySelector('[data-view="home"]')?.children||[])])node.removeAttribute("style");});
  const plantedBandProblems={};
  for(const change of ["ground","rules","white"]){plantedBandProblems[change]=await plantBands(change)?bandProblems(await homeBands(page)):["not planted"];await restoreBands();}
  check("band_check_rejects_one_ground_for_two_bands_a_missing_rule_and_a_white_ground",Object.values(plantedBandProblems).every(problems=>problems.length===1&&problems[0]!=="not planted")&&bandProblems(await homeBands(page)).length===0,{problems:plantedBandProblems});
  /* The pricing heading starts at the top of the plan card beside it on a wide screen. The known-wrong layouts are the heading
     column centred beside the taller card, as the review of September 23 found it, the card stacked under the heading, and a band
     without a card. A removed-guard control below serves the centred rule itself. */
  const pricingSideBySide=await pricingColumns(page);
  check("pricing_heading_lines_up_with_the_top_of_the_plan_card",pricingSideBySide.width>=1100&&headingMeetsTheCard(pricingSideBySide),pricingSideBySide);
  check("pricing_alignment_check_rejects_a_centred_heading_a_stacked_card_and_a_missing_card",headingMeetsTheCard(pricingSideBySide)
    &&!headingMeetsTheCard({...pricingSideBySide,titleTop:pricingSideBySide.cardTop+187})&&!headingMeetsTheCard({...pricingSideBySide,cardLeft:pricingSideBySide.titleLeft})
    &&!headingMeetsTheCard({...pricingSideBySide,cardTop:null}),pricingSideBySide);
  /* Contrast and focus in both appearances. Every text on the public pages meets WCAG AA against the ground behind it, and each of
     the first stops the keyboard reaches on the homepage carries a visible focus mark. The known-wrong page plants one grey line
     on a white ground through the style object, which the page policy allows, and one focus stop without a mark. */
  const contrastByTheme={},marksByTheme={};
  for(const theme of ["light","dark"]){
    for(const path of ["/","/waitlist","/pricing","/how-it-works","/docs","/privacy","/login"]){
      await page.goto(fixture.base+path);await page.waitForFunction(()=>document.querySelector("#service-status")?.textContent==="Service available");
      for(let press=0;press<3&&await page.evaluate(wanted=>document.documentElement.dataset.theme!==wanted,theme);press++)await page.click("#theme");
      contrastByTheme[theme+" "+path]=await contrastProblems(page);
      if(path==="/")marksByTheme[theme]=await focusMarks(page,12);
    }
  }
  for(let press=0;press<3&&await page.evaluate(()=>document.documentElement.dataset.theme!=="light");press++)await page.click("#theme");
  const lowContrast=Object.entries(contrastByTheme).filter(([,problems])=>problems.length).map(([page,problems])=>({page,problems:problems.slice(0,4)}));
  check("public_text_meets_AA_contrast_in_both_appearances",Object.keys(contrastByTheme).length===14&&lowContrast.length===0,{pages:Object.keys(contrastByTheme).length,lowContrast});
  await page.goto(fixture.base+"/");
  const plantedGrey=await page.evaluate(()=>{const line=document.createElement("p");line.id="known-wrong-grey";line.textContent="A grey line nobody can read";line.style.color="#c4c4c4";line.style.backgroundColor="#ffffff";document.querySelector('[data-band="library"]').append(line);return true;});
  const greyProblems=await contrastProblems(page);await page.evaluate(()=>document.getElementById("known-wrong-grey")?.remove());
  check("contrast_check_rejects_a_grey_line_on_white",plantedGrey&&greyProblems.length===1&&greyProblems[0].text==="A grey line nobody can read",{problems:greyProblems});
  check("keyboard_focus_is_visible_in_both_appearances",["light","dark"].every(theme=>(marksByTheme[theme]||[]).length===12&&unmarkedStops(marksByTheme[theme]).length===0),{marks:marksByTheme});
  check("focus_check_rejects_a_stop_without_a_mark",unmarkedStops([...(marksByTheme.light||[]),{name:"planted",outline:"none",width:0}]).length===1);
  /* Every reviewed recipe's client is among the harnesses the hero names, so no client the guide sets up is left unnamed. The
     converse, that the guide sets up every harness the hero names, is checked on the guide itself below. */
  const recipeClients=recipeRecord.recipes.map(recipe=>recipe.name.replace(/\s+\d+(?:\.\w+)*$/,"")).sort();
  const namesEveryRecipeClient=names=>recipeClients.length>0&&recipeClients.every(name=>names.includes(name));
  check("hero_names_every_client_the_reviewed_recipes_set_up",namesEveryRecipeClient(categoryState.harnesses),{recipes:recipeClients,hero:categoryState.harnesses});
  check("recipe_client_check_rejects_a_hero_list_without_a_reviewed_client",!namesEveryRecipeClient(categoryState.harnesses.filter(name=>name!=="Codex"))&&!namesEveryRecipeClient([]));
  /* What an account gives you, in the plan summary on the homepage: the whole library, the download as the measured unit, a key for
     each client and the usage record. */
  const offers=await page.locator("[data-offer]").evaluateAll(items=>items.map(item=>item.dataset.offer).sort()),planText=await page.locator(".plan-summary").innerText();
  const givesEveryOffer=(names,text)=>JSON.stringify(names)===JSON.stringify(["downloads","keys","library","usage"])&&["search","download","usage"].every(word=>text.toLowerCase().includes(word));
  check("homepage_says_what_an_account_gives_you",givesEveryOffer(offers,planText),{offers});
  check("offer_check_rejects_a_summary_without_the_usage_record",!givesEveryOffer(offers.filter(name=>name!=="usage"),planText)&&!givesEveryOffer(offers,planText.replace(/usage/gi,"")));
  /* The pricing band on the homepage states the price the one way the design standards allow, "$29 a month", and the measured unit,
     and links the pricing page. It no longer says who is free: the owner removed that on September 23, 2026. */
  const teaserText=await page.locator(".pricing-teaser").innerText();
  const teaserProblems=text=>[...(/\$29 a month/.test(text)?[]:["no \"$29 a month\""]),...(/per month|United States dollars/i.test(text)?["the price is written another way"]:[]),
    ...(/one downloaded item/i.test(text)?[]:["no measured unit"]),...(invitationWords.test(text)?["a retired word: "+text.match(invitationWords)[0]]:[])];
  check("homepage_states_the_plan_price_and_the_measured_unit",teaserProblems(teaserText).length===0&&await page.locator('.pricing-teaser a[data-page="pricing"]').getAttribute("href")==="/pricing",{problems:teaserProblems(teaserText)});
  check("teaser_check_rejects_another_price_phrase_a_missing_unit_and_free_invited_accounts",teaserProblems(teaserText.replace("$29 a month","$29 per month")).length>=1&&teaserProblems(teaserText.replace(/one downloaded item/gi,"one call")).length===1
    &&teaserProblems(teaserText+" Invited accounts are free.").length===1&&teaserProblems(teaserText+" Search is free.").length===1);
  /* The closing band holds the one primary action, Get started, and at most the guide beside it as a secondary action. */
  const closingActions=await page.locator('[data-band="closing"]').evaluate(band=>[...band.querySelectorAll("a, button")].filter(node=>node.getClientRects().length>0)
    .map(node=>({id:node.id,text:node.textContent.replace(/[↗→]/g,"").replace(/\s+/g," ").trim(),href:node.getAttribute("href")||"",primary:node.classList.contains("primary")})));
  const closingProblems=actions=>[...(JSON.stringify(actions.filter(action=>action.primary).map(action=>[action.id,action.text,action.href]))===JSON.stringify([["closing-primary",accessLabels.closed,accessPaths.closed]])?[]:["the closing band's primary actions are "+JSON.stringify(actions.filter(action=>action.primary))]),
    ...actions.filter(action=>!action.primary&&!(action.text==="Get set up"&&action.href==="/setup")).map(action=>"the closing band also offers "+JSON.stringify(action.text)+" at "+JSON.stringify(action.href))];
  check("homepage_closes_with_one_action_and_the_guide",closingProblems(closingActions).length===0,{actions:closingActions,problems:closingProblems(closingActions)});
  check("closing_check_rejects_a_second_primary_and_a_second_way_in",closingProblems([...closingActions,{id:"planted",text:"Join the waiting list",href:"/waitlist",primary:true}]).length===1
    &&closingProblems([...closingActions,{id:"",text:"Request an invitation",href:"/waitlist",primary:false}]).length===1&&closingProblems(closingActions.filter(action=>!action.primary)).length===1);
  /* No number, guarantee or "always" on the homepage and the use-case pages, which sell: those are statements of fact and need
     evidence. Since September 24, 2026 the closing caption is read too, because it no longer names what is not claimed. */
  const promiseWords=/\d+\s*%|\bguarantee\w*\b|\balways\b/gi,homeClaims=await page.locator('[data-view="home"]').evaluate(node=>node.textContent)+" "+Object.values(useCaseText).join(" ");
  check("homepage_and_use_cases_make_no_unmeasured_promise",(homeClaims.match(promiseWords)||[]).length===0,{words:[...new Set(homeClaims.match(promiseWords)||[])]});
  check("promise_check_rejects_a_known_wrong_claim",["Cut your token spend by 40%","Always picks the right model","Guaranteed savings every day","A 3 % better result"].every(claim=>(claim.match(promiseWords)||[]).length>0));
  /* The page reads without its script: a browser that never receives the script shows the hero with its price, its two actions,
     the harnesses and the working directory, the three demonstrations and the three use cases. */
  const withoutScript=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:"reduce"});
  await withoutScript.route("**/*",localOnly);
  await withoutScript.route(assetRoute("/assets/service.js",fixture.base),route=>route.abort());
  const plain=await withoutScript.newPage();
  plain.on("pageerror",()=>{});
  await plain.goto(fixture.base+"/");
  const plainHome=await plain.evaluate(()=>({price:document.querySelector('[data-view="home"] .hero-price')?.textContent.replace(/\s+/g," ").trim()||"",
    actions:["hero-primary","hero-setup"].filter(id=>(document.getElementById(id)?.getClientRects().length||0)>0),
    harnesses:[...document.querySelectorAll('[data-view="home"] .hero-harnesses li')].filter(node=>node.getClientRects().length>0).map(node=>node.textContent.trim())}));
  const plainProblems=[...(statesThePlanAndPrice(plainHome.price)?[]:["the hero shows no price"]),...(plainHome.actions.length===2?[]:["the hero shows the actions "+JSON.stringify(plainHome.actions)]),
    ...(JSON.stringify(plainHome.harnesses)===JSON.stringify(heroHarnesses)?[]:["the hero names "+JSON.stringify(plainHome.harnesses)]),...useCaseProblems(await homeCards(plain,'[data-view="home"] [data-use-case]',"useCase"))];
  check("homepage_reads_when_the_script_has_not_run",plainProblems.length===0,{problems:plainProblems});
  const plainHero=await heroDirectory(plain),plainDemos=await homeCards(plain,'[data-view="home"] [data-demo-card]',"demoCard");
  check("hero_directory_and_demonstrations_read_when_the_script_has_not_run",heroDirectoryProblems(plainHero).length===0&&demoCardProblems(plainDemos).length===0,{problems:[...heroDirectoryProblems(plainHero),...demoCardProblems(plainDemos)]});
  /* No layout shift from late script. The first screen is measured without the page script, then on a page whose script has
     run and whose service has answered, at the desktop and the phone width. */
  const steadiness=[];
  for(const width of [1440,390]){
    await plain.setViewportSize({width,height:1000});await plain.goto(fixture.base+"/");const served=await heroBoxes(plain);
    const scripted=await context.newPage();scripted.on("pageerror",error=>errors.push(safeError(error.message)));
    await scripted.setViewportSize({width,height:1000});await scripted.goto(fixture.base+"/");
    await scripted.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
    steadiness.push({width,served,moved:boxesMoved(served,await heroBoxes(scripted))});await scripted.close();
  }
  servedHeroBoxes=steadiness[0].served;
  check("homepage_first_screen_does_not_move_when_the_script_runs",steadiness.length===2&&steadiness.every(item=>item.moved.length===0&&Object.values(item.served).every(Boolean)),{moved:steadiness.map(item=>({width:item.width,moved:item.moved}))});
  const nudged=Object.fromEntries(Object.entries(servedHeroBoxes).map(([key,box])=>[key,key==="#hero-primary"&&box?box.map((value,index)=>index===1?value+3:value):box]));
  check("steadiness_check_rejects_a_first_screen_that_moves",JSON.stringify(boxesMoved(servedHeroBoxes,nudged))===JSON.stringify(["#hero-primary"]));
  /* The last measurement left the page without its script at phone width. Until September 24, 2026 a checkbox opened the menu
     without the script, but a checkbox cannot say whether the menu is open, and the persona journeys of that day found its name on
     a control clipped to one pixel under the logo while the icon a person touches was hidden from assistive technology. The menu is
     now one button that the script runs. Without the script the served button already carries its name, its collapsed state and
     the navigation it controls, and the footer, which needs no script, links every page the menu holds. */
  const plainMenu=await plain.evaluate(()=>{const button=document.getElementById("menu-button"),footer=[...document.querySelectorAll("footer a")].map(link=>link.getAttribute("href"));
    return {named:button?.getAttribute("aria-label")||"",expanded:button?.getAttribute("aria-expanded")||"",controls:button?.getAttribute("aria-controls")||"",shown:Boolean(button?.getClientRects().length),
      menu:[...document.querySelectorAll("#main-nav a[data-signed-out], #main-nav a:not([data-signed-in]):not([id=admin-nav])")].map(link=>link.getAttribute("href")),footer};});
  const unreachable=[...new Set(plainMenu.menu)].filter(href=>!plainMenu.footer.includes(href));
  check("phone_menu_button_is_named_before_the_script_runs_and_the_footer_links_every_menu_page",plainMenu.named==="Menu"&&plainMenu.expanded==="false"&&plainMenu.controls==="main-nav"&&plainMenu.shown
    &&plainMenu.menu.length>=6&&unreachable.length===0,{...plainMenu,unreachable});
  await plain.close();await withoutScript.close();
  /* Retired words, runtime words and the words of an invitation-only service, read from every page a customer can open: the
     shared header and footer, the three use cases and their hub, and every page of the documentation index. The Documentation
     view keeps the exact runtime terms, so it and its pages are scanned for the other rules only. */
  const docsIndex=JSON.parse(readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/documentation-index.json"),"utf8"));
  const docsPagePaths=docsIndex.sections.flatMap(section=>section.pages).filter(entry=>entry.body&&entry.address.startsWith("/docs/")).map(entry=>entry.address);
  const servedRoutes=["/",...useCasePaths,"/how-it-works","/pricing","/setup","/connect","/get-started","/waitlist","/signup","/login","/examples","/security","/privacy","/terms","/app","/account","/docs",...docsPagePaths,...showcasePaths];
  /* The directory page is read like every other page, with the listings other publishers wrote left out (tools/listing_text.mjs). */
  servedRoutes.push("/directory");
  /* The scan carries no exception. The one sentence that used to need one, on the account page, was rewritten with
     the rest of the retired words, so a retired word anywhere in what a customer reads is a named failure. */
  const vocabularyProblems=[];
  /* The deck, a page with a file of its own, is read with the other pages a customer can open. */
  servedRoutes.push("/deck");
  /* A page without the shared header or footer, such as the page for an address the service does not serve, is read
     as far as it goes, so an unserved address fails its own named checks instead of stopping the whole journey. */
  const readShownText=target=>target.evaluate(([pages,attribute])=>{
    const listing=pages.includes(location.pathname)?[...document.querySelectorAll("["+attribute+"]")].filter(node=>!node.hidden):[];
    listing.forEach(node=>{node.hidden=true;});
    try{return [document.querySelector("header")?.innerText||"",[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.innerText).join("\n"),document.querySelector("footer")?.innerText||""].join("\n");}
    finally{listing.forEach(node=>{node.hidden=false;});}
  },[listingTextPages(),LISTING_TEXT_ATTRIBUTE]);
  /* The same text for the retired-word rule and the invitation-word rule, without the approved terms and the approved privacy
     notice while each is shown with exactly the approved words. They are hidden only while this one reading is taken, and shown
     again at once. */
  const readRetiredText=target=>target.evaluate(([terms,privacy,pages,attribute])=>{
    const words=text=>text.split(/\s+/).filter(Boolean),same=(node,approved)=>node.getClientRects().length>0&&JSON.stringify(words(node.innerText))===JSON.stringify(approved);
    const listing=pages.includes(location.pathname)?[...document.querySelectorAll("["+attribute+"]")].filter(node=>!node.hidden):[];
    const exempt=[...[...document.querySelectorAll("[data-terms-of-service]")].filter(node=>same(node,terms)),...[...document.querySelectorAll("[data-privacy-notice]")].filter(node=>same(node,privacy)),...listing];
    exempt.forEach(node=>{node.hidden=true;});
    try{return [document.querySelector("header")?.innerText||"",[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.innerText).join("\n"),document.querySelector("footer")?.innerText||""].join("\n");}
    finally{exempt.forEach(node=>{node.hidden=false;});}
  },[approvedTermsWords,approvedPrivacyWords,listingTextPages(),LISTING_TEXT_ATTRIBUTE]);
  const scanShownText=(path,shownText,retiredText=shownText)=>{
    if(retiredAccessWords.test(retiredText))vocabularyProblems.push({path,rule:"retired access word",found:retiredText.match(retiredAccessWords)[0]});
    if(invitationWords.test(retiredText))vocabularyProblems.push({path,rule:"invitation word",found:retiredText.match(invitationWords)[0]});
    if(!path.startsWith("/docs")&&publicVocabulary.test(shownText))vocabularyProblems.push({path,rule:"runtime word",found:shownText.match(publicVocabulary)[0]});
    if(unpublishedTerms.test(shownText))vocabularyProblems.push({path,rule:"terms called unpublished",found:shownText.match(unpublishedTerms)[0]});
  };
  /* A documentation page draws its article after the page script fetches it, so the reading waits for the article. */
  const openCustomerPage=async (target,base,path)=>{await target.goto(base+path);
    await target.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
    if(path.startsWith("/docs/"))await target.waitForSelector("#docs-article h2",{timeout:10000}).catch(()=>{});};
  for(const path of servedRoutes){await openCustomerPage(page,fixture.base,path);scanShownText(path,await readShownText(page),await readRetiredText(page));}
  /* Rendered text is not the whole surface. A message can sit in a script the browser fetches and appear only in a
     state this pass never reaches, and a class name can carry a retired word into the served stylesheet. Every file
     the browser fetches for a customer page is therefore read, not only the markup and the main script. The two typefaces
     and the page icons are binary files; they are read like the rest, so the coverage rule below needs no exception. */
  const servedFiles=["/assets/public-pages.js","/assets/public-pages.css","/assets/documentation-index.json","/assets/documentation.js","/assets/documentation.css","/assets/docs/what-baltor-is.html","/assets/docs/your-account.html","/assets/docs/searching-and-retrieving.html","/assets/docs/usage-and-what-you-pay-for.html","/assets/docs/troubleshooting.html","/assets/docs/serving-and-connections.html","/","/assets/service.js","/assets/client-access.js","/assets/pi/baltor.ts","/assets/catalogue-browser.js","/assets/architecture-story.js","/assets/supabase-client.js","/assets/service.css","/assets/architecture.css","/assets/client-recipes.json","/assets/third-party-notices.txt","/assets/geist.woff2","/assets/geist-mono.woff2","/assets/baltor-mark.svg","/assets/favicon-32.png","/assets/favicon-192.png","/assets/apple-touch-icon.png"];
  /* The list is compared with the route table the service actually serves. The footer links to the open-source notices,
     so a customer reaches that file from every page, and a served asset added in the route table alone is a named
     failure here rather than a file nobody scans. The table lives in web_pages.py since September 21, 2026; this scan
     read http.py until September 22 and found no routes at all, which failed both checks below by name. */
  const routeTable=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_pages.py"),"utf8").match(/^WEB_ASSETS = \{$([\s\S]*?)^\}$/m);
  const assetRoutes=routeTable?[...routeTable[1].matchAll(/"(\/assets\/[^"]+)":/g)].map(found=>found[1]):[];
  const unscannedFor=list=>assetRoutes.filter(path=>!list.includes(path));
  /* The deck's own files are read like every other served file. */
  servedFiles.push("/assets/deck.css","/assets/deck.js","/assets/deck-card.png");
  /* The directory page and its files. Its row files hold only listings that other publishers wrote, so the strings under their
     "rows" key are listing text; the page marks its listing fields with data-listing-text. Everything else is read. */
  const directoryRowFiles=["/assets/directory/rows-0.json","/assets/directory/rows-1.json","/assets/directory/rows-2.json","/assets/directory/rows-3.json","/assets/directory/rows-4.json","/assets/directory/rows-5.json","/assets/directory/rows-6.json","/assets/directory/rows-7.json"];
  servedFiles.push("/directory","/assets/directory.css","/assets/directory.js","/assets/directory/manifest.json",...directoryRowFiles);
  for(const path of directoryRowFiles)registerListingText(path,{fields:["rows"]});
  registerListingText("/directory",{page:true});
  check("every_served_asset_route_is_scanned_for_retired_words",assetRoutes.length>0&&unscannedFor(servedFiles).length===0,{routes:assetRoutes.length,unscanned:unscannedFor(servedFiles)});
  check("served_asset_coverage_check_rejects_a_route_left_out_of_the_scan",assetRoutes.length>0&&assetRoutes.every(path=>JSON.stringify(unscannedFor(servedFiles.filter(kept=>kept!==path)))===JSON.stringify([path])),{routes:assetRoutes.length});
  const servedTexts=[];
  for(const path of servedFiles)servedTexts.push([path,await (await page.request.get(fixture.base+path)).text()]);
  /* approved: the words the terms are compared with; a known-wrong case below passes another approved text. */
  const retiredIn=(path,text,approved=approvedTermsWords)=>{const read=withoutApprovedTerms(withoutListingText(path,text),approved);return retiredAccessWords.test(read)?[{path:"the served file "+path,rule:"retired access word",found:read.match(retiredAccessWords)[0]}]:[];};
  const servedFileProblems=servedTexts.flatMap(([path,text])=>retiredIn(path,text));
  /* The listing text rule leaves out only what a directory registered: the listing fields of a row file and the marked elements of
     the directory page. A word in a row file's envelope, in an unregistered file, in a row file that does not parse, or in an
     unmarked part of the page is still read. */
  const plantedRows=(envelope,listing)=>JSON.stringify({record_type:"mcp_directory_rows/v1"+envelope,part:0,rows:[["io.github.x/tool",listing,"x",1,listing,0,1,0,[],0,1,0,0,"","",0,1,[],0,0]]});
  check("listing_text_rule_reads_everything_but_registered_listing_fields",
    retiredIn("/assets/directory/rows-0.json",plantedRows("","Private beta tools")).length===0
    &&retiredIn("/assets/directory/rows-0.json",plantedRows(" beta","Tools")).length===1
    &&retiredIn("/assets/unregistered-rows.json",plantedRows("","Private beta tools")).length===1
    &&retiredIn("/assets/directory/rows-0.json",'{"rows":["Private beta"').length===1
    &&retiredIn("/directory",'<li data-row><span data-listing-text>Private beta tools</span></li>').length===0
    &&retiredIn("/directory",'<h2>Private beta</h2><li data-row><span data-listing-text>Tools</span></li>').length===1
    &&invitationIn("/assets/directory/rows-0.json",plantedRows("","Invite your team")).length===0
    &&invitationIn("/assets/directory/manifest.json",'{"labels":{"x":"Invite your team"}}').length===1);
  check("no_customer_page_describes_the_product_as_a_trial",vocabularyProblems.filter(item=>item.rule==="retired access word").length===0,{problems:vocabularyProblems.filter(item=>item.rule==="retired access word")});
  check("no_customer_page_uses_the_runtime_vocabulary",vocabularyProblems.filter(item=>item.rule==="runtime word").length===0,{problems:vocabularyProblems.filter(item=>item.rule==="runtime word")});
  /* The words of an invitation-only service in the served files as well: the text of the served page and of every documentation
     body, and every string the page scripts and records can write into a page, so a message that only a state this pass never
     reaches would show is read too. A script's comments and its lowercase names, such as a state called "invite", are not
     customer text. Three kinds of file hold no text of ours and are named with their reason: the identity provider's library,
     the licences of the open-source notices, and the typefaces and pictures. The approved privacy notice and terms of service are
     left out of the served page only while each holds exactly the approved words. */
  const notOurText={"/assets/supabase-client.js":"the identity provider's own library","/assets/third-party-notices.txt":"the licence texts of other projects",
    "/assets/geist.woff2":"a typeface","/assets/geist-mono.woff2":"a typeface","/assets/baltor-mark.svg":"a picture","/assets/favicon-32.png":"a picture","/assets/favicon-192.png":"a picture","/assets/apple-touch-icon.png":"a picture"};
  notOurText["/assets/deck-card.png"]="a picture";
  const withoutComments=source=>source.replace(/\/\*[\s\S]*?\*\//g," ").replace(/(^|[\s;{}()\[\],])\/\/[^\n]*/g,"$1");
  const customerStrings=source=>[...withoutComments(source).matchAll(/"((?:[^"\\\n]|\\.)*)"|'((?:[^'\\\n]|\\.)*)'|`((?:[^`\\]|\\.)*)`/g)].map(found=>found[1]??found[2]??found[3]??"")
    .filter(value=>!/^[a-z][a-z0-9]*(?:[-_.:/][a-z0-9]+)*$/.test(value));
  const privacyBlock=/<article id="privacy-notice" data-privacy-notice>[\s\S]*?<\/article>/;
  /* approved: the words each legal text is compared with; a known-wrong case below passes another approved text. */
  const withoutApprovedLegalText=(markup,approved={})=>withoutApprovedBlock(withoutApprovedTerms(markup,approved.terms||approvedTermsWords),privacyBlock,approved.privacy||approvedPrivacyWords);
  const customerText=(path,text,approved)=>path==="/"||path.endsWith(".html")||listingTextRegistration(path)?.page?markupWords(withoutApprovedLegalText(text,approved)).join(" "):customerStrings(text).join("\n");
  const invitationIn=(path,text,approved)=>{if(notOurText[path])return [];const read=customerText(path,withoutListingText(path,text),approved);return invitationWords.test(read)?[{path:"the served file "+path,rule:"invitation word",found:read.match(invitationWords)[0]}]:[];};
  /* A sentence written inside a legal text, just after the article's own opening tag, so the case depends on no word of the text. */
  const writtenInside=(block,sentence)=>block.replace(/^(<article[^>]*>)/,"$1<p>"+sentence+"</p>");
  const invitationFileProblems=servedTexts.flatMap(([path,text])=>invitationIn(path,text));
  check("no_customer_page_uses_the_words_of_an_invitation_only_service",vocabularyProblems.filter(item=>item.rule==="invitation word").length===0,{problems:vocabularyProblems.filter(item=>item.rule==="invitation word")});
  check("no_served_file_carries_the_words_of_an_invitation_only_service",servedTexts.length===servedFiles.length&&invitationFileProblems.length===0,{files:servedTexts.length,problems:invitationFileProblems});
  check("every_served_asset_route_is_read_for_invitation_words_or_named_with_its_reason",assetRoutes.length>0&&assetRoutes.every(path=>servedFiles.includes(path))&&Object.keys(notOurText).every(path=>assetRoutes.includes(path)),{excluded:notOurText});
  /* The known-wrong cases of the invitation-word rule: every phrase the owner retired, each on its own; and the words the site
     keeps, which the rule must leave alone. */
  const invitationKnownWrong=["Invitation only while we open in small groups.","Request an invitation","Invited accounts are free.","We invite people in small groups.","Join the waiting list.",
    "Search is free.","Searching is free, and each item your tools download appears here.","Being built","A key for each device from your account page is being prepared.","Planned"];
  const invitationKept=["Get started","Create your account","One plan. The whole library.","The plan can change as you learn more.","Your account covers Baltor Pro.","Get set up connects your harness."];
  check("invitation_word_check_rejects_a_known_wrong_page",invitationKnownWrong.every(claim=>invitationWords.test(claim))&&invitationKept.every(claim=>!invitationWords.test(claim)),{pages:invitationKnownWrong.length});
  /* The served-file reading is narrow in the same way. Each case is read on its own, so a page defect elsewhere cannot hide it: a
     message in a script string and a sentence in a documentation body are reported; a comment and a lowercase state name are
     not. Each approved legal text is left out while it holds exactly the approved words, and read whole once one word changes:
     the privacy notice carries retired words of its own, and the terms, amended on September 23, 2026, carry none, so a sentence
     is written inside them and read once as an unapproved change and once as if the owner had approved it. */
  const servedIndexMarkup=servedTexts.find(([path])=>path==="/")?.[1]||"",privacyMarkup=servedIndexMarkup.match(privacyBlock)?.[0]||"",termsMarkup=servedIndexMarkup.match(termsBlock)?.[0]||"";
  const termsWithFreeSearch=writtenInside(termsMarkup,"Search is free.");
  check("served_file_invitation_scan_rejects_a_planted_message_and_leaves_names_comments_and_approved_texts_alone",
    invitationIn("/assets/service.js",'message("x", "Invitation only while we open in small groups.");').length===1
    &&invitationIn("/assets/docs/what-baltor-is.html","<p>Search is free.</p>").length===1
    &&invitationIn("/assets/service.js",'/* the invitation panel */ const state = "invite"; $("funnel-invite").hidden = true; // being built').length===0
    &&privacyMarkup!==""&&invitationWords.test(markupWords(privacyMarkup).join(" "))&&invitationIn("/",privacyMarkup).length===0&&invitationIn("/",privacyMarkup.replace("five days","thirty days")).length===1
    &&termsMarkup!==""&&termsWithFreeSearch!==termsMarkup&&invitationIn("/",termsMarkup).length===0&&invitationIn("/",termsWithFreeSearch).length===1
    &&invitationIn("/",termsWithFreeSearch,{terms:markupWords(termsWithFreeSearch)}).length===0,
    {privacy_block_found:privacyMarkup!=="",terms_block_found:termsMarkup!==""});
  /* The terms of service are published, so no page and no served file may still say that they are not. The served files are
     read whole, hidden views included. */
  const unpublishedClaims=[...vocabularyProblems.filter(item=>item.rule==="terms called unpublished"),
    ...servedTexts.filter(([path,text])=>unpublishedTerms.test(withoutListingText(path,text))).map(([path,text])=>({path:"the served file "+path,found:withoutListingText(path,text).match(unpublishedTerms)[0]}))];
  check("no_public_page_says_the_terms_are_unpublished",servedTexts.length===servedFiles.length&&unpublishedClaims.length===0,{problems:unpublishedClaims});
  check("unpublished_terms_check_rejects_a_known_wrong_page",["Terms of service: not yet published","The terms of service are not published yet.","Our terms are still a draft."].every(claim=>unpublishedTerms.test(claim))
    &&!unpublishedTerms.test("Read the terms of service and the privacy notice. By creating an account you agree to the terms of service."));
  /* The exemption for the approved terms is narrow. It leaves out the one terms block of the served page only while its words
     are the approved words, so a retired word written beside the terms, or inside terms that changed, is still reported. */
  const servedMarkup=servedTexts.find(([path])=>path==="/")?.[1]||"";
  const plantedBeside=servedMarkup.replace('<p class="eyebrow">Terms</p>','<p class="eyebrow">Terms</p><p>Join the private beta.</p>');
  /* The terms carry no retired word since the owner's amendment of September 23, 2026, so the sentence written inside them is read
     once as an unapproved change, which is reported, and once as if the owner had approved it, which is left out. */
  const servedTerms=servedMarkup.match(termsBlock)?.[0]||"",termsWithBeta=writtenInside(servedTerms,"The service is a private beta.");
  const plantedInside=servedTerms?servedMarkup.replace(servedTerms,termsWithBeta):servedMarkup;
  check("retired_word_exemption_leaves_out_only_the_unchanged_approved_terms",termsBlock.test(servedMarkup)&&retiredIn("/",servedMarkup).length===0
    &&plantedBeside!==servedMarkup&&retiredIn("/",plantedBeside).length===1&&plantedInside!==servedMarkup&&retiredIn("/",plantedInside).length===1
    &&retiredIn("/",plantedInside,markupWords(termsWithBeta)).length===0,{terms_block_found:termsBlock.test(servedMarkup)});
  /* One known-wrong page for each retired phrase, including a page that never writes pilot or beta and still offers
     early access. An earlier rule read only pilot and beta and let that last page through. The last case keeps this rule to its
     own words: the invitation words have a rule of their own above. */
  const retiredKnownWrong=["Join the private pilot.","Beta users get early access.","A pilot user can search.","Our private beta is invitation only.","Request early access from your account page."];
  check("retired_word_check_rejects_a_known_wrong_page",retiredKnownWrong.every(claim=>retiredAccessWords.test(claim))&&!retiredAccessWords.test("Accounts open in small groups. Join the waiting list."),{pages:retiredKnownWrong.length});
  check("no_served_file_carries_a_retired_word",servedTexts.length===servedFiles.length&&servedFileProblems.length===0,{files:servedTexts.length,problems:servedFileProblems});
  check("served_file_scan_rejects_a_file_that_carries_a_retired_word",servedTexts.length===servedFiles.length&&["\n/* Join the private beta. */","\n/* Ask for early access. */"].every(planted=>servedTexts.every(([path,text])=>retiredIn(path,text+planted).length===1)),{files:servedTexts.length});
  /* The deck at /deck, a page with a file of its own: its source notes, its words, its keys, swipe and overview, and a phone
     and a desktop window, in tools/deck_checks.mjs. Its removed-guard controls join the others in this report. */
  await runDeckChecks({root,browser,base:fixture.base,localOnly,check,mutants,output,safeError,errors,words:{retiredAccessWords,invitationWords,publicVocabulary}});
  check("runtime_word_check_rejects_a_known_wrong_page",["Built on Loop Engine.","Every step is a Loop node.","See the role profiles.","Read the runtime classification.","A Practitioner owns the task."].every(claim=>publicVocabulary.test(claim))&&!publicVocabulary.test("Each step gets the material it needs."));
  /* The header, signed out, as the owner decided on September 23, 2026: How it works first, then Use cases, Library, Pricing,
     Docs, the guide and Sign in in the navigation, and one primary action beside it, "Get started", which opens the sign-up
     funnel. The guide is in the bar by its own name, "Get set up" at /setup; no link in the navigation is a way into the access
     journey. The known-wrong headers: a second way in, no action, no guide, an invitation link and a second primary action. */
  await page.goto(fixture.base+"/");
  const readHeaderState=target=>target.evaluate(()=>({nav:[...document.querySelectorAll("header nav a")].filter(node=>!node.hidden).map(node=>({label:node.textContent.trim(),page:node.dataset.page||"",href:node.getAttribute("href")||""})),
    primary:[...document.querySelectorAll("header .button.primary")].map(node=>({id:node.id,label:node.textContent.trim(),href:node.getAttribute("href")}))}));
  const headerState=await readHeaderState(page);
  const guideEntries=state=>state.nav.filter(item=>item.page==="setup"||item.href==="/setup").map(item=>[item.label,item.href]);
  const oneHeaderAction=state=>state.primary.length===1&&state.primary[0].label===accessLabels.closed&&state.primary[0].href===accessPaths.closed&&state.nav.length>2
    &&state.nav[0].label==="How it works"&&JSON.stringify(guideEntries(state))===JSON.stringify([["Get set up","/setup"]])
    &&!state.nav.some(item=>opensTheJourney(item.href)||/get started|join|waiting list|invitation|create (?:your )?account/i.test(item.label));
  check("header_offers_one_primary_action_and_the_guide_beside_the_navigation",oneHeaderAction(headerState),headerState);
  check("header_check_rejects_a_second_way_in_a_missing_action_a_missing_guide_and_an_invitation",!oneHeaderAction({...headerState,nav:[{label:"Get started",page:"get-started",href:"/get-started"},...headerState.nav]})&&!oneHeaderAction({...headerState,primary:[]})
    &&!oneHeaderAction({...headerState,nav:headerState.nav.filter(item=>item.page!=="setup")})&&!oneHeaderAction({...headerState,nav:[...headerState.nav,{label:"Request an invitation",page:"waitlist",href:"/waitlist"}]})
    &&!oneHeaderAction({...headerState,primary:[...headerState.primary,{id:"planted",label:"Join the waiting list",href:"/waitlist"}]}));
  /* The top bar lists the site's pages to a visitor in the order of the site map: How it works, Use cases, Library, Pricing, Docs,
     Get set up and Sign in, then the primary action, "Get started". On a phone the pages stand in the menu and the primary action
     stays in the bar. The owner, September 23, 2026: "the UI seems to have incorrectly got rid of many pages in top bar, such as
     "get started"", later the same day: "not every page needs to be in the header", and after the redesign: "some pages have
     been lost in the header". Whether the bar stays one row at 1440 and 980 pixels is a layout rule, reported by a check of its
     own so that a layout finding and a lost page never hide each other. */
  const barPages=menuLinks;
  const barState=async (target,width)=>{
    await target.setViewportSize({width,height:900});
    const button=target.locator("header .menu-button"),folded=await button.isVisible();
    if(folded)await button.click();
    const state=await target.evaluate(()=>{const shown=node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden";
      const primary=document.getElementById("header-primary");
      return {pages:[...document.querySelectorAll("header nav a")].filter(shown).map(node=>node.textContent.trim()),
        primary:primary&&shown(primary)?[primary.textContent.trim(),primary.getAttribute("href")]:[],
        barHeight:Math.round(document.querySelector("header").getBoundingClientRect().height),overflow:document.documentElement.scrollWidth>innerWidth+1};});
    if(folded)await target.keyboard.press("Escape");
    return {width,folded,...state};
  };
  const barProblems=state=>[...(JSON.stringify(state.pages.filter(name=>barPages.includes(name)))===JSON.stringify(barPages)?[]:[state.width+" pixels wide, the bar lists "+JSON.stringify(state.pages)]),
    ...(state.overflow?[state.width+" pixels wide, the page scrolls sideways"]:[]),
    ...(JSON.stringify(state.primary)===JSON.stringify([accessLabels.closed,accessPaths.closed])?[]:[state.width+" pixels wide, the primary action is "+JSON.stringify(state.primary)])];
  const barRowProblems=state=>[...(!state.folded&&state.barHeight>80?[state.width+" pixels wide, the bar takes "+state.barHeight+" pixels, more than one row"]:[]),
    ...(state.folded&&state.barHeight>80?[state.width+" pixels wide, the phone bar takes "+state.barHeight+" pixels"]:[])];
  const bars=[];for(const width of [1440,980,390])bars.push(await barState(page,width));
  await page.setViewportSize({width:1440,height:1000});
  check("top_bar_lists_the_pages_and_the_get_started_action",bars.length===3&&bars[2].folded&&bars.every(state=>barProblems(state).length===0),{bars,problems:bars.flatMap(barProblems)});
  check("top_bar_check_rejects_a_missing_page_a_new_order_a_missing_guide_and_a_missing_action",barProblems({...bars[0],pages:bars[0].pages.filter(name=>name!=="Pricing")}).length===1
    &&barProblems({...bars[0],pages:[bars[0].pages[1],bars[0].pages[0],...bars[0].pages.slice(2)]}).length===1&&barProblems({...bars[0],pages:bars[0].pages.filter(name=>name!=="Get set up")}).length===1
    &&barProblems({...bars[0],primary:[]}).length===1&&barProblems({...bars[0],pages:barPages}).length===0);
  check("top_bar_stays_one_compact_row",bars.length===3&&!bars[0].folded&&!bars[1].folded&&bars[2].folded&&bars.every(state=>barRowProblems(state).length===0),{bars:bars.map(({pages,...rest})=>rest),problems:bars.flatMap(barRowProblems)});
  check("top_bar_row_check_rejects_a_second_row",barRowProblems({...bars[1],folded:false,barHeight:130}).length===1&&barRowProblems({...bars[2],folded:true,barHeight:254}).length===1);
  /* The footer: the brand column, then four groups with stable ids, and the base row with the mark. A group shows once it holds a
     link. Product starts with Get started and the guide, Get set up, by name. Use cases links the hub and the three use cases the
     owner named on September 23, 2026. The footer no longer links /waitlist, which since that day opens the funnel as an older
     address. */
  const readFooter=target=>target.evaluate(()=>({groups:[...document.querySelectorAll("footer .footer-links")].map(group=>({id:group.id,heading:group.querySelector(".footer-heading")?.textContent.trim()||"",
      shown:group.getClientRects().length>0,links:[...group.querySelectorAll("a")].map(link=>[link.textContent.trim(),link.getAttribute("href")])})),
    mark:Boolean(document.querySelector("footer .footer-bottom img.brand-mark"))}));
  const footerState=await readFooter(page);
  const footerGroups=[["footer-product","Product"],["footer-use-cases","Use cases"],["footer-documentation","Documentation"],["footer-company","Company"]];
  const groupLinks=(state,id)=>state.groups.find(group=>group.id===id)?.links||[];
  const footerProblems=state=>[...(JSON.stringify(state.groups.map(group=>[group.id,group.heading]))===JSON.stringify(footerGroups)?[]:["the footer groups are "+JSON.stringify(state.groups.map(group=>group.id))]),
    ...state.groups.filter(group=>group.shown!==(group.links.length>0)).map(group=>group.id+(group.shown?" shows with no link":" holds links and is hidden")),
    ...(JSON.stringify(groupLinks(state,"footer-product").slice(0,2))===JSON.stringify([[accessLabels.closed,accessPaths.closed],["Get set up",getStartedPage]])?[]:["Product does not start with Get started and Get set up"]),
    ...["/how-it-works","/#library","/pricing","/examples"].filter(href=>!groupLinks(state,"footer-product").some(([,target])=>target===href)).map(href=>"Product lacks "+href),
    ...useCasePaths.filter(href=>!groupLinks(state,"footer-use-cases").some(([,target])=>target===href)).map(href=>"Use cases lacks "+href),
    ...["/docs","/security"].filter(href=>!groupLinks(state,"footer-documentation").some(([,target])=>target===href)).map(href=>"Documentation lacks "+href),
    ...["/login","/privacy","/terms","/assets/third-party-notices.txt"].filter(href=>!groupLinks(state,"footer-company").some(([,target])=>href.startsWith("/assets/")?sameOriginAsset(target,fixture.base,href):target===href)).map(href=>"Company lacks "+href),
    ...state.groups.flatMap(group=>group.links).filter(([,target])=>(target||"").split("#")[0]==="/waitlist").map(([name])=>"the footer still links /waitlist as "+JSON.stringify(name)),
    ...(state.mark?[]:["the base row carries no mark"])];
  check("footer_carries_four_groups_with_get_started_get_set_up_the_use_cases_and_the_mark",footerProblems(footerState).length===0,{footer:footerState,problems:footerProblems(footerState)});
  const withoutProduct=structuredClone(footerState);withoutProduct.groups[0].links=withoutProduct.groups[0].links.filter(([name])=>name!=="Get set up");
  const withWaitlist=structuredClone(footerState);withWaitlist.groups.find(group=>group.id==="footer-company")?.links.unshift(["Request an invitation","/waitlist"]);
  const withoutLearning=structuredClone(footerState);for(const group of withoutLearning.groups)if(group.id==="footer-use-cases")group.links=group.links.filter(([,target])=>target!=="/learning");
  check("footer_check_rejects_a_lost_link_a_missing_group_an_empty_group_on_show_and_the_waitlist",footerProblems(withoutProduct).length===1
    &&footerProblems({...footerState,groups:footerState.groups.slice(1)}).length>=1&&footerProblems({...footerState,groups:footerState.groups.map(group=>group.id==="footer-use-cases"?{...group,shown:!group.shown}:group)}).length===1
    &&footerProblems(withWaitlist).length===1&&footerProblems(withoutLearning).length===1);
  /* At phone width the links fold into a menu that works without the page script. A press on the menu button shows every link,
     Escape closes it, the keyboard reaches it through the checkbox behind the button with a visible focus mark, and choosing a
     link closes it on the page that opens. The Get started action stays in the bar the whole time. */
  await page.setViewportSize({width:390,height:1000});await page.goto(fixture.base+"/");
  const menuStates={closed:await menuState(page)};
  await page.locator("header .menu-button").click();menuStates.pressed=await menuState(page);
  await page.keyboard.press("Escape");menuStates.escaped=await menuState(page);
  await page.locator("header .brand").focus();await page.keyboard.press("Tab");await page.keyboard.press("Space");menuStates.keyed=await menuState(page);
  await page.locator('header nav a[data-page="pricing"]').click();menuStates.chosen=await menuState(page);
  check("phone_menu_opens_by_press_and_keyboard_and_closes_on_a_choice",menuWorks(menuStates),menuStates);
  /* The header stays in view while the page scrolls, on a solid ground under its rule, with the primary action in it, on a wide
     screen, on a phone and on a phone held sideways, where the bar is slimmer. The live sweep of September 23, 2026 found the bar
     scrolling away at every size. */
  const stickyState=async (target,width,height)=>{await target.setViewportSize({width,height});await target.goto(fixture.base+"/");
    await target.waitForFunction(()=>document.querySelector("#service-status")?.textContent==="Service available");
    await target.evaluate(()=>scrollTo(0,1600));await target.waitForFunction(()=>scrollY>=1500);
    return target.evaluate(()=>{const bar=document.querySelector("header"),box=bar.getBoundingClientRect(),style=getComputedStyle(bar);
      return {width:innerWidth,height:innerHeight,top:Math.round(box.top),bar:Math.round(box.height),ground:style.backgroundColor,rule:style.borderBottomWidth,
        primary:Boolean(document.getElementById("header-primary")?.getClientRects().length)};});};
  const stickyProblems=state=>[...(state.top===0?[]:[state.width+" wide, the bar sits at "+state.top+" after a scroll"]),
    ...(/rgba\([^)]*,\s*0\)|transparent/.test(state.ground)?[state.width+" wide, the bar has no solid ground"]:[]),...(parseFloat(state.rule)>0?[]:[state.width+" wide, the bar has no rule"]),
    ...(state.primary?[]:[state.width+" wide, the primary action is gone"]),...(state.height<=500&&state.bar>56?[state.width+" by "+state.height+", the bar takes "+state.bar+" pixels"]:[])];
  const stickies=[];for(const [width,height] of [[1440,900],[390,844],[844,390]])stickies.push(await stickyState(page,width,height));
  check("header_stays_in_view_while_the_page_scrolls",stickies.length===3&&stickies.every(state=>stickyProblems(state).length===0),{stickies,problems:stickies.flatMap(stickyProblems)});
  check("sticky_check_rejects_a_bar_that_scrolls_away_or_crowds_a_short_screen",stickyProblems({...stickies[0],top:-1528}).length===1&&stickyProblems({...stickies[0],ground:"rgba(0, 0, 0, 0)"}).length===1
    &&stickyProblems({...stickies[2],bar:65}).length===1);
  await page.setViewportSize({width:390,height:1000});await page.goto(fixture.base+"/");
  /* The first screen on a phone. At 390 by 844 the header is one compact bar and the hero's primary action stands wholly inside
     the window; at 320 wide nothing scrolls sideways. The live review measured a header 254 pixels tall and the action below the
     first screen. */
  const firstScreens=[];
  for(const [width,height] of [[390,844],[320,700]]){
    await page.setViewportSize({width,height});await page.goto(fixture.base+"/");
    await page.waitForFunction(()=>document.querySelector("#service-status")?.textContent==="Service available");
    firstScreens.push({height,...await firstScreen(page)});
  }
  check("phone_first_screen_holds_the_whole_primary_action_under_a_compact_header",phoneFirstScreen(firstScreens[0]),{firstScreens});
  check("narrow_phone_has_no_sideways_scroll",firstScreens.length===2&&firstScreens.every(item=>!item.overflow),{firstScreens});
  check("first_screen_check_rejects_an_action_below_the_fold_and_a_tall_header",!phoneFirstScreen({...firstScreens[0],bottom:firstScreens[0].viewport+1})&&!phoneFirstScreen({...firstScreens[0],header:254}));
  await page.setViewportSize({width:390,height:1000});await page.goto(fixture.base+"/");
  check("phone_menu_check_rejects_a_menu_that_stays_open_or_shows_nothing",!menuWorks({...menuStates,chosen:{...menuStates.chosen,open:true,links:menuLinks}})&&!menuWorks({...menuStates,pressed:{...menuStates.pressed,links:[]}})&&!menuWorks({...menuStates,keyed:{...menuStates.keyed,focusMark:"none"}}));
  await page.setViewportSize({width:1440,height:1000});await page.goto(fixture.base+"/");
  await openGuide(page);
  const orderedSteps=await page.locator("[data-get-started-step]").evaluateAll(items=>items.map(item=>({step:item.dataset.getStartedStep,index:item.querySelector(".feature-index").textContent.trim(),title:item.querySelector("[data-get-started-title]").textContent.trim()})));
  /* The Get started page leads with access, because search and downloads need an account; the connection and the first search
     follow. The first step is the panel the service's record chooses, so its title is the same in every state. */
  const namesThreeStepsInOrder=steps=>JSON.stringify(steps.map(item=>item.step))===JSON.stringify(["access","connect","search"])&&steps.every((item,index)=>item.index.startsWith("Step "+(index+1)+" / ")&&item.title.length>0);
  check("get_started_page_names_the_three_steps_in_order",new URL(page.url()).pathname===getStartedPage&&namesThreeStepsInOrder(orderedSteps)&&await page.locator('[data-view="setup"]').isVisible(),{steps:orderedSteps});
  check("get_started_step_check_rejects_a_wrong_order_or_a_missing_step",[[orderedSteps[1],orderedSteps[0],orderedSteps[2]],[orderedSteps[0],orderedSteps[1]],[orderedSteps[0],orderedSteps[2],orderedSteps[1]]].every(steps=>!namesThreeStepsInOrder(steps))&&namesThreeStepsInOrder(orderedSteps));
  await page.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0||document.querySelector("#setup-message").textContent!=="");
  check("get_started_page_carries_the_copyable_connection_settings",await page.locator('#client-tabs[role="tablist"] [role="tab"]').count()===recipeRecord.recipes.length&&await page.locator("#client-configuration").count()===1&&await page.locator("#copy-configuration").count()===1);
  /* Every harness the hero names as one "Baltor sets up" has steps of its own on the guide: a reviewed connection entry among the
     tabs. The questions on the homepage say "Get set up shows the exact steps for each", so a harness named there without an
     entry here is a promise the guide does not keep. This replaces the harness strip's rule, which the owner's removal of the
     status words retired: a harness no longer says "Planned", so the guide must set it up. */
  const guideTabs=await page.locator('#client-tabs [role="tab"]').evaluateAll(items=>items.map(item=>item.textContent.replace(/\s+/g," ").trim()));
  const setsUpEveryNamedHarness=(names,tabs)=>names.length>0&&names.every(name=>tabs.some(tab=>tab===name||tab.startsWith(name+" ")));
  check("every_harness_the_hero_names_has_steps_on_the_guide",setsUpEveryNamedHarness(heroHarnesses,guideTabs),{hero:heroHarnesses,guide:guideTabs,missing:heroHarnesses.filter(name=>!setsUpEveryNamedHarness([name],guideTabs))});
  check("named_harness_check_rejects_a_harness_the_guide_does_not_set_up",!setsUpEveryNamedHarness([...heroHarnesses,"Invented Harness"],heroHarnesses)&&setsUpEveryNamedHarness(["OpenCode"],["OpenCode 1.x"])&&!setsUpEveryNamedHarness(["Pi"],["Codex","Pipeline tool"]));
  // The guide aliases stay on setup; Get started opens the dedicated funnel, and so does /waitlist, its older address.
  const guideShownViews=()=>page.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view));
  await page.evaluate(()=>{history.pushState({},"","/connect");dispatchEvent(new PopStateEvent("popstate"));});
  const aliasViews=await guideShownViews();
  await page.evaluate(()=>{history.pushState({},"","/get-started");dispatchEvent(new PopStateEvent("popstate"));});
  const funnelViews=await guideShownViews();
  await page.evaluate(()=>{history.pushState({},"","/waitlist");dispatchEvent(new PopStateEvent("popstate"));});
  const olderFunnelViews=await guideShownViews(),olderFunnelTitle=await page.title();
  check("guide_alias_and_funnel_open_distinct_views",JSON.stringify(aliasViews)===JSON.stringify(["setup"])&&JSON.stringify(funnelViews)===JSON.stringify(["start"]),{aliasViews,funnelViews});
  /* The owner, September 23, 2026: /waitlist opens the same funnel as an older address, so earlier links and emails keep working. */
  check("waitlist_address_opens_the_get_started_funnel",JSON.stringify(olderFunnelViews)===JSON.stringify(["start"])&&olderFunnelTitle.endsWith("| Get started"),{views:olderFunnelViews,title:olderFunnelTitle});
  for(const address of ["/setup","/get-started","/connect","/waitlist"]){const served=await page.request.get(fixture.base+address);check("guide_and_funnel_addresses_are_served_"+address.slice(1),served.status()===200&&(served.headers()["content-type"]||"").startsWith("text/html"),{status:served.status()});}
  await page.goto(fixture.base+"/");
  await headerLink(page,"pricing");
  check("pricing_view_opens_from_the_navigation",new URL(page.url()).pathname==="/pricing"&&await page.locator('[data-view="pricing"]').isVisible()&&await page.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length)===1&&(await page.title()).endsWith("| Pricing"));
  /* The pricing view is read as a person reads it: the amount and "a month" stand on two lines of the plan card, and a line break
     inside the price is a space. */
  const pricingText=(await page.locator('[data-view="pricing"]').innerText()).replace(/\s+/g," ");
  /* The published facts in the pricing view's words since September 23, 2026: one plan, Baltor Pro, "$29 a month", the download
     as the measured unit, and how to stop paying. The owner removed "Search is free" and the free invited accounts that day, and
     the price is written only "$29 a month", so each of those is a refused phrase with a known-wrong page of its own. */
  const pricingFacts=[["one plan","One plan"],["plan name","Baltor Pro"],["price","$29 a month"],["measured unit","one downloaded item"],["how to stop paying","Cancel from your account page."]];
  const refusedPricingPhrases=[["free search",/\bsearch(?:ing)? is free\b/i],["free invited accounts",/\binvited\b/i],["another way of writing the price",/United States dollars|per month|\$29\s*\/\s*mo/i]];
  const missingFacts=text=>[...pricingFacts.filter(([,fact])=>!text.includes(fact)).map(([name])=>name),...refusedPricingPhrases.filter(([,rule])=>rule.test(text)).map(([name])=>name)];
  check("pricing_view_states_every_published_fact",missingFacts(pricingText).length===0,{missing:missingFacts(pricingText)});
  check("pricing_fact_check_fails_when_one_fact_is_missing_or_a_retired_offer_returns",pricingFacts.every(([name,fact])=>missingFacts(pricingText.split(fact).join("")).includes(name))
    &&missingFacts(pricingText+"\nSearch is free.").includes("free search")&&missingFacts(pricingText+"\nInvited accounts are free.").includes("free invited accounts")
    &&missingFacts(pricingText+"\n29 United States dollars each month").includes("another way of writing the price"),{facts:pricingFacts.length});
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
  check("program_name_exception_still_refuses_loop_engine_in_words",["Built on Loop Engine.","Run the Loop-Engine tool.","Every step is a Loop node."].every(claim=>internalTerms.test(withoutProgramName(claim)))&&!internalTerms.test(withoutProgramName("Run loop-engine doctor, install loop-engine[integrations] and delete ~/.loop-engine.")));
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
  const approvedWords=markdownWords(readFileSync(resolve(root,"docs/legal/PRIVACY-NOTICE.md"),"utf8"));
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
  /* The terms of service the owner approved on September 23, 2026, served like the privacy notice: at their own address on a
     direct visit, with the operator line and the date of the last change that section 9 promises, a link to the privacy
     notice, the same words as docs/legal/TERMS-OF-SERVICE.md, and a link in the shared footer. The owner had them amended the
     same evening: section 2 no longer calls the service a beta, and section 6 states the price as "$29 a month" without free
     search or invited beta users. The page is also read for a retired word and an invitation word outside the approved text.
     Removed-guard controls serve changed bytes in memory, never a source file, and each must fail its own named check. */
  const termsOperatorLine="Operator: "+privacyOperator+", "+privacyAddress+".",termsDate="Last changed: September 23, 2026";
  const termsLink='<a href="/terms" data-page="terms">Terms of service</a>';
  const termsState=async opened=>opened.evaluate(()=>{
    const terms=document.querySelector("[data-terms-of-service]"),shown=[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden);
    return {path:location.pathname,views:shown.map(item=>item.dataset.view),title:document.title,text:terms?terms.innerText:"",
      privacy:terms?[...terms.querySelectorAll('a[href="/privacy"]')].map(link=>link.dataset.page||""):[]};});
  const namesTheTermsOperator=text=>text.includes(termsOperatorLine)&&text.split(privacyAddress).length-1===1;
  const checkTerms=async (opened,note)=>{
    const state=await termsState(opened);
    note("terms_of_service_open_at_their_own_address",state.path==="/terms"&&JSON.stringify(state.views)===JSON.stringify(["terms"])&&state.title.endsWith("| Terms of service"),{path:state.path,views:state.views,title:state.title});
    note("terms_of_service_name_the_operator_and_the_date_of_the_last_change",namesTheTermsOperator(state.text)&&state.text.includes(termsDate),{operator:state.text.includes(termsOperatorLine),date:state.text.includes(termsDate)});
    const shownWords=state.text.split(/\s+/).filter(Boolean),differs=shownWords.findIndex((word,index)=>word!==approvedTermsWords[index]);
    note("terms_of_service_says_the_same_words_as_the_approved_text",sameWords(shownWords,approvedTermsWords),{shown:shownWords.length,approved:approvedTermsWords.length,first_difference:differs<0?null:{index:differs,shown:shownWords[differs],approved:approvedTermsWords[differs]}});
    note("terms_of_service_link_the_privacy_notice",JSON.stringify(state.privacy)===JSON.stringify(["privacy"]),{links:state.privacy});
    const retired=await readRetiredText(opened);
    note("terms_page_carries_no_retired_word_outside_the_approved_text",state.text!==""&&!retiredAccessWords.test(retired),{found:retiredAccessWords.test(retired)?retired.match(retiredAccessWords)[0]:null});
    note("terms_page_carries_no_invitation_word_outside_the_approved_text",state.text!==""&&!invitationWords.test(retired),{found:invitationWords.test(retired)?retired.match(invitationWords)[0]:null});
  };
  const checkTermsFooterLink=async (opened,note)=>{
    const links=await opened.locator('footer a[href="/terms"]').evaluateAll(items=>items.map(item=>({text:item.textContent.trim(),page:item.dataset.page,shown:item.offsetParent!==null})));
    const shownText=await readShownText(opened);
    note("homepage_does_not_say_the_terms_are_unpublished",!unpublishedTerms.test(shownText),{found:unpublishedTerms.test(shownText)?shownText.match(unpublishedTerms)[0]:null});
    if(links.length===1&&links[0].shown)await opened.locator('footer a[href="/terms"]').click();
    const state=await termsState(opened);
    note("the_footer_links_to_the_terms_of_service_from_the_homepage",links.length===1&&links[0].shown&&links[0].page==="terms"&&links[0].text==="Terms of service"&&state.path==="/terms"&&JSON.stringify(state.views)===JSON.stringify(["terms"])&&namesTheTermsOperator(state.text),{links,path:state.path,views:state.views});
  };
  const directTerms=await page.request.get(fixture.base+"/terms",{maxRedirects:0});
  check("terms_of_service_are_served_on_a_direct_visit",directTerms.status()===200&&(directTerms.headers()["content-type"]||"").startsWith("text/html"),{status:directTerms.status(),content_type:directTerms.headers()["content-type"]||""});
  {const {page:opened}=await openAt("/terms");await checkTerms(opened,check);
    await opened.screenshot({path:output.replace(/\.json$/,"-terms-desktop.png"),fullPage:true});
    await opened.setViewportSize({width:360,height:1000});await opened.screenshot({path:output.replace(/\.json$/,"-terms-mobile.png"),fullPage:true});await opened.close();}
  {const {page:opened}=await openAt("/");await checkTermsFooterLink(opened,check);await opened.close();}
  check("terms_checks_reject_a_page_without_the_operator_or_the_date_or_with_a_changed_word",!namesTheTermsOperator(termsOperatorLine.split(privacyOperator).join("Another operator"))
    &&!namesTheTermsOperator(termsOperatorLine+" "+privacyAddress)&&!sameWords(approvedTermsWords.map(word=>word==="three"?"twelve":word),approvedTermsWords)
    &&!sameWords(approvedTermsWords.filter(word=>word!=="Last"),approvedTermsWords)&&approvedTermsWords.join(" ").includes(termsDate)&&approvedTermsWords.join(" ").includes(termsOperatorLine));
  const termsControls=[
    {name:"remove_the_terms_link_from_the_footer",path:"/",find:termsLink,replacement:"",run:checkTermsFooterLink,expected:["the_footer_links_to_the_terms_of_service_from_the_homepage"]},
    {name:"say_again_in_the_footer_that_the_terms_are_not_published",path:"/",find:termsLink,replacement:"<span>Terms of service: not yet published</span>",run:checkTermsFooterLink,expected:["homepage_does_not_say_the_terms_are_unpublished","the_footer_links_to_the_terms_of_service_from_the_homepage"]},
    {name:"change_one_word_in_the_served_terms",path:"/terms",find:"three months",replacement:"twelve months",run:checkTerms,expected:["terms_of_service_says_the_same_words_as_the_approved_text"]},
    {name:"drop_the_date_of_the_last_change_from_the_served_terms",path:"/terms",find:'Last changed: <time datetime="2026-09-23">September 23, 2026</time>',replacement:"",run:checkTerms,expected:["terms_of_service_name_the_operator_and_the_date_of_the_last_change","terms_of_service_says_the_same_words_as_the_approved_text"]},
    {name:"drop_the_operator_from_the_served_terms",path:"/terms",find:'<strong>Operator:</strong> '+privacyOperator+", "+privacyAddress+".",replacement:"",run:checkTerms,expected:["terms_of_service_name_the_operator_and_the_date_of_the_last_change","terms_of_service_says_the_same_words_as_the_approved_text"]},
    {name:"drop_the_privacy_link_from_the_served_terms",path:"/terms",find:'The <a href="/privacy" data-page="privacy">privacy notice</a> says',replacement:"The privacy notice says",run:checkTerms,expected:["terms_of_service_link_the_privacy_notice"]},
    {name:"write_a_retired_word_beside_the_approved_terms",path:"/terms",find:'<p class="eyebrow">Terms</p>',replacement:'<p class="eyebrow">Terms</p><p>Join the private beta.</p>',run:checkTerms,expected:["terms_page_carries_no_retired_word_outside_the_approved_text"]},
    {name:"write_a_retired_word_inside_the_approved_terms",path:"/terms",find:'<ol class="terms-list">',replacement:'<ol class="terms-list"><li>Join the private beta.</li>',run:checkTerms,expected:["terms_of_service_says_the_same_words_as_the_approved_text","terms_page_carries_no_retired_word_outside_the_approved_text"]},
    /* The sentences the owner had removed from the terms on September 23, 2026, written back into the served terms. */
    {name:"write_free_search_back_into_the_served_terms",path:"/terms",find:'<ol class="terms-list">',replacement:'<ol class="terms-list"><li>Search is free. Invited beta users are not charged.</li>',run:checkTerms,expected:["terms_of_service_says_the_same_words_as_the_approved_text","terms_page_carries_no_invitation_word_outside_the_approved_text"]}];
  for(const control of termsControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,state}=await openAt(control.path,{path:control.path,find:control.find,replacement:control.replacement});applied=state.applied;await control.run(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  /* The sentence above the button that creates an account names the terms of service and the privacy notice and links each
     one. The form shows only where the service reports that account creation is open, so the sentence is read on the real
     service whose own configuration opens email sign-up, and a press on its terms link opens the terms. Where account creation
     is closed the form and its sentence stay hidden. Removed-guard controls serve changed bytes in memory. */
  const consentMarkup='<p class="signup-consent" id="signup-consent">By creating an account you agree to the <a href="/terms" data-page="terms">terms of service</a> and the <a href="/privacy" data-page="privacy">privacy notice</a>.</p>';
  const consentWords="By creating an account you agree to the terms of service and the privacy notice.";
  const createButton='<button id="email-signup-button" type="submit" class="primary">Create account and send confirmation</button>';
  const openSignup=async mutation=>{
    const opened=await context.newPage(),state={applied:false,errors:[]};
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    if(mutation)await opened.route(url=>url.origin===new URL(fixture.signup_base).origin&&url.pathname==="/signup",async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    await opened.goto(fixture.signup_base+"/signup");
    await opened.waitForFunction(()=>document.getElementById("email-signup")?.hidden===false,null,{timeout:10000}).catch(()=>{});
    return {page:opened,state};
  };
  const consentState=opened=>opened.evaluate(()=>{
    const form=document.getElementById("email-signup-form"),button=document.getElementById("email-signup-button");
    const sentence=document.getElementById("signup-consent")||[...(form?.querySelectorAll("p")||[])].find(node=>/by creating an account/i.test(node.textContent))||null;
    return {shown:Boolean(form&&form.getClientRects().length>0&&sentence&&sentence.getClientRects().length>0),text:sentence?sentence.textContent.replace(/\s+/g," ").trim():"",
      inForm:Boolean(form&&sentence&&form.contains(sentence)),above:Boolean(sentence&&button&&(sentence.compareDocumentPosition(button)&Node.DOCUMENT_POSITION_FOLLOWING)),
      links:sentence?[...sentence.querySelectorAll("a")].map(link=>[link.getAttribute("href"),link.dataset.page||"",link.textContent.trim()]):[]};});
  const consentProblems=state=>[...(state.shown?[]:["the sentence is not shown with the account form"]),...(state.text===consentWords?[]:["the sentence reads "+JSON.stringify(state.text)]),
    ...(state.inForm&&state.above?[]:["the sentence is not inside the form, above the button that creates the account"]),
    ...(JSON.stringify(state.links)===JSON.stringify([["/terms","terms","terms of service"],["/privacy","privacy","privacy notice"]])?[]:["the links are "+JSON.stringify(state.links)])];
  const checkConsent=async (opened,note)=>{const state=await consentState(opened);note("account_form_names_and_links_the_terms_and_the_privacy_notice",consentProblems(state).length===0,{problems:consentProblems(state),text:state.text});return state;};
  {const {page:opened}=await openSignup();const shown=await checkConsent(opened,check);
    if(shown.shown)await opened.locator("#email-signup").screenshot({path:output.replace(/\.json$/,"-consent-desktop.png")});
    check("consent_check_rejects_a_missing_link_a_changed_sentence_and_a_sentence_below_the_button",consentProblems(shown).length===0
      &&consentProblems({...shown,links:shown.links.slice(1)}).length===1&&consentProblems({...shown,text:"By creating an account you agree to our terms."}).length===1
      &&consentProblems({...shown,above:false}).length===1&&consentProblems({...shown,shown:false}).length===1);
    if(shown.shown)await opened.locator('#signup-consent a[href="/terms"]').click();
    const state=await termsState(opened);
    check("consent_link_opens_the_terms_of_service",state.path==="/terms"&&JSON.stringify(state.views)===JSON.stringify(["terms"])&&namesTheTermsOperator(state.text),{path:state.path,views:state.views});
    await opened.close();}
  {const {page:opened}=await openAt("/signup");const state=await consentState(opened);
    check("consent_sentence_is_not_shown_while_account_creation_is_closed",!state.shown&&state.inForm&&state.text===consentWords,{shown:state.shown,in_form:state.inForm});await opened.close();}
  const consentControls=[
    {name:"remove_the_consent_sentence_from_the_account_form",find:consentMarkup,replacement:""},
    {name:"drop_the_terms_link_from_the_consent_sentence",find:'<a href="/terms" data-page="terms">terms of service</a> and the',replacement:"terms of service and the"},
    {name:"move_the_consent_sentence_below_the_create_button",find:consentMarkup+createButton,replacement:createButton+consentMarkup}];
  for(const control of consentControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);},expected=["account_form_names_and_links_the_terms_and_the_privacy_notice"];
    let applied=false,problem="";
    try{const {page:changed,state}=await openSignup({find:control.find,replacement:control.replacement});applied=state.applied;await checkConsent(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  const homeFits=[];
  for(const width of [1440,360]){await page.setViewportSize({width,height:1000});await page.goto(fixture.base+"/");homeFits.push({width,...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1}))});}
  check("homepage_fits_a_360_pixel_screen",homeFits.length===2&&homeFits.every(item=>!item.overflow),{measurements:homeFits});
  /* The working directory and every band of the homepage fit a phone screen, at normal and at doubled text, with no sideways page
     scroll. A code block may scroll inside itself; the page may not. */
  const demoFits=[];
  for(const width of [390,320]){
    await page.setViewportSize({width,height:1000});await page.goto(fixture.base+"/");
    for(const size of ["","200%"]){
      await page.evaluate(value=>document.documentElement.style.fontSize=value,size);
      demoFits.push({width,size:size||"100%",...await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,
        wide:[...document.querySelectorAll('[data-view="home"] *, header *, footer *')].filter(node=>{const box=node.getBoundingClientRect();return box.width&&box.right>innerWidth+1&&!node.closest("pre")&&getComputedStyle(node).visibility!=="hidden";}).slice(0,6).map(node=>node.tagName+"."+String(node.className))}))});
    }
    await page.evaluate(()=>document.documentElement.style.fontSize="");
  }
  check("homepage_and_hero_directory_fit_small_screens_and_enlarged_text",demoFits.length===4&&demoFits.every(item=>!item.overflow&&item.wide.length===0),{problems:demoFits.filter(item=>item.overflow||item.wide.length)});
  await page.setViewportSize({width:1440,height:1000});
  /* The capabilities the service can report, for account creation, for a request list, for payment and for personal keys, each
     read from a real service, with the removed-guard controls for both directions and for the record version the page was
     written against. Every public action carries the one label, "Get started", and opens the funnel in every state. Since the
     owner's decision of September 23, 2026 every state also has the same words: the note beside the hero's price, the plan's
     tag and the closing note read the same whether account creation is open or not, and none of them says invitation. The
     state itself still shows in each action's data-access-state, in the pricing view's note, in the personal-key wording and
     in the one panel that leads the guide. */
  const accessWords={note:"for the whole library",tag:"One plan",closing:"Search the whole library from the harness you already use."};
  const expectedAccess={waiting:{state:"waiting",href:accessPaths.closed,label:accessLabels.closed,...accessWords},open:{state:"open",href:accessPaths.open,label:accessLabels.open,...accessWords}};
  /* The thirteen actions that carry the state: the header, the hero, the plan on the homepage, the closing band, the pricing view,
     How it works, the first example, access and data, the documentation, the footer, and the one on each use-case page, which
     carries no id and is named here by its view. */
  const accessActionIds=["[efficiency]","[learning]","[overnight]","about-access","closing-primary","docs-access","examples-access","footer-access","header-primary","hero-primary","home-pricing-primary","pricing-primary","security-access"];
  const accessActions=target=>target.evaluate(()=>({note:document.getElementById("hero-access-note")?.textContent||"",tag:document.getElementById("home-plan-access")?.textContent||"",closing:document.getElementById("closing-note")?.textContent||"",
    actions:[...document.querySelectorAll("[data-access-state]")].map(item=>({id:item.id||"["+(item.closest("[data-view]")?.dataset.view||"")+"]",state:item.dataset.accessState,href:item.getAttribute("href"),label:item.querySelector("[data-access-label]")?.textContent||""})).sort((left,right)=>left.id<right.id?-1:1)}));
  const sameAccess=(found,want)=>JSON.stringify(found.actions.map(action=>action.id))===JSON.stringify(accessActionIds)&&found.actions.every(action=>action.state===want.state&&action.href===want.href&&action.label===want.label)
    &&found.note===want.note&&found.tag===want.tag&&found.closing===want.closing;
  /* A capabilities record whose version this page was not written against may have renamed a field or given it a different meaning.
     "version" serves the real reply of a real service with its record type changed, so the careful state is checked against a known-wrong version. */
  const openPublic=async (base,mutation,version)=>{
    const opened=await context.newPage(),state={applied:false,errors:[]};
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    if(mutation)await opened.route(assetRoute("/assets/service.js",base),async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    if(version)await opened.route("**/api/v1/capabilities",async route=>{const response=await route.fetch(),body=await response.json();body.result.record_type=version;await route.fulfill({response,json:body});});
    await opened.goto(base+"/");
    await opened.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
    return {page:opened,state};
  };
  const paymentState=async opened=>{await headerLink(opened,"pricing");return {badge:await opened.locator("#pricing-state").innerText(),shown:await opened.locator("#pricing-payment-state").innerText()};};
  /* Payment wording follows two reported facts, in the words of September 23, 2026. While account creation is closed the pricing
     view asks for the account first, whatever checkout reports; with account creation and checkout both open it says to subscribe
     from the account page; with account creation open and no checkout it offers no payment. */
  const paymentWords={accountFirst:{badge:"Available now",note:"Create your account, then subscribe from your account page. Cancel any time."},
    open:{badge:"Available now",note:"Subscribe from your account page, and cancel any time."},
    closed:{badge:"Baltor Pro",note:"Subscribe from your account page once your account is ready."}};
  const samePayment=(payment,want)=>payment.badge===want.badge&&payment.shown===want.note;
  /* The personal-key wording is published in two places. Both follow the reported capability; neither is written as a fact in the page. */
  const keyWording={
    open:{offer:"A personal key for each device, from your account page",
          plan:"Create and revoke a key for every client you connect, from your account page."},
    closed:{offer:"A key for each client you connect, issued to your account",
            plan:"Every client you connect gets its own key, issued to your account."}};
  const keyState=async opened=>({offer:await opened.locator("#offer-usage-keys").evaluate(node=>node.textContent),plan:await opened.locator("#plan-keys-detail").evaluate(node=>node.textContent)});
  const sameKeys=(keys,want)=>keys.offer===want.offer&&keys.plan===want.plan;
  /* The request list shows on the account status page as a button to Get started, and the note that points to Get started shows
     only while no list is kept. Both follow the reported capability, read only from the record version this page was written
     against, so a record version it was not written for offers nothing. The waiting list page itself is no longer reachable:
     /waitlist opens the funnel. */
  const waitlistWording={pending:{offered:false},offered:{offered:true}};
  const waitlistClaims=opened=>opened.evaluate(()=>{const shown=id=>{const node=document.getElementById(id);return node?!node.hidden:null;};
    return {signup_link:shown("signup-waitlist-link"),pending_note:shown("waiting-list-pending")};});
  const sameWaitlistClaims=(claims,want)=>claims.signup_link===want.offered&&claims.pending_note===!want.offered;
  const accountFirst=(actions,payment)=>sameAccess(actions,expectedAccess.waiting)&&samePayment(payment,paymentWords.accountFirst);
  const carefulState=async (opened,note,name)=>{
    const actions=await accessActions(opened),keys=await keyState(opened),payment=await paymentState(opened),lead=await openGetStarted(opened);
    note(name,sameAccess(actions,expectedAccess.waiting)&&samePayment(payment,paymentWords.closed)&&sameKeys(keys,keyWording.closed)&&sameLead(lead,"operator"),{actions,payment,keys,lead});
  };
  /* The homepage in the reported state carries no word of an invitation-only service: the note, the tag and the closing note are
     written by the page script, so each state is read. */
  const homepageWordProblems=async opened=>{const read=await readRetiredText(opened);return invitationWords.test(read)?[read.match(invitationWords)[0]]:[];};
  /* The actions a visitor reaches first: the homepage, the pricing view and the guide, in that order. */
  const journeyActionProblems=async (opened,registrationOpen,takesAccounts=registrationOpen)=>{
    const problems=[];
    for(const name of [null,"pricing","guide"]){if(name==="guide")await openGuide(opened);else if(name)await headerLink(opened,name);problems.push(...accessActionProblems(await publicActions(opened),registrationOpen,takesAccounts));}
    return problems;
  };
  /* One press on the hero's primary action lands on the funnel's email field, in the first screen at 1440 by 900 and at 390 by
     844, wherever the funnel takes an address: a service with a request list and a service with registration open. */
  const landingScenario=name=>async (opened,note)=>{
    const landings=[];
    for(const [width,height] of [[1440,900],[390,844]]){
      await opened.setViewportSize({width,height});
      await opened.evaluate(()=>{history.pushState({},"","/");dispatchEvent(new PopStateEvent("popstate"));scrollTo(0,0);});
      landings.push(await pressThePrimaryAction(opened,width,height));
    }
    note(name,landings.length===2&&landings.every(landsOnTheField),{landings});
    note(name.replace("the_primary_action_opens","landing_check_for"),landings.length===2&&!landsOnTheField({...landings[1],path:"/signup",views:["signup"],shown:false})
      &&!landsOnTheField({...landings[1],top:landings[1].viewport+10,bottom:landings[1].viewport+58})&&!landsOnTheField({...landings[1],label:"Request an invitation"})
      &&!landsOnTheField({...landings[1],path:"/waitlist",views:["waitlist"]})&&!landsOnTheField({...landings[1],shown:false}),{landings});
  };
  const scenarios={
    closed_service:{origin:"base",run:async (opened,note)=>{
      const actions=await accessActions(opened),keys=await keyState(opened),words=await homepageWordProblems(opened);
      note("public_actions_say_get_started_while_registration_is_closed",sameAccess(actions,expectedAccess.waiting),actions);
      note("homepage_carries_no_invitation_word_while_registration_is_closed",words.length===0,{found:words});
      note("personal_key_claim_is_held_back_when_the_service_reports_no_client_access",sameKeys(keys,keyWording.closed),keys);
      const journey=await journeyActionProblems(opened,false,false);
      note("no_public_action_offers_a_second_label_or_account_creation_while_the_service_takes_no_accounts",journey.length===0,{problems:journey});
      const lead=await startLead(opened);
      note("guide_leads_with_the_operator_when_the_service_offers_neither",sameLead(lead,"operator"),lead);
      const payment=await paymentState(opened);
      note("pricing_view_asks_for_the_account_first_while_account_creation_is_closed",accountFirst(actions,payment),{actions,payment});
      const claims=await waitlistClaims(opened);
      note("account_status_page_offers_no_get_started_button_while_the_service_keeps_no_list",sameWaitlistClaims(claims,waitlistWording.pending),claims);
    }},
    waitlist_offered:{origin:"account_base",run:async (opened,note)=>{
      const words=await homepageWordProblems(opened);
      note("homepage_carries_no_invitation_word_while_the_service_keeps_a_list",words.length===0,{found:words});
      const journey=await journeyActionProblems(opened,false,true);
      note("no_public_action_offers_a_second_label_or_account_creation_outside_the_journey_while_a_list_is_kept",journey.length===0,{problems:journey});
      const lead=await startLead(opened),leadLink=await opened.locator("#start-invite-link").getAttribute("href").catch(()=>"");
      note("guide_leads_with_the_get_started_link_when_the_service_keeps_a_list",sameLead(lead,"invite")&&leadLink===accessPaths.closed,{lead,link:leadLink});
      const claims=await waitlistClaims(opened);
      note("account_status_page_offers_get_started_once_the_service_keeps_a_list",sameWaitlistClaims(claims,waitlistWording.offered),claims);
    }},
    list_landing:{origin:"account_base",run:landingScenario("the_primary_action_opens_the_funnel_email_field_in_the_first_screen_where_the_service_keeps_a_list")},
    open_landing:{origin:"signup_base",run:landingScenario("the_primary_action_opens_the_funnel_email_field_in_the_first_screen_where_registration_is_open")},
    unsupported_version_waitlist:{origin:"account_base",version:"service_capabilities/v2",run:async (opened,note)=>{
      const claims=await waitlistClaims(opened),lead=await openGetStarted(opened);
      note("unsupported_capabilities_version_keeps_the_careful_state_over_the_waiting_list",sameWaitlistClaims(claims,waitlistWording.pending)&&sameLead(lead,"operator"),{claims,lead});
    }},
    open_registration:{origin:"signup_base",run:async (opened,note)=>{
      const actions=await accessActions(opened),words=await homepageWordProblems(opened);
      note("public_actions_say_get_started_while_registration_is_open",sameAccess(actions,expectedAccess.open),actions);
      note("homepage_carries_no_invitation_word_while_registration_is_open",words.length===0,{found:words});
      const journey=await journeyActionProblems(opened,true,true);
      note("no_public_action_offers_account_creation_outside_the_get_started_and_account_pages",journey.length===0,{problems:journey});
      const lead=await startLead(opened);
      note("guide_leads_with_account_creation_when_registration_is_open",sameLead(lead,"register"),lead);
      const payment=await paymentState(opened);
      note("pricing_view_offers_no_payment_when_account_creation_is_open_without_checkout",samePayment(payment,paymentWords.closed),{actions,payment});
    }},
    open_checkout:{origin:"billing_base",run:async (opened,note)=>{
      const actions=await accessActions(opened),payment=await paymentState(opened);
      note("pricing_view_asks_for_the_account_first_when_checkout_is_open_and_account_creation_is_closed",accountFirst(actions,payment),{actions,payment});
    }},
    open_sales:{origin:"checkout_signup_base",run:async (opened,note)=>{
      const actions=await accessActions(opened),payment=await paymentState(opened);
      note("pricing_view_says_to_subscribe_when_account_creation_and_checkout_are_open",sameAccess(actions,expectedAccess.open)&&samePayment(payment,paymentWords.open),{actions,payment});
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
  const publicOrigins=["base","signup_base","billing_base","account_base","checkout_signup_base"];
  const reported=[];
  for(const name of publicOrigins){const value=(await (await page.request.get(fixture[name]+"/api/v1/capabilities")).json()).result;reported.push({name,record_type:value.record_type,registration:value.website.registration_available,checkout:value.billing.checkout,client_access:value.website.client_access_available,list:value.website.waitlist_available});}
  check("the_public_states_are_reported_by_real_services",JSON.stringify(reported)===JSON.stringify([
    {name:"base",record_type:"service_capabilities/v1",registration:false,checkout:false,client_access:false,list:false},
    {name:"signup_base",record_type:"service_capabilities/v1",registration:true,checkout:false,client_access:false,list:false},
    {name:"billing_base",record_type:"service_capabilities/v1",registration:false,checkout:true,client_access:false,list:false},
    {name:"account_base",record_type:"service_capabilities/v1",registration:false,checkout:false,client_access:true,list:true},
    {name:"checkout_signup_base",record_type:"service_capabilities/v1",registration:true,checkout:true,client_access:false,list:false}]),{reported});
  for(const name of Object.keys(scenarios)){
    const scenario=scenarios[name],{page:opened}=await openPublic(fixture[scenario.origin],null,scenario.version);
    await scenario.run(opened,check);await opened.close();
  }
  /* Every public page on three real services: one that offers neither registration nor a list, one that keeps a request list,
     and one with registration open. Each page is read for its actions and for the words of an invitation-only service. The
     known-wrong pages after it plant one wrong action, and one retired sentence, at a time into the real pages. */
  const actionScan=[],stateWords=[];
  for(const [name,registrationOpen,takesAccounts] of [["base",false,false],["account_base",false,true],["signup_base",true,true]]){
    const scanned=await context.newPage();scanned.on("pageerror",error=>errors.push(safeError(error.message)));
    for(const path of accessJourneyPaths){
      await openCustomerPage(scanned,fixture[name],path);
      actionScan.push({origin:name,path,problems:accessActionProblems(await publicActions(scanned),registrationOpen,takesAccounts)});
      const read=await readRetiredText(scanned);
      if(invitationWords.test(read))stateWords.push({origin:name,path,found:read.match(invitationWords)[0]});
    }
    await scanned.close();
  }
  check("every_public_page_offers_one_call_to_action_and_nothing_the_service_cannot_honour",actionScan.length===3*accessJourneyPaths.length&&actionScan.every(item=>item.problems.length===0),{problems:actionScan.filter(item=>item.problems.length)});
  check("no_public_page_uses_the_words_of_an_invitation_only_service_in_any_reported_state",actionScan.length===3*accessJourneyPaths.length&&stateWords.length===0,{problems:stateWords});
  const knownWrong=await context.newPage();knownWrong.on("pageerror",error=>errors.push(safeError(error.message)));
  await knownWrong.goto(fixture.base+"/");await knownWrong.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
  const plantedAction=async (text,href,place)=>{
    const planted=await knownWrong.evaluate(([text,href,place])=>{const target=document.querySelector(place);if(!target)return false;const link=document.createElement("a");link.id="known-wrong-action";link.href=href;link.textContent=text;target.append(link);return true;},[text,href,place]);
    const problems=accessActionProblems(await publicActions(knownWrong),false);
    await knownWrong.evaluate(()=>document.getElementById("known-wrong-action")?.remove());
    return planted?problems:["(the known-wrong action could not be planted)","(so this case proves nothing)"];
  };
  const secondLabel=await plantedAction("Join the waiting list",accessPaths.closed,'[data-view="home"] .hero-actions');
  const creationWhileClosed=await plantedAction("Create your account","/signup",'[data-view="home"] .closing-actions');
  const invitationOutside=await plantedAction("Ask for an invitation",accessPaths.closed,'[data-view="home"] .pricing-teaser-side');
  const olderAddress=await plantedAction("Request an invitation","/waitlist",'[data-view="home"] .closing-actions');
  /* The label as the answer to a short question is the label; a question answered with other words is a second label. */
  const questionLabel=await plantedAction("No account yet? Get started.",accessPaths.closed,'[data-view="home"] .closing-actions');
  const questionOther=await plantedAction("No account yet? Join us.",accessPaths.closed,'[data-view="home"] .closing-actions');
  check("access_action_check_rejects_a_second_label_account_creation_and_an_invitation",secondLabel.length===2&&creationWhileClosed.length===1&&invitationOutside.length===2&&olderAddress.length===2
    &&questionLabel.length===0&&questionOther.length===1,{secondLabel,creationWhileClosed,invitationOutside,olderAddress,questionLabel,questionOther});
  /* The reading of the words, planted into real pages: a note under the hero's price, a sentence written beside the approved
     privacy notice, and the notice itself with one word changed, which is then read whole. Each must be reported. */
  const plantedWords=async (path,change)=>{await openCustomerPage(knownWrong,fixture.base,path);const planted=await knownWrong.evaluate(change);const read=await readRetiredText(knownWrong);return planted&&invitationWords.test(read);};
  const clean={home:!invitationWords.test(await (async()=>{await openCustomerPage(knownWrong,fixture.base,"/");return readRetiredText(knownWrong);})()),
    privacy:!invitationWords.test(await (async()=>{await openCustomerPage(knownWrong,fixture.base,"/privacy");return readRetiredText(knownWrong);})())};
  const plantedNote=await plantedWords("/",()=>{const node=document.getElementById("hero-access-note");if(!node)return false;node.textContent="Invitation only while we open in small groups";return true;});
  const plantedBesidePrivacy=await plantedWords("/privacy",()=>{const view=document.querySelector('[data-view="privacy"]');if(!view)return false;const line=document.createElement("p");line.textContent="Search is free.";view.prepend(line);return true;});
  const changedPrivacy=await plantedWords("/privacy",()=>{const walker=document.createTreeWalker(document.querySelector("[data-privacy-notice]")||document.body,NodeFilter.SHOW_TEXT);
    for(let node=walker.nextNode();node;node=walker.nextNode())if(node.textContent.includes("five days")){node.textContent=node.textContent.replace("five days","thirty days");return true;}return false;});
  await knownWrong.close();
  check("invitation_word_reading_rejects_a_planted_note_a_sentence_beside_the_privacy_notice_and_a_changed_notice",clean.home&&clean.privacy&&plantedNote&&plantedBesidePrivacy&&changedPrivacy,{clean,plantedNote,plantedBesidePrivacy,changedPrivacy});
  const versionGate="if (value.record_type === CAPABILITIES_RECORD_TYPE) {";
  const paymentCall="applyPaymentState(publicPaymentState(value.website.registration_available === true, value.billing.checkout === true));";
  const paymentRule='const publicPaymentState = (registration, checkout) => registration !== true ? "invitation_only" : checkout === true ? "open" : "closed";';
  const waitlistGate="const open = value?.record_type === CAPABILITIES_RECORD_TYPE && value.website?.waitlist_available === true;";
  const registrationLead='website.registration_available === true ? "register"',invitationLead='website.waitlist_available === true ? "invite"';
  const publicControls=[
    {name:"always_offer_sign_up",scenario:"closed_service",find:"applyAccessState(value.website.registration_available === true);",replacement:"applyAccessState(true);",expected:["public_actions_say_get_started_while_registration_is_closed"]},
    {name:"never_offer_sign_up",scenario:"open_registration",find:"applyAccessState(value.website.registration_available === true);",replacement:"applyAccessState(false);",expected:["public_actions_say_get_started_while_registration_is_open"]},
    {name:"bring_back_the_waiting_list_label",scenario:"closed_service",find:'waiting:{label:"Get started"',replacement:'waiting:{label:"Join the waiting list"',expected:["public_actions_say_get_started_while_registration_is_closed","no_public_action_offers_a_second_label_or_account_creation_while_the_service_takes_no_accounts"]},
    /* The owner's retired words, brought back into the words the page script writes: the invitation note of the closed state and the
       free search of the open state's closing note. */
    {name:"bring_back_the_invitation_note",scenario:"closed_service",find:'waiting:{label:"Get started", href:"/get-started", note:"for the whole library"',replacement:'waiting:{label:"Get started", href:"/get-started", note:"Invitation only while we open in small groups"',expected:["public_actions_say_get_started_while_registration_is_closed","homepage_carries_no_invitation_word_while_registration_is_closed"]},
    {name:"bring_back_free_search_in_the_closing_note",scenario:"open_registration",find:'from the harness you already use."},\n    waiting:{',replacement:'from the harness you already use. Search is free."},\n    waiting:{',expected:["public_actions_say_get_started_while_registration_is_open","homepage_carries_no_invitation_word_while_registration_is_open"]},
    {name:"always_lead_with_account_creation",scenario:"closed_service",find:registrationLead,replacement:'true ? "register"',expected:["guide_leads_with_the_operator_when_the_service_offers_neither"]},
    {name:"never_lead_with_account_creation",scenario:"open_registration",find:registrationLead,replacement:'false ? "register"',expected:["guide_leads_with_account_creation_when_registration_is_open"]},
    {name:"send_the_primary_action_to_the_account_status_page",scenario:"list_landing",find:'waiting:{label:"Get started", href:"/get-started"',replacement:'waiting:{label:"Get started", href:"/signup"',expected:["the_primary_action_opens_the_funnel_email_field_in_the_first_screen_where_the_service_keeps_a_list"]},
    {name:"send_the_open_primary_action_to_the_account_status_page",scenario:"open_landing",find:'open:{label:"Get started", href:"/get-started"',replacement:'open:{label:"Get started", href:"/signup"',expected:["the_primary_action_opens_the_funnel_email_field_in_the_first_screen_where_registration_is_open"]},
    {name:"never_lead_with_the_get_started_link",scenario:"waitlist_offered",find:invitationLead,replacement:'false ? "invite"',expected:["guide_leads_with_the_get_started_link_when_the_service_keeps_a_list"]},
    {name:"always_say_payment_is_open",scenario:"closed_service",find:paymentCall,replacement:'applyPaymentState("open");',expected:["pricing_view_asks_for_the_account_first_while_account_creation_is_closed"]},
    {name:"always_say_payment_is_open_once_checkout_is_open",scenario:"open_checkout",find:paymentCall,replacement:'applyPaymentState("open");',expected:["pricing_view_asks_for_the_account_first_when_checkout_is_open_and_account_creation_is_closed"]},
    {name:"ignore_account_creation_when_checkout_is_open",scenario:"open_checkout",find:paymentRule,replacement:'const publicPaymentState = (registration, checkout) => checkout === true ? "open" : "closed";',expected:["pricing_view_asks_for_the_account_first_when_checkout_is_open_and_account_creation_is_closed"]},
    {name:"ignore_checkout_when_account_creation_is_open",scenario:"open_registration",find:paymentRule,replacement:'const publicPaymentState = (registration, checkout) => registration !== true ? "invitation_only" : "open";',expected:["pricing_view_offers_no_payment_when_account_creation_is_open_without_checkout"]},
    {name:"never_say_payment_is_open",scenario:"open_sales",find:paymentCall,replacement:"applyPaymentState(publicPaymentState(value.website.registration_available === true, false));",expected:["pricing_view_says_to_subscribe_when_account_creation_and_checkout_are_open"]},
    {name:"always_ask_for_the_account_first",scenario:"open_sales",find:paymentCall,replacement:'applyPaymentState("invitation_only");',expected:["pricing_view_says_to_subscribe_when_account_creation_and_checkout_are_open"]},
    {name:"always_claim_personal_keys",scenario:"closed_service",find:"applyClientAccessState(value.website.client_access_available === true);",replacement:"applyClientAccessState(true);",expected:["personal_key_claim_is_held_back_when_the_service_reports_no_client_access"]},
    {name:"never_claim_personal_keys",scenario:"client_access",find:"applyClientAccessState(value.website.client_access_available === true);",replacement:"applyClientAccessState(false);",expected:["personal_key_claim_appears_when_the_service_reports_client_access"]},
    {name:"ignore_the_capabilities_record_version",scenario:"unsupported_version_registration",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_registration"]},
    {name:"ignore_the_record_version_over_payment",scenario:"unsupported_version_checkout",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_checkout"]},
    {name:"ignore_the_record_version_over_personal_keys",scenario:"unsupported_version_client_access",find:versionGate,replacement:"if (true) {",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_client_access"]},
    {name:"ignore_the_record_version_over_the_waiting_list",scenario:"unsupported_version_waitlist",find:waitlistGate,replacement:"const open = value?.website?.waitlist_available === true;",expected:["unsupported_capabilities_version_keeps_the_careful_state_over_the_waiting_list"]},
    {name:"keep_the_pointer_note_once_the_service_keeps_a_list",scenario:"waitlist_offered",find:'$("waiting-list-pending").hidden = open;',replacement:'$("waiting-list-pending").hidden = false;',expected:["account_status_page_offers_get_started_once_the_service_keeps_a_list"]},
    {name:"never_offer_get_started_on_the_account_status_page",scenario:"waitlist_offered",find:'for (const name of ["signup-waitlist-link", "waitlist-form"]) $(name).hidden = !open;',replacement:'for (const name of ["signup-waitlist-link", "waitlist-form"]) $(name).hidden = true;',expected:["account_status_page_offers_get_started_once_the_service_keeps_a_list"]},
    {name:"hide_the_pointer_note_before_the_service_keeps_a_list",scenario:"closed_service",find:'$("waiting-list-pending").hidden = open;',replacement:'$("waiting-list-pending").hidden = true;',expected:["account_status_page_offers_no_get_started_button_while_the_service_keeps_no_list"]}];
  for(const control of publicControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);},scenario=scenarios[control.scenario];
    let applied=false,problem="";
    try{const {page:changed,state}=await openPublic(fixture[scenario.origin],{find:control.find,replacement:control.replacement},scenario.version);applied=state.applied;await scenario.run(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  /* Removed-guard controls for the homepage itself: one digest of the demonstration changed, the band grounds and rules taken
     away, a card with a status word again, the owner's decisions of September 23, 2026 undone one at a time, a note that grows
     after the script runs, a second primary action in the header, and the pricing heading centred beside the plan card again.
     Each serves changed bytes of one or more files in memory, never a source file, and must fail its own named check. */
  const openChanged=async (changes,address="/")=>{
    const opened=await context.newPage(),found=new Set();
    opened.on("pageerror",()=>{});
    const paths=[...new Set(changes.map(change=>change.path))];
    for(const path of paths)await opened.route(url=>url.origin===new URL(fixture.base).origin&&url.pathname===path,async route=>{
      const response=await route.fetch(),source=await response.text();let body=source;
      for(const change of changes.filter(change=>change.path===path)){if(body.includes(change.find))found.add(change);body=body.split(change.find).join(change.replacement);}
      await route.fulfill({response,body});});
    await opened.goto(fixture.base+address);
    await opened.waitForFunction(()=>document.querySelector("#service-status")?.textContent==="Service available");
    return {page:opened,applied:()=>changes.every(change=>found.has(change))};
  };
  /* The first digest the demonstration page shows, read from the manifest for the item its first step names first, so the control
     follows the demonstrated step when it changes. */
  const firstShown=releasedReferences[shownFacts.demo[0]?.items[0]?.identity]?.digest.slice(0,8)||"(none)";
  const homepageControls=[
    {name:"change_one_digest_in_the_demonstration",address:"/demo",changes:[{path:"/demo",find:'data-fact="digest">'+firstShown+"<",replacement:'data-fact="digest">'+firstShown.replace(/.$/,last=>last==="0"?"1":"0")+"<"}],
     run:async (opened,note)=>note("demo_names_sizes_and_digests_agree_with_this_release_manifest",demoFactProblems(await demoFacts(opened,"demo")).length===0),
     expected:["demo_names_sizes_and_digests_agree_with_this_release_manifest"]},
    /* The owner's decision of September 24, 2026 undone: a worked example back in the hero, beside the working directory. */
    {name:"bring_a_worked_example_back_into_the_hero",changes:[{path:"/",find:'<figure class="hero-directory"',
      replacement:'<section class="step-demo" data-step-demo><p class="step-demo-query">search: <code data-demo-query>split address lines in a customer file</code></p><ol class="step-demo-results"><li data-demo-item="split_address_lines_into_components">sha256 <span data-fact="digest">53dc74e3</span></li></ol></section><figure class="hero-directory"'}],
     run:async (opened,note)=>note("homepage_hero_shows_a_directory_not_a_worked_example",heroDirectoryProblems(await heroDirectory(opened)).length===0),
     expected:["homepage_hero_shows_a_directory_not_a_worked_example"]},
    {name:"paint_every_band_alike_without_rules",changes:[{path:"/assets/service.css",find:"--band:#FFFFFF;",replacement:"--band:#F5F6F8;"},{path:"/assets/service.css",find:"--rule:#E2E6EC;",replacement:"--rule:transparent;"}],
     run:async (opened,note)=>note("homepage_sets_every_band_apart_on_an_off_white_ground",bandProblems(await homeBands(opened)).length===0),
     expected:["homepage_sets_every_band_apart_on_an_off_white_ground"]},
    /* The owner's decisions of September 23, 2026, each undone in the served bytes: a status word back on a card, the price out of
       the hero, the old second action in place of the guide, the retired words beside the hero's actions, the demonstration below
       the copy, a use case gone, the guide gone from the signed-out header and the old waiting list address back in the footer. */
    {name:"call_a_library_kind_available",changes:[{path:"/",find:'<li class="kind" data-kind="tools"><h3>Tools and code</h3>',replacement:'<li class="kind" data-kind="tools"><h3>Tools and code</h3><p class="status-tag is-available" data-status="available">Available now</p>'}],
     run:async (opened,note)=>note("library_names_the_six_kinds_without_a_status_word",cardProblems(await homeCards(opened,"[data-kind]","kind"),kindOrder).length===0),
     expected:["library_names_the_six_kinds_without_a_status_word"]},
    {name:"take_the_price_out_of_the_hero",changes:[{path:"/",find:'<span class="hero-price-amount">$29 a month</span>',replacement:'<span class="hero-price-amount"></span>'}],
     run:async (opened,note)=>note("homepage_hero_states_the_plan_and_the_price",statesThePlanAndPrice(await opened.evaluate(()=>document.querySelector('[data-view="home"] .hero-price')?.textContent.replace(/\s+/g," ").trim()||""))),
     expected:["homepage_hero_states_the_plan_and_the_price"]},
    {name:"bring_back_see_one_step_in_place_of_the_guide",changes:[{path:"/",find:'<a class="button secondary" id="hero-setup" href="/setup" data-page="setup">Get set up</a>',replacement:'<a class="button secondary" id="hero-see-step" href="#step-demo">See one step work</a>'}],
     run:async (opened,note)=>note("homepage_hero_offers_get_started_and_get_set_up_and_says_how_they_differ",heroActionProblems(await readHeroActions(opened)).length===0),
     expected:["homepage_hero_offers_get_started_and_get_set_up_and_says_how_they_differ"]},
    {name:"write_the_retired_words_beside_the_hero_actions",changes:[{path:"/",find:'<a class="button secondary" id="hero-setup" href="/setup" data-page="setup">Get set up</a>',replacement:'<a class="button secondary" id="hero-setup" href="/setup" data-page="setup">Get set up</a> <span>Invitation only while we open in small groups. Search is free.</span>'}],
     run:async (opened,note)=>note("homepage_carries_no_invitation_word_while_registration_is_closed",(await homepageWordProblems(opened)).length===0),
     expected:["homepage_carries_no_invitation_word_while_registration_is_closed"]},
    {name:"move_the_directory_below_the_copy",changes:[{path:"/assets/architecture.css",find:"@media(min-width:1100px){.band-hero .hero.product-hero>.hero-directory{grid-column:auto;align-self:center}}",replacement:"@media(min-width:1100px){.band-hero .hero.product-hero>.hero-directory{grid-column:1/-1;align-self:center}}"}],
     run:async (opened,note)=>{await opened.setViewportSize({width:1440,height:1000});note("homepage_directory_sits_beside_the_copy_in_the_hero",directoryBesideTheCopy(await opened.locator('[data-view="home"]').evaluate(home=>{
       const hero=home.querySelector(".product-hero"),copy=hero?.querySelector(".hero-copy"),example=hero?.querySelector(".hero-directory");const box=node=>node?node.getBoundingClientRect():{left:0,right:0,top:0,bottom:0};
       return {copyTop:Math.round(box(copy).top),copyBottom:Math.round(box(copy).bottom),copyRight:Math.round(box(copy).right),exampleTop:Math.round(box(example).top),exampleBottom:Math.round(box(example).bottom),exampleLeft:Math.round(box(example).left),hasExample:Boolean(example),hasCopy:Boolean(copy),viewport:innerWidth};})));},
     expected:["homepage_directory_sits_beside_the_copy_in_the_hero"]},
    {name:"hide_the_learning_use_case",changes:[{path:"/",find:'<li class="use-case" data-use-case="learning">',replacement:'<li class="use-case" data-use-case="learning" hidden>'}],
     run:async (opened,note)=>note("homepage_links_the_three_use_cases_the_owner_named",useCaseProblems(await homeCards(opened,'[data-view="home"] [data-use-case]',"useCase")).length===0),
     expected:["homepage_links_the_three_use_cases_the_owner_named"]},
    {name:"drop_get_set_up_from_the_signed_out_header",changes:[{path:"/",find:'<a href="/setup" data-page="setup" data-nav="get-set-up-guide" data-signed-out>Get set up</a>',replacement:""}],
     run:async (opened,note)=>{note("header_offers_one_primary_action_and_the_guide_beside_the_navigation",oneHeaderAction(await readHeaderState(opened)));
       const states=[];for(const width of [1440,980,390])states.push(await barState(opened,width));note("top_bar_lists_the_pages_and_the_get_started_action",states.every(state=>barProblems(state).length===0));},
     expected:["header_offers_one_primary_action_and_the_guide_beside_the_navigation","top_bar_lists_the_pages_and_the_get_started_action"]},
    {name:"link_the_waiting_list_again_from_the_footer",changes:[{path:"/",find:'<a href="/login" data-page="login">Sign in</a><a href="/privacy" data-page="privacy">Privacy notice</a>',replacement:'<a href="/waitlist" data-page="start">Request an invitation</a><a href="/login" data-page="login">Sign in</a><a href="/privacy" data-page="privacy">Privacy notice</a>'}],
     run:async (opened,note)=>note("footer_carries_four_groups_with_get_started_get_set_up_the_use_cases_and_the_mark",footerProblems(await readFooter(opened)).length===0),
     expected:["footer_carries_four_groups_with_get_started_get_set_up_the_use_cases_and_the_mark"]},
    {name:"unfold_the_phone_menu_into_the_header",changes:[{path:"/assets/architecture.css",find:"  .header nav{display:none;position:absolute;",replacement:"  .header nav{display:flex;flex-wrap:wrap;flex-basis:100%;position:static;"}],
     run:async (opened,note)=>{await opened.setViewportSize({width:390,height:844});note("phone_first_screen_holds_the_whole_primary_action_under_a_compact_header",phoneFirstScreen(await firstScreen(opened)));},
     expected:["phone_first_screen_holds_the_whole_primary_action_under_a_compact_header"]},
    {name:"take_the_focus_mark_away",changes:[{path:"/assets/service.css",find:":focus-visible{outline:3px solid var(--accent);outline-offset:3px}",replacement:":focus-visible{outline:0}"},{path:"/assets/architecture.css",find:":focus-visible{outline:3px solid var(--accent);outline-offset:3px}",replacement:":focus-visible{outline:0}"}],
     run:async (opened,note)=>note("keyboard_focus_is_visible_in_both_appearances",unmarkedStops(await focusMarks(opened,12)).length===0),
     expected:["keyboard_focus_is_visible_in_both_appearances"]},
    {name:"let_the_header_scroll_away",changes:[{path:"/assets/architecture.css",find:".header{position:sticky;",replacement:".header{position:static;"}],
     run:async (opened,note)=>note("header_stays_in_view_while_the_page_scrolls",stickyProblems(await stickyState(opened,1440,900)).length===0),
     expected:["header_stays_in_view_while_the_page_scrolls"]},
    {name:"drop_pricing_from_the_top_bar",changes:[{path:"/",find:'<a href="/pricing" data-page="pricing" data-signed-out>Pricing</a>',replacement:""}],
     run:async (opened,note)=>{const states=[];for(const width of [1440,980,390])states.push(await barState(opened,width));note("top_bar_lists_the_pages_and_the_get_started_action",states.every(state=>barProblems(state).length===0));},
     expected:["top_bar_lists_the_pages_and_the_get_started_action"]},
    {name:"drop_get_set_up_from_the_footer",changes:[{path:"/",find:'<a href="/setup" data-page="setup" data-nav="get-set-up">Get set up</a><a href="/how-it-works" data-page="about">How it works</a>',replacement:'<a href="/how-it-works" data-page="about">How it works</a>'}],
     run:async (opened,note)=>note("footer_carries_four_groups_with_get_started_get_set_up_the_use_cases_and_the_mark",footerProblems(await readFooter(opened)).length===0),
     expected:["footer_carries_four_groups_with_get_started_get_set_up_the_use_cases_and_the_mark"]},
    {name:"leave_the_phone_menu_open_after_a_choice",changes:[{path:"/assets/service.js",find:'show(name); setMenu(false);',replacement:"show(name);"}],
     run:async (opened,note)=>{await opened.setViewportSize({width:390,height:1000});await opened.locator("header .menu-button").click();await opened.locator('header nav a[data-page="pricing"]').click();
       const state=await menuState(opened);note("phone_menu_opens_by_press_and_keyboard_and_closes_on_a_choice",state.path==="/pricing"&&!state.open&&state.links.length===0);},
     expected:["phone_menu_opens_by_press_and_keyboard_and_closes_on_a_choice"]},
    {name:"add_a_second_primary_action_to_the_header",changes:[{path:"/",find:'<span data-access-label id="header-primary-label">Get started</span></a>',replacement:'<span data-access-label id="header-primary-label">Get started</span></a><a class="button primary" href="/waitlist">Join the waiting list</a>'}],
     run:async (opened,note)=>{const actions=await primaryActions(opened);note("homepage_primary_actions_all_carry_the_one_label",primaryProblems(actions).length===0&&actions.filter(action=>action.header).length===1&&actions.length>=4);},
     expected:["homepage_primary_actions_all_carry_the_one_label"]},
    {name:"lengthen_the_hero_note_after_the_script_runs",changes:[{path:"/assets/service.js",find:'$("hero-access-note").textContent = state.note;',replacement:'$("hero-access-note").textContent = state.note + " " + state.note + " " + state.note;'}],
     run:async (opened,note)=>note("homepage_first_screen_does_not_move_when_the_script_runs",boxesMoved(servedHeroBoxes,await heroBoxes(opened)).length===0),
     expected:["homepage_first_screen_does_not_move_when_the_script_runs"]},
    {name:"centre_the_pricing_heading_beside_the_plan_card",changes:[{path:"/assets/architecture.css",find:".home-band .pricing-teaser{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,30rem);gap:4.5rem;align-items:start;",replacement:".home-band .pricing-teaser{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,30rem);gap:4.5rem;align-items:center;"}],
     run:async (opened,note)=>{await opened.setViewportSize({width:1440,height:1000});note("pricing_heading_lines_up_with_the_top_of_the_plan_card",headingMeetsTheCard(await pricingColumns(opened)));},
     expected:["pricing_heading_lines_up_with_the_top_of_the_plan_card"]}];
  for(const control of homepageControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,applied:wasApplied}=await openChanged(control.changes,control.address);await control.run(changed,note);applied=wasApplied();await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  /* The header in both sign-in states, read as a person sees it on a real service. Signed out, it offers the pages, the guide,
     Sign in and the one primary action, in the order of the site map. Signed in, it offers the account entry, which opens the
     account page, and Sign out, and neither Sign in nor Get started. At phone width the links fold into the menu, so the opened
     menu and the bar together must offer exactly what the wide header offers. Sign out, pressed in the phone menu, ends the
     sign-in, opens the sign-in page and restores the signed-out header at both widths. The review of September 23 found Sign in
     and the access action still offered to a signed-in person, and the owner found pages lost from the header the same day. Two
     removed-guard controls serve the page script without the step that hides the signed-out entries and without the step that
     brings them back. */
  const signedOutHeader=[...menuLinks,accessLabels.closed];
  const signedInHeader=["Workspace","Get set up","Library","Docs","Account","Sign out"];
  const headerEntries=async (target,width)=>{
    await target.setViewportSize({width,height:1000});
    const button=target.locator("header .menu-button"),folded=await button.isVisible();
    if(folded&&!await target.evaluate(()=>document.getElementById("menu-button")?.getAttribute("aria-expanded")==="true"))await button.click();
    const state=await target.evaluate(()=>{const shown=node=>node.getClientRects().length>0&&getComputedStyle(node).visibility!=="hidden";
      const bar=document.querySelector("header"),menu=document.querySelector("header .menu-button");
      return {entries:[...document.querySelectorAll("header a:not(.brand), header button:not([aria-controls=main-nav])")].filter(shown).map(node=>node.textContent.replace(/\s+/g," ").trim()),
        account:[...document.querySelectorAll('header a[data-page="account"]')].filter(shown).map(node=>node.getAttribute("href")),
        menuRight:menu?Math.round(menu.getBoundingClientRect().right):0,barEnd:bar?Math.round(bar.getBoundingClientRect().right-parseFloat(getComputedStyle(bar).paddingRight)):0};});
    if(folded)await target.keyboard.press("Escape");
    return {width,folded,...state};
  };
  /* At phone width the menu button stands at the end of the bar in both states, whether or not the primary action is beside it. */
  const headerProblems=(state,want)=>[...(JSON.stringify(state.entries)===JSON.stringify(want)?[]:[state.width+" pixels wide, the header offers "+JSON.stringify(state.entries)]),
    ...(want.includes("Account")&&JSON.stringify(state.account)!==JSON.stringify(["/account"])?[state.width+" pixels wide, the account entry does not open the account page"]:[]),
    ...(state.folded&&Math.abs(state.menuRight-state.barEnd)>1?[state.width+" pixels wide, the menu button ends at "+state.menuRight+" and the bar at "+state.barEnd]:[])];
  const headerChecks=["header_offers_the_pages_the_guide_sign_in_and_get_started_to_a_visitor_who_is_not_signed_in","header_offers_the_account_entry_and_sign_out_to_a_signed_in_person",
    "header_sign_out_ends_the_sign_in_and_restores_the_signed_out_header"];
  const headerScenario=async (opened,note)=>{
    const visitor=[await headerEntries(opened,1440),await headerEntries(opened,390)];
    note(headerChecks[0],visitor.every(state=>headerProblems(state,signedOutHeader).length===0),{problems:visitor.flatMap(state=>headerProblems(state,signedOutHeader))});
    await opened.setViewportSize({width:1440,height:1000});
    await headerLink(opened,"login");await opened.fill("#access-token",fixture.token);await opened.click("#connect-button");
    await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
    const member=[await headerEntries(opened,1440),await headerEntries(opened,390)];
    note(headerChecks[1],member.every(state=>headerProblems(state,signedInHeader).length===0),{problems:member.flatMap(state=>headerProblems(state,signedInHeader))});
    await signOutFromHeader(opened);
    await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Not connected");
    const left=await opened.evaluate(()=>({path:location.pathname,menuOpen:document.getElementById("menu-button")?.getAttribute("aria-expanded")==="true",searchClosed:document.getElementById("query")?.disabled===true}));
    const after=[await headerEntries(opened,390),await headerEntries(opened,1440)];
    note(headerChecks[2],left.path==="/login"&&!left.menuOpen&&left.searchClosed&&after.every(state=>headerProblems(state,signedOutHeader).length===0),{left,problems:after.flatMap(state=>headerProblems(state,signedOutHeader))});
  };
  {const noted=new Set(),{page:opened}=await openPublic(fixture.base,null);
    try{await headerScenario(opened,(name,passed,detail)=>{noted.add(name);check(name,passed,detail);});}
    catch(error){for(const name of headerChecks.filter(name=>!noted.has(name)))check(name,false,{error:safeError(error)});}
    await opened.close();}
  check("header_state_check_rejects_a_leftover_sign_in_or_get_started_a_missing_sign_out_a_missing_guide_and_a_misplaced_menu_button",
    headerProblems({width:1440,entries:signedOutHeader,account:[]},signedOutHeader).length===0&&headerProblems({width:390,entries:signedInHeader,account:["/account"]},signedInHeader).length===0
    &&headerProblems({width:1440,entries:[...signedInHeader,"Sign in"],account:["/account"]},signedInHeader).length===1
    &&headerProblems({width:1440,entries:[...signedInHeader,accessLabels.closed],account:["/account"]},signedInHeader).length===1
    &&headerProblems({width:390,entries:signedInHeader.slice(0,-1),account:["/account"]},signedInHeader).length===1
    &&headerProblems({width:1440,entries:signedInHeader,account:["/app"]},signedInHeader).length===1
    &&headerProblems({width:390,entries:signedInHeader,account:["/account"]},signedOutHeader).length===1
    &&headerProblems({width:390,folded:true,entries:signedInHeader,account:["/account"],menuRight:160,barEnd:373},signedInHeader).length===1
    &&headerProblems({width:390,folded:true,entries:signedInHeader,account:["/account"],menuRight:373,barEnd:373},signedInHeader).length===0
    &&headerProblems({width:1440,entries:signedOutHeader.filter(name=>name!=="Get set up"),account:[]},signedOutHeader).length===1);
  const headerControls=[
    {name:"keep_sign_in_and_get_started_after_sign_in",find:'document.querySelectorAll("[data-signed-out]").forEach(item => { item.hidden = signedIn; });',replacement:"",expected:[headerChecks[1]]},
    {name:"keep_the_account_entry_and_sign_out_after_sign_out",find:"showSignedIn(false);",replacement:"",expected:[headerChecks[2]]}];
  for(const control of headerControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,state}=await openPublic(fixture.base,{find:control.find,replacement:control.replacement});applied=state.applied;await headerScenario(changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  /* The careful state must be what the service serves, not only what the page script reaches. A visitor without JavaScript reads the
     served text, and the page script starts from the same careful state before the service answers and keeps it for a record
     version it was not written for: the pricing view with no payment until the account is ready, the words every access state
     shares, keys issued to the account, the operator's panel leading the guide, and the one "Get started" action. Each element
     is read by its id from the served page itself, so a changed attribute order cannot hide a changed word. */
  const servedHome=await (await page.request.get(fixture.base+"/")).text();
  const servedDefaults=markup=>page.evaluate(markup=>{const doc=new DOMParser().parseFromString(markup,"text/html"),text=id=>doc.getElementById(id)?.textContent.replace(/\s+/g," ").trim()??null,hero=doc.getElementById("hero-primary");
    return {"pricing-state":text("pricing-state"),"pricing-payment-state":text("pricing-payment-state"),"pricing-teaser-note":text("pricing-teaser-note"),"hero-access-note":text("hero-access-note"),
      "home-plan-access":text("home-plan-access"),"closing-note":text("closing-note"),"offer-usage-keys":text("offer-usage-keys"),"plan-keys-detail":text("plan-keys-detail"),
      "start-access":doc.getElementById("start-access")?.dataset.startAccess??null,"hero-primary":hero?[hero.getAttribute("href"),hero.dataset.accessState,hero.querySelector("[data-access-label]")?.textContent.trim()]:null};},markup);
  const carefulDefaults={"pricing-state":paymentWords.closed.badge,"pricing-payment-state":paymentWords.closed.note,"pricing-teaser-note":"Cancel any time from your account page.","hero-access-note":accessWords.note,
    "home-plan-access":accessWords.tag,"closing-note":accessWords.closing,"offer-usage-keys":keyWording.closed.offer,"plan-keys-detail":keyWording.closed.plan,"start-access":"operator","hero-primary":[accessPaths.closed,"waiting",accessLabels.closed]};
  const unsettled=/Checking payment|Checking whether payment is open/;
  const carefulProblems=(found,markup)=>[...Object.entries(carefulDefaults).filter(([id,want])=>JSON.stringify(found[id])!==JSON.stringify(want)).map(([id])=>id+" is served as "+JSON.stringify(found[id])+" and the careful state is "+JSON.stringify(carefulDefaults[id])),
    ...(unsettled.test(markup)?["an unsettled placeholder"]:[])];
  const servedFound=await servedDefaults(servedHome);
  check("served_page_defaults_to_the_careful_public_state",carefulProblems(servedFound,servedHome).length===0,{problems:carefulProblems(servedFound,servedHome)});
  const wrongMarkup=servedHome.replace(/(id="pricing-state"[^>]*>)[^<]*/,"$1Checking payment").replace(/(id="pricing-payment-state"[^>]*>)[^<]*/,"$1Checking whether payment is open.");
  const wrongFound=await servedDefaults(wrongMarkup);
  check("careful_default_check_rejects_a_served_page_that_never_settles",wrongMarkup!==servedHome&&carefulProblems(wrongFound,wrongMarkup).filter(problem=>/^pricing-state |^pricing-payment-state |unsettled/.test(problem)).length===3,{problems:carefulProblems(wrongFound,wrongMarkup)});
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
  /* The words of an invitation-only service are read twice as well: here from the source tree and on the deployed pages. */
  const workspaceInvitation=namedRule("tools/check_service_workspace.mjs","invitationWords"),hostedInvitation=namedRule("tools/check_hosted_website.mjs","liveInvitation");
  check("both_public_page_checks_use_one_invitation_word_rule",workspaceInvitation!==""&&workspaceInvitation===hostedInvitation&&workspaceInvitation===String(invitationWords),{workspace:workspaceInvitation,hosted:hostedInvitation});
  const droppedFreeSearch=workspaceInvitation.replace("|\\bsearch(?:ing)? is free\\b","");
  check("invitation_word_rule_comparison_rejects_a_drifted_copy",droppedFreeSearch!==workspaceInvitation&&!new RegExp(droppedFreeSearch.slice(1,-2),"i").test("Search is free.")&&invitationWords.test("Search is free."),{dropped:droppedFreeSearch});
  /* The rule that finds a statement that the terms are not published is read twice too: here and on the deployed pages. */
  const workspaceUnpublished=namedRule("tools/check_service_workspace.mjs","unpublishedTerms"),hostedUnpublished=namedRule("tools/check_hosted_website.mjs","unpublishedTerms");
  check("both_public_page_checks_use_one_unpublished_terms_rule",workspaceUnpublished!==""&&workspaceUnpublished===hostedUnpublished&&workspaceUnpublished===String(unpublishedTerms),{workspace:workspaceUnpublished,hosted:hostedUnpublished});
  const droppedDraft=workspaceUnpublished.replace("|terms(?: of service)? (?:are|is) (?:still )?(?:a draft|not (?:yet )?published)","");
  check("unpublished_terms_rule_comparison_rejects_a_drifted_copy",droppedDraft!==workspaceUnpublished&&!new RegExp(droppedDraft.slice(1,-2),"i").test("The terms are still a draft.")&&unpublishedTerms.test("The terms are still a draft."),{dropped:droppedDraft});
  await page.goto(fixture.base+"/how-it-works#task-breakdown");
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
  await page.goto(fixture.base+"/connect"); await page.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0||document.querySelector("#setup-message").textContent!=="");
  const reviewedState=await connectState(page),skipped={skipped:"the page did not show the reviewed recipe record",refusal:reviewedState.refusal||"unavailable"};
  check("reviewed_recipe_record_is_accepted_by_the_page",reviewedState.shown&&reviewedState.refusal==="",{refusal:reviewedState.refusal});
  check("guided_setup_uses_current_origin_and_no_embedded_token",(await page.locator("#client-configuration").innerText()).includes(fixture.base+"/mcp")&&!(await page.locator("#client-configuration").innerText()).includes(fixture.token));
  check("anonymous_protocol_test_is_disabled",await page.locator("#test-protocol").isDisabled());
  await page.screenshot({path:output.replace(/\.json$/,"-connect-desktop.png"),fullPage:true});
  await page.setViewportSize({width:390,height:1000});await page.screenshot({path:output.replace(/\.json$/,"-connect-mobile.png"),fullPage:true});await page.setViewportSize({width:1440,height:1000});
  if(reviewedState.shown){
    await page.locator("#client-tab-opencode").click();
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
  /* Pi and the Baltor Harness joined the three protocol clients on September 24, 2026, so every harness the hero names has steps. */
  check("connect_view_offers_the_five_reviewed_recipes",recipeRecord.recipes.length===5&&["codex","opencode","claude-code","pi","baltor-harness"].every(id=>recipeRecord.recipes.some(item=>item.id===id))&&JSON.stringify(await recipePage.locator('#client-tabs [role="tab"]').evaluateAll(items=>items.map(item=>item.dataset.recipe)))===JSON.stringify(recipeRecord.recipes.map(item=>item.id)));
  /* The recipes are tabs: the arrow keys, Home and End move the choice and the focus, only the chosen tab is in the tab order, and
     the panel is labelled by the chosen tab. A page whose key handler is taken away is the removed-guard control. */
  const tabState=target=>target.evaluate(()=>{const tabs=[...document.querySelectorAll('#client-tabs [role="tab"]')];
    return {chosen:tabs.filter(tab=>tab.getAttribute("aria-selected")==="true").map(tab=>tab.dataset.recipe),focused:document.activeElement?.dataset?.recipe||"",
      inOrder:tabs.filter(tab=>tab.tabIndex===0).map(tab=>tab.dataset.recipe),labelled:document.getElementById("client-recipe-panel")?.getAttribute("aria-labelledby")||"",
      text:document.getElementById("client-configuration")?.textContent||""};});
  const recipeIds=recipeRecord.recipes.map(item=>item.id);
  const pressRecipeKeys=async target=>{const keyed=[];if(await target.locator("#client-tab-"+recipeIds[0]).count()===0)return keyed;
    await target.locator("#client-tab-"+recipeIds[0]).click();await target.locator("#client-tab-"+recipeIds[0]).focus();
    const last=recipeIds[recipeIds.length-1];
    for(const [key,want] of [["ArrowRight",recipeIds[1]],["ArrowRight",recipeIds[2]],["End",last],["ArrowRight",recipeIds[0]],["ArrowLeft",last],["Home",recipeIds[0]]]){await target.keyboard.press(key);keyed.push({key,want,...await tabState(target)});}
    return keyed;};
  const tabsFollowKeys=items=>items.length===6&&items.every(item=>JSON.stringify(item.chosen)===JSON.stringify([item.want])&&item.focused===item.want&&JSON.stringify(item.inOrder)===JSON.stringify([item.want])&&item.labelled==="client-tab-"+item.want)&&new Set(items.map(item=>item.text)).size===new Set(items.map(item=>item.want)).size;
  const keyed=await pressRecipeKeys(recipePage);
  check("recipe_tabs_follow_the_arrow_keys_home_and_end",tabsFollowKeys(keyed),{keyed:keyed.map(({text,...rest})=>rest)});
  check("recipe_tab_check_rejects_a_tab_that_keeps_the_focus_elsewhere",!tabsFollowKeys(keyed.map((item,index)=>index===2?{...item,focused:""}:item))&&!tabsFollowKeys(keyed.slice(1))&&!tabsFollowKeys(keyed.map(item=>({...item,inOrder:recipeIds}))));
  {
    let applied=false,problem="",followed=true;
    try{const {page:changed,state}=await openConnect(recipeContext,fixture.base,{mutation:{find:'$("client-tabs").addEventListener("keydown"',replacement:'void 0 && $("client-tabs").addEventListener("keydown"'}});
      applied=state.applied;followed=tabsFollowKeys(await pressRecipeKeys(changed));await changed.close();}catch(error){problem=safeError(error);}
    const detected=applied&&!problem&&!followed;
    mutants.push({name:"ignore_the_arrow_keys_on_the_recipe_tabs",applied,detected,required_checks:["recipe_tabs_follow_the_arrow_keys_home_and_end"],missed_checks:followed?["recipe_tabs_follow_the_arrow_keys_home_and_end"]:[],failed_checks:followed?[]:["recipe_tabs_follow_the_arrow_keys_home_and_end"],...(problem?{problem}:{})});
    check("removed_guard_is_detected_ignore_the_arrow_keys_on_the_recipe_tabs",detected,{applied,...(problem?{problem}:{})});
  }
  const namedVariables=new Set();
  for(const item of recipeRecord.recipes)for(const word of (await checkShownRecipe(recipePage,fixture.base,recipeRecord,item,check)).match(/\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b/g)||[])namedVariables.add(word);
  check("every_recipe_and_the_token_instructions_name_one_variable",namedVariables.size===1&&namedVariables.has(variable)&&recipeRecord.recipes.every(item=>textLeaves(item.configuration).some(([,text])=>text.includes(variable))),{names:[...namedVariables]});
  const entryNames=(value,parent="",found=[])=>{if(value&&typeof value==="object"&&!Array.isArray(value)){if(typeof value.url==="string")found.push(parent);for(const [name,item] of Object.entries(value))entryNames(item,name,found);}return found;};
  check("every_recipe_names_the_same_server_entry",recipeRecord.recipes.every(item=>JSON.stringify(entryNames(item.configuration))===JSON.stringify(["baltor"])&&item.removal_note.includes("baltor")&&item.removal_note.includes(variable)));
  await recipePage.locator("#client-tab-claude-code").click();
  const claude=JSON.parse(await recipePage.locator("#client-configuration").innerText()).mcpServers.baltor;
  check("claude_code_recipe_is_a_project_file_with_an_environment_reference",claude.type==="http"&&claude.url===fixture.base+"/mcp"&&JSON.stringify(claude.headers)===JSON.stringify({Authorization:"Bearer ${"+variable+"}"})&&(await recipePage.locator("#configuration-location").innerText()).includes(".mcp.json")&&await recipePage.locator("#client-verify-command").innerText()==="claude mcp list");
  await recipePage.screenshot({path:output.replace(/\.json$/,"-connect-claude-code.png"),fullPage:true});
  await recipePage.locator("#client-tab-codex").click();
  const codexText=await recipePage.locator("#client-configuration").innerText();
  check("codex_recipe_is_a_table_that_names_the_variable",codexText.startsWith("[mcp_servers.baltor]\n")&&codexText.includes('bearer_token_env_var = "'+variable+'"')&&codexText.includes('url = "'+fixture.base+'/mcp"'));
  check("copying_a_recipe_stores_nothing_in_the_browser",await recipePage.evaluate(()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie==="")&&(await recipeContext.cookies()).length===0);
  const connectMarkup=await (await recipePage.request.get(fixture.base+"/connect")).text();
  check("connect_page_keeps_inline_code_forbidden",["default-src 'none'","script-src 'self'","style-src 'self'"].every(part=>recipeState.policy.includes(part))&&!recipeState.policy.includes("unsafe-inline")&&!/<style[\s>]|\sstyle\s*=|<script(?![^>]*\ssrc=)[^>]*>|\son[a-z]+\s*=/i.test(connectMarkup)&&await recipePage.evaluate(()=>window.policyViolations.length)===0,{policy:recipeState.policy});
  const fits=[];
  for(const item of recipeRecord.recipes){
    await recipePage.locator("#client-tab-"+item.id).click();await recipePage.setViewportSize({width:320,height:1000});
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
      await other.locator("#client-tab-"+item.id).click();
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
  check("sign_in_returns_to_requested_setup_page",new URL(page.url()).pathname===getStartedPage);
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
  await headerLink(page,"account");
  check("account_route_retains_same_in_memory_connection",(await page.locator("#account-facts").innerText()).includes("alpha"));
  await page.click("#refresh-usage"); await page.waitForFunction(()=>document.querySelector("#usage").textContent.includes("record_type"));
  check("usage_is_read_from_durable_service_state",JSON.parse(await page.locator("#usage").textContent()).records===1);
  /* Recorded usage as a table. The account page shows one row for each item, with its number of recorded downloads and the time
     of the latest, in the order the service gives, and keeps the raw record behind a closed disclosure for developers. The rows
     are compared with a separate read of the same service record and with what this run did: the item downloaded above is
     downloaded once more here, through the service and with a new request, so its row must say 2. A record version the page was
     not written for is shown only as the raw record. The empty state is read below, on a service where nothing was downloaded.
     The page showed the raw record as its only view until September 23. Two removed-guard controls serve that view again and
     draw a table from a record version the page was not written for. */
  const usageRecord=async (base,token)=>(await (await page.request.get(base+"/api/v1/usage",{headers:{Authorization:"Bearer "+token}})).json()).result;
  const usageShown=target=>target.evaluate(()=>{const table=document.querySelector("#usage-view table"),raw=document.getElementById("usage-raw");
    return {columns:table?[...table.querySelectorAll("thead th")].map(cell=>cell.textContent.trim()):[],
      rows:table?[...table.querySelectorAll("tbody tr")].map(row=>{const cells=[...row.children];return {item:cells[0]?.textContent.trim()||"",count:cells[1]?.textContent.trim()||"",
        when:cells[2]?.querySelector("time")?.getAttribute("datetime")||"",text:cells[2]?.textContent.trim()||""};}):[],
      note:[...document.querySelectorAll("#usage-view p")].map(node=>node.textContent.trim()).join(" "),
      raw:{shown:Boolean(raw&&!raw.hidden),open:raw?.open===true,text:document.getElementById("usage")?.textContent||""}};});
  const rawRecord=shown=>{try{return JSON.parse(shown.raw.text);}catch(_){return null;}};
  const behindDisclosure=(shown,record)=>shown.raw.shown&&!shown.raw.open&&sameValue(rawRecord(shown),record);
  const usageTableProblems=(shown,record,counts)=>{const items=Array.isArray(record?.items)?record.items:null;
    return [...(JSON.stringify(shown.columns)===JSON.stringify(["Item","Downloads","Last used"])?[]:["the table columns are "+JSON.stringify(shown.columns)]),
      ...(items?[]:["the service record lists no items"]),
      ...(items&&JSON.stringify(shown.rows.map(row=>[row.item,row.count,row.when]))!==JSON.stringify(items.map(item=>[item.item_identity,String(item.records),new Date(item.last_used_at*1000).toISOString()]))?["the rows are not the items of the service record, in its order"]:[]),
      ...Object.entries(counts).filter(([item,count])=>!shown.rows.some(row=>row.item===item&&row.count===String(count))).map(([item,count])=>item+" does not show "+count+" downloads"),
      ...shown.rows.filter(row=>!row.text||/^[\d.\s]+$/.test(row.text)).map(row=>row.item+" shows no readable time"),
      ...(behindDisclosure(shown,record)?[]:["the raw record is not kept behind a closed disclosure"])];};
  const plantedUsage={record_type:"durable_tenant_usage/v1",tenant_id:"planted",records:3,totals:{provisioned_item:3},durability:"durable",
    items:[{item_identity:"first.item",records:2,last_used_at:1758600000},{item_identity:"second.item",records:1,last_used_at:1758500000}]};
  const plantedShown={columns:["Item","Downloads","Last used"],note:"",raw:{shown:true,open:false,text:JSON.stringify(plantedUsage,null,2)},
    rows:plantedUsage.items.map(item=>({item:item.item_identity,count:String(item.records),when:new Date(item.last_used_at*1000).toISOString(),text:"Sep 23, 2025, 4:00 AM"}))};
  check("usage_table_check_rejects_raw_text_a_wrong_count_a_missing_or_moved_row_and_an_open_record",
    usageTableProblems(plantedShown,plantedUsage,{"first.item":2}).length===0
    &&usageTableProblems({...plantedShown,columns:[],rows:[]},plantedUsage,{}).length>0
    &&usageTableProblems({...plantedShown,rows:plantedShown.rows.map(row=>({...row,count:"1"}))},plantedUsage,{}).length>0
    &&usageTableProblems({...plantedShown,rows:plantedShown.rows.slice(1)},plantedUsage,{}).length>0
    &&usageTableProblems({...plantedShown,rows:[...plantedShown.rows].reverse()},plantedUsage,{}).length>0
    &&usageTableProblems({...plantedShown,rows:plantedShown.rows.map(row=>({...row,text:String(1758600000)}))},plantedUsage,{}).length>0
    &&usageTableProblems({...plantedShown,raw:{...plantedShown.raw,open:true}},plantedUsage,{}).length>0
    &&usageTableProblems(plantedShown,{...plantedUsage,items:undefined},{}).length>0);
  const searched=await page.request.post(fixture.base+"/api/v1/retrieval",{headers:{Authorization:"Bearer "+fixture.token},
    data:{record_type:"service_retrieval_request/v2",query:"Alpha",mode:"lexical",top_n:10}});
  const downloaded=(await searched.json()).result.hits[0];
  const secondRead=await page.request.post(fixture.base+"/api/v1/download",{headers:{Authorization:"Bearer "+fixture.token},
    data:{record_type:"service_provisioning_request/v1",operation:"read",identity:downloaded.reference.identity,expected_digest:downloaded.reference.body_digest,request_id:"usage-table-second-download"}});
  const refreshUsage=async (target,shown)=>{await target.click("#refresh-usage");await target.waitForFunction(text=>document.querySelector("#usage")?.textContent.includes(text),shown);};
  const usageChecks=["usage_panel_shows_each_item_with_its_count_and_last_use","usage_panel_refuses_a_record_version_it_was_not_written_for","usage_table_fits_small_screens_and_enlarged_text"];
  const usageScenarioChecks={filled:[usageChecks[0],usageChecks[2]],other_version:[usageChecks[1]]};
  const usageScenarios={
    filled:async (opened,note)=>{
      await refreshUsage(opened,'"records": 2');
      const shown=await usageShown(opened),record=await usageRecord(fixture.base,fixture.token),problems=usageTableProblems(shown,record,{[downloaded.reference.identity]:2});
      note(usageChecks[0],secondRead.status()===200&&record.records===2&&problems.length===0,{problems,records:record.records,status:secondRead.status()});
      /* The table stands in three columns on a wide card and as one block for each row on a narrow one, so neither a phone nor
         enlarged text moves the page sideways. A box counts as far as it can be seen: a box inside an ancestor that clips it,
         such as the column headings kept for screen readers in a one pixel box, or a code block that scrolls inside itself,
         reaches no further than that ancestor. */
      const fits=[];
      for(const width of [1440,390,320]){
        await opened.setViewportSize({width,height:1000});
        for(const size of ["","200%"]){
          await opened.evaluate(value=>document.documentElement.style.fontSize=value,size);
          fits.push({width,size:size||"100%",...await opened.evaluate(()=>{
            const seenRight=node=>{let right=node.getBoundingClientRect().right;for(let item=node.parentElement;item&&item!==document.documentElement;item=item.parentElement){const style=getComputedStyle(item);if(style.overflowX!=="visible"||style.clip!=="auto")right=Math.min(right,item.getBoundingClientRect().right);}return right;};
            return {overflow:document.documentElement.scrollWidth>innerWidth+1,
              wide:[...document.querySelectorAll("#account-usage *")].filter(node=>node.getBoundingClientRect().width&&seenRight(node)>innerWidth+1).map(node=>node.tagName+"."+String(node.className)).slice(0,6)};})});
        }
        await opened.evaluate(()=>document.documentElement.style.fontSize="");
      }
      await opened.setViewportSize({width:1440,height:1000});
      note(usageChecks[2],shown.rows.length>0&&fits.length===6&&fits.every(item=>!item.overflow&&item.wide.length===0),{rows:shown.rows.length,problems:fits.filter(item=>item.overflow||item.wide.length)});},
    other_version:async (opened,note)=>{
      await opened.route("**/api/v1/usage",async route=>{const response=await route.fetch(),body=await response.json();body.result.record_type="durable_tenant_usage/v2";await route.fulfill({response,json:body});});
      await refreshUsage(opened,"durable_tenant_usage/v2");
      const shown=await usageShown(opened);await opened.unroute("**/api/v1/usage");
      note(usageChecks[1],shown.columns.length===0&&shown.rows.length===0&&/not written for/i.test(shown.note)&&shown.raw.shown&&!shown.raw.open,{note:shown.note,raw:shown.raw.shown});}};
  /* A signed-in account page on the first service. A removed-guard control changes one served file, the page script unless it
     names another, in memory only. */
  const openAccount=async mutation=>{
    const opened=await context.newPage(),state={applied:false,errors:[]},path=mutation?.path||"/assets/service.js";
    opened.on("pageerror",error=>(mutation?state.errors:errors).push(safeError(error.message)));
    if(mutation)await opened.route(url=>url.origin===new URL(fixture.base).origin&&url.pathname===path,async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);state.applied=changed!==source;await route.fulfill({response,body:changed});});
    await opened.goto(fixture.base+"/");await opened.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
    await headerLink(opened,"login");await opened.fill("#access-token",fixture.token);await opened.click("#connect-button");
    await opened.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");await headerLink(opened,"account");return {page:opened,state};};
  for(const name of Object.keys(usageScenarios)){
    const noted=new Set(),{page:opened}=await openAccount(null);
    try{await usageScenarios[name](opened,(checkName,passed,detail)=>{noted.add(checkName);check(checkName,passed,detail);});}
    catch(error){for(const checkName of usageScenarioChecks[name].filter(checkName=>!noted.has(checkName)))check(checkName,false,{error:safeError(error)});}
    await opened.close();
  }
  const usageControls=[
    {name:"show_the_usage_record_as_raw_text_again",scenario:"filled",find:'renderUsage(await request("/api/v1/usage"));',
     replacement:'$("usage").textContent = JSON.stringify(await request("/api/v1/usage"), null, 2);',expected:[usageChecks[0]]},
    {name:"draw_a_table_from_a_usage_record_version_the_page_was_not_written_for",scenario:"other_version",find:"value?.record_type === USAGE_RECORD_TYPE && ",replacement:"",expected:[usageChecks[1]]},
    {name:"keep_three_usage_columns_on_a_narrow_card",scenario:"filled",path:"/assets/architecture.css",find:"@container (max-width:26em){",replacement:"@container (max-width:0em){",expected:[usageChecks[2]]}];
  for(const control of usageControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let applied=false,problem="";
    try{const {page:changed,state}=await openAccount({path:control.path,find:control.find,replacement:control.replacement});applied=state.applied;await usageScenarios[control.scenario](changed,note);await changed.close();}catch(error){problem=safeError(error);}
    const missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
  }
  await page.click("#refresh-billing"); await page.waitForFunction(()=>document.querySelector("#billing").textContent.includes("unavailable"));
  check("unconfigured_billing_is_not_a_fake_purchase_flow",await page.locator("#billing button").count()===0);
  await headerLink(page,"workspace");
  await page.route("**/api/v1/retrieval",async route=>{const response=await route.fetch(); const body=await response.json(); body.result.hits[0].purpose='<img src=x onerror="window.poisoned=true">'; await route.fulfill({response,json:body});});
  await page.click("#search-button"); await page.waitForFunction(()=>document.querySelector("#results").textContent.includes("onerror"));
  check("retrieved_metadata_is_text_not_executable_HTML",await page.locator("#results img").count()===0&&await page.evaluate(()=>window.poisoned!==true));
  await page.unroute("**/api/v1/retrieval");
  await page.route("**/api/v1/download",async route=>{const response=await route.fetch(); await route.fulfill({response,body:"CORRUPTED_LOCAL_FIXTURE"});});
  await page.locator(".result button").first().click(); await page.waitForFunction(()=>document.querySelector(".result").textContent.includes("Nothing was saved"));
  check("changed_download_is_refused_by_the_browser",(await page.locator(".result").first().innerText()).includes("do not match")); await page.unroute("**/api/v1/download");
  for(const width of [1440,820,390,320]){
    await page.setViewportSize({width,height:1000});
    /* Every public page, the three use cases the owner named on September 23, 2026 and their hub included, fits the width it is
       read at and shows one view. */
    for(const path of ["/",...useCasePaths,"/get-started","/login","/signup","/pricing","/account","/admin","/app","/docs","/how-it-works","/connect","/examples","/security","/privacy","/terms","/waitlist",...showcasePaths]){
      await page.goto(fixture.base+path);
      const measurement=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(x=>!x.hidden).length}));
      check(`responsive_${width}_${path}`,!measurement.overflow&&measurement.views===1,measurement);
    }
  }
  for(const width of [1440,320]){
    await page.setViewportSize({width,height:1000});
    for(const path of ["/",...useCasePaths,"/get-started","/how-it-works","/pricing","/connect","/examples","/security","/privacy","/terms",...showcasePaths]){
      await page.goto(fixture.base+path); await page.evaluate(()=>document.documentElement.style.fontSize="200%");
      const enlarged=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth+1,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).length,items:[...document.querySelectorAll("body *")].filter(item=>{const box=item.getBoundingClientRect();return box.width&&box.right>innerWidth+1;}).slice(0,12).map(item=>({tag:item.tagName,id:item.id,className:String(item.className)}))}));
      check(`enlarged_text_${width}_${path}`,!enlarged.overflow&&enlarged.views===1,enlarged);
      await page.evaluate(()=>document.documentElement.style.fontSize="");
    }
  }
  await page.goto(fixture.base+"/login"); await page.fill("#access-token",fixture.token); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await page.fill("#query","Alpha"); await page.click("#search-button"); await page.waitForSelector(".result");
  /* The sign-in page keeps its own Disconnect button. The header offers Sign out, not Sign in, to a signed-in person, so the page
     is reached here through the workspace's own link to it. */
  await page.locator("#workspace-access-link").click(); await page.click("#disconnect");
  check("disconnect_clears_identity_results_and_controls",await page.locator(".result").count()===0&&await page.locator("#query").isDisabled()&&await page.locator("#identity-facts").innerText()==="");
  await page.goto(fixture.billing_base+"/login"); await page.fill("#access-token",fixture.billing_token); await page.click("#connect-button"); await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await headerLink(page,"account");
  /* Nothing was downloaded on this service, so its usage record lists no item, and the panel says so in words instead of
     drawing an empty table. The raw record is still behind the closed disclosure. */
  await refreshUsage(page,"record_type");
  const emptyShown=await usageShown(page),emptyRecord=await usageRecord(fixture.billing_base,fixture.billing_token);
  const emptyProblems=[...(emptyRecord.records===0&&Array.isArray(emptyRecord.items)&&emptyRecord.items.length===0?[]:["the service record is not an empty list of items"]),
    ...(emptyShown.columns.length===0&&emptyShown.rows.length===0?[]:["a table is drawn"]),...(/no downloads/i.test(emptyShown.note)?[]:["the panel does not say that nothing is recorded"]),
    ...(behindDisclosure(emptyShown,emptyRecord)?[]:["the raw record is not kept behind a closed disclosure"])];
  check("usage_panel_says_plainly_when_nothing_is_recorded",emptyProblems.length===0,{problems:emptyProblems,note:emptyShown.note});
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
  const publicRefreshOrigin=new URL(page.url()).origin;
  const publicRefreshRoute=url=>url.origin===publicRefreshOrigin&&((url.pathname==="/api/v1/capabilities"&&!url.search)||sameOriginAsset(url.href,publicRefreshOrigin,"/assets/client-recipes.json",false));
  await page.route(publicRefreshRoute,async route=>{heldPublic++;await publicGate;await route.continue().catch(()=>{});});
  await page.goto(fixture.base+"/login");await page.waitForFunction(()=>document.querySelector("#connect-button")!==null);
  await page.fill("#access-token",fixture.token);await page.click("#connect-button");await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  releasePublic();await page.waitForFunction(()=>document.querySelector("#service-status").textContent.includes("Service available")||document.querySelector("#service-status").textContent.includes("Service unavailable"));
  await page.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0||document.querySelector("#setup-message").textContent!=="");
  check("sign_in_during_public_configuration_loading_preserves_setup",heldPublic===2&&await page.locator('#client-tabs [role="tab"]').count()>0&&!await page.locator("#test-protocol").isDisabled(),{heldPublic});
  await page.unroute(publicRefreshRoute);
  let releasePrivate,heldPrivate=false;const privateGate=new Promise(resolve=>{releasePrivate=resolve;});
  await page.route("**/mcp",async route=>{if(route.request().postDataJSON()?.method==="tools/list"){heldPrivate=true;await privateGate;}await route.continue().catch(()=>{});});
  await page.locator('[data-view="workspace"] .dashboard-nav a[data-page="setup"]').click();await page.click("#test-protocol");
  await new Promise((resolve,reject)=>{const deadline=setTimeout(()=>{clearInterval(poll);reject(new Error("No held authenticated request"));},5000);const poll=setInterval(()=>{if(heldPrivate){clearInterval(poll);clearTimeout(deadline);resolve();}},10);});
  /* The wait is handled at once, so a step that fails before it is awaited is reported by name instead of ending the run
     unreported; awaiting it below still fails when no request was cancelled. */
  const aborted=page.waitForEvent("requestfailed",{predicate:request=>new URL(request.url()).pathname==="/mcp"});aborted.catch(()=>{});
  await signOutFromHeader(page);await aborted;releasePrivate();
  check("sign_out_still_aborts_credential_bound_protocol_requests",await page.locator("#protocol-tools li").count()===0&&await page.locator("#test-protocol").isDisabled()&&(await page.locator("#protocol-result").innerText()).startsWith("Not tested"));
  await page.unroute("**/mcp");
  await page.route(fixture.identity_origin+"/auth/v1/token**",route=>route.fulfill({status:200,contentType:"application/json",headers:{"Access-Control-Allow-Origin":fixture.account_base,"Access-Control-Allow-Headers":"*","Access-Control-Allow-Methods":"POST, OPTIONS"},body:JSON.stringify({access_token:fixture.identity_token,refresh_token:"local-fixture-refresh",expires_in:1800,token_type:"bearer",user:fixture.identity_user})}));
  await page.route(fixture.identity_origin+"/auth/v1/logout**",route=>route.fulfill({status:204,headers:{"Access-Control-Allow-Origin":fixture.account_base,"Access-Control-Allow-Headers":"*"}}));
  await page.goto(fixture.account_base+"/login");await page.waitForSelector("#email-login:not([hidden])");
  await page.fill("#login-email",fixture.identity_user.email);await page.fill("#login-password","local-browser-fixture-password");await page.click("#email-login-button");
  await page.waitForFunction(()=>document.querySelector("#connection-state").textContent==="Connected");
  await headerLink(page,"account");await page.click("#refresh-client-access");
  await page.waitForSelector("#client-access-controls:not([hidden])");
  check("verified_customer_can_open_personal_token_controls",await page.locator("#create-client-token").isEnabled()&&await page.locator("#client-token-scopes input").count()===3);
  await page.fill("#client-token-label","My laptop");await page.fill("#client-token-minutes","60");await page.click("#create-client-token");
  await page.waitForSelector("#client-issued:not([hidden])");
  const personalToken=await page.inputValue("#client-issued-token");secrets.push(personalToken);
  const personalSession=await page.request.get(fixture.account_base+"/api/v1/session",{headers:{Authorization:"Bearer "+personalToken}});
  check("customer_dashboard_creates_real_personal_access",personalSession.status()===200&&(await personalSession.json()).result.principal.tenant_id.startsWith("browser-customers."));
  /* Since September 24, 2026 the tab keeps the email sign-in, under one key that holds the identity provider's access token and its
     expiry. The client token the account page just created is in no storage at all. */
  check("customer_token_secret_stays_out_of_text_and_browser_storage",!(await page.locator("body").innerText()).includes(personalToken)&&await page.evaluate(token=>localStorage.length===0
    &&Object.keys(sessionStorage).every(key=>key==="baltor.identity-session")&&!Object.values(sessionStorage).some(value=>value.includes(token))&&document.cookie==="",personalToken));
  check("customer_token_cannot_manage_more_credentials",(await page.request.get(fixture.account_base+"/api/v1/account/access",{headers:{Authorization:"Bearer "+personalToken}})).status()===403);
  await page.click("#clear-client-token");check("customer_can_clear_the_one_time_secret",await page.inputValue("#client-issued-token")==="");
  page.once("dialog",dialog=>dialog.accept());await page.getByRole("button",{name:"Revoke My laptop",exact:true}).click();
  await page.waitForFunction(()=>document.querySelector("#client-access-list").textContent.includes("revoked"));
  check("customer_dashboard_revokes_real_client_access",(await page.request.get(fixture.account_base+"/api/v1/session",{headers:{Authorization:"Bearer "+personalToken}})).status()===401);
  /* The account page follows the dashboard design: a side navigation whose every link opens a page or a section this service has,
     with Overview marked as the current page. The design's settings page is left out, because this service has none yet. */
  const dashboardNav=await page.evaluate(()=>[...(document.querySelector('[data-view="account"]')?.querySelectorAll(".dashboard-nav a")||[])].map(link=>{const href=link.getAttribute("href")||"",part=href.split("#")[1]||"";
    return {label:link.textContent.trim(),href,current:link.getAttribute("aria-current")==="page",target:part?Boolean(document.getElementById(part)):href.startsWith("/")};}));
  const navProblems=items=>[...(JSON.stringify(items.map(item=>item.label))===JSON.stringify(["Overview","Connect","Keys","Library","Usage","Billing"])?[]:["the sections are "+JSON.stringify(items.map(item=>item.label))]),
    ...items.filter(item=>!item.target).map(item=>item.label+" points at a section the page does not have"),...(items.filter(item=>item.current).map(item=>item.label).join()==="Overview"?[]:["Overview is not marked as the current page"])];
  check("account_page_carries_the_dashboard_navigation",navProblems(dashboardNav).length===0,{problems:navProblems(dashboardNav)});
  check("dashboard_navigation_check_rejects_a_link_to_a_missing_section",dashboardNav.length===6&&navProblems([...dashboardNav.slice(0,5),{...dashboardNav[5],target:false}]).length===1&&navProblems(dashboardNav.map(item=>({...item,current:false}))).length===1);
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
  await signOutFromHeader(page);releaseCustomer();
  check("customer_sign_out_clears_tokens_before_delayed_reply",await page.locator("#client-access-controls").isHidden()&&await page.inputValue("#client-issued-token")===""&&await page.locator("#refresh-client-access").isDisabled());
  await page.unroute("**/api/v1/account/access");
  /* Email-first sign-up, the page a message link opens, and the Get started funnel. Every service here is real. The identity project
     behind the sign-up service is the stand-in from account_email_checks.py, served over a loopback socket: it keeps the first password of
     an address that is not confirmed, as the probe of September 23, 2026 observed, and its public sign-up plays the provider's own route,
     which the owner is closing. Every rule below has a removed-guard control that serves changed page bytes in memory, for that control
     run only, and must fail the rule's own named check. */
  const standIn=fixture.confirm_identity_origin;
  /* The plan step's words for a signed-in account without paid access while checkout is closed, and for one that checkout covers. */
  const unpaidPlanText="$29 a month. Subscribe from your account page.",checkoutPlanText="$29 a month. Cancel any time from your account page.";
  const outbox=async (target,address)=>(await (await target.request.get(standIn+"/stand-in/outbox?to="+encodeURIComponent(address))).json());
  const newestLink=async (target,address)=>{const box=await outbox(target,address);return (box.messages.at(-1)?.text||"").split(/\s+/).find(word=>word.includes("/auth/confirm?"))||"";};
  const standInSignIn=async (target,address,password)=>(await target.request.post(standIn+"/auth/v1/token?grant_type=password",{data:{email:address,password}})).status();
  let journeyCount=0;
  const journeyAddress=name=>"journey-"+name+"-"+(++journeyCount)+"-"+randomBytes(3).toString("hex")+"@example.invalid";
  /* A fresh context for one scenario. A control passes its mutation, and every context the scenario opens serves that one file changed in
     memory; the tracker records whether the change applied. */
  const openJourney=async (mutation,viewport={width:1440,height:900},tracker={applied:false})=>{
    const opened=await browser.newContext({viewport,reducedMotion:"reduce"});await opened.route("**/*",localOnly);
    if(mutation)await opened.route(url=>url.pathname===mutation.path&&url.origin!==standIn,async route=>{
      const response=await route.fetch(),source=await response.text(),changed=source.split(mutation.find).join(mutation.replacement);
      if(changed!==source)tracker.applied=true;await route.fulfill({response,body:changed});});
    const target=await opened.newPage();target.on("pageerror",error=>{if(!mutation)errors.push(safeError(error.message));});
    return {context:opened,page:target};
  };
  const shownViews=target=>target.evaluate(()=>[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view));
  /* The whole journey for an address that someone else registered first, through the provider's own public sign-up. */
  const signUpJourney=async (target,note)=>{
    const address=journeyAddress("owner"),chosenFirst="first-registrant-"+randomBytes(6).toString("hex"),owner="owner-chosen-"+randomBytes(8).toString("hex");
    const preRegistered=(await target.request.post(standIn+"/auth/v1/signup",{data:{email:address,password:chosenFirst}})).status();
    const sent=[];target.on("request",request=>{const url=new URL(request.url());if(request.method()!=="GET"||url.origin===standIn)sent.push({method:request.method(),path:url.pathname,origin:url.origin,body:request.postData()||""});});
    await target.goto(fixture.confirm_base+"/get-started");
    await target.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:10000}).catch(()=>{});
    await target.fill("#funnel-email",address);await target.click("#funnel-signup-button");
    await target.waitForFunction(()=>/^Check your email/.test(document.getElementById("funnel-signup-message")?.textContent||""),null,{timeout:10000}).catch(()=>{});
    const signups=sent.filter(item=>item.path==="/api/v1/account/signup"),providerSignups=sent.filter(item=>item.origin===standIn&&item.path==="/auth/v1/signup");
    let body={};try{body=JSON.parse(signups[0]?.body||"{}");}catch(_){}
    note("sign_up_sends_the_address_alone_to_this_service_and_never_calls_the_provider_sign_up",preRegistered===200&&signups.length===1
      &&JSON.stringify(body)===JSON.stringify({record_type:"service_account_signup_request/v2",email:address})&&providerSignups.length===0
      &&await target.evaluate(()=>document.querySelector('[data-funnel-step="confirm"]')?.getAttribute("aria-current"))==="step",{sent:sent.map(item=>item.method+" "+item.path)});
    const link=await newestLink(target,address),token=link?new URL(link).searchParams.get("token_hash")||"":"";
    if(!link)return {address,owner,link:"",signedIn:false};
    await target.goto(link);
    await target.waitForFunction(()=>document.querySelector('[data-view="confirm"]')?.hidden===false,null,{timeout:10000}).catch(()=>{});
    const opened=await target.evaluate(token=>({path:location.pathname,search:location.search,inAddress:location.href.includes(token),inText:document.body.innerText.includes(token),
      form:Boolean(document.getElementById("confirm-form")?.getClientRects().length),connected:document.getElementById("connection-state")?.textContent||"",stored:localStorage.length+sessionStorage.length}),token);
    const views=await shownViews(target);
    note("the_confirmation_page_clears_the_token_from_the_address_and_asks_for_a_password_first",Boolean(token)&&opened.path==="/auth/confirm"&&opened.search===""
      &&!opened.inAddress&&!opened.inText&&JSON.stringify(views)===JSON.stringify(["confirm"])&&opened.form&&opened.connected==="Not connected"&&opened.stored===0,{opened,views});
    await target.fill("#confirm-password",owner);await target.fill("#confirm-password-again",owner);await target.click("#confirm-button");
    await target.waitForFunction(()=>document.getElementById("connection-state")?.textContent==="Connected"||document.getElementById("confirm-message")?.classList.contains("error"),null,{timeout:15000}).catch(()=>{});
    await target.waitForFunction(()=>location.pathname!=="/auth/confirm",null,{timeout:5000}).catch(()=>{});
    const order=sent.map(item=>item.method+" "+item.path),verified=order.indexOf("POST /auth/v1/verify"),chosen=order.indexOf("PUT /auth/v1/user"),activated=order.indexOf("POST /api/v1/account/activate");
    const after={path:new URL(target.url()).pathname,views:await shownViews(target),connected:await target.locator("#connection-state").textContent(),
      funnel:await target.evaluate(()=>({state:document.getElementById("funnel")?.dataset.funnelState,title:document.getElementById("funnel-plan-title")?.textContent,text:document.getElementById("funnel-plan-text")?.textContent,subscribe:!document.getElementById("funnel-subscribe")?.hidden}))};
    note("the_new_password_is_set_before_the_account_opens",verified>=0&&chosen>verified&&activated>chosen&&after.connected==="Connected"&&after.path==="/get-started"
      &&JSON.stringify(after.views)===JSON.stringify(["start"]),{order,after});
    note("a_password_chosen_first_by_someone_else_no_longer_opens_the_account",await standInSignIn(target,address,chosenFirst)===400&&await standInSignIn(target,address,owner)===200);
    /* While checkout is closed the plan step names the plan and its price and offers no control that starts a payment. Since
       September 23, 2026 it no longer says that payment is not open; the absent control is what the rule holds. */
    note("get_started_funnel_offers_no_payment_while_checkout_is_closed",after.funnel.state==="plan"&&after.funnel.title==="Subscribe to Baltor Pro"&&after.funnel.text===unpaidPlanText&&after.funnel.subscribe===false,after.funnel);
    return {address,owner,link,signedIn:after.connected==="Connected"};
  };
  /* A used link says so plainly, changes nothing and offers a way to ask for another. */
  const usedLink=async (target,note,journey)=>{
    await target.goto(journey.link);
    await target.waitForFunction(()=>document.querySelector('[data-view="confirm"]')?.hidden===false,null,{timeout:10000}).catch(()=>{});
    const password="another-try-"+randomBytes(6).toString("hex");
    await target.fill("#confirm-password",password);await target.fill("#confirm-password-again",password);await target.click("#confirm-button");
    await target.waitForFunction(()=>document.getElementById("confirm-unusable")?.hidden===false||document.getElementById("confirm-message")?.classList.contains("error"),null,{timeout:10000}).catch(()=>{});
    const shown=await target.evaluate(()=>({unusable:document.getElementById("confirm-unusable")?.hidden===false,form:document.getElementById("confirm-password-step")?.hidden===false,
      heading:document.querySelector("#confirm-unusable h1")?.textContent||"",newLink:document.getElementById("confirm-new-link")?.getAttribute("href"),connected:document.getElementById("connection-state")?.textContent}));
    note("a_used_link_says_so_plainly_and_offers_a_new_one",shown.unusable&&!shown.form&&shown.heading==="This link cannot be used."&&shown.newLink==="/signup"&&shown.connected==="Not connected"
      &&await standInSignIn(target,journey.address,password)===400&&await standInSignIn(target,journey.address,journey.owner)===200,shown);
  };
  /* Recovery asks this service for a link to the same page and ends at a password the owner chooses. */
  const recoveryJourney=async (target,note,journey)=>{
    await target.goto(fixture.confirm_base+"/login");
    await target.waitForSelector("#email-recovery:not([hidden])",{timeout:10000}).catch(()=>{});
    await target.fill("#recovery-email",journey.address);await target.click("#recovery-button");
    await target.waitForFunction(()=>/^Check your email/.test(document.getElementById("recovery-message")?.textContent||""),null,{timeout:10000}).catch(()=>{});
    const link=await newestLink(target,journey.address),kind=link?new URL(link).searchParams.get("type"):"";
    if(link){await target.goto(link);await target.waitForFunction(()=>document.querySelector('[data-view="confirm"]')?.hidden===false,null,{timeout:10000}).catch(()=>{});}
    const page3=await target.evaluate(()=>({path:location.pathname,search:location.search,heading:document.getElementById("confirm-heading")?.textContent||"",form:document.getElementById("confirm-password-step")?.hidden===false,step:document.getElementById("confirm-step")?.hidden}));
    const renewed="renewed-owner-"+randomBytes(8).toString("hex");
    if(page3.form){await target.fill("#confirm-password",renewed);await target.fill("#confirm-password-again",renewed);await target.click("#confirm-button");
      await target.waitForFunction(()=>document.getElementById("connection-state")?.textContent==="Connected"||document.getElementById("confirm-message")?.classList.contains("error"),null,{timeout:15000}).catch(()=>{});
      await target.waitForFunction(()=>location.pathname!=="/auth/confirm",null,{timeout:5000}).catch(()=>{});}
    note("recovery_reaches_the_same_choose_a_password_page",kind==="recovery"&&page3.path==="/auth/confirm"&&page3.search===""&&page3.heading==="Choose a new password."&&page3.form&&page3.step===true
      &&new URL(target.url()).pathname==="/account"&&await standInSignIn(target,journey.address,renewed)===200&&await standInSignIn(target,journey.address,journey.owner)===400,{kind,page3});
    journey.owner=renewed;
  };
  /* The funnel as a visitor and as a signed-in account sees it. */
  const funnelFacts=target=>target.evaluate(()=>{
    const view=document.querySelector('[data-view="start"]'),shown=node=>Boolean(node&&node.getClientRects().length>0);
    const box=node=>{if(!shown(node))return null;const rect=node.getBoundingClientRect();return {top:Math.round(rect.top),bottom:Math.round(rect.bottom)};};
    const consent=document.getElementById("funnel-consent");
    return {path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),state:document.getElementById("funnel")?.dataset.funnelState||"",
      primaries:[...(view?.querySelectorAll(".primary")||[])].filter(shown).map(node=>({id:node.id,text:node.textContent.trim(),href:node.getAttribute("href")})),
      steps:[...document.querySelectorAll("[data-funnel-step] strong")].map(node=>node.textContent.trim()),setup:document.getElementById("funnel-setup-link")?.getAttribute("href"),
      price:document.querySelector(".funnel-price")?.textContent||"",form:shown(document.getElementById("funnel-signup-form")),
      consent:shown(consent)?{text:consent.textContent.replace(/\s+/g," ").trim(),links:[...consent.querySelectorAll("a")].map(link=>link.getAttribute("href"))}:null,
      title:document.getElementById("funnel-plan-title")?.textContent||"",subscribe:shown(document.getElementById("funnel-subscribe")),
      heading:box(document.getElementById("funnel-title")),priceBox:box(document.querySelector(".funnel-price")),lastStep:box(document.querySelector('[data-funnel-step="setup"]')),
      field:box(document.getElementById("funnel-email")),action:box(document.getElementById("funnel-signup-button"))||box(document.getElementById("funnel-invite")),
      viewport:innerHeight,overflow:document.documentElement.scrollWidth>innerWidth+1,words:view?.innerText||""};
  });
  const openSteps=["Create your account","Confirm your email","Choose a password","Subscribe to Baltor Pro","Get set up"];
  /* The funnel in each state a service can report. Where the service takes new accounts, by registration or by its request list,
     the card shows the one account form, #funnel-email with its one action and the sentence that links the terms and the privacy
     notice, and the first step reads "Create your account", in the same words in both states. Where it takes neither, the card
     offers Sign in. The price line says "$29 a month" and, since the owner's decision of September 23, 2026, no longer says that
     search is free; no step and no action says invitation. */
  const funnelProblems=(facts,open,waitingList=false)=>{const creating=open||waitingList;return [...(facts.path==="/get-started"&&JSON.stringify(facts.views)===JSON.stringify(["start"])?[]:["the page is not the funnel alone"]),
    ...(facts.state===(creating?"register":"invite")?[]:["the card is "+JSON.stringify(facts.state)]),
    ...(facts.primaries.length===1?[]:[facts.primaries.length+" primary actions"]),
    ...(creating?(facts.primaries[0]?.id==="funnel-signup-button"&&facts.form&&facts.consent?.text===consentWords&&JSON.stringify(facts.consent?.links)===JSON.stringify(["/terms","/privacy"])?[]:["the account form, its one action or its consent sentence is missing"])
      :(facts.primaries[0]?.id==="funnel-invite"&&facts.primaries[0]?.text==="Sign in"&&facts.primaries[0]?.href==="/login"&&!facts.form&&!facts.consent?[]:["the sign-in action is missing or account creation is offered"])),
    ...(JSON.stringify(facts.steps)===JSON.stringify([creating?openSteps[0]:"Sign in",...openSteps.slice(1)])&&facts.setup==="/setup"?[]:["the five steps read "+JSON.stringify(facts.steps)]),
    ...(facts.price.includes("$29 a month")&&!invitationWords.test(facts.price)?[]:["the price line reads "+JSON.stringify(facts.price)]),
    ...(invitationWords.test(facts.words||"")?["the funnel says "+JSON.stringify(facts.words.match(invitationWords)[0])]:[])];};
  /* The first screen: at 1440 by 900 the heading, the price, all five steps and the first step's action; at 390 by 844 the heading and the
     first step's field and action. The steps may follow on a phone. */
  const firstScreenProblems=(facts,wide,open)=>[...(facts.overflow?["the page scrolls sideways"]:[]),
    ...[["heading",facts.heading],["price",wide?facts.priceBox:facts.heading],["last step",wide?facts.lastStep:facts.heading],["field",open?facts.field:facts.action],["action",facts.action]]
      .filter(([,box])=>!box||box.bottom>facts.viewport).map(([name,box])=>name+(box?" ends at "+box.bottom:" is not shown"))];
  const funnelScreenshot=async (base,open,wide,screenshot)=>{
    const {context:opened,page:target}=await openJourney(null,wide?{width:1440,height:900}:{width:390,height:844});
    await target.goto(base+"/get-started");
    await target.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
    await target.waitForFunction(want=>document.getElementById("funnel")?.dataset.funnelState===want,open?"register":"invite",{timeout:5000}).catch(()=>{});
    await target.screenshot({path:output.replace(/\.json$/,screenshot)});
    await opened.close();
  };
  const funnelScenario=(base,open,waitingList=false)=>async (target,note)=>{
    const creating=open||waitingList,state=open?"open":waitingList?"list":"closed";
    await target.goto(base+"/get-started");
    await target.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
    await target.waitForFunction(want=>document.getElementById("funnel")?.dataset.funnelState===want,creating?"register":"invite",{timeout:5000}).catch(()=>{});
    const facts=await funnelFacts(target);
    note(open?"get_started_funnel_offers_account_creation_while_registration_is_open":waitingList?"get_started_funnel_takes_the_address_where_the_service_keeps_a_request_list":"get_started_funnel_offers_sign_in_when_registration_and_the_request_list_are_closed",funnelProblems(facts,open,waitingList).length===0,{problems:funnelProblems(facts,open,waitingList)});
    for(const [wide,size] of [[true,{width:1440,height:900}],[false,{width:390,height:844}]]){
      await target.setViewportSize(size);const sized=await funnelFacts(target);
      note("get_started_funnel_first_step_fits_the_first_screen_"+state+"_"+size.width,firstScreenProblems(sized,wide,creating).length===0,{problems:firstScreenProblems(sized,wide,creating)});
    }
  };
  /* The funnel's form on a service that keeps a request list: the address goes to the list, the visitor is told that a link to
     finish creating the account follows by email, the funnel moves on to the second step, and the service's own record holds the
     address. A second request from the same address is told that it is already registered, and the form stays. */
  const listRequest=async (target,note)=>{
    const address=journeyAddress("list"),sent=[];
    target.on("request",request=>{const url=new URL(request.url());if(request.method()==="POST")sent.push({path:url.pathname,body:request.postData()||""});});
    await target.goto(fixture.account_base+"/get-started");
    await target.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:10000}).catch(()=>{});
    const ask=async ()=>{await target.fill("#funnel-email",address);await target.click("#funnel-signup-button");
      await target.waitForFunction(()=>{const node=document.getElementById("funnel-signup-message");return Boolean(node&&node.textContent&&node.textContent!=="Sending…");},null,{timeout:10000}).catch(()=>{});
      return target.evaluate(()=>({message:document.getElementById("funnel-signup-message")?.textContent||"",error:document.getElementById("funnel-signup-message")?.classList.contains("error")===true,
        form:Boolean(document.getElementById("funnel-signup-form")?.getClientRects().length),current:document.querySelector("[data-funnel-step][aria-current=step]")?.dataset.funnelStep||""}));};
    const first=await ask(),requests=sent.filter(item=>item.path==="/api/v1/waitlist");
    let body={};try{body=JSON.parse(requests[0]?.body||"{}");}catch(_){}
    const listed=await target.request.get(fixture.account_base+"/api/v1/admin/waitlist",{headers:{Authorization:"Bearer "+fixture.account_admin_token}});
    const entries=listed.status()===200?(await listed.json()).result.entries.filter(entry=>entry.email===address):[];
    note("get_started_funnel_puts_the_address_on_the_request_list_and_says_a_link_follows",requests.length===1&&JSON.stringify(body)===JSON.stringify({record_type:"service_waitlist_request/v1",email:address,note:""})
      &&!first.error&&first.message==="Thank you. We will email you a link to finish creating your account."&&!first.message.includes(address)&&first.current==="confirm"
      &&entries.length===1&&entries[0].state==="waiting"&&!invitationWords.test(first.message),{first,requests:requests.length,entries:entries.length,status:listed.status()});
    const second=await ask();
    note("get_started_funnel_tells_a_second_request_from_the_same_address_that_it_is_registered",second.error&&second.message.startsWith("This address is already registered.")&&second.form&&!invitationWords.test(second.message),second);
  };
  /* Staff administration through the website. A superadmin named in the service's accounts policy signs in like anyone,
     sees the Administration link, every account with its plan, and grants free monthly Baltor Pro to one of them. */
  /* Staff sign in like anyone: the identity provider's token address answers with the staff member's session. */
  const staffSignIn=async target=>{
    await target.route(fixture.identity_origin+"/auth/v1/token**",route=>route.fulfill({status:200,contentType:"application/json",headers:{"Access-Control-Allow-Origin":fixture.staff_base,"Access-Control-Allow-Headers":"*","Access-Control-Allow-Methods":"POST, OPTIONS"},body:JSON.stringify({access_token:fixture.staff_token,refresh_token:"local-fixture-refresh",expires_in:1800,token_type:"bearer",user:fixture.staff_user})}));
    await target.route(fixture.identity_origin+"/auth/v1/logout**",route=>route.fulfill({status:204,headers:{"Access-Control-Allow-Origin":fixture.staff_base,"Access-Control-Allow-Headers":"*"}}));
    await target.goto(fixture.staff_base+"/login");await target.waitForSelector("#email-login:not([hidden])",{timeout:10000});
    await target.fill("#login-email",fixture.staff_user.email);await target.fill("#login-password","local-browser-fixture-password");await target.click("#email-login-button");
    await target.waitForFunction(()=>document.querySelector("#connection-state")?.textContent==="Connected",null,{timeout:10000}).catch(()=>{});
    await target.evaluate(()=>{history.pushState({},"","/admin");dispatchEvent(new PopStateEvent("popstate"));});
    await target.waitForFunction(()=>document.querySelectorAll("#staff-accounts article").length>=2,null,{timeout:10000}).catch(()=>{});
  };
  /* Staff administration through the website. A superadmin named in the service's accounts policy signs in like anyone,
     sees the Administration link, every account with its plan, and grants free monthly Baltor Pro to one of them. */
  const staffJourney=async (target,note)=>{
    await staffSignIn(target);
    const read=()=>target.evaluate(()=>({link:!document.getElementById("admin-nav")?.hidden,section:document.getElementById("staff-admin")?.hidden===false,
      role:document.getElementById("staff-role")?.textContent||"",rows:[...document.querySelectorAll("#staff-accounts article")].map(item=>({title:item.querySelector("h3")?.textContent||"",plan:item.querySelector(".badge")?.textContent||"",
      text:item.innerText}))}));
    const before=await read(),customer=before.rows.find(row=>row.title==="customer-test@example.invalid");
    /* The scenario runs again for its removed-guard control, so it grants when the account has no free plan and revokes when it has one. */
    const granting=customer?.plan!=="Free monthly",label=(granting?"Grant":"Revoke")+" free monthly for customer-test@example.invalid";
    target.once("dialog",dialog=>dialog.accept());
    await target.getByRole("button",{name:label,exact:true}).click({timeout:5000}).catch(()=>{});
    await target.waitForFunction(()=>/is done\.$/.test(document.getElementById("staff-message")?.textContent||""),null,{timeout:10000}).catch(()=>{});
    const after=await read(),changed=after.rows.find(row=>row.title==="customer-test@example.invalid");
    note("a_superadmin_sees_every_account_and_grants_free_monthly_in_the_administration_view",before.link&&before.section&&before.role==="superadmin"
      &&["staff-test@example.invalid","customer-test@example.invalid"].every(title=>before.rows.some(row=>row.title===title))
      &&/Confirmed/.test(customer?.text||"")&&changed?.plan===(granting?"Free monthly":"None"),{before,after,granting});
  };
  /* The owner's request of September 24, 2026: a superadmin types an address and the person is sent Baltor's own sign-up link.
     The account shows as waiting until the person chooses a password. The words stay those of a staff tool. */
  const staffLinkJourney=async (target,note)=>{
    await staffSignIn(target);
    const address=journeyAddress("link");
    const form=await target.evaluate(()=>document.getElementById("staff-links-form")?.hidden===false);
    if(form){await target.fill("#staff-link-addresses",address);await target.check("#staff-link-free");await target.click("#staff-link-button");
      await target.waitForFunction(()=>/^Link sent to /.test(document.getElementById("staff-message")?.textContent||"")||document.getElementById("staff-message")?.classList.contains("error"),null,{timeout:10000}).catch(()=>{});}
    /* A picture of the staff view for review, from the real run only; the removed-guard runs change the page. */
    if(note===check)await target.locator("#staff-admin").screenshot({path:output.replace(/\.json$/,"-staff-links.png")}).catch(()=>{});
    const shown=await target.evaluate(address=>({message:document.getElementById("staff-message")?.textContent||"",
      row:[...document.querySelectorAll("#staff-accounts article")].map(item=>item.innerText).find(text=>text.includes(address))||"",
      formWords:document.getElementById("staff-links-form")?.innerText||""}),address);
    note("a_superadmin_sends_a_sign_up_link_and_the_account_shows_as_waiting",form&&shown.message==="Link sent to "+address+"."
      &&/Sign-up link sent/.test(shown.row)&&/Free monthly Baltor Pro starts when the account opens/.test(shown.row)&&/Not confirmed/.test(shown.row)
      &&!invitationWords.test(shown.message+" "+shown.row+" "+shown.formWords),{form,...shown});
  };
  /* The confirmation page keeps Confirm disabled, with a short note, until its sign-in settings have loaded, so a quick click
     is never refused with the link unused. The settings request is held here, then released. */
  const confirmWait=async (target,note)=>{
    let release=()=>{};const held=new Promise(resolve=>{release=resolve;});
    await target.route(url=>new URL(url).pathname==="/api/v1/account/identity",async route=>{await held;await route.continue();});
    await target.goto(fixture.confirm_base+"/auth/confirm?token_hash=pkce_browser0wait0check&type=signup",{waitUntil:"domcontentloaded"});
    await target.waitForFunction(()=>document.querySelector('[data-view="confirm"]')?.hidden===false,null,{timeout:10000}).catch(()=>{});
    const read=()=>target.evaluate(()=>({disabled:document.getElementById("confirm-button")?.disabled===true,loading:document.getElementById("confirm-loading")?.hidden===false,
      text:document.getElementById("confirm-loading")?.textContent||""}));
    const waiting=await read();
    if(note===check)await target.locator("#confirm-card").screenshot({path:output.replace(/\.json$/,"-confirm-waiting.png")}).catch(()=>{});
    release();
    await target.waitForFunction(()=>document.getElementById("confirm-button")?.disabled===false,null,{timeout:10000}).catch(()=>{});
    const ready=await read();
    note("the_confirm_button_waits_for_the_sign_in_settings",waiting.disabled&&waiting.loading&&waiting.text==="Loading the sign-in settings…"
      &&!ready.disabled&&!ready.loading,{waiting,ready});
  };
  /* Finding 4 of the persona journeys of September 24, 2026: after the new password was accepted, the card said "This link cannot
     be used ... Nothing was changed." until the account opened. Here the activation request is held, so the moment between the
     accepted password and the open account lasts as long as a slow connection would make it, and every drawing of the notice is
     recorded from the first script on. A second journey has the service refuse to open the account after the password is set. */
  const watchTheUnusableNotice=()=>{window.__unusableShown=[];document.addEventListener("DOMContentLoaded",()=>{const node=document.getElementById("confirm-unusable");
    if(node)new MutationObserver(()=>{if(!node.hidden)window.__unusableShown.push(document.getElementById("confirm-message")?.textContent||"");}).observe(node,{attributes:true,attributeFilter:["hidden"]});});};
  const openingJourney=refuse=>async (target,note)=>{
    await target.addInitScript(watchTheUnusableNotice);
    const address=journeyAddress(refuse?"refused":"opening"),password="opening-owner-"+randomBytes(8).toString("hex");
    const asked=await target.request.post(fixture.confirm_base+"/api/v1/account/signup",{data:{record_type:"service_account_signup_request/v2",email:address}});
    const link=asked.status()===202?await newestLink(target,address):"";
    let release=()=>{},held=false;const gate=new Promise(resolve=>{release=resolve;});
    await target.route(url=>url.pathname==="/api/v1/account/activate",async route=>{held=true;await gate;
      if(refuse)await route.fulfill({status:503,contentType:"application/json",body:JSON.stringify({record_type:"service_http_error/v1",error:{code:"service_unavailable"}})});
      else await route.continue();});
    if(link){await target.goto(link);await target.waitForFunction(()=>document.getElementById("confirm-button")?.disabled===false,null,{timeout:10000}).catch(()=>{});
      await target.fill("#confirm-password",password);await target.fill("#confirm-password-again",password);await target.click("#confirm-button");}
    const deadline=Date.now()+10000;while(link&&!held&&Date.now()<deadline)await target.waitForTimeout(20);
    await target.waitForTimeout(150);
    const card=()=>target.evaluate(()=>{const shown=id=>{const node=document.getElementById(id);return Boolean(node&&node.getClientRects().length);};
      return {path:location.pathname,unusable:shown("confirm-unusable"),form:shown("confirm-password-step"),set:shown("confirm-set"),signIn:shown("confirm-set-sign-in")?document.getElementById("confirm-set-sign-in").getAttribute("href"):"",
        status:document.getElementById("confirm-message")?.textContent||"",error:document.getElementById("confirm-message")?.classList.contains("error")===true,
        disabled:document.getElementById("confirm-button")?.disabled===true,setText:document.getElementById("confirm-set")?.innerText||"",connected:document.getElementById("connection-state")?.textContent||""};});
    const opening=await card();
    if(note===check&&!refuse)await target.locator("#confirm-card").screenshot({path:output.replace(/\.json$/,"-confirm-opening.png")}).catch(()=>{});
    release();
    if(refuse)await target.waitForFunction(()=>document.getElementById("confirm-message")?.classList.contains("error")===true,null,{timeout:10000}).catch(()=>{});
    else{await target.waitForFunction(()=>document.getElementById("connection-state")?.textContent==="Connected",null,{timeout:10000}).catch(()=>{});
      await target.waitForFunction(()=>location.pathname!=="/auth/confirm",null,{timeout:5000}).catch(()=>{});}
    await target.waitForTimeout(150);
    const after=await card(),drawn=await target.evaluate(()=>window.__unusableShown||null);
    if(!refuse){
      note("password_set_keeps_its_card_while_the_account_opens",held&&opening.path==="/auth/confirm"&&!opening.unusable&&opening.form&&!opening.set
        &&opening.status==="Password set. Opening your account…"&&!opening.error&&opening.disabled,{held,opening});
      note("the_unusable_notice_never_appears_after_the_password_is_accepted",held&&Array.isArray(drawn)&&drawn.length===0&&after.connected==="Connected"
        &&after.path==="/get-started"&&JSON.stringify(await shownViews(target))===JSON.stringify(["start"]),{held,drawn,after});
      return;}
    if(note===check)await target.locator("#confirm-card").screenshot({path:output.replace(/\.json$/,"-confirm-refused.png")}).catch(()=>{});
    note("a_password_set_without_an_open_account_says_so_and_offers_sign_in",held&&Array.isArray(drawn)&&drawn.length===0&&after.path==="/auth/confirm"&&!after.unusable&&!after.form&&after.set
      &&after.setText.includes("Your password is set.")&&after.setText.includes("Sign in with your email address and your new password.")&&after.signIn==="/login"
      &&after.error&&after.status==="The service did not open your account."&&after.connected==="Not connected"&&await standInSignIn(target,address,password)===200,{held,drawn,after});
  };
  /* Finding 2 of the persona journeys of September 24, 2026: Security and How it works said that public account creation was not
     open and that access came from an operator, beside a Get started button that opened working self-service sign-up. Where the
     service reports registration open, no page a visitor reads says that account creation is closed, that an operator issues access,
     or names test tokens, and Security and How it works state the live facts. Where it reports registration closed, no page says
     that anyone can create an account. The sentences that depend on the state are read after the service has answered. */
  const closedAccessWords=/account creation (?:is|remains) (?:not open|closed)|public account creation|not open yet|comes? from your operator|issued? by your operator|operator gave you|ask your operator|test tokens?|not taking new accounts|email sign-in is not enabled/i;
  const openAccessWords=/anyone can create an account/i;
  const accessFactPages=["/security","/how-it-works","/login","/setup","/get-started","/pricing","/examples","/docs","/"];
  const accessFacts=(base,open)=>async (target,note)=>{
    const found={};
    for(const path of accessFactPages){
      await target.goto(base+path);
      await target.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
      if(open)await target.waitForFunction(()=>document.getElementById("email-login")?.hidden===false,null,{timeout:10000}).catch(()=>{});
      if(path==="/setup")await target.waitForFunction(()=>document.querySelectorAll('#client-tabs [role="tab"]').length>0||document.getElementById("setup-message")?.textContent!=="",null,{timeout:10000}).catch(()=>{});
      found[path]=await target.evaluate(()=>{const view=[...document.querySelectorAll("[data-view]")].find(item=>!item.hidden);
        return [document.querySelector("header")?.innerText||"",view?.innerText||"",document.querySelector("footer")?.innerText||""].join("\n");});
    }
    const wrong=Object.entries(found).map(([path,words])=>[path,(open?closedAccessWords:openAccessWords).exec(words)?.[0]||""]).filter(([,words])=>words);
    const security=found["/security"]||"",about=found["/how-it-works"]||"";
    const facts=["You sign in with your email address and password.","Client tokens for your tools are created and revoked on your account page"].every(text=>security.includes(text))
      &&about.includes("you sign in with your email address and password, create a client token for each of your tools on your account page");
    if(open){
      note("no_page_says_account_creation_is_closed_while_registration_is_open",wrong.length===0,{wrong});
      note("security_and_how_it_works_state_the_self_service_account_facts",facts&&security.includes("Anyone can create an account on Get started: you give your email address, open the link we send and choose a password.")
        &&about.includes("Anyone can create an account on Get started."),{facts});
    }else note("no_page_offers_account_creation_while_registration_is_closed",wrong.length===0&&facts&&security.includes("This service is not taking new accounts right now."),{wrong,facts});
  };
  /* Fix 5 of the persona journeys of September 24, 2026: a reload or an address typed in the same tab signed the person out,
     because the sign-in lived only in the memory of the page. An email sign-in now lasts as long as the tab: once the service has
     opened the account, the identity provider's access token and its expiry, and nothing else, are kept in the tab's session
     storage. Signing out forgets it, a service token is never kept, a confirmation whose password is not set yet is never kept, a
     page opened by a confirmation link starts from the link, and a staff member's Administration link and view come back. The
     readers return key and field names only, never a stored value. */
  const keptKey="baltor.identity-session";
  const keptFacts=target=>target.evaluate(key=>{let kept=null;try{kept=JSON.parse(sessionStorage.getItem(key)||"null");}catch(_){kept="unreadable";}
    return {keys:Object.keys(sessionStorage),local:localStorage.length,cookie:document.cookie,fields:kept&&typeof kept==="object"?Object.keys(kept).sort():[],
      connected:document.getElementById("connection-state")?.textContent||"",path:location.pathname,account:document.getElementById("header-account")?.hidden===false,
      signIn:document.querySelector("header .nav-sign-in")?.hidden===false,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view)};},keptKey);
  const waitConnected=(target,want="Connected")=>target.waitForFunction(want=>document.getElementById("connection-state")?.textContent===want,want,{timeout:10000}).catch(()=>{});
  const settled=target=>target.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability",null,{timeout:10000}).catch(()=>{});
  const confirmedAccount=async (target,password)=>{
    const address=journeyAddress("kept");
    const asked=await target.request.post(fixture.confirm_base+"/api/v1/account/signup",{data:{record_type:"service_account_signup_request/v2",email:address}});
    const link=asked.status()===202?await newestLink(target,address):"";
    if(link){await target.goto(link);await target.waitForFunction(()=>document.getElementById("confirm-button")?.disabled===false,null,{timeout:10000}).catch(()=>{});
      await target.fill("#confirm-password",password);await target.fill("#confirm-password-again",password);await target.click("#confirm-button");
      await waitConnected(target);await target.waitForFunction(()=>location.pathname!=="/auth/confirm",null,{timeout:5000}).catch(()=>{});}
    return {address,link};
  };
  const keptSignIn=async (target,note)=>{
    await confirmedAccount(target,"kept-owner-"+randomBytes(8).toString("hex"));
    const opened=await keptFacts(target);
    note("the_kept_sign_in_holds_the_access_token_and_its_expiry_alone",opened.connected==="Connected"&&JSON.stringify(opened.keys)===JSON.stringify([keptKey])
      &&JSON.stringify(opened.fields)===JSON.stringify(["access_token","expires_at"])&&opened.local===0&&opened.cookie==="",{opened});
    await target.evaluate(()=>{history.pushState({},"","/setup");dispatchEvent(new PopStateEvent("popstate"));});
    await target.reload();await settled(target);await waitConnected(target);await target.waitForTimeout(200);
    const reloaded=await keptFacts(target);
    await target.goto(fixture.confirm_base+"/account");await settled(target);await waitConnected(target);await target.waitForTimeout(200);
    const typed=await keptFacts(target);
    const signedIn=(facts,path,view)=>facts.connected==="Connected"&&facts.path===path&&JSON.stringify(facts.views)===JSON.stringify([view])&&facts.account&&!facts.signIn&&JSON.stringify(facts.keys)===JSON.stringify([keptKey]);
    note("a_reload_and_a_typed_address_keep_an_email_sign_in",signedIn(reloaded,"/setup","setup")&&signedIn(typed,"/account","account"),{reloaded,typed});
    if(await target.locator("#header-sign-out").isVisible()){await signOutFromHeader(target);await waitConnected(target,"Not connected");}
    const signedOut=await keptFacts(target);
    await target.reload();await settled(target);await target.waitForTimeout(800);
    const afterSignOut=await keptFacts(target);
    note("signing_out_forgets_the_kept_sign_in",signedOut.keys.length===0&&afterSignOut.keys.length===0&&afterSignOut.connected==="Not connected"&&!afterSignOut.account&&afterSignOut.signIn,{signedOut,afterSignOut});
    /* A page opened by a confirmation link starts from the link, even in a tab that keeps a sign-in. */
    await confirmedAccount(target,"kept-other-"+randomBytes(8).toString("hex"));
    const address=journeyAddress("link");
    const asked=await target.request.post(fixture.confirm_base+"/api/v1/account/signup",{data:{record_type:"service_account_signup_request/v2",email:address}});
    const link=asked.status()===202?await newestLink(target,address):"";
    if(link){await target.goto(link);await settled(target);await target.waitForFunction(()=>document.getElementById("confirm-button")?.disabled===false,null,{timeout:10000}).catch(()=>{});}
    await target.waitForTimeout(500);
    const byLink=await target.evaluate(()=>({form:Boolean(document.getElementById("confirm-form")?.getClientRects().length),unusable:document.getElementById("confirm-unusable")?.hidden===false}));
    const linkFacts=await keptFacts(target);
    note("a_page_opened_by_a_confirmation_link_starts_from_the_link",Boolean(link)&&byLink.form&&!byLink.unusable&&linkFacts.connected==="Not connected"&&linkFacts.keys.length===0,{byLink,linkFacts});
    /* The same link with a password the page refuses after the provider verified it: the verified session is held for the retry,
       and is never kept, so a reload elsewhere in the tab does not open the account. */
    if(link&&byLink.form){await target.fill("#confirm-password",address);await target.fill("#confirm-password-again",address);await target.click("#confirm-button");
      await target.waitForFunction(()=>document.getElementById("confirm-message")?.classList.contains("error"),null,{timeout:10000}).catch(()=>{});}
    const pending=await keptFacts(target);
    await target.evaluate(()=>{history.pushState({},"","/account");dispatchEvent(new PopStateEvent("popstate"));});
    await target.reload();await settled(target);await target.waitForTimeout(800);
    const pendingReloaded=await keptFacts(target);
    note("a_confirmation_whose_password_is_not_set_is_never_kept",Boolean(link)&&byLink.form&&pending.keys.length===0&&pending.connected==="Not connected"
      &&pendingReloaded.keys.length===0&&pendingReloaded.connected==="Not connected"&&pendingReloaded.path==="/account",{pending,pendingReloaded});
    /* A service token pasted on the sign-in page stays in page memory only. */
    await target.goto(fixture.base+"/login");await target.fill("#access-token",fixture.token);await target.click("#connect-button");await waitConnected(target);
    const byToken=await keptFacts(target);
    await target.reload();await settled(target);await target.waitForTimeout(800);
    const tokenReloaded=await keptFacts(target);
    note("a_service_token_is_never_kept",byToken.connected==="Connected"&&byToken.keys.length===0&&tokenReloaded.keys.length===0&&tokenReloaded.connected==="Not connected",{byToken,tokenReloaded});
  };
  /* A staff member reloads the Administration view, then opens it again from the header without a new page load. */
  const keptStaffSignIn=async (target,note)=>{
    await staffSignIn(target);
    await target.reload();await settled(target);await waitConnected(target);
    await target.waitForFunction(()=>document.querySelectorAll("#staff-accounts article").length>=2,null,{timeout:10000}).catch(()=>{});
    const reloaded=await target.evaluate(()=>({path:location.pathname,link:document.getElementById("admin-nav")?.hidden===false,section:document.getElementById("staff-admin")?.hidden===false,
      rows:document.querySelectorAll("#staff-accounts article").length}));
    await target.evaluate(()=>{window.__samePage=true;history.pushState({},"","/account");dispatchEvent(new PopStateEvent("popstate"));});
    if(await target.locator("#admin-nav").isVisible())await headerLink(target,"admin").catch(()=>{});
    await target.waitForTimeout(300);
    const reopened=await target.evaluate(()=>({path:location.pathname,samePage:window.__samePage===true,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),
      section:document.getElementById("staff-admin")?.hidden===false}));
    note("a_reload_keeps_the_administration_link_and_view_for_staff",reloaded.path==="/admin"&&reloaded.link&&reloaded.section&&reloaded.rows>=2
      &&reopened.path==="/admin"&&reopened.samePage&&JSON.stringify(reopened.views)===JSON.stringify(["admin"])&&reopened.section,{reloaded,reopened});
  };
  /* Fix 4 of the persona journeys of September 24, 2026: signed in with an email address, Get set up still offered only "Sign in
     to check access", which led back to the sign-in page, beside a disabled check that needs a client token. Signed in, the guide
     now offers "Create a client token", which opens the account page's token panel, loaded and ready, and says in one line that the
     check runs with a client token. A visitor who is not signed in still sees the sign-in link. */
  const setupCheck=target=>target.evaluate(()=>{const seen=id=>{const node=document.getElementById(id);return Boolean(node&&node.getClientRects().length);};
    return {path:location.pathname,hash:location.hash,signIn:seen("setup-sign-in"),create:seen("setup-create-token"),createText:document.getElementById("setup-create-token")?.textContent||"",
      createHref:document.getElementById("setup-create-token")?.getAttribute("href")||"",line:document.getElementById("setup-identity")?.textContent||"",
      controls:seen("client-access-controls"),creator:document.getElementById("create-client-token")?.disabled===false,focused:document.activeElement?.id||"",
      views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view)};});
  const setupSignedIn=async (target,note)=>{
    await target.goto(fixture.confirm_base+"/setup");await settled(target);await target.waitForTimeout(300);
    const visitor=await setupCheck(target);
    await confirmedAccount(target,"setup-owner-"+randomBytes(8).toString("hex"));
    await target.evaluate(()=>{history.pushState({},"","/setup");dispatchEvent(new PopStateEvent("popstate"));});
    await target.waitForTimeout(300);
    const member=await setupCheck(target);
    note("get_set_up_offers_a_signed_in_visitor_a_client_token_instead_of_sign_in",visitor.signIn&&!visitor.create&&member.path==="/setup"&&!member.signIn&&member.create
      &&member.createText==="Create a client token"&&member.createHref==="/account#account-keys"
      &&member.line.startsWith("This check runs with a client token, not with your email sign-in.")&&await target.locator("#test-protocol").isDisabled(),{visitor,member});
    if(member.create)await target.click("#setup-create-token");
    await target.waitForFunction(()=>document.getElementById("client-access-controls")?.hidden===false,null,{timeout:10000}).catch(()=>{});
    await target.waitForTimeout(200);
    const panel=await setupCheck(target);
    if(note===check)await target.screenshot({path:output.replace(/\.json$/,"-setup-client-token.png")}).catch(()=>{});
    note("create_a_client_token_opens_the_loaded_token_panel",member.create&&panel.path==="/account"&&panel.hash==="#account-keys"&&JSON.stringify(panel.views)===JSON.stringify(["account"])
      &&panel.controls&&panel.creator&&panel.focused==="client-token-label",{panel});
  };
  /* Finding 10 of the persona journeys of September 24, 2026: the price line under the Get started heading said "subscribe to Baltor
     Pro for $29 a month" to an account that the founding offer already covered, the step list marked "Subscribe to Baltor Pro, $29 a
     month" as done for an account that never subscribed, and no page stated the founding offer before sign-up. The price line, the
     fourth step and the pricing page's free plan answer now follow the account's plan and the founding offer the service reports. */
  const foundingSentence="While founding places last, a new account gets Baltor Pro free each month.";
  const foundingPrice="Create your account and connect your harness. Baltor Pro is $29 a month, and while founding places last a new account gets it free each month.";
  const planFacts=target=>target.evaluate(()=>{const shown=node=>Boolean(node&&node.getClientRects().length);
    return {price:document.getElementById("funnel-price")?.textContent||"",stepTitle:document.getElementById("funnel-step-plan-title")?.textContent||"",
      stepNote:document.getElementById("funnel-step-plan-note")?.textContent||"",stepDone:document.querySelector('[data-funnel-step="plan"]')?.classList.contains("is-done")===true,
      founding:[...document.querySelectorAll("[data-founding-offer]")].filter(node=>!node.hidden).map(node=>node.textContent.trim()),
      notes:[...document.querySelectorAll("[data-plan-note]")].filter(node=>!node.hidden).map(node=>node.dataset.planNote),
      card:shown(document.getElementById("pricing-founding")),answer:(()=>{const copy=document.querySelector("#pricing-free-plan p")?.cloneNode(true);
        copy?.querySelectorAll("[hidden]").forEach(node=>node.remove());return copy?.textContent||"";})()};});
  const openInPage=async (target,path)=>{await target.evaluate(path=>{history.pushState({},"",path);dispatchEvent(new PopStateEvent("popstate"));},path);await target.waitForTimeout(100);};
  const foundingPublic=(base,open)=>async (target,note)=>{
    await target.goto(base+"/pricing");await settled(target);await target.waitForTimeout(200);
    const pricing=await planFacts(target);
    await openInPage(target,"/get-started");
    const funnel=await planFacts(target);
    const reported=(await (await target.request.get(base+"/api/v1/capabilities")).json()).result.website.founding_offer_open;
    if(open)note("pricing_and_get_started_state_the_founding_offer_while_places_remain",reported===true&&pricing.card
      &&JSON.stringify(pricing.founding)===JSON.stringify([foundingSentence,foundingSentence.trim()])&&pricing.answer.includes(foundingSentence)&&pricing.notes.length===0
      &&funnel.price===foundingPrice&&funnel.price.includes("$29 a month")&&funnel.stepTitle==="Subscribe to Baltor Pro"&&funnel.stepNote==="$29 a month, or free each month while founding places last",{reported,pricing,funnel});
    else note("no_page_states_the_founding_offer_when_the_service_reports_no_free_place",reported===false&&!pricing.card&&pricing.founding.length===0&&!/founding/i.test(pricing.answer)
      &&funnel.price==="Create your account, subscribe to Baltor Pro for $29 a month and connect your harness."&&funnel.stepNote==="$29 a month, cancel any time",{reported,pricing,funnel});
  };
  const coveredPlan=(credential,source)=>async (target,note)=>{
    await target.goto(fixture.billing_base+"/login");await target.fill("#access-token",credential);await target.click("#connect-button");await waitConnected(target);
    await openInPage(target,"/get-started");
    const funnel=await planFacts(target),steps=await target.evaluate(()=>[...document.querySelectorAll("[data-funnel-step] strong")].map(node=>node.textContent.trim()));
    await openInPage(target,"/pricing");
    const pricing=await planFacts(target);
    const expected={founding_free_monthly:["Baltor Pro included","Free each month, as one of the first accounts","Your account holds a founding place, so Baltor Pro is free for it each month."],
      free_monthly:["Baltor Pro included","Free each month for this account","Your account includes Baltor Pro free each month."]}[source];
    note("get_started_and_pricing_follow_the_"+source+"_plan",funnel.price==="Your account includes Baltor Pro. Connect your harness to start."&&!/\$29|subscribe/i.test(funnel.price)
      &&funnel.stepTitle===expected[0]&&funnel.stepNote===expected[1]&&funnel.stepDone&&!steps.includes("Subscribe to Baltor Pro")
      &&JSON.stringify(pricing.notes)===JSON.stringify([source])&&pricing.answer.includes(expected[2])&&pricing.founding.length===0&&!pricing.card,{funnel,steps,pricing});
  };
  /* Finding 8 of the persona journeys of September 24, 2026: nothing said who vets library items, or how. Security now has a "How
     review works" section, and the pricing line "New vetted additions" links to it. Every number and rule it states is read from the
     review records: the panel policy for new items and the review record of the served catalogue's first release, including that
     one of its reviewers came from the model family of the items' author. */
  const numberWords=["no","one","two","three","four","five","six","seven","eight","nine","ten"];
  const reviewClaims=()=>{const totals=catalogueReviews.totals,lenses=catalogueReviews.reviewers.map(item=>item.lens);
    const sameFamily=catalogueReviews.reviewers.some(item=>/\bclaude\b/i.test(item.label));
    return ["An item joins the library only after independent reviewers approve its exact bytes.",
      ...(catalogueReviews.reviewers.every(item=>item.produced_any_item_under_review===false)?["No reviewer judges an item it wrote"]:[]),
      ...(reviewPanelPolicy.any_rejection_withholds_approval===true?["one written rejection keeps an item out, with the reason recorded."]:[]),
      "a new item needs approval from at least "+numberWords[reviewPanelPolicy.minimum_approvals]+" reviewers of at least "+numberWords[reviewPanelPolicy.minimum_distinct_families]+" model families",
      ...(reviewPanelPolicy.exclude_producer_family===true?["none of them from the family of the model that wrote the item."]:[]),
      ...(reviewPanelPolicy.prechecks.licence?["a licence that is not accepted or that disagrees with the licence the item declares"]:[]),
      ...(reviewPanelPolicy.prechecks.format?["a missing part"]:[]),...(reviewPanelPolicy.prechecks.safety?["unsafe instructions"]:[]),
      ...(reviewPanelPolicy.prechecks.effects?["declared effects that do not match its steps"]:[]),...(reviewPanelPolicy.prechecks.secrets?["a value shaped like a credential"]:[]),
      ...(reviewPanelPolicy.prechecks.duplicates?["a copy of another item"]:[]),
      "The library's first "+totals.approved+" items were approved on September 21, 2026","three reviewers who wrote none of them",
      ...lenses.map(lens=>lens==="adversarial"?"one adversarial":"one for "+lens),
      totals.rejected+" of the "+totals.items_reviewed+" items they judged were rejected.",
      ...(sameFamily?["One of those reviewers came from the same model family as the model that wrote the items."]:[])];};
  const reviewExplained=async (target,note)=>{
    await target.goto(fixture.base+"/security");await settled(target);
    const section=await target.evaluate(()=>{const node=document.getElementById("how-review-works");
      return {shown:Boolean(node&&node.getClientRects().length),heading:node?.querySelector("h2")?.textContent||"",words:(node?.innerText||"").replace(/\s+/g," ")};});
    const missing=reviewClaims().filter(claim=>!section.words.includes(claim));
    note("how_review_works_states_only_what_the_review_records_hold",catalogueReviews.recorded_at==="2026-09-21"&&section.shown&&section.heading==="How review works"&&missing.length===0,{missing,heading:section.heading});
    await target.goto(fixture.base+"/pricing");await settled(target);
    const link=await target.evaluate(()=>{const node=document.querySelector('[data-plan-point="additions"] a');return {href:node?.getAttribute("href")||"",text:node?.textContent||""};});
    if(link.href)await target.click('[data-plan-point="additions"] a');
    await target.waitForTimeout(300);
    const landed=await target.evaluate(()=>{const node=document.getElementById("how-review-works"),box=node?.getBoundingClientRect();
      return {path:location.pathname,hash:location.hash,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),top:box?Math.round(box.top):-1,viewport:innerHeight};});
    note("pricing_links_new_vetted_additions_to_how_review_works",link.href==="/security#how-review-works"&&link.text==="pass review"&&landed.path==="/security"&&landed.hash==="#how-review-works"
      &&JSON.stringify(landed.views)===JSON.stringify(["security"])&&landed.top>=0&&landed.top<landed.viewport,{link,landed});
  };
  /* Finding 6 of the persona journeys of September 24, 2026: the Pi tab named the extension this website serves, /assets/pi/baltor.ts,
     as plain text. The path is now a link to the served file, the note keeps its exact words, and one button copies the file's full
     address. The file the link opens is compared with the source file, and a tab whose note names no file shows no file action. */
  const piSource=readFileSync(resolve(root,"src/loop_engine/core/service_runtime/web_assets/pi/baltor.ts"),"utf8");
  const piExtension=async (target,note)=>{
    await target.context().grantPermissions(["clipboard-read","clipboard-write"]);
    await target.goto(fixture.base+"/setup");await settled(target);
    await target.waitForSelector("#client-tab-pi",{timeout:10000}).catch(()=>{});
    const recipe=recipeRecord.recipes.find(item=>item.id==="pi");
    const tabFacts=()=>target.evaluate(()=>{const link=document.querySelector("#client-configuration-note a");
      return {note:document.getElementById("client-configuration-note")?.textContent||"",href:link?.getAttribute("href")||"",text:link?.textContent||"",newTab:link?.target==="_blank"&&/noopener/.test(link?.rel||""),
        action:Boolean(document.getElementById("copy-client-file")?.getClientRects().length),address:document.getElementById("client-file-address")?.textContent||""};});
    await target.click("#client-tab-codex").catch(()=>{});
    const other=await tabFacts();
    await target.click("#client-tab-pi").catch(()=>{});
    const pi=await tabFacts();
    await target.evaluate(()=>navigator.clipboard.writeText("nothing copied yet")).catch(()=>{});
    if(pi.action)await target.click("#copy-client-file");
    await target.waitForTimeout(200);
    const copied=await target.evaluate(()=>navigator.clipboard.readText()).catch(()=>"");
    const served=pi.href?await target.request.get(fixture.base+pi.href):null,body=served?await served.text():"";
    note("the_pi_extension_path_is_a_link_with_a_copy_action",pi.note===recipe.configuration_note&&pi.href==="/assets/pi/baltor.ts"&&pi.text==="/assets/pi/baltor.ts"&&pi.newTab
      &&pi.action&&pi.address===fixture.base+"/assets/pi/baltor.ts"&&copied===pi.address&&served?.status()===200&&body===piSource
      &&!other.href&&!other.action&&other.note===recipeRecord.recipes.find(item=>item.id==="codex").configuration_note,{pi,other,copied,status:served?.status()});
  };
  /* Finding 7 of the persona journeys of September 24, 2026: the phone menu's named control was a checkbox clipped to one pixel under
     the logo, and the 44 pixel icon a person touches was a label hidden from assistive technology. The menu is now one visible button
     with a name, aria-expanded and aria-controls="main-nav". At phone width, on every public page, the control under the icon is that
     button, it opens and closes the navigation it names and says so, Escape closes it with focus back on it, and a choice closes it,
     with no script error. */
  const menuPages=["/","/pricing","/how-it-works","/use-cases","/setup","/get-started","/security","/docs","/login"];
  const phoneMenu=async (target,note)=>{
    const pageErrors=[];target.on("pageerror",error=>pageErrors.push(safeError(error.message)));
    await target.setViewportSize({width:390,height:844});
    const facts=()=>target.evaluate(()=>{const button=document.getElementById("menu-button"),nav=document.getElementById("main-nav"),brand=document.querySelector("header .brand");
      const box=button?.getBoundingClientRect(),logo=brand?.getBoundingClientRect(),under=box?document.elementFromPoint(box.left+box.width/2,box.top+box.height/2):null;
      return {tag:button?.tagName||"",name:button?.getAttribute("aria-label")||"",hidden:button?.getAttribute("aria-hidden")||"",controls:button?.getAttribute("aria-controls")||"",expanded:button?.getAttribute("aria-expanded")||"",
        size:box?[Math.round(box.width),Math.round(box.height)]:[0,0],touched:Boolean(under&&button&&(under===button||button.contains(under))),
        apart:Boolean(box&&logo&&(box.left>=logo.right||box.right<=logo.left||box.top>=logo.bottom||box.bottom<=logo.top)),
        navShown:Boolean(nav&&getComputedStyle(nav).display!=="none"),focused:document.activeElement===button,
        checkbox:Boolean(document.getElementById("menu-toggle")||document.querySelector("header input[type=checkbox]")),hiddenLabel:Boolean(document.querySelector('header label[aria-hidden="true"]'))};});
    const visits=[];
    for(const path of menuPages){
      await target.goto(fixture.base+path);await settled(target);
      const closed=await facts();
      await target.click("#menu-button").catch(()=>{});const opened=await facts();
      await target.keyboard.press("Escape");const escaped=await facts();
      await target.click("#menu-button").catch(()=>{});
      await target.locator('#main-nav a[data-page="pricing"]').click({timeout:3000}).catch(()=>{});
      const chosen=await facts();
      visits.push({path,closed,opened,escaped,chosen});
    }
    const problems=visits.flatMap(({path,closed,opened,escaped,chosen})=>[
      ...(closed.tag==="BUTTON"&&closed.name==="Menu"&&closed.hidden===""&&closed.controls==="main-nav"&&closed.expanded==="false"&&!closed.navShown?[]:[path+": the closed menu is "+JSON.stringify(closed)]),
      ...(closed.size[0]>=44&&closed.size[1]>=44&&closed.touched&&closed.apart&&!closed.checkbox&&!closed.hiddenLabel?[]:[path+": the control a person touches is not the named button"]),
      ...(opened.expanded==="true"&&opened.navShown?[]:[path+": a press does not open the menu and say so"]),
      ...(escaped.expanded==="false"&&!escaped.navShown&&escaped.focused?[]:[path+": Escape does not close the menu with focus on its button"]),
      ...(chosen.expanded==="false"&&!chosen.navShown?[]:[path+": a choice leaves the menu open"])]);
    note("phone_menu_is_one_named_button_that_states_whether_it_is_open_on_every_page",visits.length===menuPages.length&&problems.length===0&&pageErrors.length===0,{problems,pageErrors});
  };
  const signedInFunnel=(credential,covered,freeMonthly=false)=>async (target,note)=>{
    await target.goto(fixture.billing_base+"/login");await target.fill("#access-token",credential);await target.click("#connect-button");
    await target.waitForFunction(()=>document.querySelector("#connection-state")?.textContent==="Connected",null,{timeout:10000}).catch(()=>{});
    await target.evaluate(()=>{history.pushState({},"","/get-started");dispatchEvent(new PopStateEvent("popstate"));});
    const facts=await funnelFacts(target);
    /* The owner's wording of September 23, 2026: an account with free monthly Baltor Pro, founding or granted, reads that its
       account includes Baltor Pro, on the funnel and on the account page, with no invitation or trial word. */
    if(covered&&freeMonthly){const plan=await target.evaluate(()=>({shown:document.getElementById("account-plan")?.hidden===false,text:document.getElementById("account-plan")?.textContent||""}));
      note("get_started_funnel_tells_a_free_monthly_account_that_it_includes_baltor_pro",facts.state==="plan"&&facts.title==="Your account includes Baltor Pro"&&!facts.subscribe&&!invitationWords.test(facts.words)
        &&facts.primaries.length===1&&facts.primaries[0].id==="funnel-setup-action"&&facts.primaries[0].href==="/setup"&&plan.shown&&plan.text==="Your account includes Baltor Pro.",{...facts,plan});return;}
    if(covered){note("get_started_funnel_tells_a_granted_account_that_its_plan_is_covered",facts.state==="plan"&&facts.title==="Your account covers Baltor Pro"&&!facts.subscribe&&!invitationWords.test(facts.words)
      &&facts.primaries.length===1&&facts.primaries[0].id==="funnel-setup-action"&&facts.primaries[0].href==="/setup",facts);return;}
    let link="";
    if(facts.subscribe){await target.click("#funnel-subscribe");
      await target.waitForFunction(()=>document.querySelector("#funnel-plan-message a")!==null||document.getElementById("funnel-plan-message")?.classList.contains("error"),null,{timeout:10000}).catch(()=>{});
      link=await target.evaluate(()=>document.querySelector("#funnel-plan-message a")?.href||"");}
    note("get_started_funnel_offers_checkout_to_an_account_without_paid_access",facts.state==="plan"&&facts.title==="Subscribe to Baltor Pro"&&facts.subscribe&&facts.primaries.length===1&&(await target.locator("#funnel-plan-text").textContent())===checkoutPlanText
      &&facts.primaries[0].id==="funnel-subscribe"&&facts.primaries[0].text==="Subscribe for $29 a month"&&link.startsWith("https://checkout.stripe.com/"),{...facts,link});
  };
  /* A scenario that needs a second visit opens a second context, as a person opening the link on another device would. */
  const inSecondContext=async (mutation,tracker,run)=>{const {context:later,page:second}=await openJourney(mutation,undefined,tracker);try{await run(second);}finally{await later.close();}};
  const journeyScenarios={
    sign_up:(target,note)=>signUpJourney(target,note),
    used_link:async (target,note,mutation,tracker)=>{const journey=await signUpJourney(target,()=>{});await inSecondContext(mutation,tracker,second=>usedLink(second,note,journey));},
    recovery:async (target,note,mutation,tracker)=>{const journey=await signUpJourney(target,()=>{});await inSecondContext(mutation,tracker,second=>recoveryJourney(second,note,journey));},
    funnel_open:funnelScenario(fixture.confirm_base,true),funnel_closed:funnelScenario(fixture.base,false),funnel_waitlist:funnelScenario(fixture.account_base,false,true),list_request:listRequest,
    invited:signedInFunnel(fixture.billing_invited_token,true),unpaid:signedInFunnel(fixture.billing_token,false),
    free_monthly:signedInFunnel(fixture.billing_free_monthly_token,true,true),
    staff:(target,note)=>staffJourney(target,note),staff_links:(target,note)=>staffLinkJourney(target,note),
    confirm_wait:(target,note)=>confirmWait(target,note),password_opening:openingJourney(false),password_refused:openingJourney(true),
    access_facts_open:accessFacts(fixture.confirm_base,true),access_facts_closed:accessFacts(fixture.base,false),
    kept_sign_in:keptSignIn,kept_staff_sign_in:keptStaffSignIn,setup_signed_in:setupSignedIn,
    founding_open:foundingPublic(fixture.signup_base,true),founding_closed:foundingPublic(fixture.confirm_base,false),
    plan_founding:coveredPlan(fixture.billing_founding_token,"founding_free_monthly"),plan_free_monthly:coveredPlan(fixture.billing_free_monthly_token,"free_monthly"),
    review_explained:reviewExplained,pi_extension:piExtension,phone_menu:phoneMenu};
  for(const name of Object.keys(journeyScenarios)){
    const {context:opened,page:target}=await openJourney(null);
    try{await journeyScenarios[name](target,check);}catch(error){check("journey_scenario_completed_"+name,false,{error:safeError(error)});}
    await opened.close();
  }
  /* The funnel in both states at both sizes. */
  for(const [base,open] of [[fixture.confirm_base,true],[fixture.base,false]])for(const wide of [true,false])
    await funnelScreenshot(base,open,wide,"-start-"+(open?"open":"closed")+"-"+(wide?"desktop":"mobile")+".png");
  const journeyControls=[
    {name:"call_the_provider_sign_up_from_the_page",scenario:"sign_up",path:"/assets/service.js",find:"try { await requestAccountLink(\"signup\", $(field).value.trim()); message(status, signupSent); sent(); }",
     replacement:"try { await identityClient.auth.signUp({email:$(field).value.trim(),password:$(field).value.trim()}); message(status, signupSent); sent(); }",expected:["sign_up_sends_the_address_alone_to_this_service_and_never_calls_the_provider_sign_up"]},
    {name:"keep_the_token_in_the_address",scenario:"sign_up",path:"/assets/service.js",find:'history.replaceState({}, "", "/auth/confirm");',replacement:"",expected:["the_confirmation_page_clears_the_token_from_the_address_and_asks_for_a_password_first"]},
    {name:"open_the_account_without_a_new_password",scenario:"sign_up",path:"/assets/service.js",find:"const updated = await client.auth.updateUser({password});",replacement:"const updated = {error:null};",
     expected:["the_new_password_is_set_before_the_account_opens","a_password_chosen_first_by_someone_else_no_longer_opens_the_account"]},
    {name:"offer_payment_while_checkout_is_closed",scenario:"sign_up",path:"/assets/service.js",find:"(checkout ? funnelPlans.checkout : funnelPlans.unpaid)",replacement:"funnelPlans.checkout",expected:["get_started_funnel_offers_no_payment_while_checkout_is_closed"]},
    {name:"take_a_used_link_for_a_sign_in",scenario:"used_link",path:"/assets/service.js",find:"if (verified.error || !verified.data?.session) { showConfirmation(); message(\"confirm-message\", \"\"); return; }",replacement:"",expected:["a_used_link_says_so_plainly_and_offers_a_new_one"]},
    {name:"refuse_recovery_links",scenario:"recovery",path:"/assets/service.js",find:'const confirmTypes = ["signup", "recovery"];',replacement:'const confirmTypes = ["signup"];',expected:["recovery_reaches_the_same_choose_a_password_page"]},
    {name:"never_offer_account_creation_on_the_funnel",scenario:"funnel_open",path:"/assets/service.js",find:'(registrationOpen || waitingList) ? "register" : "invite"',replacement:'false ? "register" : "invite"',expected:["get_started_funnel_offers_account_creation_while_registration_is_open"]},
    {name:"always_offer_account_creation_on_the_funnel",scenario:"funnel_closed",path:"/assets/service.js",find:'(registrationOpen || waitingList) ? "register" : "invite"',replacement:'true ? "register" : "invite"',expected:["get_started_funnel_offers_sign_in_when_registration_and_the_request_list_are_closed"]},
    {name:"ignore_the_request_list_on_the_funnel",scenario:"funnel_waitlist",path:"/assets/service.js",find:'(registrationOpen || waitingList) ? "register" : "invite"',replacement:'registrationOpen ? "register" : "invite"',expected:["get_started_funnel_takes_the_address_where_the_service_keeps_a_request_list"]},
    {name:"bring_back_free_search_in_the_funnel_price_line",scenario:"funnel_waitlist",path:"/get-started",find:'subscribe to Baltor Pro for $29 a month and connect your harness.</p>',replacement:'subscribe to Baltor Pro for $29 a month and connect your harness. Search is free.</p>',expected:["get_started_funnel_takes_the_address_where_the_service_keeps_a_request_list"]},
    {name:"send_no_address_to_the_request_list",scenario:"list_request",path:"/assets/service.js",find:'email:$("funnel-email").value.trim(),note:""',replacement:'email:"",note:""',expected:["get_started_funnel_puts_the_address_on_the_request_list_and_says_a_link_follows"]},
    {name:"take_no_request_on_the_funnel",scenario:"list_request",path:"/assets/service.js",find:"const listed = capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.waitlist_available === true;",replacement:"const listed = false;",expected:["get_started_funnel_puts_the_address_on_the_request_list_and_says_a_link_follows"]},
    {name:"push_the_first_step_below_the_first_screen_open",scenario:"funnel_open",path:"/assets/service.css",find:".funnel-band{padding:64px",replacement:".funnel-band{padding-top:900px!important;padding:64px",expected:["get_started_funnel_first_step_fits_the_first_screen_open_1440","get_started_funnel_first_step_fits_the_first_screen_open_390"]},
    {name:"push_the_first_step_below_the_first_screen_closed",scenario:"funnel_closed",path:"/assets/service.css",find:".funnel-band{padding:64px",replacement:".funnel-band{padding-top:900px!important;padding:64px",expected:["get_started_funnel_first_step_fits_the_first_screen_closed_1440","get_started_funnel_first_step_fits_the_first_screen_closed_390"]},
    {name:"push_the_first_step_below_the_first_screen_list",scenario:"funnel_waitlist",path:"/assets/service.css",find:".funnel-band{padding:64px",replacement:".funnel-band{padding-top:900px!important;padding:64px",expected:["get_started_funnel_first_step_fits_the_first_screen_list_1440","get_started_funnel_first_step_fits_the_first_screen_list_390"]},
    {name:"ignore_where_paid_access_comes_from",scenario:"invited",path:"/assets/service.js",find:"funnelPlans[accessSource] ||",replacement:"",expected:["get_started_funnel_tells_a_granted_account_that_its_plan_is_covered"]},
    {name:"use_another_title_for_a_free_monthly_account",scenario:"free_monthly",path:"/assets/service.js",find:'free_monthly:{title:"Your account includes Baltor Pro"',replacement:'free_monthly:{title:"Your account covers Baltor Pro"',expected:["get_started_funnel_tells_a_free_monthly_account_that_it_includes_baltor_pro"]},
    {name:"hide_the_included_plan_on_the_account_page",scenario:"free_monthly",path:"/assets/service.js",find:'$("account-plan").hidden = !coveredSources.includes(accessSource);',replacement:'$("account-plan").hidden = true;',expected:["get_started_funnel_tells_a_free_monthly_account_that_it_includes_baltor_pro"]},
    {name:"hide_the_staff_accounts_view",scenario:"staff",path:"/assets/service.js",find:'$("staff-admin").hidden = false;',replacement:"",expected:["a_superadmin_sees_every_account_and_grants_free_monthly_in_the_administration_view"]},
    {name:"hide_the_sign_up_link_form",scenario:"staff_links",path:"/assets/service.js",find:'$("staff-links-form").hidden = !overview.permissions.includes("accounts.send_sign_up_links");',replacement:'$("staff-links-form").hidden = true;',expected:["a_superadmin_sends_a_sign_up_link_and_the_account_shows_as_waiting"]},
    {name:"draw_the_unusable_notice_while_the_account_opens",scenario:"password_opening",path:"/assets/service.js",
     find:'if (passwordSet === "opening") { $("confirm-password-step").hidden = false; $("confirm-unusable").hidden = true; $("confirm-button").disabled = true; $("confirm-loading").hidden = true; return; }',replacement:"",
     expected:["password_set_keeps_its_card_while_the_account_opens","the_unusable_notice_never_appears_after_the_password_is_accepted"]},
    {name:"keep_saying_setting_your_password_while_the_account_opens",scenario:"password_opening",path:"/assets/service.js",find:'message("confirm-message", "Password set. Opening your account…");',replacement:"",
     expected:["password_set_keeps_its_card_while_the_account_opens"]},
    {name:"say_the_link_cannot_be_used_after_the_password_is_set",scenario:"password_refused",path:"/assets/service.js",
     find:'if (passwordSet === "set") { $("confirm-password-step").hidden = true; $("confirm-unusable").hidden = true; return; }',replacement:"",
     expected:["a_password_set_without_an_open_account_says_so_and_offers_sign_in"]},
    {name:"bring_back_the_closed_account_creation_sentence_on_security",scenario:"access_facts_open",path:"/security",
     find:'You sign in with your email address and password. Client tokens',replacement:'Public account creation is not open. Access comes from your operator, who can issue and revoke test tokens. Client tokens',
     expected:["no_page_says_account_creation_is_closed_while_registration_is_open","security_and_how_it_works_state_the_self_service_account_facts"]},
    {name:"bring_back_the_operator_revocation_sentence_on_get_set_up",scenario:"access_facts_open",path:"/assets/client-recipes.json",
     find:'"revocation_note": "Open your account page,',replacement:'"revocation_note": "If your operator gave you the token, ask your operator to revoke it. Open your account page,',
     expected:["no_page_says_account_creation_is_closed_while_registration_is_open"]},
    {name:"never_state_that_the_service_takes_new_accounts",scenario:"access_facts_open",path:"/assets/service.js",find:"applyRegistrationState(registrationOpen);",replacement:"",
     expected:["security_and_how_it_works_state_the_self_service_account_facts"]},
    {name:"state_that_anyone_can_create_an_account_in_every_state",scenario:"access_facts_closed",path:"/assets/service.js",find:'sentence.dataset.registrationState !== (open ? "open" : "closed")',replacement:'sentence.dataset.registrationState !== "open"',
     expected:["no_page_offers_account_creation_while_registration_is_closed"]},
    {name:"keep_no_sign_in_across_a_reload",scenario:"kept_sign_in",path:"/assets/service.js",find:'if (authenticationMode === "browser_identity") keptSession.write(supplied);',replacement:"",
     expected:["the_kept_sign_in_holds_the_access_token_and_its_expiry_alone","a_reload_and_a_typed_address_keep_an_email_sign_in"]},
    {name:"keep_no_staff_sign_in_across_a_reload",scenario:"kept_staff_sign_in",path:"/assets/service.js",find:'if (authenticationMode === "browser_identity") keptSession.write(supplied);',replacement:"",
     expected:["a_reload_keeps_the_administration_link_and_view_for_staff"]},
    {name:"open_the_workspace_instead_of_the_page_asked_for_after_a_reload",scenario:"kept_sign_in",path:"/assets/service.js",find:"if (!stay) {",replacement:"if (true) {",
     expected:["a_reload_and_a_typed_address_keep_an_email_sign_in"]},
    {name:"keep_the_sign_in_after_sign_out",scenario:"kept_sign_in",path:"/assets/service.js",find:'generation++; token = ""; keptSession.clear();',replacement:'generation++; token = "";',
     expected:["signing_out_forgets_the_kept_sign_in"]},
    {name:"keep_every_token_the_page_holds",scenario:"kept_sign_in",path:"/assets/service.js",find:'if (authenticationMode === "browser_identity") keptSession.write(supplied);',
     replacement:'sessionStorage.setItem("baltor.identity-session", JSON.stringify({access_token:supplied, expires_at:0}));',expected:["a_service_token_is_never_kept"]},
    {name:"keep_the_session_of_a_confirmation_before_its_password_is_set",scenario:"kept_sign_in",path:"/assets/service.js",
     find:'flow.session = verified.data.session; flow.email = verified.data.user?.email || "";',replacement:'flow.session = verified.data.session; flow.email = verified.data.user?.email || ""; keptSession.write(flow.session.access_token);',
     expected:["a_confirmation_whose_password_is_not_set_is_never_kept"]},
    {name:"restore_a_kept_sign_in_over_a_confirmation_link",scenario:"kept_sign_in",path:"/assets/service.js",find:"if (kept && !confirmation && ",replacement:"if (kept && ",
     expected:["a_page_opened_by_a_confirmation_link_starts_from_the_link"]},
    {name:"keep_offering_sign_in_to_a_signed_in_visitor_on_get_set_up",scenario:"setup_signed_in",path:"/auth/confirm",
     find:'data-after-login="/setup" data-signed-out>',replacement:'data-after-login="/setup">',expected:["get_set_up_offers_a_signed_in_visitor_a_client_token_instead_of_sign_in"]},
    {name:"offer_no_client_token_on_get_set_up",scenario:"setup_signed_in",path:"/auth/confirm",
     find:'data-page="account" data-signed-in hidden>Create a client token</a>',replacement:'data-page="account" hidden>Create a client token</a>',
     expected:["get_set_up_offers_a_signed_in_visitor_a_client_token_instead_of_sign_in","create_a_client_token_opens_the_loaded_token_panel"]},
    {name:"open_the_account_page_without_loading_the_token_panel",scenario:"setup_signed_in",path:"/assets/service.js",
     find:'clientAccess.refresh().then(() => { if (!$("client-access-controls").hidden) $("client-token-label").focus({preventScroll:true}); });',replacement:"",
     expected:["create_a_client_token_opens_the_loaded_token_panel"]},
    {name:"mark_the_subscription_step_done_for_a_free_monthly_account",scenario:"plan_free_monthly",path:"/assets/service.js",
     find:'$("funnel-step-plan-title").textContent = coveredStep ? coveredStep[0] : servedFunnel.title;',replacement:'$("funnel-step-plan-title").textContent = servedFunnel.title;',
     expected:["get_started_and_pricing_follow_the_free_monthly_plan"]},
    {name:"offer_the_subscription_price_to_a_founding_account",scenario:"plan_founding",path:"/assets/service.js",
     find:'$("funnel-price").textContent = coveredStep ? plan.title',replacement:'$("funnel-price").textContent = false ? plan.title',
     expected:["get_started_and_pricing_follow_the_founding_free_monthly_plan"]},
    {name:"hide_the_plan_note_on_pricing",scenario:"plan_founding",path:"/assets/service.js",
     find:'sentence.hidden = !signedIn || sentence.dataset.planNote !== accessSource;',replacement:"sentence.hidden = true;",
     expected:["get_started_and_pricing_follow_the_founding_free_monthly_plan"]},
    {name:"state_the_founding_offer_when_no_place_is_free",scenario:"founding_closed",path:"/assets/service.js",
     find:"const foundingOpen = !signedIn && capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.founding_offer_open === true;",replacement:"const foundingOpen = !signedIn;",
     expected:["no_page_states_the_founding_offer_when_the_service_reports_no_free_place"]},
    {name:"never_state_the_founding_offer",scenario:"founding_open",path:"/assets/service.js",
     find:"const foundingOpen = !signedIn && capabilities?.record_type === CAPABILITIES_RECORD_TYPE && capabilities.website?.founding_offer_open === true;",replacement:"const foundingOpen = false;",
     expected:["pricing_and_get_started_state_the_founding_offer_while_places_remain"]},
    {name:"claim_three_model_families_for_review",scenario:"review_explained",path:"/security",find:"at least two model families",replacement:"at least three model families",
     expected:["how_review_works_states_only_what_the_review_records_hold"]},
    {name:"hide_that_a_first_release_reviewer_shared_the_authors_model_family",scenario:"review_explained",path:"/security",
     find:" One of those reviewers came from the same model family as the model that wrote the items.",replacement:"",expected:["how_review_works_states_only_what_the_review_records_hold"]},
    {name:"leave_new_vetted_additions_unexplained",scenario:"review_explained",path:"/pricing",
     find:'<a href="/security#how-review-works" data-page="security" id="pricing-review-link">pass review</a>',replacement:"pass review",expected:["pricing_links_new_vetted_additions_to_how_review_works"]},
    {name:"print_the_pi_extension_path_as_plain_text",scenario:"pi_extension",path:"/assets/service.js",find:"const target = $(\"client-configuration-note\"), found = note.match(servedFile);",
     replacement:"const target = $(\"client-configuration-note\"), found = null;",expected:["the_pi_extension_path_is_a_link_with_a_copy_action"]},
    {name:"copy_only_the_path_of_the_pi_extension",scenario:"pi_extension",path:"/assets/service.js",find:"$(\"client-file-address\").textContent = location.origin + found[0];",
     replacement:"$(\"client-file-address\").textContent = found[0];",expected:["the_pi_extension_path_is_a_link_with_a_copy_action"]},
    {name:"never_say_whether_the_phone_menu_is_open",scenario:"phone_menu",path:"/assets/service.js",find:'menuButton.setAttribute("aria-expanded", String(open)); ',replacement:"",
     expected:["phone_menu_is_one_named_button_that_states_whether_it_is_open_on_every_page"]},
    {name:"hide_the_phone_menu_button_from_assistive_technology",scenario:"phone_menu",path:"/pricing",find:'aria-label="Menu" aria-expanded="false"',replacement:'aria-hidden="true" aria-expanded="false"',
     expected:["phone_menu_is_one_named_button_that_states_whether_it_is_open_on_every_page"]},
    {name:"let_confirm_run_before_the_sign_in_settings_load",scenario:"confirm_wait",path:"/assets/service.js",find:'$("confirm-button").disabled = !identityClient; $("confirm-loading").hidden = Boolean(identityClient);',replacement:'$("confirm-button").disabled = false; $("confirm-loading").hidden = true;',expected:["the_confirm_button_waits_for_the_sign_in_settings"]},
    {name:"offer_no_checkout_to_an_account_without_paid_access",scenario:"unpaid",path:"/assets/service.js",find:"$(\"funnel-subscribe\").hidden = !plan.subscribe;",replacement:"$(\"funnel-subscribe\").hidden = true;",expected:["get_started_funnel_offers_checkout_to_an_account_without_paid_access"]}];
  for(const control of journeyControls){
    const failed=new Set(),note=(name,passed)=>{if(passed!==true)failed.add(name);};
    let problem="";const tracker={applied:false},mutation={path:control.path,find:control.find,replacement:control.replacement};
    const {context:opened,page:target}=await openJourney(mutation,undefined,tracker);
    try{await journeyScenarios[control.scenario](target,note,mutation,tracker);}catch(error){problem=safeError(error);}
    await opened.close();
    const applied=tracker.applied,missed=control.expected.filter(name=>!failed.has(name)),detected=applied&&!problem&&missed.length===0;
    mutants.push({name:control.name,applied,detected,required_checks:control.expected,missed_checks:missed,failed_checks:[...failed].sort(),...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+control.name,detected,{applied,missed_checks:missed,...(problem?{problem}:{})});
  }
  await runSignupSessionBoundaries(browser,fixture,check);
  for(const [name,expected] of [["omit_invalidation",["a_stale_confirmation_never_changes_the_new_sessions_password"]],
    ["omit_async_guards",["disconnect_during_verify_never_reactivates_the_page","disconnect_during_password_never_reactivates_the_page"]]]){
    const failed=[];const {mutationApplied}=await runSignupSessionBoundaries(browser,fixture,(name,passed)=>{if(!passed)failed.push(name);},name);
    const detected=mutationApplied&&expected.every(name=>failed.includes(name));
    mutants.push({name:"signup_session_"+name,applied:mutationApplied,detected,required_checks:expected,failed_checks:failed,missed_checks:expected.filter(name=>!failed.includes(name))});
    check("signup_session_guard_removal_detected_"+name,detected,{failed});
  }
  /* The request list is offered only where the service keeps one. The first service keeps none; the account service keeps one.
     Since September 23, 2026 the list has no page of its own: /waitlist opens the Get started funnel as an older address, the
     funnel's one form takes the address, the header's one primary action, "Get started", leads there, and the guide's lead links
     to Get started. The form's own journey, the request, the record and the second request, is checked in the funnel above. */
  await page.setViewportSize({width:1440,height:1000});
  const funnelAt=target=>target.evaluate(()=>({path:location.pathname,views:[...document.querySelectorAll("[data-view]")].filter(item=>!item.hidden).map(item=>item.dataset.view),title:document.title,
    state:document.getElementById("funnel")?.dataset.funnelState||"",field:Boolean(document.getElementById("funnel-email")?.getClientRects().length),
    oldForm:Boolean(document.getElementById("waitlist-form")?.getClientRects().length)}));
  const opensTheFunnel=(state,path,withField)=>state.path===path&&JSON.stringify(state.views)===JSON.stringify(["start"])&&state.title.endsWith("| Get started")&&state.field===withField
    &&state.state===(withField?"register":"invite")&&!state.oldForm;
  await page.goto(fixture.base+"/waitlist"); await page.waitForFunction(()=>document.querySelector("#service-status")?.textContent!=="Checking service availability");
  const closedList=await funnelAt(page);
  check("a_service_without_a_request_list_takes_no_address_at_the_older_address",opensTheFunnel(closedList,"/waitlist",false)&&await page.locator("#waitlist-discount").isHidden(),closedList);
  await page.goto(fixture.base+"/signup");
  check("a_service_without_a_waiting_list_does_not_offer_it_on_the_registration_page",await page.locator("#signup-waitlist-link").isHidden());
  await page.goto(fixture.account_base+"/pricing"); await page.waitForFunction(()=>document.querySelector("#service-status").textContent==="Service available");
  await page.locator("#header-primary").click();
  await page.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:10000}).catch(()=>{});
  const fromHeader=await funnelAt(page);
  check("a_service_with_a_request_list_opens_the_account_form_from_the_header",opensTheFunnel(fromHeader,accessPaths.closed,true),fromHeader);
  await openGuide(page);
  const getStartedLead=await startLead(page);
  check("the_guide_links_to_get_started_when_the_service_keeps_a_list",sameLead(getStartedLead,"invite")&&await page.locator("#start-invite-link").getAttribute("href")===accessPaths.closed,getStartedLead);
  await page.goto(fixture.account_base+"/waitlist"); await page.waitForFunction(()=>document.getElementById("funnel")?.dataset.funnelState==="register",null,{timeout:10000}).catch(()=>{});
  const waitlistAddressState=await funnelAt(page);
  check("the_waiting_list_address_opens_the_get_started_funnel_with_its_form",opensTheFunnel(waitlistAddressState,"/waitlist",true),waitlistAddressState);
  {
    /* The removed-guard control: the page script routes /waitlist back to the old waiting list page. */
    let applied=false,problem="",opens=true;
    try{const opened=await context.newPage();opened.on("pageerror",()=>{});
      await opened.route(assetRoute("/assets/service.js",fixture.account_base),async route=>{const response=await route.fetch(),source=await response.text(),changed=source.split('"/waitlist":"start"').join('"/waitlist":"waitlist"');applied=changed!==source;await route.fulfill({response,body:changed});});
      await opened.goto(fixture.account_base+"/waitlist");await opened.waitForFunction(()=>document.querySelector("#service-status")?.textContent==="Service available");
      opens=opensTheFunnel(await funnelAt(opened),"/waitlist",true);await opened.close();}catch(error){problem=safeError(error);}
    const detected=applied&&!problem&&!opens,name="send_the_waiting_list_address_back_to_its_old_page",required=["the_waiting_list_address_opens_the_get_started_funnel_with_its_form"];
    mutants.push({name,applied,detected,required_checks:required,missed_checks:opens?required:[],failed_checks:opens?[]:required,...(problem?{problem}:{})});
    check("removed_guard_is_detected_"+name,detected,{applied,...(problem?{problem}:{})});
  }
  check("older_address_check_rejects_the_old_page_the_guide_and_a_funnel_without_its_form",!opensTheFunnel({...waitlistAddressState,views:["waitlist"]},"/waitlist",true)
    &&!opensTheFunnel({...waitlistAddressState,views:["setup"],title:"Baltor | Get set up"},"/waitlist",true)&&!opensTheFunnel({...waitlistAddressState,field:false,state:"invite"},"/waitlist",true)
    &&!opensTheFunnel({...waitlistAddressState,oldForm:true},"/waitlist",true)&&opensTheFunnel(waitlistAddressState,"/waitlist",true));
  check("the_discount_is_named_only_where_checkout_takes_a_code",await page.locator("#waitlist-discount").isHidden(),{discount_code:(await (await page.request.get(fixture.account_base+"/api/v1/capabilities")).json()).result.billing.discount_code});
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
  const internalReference=value=>{try{const url=new URL(value,fixture.browse_base);return value.startsWith("/")&&url.origin===fixture.browse_base&&!url.username&&!url.password?url.pathname+url.search:null;}catch(_){return null;}};
  const internalAddresses=text=>[...new Set([...text.matchAll(/(?:href|src)="([^\"]+)"/g)].map(found=>internalReference(found[1])).filter(Boolean))]
    .filter(value=>!value.startsWith("/api/")&&!value.startsWith("/.well-known/")&&value!=="/mcp");
  const servedPage=await plainContext.request.get(fixture.browse_base+"/app");
  const pageText=servedPage.status()===200?await servedPage.text():"";
  const namedScripts=[...new Set([...pageText.matchAll(/src="([^\"]+)"/g)].map(found=>internalReference(found[1])).filter(Boolean).map(value=>new URL(value,fixture.browse_base).pathname))];
  const namedAssets=[...pageText.matchAll(/(?:href|src)="([^\"]+)"/g)].map(found=>found[1]).filter(value=>{try{return new URL(value,fixture.browse_base).pathname.startsWith("/assets/");}catch(_){return false;}});
  check("served_page_asset_versions_bind_to_exact_packaged_bytes",namedAssets.length>0&&namedAssets.every(value=>sameOriginAsset(value,fixture.browse_base,new URL(value,fixture.browse_base).pathname)),{assets:namedAssets});
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
      await signOutFromHeader(opened);
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
      await signOutFromHeader(opened);
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
  /* The pages of September 24, 2026 and the page each hostname shows at its root, in tools/showcase_page_checks.mjs. */
  await runShowcasePageChecks({root,python:process.env.PYTHON||resolve(root,".venv/bin/python"),browser,context,fixture,check,mutants,output,safeError,localOnly,
    words:{retiredAccessWords,invitationWords,publicVocabulary}});
  /* The directory page at /directory: tools/directory_browser_checks.mjs holds its checks and their removed-guard controls. */
  directoryResult=await runDirectoryChecks({browser,base:fixture.base,check,mutants,errors,localOnly,screenshot:suffix=>output.replace(/\.json$/,suffix)});
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
const paths=[...['http.py','records.py','access.py','access_checks.py','http_entrypoint.py','runtime.py','browser_identity.py','browser_identity_checks.py','account_email.py','account_email_checks.py'].map(name=>"src/loop_engine/core/service_runtime/"+name),...['index.html','service.css','service.js','client-access.js','catalogue-browser.js','architecture-story.js','architecture.css','client-recipes.json','directory.html','directory.css','directory.js'].map(name=>"src/loop_engine/core/service_runtime/web_assets/"+name)];
/* Version 2 of this report carries the removed-guard controls, and all_passed is true only when every check passed and every control was detected. Version 1 had neither. */
const result={record_type:"service_workspace_browser_checks/v2",scope:"real browser and loopback service; provider fixtures only; every page asset is served by the service",external_provider_calls:0,
  /* What the check supplied instead of the running system, named on the face of the report. Offered,
     fetched, loaded and used are separate facts, and so is substituted. */
  harness_substitutions:["a removed-guard control answers /assets/catalogue-browser.js with changed bytes, in memory, for that control run only",
    "the held download checks wrap crypto.subtle.digest in the page so one measurement can be held, which puts the sign-out inside the window the guard defends",
    "the sign-up journey's identity project is the stand-in from account_email_checks.py on a loopback socket, and its mail provider is the same stand-in's outbox"],
  directory:directoryResult,checks,passed:checks.filter(x=>x.passed).length,total:checks.length,mutants,mutants_detected:mutants.filter(x=>x.detected).length,all_passed:checks.every(x=>x.passed)&&mutants.every(x=>x.detected),source_sha256:Object.fromEntries(paths.map(path=>[path,createHash("sha256").update(readFileSync(resolve(root,path))).digest("hex")]))};
writeFileSync(output,JSON.stringify(result,null,2)+"\n",{flag:"wx"}); console.log(JSON.stringify({passed:result.passed,total:result.total,mutants_detected:result.mutants_detected,mutants:mutants.length,all_passed:result.all_passed,failures:checks.filter(x=>!x.passed),output})); process.exitCode=result.all_passed?0:1;
