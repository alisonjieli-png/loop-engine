// Demo of the vignette pass, rendered by the family verifier and usable as an example. A lit scene is rendered into a
// render target, then the vignette material draws it to the screen on a full-screen triangle. The baseline draws the
// same target with strength 0. Before that, the pass runs on a white input into a float target and must match the
// CPU mirror at every pixel.

export function demo(THREE, vignette, harness) {
  // 1. GPU against CPU: a white input, black vignette colour, 32 x 32 float output equals 1 - vignetteAmount.
  const white = new THREE.DataTexture(new Uint8Array([255, 255, 255, 255]), 1, 1);
  white.needsUpdate = true;
  const probe = vignette.createVignetteMaterial(THREE, {inner: 0.2, outer: 1.2});
  probe.uniforms.tDiffuse.value = white;
  const quad = harness.fullscreen(probe);
  const size = 32;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  let worst = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const expected = 1 - vignette.vignetteAmount((x + 0.5) / size, (y + 0.5) / size, {inner: 0.2, outer: 1.2});
      worst = Math.max(worst, Math.abs(values[(y * size + x) * 4] - expected));
    }
  }
  harness.check('gpu_vignette_matches_cpu_mirror', worst < 2e-3, {pixels: size * size, worst_difference: worst});

  // 2. The showcase: a bright scene through the pass.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xb9c7d8);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 2.2));
  const sun = new THREE.DirectionalLight(0xfff1dd, 2.0);
  sun.position.set(2, 4, 3);
  scene.add(sun);
  const colours = [0xe4572e, 0x29335c, 0xf3a712, 0x669bbc, 0xa8c686];
  for (let index = 0; index < 25; index += 1) {
    const mesh = new THREE.Mesh(new THREE.IcosahedronGeometry(0.32, 2),
      new THREE.MeshStandardMaterial({color: colours[index % colours.length], roughness: 0.5}));
    mesh.position.set((index % 5) - 2, Math.floor(index / 5) - 2, -Math.abs((index % 5) - 2) * 0.3);
    scene.add(mesh);
  }
  const camera = new THREE.PerspectiveCamera(50, 1, 0.1, 50);
  camera.position.set(0, 0, 5.4);
  const input = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, input);

  const pass = vignette.createVignetteMaterial(THREE, {strength: 0.85, inner: 0.35, outer: 1.35});
  pass.uniforms.tDiffuse.value = input.texture;
  const shown = harness.fullscreen(pass);
  const plain = vignette.createVignetteMaterial(THREE, {strength: 0});
  plain.uniforms.tDiffuse.value = input.texture;
  const untouched = harness.fullscreen(plain);
  harness.check('shader_definition_has_tdiffuse', 'tDiffuse' in vignette.createVignetteShader().uniforms, {});
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
