/* Copyright (c) 2026 Alie Jie Li. MIT. Original score and synthesis; no samples or external inputs. */
import {readFile,writeFile} from "node:fs/promises";
import {pathToFileURL} from "node:url";
const TAU=2*Math.PI;
export const frequency = note => 440*2**((note-69)/12);

export function eventsFor(score) {
  if(Object.keys(score).sort().join()!==["record_type","title","tempo_bpm","beats","sample_rate","transpose","melody_gain","chords","melody"].sort().join()
    ||score.record_type!=="baltor_original_cue/v1"||score.sample_rate!==44100||score.beats!==16
    ||typeof score.tempo_bpm!=="number"||!Number.isFinite(score.tempo_bpm)
    ||score.tempo_bpm<65||score.tempo_bpm>120||!Number.isInteger(score.transpose)||Math.abs(score.transpose)>12
    ||typeof score.melody_gain!=="number"||!Number.isFinite(score.melody_gain)||score.melody_gain<=0||score.melody_gain>0.3
    ||!Array.isArray(score.chords)||score.chords.length!==4||!Array.isArray(score.melody)||score.melody.length>64)
    throw Error("Unsupported or unbounded score.");
  const events=[];
  const add=(voice,beat,note,length,gain,pan=0)=>{
    if(![beat,note,length,gain,pan].every(Number.isFinite)||beat<0||beat>=16||length<=0||length>4
      ||note<24||note>96||gain<0||gain>0.3||Math.abs(pan)>0.8)throw Error("Invalid note event.");
    events.push({voice,beat,note:note+(["pad","bass","melody"].includes(voice)?score.transpose:0),length,gain,pan});
  };
  score.chords.forEach((chord,bar)=>{
    if(chord.length!==4)throw Error("Four-note voicings required.");
    chord.forEach((note,index)=>add("pad",bar*4,note,3.95,0.036,(index-1.5)/3.5));
    for(const offset of [0,2,3.5])add("bass",bar*4+offset,chord[0]-12,offset===3.5?0.45:1.2,0.14,-0.04);
    for(const beat of [0,2])add("kick",bar*4+beat,36,0.4,0.17);
    for(const beat of [1,3])add("brush",bar*4+beat,38,0.3,0.05,0.1);
    for(let tick=0;tick<8;tick++)add("hat",bar*4+tick*0.5,42,0.12,tick%2?0.035:0.022,0.32);
  });
  score.melody.forEach(([beat,note,length],index)=>add("melody",beat,note,length,score.melody_gain,index%2?0.12:-0.12));
  return events.sort((a,b)=>a.beat-b.beat||a.voice.localeCompare(b.voice));
}

export function renderCue(score) {
  const events=eventsFor(score), seconds=score.beats*60/score.tempo_bpm,rate=score.sample_rate;
  if(seconds>16)throw Error("Cue exceeds sixteen seconds.");
  const length=Math.round(seconds*rate),left=new Float64Array(length),right=new Float64Array(length);
  let noiseState=0x51f17;
  const noise=()=>{noiseState=(Math.imul(noiseState,1664525)+1013904223)>>>0;return noiseState/2147483648-1;};
  for(const event of events) {
    const start=Math.round(event.beat*60/score.tempo_bpm*rate),duration=event.length*60/score.tempo_bpm;
    const tail=event.voice==="melody"?0.45:0.1,end=Math.min(length,start+Math.round((duration+tail)*rate));
    const hz=frequency(event.note),gainL=Math.sqrt((1-event.pan)/2)*event.gain,gainR=Math.sqrt((1+event.pan)/2)*event.gain;
    let priorNoise=0;
    for(let i=start;i<end;i++) {
      const t=(i-start)/rate,phase=TAU*hz*t;let value;
      if(event.voice==="pad") {
        const envelope=Math.min(1,t/0.22)*Math.min(1,Math.max(0,(duration+0.1-t)/0.35));
        value=(Math.sin(phase)+0.22*Math.sin(phase*2.002)+0.1*Math.sin(phase*3))*envelope;
      } else if(event.voice==="melody") {
        const envelope=Math.min(1,t/0.005)*Math.exp(-3.6*t)*Math.min(1,Math.max(0,(duration+tail-t)/0.12));
        value=(Math.sin(phase)+0.34*Math.sin(2*phase)*Math.exp(-3*t)+0.14*Math.sin(3*phase))*envelope;
      } else if(event.voice==="bass") {
        const envelope=Math.min(1,t/0.012)*Math.exp(-2.8*t)*Math.min(1,Math.max(0,(duration+0.1-t)/0.09));
        value=(Math.sin(phase)-Math.sin(3*phase)/9+Math.sin(5*phase)/25)*envelope;
      } else if(event.voice==="kick") {
        value=Math.sin(TAU*(47*t+1.8*(1-Math.exp(-35*t))))*Math.exp(-17*t)*Math.min(1,t/0.002);
      } else {
        const raw=noise(),high=raw-priorNoise*0.9;priorNoise=raw;
        value=high*Math.exp(-(event.voice==="hat"?70:27)*t)*Math.min(1,t/0.001);
      }
      left[i]+=value*gainL;right[i]+=value*gainR;
    }
  }
  const dryLeft=left.slice(),dryRight=right.slice();
  for(const [delay,gain] of [[0.173,0.15],[0.287,0.1],[0.419,0.065]]) {
    const samples=Math.round(delay*rate);
    for(let i=samples;i<length;i++){left[i]+=dryRight[i-samples]*gain;right[i]+=dryLeft[i-samples]*gain;}
  }
  let peak=0;
  for(let i=0;i<length;i++) {
    const fade=Math.min(1,i/(rate*0.018),(length-1-i)/(rate*0.2));
    left[i]*=fade;right[i]*=fade;peak=Math.max(peak,Math.abs(left[i]),Math.abs(right[i]));
  }
  const scale=0.82/Math.max(peak,0.001);let sum=0;
  for(let i=0;i<length;i++){left[i]*=scale;right[i]*=scale;sum+=left[i]**2+right[i]**2;}
  return {left,right,events,seconds,sample_rate:rate,peak:0.82,rms:Math.sqrt(sum/(length*2))};
}

export function wavBytes(render) {
  const length=render.left.length,body=Buffer.alloc(44+length*4);
  body.write("RIFF",0);body.writeUInt32LE(body.length-8,4);body.write("WAVEfmt ",8);
  body.writeUInt32LE(16,16);body.writeUInt16LE(1,20);body.writeUInt16LE(2,22);
  body.writeUInt32LE(render.sample_rate,24);body.writeUInt32LE(render.sample_rate*4,28);
  body.writeUInt16LE(4,32);body.writeUInt16LE(16,34);body.write("data",36);body.writeUInt32LE(length*4,40);
  for(let i=0;i<length;i++)for(const [channel,values]of [[0,render.left],[1,render.right]])
    body.writeInt16LE(Math.max(-32768,Math.min(32767,Math.round(values[i]*32767))),44+i*4+channel*2);
  return body;
}

if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) {
  if(process.argv.length!==4)throw Error("Use: node music.mjs score.json NEW_OUTPUT.wav");
  const score=JSON.parse(await readFile(process.argv[2],"utf8")),render=renderCue(score);
  await writeFile(process.argv[3],wavBytes(render),{flag:"wx"});
  console.log(JSON.stringify({seconds:render.seconds,events:render.events.length,peak:render.peak,rms:render.rms}));
}
