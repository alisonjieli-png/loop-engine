// Known answers for the sky dome: the zenith, horizon and ground colours, the sun disc and halo, a direction between,
// the sun angle helper, and the material the builder makes (with a minimal stand-in for THREE). Each guard also runs on
// a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  SKY_DOME_DEFAULTS, SKY_DOME_FRAGMENT, SKY_DOME_GLSL, SKY_DOME_VERTEX, createSkyDomeMaterial, skyColor,
  sunDirectionFromAngles,
} from './gradient_sky_dome_material.mjs';

const FakeThree = {
  BackSide: 1,
  Color: class { constructor(r, g, b) { Object.assign(this, {r, g, b, isColor: true}); } },
  Vector3: class { constructor(x, y, z) { Object.assign(this, {x, y, z}); } },
  Vector4: class { constructor(x, y, z, w) { Object.assign(this, {x, y, z, w}); } },
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters, {isShaderMaterial: true}); } },
};

const POINTED = {sunDirection: [0, 0.3, -1], sunAngularRadius: 5, sunEdgeSoftness: 2, sunIntensity: 3, haloStrength: 0};
// Computed independently (Python transcription of the gradient, horizon blend, disc and halo).
const SKY_CASES = [
  [[[0, 1, 0]], [0.12, 0.3, 0.68]],
  [[[1, 0, 0]], [0.62, 0.74, 0.86]],
  [[[0, -1, 0]], [0.16, 0.15, 0.14]],
  [[[0.35, 0.18, -0.92]], [12.843245810693112, 11.249456313409938, 8.471368491849521]],
  [[[0, 0.3, -1], POINTED], [3.435627387756772, 3.1577521012259595, 2.653625859592438]],
  [[[0.2, 0.5, -0.8], {haloStrength: 0, sunIntensity: 0}], [0.32436705589906856, 0.47984300919118034, 0.7535721401236647]],
];

function skyProblems(sky) {
  const problems = [];
  for (const [args, expected] of SKY_CASES) {
    const actual = sky(...args);
    expected.forEach((value, k) => {
      if (Math.abs(actual[k] - value) > 1e-9) problems.push(`sky(${JSON.stringify(args[0])})[${k}] = ${actual[k]}, expected ${value}`);
    });
  }
  return problems;
}

test('skyColor gives the zenith, horizon, ground, sun and in-between colours', () => {
  assert.deepEqual(skyProblems(skyColor), []);
});

test('known wrong: a gradient by linear elevation without the horizon blend is refused', () => {
  const linear = (direction) => {
    const length = Math.hypot(...direction);
    const y = direction[1] / length;
    const top = SKY_DOME_DEFAULTS.zenithColor;
    const low = SKY_DOME_DEFAULTS.groundColor;
    return [0, 1, 2].map((k) => low[k] + (top[k] - low[k]) * (y + 1) / 2);
  };
  assert.notDeepEqual(skyProblems(linear), []);
});

test('sunDirectionFromAngles points up by elevation and around by azimuth from -Z toward +X', () => {
  const east = sunDirectionFromAngles(30, 90);
  [0.8660254037844387, 0.49999999999999994, 0].forEach((value, k) => assert.ok(Math.abs(east[k] - value) < 1e-12));
  const ahead = sunDirectionFromAngles(0, 0);
  [0, 0, -1].forEach((value, k) => assert.ok(Math.abs(ahead[k] - value) < 1e-12));
  assert.throws(() => sunDirectionFromAngles(120, 0), RangeError);
});

test('invalid options are refused', () => {
  assert.throws(() => skyColor([0, 0, 0]), RangeError);
  assert.throws(() => skyColor([0, 1, 0], {sunSize: 2}), TypeError);
  assert.throws(() => skyColor([0, 1, 0], {sunEdgeSoftness: 0}), RangeError);
  assert.throws(() => createSkyDomeMaterial(FakeThree, {zenithColor: 0x3366aa}), TypeError);
  assert.throws(() => createSkyDomeMaterial(FakeThree, {skyExponent: 0}), RangeError);
});

test('createSkyDomeMaterial renders back faces without depth and packs the disc', () => {
  const material = createSkyDomeMaterial(FakeThree, {sunAngularRadius: 2, sunEdgeSoftness: 1, sunDirection: [0, 0, -3]});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uGroundColor', 'uHaloStrength', 'uHorizonColor', 'uShape',
    'uSunColor', 'uSunDirection', 'uSunDisc', 'uZenithColor']);
  const disc = material.uniforms.uSunDisc.value;
  assert.ok(Math.abs(disc.x - Math.cos((2 * Math.PI) / 180)) < 1e-15 && Math.abs(disc.y - Math.cos((3 * Math.PI) / 180)) < 1e-15);
  assert.equal(disc.z, SKY_DOME_DEFAULTS.sunIntensity);
  const {x, y, z} = material.uniforms.uSunDirection.value;
  assert.deepEqual([x, y, z], [0, 0, -1]);
  assert.equal(material.side, FakeThree.BackSide);
  assert.equal(material.depthWrite, false);
  assert.equal(material.fog, false);
  assert.equal(material.vertexShader, SKY_DOME_VERTEX);
  assert.equal(material.fragmentShader, SKY_DOME_FRAGMENT);
  assert.ok(SKY_DOME_FRAGMENT.includes(SKY_DOME_GLSL));
  for (const name of Object.keys(material.uniforms)) assert.match(SKY_DOME_FRAGMENT, new RegExp(`uniform \\w+ ${name};`));
});
