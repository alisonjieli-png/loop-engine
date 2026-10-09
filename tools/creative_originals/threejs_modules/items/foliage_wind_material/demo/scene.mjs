// Demo of the foliage wind material, rendered by the family verifier and usable as an example. A meadow of 2,200
// instanced, tapered blades bends in a gusty wind at uTime = 2.3. Before that the wind chunk runs on the GPU against
// the CPU mirror for 512 blade positions. The baseline is the same meadow with no wind.

function bladeGeometry(THREE) {
  const geometry = new THREE.PlaneGeometry(0.07, 1, 1, 6);
  geometry.translate(0, 0.5, 0);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    position.setX(index, position.getX(index) * (1 - 0.85 * position.getY(index)));
  }
  geometry.computeVertexNormals();
  return geometry;
}

function meadow(THREE, material) {
  let state = 2024;
  const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
  const count = 2200;
  const grass = new THREE.InstancedMesh(bladeGeometry(THREE), material, count);
  const matrix = new THREE.Matrix4();
  const rotation = new THREE.Quaternion();
  const up = new THREE.Vector3(0, 1, 0);
  for (let index = 0; index < count; index += 1) {
    const radius = 4.6 * Math.sqrt(next());
    const angle = next() * Math.PI * 2;
    const height = 0.55 + next() * 0.7;
    rotation.setFromAxisAngle(up, next() * Math.PI);
    matrix.compose(new THREE.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius), rotation,
      new THREE.Vector3(1, height, 1));
    grass.setMatrixAt(index, matrix);
  }
  return grass;
}

function buildScene(THREE, material) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x9cc7e8);
  const ground = new THREE.Mesh(new THREE.CircleGeometry(6, 48), new THREE.MeshBasicMaterial({color: 0x3b4a22}));
  ground.rotation.x = -Math.PI / 2;
  scene.add(ground, meadow(THREE, material));
  return scene;
}

export function demo(THREE, wind, harness) {
  // 1. The wind chunk on the GPU against the CPU mirror: 32 x 16 anchors and heights at time 3.7.
  const uniforms = wind.foliageWindUniforms(THREE, {strength: 0.3});
  uniforms.uTime.value = 3.7;
  const probe = new THREE.ShaderMaterial({
    uniforms,
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `${wind.FOLIAGE_WIND_UNIFORMS_GLSL}\nvarying vec2 vUv;\n${wind.FOLIAGE_WIND_GLSL}
void main() {
  vec3 anchor = vec3(vUv.x * 20.0 - 10.0, 0.0, vUv.y * 7.0 - 3.0);
  gl_FragColor = vec4(windOffset(vec3(0.0, vUv.y, 0.0), anchor, uTime), 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const width = 32;
  const height = 16;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, height));
  let worst = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const u = (x + 0.5) / width;
      const v = (y + 0.5) / height;
      const expected = wind.windOffset([0, v, 0], [u * 20 - 10, 0, v * 7 - 3], 3.7, {strength: 0.3});
      for (let k = 0; k < 3; k += 1) worst = Math.max(worst, Math.abs(values[(y * width + x) * 4 + k] - expected[k]));
    }
  }
  harness.check('gpu_wind_matches_cpu_mirror', worst < 1e-4, {samples: width * height, worst_difference: worst});

  // 2. The meadow in the wind, and the same meadow becalmed.
  const windy = wind.createFoliageWindMaterial(THREE, {strength: 0.32, gustStrength: 0.8, direction: [1, 0.25]});
  windy.uniforms.uTime.value = 2.3;
  const calm = wind.createFoliageWindMaterial(THREE, {strength: 0});
  harness.check('materials_are_double_sided', windy.side === THREE.DoubleSide && calm.side === THREE.DoubleSide, {});
  const camera = new THREE.PerspectiveCamera(45, 1, 0.05, 50);
  camera.position.set(0.3, 2.1, 6.2);
  camera.lookAt(0, 0.15, 0);
  return {scene: buildScene(THREE, windy), camera, baseline: {scene: buildScene(THREE, calm), camera}};
}
