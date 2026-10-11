// Demo of the rounded box geometry, rendered by the family verifier and usable as an example: three boxes with
// different radii under a key light and a sky fill. The baseline shows the same boxes as sharp BoxGeometry.

export function demo(THREE, box, harness) {
  const sizes = [
    {width: 1.1, height: 0.7, depth: 0.9, radius: 0.08, position: [-1.15, -0.35, 0.2], color: 0xd9744a},
    {width: 0.9, height: 0.9, depth: 0.9, radius: 0.26, position: [0.05, 0.25, -0.2], color: 0x4f8fd6},
    {width: 0.8, height: 1.3, depth: 0.5, radius: 0.24, position: [1.1, -0.15, 0.35], color: 0x6cbf6a},
  ];
  const background = new THREE.Color(0x20242e);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(3, 5, 4);
    target.add(key, new THREE.HemisphereLight(0xbfd4ff, 0x30261f, 1.1));
  }
  for (const entry of sizes) {
    const {position, color, ...options} = entry;
    const geometry = box.createRoundedBoxGeometry(THREE, {...options, bevelSegments: 6});
    geometry.computeBoundingBox();
    const extent = geometry.boundingBox.getSize(new THREE.Vector3());
    harness.check(`bounds_match_size_${options.radius}`,
      Math.abs(extent.x - options.width) < 1e-5 && Math.abs(extent.y - options.height) < 1e-5
        && Math.abs(extent.z - options.depth) < 1e-5, {size: extent.toArray()});
    harness.check(`six_material_groups_${options.radius}`, geometry.groups.length === 6, {groups: geometry.groups.length});
    const material = new THREE.MeshStandardMaterial({color, roughness: 0.35, metalness: 0.05});
    const rounded = new THREE.Mesh(geometry, material);
    rounded.position.fromArray(position);
    rounded.rotation.set(0.35, 0.6, 0);
    scene.add(rounded);
    const sharp = new THREE.Mesh(new THREE.BoxGeometry(options.width, options.height, options.depth), material);
    sharp.position.copy(rounded.position);
    sharp.rotation.copy(rounded.rotation);
    baseline.add(sharp);
  }
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0.3, 1.4, 4.6);
  camera.lookAt(0, -0.05, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
