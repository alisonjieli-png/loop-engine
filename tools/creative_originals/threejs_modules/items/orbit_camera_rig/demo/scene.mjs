// Demo of the orbit camera rig, rendered by the family verifier and usable as an example. A rig starts on a sculpture
// garden, receives a rotate, a dolly and a pixel pan, and settles over 1.5 s of 60 Hz updates; the frame is taken
// from the settled camera. The baseline is the view from the rig's starting state. In the browser the camera is
// checked against three.js Vector3.setFromSphericalCoords, the target's projection and a 20 Hz run.

function sequence(rig) {
  rig.rotate(0.95, -0.38).dolly(0.62).panPixels(-36, 18, 45, 256);
  return rig;
}

export function demo(THREE, orbit, harness) {
  const start = {target: [0.6, 0.7, -0.4], radius: 9, azimuth: -0.5, polar: 1.25, smoothTime: 0.15};
  const rig = sequence(new orbit.OrbitCameraRig(start));
  for (let frame = 0; frame < 90; frame += 1) rig.update(1 / 60);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  rig.applyTo(camera);
  camera.updateMatrixWorld();

  const target = new THREE.Vector3().fromArray(rig.current.target);
  const spherical = new THREE.Vector3().setFromSphericalCoords(rig.current.radius, rig.current.polar, rig.current.azimuth)
    .add(target);
  harness.check('position_matches_three_spherical', spherical.distanceTo(camera.position) < 1e-9,
    {difference: spherical.distanceTo(camera.position)});
  const projected = target.clone().project(camera);
  harness.check('target_projects_to_the_centre', Math.abs(projected.x) < 1e-6 && Math.abs(projected.y) < 1e-6,
    {ndc: [projected.x, projected.y]});
  const slow = sequence(new orbit.OrbitCameraRig(start));
  for (let frame = 0; frame < 30; frame += 1) slow.update(1 / 20);
  const drift = slow.position().reduce((sum, value, axis) => Math.max(sum, Math.abs(value - rig.position()[axis])), 0);
  harness.check('same_state_at_20_and_60_hz', drift < 1e-9, {difference: drift});
  const moving = rig.update(0);
  harness.check('distance_equals_radius', Math.abs(camera.position.distanceTo(target) - rig.current.radius) < 1e-9
    && typeof moving === 'boolean', {radius: rig.current.radius});

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0f1d2b);
  scene.fog = new THREE.Fog(0x0f1d2b, 12, 30);
  scene.add(new THREE.HemisphereLight(0xcfe6ff, 0x1d2a1a, 1.5));
  const sun = new THREE.DirectionalLight(0xffeedd, 2.2);
  sun.position.set(5, 8, 4);
  scene.add(sun);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(12, 64), new THREE.MeshStandardMaterial({color: 0x24384a}));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground);
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.55, 0.18, 160, 20),
    new THREE.MeshStandardMaterial({color: 0xf25f5c, roughness: 0.35}));
  knot.position.fromArray(start.target);
  scene.add(knot);
  const colours = [0xffe066, 0x70c1b3, 0x247ba0, 0xb2dbbf, 0xf3ffbd];
  for (let k = 0; k < 10; k += 1) {
    const angle = (k / 10) * Math.PI * 2;
    const height = 0.6 + (k % 3) * 0.5;
    const pillar = new THREE.Mesh(new THREE.BoxGeometry(0.45, height, 0.45),
      new THREE.MeshStandardMaterial({color: colours[k % colours.length], roughness: 0.6}));
    pillar.position.set(Math.cos(angle) * 3.4, height / 2, Math.sin(angle) * 3.4);
    scene.add(pillar);
  }
  const before = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  new orbit.OrbitCameraRig(start).applyTo(before);
  return {scene, camera, baseline: {scene, camera: before}};
}
