// Demo of marching tetrahedra, rendered by the family verifier and usable as an example: five metaballs sampled on a
// 56 x 56 x 56 grid and polygonized at density 1 into one welded blob. The baseline shows the five balls as separate
// spheres. The checks look at the mesh three.js holds: closed, on the level set, and its gradient normals agreeing
// with three.js's face-averaged normals.

const BALLS = [
  {centre: [-0.42, -0.08, 0.05], strength: 0.075},
  {centre: [0.3, 0.12, -0.1], strength: 0.09},
  {centre: [0.02, 0.48, 0.12], strength: 0.05},
  {centre: [0.55, -0.42, 0.18], strength: 0.04},
  {centre: [-0.18, -0.5, -0.2], strength: 0.045},
];

function density(x, y, z) {
  let sum = 0;
  for (const {centre, strength} of BALLS) {
    const dx = x - centre[0];
    const dy = y - centre[1];
    const dz = z - centre[2];
    sum += strength / (dx * dx + dy * dy + dz * dz + 1e-9);
  }
  return sum;
}

export function demo(THREE, iso, harness) {
  const field = iso.sampleScalarField(density, {min: [-1.05, -1.05, -1.05], max: [1.05, 1.05, 1.05], resolution: 56});
  const geometry = iso.createIsosurfaceGeometry(THREE, field, {isoLevel: 1, insideBelow: false});
  const index = geometry.getIndex().array;
  const position = geometry.getAttribute('position');
  const edges = new Map();
  for (let t = 0; t < index.length; t += 3) {
    for (let k = 0; k < 3; k += 1) {
      const key = `${index[t + k]}>${index[t + (k + 1) % 3]}`;
      edges.set(key, (edges.get(key) || 0) + 1);
    }
  }
  let open = 0;
  for (const [key, count] of edges) {
    const [from, to] = key.split('>');
    if (count !== 1 || edges.get(`${to}>${from}`) !== 1) open += 1;
  }
  const euler = position.count - edges.size / 2 + index.length / 3;
  harness.check('surface_closed_and_welded', open === 0 && euler === 2, {triangles: index.length / 3, euler, open_edges: open});
  let worst = 0;
  for (let v = 0; v < position.count; v += 1) {
    worst = Math.max(worst, Math.abs(density(position.getX(v), position.getY(v), position.getZ(v)) - 1));
  }
  harness.check('vertices_on_level_set', worst < 0.08, {worst_density_error: worst});
  const averaged = geometry.clone();
  averaged.computeVertexNormals();
  const ours = geometry.getAttribute('normal');
  const theirs = averaged.getAttribute('normal');
  let sum = 0;
  for (let v = 0; v < ours.count; v += 1) {
    sum += ours.getX(v) * theirs.getX(v) + ours.getY(v) * theirs.getY(v) + ours.getZ(v) * theirs.getZ(v);
  }
  harness.check('gradient_normals_match_face_normals', sum / ours.count > 0.99, {mean_dot: sum / ours.count});

  const background = new THREE.Color(0x15181f);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(2, 3, 4);
    const rim = new THREE.DirectionalLight(0x7fb7ff, 1.4);
    rim.position.set(-3, 1, -2);
    target.add(key, rim, new THREE.HemisphereLight(0xffe2c4, 0x1c2433, 0.8));
  }
  const material = new THREE.MeshStandardMaterial({color: 0xe0566b, roughness: 0.28, metalness: 0.1});
  scene.add(new THREE.Mesh(geometry, material));
  for (const {centre, strength} of BALLS) {
    const ball = new THREE.Mesh(new THREE.SphereGeometry(Math.sqrt(strength), 32, 16), material);
    ball.position.fromArray(centre);
    baseline.add(ball);
  }
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0.6, 0.5, 3.4);
  camera.lookAt(0.03, 0, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
