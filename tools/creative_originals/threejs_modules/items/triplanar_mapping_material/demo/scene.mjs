// Demo of the triplanar material, rendered by the family verifier and usable as an example: a stretched box and a tall
// cylinder with a brick texture and a lumpy rock with the built-in checker, all without relying on their UVs. The
// baseline maps the same textures through the meshes' own UVs, which stretch. First the GLSL weights and checker are
// evaluated on the GPU and compared with the CPU mirrors.

function brickTexture(THREE) {
  const size = 64;
  const data = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    const row = Math.floor(y / 16);
    for (let x = 0; x < size; x += 1) {
      const shifted = x + (row % 2) * 16;
      const brick = Math.floor(shifted / 32) + row * 7;
      const mortar = y % 16 < 2 || shifted % 32 < 2;
      const shade = 150 + ((brick * 97) % 41);
      const offset = (y * size + x) * 4;
      data.set(mortar ? [205, 198, 186, 255] : [shade + 30, Math.round(shade * 0.45), Math.round(shade * 0.32), 255], offset);
    }
  }
  const texture = new THREE.DataTexture(data, size, size);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  texture.generateMipmaps = true;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function checkerTexture(THREE) {
  const data = new Uint8Array(8 * 8 * 4);
  for (let index = 0; index < 64; index += 1) {
    const dark = ((index % 8) + Math.floor(index / 8)) % 2 === 1;
    data.set(dark ? [41, 51, 71, 255] : [217, 209, 191, 255], index * 4);
  }
  const texture = new THREE.DataTexture(data, 8, 8);
  texture.magFilter = THREE.NearestFilter;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

function rockGeometry(THREE) {
  const geometry = new THREE.SphereGeometry(0.72, 96, 64);
  const position = geometry.attributes.position;
  for (let index = 0; index < position.count; index += 1) {
    const x = position.getX(index);
    const y = position.getY(index);
    const z = position.getZ(index);
    const bump = 1 + 0.16 * Math.sin(3.1 * x + 1.3) * Math.sin(2.7 * y + 0.4) + 0.1 * Math.sin(4.3 * z + 2.1 * x);
    position.setXYZ(index, x * bump * 1.25, y * bump * 0.85, z * bump);
  }
  geometry.computeVertexNormals();
  return geometry;
}

export function demo(THREE, triplanar, harness) {
  // 1. Weights (rgb) and checker (alpha) on the GPU equal the CPU mirrors on a 16 x 16 grid of normals.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${triplanar.TRIPLANAR_GLSL}
void main() {
  vec3 normal = normalize(vec3(vUv.x * 2.0 - 1.0, vUv.y * 2.0 - 1.0, 0.35));
  gl_FragColor = vec4(triplanarWeights(normal, 4.0), triplanarChecker(vUv * 8.0));
}`,
  });
  const quad = harness.fullscreen(probe);
  const size = 16;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(size, size));
  let worst = 0;
  let checkerMismatches = 0;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const u = (x + 0.5) / size;
      const v = (y + 0.5) / size;
      const raw = [u * 2 - 1, v * 2 - 1, 0.35];
      const length = Math.hypot(...raw);
      const expected = triplanar.triplanarWeights(raw.map((value) => value / length), 4);
      const offset = (y * size + x) * 4;
      for (let axis = 0; axis < 3; axis += 1) worst = Math.max(worst, Math.abs(values[offset + axis] - expected[axis]));
      if (values[offset + 3] !== triplanar.triplanarChecker(u * 8, v * 8)) checkerMismatches += 1;
    }
  }
  harness.check('gpu_weights_match_cpu_mirror', worst < 1e-4, {samples: size * size, worst_difference: worst});
  harness.check('gpu_checker_matches_cpu_mirror', checkerMismatches === 0, {mismatches: checkerMismatches});

  // 2. The showcase and its UV-mapped baseline.
  const bricks = brickTexture(THREE);
  const checker = checkerTexture(THREE);
  const background = new THREE.Color(0x1c2230);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(0.45, 0.8, 0.4);
  baseline.add(key, new THREE.AmbientLight(0xffffff, 0.9));
  const parts = [
    {geometry: new THREE.BoxGeometry(1, 1, 1), scale: [3.1, 0.75, 0.85], position: [-0.2, -0.85, -0.4],
      options: {map: bricks, scale: 1.5}, map: bricks},
    {geometry: new THREE.CylinderGeometry(0.42, 0.42, 1, 48), scale: [1, 2.1, 1], position: [1.3, 0.2, -0.7],
      options: {map: bricks, scale: 1.5}, map: bricks},
    {geometry: rockGeometry(THREE), scale: [1, 1, 1], position: [-0.55, 0.45, 0.2],
      options: {scale: 4, sharpness: 6}, map: checker},
  ];
  for (const part of parts) {
    const shown = new THREE.Mesh(part.geometry, triplanar.createTriplanarMaterial(THREE, part.options));
    const plain = new THREE.Mesh(part.geometry, new THREE.MeshLambertMaterial({map: part.map}));
    for (const mesh of [shown, plain]) {
      mesh.scale.fromArray(part.scale);
      mesh.position.fromArray(part.position);
      mesh.rotation.set(0.1, 0.5, 0);
    }
    scene.add(shown);
    baseline.add(plain);
  }
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(1.1, 1.45, 4.9);
  camera.lookAt(0.15, -0.1, -0.25);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
