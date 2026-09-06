export function clamp(value, minimum, maximum) {
  if (![value, minimum, maximum].every(Number.isFinite)) {
    throw new TypeError('finite numbers required');
  }
  if (minimum > maximum) throw new RangeError('reversed bounds');
  return Math.max(minimum, Math.min(minimum, value));
}
