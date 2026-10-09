// Known answers for the terrain splat material: 2D value noise and the four layer weights against values computed
// independently, the weights always summing to 1, and the material the builder makes (with a minimal stand-in for
// THREE). Each guard also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  TERRAIN_SPLAT_DEFAULTS, TERRAIN_SPLAT_FRAGMENT, TERRAIN_SPLAT_GLSL, TERRAIN_SPLAT_VERTEX,
  createTerrainSplatMaterial, splatWeights, valueNoise2,
} from './terrain_splat_material.mjs';

const FakeThree = {
  Color: class {
    constructor(r, g, b) {
      this.isColor = true;
      if (g === undefined) Object.assign(this, {source: r});
      else Object.assign(this, {r, g, b});
    }
  },
  Vector3: class { constructor(x, y, z) { Object.assign(this, {x, y, z}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters, {isShaderMaterial: true}); } },
};

// Computed independently (Python transcription of the same smoothstep bands and normalization).
const WEIGHT_CASES = [
  [[0, 0], [1, 0, 0, 0]],
  [[0.8, 0.1], [0, 1, 0, 0]],
  [[2.5, 0.05], [0, 0, 0, 1]],
  [[0.8, 0.9], [0, 0, 1, 0]],
  [[0.15, 0], [0.5000000000000001, 0.4999999999999999, 0, 0]],
  [[0.8, 0.45], [0, 0.5, 0.5, 0]],
  [[1.6, 0.2, {}, 0.9], [0, 0.01967592592592593, 0, 0.9803240740740741]],
  [[0.5, 0.5, {sandLevel: 0.4, snowLevel: 0.6, band: 0.3}], [0.02392578125000002, 0.04443359375000005, 0.9077148437499999,
    0.023925781250000038]],
];

function weightProblems(weights) {
  const problems = [];
  for (const [args, expected] of WEIGHT_CASES) {
    const actual = weights(...args);
    expected.forEach((value, index) => {
      if (Math.abs(actual[index] - value) > 1e-12) problems.push(`weights(${JSON.stringify(args)})[${index}] = ${actual[index]}`);
    });
  }
  return problems;
}

test('splatWeights gives the expected layers at known heights and slopes', () => {
  assert.deepEqual(weightProblems(splatWeights), []);
});

test('known wrong: weights that are not renormalized after the rock share are refused', () => {
  const unnormalized = (height, slope, settings, noise) => {
    const [sand, grass, rock, snow] = splatWeights(height, slope, settings, noise);
    return [sand / (1 - rock || 1), grass / (1 - rock || 1), rock, snow / (1 - rock || 1)];
  };
  assert.notDeepEqual(weightProblems(unnormalized), []);
});

test('the weights always sum to 1 and never go negative', () => {
  for (let height = -1; height <= 3; height += 0.05) {
    for (let slope = 0; slope <= 1; slope += 0.1) {
      const weights = splatWeights(height, slope, {}, (height * 7.3) % 1);
      assert.ok(Math.abs(weights.reduce((sum, value) => sum + value, 0) - 1) < 1e-12);
      assert.ok(weights.every((value) => value >= 0));
    }
  }
});

test('valueNoise2 matches the independent transcription', () => {
  assert.ok(Math.abs(valueNoise2(0, 0, 0) - 0.021025359630584717) < 1e-12);
  assert.ok(Math.abs(valueNoise2(-2.5, 3.25, 11) - 0.4779092353419401) < 1e-12);
  assert.ok(Math.abs(valueNoise2(7.1, -0.3, 5) - 0.5982011247572298) < 1e-12);
});

test('invalid inputs are refused', () => {
  assert.throws(() => splatWeights(0, 0, {snowline: 2}), TypeError);
  assert.throws(() => splatWeights(Number.NaN, 0), TypeError);
  assert.throws(() => valueNoise2(0, 0, 1.5), RangeError);
  assert.throws(() => valueNoise2(5e6, 0, 0), RangeError);
  assert.throws(() => createTerrainSplatMaterial(FakeThree, {sandLevel: 2, snowLevel: 1}), RangeError);
  assert.throws(() => createTerrainSplatMaterial(FakeThree, {rockSlope: 1.5}), RangeError);
  assert.throws(() => createTerrainSplatMaterial(FakeThree, {grass: [0, 1, 0]}), TypeError);
});

test('createTerrainSplatMaterial wires every uniform', () => {
  const material = createTerrainSplatMaterial(FakeThree, {snowLevel: 3, seed: 4, lightDirection: [0, 0, 5]});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uAmbient', 'uBand', 'uDetail', 'uGrassColor', 'uJitter',
    'uLightDirection', 'uNoiseScale', 'uRockColor', 'uRockSlope', 'uSandColor', 'uSandLevel', 'uSeed', 'uSlopeBand',
    'uSnowColor', 'uSnowLevel']);
  assert.equal(material.uniforms.uSnowLevel.value, 3);
  assert.equal(material.uniforms.uSeed.value, 4);
  assert.equal(material.uniforms.uBand.value, TERRAIN_SPLAT_DEFAULTS.band);
  const {x, y, z} = material.uniforms.uLightDirection.value;
  assert.deepEqual([x, y, z], [0, 0, 1]);
  assert.equal(material.vertexShader, TERRAIN_SPLAT_VERTEX);
  assert.equal(material.fragmentShader, TERRAIN_SPLAT_FRAGMENT);
  assert.ok(TERRAIN_SPLAT_FRAGMENT.includes(TERRAIN_SPLAT_GLSL));
  for (const name of Object.keys(material.uniforms)) assert.match(TERRAIN_SPLAT_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});
