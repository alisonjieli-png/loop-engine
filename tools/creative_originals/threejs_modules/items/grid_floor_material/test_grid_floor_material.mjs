// Known answers for the grid floor: line coverage on and off the lines, partial pixels, sub-pixel widths, the moire fade,
// axis lines and the distance fade, against values computed independently, plus the material the builder makes (with
// a minimal stand-in for THREE). Each guard also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GRID_FLOOR_DEFAULTS, GRID_FLOOR_FRAGMENT, GRID_FLOOR_GLSL, GRID_FLOOR_VERTEX,
  createGridFloorMaterial, gridAxisCoverage, gridFade, gridLineCoverage,
} from './grid_floor_material.mjs';

const FakeThree = {
  DoubleSide: 2,
  Color: class {
    constructor(r, g, b) {
      this.isColor = true;
      if (g === undefined) Object.assign(this, {source: r});
      else Object.assign(this, {r, g, b});
    }
  },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters, {isShaderMaterial: true}); } },
};

// Computed independently from the distance to the nearest line in pixels and the smoothstep edges.
const LINE_CASES = [
  [[0, 1, 1.5, 0.05], 1],
  [[0.5, 1, 1.5, 0.05], 0],
  [[0.02, 1, 1.5, 0.05], 0.9392499999999997],
  [[-3.98, 1, 1.5, 0.05], 0.9392500000000066],
  [[0, 1, 1, 0.4], 0.3520000000000001],
  [[0, 1, 0.5, 0.05], 0.421875],
  [[10.05, 10, 1.6, 0.05], 0.215999999999971],
  [[-20.02, 10, 1.6, 0.05], 0.9720000000000238],
];

function lineProblems(coverage) {
  const problems = [];
  for (const [args, expected] of LINE_CASES) {
    const actual = coverage(...args);
    if (Math.abs(actual - expected) > 1e-9) problems.push(`coverage(${args}) = ${actual}, expected ${expected}`);
  }
  return problems;
}

test('gridLineCoverage measures line width in pixels and fades dense grids', () => {
  assert.deepEqual(lineProblems(gridLineCoverage), []);
});

test('known wrong: a grid measured in world units instead of pixels is refused', () => {
  const worldUnits = (coordinate, spacing, width) => {
    const cell = coordinate / spacing - 0.5;
    const distance = Math.abs(cell - Math.floor(cell) - 0.5) * spacing;
    return distance < width * 0.5 * 0.05 ? 1 : 0;
  };
  assert.notDeepEqual(lineProblems(worldUnits), []);
});

test('axis lines and the distance fade', () => {
  assert.equal(gridAxisCoverage(0.1, 2, 0.1), 0.5);
  assert.equal(gridAxisCoverage(0.03, 2.2, 0.05), 1);
  assert.equal(gridAxisCoverage(5, 2.2, 0.05), 0);
  assert.equal(gridFade(10, 15, 45), 1);
  assert.equal(gridFade(30, 15, 45), 0.5);
  assert.equal(gridFade(50, 15, 45), 0);
});

test('invalid inputs and options are refused', () => {
  assert.throws(() => gridLineCoverage(0, 0, 1, 0.1), RangeError);
  assert.throws(() => gridLineCoverage(Number.NaN, 1, 1, 0.1), TypeError);
  assert.throws(() => gridAxisCoverage(0, -1, 0.1), RangeError);
  assert.throws(() => createGridFloorMaterial(FakeThree, {spacing: 2}), TypeError);
  assert.throws(() => createGridFloorMaterial(FakeThree, {fadeStart: 50, fadeEnd: 10}), RangeError);
  assert.throws(() => createGridFloorMaterial(FakeThree, {minorLineWidth: 0}), RangeError);
});

test('createGridFloorMaterial is transparent, double-sided and writes no depth', () => {
  const material = createGridFloorMaterial(FakeThree, {majorSpacing: 5, opacity: 0.8});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uAxisLineWidth', 'uFadeEnd', 'uFadeStart', 'uMajorColor',
    'uMajorLineWidth', 'uMajorSpacing', 'uMinorColor', 'uMinorLineWidth', 'uMinorSpacing', 'uOpacity', 'uXAxisColor',
    'uZAxisColor']);
  assert.equal(material.uniforms.uMajorSpacing.value, 5);
  assert.equal(material.uniforms.uOpacity.value, 0.8);
  assert.equal(material.uniforms.uMinorSpacing.value, GRID_FLOOR_DEFAULTS.minorSpacing);
  assert.equal(material.transparent, true);
  assert.equal(material.depthWrite, false);
  assert.equal(material.side, FakeThree.DoubleSide);
  assert.equal(material.vertexShader, GRID_FLOOR_VERTEX);
  assert.equal(material.fragmentShader, GRID_FLOOR_FRAGMENT);
  assert.ok(GRID_FLOOR_FRAGMENT.includes(GRID_FLOOR_GLSL) && GRID_FLOOR_FRAGMENT.includes('fwidth(coordinate)'));
  for (const name of Object.keys(material.uniforms)) assert.match(GRID_FLOOR_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});
