// Demo of the force-field shield, rendered by the family verifier and usable as an example. A ship inside a shield
// sphere is hit three times; at uTime = 2 the rings are 0.18, 0.55 and 0.85 seconds old. Before that the ripple chunk
// runs on the GPU against its CPU mirror, and the eight-slot hit buffer is filled past its end. The baseline is the
// same shield with no hits.

function stars(THREE) {
  let state = 12345;
  const next = () => { state = (Math.imul(state, 1103515245) + 12345) >>> 0; return state / 4294967296; };
  const positions = [];
  for (let index = 0; index < 600; index += 1) {
    const theta = next() * Math.PI * 2;
    const height = next() * 2 - 1;
    const radius = Math.sqrt(1 - height * height) * 30;
    positions.push(Math.cos(theta) * radius, height * 30, Math.sin(theta) * radius);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  return new THREE.Points(geometry, new THREE.PointsMaterial({color: 0xcfd8ff, size: 1.6, sizeAttenuation: false}));
}

function buildScene(THREE, shield) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x05070f);
  scene.add(stars(THREE), new THREE.HemisphereLight(0x9fb8ff, 0x1a1020, 1.1));
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(3, 4, 5);
  scene.add(key);
  const ship = new THREE.Mesh(new THREE.TorusKnotGeometry(0.5, 0.16, 160, 20),
    new THREE.MeshStandardMaterial({color: 0x9aa5b8, metalness: 0.7, roughness: 0.3}));
  ship.rotation.set(0.4, 0.3, 0);
  scene.add(ship, shield);
  return scene;
}

export function demo(THREE, field, harness) {
  // 1. The ripple chunk on the GPU against the CPU mirror over distances 0..2.4 and ages -0.15..1.55.
  const settings = {rippleSpeed: 1.6, rippleWidth: 0.12, rippleLifetime: 1.4, rippleStrength: 1.4};
  const probe = new THREE.ShaderMaterial({
    uniforms: {},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${field.FORCE_FIELD_GLSL}
void main() {
  gl_FragColor = vec4(rippleIntensity(vUv.x * 2.4, vUv.y * 1.7 - 0.15, 1.6, 0.12, 1.4, 1.4), 0.0, 0.0, 1.0);
}`,
  });
  const quad = harness.fullscreen(probe);
  const width = 64;
  const height = 16;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, height));
  let worst = 0;
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const expected = field.rippleIntensity(((x + 0.5) / width) * 2.4, ((y + 0.5) / height) * 1.7 - 0.15, settings);
      worst = Math.max(worst, Math.abs(values[(y * width + x) * 4] - expected));
    }
  }
  harness.check('gpu_ripple_matches_cpu_mirror', worst < 1e-4, {samples: width * height, worst_difference: worst});

  // 2. The ring buffer keeps the newest eight hits.
  const buffer = field.createForceFieldMaterial(THREE);
  for (let hit = 0; hit < 10; hit += 1) field.addHit(buffer, [hit, 0, 0], hit);
  harness.check('ring_buffer_keeps_newest_eight', buffer.uniforms.uHitTimes.value[0] === 8
    && buffer.uniforms.uHitTimes.value[1] === 9 && buffer.uniforms.uHitTimes.value[2] === 2, {});

  // 3. The shield, struck three times.
  const radius = 1.35;
  const onSurface = (direction) => {
    const size = Math.hypot(...direction);
    return direction.map((value) => (value / size) * radius);
  };
  const material = field.createForceFieldMaterial(THREE, {doubleSided: true});
  material.uniforms.uTime.value = 2;
  field.addHit(material, onSurface([0.55, 0.5, 0.8]), 1.82);
  field.addHit(material, onSurface([-0.75, 0.15, 0.65]), 1.45);
  field.addHit(material, onSurface([0.1, -0.85, 0.55]), 1.15);
  const geometry = new THREE.SphereGeometry(radius, 128, 64);
  const shield = new THREE.Mesh(geometry, material);
  const calm = field.clearHits(field.createForceFieldMaterial(THREE, {doubleSided: true}));
  calm.uniforms.uTime.value = 2;
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0.6, 0.5, 4.6);
  camera.lookAt(0, 0, 0);
  return {scene: buildScene(THREE, shield), camera, baseline: {scene: buildScene(THREE, new THREE.Mesh(geometry, calm)), camera}};
}
