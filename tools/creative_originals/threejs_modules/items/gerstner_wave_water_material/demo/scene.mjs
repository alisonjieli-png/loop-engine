// Demo of the Gerstner water material, rendered by the family verifier and usable as an example: open water at
// t = 3.2 s under a low sun, with a buoy placed by the CPU buoyancy height and tilted to the CPU normal. The baseline
// is the same plane, flat and unshaded. First the GLSL offset, Jacobian and normal are evaluated on the GPU across a
// 20 x 20 unit patch and compared with the CPU mirrors.

function probe(THREE, water, harness, body, waves) {
  const packed = water.packGerstnerWaves(waves);
  const material = new THREE.ShaderMaterial({
    uniforms: {uWaves: {value: packed.waves}, uWaveSpeeds: {value: packed.speeds}, uWaveCount: {value: packed.count}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform vec4 uWaves[4];\nuniform vec4 uWaveSpeeds;\nuniform float uWaveCount;\nvarying vec2 vUv;
${water.GERSTNER_WATER_GLSL}
void main() {
  vec2 xz = vUv * 20.0 - 10.0;
  ${body}
}`,
  });
  const quad = harness.fullscreen(material);
  return harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(32, 32));
}

export function demo(THREE, water, harness) {
  const waves = water.GERSTNER_WATER_DEFAULTS.waves;
  const time = 1.7;
  const offsets = probe(THREE, water, harness,
    'gl_FragColor = vec4(gerstnerOffset(xz, 1.7, uWaves, uWaveSpeeds, uWaveCount), gerstnerJacobian(xz, 1.7, uWaves, uWaveSpeeds, uWaveCount));',
    waves);
  const normals = probe(THREE, water, harness,
    'gl_FragColor = vec4(gerstnerNormal(xz, 1.7, uWaves, uWaveSpeeds, uWaveCount), 1.0);', waves);
  const worst = {offset: 0, jacobian: 0, normal: 0};
  for (let y = 0; y < 32; y += 1) {
    for (let x = 0; x < 32; x += 1) {
      const px = ((x + 0.5) / 32) * 20 - 10;
      const pz = ((y + 0.5) / 32) * 20 - 10;
      const at = (y * 32 + x) * 4;
      const offset = water.gerstnerDisplacement(waves, px, pz, time);
      const normal = water.gerstnerNormal(waves, px, pz, time);
      for (let k = 0; k < 3; k += 1) {
        worst.offset = Math.max(worst.offset, Math.abs(offsets[at + k] - offset[k]));
        worst.normal = Math.max(worst.normal, Math.abs(normals[at + k] - normal[k]));
      }
      worst.jacobian = Math.max(worst.jacobian, Math.abs(offsets[at + 3] - water.gerstnerJacobian(waves, px, pz, time)));
    }
  }
  harness.check('gpu_offsets_match_cpu_mirror', worst.offset < 1e-3, {samples: 1024, worst_difference: worst.offset});
  harness.check('gpu_jacobian_matches_cpu_mirror', worst.jacobian < 1e-3, {worst_difference: worst.jacobian});
  harness.check('gpu_normals_match_cpu_mirror', worst.normal < 1e-3, {worst_difference: worst.normal});

  // The showcase: water, a buoy floating on the CPU height, and the sky colour as background.
  const now = 3.2;
  const material = water.createGerstnerWaterMaterial(THREE, {
    skyColor: [0.32, 0.44, 0.62], deepColor: [0.004, 0.035, 0.08], shallowColor: [0.02, 0.2, 0.25],
  });
  material.uniforms.uTime.value = now;
  const sky = new THREE.Color(0.32, 0.44, 0.62);
  const plane = new THREE.PlaneGeometry(36, 36, 260, 260);
  plane.rotateX(-Math.PI / 2);
  const scene = new THREE.Scene();
  scene.background = sky;
  scene.add(new THREE.Mesh(plane, material));
  const sun = new THREE.DirectionalLight(0xfff0d8, 2.4);
  sun.position.set(-4, 5, -7.5);
  scene.add(sun, new THREE.HemisphereLight(0xcfe3ff, 0x1a3040, 1.1));
  const buoy = new THREE.Group();
  const hull = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.3, 0.42, 32), new THREE.MeshStandardMaterial({color: 0xd8342c}));
  const stripe = new THREE.Mesh(new THREE.CylinderGeometry(0.225, 0.225, 0.1, 32), new THREE.MeshStandardMaterial({color: 0xf2f2f2}));
  stripe.position.y = 0.05;
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.08, 16, 8), new THREE.MeshBasicMaterial({color: 0xffe08a}));
  lamp.position.y = 0.3;
  buoy.add(hull, stripe, lamp);
  const floating = water.gerstnerSurfaceHeight(waves, 1.2, 0.6, now);
  const up = water.gerstnerNormal(waves, floating.rest[0], floating.rest[1], now);
  buoy.position.set(1.2, floating.height + 0.05, 0.6);
  buoy.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(up[0], up[1], up[2]));
  scene.add(buoy);
  harness.check('buoyancy_height_converges', floating.residual < 1e-4, {height: floating.height, residual: floating.residual});

  const baseline = new THREE.Scene();
  baseline.background = sky;
  baseline.add(new THREE.Mesh(plane, new THREE.MeshBasicMaterial({color: new THREE.Color(0.03, 0.2, 0.26), side: THREE.DoubleSide})));
  baseline.add(sun.clone(), new THREE.HemisphereLight(0xcfe3ff, 0x1a3040, 1.1));
  const flatBuoy = buoy.clone();
  flatBuoy.position.y = 0.05;
  flatBuoy.quaternion.identity();
  baseline.add(flatBuoy);
  const camera = new THREE.PerspectiveCamera(48, 1, 0.1, 100);
  camera.position.set(0, 1.9, 6.2);
  camera.lookAt(0, 0, -1.5);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
