import {chromium} from '/home/username/loop-engine/showcase/node_modules/playwright-core/index.mjs';
import {writeFileSync,readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
const output=new URL('./',import.meta.url).pathname;
const browser=await chromium.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox']});
const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce',serviceWorkers:'block'});
const rejected=[],errors=[],pages=[];
await context.route('**/*',route=>{
 const request=route.request();
 if(request.method()==='GET'&&new URL(request.url()).origin==='https://baltor.ai')return route.continue();
 rejected.push({url:request.url(),method:request.method()});return route.abort();
});
const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
const rect=el=>el?{x:el.getBoundingClientRect().x,y:el.getBoundingClientRect().y,width:el.getBoundingClientRect().width,height:el.getBoundingClientRect().height}:null;
async function inspect(path,width,height,name,full=false){
 await page.setViewportSize({width,height});
 const response=await page.goto('https://baltor.ai'+path,{waitUntil:'networkidle'});
 const row={path,width,height,status:response.status(),observed_at:new Date().toISOString()};
 Object.assign(row,await page.evaluate(()=>{
 const visible=e=>!!e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
 const box=e=>e?{x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}:null;
 const text=e=>(e.innerText||e.textContent||'').replace(/\s+/g,' ').trim();
 const focusable=[...document.querySelectorAll('a,button,input,select,textarea,summary')].filter(visible);
 return {title:document.title,height:document.documentElement.scrollHeight,overflow:document.documentElement.scrollWidth>innerWidth+1,
 h1:[...document.querySelectorAll('h1')].filter(visible).map(text),
 header:box(document.querySelector('header')),hero:box(document.querySelector('.hero-copy')),aside:box(document.querySelector('.hero-aside')),demo:box(document.querySelector('.step-demo')),action:box(document.querySelector('#hero-primary')),email:box(document.querySelector('#waitlist-email')),
 visible_text:document.body.innerText,links:[...document.querySelectorAll('a[href]')].filter(visible).map(e=>({text:text(e),href:e.getAttribute('href')})),
 unlabeled_controls:focusable.filter(e=>e.tagName!=='A'&&!text(e)&&!e.getAttribute('aria-label')&&!e.getAttribute('aria-labelledby')&&!(e.labels?.length)).map(e=>e.outerHTML.slice(0,180)),
 tiny_controls:focusable.filter(e=>{const b=box(e);return b.width<24||b.height<24}).map(e=>({text:text(e),id:e.id,box:box(e)})),
 logo:{src:document.querySelector('.brand-mark')?.getAttribute('src'),box:box(document.querySelector('.brand-mark'))},
 meta_description:document.querySelector('meta[name="description"]')?.content,canonical:document.querySelector('link[rel="canonical"]')?.href||null,
 navigation_timing:performance.getEntriesByType('navigation').map(e=>({response_start:e.responseStart,dom_content_loaded:e.domContentLoadedEventEnd,load:e.loadEventEnd}))};
 }));
 await page.screenshot({path:output+name+'.png'});if(full)await page.screenshot({path:output+name+'-full.png',fullPage:true});pages.push(row);
}
try{
 for(const [w,h,n] of [[1440,900,'desktop'],[390,844,'phone'],[320,700,'small-phone']])await inspect('/',w,h,'home-'+n,true);
 await inspect('/waitlist',390,844,'waitlist-phone',true);
 await inspect('/pricing',1440,900,'pricing-desktop');
 await inspect('/connect',390,844,'connect-phone',true);
 await inspect('/signup',390,844,'signup-phone');
 await inspect('/account',1440,900,'account-signed-out');
 await inspect('/app',1440,900,'workspace-signed-out');
 await inspect('/docs',1440,900,'docs-desktop');
 await inspect('/how-it-works',390,844,'how-it-works-phone',true);
 await page.setViewportSize({width:390,height:844});await page.goto('https://baltor.ai/',{waitUntil:'networkidle'});
 const keyboard=[];
 for(let i=0;i<5;i++){await page.keyboard.press('Tab');keyboard.push(await page.evaluate(()=>({tag:document.activeElement.tagName,id:document.activeElement.id,text:document.activeElement.textContent.trim(),aria:document.activeElement.getAttribute('aria-label')})));}
 await page.locator('#menu-toggle').focus();await page.keyboard.press('Space');
 const menu=await page.evaluate(()=>({checked:document.querySelector('#menu-toggle').checked,expanded:document.querySelector('#menu-toggle').getAttribute('aria-expanded'),visible:!!document.querySelector('#main-nav').getClientRects().length,height:document.querySelector('header').getBoundingClientRect().height}));
 await page.screenshot({path:output+'phone-menu-open.png'});
 await page.locator('#hero-primary').click();
 const invitation=await page.evaluate(()=>{const e=document.querySelector('#waitlist-email'),b=e.getBoundingClientRect();return {path:location.pathname,visible:!!e.getClientRects().length,top:b.top,bottom:b.bottom,viewport:innerHeight,active:document.activeElement.id};});
 await page.screenshot({path:output+'phone-invitation-from-hero.png'});
 const assetHashes={};for(const asset of ['baltor-mark.svg','favicon-32.png','architecture.css','service.js']){const response=await page.request.get('https://baltor.ai/assets/'+asset),body=await response.body();assetHashes[asset]={status:response.status(),sha256:createHash('sha256').update(body).digest('hex'),bytes:body.length};}
 writeFileSync(output+'browser-observations.json',JSON.stringify({record_type:'read_only_browser_review/v1',source_revision:'abcad4f8',at:new Date().toISOString(),browser:await browser.version(),pages,keyboard,menu,invitation,assetHashes,errors,rejected,limits:['No forms submitted, no accounts used, no protected material fetched','One isolated Chromium session, no screen-reader or conversion measurement']},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({pages:pages.map(({path,width,overflow,header,action,email})=>({path,width,overflow,header,action,email})),keyboard,menu,invitation,errors,rejected},null,2));
}finally{await browser.close();}
