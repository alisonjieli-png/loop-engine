// Demo of pointer rays and plane dragging, rendered by the family verifier and usable as an example. Two blocks are
// dragged across the floor along simulated pointer paths, one freely and one snapped to a half-unit grid; small
// beads mark each step and wireframes mark where they started. The baseline shows the blocks unmoved. In the browser
// the rays and plane hits are compared with three.js Raycaster.setFromCamera and Ray.intersectPlane.

export function demo(THREE, drag, harness) {
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 80);
  camera.position.set(6, 7.5, 9);
  camera.lookAt(0, 0, 0);
  camera.updateMatrixWorld();
  const rayAt = (cam, x, y) => drag.rayFromCamera(x, y, cam.projectionMatrixInverse.elements, cam.matrixWorld.elements);

  // 1. Rays against three.js for a perspective and an orthographic camera, and plane hits against Ray.intersectPlane.
  const orthographic = new THREE.OrthographicCamera(-4, 4, 4, -4, 0.1, 50);
  orthographic.position.set(2, 8, 6);
  orthographic.lookAt(0, 0, 0);
  orthographic.updateMatrixWorld();
  const raycaster = new THREE.Raycaster();
  const floor = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  const hit = new THREE.Vector3();
  const worst = {direction: 0, origin: 0, hit: 0};
  for (const cam of [camera, orthographic]) {
    for (let i = 0; i < 5; i += 1) {
      for (let j = 0; j < 5; j += 1) {
        const x = -0.9 + 0.45 * i;
        const y = -0.9 + 0.45 * j;
        const ours = rayAt(cam, x, y);
        raycaster.setFromCamera(new THREE.Vector2(x, y), cam);
        const direction = new THREE.Vector3().fromArray(ours.direction);
        worst.direction = Math.max(worst.direction, 1 - direction.dot(raycaster.ray.direction));
        worst.origin = Math.max(worst.origin, raycaster.ray.distanceToPoint(new THREE.Vector3().fromArray(ours.origin)));
        const t = drag.intersectRayPlane(ours.origin, ours.direction, [0, 1, 0], 0);
        if (t !== null && raycaster.ray.intersectPlane(floor, hit)) {
          const point = new THREE.Vector3().fromArray(ours.origin).addScaledVector(direction, t);
          worst.hit = Math.max(worst.hit, point.distanceTo(hit));
        }
      }
    }
  }
  harness.check('rays_match_three_raycaster', worst.direction < 1e-9 && worst.origin < 1e-6, worst);
  harness.check('plane_hits_match_three', worst.hit < 1e-6, {largest_distance: worst.hit});

  // 2. Two drags along pointer paths that start on each block's projected centre.
  const runs = [];
  for (const [start, end, snap, colour] of [[[-3.5, 0.4, 2.5], [0.42, -0.42], 0, 0x2ec4b6],
    [[2.5, 0.4, -2], [-0.6, 0.38], 0.5, 0xff9f1c]]) {
    const controller = new drag.PlaneDrag({snap});
    const from = new THREE.Vector3(...start).project(camera);
    controller.begin(rayAt(camera, from.x, from.y), start);
    const steps = [];
    let last = null;
    for (let k = 1; k <= 24; k += 1) {
      const s = k / 24;
      const x = from.x + (end[0] - from.x) * s + 0.18 * Math.sin(Math.PI * s);
      const y = from.y + (end[1] - from.y) * s - 0.12 * Math.sin(Math.PI * s);
      const ray = rayAt(camera, x, y);
      const position = controller.move(ray);
      if (position) steps.push(position);
      last = ray;
    }
    runs.push({start, steps, snap, colour, last, controller});
  }
  const [free, snapped] = runs;
  const lastHit = free.controller.hit(free.last);
  const final = free.steps[free.steps.length - 1];
  const offsetError = Math.max(...[0, 1, 2].map((axis) => Math.abs(final[axis] - lastHit[axis] - free.controller.offset[axis])));
  harness.check('drag_keeps_grab_offset_and_height', offsetError < 1e-9 && free.steps.every((p) => Math.abs(p[1] - 0.4) < 1e-9),
    {offset_error: offsetError, steps: free.steps.length});
  const offGrid = Math.max(...snapped.steps.map((p) => Math.max(Math.abs(p[0] * 2 - Math.round(p[0] * 2)),
    Math.abs(p[2] * 2 - Math.round(p[2] * 2)))));
  harness.check('snapped_steps_on_half_unit_grid', offGrid < 1e-9 && snapped.steps.length === 24, {largest_error: offGrid});

  const build = (withDrag) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1f2b);
    scene.add(new THREE.HemisphereLight(0xe6eeff, 0x2a2420, 1.5));
    const sun = new THREE.DirectionalLight(0xffffff, 2.2);
    sun.position.set(-3, 8, 5);
    scene.add(sun);
    const ground = new THREE.Mesh(new THREE.PlaneGeometry(14, 14), new THREE.MeshStandardMaterial({color: 0x2b3245}));
    ground.rotation.x = -Math.PI / 2;
    scene.add(ground, new THREE.GridHelper(14, 28, 0x4c5873, 0x39425a));
    for (const run of runs) {
      const block = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.8, 0.8),
        new THREE.MeshStandardMaterial({color: run.colour, roughness: 0.4}));
      block.position.fromArray(withDrag ? run.steps[run.steps.length - 1] : run.start);
      scene.add(block);
      if (!withDrag) continue;
      const ghost = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.8, 0.8),
        new THREE.MeshBasicMaterial({color: run.colour, wireframe: true}));
      ghost.position.fromArray(run.start);
      scene.add(ghost);
      for (const step of run.steps) {
        const bead = new THREE.Mesh(new THREE.SphereGeometry(0.07, 12, 8), new THREE.MeshBasicMaterial({color: run.colour}));
        bead.position.set(step[0], 0.05, step[2]);
        scene.add(bead);
      }
    }
    return scene;
  };
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
