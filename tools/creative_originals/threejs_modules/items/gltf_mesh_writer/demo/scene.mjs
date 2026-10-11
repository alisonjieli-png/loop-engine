// Demo of the glTF mesh writer, rendered by the family verifier and usable as an example. Three three.js geometries
// become writer meshes (one with vertex colours), placed in a small node hierarchy, written as .gltf JSON and as GLB,
// and loaded back with three.js's GLTFLoader: vertex counts and node world transforms must match what was written.
// The baseline is the same stage without the loaded model.

function stage(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1c2230);
  const key = new THREE.DirectionalLight(0xffffff, 2.3);
  key.position.set(2.5, 4, 3);
  scene.add(key, new THREE.HemisphereLight(0xd4e2ff, 0x2c241c, 1.0));
  return scene;
}

function rainbow(count) {
  const colors = new Float32Array(count * 3);
  for (let vertex = 0; vertex < count; vertex += 1) {
    const hue = (vertex / count) * Math.PI * 2;
    colors.set([0.55 + 0.45 * Math.cos(hue), 0.55 + 0.45 * Math.cos(hue - 2.1), 0.55 + 0.45 * Math.cos(hue + 2.1)], vertex * 3);
  }
  return colors;
}

export function demo(THREE, writer, harness) {
  return build(THREE, writer, harness);
}

async function build(THREE, writer, harness) {
  const knot = writer.meshFromBufferGeometry(new THREE.TorusKnotGeometry(0.42, 0.14, 128, 16),
    {name: 'knot', material: {color: [0.88, 0.36, 0.18, 1], roughness: 0.35}});
  const gem = writer.meshFromBufferGeometry(new THREE.IcosahedronGeometry(0.42, 1), {name: 'gem',
    material: {color: [1, 1, 1, 1], roughness: 0.5}});
  gem.colors = rainbow(gem.positions.length / 3);
  const slab = writer.meshFromBufferGeometry(new THREE.BoxGeometry(1, 1, 1), {name: 'slab',
    material: {color: [0.3, 0.34, 0.42, 1], roughness: 0.8}});
  const turn = [0, Math.sin(Math.PI / 12), 0, Math.cos(Math.PI / 12)];
  const input = {
    meshes: [knot, gem, slab],
    nodes: [
      {name: 'turntable', translation: [0, 0.05, 0], rotation: turn, children: [1, 2]},
      {name: 'knot_node', mesh: 0, translation: [-0.65, 0.35, 0]},
      {name: 'gem_node', mesh: 1, translation: [0.7, 0.3, 0.1], scale: [0.9, 0.9, 0.9]},
      {name: 'slab_node', mesh: 2, translation: [0, -0.45, 0], scale: [2.6, 0.16, 1.3]},
    ],
  };
  const loader = new harness.addons.GLTFLoader();
  const loaded = await loader.parseAsync(JSON.stringify(writer.writeGltf(input)), '');
  loaded.scene.updateMatrixWorld(true);

  const expected = new Map();
  const local = (node) => new THREE.Matrix4().compose(new THREE.Vector3(...(node.translation ?? [0, 0, 0])),
    new THREE.Quaternion(...(node.rotation ?? [0, 0, 0, 1])), new THREE.Vector3(...(node.scale ?? [1, 1, 1])));
  const parentMatrix = local(input.nodes[0]);
  expected.set('turntable', parentMatrix);
  expected.set('knot_node', parentMatrix.clone().multiply(local(input.nodes[1])));
  expected.set('gem_node', parentMatrix.clone().multiply(local(input.nodes[2])));
  expected.set('slab_node', local(input.nodes[3]));
  let worst = 0;
  for (const [name, matrix] of expected) {
    const node = loaded.scene.getObjectByName(name);
    if (!node) {
      worst = Infinity;
      continue;
    }
    node.matrixWorld.elements.forEach((value, index) => { worst = Math.max(worst, Math.abs(value - matrix.elements[index])); });
  }
  harness.check('node_world_transforms_match', worst < 1e-5, {worst_difference: worst});

  const counts = [];
  loaded.scene.traverse((object) => { if (object.isMesh) counts.push(object.geometry.attributes.position.count); });
  const vertexCounts = [knot, gem, slab].map((mesh) => mesh.positions.length / 3);
  const loadedTotal = counts.reduce((sum, value) => sum + value, 0);
  harness.check('vertex_counts_match', counts.length === 3
    && [...counts].sort((a, b) => a - b).join() === [...vertexCounts].sort((a, b) => a - b).join(),
  {written: vertexCounts, loaded: counts});
  const gemMesh = loaded.scene.getObjectByName('gem_node');
  let colourAttribute = false;
  gemMesh.traverse((object) => { if (object.isMesh && object.geometry.attributes.color) colourAttribute = true; });
  harness.check('vertex_colours_survive', colourAttribute, {});

  const glb = writer.writeGlb(input);
  const fromGlb = await loader.parseAsync(glb.buffer, '');
  let glbVertices = 0;
  fromGlb.scene.traverse((object) => { if (object.isMesh) glbVertices += object.geometry.attributes.position.count; });
  harness.check('glb_loads_with_the_same_vertices', glbVertices === loadedTotal, {glb_bytes: glb.byteLength, glbVertices});

  const scene = stage(THREE);
  scene.add(loaded.scene);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(0.25, 1.3, 4.25);
  camera.lookAt(0, 0.05, 0);
  return {scene, camera, baseline: {scene: stage(THREE), camera}};
}
