/* Local real HTTP rendering/profile export; account-provider responses are explicit UI fixtures. */
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {mkdirSync,existsSync,writeFileSync,readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {chromium} from '../showcase/node_modules/playwright-core/index.mjs';
const root=resolve(new URL('..',import.meta.url).pathname),output=resolve(process.argv[2]||'');
if(!process.argv[2]||existsSync(output))throw Error('Use a new evidence directory');mkdirSync(output,{recursive:true});
const checks=[],errors=[];const check=(name,passed,detail={})=>checks.push({name,passed:Boolean(passed),detail});
const program=`from pathlib import Path
from tempfile import TemporaryDirectory
from dataclasses import replace
import json,sys
from loop_engine.core.service_runtime.brand_profiles import ServiceBrandProfile
from loop_engine.core.service_runtime.catalogue_release_checks import Fixture
from loop_engine.core.service_runtime.http_test_fixtures import running_http
from loop_engine.core.service_runtime.http import ServiceHttpApplication
origin='https://agentfeeds.example.test'
with TemporaryDirectory(prefix='agentfeeds-browser-') as folder:
    case=Fixture(Path(folder));case.publish([case.line('private_fixture_body','PRIVATE BODY REMAINS PRIVATE')])
    fixture=type('Served',(),{'runtime':case.runtime,'provisioning':case.binding()})()
    def application(config):
        config=replace(config,allowed_hosts=(*config.allowed_hosts,'agentfeeds.example.test'),
            allowed_origins=(*config.allowed_origins,origin),brand_profiles=(ServiceBrandProfile('agentfeeds',origin),))
        return ServiceHttpApplication(case.runtime,fixture.provisioning,config)
    with running_http(fixture,application_factory=application) as (base,service):
        print(json.dumps({'transport':base,'base':origin}),flush=True);sys.stdin.readline()
`;
let child,browser;
try{
 child=spawn(process.env.PYTHON||'python3',['-u','-c',program],{cwd:root,env:{...process.env,PYTHONPATH:resolve(root,'src'),PYTHONDONTWRITEBYTECODE:'1'},stdio:['pipe','pipe','pipe']});
 let stderr='';child.stderr.on('data',part=>{stderr+=part;});
 const {base,transport}=await new Promise((done,fail)=>{const lines=createInterface({input:child.stdout}),timer=setTimeout(()=>fail(Error('Fixture timeout '+stderr)),30000);lines.once('line',line=>{clearTimeout(timer);lines.close();done(JSON.parse(line));});child.once('exit',code=>{clearTimeout(timer);fail(Error('Fixture exited '+code+' '+stderr));});});
 // Route only the socket destination to loopback. Real Host/Origin dispatch,
 // HTTP responses, CSP and source/profile operations remain under the service.
 // TLS itself is verified separately against the deployed hostname.
 const serviceRoute=async route=>{
  const request=route.request(),url=new URL(request.url());if(url.origin!==base)return route.abort();
  const response=await route.fetch({url:transport+url.pathname+url.search,headers:{...request.headers(),host:url.host},maxRedirects:0});
  if(url.pathname==='/api/v1/feeds/profile'){
   let envelope;try{envelope=await response.json();}catch{}
   check('profile HTTP response',response.status()===200,{status:response.status(),code:envelope?.error?.code||null,origin:request.headers().origin||null});
  }
  return route.fulfill({response});
 };
 browser=await chromium.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox']});
 for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
  const context=await browser.newContext({viewport,acceptDownloads:true,reducedMotion:'reduce'});
  await context.route('**/*',serviceRoute);
  const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
  for(const path of ['/','/collections','/collections/coding-benchmarks','/build','/connect','/pricing','/help','/privacy','/terms','/login','/oauth/consent']){
   const response=await page.goto(base+path);await page.locator('h1').waitFor();
   check('page '+path+' '+viewport.width,response.status()===200&&await page.locator('h1:visible').count()===1);
   check('brand canonical '+path+' '+viewport.width,await page.locator('link[rel=canonical]').getAttribute('href')===base+path);
   check('no overflow '+path+' '+viewport.width,await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
   check('independent navigation '+path+' '+viewport.width,await page.locator('header a,footer a').evaluateAll(links=>links.every(link=>!['baltor.ai','www.baltor.ai'].includes(new URL(link.href).hostname)&&!['/library','/gallery','/overnight'].includes(new URL(link.href).pathname))));
   if(['/', '/build','/collections','/login'].includes(path))await page.screenshot({path:resolve(output,(path==='/'?'home':path.slice(1))+'-'+viewport.width+'.png'),fullPage:true});
  }
  await page.goto(base+'/collections/coding-benchmarks');
  const formats=await page.evaluate(async()=>{
   const results=[];
   for(const suffix of ['md','json','rss']){
    const path='/feeds/collections/coding-benchmarks.'+suffix,response=await fetch(path),body=await response.text(),etag=response.headers.get('etag');
    const unchanged=await fetch(path,{headers:{'If-None-Match':etag}});
    const valid=suffix==='json'?JSON.parse(body).items.length===2:suffix==='rss'?(()=>{const doc=new DOMParser().parseFromString(body,'application/xml');return !doc.querySelector('parsererror')&&doc.querySelectorAll('item').length===2;})():body.includes('SWE-bench');
    results.push({suffix,status:response.status,conditional:unchanged.status,valid,etag:Boolean(etag)});
   }
   return results;
  });
  for(const format of formats)check('real collection '+format.suffix+' '+viewport.width,format.status===200&&format.conditional===304&&format.valid&&format.etag,format);
  check('RSS link exposed '+viewport.width,await page.getByRole('link',{name:'Read RSS',exact:true}).count()===1);
  const notices=await page.evaluate(async()=>{const response=await fetch('/assets/third-party-notices.txt');return {status:response.status,body:(await response.text()).length};});
  check('required third-party notices '+viewport.width,notices.status===200&&notices.body>0,notices);
  await page.goto(base+'/collections');await page.locator('#collection-search').fill('no-such-topic');check('empty collection state '+viewport.width,await page.locator('#collection-empty').isVisible());
  await page.locator('#collection-search').fill('coding');check('collection search '+viewport.width,await page.locator('[data-collection]:visible').count()>0);
  if(viewport.width===390){await page.locator('.menu-button').click();check('phone menu expanded',await page.locator('.menu-button').getAttribute('aria-expanded')==='true');await page.keyboard.press('Escape');check('escape restores menu focus',await page.locator('.menu-button').evaluate(node=>document.activeElement===node&&node.getAttribute('aria-expanded')==='false'));}
  await page.goto(base+'/build?collection=coding-benchmarks');
  check('detail preselects existing collection '+viewport.width,await page.locator('[name=collection_ids][value=coding-benchmarks]').isChecked());
  await page.locator('[data-choice-search]').first().fill('finance');
  check('filter retains selected hidden source '+viewport.width,await page.locator('[name=collection_ids][value=coding-benchmarks]').isChecked()&&await page.locator('[name=collection_ids][value=coding-benchmarks]').isHidden());
  await page.locator('[data-choice-search]').first().fill('');
  await page.locator('[name=agent_label]').fill('Coding reviewer');await page.getByRole('button',{name:'Build reading profile',exact:true}).click();
  try{await page.locator('#feed-profile-downloads a').first().waitFor({timeout:10000});}
  catch(error){throw Error('Profile download failed: '+await page.locator('#feed-profile-status').innerText()+'; '+error.message);}
  for(const name of ['profile.json','READING.md']){const waiting=page.waitForEvent('download');await page.locator('#feed-profile-downloads a[download="'+name+'"]').click();const file=await waiting;const text=readFileSync(await file.path(),'utf8');check('real exact profile '+name+' '+viewport.width,text.length>10&&text.includes('Coding reviewer'));}
  await page.locator('[name=agent_label]').fill('Changed agent');check('edit invalidates download '+viewport.width,await page.locator('#feed-profile-downloads').isHidden());
  await page.route('**/api/v1/feeds/profile',route=>route.fulfill({status:503,contentType:'application/json',body:'{}'}));
  await page.getByRole('button',{name:'Build reading profile',exact:true}).click();await page.waitForFunction(()=>document.querySelector('#feed-profile-status').textContent.includes('could not'));
  check('failure retains selection '+viewport.width,await page.locator('[name=agent_label]').inputValue()==='Changed agent'&&await page.locator('[name=collection_ids][value=coding-benchmarks]').isChecked());
  await context.close();
 }
 const account=await browser.newContext();await account.route('**/*',serviceRoute);
 const actions=[];let confirmCalls=0;
 const access='fixture.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+3600})).toString('base64url')+'.signature';
 const settings={record_type:'browser_identity_public_configuration/v1',provider_profile:'supabase_user/v1',publishable_key:['sb','publishable','fixture'].join('_'),project_url:'https://identity.invalid',registration_enabled:true,email_signup_enabled:true,signup_available:true,recovery_available:true,minimum_password_length:12};
 await account.route('**/assets/supabase-client.js*',route=>route.fulfill({contentType:'text/javascript',body:`window.BaltorIdentitySdk={createClient:()=>({auth:{signInWithPassword:async()=>({data:{session:{access_token:${JSON.stringify(access)}}}}),verifyOtp:async()=>{window.confirmCalls=(window.confirmCalls||0)+1;return {data:{session:{access_token:${JSON.stringify(access)}},user:{email:'reader@example.invalid'}}}},updateUser:async()=>({data:{},error:null}),signOut:async()=>({error:null})}})};`}));
 await account.route('**/api/v1/**',route=>{const path=new URL(route.request().url()).pathname;let body={};try{body=route.request().postDataJSON()||{};}catch{}actions.push({path,body,authorized:Boolean(route.request().headers().authorization)});
  let result=settings,status=200;
  if(path.endsWith('/signup')){result={record_type:'service_account_signup_result/v1',status:'confirmation_sent'};status=202;}
  else if(path.endsWith('/recovery')){result={record_type:'service_account_recovery_result/v1',status:'recovery_sent'};status=202;}
  else if(path.endsWith('/activate'))result={record_type:'service_account_activation/v1',tenant_id:'fixture-account'};
  else if(path.endsWith('/session'))result={record_type:'service_session/v1',authentication_mode:'browser_identity',principal:{tenant_id:'fixture-account'}};
  else if(path.endsWith('/logout'))result={record_type:'service_browser_logout_result/v1',committed:true,revoked:true};
  return route.fulfill({status,contentType:'application/json',body:JSON.stringify({result})});});
 const page=await account.newPage();page.on('pageerror',error=>errors.push(error.message));
 await page.goto(base+'/get-started');await page.waitForFunction(()=>!document.querySelector('form button').disabled);await page.locator('[name=email]').fill('reader@example.invalid');await page.locator('form button').click();await page.waitForFunction(()=>document.querySelector('[data-account-status]').textContent.includes('Check your email'));
 check('email-first exact signup',actions.some(row=>row.path.endsWith('/signup')&&JSON.stringify(Object.keys(row.body).sort())==='["email","record_type"]'&&row.body.record_type==='service_account_signup_request/v2'&&!row.authorized));
 await page.goto(base+'/auth/confirm?token_hash=fixture_confirmation&type=signup');await page.waitForFunction(()=>!document.querySelector('form button').disabled);
 check('confirmation token scrubbed before interaction',page.url()===base+'/auth/confirm'&&await page.evaluate(()=>!window.confirmCalls));
 await page.locator('[name=password]').fill('a good long fixture password');await page.locator('[name=again]').fill('a good long fixture password');await page.locator('form button').click();await page.waitForURL('**/account');await page.waitForFunction(()=>document.querySelector('[data-account-details]')?.hidden===false);
 check('confirmation activates and opens same account',actions.some(row=>row.path.endsWith('/activate')&&row.authorized)&&await page.locator('[data-account-facts]').innerText().then(text=>text.includes('fixture-account')));
 await page.locator('[data-signout]').click();await page.waitForFunction(()=>document.querySelector('[data-account-status]').textContent==='Signed out.');
 check('signout clears tab token',await page.evaluate(()=>sessionStorage.getItem('agentfeeds.identity-session')===null));
 await page.goto(base+'/auth/confirm?token_hash=one&token_hash=two&type=signup');await page.waitForFunction(()=>document.querySelector('[data-account-status]').textContent.includes('invalid'));
 check('ambiguous confirmation refused',await page.locator('form button').isDisabled());
 const id='boar_'+'a'.repeat(43);await page.goto(base+'/oauth/consent?authorization_id='+id);await page.waitForFunction(()=>document.querySelector('#oauth-consent-status').textContent.includes('Sign in'));
 check('consent controller has AgentFeeds name',!(await page.locator('#oauth-consent-status').innerText()).includes('Baltor')&&(await page.locator('#oauth-consent-status').innerText()).includes('AgentFeeds'));
 await page.evaluate(()=>window.BaltorOAuthConsent.create({request:()=>{},browserSignedIn:()=>false,signIn:()=>{},epoch:()=>0}).show());
 check('existing consent caller retains Baltor default',(await page.locator('#oauth-consent-status').innerText()).includes('Baltor'));
 await page.locator('#oauth-sign-in').click();await page.waitForURL('**/login?oauth_authorization_id=*');check('consent return keeps only valid id',new URL(page.url()).searchParams.get('oauth_authorization_id')===id);
 await page.route('**/api/v1/session',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({result:{record_type:'wrong/v1',authentication_mode:'browser_identity',principal:{tenant_id:'wrong-account'}}})}));
 await page.waitForFunction(()=>!document.querySelector('form[data-account-form=login] button').disabled);
 await page.locator('form[data-account-form=login] [name=email]').fill('reader@example.invalid');await page.locator('[name=password]').fill('fixture password');await page.locator('form[data-account-form=login] button').click();
 await page.waitForFunction(()=>document.querySelector('[data-account-status]').textContent.includes('could not be verified'));
 check('wrong session contract cannot persist or open account',await page.evaluate(()=>sessionStorage.getItem('agentfeeds.identity-session')===null)&&new URL(page.url()).pathname==='/login');
 await account.close();check('no browser errors',errors.length===0,{errors});
}catch(error){errors.push(String(error));check('journey completed',false,{error:String(error)});}
finally{if(browser)await browser.close();if(child){child.stdin.end('\n');await new Promise(done=>{if(child.exitCode!==null)return done();const timer=setTimeout(()=>{child.kill('SIGTERM');done();},5000);child.once('exit',()=>{clearTimeout(timer);done();});});}
 const report={record_type:'agentfeeds_browser_checks/v1',checks,errors,passed:checks.length>0&&checks.every(row=>row.passed)&&!errors.length,scope:'Real selected-brand Host/Origin HTTP dispatch, renderer, assets, CSP and profile operations over a loopback socket. TLS is not tested locally. Provider/account responses are UI fixtures, not a live signup or deployment.'};writeFileSync(resolve(output,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({passed:report.passed,checks:checks.length,failed:checks.filter(row=>!row.passed),output}));process.exitCode=report.passed?0:1;}
