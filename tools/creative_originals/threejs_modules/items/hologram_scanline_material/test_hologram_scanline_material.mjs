// Known answers for the hologram material: the scanline profile, the hashed flicker and the glitch offsets against
// values computed independently, and the material the builder makes (with a minimal stand-in for THREE). Each guard
// also runs on a known-wrong input that it must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  HOLOGRAM_DEFAULTS, HOLOGRAM_FRAGMENT, HOLOGRAM_GLSL, HOLOGRAM_VERTEX,
  createHologramMaterial, glitchOffset, hologramFlicker, scanlineIntensity,
} from './hologram_scanline_material.mjs';

const FakeThree = {
  AdditiveBlending: 2,
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

// Computed independently (Python: the same lowbias32-style hash, cosine profile and band keys).
const FLICKER_CASES = [[[0, 12, 0.25, 3], 0.9180224984884262], [[1.37, 12, 0.25, 3], 0.973895326256752],
  [[5, 7, 0.5, 11], 0.5099281966686249]];
const GLITCH_CASES = [[[0.05, 1.3, 6, 4, 0.12, 0.06, 3], -0.03373312711715698], [[0.05, 0.1, 6, 4, 0.12, 0.06, 3], 0],
  [[0.4, 2.3, 6, 4, 1, 0.1, 3], 0.05667095184326172], [[-0.9, 1.3, 6, 4, 1, 0.1, 3], 0.022477138042449954]];

function hashedProblems(flicker, glitch) {
  const problems = [];
  for (const [args, expected] of FLICKER_CASES) {
    const actual = flicker(...args);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`flicker(${args}) = ${actual}, expected ${expected}`);
  }
  for (const [args, expected] of GLITCH_CASES) {
    const actual = glitch(...args);
    if (Math.abs(actual - expected) > 1e-12) problems.push(`glitch(${args}) = ${actual}, expected ${expected}`);
  }
  return problems;
}

test('scanlineIntensity peaks on a line and vanishes half way between lines', () => {
  assert.equal(scanlineIntensity(0, 0, 30, 0.5, 6), 1);
  assert.ok(scanlineIntensity(1 / 60, 0, 30, 0.5, 6) < 1e-12);
  assert.ok(Math.abs(scanlineIntensity(0.01, 0, 30, 0.5, 1) - 0.34549150281252633) < 1e-12);
  assert.ok(Math.abs(scanlineIntensity(0.37, 1.2, 12, 0.5, 4) - 0.34773545902138037) < 1e-12);
  assert.ok(Math.abs(scanlineIntensity(0.25, 2, 4, 0.5, 3) - scanlineIntensity(0, 0, 4, 0.5, 3)) < 1e-12,
    'after 2 s at speed 0.5 the lines moved up by one quarter unit (one line at density 4)');
});

test('flicker and glitch match the independent hash transcription', () => {
  assert.deepEqual(hashedProblems(hologramFlicker, glitchOffset), []);
});

test('known wrong: glitch keys built from the band without the offset are refused', () => {
  const shifted = (height, time, bands, rate, chance, strength, seed) =>
    glitchOffset(height + 1 / bands, time, bands, rate, chance, strength, seed);
  const lowered = (time, rate, depth, seed) => hologramFlicker(time, rate, depth, seed + 1);
  assert.notDeepEqual(hashedProblems(lowered, shifted), []);
});

test('the glitch holds still inside a band and a time step, and respects chance and strength', () => {
  assert.equal(glitchOffset(0.4, 2.3, 6, 4, 1, 0.1, 3), glitchOffset(0.45, 2.4, 6, 4, 1, 0.1, 3));
  assert.equal(glitchOffset(0.4, 2.3, 6, 4, 0, 0.1, 3), 0, 'chance 0 never glitches');
  for (let band = -20; band < 20; band += 1) {
    assert.ok(Math.abs(glitchOffset(band / 6 + 0.01, 1.3, 6, 4, 1, 0.1, 9)) <= 0.1);
  }
});

test('invalid inputs are refused', () => {
  assert.throws(() => scanlineIntensity(0, 0, 30, 0.5, 0), RangeError);
  assert.throws(() => hologramFlicker(0, 12, 2, 3), RangeError);
  assert.throws(() => hologramFlicker(0, 12, 0.2, -1), RangeError);
  assert.throws(() => glitchOffset(0, 0, 6, 4, 1.5, 0.1, 3), RangeError);
  assert.throws(() => glitchOffset(Number.NaN, 0, 6, 4, 0.5, 0.1, 3), TypeError);
  assert.throws(() => createHologramMaterial(FakeThree, {scanlines: 10}), TypeError);
  assert.throws(() => createHologramMaterial(FakeThree, {opacity: 2}), RangeError);
});

test('createHologramMaterial is additive, transparent and double-sided with every uniform', () => {
  const material = createHologramMaterial(FakeThree, {scanDensity: 12, seed: 5});
  assert.deepEqual(Object.keys(material.uniforms).sort(), ['uBaseGlow', 'uColor', 'uFlickerDepth', 'uFlickerRate',
    'uFresnelPower', 'uFresnelStrength', 'uGlitchBands', 'uGlitchChance', 'uGlitchRate', 'uGlitchStrength', 'uOpacity',
    'uScanDensity', 'uScanSharpness', 'uScanSpeed', 'uSeed', 'uTime']);
  assert.equal(material.uniforms.uScanDensity.value, 12);
  assert.equal(material.uniforms.uSeed.value, 5);
  assert.equal(material.uniforms.uGlitchChance.value, HOLOGRAM_DEFAULTS.glitchChance);
  assert.equal(material.blending, FakeThree.AdditiveBlending);
  assert.equal(material.transparent, true);
  assert.equal(material.depthWrite, false);
  assert.equal(material.side, FakeThree.DoubleSide);
  assert.equal(material.vertexShader, HOLOGRAM_VERTEX);
  assert.equal(material.fragmentShader, HOLOGRAM_FRAGMENT);
  assert.ok(HOLOGRAM_VERTEX.includes(HOLOGRAM_GLSL) && HOLOGRAM_FRAGMENT.includes(HOLOGRAM_GLSL));
  const declared = HOLOGRAM_VERTEX + HOLOGRAM_FRAGMENT;
  for (const name of Object.keys(material.uniforms)) assert.match(declared, new RegExp(`uniform \\w+ ${name};`));
});
