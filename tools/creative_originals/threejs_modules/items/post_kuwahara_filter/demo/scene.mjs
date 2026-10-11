// Demo of the Kuwahara filter, rendered by the family verifier and usable as an example. On a 24 x 24 float test
// image (a diagonal edge, two curved gradients and three discs) the pass must return, at every pixel, the mean of a quadrant
// whose variance is the least (within float rounding, so near-ties may go either way) and must equal kuwaharaPixel
// wherever there is no near-tie. Then a speckled garden scene is painted with radius 5; the baseline is a plain copy.

function testImage(size) {
  const data = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const above = x + 0.6 * y > 18;
      let colour = above ? [0.85, 0.5 + 0.0007 * y * y, 0.2] : [0.15 + 0.0011 * x * x, 0.3, 0.6];
      for (const [cx, cy, radius, tint] of [[6, 17, 3.2, [0.9, 0.9, 0.85]], [17, 5, 2.6, [0.1, 0.7, 0.3]],
        [12, 12, 2.1, [0.6, 0.1, 0.5]]]) {
        if ((x - cx) ** 2 + (y - cy) ** 2 < radius * radius) colour = tint;
      }
      data.set([...colour, 1], (y * size + x) * 4);
    }
  }
  return data;
}

export function demo(THREE, kuwahara, harness) {
  const size = 24;
  const radius = 3;
  const data = testImage(size);
  const input = new THREE.DataTexture(data, size, size, THREE.RGBAFormat, THREE.FloatType);
  input.minFilter = THREE.NearestFilter;
  input.magFilter = THREE.NearestFilter;
  input.needsUpdate = true;
  const probe = kuwahara.createKuwaharaMaterial(THREE, {radius, resolution: [size, size]});
  probe.uniforms.tDiffuse.value = input;
  const quad = harness.fullscreen(probe);
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  let wrong = 0;
  let nearTies = 0;
  let worstExact = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const index = (y * size + x) * 4;
      const gpu = [values[index], values[index + 1], values[index + 2]];
      const quadrants = kuwahara.kuwaharaQuadrants(data, size, size, x, y, radius);
      const least = Math.min(...quadrants.map((quadrant) => quadrant.variance));
      const candidates = quadrants.filter((quadrant) => quadrant.variance <= least + 2e-7);
      const matches = (mean) => mean.every((value, channel) => Math.abs(value - gpu[channel]) < 1e-5);
      if (!candidates.some((quadrant) => matches(quadrant.mean))) wrong += 1;
      const distinct = new Set(candidates.map((quadrant) => quadrant.mean.map((value) => value.toFixed(5)).join(',')));
      if (distinct.size > 1) {
        nearTies += 1;
      } else {
        const expected = kuwahara.kuwaharaPixel(data, size, size, x, y, radius);
        worstExact = Math.max(worstExact, ...gpu.map((value, channel) => Math.abs(value - expected[channel])));
      }
    }
  }
  harness.check('gpu_picks_a_least_varied_quadrant', wrong === 0, {pixels: size * size, wrong, near_ties: nearTies});
  harness.check('gpu_matches_cpu_mirror_without_ties', worstExact < 1e-5, {worst: worstExact});

  // The showcase: a bright garden of shapes, painted with radius 4.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x9ec9e6);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x5a7040, 1.5));
  const sun = new THREE.DirectionalLight(0xfff0d0, 2.4);
  sun.position.set(2, 5, 3);
  scene.add(sun);
  // Speckled grass and leaves give the filter fine detail to turn into patches.
  const speckles = (base, spread) => {
    const pixels = new Uint8Array(64 * 64 * 4);
    for (let index = 0; index < 64 * 64; index += 1) {
      const wobble = (Math.imul(index, 2654435761) >>> 24) / 255 - 0.5;
      pixels.set(base.map((value) => Math.max(0, Math.min(255, Math.round(value + wobble * spread)))).concat(255), index * 4);
    }
    const texture = new THREE.DataTexture(pixels, 64, 64);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  };
  const grassMap = speckles([110, 156, 72], 90);
  grassMap.repeat.set(4, 4);
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.MeshStandardMaterial({map: grassMap}));
  grass.rotation.x = -Math.PI / 2;
  grass.position.y = -1;
  scene.add(grass);
  const petals = [0xe94f64, 0xf2b134, 0xf5e6c8, 0xa45ee5, 0xff8c42];
  for (let index = 0; index < 14; index += 1) {
    const angle = index * 2.4;
    const distance = 0.4 + 0.18 * index;
    const flower = new THREE.Mesh(new THREE.IcosahedronGeometry(0.22 + 0.04 * (index % 3), 1),
      new THREE.MeshStandardMaterial({color: petals[index % petals.length], flatShading: true}));
    flower.position.set(Math.cos(angle) * distance, -0.7 + 0.05 * (index % 4), Math.sin(angle) * distance - 0.8);
    scene.add(flower);
  }
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.18, 1.6, 12), new THREE.MeshStandardMaterial({color: 0x7a5233}));
  trunk.position.set(1.6, -0.2, -1.6);
  const crown = new THREE.Mesh(new THREE.SphereGeometry(0.8, 24, 16), new THREE.MeshStandardMaterial({map: speckles([63, 127, 58], 110)}));
  crown.position.set(1.6, 0.9, -1.6);
  scene.add(trunk, crown);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 0.8, 3.8);
  camera.lookAt(0.2, -0.3, -0.8);
  const frame = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, frame);
  const paint = kuwahara.createKuwaharaMaterial(THREE, {radius: 5, resolution: [harness.size, harness.size]});
  paint.uniforms.tDiffuse.value = frame.texture;
  const shown = harness.fullscreen(paint);
  const copy = new THREE.ShaderMaterial({
    uniforms: {tDiffuse: {value: frame.texture}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D tDiffuse;\nvarying vec2 vUv;\nvoid main() {\n  gl_FragColor = texture2D(tDiffuse, vUv);\n'
      + '  #include <colorspace_fragment>\n}',
  });
  const untouched = harness.fullscreen(copy);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
