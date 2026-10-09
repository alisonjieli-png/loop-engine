// Demo of the heightfield terrain, rendered by the family verifier and usable as an example: a 97 x 97 procedural
// height grid built into a closed diorama block (skirts and a bottom), coloured by height. The baseline is a flat slab
// with the same footprint. The checks drop three.js rays onto the mesh and compare the hits with sampleSurfaceHeight.

function heightsOf(width, depth) {
  const heights = new Float32Array(width * depth);
  for (let j = 0; j < depth; j += 1) {
    for (let i = 0; i < width; i += 1) {
      const x = i / (width - 1);
      const z = j / (depth - 1);
      const peak = 0.55 * Math.exp(-((x - 0.62) ** 2 + (z - 0.38) ** 2) * 16);
      const ridges = 0.22 * Math.sin(3.1 * x + 1.2) * Math.cos(2.3 * z) + 0.1 * Math.sin(9.1 * x * z + 0.4);
      const detail = 0.035 * Math.cos(23 * x - 17 * z) + 0.025 * Math.sin(31 * z + 7 * x);
      heights[j * width + i] = peak + ridges + detail;
    }
  }
  return heights;
}

function colourOf(t) {
  const stops = [[0, [0.05, 0.16, 0.24]], [0.22, [0.32, 0.42, 0.14]], [0.55, [0.2, 0.3, 0.1]], [0.75, [0.32, 0.27, 0.22]],
    [0.9, [0.85, 0.86, 0.9]], [1, [0.95, 0.96, 1]]];
  for (let k = 1; k < stops.length; k += 1) {
    if (t <= stops[k][0]) {
      const f = (t - stops[k - 1][0]) / (stops[k][0] - stops[k - 1][0]);
      return stops[k - 1][1].map((value, c) => value + (stops[k][1][c] - value) * f);
    }
  }
  return stops[stops.length - 1][1];
}

export function demo(THREE, terrain, harness) {
  const width = 97;
  const depth = 97;
  const size = 2.6;
  const cellSize = size / (width - 1);
  const heightScale = 0.9;
  const heights = heightsOf(width, depth);
  const geometry = terrain.createHeightfieldTerrainGeometry(THREE, heights, width, depth, {cellSize, heightScale,
    skirt: true, closeBottom: true, skirtBase: -0.45});
  const position = geometry.getAttribute('position');
  const top = width * depth;
  let low = Infinity;
  let high = -Infinity;
  for (let v = 0; v < top; v += 1) {
    low = Math.min(low, position.getY(v));
    high = Math.max(high, position.getY(v));
  }
  const colours = new Float32Array(position.count * 3);
  for (let v = 0; v < position.count; v += 1) {
    colours.set(v < top ? colourOf((position.getY(v) - low) / (high - low)) : [0.18, 0.11, 0.07], v * 3);
  }
  geometry.setAttribute('color', new THREE.BufferAttribute(colours, 3));
  const block = new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({vertexColors: true, roughness: 0.92}));
  block.updateMatrixWorld();

  // Rays from above land where sampleSurfaceHeight says the surface is.
  const raycaster = new THREE.Raycaster();
  let worst = 0;
  for (const [x, z] of [[0.31, -0.42], [-0.9, 0.77], [1.1, 1.05], [-1.2, -1.21], [0.02, 0.03], [0.55, -0.6]]) {
    raycaster.set(new THREE.Vector3(x, 10, z), new THREE.Vector3(0, -1, 0));
    const hit = raycaster.intersectObject(block)[0];
    const expected = heightScale * terrain.sampleSurfaceHeight(heights, width, depth, (x + size / 2) / cellSize,
      (z + size / 2) / cellSize);
    worst = Math.max(worst, hit ? Math.abs(hit.point.y - expected) : Infinity);
  }
  harness.check('raycast_hits_match_sampleSurfaceHeight', worst < 1e-4, {rays: 6, worst_difference: worst});

  // Central-difference normals agree with the face normals three.js averages over the top surface.
  const averaged = geometry.clone();
  averaged.computeVertexNormals();
  const ours = geometry.getAttribute('normal');
  const theirs = averaged.getAttribute('normal');
  let sum = 0;
  for (let v = 0; v < top; v += 1) {
    sum += ours.getX(v) * theirs.getX(v) + ours.getY(v) * theirs.getY(v) + ours.getZ(v) * theirs.getZ(v);
  }
  harness.check('normals_match_three_vertex_normals', sum / top > 0.995, {mean_dot: sum / top});

  const background = new THREE.Color(0x232833);
  const scene = new THREE.Scene();
  const baseline = new THREE.Scene();
  scene.background = background;
  baseline.background = background;
  for (const target of [scene, baseline]) {
    const sun = new THREE.DirectionalLight(0xfff2e0, 2.6);
    sun.position.set(-3, 4, 2);
    target.add(sun, new THREE.HemisphereLight(0xbcd2ff, 0x3a2c22, 0.9));
  }
  scene.add(block);
  const slab = new THREE.Mesh(new THREE.BoxGeometry(size, 0.6, size), new THREE.MeshStandardMaterial({color: 0x5a6b3a}));
  slab.position.y = -0.15;
  baseline.add(slab);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 50);
  camera.position.set(2.9, 2.5, 3.7);
  camera.lookAt(0, -0.12, 0);
  return {scene, camera, baseline: {scene: baseline, camera}};
}
