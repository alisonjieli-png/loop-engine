// Demo of the glTF scene budget report, rendered by the family verifier and usable as an example. three.js's
// GLTFExporter writes a scene with a torus knot, four instances of one sphere, line segments and points; the report
// counts it, GLTFLoader loads it back, and three.js's renderer.info after drawing the loaded scene must agree on
// triangles, lines, points and draw calls. Bars show each budget use (green inside the budget, red over it); the
// baseline is the stage without the model and the bars.

function sourceScene(THREE) {
  const root = new THREE.Group();
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.4, 0.13, 96, 12), new THREE.MeshStandardMaterial({color: 0xe0703f}));
  knot.position.set(-0.6, 0.45, 0);
  root.add(knot);
  const ballGeometry = new THREE.SphereGeometry(0.16, 24, 12);
  const ballMaterial = new THREE.MeshStandardMaterial({color: 0x4c8fdf});
  for (let index = 0; index < 4; index += 1) {
    const ball = new THREE.Mesh(ballGeometry, ballMaterial);
    ball.position.set(0.25 + (index % 2) * 0.42, 0.25 + Math.floor(index / 2) * 0.42, 0);
    root.add(ball);
  }
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(0.5, 0.5, 0.5)),
    new THREE.LineBasicMaterial({color: 0xf2e86d}));
  edges.position.set(1.25, 0.45, 0);
  root.add(edges);
  const positions = new Float32Array(60);
  for (let index = 0; index < 20; index += 1) positions.set([1.0 + (index % 5) * 0.12, 0.05 + Math.floor(index / 5) * 0.1, 0], index * 3);
  const dots = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(positions, 3)),
    new THREE.PointsMaterial({color: 0xffffff, size: 3, sizeAttenuation: false}));
  root.add(dots);
  return root;
}

function stage(THREE) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1d2330);
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(2, 4, 3);
  scene.add(key, new THREE.HemisphereLight(0xd6e4ff, 0x30281f, 1.0));
  return scene;
}

export function demo(THREE, budget, harness) {
  return build(THREE, budget, harness);
}

async function build(THREE, budget, harness) {
  const json = await new harness.addons.GLTFExporter().parseAsync(sourceScene(THREE), {binary: false});
  const report = budget.sceneBudgetReport(json);
  const loaded = await new harness.addons.GLTFLoader().parseAsync(JSON.stringify(json), '');
  loaded.scene.traverse((object) => { object.frustumCulled = false; });

  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
  camera.position.set(0.3, 0.2, 3.6);
  camera.lookAt(0.3, 0.2, 0);
  const counting = new THREE.Scene();
  counting.add(loaded.scene);
  harness.renderToTarget(counting, camera, harness.byteTarget(64, 64));
  const info = harness.renderer.info.render;
  const drawn = {triangles: info.triangles, lines: info.lines, points: info.points, calls: info.calls};
  harness.check('report_matches_renderer_info', drawn.triangles === report.triangles && drawn.lines === report.lines
    && drawn.points === report.points && drawn.calls === report.drawCalls,
  {report: {triangles: report.triangles, lines: report.lines, points: report.points, drawCalls: report.drawCalls}, drawn});
  harness.check('instances_share_one_mesh', report.meshInstances === 7 && (json.meshes || []).length === 4,
    {meshInstances: report.meshInstances, meshes: (json.meshes || []).length});

  const limits = {triangles: 6000, drawCalls: 6, vertices: 4000};
  const violations = budget.checkBudget(report, limits);
  harness.check('budget_violations_listed', violations.length === 1 && violations[0].metric === 'drawCalls',
    {violations});

  const scene = stage(THREE);
  scene.add(loaded.scene);
  Object.entries(limits).forEach(([metric, limit], index) => {
    const height = 0.6 * Math.max(Math.min(report[metric] / limit, 1.6), 0.03);
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.2, height, 0.1),
      new THREE.MeshStandardMaterial({color: report[metric] > limit ? 0xd8403a : 0x3fbf5a, roughness: 0.5}));
    bar.position.set(0.75 + index * 0.3, -0.95 + height / 2, 0.2);
    scene.add(bar);
  });
  const shelf = new THREE.Mesh(new THREE.BoxGeometry(1.0, 0.04, 0.3), new THREE.MeshStandardMaterial({color: 0x59606e}));
  shelf.position.set(1.05, -0.97, 0.2);
  scene.add(shelf);
  const view = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
  view.position.set(0.25, 0.1, 4.2);
  view.lookAt(0.25, -0.1, 0);
  return {scene, camera: view, baseline: {scene: stage(THREE), camera: view}};
}
