import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {DURATION,FPS,SHOTS,shotAt,ease,inspectTimeline} from './timeline.mjs';
import {composeAudio} from './audio.mjs';

test('timeline covers exactly30seconds with explicit factual constraints',()=>{assert.equal(DURATION,30);assert.equal(FPS,24);assert.deepEqual(inspectTimeline(),[]);for(let i=0;i<720;i++)assert(shotAt(i/24));assert.equal(shotAt(30).id,'close');});
test('invalid time is refused',()=>{for(const value of [-1,31,NaN,Infinity,'1'])assert.throws(()=>shotAt(value));});
test('wrong duration and missing localPreview are detected',()=>{assert(inspectTimeline(SHOTS.slice(0,-1)).length);assert(inspectTimeline(SHOTS.map(s=>s.id==='afk'?{...s,note:'Hosted work while you sleep.'}:s)).length);});
test('easing is finite clamped and monotone',()=>{let before=-1;for(let i=-10;i<=110;i++){const value=ease(i/100);assert(value>=0&&value<=1&&value>=before);before=value;}});
test('score is original deterministic stereo PCM with headroom',()=>{const a=composeAudio(),b=composeAudio();assert.deepEqual(a.buffer,b.buffer);assert.equal(a.buffer.subarray(0,4).toString(),'RIFF');assert.equal(a.report.external_samples,0);assert.equal(a.report.voice,false);assert.equal(a.report.sample_rate,48000);assert(a.report.peak_dbfs<-3);assert(a.report.rms_dbfs>-40);assert.throws(()=>composeAudio(120));});
test('actual AFK download is named, not an inventedjson file',async()=>{const source=await readFile(new URL('./scene.mjs',import.meta.url),'utf8');assert(source.includes('baltor-tasks.txt'));assert(!source.includes('manifest.json'));});
test('the three treatments declare different mechanisms',async()=>{const source=await readFile(new URL('./scene.mjs',import.meta.url),'utf8'),world=await readFile(new URL('./world.mjs',import.meta.url),'utf8');assert(source.includes('translate3d'));assert(source.includes('translateX'));assert(world.includes('ExtrudeGeometry'));assert(world.includes('PerspectiveCamera'));assert(world.includes('GLTFExporter'));});
test('source contains no remote imports or customer effects',async()=>{for(const file of ['scene.mjs','world.mjs','audio.mjs']){const source=await readFile(new URL('./'+file,import.meta.url),'utf8');for(const forbidden of ['fetch(','localStorage','sessionStorage','document.cookie','https://','XMLHttpRequest'])assert(!source.includes(forbidden),file+':'+forbidden);}});
test('walkthrough encodes captured duration rather than browser shutdown time',async()=>{const source=await readFile(new URL('./walkthrough.mjs',import.meta.url),'utf8');assert(source.includes('const duration=Number(rawProbe.format.duration)'));assert(!source.includes('duration=(Date.now()-start)/1000'));});
