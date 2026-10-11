// Demo of the toon band material, rendered by the family verifier and usable as an example. demo(THREE, toon,
// harness) receives three.js, this item's module and the verifier harness (renderer, size, check(), fullscreen(),
// floatTarget(), renderToTarget()); it returns the scene to show and a baseline without the effect.

export function demo(THREE, toon, harness) {
  // 1. The band function on the GPU equals its CPU mirror: evaluate it across a 128 x 1 float target.
  const probe = new THREE.ShaderMaterial({
    uniforms: {uBands: {value: 4}, uSoftness: {value: 0.02}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform float uBands;\nuniform float uSoftness;\nvarying vec2 vUv;\n${toon.TOON_BAND_GLSL}
void main() { gl_FragColor = vec4(toonBandLevel(vUv.x * 2.0 - 1.0, uBands, uSoftness), 0.0, 0.0, 1.0); }`,
  });
  const quad = harness.fullscreen(probe);
  const width = 128;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
  let worst = 0;
  for (let x = 0; x < width; x += 1) {
    const nDotL = ((x + 0.5) / width) * 2 - 1;
    worst = Math.max(worst, Math.abs(values[x * 4] - toon.toonBandLevel(nDotL, 4, 0.02)));
  }
  harness.check('gpu_band_levels_match_cpu_mirror', worst < 1e-3, {samples: width, worst_difference: worst});

  // 2. The showcase: a torus knot and a sphere under the toon material, against a dark backdrop.
  const background = new THREE.Color(0x1b2030);
  const scene = new THREE.Scene();
  scene.background = background;
  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 50);
  camera.position.set(0.4, 0.9, 6.3);
  camera.lookAt(0, 0, 0);
  const lightDirection = toon.toonLightDirection([4, 6, 3]);
  const warm = toon.createToonBandMaterial(THREE, {bands: 3, softness: 0.01, specularSize: 0.04, lightDirection});
  const cool = toon.createToonBandMaterial(THREE, {
    bands: 2, softness: 0.01, color: [0.2, 0.55, 0.85], shadowColor: [0.05, 0.08, 0.2], lightDirection, specularSize: 0.08,
  });
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.85, 0.3, 192, 24), warm);
  knot.position.set(-0.55, 0.15, 0);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.55, 48, 24), cool);
  ball.position.set(1.25, -0.7, 0.4);
  scene.add(knot, ball);
  harness.check('builder_makes_shader_materials', warm.isShaderMaterial === true && cool.uniforms.uBands.value === 2,
    {uniforms: Object.keys(warm.uniforms).length});

  // Baseline: the same meshes in flat unlit colours, so the verifier can see the shading change the frame.
  const baseline = new THREE.Scene();
  baseline.background = background;
  const flatKnot = new THREE.Mesh(knot.geometry, new THREE.MeshBasicMaterial({color: warm.uniforms.uColor.value}));
  flatKnot.position.copy(knot.position);
  const flatBall = new THREE.Mesh(ball.geometry, new THREE.MeshBasicMaterial({color: cool.uniforms.uColor.value}));
  flatBall.position.copy(ball.position);
  baseline.add(flatKnot, flatBall);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
