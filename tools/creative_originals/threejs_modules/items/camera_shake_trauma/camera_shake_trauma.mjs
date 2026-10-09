// Trauma-driven camera shake: hits add trauma in [0, 1], trauma decays linearly per second, and the shake is
// trauma raised to an exponent times seeded smooth 1D gradient noise on six channels (three translation axes and
// pitch, yaw, roll). Original Baltor implementation; time is passed in, nothing reads a clock, nothing is imported.

/** Default options of shakeOffsets and CameraShake. Amplitudes are the largest offsets at full trauma. */
export const CAMERA_SHAKE_DEFAULTS = Object.freeze({
  decay: 0.8,
  exponent: 2,
  frequency: 16,
  translation: Object.freeze([0.12, 0.12, 0.04]),
  rotation: Object.freeze([0.05, 0.05, 0.08]),
  seed: 1,
});

const CHANNELS = 6;
const UINT32_RANGE = 4294967296;

function latticeHash(seed, index) {
  let h = (Math.imul(index, 0x27d4eb2d) ^ Math.imul(seed + 0x165667b1, 0x9e3779b1)) >>> 0;
  h = Math.imul(h ^ (h >>> 15), 0x85ebca6b) >>> 0;
  h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0;
  return (h ^ (h >>> 16)) >>> 0;
}

function gradient(seed, index) {
  return (latticeHash(seed, index) / UINT32_RANGE) * 2 - 1;
}

/**
 * Seeded 1D gradient noise in [-1, 1]: a gradient in [-1, 1) at every integer lattice point from an integer hash,
 * blended with the quintic fade 6f^5 - 15f^4 + 10f^3, so it is zero on the lattice, smooth (C2) everywhere and the
 * same for the same seed and x on every platform.
 */
export function shakeNoise(seed, x) {
  if (!Number.isInteger(seed)) throw new TypeError(`seed must be an integer, got ${seed}`);
  if (!Number.isFinite(x)) throw new RangeError(`x must be finite, got ${x}`);
  const index = Math.floor(x);
  const f = x - index;
  const a = gradient(seed, index) * f;
  const b = gradient(seed, index + 1) * (f - 1);
  const fade = f * f * f * (f * (f * 6 - 15) + 10);
  return 2 * (a + (b - a) * fade);
}

function triple(value, name) {
  if (!(Array.isArray(value) && value.length === 3 && value.every((entry) => Number.isFinite(entry) && entry >= 0))) {
    throw new TypeError(`${name} must be three non-negative numbers`);
  }
  return value;
}

function settingsOf(options) {
  if (options === null || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(CAMERA_SHAKE_DEFAULTS, key)) throw new TypeError(`unknown camera shake option ${key}`);
  }
  const settings = {...CAMERA_SHAKE_DEFAULTS, ...options};
  const ranges = {decay: [0, 100], exponent: [0.5, 8], frequency: [0, 200]};
  for (const [key, [low, high]] of Object.entries(ranges)) {
    if (!(typeof settings[key] === 'number' && settings[key] >= low && settings[key] <= high)) {
      throw new RangeError(`${key} must be a number in [${low}, ${high}], got ${settings[key]}`);
    }
  }
  if (!(Number.isInteger(settings.seed) && settings.seed >= 0 && settings.seed < 2 ** 31)) {
    throw new RangeError(`seed must be an integer in [0, 2^31), got ${settings.seed}`);
  }
  triple(settings.translation, 'translation');
  triple(settings.rotation, 'rotation');
  return settings;
}

/** Trauma left after `seconds` of linear decay at `decay` per second, starting from `trauma` (clamped to [0, 1]). */
export function traumaAfter(trauma, seconds, decay = CAMERA_SHAKE_DEFAULTS.decay) {
  if (!(Number.isFinite(trauma) && seconds >= 0 && decay >= 0)) {
    throw new RangeError('trauma must be finite and seconds and decay non-negative');
  }
  return Math.max(0, Math.min(1, trauma) - decay * seconds);
}

/**
 * The shake at `time` (seconds) for a trauma level: {translation: [x, y, z], rotation: [pitch, yaw, roll],
 * intensity}. intensity = clamp(trauma, 0, 1)^exponent; channel k samples the noise with seed 7 * seed + k + 1 at
 * time * frequency + k / 6, so the six channels never all pass through zero together.
 */
export function shakeOffsets(trauma, time, options = {}) {
  const settings = settingsOf(options);
  if (!Number.isFinite(trauma)) throw new RangeError(`trauma must be finite, got ${trauma}`);
  if (!Number.isFinite(time)) throw new RangeError(`time must be finite, got ${time}`);
  const intensity = Math.min(1, Math.max(0, trauma)) ** settings.exponent;
  const values = [];
  for (let channel = 0; channel < CHANNELS; channel += 1) {
    const amplitude = channel < 3 ? settings.translation[channel] : settings.rotation[channel - 3];
    const noise = intensity > 0 ? shakeNoise(7 * settings.seed + channel + 1, time * settings.frequency + channel / 6) : 0;
    values.push(amplitude * intensity * noise);
  }
  return {translation: values.slice(0, 3), rotation: values.slice(3), intensity};
}

function multiply(a, b) {
  return [
    a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1],
    a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0],
    a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3],
    a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2],
  ];
}

function rotate(q, v) {
  const p = multiply(multiply(q, [v[0], v[1], v[2], 0]), [-q[0], -q[1], -q[2], q[3]]);
  return [p[0], p[1], p[2]];
}

function eulerQuaternion(pitch, yaw, roll) {
  const x = [Math.sin(pitch / 2), 0, 0, Math.cos(pitch / 2)];
  const y = [0, Math.sin(yaw / 2), 0, Math.cos(yaw / 2)];
  const z = [0, 0, Math.sin(roll / 2), Math.cos(roll / 2)];
  return multiply(multiply(x, y), z);
}

/**
 * A camera shake with its own trauma and clock. addTrauma(amount) on a hit, update(deltaSeconds) once a frame, then
 * applyTo(camera, basePosition, baseQuaternion): the translation is applied along the camera's own axes and the
 * rotation after the base orientation, so the base pose is never changed by the shake.
 */
export class CameraShake {
  constructor(options = {}) {
    this.settings = settingsOf(options);
    this.trauma = 0;
    this.time = 0;
  }

  addTrauma(amount) {
    if (!(Number.isFinite(amount) && amount >= 0)) throw new RangeError(`amount must be non-negative, got ${amount}`);
    this.trauma = Math.min(1, this.trauma + amount);
    return this.trauma;
  }

  update(deltaSeconds) {
    if (!(Number.isFinite(deltaSeconds) && deltaSeconds >= 0)) throw new RangeError('deltaSeconds must be non-negative');
    this.time += deltaSeconds;
    this.trauma = traumaAfter(this.trauma, deltaSeconds, this.settings.decay);
    return this.trauma;
  }

  sample(time = this.time) {
    return shakeOffsets(this.trauma, time, this.settings);
  }

  /** Pose a camera (any object with position.set and quaternion.set) at the base pose plus the current shake. */
  applyTo(camera, basePosition, baseQuaternion = [0, 0, 0, 1]) {
    const {translation, rotation} = this.sample();
    const offset = rotate(baseQuaternion, translation);
    camera.position.set(basePosition[0] + offset[0], basePosition[1] + offset[1], basePosition[2] + offset[2]);
    const shaken = multiply(baseQuaternion, eulerQuaternion(rotation[0], rotation[1], rotation[2]));
    camera.quaternion.set(shaken[0], shaken[1], shaken[2], shaken[3]);
    return camera;
  }
}
