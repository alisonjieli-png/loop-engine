// Demo of the tileable noise textures, rendered by the family verifier and usable as an example. One period of fBm
// noise tiles three by three across a sandstone slab as colour and bump map; the baseline is the slab without them.
// First, the texture is sampled twice across a float target on the GPU: both copies must be identical (repeat
// wrapping) and equal to the CPU bytes.

export function demo(THREE, noise, harness) {
  // 1. GPU: sample a 32 x 32 texture with uv * 2 into a 64 x 32 float target.
  const size = 32;
  const options = {period: 4, octaves: 3, seed: 7};
  const bytes = noise.noiseTextureData(size, size, options);
  const probe = new THREE.ShaderMaterial({
    uniforms: {uNoise: {value: noise.createNoiseTexture(THREE, size, size, options)}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D uNoise;\nvarying vec2 vUv;\nvoid main() { gl_FragColor = texture2D(uNoise, vec2(vUv.x * 2.0, vUv.y)); }',
  });
  const quad = harness.fullscreen(probe);
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size * 2, size));
  let tileWorst = 0;
  let byteWorst = 0;
  for (let row = 0; row < size; row += 1) {
    for (let column = 0; column < size; column += 1) {
      const left = values[(row * size * 2 + column) * 4];
      const right = values[(row * size * 2 + column + size) * 4];
      tileWorst = Math.max(tileWorst, Math.abs(left - right));
      byteWorst = Math.max(byteWorst, Math.abs(left - bytes[(row * size + column) * 4] / 255));
    }
  }
  harness.check('gpu_repeats_the_tile_exactly', tileWorst < 1e-6, {worst_difference: tileWorst});
  harness.check('gpu_reads_the_cpu_bytes', byteWorst < 1e-5, {worst_difference: byteWorst});

  // 2. The showcase: a slab with the noise tiled 3 x 3 as colour and bump.
  const texture = noise.createNoiseTexture(THREE, 128, 128, {period: 6, octaves: 5, gain: 0.55, seed: 3});
  texture.repeat.set(3, 3);
  const build = (textured) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1f2b);
    const sun = new THREE.DirectionalLight(0xfff2de, 2.8);
    sun.position.set(-3, 1.3, 1.2);
    scene.add(sun, new THREE.HemisphereLight(0xb8c8e8, 0x2a2018, 0.7));
    const material = new THREE.MeshStandardMaterial({color: 0xd8b98c, roughness: 0.85});
    if (textured) {
      material.map = texture;
      material.bumpMap = texture;
      material.bumpScale = 7;
    }
    const slab = new THREE.Mesh(new THREE.BoxGeometry(2.4, 0.18, 2.4), material);
    slab.rotation.set(0.62, 0.35, 0);
    scene.add(slab);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 30);
  camera.position.set(0, 0.35, 3.6);
  camera.lookAt(0, 0, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
