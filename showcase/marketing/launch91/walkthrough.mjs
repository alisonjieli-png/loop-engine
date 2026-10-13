/* Record an actual signed-out tour. No replayed API response or fabricated UI.
   Task paths are visibly labelled demo inputs; no model or worker is started. */
import {readFile,writeFile,mkdir,stat} from 'node:fs/promises';
import {resolve,dirname,isAbsolute} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {composeAudio} from './audio.mjs';
const here=dirname(fileURLToPath(import.meta.url)),repository=resolve(here,'../../..'),output=process.argv[2];
if(!output||!isAbsolute(output))throw Error('Provide a new absolute output directory');
const modules=resolve(process.env.BALTOR_SHOWCASE_MODULES||resolve(repository,'showcase/node_modules')),require=createRequire(import.meta.url);
const {chromium}=await import(pathToFileURL(resolve(modules,'playwright-core/index.mjs')).href),ffmpeg=require(resolve(modules,'ffmpeg-static')),ffprobe=require(resolve(modules,'ffprobe-static')).path;
await mkdir(output);await mkdir(resolve(output,'screenshots'));await mkdir(resolve(output,'capture'));
const origins=['https://dontbeameatproxy.si','https://agentfeeds.si','https://getagentfoundry.si','https://agentafk.si'];
const report={record_type:'baltor_signed_out_walkthrough/v1',started_at:new Date().toISOString(),origins,chapters:[],checks:[],errors:[],blocked:[],requests:0,scope:'Actual public UI recorded continuously. Only allowed-origin GET/HEAD requests. Form selections and AFK manifest preparation are local demo inputs. No customer identity, signup, email, payment, model or worker execution. Original instrumental soundtrack; no narration.'};
const check=(name,passed,detail={})=>report.checks.push({name,passed:passed===true,detail});
const browser=await chromium.launch({executablePath:process.env.BALTOR_CHROME||'/opt/google/chrome/chrome',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
let context,page,video,start;
try{
 context=await browser.newContext({viewport:{width:1920,height:1080},deviceScaleFactor:1,recordVideo:{dir:resolve(output,'capture'),size:{width:1920,height:1080}},acceptDownloads:true});
 await context.route('**/*',route=>{const r=route.request();report.requests++;if(report.requests>500||!origins.includes(new URL(r.url()).origin)||!['GET','HEAD'].includes(r.method())){report.blocked.push({method:r.method(),url:r.url()});return route.abort();}return route.continue();});
 page=await context.newPage();video=page.video();start=Date.now();page.on('pageerror',e=>report.errors.push(e.message));
 async function chapter(id,url,caption,act){
   const begin=(Date.now()-start)/1000,response=await page.goto(url,{waitUntil:'networkidle',timeout:30000});
   check(id+' actual HTTPS page',response.status()===200&&page.url()===url,{url,status:response.status()});
   await page.evaluate(()=>document.fonts.ready);await act?.();
   const state=await page.evaluate(()=>({h1:document.querySelector('h1')?.textContent,overflow:document.documentElement.scrollWidth>innerWidth+1}));check(id+' visible page',Boolean(state.h1)&&!state.overflow,state);
   await page.screenshot({path:resolve(output,'screenshots',id+'.png')});
   const elapsed=(Date.now()-start)/1000-begin;if(elapsed<10.4)await page.waitForTimeout((10.4-elapsed)*1000);
   const end=(Date.now()-start)/1000;report.chapters.push({id,url,caption,start_seconds:begin,end_seconds:end});console.log(JSON.stringify({chapter:id,elapsed_seconds:end}));
 }
 await chapter('01-campaign',origins[0]+'/',"Don't be a meat proxy. This campaign points to the AgentFeeds tools you can use today.");
 await chapter('02-source-collections',origins[1]+'/collections','AgentFeeds offers curated source references and comparison questions. Your agent reads the original sources.',async()=>{await page.locator('#collection-search').fill('coding');});
 await chapter('03-coding-decision',origins[1]+'/collections/coding-benchmarks','Open a collection to inspect its sources, comparison fields and Markdown, RSS or JSON Feed links.');
 await chapter('04-reading-profile',origins[1]+'/build','Choose a reading profile for one agent. These are example selections, not an activated hosted schedule.',async()=>{await page.locator('[name=agent_label]').fill('Demo coding reviewer');await page.locator('[name=collection_ids]').first().check();await page.locator('#profile-output').scrollIntoViewIfNeeded();});
 await chapter('05-component-foundry',origins[2]+'/','AgentFoundry shows reusable components and recorded previews. Check source, requirements and use conditions.');
 await chapter('06-component-examples',origins[2]+'/examples','Filter public component examples. A preview does not establish installation or accepted customer work.',async()=>{await page.locator('[name=query]').fill('halftone');await page.waitForTimeout(500);check('example filter has a result',await page.locator('[data-component]:visible').count()>0);});
 await chapter('07-public-search',origins[2]+'/library','Search the actual Public Good collection. Account access and setup remain separate from public discovery.',async()=>{await page.locator('[name=query]').fill('water');await page.getByRole('button',{name:'Search',exact:true}).click();await page.waitForFunction(()=>/matching components/.test(document.querySelector('[data-public-status]')?.textContent||''),null,{timeout:20000});await page.locator('.public-result').first().scrollIntoViewIfNeeded();check('actual public search results',await page.locator('.public-result').count()>0&&await page.locator('.public-result').first().isVisible());});
 await chapter('08-local-work-plan',origins[3]+'/plan','AgentAFK is a local Preview. These demo task paths prepare a downloadable list; no worker starts here.',async()=>{await page.locator('[name=tasks]').fill('/demo/tasks/review.txt\n/demo/tasks/report.txt');await page.getByRole('button',{name:'Prepare the queue',exact:true}).click();await page.locator('#run-desk-command').scrollIntoViewIfNeeded();check('local command prepared',(await page.locator('#run-desk-command').textContent()).includes('tools/overnight_queue.py'));const wait=page.waitForEvent('download');await page.locator('#run-desk-download').click();const download=await wait;if(download.suggestedFilename()!=='baltor-tasks.txt')throw Error('Unexpected local filename');await download.saveAs(resolve(output,'baltor-tasks.txt'));});
 await chapter('09-execution-limits',origins[3]+'/help','Bring your worker and model access. Hosted execution, cloud supervision and learned queue ranking are not available from this Preview.');
 await context.close();context=null;await browser.close();
 const raw=await video.path();
 const rawProbe=JSON.parse(run(ffprobe,['-v','error','-show_format','-of','json',raw]));
 const duration=Number(rawProbe.format.duration);
 check('long-form tour exceeds60seconds',duration>=90&&duration<=120,{recorded_video_seconds:duration,chapters:report.chapters.length});
 const stamp=t=>new Date(Math.round(t*1000)).toISOString().slice(11,23).replace('.',',');const srt=report.chapters.map((c,i)=>`${i+1}\n${stamp(c.start_seconds)} --> ${stamp(c.end_seconds)}\n${c.caption}\n`).join('\n');await writeFile(resolve(output,'walkthrough.srt'),srt,{flag:'wx'});
 const score=composeAudio();await writeFile(resolve(output,'original-score.wav'),score.buffer,{flag:'wx'});
 const file=resolve(output,'baltor-live-walkthrough.mp4');
 function run(command,args){const result=spawnSync(command,args,{encoding:'utf8',maxBuffer:2*1024*1024});if(result.status!==0)throw Error(String(result.stderr).slice(-1200));return result.stdout;}
 run(ffmpeg,['-hide_banner','-loglevel','error','-n','-i',raw,'-stream_loop','3','-i',resolve(output,'original-score.wav'),'-i',resolve(output,'walkthrough.srt'),'-map','0:v:0','-map','1:a:0','-map','2:s:0','-t',String(duration),'-vf','fps=24,format=yuv420p','-c:v','libx264','-preset','fast','-crf','20','-threads','2','-c:a','aac','-b:a','160k','-c:s','mov_text','-disposition:s:0','default','-movflags','+faststart',file]);
 run(ffmpeg,['-v','error','-i',file,'-f','null','-']);const probe=JSON.parse(run(ffprobe,['-v','error','-show_format','-show_streams','-of','json',file]));const v=probe.streams.find(s=>s.codec_type==='video');check('complete1080p long-form media',v.width===1920&&v.height===1080&&Number(probe.format.duration)>=90&&Number(probe.format.duration)<=120&&probe.streams.some(s=>s.codec_type==='audio')&&probe.streams.some(s=>s.codec_type==='subtitle'),probe);const bytes=await readFile(file);report.video={file:'baltor-live-walkthrough.mp4',sha256:createHash('sha256').update(bytes).digest('hex'),bytes:bytes.length,duration_seconds:Number(probe.format.duration),full_decode_passed:true};
}catch(error){report.errors.push({error:String(error),stack:error.stack});}
finally{if(context)await context.close();if(browser.isConnected())await browser.close();report.finished_at=new Date().toISOString();report.passed=report.chapters.length===9&&report.checks.every(c=>c.passed)&&report.errors.length===0&&report.blocked.length===0;await writeFile(resolve(output,'verification.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({output,passed:report.passed,chapters:report.chapters.length,checks:report.checks.length,failed:report.checks.filter(c=>!c.passed).map(c=>c.name),errors:report.errors,blocked:report.blocked}));if(!report.passed)process.exitCode=1;}
