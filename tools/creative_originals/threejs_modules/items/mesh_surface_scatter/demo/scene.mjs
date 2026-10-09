// Demo of mesh surface scattering, rendered by the family verifier and usable as an example: 900 spikes stand on a
// torus knot along its smooth normals, denser where a per-vertex weight is high. The baseline is the bare knot. In
// the browser every sample is checked against three.js Triangle.closestPointToPoint on its own triangle.

export function demo(THREE, scatter, harness) {
  const knot = new THREE.TorusKnotGeometry(0.95, 0.32, 160, 20);
  const position = knot.attributes.position;
  const weights = new Float32Array(position.count);
  for (let index = 0; index < position.count; index += 1) weights[index] = 0.25 + Math.max(position.getY(index), 0);
  const samples = scatter.scatterOnGeometry(knot, {count: 900, seed: 17, weights});

  // Independent read-back: each sample against its triangle, with three.js geometry code.
  const triangle = new THREE.Triangle();
  const closest = new THREE.Vector3();
  const point = new THREE.Vector3();
  const faceNormal = new THREE.Vector3();
  const index = knot.index;
  let farthest = 0;
  let leastAligned = 1;
  let upper = 0;
  for (let k = 0; k < 900; k += 1) {
    const t = samples.triangles[k];
    triangle.setFromAttributeAndIndices(position, index.getX(3 * t), index.getX(3 * t + 1), index.getX(3 * t + 2));
    point.fromArray(samples.positions, 3 * k);
    farthest = Math.max(farthest, triangle.closestPointToPoint(point, closest).distanceTo(point));
    triangle.getNormal(faceNormal);
    leastAligned = Math.min(leastAligned, faceNormal.dot(new THREE.Vector3().fromArray(samples.normals, 3 * k)));
    if (point.y > 0) upper += 1;
  }
  harness.check('samples_lie_on_their_triangles', farthest < 1e-5, {largest_distance: farthest});
  harness.check('normals_face_out_with_their_triangles', leastAligned > 0.5, {smallest_dot: leastAligned});
  harness.check('weights_favour_the_upper_half', upper > 600, {upper_samples: upper, of: 900});

  const spike = new THREE.ConeGeometry(0.035, 0.22, 6);
  spike.translate(0, 0.11, 0);
  const spikes = new THREE.InstancedMesh(spike, new THREE.MeshStandardMaterial({color: 0xffa040, roughness: 0.45}), 900);
  spikes.instanceMatrix.array.set(scatter.surfaceMatrices(samples, {scaleJitter: 0.4, seed: 2}));
  spikes.instanceMatrix.needsUpdate = true;

  const build = (withSpikes) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x161b29);
    scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x302020, 1.3));
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(2, 4, 5);
    scene.add(key);
    scene.add(new THREE.Mesh(knot, new THREE.MeshStandardMaterial({color: 0x2e5fa8, roughness: 0.35, metalness: 0.1})));
    if (withSpikes) scene.add(spikes);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0.3, 0.8, 5.6);
  camera.lookAt(0, 0, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
