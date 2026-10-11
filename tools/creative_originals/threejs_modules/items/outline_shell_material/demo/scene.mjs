// Demo of the inverted-hull outline, rendered by the family verifier and usable as an example. Three toon-shaded
// shapes on a paper-coloured backdrop get ink outlines of 2, 3 and 5 pixels. Before that the outline chunk runs on
// the GPU against its CPU mirror, and a magenta 4-pixel outline around a sphere is measured on all four sides. The
// baseline is the same scene without the outlines.

function isMagenta(pixels, x, y, size) {
  const index = (y * size + x) * 4;
  return pixels[index] > 200 && pixels[index + 1] < 60 && pixels[index + 2] > 200;
}

// Length of the magenta run that starts at the first magenta pixel met walking from (x, y) by (dx, dy).
function runFrom(pixels, size, x, y, dx, dy) {
  let px = x;
  let py = y;
  while (px >= 0 && py >= 0 && px < size && py < size && !isMagenta(pixels, px, py, size)) { px += dx; py += dy; }
  let run = 0;
  while (px >= 0 && py >= 0 && px < size && py < size && isMagenta(pixels, px, py, size)) { run += 1; px += dx; py += dy; }
  return run;
}

export function demo(THREE, outline, harness) {
  const size = harness.size;
  // 1. The GPU chunk equals the CPU mirror on a 16 x 16 grid of clip positions and normals.
  const probe = new THREE.ShaderMaterial({
    uniforms: {uWidth: {value: 3.5}, uResolution: {value: new THREE.Vector2(640, 360)}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `uniform float uWidth;\nuniform vec2 uResolution;\nvarying vec2 vUv;\n${outline.OUTLINE_GLSL}
void main() {
  vec4 clipPosition = vec4(vUv.x * 2.0 - 1.0, vUv.y * 2.0 - 1.0, 0.25, 1.0 + 2.0 * vUv.x);
  float angle = vUv.y * 6.2831853 + vUv.x * 3.0;
  gl_FragColor = outlineClipOffset(clipPosition, vec4(cos(angle), sin(angle), 0.5, 0.0), uWidth, uResolution);
}`,
  });
  const grid = 16;
  const quad = harness.fullscreen(probe);
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(grid, grid));
  let worst = 0;
  for (let y = 0; y < grid; y += 1) {
    for (let x = 0; x < grid; x += 1) {
      const u = (x + 0.5) / grid;
      const v = (y + 0.5) / grid;
      const angle = v * 6.2831853 + u * 3;
      const expected = outline.outlineClipOffset([u * 2 - 1, v * 2 - 1, 0.25, 1 + 2 * u],
        [Math.cos(angle), Math.sin(angle), 0.5, 0], 3.5, [640, 360]);
      for (let k = 0; k < 4; k += 1) worst = Math.max(worst, Math.abs(values[(y * grid + x) * 4 + k] - expected[k]));
    }
  }
  harness.check('gpu_offset_matches_cpu_mirror', worst < 1e-4, {samples: grid * grid, worst_difference: worst});

  // 2. A 4-pixel magenta outline rings a sphere: 3 to 5 pixels thick on every side, none over the sphere itself.
  const ringScene = new THREE.Scene();
  ringScene.background = new THREE.Color(0x000000);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(1, 96, 48), new THREE.MeshBasicMaterial({color: 0x3366cc}));
  ringScene.add(ball);
  const ring = outline.createOutlineShell(THREE, ball, {color: [1, 0, 1], width: 4, resolution: [size, size]});
  const ringCamera = new THREE.PerspectiveCamera(40, 1, 0.1, 20);
  ringCamera.position.set(0, 0, 4);
  const pixels = harness.renderToCanvas(ringScene, ringCamera);
  const middle = size / 2;
  const runs = [runFrom(pixels, size, 0, middle, 1, 0), runFrom(pixels, size, size - 1, middle, -1, 0),
    runFrom(pixels, size, middle, 0, 0, 1), runFrom(pixels, size, middle, size - 1, 0, -1)];
  harness.check('outline_rings_the_silhouette', runs.every((run) => run >= 3 && run <= 5)
    && !isMagenta(pixels, middle, middle, size) && ball.children.includes(ring), {runs_left_right_bottom_top: runs});

  // 3. The showcase.
  const build = (withOutlines) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xf2ead8);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x8a8170, 1.2));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(3, 5, 4);
    scene.add(key);
    const shapes = [
      [new THREE.TorusKnotGeometry(0.62, 0.21, 160, 20), 0xe76f51, [-1.15, 0.35, 0], 3],
      [new THREE.SphereGeometry(0.62, 48, 24), 0x2a9d8f, [1.2, 0.45, -0.3], 5],
      [new THREE.ConeGeometry(0.55, 1.1, 40), 0xe9c46a, [0.15, -0.95, 0.4], 2],
    ];
    for (const [geometry, colour, position, width] of shapes) {
      const mesh = new THREE.Mesh(geometry, new THREE.MeshToonMaterial({color: colour}));
      mesh.position.fromArray(position);
      mesh.rotation.set(0.3, 0.5, 0);
      scene.add(mesh);
      if (withOutlines) outline.createOutlineShell(THREE, mesh, {width, color: [0.03, 0.03, 0.05], resolution: [size, size]});
    }
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 40);
  camera.position.set(0, 0.4, 5.2);
  camera.lookAt(0, -0.05, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
