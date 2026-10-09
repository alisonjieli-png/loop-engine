// Demo of the FABRIK solver, rendered by the family verifier and usable as an example. Two tentacles of nine joints
// (three.js Object3D chains, each segment a tapered cylinder) start straight up. applyFabrikChain curls the left one
// down to a target near the floor and stretches the right one straight toward a target out of its reach. The
// baseline shows both tentacles at rest.

const SEGMENTS = 8;
const SEGMENT_LENGTH = 0.32;

function buildTentacle(THREE, base, hue) {
  const joints = [];
  let parent = null;
  for (let index = 0; index <= SEGMENTS; index += 1) {
    const joint = new THREE.Group();
    if (parent) {
      joint.position.set(0, SEGMENT_LENGTH, 0);
      parent.add(joint);
    } else {
      joint.position.fromArray(base);
    }
    if (index < SEGMENTS) {
      const radius = 0.11 * (1 - index / (SEGMENTS + 2));
      const geometry = new THREE.CylinderGeometry(radius * 0.8, radius, SEGMENT_LENGTH, 18);
      geometry.translate(0, SEGMENT_LENGTH / 2, 0);
      const colour = new THREE.Color().setHSL(hue, 0.65, 0.42 + 0.03 * index);
      joint.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: colour, roughness: 0.4})));
      joint.add(new THREE.Mesh(new THREE.SphereGeometry(radius * 1.05, 16, 8),
        new THREE.MeshStandardMaterial({color: colour, roughness: 0.4})));
    }
    joints.push(joint);
    parent = joint;
  }
  return joints;
}

function buildScene(THREE, tentacles, targets) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1c26);
  scene.add(new THREE.HemisphereLight(0xd4f1ff, 0x1d2a22, 1.5));
  const key = new THREE.DirectionalLight(0xffffff, 2.0);
  key.position.set(3, 6, 4);
  scene.add(key);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(5, 48), new THREE.MeshStandardMaterial({color: 0x2c4a52}));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);
  for (const joints of tentacles) scene.add(joints[0]);
  for (const target of targets) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.035, 12, 40),
      new THREE.MeshStandardMaterial({color: 0xffb703, emissive: 0xffb703, emissiveIntensity: 0.7}));
    ring.position.fromArray(target);
    scene.add(ring);
  }
  return scene;
}

export function demo(THREE, fabrik, harness) {
  const near = [0.35, 0.45, 0.7];
  const far = [3.0, 3.1, -0.4];
  const left = buildTentacle(THREE, [-1.2, 0, 0], 0.93);
  const right = buildTentacle(THREE, [1.3, 0, 0], 0.52);
  const world = (object) => object.getWorldPosition(new THREE.Vector3());

  const solved = fabrik.applyFabrikChain(THREE, left, near, {maxIterations: 200, tolerance: 1e-5});
  const tip = world(left[SEGMENTS]);
  harness.check('tip_reaches_target', solved.reached === true && tip.distanceTo(new THREE.Vector3(...near)) <= 1e-5,
    {iterations: solved.iterations, miss: tip.distanceTo(new THREE.Vector3(...near))});
  let lengthsKept = true;
  for (let index = 0; index < SEGMENTS; index += 1) {
    lengthsKept = lengthsKept && Math.abs(world(left[index]).distanceTo(world(left[index + 1])) - SEGMENT_LENGTH) < 1e-9;
  }
  harness.check('segment_lengths_kept', lengthsKept, {segments: SEGMENTS});
  harness.check('root_fixed_and_hierarchy_matches', world(left[0]).distanceTo(new THREE.Vector3(-1.2, 0, 0)) === 0
    && world(left[4]).distanceTo(new THREE.Vector3(...solved.joints[4])) < 1e-9, {});

  const stretched = fabrik.applyFabrikChain(THREE, right, far);
  const base = new THREE.Vector3(1.3, 0, 0);
  const direction = new THREE.Vector3(...far).sub(base).normalize();
  const expected = base.clone().addScaledVector(direction, SEGMENTS * SEGMENT_LENGTH);
  harness.check('unreachable_target_straightens', stretched.reachable === false
    && world(right[SEGMENTS]).distanceTo(expected) < 1e-9, {miss: world(right[SEGMENTS]).distanceTo(expected)});

  const scene = buildScene(THREE, [left, right], [near, far]);
  const rest = buildScene(THREE, [buildTentacle(THREE, [-1.2, 0, 0], 0.93), buildTentacle(THREE, [1.3, 0, 0], 0.52)], [near, far]);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0.3, 2.4, 7.2);
  camera.lookAt(0.4, 1.3, 0);
  return {scene, camera, baseline: {scene: rest, camera}};
}
