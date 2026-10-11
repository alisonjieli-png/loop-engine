// Demo of GPU picking, rendered by the family verifier and usable as an example. Six meshes with ids that use all
// three bytes, a ring of twelve instanced cubes with per-instance ids, an unnamed panel in front of one mesh and a
// cloud of points (hidden while picking) are picked at their projected centres and at the background; picked
// objects glow and white beads mark the picked pixels. The baseline is the same scene unpicked. In the browser each
// pick is compared with the first mesh three.js Raycaster finds through the same pixel centre.

const IDS = [7, 300, 70000, 4242, 123456, 9999999];

function build(THREE, picking) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x111827);
  scene.add(new THREE.HemisphereLight(0xe0e8ff, 0x202030, 1.4));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(3, 5, 6);
  scene.add(key);
  const shapes = [new THREE.BoxGeometry(0.9, 0.9, 0.9), new THREE.SphereGeometry(0.55, 32, 16),
    new THREE.TorusGeometry(0.42, 0.17, 16, 48), new THREE.ConeGeometry(0.5, 1, 32),
    new THREE.CylinderGeometry(0.4, 0.4, 0.9, 32), new THREE.IcosahedronGeometry(0.55, 0)];
  const colours = [0xef476f, 0xffd166, 0x06d6a0, 0x118ab2, 0x8338ec, 0xff8c42];
  const meshes = shapes.map((geometry, index) => {
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: colours[index], roughness: 0.45}));
    mesh.position.set(-2.7 + index * 1.08, 0.55 + 0.25 * Math.sin(index * 1.3), index % 2 === 0 ? 0.4 : -0.3);
    mesh.userData.pickId = IDS[index];
    scene.add(mesh);
    return mesh;
  });
  const panel = new THREE.Mesh(new THREE.BoxGeometry(0.75, 0.45, 0.05), new THREE.MeshStandardMaterial({color: 0x9aa5b1}));
  panel.position.set(meshes[3].position.x, meshes[3].position.y - 0.2, meshes[3].position.z + 0.9);
  scene.add(panel);
  const ring = new THREE.InstancedMesh(new THREE.BoxGeometry(0.35, 0.35, 0.35),
    new THREE.MeshStandardMaterial({color: 0x94a3b8, roughness: 0.6}), 12);
  const matrix = new THREE.Matrix4();
  for (let index = 0; index < 12; index += 1) {
    const angle = (index / 12) * Math.PI - Math.PI;
    ring.setMatrixAt(index, matrix.makeTranslation(Math.cos(angle) * 3.4, 1.7 + Math.sin(index) * 0.2, -2.6 + Math.sin(angle) * 0.6));
  }
  ring.instanceMatrix.needsUpdate = true;
  picking.setInstancePickIds(THREE, ring, Array.from({length: 12}, (_, index) => 1000000 + index));
  scene.add(ring);
  const cloud = new Float32Array(600 * 3);
  for (let index = 0; index < 600; index += 1) {
    cloud.set([Math.sin(index * 12.9898) * 4, Math.sin(index * 78.233) * 2 + 1, 2 + Math.sin(index * 37.719)], index * 3);
  }
  const points = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(cloud, 3)),
    new THREE.PointsMaterial({color: 0xffffff, size: 0.03}));
  scene.add(points);
  return {scene, meshes, panel, ring};
}

export function demo(THREE, picking, harness) {
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 2.2, 7.5);
  camera.lookAt(0, 0.4, 0);
  camera.updateMatrixWorld();
  const shown = build(THREE, picking);
  const picker = picking.createPicker(THREE, harness.renderer);
  const size = harness.size;
  const toPixel = (point) => {
    const ndc = point.clone().project(camera);
    return [Math.floor(((ndc.x + 1) / 2) * size), Math.floor(((1 - ndc.y) / 2) * size)];
  };
  // Aim at each mesh's body: the torus has a hole at its centre, so it is picked on its tube.
  const aims = shown.meshes.map((mesh, index) => mesh.position.clone().add(new THREE.Vector3(index === 2 ? 0.42 : 0, 0, 0)));
  const targets = shown.meshes.map((mesh, index) => ({pixel: toPixel(aims[index]), expected: mesh.userData.pickId, mesh}));
  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  for (let index = 0; index < 12; index += 1) {
    shown.ring.getMatrixAt(index, matrix);
    targets.push({pixel: toPixel(position.setFromMatrixPosition(matrix)), expected: 1000000 + index, instance: index});
  }
  targets.push({pixel: toPixel(shown.panel.position), expected: 0, occluder: true});
  targets.push({pixel: [2, 2], expected: 0});

  const raycaster = new THREE.Raycaster();
  const pickable = [...shown.meshes, shown.panel, shown.ring];
  let agree = 0;
  let correct = 0;
  const results = [];
  for (const entry of targets) {
    const id = picker.pick(shown.scene, camera, entry.pixel[0] + 0.5, entry.pixel[1] + 0.5);
    raycaster.setFromCamera(new THREE.Vector2(((entry.pixel[0] + 0.5) / size) * 2 - 1, 1 - ((entry.pixel[1] + 0.5) / size) * 2), camera);
    const hit = raycaster.intersectObjects(pickable, false)[0];
    const raycastId = !hit ? 0 : hit.object.isInstancedMesh ? 1000000 + hit.instanceId : hit.object.userData.pickId || 0;
    if (id === raycastId) agree += 1;
    if (id === entry.expected) correct += 1;
    if (hit && id !== 0) entry.point = hit.point.clone();
    results.push(id);
  }
  harness.check('picks_equal_expected_ids', correct === targets.length, {correct, targets: targets.length, ids: results});
  harness.check('picks_equal_three_raycaster', agree === targets.length, {agree, targets: targets.length});
  const materialsBack = shown.scene.children.every((child) => !child.isMesh || child.material.name !== 'BaltorPickingMaterial');
  const viewBack = camera.view === null || camera.view.enabled === false;
  harness.check('state_restored_after_picking', materialsBack && viewBack && shown.scene.background !== null
    && harness.renderer.getRenderTarget() === null, {materials: materialsBack, view: viewBack});
  picker.dispose();

  for (const mesh of shown.meshes) {
    mesh.material.emissive = new THREE.Color(0xffc857);
    mesh.material.emissiveIntensity = 0.55;
  }
  for (const entry of targets) {
    if (!entry.point) continue;
    const bead = new THREE.Mesh(new THREE.SphereGeometry(0.06, 16, 8), new THREE.MeshBasicMaterial({color: 0xffffff}));
    bead.position.copy(entry.point).lerp(camera.position, 0.02);
    shown.scene.add(bead);
  }
  return {scene: shown.scene, camera, baseline: {scene: build(THREE, picking).scene, camera}};
}
