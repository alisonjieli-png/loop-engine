/* Public demo integrity across every task/harness transition; no credentials or model calls. */
import {chromium} from '../showcase/node_modules/playwright-core/index.mjs';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve} from 'node:path';
const root=resolve(new URL('..',import.meta.url).pathname),output=resolve(process.argv[2]||'');
if(!process.argv[2]||existsSync(output))throw Error('A new evidence output is required');
const remote=process.argv[3];if(remote&&new URL(remote).origin!==remote)throw Error('Exact origin required');
const refs=new Map(JSON.parse(readFileSync(resolve(root,'examples/29_intelligence_service/starter-catalogue/host-release/manifest.json'))).items.map(row=>[row.reference.identity,row.reference]));
const skillRoots=JSON.parse(readFileSync(resolve(root,'integrations/baltor-library/release.json'))).native_skill_folders;
const profiles={"claude-code":['CLAUDE.md','.mcp.json'],codex:['AGENTS.md','.codex/config.toml'],opencode:['AGENTS.md','opencode.json'],pi:['AGENTS.md','.pi/baltor.json'],"baltor-harness":['task.md',null]};
const tasks={dedupe:['find_duplicate_records_with_blocking_keys','step-3-find-duplicates'],overnight:['read_the_train_validation_gap','step-2-close-the-validation-gap'],handoff:['report_observed_derived_assumed_and_unknown','step-5-report-the-result']};
const checks=[],errors=[];let child,browser,lastPage,base=remote;
const check=(name,passed,detail={})=>checks.push({name,passed:passed===true,detail});
const valid=(state,harness,task)=>{
 const [identity,step]=tasks[task],record=refs.get(identity),[instruction,config]=profiles[harness];
 const rootPath=skillRoots[harness]?.project.replace(/baltor-library$/,'');
 return state.harness===harness&&state.task===task&&state.identity===identity&&state.read===identity
   &&state.digest===record.digest&&state.expected===record.digest&&state.step===step+'/'
   &&state.tree.includes(instruction)&&(!config||state.tree.includes(config))
   &&(!rootPath||state.tree.includes(rootPath)&&state.path===rootPath+identity.replaceAll('_','-')+'/SKILL.md')
   &&(harness==='claude-code'||!state.tree.includes('CLAUDE.md')&&!state.tree.includes('.claude/skills/'));
};
try{
 if(!base){
  const boot=`from tempfile import TemporaryDirectory
from pathlib import Path
import json,sys
from loop_engine.core.service_runtime.http_test_fixtures import HttpDomainFixture,running_http
with TemporaryDirectory() as folder:
 fixture=HttpDomainFixture(Path(folder))
 with running_http(fixture,display_name='Baltor') as (base,app):
  print(json.dumps({'base':base}),flush=True)
  sys.stdin.readline()
`;
  child=spawn(resolve(root,'.venv/bin/python'),['-u','-c',boot],{cwd:root,env:{...process.env,PYTHONPATH:'src'},stdio:['pipe','pipe','pipe']});
  let stderr='';child.stderr.on('data',b=>{stderr=(stderr+b.toString()).slice(-2000);});
  base=await new Promise((yes,no)=>{const lines=createInterface({input:child.stdout});const timer=setTimeout(()=>no(Error('fixture timeout '+stderr)),20000);lines.once('line',line=>{clearTimeout(timer);yes(JSON.parse(line).base);});child.once('exit',code=>{clearTimeout(timer);no(Error('fixture exit '+code+' '+stderr));});});
 }
 browser=await chromium.launch({executablePath:'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
 await context.route('**/*',route=>new URL(route.request().url()).origin===base?route.continue():route.abort());
 const page=await context.newPage();lastPage=page;page.on('pageerror',error=>errors.push(String(error)));
 const state=()=>page.locator('.hero-terminal').evaluate(node=>({
  harness:node.querySelector('[data-hero-harness][aria-pressed=true]')?.dataset.heroHarness,
  task:node.querySelector('[data-hero-scenario][aria-pressed=true]')?.dataset.heroScenario,
  identity:node.querySelector('.hero-results .is-chosen')?.dataset.demoItem,
  digest:node.querySelector('.hero-results .is-chosen')?.dataset.demoDigest,
  read:node.querySelector('[data-demo-download]')?.dataset.demoDownload,
  expected:node.querySelector('[data-demo-expected-digest]')?.dataset.demoExpectedDigest,
  step:node.querySelector('[data-hero-step]')?.textContent,
  tree:node.querySelector('.hero-tree')?.textContent,
  path:node.querySelector('.hero-tree [data-demo-path]')?.dataset.demoPath}));
 for(const width of [1440,390]){
  await page.setViewportSize({width,height:1000});await page.goto(base+'/');
  await page.waitForFunction(()=>document.querySelector('.hero-terminal')?.dataset.heroScenario==='dedupe');
  for(const from of Object.keys(profiles)){
   await page.locator(`[data-hero-harness="${from}"]`).click();
   for(const harness of Object.keys(profiles)){
    await page.locator(`[data-hero-harness="${harness}"]`).click();
    for(const task of ['dedupe','overnight','handoff','dedupe','overnight']){
     await page.locator(`button[data-hero-scenario="${task}"]`).click();
     const seen=await state();check('consistent_selection',valid(seen,harness,task),{width,from,harness,task,...seen});
    }
   }
  }
  await page.reload();await page.waitForFunction(()=>document.querySelector('.hero-terminal')?.dataset.heroScenario==='dedupe');
  check('reload_starts_coherently',valid(await state(),'claude-code','dedupe'),{width});
  const seen=await state();
  check('known_wrong_profile_refused',!valid({...seen,harness:'codex'},'codex','dedupe'),{width});
  check('known_wrong_read_refused',!valid({...seen,read:'wrong'},'claude-code','dedupe'),{width});
  check('known_wrong_full_digest_refused',!valid({...seen,digest:'0'.repeat(64),expected:'0'.repeat(64)},'claude-code','dedupe'),{width});
 }
 check('no_browser_errors',errors.length===0,{errors});
}catch(error){check('completed_sequence',false,{message:String(error),
 page:lastPage?await lastPage.evaluate(()=>({url:location.href,title:document.title,text:document.body.innerText.slice(0,800),scripts:[...document.scripts].map(s=>s.src)})).catch(()=>null):null});}
finally{
 if(browser)await browser.close();
 if(child&&child.exitCode===null){const ended=new Promise(done=>child.once('exit',done));child.stdin.end('\n');await ended;}
 writeFileSync(output,JSON.stringify({record_type:'homepage_selection_acceptance/v1',origin:base,all_passed:checks.every(r=>r.passed),checks,errors},null,2)+'\n');
}
console.log(JSON.stringify({output,passed:checks.filter(r=>r.passed).length,total:checks.length,all_passed:checks.every(r=>r.passed)}));
if(checks.some(r=>!r.passed))process.exitCode=1;
