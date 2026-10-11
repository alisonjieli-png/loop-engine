// Demo of the hologram material, rendered by the family verifier and usable as an example: a projector disc under a
// cyan hologram of a torus knot and a magenta crystal, caught at a moment when two glitch bands are displaced. The
// baseline replaces the hologram with plain additive colour. First the GLSL scanline, glitch and flicker functions are
// evaluated on the GPU and compared with the CPU mirrors.

function projector(THREE, scene) {
  const disc = new THREE.Mesh(new THREE.CylinderGeometry(1.05, 1.2, 0.18, 64),
    new THREE.MeshStandardMaterial({color: 0x2a3140, metalness: 0.6, roughness: 0.35}));
  disc.position.y = -1.2;
  const lens = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 0.02, 64), new THREE.MeshBasicMaterial({color: 0x3fd7ff}));
  lens.position.y = -1.1;
  const key = new THREE.DirectionalLight(0xffffff, 2);
  key.position.set(2, 3, 4);
  scene.add(disc, lens, key, new THREE.AmbientLight(0x8090b0, 0.6));
}

function figures(THREE, cyan, magenta) {
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.55, 0.17, 220, 24), cyan);
  knot.position.set(-0.2, 0.05, 0);
  const crystal = new THREE.Mesh(new THREE.OctahedronGeometry(0.38, 0), magenta);
  crystal.position.set(0.72, 0.62, 0.1);
  crystal.rotation.set(0.3, 0.5, 0.2);
  return [knot, crystal];
}

export function demo(THREE, hologram, harness) {
  // 1. Scanline (r), glitch (g) and flicker (b) on the GPU equal the CPU mirrors on a 64 x 16 grid.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${hologram.HOLOGRAM_GLSL}
void main() {
  float height = vUv.y * 3.0 - 1.5;
  float scan = scanlineIntensity(height, 1.37, 12.0, 0.5, 4.0);
  float glitch = glitchOffset(height, 1.37 + vUv.x * 5.0, 6.0, 4.0, 0.3, 0.1, 3u);
  gl_FragColor = vec4(scan, glitch, hologramFlicker(vUv.x * 5.0, 12.0, 0.25, 3u), 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const [width, height] = [64, 16];
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, height));
  const worst = [0, 0, 0];
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const u = (x + 0.5) / width;
      const level = ((y + 0.5) / height) * 3 - 1.5;
      const expected = [hologram.scanlineIntensity(level, 1.37, 12, 0.5, 4),
        hologram.glitchOffset(level, 1.37 + u * 5, 6, 4, 0.3, 0.1, 3), hologram.hologramFlicker(u * 5, 12, 0.25, 3)];
      const offset = (y * width + x) * 4;
      for (let channel = 0; channel < 3; channel += 1) {
        worst[channel] = Math.max(worst[channel], Math.abs(values[offset + channel] - expected[channel]));
      }
    }
  }
  harness.check('gpu_scanlines_match_cpu_mirror', worst[0] < 1e-3, {samples: width * height, worst_difference: worst[0]});
  harness.check('gpu_glitch_matches_cpu_mirror', worst[1] < 1e-6, {worst_difference: worst[1]});
  harness.check('gpu_flicker_matches_cpu_mirror', worst[2] < 1e-6, {worst_difference: worst[2]});

  // 2. The showcase at t = 2.3 s, and the same figures in plain additive colour.
  const cyan = hologram.createHologramMaterial(THREE, {scanDensity: 18, glitchChance: 0.3, glitchStrength: 0.12, seed: 3});
  const magenta = hologram.createHologramMaterial(THREE, {color: [1, 0.3, 0.85], scanDensity: 18, seed: 8});
  cyan.uniforms.uTime.value = 2.3;
  magenta.uniforms.uTime.value = 2.3;
  const background = new THREE.Color(0x05070d);
  const scene = new THREE.Scene();
  scene.background = background;
  projector(THREE, scene);
  scene.add(...figures(THREE, cyan, magenta));
  const flat = (color) => new THREE.MeshBasicMaterial({color, transparent: true, opacity: 0.45,
    blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide});
  const baseline = new THREE.Scene();
  baseline.background = background;
  projector(THREE, baseline);
  baseline.add(...figures(THREE, flat(cyan.uniforms.uColor.value), flat(magenta.uniforms.uColor.value)));
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(0.2, 0.55, 5);
  camera.lookAt(0.12, -0.12, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
