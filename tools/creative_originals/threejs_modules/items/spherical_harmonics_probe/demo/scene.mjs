// Demo of the spherical harmonics probe, rendered by the family verifier and usable as an example. A sky (blue from
// above, a warm sun lobe, dark ground) is projected to nine coefficients and given to three.js as a LightProbe, the
// only light in the scene: matte spheres must come out brighter on top than below, and three.js's own
// SphericalHarmonics3.getIrradianceAt must agree with evaluateIrradiance. The baseline has no probe.

function sky(direction) {
  const [x, y, z] = direction;
  const up = Math.max(y, 0);
  const sun = Math.max(0.35 * x + 0.8 * y + 0.48 * z, 0) ** 24 * 6;
  const ground = Math.max(-y, 0) * 0.08;
  return [0.25 + 0.55 * up + sun * 1.0 + ground, 0.32 + 0.6 * up + sun * 0.85 + ground * 0.8, 0.45 + 0.8 * up + sun * 0.6 + ground * 0.6]
    .map((value) => value * (y < -0.05 ? 0.25 : 1));
}

export function demo(THREE, probeModule, harness) {
  const coefficients = probeModule.projectRadiance(sky);
  const probe = probeModule.toLightProbe(THREE, coefficients);
  let worst = 0;
  for (const normal of [[0, 1, 0], [0, -1, 0], [1, 0, 0], [0.4, 0.4, 0.82]]) {
    const ours = probeModule.evaluateIrradiance(coefficients, normal);
    const length = Math.hypot(...normal);
    const theirs = probe.sh.getIrradianceAt(new THREE.Vector3(...normal.map((value) => value / length)), new THREE.Vector3());
    [theirs.x, theirs.y, theirs.z].forEach((value, index) => { worst = Math.max(worst, Math.abs(value - ours[index]) / Math.max(1e-3, Math.abs(ours[index]))); });
  }
  harness.check('three_irradiance_matches_evaluateIrradiance', worst < 1e-4, {worst_relative_difference: worst});

  const build = (withProbe) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x10141f);
    if (withProbe) scene.add(probe);
    const albedos = [0xf2f2f2, 0xe8a070, 0x7fb0e8];
    albedos.forEach((albedo, index) => {
      const ball = new THREE.Mesh(new THREE.SphereGeometry(0.42, 64, 32),
        new THREE.MeshStandardMaterial({color: albedo, roughness: 1, metalness: 0}));
      ball.position.set(-1.0 + index * 1.0, 0.1, 0);
      scene.add(ball);
    });
    const floor = new THREE.Mesh(new THREE.CircleGeometry(1.9, 64), new THREE.MeshStandardMaterial({color: 0x9c9488, roughness: 1}));
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -0.33;
    scene.add(floor);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 30);
  camera.position.set(0, 1.6, 4.4);
  camera.lookAt(0, -0.1, 0);

  // The white sphere's top and bottom, read from a render of the probe-lit scene.
  const scene = build(true);
  const pixels = harness.renderToCanvas(scene, camera);
  const at = (x, y) => pixels[(y * harness.size + x) * 4];
  const centre = new THREE.Vector3(-1.0, 0.1, 0);
  const project = (point) => {
    const ndc = point.clone().project(camera);
    return [Math.round((ndc.x * 0.5 + 0.5) * (harness.size - 1)), Math.round((ndc.y * 0.5 + 0.5) * (harness.size - 1))];
  };
  const [topX, topY] = project(centre.clone().add(new THREE.Vector3(0, 0.3, 0.2)));
  const [lowX, lowY] = project(centre.clone().add(new THREE.Vector3(0, -0.3, 0.2)));
  harness.check('probe_lights_the_top_more_than_the_bottom', at(topX, topY) > at(lowX, lowY) + 20,
    {top: at(topX, topY), bottom: at(lowX, lowY)});
  return {scene, camera, baseline: {scene: build(false), camera}};
}
