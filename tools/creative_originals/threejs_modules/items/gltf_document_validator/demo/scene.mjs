// Demo of the glTF document validator, rendered by the family verifier and usable as an example. three.js's
// GLTFExporter writes a small scene as glTF JSON and as GLB; both must validate with no error, and three damaged
// copies must be refused with the expected codes. Five tiles show the verdicts (green when the validator answered as
// expected); the baseline shows the same stage with grey tiles.

function splitGlb(buffer) {
  const view = new DataView(buffer);
  const jsonLength = view.getUint32(12, true);
  const json = JSON.parse(new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLength)));
  const binStart = 20 + jsonLength + 8;
  return {json, binary: new Uint8Array(buffer, binStart, view.getUint32(20 + jsonLength, true))};
}

function source(THREE) {
  const group = new THREE.Group();
  const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.42, 0.14, 128, 16),
    new THREE.MeshStandardMaterial({color: 0xe0703f, roughness: 0.4}));
  knot.position.set(-0.7, 0.55, 0);
  const holder = new THREE.Group();
  holder.position.set(0.55, 0.35, 0);
  holder.rotation.set(0.2, 0.5, 0);
  const ball = new THREE.Mesh(new THREE.IcosahedronGeometry(0.38, 3), new THREE.MeshStandardMaterial({color: 0x4c8fdf}));
  const cube = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.3, 0.3), new THREE.MeshStandardMaterial({color: 0x9bd46a}));
  cube.position.set(0.55, 0.3, 0.1);
  holder.add(ball, cube);
  group.add(knot, holder);
  return group;
}

function stage(THREE, model, colours) {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1e2430);
  const key = new THREE.DirectionalLight(0xffffff, 2.2);
  key.position.set(2, 4, 3);
  scene.add(key, new THREE.HemisphereLight(0xd6e4ff, 0x30281f, 1.0), model);
  colours.forEach((colour, index) => {
    const tile = new THREE.Mesh(new THREE.BoxGeometry(0.42, 0.26, 0.08), new THREE.MeshStandardMaterial({color: colour, roughness: 0.5}));
    tile.position.set(-1.0 + index * 0.5, -0.55, 0.3);
    scene.add(tile);
  });
  return scene;
}

export function demo(THREE, validator, harness) {
  return build(THREE, validator, harness);
}

async function build(THREE, validator, harness) {
  const {GLTFExporter} = harness.addons;
  const model = source(THREE);
  const exporter = new GLTFExporter();
  const json = await exporter.parseAsync(model, {binary: false});
  const plain = validator.validateGltf(json);
  harness.check('exporter_json_validates', plain.valid && plain.errors.length === 0,
    {errors: plain.errors.slice(0, 5), warnings: plain.warnings.slice(0, 5), counts: plain.counts});
  const container = splitGlb(await exporter.parseAsync(model, {binary: true}));
  const binary = validator.validateGltf(container.json, {buffers: [container.binary]});
  harness.check('exporter_glb_validates_with_its_bin_chunk', binary.valid && binary.errors.length === 0,
    {errors: binary.errors.slice(0, 5), warnings: binary.warnings.slice(0, 5)});

  const damaged = [
    ['index_out_of_range', (doc) => { doc.accessors[0].bufferView = doc.bufferViews.length + 3; }],
    ['node_cycle', (doc) => {
      const root = doc.scenes[doc.scene ?? 0].nodes.find((index) => (doc.nodes[index].children || []).length > 0);
      const child = doc.nodes[root].children[0];
      doc.nodes[child].children = [...(doc.nodes[child].children || []), root];
    }],
    ['accessor_value_outside_bounds', (doc) => {
      doc.accessors[doc.meshes[0].primitives[0].attributes.POSITION].max = [0, 0, 0];
    }],
  ];
  const verdicts = [plain.valid, binary.valid];
  const found = {};
  for (const [code, damage] of damaged) {
    const copy = JSON.parse(JSON.stringify(json));
    damage(copy);
    const result = validator.validateGltf(copy);
    found[code] = result.errors.map((issue) => issue.code).slice(0, 4);
    verdicts.push(!result.valid && result.errors.some((issue) => issue.code === code));
  }
  harness.check('damaged_copies_refused_with_their_codes', verdicts.slice(2).every(Boolean), found);

  const scene = stage(THREE, model, verdicts.map((good) => (good ? 0x3fbf5a : 0xd8403a)));
  const baseline = stage(THREE, source(THREE), verdicts.map(() => 0x8a8f99));
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 50);
  camera.position.set(0, 0.5, 4.3);
  camera.lookAt(0, 0.12, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
