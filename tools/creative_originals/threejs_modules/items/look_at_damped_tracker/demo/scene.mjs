// Demo of the damped look-at tracker, rendered by the family verifier and usable as an example. Three turrets track a
// glowing orb for two simulated seconds at 60 updates a second. The two outer turrets have the default limits and end
// aimed at the orb (their beams touch it); the right turret rests facing away with a yaw limit of 0.6 rad and stops
// at that limit. The baseline shows the turrets in their rest orientation.

const ORB = [0.3, 2.7, 2.0];

function buildTurret(THREE, position, restQuaternion, colour) {
  const base = new THREE.Group();
  base.position.fromArray(position);
  base.scale.setScalar(1.35);
  const metal = new THREE.MeshStandardMaterial({color: 0x59626f, roughness: 0.45, metalness: 0.5});
  const paint = new THREE.MeshStandardMaterial({color: colour, roughness: 0.4, metalness: 0.2});
  const pedestal = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.45, 0.6, 24), metal);
  pedestal.position.y = 0.3;
  base.add(pedestal);
  const head = new THREE.Group();
  head.position.y = 0.75;
  head.quaternion.fromArray(restQuaternion);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(0.32, 24, 16), paint);
  const barrelGeometry = new THREE.CylinderGeometry(0.06, 0.07, 0.8, 16);
  barrelGeometry.rotateX(Math.PI / 2);
  barrelGeometry.translate(0, 0, 0.55);
  head.add(dome, new THREE.Mesh(barrelGeometry, metal));
  base.add(head);
  return {base, head};
}

function buildScene(THREE, turrets, beams) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x121826);
  scene.add(new THREE.HemisphereLight(0xcfe0ff, 0x2a2219, 1.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.8);
  key.position.set(-3, 6, 5);
  scene.add(key);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(14, 10), new THREE.MeshStandardMaterial({color: 0x283040}));
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);
  const orb = new THREE.Mesh(new THREE.SphereGeometry(0.18, 24, 16), new THREE.MeshBasicMaterial({color: 0xffd166}));
  orb.position.fromArray(ORB);
  scene.add(orb);
  const glow = new THREE.PointLight(0xffd166, 6, 6);
  glow.position.fromArray(ORB);
  scene.add(glow);
  for (const turret of turrets) scene.add(turret.base);
  for (const beam of beams) scene.add(beam);
  return scene;
}

export function demo(THREE, look, harness) {
  const facingAway = [0, Math.sin(Math.PI / 4), 0, Math.cos(Math.PI / 4)];
  const setups = [
    {position: [-2.2, 0, 0], rest: [0, 0, 0, 1], options: {}, colour: 0xe76f51},
    {position: [0, 0, -1.2], rest: [0, 0, 0, 1], options: {maxSpeed: 2}, colour: 0x2a9d8f},
    {position: [2.2, 0, 0], rest: facingAway, options: {yawLimit: 0.6}, colour: 0x8e7dbe},
  ];
  const turrets = setups.map((setup) => buildTurret(THREE, setup.position, setup.rest, setup.colour));
  const trackers = setups.map((setup) => new look.LookAtTracker(setup.options, setup.rest));
  let largestTurn = 0;
  let allowed = true;
  const results = [];
  for (let frame = 0; frame < 120; frame += 1) {
    turrets.forEach((turret, index) => {
      const before = new THREE.Quaternion(...trackers[index].quaternion);
      const headPosition = turret.head.getWorldPosition(new THREE.Vector3()).toArray();
      results[index] = trackers[index].update(headPosition, ORB, 1 / 60);
      const turn = before.angleTo(new THREE.Quaternion(...results[index].quaternion));
      largestTurn = Math.max(largestTurn, turn);
      allowed = allowed && turn <= trackers[index].settings.maxSpeed / 60 + 1e-9;
      trackers[index].applyTo(turret.head);
    });
  }
  harness.check('turn_per_update_within_speed_cap', allowed, {largest_turn: largestTurn});

  const beams = [];
  const aimErrors = turrets.map((turret) => {
    const origin = turret.head.getWorldPosition(new THREE.Vector3());
    const forward = new THREE.Vector3(0, 0, 1).applyQuaternion(turret.head.getWorldQuaternion(new THREE.Quaternion()));
    const toward = new THREE.Vector3(...ORB).sub(origin);
    const start = 1.25;
    const span = Math.max(toward.length() - start, 0.1);
    const geometry = new THREE.CylinderGeometry(0.018, 0.018, span, 8);
    geometry.translate(0, span / 2 + start, 0);
    const beam = new THREE.Mesh(geometry, new THREE.MeshBasicMaterial({color: 0xff4d6d}));
    beam.position.copy(origin);
    beam.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), forward);
    beams.push(beam);
    return forward.angleTo(toward);
  });
  harness.check('free_turrets_aim_at_the_orb', aimErrors[0] < 1e-3 && aimErrors[1] < 1e-3,
    {aim_errors: aimErrors.slice(0, 2)});
  harness.check('limited_turret_stops_at_its_yaw_limit', results[2].clamped === true
    && Math.abs(Math.abs(trackers[2].yaw) - 0.6) < 1e-3 && aimErrors[2] > 0.5, {yaw: trackers[2].yaw});

  const scene = buildScene(THREE, turrets, beams);
  const rest = buildScene(THREE, setups.map((setup) => buildTurret(THREE, setup.position, setup.rest, setup.colour)), []);
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 50);
  camera.position.set(0.3, 2.3, 7.0);
  camera.lookAt(0.1, 1.25, 0.3);
  return {scene, camera, baseline: {scene: rest, camera}};
}
