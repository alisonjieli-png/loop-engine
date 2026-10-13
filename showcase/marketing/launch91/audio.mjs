// Original deterministic instrumental bed. No samples, voice or outside media.
export function composeAudio(seconds=30,sampleRate=48000){
 if(seconds!==30||sampleRate!==48000)throw Error('This score is qualified at30seconds/48kHz');
 const samples=seconds*sampleRate,buffer=Buffer.alloc(44+samples*4);buffer.write('RIFF');buffer.writeUInt32LE(buffer.length-8,4);buffer.write('WAVEfmt ',8);buffer.writeUInt32LE(16,16);buffer.writeUInt16LE(1,20);buffer.writeUInt16LE(2,22);buffer.writeUInt32LE(sampleRate,24);buffer.writeUInt32LE(sampleRate*4,28);buffer.writeUInt16LE(4,32);buffer.writeUInt16LE(16,34);buffer.write('data',36);buffer.writeUInt32LE(samples*4,40);
 const chords=[[130.8128,164.8138,195.9977],[110,130.8128,164.8138],[146.8324,174.6141,220],[97.9989,123.4708,146.8324],[130.8128,164.8138,195.9977],[130.8128,164.8138,261.6256]];
 let peak=0,sum=0;
 for(let i=0;i<samples;i++){
   const t=i/sampleRate,section=Math.min(5,Math.floor(t/5)),chord=chords[section],within=t%5,fade=Math.min(1,t/.6,(seconds-t)/1.2),pad=Math.min(1,within/.3,(5-within)/.35),beat=t%(60/96),pulse=Math.exp(-beat*10);
   const notes=chord.reduce((value,hz,j)=>value+(Math.sin(2*Math.PI*hz*t)+.22*Math.sin(2*Math.PI*hz*2*t))*(.032+.004*Math.sin(t*.6+j)),0)*Math.max(0,pad);
   const bass=Math.sin(2*Math.PI*(chord[0]/2)*t)*.06*pulse;
   const tick=Math.sin(2*Math.PI*1800*t)*Math.sin(2*Math.PI*2317*t)*Math.exp(-beat*95)*.016;
   const tone=(notes+bass+tick)*Math.max(0,fade),left=tone*(.95+.05*Math.sin(t*.2)),right=tone*(.95-.05*Math.sin(t*.2));
   peak=Math.max(peak,Math.abs(left),Math.abs(right));sum+=left*left+right*right;buffer.writeInt16LE(Math.round(left*32767),44+i*4);buffer.writeInt16LE(Math.round(right*32767),46+i*4);
 }
 return {buffer,report:{creator:'Original deterministic Baltor score',samples,sample_rate:sampleRate,channels:2,peak_dbfs:20*Math.log10(peak),rms_dbfs:20*Math.log10(Math.sqrt(sum/(samples*2))),external_samples:0,voice:false}};
}
