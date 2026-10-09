// Solar position for lighting: the sun's elevation and azimuth for a UTC time and a place, from the low-precision
// solar coordinates (Julian day, mean anomaly, equation of centre, apparent longitude, obliquity, declination,
// equation of time, hour angle) with optional atmospheric refraction, and a unit direction toward the sun in a scene
// convention of +Y up, -Z north and +X east. Original Baltor implementation written from the astronomical formulas;
// numbers only, and aimSunLight places any light that has a position (such as a THREE.DirectionalLight).

/** Default options of solarPosition and sunDirection. */
export const SOLAR_DEFAULTS = Object.freeze({refraction: true});

const DEGREE = Math.PI / 180;
const UNIX_EPOCH_JULIAN_DAY = 2440587.5;
const J2000 = 2451545;
const MILLISECONDS_PER_DAY = 86400000;
const MINUTES_PER_DAY = 1440;

function millisecondsOf(date) {
  const value = date instanceof Date ? date.getTime() : date;
  if (!(typeof value === 'number' && Number.isFinite(value))) throw new TypeError('date must be a Date or epoch milliseconds');
  return value;
}

/** The Julian day of a UTC instant (a Date or milliseconds since 1970-01-01T00:00Z). */
export function julianDay(date) {
  return millisecondsOf(date) / MILLISECONDS_PER_DAY + UNIX_EPOCH_JULIAN_DAY;
}

function settingsOf(options) {
  if (!options || typeof options !== 'object') throw new TypeError('options must be an object');
  for (const key of Object.keys(options)) if (!Object.prototype.hasOwnProperty.call(SOLAR_DEFAULTS, key)) throw new TypeError(`unknown solar option ${key}`);
  const settings = {...SOLAR_DEFAULTS, ...options};
  if (typeof settings.refraction !== 'boolean') throw new TypeError('refraction must be true or false');
  return settings;
}

// Atmospheric refraction in degrees for a geometric elevation in degrees (the low-precision piecewise fit).
function refraction(elevation) {
  if (elevation > 85) return 0;
  const tangent = Math.tan(elevation * DEGREE);
  let seconds;
  if (elevation > 5) seconds = 58.1 / tangent - 0.07 / tangent ** 3 + 0.000086 / tangent ** 5;
  else if (elevation > -0.575) seconds = 1735 + elevation * (-518.2 + elevation * (103.4 + elevation * (-12.79 + elevation * 0.711)));
  else seconds = -20.772 / tangent;
  return seconds / 3600;
}

/**
 * The sun seen from latitude (degrees, north positive) and longitude (degrees, east positive) at a UTC instant:
 * {elevation, azimuth, zenith, declination, hourAngle} in degrees (azimuth clockwise from north), equationOfTime in
 * minutes and julianDay. With refraction (the default) elevation and zenith are apparent, as an observer sees them.
 */
