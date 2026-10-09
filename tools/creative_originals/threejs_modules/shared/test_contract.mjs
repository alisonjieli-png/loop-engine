// Contract tests shared by every threejs_modules package (Node's built-in test runner, no dependencies).
//
// component.json is the contract card. The module it names must export exactly the declared names, each of the
// declared kind (an exported object constant is frozen). Every example in the contract must give its declared
// result. Every GLSL export must look like one shader stage of its declared kind, and every declared uniform must be
// declared in the module's GLSL with its type. Known-wrong controls show that each comparison refuses a wrong value,
// a missing uniform, an unbalanced shader and an unknown function.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';

const card = JSON.parse(readFileSync(new URL('./component.json', import.meta.url), 'utf8'));
const contract = card.contract;
const moduleUrl = new URL(`./${contract.module}`, import.meta.url).href;
const loaded = await import(moduleUrl);

const TYPED = {Float32Array, Float64Array, Int8Array, Int16Array, Int32Array, Uint8Array, Uint8ClampedArray,
  Uint16Array, Uint32Array};
const CLASS_SOURCE = /^class[\s{]/;
const STAGES = new Set(['vertex', 'fragment', 'chunk']);

function decode(value) {
  if (Array.isArray(value)) return value.map(decode);
  if (value && typeof value === 'object') {
    if (typeof value.$typed === 'string') {
      const Type = TYPED[value.$typed];
      if (!Type) throw new TypeError(`unknown typed array ${value.$typed}`);
      return new Type(value.values);
    }
    return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, decode(entry)]));
  }
  return value;
}

function select(value, path) {
  if (!path) return value;
  let current = value;
  for (const part of path.split('.')) {
    if (current === null || current === undefined) return undefined;
    current = current[part];
  }
  return current;
}

function isListLike(value) {
  return Array.isArray(value) || ArrayBuffer.isView(value);
}

// A description of the first difference, or null when actual matches expected within the tolerance. Objects are
// compared on the keys the expectation lists; lists must have the same length.
function difference(actual, expected, tolerance, where = '$') {
  if (typeof expected === 'number') {
    if (typeof actual !== 'number' && typeof actual !== 'bigint') return `${where}: expected a number, got ${typeof actual}`;
    const value = Number(actual);
    if (Number.isNaN(expected)) return Number.isNaN(value) ? null : `${where}: expected NaN, got ${value}`;
    return Math.abs(value - expected) <= tolerance ? null : `${where}: expected ${expected}, got ${value}`;
  }
  if (Array.isArray(expected)) {
    if (!isListLike(actual)) return `${where}: expected a list`;
    if (actual.length !== expected.length) return `${where}: expected length ${expected.length}, got ${actual.length}`;
    for (let index = 0; index < expected.length; index += 1) {
      const problem = difference(actual[index], expected[index], tolerance, `${where}[${index}]`);
      if (problem) return problem;
    }
    return null;
  }
  if (expected && typeof expected === 'object') {
    if (!actual || typeof actual !== 'object') return `${where}: expected an object`;
    for (const key of Object.keys(expected)) {
      const problem = difference(actual[key], expected[key], tolerance, `${where}.${key}`);
      if (problem) return problem;
    }
    return null;
  }
  return Object.is(actual, expected) ? null : `${where}: expected ${JSON.stringify(expected)}, got ${String(actual)}`;
}

function runExample(example, namespace) {
  const target = namespace[example.call];
  if (typeof target !== 'function') throw new TypeError(`${example.call} is not an exported function`);
  return select(target(...decode(example.args || [])), example.select);
}

function wrongCopy(value) {
  if (typeof value === 'number') return value + 1 + Math.abs(value);
  if (typeof value === 'boolean') return !value;
  if (typeof value === 'string') return `${value}-wrong`;
  if (Array.isArray(value)) return value.length ? [wrongCopy(value[0]), ...value.slice(1)] : [0];
  if (value && typeof value === 'object') {
    const keys = Object.keys(value);
    return keys.length ? {...value, [keys[0]]: wrongCopy(value[keys[0]])} : {wrong: 1};
  }
  return 'wrong';
}

function stripComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/\/\/[^\n]*/g, ' ');
}

function balanced(source) {
  const pairs = {')': '(', ']': '[', '}': '{'};
  const stack = [];
  for (const character of stripComments(source)) {
    if (character === '(' || character === '[' || character === '{') stack.push(character);
    else if (character in pairs && stack.pop() !== pairs[character]) return false;
  }
  return stack.length === 0;
}

