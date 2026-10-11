/* Copyright (c) 2026 Alie Jie Li. MIT. Original mathematical drawing, no external assets. */
export const scene = Object.freeze({record_type:"baltor_orbit_example/v1", width:960, height:540,
  duration_seconds:12, fps:24, ribbons:12, winding:3, radius:138, tube:58, tilt:0.82});
export const revisedScene = Object.freeze({...scene, ribbons:8, winding:2, radius:155, tube:48});

export function validateScene(value) {
  if (Object.keys(value).sort().join() !== Object.keys(scene).sort().join() || value.record_type !== scene.record_type)
    throw Error("Unknown scene shape.");
  for (const [key, low, high] of [["width",320,1920],["height",180,1080],["duration_seconds",2,16],
    ["fps",12,30],["ribbons",4,20],["winding",2,5],["radius",80,180],["tube",25,70],["tilt",0,1.5]])
    if (!Number.isFinite(value[key]) || value[key] < low || value[key] > high) throw Error("Out of bounds: " + key);
  for (const key of ["width","height","fps","ribbons","winding"]) if (!Number.isInteger(value[key])) throw Error("Integer required: " + key);
  return value;
}

export function orbitPoint(u, ribbon, seconds, settings=scene) {
  const phase = 2 * Math.PI * (((seconds % settings.duration_seconds) + settings.duration_seconds) % settings.duration_seconds) / settings.duration_seconds;
  const offset = ribbon / settings.ribbons * 2 * Math.PI;
  const v = settings.winding * u + offset + 0.28 * Math.sin(phase);
  const radius = settings.radius + settings.tube * Math.cos(v);
  const x = radius * Math.cos(2*u), y = radius * Math.sin(2*u), z = settings.tube * Math.sin(v);
  const yaw = 0.58 * Math.sin(phase), pitch = settings.tilt + 0.12 * Math.sin(phase);
  const xx = x*Math.cos(yaw) + z*Math.sin(yaw), zz = z*Math.cos(yaw) - x*Math.sin(yaw);
  const yy = y*Math.cos(pitch) - zz*Math.sin(pitch), depth = y*Math.sin(pitch) + zz*Math.cos(pitch);
  const perspective = 780 / (780 - depth);
  return {x:settings.width/2 + xx*perspective, y:settings.height/2 + yy*perspective,
    depth, brightness:(Math.cos(v - phase)*0.5+0.5)};
}

export function drawOrbit(canvas, seconds, settings=scene) {
  validateScene(settings);
  canvas.width=settings.width; canvas.height=settings.height;
  const ctx=canvas.getContext("2d",{alpha:false}), w=settings.width,h=settings.height;
  const ground=ctx.createRadialGradient(w*0.5,h*0.42,10,w*0.5,h*0.5,w*0.65);
  ground.addColorStop(0,"#36201a"); ground.addColorStop(0.6,"#1c1519"); ground.addColorStop(1,"#10151e");
  ctx.fillStyle=ground; ctx.fillRect(0,0,w,h);
  ctx.fillStyle="#f4d5b418";
  for(let y=24;y<h;y+=24)for(let x=24;x<w;x+=24){ctx.beginPath();ctx.arc(x,y,0.55,0,Math.PI*2);ctx.fill();}
  const shadow=ctx.createRadialGradient(w/2,h*0.87,0,w/2,h*0.87,190);
  shadow.addColorStop(0,"#00000088");shadow.addColorStop(1,"#00000000");
  ctx.save();ctx.translate(0,h*0.7);ctx.scale(1,0.2);ctx.fillStyle=shadow;ctx.fillRect(0,0,w,h);ctx.restore();
  const segments=[],steps=180;
  for(let band=0;band<settings.ribbons;band++)for(let step=0;step<steps;step++) {
    const a=orbitPoint(step/steps*Math.PI*2,band,seconds,settings);
    const b=orbitPoint((step+1)/steps*Math.PI*2,band,seconds,settings);
    segments.push({a,b,depth:(a.depth+b.depth)/2,band});
  }
  segments.sort((a,b)=>a.depth-b.depth);
  ctx.lineCap="round";
  for(const segment of segments) {
    const light=Math.max(0,Math.min(1,(segment.depth+220)/440));
    const bright=segment.a.brightness;
    const red=Math.round(162+93*light),green=Math.round(64+133*light+10*bright),blue=Math.round(32+128*light);
    ctx.strokeStyle=`rgb(${red},${green},${blue})`;
    ctx.lineWidth=2.1+1.6*light;
    ctx.beginPath();ctx.moveTo(segment.a.x,segment.a.y);ctx.lineTo(segment.b.x,segment.b.y);ctx.stroke();
  }
  ctx.strokeStyle="#f5d8b428";ctx.lineWidth=1;ctx.strokeRect(20.5,20.5,w-41,h-41);
  return {segments:segments.length, seconds, source:"original mathematical curves", settings};
}