export function solarPosition(date, latitude, longitude, options = {}) {
  const settings = settingsOf(options);
  if (!(typeof latitude === 'number' && latitude >= -90 && latitude <= 90)) throw new RangeError('latitude must be in [-90, 90]');
  if (!(typeof longitude === 'number' && longitude >= -180 && longitude <= 180)) throw new RangeError('longitude must be in [-180, 180]');
  const day = julianDay(date);
  const t = (day - J2000) / 36525;
  const meanLongitude = (((280.46646 + t * (36000.76983 + t * 0.0003032)) % 360) + 360) % 360;
  const meanAnomaly = 357.52911 + t * (35999.05029 - 0.0001537 * t);
  const eccentricity = 0.016708634 - t * (0.000042037 + 0.0000001267 * t);
  const m = meanAnomaly * DEGREE;
  const centre = Math.sin(m) * (1.914602 - t * (0.004817 + 0.000014 * t)) + Math.sin(2 * m) * (0.019993 - 0.000101 * t)
    + Math.sin(3 * m) * 0.000289;
  const node = (125.04 - 1934.136 * t) * DEGREE;
  const apparentLongitude = (meanLongitude + centre - 0.00569 - 0.00478 * Math.sin(node)) * DEGREE;
  const meanObliquity = 23 + (26 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60) / 60;
  const obliquity = (meanObliquity + 0.00256 * Math.cos(node)) * DEGREE;
  const declination = Math.asin(Math.sin(obliquity) * Math.sin(apparentLongitude));
  const y = Math.tan(obliquity / 2) ** 2;
  const l0 = meanLongitude * DEGREE;
  const equationOfTime = (4 / DEGREE) * (y * Math.sin(2 * l0) - 2 * eccentricity * Math.sin(m)
    + 4 * eccentricity * y * Math.sin(m) * Math.cos(2 * l0) - 0.5 * y * y * Math.sin(4 * l0)
    - 1.25 * eccentricity * eccentricity * Math.sin(2 * m));
  const milliseconds = millisecondsOf(date);
  const utcMinutes = ((milliseconds % MILLISECONDS_PER_DAY) + MILLISECONDS_PER_DAY) % MILLISECONDS_PER_DAY / 60000;
  const trueSolarMinutes = (((utcMinutes + equationOfTime + 4 * longitude) % MINUTES_PER_DAY) + MINUTES_PER_DAY) % MINUTES_PER_DAY;
  let hourAngle = trueSolarMinutes / 4 - 180;
  if (hourAngle < -180) hourAngle += 360;
  const phi = latitude * DEGREE;
  const h = hourAngle * DEGREE;
  const cosZenith = Math.min(Math.max(Math.sin(phi) * Math.sin(declination) + Math.cos(phi) * Math.cos(declination) * Math.cos(h), -1), 1);
  const geometricZenith = Math.acos(cosZenith) / DEGREE;
  const geometricElevation = 90 - geometricZenith;
  const elevation = geometricElevation + (settings.refraction ? refraction(geometricElevation) : 0);
  const azimuth = ((Math.atan2(Math.sin(h), Math.cos(h) * Math.sin(phi) - Math.tan(declination) * Math.cos(phi)) / DEGREE + 180) % 360
    + 360) % 360;
  return {elevation, azimuth, zenith: 90 - elevation, declination: declination / DEGREE, hourAngle, equationOfTime, julianDay: day};
}

/** A unit vector toward azimuth (degrees clockwise from north) and elevation, with +Y up, -Z north and +X east. */
export function directionFromAngles(azimuth, elevation) {
  if (!(Number.isFinite(azimuth) && Number.isFinite(elevation))) throw new TypeError('azimuth and elevation must be numbers');
  const a = azimuth * DEGREE;
  const e = elevation * DEGREE;
  return [Math.sin(a) * Math.cos(e), Math.sin(e), -Math.cos(a) * Math.cos(e)];
}

/** The unit direction toward the sun (+Y up, -Z north, +X east); below the horizon its y is negative. */
export function sunDirection(date, latitude, longitude, options = {}) {
  const {azimuth, elevation} = solarPosition(date, latitude, longitude, options);
  return directionFromAngles(azimuth, elevation);
}

/**
 * Place a light distance units from its target along direction (light.position = target + direction * distance).
 * Works with a THREE.DirectionalLight (it uses light.target.position when there is a target) or any object whose
 * position has set(x, y, z). Returns the light.
 */
export function aimSunLight(light, direction, distance = 20) {
  if (!light || !light.position || typeof light.position.set !== 'function') throw new TypeError('light needs position.set');
  if (!(Array.isArray(direction) && direction.length === 3 && direction.every(Number.isFinite))) throw new TypeError('direction is [x, y, z]');
  if (!(typeof distance === 'number' && distance > 0)) throw new RangeError('distance must be positive');
  const length = Math.hypot(...direction);
  if (!(length > 0)) throw new RangeError('direction must not be zero');
  const target = light.target && light.target.position ? light.target.position : {x: 0, y: 0, z: 0};
  light.position.set(target.x + (direction[0] / length) * distance, target.y + (direction[1] / length) * distance,
    target.z + (direction[2] / length) * distance);
  return light;
}
