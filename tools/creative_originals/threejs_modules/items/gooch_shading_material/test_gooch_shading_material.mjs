// Known answers for the Gooch material: the cool-to-warm tone at the lit pole, the dark pole and the terminator, the
// silhouette band, and the material the builder makes (with a minimal stand-in for THREE). Each guard also runs on a
// known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GOOCH_DEFAULTS, GOOCH_FRAGMENT, GOOCH_GLSL, GOOCH_VERTEX, createGoochMaterial, goochColor, goochSilhouette,
} from './gooch_shading_material.mjs';

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

const BASE = [0.75, 0.3, 0.2];
const COOL = [0, 0, 0.55];
const WARM = [0.3, 0.3, 0];
// Computed independently from t = (1 + n.l) / 2, t (warm + beta base) + (1 - t)(cool + alpha base).
const TONE_CASES = [
  [[1, BASE, COOL, WARM, 0.25, 0.5], [0.675, 0.44999999999999996, 0.1]],
  [[-1, BASE, COOL, WARM, 0.25, 0.5], [0.1875, 0.075, 0.6000000000000001]],
  [[0, BASE, COOL, WARM, 0.25, 0.5], [0.43125, 0.26249999999999996, 0.35000000000000003]],
  [[0.6, [0.2, 0.5, 0.8], [0, 0, 0.4], [0.4, 0.4, 0], 0.2, 0.6], [0.42400000000000004, 0.58, 0.496]],
];

function toneProblems(tone) {
  const problems = [];
  for (const [args, expected] of TONE_CASES) {
    const actual = tone(...args);
    expected.forEach((value, k) => {
      if (Math.abs(actual[k] - value) > 1e-12) problems.push(`tone(${args[0]})[${k}] = ${actual[k]}, expected ${value}`);
    });
  }
  return problems;
}

test('goochColor runs from the warm tone facing the light to the cool tone facing away', () => {
  assert.deepEqual(toneProblems(goochColor), []);
});

test('known wrong: plain Lambert darkening toward black is refused', () => {
  const lambert = (nDotL, base) => base.map((value) => value * Math.max(nDotL, 0));
  assert.notDeepEqual(toneProblems(lambert), []);
});

test('goochSilhouette is the outline band and vanishes at width 0', () => {
  assert.equal(goochSilhouette(0, 0.18, 0.06), 1);
  assert.equal(goochSilhouette(0.5, 0.18, 0.06), 0);
  assert.ok(Math.abs(goochSilhouette(0.21, 0.18, 0.06) - 0.5) < 1e-12);
  assert.ok(Math.abs(goochSilhouette(-0.2, 0.18, 0.06) - 0.7407407407407403) < 1e-12, 'the band is symmetric in N.V');
  assert.equal(goochSilhouette(0, 0, 0.06), 0);
});

test('invalid inputs and options are refused', () => {
  assert.throws(() => goochColor(1.5, BASE, COOL, WARM, 0.25, 0.5), RangeError);
  assert.throws(() => goochColor(0, [1, 1], COOL, WARM, 0.25, 0.5), TypeError);
  assert.throws(() => goochSilhouette(0, 2, 0.1), RangeError);
  assert.throws(() => createGoochMaterial(FakeThree, {warm: [1, 1, 0]}), TypeError);
  assert.throws(() => createGoochMaterial(FakeThree, {beta: 3}), RangeError);
  assert.throws(() => createGoochMaterial(FakeThree, {lightDirection: [0, 0, 0]}), TypeError);
});

test('createGoochMaterial wires every uniform', () => {
  const material = createGoochMaterial(FakeThree, {alpha: 0.4, silhouetteWidth: 0, lightDirection: [3, 0, 4]});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uAlpha', 'uBaseColor', 'uBeta', 'uCoolColor', 'uHighlightColor',
    'uHighlightStrength', 'uLightDirection', 'uShininess', 'uSilhouetteColor', 'uSilhouetteSoftness', 'uSilhouetteWidth',
    'uWarmColor']);
  assert.equal(material.uniforms.uAlpha.value, 0.4);
  assert.equal(material.uniforms.uSilhouetteWidth.value, 0);
  assert.equal(material.uniforms.uBeta.value, GOOCH_DEFAULTS.beta);
  const {x, y, z} = material.uniforms.uLightDirection.value;
  assert.deepEqual([x, y, z], [0.6, 0, 0.8]);
  assert.equal(material.vertexShader, GOOCH_VERTEX);
  assert.equal(material.fragmentShader, GOOCH_FRAGMENT);
  assert.ok(GOOCH_FRAGMENT.includes(GOOCH_GLSL));
  for (const name of Object.keys(material.uniforms)) assert.match(GOOCH_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});
