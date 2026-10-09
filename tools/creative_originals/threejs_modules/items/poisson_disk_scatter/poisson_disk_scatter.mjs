// Poisson disk scattering for three.js scenes: blue-noise points in a rectangle where no two points are closer than
// a minimum distance (Bridson's algorithm with a background grid), an optional mask and density thinning, and the
// instance matrices that place a model at every point with seeded yaw and scale jitter. Original Baltor
// implementation; it needs no three.js and returns typed arrays.

/** Default options of poissonDiskPoints. mask(x, y) -> boolean and density(x, y) -> [0, 1] are optional. */
export const POISSON_DISK_DEFAULTS = Object.freeze({
  width: 10,
  height: 10,
  originX: 0,
  originY: 0,
  minDistance: 1,
  attempts: 30,
  seed: 1,
  maxPoints: 100000,
  mask: null,
  density: null,
});

/** Default options of toInstanceMatrices. */
export const INSTANCE_MATRIX_DEFAULTS = Object.freeze({
  plane: 'xz',
  offset: 0,
  scale: 1,
  scaleJitter: 0,
  yawJitter: Math.PI * 2,
  seed: 7,
});

const MAXIMUM_CELLS = 16000000;
const SEED_TRIES = 64;

// A small seeded generator: a Weyl sequence through the 32-bit finalizer of a hash mixer. Uniform in [0, 1).
function createRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x9e3779b9) >>> 0;
    let mixed = state;
    mixed = Math.imul(mixed ^ (mixed >>> 16), 0x85ebca6b);
    mixed = Math.imul(mixed ^ (mixed >>> 13), 0xc2b2ae35);
    mixed ^= mixed >>> 16;
    return (mixed >>> 0) / 4294967296;
  };
}

function strict(options, defaults, name) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(defaults, key)) throw new TypeError(`unknown ${name} option ${key}`);
  }
  return {...defaults, ...options};
}

function positive(value, name) {
  if (!(typeof value === 'number' && value > 0 && Number.isFinite(value))) {
    throw new RangeError(`${name} must be a positive finite number, got ${value}`);
  }
}

/**
 * Points in [originX, originX + width) x [originY, originY + height), no two closer than minDistance, as a
 * Float32Array [x0, y0, x1, y1, ...]. mask(x, y) keeps candidates where it returns a truthy value; when the frontier runs out,
 * random restarts find mask regions the frontier could not reach. density(x, y) then keeps each point with that
 * probability. The same options and seed always give the same points.
 */
