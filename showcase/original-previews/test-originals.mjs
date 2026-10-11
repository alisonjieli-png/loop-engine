import test from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {scene,revisedScene,validateScene,orbitPoint} from "./orbit.mjs";
import {eventsFor,frequency,renderCue,wavBytes} from "./music.mjs";
const score=JSON.parse(await readFile(new URL("score.json",import.meta.url),"utf8"));

test("the loop source is periodic, bounded and changes meaningfully",()=>{
  for(const settings of [scene,revisedScene])for(let index=0;index<25;index++) {
    const point=orbitPoint(index/25*Math.PI*2,index%settings.ribbons,0,settings);
    assert.deepEqual(point,orbitPoint(index/25*Math.PI*2,index%settings.ribbons,12,settings));
    assert.ok(point.x>20&&point.x<940&&point.y>20&&point.y<520);
  }
  assert.notDeepEqual(orbitPoint(1,1,3,scene),orbitPoint(1,1,3,revisedScene));
  assert.equal(scene.duration_seconds,revisedScene.duration_seconds);
  for(const change of [{duration_seconds:17},{fps:240},{ribbons:0},{record_type:"unknown"},{extra:true}])
    assert.throws(()=>validateScene({...scene,...change}));
});
test("pitch and arrangement have known musical identities",()=>{
  assert.equal(frequency(69),440);
  assert.equal(frequency(81),880);
  const events=eventsFor(score);
  assert.equal(events.length,96);
  assert.equal(new Set(events.map(row=>row.voice)).size,6);
  assert.equal(events.filter(row=>row.voice==="melody").length,20);
  assert.equal(events.filter(row=>row.voice==="pad").length,16);
  assert.ok(new Set(events.filter(row=>row.voice==="melody").map(row=>row.note)).size>6);
});
test("the transposed revision retains rhythm and percussion",()=>{
  const original=eventsFor(score),revised=eventsFor({...score,transpose:2,melody_gain:score.melody_gain*Math.SQRT1_2});
  for(let i=0;i<original.length;i++) {
    assert.equal(original[i].beat,revised[i].beat);
    assert.equal(original[i].length,revised[i].length);
    const tonal=["pad","bass","melody"].includes(original[i].voice);
    assert.equal(revised[i].note-original[i].note,tonal?2:0);
  }
});
test("PCM render is deterministic, non-silent and has headroom",()=>{
  const a=renderCue(score),b=renderCue(score);
  assert.equal(a.seconds,12);
  assert.ok(a.rms>0.03&&a.rms<0.3);
  const bytes=wavBytes(a);
  assert.ok(bytes.equals(wavBytes(b)));
  assert.equal(bytes.subarray(0,4).toString(),"RIFF");
  assert.equal(bytes.readUInt32LE(24),44100);
  assert.equal(bytes.readUInt16LE(22),2);
  assert.equal(bytes.length,44+12*44100*4);
  let peak=0;for(const side of [a.left,a.right])for(const sample of side)peak=Math.max(peak,Math.abs(sample));
  assert.ok(peak>0.8&&peak<0.83);
  const silent={...a,left:new Float64Array(a.left.length),right:new Float64Array(a.right.length)};
  assert.notDeepEqual(wavBytes(silent),bytes);
});
test("unbounded or mismatched score input is refused before rendering",()=>{
  for(const change of [{tempo_bpm:0},{tempo_bpm:1},{tempo_bpm:NaN},{tempo_bpm:"invalid"},{tempo_bpm:"80"},
    {sample_rate:1000000},{beats:100000},{transpose:999},
    {melody_gain:NaN},{record_type:"unknown"},{melody:[[0,999,1]]},{extra:true}])
    assert.throws(()=>renderCue({...score,...change}));
});
