// Known answers for the Kuwahara filter: quadrant means and luminance variances on a 3 x 3 image (computed
// independently with python3), the chosen quadrant, a constant image unchanged, a step edge kept exactly, alpha from
// the centre, and the shader definition (with a minimal stand-in for THREE). A box blur and a filter that picks the
// most varied quadrant are refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  KUWAHARA_DEFAULTS, KUWAHARA_FRAGMENT, KUWAHARA_VERTEX, createKuwaharaMaterial, createKuwaharaShader,
  kuwaharaImage, kuwaharaPixel, kuwaharaQuadrants,
} from './post_kuwahara_filter.mjs';

const SMALL = Float64Array.from([
  0.1, 0.2, 0.3, 1, 0.9, 0.1, 0.4, 1, 0.3, 0.3, 0.3, 1,
  0.5, 0.6, 0.1, 1, 0.6, 0.5, 0.4, 0.5, 0.7, 0.7, 0.2, 1,
  0.2, 0.25, 0.3, 1, 0.45, 0.4, 0.35, 1, 0.85, 0.8, 0.9, 1,
]);

function stepImage() {
  const data = new Float32Array(8 * 4 * 4);
  for (let y = 0; y < 4; y += 1) {
    for (let x = 0; x < 8; x += 1) data.set(x < 4 ? [0.2, 0.2, 0.2, 1] : [0.8, 0.8, 0.8, 1], (y * 8 + x) * 4);
  }
  return data;
}

function filterProblems(pixel) {
  const problems = [];
  const chosen = pixel(SMALL, 3, 3, 1, 1, 1);
  [0.4375, 0.4375, 0.2875, 0.5].forEach((expected, channel) => {
    if (Math.abs(chosen[channel] - expected) > 1e-12) problems.push(`3 x 3 channel ${channel} is ${chosen[channel]}`);
  });
  const step = stepImage();
  for (let y = 0; y < 4; y += 1) {
    for (let x = 0; x < 8; x += 1) {
      const value = pixel(step, 8, 4, x, y, 2)[0];
      const expected = x < 4 ? 0.2 : 0.8;
      if (Math.abs(value - expected) > 1e-6) problems.push(`step (${x}, ${y}) is ${value}`);
    }
  }
  return problems;
}

test('kuwaharaQuadrants measures the four quadrants', () => {
  const quadrants = kuwaharaQuadrants(SMALL, 3, 3, 1, 1, 1);
  const expected = [
    [[0.525, 0.35, 0.3], 0.02245203607499996], [[0.625, 0.4, 0.325], 0.024292683399999987],
    [[0.4375, 0.4375, 0.2875], 0.013802674100000023], [[0.65, 0.6, 0.4625], 0.024042565118750026],
  ];
  quadrants.forEach((quadrant, index) => {
    quadrant.mean.forEach((value, channel) => assert.ok(Math.abs(value - expected[index][0][channel]) < 1e-12));
    assert.ok(Math.abs(quadrant.variance - expected[index][1]) < 1e-12, `quadrant ${index} variance`);
  });
});

test('kuwaharaPixel keeps the least varied quadrant and edges stay sharp', () => {
  assert.deepEqual(filterProblems(kuwaharaPixel), []);
  const flat = new Float32Array(5 * 5 * 4).fill(0.375);
  assert.deepEqual(kuwaharaImage(flat, 5, 5, 3), flat);
  assert.deepEqual(Array.from(kuwaharaImage(stepImage(), 8, 4, 2)), Array.from(stepImage()));
});

test('known wrong: a box blur and a most-varied-quadrant filter are refused', () => {
  const boxBlur = (data, width, height, x, y, radius) => {
    const sum = [0, 0, 0];
    let count = 0;
    for (let j = -radius; j <= radius; j += 1) {
      for (let i = -radius; i <= radius; i += 1) {
        const base = (Math.min(Math.max(y + j, 0), height - 1) * width + Math.min(Math.max(x + i, 0), width - 1)) * 4;
        for (let channel = 0; channel < 3; channel += 1) sum[channel] += data[base + channel];
        count += 1;
      }
    }
    return [...sum.map((value) => value / count), data[(y * width + x) * 4 + 3]];
  };
  assert.notDeepEqual(filterProblems(boxBlur), []);
  const mostVaried = (data, width, height, x, y, radius) => {
    const quadrants = kuwaharaQuadrants(data, width, height, x, y, radius);
    const worst = quadrants.reduce((best, quadrant) => (quadrant.variance > best.variance ? quadrant : best));
    return [...worst.mean, data[(y * width + x) * 4 + 3]];
  };
  assert.notDeepEqual(filterProblems(mostVaried), []);
});

test('the shader definition sets the radius and texel size', () => {
  const shader = createKuwaharaShader({radius: 5, resolution: [400, 300]});
  assert.deepEqual(Object.keys(shader.uniforms).sort(), ['tDiffuse', 'uRadius', 'uTexelSize']);
  assert.equal(shader.uniforms.uRadius.value, 5);
  assert.deepEqual(shader.uniforms.uTexelSize.value, [1 / 400, 1 / 300]);
  assert.equal(createKuwaharaShader().uniforms.uRadius.value, KUWAHARA_DEFAULTS.radius);
  assert.equal(shader.vertexShader, KUWAHARA_VERTEX);
  assert.equal(shader.fragmentShader, KUWAHARA_FRAGMENT);
  const FakeThree = {ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); } }};
  assert.equal(createKuwaharaMaterial(FakeThree, {radius: 2}).uniforms.uRadius.value, 2);
});

test('known wrong: invalid radii, images and options are refused', () => {
  assert.throws(() => createKuwaharaShader({radius: 0}), RangeError);
  assert.throws(() => createKuwaharaShader({radius: 7}), RangeError);
  assert.throws(() => kuwaharaPixel(new Float32Array(10), 3, 3, 1, 1, 1), TypeError);
  assert.throws(() => createKuwaharaShader({sectors: 8}), TypeError);
  assert.throws(() => createKuwaharaShader({toString: 8}), TypeError, 'an inherited name is not an option');
});
