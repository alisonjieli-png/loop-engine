// Known answers for the Sobel edge pass: gradient magnitudes on a step edge, a single bright pixel and a diagonal
// ramp (clamp-to-edge borders), the soft mask, Rec. 709 luminance, the shader definition and the material (with a
// minimal stand-in for THREE). A Prewitt-weighted gradient is refused by the step-edge answer.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SOBEL_EDGES_DEFAULTS, SOBEL_EDGES_FRAGMENT, SOBEL_EDGES_VERTEX, SOBEL_EDGE_MODES, createSobelEdgesMaterial,
  createSobelEdgesShader, luminance, sobelEdgeMask, sobelMagnitude,
} from './post_sobel_edges.mjs';

const STEP = Float32Array.from([0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1]);
const DOT = Float32Array.from([0, 0, 0, 0, 1, 0, 0, 0, 0]);
const RAMP = Float32Array.from({length: 16}, (_, index) => ((index % 4) + Math.floor(index / 4)) / 6);

// Magnitudes computed independently with the Sobel kernels and clamped borders.
function magnitudeProblems(magnitude) {
  const problems = [];
  const cases = [
    [STEP, 4, 4, [[0, 1, 0], [1, 1, 4], [2, 1, 4], [3, 1, 0]]],
    [DOT, 3, 3, [[0, 0, Math.SQRT2], [0, 1, 2], [1, 1, 0], [1, 0, 2]]],
    [RAMP, 4, 4, [[1, 1, 1.885618083164127], [0, 0, 0.9428090415820634]]],
  ];
  for (const [image, width, height, points] of cases) {
    for (const [x, y, expected] of points) {
      const actual = magnitude(image, width, height, x, y);
      if (Math.abs(actual - expected) > 1e-6) problems.push(`(${x}, ${y}) gave ${actual}, expected ${expected}`);
    }
  }
  return problems;
}

test('sobelMagnitude gives the Sobel gradient with clamped borders', () => {
  assert.deepEqual(magnitudeProblems(sobelMagnitude), []);
});

test('known wrong: a Prewitt gradient (no centre weight) is refused', () => {
  const prewitt = (luma, width, height, x, y) => {
    const at = (dx, dy) => luma[Math.min(Math.max(y + dy, 0), height - 1) * width + Math.min(Math.max(x + dx, 0), width - 1)];
    const gx = (at(1, -1) + at(1, 0) + at(1, 1)) - (at(-1, -1) + at(-1, 0) + at(-1, 1));
    const gy = (at(-1, 1) + at(0, 1) + at(1, 1)) - (at(-1, -1) + at(0, -1) + at(1, -1));
    return Math.hypot(gx, gy);
  };
  assert.notDeepEqual(magnitudeProblems(prewitt), []);
});

test('sobelEdgeMask turns magnitudes into a soft mask', () => {
  assert.deepEqual(Array.from(sobelEdgeMask(STEP, 4, 4).slice(0, 4)), [0, 1, 1, 0]);
  const soft = sobelEdgeMask(Float32Array.from([0, 0.25, 0.25]), 3, 1, {threshold: 0.2, softness: 0.1});
  // A one-row image 0, 0.25, 0.25: the first two pixels see a 0 to 0.25 step (magnitude 4 * 0.25 = 1, fully on);
  // the last sees 0.25 on both sides (magnitude 0).
  assert.deepEqual(Array.from(soft), [1, 1, 0]);
  const partial = sobelEdgeMask(Float32Array.from([0, 0.0625]), 2, 1, {threshold: 0.2, softness: 0.1, opacity: 0.5});
  assert.ok(Math.abs(partial[0] - 0.84375 * 0.5) < 1e-7, `smoothstep(0.1, 0.3, 0.25) * 0.5, got ${partial[0]}`);
  assert.throws(() => sobelEdgeMask(STEP, 3, 3), RangeError);
});

test('luminance uses the Rec. 709 weights', () => {
  assert.ok(Math.abs(luminance(1, 1, 1) - 1) < 1e-12);
  assert.ok(Math.abs(luminance(0.5, 0.25, 1) - 0.3573) < 1e-12);
});

test('createSobelEdgesShader returns a fresh ShaderPass-style definition', () => {
  const shader = createSobelEdgesShader({mode: 'edges', resolution: [800, 400], outlineColor: [1, 0, 0]});
  assert.deepEqual(Object.keys(shader.uniforms).sort(), ['tDiffuse', 'uBackgroundColor', 'uMode', 'uOpacity',
    'uOutlineColor', 'uSoftness', 'uTexelSize', 'uThreshold']);
  assert.equal(shader.uniforms.uMode.value, SOBEL_EDGE_MODES.edges);
  assert.deepEqual(shader.uniforms.uTexelSize.value, [1 / 800, 1 / 400]);
  shader.uniforms.uOutlineColor.value[0] = 0.5;
  assert.deepEqual(createSobelEdgesShader().uniforms.uOutlineColor.value, [...SOBEL_EDGES_DEFAULTS.outlineColor]);
  assert.equal(shader.vertexShader, SOBEL_EDGES_VERTEX);
  assert.equal(shader.fragmentShader, SOBEL_EDGES_FRAGMENT);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  const material = createSobelEdgesMaterial(FakeThree, {threshold: 0.4});
  assert.equal(material.uniforms.uThreshold.value, 0.4);
  assert.equal(material.depthTest, false);
});

test('known wrong: invalid options are refused', () => {
  assert.throws(() => createSobelEdgesShader({mode: 'outline'}), TypeError);
  assert.throws(() => createSobelEdgesShader({mode: 'toString'}), TypeError, 'an inherited name is not a mode');
  assert.throws(() => createSobelEdgesShader({threshold: -1}), RangeError);
  assert.throws(() => createSobelEdgesShader({resolution: [0, 10]}), RangeError);
  assert.throws(() => createSobelEdgesShader({outlineColour: [0, 0, 0]}), TypeError);
  assert.throws(() => createSobelEdgesShader({toString: 1}), TypeError, 'an inherited name is not an option');
});
