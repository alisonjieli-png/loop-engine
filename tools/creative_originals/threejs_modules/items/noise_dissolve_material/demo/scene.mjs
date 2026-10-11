// Demo of the noise dissolve material, rendered by the family verifier and usable as an example: a torus knot burning
// away with an orange front and a sphere with a cold blue front. The baseline is the same scene at threshold 0 (whole).
// First the GLSL value noise, fractal noise and edge are evaluated on the GPU and compared with the CPU mirrors.

function build(THREE, dissolve, scale) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x10131c);
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.8, 0.28, 220, 32), dissolve.createNoiseDissolveMaterial(THREE, {
    threshold: 0.42 * scale, color: [0.62, 0.6, 0.58], noiseScale: 2.2, seed: 7, edgeIntensity: 1.7, edgeWidth: 0.07,
  }));
  knot.position.set(-0.55, 0.3, 0);
  knot.rotation.set(0.3, 0.4, 0);
  const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.62, 96, 48), dissolve.createNoiseDissolveMaterial(THREE, {
    threshold: 0.47 * scale, color: [0.32, 0.36, 0.5], edgeColor: [0.25, 0.7, 1], edgeIntensity: 2.2, edgeWidth: 0.05,
    noiseScale: 3.2, octaves: 5, seed: 19,
  }));
  sphere.position.set(1.05, -0.65, 0.3);
  scene.add(knot, sphere);
  return scene;
}

export function demo(THREE, dissolve, harness) {
  // 1. Value noise (r), fractal noise (g) and the edge (b) on the GPU equal the CPU mirrors on a 32 x 32 grid.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${dissolve.NOISE_DISSOLVE_GLSL}
void main() {
  vec3 p = vec3(vUv * 6.0 - 3.0, 1.7);
  float fractal = fbm3(p * 0.9, 4.0, 11u);
  gl_FragColor = vec4(valueNoise3(p, 7u), fractal, dissolveEdge(fractal, 0.45, 0.06), 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const size = 32;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  const worst = [0, 0, 0];
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const px = ((x + 0.5) / size) * 6 - 3;
      const py = ((y + 0.5) / size) * 6 - 3;
      const fractal = dissolve.fbm3(px * 0.9, py * 0.9, 1.7 * 0.9, 4, 11);
      const expected = [dissolve.valueNoise3(px, py, 1.7, 7), fractal, dissolve.dissolveEdge(fractal, 0.45, 0.06)];
      const offset = (y * size + x) * 4;
      for (let channel = 0; channel < 3; channel += 1) {
        worst[channel] = Math.max(worst[channel], Math.abs(values[offset + channel] - expected[channel]));
      }
    }
  }
  harness.check('gpu_value_noise_matches_cpu_mirror', worst[0] < 1e-5, {samples: size * size, worst_difference: worst[0]});
  harness.check('gpu_fractal_noise_matches_cpu_mirror', worst[1] < 1e-5, {worst_difference: worst[1]});
  harness.check('gpu_edge_matches_cpu_mirror', worst[2] < 1e-3, {worst_difference: worst[2]});

  // 2. The showcase and the same scene before the dissolve starts.
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0.15, 0.2, 6.3);
  camera.lookAt(0.15, -0.1, 0);
  return {scene: build(THREE, dissolve, 1), camera, baseline: {scene: build(THREE, dissolve, 0), camera}};
}
