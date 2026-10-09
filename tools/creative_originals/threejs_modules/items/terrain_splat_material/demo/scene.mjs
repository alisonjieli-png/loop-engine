// Demo of the terrain splat material, rendered by the family verifier and usable as an example: an island with beaches,
// grassy slopes, rock faces and a snowy peak, painted from height and slope alone. The baseline is the same terrain in
// one Lambert colour. First the GLSL weights are evaluated on the GPU over a grid of heights, slopes and noise values
// and compared with the CPU mirror.

function landscape(THREE) {
  const geometry = new THREE.PlaneGeometry(11, 11, 230, 230);
  geometry.rotateX(-Math.PI / 2);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const z = position.getZ(index);
    const peak = 2.9 * Math.exp(-((x - 1.1) ** 2 + (z + 1.4) ** 2) / 3.1);
    const hill = 0.95 * Math.exp(-((x + 2.4) ** 2 + (z - 0.6) ** 2) / 3);
    const ridges = 0.28 * Math.sin(1.7 * x) * Math.cos(1.3 * z) + 0.1 * Math.sin(4.1 * x + 2.3 * z);
    const shore = -0.9 * Math.max(0, Math.hypot(x, z) - 3.8) ** 1.3;
    position.setY(index, peak + hill + ridges + shore - 0.05);
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function demo(THREE, terrain, harness) {
  // 1. The four weights on the GPU equal the CPU mirror for a 32 x 32 grid of heights, slopes and noise samples.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${terrain.TERRAIN_SPLAT_GLSL}
void main() {
  float noiseValue = valueNoise2(vUv * 9.0, 11u);
  gl_FragColor = splatWeights(vUv.x * 2.4 - 0.4, vUv.y, noiseValue, 0.15, 1.6, 0.12, 0.45, 0.08, 0.25);
}`,
  });
  const quad = harness.fullscreen(probe);
  const size = 32;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  let worst = 0;
  let worstSum = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const u = (x + 0.5) / size;
      const v = (y + 0.5) / size;
      const expected = terrain.splatWeights(u * 2.4 - 0.4, v, {}, terrain.valueNoise2(u * 9, v * 9, 11));
      const offset = (y * size + x) * 4;
      let sum = 0;
      for (let k = 0; k < 4; k += 1) {
        worst = Math.max(worst, Math.abs(values[offset + k] - expected[k]));
        sum += values[offset + k];
      }
      worstSum = Math.max(worstSum, Math.abs(sum - 1));
    }
  }
  harness.check('gpu_weights_match_cpu_mirror', worst < 1e-4, {samples: size * size, worst_difference: worst});
  harness.check('gpu_weights_sum_to_one', worstSum < 1e-5, {worst_sum_error: worstSum});

  // 2. The island, with a sea plane, and the same island in one flat colour.
  const geometry = landscape(THREE);
  const sky = new THREE.Color(0x9fc4e6);
  const sea = new THREE.Mesh(new THREE.PlaneGeometry(400, 400).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({color: 0x1d5f8a, transparent: true, opacity: 0.82}));
  sea.position.y = 0.02;
  const scene = new THREE.Scene();
  scene.background = sky;
  scene.add(new THREE.Mesh(geometry, terrain.createTerrainSplatMaterial(THREE, {lightDirection: [0.6, 0.75, 0.35]})), sea);
  const baseline = new THREE.Scene();
  baseline.background = sky;
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(0.6, 0.75, 0.35);
  baseline.add(new THREE.Mesh(geometry, new THREE.MeshLambertMaterial({color: 0x7a8466})), sea.clone(), sun,
    new THREE.AmbientLight(0xffffff, 0.8));
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(7.4, 4.9, 8.6);
  camera.lookAt(-0.3, 0.55, -0.8);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
