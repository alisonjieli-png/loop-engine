// Known answers for the spherical harmonics probe, from closed forms computed independently with Python: the basis
// constants (1 / (2 sqrt pi) and so on); a constant radiance L projects to c0 = 2 sqrt(pi) L with every other
// coefficient near zero and irradiance pi L everywhere; the top light max(y, 0) projects to c0 = sqrt(pi) / 2,
// c(y) = 1.0233267, c(3z^2 - 1) = -0.2477080, c(x^2 - y^2) = -0.4290428, and its band-limited irradiance at +Y is
// 2.0780326 (the exact value is 2 pi / 3). Known-wrong control: a projection without solid-angle weights is refused.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SH_BASIS, SH_COSINE_LOBE, SH_DEFAULTS, evaluateIrradiance, evaluateRadiance, projectEquirect, projectRadiance, shBasis,
  toLightProbe,
} from './spherical_harmonics_probe.mjs';

const TOP_LIGHT = [0.8862269254527579, 1.0233267079464885, 0, 0, 0, 0, -0.24770795610037571, 0, -0.4290427654048917];
const toplit = (direction) => {
  const value = Math.max(direction[1], 0);
  return [value, value, value];
};

function channel(coefficients, index, colour = 0) {
  return coefficients[index * 3 + colour];
}

function projectionProblems(project) {
  const coefficients = project(toplit);
  return TOP_LIGHT.map((expected, index) => [index, channel(coefficients, index) - expected])
    .filter(([, difference]) => Math.abs(difference) > 1e-3).map(([index]) => `coefficient ${index}`);
}

test('the basis constants match their closed forms', () => {
  assert.ok(Math.abs(SH_BASIS[0] - 0.28209479177387814) < 1e-16);
  assert.ok(Math.abs(SH_BASIS[1] - 0.4886025119029199) < 1e-16);
  assert.ok(Math.abs(SH_BASIS[4] - 1.0925484305920792) < 1e-15);
  assert.ok(Math.abs(SH_BASIS[6] - 0.31539156525252005) < 1e-16);
  assert.ok(Math.abs(SH_BASIS[8] - 0.5462742152960396) < 1e-16);
  const up = shBasis([0, 1, 0]);
  assert.deepEqual(up.map((value) => Math.round(value * 1e6) / 1e6), [0.282095, 0.488603, 0, 0, 0, 0, -0.315392, 0, -0.546274]);
  assert.deepEqual(SH_COSINE_LOBE.map((value) => value / Math.PI), [1, 2 / 3, 0.25]);
});

test('constant radiance gives only the band 0 term and irradiance pi L', () => {
  const colour = [1, 0.5, 0.25];
  const coefficients = projectRadiance(() => colour);
  colour.forEach((value, index) => assert.ok(Math.abs(channel(coefficients, 0, index) - 2 * Math.sqrt(Math.PI) * value) < 1e-9));
  for (let index = 1; index < 9; index += 1) assert.ok(Math.abs(channel(coefficients, index)) < 1e-3, `coefficient ${index}`);
  for (const normal of [[0, 1, 0], [1, 0, 0], [0.3, -0.5, 0.8], [0, 0, -1]]) {
    const irradiance = evaluateIrradiance(coefficients, normal);
    colour.forEach((value, index) => assert.ok(Math.abs(irradiance[index] - Math.PI * value) < 2e-3));
  }
  const radiance = evaluateRadiance(coefficients, [0, 0, 1]);
  assert.ok(Math.abs(radiance[0] - 1) < 2e-3, 'a constant is reconstructed');
});

test('a top light projects to its closed-form coefficients and lights the top', () => {
  assert.deepEqual(projectionProblems(projectRadiance), []);
  const coefficients = projectRadiance(toplit, {latitudeSamples: 128, longitudeSamples: 64});
  const up = evaluateIrradiance(coefficients, [0, 1, 0])[0];
  assert.ok(Math.abs(up - 2.0780326406557483) < 2e-3, `irradiance at +Y is ${up}`);
  assert.ok(evaluateIrradiance(coefficients, [0, -1, 0])[0] < 0.05);
  assert.ok(Math.abs(evaluateIrradiance(coefficients, [1, 0, 0])[0] - 0.6626797003665968) < 2e-3);
});

test('known wrong: a projection without solid-angle weights is refused', () => {
  const unweighted = (radiance) => {
    const rows = 64;
    const columns = 128;
    const result = new Float64Array(27);
    for (let row = 0; row < rows; row += 1) {
      const theta = (Math.PI * (row + 0.5)) / rows;
      for (let column = 0; column < columns; column += 1) {
        const phi = ((column + 0.5) / columns - 0.5) * 2 * Math.PI;
        const direction = [Math.sin(theta) * Math.cos(phi), Math.cos(theta), Math.sin(theta) * Math.sin(phi)];
        const basis = shBasis(direction);
        const value = radiance(direction);
        for (let index = 0; index < 9; index += 1) result[index * 3] += value[0] * basis[index] * ((4 * Math.PI) / (rows * columns));
      }
    }
    return result;
  };
  assert.notDeepEqual(projectionProblems(unweighted), []);
});

test('an equirectangular image projects like the function it samples', () => {
  const width = 32;
  const height = 16;
  const constant = new Float32Array(width * height * 3).fill(0.5);
  const fromImage = projectEquirect(constant, width, height, 3);
  const fromFunction = projectRadiance(() => [0.5, 0.5, 0.5], {latitudeSamples: height, longitudeSamples: width});
  fromImage.forEach((value, index) => assert.ok(Math.abs(value - fromFunction[index]) < 1e-12));
  const towardZ = new Float32Array(width * height * 4);
  for (let row = 0; row < height; row += 1) towardZ[(row * width + (width * 3) / 4) * 4] = 1;
  const lobe = projectEquirect(towardZ, width, height);
  assert.ok(channel(lobe, 2) > 0.01, 'u = 0.75 points along +Z');
  assert.ok(Math.abs(channel(lobe, 3)) < 0.2 * channel(lobe, 2), 'and not along X');
});

test('toLightProbe and bad input', () => {
  const calls = [];
  const FakeThree = {
    SphericalHarmonics3: class { fromArray(array) { calls.push(array.length); this.values = array; return this; } },
    LightProbe: class { constructor(sh, intensity) { Object.assign(this, {sh, intensity}); } },
  };
  const probe = toLightProbe(FakeThree, new Float64Array(27).fill(0.25), 2);
  assert.deepEqual([calls[0], probe.intensity, probe.sh.values[26]], [27, 2, 0.25]);
  assert.throws(() => toLightProbe(FakeThree, new Float64Array(9)), TypeError);
  assert.throws(() => projectRadiance(() => [1, 1, 1], {samples: 8}), TypeError);
  assert.throws(() => projectRadiance(() => [1, 1, 1], {toString: 8}), TypeError, 'an inherited name is not an option');
  assert.throws(() => projectRadiance(() => [1, 1, 1], {latitudeSamples: 2}), RangeError);
  assert.throws(() => evaluateIrradiance(new Float64Array(27), [0, 0, 0]), RangeError);
  assert.equal(SH_DEFAULTS.latitudeSamples, 64);
});
