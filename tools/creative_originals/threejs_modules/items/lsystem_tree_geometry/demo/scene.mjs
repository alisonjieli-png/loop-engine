// Demo of the L-system tree, rendered by the family verifier and usable as an example: a seeded stochastic grammar
// (the first fork always branches, later forks may stop) grown six times, walked by the turtle into tapered branches,
// with instanced foliage on the leaf anchors. The baseline shows a cone-and-trunk placeholder tree on the same ground.

const RULES = {
  B: '!"F[&+FLA]\\\\[&-FLA]\\\\[^FLA]',
  A: [
    {successor: '!"F[&+FLA]\\\\[&-FLA]\\\\[^FLA]', weight: 3},
    {successor: '!"F[&FLA]\\\\\\[&FLA]', weight: 2},
    {successor: '!"FL', weight: 1},
  ],
};

export function demo(THREE, lsystem, harness) {
  const commands = lsystem.rewriteLSystem('FFB', RULES, 6, 20261009);
  harness.check('rewrite_repeats_by_seed', commands === lsystem.rewriteLSystem('FFB', RULES, 6, 20261009),
    {length: commands.length});
  const options = {angle: 30, length: 0.42, lengthScale: 0.84, radius: 0.07, taper: 0.74, segmentTaper: 0.95,
    radialSegments: 6};
  const geometry = lsystem.createLsystemTreeGeometry(THREE, commands, options);
  const segmentCount = [...commands].filter((symbol) => symbol === 'F').length;
  const leafCount = [...commands].filter((symbol) => symbol === 'L').length;
  harness.check('one_branch_per_F', segmentCount >= 60 && geometry.getAttribute('position').count === segmentCount * 2 * 7,
    {segments: segmentCount, vertices: geometry.getAttribute('position').count});
  harness.check('one_leaf_per_L', geometry.userData.leafPositions.length === leafCount * 3, {leaves: leafCount});
  harness.check('tree_rises_above_trunk', geometry.boundingBox.max.y > 0.84, {top: geometry.boundingBox.max.y});
  const extent = geometry.boundingBox.getSize(new THREE.Vector3());
  harness.check('crown_spreads_sideways', extent.x >= 0.3 * extent.y && extent.z >= 0.3 * extent.y,
    {extent: extent.toArray()});

  const background = new THREE.Color(0xa9c3dc);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  const ground = new THREE.Mesh(new THREE.CircleGeometry(2.2, 48), new THREE.MeshStandardMaterial({color: 0x56703a}));
  ground.rotation.x = -Math.PI / 2;
  for (const target of [scene, baseline]) {
    const sun = new THREE.DirectionalLight(0xfff0d8, 2.6);
    sun.position.set(3, 6, 4);
    target.add(sun, new THREE.HemisphereLight(0xdbe8ff, 0x4a3a28, 1.2), ground.clone());
  }
  scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0x6b4a2f, roughness: 0.9})));
  const leaves = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(0.075, 0),
    new THREE.MeshStandardMaterial({color: 0x4f9a3c, roughness: 0.7, flatShading: true}), leafCount);
  const matrix = new THREE.Matrix4();
  const anchors = geometry.userData.leafPositions;
  for (let k = 0; k < leafCount; k += 1) {
    const size = 0.8 + 0.6 * ((k * 0.618034) % 1);
    matrix.makeScale(size, size, size).setPosition(anchors[k * 3], anchors[k * 3 + 1], anchors[k * 3 + 2]);
    leaves.setMatrixAt(k, matrix);
  }
  scene.add(leaves);

  const height = geometry.boundingBox.max.y;
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, height * 0.4, 8),
    new THREE.MeshStandardMaterial({color: 0x6b4a2f}));
  trunk.position.y = height * 0.2;
  const crown = new THREE.Mesh(new THREE.ConeGeometry(height * 0.35, height * 0.7, 16),
    new THREE.MeshStandardMaterial({color: 0x4f9a3c}));
  crown.position.y = height * 0.62;
  baseline.add(trunk, crown);

  const centre = new THREE.Vector3(0, height * 0.48, 0);
  const camera = new THREE.PerspectiveCamera(40, 1, 0.05, 50);
  camera.position.set(height * 0.9, height * 0.75, height * 1.55);
  camera.lookAt(centre);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
