/* Local prototype qualification; no internet, accounts, uploads or backend. */
import {spawn} from 'node:child_process';
import {createHash} from 'node:crypto';
import {existsSync,mkdirSync,readFileSync,writeFileSync} from 'node:fs';
import {dirname,resolve} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=dirname(fileURLToPath(import.meta.url)),modulePath=process.argv[2],output=process.argv[3];
if(!modulePath||!output||existsSync(output))throw Error('Use an installed Playwright module and new evidence directory');
const {chromium}=await import(pathToFileURL(resolve(modulePath)).href);
mkdirSync(output,{recursive:true,mode:0o700});
const source=Object.fromEntries(['index.html','styles.css','app.js','serve_preview.py'].map(name=>[name,createHash('sha256').update(readFileSync(resolve(root,name))).digest('hex')]));
const report={record_type:'agentbriefs_local_design_check/v1',started_at:new Date().toISOString(),source,checks:[],errors:[],requests:[],unexpected_requests:[],views:[],scope:'Loopback only; synthetic fixtures, in-memory interactions, actual native Chromium. No accounts, provider requests, public hosting or backend qualification.'};
const check=(name,passed,details={})=>report.checks.push({name,passed:passed===true,details});
const server=spawn('/usr/bin/python3',[resolve(root,'serve_preview.py'),'--port','0'],{cwd:root,stdio:['ignore','pipe','pipe']});
let browser;
const deadline=setTimeout(()=>{report.errors.push({phase:'deadline',message:'120-second check ceiling'});browser?.close();server.kill('SIGTERM');},120000);
try{
 const origin=await new Promise((yes,no)=>{let value='';server.stdout.on('data',data=>{value+=data;if(value.includes('\n')){const address=value.trim();if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(address))no(Error('Unexpected preview address'));else yes(address);}});server.once('error',no);server.once('exit',code=>no(Error('Preview exited '+code)));setTimeout(()=>no(Error('Preview readiness timeout')),10000).unref();});
 report.origin=origin;
 const sourceJs=readFileSync(resolve(root,'app.js'),'utf8');
 check('app has no network or persistent-storage API',!/(fetch\s*\(|XMLHttpRequest|WebSocket|sendBeacon|localStorage|sessionStorage|indexedDB|\.cookie\s*=|serviceWorker)/.test(sourceJs));
 check('app uses no HTML injection sink',!/(innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\s*\(|new Function)/.test(sourceJs));
 browser=await chromium.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox']});
 for(const viewport of [{width:1440,height:1000},{width:820,height:1000},{width:390,height:844}]){
  const context=await browser.newContext({viewport,reducedMotion:'reduce',colorScheme:'light',serviceWorkers:'block'});
  await context.route('**/*',route=>{const req=route.request(),url=new URL(req.url());report.requests.push({method:req.method(),url:req.url()});
   if(url.origin!==origin||!['GET','HEAD'].includes(req.method())||!['/','/index.html','/styles.css','/app.js','/favicon.ico'].includes(url.pathname)){report.unexpected_requests.push({method:req.method(),url:req.url()});return route.abort();}return route.continue();});
  const page=await context.newPage();page.on('pageerror',error=>report.errors.push({width:viewport.width,message:error.message}));
  const response=await page.goto(origin,{waitUntil:'networkidle'});
  async function navigate(name){await page.locator('[data-nav="'+name+'"]').click();await page.locator('[data-view="'+name+'"]').waitFor({state:'visible'});}
  check('served prototype '+viewport.width,response?.status()===200&&response.headers()['content-security-policy'].includes("connect-src 'none'")&&response.headers()['content-security-policy'].includes("form-action 'none'"));
  for(const name of ['overview','company','brief','evidence','decisions']){
   await navigate(name);
   const state=await page.evaluate(()=>{
    const visible=node=>node.getClientRects().length>0;
    const view=document.querySelector('[data-view]:not([hidden])');
    const labels=[...view.querySelectorAll('input,select,textarea')].filter(visible).every(node=>node.labels?.length>0);
    const targets=[...document.querySelectorAll('button,nav a,input,select,textarea')].filter(visible).map(node=>({name:node.textContent?.trim().slice(0,60)||node.id,width:node.getBoundingClientRect().width,height:node.getBoundingClientRect().height}));
    function rgb(value){const m=value.match(/rgba?\(([^)]+)\)/);return m?m[1].split(',').map(Number):null;}
    function light(v){return v.slice(0,3).map(n=>{const x=n/255;return x<=.04045?x/12.92:((x+.055)/1.055)**2.4;}).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);}
    const contrast=[];
    for(const node of [...document.querySelectorAll('h1,h2,h3,p,label,a,button,dt,dd,small,.tag,.label,.record-id,.tiny')].filter(n=>visible(n)&&n.textContent.trim()&&!n.disabled)){
     const ink=rgb(getComputedStyle(node).color);let ancestor=node,background=null;
     while(ancestor&&!background){const candidate=rgb(getComputedStyle(ancestor).backgroundColor);if(candidate&&(candidate.length<4||candidate[3]===1))background=candidate;ancestor=ancestor.parentElement;}
     if(ink&&background){const a=light(ink),b=light(background),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);if(ratio<4.5)contrast.push({text:node.textContent.trim().slice(0,60),ratio});}
    }
    return {view:view.dataset.view,headingCount:[...document.querySelectorAll('h1')].filter(visible).length,overflow:document.documentElement.scrollWidth-innerWidth,labels,targets,contrast,navCurrent:document.querySelectorAll('nav [aria-current=page]').length};
   });
   check(name+' layout '+viewport.width,state.view===name&&state.headingCount===1&&state.overflow<=1&&state.navCurrent===1,state);
   check(name+' form labels '+viewport.width,state.labels);
   check(name+' control targets '+viewport.width,state.targets.every(target=>target.height>=43.5&&target.width>=43.5),{small:state.targets.filter(target=>target.height<43.5||target.width<43.5)});
   check(name+' text contrast '+viewport.width,state.contrast.length===0,{problems:state.contrast});
   await page.screenshot({path:resolve(output,name+'-'+viewport.width+'.png'),fullPage:true});report.views.push({name,width:viewport.width});
  }
  await navigate('overview');
  check('default category-aware evidence gate '+viewport.width,await page.locator('#surface-count').textContent()==='1'&&(await page.locator('[data-candidate=AB-002] .reason').textContent()).includes('No approved experiment'));
  await page.locator('#priority').fill('95');check('importance holds all '+viewport.width,await page.locator('#surface-count').textContent()==='0');
  await page.locator('#priority').fill('0');await page.locator('#floor').selectOption('relevant');await page.locator('#freshness').fill('30');await page.locator('#attention').fill('3');
  check('relaxed rules show three with explicit no-effect status '+viewport.width,await page.locator('#surface-count').textContent()==='3'&&(await page.locator('#rule-status').textContent()).includes('No notification is sent'));
  await page.locator('#category').selectOption('experiment');check('category selection '+viewport.width,await page.locator('#surface-count').textContent()==='1');
  await page.locator('#floor').selectOption('ready');check('no false experiment qualification '+viewport.width,await page.locator('#surface-count').textContent()==='0');
  await page.locator('#category').selectOption('all');await page.locator('#floor').selectOption('relevant');await page.locator('#attention').fill('0');check('attention zero suppresses all '+viewport.width,await page.locator('#surface-count').textContent()==='0');
  await navigate('company');await page.locator('#company-name').fill('');await page.locator('#apply-context').click();
  check('missing company name refused '+viewport.width,(await page.locator('#context-status').textContent()).includes('Enter an invented')&&(await page.locator('#context-name').textContent())==='Northstar Components');
  const payload='<img src=x onerror="window.__xss=1">';await page.locator('#company-name').fill(payload);await page.locator('#goal').fill(payload);await page.locator('#apply-context').click();
  check('user text rendered inert '+viewport.width,await page.locator('#context-name').textContent()===payload&&await page.locator('#context-goal').textContent()===payload&&await page.locator('img').count()===0&&await page.evaluate(()=>typeof window.__xss)==='undefined');
  check('context is local only '+viewport.width,(await page.locator('#context-status').textContent()).includes('Nothing was uploaded or stored'));
  await navigate('brief');
  check('brief context not silently re-bound '+viewport.width,(await page.locator('.brief-metadata').textContent()).includes('original context v3')&&!(await page.locator('.brief-metadata').textContent()).includes(payload));
  await page.locator('#discuss').click();await page.locator('#discuss').click();await page.locator('#dismiss').click();
  await navigate('decisions');check('deduplicated local decisions '+viewport.width,await page.locator('#decision-list li').count()===2&&(await page.locator('#decision-list').textContent()).includes('review context v4')&&(await page.locator('#decision-list').textContent()).includes('original context v3'));
  check('no false realized benefit '+viewport.width,(await page.locator('.outcome-strip').textContent()).includes('Not measured'));
  await page.reload({waitUntil:'networkidle'});check('reload resets local decisions '+viewport.width,await page.locator('#decision-list li').count()===0);
  await navigate('company');check('reload resets context '+viewport.width,await page.locator('#company-name').inputValue()==='Northstar Components');
  check('no origin persistence '+viewport.width,await page.evaluate(()=>localStorage.length===0&&sessionStorage.length===0&&document.cookie===''));
  await page.goto(origin,{waitUntil:'networkidle'});await page.keyboard.press('Tab');check('keyboard skip link '+viewport.width,await page.evaluate(()=>document.activeElement.classList.contains('skip')));await page.keyboard.press('Enter');check('skip targets main '+viewport.width,await page.evaluate(()=>document.activeElement.id==='main'));
  await page.locator('[data-nav=brief]').focus();check('visible keyboard focus '+viewport.width,await page.locator('[data-nav=brief]').evaluate(node=>getComputedStyle(node).outlineStyle!=='none'&&parseFloat(getComputedStyle(node).outlineWidth)>=3));
  await page.keyboard.press('Enter');await page.locator('[data-view=brief]').waitFor({state:'visible'});check('keyboard navigation '+viewport.width,await page.locator('[data-view=brief]').isVisible());
  await context.close();
 }
 check('zero outbound requests',report.unexpected_requests.length===0,{unexpected:report.unexpected_requests});
 check('all fifteen views checked',report.views.length===15);
}catch(error){report.errors.push({phase:'checker',message:String(error)});}
finally{clearTimeout(deadline);if(browser)await browser.close();server.kill('SIGTERM');report.finished_at=new Date().toISOString();report.passed=report.errors.length===0&&report.checks.every(row=>row.passed)&&report.views.length===15;writeFileSync(resolve(output,'report.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx',mode:0o600});console.log(JSON.stringify({output,passed:report.passed,checks:report.checks.length,failed:report.checks.filter(row=>!row.passed),errors:report.errors,requests:report.requests.length,outbound:report.unexpected_requests.length}));process.exitCode=report.passed?0:1;}
