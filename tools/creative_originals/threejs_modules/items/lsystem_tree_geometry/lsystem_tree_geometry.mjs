// L-system trees for three.js: rewrite a string with deterministic or seeded stochastic rules, walk it with a 3D
// turtle, and build the branches as tapered cylinders merged into one mesh with leaf anchor points for foliage.
// Original Baltor implementation; rewriting, the turtle and lsystemTreeData work on strings and typed arrays alone.
//
// Turtle commands: F forward drawing a branch, f forward without drawing, + and - turn left and right, & and ^ pitch
// down and up, backslash and / roll left and right, | turn around, [ and ] push and pop the state, ! taper the radius,
// " shorten the step, L record a leaf anchor. Any other character is a variable for rewriting and draws nothing.

/** Default turtle and mesh options. angle in degrees. */
export const LSYSTEM_TREE_DEFAULTS = Object.freeze({
  angle: 25,
  length: 1,
  lengthScale: 0.8,
  radius: 0.1,
  taper: 0.7,
  segmentTaper: 1,
  radialSegments: 6,
  maxSegments: 200000,
});

const MAXIMUM_ITERATIONS = 64;
const MAXIMUM_RADIAL = 64;
const DEGREES = Math.PI / 180;

// A 32-bit Weyl sequence passed through a multiply-xorshift finalizer: a small, seedable, repeatable generator.
function generator(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x9e3779b9) >>> 0;
    let z = state;
    z = Math.imul(z ^ (z >>> 16), 0x85ebca6b) >>> 0;
    z = Math.imul(z ^ (z >>> 13), 0xc2b2ae35) >>> 0;
    return ((z ^ (z >>> 16)) >>> 0) / 4294967296;
  };
}

function rulesOf(rules) {
  if (!rules || typeof rules !== 'object' || Array.isArray(rules)) throw new TypeError('rules map one character to a successor');
  const table = new Map();
  for (const [symbol, successor] of Object.entries(rules)) {
    if (symbol.length !== 1) throw new TypeError(`rule key ${JSON.stringify(symbol)} must be one character`);
    if (typeof successor === 'string') {
      table.set(symbol, [{successor, weight: 1}]);
      continue;
    }
    if (!Array.isArray(successor) || successor.length === 0) throw new TypeError(`rule ${symbol} needs a string or choices`);
    const choices = successor.map((choice) => {
      if (!choice || typeof choice.successor !== 'string' || !(choice.weight >= 0)) {
        throw new TypeError(`rule ${symbol} choices are {successor, weight} with weight >= 0`);
      }
      return {successor: choice.successor, weight: choice.weight};
    });
    if (!(choices.reduce((sum, choice) => sum + choice.weight, 0) > 0)) throw new RangeError(`rule ${symbol} has no weight`);
    table.set(symbol, choices);
  }
  return table;
}

/**
 * Rewrite the axiom `iterations` times, replacing every symbol at once in each step. A rule is a successor string or a
 * list of {successor, weight} choices picked with the seeded generator, so one seed always grows the same tree.
 * Throws RangeError when the string would grow past maxLength characters.
 */
export function rewriteLSystem(axiom, rules, iterations, seed = 1, maxLength = 1000000) {
  if (typeof axiom !== 'string') throw new TypeError('the axiom is a string');
  if (!Number.isInteger(iterations) || iterations < 0 || iterations > MAXIMUM_ITERATIONS) {
    throw new RangeError(`iterations must be an integer from 0 to ${MAXIMUM_ITERATIONS}`);
  }
  if (!Number.isInteger(seed)) throw new TypeError('seed must be an integer');
  const table = rulesOf(rules);
  const random = generator(seed);
  let current = axiom;
  for (let step = 0; step < iterations; step += 1) {
    const parts = [];
    let size = 0;
    for (const symbol of current) {
      const choices = table.get(symbol);
      let piece = symbol;
      if (choices) {
        piece = choices[0].successor;
        if (choices.length > 1) {
          const total = choices.reduce((sum, choice) => sum + choice.weight, 0);
          let pick = random() * total;
          for (const choice of choices) {
            pick -= choice.weight;
            if (pick < 0) {
              piece = choice.successor;
              break;
            }
          }
        }
      }
      size += piece.length;
      if (size > maxLength) throw new RangeError(`the string grows past ${maxLength} characters at step ${step + 1}`);
      parts.push(piece);
    }
    current = parts.join('');
  }
  return current;
}

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];

function rotate(vector, axis, angle) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return add(add(scale(vector, cosine), scale(cross(axis, vector), sine)), scale(axis, dot(axis, vector) * (1 - cosine)));
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(LSYSTEM_TREE_DEFAULTS, key)) throw new TypeError(`unknown L-system option ${key}`);
  }
  const settings = {...LSYSTEM_TREE_DEFAULTS, ...options};
  const positive = ['length', 'radius', 'lengthScale', 'taper', 'segmentTaper'];
  for (const key of positive) {
    if (!(settings[key] > 0 && Number.isFinite(settings[key]))) throw new RangeError(`${key} must be positive`);
  }
  if (!Number.isFinite(settings.angle)) throw new RangeError('angle must be a finite number of degrees');
  if (!Number.isInteger(settings.radialSegments) || settings.radialSegments < 3 || settings.radialSegments > MAXIMUM_RADIAL) {
    throw new RangeError(`radialSegments must be an integer from 3 to ${MAXIMUM_RADIAL}`);
  }
  if (!Number.isInteger(settings.maxSegments) || settings.maxSegments < 1) throw new RangeError('maxSegments must be a positive integer');
  return settings;
}

