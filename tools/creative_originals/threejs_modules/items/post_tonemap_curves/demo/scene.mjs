// Demo of the tone mapping curves, rendered by the family verifier and usable as an example. First an HDR ramp
// (0 to 16 across the channels) goes through all four curves on the GPU and must equal tonemapValue at every texel.
// Then an HDR scene with highlights far above 1 is rendered into a HalfFloat target and shown through the ACES curve;
// the baseline shows it through the plain clamp, which clips the highlights.

export function demo(THREE, tonemap, harness) {
  // 1. HDR ramp through every curve.
  const width = 64;
  const ramp = new Float32Array(width * 4);
  for (let x = 0; x < width; x += 1) {
    const value = (8 * x) / (width - 1);
    ramp.set([value, value * 0.5, value * 2, 1], x * 4);
  }
  const input = new THREE.DataTexture(ramp, width, 1, THREE.RGBAFormat, THREE.FloatType);
  input.minFilter = THREE.NearestFilter;
  input.magFilter = THREE.NearestFilter;
  input.needsUpdate = true;
  const settings = {exposure: 1.3, whitePoint: 5};
  const probe = tonemap.createTonemapMaterial(THREE, settings);
  probe.uniforms.tDiffuse.value = input;
  const quad = harness.fullscreen(probe);
  const target = harness.floatTarget(width, 1);
  const worst = {};
  for (const [name, number] of Object.entries(tonemap.TONEMAP_OPERATORS)) {
    probe.uniforms.uOperator.value = number;
    const values = harness.renderToTarget(quad.scene, quad.camera, target);
    let largest = 0;
    for (let x = 0; x < width; x += 1) {
      for (let channel = 0; channel < 3; channel += 1) {
        const expected = tonemap.tonemapValue(ramp[x * 4 + channel], {...settings, operator: name});
        largest = Math.max(largest, Math.abs(values[x * 4 + channel] - expected));
      }
    }
    worst[name] = largest;
  }
  harness.check('gpu_curves_match_cpu_mirror', Object.values(worst).every((value) => value < 1e-5), worst);

  // 2. The showcase: an HDR dusk scene with neon tubes and a hot sun.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0.035, 0.04, 0.09);
  scene.add(new THREE.HemisphereLight(0x8fb0ff, 0x201810, 0.6));
  const sun = new THREE.DirectionalLight(0xffd9a8, 9);
  sun.position.set(-3, 2.5, 3);
  scene.add(sun);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(10, 10),
    new THREE.MeshStandardMaterial({color: 0x30343c, roughness: 0.25, metalness: 0.2}));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1;
  scene.add(floor);
  [[0xff2d6f, -1.4, 0xc8743c], [0x2dd0ff, 0, 0x3c9c94], [0xffd23c, 1.4, 0xe8e2d6]].forEach(([neon, x, body]) => {
    const tube = new THREE.Mesh(new THREE.TorusGeometry(0.42, 0.06, 16, 64),
      new THREE.MeshStandardMaterial({color: neon, emissive: neon, emissiveIntensity: 3.5}));
    tube.position.set(x, 0.55, -0.9);
    scene.add(tube);
    const ball = new THREE.Mesh(new THREE.SphereGeometry(0.42, 48, 24),
      new THREE.MeshStandardMaterial({color: body, roughness: 0.22, metalness: 0.15}));
    ball.position.set(x * 0.85, -0.58, 0.35);
    scene.add(ball);
  });
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 0.5, 4.2);
  camera.lookAt(0, -0.3, 0);
  const hdr = new THREE.WebGLRenderTarget(harness.size, harness.size, {type: THREE.HalfFloatType});
  harness.renderer.setRenderTarget(hdr);
  harness.renderer.render(scene, camera);
  harness.renderer.setRenderTarget(null);

  const filmic = tonemap.createTonemapMaterial(THREE, {operator: 'aces', exposure: 0.9});
  filmic.uniforms.tDiffuse.value = hdr.texture;
  const shown = harness.fullscreen(filmic);
  const clipped = tonemap.createTonemapMaterial(THREE, {operator: 'clamp', exposure: 0.9});
  clipped.uniforms.tDiffuse.value = hdr.texture;
  const untouched = harness.fullscreen(clipped);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
