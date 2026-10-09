// Demo of the solar position, rendered by the family verifier and usable as an example. A courtyard in Paris on the
// afternoon of the 2024 June solstice is lit by a shadow-casting DirectionalLight placed with sunDirection and
// aimSunLight; the baseline puts the same light straight overhead. A tall post's shadow must fall on the side away
// from the sun: the ground just beyond it, along the shadow, is darker than the same distance toward the sun.

const PARIS = [48.8566, 2.3522];
const WHEN = new Date('2024-06-21T15:30:00Z');

function courtyard(THREE, direction) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x9cc4e8);
  const sun = new THREE.DirectionalLight(0xfff1d6, 3.2);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  Object.assign(sun.shadow.camera, {left: -3.5, right: 3.5, top: 3.5, bottom: -3.5, near: 1, far: 30});
  scene.add(sun, sun.target, new THREE.HemisphereLight(0xcfe3ff, 0x5a4a38, 0.55));
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(9, 9), new THREE.MeshStandardMaterial({color: 0xe6dccb, roughness: 0.9}));
  ground.rotation.x = -Math.PI / 2;
  ground.receiveShadow = true;
  scene.add(ground);
  const stone = new THREE.MeshStandardMaterial({color: 0xb7a58c, roughness: 0.7});
  const post = new THREE.Mesh(new THREE.BoxGeometry(0.28, 1.6, 0.28), stone);
  post.position.y = 0.8;
  const pieces = [post];
  for (const [x, z, height] of [[-1.6, -1.2, 0.9], [1.4, -1.5, 1.3], [-1.3, 1.2, 0.6], [1.5, 1.1, 0.8]]) {
    const block = new THREE.Mesh(new THREE.BoxGeometry(0.55, height, 0.55), stone);
    block.position.set(x, height / 2, z);
    pieces.push(block);
  }
  for (const piece of pieces) {
    piece.castShadow = true;
    piece.receiveShadow = true;
    scene.add(piece);
  }
  return {scene, sun, aim: (toward) => direction.aimSunLight(sun, toward, 12)};
}

export function demo(THREE, solar, harness) {
  harness.renderer.shadowMap.enabled = true;
  harness.renderer.shadowMap.type = THREE.PCFShadowMap;
  const position = solar.solarPosition(WHEN, ...PARIS);
  const toward = solar.sunDirection(WHEN, ...PARIS);
  harness.check('afternoon_sun_in_the_west_above_the_horizon', position.azimuth > 200 && position.azimuth < 300
    && position.elevation > 25 && Math.abs(Math.hypot(...toward) - 1) < 1e-12,
  {azimuth: position.azimuth, elevation: position.elevation});

  const lit = courtyard(THREE, solar);
  lit.aim(toward);
  const offset = lit.sun.position.clone().sub(lit.sun.target.position).normalize();
  harness.check('light_placed_along_the_sun_direction', Math.abs(offset.x - toward[0]) < 1e-6 && Math.abs(offset.y - toward[1]) < 1e-6
    && Math.abs(offset.z - toward[2]) < 1e-6, {placed: offset.toArray()});

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
  camera.position.set(0, 4.6, 5.2);
  camera.lookAt(0, 0.2, 0);
  const pixels = harness.renderToCanvas(lit.scene, camera);
  const shade = (x, z) => {
    const ndc = new THREE.Vector3(x, 0, z).project(camera);
    const px = Math.round((ndc.x * 0.5 + 0.5) * (harness.size - 1));
    const py = Math.round((ndc.y * 0.5 + 0.5) * (harness.size - 1));
    const at = (py * harness.size + px) * 4;
    return pixels[at] + pixels[at + 1] + pixels[at + 2];
  };
  const along = [-toward[0], -toward[2]];
  const length = Math.hypot(...along);
  const away = shade((along[0] / length) * 0.6, (along[1] / length) * 0.6);
  const facing = shade((-along[0] / length) * 0.6, (-along[1] / length) * 0.6);
  harness.check('post_shadow_falls_away_from_the_sun', away + 60 < facing, {shadow_side: away, sun_side: facing});

  const overhead = courtyard(THREE, solar);
  overhead.aim(solar.directionFromAngles(0, 90));
  return {scene: lit.scene, camera, baseline: {scene: overhead.scene, camera}};
}
