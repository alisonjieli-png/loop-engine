/* Local website-demo production; no source publication or catalogue admission. */
import {readFile,writeFile,mkdir,stat} from "node:fs/promises";
import {createHash} from "node:crypto";
import {resolve,dirname} from "node:path";
import {fileURLToPath} from "node:url";
import {spawn} from "node:child_process";
import {once} from "node:events";
import {chromium} from "../node_modules/playwright-core/index.mjs";
import {findBrowser,findFfmpeg,findFfprobe,run,probeMedia,summarizeMedia,sha256} from "../tools/media-common.mjs";
import {scene,revisedScene,validateScene,orbitPoint} from "./orbit.mjs";
import {renderCue,wavBytes} from "./music.mjs";

const here=dirname(fileURLToPath(import.meta.url)),output=resolve(process.argv[2]||"");
const stillsOnly=process.argv[3]==="--stills";
if(!process.argv[2]||process.argv.length>(stillsOnly?4:3))throw Error("Use: node showcase/original-previews/export.mjs NEW_DIRECTORY [--stills]");
await mkdir(output,{mode:0o700});
const ffmpeg=findFfmpeg(),ffprobe=findFfprobe(),chrome=await findBrowser();
const record={record_type:"original_website_media_prototype/v1",created_at:new Date().toISOString(),
  scope:"Private original website demonstrations, not catalogue content; independent review and publication pending.",
  tool_paths:{ffmpeg,ffprobe,chrome},tool_sha256:{},source_sha256:{},checks:[],outputs:[],external_requests:[],
  model_calls:0,provider_calls:0,gpu_claim:false,stills_only:stillsOnly};
for(const [name,path]of Object.entries(record.tool_paths))record.tool_sha256[name]=await sha256(path);
record.tool_versions={ffmpeg:run(ffmpeg,["-version"],"FFmpeg version").stdout.split("\n")[0],
  ffprobe:run(ffprobe,["-version"],"ffprobe version").stdout.split("\n")[0]};
for(const name of ["orbit.mjs","orbit.html","score.json","music.mjs","export.mjs"])
  record.source_sha256[name]=await sha256(resolve(here,name));
