// Known answers for the separable Gaussian blur: normalized kernels, merged bilinear taps (the pair rule and the
// unpaired last tap), that a merged tap reads exactly its pair under linear interpolation, the CPU line blur with
// clamped ends, the generated GLSL and the shader definition (with a minimal stand-in for THREE). A kernel that
// forgets the doubled side weights is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GAUSSIAN_BLUR_DEFAULTS, GAUSSIAN_BLUR_VERTEX, blurLine, createGaussianBlurMaterial, createGaussianBlurShader,
  gaussianBlurFragment, gaussianWeights, linearSampledTaps,
} from './post_gaussian_blur_separable.mjs';

const close = (actual, expected, tolerance = 1e-12) => {
  assert.equal(actual.length, expected.length);
  actual.forEach((value, index) => assert.ok(Math.abs(value - expected[index]) <= tolerance,
    `[${index}] ${value} != ${expected[index]}`));
};

// Weights computed independently with python3 (exp(-i^2 / (2 sigma^2)), normalized over both sides).
function kernelProblems(weightsOf) {
  const problems = [];
  const cases = [
    [1, 3, [0.39905027965245493, 0.24203622937611435, 0.0540055826224145, 0.004433048175243746]],
    [1, 2, [0.40261994689424746, 0.24420134200323335, 0.054488684549642945]],
  ];
  for (const [sigma, radius, expected] of cases) {
    const actual = weightsOf(sigma, radius);
    if (actual.length !== expected.length || actual.some((value, index) => Math.abs(value - expected[index]) > 1e-12)) {
      problems.push(`sigma ${sigma} radius ${radius} gave ${actual}`);
    }
  }
  return problems;
}

test('gaussianWeights is the normalized one-sided kernel', () => {
  assert.deepEqual(kernelProblems(gaussianWeights), []);
  for (const [sigma, radius] of [[2, 6], [0.5, 0], [4, 12]]) {
    const weights = gaussianWeights(sigma, radius);
    assert.ok(Math.abs(weights[0] + 2 * weights.slice(1).reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
  }
  assert.deepEqual(gaussianWeights(3, 0), [1]);
});

test('known wrong: a kernel normalized over one side only is refused', () => {
  const oneSided = (sigma, radius) => {
    const raw = Array.from({length: radius + 1}, (_, index) => Math.exp(-(index * index) / (2 * sigma * sigma)));
    const total = raw.reduce((sum, value) => sum + value, 0);
    return raw.map((value) => value / total);
  };
  assert.notDeepEqual(kernelProblems(oneSided), []);
});

test('linearSampledTaps merges pairs and keeps an unpaired last tap', () => {
  const sigmaOne = linearSampledTaps(gaussianWeights(1, 3));
  close(sigmaOne.offsets, [0, 1.1824255238063563, 3]);
  close(sigmaOne.weights, [0.39905027965245493, 0.29604181199852886, 0.004433048175243746]);
  const sigmaTwo = linearSampledTaps(gaussianWeights(2, 6));
  close(sigmaTwo.offsets, [0, 1.40733340004593, 3.294214972162989, 5.201813222260378]);
  close(sigmaTwo.weights, [0.1996756274979211, 0.29732251286339895, 0.09184834274140634, 0.01099133064623415]);
  // A merged fetch between texels i and i + 1 reads w_i * a + w_(i+1) * b under linear interpolation.
  const weights = gaussianWeights(2, 6);
  const {offsets, weights: merged} = linearSampledTaps(weights);
  const a = 0.3;
  const b = 0.9;
  const fraction = offsets[1] - 1;
  assert.ok(Math.abs(merged[1] * (a * (1 - fraction) + b * fraction) - (weights[1] * a + weights[2] * b)) < 1e-12);
  assert.throws(() => linearSampledTaps([]), TypeError);
});

test('blurLine is the discrete blur with clamped ends', () => {
  const weights = gaussianWeights(1, 2);
  close(Array.from(blurLine([0, 0, 1, 0, 0], weights)),
    [0.054488684549642945, 0.24420134200323335, 0.40261994689424746, 0.24420134200323335, 0.054488684549642945]);
  close(Array.from(blurLine([1, 0, 0, 0], weights)), [0.7013099734471238, 0.2986900265528763, 0.054488684549642945, 0]);
  close(Array.from(blurLine([0.25, 0.25, 0.25], weights)), [0.25, 0.25, 0.25]);
});

test('the generated fragment stage holds the merged taps', () => {
  const glsl = gaussianBlurFragment(1, 3);
  assert.match(glsl, /const int TAP_COUNT = 3;/);
  assert.match(glsl, /TAP_OFFSETS\[3\] = float\[3\]\(0\.000000000, 1\.182425524, 3\.000000000\)/);
  assert.match(glsl, /uniform vec2 uTexelStep;/);
  assert.match(gaussianBlurFragment(1, 0), /float\[1\]\(1\.000000000\)/);
});

test('createGaussianBlurShader sets the step from direction and resolution', () => {
  const vertical = createGaussianBlurShader({direction: [0, 1], resolution: [640, 480], sigma: 3, radius: 9});
  assert.deepEqual(vertical.uniforms.uTexelStep.value, [0, 1 / 480]);
  assert.equal(vertical.uniforms.tDiffuse.value, null);
  assert.equal(vertical.vertexShader, GAUSSIAN_BLUR_VERTEX);
  assert.equal(vertical.fragmentShader, gaussianBlurFragment(3, 9));
  assert.deepEqual(createGaussianBlurShader().uniforms.uTexelStep.value, [1 / GAUSSIAN_BLUR_DEFAULTS.resolution[0], 0]);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  const material = createGaussianBlurMaterial(FakeThree, {sigma: 1, radius: 3});
  assert.equal(material.fragmentShader, gaussianBlurFragment(1, 3));
  assert.equal(material.depthTest, false);
});

test('known wrong: invalid kernels and options are refused', () => {
  assert.throws(() => gaussianWeights(0, 3), RangeError);
  assert.throws(() => gaussianWeights(2, 40), RangeError);
  assert.throws(() => gaussianWeights(2, 1.5), RangeError);
  assert.throws(() => createGaussianBlurShader({direction: [0, 0]}), TypeError);
  assert.throws(() => createGaussianBlurShader({size: 3}), TypeError);
  assert.throws(() => createGaussianBlurShader({toString: 3}), TypeError, 'an inherited name is not an option');
});
