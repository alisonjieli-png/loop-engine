import {DURATION,FPS,SHOTS,shotAt,ease,clamp} from './timeline.mjs';
const treatment=new URLSearchParams(location.search).get('treatment')||'2d';
if(!['2d','2.5d','3d'].includes(treatment))throw Error('Unsupported rendering treatment');
document.body.dataset.treatment=treatment;
const flat=document.querySelector('#flat');let active='';let world=null;
const card=(tag,title,copy,kind='')=>`<div class="card ${kind}"><span class="tag">${tag}</span><strong>${title}</strong><small>${copy}</small><span class="line"></span><span class="line"></span></div>`;
function flatContents(id){
 if(id==='intro')return card('The human relay','Read. Filter. Copy. Paste.','Somebody’s take becomes your agent’s context.','dark')+card('A direct reading job','Sources → your agent','You set the question and check the evidence.','accent');
 if(id==='feeds')return card('01 / Source collection','Compare the evidence','Original references and research questions.')+card('02 / Reading profile','profile.json','A reading list for this agent.','accent')+card('03 / Reading guide','READING.md','Use your own agent and web access.','dark');
 if(id==='foundry')return card('Explore','Component examples','See the output before choosing a starting point.')+card('Inspect','Source + use conditions','Check requirements, version and licence.','accent')+card('Take it to your tools','Reusable working files','Download access follows the existing account rules.','dark');
 if(id==='afk')return card('Ready task / 01','Review the inputs','Write the permitted work and completion checks.')+card('Ready task / 02','Arrange the local plan','The current worker follows manifest order.','accent')+card('Actual download filename','baltor-tasks.txt','You start the worker. No cloud execution here.','dark');
 return '<div class="closing-list"><div>AgentFeeds<small>agentfeeds.si</small></div><div>AgentFoundry<small>getagentfoundry.si</small></div><div>AgentAFK <small>agentafk.si · Local Preview</small></div></div>';
}
if(treatment==='3d'){const module=await import('./world.mjs');world=await module.createWorld(document.querySelector('#world'));}
function render(seconds){
 const shot=shotAt(seconds),local=seconds-shot.start,index=SHOTS.indexOf(shot),enter=ease(local/.65),exit=1-clamp((local-(shot.end-shot.start-.35))/.35)*.15;
 document.documentElement.style.setProperty('--accent',shot.accent);
 if(active!==shot.id){active=shot.id;document.querySelector('#kicker').textContent=shot.label;document.querySelector('#headline').textContent=shot.title;document.querySelector('#copy').textContent=shot.copy;document.querySelector('#url').textContent=shot.url;document.querySelector('#note').textContent=shot.note;document.querySelector('#scene-number').textContent=`0${index+1} / 05`;flat.innerHTML=flatContents(shot.id);}
 const words=document.querySelector('#words');words.style.opacity=String(.3+.7*enter);words.style.transform=`translateY(${(1-enter)*22}px)`;
 if(world)world.render(shot.id,seconds,local);
 else{
   const cards=[...flat.querySelectorAll('.card')];
   cards.forEach((node,i)=>{
     const reveal=ease((local-i*.17)/.75),two=treatment==='2d';
     node.style.left=(two?i%2*8:5+i*1.5)+'%';node.style.top=((cards.length===2?12:4)+i*(cards.length===2?45:31))+'%';
     node.style.opacity=String(reveal*exit);
     node.style.transform=two?`translateX(${(1-reveal)*50+Math.sin(seconds*.7+i)*3}px)`:`translate3d(${Math.sin(seconds*.65+i)*10}px,${(1-reveal)*45+Math.sin(seconds*.7+i)*9}px,${i*45}px) rotateY(${-11+Math.sin(seconds*.35)*5}deg) rotateX(${7+Math.cos(seconds*.4)*3}deg) rotateZ(${-3+i*2}deg)`;
     node.querySelectorAll('.line').forEach((line,j)=>{line.style.transformOrigin='left';line.style.transform=`scaleX(${.83+.17*Math.sin(seconds*.9+i+j)})`;});
   });
   flat.querySelectorAll('.closing-list>div').forEach((node,i)=>{const reveal=ease((local-i*.16)/.55);node.style.opacity=String(reveal);node.style.transform=`translateX(${(1-reveal)*40}px)`;});
 }
 document.querySelector('#progress').style.width=seconds/DURATION*100+'%';
 return {shot:shot.id,time:seconds,treatment};
}
function inspect(){
 const ids=['kicker','headline','copy','url','note'];
 const textBounds=ids.map(id=>{const el=document.getElementById(id),b=el.getBoundingClientRect();return{id,text:el.textContent,left:b.left,top:b.top,right:b.right,bottom:b.bottom,visible:getComputedStyle(el).opacity!=='0'};});
 return {treatment,duration:DURATION,fps:FPS,textBounds,overflow:document.documentElement.scrollWidth>innerWidth||document.documentElement.scrollHeight>innerHeight,three:world?.inspect()||null};
}
window.launch91={render,inspect,exportScene:()=>world?.exportScene()};render(0);window.launch91.ready=true;
if(new URLSearchParams(location.search).get('play')==='1'){const started=performance.now();function tick(now){render(((now-started)/1000)%DURATION);requestAnimationFrame(tick);}requestAnimationFrame(tick);}