export function poissonDiskPoints(options = {}) {
  const settings = strict(options, POISSON_DISK_DEFAULTS, 'Poisson disk');
  positive(settings.width, 'width');
  positive(settings.height, 'height');
  positive(settings.minDistance, 'minDistance');
  for (const key of ['originX', 'originY']) {
    if (!Number.isFinite(settings[key])) throw new RangeError(`${key} must be finite`);
  }
  if (!Number.isInteger(settings.attempts) || settings.attempts < 1 || settings.attempts > 1000) {
    throw new RangeError('attempts must be an integer from 1 to 1000');
  }
  if (!Number.isInteger(settings.maxPoints) || settings.maxPoints < 0) throw new RangeError('maxPoints must be >= 0');
  if (!Number.isInteger(settings.seed)) throw new RangeError('seed must be an integer');
  for (const key of ['mask', 'density']) {
    if (settings[key] !== null && typeof settings[key] !== 'function') throw new TypeError(`${key} must be a function`);
  }
  const {width, height, originX, originY, minDistance, attempts, mask} = settings;
  const cell = minDistance / Math.SQRT2;
  const columns = Math.ceil(width / cell);
  const rows = Math.ceil(height / cell);
  if (columns * rows > MAXIMUM_CELLS) throw new RangeError('the field is too large for this minDistance');
  const grid = new Int32Array(columns * rows).fill(-1);
  const squared = minDistance * minDistance;
  const random = createRandom(settings.seed);
  const xs = [];
  const ys = [];
  const active = [];

  const fits = (x, y) => {
    if (!(x >= 0 && x < width && y >= 0 && y < height)) return false;
    const column = Math.floor(x / cell);
    const row = Math.floor(y / cell);
    for (let j = Math.max(0, row - 2); j <= Math.min(rows - 1, row + 2); j += 1) {
      for (let i = Math.max(0, column - 2); i <= Math.min(columns - 1, column + 2); i += 1) {
        const other = grid[j * columns + i];
        if (other >= 0) {
          const dx = xs[other] - x;
          const dy = ys[other] - y;
          if (dx * dx + dy * dy < squared) return false;
        }
      }
    }
    return mask === null || Boolean(mask(originX + x, originY + y));
  };
  const add = (x, y) => {
    grid[Math.floor(y / cell) * columns + Math.floor(x / cell)] = xs.length;
    active.push(xs.length);
    xs.push(x);
    ys.push(y);
  };
  const reseed = () => {
    for (let k = 0; k < SEED_TRIES * attempts && xs.length < settings.maxPoints; k += 1) {
      const x = random() * width;
      const y = random() * height;
      if (fits(x, y)) {
        add(x, y);
        return true;
      }
    }
    return false;
  };

  while (xs.length < settings.maxPoints && reseed()) {
    while (active.length > 0 && xs.length < settings.maxPoints) {
      const pick = Math.floor(random() * active.length);
      const from = active[pick];
      let placed = false;
      for (let k = 0; k < attempts; k += 1) {
        const angle = random() * Math.PI * 2;
        const radius = minDistance * Math.sqrt(1 + 3 * random());
        const x = xs[from] + radius * Math.cos(angle);
        const y = ys[from] + radius * Math.sin(angle);
        if (fits(x, y)) {
          add(x, y);
          placed = true;
          break;
        }
      }
      if (!placed) {
        active[pick] = active[active.length - 1];
        active.pop();
      }
    }
  }

  const kept = [];
  for (let index = 0; index < xs.length; index += 1) {
    const x = originX + xs[index];
    const y = originY + ys[index];
    if (settings.density !== null) {
      const chance = Math.min(Math.max(Number(settings.density(x, y)) || 0, 0), 1);
      if (!(random() < chance)) continue;
    }
    kept.push(x, y);
  }
  return Float32Array.from(kept);
}

/**
 * Column-major 4 x 4 matrices (Float32Array, 16 per point) that place a model at each 2D point, ready to copy into
 * InstancedMesh.instanceMatrix.array. plane 'xz' puts point (x, y) at (x, offset, y) and spins it about +Y; plane
 * 'xy' puts it at (x, y, offset) and spins it about +Z. Scale is scale * (1 +- scaleJitter), yaw is uniform in
 * [0, yawJitter), both seeded.
 */
export function toInstanceMatrices(points, options = {}) {
  const settings = strict(options, INSTANCE_MATRIX_DEFAULTS, 'instance matrix');
  if (settings.plane !== 'xz' && settings.plane !== 'xy') throw new RangeError("plane must be 'xz' or 'xy'");
  positive(settings.scale, 'scale');
  if (!(settings.scaleJitter >= 0 && settings.scaleJitter < 1)) throw new RangeError('scaleJitter must be in [0, 1)');
  if (!(settings.yawJitter >= 0 && settings.yawJitter <= Math.PI * 2)) throw new RangeError('yawJitter must be in [0, 2 pi]');
  if (!Number.isFinite(settings.offset)) throw new RangeError('offset must be finite');
  if (!Number.isInteger(settings.seed)) throw new RangeError('seed must be an integer');
  if (!(points && points.length % 2 === 0)) throw new RangeError('points must hold x, y pairs');
  const count = points.length / 2;
  const random = createRandom(settings.seed);
  const matrices = new Float32Array(count * 16);
  for (let index = 0; index < count; index += 1) {
    const yaw = random() * settings.yawJitter;
    const size = settings.scale * (1 + settings.scaleJitter * (2 * random() - 1));
    const cosine = Math.cos(yaw) * size;
    const sine = Math.sin(yaw) * size;
    const base = index * 16;
    const x = points[index * 2];
    const y = points[index * 2 + 1];
    if (settings.plane === 'xz') {
      matrices.set([cosine, 0, -sine, 0, 0, size, 0, 0, sine, 0, cosine, 0, x, settings.offset, y, 1], base);
    } else {
      matrices.set([cosine, sine, 0, 0, -sine, cosine, 0, 0, 0, 0, size, 0, x, y, settings.offset, 1], base);
    }
  }
  return matrices;
}
