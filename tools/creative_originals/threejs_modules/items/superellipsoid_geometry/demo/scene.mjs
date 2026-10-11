// Demo of the superellipsoid geometry, rendered by the family verifier and usable as an example: six shapes from one
// generator, from a rounded cube to an octahedron and a star prism, under a key light and a sky fill. The baseline
// shows plain spheres in the same places.

const SHAPES = [
  {exponentY: 0.15, exponentXZ: 0.15, color: 0xe07a4f},
  {exponentY: 0.6, exponentXZ: 1.0, color: 0xf2c14e},
  {exponentY: 1.0, exponentXZ: 1.0, color: 0x6cbf84},
  {exponentY: 2.0, exponentXZ: 2.0, color: 0x4f8fd6},
  {exponentY: 0.2, exponentXZ: 2.6, color: 0x9b6dd6},
  {exponentY: 1.4, exponentXZ: 0.4, color: 0xd65f8f},
];

export function demo(THREE, superellipsoid, harness) {
  const background = new THREE.Color(0x1d212b);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.3);
    key.position.set(2.5, 4, 5);
    target.add(key, new THREE.HemisphereLight(0xc8d8ff, 0x2a2420, 1.0));
  }
  const radius = 0.48;
  SHAPES.forEach((shape, index) => {
    const {color, ...exponents} = shape;
    const geometry = superellipsoid.createSuperellipsoidGeometry(THREE, {
      ...exponents, radiusX: radius, radiusY: radius, radiusZ: radius, widthSegments: 96, heightSegments: 64,
    });
    const size = geometry.boundingBox.getSize(new THREE.Vector3());
    harness.check(`bounds_${index}`, [size.x, size.y, size.z].every((value) => Math.abs(value - 2 * radius) < 1e-4),
      {size: size.toArray(), exponents});
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color, roughness: 0.38, metalness: 0.08}));
    mesh.position.set((index % 3) * 1.25 - 1.25, index < 3 ? 0.62 : -0.62, 0);
    mesh.rotation.set(0.45, 0.6, 0);
    scene.add(mesh);
    const plain = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 16), mesh.material);
    plain.position.copy(mesh.position);
    baseline.add(plain);
  });

  // The analytic normals agree with the face normals three.js averages for the same sphere-shaped mesh.
  const sphere = superellipsoid.createSuperellipsoidGeometry(THREE, {exponentY: 1, exponentXZ: 1, widthSegments: 64,
    heightSegments: 32});
  const analytic = sphere.getAttribute('normal').array.slice();
  sphere.computeVertexNormals();
  const averaged = sphere.getAttribute('normal').array;
  let sum = 0;
  let worst = 1;
  for (let v = 0; v < analytic.length; v += 3) {
    const dot = analytic[v] * averaged[v] + analytic[v + 1] * averaged[v + 1] + analytic[v + 2] * averaged[v + 2];
    sum += dot;
    worst = Math.min(worst, dot);
  }
  const mean = sum / (analytic.length / 3);
  harness.check('analytic_normals_match_three_vertex_normals', mean > 0.995, {mean_dot: mean, worst_dot: worst});

  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0, 0.25, 5.2);
  camera.lookAt(0, 0, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
