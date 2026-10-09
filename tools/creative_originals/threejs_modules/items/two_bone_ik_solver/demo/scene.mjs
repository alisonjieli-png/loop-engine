// Demo of two-bone IK, rendered by the family verifier and usable as an example. Two arms built as three.js Object3D
// chains (shoulder -> elbow -> hand) start straight up. applyTwoBoneIK bends the left arm so its hand touches the red
// target, with the elbow leaning toward the blue pole marker, and stretches the right arm straight toward a target
// out of its reach. The baseline shows both arms in their rest pose.

const UPPER = 1.2;
const LOWER = 1.0;

function buildArm(THREE, base, colour) {
  const root = new THREE.Group();
  root.position.fromArray(base);
  const material = new THREE.MeshStandardMaterial({color: colour, roughness: 0.45});
  const jointMaterial = new THREE.MeshStandardMaterial({color: 0xf1f1f1, roughness: 0.3});
  const bone = (lengthOfBone) => {
    const geometry = new THREE.CylinderGeometry(0.07, 0.09, lengthOfBone, 20);
    geometry.translate(0, lengthOfBone / 2, 0);
    return new THREE.Mesh(geometry, material);
  };
  const joint = () => new THREE.Mesh(new THREE.SphereGeometry(0.12, 24, 12), jointMaterial);
  const upper = new THREE.Group();
  upper.add(bone(UPPER), joint());
  const lower = new THREE.Group();
  lower.position.set(0, UPPER, 0);
  lower.add(bone(LOWER), joint());
  const hand = new THREE.Group();
  hand.position.set(0, LOWER, 0);
  hand.add(joint());
  lower.add(hand);
  upper.add(lower);
  root.add(upper);
  return {root, upper, lower, hand};
}

function marker(THREE, position, colour, kind) {
  const geometry = kind === 'target' ? new THREE.TorusGeometry(0.24, 0.045, 12, 48) : new THREE.BoxGeometry(0.2, 0.2, 0.2);
  const mesh = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: colour, emissive: colour, emissiveIntensity: 0.6}));
  mesh.position.fromArray(position);
  return mesh;
}

function buildScene(THREE, arms, targets, poles) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x182030);
  scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x2a2420, 1.4));
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(3, 6, 5);
  scene.add(key);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 8), new THREE.MeshStandardMaterial({color: 0x2e3747}));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);
  for (const arm of arms) scene.add(arm.root);
  for (const target of targets) scene.add(marker(THREE, target, 0xe63946, 'target'));
  for (const pole of poles) scene.add(marker(THREE, pole, 0x4895ef, 'pole'));
  return scene;
}

export function demo(THREE, ik, harness) {
  const reachable = [-0.35, 1.15, 0.75];
  const pole = [-2.15, 2.0, 0.9];
  const unreachable = [3.6, 2.6, 0.4];
  const left = buildArm(THREE, [-1.3, 0, 0], 0xf4a261);
  const right = buildArm(THREE, [1.1, 0, 0], 0x2a9d8f);
  const world = (object) => object.getWorldPosition(new THREE.Vector3());

  const solution = ik.applyTwoBoneIK(THREE, left.upper, left.lower, left.hand, reachable, pole);
  const hand = world(left.hand);
  const elbow = world(left.lower);
  const shoulder = world(left.upper);
  harness.check('hand_reaches_target', hand.distanceTo(new THREE.Vector3(...reachable)) < 1e-9 && solution.reached === true,
    {miss: hand.distanceTo(new THREE.Vector3(...reachable))});
  harness.check('bone_lengths_kept', Math.abs(elbow.distanceTo(shoulder) - UPPER) < 1e-9
    && Math.abs(hand.distanceTo(elbow) - LOWER) < 1e-9, {upper: elbow.distanceTo(shoulder), lower: hand.distanceTo(elbow)});
  harness.check('hierarchy_matches_solver', elbow.distanceTo(new THREE.Vector3(...solution.mid)) < 1e-9, {});

  const far = ik.applyTwoBoneIK(THREE, right.upper, right.lower, right.hand, unreachable, [1.1, 1, 2]);
  const base = world(right.upper);
  const direction = new THREE.Vector3(...unreachable).sub(base).normalize();
  const expectedHand = base.clone().addScaledVector(direction, UPPER + LOWER);
  harness.check('unreachable_target_straightens_the_arm', far.reached === false
    && world(right.hand).distanceTo(expectedHand) < 1e-9, {miss: world(right.hand).distanceTo(expectedHand)});

  const scene = buildScene(THREE, [left, right], [reachable, unreachable], [pole]);
  const rest = buildScene(THREE, [buildArm(THREE, [-1.3, 0, 0], 0xf4a261), buildArm(THREE, [1.1, 0, 0], 0x2a9d8f)],
    [reachable, unreachable], [pole]);
  const camera = new THREE.PerspectiveCamera(46, 1, 0.1, 50);
  camera.position.set(0.5, 2.2, 8.2);
  camera.lookAt(0.5, 1.25, 0);
  return {scene, camera, baseline: {scene: rest, camera}};
}
