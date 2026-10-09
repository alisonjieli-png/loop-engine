// Demo of welding and crease normals, rendered by the family verifier and usable as an example: four three.js
// geometries turned into triangle soups (every face flat) and rebuilt with crease-angle normals: the cylinder's side
// turns smooth while its caps stay sharp, the sphere and the knot turn smooth, the box and the dodecahedron keep their
// edges. The baseline shows the same soups with flat face normals.

export function demo(THREE, crease, harness) {
  const sources = [
    {geometry: new THREE.CylinderGeometry(0.45, 0.45, 0.9, 28), position: [-1.05, 0.5, 0], color: 0x4f8fd6},
    {geometry: new THREE.IcosahedronGeometry(0.5, 2), position: [0.05, 0.55, 0], color: 0xe07a4f},
    {geometry: new THREE.BoxGeometry(0.75, 0.75, 0.75), position: [1.1, 0.5, 0], color: 0x6cbf84},
    {geometry: new THREE.TorusKnotGeometry(0.3, 0.11, 72, 10), position: [-0.55, -0.62, 0], color: 0xf2c14e},
    {geometry: new THREE.DodecahedronGeometry(0.48, 0), position: [0.65, -0.62, 0], color: 0x9b6dd6},
  ];
  const background = new THREE.Color(0x1c2029);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(2, 3, 4);
    target.add(key, new THREE.HemisphereLight(0xcfdcff, 0x2a231d, 1.0));
  }
  // Triangle soups: indexed geometries are expanded, the polyhedra already are soups.
  const soups = sources.map((source) => (source.geometry.index ? source.geometry.toNonIndexed() : source.geometry));
  sources.forEach((source, index) => {
    const soup = soups[index];
    soup.computeVertexNormals();
    const creased = crease.createCreasedGeometry(THREE, soup, 40);
    const material = new THREE.MeshStandardMaterial({color: source.color, roughness: 0.35, metalness: 0.05});
    const mesh = new THREE.Mesh(creased, material);
    const flat = new THREE.Mesh(soup, material);
    for (const shown of [mesh, flat]) {
      shown.position.fromArray(source.position);
      shown.rotation.set(0.5, 0.4, 0);
    }
    scene.add(mesh);
    baseline.add(flat);
  });

  // The cylinder keeps two kinds of normals only: horizontal on the side, vertical on the caps.
  const cylinder = crease.createCreasedGeometry(THREE, soups[0], 40);
  const normals = cylinder.getAttribute('normal');
  let mixed = 0;
  for (let v = 0; v < normals.count; v += 1) {
    const y = Math.abs(normals.getY(v));
    if (!(y < 1e-6 || Math.abs(y - 1) < 1e-6)) mixed += 1;
  }
  harness.check('cylinder_side_smooth_caps_sharp', mixed === 0, {vertices: normals.count, mixed});
  // The sphere becomes smooth: every normal close to the radial direction.
  const sphere = crease.createCreasedGeometry(THREE, soups[1], 40);
  const points = sphere.getAttribute('position');
  const sphereNormals = sphere.getAttribute('normal');
  let worst = 1;
  for (let v = 0; v < points.count; v += 1) {
    const length = Math.hypot(points.getX(v), points.getY(v), points.getZ(v));
    const dot = (points.getX(v) * sphereNormals.getX(v) + points.getY(v) * sphereNormals.getY(v)
      + points.getZ(v) * sphereNormals.getZ(v)) / length;
    worst = Math.min(worst, dot);
  }
  harness.check('sphere_normals_radial', worst > 0.98, {worst_dot: worst});
  const box = crease.weldVertices(soups[2].getAttribute('position').array, 1e-6);
  harness.check('box_welds_to_eight_corners', box.positions.length / 3 === 8, {welded: box.positions.length / 3});

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0, 0.1, 4.75);
  camera.lookAt(0, 0, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
