// Demo of the Gooch material, rendered by the family verifier and usable as an example: a torus knot, a turned vase and
// a capsule in the cool-to-warm style on a paper-coloured background. The baseline is the same scene in Lambert shading.
// First the GLSL tone and silhouette are evaluated on the GPU and compared with the CPU mirrors.

function vase(THREE) {
  const profile = [];
  for (let step = 0; step <= 24; step += 1) {
    const t = step / 24;
    profile.push(new THREE.Vector2(0.18 + 0.32 * Math.sin(Math.PI * (0.15 + 0.8 * t)) + 0.06 * Math.sin(9 * t), t * 1.5 - 0.75));
  }
  return new THREE.LatheGeometry(profile, 64);
}

export function demo(THREE, gooch, harness) {
  // 1. Tone (rgb) and silhouette (a) across N.L and N.V in [-1, 1] on the GPU equal the CPU mirrors.
  const probe = new THREE.ShaderMaterial({
    vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
    fragmentShader: `varying vec2 vUv;\n${gooch.GOOCH_GLSL}
void main() {
  float n = vUv.x * 2.0 - 1.0;
  vec3 tone = goochColor(n, vec3(0.75, 0.3, 0.2), vec3(0.0, 0.0, 0.55), vec3(0.3, 0.3, 0.0), 0.25, 0.5);
  gl_FragColor = vec4(tone, goochSilhouette(n, 0.18, 0.06));
}`,
  });
  const quad = harness.fullscreen(probe);
  const width = 128;
  const values = harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(width, 1));
  let worstTone = 0;
  let worstEdge = 0;
  for (let x = 0; x < width; x += 1) {
    const n = ((x + 0.5) / width) * 2 - 1;
    const tone = gooch.goochColor(n, [0.75, 0.3, 0.2], [0, 0, 0.55], [0.3, 0.3, 0], 0.25, 0.5);
    for (let k = 0; k < 3; k += 1) worstTone = Math.max(worstTone, Math.abs(values[x * 4 + k] - tone[k]));
    worstEdge = Math.max(worstEdge, Math.abs(values[x * 4 + 3] - gooch.goochSilhouette(n, 0.18, 0.06)));
  }
  harness.check('gpu_tone_matches_cpu_mirror', worstTone < 1e-5, {samples: width, worst_difference: worstTone});
  harness.check('gpu_silhouette_matches_cpu_mirror', worstEdge < 1e-4, {worst_difference: worstEdge});

  // 2. The showcase and its Lambert baseline.
  const parts = [
    {geometry: new THREE.TorusKnotGeometry(0.55, 0.19, 220, 28), color: [0.75, 0.3, 0.2], position: [-0.85, 0.35, 0]},
    {geometry: vase(THREE), color: [0.25, 0.45, 0.7], position: [0.95, 0.05, -0.3]},
    {geometry: new THREE.CapsuleGeometry(0.28, 0.7, 12, 32), color: [0.55, 0.62, 0.3], position: [-0.15, -0.75, 0.5]},
  ];
  const paper = new THREE.Color(0xeeeae2);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = paper;
  baseline.background = paper;
  const key = new THREE.DirectionalLight(0xffffff, 2.4);
  key.position.set(0.5, 0.8, 0.4);
  baseline.add(key, new THREE.AmbientLight(0xffffff, 0.5));
  for (const part of parts) {
    const shaded = new THREE.Mesh(part.geometry, gooch.createGoochMaterial(THREE, {baseColor: part.color}));
    const plain = new THREE.Mesh(part.geometry, new THREE.MeshLambertMaterial({color: new THREE.Color(...part.color)}));
    for (const mesh of [shaded, plain]) {
      mesh.position.fromArray(part.position);
      mesh.rotation.set(0.35, 0.4, 0.1);
    }
    scene.add(shaded);
    baseline.add(plain);
  }
  const camera = new THREE.PerspectiveCamera(36, 1, 0.1, 50);
  camera.position.set(0, 0.3, 5.6);
  camera.lookAt(0, -0.05, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
