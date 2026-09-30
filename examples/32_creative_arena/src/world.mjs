import * as THREE from 'three';

export function createWorld(scene) {
  const root=new THREE.Group();root.name='Ashen_Wilds';scene.add(root);
  const obstacles=[],animated=[];
  let seed=21;const random=()=>{seed=(seed*1664525+1013904223)>>>0;return seed/4294967296;};
  const materials={stone:new THREE.MeshStandardMaterial({color:0x596f73,roughness:.92}),
    ground:new THREE.MeshStandardMaterial({color:0x344b3a,roughness:1}),
    grass:new THREE.MeshStandardMaterial({color:0x536d42,roughness:1,flatShading:true}),
    leaf:new THREE.MeshStandardMaterial({color:0x244739,roughness:1,flatShading:true}),
    bark:new THREE.MeshStandardMaterial({color:0x514238,roughness:1}),
    gold:new THREE.MeshStandardMaterial({color:0xae9059,metalness:.55,roughness:.4}),
    glow:new THREE.MeshStandardMaterial({color:0x78eedc,emissive:0x3df0cf,emissiveIntensity:2}),
    flame:new THREE.MeshStandardMaterial({color:0xffd790,emissive:0xff9c42,emissiveIntensity:3})};
  const add=(geo,mat,x,y,z,parent=root)=>{
    const mesh=new THREE.Mesh(geo,typeof mat==='string'?materials[mat]:mat);
    mesh.position.set(x,y,z);mesh.castShadow=true;mesh.receiveShadow=true;parent.add(mesh);return mesh;
  };
  add(new THREE.CylinderGeometry(17.9,17.8,.48,80),'ground',0,-.22,0);
  const rock=add(new THREE.IcosahedronGeometry(16,2),'stone',0,-6.8,0);rock.scale.set(1.11,.39,1.11);
  for(let i=0;i<60;i++){
    const a=random()*Math.PI*2,r=17+random()*.85;
    const b=add(new THREE.DodecahedronGeometry(.6+random()*.7,0),'stone',Math.cos(a)*r,-.1-random()*.3,Math.sin(a)*r);
    b.scale.y=.65;b.rotation.set(random(),random(),random());
  }
  for(let z=-12;z<12;z+=1.65){
    for(let x=-1;x<=1;x++){
      const p=add(new THREE.CylinderGeometry(.78,.82,.1,6),'stone',x*1.65+Math.sin(z*.4)*.3,.045,z);
      p.rotation.y=random()*.2;
    }
  }
  const dais=add(new THREE.CylinderGeometry(4.5,4.7,.22,32),'stone',0,.05,-8.4);
  for(let i=0;i<14;i++){
    const a=i/14*Math.PI*2;const r=3.9;
    const tile=add(new THREE.BoxGeometry(.11,.07,.6),'gold',Math.cos(a)*r,.2,-8.4+Math.sin(a)*r);
    tile.rotation.y=-a;
  }
  for(const x of [-3.2,3.2]){
    add(new THREE.BoxGeometry(1.15,.42,1.35),'stone',x,.35,-10.5);
    add(new THREE.BoxGeometry(.82,3.8,.85),'stone',x,2.4,-10.5);
    add(new THREE.BoxGeometry(1.13,.32,1.1),'gold',x,4.22,-10.5);
    obstacles.push({x,z:-10.5,radius:.7});
  }
  for(let i=0;i<13;i++){
    const a=i/12*Math.PI;
    const m=add(new THREE.BoxGeometry(.82,.84,.88),'stone',Math.cos(a)*3.2,4.25+Math.sin(a)*2.4,-10.5);
    m.rotation.z=a-Math.PI/2;
  }
  const gate=new THREE.Group();gate.name='Portal';root.add(gate);gate.position.set(0,2.5,-10.4);
  const ring=add(new THREE.TorusGeometry(2.05,.08,8,80),'glow',0,0,0,gate);ring.scale.y=1.18;
  const inner=add(new THREE.TorusGeometry(1.7,.025,6,60),'glow',0,0,.05,gate);inner.scale.y=1.18;
  const veil=add(new THREE.CircleGeometry(1.95,64),new THREE.MeshBasicMaterial({color:0x258b80,transparent:true,opacity:.19,side:THREE.DoubleSide,depthWrite:false}),0,0,-.05,gate);veil.scale.y=1.18;
  for(let i=0;i<12;i++){
    const a=i/12*Math.PI*2;
    const rune=add(new THREE.OctahedronGeometry(.08),'glow',Math.cos(a)*1.86,Math.sin(a)*2.2,.08,gate);
    animated.push({mesh:rune,type:'rune',phase:a});
  }
  for(const x of [-4.9,4.9]){
    add(new THREE.CylinderGeometry(.22,.28,1.6,6),'stone',x,.8,-8.5);
    add(new THREE.CylinderGeometry(.42,.22,.3,8),'gold',x,1.65,-8.5);
    const flame=add(new THREE.IcosahedronGeometry(.28,1),'flame',x,2.05,-8.5);flame.scale.y=1.8;
    animated.push({mesh:flame,type:'flame',phase:x});
    const light=new THREE.PointLight(0xffa968,15,12,2);light.position.set(x,2.5,-8.5);root.add(light);
  }
  for(const [x,z,height] of [[-7,-4,3.4],[7,-4,2.5],[-9,4,1.6],[9,5,3],[-11,-9,2.1],[11,-10,2.8]]){
    add(new THREE.CylinderGeometry(.48,.6,height,7),'stone',x,height/2,z);
    add(new THREE.BoxGeometry(1.2,.28,1.2),'stone',x,height,z);
    add(new THREE.BoxGeometry(1.3,.25,1.3),'stone',x,.12,z);
    obstacles.push({x,z,radius:.7});
  }
  for(let i=0;i<30;i++){
    const a=i/30*Math.PI*2,r=13.4+random()*3.2;
    const x=Math.cos(a)*r,z=Math.sin(a)*r;
    if(Math.abs(x)<4 && z>0)continue;
    const h=3.5+random()*3.3;
    add(new THREE.CylinderGeometry(.14,.34,h*.7,6),'bark',x,h*.32,z);
    for(let layer=0;layer<3;layer++){
      const cone=add(new THREE.ConeGeometry(1.3-layer*.23,h*.65,6),'leaf',x,h*(.47+layer*.16),z);
      cone.rotation.y=random();
    }
    obstacles.push({x,z,radius:.43});
  }
  const grassGeometry=new THREE.ConeGeometry(.08,.45,3),grass=new THREE.InstancedMesh(grassGeometry,materials.grass,520);
  const dummy=new THREE.Object3D();let count=0;
  for(let i=0;i<700 && count<520;i++){
    const a=random()*Math.PI*2,r=Math.sqrt(random())*16.8,x=Math.cos(a)*r,z=Math.sin(a)*r;
    if(Math.abs(x)<2.7 || Math.hypot(x,z+8.4)<4.6)continue;
    dummy.position.set(x,.16,z);dummy.rotation.set(0,random()*6.28,(random()-.5)*.4);
    dummy.scale.setScalar(.6+random()*1.3);dummy.updateMatrix();grass.setMatrixAt(count++,dummy.matrix);
  }
  grass.count=count;root.add(grass);
  for(let i=0;i<40;i++){
    const a=random()*6.28,r=6+random()*10;
    const stone=add(new THREE.DodecahedronGeometry(.2+random()*.45),'stone',Math.cos(a)*r,.15,Math.sin(a)*r);
    stone.scale.y=.65;
  }
  for(let i=0;i<18;i++){
    const x=(random()-.5)*28,z=(random()-.5)*28;
    const mote=add(new THREE.SphereGeometry(.025,4,3),'glow',x,.6+random()*2.5,z);
    animated.push({mesh:mote,type:'mote',phase:random()*6.28,y:mote.position.y});
  }
  const hemi=new THREE.HemisphereLight(0x94c9e3,0x243e31,2.1);scene.add(hemi);
  const sun=new THREE.DirectionalLight(0xd9eafa,3);sun.position.set(8,20,5);sun.castShadow=true;
  sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-22;sun.shadow.camera.right=22;
  sun.shadow.camera.top=22;sun.shadow.camera.bottom=-22;sun.shadow.normalBias=.035;scene.add(sun);
  const rim=new THREE.DirectionalLight(0x5bcbb8,2);rim.position.set(-7,7,-14);scene.add(rim);
  const portalLight=new THREE.PointLight(0x49e9d4,25,13);portalLight.position.set(0,3,-8);scene.add(portalLight);
  const atmospheres={dusk:{fog:0x142f36,stone:0x627a7d,ground:0x36503d,leaf:0x264b3d,light:2.6},
    dawn:{fog:0x758b89,stone:0x858b76,ground:0x567247,leaf:0x456843,light:3.7},
    astral:{fog:0x191d3e,stone:0x666a90,ground:0x354456,leaf:0x354661,light:2.3}};
  function atmosphere(name){
    const p=atmospheres[name]??atmospheres.dusk;
    scene.background=new THREE.Color(p.fog);scene.fog=new THREE.FogExp2(p.fog,.018);
    for(const k of ['stone','ground','leaf'])materials[k].color.setHex(p[k]);sun.intensity=p.light;
  }
  atmosphere('dusk');
  return {root,obstacles,atmosphere,update(time){
    inner.rotation.z=time*.14;
    for(const a of animated){
      if(a.type==='rune')a.mesh.rotation.z=time*.5+a.phase;
      else if(a.type==='flame')a.mesh.scale.y=1.6+Math.sin(time*8+a.phase)*.23;
      else a.mesh.position.y=a.y+Math.sin(time*.8+a.phase)*.28;
    }
  }};
}