const check=(name,passed,detail={})=>{record.checks.push({name,passed:passed===true,detail});if(!passed)throw Error(name);};
const evidence=async(file,kind)=>({file,kind,bytes:(await stat(resolve(output,file))).size,sha256:await sha256(resolve(output,file))});
const script=await readFile(resolve(here,"orbit.mjs"),"utf8");
let browser;
try {
  browser=await chromium.launch({executablePath:chrome,headless:true,args:["--no-sandbox","--disable-gpu"]});
  record.tool_versions.chromium=browser.version();
  const page=await browser.newPage({viewport:{width:scene.width,height:scene.height},deviceScaleFactor:1});
  await page.route("**/*",route=>{record.external_requests.push(route.request().url());return route.abort();});
  page.on("pageerror",error=>{throw error;});
  await page.setContent('<!doctype html><html><body style="margin:0"><canvas id="preview"></canvas></body></html>');
  await page.addScriptTag({type:"module",content:script+"\nwindow.renderOriginal=(seconds,settings)=>{drawOrbit(document.querySelector('canvas'),seconds,settings);return document.querySelector('canvas').toDataURL('image/png').split(',')[1]};"});
  await page.waitForFunction(()=>typeof window.renderOriginal==="function");
  const frame=async(time,settings)=>Buffer.from(await page.evaluate(({time,settings})=>window.renderOriginal(time,settings),{time,settings}),"base64");
  for(const [variant,settings]of [["original",scene],["revision",revisedScene]]) {
    validateScene(settings);
    const first=await frame(0,settings),closed=await frame(settings.duration_seconds,settings);
    check(variant+" loop returns to exact first frame",first.equals(closed));
    for(const time of [0,3,6,9])await writeFile(resolve(output,`copper-current-${variant}-${time}s.png`),await frame(time,settings),{flag:"wx"});
    if(stillsOnly)continue;
    const file=`copper-current-${variant}.mp4`,path=resolve(output,file);
    const args=["-hide_banner","-loglevel","error","-n","-f","image2pipe","-framerate",String(settings.fps),"-vcodec","png","-i","pipe:0",
      "-an","-c:v","libx264","-preset","fast","-crf","24","-maxrate","1100k","-bufsize","2200k","-threads","2",
      "-pix_fmt","yuv420p","-movflags","+faststart","-metadata","title=Copper Current: original procedural clip",path];
    const encoder=spawn(ffmpeg,args,{stdio:["pipe","ignore","pipe"]});let errors="";
    encoder.stderr.on("data",data=>{errors+=data;});
    const exit=once(encoder,"exit");
    for(let index=0;index<settings.duration_seconds*settings.fps;index++) {
      const png=await frame(index/settings.fps,settings);
      if(!encoder.stdin.write(png))await once(encoder.stdin,"drain");
    }
    encoder.stdin.end();const [status]=await exit;
    check(variant+" video encoder succeeds",status===0,{status,errors});
    run(ffmpeg,["-v","error","-i",path,"-f","null","-"],"Decode original website clip");
    const summary=summarizeMedia(probeMedia(ffprobe,path));
    check(variant+" video format and bound",summary.width===960&&summary.height===540&&summary.videoCodec==="h264"
      &&summary.pixelFormat==="yuv420p"&&Math.abs(summary.durationSeconds-12)<0.05&&summary.frameRate===24
      &&summary.sizeBytes<=2*1024*1024&&summary.streamCount===1,summary);
    record.outputs.push({...await evidence(file,"video"),...summary,settings});
  }
  check("geometry revision changes actual pixels",!(await frame(3,scene)).equals(await frame(3,revisedScene)));
  check("geometry revision preserves declared duration and canvas",scene.duration_seconds===revisedScene.duration_seconds
    &&scene.width===revisedScene.width&&scene.height===revisedScene.height);
  check("periodic mathematical source closes at sampled points",[0,1,2,3].every(index=>
    JSON.stringify(orbitPoint(index,1,0))===JSON.stringify(orbitPoint(index,1,12))));
} finally {if(browser)await browser.close();}
if(!stillsOnly) {
  const original=JSON.parse(await readFile(resolve(here,"score.json"),"utf8"));
  const revision={...original,transpose:2,melody_gain:original.melody_gain*Math.SQRT1_2};
  let firstEvents;
  for(const [variant,score]of [["original",original],["revision",revision]]) {
    const rendered=renderCue(score),wav=`first-light-${variant}.wav`,mp3=`first-light-${variant}.mp3`;
    await writeFile(resolve(output,wav),wavBytes(rendered),{flag:"wx"});
    await writeFile(resolve(output,`score-${variant}.json`),JSON.stringify(score,null,2)+"\n",{flag:"wx"});
    run(ffmpeg,["-hide_banner","-loglevel","error","-n","-i",resolve(output,wav),"-c:a","libmp3lame","-b:a","192k",
      "-threads","2","-metadata","title=First Light: original twelve-second cue",resolve(output,mp3)],"Encode original music cue");
    run(ffmpeg,["-v","error","-i",resolve(output,mp3),"-f","null","-"],"Decode original music cue");
    const summary=summarizeMedia(probeMedia(ffprobe,resolve(output,mp3)));
    check(variant+" music duration and size",summary.audioCodec==="mp3"&&summary.audioChannels===2
      &&Math.abs(summary.durationSeconds-12)<0.1&&summary.sizeBytes<=2*1024*1024,summary);
    const decoded=run(ffmpeg,["-hide_banner","-i",resolve(output,mp3),"-af","astats=metadata=1:reset=0","-f","null","-"],"Measure decoded cue");
    const peaks=[...decoded.stderr.matchAll(/Peak level dB: (-?[0-9.]+)/g)].map(match=>Number(match[1]));
    check(variant+" decoded music has peak headroom",peaks.length>0&&Math.max(...peaks)<-0.3,{peak_db:Math.max(...peaks)});
    check(variant+" music is a structured multi-voice composition",new Set(rendered.events.map(row=>row.voice)).size===6
      &&score.melody.length===20&&score.chords.length===4&&rendered.rms>0.03&&rendered.peak<0.9,
      {events:rendered.events.length,voices:[...new Set(rendered.events.map(row=>row.voice))],rms:rendered.rms,peak:rendered.peak});
    const repeated=wavBytes(renderCue(score));
    check(variant+" music re-render is byte-identical",repeated.equals(await readFile(resolve(output,wav))));
    if(variant==="original")firstEvents=rendered.events;
    else check("musical revision transposes tonal notes and preserves rhythms",rendered.events.every((row,index)=>
      row.beat===firstEvents[index].beat&&row.length===firstEvents[index].length&&row.voice===firstEvents[index].voice
      &&row.note-firstEvents[index].note===(["pad","bass","melody"].includes(row.voice)?2:0)));
    record.outputs.push({...await evidence(mp3,"music"),...summary,score,events:rendered.events.length,
      pcm_sha256:await sha256(resolve(output,wav)),pcm_peak:rendered.peak,pcm_rms:rendered.rms});
  }
}
check("no external asset request",record.external_requests.length===0);
record.finished_at=new Date().toISOString();record.all_checks_passed=record.checks.every(row=>row.passed);
await writeFile(resolve(output,"verification.json"),JSON.stringify(record,null,2)+"\n",{flag:"wx"});
console.log(JSON.stringify({all_checks_passed:record.all_checks_passed,checks:record.checks.length,outputs:record.outputs.map(row=>({file:row.file,bytes:row.bytes}))}));