/**
 * Walk the commands with a 3D turtle starting at the origin heading +Y (left -X, up +Z). Returns {segments, leaves}:
 * each segment {start, end, startRadius, endRadius, left, up} and each leaf {position, heading}, as plain arrays.
 */
export function interpretTurtle(commands, options = {}) {
  if (typeof commands !== 'string') throw new TypeError('commands is a string');
  const settings = settingsOf(options);
  const turn = settings.angle * DEGREES;
  let state = {position: [0, 0, 0], heading: [0, 1, 0], left: [-1, 0, 0], up: [0, 0, 1], radius: settings.radius,
    length: settings.length};
  const stack = [];
  const segments = [];
  const leaves = [];
  const yaw = (angle) => {
    state.heading = rotate(state.heading, state.up, angle);
    state.left = rotate(state.left, state.up, angle);
  };
  const pitch = (angle) => {
    state.heading = rotate(state.heading, state.left, angle);
    state.up = rotate(state.up, state.left, angle);
  };
  const roll = (angle) => {
    state.left = rotate(state.left, state.heading, angle);
    state.up = rotate(state.up, state.heading, angle);
  };
  for (const symbol of commands) {
    switch (symbol) {
      case 'F': {
        const end = add(state.position, scale(state.heading, state.length));
        const endRadius = state.radius * settings.segmentTaper;
        segments.push({start: state.position, end, startRadius: state.radius, endRadius, left: state.left, up: state.up});
        if (segments.length > settings.maxSegments) throw new RangeError(`more than ${settings.maxSegments} segments`);
        state.position = end;
        state.radius = endRadius;
        break;
      }
      case 'f': state.position = add(state.position, scale(state.heading, state.length)); break;
      case '+': yaw(turn); break;
      case '-': yaw(-turn); break;
      case '&': pitch(turn); break;
      case '^': pitch(-turn); break;
      case '\\': roll(turn); break;
      case '/': roll(-turn); break;
      case '|': yaw(Math.PI); break;
      case '[': stack.push({...state}); break;
      case ']':
        if (stack.length === 0) throw new RangeError('] without a matching [');
        state = stack.pop();
        break;
      case '!': state.radius *= settings.taper; break;
      case '"': state.length *= settings.lengthScale; break;
      case 'L': leaves.push({position: state.position, heading: state.heading}); break;
      default: break;
    }
  }
  return {segments, leaves};
}

/**
 * The tree as typed arrays {positions, normals, uvs, indices, segmentCount, leafPositions, leafDirections}: one open
 * tapered cylinder per F (two rings of radialSegments + 1 vertices, the seam repeated for UVs, normals tilted by the
 * taper), triangles counter-clockwise from outside, u around and v along each branch, and the leaf anchors.
 */
export function lsystemTreeData(commands, options = {}) {
  const settings = settingsOf(options);
  const {segments, leaves} = interpretTurtle(commands, options);
  const columns = settings.radialSegments + 1;
  const vertexCount = segments.length * 2 * columns;
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const indexCount = segments.length * settings.radialSegments * 6;
  const indices = vertexCount > 65535 ? new Uint32Array(indexCount) : new Uint16Array(indexCount);
  const ring = Array.from({length: columns}, (_, j) => {
    const angle = (2 * Math.PI * (j % settings.radialSegments)) / settings.radialSegments;
    return [Math.cos(angle), Math.sin(angle)];
  });
  let vertex = 0;
  let index = 0;
  for (const segment of segments) {
    const axis = [segment.end[0] - segment.start[0], segment.end[1] - segment.start[1], segment.end[2] - segment.start[2]];
    const length = Math.hypot(...axis);
    const heading = scale(axis, 1 / length);
    const slope = (segment.endRadius - segment.startRadius) / length;
    const first = vertex;
    for (const [centre, radius, v] of [[segment.start, segment.startRadius, 0], [segment.end, segment.endRadius, 1]]) {
      for (let j = 0; j < columns; j += 1) {
        const [cosine, sine] = ring[j];
        const radial = add(scale(segment.left, cosine), scale(segment.up, sine));
        const normal = add(radial, scale(heading, -slope));
        const size = Math.hypot(...normal);
        positions.set(add(centre, scale(radial, radius)), vertex * 3);
        normals.set(scale(normal, 1 / size), vertex * 3);
        uvs.set([j / settings.radialSegments, v], vertex * 2);
        vertex += 1;
      }
    }
    for (let j = 0; j < settings.radialSegments; j += 1) {
      const a = first + j;
      const b = a + 1;
      const d = first + columns + j;
      const c = d + 1;
      indices.set([a, b, c, a, c, d], index);
      index += 6;
    }
  }
  const leafPositions = new Float32Array(leaves.length * 3);
  const leafDirections = new Float32Array(leaves.length * 3);
  leaves.forEach((leaf, k) => {
    leafPositions.set(leaf.position, k * 3);
    leafDirections.set(leaf.heading, k * 3);
  });
  return {positions, normals, uvs, indices, segmentCount: segments.length, leafPositions, leafDirections};
}

/**
 * A THREE.BufferGeometry of the branches with position, normal and uv attributes and an index; the leaf anchors are in
 * geometry.userData.leafPositions and geometry.userData.leafDirections.
 */
export function createLsystemTreeGeometry(THREE, commands, options = {}) {
  const data = lsystemTreeData(commands, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.userData.leafPositions = data.leafPositions;
  geometry.userData.leafDirections = data.leafDirections;
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
