// Known answers for the Gerstner water: one wave in closed form, the default four waves against an independent
// transcription, the analytic normal against a finite-difference normal of the displaced surface, the Jacobian, the
// buoyancy height and the material the builder makes (with a minimal stand-in for THREE). Each guard also runs on a
// known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  GERSTNER_WATER_DEFAULTS, GERSTNER_WATER_FRAGMENT, GERSTNER_WATER_GLSL, GERSTNER_WATER_VERTEX,
  createGerstnerWaterMaterial, gerstnerDisplacement, gerstnerJacobian, gerstnerNormal, gerstnerSurfaceHeight,
  packGerstnerWaves,
} from './gerstner_wave_water_material.mjs';

const FakeThree = {
  DoubleSide: 2,
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

const WAVES = GERSTNER_WATER_DEFAULTS.waves;
const ONE = [{direction: [1, 0], wavelength: 2 * Math.PI, steepness: 0.5, speed: 0}];

function close(actual, expected, tolerance, label) {
  expected.forEach((value, index) => {
    assert.ok(Math.abs(actual[index] - value) <= tolerance, `${label}[${index}] = ${actual[index]}, expected ${value}`);
  });
}

// The normal of the displaced surface measured with central differences of gerstnerDisplacement.
function measuredNormal(displace, waves, x, z, time) {
  const step = 1e-5;
  const point = (px, pz) => {
    const [dx, dy, dz] = displace(waves, px, pz, time);
    return [px + dx, dy, pz + dz];
  };
  const [a, b, c, d] = [point(x + step, z), point(x - step, z), point(x, z + step), point(x, z - step)];
  const alongX = a.map((value, index) => value - b[index]);
  const alongZ = c.map((value, index) => value - d[index]);
  const normal = [alongZ[1] * alongX[2] - alongZ[2] * alongX[1], alongZ[2] * alongX[0] - alongZ[0] * alongX[2],
    alongZ[0] * alongX[1] - alongZ[1] * alongX[0]];
  const length = Math.hypot(...normal);
  return normal.map((value) => value / length);
}

test('one wave matches the closed form: crest offset, normal and compression', () => {
  close(gerstnerDisplacement(ONE, 0, 0, 0), [0.5, 0, 0], 1e-15, 'offset at phase 0');
  close(gerstnerDisplacement(ONE, Math.PI / 2, 0, 0), [0, 0.5, 0], 1e-15, 'offset at phase pi/2');
  close(gerstnerNormal(ONE, 0, 0, 0), [-0.4472135954999579, 0.8944271909999159, 0], 1e-15, 'normal at phase 0');
  assert.ok(Math.abs(gerstnerJacobian(ONE, Math.PI / 2, 0, 0) - 0.5) < 1e-15);
  assert.equal(gerstnerJacobian(ONE, 0, 0, 0), 1);
});

test('the default waves match an independent transcription', () => {
  close(gerstnerDisplacement(WAVES, 1.3, -2.1, 0.7), [0.17192476501060874, -0.03931240794780899, 0.10946818257660718],
    1e-12, 'offset');
  close(gerstnerNormal(WAVES, 1.3, -2.1, 0.7), [-0.153681959838469, 0.9765956011103947, -0.15047553658995208], 1e-12, 'normal');
  assert.ok(Math.abs(gerstnerJacobian(WAVES, 1.3, -2.1, 0.7) - 1.0181263301931882) < 1e-12);
  assert.ok(Math.abs(packGerstnerWaves(WAVES).maxHeight - 0.37783383490015954) < 1e-12);
});

test('the analytic normal equals the finite-difference normal of the displaced surface', () => {
  for (const [x, z, time] of [[0.4, 0.9, 0], [-3.2, 1.7, 2.5], [6.1, -4.4, 11.3]]) {
    close(gerstnerNormal(WAVES, x, z, time), measuredNormal(gerstnerDisplacement, WAVES, x, z, time), 1e-6, `normal at ${x}, ${z}`);
  }
});

test('known wrong: a perturbed wave surface is refused by the normal comparison', () => {
  const wrong = (waves, x, z, time) => {
    const [dx, dy, dz] = gerstnerDisplacement(waves, x, z, time);
    const [cx] = gerstnerDisplacement(waves, x + 0.37, z, time);
    return [dx, dy + 0.3 * cx, dz];
  };
  const measured = measuredNormal(wrong, WAVES, 0.4, 0.9, 0);
  const analytic = gerstnerNormal(WAVES, 0.4, 0.9, 0);
  assert.ok(measured.some((value, index) => Math.abs(value - analytic[index]) > 1e-3));
});

test('gerstnerSurfaceHeight finds the rest point whose displaced position lands on the query', () => {
  const found = gerstnerSurfaceHeight(WAVES, 0.5, 0.25, 1.1);
  assert.ok(Math.abs(found.height - -0.31325766490711965) < 1e-9);
  assert.ok(found.residual < 1e-5);
  const deep = gerstnerSurfaceHeight(WAVES, 0.5, 0.25, 1.1, 40);
  assert.ok(deep.residual < 1e-10 && Math.abs(deep.height - -0.31325753040460996) < 1e-9);
});

test('invalid waves and options are refused', () => {
  assert.throws(() => packGerstnerWaves([]), RangeError);
  assert.throws(() => packGerstnerWaves([...WAVES, WAVES[0]]), RangeError);
  assert.throws(() => packGerstnerWaves([{direction: [0, 0], wavelength: 2, steepness: 0.1, speed: 1}]), RangeError);
  assert.throws(() => packGerstnerWaves([{direction: [1, 0], wavelength: 2, steepness: 0.6, speed: 1},
    {direction: [0, 1], wavelength: 3, steepness: 0.6, speed: 1}]), RangeError);
  assert.throws(() => packGerstnerWaves([{direction: [1, 0], wavelength: 2, steepness: 0.1, speed: 1, height: 3}]), TypeError);
  assert.throws(() => gerstnerDisplacement(WAVES, Number.NaN, 0, 0), TypeError);
  assert.throws(() => createGerstnerWaterMaterial(FakeThree, {wave: []}), TypeError);
  assert.throws(() => createGerstnerWaterMaterial(FakeThree, {foamSoftness: 0}), RangeError);
});

test('createGerstnerWaterMaterial packs the waves into the uniforms', () => {
  const material = createGerstnerWaterMaterial(FakeThree, {waves: ONE, shininess: 64});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uDeepColor', 'uFoamColor', 'uFoamSoftness', 'uFoamThreshold',
    'uMaxHeight', 'uShallowColor', 'uShininess', 'uSkyColor', 'uSunColor', 'uSunDirection', 'uTime', 'uWaveCount',
    'uWaveSpeeds', 'uWaves']);
  assert.deepEqual(Array.from(material.uniforms.uWaves.value.slice(0, 4)), [1, 0, Math.fround(2 * Math.PI), 0.5]);
  assert.equal(material.uniforms.uWaveCount.value, 1);
  assert.ok(Math.abs(material.uniforms.uMaxHeight.value - 0.5) < 1e-12);
  assert.equal(material.uniforms.uShininess.value, 64);
  assert.equal(material.side, FakeThree.DoubleSide);
  assert.equal(material.vertexShader, GERSTNER_WATER_VERTEX);
  assert.equal(material.fragmentShader, GERSTNER_WATER_FRAGMENT);
  assert.ok(GERSTNER_WATER_VERTEX.includes(GERSTNER_WATER_GLSL) && GERSTNER_WATER_FRAGMENT.includes(GERSTNER_WATER_GLSL));
  const declared = GERSTNER_WATER_VERTEX + GERSTNER_WATER_FRAGMENT;
  for (const name of Object.keys(material.uniforms)) assert.match(declared, new RegExp(`uniform \\w+ ${name}(\\[4\\])?;`));
});
