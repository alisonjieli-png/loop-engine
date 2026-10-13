/* Deterministic local-only complete video exporter. Each output is new and
   source-bound. The browser cannot contact the internet or customer accounts. */
import {createServer} from 'node:http';
import {readFile,writeFile,mkdir,realpath,stat} from 'node:fs/promises';
import {resolve,dirname,sep,extname,isAbsolute} from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {DURATION,FPS,SHOTS,inspectTimeline} from './timeline.mjs';
import {composeAudio} from './audio.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const repository=resolve(here,'../../..');
const output=process.argv[2];
const selected=process.argv[3]||'all';
if(!output||!isAbsolute(output)||!['all','proof','2d','2.5d','3d'].includes(selected))throw Error('Usage: node export.mjs ABSOLUTE_NEW_OUTPUT_DIRECTORY [all|proof|2d|2.5d|3d]');
if(inspectTimeline().length)throw Error('Timeline contract failed');
const showcaseModules=resolve(process.env.BALTOR_SHOWCASE_MODULES||resolve(repository,'showcase/node_modules'));
const threeModules=resolve(process.env.BALTOR_THREE_MODULES||resolve(repository,'examples/32_creative_arena/node_modules'));
const require=createRequire(import.meta.url),ffmpeg=require(resolve(showcaseModules,'ffmpeg-static')),ffprobe=require(resolve(showcaseModules,'ffprobe-static')).path;
const {chromium}=await import(pathToFileURL(resolve(showcaseModules,'playwright-core/index.mjs')).href);
const threePackage=JSON.parse(await readFile(resolve(threeModules,'three/package.json')));
if(threePackage.version!=='0.186.1')throw Error('Use the repository-pinned Three.js0.186.1');
const browserPath=process.env.BALTOR_CHROME||'/opt/google/chrome/chrome';
const hash=body=>createHash('sha256').update(body).digest('hex');
const sourceFiles=['index.html','style.css','scene.mjs','world.mjs','timeline.mjs','audio.mjs','export.mjs'];
const sourceHashes={};for(const name of sourceFiles)sourceHashes[name]=hash(await readFile(resolve(here,name)));
await mkdir(output);await mkdir(resolve(output,'keyframes'));
const report={record_type:'baltor_launch_motion_export/v1',started_at:new Date().toISOString(),source_sha256:sourceHashes,source_revision:spawnSync('git',['-C',repository,'rev-parse','HEAD'],{encoding:'utf8'}).stdout.trim(),treatments:[],checks:[],errors:[],blocked_requests:[],videos:[],audio:null,scope:'Original30-second motion ads, three rendering systems, signed-out feature claims. No website capture or customer-result claim. Diagrams visibly labelled. Local-only rendering; no model, provider or catalogue effect.'};
const check=(name,passed,detail={})=>report.checks.push({name,passed:passed===true,detail});
const types={'.html':'text/html','.css':'text/css','.mjs':'text/javascript','.js':'text/javascript','.json':'application/json'};
const server=createServer(async(req,res)=>{try{
 if(req.method!=='GET'){res.writeHead(405);res.end();return;}
 const pathname=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);if(pathname==='/favicon.ico'){res.writeHead(204);res.end();return;}
 let root=here,path=pathname==='/'?'index.html':pathname.slice(1);
 if(pathname.startsWith('/vendor/three/')){root=resolve(threeModules,'three');path=pathname.slice('/vendor/three/'.length);}
 if(path.split('/').some(x=>x==='..'||x==='')||path.includes('\\'))throw Error('Invalid asset path');
 root=await realpath(root);const file=await realpath(resolve(root,path));if(!file.startsWith(root+sep))throw Error('Asset outside root');
 const bytes=await readFile(file);if(bytes.length>4*1024*1024)throw Error('Asset byte bound');res.writeHead(200,{'Content-Type':types[extname(file)]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
 }catch{res.writeHead(404);res.end();}});
await new Promise(done=>server.listen(0,'127.0.0.1',done));const origin='http://127.0.0.1:'+server.address().port;
let browser;
function run(command,args,label){const p=spawnSync(command,args,{encoding:'utf8',maxBuffer:4*1024*1024});if(p.status!==0)throw Error(label+': '+String(p.stderr).slice(-1200));return p.stdout;}
const stamp=t=>new Date(t*1000).toISOString().slice(11,23).replace('.',',');
try{
 const audio=composeAudio();await writeFile(resolve(output,'original-score.wav'),audio.buffer,{flag:'wx'});report.audio={...audio.report,bytes:audio.buffer.length,sha256:hash(audio.buffer),listening_review:false};
 check('original soundbed headroom',audio.report.peak_dbfs<-3&&audio.report.rms_dbfs>-40,audio.report);
 await writeFile(resolve(output,'captions.srt'),SHOTS.map((shot,i)=>`${i+1}\n${stamp(shot.start)} --> ${stamp(shot.end)}\n${shot.title.replaceAll('\n',' ')} ${shot.copy}\n${shot.note}\n`).join('\n'),{flag:'wx'});
 browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox','--disable-dev-shm-usage','--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist']});
 const treatments=selected==='all'||selected==='proof'?['2d','2.5d','3d']:[selected];
 for(const treatment of treatments)for(const format of ['landscape','portrait']){
   const width=format==='landscape'?1920:1080,height=format==='landscape'?1080:1920,label=treatment.replace('.','p')+'-'+format;
   const context=await browser.newContext({viewport:{width,height},deviceScaleFactor:1,reducedMotion:'reduce'});
   await context.route('**/*',route=>{const r=route.request();if(new URL(r.url()).origin===origin&&r.method()==='GET')return route.continue();report.blocked_requests.push({url:r.url(),method:r.method()});return route.abort();});
   const page=await context.newPage();page.on('pageerror',e=>report.errors.push({label,error:e.message}));
   await page.goto(origin+'/?treatment='+treatment);await page.waitForFunction(()=>window.launch91?.ready===true,null,{timeout:30000});await page.evaluate(()=>document.fonts.ready);
   for(const shot of SHOTS){
     await page.evaluate(t=>window.launch91.render(t),shot.start+1.2);const state=await page.evaluate(()=>window.launch91.inspect());
     const fitted=!state.overflow&&state.textBounds.every(b=>b.left>=0&&b.right<=width&&b.top>=0&&b.bottom<=height);
     check(label+' '+shot.id+' text fits',fitted,state);
     if(shot.id==='afk')check(label+' visible AFK limit',state.textBounds.some(b=>b.text.includes('No hosted execution')));
     await page.screenshot({path:resolve(output,'keyframes',label+'-'+shot.id+'.png')});
   }
   if(treatment==='2.5d')check(label+' depth transforms',await page.locator('.closing-list').count()>0&&await page.evaluate(()=>{window.launch91.render(8);return [...document.querySelectorAll('.card')].every(el=>getComputedStyle(el).transform.startsWith('matrix3d'));}));
   if(treatment==='3d'){
     await page.evaluate(()=>window.launch91.render(15));const state=await page.evaluate(()=>window.launch91.inspect());check(label+' actual 3D geometry',state.three.real_geometry&&state.three.meshes>20&&state.three.triangles>1000,state.three);
     if(format==='landscape'){const model=Buffer.from(await page.evaluate(()=>window.launch91.exportScene()));await writeFile(resolve(output,'foundry-workflow-sculpture.glb'),model,{flag:'wx'});check('GLB signature',model.readUInt32LE(0)===0x46546c67,{bytes:model.length,sha256:hash(model)});}
   }
   report.treatments.push({treatment,format,width,height});
   if(selected!=='proof'){
     const file=resolve(output,label+'.mp4');
     const encoder=spawn(ffmpeg,['-hide_banner','-loglevel','error','-n','-f','image2pipe','-framerate',String(FPS),'-vcodec','png','-i','pipe:0','-i',resolve(output,'original-score.wav'),'-map','0:v:0','-map','1:a:0','-t',String(DURATION),'-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-threads','2','-c:a','aac','-b:a','160k','-movflags','+faststart',file],{stdio:['pipe','ignore','pipe']});
     let stderr='';encoder.stderr.on('data',v=>{stderr=(stderr+v.toString()).slice(-4000);});const finished=new Promise((accept,reject)=>{encoder.on('error',reject);encoder.on('close',code=>code===0?accept():reject(Error('Encoder failed'+code+': '+stderr)));});finished.catch(()=>{});
     const frameDigests=[];
     for(let frame=0;frame<DURATION*FPS;frame++){
       await page.evaluate(t=>window.launch91.render(t),frame/FPS);const png=await page.screenshot({type:'png',animations:'allow',optimizeForSpeed:true});
       if(frame%FPS===0)frameDigests.push(hash(png));
       if(!encoder.stdin.write(png))await once(encoder.stdin,'drain');
       if(frame%(FPS*5)===0)console.log(JSON.stringify({rendering:label,seconds:frame/FPS}));
     }
     encoder.stdin.end();await finished;run(ffmpeg,['-v','error','-i',file,'-f','null','-'],'Full decode');
     const metadata=JSON.parse(run(ffprobe,['-v','error','-show_format','-show_streams','-of','json',file],'Probe'));
     const video=metadata.streams.find(s=>s.codec_type==='video'),sound=metadata.streams.find(s=>s.codec_type==='audio');
     check(label+' complete video and audio',video.width===width&&video.height===height&&video.codec_name==='h264'&&video.pix_fmt==='yuv420p'&&Math.abs(Number(metadata.format.duration)-DURATION)<.1&&Number(video.nb_frames)===DURATION*FPS&&sound?.codec_name==='aac'&&sound?.channels===2,metadata);
     check(label+' continuous motion samples',new Set(frameDigests).size>=28,{distinct_seconds:new Set(frameDigests).size});
     const bytes=await readFile(file);report.videos.push({file:label+'.mp4',width,height,duration_seconds:Number(metadata.format.duration),frames:Number(video.nb_frames),bytes:bytes.length,sha256:hash(bytes),full_decode_passed:true});
   }
   await context.close();
 }
}catch(error){report.errors.push({stage:'export',error:String(error),stack:error.stack});}
finally{if(browser)await browser.close();await new Promise(done=>server.close(done));report.finished_at=new Date().toISOString();report.passed=report.checks.length>0&&report.checks.every(c=>c.passed)&&report.errors.length===0&&report.blocked_requests.length===0;await writeFile(resolve(output,'verification.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({output,passed:report.passed,checks:report.checks.length,failed:report.checks.filter(c=>!c.passed).map(c=>c.name),errors:report.errors,videos:report.videos.length}));if(!report.passed)process.exitCode=1;}
