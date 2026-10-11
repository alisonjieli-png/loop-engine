// Demo of the grid floor, rendered by the family verifier and usable as an example: an editor viewport with a few props
// standing on the grid, the red X axis and the blue Z axis through the origin. The baseline is the same viewport
// without the grid. First the GLSL coverage is evaluated on the GPU with a known derivative (a coordinate of 40 units
// across 256 pixels, so fwidth is 0.15625) and compared with the CPU mirror.

function props(THREE, scene) {
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(4, 7, 5);
  scene.add(key, new THREE.HemisphereLight(0xc8d4ff, 0x30303a, 1.2));
  const material = (color) => new THREE.MeshStandardMaterial({color, roughness: 0.55, metalness: 0.05});
  const box = new THREE.Mesh(new THREE.BoxGeometry(1.4, 1.4, 1.4), material(0xd98c4a));
  box.position.set(-1.6, 0.7, -0.8);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.75, 48, 24), material(0x5aa0d8));
  ball.position.set(1.3, 0.75, 0.6);
  const column = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.35, 2.6, 32), material(0x9ccf6a));
  column.position.set(0.6, 1.3, -2.6);
  scene.add(box, ball, column);
}

export function demo(THREE, grid, harness) {
  // 1. Line coverage (r), axis coverage (g) and the derivative itself (b) across 256 pixels.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${grid.GRID_FLOOR_GLSL}
void main() {
  float coordinate = vUv.x * 40.0;
  float footprint = fwidth(coordinate);
  gl_FragColor = vec4(gridLineCoverage(coordinate, 1.0, 1.5, footprint), gridAxisCoverage(coordinate - 20.0, 2.2, footprint),
                      footprint, 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const width = 256;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
  const footprint = 40 / width;
  let worstLine = 0;
  let worstAxis = 0;
  let worstFootprint = 0;
  for (let x = 0; x < width; x += 1) {
    const coordinate = ((x + 0.5) / width) * 40;
    worstLine = Math.max(worstLine, Math.abs(values[x * 4] - grid.gridLineCoverage(coordinate, 1, 1.5, footprint)));
    worstAxis = Math.max(worstAxis, Math.abs(values[x * 4 + 1] - grid.gridAxisCoverage(coordinate - 20, 2.2, footprint)));
    worstFootprint = Math.max(worstFootprint, Math.abs(values[x * 4 + 2] - footprint));
  }
  harness.check('gpu_derivative_is_known', worstFootprint < 1e-5, {expected: footprint, worst_difference: worstFootprint});
  harness.check('gpu_line_coverage_matches_cpu_mirror', worstLine < 2e-3, {samples: width, worst_difference: worstLine});
  harness.check('gpu_axis_coverage_matches_cpu_mirror', worstAxis < 2e-3, {worst_difference: worstAxis});

  // 2. The viewport with and without the grid.
  const background = new THREE.Color(0x2b2d33);
  const scene = new THREE.Scene();
  scene.background = background;
  props(THREE, scene);
  const plane = new THREE.PlaneGeometry(400, 400);
  plane.rotateX(-Math.PI / 2);
  scene.add(new THREE.Mesh(plane, grid.createGridFloorMaterial(THREE, {fadeStart: 10, fadeEnd: 32})));
  const baseline = new THREE.Scene();
  baseline.background = background;
  props(THREE, baseline);
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  camera.position.set(6.5, 4.6, 7.5);
  camera.lookAt(-0.2, 0.4, -0.6);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
