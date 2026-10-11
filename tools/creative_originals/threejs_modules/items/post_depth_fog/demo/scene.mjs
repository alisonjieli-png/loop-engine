// Demo of the depth fog pass, rendered by the family verifier and usable as an example. Two GPU checks: a plane six
// units away, rendered with a DepthTexture, must come out of the pass in exactly the CPU's fogged colour; and over a
// tilted plane the GLSL linearization must equal linearizeDepth of the depth values the GPU read. Then an avenue of
// columns is fogged; the baseline is the same frame with density 0.

function depthTarget(THREE, width, height, type) {
  const target = new THREE.WebGLRenderTarget(width, height, {type});
  target.depthTexture = new THREE.DepthTexture(width, height);
  return target;
}

function draw(harness, target, scene, camera) {
  harness.renderer.setRenderTarget(target);
  harness.renderer.render(scene, camera);
  harness.renderer.setRenderTarget(null);
}

export function demo(THREE, fog, harness) {
  const near = 0.1;
  const far = 50;
  const size = 32;
  const camera = new THREE.PerspectiveCamera(50, 1, near, far);

  // 1. A plane at distance 6: every pixel must be the CPU's fogged colour.
  const wall = new THREE.Scene();
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(100, 100), new THREE.MeshBasicMaterial({color: new THREE.Color(0.8, 0.3, 0.2)}));
  plane.position.z = -6;
  wall.add(plane);
  const frame = depthTarget(THREE, size, size, THREE.FloatType);
  draw(harness, frame, wall, camera);
  const settings = {near, far, density: 0.15, start: 1, color: [0.5, 0.6, 0.7]};
  const pass = fog.createDepthFogMaterial(THREE, settings);
  pass.uniforms.tDiffuse.value = frame.texture;
  pass.uniforms.tDepth.value = frame.depthTexture;
  const quad = harness.fullscreen(pass);
  const fogged = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  const expected = fog.applyDepthFogCpu([0.8, 0.3, 0.2], fog.depthFromDistance(6, near, far), settings);
  let worstPlane = 0;
  for (let pixel = 0; pixel < size * size; pixel += 1) {
    for (let channel = 0; channel < 3; channel += 1) {
      worstPlane = Math.max(worstPlane, Math.abs(fogged[pixel * 4 + channel] - expected[channel]));
    }
  }
  harness.check('gpu_fogged_plane_matches_cpu', worstPlane < 1e-4, {expected, worst: worstPlane});

  // 2. A tilted plane: the GLSL linearization against linearizeDepth of the raw depth values.
  const slope = new THREE.Scene();
  const tilted = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshBasicMaterial({color: 0xffffff}));
  tilted.position.set(0, -2, -8);
  tilted.rotation.x = -1.2;
  slope.add(tilted);
  const sloped = depthTarget(THREE, size, size, THREE.FloatType);
  draw(harness, sloped, slope, camera);
  const probe = (body) => new THREE.ShaderMaterial({
    uniforms: {tDepth: {value: sloped.depthTexture}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform sampler2D tDepth;\nvarying vec2 vUv;\n${fog.DEPTH_FOG_GLSL}\nvoid main() {\n  float depth = texture2D(tDepth, vUv).x;\n  ${body}\n}`,
  });
  const raw = harness.fullscreen(probe('gl_FragColor = vec4(depth, 0.0, 0.0, 1.0);'));
  const rawDepth = harness.renderToTarget(raw.scene, raw.camera, harness.floatTarget(size, size));
  const linear = harness.fullscreen(probe(`gl_FragColor = vec4(fogViewDistance(depth, ${near.toFixed(1)}, ${far.toFixed(1)}, 0), 0.0, 0.0, 1.0);`));
  const distances = harness.renderToTarget(linear.scene, linear.camera, harness.floatTarget(size, size));
  let worstRelative = 0;
  let covered = 0;
  let nearest = Infinity;
  let farthest = 0;
  for (let pixel = 0; pixel < size * size; pixel += 1) {
    const depth = rawDepth[pixel * 4];
    if (!(depth < 1)) continue;
    covered += 1;
    const cpu = fog.linearizeDepth(depth, near, far);
    nearest = Math.min(nearest, cpu);
    farthest = Math.max(farthest, cpu);
    worstRelative = Math.max(worstRelative, Math.abs(distances[pixel * 4] - cpu) / cpu);
  }
  harness.check('gpu_linearization_matches_cpu', covered > size * size / 2 && farthest > 2 * nearest
    && worstRelative < 1e-4, {covered, nearest, farthest, worst_relative: worstRelative});

  // 3. The showcase: an avenue of columns receding into fog.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0.55, 0.62, 0.72);
  scene.add(new THREE.HemisphereLight(0xdde8ff, 0x5a4a3a, 1.5));
  const sun = new THREE.DirectionalLight(0xffe8c8, 2.2);
  sun.position.set(-4, 6, 2);
  scene.add(sun);
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(40, 120), new THREE.MeshStandardMaterial({color: 0x8a7a62}));
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(0, -1.5, -40);
  scene.add(ground);
  const stone = new THREE.MeshStandardMaterial({color: 0xd8cfc0, roughness: 0.6});
  const accent = new THREE.MeshStandardMaterial({color: 0xb2523a, roughness: 0.5});
  for (let row = 0; row < 12; row += 1) {
    for (const side of [-1, 1]) {
      const column = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.38, 4, 20), row % 3 === 0 ? accent : stone);
      column.position.set(side * 2.4, 0.5, -3 - row * 4);
      scene.add(column);
    }
  }
  const view = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
  view.position.set(0.4, 0.6, 2);
  view.lookAt(0, 0.2, -20);
  const hdr = depthTarget(THREE, harness.size, harness.size, THREE.HalfFloatType);
  draw(harness, hdr, scene, view);
  const misty = fog.createDepthFogMaterial(THREE, {near: 0.1, far: 100, density: 0.045, start: 3, color: [0.55, 0.62, 0.72]});
  misty.uniforms.tDiffuse.value = hdr.texture;
  misty.uniforms.tDepth.value = hdr.depthTexture;
  const shown = harness.fullscreen(misty);
  const clear = fog.createDepthFogMaterial(THREE, {near: 0.1, far: 100, density: 0});
  clear.uniforms.tDiffuse.value = hdr.texture;
  clear.uniforms.tDepth.value = hdr.depthTexture;
  const untouched = harness.fullscreen(clear);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