function stageProblems(source, stage) {
  const problems = [];
  const code = stripComments(source);
  if (!balanced(source)) problems.push('unbalanced brackets');
  if (/#\s*version\b/.test(code)) problems.push('declares #version (three.js adds it)');
  if (stage === 'vertex' || stage === 'fragment') {
    if (!/\bvoid\s+main\s*\(\s*(?:void\s*)?\)/.test(code)) problems.push('no void main()');
  }
  if (stage === 'vertex' && !/\bgl_Position\s*=/.test(code)) problems.push('never writes gl_Position');
  if (stage === 'fragment' && !/\bgl_FragColor\b|\bpc_fragColor\b|\bout\s+(?:(?:lowp|mediump|highp)\s+)?vec4\b/.test(code)) {
    problems.push('never writes a colour');
  }
  return problems;
}

function declaresUniform(source, name, type) {
  const pattern = new RegExp(`\\buniform\\s+(?:(?:lowp|mediump|highp)\\s+)?${type}\\s+${name}\\s*(?:\\[[^\\]]+\\])?\\s*;`);
  return pattern.test(stripComments(source));
}

function glslSources(namespace) {
  const sources = [];
  for (const row of contract.exports) {
    if (!row.glsl) continue;
    const value = row.kind === 'function' ? namespace[row.name](...decode(row.glsl_args || [])) : namespace[row.name];
    sources.push({name: row.name, stage: row.glsl, source: value});
  }
  return sources;
}

test('exports are exactly the declared names, each of its declared kind', () => {
  const declared = contract.exports.map((row) => row.name).sort();
  assert.deepEqual(Object.keys(loaded).sort(), declared);
  for (const row of contract.exports) {
    const value = loaded[row.name];
    if (row.kind === 'function' || row.kind === 'class') {
      assert.equal(typeof value, 'function', `${row.name} is a ${row.kind}`);
      const isClass = CLASS_SOURCE.test(Function.prototype.toString.call(value));
      assert.equal(isClass, row.kind === 'class', `${row.name} is declared as a ${row.kind}`);
    } else {
      assert.equal(row.kind, 'constant', `${row.name} has a known kind`);
      assert.notEqual(typeof value, 'function', `${row.name} is a constant`);
      if (value !== null && typeof value === 'object') assert.ok(Object.isFrozen(value), `${row.name} is frozen`);
    }
  }
});

test('every contract example gives its declared result', () => {
  const examples = contract.examples || [];
  for (const example of examples) {
    if (example.throws) {
      assert.throws(() => runExample(example, loaded), (error) => error && error.name === example.throws,
        `${example.call} throws ${example.throws}`);
      continue;
    }
    const actual = runExample(example, loaded);
    const problem = difference(actual, example.expect, example.tolerance ?? 0);
    assert.equal(problem, null, `${example.call}(${JSON.stringify(example.args)}): ${problem}`);
  }
});

test('every GLSL export is one well-formed stage and declares the contract uniforms', () => {
  const sources = glslSources(loaded);
  for (const {name, stage, source} of sources) {
    assert.ok(STAGES.has(stage), `${name} has a known stage`);
    assert.equal(typeof source, 'string', `${name} is GLSL text`);
    assert.deepEqual(stageProblems(source, stage), [], name);
  }
  for (const uniform of contract.uniforms || []) {
    assert.ok(sources.some(({source}) => declaresUniform(source, uniform.name, uniform.type)),
      `uniform ${uniform.type} ${uniform.name} is declared in the module's GLSL`);
  }
});

test('known-wrong controls: the comparisons refuse wrong values, shaders and calls', () => {
  assert.notEqual(difference(1.0, 1.1, 1e-6), null);
  assert.notEqual(difference([1, 2], [1, 2, 3], 0), null);
  assert.notEqual(difference({a: 1, b: [2]}, {b: [3]}, 0), null);
  assert.notEqual(difference('a', 'b', 0), null);
  assert.equal(difference(new Float32Array([0.5, 0.25]), [0.5, 0.25], 0), null);
  assert.equal(declaresUniform('uniform float uOther;', 'uBands', 'float'), false);
  assert.equal(declaresUniform('uniform highp vec3 uTint[4];', 'uTint', 'vec3'), true);
  assert.notDeepEqual(stageProblems('void main() { gl_Position = vec4(0.0); ', 'vertex'), []);
  assert.notDeepEqual(stageProblems('#version 300 es\nvoid main() { gl_FragColor = vec4(1.0); }', 'fragment'), []);
  assert.throws(() => runExample({call: 'noSuchExport', args: []}, loaded), TypeError);
  for (const example of contract.examples || []) {
    if (example.throws) continue;
    const actual = runExample(example, loaded);
    assert.notEqual(difference(actual, wrongCopy(example.expect), example.tolerance ?? 0), null,
      `a wrong expectation for ${example.call} is refused`);
  }
});
