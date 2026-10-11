// Demo of camera framing, rendered by the family verifier and usable as an example: a small still life is framed by
// fitBoxPerspective from a three-quarter view with a 6 percent margin. The baseline is the same scene from a camera
// placed by hand at the origin's front. In the browser the fitted cameras are checked by projecting the corners of
// three.js Box3.setFromObject with Vector3.project.

export function demo(THREE, fitting, harness) {
  const group = new THREE.Group();
  const material = (color, roughness = 0.5) => new THREE.MeshStandardMaterial({color, roughness});
  const table = new THREE.Mesh(new THREE.BoxGeometry(3.2, 0.15, 1.6), material(0x8a5a3c, 0.7));
  table.position.set(0.4, -0.08, -0.6);
  const vase = new THREE.Mesh(new THREE.CylinderGeometry(0.22, 0.32, 0.9, 32), material(0x3f88c5, 0.3));
  vase.position.set(-0.6, 0.45, -0.9);
  const ball = new THREE.Mesh(new THREE.SphereGeometry(0.35, 32, 16), material(0xe94f37, 0.35));
  ball.position.set(0.5, 0.35, -0.3);
  const ring = new THREE.Mesh(new THREE.TorusGeometry(0.3, 0.09, 16, 48), material(0xf2c14e, 0.25));
  ring.position.set(1.4, 0.4, -1);
  ring.rotation.set(0.3, 0.7, 0);
  const spire = new THREE.Mesh(new THREE.ConeGeometry(0.2, 0.7, 24), material(0x44bba4, 0.4));
  spire.position.set(1.65, 0.35, -0.2);
  group.add(table, vase, ball, ring, spire);
  group.position.set(2, 0.5, -3);
  group.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(group);
  const min = box.min.toArray();
  const max = box.max.toArray();

  const margin = 1.06;
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  fitting.applyFit(camera, fitting.fitBoxPerspective(min, max, camera.fov, camera.aspect,
    {direction: [-1, -0.75, -1.2], margin}));
  camera.updateMatrixWorld();
  const corners = [];
  for (let k = 0; k < 8; k += 1) corners.push(new THREE.Vector3(k & 1 ? max[0] : min[0], k & 2 ? max[1] : min[1], k & 4 ? max[2] : min[2]));
  const measure = (cam) => {
    let outermost = 0;
    let depthInside = true;
    for (const corner of corners) {
      const ndc = corner.clone().project(cam);
      outermost = Math.max(outermost, Math.abs(ndc.x), Math.abs(ndc.y));
      depthInside = depthInside && ndc.z >= -1 && ndc.z <= 1;
    }
    return {outermost, depthInside};
  };
  const perspective = measure(camera);
  harness.check('perspective_corners_touch_the_margin', Math.abs(perspective.outermost - 1 / margin) < 1e-6
    && perspective.depthInside, perspective);
  const flat = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  fitting.applyFit(flat, fitting.fitBoxOrthographic(min, max, 1, {direction: [0.4, -1, -0.6], margin}));
  flat.updateMatrixWorld();
  const orthographic = measure(flat);
  harness.check('orthographic_corners_touch_the_margin', Math.abs(orthographic.outermost - 1 / margin) < 1e-6
    && orthographic.depthInside, orthographic);
  const sphere = box.getBoundingSphere(new THREE.Sphere());
  const distance = fitting.fitSphereDistance(sphere.radius, 40, 1);
  harness.check('sphere_distance_is_tangent', Math.abs(Math.asin(sphere.radius / distance) - (20 * Math.PI) / 180) < 1e-12,
    {radius: sphere.radius, distance});

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xeae2d6);
  scene.add(new THREE.HemisphereLight(0xffffff, 0x8c7a66, 1.3));
  const key = new THREE.DirectionalLight(0xfff4e0, 2.4);
  key.position.set(-2, 6, 3);
  scene.add(key, group);
  const handPlaced = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  handPlaced.position.set(0, 1.2, 3);
  handPlaced.lookAt(0, 0.5, 0);
  return {scene, camera, baseline: {scene, camera: handPlaced}};
}
