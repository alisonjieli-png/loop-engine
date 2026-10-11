// Demo of the gradient ramp textures, rendered by the family verifier and usable as an example. A three-step toon
// gradient map shades a torus knot and a sphere with MeshToonMaterial, and a sunset ramp is shown as a colour strip.
// The baseline uses MeshToonMaterial's built-in two-tone shading and a plain strip. First, the sRGB ramp texture is
// sampled on the GPU and must decode to the CPU's linear-light gradient.

const SUNSET = [
  {position: 0, color: 0x1b1f4a},
  {position: 0.45, color: 0xd9465f},
  {position: 0.75, color: 0xf4a259},
  {position: 1, color: 0xfbe6a2},
];

export function demo(THREE, ramp, harness) {
  // 1. GPU: three.js uploads the sRGB ramp as SRGB8_ALPHA8, so sampling returns linear light; it must match
  //    sampleGradient at each texel centre within 8-bit sRGB quantization.
  const width = 64;
  const texture = ramp.createGradientTexture(THREE, SUNSET, {width});
  const probe = new THREE.ShaderMaterial({
    uniforms: {uRamp: {value: texture}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D uRamp;\nvarying vec2 vUv;\nvoid main() { gl_FragColor = texture2D(uRamp, vec2(vUv.x, 0.5)); }',
  });
  const quad = harness.fullscreen(probe);
  const sampled = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
  let worst = 0;
  for (let texel = 0; texel < width; texel += 1) {
    const expected = ramp.sampleGradient(SUNSET, (texel + 0.5) / width);
    for (let channel = 0; channel < 3; channel += 1) worst = Math.max(worst, Math.abs(sampled[texel * 4 + channel] - expected[channel]));
  }
  harness.check('gpu_samples_linear_light_gradient', worst < 0.006, {texels: width, worst_difference: worst});

  // 2. The showcase.
  const toonMap = ramp.createToonGradientMap(THREE, [0.16, 0.52, 1]);
  harness.check('toon_map_has_three_nearest_texels', toonMap.image.width === 3 && toonMap.magFilter === THREE.NearestFilter, {});
  const build = (withRamps) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x15192a);
    const sun = new THREE.DirectionalLight(0xffffff, 2.6);
    sun.position.set(3, 4, 4);
    scene.add(sun, new THREE.AmbientLight(0xffffff, 0.25));
    const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.62, 0.21, 160, 20),
      new THREE.MeshToonMaterial({color: 0xe8794a, gradientMap: withRamps ? toonMap : null}));
    knot.position.set(-0.45, 0.35, 0);
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.45, 48, 24),
      new THREE.MeshToonMaterial({color: 0x5aa2e6, gradientMap: withRamps ? toonMap : null}));
    ball.position.set(1.05, 0.15, 0.2);
    const strip = new THREE.Mesh(new THREE.PlaneGeometry(2.8, 0.42),
      new THREE.MeshBasicMaterial(withRamps ? {map: texture} : {color: 0x6b5a7a}));
    strip.position.set(0.15, -0.95, 0.3);
    scene.add(knot, ball, strip);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 30);
  camera.position.set(0.15, 0.2, 4.6);
  camera.lookAt(0.15, -0.05, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
