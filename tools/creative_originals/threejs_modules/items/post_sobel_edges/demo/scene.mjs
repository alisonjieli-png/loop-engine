// Demo of the Sobel edge pass, rendered by the family verifier and usable as an example. First the pass runs in
// edges-only mode on a small coloured test image (a disc, a step and a ramp) and its mask must equal the CPU mirror
// at every pixel. Then a simple lit scene is rendered into a target and drawn with ink outlines; the baseline draws
// it with opacity 0.

function testImage(size) {
  const rgba = new Float32Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const inDisc = (x - 15.5) ** 2 + (y - 8.5) ** 2 < 30;
      const step = x < 7 ? 0.1 : 0.7;
      const ramp = y / (size - 1);
      rgba.set([inDisc ? 0.9 : step, inDisc ? 0.2 : ramp * 0.6, inDisc ? 0.1 : 0.3, 1], (y * size + x) * 4);
    }
  }
  return rgba;
}

export function demo(THREE, edges, harness) {
  // 1. GPU mask against the CPU mirror, edges only, white on black.
  const size = 24;
  const rgba = testImage(size);
  const input = new THREE.DataTexture(rgba, size, size, THREE.RGBAFormat, THREE.FloatType);
  input.minFilter = THREE.NearestFilter;
  input.magFilter = THREE.NearestFilter;
  input.needsUpdate = true;
  const settings = {mode: 'edges', threshold: 0.35, softness: 0.2, outlineColor: [1, 1, 1], backgroundColor: [0, 0, 0],
    resolution: [size, size]};
  const probe = edges.createSobelEdgesMaterial(THREE, settings);
  probe.uniforms.tDiffuse.value = input;
  const quad = harness.fullscreen(probe);
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  const luma = new Float32Array(size * size);
  for (let index = 0; index < size * size; index += 1) {
    luma[index] = edges.luminance(rgba[index * 4], rgba[index * 4 + 1], rgba[index * 4 + 2]);
  }
  const mask = edges.sobelEdgeMask(luma, size, size, settings);
  let worst = 0;
  let edgePixels = 0;
  for (let index = 0; index < size * size; index += 1) {
    worst = Math.max(worst, Math.abs(values[index * 4] - mask[index]));
    if (mask[index] > 0.5) edgePixels += 1;
  }
  harness.check('gpu_edge_mask_matches_cpu_mirror', worst < 1e-4 && edgePixels > 20, {worst, edge_pixels: edgePixels});

  // 2. The showcase: flat-lit shapes with ink outlines.
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xf2ead8);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8a7d6b, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.8);
  sun.position.set(-2, 4, 3);
  scene.add(sun);
  const shapes = [
    [new THREE.TorusKnotGeometry(0.55, 0.18, 128, 16), 0xe76f51, [-1.0, 0.55, 0]],
    [new THREE.IcosahedronGeometry(0.6, 0), 0x2a9d8f, [1.0, 0.6, 0]],
    [new THREE.CylinderGeometry(0.45, 0.45, 0.9, 24), 0xe9c46a, [-0.95, -0.85, 0]],
    [new THREE.BoxGeometry(0.8, 0.8, 0.8), 0x264653, [1.0, -0.85, 0]],
  ];
  for (const [geometry, colour, position] of shapes) {
    const mesh = new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({color: colour}));
    mesh.position.fromArray(position);
    mesh.rotation.set(0.5, 0.7, 0);
    scene.add(mesh);
  }
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
  camera.position.set(0, 0, 4.6);
  const frame = harness.byteTarget(harness.size, harness.size);
  harness.renderToTarget(scene, camera, frame);
  const resolution = [harness.size, harness.size];
  const ink = edges.createSobelEdgesMaterial(THREE, {threshold: 0.12, softness: 0.06, resolution});
  ink.uniforms.tDiffuse.value = frame.texture;
  const shown = harness.fullscreen(ink);
  const plain = edges.createSobelEdgesMaterial(THREE, {opacity: 0, resolution});
  plain.uniforms.tDiffuse.value = frame.texture;
  const untouched = harness.fullscreen(plain);
  return {scene: shown.scene, camera: shown.camera, baseline: {scene: untouched.scene, camera: untouched.camera}};
}
