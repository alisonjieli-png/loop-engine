// Demo of tangent frames, rendered by the family verifier and usable as an example: a tiled normal map on a torus knot
// and a dimpled one on a sphere, lit through the tangent attribute this module computes (three.js switches to vertex
// tangents when a geometry has one). The baseline shows the same meshes without normal maps. A check compares the
// tangents with three.js's own BufferGeometry.computeTangents.

function normalMap(THREE, size, height) {
  const heights = new Float32Array(size * size);
  for (let y = 0; y < size; y += 1) for (let x = 0; x < size; x += 1) heights[y * size + x] = height(x / size, y / size);
  const data = new Uint8Array(size * size * 4);
  const at = (x, y) => heights[((y + size) % size) * size + ((x + size) % size)];
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = (at(x + 1, y) - at(x - 1, y)) * size * 0.5;
      const dy = (at(x, y + 1) - at(x, y - 1)) * size * 0.5;
      const length = Math.hypot(dx, dy, 1);
      data.set([(-dx / length) * 127.5 + 127.5, (-dy / length) * 127.5 + 127.5, (1 / length) * 127.5 + 127.5, 255],
        (y * size + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, size, size);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.needsUpdate = true;
  return texture;
}

export function demo(THREE, frames, harness) {
  const smooth = (edge0, edge1, x) => {
    const t = Math.min(Math.max((x - edge0) / (edge1 - edge0), 0), 1);
    return t * t * (3 - 2 * t);
  };
  const tiles = normalMap(THREE, 128, (u, v) => {
    const fu = (u * 8) % 1;
    const fv = (v * 4 + (Math.floor(u * 8) % 2) * 0.5) % 1;
    return 0.02 * smooth(0, 0.08, Math.min(fu, 1 - fu)) * smooth(0, 0.08, Math.min(fv, 1 - fv));
  });
  tiles.repeat.set(6, 1);
  const dimples = normalMap(THREE, 128, (u, v) => {
    const cu = ((u * 6) % 1) - 0.5;
    const cv = ((v * 6) % 1) - 0.5;
    return -0.012 * Math.exp(-(cu * cu + cv * cv) * 30);
  });
  dimples.repeat.set(3, 2);

  const knot = frames.addTangents(THREE, new THREE.TorusKnotGeometry(0.55, 0.2, 200, 24));
  const sphere = frames.addTangents(THREE, new THREE.SphereGeometry(0.55, 64, 32));
  const background = new THREE.Color(0x1d2129);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(-2, 3, 3);
    target.add(key, new THREE.HemisphereLight(0xd6e2ff, 0x2a231c, 0.9));
  }
  const tiled = new THREE.MeshStandardMaterial({color: 0xc98a5a, roughness: 0.55, normalMap: tiles});
  const dimpled = new THREE.MeshStandardMaterial({color: 0x9fb4c8, roughness: 0.3, metalness: 0.6, normalMap: dimples});
  const placed = [[knot, tiled, [-0.62, 0.15, 0]], [sphere, dimpled, [0.95, -0.25, 0.2]]];
  for (const [geometry, material, position] of placed) {
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.fromArray(position);
    scene.add(mesh);
    const plain = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: material.color, roughness: material.roughness,
      metalness: material.metalness}));
    plain.position.fromArray(position);
    baseline.add(plain);
  }

  // Our tangents against three.js's own computeTangents on the same knot.
  const reference = new THREE.TorusKnotGeometry(0.55, 0.2, 200, 24);
  reference.computeTangents();
  const ours = knot.getAttribute('tangent');
  const theirs = reference.getAttribute('tangent');
  let dots = 0;
  let sameSide = 0;
  for (let v = 0; v < ours.count; v += 1) {
    const a = [ours.getX(v), ours.getY(v), ours.getZ(v)];
    const b = [theirs.getX(v), theirs.getY(v), theirs.getZ(v)];
    dots += (a[0] * b[0] + a[1] * b[1] + a[2] * b[2]) / (Math.hypot(...b) || 1);
    if (ours.getW(v) === theirs.getW(v)) sameSide += 1;
  }
  harness.check('tangents_match_three_computeTangents', dots / ours.count > 0.99 && sameSide === ours.count,
    {mean_dot: dots / ours.count, same_handedness: sameSide, vertices: ours.count});
  harness.check('tangent_attribute_is_vec4', ours.itemSize === 4 && sphere.getAttribute('tangent').itemSize === 4, {});

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0.15, 0.2, 4.7);
  camera.lookAt(0.1, -0.05, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
