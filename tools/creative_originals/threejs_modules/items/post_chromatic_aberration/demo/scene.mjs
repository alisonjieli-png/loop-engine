// Demo of the chromatic aberration pass, rendered by the family verifier and usable as an example. Two GPU checks
// first: an input texture that stores its own coordinates reveals where each channel sampled, which must equal the
// CPU mirror (three-tap and dispersion paths). Then a high-contrast scene is rendered into a target and drawn
// through the pass; the baseline draws it with strength 0.

function coordinateTexture(THREE, size, layout) {
  const data = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const u = (x + 0.5) / size;
      const v = (y + 0.5) / size;
      data.set(layout(u, v), (y * size + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

export function demo(THREE, aberration, harness) {
  const inputSize = 64;
  const low = 0.5 / inputSize;
  const clampCoordinate = (value) => Math.min(Math.max(value, low), 1 - low);
  const outputSize = 32;
  const settings = {strength: 0.15, power: 1.3, center: [0.45, 0.55], aspect: 1.25};

  // 1. Three-tap path: (u, v, u) and (v, u, v) inputs give every channel's sample coordinate.
  const material = aberration.createChromaticAberrationMaterial(THREE, settings);
  const quad = harness.fullscreen(material);
  const target = harness.floatTarget(outputSize, outputSize);
  material.uniforms.tDiffuse.value = coordinateTexture(THREE, inputSize, (u, v) => [u, v, u, 1]);
  const first = harness.renderToTarget(quad.scene, quad.camera, target);
  material.uniforms.tDiffuse.value = coordinateTexture(THREE, inputSize, (u, v) => [v, u, v, 1]);
  const second = harness.renderToTarget(quad.scene, quad.camera, target);
  let worst = 0;
  for (let y = 0; y < outputSize; y += 1) {
    for (let x = 0; x < outputSize; x += 1) {
      const offsets = aberration.aberrationOffset((x + 0.5) / outputSize, (y + 0.5) / outputSize, settings);
      const index = (y * outputSize + x) * 4;
      const pairs = [
        [first[index], offsets.red[0]], [second[index], offsets.red[1]],
        [second[index + 1], offsets.green[0]], [first[index + 1], offsets.green[1]],
        [first[index + 2], offsets.blue[0]], [second[index + 2], offsets.blue[1]],
      ];
      for (const [gpu, cpu] of pairs) worst = Math.max(worst, Math.abs(gpu - clampCoordinate(cpu)));
    }
  }
  harness.check('gpu_channel_coordinates_match_cpu_mirror', worst < 1e-5, {pixels: outputSize * outputSize, worst});

  // 2. Dispersion path: every channel is the weighted mean of the taps' u coordinates.
  const dispersed = aberration.createChromaticAberrationMaterial(THREE, {...settings, samples: 5});
  dispersed.uniforms.tDiffuse.value = coordinateTexture(THREE, inputSize, (u) => [u, u, u, 1]);
  const dispersedQuad = harness.fullscreen(dispersed);
  const third = harness.renderToTarget(dispersedQuad.scene, dispersedQuad.camera, target);
  let worstDispersion = 0;
  for (let y = 0; y < outputSize; y += 1) {
    for (let x = 0; x < outputSize; x += 1) {
      const taps = aberration.dispersionTaps((x + 0.5) / outputSize, (y + 0.5) / outputSize, {...settings, samples: 5});
      for (let channel = 0; channel < 3; channel += 1) {
        const expected = taps.reduce((sum, tap) => sum + tap.weights[channel] * clampCoordinate(tap.uv[0]), 0);
        worstDispersion = Math.max(worstDispersion, Math.abs(third[(y * outputSize + x) * 4 + channel] - expected));
      }
    }
  }
  harness.check('gpu_dispersion_matches_cpu_mirror', worstDispersion < 1e-5, {worst: worstDispersion});

  // 3. The showcase: bright bars and spheres on a dark ground, through a strong dispersed aberration.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0e16);
  scene.add(new THREE.HemisphereLight(0xd8e4ff, 0x1a1410, 1.4));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(2, 3, 4);
  scene.add(sun);
  const glow = new THREE.MeshStandardMaterial({color: 0xffffff, emissive: 0xf4f1e8, emissiveIntensity: 0.9});
  for (let index = 0; index < 7; index += 1) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.09, 3.4, 0.09), glow);
    bar.position.set(-2.1 + index * 0.7, 0, -0.6);
    bar.rotation.z = 0.35;
    scene.add(bar);
  }
  const colours = [0xff5a3c, 0x3ca7ff, 0xffd23c, 0x7cff6b];
  colours.forEach((colour, index) => {
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.42, 40, 20),
      new THREE.MeshStandardMaterial({color: colour, roughness: 0.3}));
    ball.position.set(index % 2 === 0 ? -1.15 : 1.15, index < 2 ? 0.95 : -0.95, 0.4);
    scene.add(ball);
  });
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 50);
  camera.position.set(0, 0, 4.6);
  const input = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, input);

  const pass = aberration.createChromaticAberrationMaterial(THREE, {strength: 0.045, power: 1.2, samples: 6});
  pass.uniforms.tDiffuse.value = input.texture;
  const shown = harness.fullscreen(pass);
  const plain = aberration.createChromaticAberrationMaterial(THREE, {strength: 0});
  plain.uniforms.tDiffuse.value = input.texture;
  const untouched = harness.fullscreen(plain);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
