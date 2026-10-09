// Demo of the separable Gaussian blur, rendered by the family verifier and usable as an example. GPU checks first:
// an impulse blurred across one row (in the middle and next to the edge) must equal the CPU line blur, and an
// impulse blurred across then up must equal the outer product of the kernel. Then a detailed scene is blurred in two
// passes and shown through a frosted-glass panel; the baseline shows the scene without the panel.

function impulseTexture(THREE, width, height, x, y) {
  const data = new Float32Array(width * height * 4);
  data[(y * width + x) * 4] = 1;
  data[(y * width + x) * 4 + 3] = 1;
  const texture = new THREE.DataTexture(data, width, height, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.LinearFilter;
  texture.magFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return texture;
}

function linearTarget(THREE, width, height, type) {
  return new THREE.WebGLRenderTarget(width, height, {
    type, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, depthBuffer: false,
  });
}

export function demo(THREE, blur, harness) {
  const sigma = 2.5;
  const radius = 8;
  const weights = blur.gaussianWeights(sigma, radius);

  // 1. One row: impulses in the middle and beside the left edge.
  const width = 33;
  let worstLine = 0;
  for (const position of [16, 1]) {
    const material = blur.createGaussianBlurMaterial(THREE, {sigma, radius, direction: [1, 0], resolution: [width, 1]});
    material.uniforms.tDiffuse.value = impulseTexture(THREE, width, 1, position, 0);
    const quad = harness.fullscreen(material);
    const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
    const impulse = Array.from({length: width}, (_, x) => (x === position ? 1 : 0));
    const expected = blur.blurLine(impulse, weights);
    for (let x = 0; x < width; x += 1) worstLine = Math.max(worstLine, Math.abs(values[x * 4] - expected[x]));
  }
  harness.check('gpu_row_blur_matches_cpu_line_blur', worstLine < 1e-6, {worst: worstLine, sigma, radius});

  // 2. Two passes: across into a linearly filtered float target, then up; the result is the kernel's outer product.
  const size = 17;
  const across = blur.createGaussianBlurMaterial(THREE, {sigma, radius, direction: [1, 0], resolution: [size, size]});
  across.uniforms.tDiffuse.value = impulseTexture(THREE, size, size, 8, 8);
  const middle = linearTarget(THREE, size, size, THREE.FloatType);
  const acrossQuad = harness.fullscreen(across);
  harness.renderer.setRenderTarget(middle);
  harness.renderer.render(acrossQuad.scene, acrossQuad.camera);
  harness.renderer.setRenderTarget(null);
  const up = blur.createGaussianBlurMaterial(THREE, {sigma, radius, direction: [0, 1], resolution: [size, size]});
  up.uniforms.tDiffuse.value = middle.texture;
  const upQuad = harness.fullscreen(up);
  const values = harness.renderToTarget(upQuad.scene, upQuad.camera, harness.floatTarget(size, size));
  let worstGrid = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = Math.abs(x - 8);
      const dy = Math.abs(y - 8);
      const expected = (dx <= radius ? weights[dx] : 0) * (dy <= radius ? weights[dy] : 0);
      worstGrid = Math.max(worstGrid, Math.abs(values[(y * size + x) * 4] - expected));
    }
  }
  harness.check('gpu_two_pass_blur_is_separable_kernel', worstGrid < 1e-6, {worst: worstGrid});

  // 3. The showcase: a checker floor and props, blurred in two passes, shown through a frosted-glass panel.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x26384f);
  scene.add(new THREE.HemisphereLight(0xe6f0ff, 0x302820, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(3, 5, 2);
  scene.add(sun);
  const tiles = new Uint8Array(8 * 8 * 4);
  for (let index = 0; index < 64; index += 1) {
    const light = ((index % 8) + Math.floor(index / 8)) % 2 === 0;
    tiles.set(light ? [235, 228, 210, 255] : [60, 70, 92, 255], index * 4);
  }
  const checker = new THREE.DataTexture(tiles, 8, 8);
  checker.magFilter = THREE.NearestFilter;
  checker.wrapS = THREE.RepeatWrapping;
  checker.wrapT = THREE.RepeatWrapping;
  checker.repeat.set(3, 3);
  checker.colorSpace = THREE.SRGBColorSpace;
  checker.needsUpdate = true;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(8, 8), new THREE.MeshStandardMaterial({map: checker}));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1;
  scene.add(floor);
  [0xff6b4a, 0xffc94a, 0x4ad1ff, 0xb46bff].forEach((colour, index) => {
    const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.32, 0.1, 96, 12),
      new THREE.MeshStandardMaterial({color: colour, roughness: 0.35}));
    knot.position.set(-1.5 + index, -0.35 + (index % 2) * 0.5, -0.4 * index);
    scene.add(knot);
  });
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 1.2, 4.2);
  camera.lookAt(0, -0.3, -0.5);

  const frame = harness.size;
  const sharp = linearTarget(THREE, frame, frame, THREE.HalfFloatType);
  const halfway = linearTarget(THREE, frame, frame, THREE.HalfFloatType);
  const blurred = linearTarget(THREE, frame, frame, THREE.HalfFloatType);
  const renderer = harness.renderer;
  const draw = (target, drawnScene, drawnCamera) => {
    renderer.setRenderTarget(target);
    renderer.render(drawnScene, drawnCamera);
    renderer.setRenderTarget(null);
  };
  draw(sharp, scene, camera);
  const settings = {sigma: 6, radius: 18, resolution: [frame, frame]};
  const first = blur.createGaussianBlurMaterial(THREE, {...settings, direction: [1, 0]});
  first.uniforms.tDiffuse.value = sharp.texture;
  const firstQuad = harness.fullscreen(first);
  draw(halfway, firstQuad.scene, firstQuad.camera);
  const second = blur.createGaussianBlurMaterial(THREE, {...settings, direction: [0, 1]});
  second.uniforms.tDiffuse.value = halfway.texture;
  const secondQuad = harness.fullscreen(second);
  draw(blurred, secondQuad.scene, secondQuad.camera);

  const panel = (enabled) => new THREE.ShaderMaterial({
    uniforms: {tSharp: {value: sharp.texture}, tBlur: {value: blurred.texture}, uPanel: {value: enabled}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform sampler2D tSharp;
uniform sampler2D tBlur;
uniform float uPanel;
varying vec2 vUv;
float roundedBox(vec2 point, vec2 halfSize, float corner) {
  vec2 q = abs(point) - halfSize + corner;
  return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - corner;
}
void main() {
  float distanceToPanel = roundedBox(vUv - vec2(0.5, 0.4), vec2(0.36, 0.2), 0.06);
  float inside = (1.0 - smoothstep(-0.003, 0.003, distanceToPanel)) * uPanel;
  vec3 glass = mix(texture2D(tBlur, vUv).rgb, vec3(1.0), 0.16);
  float rim = (1.0 - smoothstep(0.0, 0.005, abs(distanceToPanel))) * uPanel * 0.5;
  gl_FragColor = vec4(mix(texture2D(tSharp, vUv).rgb, glass, inside) + rim, 1.0);
  #include <colorspace_fragment>
}`,
  });
  const shown = harness.fullscreen(panel(1));
  const untouched = harness.fullscreen(panel(0));
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
