// Demo of the trauma camera shake, rendered by the family verifier and usable as an example. A camera that has just
// taken a full hit looks at a row of pillars; a line in the middle of the frame traces the shake's translation over
// the next 1.4 seconds, magnified 12 times, fading from red to blue as the trauma decays. The baseline is the same
// scene seen from the unshaken camera, without the trace.

function buildScene(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x141b2b);
  scene.add(new THREE.HemisphereLight(0xc9d8ff, 0x2a2018, 1.3));
  const key = new THREE.DirectionalLight(0xffe9c8, 2.2);
  key.position.set(4, 7, 5);
  scene.add(key);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(30, 30), new THREE.MeshStandardMaterial({color: 0x2c3442}));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
  const colours = [0xe76f51, 0xf4a261, 0xe9c46a, 0x2a9d8f, 0x6d9dc5, 0xb56576, 0x8ab17d];
  colours.forEach((colour, index) => {
    const height = 1.2 + ((index * 37) % 5) * 0.35;
    const pillar = new THREE.Mesh(new THREE.BoxGeometry(0.55, height, 0.55),
      new THREE.MeshStandardMaterial({color: colour, roughness: 0.55}));
    pillar.position.set((index - 3) * 1.05, height / 2, -1.2 - Math.abs(index - 3) * 0.45);
    scene.add(pillar);
  });
  return scene;
}

export function demo(THREE, shakeModule, harness) {
  const base = new THREE.PerspectiveCamera(48, 1, 0.1, 60);
  base.position.set(0, 1.5, 6);
  base.lookAt(0, 1.1, 0);
  const basePosition = base.position.toArray();
  const baseQuaternion = base.quaternion.toArray();

  // Zero trauma leaves the camera exactly at its base pose.
  const calm = new shakeModule.CameraShake();
  const probe = new THREE.PerspectiveCamera();
  calm.applyTo(probe, basePosition, baseQuaternion);
  harness.check('zero_trauma_keeps_base_pose',
    probe.position.equals(base.position) && probe.quaternion.equals(base.quaternion), {});

  // A full hit: sample the shake over 1.4 s; every offset stays within its amplitude and the trauma reaches zero.
  const shake = new shakeModule.CameraShake({decay: 0.8});
  shake.addTrauma(1);
  const settings = shake.settings;
  const trace = [];
  const colours = [];
  let within = true;
  for (let step = 0; step <= 280; step += 1) {
    const {translation, rotation} = shake.sample();
    translation.forEach((value, axis) => { within = within && Math.abs(value) <= settings.translation[axis]; });
    rotation.forEach((value, axis) => { within = within && Math.abs(value) <= settings.rotation[axis]; });
    trace.push(translation[0] * 12, 1.1 + translation[1] * 12, 1.2);
    const fade = step / 280;
    colours.push(1 - fade * 0.7, 0.25 + fade * 0.2, 0.2 + fade * 0.8);
    shake.update(0.005);
  }
  harness.check('offsets_within_amplitudes', within, {samples: 281});
  harness.check('trauma_decays_to_zero', shake.trauma === 0 && Math.abs(shake.time - 1.405) < 1e-9,
    {trauma: shake.trauma, time: shake.time});

  // The shaken view: the camera just after the hit.
  const hit = new shakeModule.CameraShake();
  hit.addTrauma(1);
  hit.update(0.06);
  const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 60);
  hit.applyTo(camera, basePosition, baseQuaternion);
  const offset = camera.position.distanceTo(base.position);
  harness.check('shaken_camera_moves_within_bounds', offset > 0 && offset <= Math.hypot(...settings.translation),
    {offset, angle: camera.quaternion.angleTo(base.quaternion)});

  const scene = buildScene(THREE);
  const line = new THREE.BufferGeometry();
  line.setAttribute('position', new THREE.Float32BufferAttribute(trace, 3));
  line.setAttribute('color', new THREE.Float32BufferAttribute(colours, 3));
  scene.add(new THREE.Line(line, new THREE.LineBasicMaterial({vertexColors: true})));
  return {scene, camera, baseline: {scene: buildScene(THREE), camera: base}};
}
