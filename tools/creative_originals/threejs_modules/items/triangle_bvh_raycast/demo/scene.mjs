// Demo of the BVH raycaster, rendered by the family verifier and usable as an example: a torus knot with its
// hierarchy's boxes three levels down, and beads where a fan of 1,024 rays from a point to the left hits it, coloured
// by distance. The baseline is the bare knot. In the browser every ray is compared with three.js Raycaster.

export function demo(THREE, bvhModule, harness) {
  const geometry = new THREE.TorusKnotGeometry(1, 0.35, 160, 20);
  const knot = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({color: 0x3d5a80, roughness: 0.45,
    side: THREE.DoubleSide}));
  knot.updateMatrixWorld();
  const bvh = bvhModule.bvhFromGeometry(geometry);
  const summary = bvhModule.describeBVH(bvh);

  const source = new THREE.Vector3(-4.5, 1.8, 3.2);
  const raycaster = new THREE.Raycaster();
  const hits = [];
  let agree = 0;
  let worst = 0;
  let anyAgrees = true;
  const side = 32;
  for (let i = 0; i < side; i += 1) {
    for (let j = 0; j < side; j += 1) {
      const aim = new THREE.Vector3(-1.6 + (3.2 * (i + 0.5)) / side, -1.6 + (3.2 * (j + 0.5)) / side, 0);
      const direction = aim.clone().sub(source).normalize();
      const ours = bvhModule.raycastBVH(bvh, source.toArray(), direction.toArray());
      raycaster.set(source, direction);
      const theirs = raycaster.intersectObject(knot, false)[0] || null;
      if ((ours === null) === (theirs === null)
        && (ours === null || (Math.abs(ours.distance - theirs.distance) < 1e-5
          && (ours.triangle === theirs.faceIndex || Math.abs(ours.distance - theirs.distance) < 1e-9)))) {
        agree += 1;
      }
      if (ours !== null && theirs !== null) worst = Math.max(worst, Math.abs(ours.distance - theirs.distance));
      anyAgrees = anyAgrees && bvhModule.raycastAnyBVH(bvh, source.toArray(), direction.toArray()) === (ours !== null);
      if (ours !== null) hits.push(ours);
    }
  }
  harness.check('closest_hits_equal_three_raycaster', agree === side * side && hits.length > 200,
    {agreeing_rays: agree, rays: side * side, hits: hits.length, largest_distance_difference: worst});
  harness.check('any_hit_agrees_with_closest_hit', anyAgrees, {});
  harness.check('hierarchy_is_balanced', summary.leaves * 2 - 1 === summary.nodes && summary.maximumDepth < 30, summary);

  const beads = new THREE.InstancedMesh(new THREE.SphereGeometry(0.03, 8, 6), new THREE.MeshBasicMaterial(), hits.length);
  const matrix = new THREE.Matrix4();
  const colour = new THREE.Color();
  const near = Math.min(...hits.map((hit) => hit.distance));
  const far = Math.max(...hits.map((hit) => hit.distance));
  hits.forEach((hit, index) => {
    beads.setMatrixAt(index, matrix.makeTranslation(hit.point[0], hit.point[1], hit.point[2]));
    beads.setColorAt(index, colour.setHSL(0.08 + 0.5 * ((hit.distance - near) / Math.max(far - near, 1e-9)), 0.9, 0.6));
  });
  beads.instanceMatrix.needsUpdate = true;
  const boxes = new THREE.Group();
  const stack = [[0, 0]];
  while (stack.length > 0) {
    const [node, depth] = stack.pop();
    if (depth === 3 || bvh.nodeCounts[node] > 0) {
      const b = bvh.nodeBounds.subarray(node * 6, node * 6 + 6);
      const box = new THREE.Box3(new THREE.Vector3(b[0], b[1], b[2]), new THREE.Vector3(b[3], b[4], b[5]));
      boxes.add(new THREE.Box3Helper(box, 0x98c1d9));
      continue;
    }
    stack.push([bvh.nodeOffsets[node], depth + 1], [bvh.nodeOffsets[node] + 1, depth + 1]);
  }

  const build = (withRays) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0e1320);
    scene.add(new THREE.HemisphereLight(0xdfe8ff, 0x1a1a24, 1.2));
    const key = new THREE.DirectionalLight(0xffffff, 2);
    key.position.set(-3, 4, 5);
    scene.add(key);
    scene.add(withRays ? knot : new THREE.Mesh(geometry, knot.material));
    if (withRays) scene.add(beads, boxes);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(-1.2, 1.4, 6.6);
  camera.lookAt(0, 0, 0);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
