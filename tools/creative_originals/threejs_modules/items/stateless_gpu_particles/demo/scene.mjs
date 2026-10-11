// Demo of the stateless GPU particles, rendered by the family verifier and usable as an example. A fountain of 4,000
// sparks at uTime = 3.25 rises from a glowing emitter, swirls and falls back. Before that the particle chunk runs on
// the GPU for 1,024 particles (seeds and births read from a float texture) against the CPU mirror. The baseline is the
// same scene without the sparks.

function buildStage(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0b0d16);
  const floor = new THREE.Mesh(new THREE.CircleGeometry(4, 48), new THREE.MeshBasicMaterial({color: 0x1b1f2e}));
  floor.rotation.x = -Math.PI / 2;
  const emitter = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.32, 0.12, 32), new THREE.MeshBasicMaterial({color: 0xffb347}));
  emitter.position.y = 0.06;
  scene.add(floor, emitter);
  return scene;
}

export function demo(THREE, particles, harness) {
  // 1. The particle chunk on the GPU against the CPU mirror.
  const time = 3.25;
  const side = 32;
  const inputs = new Float32Array(side * side * 4);
  for (let index = 0; index < side * side; index += 1) {
    inputs[index * 4] = index;
    inputs[index * 4 + 1] = particles.particleBirth(index);
  }
  const texture = new THREE.DataTexture(inputs, side, side, THREE.RGBAFormat, THREE.FloatType);
  texture.minFilter = THREE.NearestFilter;
  texture.magFilter = THREE.NearestFilter;
  texture.needsUpdate = true;
  const reference = particles.createParticleMaterial(THREE);
  const probe = new THREE.ShaderMaterial({
    uniforms: {...reference.uniforms, uTime: {value: time}, uInputs: {value: texture}},
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `${particles.PARTICLE_UNIFORMS_GLSL}\nuniform sampler2D uInputs;\nvarying vec2 vUv;\n${particles.PARTICLE_GLSL}
void main() {
  vec4 inputs = texture2D(uInputs, vUv);
  gl_FragColor = particleState(inputs.r, inputs.g, uTime);
}`,
  });
  const quad = harness.fullscreen(probe);
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(side, side));
  let worstPosition = 0;
  let worstRelative = 0;
  let worstLife = 0;
  let skipped = 0;
  const lifetime = particles.GPU_PARTICLES_DEFAULTS.lifetime;
  for (let index = 0; index < side * side; index += 1) {
    const loops = (time - particles.particleBirth(index)) / lifetime;
    if (Math.abs(loops - Math.round(loops)) < 1e-5) {
      skipped += 1;
      continue;
    }
    const state = particles.particleState(index, time);
    for (let axis = 0; axis < 3; axis += 1) {
      const error = Math.abs(values[index * 4 + axis] - state.position[axis]);
      worstPosition = Math.max(worstPosition, error);
      worstRelative = Math.max(worstRelative, error / (1 + Math.abs(state.position[axis])));
    }
    worstLife = Math.max(worstLife, Math.abs(values[index * 4 + 3] - state.life));
  }
  // A wrong hash, loop or formula moves a particle by tenths of a unit or more; float32 trigonometry on the GPU stays
  // within a thousandth of 1 + |coordinate|.
  harness.check('gpu_particles_match_cpu_mirror', worstRelative < 1e-3 && worstLife < 1e-4 && skipped < 4,
    {particles: side * side, skipped_at_loop_boundary: skipped, worst_position: worstPosition,
      worst_relative_position: worstRelative, worst_life: worstLife});

  // 2. The fountain.
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 60);
  camera.position.set(0, 1.7, 7.4);
  camera.lookAt(0, 1.45, 0);
  const pointScale = harness.size / (2 * Math.tan((camera.fov * Math.PI) / 360));
  const fountain = particles.createParticlePoints(THREE, {count: 4000, pointScale, startSize: 0.12, endSize: 0.03});
  fountain.material.uniforms.uTime.value = time;
  harness.check('points_carry_seed_and_birth', fountain.geometry.getAttribute('aSeed').count === 4000
    && fountain.geometry.getAttribute('aBirth').getX(7) === particles.particleBirth(7), {});
  const scene = buildStage(THREE);
  scene.add(fountain);
  return {scene, camera, baseline: {scene: buildStage(THREE), camera}};
}
