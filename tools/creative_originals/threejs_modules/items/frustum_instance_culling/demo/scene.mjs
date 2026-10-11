// Demo of frustum instance culling, rendered by the family verifier and usable as an example. A 15 x 15 field of
// instanced blocks is culled against a second camera (drawn with a CameraHelper): kept blocks are orange, culled ones
// grey. The baseline shows the whole field grey. In the browser the kept set must equal three.js Frustum's verdict.

export function demo(THREE, culling, harness) {
  const spacing = 1.2;
  const side = 15;
  const source = new Float32Array(side * side * 16);
  const matrix = new THREE.Matrix4();
  for (let row = 0; row < side; row += 1) {
    for (let column = 0; column < side; column += 1) {
      const lift = 0.3 + 0.25 * Math.sin(row * 0.7) * Math.cos(column * 0.5);
      matrix.makeTranslation((column - 7) * spacing, lift, (row - 7) * spacing);
      matrix.toArray(source, (row * side + column) * 16);
    }
  }
  const radius = (0.6 * Math.sqrt(3)) / 2;
  const viewer = new THREE.PerspectiveCamera(42, 1.5, 0.5, 9);
  viewer.position.set(-6, 1.4, 5.5);
  viewer.lookAt(2, 0, -3);
  viewer.updateMatrixWorld();
  const viewProjection = new THREE.Matrix4().multiplyMatrices(viewer.projectionMatrix, viewer.matrixWorldInverse);
  const planes = culling.frustumPlanes(viewProjection.elements);
  const kept = new Float32Array(source.length);
  const indices = new Uint32Array(side * side);
  const count = culling.cullInstances(source, radius, planes, kept, {indices});

  // Independent verdict: three.js Frustum on the same spheres, and the same six planes in some order.
  const frustum = new THREE.Frustum().setFromProjectionMatrix(viewProjection);
  const expected = [];
  const centre = new THREE.Vector3();
  for (let instance = 0; instance < side * side; instance += 1) {
    centre.fromArray(source, instance * 16 + 12);
    if (frustum.intersectsSphere(new THREE.Sphere(centre, radius))) expected.push(instance);
  }
  const ours = Array.from(indices.subarray(0, count));
  harness.check('kept_set_equals_three_frustum', JSON.stringify(ours) === JSON.stringify(expected),
    {kept: count, three_kept: expected.length, of: side * side});
  const matched = [];
  for (let plane = 0; plane < 6; plane += 1) {
    const normal = new THREE.Vector3().fromArray(planes, plane * 4);
    matched.push(frustum.planes.some((other) => other.normal.dot(normal) > 1 - 1e-6
      && Math.abs(other.constant - planes[plane * 4 + 3]) < 1e-6));
  }
  harness.check('planes_equal_three_planes', matched.every(Boolean), {matched});
  harness.check('some_culled_some_kept', count > 10 && count < side * side - 10, {kept: count});

  const culled = [];
  const keptSet = new Set(ours);
  for (let instance = 0; instance < side * side; instance += 1) if (!keptSet.has(instance)) culled.push(instance);
  const block = new THREE.BoxGeometry(0.6, 0.6, 0.6);
  const bright = new THREE.InstancedMesh(block, new THREE.MeshStandardMaterial({color: 0xff8c42, roughness: 0.5}), count);
  bright.instanceMatrix.array.set(kept.subarray(0, count * 16));
  bright.instanceMatrix.needsUpdate = true;
  const grey = new THREE.MeshStandardMaterial({color: 0x56607a, roughness: 0.8});
  const dim = new THREE.InstancedMesh(block, grey, culled.length);
  culled.forEach((instance, k) => dim.instanceMatrix.array.set(source.subarray(instance * 16, instance * 16 + 16), k * 16));
  dim.instanceMatrix.needsUpdate = true;
  const everything = new THREE.InstancedMesh(block, grey, side * side);
  everything.instanceMatrix.array.set(source);
  everything.instanceMatrix.needsUpdate = true;

  const build = (withCulling) => {
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x10141f);
    scene.add(new THREE.HemisphereLight(0xdde8ff, 0x202430, 1.4));
    const sun = new THREE.DirectionalLight(0xffffff, 2);
    sun.position.set(4, 9, 6);
    scene.add(sun);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({color: 0x1f2533}));
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);
    if (withCulling) scene.add(bright, dim, new THREE.CameraHelper(viewer));
    else scene.add(everything);
    return scene;
  };
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 80);
  camera.position.set(2.5, 17, 13);
  camera.lookAt(0, 0, -0.5);
  return {scene: build(true), camera, baseline: {scene: build(false), camera}};
}
