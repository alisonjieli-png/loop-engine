// Demo of the sky dome, rendered by the family verifier and usable as an example: an evening sky with a low sun over
// dark hills. The baseline replaces the dome with one flat horizon colour. First the GLSL sky is evaluated on the GPU
// for every direction of a 64 x 32 equirectangular grid and compared with the CPU mirror.

const UNIFORMS = `uniform vec3 uZenithColor;\nuniform vec3 uHorizonColor;\nuniform vec3 uGroundColor;\nuniform vec3 uShape;
uniform vec3 uSunDirection;\nuniform vec3 uSunColor;\nuniform vec4 uSunDisc;\nuniform float uHaloStrength;\n`;

function hills(THREE, scene) {
  const ground = new THREE.Mesh(new THREE.CircleGeometry(60, 64).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({color: 0x10141b}));
  ground.position.y = -0.6;
  scene.add(ground);
  const shapes = [[-9, -22, 7, 3.2], [-2, -26, 9, 2.4], [7, -21, 6, 3.6], [15, -27, 8, 2.8], [-17, -18, 6, 2.2]];
  for (const [x, z, radius, height] of shapes) {
    const hill = new THREE.Mesh(new THREE.SphereGeometry(radius, 32, 12, 0, Math.PI * 2, 0, Math.PI / 2),
      new THREE.MeshBasicMaterial({color: 0x1a1f29}));
    hill.scale.y = height / radius;
    hill.position.set(x, -0.6, z);
    scene.add(hill);
  }
}

export function demo(THREE, sky, harness) {
  const options = {
    zenithColor: [0.05, 0.12, 0.35], horizonColor: [0.95, 0.55, 0.3], groundColor: [0.08, 0.07, 0.08],
    skyExponent: 0.55, sunDirection: sky.sunDirectionFromAngles(6, -18), sunColor: [1, 0.75, 0.45],
    sunAngularRadius: 2.2, sunEdgeSoftness: 0.8, sunIntensity: 6, haloSharpness: 24, haloStrength: 0.6,
  };
  // 1. The sky on the GPU for every direction of an equirectangular grid equals the CPU mirror. The GPU writes the
  // direction it used to a second float target, so both sides evaluate the same direction.
  const probeOptions = {...options, sunAngularRadius: 8, sunEdgeSoftness: 3, sunIntensity: 4, haloSharpness: 16};
  const body = (output) => `${UNIFORMS}varying vec2 vUv;\n${sky.SKY_DOME_GLSL}
void main() {
  float longitude = (vUv.x - 0.5) * 6.283185307179586;
  float latitude = (vUv.y - 0.5) * 3.141592653589793;
  vec3 direction = vec3(cos(latitude) * sin(longitude), sin(latitude), -cos(latitude) * cos(longitude));
  ${output}
}`;
  const run = (fragmentShader) => {
    const material = new THREE.ShaderMaterial({
      uniforms: sky.createSkyDomeMaterial(THREE, probeOptions).uniforms,
      vertexShader: 'varying vec2 vUv;\nvoid main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
      fragmentShader,
    });
    const quad = harness.fullscreen(material);
    return harness.renderToTarget(quad.scene, quad.camera, harness.floatTarget(64, 32));
  };
  const directions = run(body('gl_FragColor = vec4(direction, 1.0);'));
  const colours = run(body(`gl_FragColor = vec4(skyGradient(direction, uZenithColor, uHorizonColor, uGroundColor, uShape)
    + skySun(direction, uSunDirection, uSunColor, uSunDisc, uHaloStrength), 1.0);`));
  let worst = 0;
  for (let index = 0; index < 64 * 32; index += 1) {
    const direction = [directions[index * 4], directions[index * 4 + 1], directions[index * 4 + 2]];
    const expected = sky.skyColor(direction, probeOptions);
    for (let k = 0; k < 3; k += 1) {
      worst = Math.max(worst, Math.abs(colours[index * 4 + k] - expected[k]) / Math.max(1, Math.abs(expected[k])));
    }
  }
  harness.check('gpu_sky_matches_cpu_mirror', worst < 1e-4, {directions: 64 * 32, worst_relative_difference: worst});

  // 2. The evening scene and its flat-colour baseline.
  const dome = new THREE.SphereGeometry(45, 64, 32);
  const scene = new THREE.Scene();
  scene.add(new THREE.Mesh(dome, sky.createSkyDomeMaterial(THREE, options)));
  hills(THREE, scene);
  const baseline = new THREE.Scene();
  baseline.add(new THREE.Mesh(dome, new THREE.MeshBasicMaterial({color: new THREE.Color(0.95, 0.55, 0.3), side: THREE.BackSide})));
  hills(THREE, baseline);
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 200);
  camera.position.set(0, 1.2, 4);
  camera.lookAt(-4, 6.5, -30);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
