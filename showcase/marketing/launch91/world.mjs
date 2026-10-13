import * as THREE from 'three';
import {GLTFExporter} from 'three/addons/exporters/GLTFExporter.js';

// Original geometry and label textures. No external models or image downloads.
export async function createWorld(canvas){
 const renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.4;
 const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(36,1,.1,100);camera.position.set(8,6,12);camera.lookAt(0,0,0);
 scene.add(new THREE.AmbientLight(0xc6dae4,2.2));const key=new THREE.DirectionalLight(0xffffff,4);key.position.set(5,8,7);scene.add(key);const rim=new THREE.DirectionalLight(0x73d8cf,3);rim.position.set(-5,3,-4);scene.add(rim);
 const palette={mint:0x68d5b7,gold:0xf5bc69,purple:0xb9a2ed,cream:0xf5f0e8,ink:0x203847};
 const material=color=>new THREE.MeshStandardMaterial({color,roughness:.33,metalness:.12});
 const root=new THREE.Group();root.name='Baltor_workflow_sculpture';scene.add(root);
 const base=new THREE.Mesh(new THREE.CylinderGeometry(5,5.25,.32,96),material(0x243e4b));base.position.y=-2.05;root.add(base);
 const ring=new THREE.Mesh(new THREE.TorusGeometry(4.65,.026,8,100),material(palette.mint));ring.rotation.x=Math.PI/2;ring.position.y=-1.86;root.add(ring);
 function label(text,width=512,height=160){const c=document.createElement('canvas');c.width=width;c.height=height;const p=c.getContext('2d');p.fillStyle='#f5f0e8';p.fillRect(0,0,width,height);p.fillStyle='#15252d';p.font='bold 48px Arial';p.textAlign='center';p.textBaseline='middle';p.fillText(text,width/2,height/2);const tex=new THREE.CanvasTexture(c);tex.colorSpace=THREE.SRGBColorSpace;return new THREE.MeshBasicMaterial({map:tex});}
 function block(name,w,h,d,color){const group=new THREE.Group();group.name=name;const shape=new THREE.Shape();const r=.13;shape.moveTo(-w/2+r,-h/2);shape.lineTo(w/2-r,-h/2);shape.quadraticCurveTo(w/2,-h/2,w/2,-h/2+r);shape.lineTo(w/2,h/2-r);shape.quadraticCurveTo(w/2,h/2,w/2-r,h/2);shape.lineTo(-w/2+r,h/2);shape.quadraticCurveTo(-w/2,h/2,-w/2,h/2-r);shape.lineTo(-w/2,-h/2+r);shape.quadraticCurveTo(-w/2,-h/2,-w/2+r,-h/2);const mesh=new THREE.Mesh(new THREE.ExtrudeGeometry(shape,{depth:d,bevelEnabled:true,bevelSize:.08,bevelThickness:.07,bevelSegments:3,steps:1}),material(color));mesh.position.z=-d/2;group.add(mesh);return group;}
 function slab(text,color,x,y,z){const group=block(text,3.2,.95,.32,color);group.position.set(x,y,z);const title=new THREE.Mesh(new THREE.PlaneGeometry(2.6,.7),label(text));title.position.z=.25;group.add(title);return group;}
 const groups={};for(const id of ['intro','feeds','foundry','afk','close']){groups[id]=new THREE.Group();groups[id].name=id;root.add(groups[id]);}
 for(const id of ['intro','close']){['AgentFeeds','AgentFoundry','AgentAFK'].forEach((name,i)=>{const object=slab(name,[palette.mint,palette.gold,palette.purple][i],(i-1)*.45,-.8+i*1.35,(i-1)*-.75);object.rotation.y=-.1+i*.12;groups[id].add(object);});}
 for(let i=0;i<4;i++){const source=slab(['Sources','Questions','profile.json','READING.md'][i],i<2?palette.cream:palette.mint,-.7+(i%2)*1.35,-1+i*.98,-.6+i*.15);source.rotation.y=-.17;groups.feeds.add(source);}
 for(let x=0;x<2;x++)for(let y=0;y<2;y++)for(let z=0;z<2;z++){const object=block(`component_${x}${y}${z}`,1.52,1.52,1.52,(x+y+z)%2?palette.gold:palette.cream);object.userData.base=[(x-.5)*1.75,(y-.5)*1.75+.1,(z-.5)*1.75];object.position.fromArray(object.userData.base);groups.foundry.add(object);}
 const orbit=new THREE.Mesh(new THREE.TorusGeometry(2.65,.045,12,100),material(palette.gold));orbit.rotation.x=.9;groups.foundry.add(orbit);
 ['Task 01','Task 02','Local plan'].forEach((name,i)=>{const object=slab(name,i===2?palette.purple:palette.cream,(i-1)*.65,-.85+i*1.25,(i-1)*-.6);groups.afk.add(object);});
 let current='intro';
 function render(id,time,local){current=id;const box=canvas.getBoundingClientRect();renderer.setSize(Math.round(box.width),Math.round(box.height),false);camera.aspect=box.width/box.height;camera.updateProjectionMatrix();
   Object.entries(groups).forEach(([key,group])=>{group.visible=key===id;});
   root.rotation.y=-.22+Math.sin(time*.36)*.23;root.position.y=.15+Math.sin(time*.7)*.09;ring.rotation.z=time*.1;
   groups.foundry.children.forEach((object,i)=>{if(object.userData.base){const spread=1+.13*(1+Math.sin(local*1.3+i*.15));object.position.fromArray(object.userData.base).multiplyScalar(spread);object.rotation.y=Math.sin(local*.7)*.1;}});
   for(const key of ['intro','feeds','afk','close'])groups[key].children.forEach((object,i)=>{object.rotation.z=Math.sin(time*.5+i)*.02;});
   camera.position.set(8+Math.sin(time*.25)*1.1,5.8,12.3);camera.lookAt(0,.15,0);renderer.render(scene,camera);
 }
 function inspect(){let meshes=0,triangles=0;scene.traverse(o=>{if(o.isMesh){meshes++;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;}});return{engine:'Three.js',revision:THREE.REVISION,meshes,triangles,selected_scene:current,camera:camera.position.toArray(),real_geometry:true};}
 async function exportScene(){const exporter=new GLTFExporter();return Array.from(new Uint8Array(await exporter.parseAsync(scene,{binary:true,onlyVisible:true})));}
 return {render,inspect,exportScene};
}
