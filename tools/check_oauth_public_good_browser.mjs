/* Real local service and browser; synthetic identity provider only. No production credentials or external calls. */
import {chromium} from '../showcase/node_modules/playwright-core/index.mjs';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {existsSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,dirname} from 'node:path';
const root=resolve(new URL('..',import.meta.url).pathname), output=resolve(process.argv[2]||'artifacts/oauth-public-good-browser.json');
if(existsSync(output))throw new Error('Evidence already exists');
mkdirSync(dirname(output),{recursive:true});
const checks=[],errors=[],screenshots=[],blocked=[];
const check=(name,passed,detail={})=>{checks.push({name,passed:passed===true,detail});if(!passed)throw new Error(name);};
const boot=`import json,sys
from dataclasses import replace
from test_oauth_http import HttpOAuthIntegration
from loop_engine.core.service_runtime.public_good import PublicGoodGrant
case=HttpOAuthIntegration()
case.setUp()
try:
    binding=case.fixture.provisioning
    view=replace(binding.current_view(),item_versions={'skill.alpha':'a'*64})
    binding.install_view(view)
    selected=case.fixture.bindings['skill.alpha']
    grant=PublicGoodGrant(selected,'a'*64,view.qualification_resolver.resolve(selected).approval_ref,'synthetic-rights',(4,),'Synthetic learning fixture',int(__import__('time').time())+3600)
    binding.public_good.configure(view,(grant,))
    print(json.dumps({'base':case.base,'identity':case.identity_base,'token':case.browser_token,'pending':case.pending(),'second':case.pending(),'callback':case.callback}),flush=True)
    sys.stdin.readline()
finally:
    case.stack.close()
`;
let child,browser;
try{
 child=spawn(resolve(root,'.venv/bin/python'),['-u','-c',boot],{cwd:root,env:{...process.env,PYTHONPATH:'src:tools'},stdio:['pipe','pipe','pipe']});
 const fixture=await new Promise((accept,reject)=>{const lines=createInterface({input:child.stdout}),timer=setTimeout(()=>reject(new Error('fixture startup deadline')),20000);
  lines.once('line',line=>{clearTimeout(timer);accept(JSON.parse(line));});child.once('exit',code=>reject(new Error('fixture stopped '+code)));});
 const base=fixture.base;
 browser=await chromium.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:900}});
 let decisions=0, bodyReads=0, callback='';
 await context.route('**/*',async route=>{
  const request=route.request(),url=new URL(request.url());
  if(url.origin===base){if(url.pathname==='/api/v1/oauth/consent'&&request.method()==='POST')decisions++;
   if(url.pathname==='/api/v1/download')bodyReads++;return route.continue();}
  if(url.origin===fixture.identity&&url.pathname==='/auth/v1/token'&&request.method()==='POST')return route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({
   access_token:fixture.token,token_type:'bearer',expires_in:1800,refresh_token:'synthetic-unused-refresh',user:{id:'synthetic-oauth-user',email:'synthetic@example.invalid'}})});
  if(url.origin+url.pathname===fixture.callback){callback=url.href;return route.fulfill({status:200,contentType:'text/html',body:'<h1>Synthetic app callback</h1>'});}
  blocked.push(url.origin+url.pathname);return route.abort();
 });
 const page=await context.newPage();page.on('pageerror',error=>errors.push(String(error)));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900});await page.goto(base+'/public-good');
  await page.waitForSelector('.pg-item');
  check('public_good_'+width+'_no_horizontal_overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  check('public_good_'+width+'_seventeen_goals',await page.locator('#public-good-goal option').count()===19);
  check('public_good_'+width+'_main_header_link',await page.locator('header a[href="/public-good"]').count()===1);
  const file=output.replace(/\.json$/,`-public-good-${width}.png`);await page.screenshot({path:file,fullPage:true});screenshots.push(file);
 }
 await page.selectOption('#public-good-goal','1');await page.waitForFunction(()=>document.getElementById('public-good-status').textContent.startsWith('No published'));
 check('empty_goal_is_honest',await page.locator('.pg-item').count()===0);
 await page.selectOption('#public-good-goal','4');await page.waitForSelector('.pg-item');
 await page.fill('#public-good-query','not-present-fixture');await page.locator('#public-good-filters button').click();
 await page.waitForFunction(()=>document.getElementById('public-good-status').textContent.startsWith('No published'));
 check('query_filters_metadata',await page.locator('.pg-item').count()===0);
 await page.goto(base+'/oauth/consent?authorization_id='+fixture.pending);
 await page.waitForFunction(()=>!document.getElementById('oauth-sign-in').hidden);
 check('signed_out_needs_sign_in_without_auto_consent',decisions===0);
 await page.locator('#oauth-sign-in').click();
 check('sign_in_preserves_authorization_intent',new URL(page.url()).searchParams.get('oauth_authorization_id')===fixture.pending);
 await page.waitForFunction(()=>!document.getElementById('email-login').hidden&&!document.getElementById('email-login-button').disabled);
 await page.fill('#login-email','synthetic@example.invalid');await page.fill('#login-password','synthetic-password-not-a-real-secret');await page.locator('#email-login-button').click();
 await page.waitForFunction(()=>location.pathname==='/oauth/consent'&&!document.getElementById('oauth-approve').disabled);
 check('normal_sign_in_resumes_consent_without_api_key',decisions===0&&await page.locator('#oauth-client-name').textContent()==='Synthetic QA client');
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:900});check('consent_'+width+'_no_overflow',await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  const file=output.replace(/\.json$/,`-consent-${width}.png`);await page.screenshot({path:file,fullPage:false});screenshots.push(file);
 }
 await page.locator('#oauth-approve').click();await page.waitForSelector('h1:text("Synthetic app callback")');
 check('explicit_consent_returns_code_once',decisions===1&&new URL(callback).searchParams.has('code')&&!callback.includes(fixture.token));
 await page.goto(base+'/oauth/consent?authorization_id='+fixture.second);await page.waitForFunction(()=>!document.getElementById('oauth-deny').disabled);
 await page.locator('#oauth-deny').click();await page.waitForSelector('h1:text("Synthetic app callback")');
 check('explicit_denial_returns_only_denial',decisions===2&&new URL(callback).searchParams.get('error')==='access_denied'&&!new URL(callback).searchParams.has('code'));
 await page.goto(base+'/public-good');await page.waitForSelector('.pg-item');await page.locator('.pg-item a').click();
 await page.waitForFunction(()=>document.getElementById('browse-detail').textContent.includes('skill.alpha'));
 await page.waitForSelector('#browse-download');
 check('public_good_card_opens_exact_component_without_auto_download',bodyReads===0&&new URL(page.url()).searchParams.get('component')==='skill.alpha');
 check('unpaid_account_can_choose_free_download',await page.locator('#browse-download').isEnabled());
 const download=page.waitForEvent('download');await page.locator('#browse-download').click();await download;
 check('explicit_free_download_completes',bodyReads===1);
 check('no_browser_errors',errors.length===0,{errors});check('no_unexpected_network',blocked.length===0,{blocked});
}catch(error){checks.push({name:'completed_browser_sequence',passed:false,detail:{message:String(error)}});}
finally{if(browser)await browser.close();if(child){child.stdin.end('\n');await new Promise(done=>child.once('exit',done));}
 writeFileSync(output,JSON.stringify({record_type:'oauth_public_good_browser_check/v1',all_passed:checks.every(check=>check.passed),checks,errors,blocked,screenshots,limits:['Synthetic identity provider; production and real ChatGPT connections are separate checks.']},null,2)+'\n');}
console.log(JSON.stringify({all_passed:checks.every(check=>check.passed),checks:checks.length,output}));
if(checks.some(check=>!check.passed))process.exitCode=1;
