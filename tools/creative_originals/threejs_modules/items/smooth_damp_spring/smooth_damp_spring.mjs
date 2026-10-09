// Critically damped springs ("smooth damp") for numbers, vectors and angles. Each step applies the exact solution of
// the spring equation x'' = -w^2 (x - target) - 2 w x' with w = 2 / smoothTime, so a value reaches the same place in
// one long step as in many short ones and never overshoots a target it starts toward from rest. Original Baltor
// implementation; it needs no three.js and works on plain numbers and arrays.

/** Default options of SpringFollower. maxSpeed Infinity means no speed limit. */
export const SMOOTH_DAMP_DEFAULTS = Object.freeze({smoothTime: 0.25, maxSpeed: Infinity});

const TAU = Math.PI * 2;

function checkTiming(smoothTime, dt, maxSpeed) {
  if (!(typeof smoothTime === 'number' && smoothTime > 0 && Number.isFinite(smoothTime))) {
    throw new RangeError(`smoothTime must be a positive number of seconds, got ${smoothTime}`);
  }
  if (!(typeof dt === 'number' && dt >= 0 && Number.isFinite(dt))) {
    throw new RangeError(`dt must be a non-negative number of seconds, got ${dt}`);
  }
  if (!(typeof maxSpeed === 'number' && maxSpeed > 0)) {
    throw new RangeError(`maxSpeed must be a positive number or Infinity, got ${maxSpeed}`);
  }
}

function checkNumber(value, name) {
  if (!(typeof value === 'number' && Number.isFinite(value))) throw new TypeError(`${name} must be a finite number`);
}

// The exact critically damped step for a displacement y from the target and a velocity v over dt.
function exactStep(displacement, velocity, omega, dt, out, index) {
  const lead = velocity + omega * displacement;
  const decay = Math.exp(-omega * dt);
  out[index] = (displacement + lead * dt) * decay;
  out[index + 1] = (velocity - omega * lead * dt) * decay;
}

const scratch = new Float64Array(2);

// How far the target may be from current. Holding the target at distance D at the start of every step makes the
// stepped motion settle where each step covers exactly maxSpeed * dt: with a = e^(-w dt) and x = w dt the steady
// state of the exact step solves to D = maxSpeed * dt * (1 - a + a x) / (1 - a)^2, which tends to
// maxSpeed * smoothTime as dt goes to 0. From rest the steps grow toward that speed without passing it while
// x <= 1 (dt <= smoothTime / 2), because the velocity recurrence v' = a (1 - x) v + const is then monotonic.
function distanceLimit(maxSpeed, omega, dt) {
  if (maxSpeed === Infinity) return Infinity;
  const x = omega * dt;
  if (!(x > 0)) return (2 * maxSpeed) / omega;
  const gap = -Math.expm1(-x);
  return (maxSpeed * dt * (gap + (1 - gap) * x)) / (gap * gap);
}

/**
 * One step of a critically damped spring from current toward target. Returns {value, velocity}. With a finite
 * maxSpeed the target is first moved toward current, to about maxSpeed * smoothTime away (the exact distance depends
 * on dt), so a far target is approached covering exactly maxSpeed per second at any step size; from rest the steps
 * and the velocity rise to that speed without passing it while dt is at most smoothTime / 2.
 */
export function smoothDamp(current, target, velocity, smoothTime, dt, maxSpeed = Infinity) {
  checkTiming(smoothTime, dt, maxSpeed);
  checkNumber(current, 'current');
  checkNumber(target, 'target');
  checkNumber(velocity, 'velocity');
  const omega = 2 / smoothTime;
  const limit = distanceLimit(maxSpeed, omega, dt);
  let displacement = current - target;
  if (Math.abs(displacement) > limit) displacement = Math.sign(displacement) * limit;
  exactStep(displacement, velocity, omega, dt, scratch, 0);
  return {value: current - displacement + scratch[0], velocity: scratch[1]};
}

/**
 * The same step for vectors of any length (arrays or typed arrays of equal length). maxSpeed limits the length of
 * the velocity, not each component. Returns {value, velocity} as new plain arrays.
 */
export function smoothDampVector(current, target, velocity, smoothTime, dt, maxSpeed = Infinity) {
  checkTiming(smoothTime, dt, maxSpeed);
  const size = current.length;
  if (!(size > 0) || target.length !== size || velocity.length !== size) {
    throw new RangeError('current, target and velocity must be non-empty and of equal length');
  }
  const displacement = new Array(size);
  let squared = 0;
  for (let index = 0; index < size; index += 1) {
    checkNumber(current[index], 'current');
    checkNumber(target[index], 'target');
    checkNumber(velocity[index], 'velocity');
    displacement[index] = current[index] - target[index];
    squared += displacement[index] * displacement[index];
  }
  const omega = 2 / smoothTime;
  const limit = distanceLimit(maxSpeed, omega, dt);
  const length = Math.sqrt(squared);
  const scale = length > limit ? limit / length : 1;
  const value = new Array(size);
  const speed = new Array(size);
  for (let index = 0; index < size; index += 1) {
    const clamped = displacement[index] * scale;
    exactStep(clamped, velocity[index], omega, dt, scratch, 0);
    value[index] = current[index] - clamped + scratch[0];
    speed[index] = scratch[1];
  }
  return {value, velocity: speed};
}

/** The signed difference from one angle to another along the shorter arc, in (-pi, pi] radians. */
export function shortestAngle(from, to) {
  checkNumber(from, 'from');
  checkNumber(to, 'to');
  let difference = (to - from) % TAU;
  if (difference <= -Math.PI) difference += TAU;
  if (difference > Math.PI) difference -= TAU;
  return difference;
}

/**
 * The spring for an angle in radians: it turns along the shorter arc. The returned value continues from current
 * without wrapping, so it can pass pi; wrap it yourself if you need a range.
 */
export function smoothDampAngle(current, target, velocity, smoothTime, dt, maxSpeed = Infinity) {
  return smoothDamp(current, current + shortestAngle(current, target), velocity, smoothTime, dt, maxSpeed);
}

/**
 * A spring state for a vector of a fixed size: reset(value) then update(target, dt) each frame. value and velocity
 * are Float64Arrays updated in place, so a three.js object can read them with position.fromArray(follower.value).
 */
export class SpringFollower {
  constructor(size, options = {}) {
    if (!Number.isInteger(size) || size < 1 || size > 64) throw new RangeError('size must be an integer from 1 to 64');
    for (const key of Object.keys(options)) {
      if (!Object.prototype.hasOwnProperty.call(SMOOTH_DAMP_DEFAULTS, key)) throw new TypeError(`unknown spring option ${key}`);
    }
    const settings = {...SMOOTH_DAMP_DEFAULTS, ...options};
    checkTiming(settings.smoothTime, 0, settings.maxSpeed);
    this.smoothTime = settings.smoothTime;
    this.maxSpeed = settings.maxSpeed;
    this.value = new Float64Array(size);
    this.velocity = new Float64Array(size);
  }

  reset(value, velocity = null) {
    if (value.length !== this.value.length) throw new RangeError('value has the wrong length');
    this.value.set(value);
    if (velocity === null) this.velocity.fill(0);
    else if (velocity.length !== this.velocity.length) throw new RangeError('velocity has the wrong length');
    else this.velocity.set(velocity);
    return this.value;
  }

  update(target, dt) {
    const result = smoothDampVector(this.value, target, this.velocity, this.smoothTime, dt, this.maxSpeed);
    this.value.set(result.value);
    this.velocity.set(result.velocity);
    return this.value;
  }
}
