import * as THREE from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

// Original rigid-weight rigs. The same skeleton supports gameplay and GLB export.
export function character(id, goblin = false) {
  const root = new THREE.Group(); root.name = id;
  const bones = {}, ordered = [];
  const bone = (name, parent, x, y, z) => {
    const b = new THREE.Bone(); b.name = `${id}_${name}`; b.position.set(x, y, z);
    bones[name] = b; ordered.push(b); (parent ? bones[parent] : root).add(b); return b;
  };
  bone('hips', null, 0, 1.05, 0);
  bone('spine', 'hips', 0, .36, 0);
  bone('head', 'spine', 0, .46, 0);
  bone('leftArm', 'spine', -.42, .22, 0);
  bone('leftForearm', 'leftArm', 0, -.38, 0);
  bone('rightArm', 'spine', .42, .22, 0);
  bone('rightForearm', 'rightArm', 0, -.38, 0);
  bone('leftLeg', 'hips', -.2, 0, 0);
  bone('leftShin', 'leftLeg', 0, -.48, 0);
  bone('rightLeg', 'hips', .2, 0, 0);
  bone('rightShin', 'rightLeg', 0, -.48, 0);
  root.updateMatrixWorld(true);
  const pieces = [];
  const skin = goblin ? 0x83a748 : 0xdca77b;
  const tunic = goblin ? 0x68422c : 0x284e55;
  const metal = goblin ? 0x4e5860 : 0x8b9fa7;
  function part(geometry, position, color, owner, scale = [1, 1, 1]) {
    let geo = geometry.index ? geometry.toNonIndexed() : geometry;
    geo.scale(...scale); geo.translate(...position);
    const n = geo.attributes.position.count, index = ordered.indexOf(bones[owner]);
    const indices = new Uint16Array(n * 4), weights = new Float32Array(n * 4);
    const colors = new Float32Array(n * 3), c = new THREE.Color(color);
    for (let i = 0; i < n; i++) {
      indices[i * 4] = index; weights[i * 4] = 1;
      colors.set([c.r, c.g, c.b], i * 3);
    }
    geo.setAttribute('skinIndex', new THREE.BufferAttribute(indices, 4));
    geo.setAttribute('skinWeight', new THREE.BufferAttribute(weights, 4));
    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    pieces.push(geo);
  }
  const box = (x,y,z) => new THREE.BoxGeometry(x,y,z);
  const ball = (r) => new THREE.IcosahedronGeometry(r, 1);
  part(box(.64,.64,.38), [0,1.4,0], tunic,'spine');
  part(box(.57,.2,.4), [0,1.04,0], 0x352e32,'hips');
  part(box(.16,.14,.45), [0,1.14,.01],0xb99952,'hips');
  part(ball(goblin ? .36 : .29),[0,1.98,.02],skin,'head',[1,1.12,1]);
  part(box(.36,.12,.3),[0,1.81,.04],skin,'head');
  for (const side of [-1,1]) {
    const prefix = side < 0 ? 'left' : 'right';
    part(box(.24,.38,.26),[side*.2,.82,0],goblin ? 0x4a383f : 0x343b42,`${prefix}Leg`);
    part(box(.24,.47,.27),[side*.2,.34,.01],0x343432,`${prefix}Shin`);
    part(box(.27,.18,.42),[side*.2,.1,.09],0x282b30,`${prefix}Shin`);
    part(ball(.24),[side*.42,1.64,0],metal,`${prefix}Arm`,[1.12,.8,1.1]);
    part(box(.22,.35,.24),[side*.43,1.45,0],tunic,`${prefix}Arm`);
    part(box(.18,.32,.21),[side*.43,1.09,0],skin,`${prefix}Forearm`);
    part(box(.22,.12,.24),[side*.43,.98,0],metal,`${prefix}Forearm`);
    part(ball(.11),[side*.43,.88,.02],skin,`${prefix}Forearm`);
    part(box(.11,.065,.055),[side*.115,2.02,.29],0xf4edcf,'head');
    part(box(.035,.05,.06),[side*.115,2.02,.32],0x141b1a,'head');
  }
  if (goblin) {
    for (const side of [-1,1]) {
      const ear = new THREE.ConeGeometry(.15,.42,3); ear.rotateZ(-side*Math.PI/2);
      part(ear,[side*.4,2.06,0],skin,'head');
    }
    part(new THREE.ConeGeometry(.1,.24,4),[0,1.99,.3],skin,'head',[1,.6,1.6]);
    part(box(.11,.16,.08),[-.14,1.85,.3],0xe9d7aa,'head');
    part(box(.11,.16,.08),[.14,1.85,.3],0xe9d7aa,'head');
  } else {
    part(ball(.31),[0,2.16,-.04],0x302b2c,'head',[1,.65,1]);
    part(box(.64,.12,.12),[0,2.13,.25],0xb69b61,'head');
    part(box(.09,.22,.09),[0,2.11,.31],0xb69b61,'head');
    part(box(.48,.26,.045),[0,1.52,.215],metal,'spine');
    part(box(.62,.85,.055),[0,1.12,-.26],0xa94539,'spine');
  }
  const geometry = mergeGeometries(pieces);
  const material = new THREE.MeshStandardMaterial({vertexColors:true, roughness:.72, metalness:.15, flatShading:true});
  const mesh = new THREE.SkinnedMesh(geometry,material); mesh.name=`${id}_body`;
  mesh.castShadow=true; mesh.receiveShadow=true; root.add(mesh);
  mesh.bind(new THREE.Skeleton(ordered)); mesh.frustumCulled=false;
  const weapon = new THREE.Group(); weapon.name=`${id}_weapon`; weapon.position.set(0,-.43,.025);
  bones.rightForearm.add(weapon);
  if (!goblin) weapon.rotation.x=-1.1;
  const weaponPart=(geo,color,y)=> {
    const m=new THREE.Mesh(geo,new THREE.MeshStandardMaterial({color,metalness:.65,roughness:.3}));
    m.position.y=y;m.castShadow=true;weapon.add(m);
  };
  weaponPart(new THREE.CylinderGeometry(.045,.045,.26,6),0x453a32,-.09);
  if (goblin) {
    weaponPart(new THREE.CylinderGeometry(.11,.065,.8,5),0x59422d,-.55);
    weaponPart(new THREE.IcosahedronGeometry(.21,0),0x738087,-.86);
  } else {
    weaponPart(new THREE.BoxGeometry(.42,.075,.12),0xcdb475,-.26);
    weaponPart(new THREE.BoxGeometry(.16,.91,.045),0xd0e5e8,-.75);
    const tip = new THREE.ConeGeometry(.082,.22,4);tip.rotateZ(Math.PI);
    weaponPart(tip,0xd0e5e8,-1.31);
    weaponPart(new THREE.BoxGeometry(.025,.8,.055),0x7ce7da,-.73);
  }
  if (goblin) root.scale.setScalar(.86);
  const times=[0,.25,.5,.75,1];
  const rotations=(name,poses,duration=1)=> {
    const values=poses.flatMap(p=>new THREE.Quaternion().setFromEuler(new THREE.Euler(...p)).toArray());
    return new THREE.QuaternionKeyframeTrack(`${bones[name].name}.quaternion`,times.map(t=>t*duration),values);
  };
  const walk=(amp)=> [0,amp,0,-amp,0].map(x=>[x,0,0]);
  const idle = new THREE.AnimationClip('Idle',2,[rotations('spine',[[0,0,.01],[.02,0,0],[0,0,-.01],[-.01,0,0],[0,0,.01]],2)]);
  const run = new THREE.AnimationClip('Run',.7,[
    rotations('leftLeg',walk(.65),.7),rotations('rightLeg',walk(-.65),.7),
    rotations('leftArm',walk(-.6),.7),rotations('rightArm',walk(.6),.7),
    rotations('leftShin',[[.1,0,0],[.8,0,0],[.1,0,0],[0,0,0],[.1,0,0]],.7),
    rotations('rightShin',[[.1,0,0],[0,0,0],[.1,0,0],[.8,0,0],[.1,0,0]],.7)]);
  const attack = new THREE.AnimationClip('Sword',.48,[
    rotations('rightArm',[[0,0,0],[-2.4,0,-.5],[-1.2,0,1.2],[-.4,0,.7],[0,0,0]],.48),
    rotations('spine',[[0,0,0],[0,-.6,0],[0,.8,0],[0,.35,0],[0,0,0]],.48)]);
  const dance = new THREE.AnimationClip('Dance',2,[
    rotations('hips',[[0,-.2,0],[0,.1,.1],[0,.2,0],[0,-.1,-.1],[0,-.2,0]],2),
    rotations('leftArm',[[0,0,-1.2],[0,0,-2],[0,0,-1.2],[0,0,-.4],[0,0,-1.2]],2),
    rotations('rightArm',[[0,0,1.2],[0,0,.4],[0,0,1.2],[0,0,2],[0,0,1.2]],2),
    rotations('leftLeg',walk(.3),2),rotations('rightLeg',walk(-.3),2)]);
  const clips=[idle,run,attack,dance];const mixer=new THREE.AnimationMixer(root);
  const actions=Object.fromEntries(clips.map(clip=>[clip.name,mixer.clipAction(clip)]));
  let active='';
  const play=(name)=> {
    if(name===active || !actions[name])return;
    if(active)actions[active].fadeOut(.12);
    actions[name].reset().fadeIn(.12).play();active=name;
  };
  play('Idle');
  root.userData={origin:'Baltor original procedural character',rig:'baltor_biped/v1',animations:clips.map(c=>c.name)};
  return {root,mesh,bones,clips,mixer,play,weapon};
}
