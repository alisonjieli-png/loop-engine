// Demo of the film grain pass, rendered by the family verifier and usable as an example. First the hash chunk runs on
// the GPU and its top 24 bits must equal grainHash exactly at every pixel; then the whole pass runs on a coloured
// test image and must equal applyGrainCpu at every pixel. Then a dim still life is shown with mono grain; the
// baseline is the same frame at intensity 0.

function testImage(THREE, size) {
  const data = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      data.set([x / (size - 1), 0.5 * (y / (size - 1)), 0.3 + 0.4 * ((x + y) % 2), 1], (y * size + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.needsUpdate = true;
  return {texture, data};
}

export function demo(THREE, grain, harness) {
  // 1. The integer hash on the GPU, bit for bit (the top 24 bits fit a float exactly).
  const hashSize = 64;
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'void main() { gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `${grain.FILM_GRAIN_HASH_GLSL}
void main() {
  uvec2 cell = uvec2(floor(gl_FragCoord.xy));
  gl_FragColor = vec4(float(grainHash(cell, 7u, 3u, 0u) >> 8u), float(grainHash(cell, 7u, 3u, 1u) >> 8u),
    float(grainHash(cell, 7u, 3u, 2u) >> 8u), 1.0);
}`,
  });
  const probeQuad = harness.fullscreen(probe);
  const hashes = harness.renderToTarget(probeQuad.scene, probeQuad.camera, harness.floatTarget(hashSize, hashSize));
  let hashMismatches = 0;
  for (let y = 0; y < hashSize; y += 1) {
    for (let x = 0; x < hashSize; x += 1) {
      for (let channel = 0; channel < 3; channel += 1) {
        if (hashes[(y * hashSize + x) * 4 + channel] !== grain.grainHash(x, y, 7, 3, channel) >>> 8) hashMismatches += 1;
      }
    }
  }
  harness.check('gpu_hash_equals_cpu_hash_bit_for_bit', hashMismatches === 0,
    {values: hashSize * hashSize * 3, mismatches: hashMismatches});

  // 2. The whole pass on a coloured image: coloured grain, 2-pixel cells, frame 5, seed 2.
  const size = 48;
  const {texture, data} = testImage(THREE, size);
  const settings = {intensity: 0.3, response: 0.6, colored: true, frame: 5, seed: 2, grainSize: 2};
  const pass = grain.createFilmGrainMaterial(THREE, settings);
  pass.uniforms.tDiffuse.value = texture;
  const passQuad = harness.fullscreen(pass);
  const values = harness.renderToTarget(passQuad.scene, passQuad.camera, harness.floatTarget(size, size));
  let worst = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const expected = grain.applyGrainCpu([data[index], data[index + 1], data[index + 2]], x, y, settings);
      for (let channel = 0; channel < 3; channel += 1) {
        worst = Math.max(worst, Math.abs(values[index + channel] - expected[channel]));
      }
    }
  }
  harness.check('gpu_pass_matches_cpu_mirror', worst < 1e-5, {pixels: size * size, worst});

  // 3. The showcase: a dim still life under one warm lamp, with mono grain.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x4a4038);
  scene.add(new THREE.HemisphereLight(0x9fb0c0, 0x302418, 1.3));
  const lamp = new THREE.SpotLight(0xffd2a0, 90, 12, 0.6, 0.5, 2);
  lamp.position.set(-1.5, 3, 2.5);
  scene.add(lamp);
  const table = new THREE.Mesh(new THREE.BoxGeometry(5, 0.2, 3), new THREE.MeshStandardMaterial({color: 0x6b4a33}));
  table.position.y = -1.1;
  scene.add(table);
  const vase = new THREE.Mesh(new THREE.LatheGeometry([
    new THREE.Vector2(0.0, -1), new THREE.Vector2(0.35, -0.98), new THREE.Vector2(0.45, -0.6),
    new THREE.Vector2(0.25, 0.1), new THREE.Vector2(0.18, 0.4), new THREE.Vector2(0.26, 0.55),
  ], 48), new THREE.MeshStandardMaterial({color: 0x8fa9b8, roughness: 0.35}));
  vase.position.set(-0.4, 0, 0);
  scene.add(vase);
  [[0.75, -0.75, 0.3, 0xd04a2a], [1.25, -0.8, -0.2, 0xe6b84a], [0.55, -0.82, 0.8, 0x7aa04a]].forEach(([x, y, z, colour]) => {
    const fruit = new THREE.Mesh(new THREE.SphereGeometry(0.26, 32, 16), new THREE.MeshStandardMaterial({color: colour}));
    fruit.position.set(x, y, z);
    scene.add(fruit);
  });
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
  camera.position.set(0.3, 0.4, 4.2);
  camera.lookAt(0.2, -0.45, 0);
  const frame = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, frame);
  const shownMaterial = grain.createFilmGrainMaterial(THREE, {intensity: 0.1, response: 0.6, frame: 3});
  shownMaterial.uniforms.tDiffuse.value = frame.texture;
  const shown = harness.fullscreen(shownMaterial);
  const plainMaterial = grain.createFilmGrainMaterial(THREE, {intensity: 0});
  plainMaterial.uniforms.tDiffuse.value = frame.texture;
  const untouched = harness.fullscreen(plainMaterial);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
