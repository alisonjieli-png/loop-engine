// Demo of Poisson disk scattering, rendered by the family verifier and usable as an example: a forest of instanced
// cones on a meadow, kept out of a clearing by a mask and thinned toward the camera by a density function, with rocks
// scattered inside the clearing by a second call. The baseline is the empty meadow.

export function demo(THREE, scatter, harness) {
  const clearing = {x: 0.6, y: 0.8, radius: 1.7};
  const minDistance = 0.62;
  const outsideClearing = (x, y) => Math.hypot(x - clearing.x, y - clearing.y) > clearing.radius;
  const thinnerInFront = (x, y) => 1 - 0.55 * Math.min(Math.max((y + 5) / 10, 0), 1);
  const points = scatter.poissonDiskPoints({
    width: 10, height: 10, originX: -5, originY: -5, minDistance, seed: 21, mask: outsideClearing, density: thinnerInFront,
  });
  const count = points.length / 2;
  const matrices = scatter.toInstanceMatrices(points, {scaleJitter: 0.35, seed: 4});
  const rocks = scatter.poissonDiskPoints({
    width: 3.4, height: 3.4, originX: clearing.x - 1.7, originY: clearing.y - 1.7, minDistance: 0.45, seed: 2,
    mask: (x, y) => Math.hypot(x - clearing.x, y - clearing.y) < clearing.radius - 0.25,
  });

  const cone = new THREE.ConeGeometry(0.27, 0.95, 7);
  cone.translate(0, 0.475, 0);
  const trees = new THREE.InstancedMesh(cone, new THREE.MeshStandardMaterial({roughness: 0.9}), count);
  trees.instanceMatrix.array.set(matrices);
  trees.instanceMatrix.needsUpdate = true;
  const greens = [0x2f6b3a, 0x3d8a4a, 0x285c33, 0x4b9a55, 0x356e2c];
  const colour = new THREE.Color();
  for (let index = 0; index < count; index += 1) trees.setColorAt(index, colour.setHex(greens[index % greens.length]));
  const stone = new THREE.InstancedMesh(new THREE.DodecahedronGeometry(0.13, 0),
    new THREE.MeshStandardMaterial({color: 0x9a948a, roughness: 0.8}), rocks.length / 2);
  stone.instanceMatrix.array.set(scatter.toInstanceMatrices(rocks, {offset: 0.06, scaleJitter: 0.5, seed: 9}));
  stone.instanceMatrix.needsUpdate = true;

  // Independent read-back through three.js: decompose every instance matrix and re-measure the spacing.
  const matrix = new THREE.Matrix4();
  const position = new THREE.Vector3();
  const rotation = new THREE.Quaternion();
  const scale = new THREE.Vector3();
  const placed = [];
  let mismatch = 0;
  let scaleRange = [Infinity, -Infinity];
  for (let index = 0; index < count; index += 1) {
    trees.getMatrixAt(index, matrix);
    matrix.decompose(position, rotation, scale);
    mismatch = Math.max(mismatch, Math.abs(position.x - points[2 * index]), Math.abs(position.z - points[2 * index + 1]));
    scaleRange = [Math.min(scaleRange[0], scale.y), Math.max(scaleRange[1], scale.y)];
    placed.push(new THREE.Vector2(position.x, position.z));
  }
  let closest = Infinity;
  for (let i = 0; i < placed.length; i += 1) {
    for (let j = i + 1; j < placed.length; j += 1) closest = Math.min(closest, placed[i].distanceTo(placed[j]));
  }
  const centre = new THREE.Vector2(clearing.x, clearing.y);
  const nearestToCentre = Math.min(...placed.map((point) => point.distanceTo(centre)));
  harness.check('instances_match_points', mismatch < 1e-5 && scaleRange[0] >= 0.65 - 1e-5 && scaleRange[1] <= 1.35 + 1e-5,
    {instances: count, largest_offset: mismatch, scale_range: scaleRange});
  harness.check('spacing_holds_after_decompose', closest >= minDistance * (1 - 1e-6), {closest_pair: closest});
  harness.check('clearing_stays_empty', nearestToCentre > clearing.radius, {nearest_to_centre: nearestToCentre});

  const build = (withScatter) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xa9c7e0);
    scene.add(new THREE.HemisphereLight(0xe3f0ff, 0x4a5a32, 1.6));
    const sun = new THREE.DirectionalLight(0xfff0d6, 2.2);
    sun.position.set(-4, 7, 3);
    scene.add(sun);
    const ground = new THREE.Mesh(new THREE.CircleGeometry(7.5, 64), new THREE.MeshStandardMaterial({color: 0x7f9b4e}));
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground);
    if (withScatter) scene.add(trees, stone);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 60);
  camera.position.set(0.5, 6.2, 8.2);
  camera.lookAt(0, 0, -0.6);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
