// Demo of the Fresnel rim material, rendered by the family verifier and usable as an example: a torus knot with an
// opaque cyan rim, and a sphere with a magenta rim inside an additive glow shell. The baseline is the same scene with
// every rim intensity at 0. First the GLSL rim and pulse are evaluated on the GPU and compared with the CPU mirror.

function build(THREE, rim, intensity) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x070b18);
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.75, 0.26, 200, 28),
    rim.createFresnelRimMaterial(THREE, {intensity, power: 2.2, baseColor: [0.03, 0.05, 0.1]}));
  knot.position.set(-0.75, 0.35, 0);
  const sphere = new THREE.Mesh(new THREE.SphereGeometry(0.62, 64, 32), rim.createFresnelRimMaterial(THREE, {
    intensity, baseColor: [0.08, 0.02, 0.1], rimColor: [1, 0.25, 0.85], power: 3, scale: 1.6,
  }));
  sphere.position.set(0.95, -0.55, 0.2);
  const shell = new THREE.Mesh(sphere.geometry, rim.createFresnelRimMaterial(THREE, {
    mode: 'additive', intensity: intensity * 1.4, rimColor: [1, 0.3, 0.9], power: 2.4, bias: 0, scale: 1.2,
  }));
  shell.position.copy(sphere.position);
  shell.scale.setScalar(1.14);
  scene.add(knot, sphere, shell);
  return scene;
}

export function demo(THREE, rim, harness) {
  // 1. The GLSL rim times the pulse on the GPU equals the CPU mirror across cos(theta) in [-1, 1].
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${rim.FRESNEL_RIM_GLSL}
void main() {
  float value = fresnelRim(vUv.x * 2.0 - 1.0, 3.0, 0.05, 1.2) * fresnelPulse(0.8, 2.0, 0.3);
  gl_FragColor = vec4(value, 0.0, 0.0, 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const width = 128;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
  let worst = 0;
  for (let x = 0; x < width; x += 1) {
    const cosTheta = ((x + 0.5) / width) * 2 - 1;
    const expected = rim.fresnelRim(cosTheta, 3, 0.05, 1.2) * rim.fresnelPulse(0.8, 2, 0.3);
    worst = Math.max(worst, Math.abs(values[x * 4] - expected));
  }
  harness.check('gpu_rim_matches_cpu_mirror', worst < 1e-4, {samples: width, worst_difference: worst});

  // 2. The showcase and its baseline without any rim.
  const scene = build(THREE, rim, 1);
  const additive = scene.children[2].material;
  harness.check('additive_shell_blends_additively', additive.blending === THREE.AdditiveBlending
    && additive.depthWrite === false && additive.uniforms.uAdditive.value === 1, {blending: additive.blending});
  const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 50);
  camera.position.set(0.05, 0.15, 6.1);
  camera.lookAt(0.05, -0.05, 0);
  return {scene, camera, baseline: {scene: build(THREE, rim, 0), camera}};
}
