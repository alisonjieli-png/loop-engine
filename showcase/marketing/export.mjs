/* Export silent, captioned marketing drafts from the actual packaged deck and
   original game render. No external assets, account data or model calls. */
import {createServer} from 'node:http';
import {readFile, writeFile, mkdir, realpath, stat} from 'node:fs/promises';
import {resolve, dirname, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {chromium} from '../node_modules/playwright-core/index.mjs';
import {findBrowser, findFfmpeg, findFfprobe, run} from '../tools/media-common.mjs';

const here=dirname(fileURLToPath(import.meta.url));
const assets=resolve(here,'../../src/loop_engine/core/service_runtime/web_assets');
const output=resolve(process.argv[2]||'');
if(!process.argv[2]||output===here)throw new Error('Usage: node showcase/marketing/export.mjs NEW_OUTPUT_DIRECTORY');
await mkdir(output); // Never replace a prior export.
await mkdir(resolve(output,'frames')); await mkdir(resolve(output,'segments'));
const types={'.html':'text/html','.js':'text/javascript','.css':'text/css','.png':'image/png','.svg':'image/svg+xml','.woff2':'font/woff2'};
const server=createServer(async(req,res)=>{
  try{
    const path=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
    let file;
    if(path==='/deck')file=resolve(assets,'deck.html');
    else if(path==='/ad')file=resolve(here,'social-ad.html');
    else if(path==='/demo-frame.png')file=resolve(output,'demo-frame.png');
    else if(path.startsWith('/assets/')){
      file=await realpath(resolve(assets,path.slice(8)));
      if(!file.startsWith(assets+sep))throw new Error('outside assets');
    }else{res.writeHead(404);res.end();return;}
    let bytes=await readFile(file);
    if(file.endsWith('.html'))bytes=Buffer.from(bytes.toString().replaceAll('{{SERVICE_NAME}}','Baltor'));
    const extension=file.slice(file.lastIndexOf('.'));
    res.writeHead(200,{'Content-Type':types[extension]||'application/octet-stream','Cache-Control':'no-store'});res.end(bytes);
  }catch{res.writeHead(404);res.end();}
});
await new Promise(done=>server.listen(0,'127.0.0.1',done));
const base='http://127.0.0.1:'+server.address().port;
const browser=await chromium.launch({executablePath:await findBrowser(),headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
const errors=[],checks=[],externalOrigins=[];
const captions={social:[
  'Reusable code, tools and reference material for your own AI harness.',
  'Inspect the source, licence and version. Download complete packages.',
  'Play Ashen Wilds, change the scene and export an editable model for Blender.',
  'Try the demo and explore the library at baltor.ai.'
],pitch:[]};
const duration={social:[7,7,10,6],pitch:[12,12,12,12,12,12,12,12,12,12]};
const frames={social:[],pitch:[]};
const context=await browser.newContext({viewport:{width:1440,height:900},reducedMotion:'reduce'});
await context.route('**/*',route=>{
  const origin=new URL(route.request().url()).origin;
  if(origin===base)return route.continue();
  externalOrigins.push(origin);return route.abort();
});
const page=await context.newPage();page.on('pageerror',error=>errors.push(error.message));
try{
  await page.goto(base+'/assets/creative-arena/index.html');
  await page.waitForFunction(()=>window.baltorArena?.inspect().renderedFrames>5,null,{timeout:60000});
  await page.locator('#begin').click();await page.locator('#pause').click();
  await page.locator('#scene-tools summary').click();
  await page.locator('#atmosphere').selectOption('dawn');await page.locator('#motion').selectOption('Run');
  await page.waitForTimeout(800);
  // Capture the actual rendered canvas, without introducing an invented UI.
  await page.locator('#world').screenshot({path:resolve(output,'demo-frame.png')});
  for(let index=0;index<4;index++){
    await page.setViewportSize({width:1080,height:1920});await page.goto(base+'/ad?scene='+index);
    await page.evaluate(()=>document.fonts.ready);
    await page.locator('.scene').evaluate(img=>img.decode());
    const fit=await page.evaluate(()=>document.body.scrollWidth===1080&&document.body.scrollHeight===1920
      &&document.querySelector('.footer').getBoundingClientRect().bottom<=1800);
    checks.push({name:'social_scene_'+index+'_fits',passed:fit});
    const file=resolve(output,'frames','social-'+index+'.png');await page.screenshot({path:file});frames.social.push(file);
  }
  await page.setViewportSize({width:1920,height:1080});await page.goto(base+'/deck');
  await page.evaluate(()=>document.fonts.ready);
  const ids=await page.locator('[data-slide]').evaluateAll(rows=>rows.map(row=>row.id));
  if(ids.length!==duration.pitch.length)throw new Error('Deck slide count changed; revise the timing explicitly.');
  for(const [index,id]of ids.entries()){
    if(index)await page.keyboard.press('ArrowRight');
    await page.waitForTimeout(150);
    checks.push({name:'pitch_slide_'+id+'_shown',passed:await page.locator('#'+id).isVisible()});
    captions.pitch.push(await page.locator('#'+id+' h1, #'+id+' h2').first().textContent());
    const file=resolve(output,'frames','pitch-'+index+'.png');await page.screenshot({path:file});frames.pitch.push(file);
  }
}finally{await browser.close();await new Promise(done=>server.close(done));}
if(errors.length||checks.some(row=>!row.passed))throw new Error(JSON.stringify({errors,checks}));
const ffmpeg=findFfmpeg(),ffprobe=findFfprobe();
const timestamp=seconds=>new Date(seconds*1000).toISOString().slice(11,23).replace('.',',');
const reports=[];
for(const kind of ['social','pitch']){
  let cursor=0;const segments=[],subtitles=[];
  for(const [index,file]of frames[kind].entries()){
    const seconds=duration[kind][index],segment=resolve(output,'segments',kind+'-'+index+'.mp4');segments.push(segment);
    run(ffmpeg,['-hide_banner','-loglevel','error','-n','-loop','1','-framerate','24','-i',file,
      '-t',String(seconds),'-vf',`fade=t=in:st=0:d=0.2,fade=t=out:st=${seconds-.2}:d=0.2,format=yuv420p`,
      '-c:v','libx264','-preset','fast','-crf','21','-threads','2','-an',segment],'Encode '+kind+' scene');
    subtitles.push(`${index+1}\n${timestamp(cursor)} --> ${timestamp(cursor+seconds)}\n${captions[kind][index]}\n`);cursor+=seconds;
  }
  const list=resolve(output,kind+'-segments.txt');
  // FFmpeg's concat quoting: preserve paths, including single quotes.
  await writeFile(list,segments.map(file=>"file '"+file.replaceAll("'","'\\''")+"'").join('\n')+'\n',{flag:'wx'});
  const file=resolve(output,kind==='social'?'baltor-30-second-social.mp4':'baltor-2-minute-pitch.mp4');
  run(ffmpeg,['-hide_banner','-loglevel','error','-n','-f','concat','-safe','0','-i',list,
    '-c','copy','-movflags','+faststart',file],'Join '+kind);
  run(ffmpeg,['-v','error','-i',file,'-f','null','-'],'Decode '+kind);
  const media=JSON.parse(run(ffprobe,['-v','error','-show_format','-show_streams','-of','json',file],'Probe '+kind).stdout);
  const video=media.streams.find(row=>row.codec_type==='video');
  if(Math.abs(Number(media.format.duration)-cursor)>.05||video.codec_name!=='h264'||video.pix_fmt!=='yuv420p')throw new Error('Unexpected video format');
  await writeFile(file.replace('.mp4','.srt'),subtitles.join('\n'),{flag:'wx'});
  reports.push({file:file.split(sep).at(-1),duration_seconds:Number(media.format.duration),width:video.width,height:video.height,
    bytes:(await stat(file)).size,sha256:createHash('sha256').update(await readFile(file)).digest('hex')});
}
const sourceFiles=['social-ad.html','export.mjs'].map(file=>resolve(here,file));
sourceFiles.push(resolve(assets,'deck.html'),resolve(assets,'creative-arena/arena.js'));
const sourceDigests={};for(const file of sourceFiles)sourceDigests[file.slice(resolve(here,'../..').length+1)]=createHash('sha256').update(await readFile(file)).digest('hex');
const report={record_type:'baltor_marketing_export/v1',recorded_at:new Date().toISOString(),checks,errors,videos:reports,source_sha256:sourceDigests,
  model_calls:0,external_asset_requests:externalOrigins.length,blocked_external_origins:[...new Set(externalOrigins)],audio:'No audio track. Visible copy and separate SRT captions.',
  scope:'Captioned draft exports with still-frame fades, using the actual packaged pitch deck and a rendered original demo scene. Not a customer-benefit comparison or automatic video recreation.'};
await writeFile(resolve(output,'verification.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(report));
