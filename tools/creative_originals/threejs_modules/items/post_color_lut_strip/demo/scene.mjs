// Demo of the LUT strip grading pass, rendered by the family verifier and usable as an example. On a 32 x 32 float
// test image, an identity strip must return the input and a baked warm grade must equal gradeColorCpu at every
// pixel. Then a lit scene is graded with a teal-and-orange look; the baseline draws it at intensity 0.

function testTexture(THREE, size) {
  const data = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      data.set([x / (size - 1), y / (size - 1), ((x * 7 + y * 3) % size) / (size - 1), 1], (y * size + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.needsUpdate = true;
  return {texture, data};
}

function warmGrade(r, g, b) {
  return [Math.min(1, r * 1.08 + 0.04), Math.min(1, g * 1.0 + 0.01), b * 0.82];
}

function tealOrange(r, g, b) {
  const luma = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const t = luma * luma * (3 - 2 * luma);
  const tint = [0.86 + 0.26 * t, 0.98 + 0.0 * t, 1.12 - 0.36 * t];
  const curve = (value) => value + 0.35 * (value * value * (3 - 2 * value) - value);
  return [curve(r) * tint[0], curve(g) * tint[1], curve(b) * tint[2]].map((value) => Math.min(1, Math.max(0, value)));
}

export function demo(THREE, lut, harness) {
  const size = 32;
  const {texture, data} = testTexture(THREE, size);
  const target = harness.floatTarget(size, size);

  // 1. Identity strip, linear domain: the output equals the input.
  const identity = lut.createColorLutMaterial(THREE, {size: 16, domain: 'linear'});
  identity.uniforms.tDiffuse.value = texture;
  identity.uniforms.tLut.value = lut.createLutStripTexture(THREE, lut.identityLutStrip(16), 16);
  const identityQuad = harness.fullscreen(identity);
  const same = harness.renderToTarget(identityQuad.scene, identityQuad.camera, target);
  let worstIdentity = 0;
  for (let index = 0; index < size * size * 4; index += 1) {
    if (index % 4 !== 3) worstIdentity = Math.max(worstIdentity, Math.abs(same[index] - data[index]));
  }
  harness.check('identity_strip_returns_input', worstIdentity < 1e-4, {worst: worstIdentity});

  // 2. A baked warm grade in the sRGB domain equals the CPU mirror.
  const strip = lut.lutStripFromFunction(16, warmGrade);
  const warm = lut.createColorLutMaterial(THREE, {size: 16, domain: 'srgb'});
  warm.uniforms.tDiffuse.value = texture;
  warm.uniforms.tLut.value = lut.createLutStripTexture(THREE, strip, 16);
  const warmQuad = harness.fullscreen(warm);
  const graded = harness.renderToTarget(warmQuad.scene, warmQuad.camera, target);
  let worstGrade = 0;
  for (let pixel = 0; pixel < size * size; pixel += 1) {
    const expected = lut.gradeColorCpu(strip, 16, [data[pixel * 4], data[pixel * 4 + 1], data[pixel * 4 + 2]],
      {domain: 'srgb'});
    for (let channel = 0; channel < 3; channel += 1) {
      worstGrade = Math.max(worstGrade, Math.abs(graded[pixel * 4 + channel] - expected[channel]));
    }
  }
  harness.check('gpu_grade_matches_cpu_mirror', worstGrade < 1e-4, {worst: worstGrade});

  // 3. The showcase: a warm-lit scene graded teal and orange.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x6f8fa8);
  scene.add(new THREE.HemisphereLight(0xcfe3ff, 0x4a3b2a, 1.5));
  const sun = new THREE.DirectionalLight(0xffe2b8, 2.6);
  sun.position.set(3, 4, 2);
  scene.add(sun);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshStandardMaterial({color: 0x9c8c74}));
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -1;
  scene.add(ground);
  const colours = [0xd9b48f, 0x8fb3d9, 0xe0e0e0, 0xc46a4a, 0x6a9c78];
  colours.forEach((colour, index) => {
    const pillar = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.32, 1.4 + index * 0.25, 32),
      new THREE.MeshStandardMaterial({color: colour, roughness: 0.45}));
    pillar.position.set(-1.8 + index * 0.9, -0.3 + index * 0.125, -index * 0.35);
    scene.add(pillar);
  });
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.5, 48, 24), new THREE.MeshStandardMaterial({color: 0xf2d0a4}));
  ball.position.set(0.2, -0.5, 1.0);
  scene.add(ball);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 0.6, 4.8);
  camera.lookAt(0, -0.2, 0);
  const frame = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, frame);

  const look = lut.createLutStripTexture(THREE, lut.lutStripFromFunction(32, tealOrange), 32);
  const pass = lut.createColorLutMaterial(THREE, {size: 32});
  pass.uniforms.tDiffuse.value = frame.texture;
  pass.uniforms.tLut.value = look;
  const shown = harness.fullscreen(pass);
  const plain = lut.createColorLutMaterial(THREE, {size: 32, intensity: 0});
  plain.uniforms.tDiffuse.value = frame.texture;
  plain.uniforms.tLut.value = look;
  const untouched = harness.fullscreen(plain);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
