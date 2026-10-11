// Demo of the GLB codec, rendered by the family verifier and usable as an example. three.js's GLTFExporter writes a
// small scene as GLB; parseGlb reads that container, encodeGlb packs its JSON and BIN chunk again, and GLTFLoader
// loads the repacked bytes, which are rendered. Damaged copies must be refused with their reason codes. The baseline
// is the same stage without the loaded model.

function countVertices(root) {
  let vertices = 0;
  let meshes = 0;
  root.traverse((node) => {
    if (node.isMesh) {
      meshes += 1;
      vertices += node.geometry.attributes.position.count;
    }
  });
  return {meshes, vertices};
}

function stage(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1d2433);
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(2, 4, 3);
  scene.add(key, new THREE.HemisphereLight(0xcfe0ff, 0x2a2018, 1.0));
  const floor = new THREE.Mesh(new THREE.CircleGeometry(2.4, 64), new THREE.MeshStandardMaterial({color: 0x39424f}));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.85;
  scene.add(floor);
  return scene;
}

export function demo(THREE, glb, harness) {
  return build(THREE, glb, harness);
}

async function build(THREE, glb, harness) {
  const {GLTFExporter, GLTFLoader} = harness.addons;
  const source = new THREE.Scene();
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.55, 0.18, 160, 20),
    new THREE.MeshStandardMaterial({color: 0xe0703f, roughness: 0.35, metalness: 0.1}));
  knot.position.set(-0.55, 0.1, 0);
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.7, 0.7), new THREE.MeshStandardMaterial({color: 0x4c8fdf, roughness: 0.5}));
  box.position.set(0.95, -0.45, 0.2);
  box.rotation.set(0.3, 0.7, 0);
  source.add(knot, box);
  const expected = countVertices(source);

  const exported = await new GLTFExporter().parseAsync(source, {binary: true});
  const parsed = glb.parseGlb(exported);
  harness.check('exporter_glb_parses', glb.isGlb(exported) && parsed.json.asset.version === '2.0' && parsed.binary !== null
    && parsed.chunks[0].name === 'JSON' && parsed.chunks[1].name === 'BIN',
  {bytes: parsed.byteLength, chunks: parsed.chunks.map((chunk) => [chunk.name, chunk.byteLength])});

  const binary = parsed.binary.subarray(0, parsed.json.buffers[0].byteLength);
  const repacked = glb.encodeGlb(parsed.json, binary);
  const loaded = await new GLTFLoader().parseAsync(repacked.buffer, '');
  const found = countVertices(loaded.scene);
  harness.check('repacked_glb_loads_in_gltfloader', found.meshes === expected.meshes && found.vertices === expected.vertices,
    {expected, found, repacked_bytes: repacked.byteLength});

  const reasons = {};
  const damaged = Uint8Array.from(repacked);
  damaged[0] = 0x66;
  const shortened = repacked.slice(0, repacked.byteLength - 4);
  for (const [name, bytes] of [['magic', damaged], ['length', shortened]]) {
    try {
      glb.parseGlb(bytes);
      reasons[name] = 'accepted';
    } catch (error) {
      reasons[name] = error instanceof glb.GlbError ? error.code : error.name;
    }
  }
  harness.check('damaged_containers_refused', reasons.magic === 'magic' && reasons.length === 'length_mismatch', reasons);

  const scene = stage(THREE);
  scene.add(loaded.scene);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(0.25, 1.2, 4.1);
  camera.lookAt(0.1, -0.15, 0);
  return {scene, camera, baseline: {scene: stage(THREE), camera}};
}
