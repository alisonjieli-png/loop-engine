import * as THREE from 'three';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {EffectComposer} from 'three/addons/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/addons/postprocessing/RenderPass.js';
import {UnrealBloomPass} from 'three/addons/postprocessing/UnrealBloomPass.js';
import {OutputPass} from 'three/addons/postprocessing/OutputPass.js';
import {character} from './characters.mjs';
import {createWorld} from './world.mjs';
import {advance,createState,spawnWave} from './simulation.mjs';

const $=id=>document.getElementById(id);
const canvas=$('world');
let renderer;
try{renderer=new THREE.WebGLRenderer({canvas,antialias:true,preserveDrawingBuffer:true});}
catch(error){
  const warning=document.createElement('div');warning.className='fatal';
  warning.textContent='This scene needs WebGL 2. Enable hardware acceleration in your browser, then reload.';
  $('arena').append(warning);throw error;
}
const gl=renderer.getContext(),debugInfo=gl.getExtension('WEBGL_debug_renderer_info');
const rendererName=debugInfo?String(gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL)):'';
const reducedEffects=/swiftshader|llvmpipe|software/i.test(rendererName)||matchMedia('(pointer: coarse)').matches;
renderer.setPixelRatio(reducedEffects?1:Math.min(devicePixelRatio,1.7));renderer.shadowMap.enabled=!reducedEffects;
renderer.shadowMap.type=THREE.PCFSoftShadowMap;renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure=1.25;
renderer.info.autoReset=false;
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(47,1,.1,160);
const world=createWorld(scene),actors=new THREE.Group();actors.name='Characters';scene.add(actors);
let hero=character('Warden');actors.add(hero.root);
let state=createState();state.obstacles=world.obstacles;spawnWave(state);
const enemies=new Map(),particles=[];
let started=false,paused=true,motion='game',cameraAngle=0,cameraHeight=12,cameraDistance=15;
let move={x:0,z:0},keys=new Set(),attack=false,dodge=false,accumulator=0,last=performance.now(),noticeUntil=0;
let sound=false,audio=null,uiElapsed=0,theme='dusk',exporting=false;
let drag=null,orbitMoved=false,visibleFrames=0;
const composer=new EffectComposer(renderer);composer.addPass(new RenderPass(scene,camera));
const bloom=new UnrealBloomPass(new THREE.Vector2(1,1),.35,.65,.95);bloom.enabled=!reducedEffects;composer.addPass(bloom);composer.addPass(new OutputPass());
function resize(){const w=innerWidth,h=innerHeight;renderer.setSize(w,h);composer.setSize(w,h);camera.aspect=w/h;camera.updateProjectionMatrix();}
resize();addEventListener('resize',resize);
function notify(message,seconds=3){$('notice').textContent=message;noticeUntil=performance.now()+seconds*1000;$('notice').classList.add('visible');}
function tone(frequency,duration=.12){
  if(!sound||!audio)return;
  const osc=audio.createOscillator(),gain=audio.createGain();osc.type='triangle';
  osc.frequency.setValueAtTime(frequency,audio.currentTime);osc.frequency.exponentialRampToValueAtTime(frequency*.45,audio.currentTime+duration);
  gain.gain.setValueAtTime(.045,audio.currentTime);gain.gain.exponentialRampToValueAtTime(.0001,audio.currentTime+duration);
  osc.connect(gain);gain.connect(audio.destination);osc.start();osc.stop(audio.currentTime+duration);
}
function spawnVisuals(){
  const ids=new Set(state.enemies.map(e=>e.id));
  for(const [id,rig] of enemies){if(!ids.has(id)){actors.remove(rig.root);dispose(rig.root);enemies.delete(id);}}
  for(const enemy of state.enemies)if(!enemies.has(enemy.id)){const rig=character(enemy.id,true);actors.add(rig.root);enemies.set(enemy.id,rig);}
}
function dispose(root){root.traverse(object=>{object.geometry?.dispose();if(object.material){for(const m of [object.material].flat())m.dispose();}});}
spawnVisuals();
function reset(){
  state=createState();state.obstacles=world.obstacles;spawnWave(state);spawnVisuals();
  started=true;paused=false;motion='game';$('motion').value='game';$('curtain').hidden=true;
  $('pause').textContent='Pause';cameraAngle=0;keys.clear();move={x:0,z:0};attack=false;dodge=false;
  updateUI();canvas.focus();return inspect();
}
function togglePause(){
  if(!started){reset();return;}
  paused=!paused;$('pause').textContent=paused?'Resume':'Pause';keys.clear();move={x:0,z:0};
  if(motion!=='game')notify('Choose Gameplay to resume combat.');
}
function updateUI(){
  $('health-label').textContent=String(Math.round(state.health));
  $('health-fill').style.width=`${state.health}%`;$('stamina-fill').style.width=`${state.stamina}%`;
  document.querySelector('.health-track').setAttribute('aria-valuenow',String(Math.round(state.health)));
  document.querySelector('.stamina-track').setAttribute('aria-valuenow',String(Math.round(state.stamina)));
  $('wave').textContent=`Wave ${state.wave} / 3`;
  const alive=state.enemies.filter(e=>!e.dead).length;$('remaining').textContent=`${alive} goblin${alive===1?'':'s'}`;
  $('wave-fill').style.width=`${state.defeated/12*100}%`;
  $('objective').textContent=motion==='game'?'Hold the gate. Defeat three waves.':`${motion} animation study. Combat is paused.`;
  if(started && state.phase!=='playing'){
    $('curtain').hidden=false;$('curtain-title').textContent=state.phase==='victory'?'The gate holds.':'A warden rises again.';
    $('curtain-copy').textContent=state.phase==='victory'?'The ruins are quiet. Keep exploring the animations, or defend them once more.':'Watch the goblins wind up. Dodge, turn, and strike back.';
    $('begin').textContent='Play again →';paused=true;$('pause').textContent='Resume';
  }
}
function burst(x,z,color,count=10){
  for(let i=0;i<count;i++){
    const m=new THREE.Mesh(new THREE.OctahedronGeometry(.045),new THREE.MeshBasicMaterial({color}));
    m.position.set(x,1.1,z);scene.add(m);particles.push({mesh:m,life:.5,v:new THREE.Vector3((Math.random()-.5)*4,Math.random()*3,(Math.random()-.5)*4)});
  }
}
function handleEvents(){
  for(const event of state.events){
    if(event.type==='hit'){burst(event.x,event.z,0xffdf91);tone(250);}
    else if(event.type==='defeat'){burst(event.x,event.z,0x88e8bc,18);tone(610,.25);}
    else if(event.type==='swing')tone(130,.13);
    else if(event.type==='hurt'){$('hurt-flash').style.opacity='1';setTimeout(()=>$('hurt-flash').style.opacity='0',160);tone(75,.22);}
    else if(event.type==='wave'){spawnVisuals();notify(`Wave ${state.wave}. Hold your ground.`);}
  }
}
function controls(){
  const x=(keys.has('KeyD')?1:0)-(keys.has('KeyA')?1:0)+move.x;
  const z=(keys.has('KeyS')?1:0)-(keys.has('KeyW')?1:0)+move.z;
  const input={x:x*Math.cos(cameraAngle)+z*Math.sin(cameraAngle),z:z*Math.cos(cameraAngle)-x*Math.sin(cameraAngle),
    attack:attack||keys.has('KeyJ'),dodge,sprint:keys.has('ShiftLeft')||keys.has('ShiftRight')};
  attack=false;dodge=false;return input;
}
function updateActors(dt){
  hero.root.position.set(state.hero.x,0,state.hero.z);hero.root.rotation.y=state.hero.yaw;
  const name=motion!=='game'?motion:state.hero.attack>0?'Sword':state.hero.moving?'Run':'Idle';
  hero.play(name);hero.mixer.update(dt);
  for(const enemy of state.enemies){
    const rig=enemies.get(enemy.id);if(!rig)continue;
    rig.root.position.set(enemy.x,enemy.dead?-.5:0,enemy.z);rig.root.rotation.y=enemy.yaw;
    rig.root.rotation.z=enemy.dead?Math.PI/2:enemy.stagger>0?-.12:0;
    rig.play(enemy.attack>0?'Sword':enemy.moving?'Run':'Idle');rig.mixer.update(enemy.dead?0:dt);
    rig.root.visible=motion==='game';
  }
}
function frame(now){
  const dt=Math.min(.05,(now-last)/1000);last=now;
  if(!paused&&motion==='game'&&document.visibilityState==='visible'){
    accumulator+=dt;
    while(accumulator>=1/60){advance(state,controls(),1/60);handleEvents();accumulator-=1/60;}
  }else{accumulator=0;state.hero.moving=false;}
  updateActors((!paused||motion!=='game'||!started)?dt:0);
  const target=new THREE.Vector3(state.hero.x*.68,1,state.hero.z*.68-1.9);
  if(motion!=='game'){target.set(state.hero.x,1.2,state.hero.z);}
  const dist=motion!=='game'?5.6:cameraDistance,height=motion!=='game'?2.8:cameraHeight;
  const position=target.clone().add(new THREE.Vector3(Math.sin(cameraAngle)*dist,height,Math.cos(cameraAngle)*dist));
  camera.position.lerp(position,1-Math.exp(-dt*3));camera.lookAt(target);
  world.update(now/1000);
  for(let i=particles.length-1;i>=0;i--){const p=particles[i];p.life-=dt;p.mesh.position.addScaledVector(p.v,dt);p.v.y-=dt*5;if(p.life<=0){scene.remove(p.mesh);dispose(p.mesh);particles.splice(i,1);}}
  renderer.info.reset();composer.render();visibleFrames++;
  uiElapsed+=dt;if(uiElapsed>.1){updateUI();uiElapsed=0;}
  if(now>noticeUntil)$('notice').classList.remove('visible');
  requestAnimationFrame(frame);
}
camera.position.set(15,18,23);camera.lookAt(0,0,-3);requestAnimationFrame(frame);
$('begin').addEventListener('click',reset);$('pause').addEventListener('click',togglePause);
$('sound').addEventListener('click',()=>{sound=!sound;if(sound){audio??=new AudioContext();audio.resume();tone(440);} $('sound').textContent=sound?'Sound on':'Sound off';$('sound').setAttribute('aria-pressed',String(sound));});
function setMotion(value){
  const choices=['game',...hero.clips.map(c=>c.name)];if(!choices.includes(value))throw new Error('Unknown animation.');
  motion=value;$('motion').value=value;
  if(value!=='game'){$('curtain').hidden=true;paused=true;$('pause').textContent='Resume';state.hero.yaw=0;}
  else if(started){paused=false;$('pause').textContent='Pause';}
  updateUI();return inspect();
}
function setEnvironment(value){if(!['dusk','dawn','astral'].includes(value))throw new Error('Unknown environment.');theme=value;world.atmosphere(value);$('atmosphere').value=value;return inspect();}
$('motion').addEventListener('change',e=>setMotion(e.target.value));$('atmosphere').addEventListener('change',e=>setEnvironment(e.target.value));
addEventListener('keydown',e=>{
  if(['INPUT','SELECT','TEXTAREA','BUTTON'].includes(document.activeElement?.tagName))return;
  if(['KeyW','KeyA','KeyS','KeyD','Space','KeyJ','ShiftLeft','ShiftRight','Escape'].includes(e.code))e.preventDefault();
  if(e.code==='Escape'&&!e.repeat)togglePause();
  if(e.code==='Space'&&!e.repeat)dodge=true;keys.add(e.code);
});
addEventListener('keyup',e=>keys.delete(e.code));addEventListener('blur',()=>{keys.clear();move={x:0,z:0};attack=false;dodge=false;});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&started){paused=true;$('pause').textContent='Resume';keys.clear();move={x:0,z:0};}});
canvas.addEventListener('contextmenu',e=>e.preventDefault());
canvas.addEventListener('pointerdown',e=>{drag={x:e.clientX,y:e.clientY,id:e.pointerId};orbitMoved=false;canvas.setPointerCapture(e.pointerId);canvas.focus();});
canvas.addEventListener('pointermove',e=>{if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;if(Math.abs(dx)+Math.abs(dy)>2)orbitMoved=true;cameraAngle-=dx*.006;cameraHeight=Math.max(5,Math.min(21,cameraHeight+dy*.025));drag.x=e.clientX;drag.y=e.clientY;});
canvas.addEventListener('pointerup',()=>{if(!orbitMoved&&started&&motion==='game')attack=true;drag=null;});canvas.addEventListener('pointercancel',()=>drag=null);
canvas.addEventListener('wheel',e=>{e.preventDefault();cameraDistance=Math.max(8,Math.min(24,cameraDistance+e.deltaY*.015));},{passive:false});
const joystick=$('joystick');
joystick.addEventListener('pointerdown',e=>{joystick.setPointerCapture(e.pointerId);joystickMove(e);});
joystick.addEventListener('pointermove',e=>{if(joystick.hasPointerCapture(e.pointerId))joystickMove(e);});
function joystickMove(e){const box=joystick.getBoundingClientRect(),x=e.clientX-box.left-box.width/2,z=e.clientY-box.top-box.height/2;const d=Math.max(32,Math.hypot(x,z));move={x:x/d,z:z/d};$('stick').style.transform=`translate(${move.x*29}px,${move.z*29}px)`;}
for(const name of ['pointerup','pointercancel'])joystick.addEventListener(name,()=>{move={x:0,z:0};$('stick').style.transform='';});
$('touch-attack').addEventListener('pointerdown',()=>attack=true);$('touch-dodge').addEventListener('pointerdown',()=>dodge=true);
function download(bytes,name,type){const url=URL.createObjectURL(new Blob([bytes],{type}));const link=document.createElement('a');link.href=url;link.download=name;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('frame').addEventListener('click',()=>{composer.render();canvas.toBlob(blob=>{if(blob){download(blob,'ashen-wilds.png','image/png');notify('Frame saved.');}else notify('Could not capture this frame.');});});
async function exportGlb(onlyCharacter){
  if(exporting)return;exporting=true;const wasPaused=paused;paused=true;
  const buttons=[$('export-character'),$('export-scene')];buttons.forEach(b=>b.disabled=true);
  try{
    const clips=onlyCharacter?hero.clips:[...hero.clips,...[...enemies.values()].flatMap(r=>r.clips)];
    const bytes=await new GLTFExporter().parseAsync(onlyCharacter?hero.root:scene,{binary:true,animations:clips,onlyVisible:onlyCharacter});
    download(bytes,onlyCharacter?'baltor-warden.glb':'ashen-wilds.glb','model/gltf-binary');
    notify('GLB saved with editable geometry and animation clips.');
  }catch(error){notify(`Export failed: ${error.message}`,6);}
  finally{paused=wasPaused;exporting=false;buttons.forEach(b=>b.disabled=false);}
}
$('export-character').addEventListener('click',()=>exportGlb(true));$('export-scene').addEventListener('click',()=>exportGlb(false));
$('briefs').addEventListener('click',async()=>{try{const response=await fetch('./asset-briefs.json');if(!response.ok)throw new Error('Asset briefs are unavailable.');download(await response.text(),'baltor-asset-briefs.json','application/json');}catch(error){notify(error.message);}});
$('character-file').addEventListener('change',async e=>{
  const file=e.target.files[0];if(!file)return;
  const wasPaused=paused;paused=true;
  try{
    if(file.size>64*1024*1024)throw new Error('This browser preview accepts GLB files up to 64 MiB.');
    const bytes=await file.arrayBuffer();if(bytes.byteLength<12||new DataView(bytes).getUint32(0,true)!==0x46546c67)throw new Error('Choose a binary glTF (.glb) file.');
    const manager=new THREE.LoadingManager();manager.setURLModifier(url=>{if(!url.startsWith('blob:')&&!url.startsWith('data:'))throw new Error('Use a self-contained GLB with embedded assets.');return url;});
    const loaded=await new GLTFLoader(manager).parseAsync(bytes,'');
    const bounds=new THREE.Box3().setFromObject(loaded.scene),size=bounds.getSize(new THREE.Vector3());
    if(!Number.isFinite(size.y)||size.y<=0)throw new Error('The model has no usable geometry.');
    const center=bounds.getCenter(new THREE.Vector3());loaded.scene.position.set(-center.x,-bounds.min.y,-center.z);
    const wrapper=new THREE.Group();wrapper.add(loaded.scene);wrapper.scale.setScalar(2.35/size.y);
    wrapper.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
    actors.remove(hero.root);dispose(hero.root);actors.add(wrapper);
    const mixer=new THREE.AnimationMixer(wrapper),actions=new Map(loaded.animations.map(c=>[c.name,mixer.clipAction(c)]));let current='';
    hero={root:wrapper,clips:loaded.animations,mixer,play(name){
      const target=actions.has(name)?name:[...actions.keys()].find(n=>n.toLowerCase().includes(name.toLowerCase()));
      if(!target||current===target)return;mixer.stopAllAction();actions.get(target).play();current=target;
    }};
    $('motion').replaceChildren(...['game',...hero.clips.map(c=>c.name)].map(name=>{const option=document.createElement('option');option.value=name;option.textContent=name==='game'?'Gameplay':name;return option;}));
    $('motion-note').textContent=hero.clips.length?`${hero.clips.length} animation clips supplied by this file.`:'This model has no animation clips. The preview does not create a rig.';
    motion='game';notify('Character loaded in this tab.');
  }catch(error){notify(`Import failed: ${error.message}`,7);}
  finally{paused=wasPaused;e.target.value='';}
});
function inspect(){return {record_type:'fantasy_arena_observation/v1',phase:state.phase,started,paused,motion,environment:theme,
  wave:state.wave,health:state.health,stamina:Math.round(state.stamina),defeated:state.defeated,
  hero:{x:state.hero.x,z:state.hero.z,yaw:state.hero.yaw},enemies:state.enemies.map(e=>({id:e.id,x:e.x,z:e.z,health:e.health,dead:e.dead})),
  animations:hero.clips.map(c=>c.name),renderedFrames:visibleFrames,graphicsProfile:reducedEffects?'reduced_effects':'full_effects',renderer:renderer.info.render};}
const tools=[{name:'inspect_fantasy_arena',description:'Read the visible game state and available character animations.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true},execute(input){if(!input||Object.keys(input).length)throw new Error('Expected an empty object.');return inspect();}},
  {name:'configure_fantasy_arena',description:'Change the environment or preview a character animation. Animation preview pauses combat.',inputSchema:{type:'object',properties:{environment:{type:'string',enum:['dusk','dawn','astral']},motion:{type:'string'}},additionalProperties:false},annotations:{readOnlyHint:false},execute(input){
    if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).some(k=>!['environment','motion'].includes(k)))throw new Error('Expected environment or motion settings.');
    if(input.environment!==undefined&&!['dusk','dawn','astral'].includes(input.environment))throw new Error('Unknown environment.');
    if(input.motion!==undefined&&!['game',...hero.clips.map(c=>c.name)].includes(input.motion))throw new Error('Unknown animation.');
    if(input.environment!==undefined)setEnvironment(input.environment);if(input.motion!==undefined)setMotion(input.motion);return inspect();}},
  {name:'restart_fantasy_arena',description:'Restart the visible game with full health and the first goblin wave.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:false},execute(input){if(!input||Object.keys(input).length)throw new Error('Expected an empty object.');return reset();}}];
const registry=document.modelContext,lifecycle=new AbortController();
if(registry?.registerTool)for(const tool of tools){try{Promise.resolve(registry.registerTool(tool,{signal:lifecycle.signal})).catch(()=>{});}catch{}}
addEventListener('pagehide',()=>lifecycle.abort(),{once:true});
// Read-back is useful for local browser qualification and does not bypass game rules.
window.baltorArena=Object.freeze({inspect});
updateUI();
