// Demo of the cinematic camera path, rendered by the family verifier and usable as an example. An overview camera
// looks at a small set: the path through five keyframes is drawn as a line that shifts from orange to blue, the
// keyframes as white beads, and twelve camera cones show the position and orientation sampleAt gives at equal steps
// of the timeline. The baseline is the same set without the path.

const KEYFRAMES = [
  {position: [0, 1.2, 6], target: [0, 1, 0]},
  {position: [4.2, 1.6, 3.8], target: [0, 1.2, 0]},
  {position: [4.6, 2.2, -0.6], target: [0, 1, 0]},
  {position: [0.6, 3, -5], target: [0, 0.8, 0]},
  {position: [-4.8, 2, -2], target: [0, 1, 0]},
];

function buildSet(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x10151f);
  scene.add(new THREE.HemisphereLight(0xdde6ff, 0x26201a, 1.4));
  const key = new THREE.DirectionalLight(0xfff0dc, 2.4);
  key.position.set(5, 9, 4);
  scene.add(key);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(7.5, 64), new THREE.MeshStandardMaterial({color: 0x2b3240}));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);
  const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.7, 0.85, 0.5, 32),
    new THREE.MeshStandardMaterial({color: 0x8d99ae, roughness: 0.6}));
  pedestal.position.y = 0.25;
  const statue = new THREE.Mesh(new THREE.TorusKnotGeometry(0.42, 0.14, 128, 16),
    new THREE.MeshStandardMaterial({color: 0xe0a458, roughness: 0.3, metalness: 0.4}));
  statue.position.y = 1.1;
  scene.add(pedestal, statue);
  return scene;
}

export function demo(THREE, cinematic, harness) {
  const path = new cinematic.CameraPath(KEYFRAMES, {easing: 'linear'});
  const fractions = path.keyframeFractions();
  const misses = fractions.map((fraction, index) => {
    const [x, y, z] = path.sampleAt(fraction).position;
    const [kx, ky, kz] = KEYFRAMES[index].position;
    return Math.hypot(x - kx, y - ky, z - kz);
  });
  harness.check('passes_through_keyframes', Math.max(...misses) < 1e-9, {largest_miss: Math.max(...misses)});

  const steps = [];
  let previous = path.sampleAt(0).position;
  let unit = true;
  for (let index = 1; index <= 300; index += 1) {
    const {position, quaternion} = path.sampleAt(index / 300);
    steps.push(Math.hypot(position[0] - previous[0], position[1] - previous[1], position[2] - previous[2]));
    unit = unit && Math.abs(Math.hypot(...quaternion) - 1) < 1e-12;
    previous = position;
  }
  const ratio = Math.max(...steps) / Math.min(...steps);
  harness.check('near_constant_speed', ratio < 1.02, {largest_over_smallest_step: ratio});
  harness.check('unit_quaternions', unit, {samples: 300});

  const probe = new THREE.PerspectiveCamera();
  path.applyTo(probe, 0.42);
  const sample = path.sampleAt(0.42);
  const forward = probe.getWorldDirection(new THREE.Vector3());
  const expected = new THREE.Vector3(0, 0, -1).applyQuaternion(new THREE.Quaternion(...sample.quaternion));
  harness.check('apply_to_poses_a_three_camera', probe.position.distanceTo(new THREE.Vector3(...sample.position)) < 1e-12
    && forward.angleTo(expected) < 1e-6, {});

  const scene = buildSet(THREE);
  const points = [];
  const colours = [];
  for (let index = 0; index <= 400; index += 1) {
    const t = index / 400;
    points.push(...path.sampleAt(t).position);
    colours.push(1 - 0.75 * t, 0.55 + 0.1 * t, 0.2 + 0.8 * t);
  }
  const line = new THREE.BufferGeometry();
  line.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
  line.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3));
  scene.add(new THREE.Line(line, new THREE.LineBasicMaterial({vertexColors: true})));
  const bead = new THREE.SphereGeometry(0.17, 16, 8);
  const white = new THREE.MeshBasicMaterial({color: 0xffffff});
  for (const frame of KEYFRAMES) {
    const mesh = new THREE.Mesh(bead, white);
    mesh.position.fromArray(frame.position);
    scene.add(mesh);
  }
  const cone = new THREE.ConeGeometry(0.24, 0.7, 16);
  cone.rotateX(-Math.PI / 2);
  for (let index = 0; index < 12; index += 1) {
    const t = index / 11;
    const {position, quaternion} = path.sampleAt(t);
    const gizmo = new THREE.Mesh(cone, new THREE.MeshStandardMaterial({color: new THREE.Color().setHSL(0.08 + 0.5 * t, 0.8, 0.55)}));
    gizmo.position.fromArray(position);
    gizmo.quaternion.fromArray(quaternion);
    scene.add(gizmo);
  }
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 80);
  camera.position.set(0.8, 15, 9.5);
  camera.lookAt(-0.1, 0, 0.4);
  return {scene, camera, baseline: {scene: buildSet(THREE), camera}};
}
