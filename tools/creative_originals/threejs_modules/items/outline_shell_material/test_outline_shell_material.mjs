// Known answers for the inverted-hull outline: the clip-space offset worked by hand, the property that the offset is
// exactly `width` pixels long and points along the normal's direction in pixels on any drawing buffer, the material
// and the shell the builders make (with a minimal stand-in for THREE). Known-wrong control: an offset that takes the
// direction in clip units instead of pixels fails the direction property on a non-square buffer.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  OUTLINE_FRAGMENT, OUTLINE_GLSL, OUTLINE_SHELL_DEFAULTS, OUTLINE_VERTEX, createOutlineMaterial, createOutlineShell,
  outlineClipOffset, setOutlineResolution,
} from './outline_shell_material.mjs';

const FakeThree = {
  BackSide: 'back-side',
  Color: class { constructor(r, g, b) { Object.assign(this, {r, g, b}); } },
  Vector2: class {
    constructor(x, y) { Object.assign(this, {x, y}); }
    set(x, y) { Object.assign(this, {x, y}); return this; }
  },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } },
  Mesh: class { constructor(geometry, material) { Object.assign(this, {geometry, material}); } },
  InstancedMesh: class { constructor(geometry, material, count) { Object.assign(this, {geometry, material, count}); } },
};

// Problems with an offset function: over seeded random clip positions, normals, widths and non-square buffers, the
// offset measured in pixels (after the perspective divide) must be exactly the width long and parallel to the
// normal measured in pixels (clipNormal.xy times the buffer size).
function pixelProblems(offset) {
  let state = 7;
  const next = () => { state = (Math.imul(state, 1664525) + 1013904223) >>> 0; return state / 4294967296; };
  const problems = [];
  for (let trial = 0; trial < 500; trial += 1) {
    const position = [next() * 2 - 1, next() * 2 - 1, next(), 0.5 + next() * 4];
    const normal = [next() * 2 - 1, next() * 2 - 1, next() * 2 - 1, 0];
    const resolution = [64 + Math.floor(next() * 1900), 64 + Math.floor(next() * 1000)];
    const width = next() * 8;
    const moved = offset(position, normal, width, resolution);
    const dx = ((moved[0] / moved[3] - position[0] / position[3]) * resolution[0]) / 2;
    const dy = ((moved[1] / moved[3] - position[1] / position[3]) * resolution[1]) / 2;
    if (Math.abs(Math.hypot(dx, dy) - width) > 1e-9) problems.push(`trial ${trial}: ${Math.hypot(dx, dy)} px for ${width}`);
    const nx = normal[0] * resolution[0];
    const ny = normal[1] * resolution[1];
    const sine = (dx * ny - dy * nx) / (Math.hypot(dx, dy) * Math.hypot(nx, ny) || 1);
    if (width > 1e-6 && Math.abs(sine) > 1e-9) problems.push(`trial ${trial}: off the pixel normal by ${sine}`);
    if (moved[2] !== position[2] || moved[3] !== position[3]) problems.push(`trial ${trial}: depth changed`);
  }
  return problems.slice(0, 5);
}

test('outlineClipOffset worked by hand', () => {
  assert.deepEqual(outlineClipOffset([0, 0, 0, 2], [1, 0, 0, 0], 2, [200, 100]), [0.04, 0, 0, 2]);
  const diagonal = outlineClipOffset([0, 0, 0.3, 1], [1, 1, 0, 0], 2, [200, 100]);
  const expected = (4 * (2 / Math.sqrt(5))) / 200;
  assert.ok(Math.abs(diagonal[0] - expected) < 1e-15 && Math.abs(diagonal[1] - expected) < 1e-15);
  assert.deepEqual(outlineClipOffset([0.2, 0.1, 0.5, 1], [0, 0, 1, 0], 3, [100, 100]), [0.2, 0.1, 0.5, 1],
    'a normal facing the camera does not move the vertex');
});

test('the offset is exactly the requested number of pixels on any buffer', () => {
  assert.deepEqual(pixelProblems(outlineClipOffset), []);
});

test('known wrong: an offset whose direction is taken in clip units is refused', () => {
  const squareOnly = (position, normal, width, resolution) => {
    const size = Math.hypot(normal[0], normal[1]);
    return [position[0] + (normal[0] / size) * width * 2 / resolution[0] * position[3],
      position[1] + (normal[1] / size) * width * 2 / resolution[1] * position[3], position[2], position[3]];
  };
  assert.notDeepEqual(pixelProblems(squareOnly), []);
});

test('createOutlineMaterial draws back faces with the declared uniforms', () => {
  const material = createOutlineMaterial(FakeThree, {width: 5, color: [1, 0, 1], resolution: [800, 600]});
  assert.equal(material.side, 'back-side');
  assert.equal(material.transparent, false);
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uColor', 'uOpacity', 'uResolution', 'uWidth']);
  assert.equal(material.uniforms.uWidth.value, 5);
  assert.deepEqual([material.uniforms.uResolution.value.x, material.uniforms.uResolution.value.y], [800, 600]);
  assert.equal(material.vertexShader, OUTLINE_VERTEX);
  assert.equal(material.fragmentShader, OUTLINE_FRAGMENT);
  assert.ok(OUTLINE_VERTEX.includes(OUTLINE_GLSL), 'the vertex stage uses the chunk the CPU mirror copies');
  assert.equal(createOutlineMaterial(FakeThree, {opacity: 0.5}).transparent, true);
  assert.equal(OUTLINE_SHELL_DEFAULTS.width, 3);
  setOutlineResolution(material, 1920, 1080);
  assert.deepEqual([material.uniforms.uResolution.value.x, material.uniforms.uResolution.value.y], [1920, 1080]);
});

test('createOutlineShell shares the geometry, follows the mesh and ignores raycasts', () => {
  const children = [];
  const mesh = {isMesh: true, name: 'hero', geometry: {id: 1}, add(child) { children.push(child); }};
  const shell = createOutlineShell(FakeThree, mesh, {width: 2});
  assert.equal(shell.geometry, mesh.geometry);
  assert.deepEqual(children, [shell]);
  assert.equal(shell.name, 'heroOutline');
  assert.equal(shell.raycast(), undefined);
  const crowd = {isMesh: true, isInstancedMesh: true, count: 12, instanceMatrix: {id: 2}, geometry: {}, add() {}};
  const outlines = createOutlineShell(FakeThree, crowd);
  assert.equal(outlines.count, 12);
  assert.equal(outlines.instanceMatrix, crowd.instanceMatrix, 'instances share their matrices');
});

test('invalid options and inputs are refused', () => {
  assert.throws(() => createOutlineMaterial(FakeThree, {thickness: 2}), TypeError);
  assert.throws(() => createOutlineMaterial(FakeThree, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.throws(() => createOutlineMaterial(FakeThree, {width: -1}), RangeError);
  assert.throws(() => createOutlineShell(FakeThree, null), TypeError);
  assert.throws(() => outlineClipOffset([0, 0, 0], [1, 0, 0, 0], 1, [10, 10]), TypeError);
  assert.throws(() => setOutlineResolution({uniforms: {}}, 10, 10), TypeError);
});
