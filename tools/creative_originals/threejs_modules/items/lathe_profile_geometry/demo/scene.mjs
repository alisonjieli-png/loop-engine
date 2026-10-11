// Demo of the lathe profile geometry, rendered by the family verifier and usable as an example: a vase, a goblet with
// creased foot edges, a pawn and a torus ring from a closed profile. The baseline shows cylinders in their places.

const VASE = [[0, 0], [0.34, 0], [0.4, 0.08], [0.5, 0.32], [0.48, 0.58], [0.34, 0.86], [0.24, 1.02], [0.26, 1.16],
  [0.34, 1.24]];
const GOBLET = [[0, 0], [0.36, 0], [0.36, 0.05], [0.07, 0.12], [0.05, 0.52], [0.18, 0.58], [0.33, 0.76], [0.38, 1.02]];
const PAWN = [[0, 0], [0.4, 0], [0.4, 0.08], [0.3, 0.16], [0.17, 0.32], [0.12, 0.62], [0.22, 0.68], [0.12, 0.74],
  ...Array.from({length: 11}, (_, k) => {
    const angle = -Math.PI / 2 + (Math.PI * (k + 1)) / 12;
    return [0.2 * Math.cos(angle), 0.94 + 0.2 * Math.sin(angle)];
  }), [0, 1.14]];
const RING = Array.from({length: 32}, (_, k) => [0.36 + 0.1 * Math.cos((2 * Math.PI * k) / 32), 0.1 * Math.sin((2 * Math.PI * k) / 32)]);

function signedVolume(geometry) {
  const position = geometry.getAttribute('position').array;
  const index = geometry.getIndex().array;
  let volume = 0;
  for (let t = 0; t < index.length; t += 3) {
    const [a, b, c] = [0, 1, 2].map((k) => [position[index[t + k] * 3], position[index[t + k] * 3 + 1],
      position[index[t + k] * 3 + 2]]);
    volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
  }
  return volume;
}

export function demo(THREE, lathe, harness) {
  const background = new THREE.Color(0x1c2029);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.4);
    key.position.set(3, 5, 4);
    target.add(key, new THREE.HemisphereLight(0xcdd9ff, 0x2b231d, 1.0));
  }
  const pieces = [
    {profile: VASE, options: {segments: 64}, color: 0x3f8fbf, position: [-1.12, -0.62, 0]},
    {profile: GOBLET, options: {segments: 64, creaseAngle: 25}, color: 0xd9a441, position: [-0.33, -0.62, 0.2]},
    {profile: PAWN, options: {segments: 48}, color: 0xe8e2d6, position: [0.42, -0.62, 0.15]},
    {profile: RING, options: {segments: 64, closed: true}, color: 0xc0504d, position: [1.14, -0.2, 0]},
  ];
  for (const piece of pieces) {
    const geometry = lathe.createLatheProfileGeometry(THREE, piece.profile, piece.options);
    const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: piece.color, roughness: 0.32,
      metalness: piece.color === 0xd9a441 ? 0.6 : 0.05}));
    mesh.position.fromArray(piece.position);
    if (piece.options.closed) mesh.rotation.set(1.1, 0.3, 0);
    scene.add(mesh);
    const height = geometry.boundingBox.max.y - geometry.boundingBox.min.y;
    const cylinder = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, height, 24), mesh.material);
    cylinder.position.set(piece.position[0], piece.position[1] + (piece.options.closed ? 0 : height / 2), piece.position[2]);
    baseline.add(cylinder);
  }

  // The geometry three.js holds encloses the polygon version of the profile's volume.
  const segments = 64;
  const vase = lathe.createLatheProfileGeometry(THREE, VASE, {segments});
  const expected = lathe.latheProfileVolume(VASE) * (segments / (2 * Math.PI)) * Math.sin((2 * Math.PI) / segments);
  const actual = signedVolume(vase);
  harness.check('vase_volume_matches_profile', Math.abs(actual - expected) < 1e-4 * expected, {actual, expected});
  const ring = lathe.createLatheProfileGeometry(THREE, RING, {segments, closed: true});
  const ringExpected = lathe.latheProfileVolume(RING, true) * (segments / (2 * Math.PI)) * Math.sin((2 * Math.PI) / segments);
  harness.check('ring_volume_matches_profile', Math.abs(signedVolume(ring) - ringExpected) < 1e-4 * ringExpected,
    {actual: signedVolume(ring), expected: ringExpected});
  harness.check('vase_height_matches_profile', Math.abs(vase.boundingBox.max.y - 1.24) < 1e-6, {top: vase.boundingBox.max.y});

  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0, 0.95, 4.9);
  camera.lookAt(0, -0.05, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
