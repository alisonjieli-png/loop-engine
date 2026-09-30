import test from 'node:test';
import assert from 'node:assert/strict';
import {advance,createState,spawnWave,RULES} from '../src/simulation.mjs';

const ticks=(state,input,count)=>{for(let i=0;i<count;i++)advance(state,input,1/60);};
test('movement stops at the arena boundary and at solid props',()=>{
  const state=createState();state.obstacles=[{x:0,z:8,radius:1}];
  ticks(state,{z:1},120);assert.ok(state.hero.z<6.56);
  ticks(state,{x:1},600);assert.ok(Math.hypot(state.hero.x,state.hero.z)<=RULES.radius-RULES.heroRadius+.01);
});
test('a sword hit needs both range and facing',()=>{
  const state=createState();state.hero={...state.hero,x:0,z:0,yaw:0};
  spawnWave(state);state.enemies=state.enemies.slice(0,2);
  Object.assign(state.enemies[0],{x:0,z:1,cooldown:100,stagger:100});
  Object.assign(state.enemies[1],{x:0,z:-1,cooldown:100,stagger:100});
  advance(state,{attack:true},1/60);ticks(state,{},20);
  assert.equal(state.enemies[0].health,34);assert.equal(state.enemies[1].health,68);
});
test('dodging consumes stamina and prevents damage during its window',()=>{
  const state=createState();spawnWave(state);const enemy=state.enemies[0];
  Object.assign(enemy,{x:state.hero.x,z:state.hero.z+1,attack:.17,cooldown:10});
  advance(state,{dodge:true,x:1},1/60);advance(state,{},1/60);
  assert.equal(state.health,100);assert.ok(state.stamina<80);assert.ok(state.hero.invulnerable>0);
});
test('three completed waves end the game and restart state is independent',()=>{
  const state=createState();spawnWave(state);
  for(let wave=1;wave<=3;wave++){
    state.enemies.forEach(e=>{e.dead=true;e.health=0;});ticks(state,{},185);
  }
  assert.equal(state.phase,'victory');assert.equal(createState().phase,'playing');
  const time=state.time;advance(state,{x:1},1/60);assert.equal(state.time,time);
});
test('invalid time steps are rejected before state changes',()=>{
  const state=createState();assert.throws(()=>advance(state,{},Infinity));assert.equal(state.time,0);
});
