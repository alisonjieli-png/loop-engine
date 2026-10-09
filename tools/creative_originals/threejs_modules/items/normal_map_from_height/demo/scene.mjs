// Demo of the normal map generator, rendered by the family verifier and usable as an example. A height field of
// studs and ripples becomes a normal map on a metal plate lit at a grazing angle; the baseline is the same plate
// without the map. First, a small map is sampled on the GPU and must decode to the bytes and normals the CPU wrote.

function studs(size) {
  const heights = new Float32Array(size * size);
  const cell = size / 4;
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const dx = (x % cell) - cell / 2 + 0.5;
      const dy = (y % cell) - cell / 2 + 0.5;
      const radius = cell * 0.36;
      const dome = Math.sqrt(Math.max(radius * radius - dx * dx - dy * dy, 0)) * 0.55;
      heights[y * size + x] = dome + 0.6 * Math.sin((x + y) * 0.35) + 0.25 * Math.sin(x * 1.3) * Math.cos(y * 0.9);
    }
  }
  return heights;
}

export function demo(THREE, normals, harness) {
  // 1. GPU decode: a 16 x 16 map sampled at texel centres must give back the CPU's bytes and, within 8-bit
  //    quantization, its unit normals.
  const small = 16;
  const field = new Float32Array(small * small).map((_, index) => 3 * Math.sin(index * 0.37) * Math.cos(index * 0.11));
  const bytes = normals.normalMapFromHeight(field, small, small, {strength: 0.8});
  const exact = normals.normalsFromHeight(field, small, small, {strength: 0.8});
  const probe = new THREE.ShaderMaterial({
    uniforms: {uMap: {value: normals.createNormalMapTexture(THREE, bytes, small, small)}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: 'uniform sampler2D uMap;\nvarying vec2 vUv;\nvoid main() { gl_FragColor = vec4(texture2D(uMap, vUv).xyz * 2.0 - 1.0, 1.0); }',
  });
  const quad = harness.fullscreen(probe);
  const decoded = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(small, small));
  let byteWorst = 0;
  let normalWorst = 0;
  for (let texel = 0; texel < small * small; texel += 1) {
    for (let axis = 0; axis < 3; axis += 1) {
      const gpu = decoded[texel * 4 + axis];
      byteWorst = Math.max(byteWorst, Math.abs(gpu - (bytes[texel * 4 + axis] / 255) * 2 + 1));
      normalWorst = Math.max(normalWorst, Math.abs(gpu - exact[texel * 3 + axis]));
    }
  }
  harness.check('gpu_decodes_the_cpu_bytes', byteWorst < 1e-5, {texels: small * small, worst_difference: byteWorst});
  harness.check('gpu_normals_within_quantization', normalWorst < 0.01, {worst_difference: normalWorst});

  // 2. The showcase: a brushed metal plate with studs, lit from a low angle.
  const size = 128;
  const map = normals.createNormalMapTexture(THREE, normals.normalMapFromHeight(studs(size), size, size, {strength: 0.9}), size, size);
  map.repeat.set(2, 2);
  const plate = new THREE.PlaneGeometry(2.6, 2.6);
  const build = (normalMap) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x161b24);
    const grazing = new THREE.DirectionalLight(0xfff0dc, 3.2);
    grazing.position.set(-3, 1.2, 1.5);
    scene.add(grazing, new THREE.HemisphereLight(0x9fb6d8, 0x221c18, 0.6));
    const material = new THREE.MeshStandardMaterial({color: 0xb9c3d1, metalness: 0.55, roughness: 0.38});
    if (normalMap) material.normalMap = normalMap;
    const mesh = new THREE.Mesh(plate, material);
    mesh.rotation.x = -0.75;
    scene.add(mesh);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 30);
  camera.position.set(0, 0.25, 3.3);
  camera.lookAt(0, 0, 0);
  return {scene: build(map), camera, baseline: {scene: build(null), camera}};
}
