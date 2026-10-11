// Demo of the rotation-minimizing tube, rendered by the family verifier and usable as an example: a trefoil knot tube
// with one stripe along its length (rotation-minimizing frames keep the stripe from spinning), a tapered horn and a
// mitred pipe. The baseline draws the knot with three.js TubeGeometry (Frenet frames) and the same texture.

function stripeTexture(THREE) {
  const width = 64;
  const height = 16;
  const data = new Uint8Array(width * height * 4);
  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const stripe = y < 3;
      const tick = x % 16 < 2;
      const colour = stripe ? [250, 214, 92] : tick ? [40, 72, 120] : [58, 110, 178];
      data.set([...colour, 255], (y * width + x) * 4);
    }
  }
  const texture = new THREE.DataTexture(data, width, height);
  texture.wrapS = THREE.RepeatWrapping;
  texture.wrapT = THREE.RepeatWrapping;
  texture.repeat.set(6, 1);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  return texture;
}

export function demo(THREE, tube, harness) {
  const trefoil = Array.from({length: 36}, (_, k) => {
    const t = (2 * Math.PI * k) / 36;
    return [0.3 * (Math.sin(t) + 2 * Math.sin(2 * t)), 0.3 * (Math.cos(t) - 2 * Math.cos(2 * t)), -0.3 * Math.sin(3 * t)];
  });
  const material = new THREE.MeshStandardMaterial({map: stripeTexture(THREE), roughness: 0.42, metalness: 0.05});
  const background = new THREE.Color(0x1b1f28);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(2, 4, 5);
    target.add(key, new THREE.HemisphereLight(0xd0dcff, 0x2a241e, 1.1));
  }
  const samplesPerSegment = 6;
  const knotGeometry = tube.createTubeRmfGeometry(THREE, trefoil, {closed: true, radius: 0.13, radialSegments: 16,
    samplesPerSegment});
  const knot = new THREE.Mesh(knotGeometry, material);
  knot.position.set(-0.05, 0.3, 0);
  scene.add(knot);

  const horn = tube.createTubeRmfGeometry(THREE, [[0, 0, 0], [0.35, 0.25, 0.1], [0.55, 0.65, 0], [0.45, 1.0, -0.1]], {
    radii: [0.03, 0.08, 0.14, 0.22], radialSegments: 20});
  const hornMesh = new THREE.Mesh(horn, new THREE.MeshStandardMaterial({color: 0xd9a441, roughness: 0.3, metalness: 0.5}));
  hornMesh.position.set(0.72, -1.3, 0.3);
  scene.add(hornMesh);
  const pipe = tube.createTubeRmfGeometry(THREE, [[0, 0, 0], [0.5, 0, 0], [0.5, 0.45, 0], [1.0, 0.45, 0.3]], {
    curve: 'polyline', radius: 0.07, radialSegments: 16});
  const pipeMesh = new THREE.Mesh(pipe, new THREE.MeshStandardMaterial({color: 0xc4ced8, roughness: 0.3, metalness: 0.2}));
  pipeMesh.position.set(-1.45, -1.3, 0.3);
  scene.add(pipeMesh);

  // The same centripetal Catmull-Rom spline from three.js passes through the same sample points.
  const curve = new THREE.CatmullRomCurve3(trefoil.map((point) => new THREE.Vector3(...point)), true, 'centripetal');
  const samples = tube.sampleCentripetalCatmullRom(trefoil, samplesPerSegment, true);
  let worst = 0;
  samples.points.forEach((point, i) => {
    const reference = curve.getPoint(i / samples.points.length);
    worst = Math.max(worst, reference.distanceTo(new THREE.Vector3(...point)));
  });
  harness.check('samples_match_three_centripetal_curve', worst < 1e-5, {samples: samples.points.length, worst_distance: worst});
  const frames = tube.rotationMinimizingFrames(samples.points, samples.tangents, {closed: true});
  harness.check('trefoil_twist_found_and_spread', Math.abs(frames.closingAngle) > 1,
    {closing_angle_radians: frames.closingAngle});

  const frenet = new THREE.TubeGeometry(curve, samples.points.length, 0.13, 16, true);
  const plain = new THREE.Mesh(frenet, material);
  plain.position.copy(knot.position);
  baseline.add(plain);

  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 50);
  camera.position.set(0, 0, 4.6);
  camera.lookAt(0, -0.2, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
