// Demo of the ordered dither pass, rendered by the family verifier and usable as an example. On a 32 x 32 float
// gradient the pass must give exactly ditherPixel at every pixel, in levels mode (linear) and in palette mode (sRGB,
// 2-pixel blocks, 8 x 8 matrix). Then a lit scene is dithered to an 8-colour palette in 2-pixel blocks; the baseline
// is a plain copy of the same frame.

const DUSK = [
  [0.1, 0.09, 0.16], [0.28, 0.22, 0.36], [0.55, 0.31, 0.4], [0.87, 0.47, 0.34],
  [0.98, 0.78, 0.45], [0.36, 0.56, 0.62], [0.67, 0.83, 0.8], [0.98, 0.96, 0.9],
];

function gradient(THREE, size) {
  const data = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      data.set([x / (size - 1), y / (size - 1), ((x * 5 + y * 3) % size) / (size - 1), 1], (y * size + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.needsUpdate = true;
  return {texture, data};
}

function mismatches(dither, values, data, size, options) {
  let count = 0;
  let worst = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const [sx, sy] = dither.ditherSamplePixel(x, y, options.pixelSize || 1);
      const source = (sy * size + sx) * 4;
      const expected = dither.ditherPixel([data[source], data[source + 1], data[source + 2]], x, y, options);
      const difference = Math.max(...expected.map((value, channel) => Math.abs(values[(y * size + x) * 4 + channel] - value)));
      worst = Math.max(worst, difference);
      if (difference > 1e-5) count += 1;
    }
  }
  return {count, worst};
}

export function demo(THREE, dither, harness) {
  const size = 32;
  const {texture, data} = gradient(THREE, size);
  const target = harness.floatTarget(size, size);
  const runs = {
    levels: {mode: 'levels', levels: 4, matrixSize: 4, domain: 'linear', resolution: [size, size]},
    palette: {mode: 'palette', palette: DUSK, spread: 0.35, matrixSize: 8, pixelSize: 2, domain: 'srgb',
      resolution: [size, size]},
  };
  for (const [name, options] of Object.entries(runs)) {
    const material = dither.createOrderedDitherMaterial(THREE, options);
    material.uniforms.tDiffuse.value = texture;
    const quad = harness.fullscreen(material);
    const result = mismatches(dither, harness.renderToTarget(quad.scene, quad.camera, target), data, size, options);
    harness.check(`gpu_${name}_dither_matches_cpu_mirror`, result.count === 0, result);
  }

  // The showcase: a sunset still life dithered to the dusk palette.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xe39a6a);
  scene.add(new THREE.HemisphereLight(0xffd8b0, 0x2a2440, 1.4));
  const sun = new THREE.DirectionalLight(0xffe0b0, 2.4);
  sun.position.set(-3, 2, 2);
  scene.add(sun);
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), new THREE.MeshStandardMaterial({color: 0x3a6f86, roughness: 0.4}));
  sea.rotation.x = -Math.PI / 2;
  sea.position.y = -1;
  scene.add(sea);
  const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.9, 1), new THREE.MeshStandardMaterial({color: 0x5b4a63}));
  rock.position.set(-0.8, -0.6, -0.5);
  scene.add(rock);
  const lighthouse = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.32, 1.9, 24),
    new THREE.MeshStandardMaterial({color: 0xf3ede1}));
  lighthouse.position.set(0.9, -0.05, -0.2);
  scene.add(lighthouse);
  const lamp = new THREE.Mesh(new THREE.SphereGeometry(0.2, 24, 12),
    new THREE.MeshStandardMaterial({color: 0xffe9a8, emissive: 0xffd36b, emissiveIntensity: 1.5}));
  lamp.position.set(0.9, 1.0, -0.2);
  scene.add(lamp);
  const moon = new THREE.Mesh(new THREE.SphereGeometry(0.35, 32, 16), new THREE.MeshBasicMaterial({color: 0xfff4dc}));
  moon.position.set(-1.6, 1.4, -3);
  scene.add(moon);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 0.3, 4.4);
  camera.lookAt(0, 0, 0);
  const frame = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, frame);

  const pass = dither.createOrderedDitherMaterial(THREE, {mode: 'palette', palette: DUSK, spread: 0.3, pixelSize: 2,
    matrixSize: 4, resolution: [harness.size, harness.size]});
  pass.uniforms.tDiffuse.value = frame.texture;
  const shown = harness.fullscreen(pass);
  const copy = new THREE.ShaderMaterial({
    uniforms: {tDiffuse: {value: frame.texture}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D tDiffuse;\nvarying vec2 vUv;\nvoid main() {\n  gl_FragColor = texture2D(tDiffuse, vUv);\n'
      + '  #include <colorspace_fragment>\n}',
  });
  const untouched = harness.fullscreen(copy);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
