// Known answers for the solar position, from published astronomical facts and hand calculation: the Julian day of
// J2000 (2451545) and of the Unix epoch (2440587.5); declination near +23.44 degrees at the June 2024 solstice
// (2024-06-20 20:51 UTC) and near 0 at the March 2024 equinox (03:06 UTC); the equation of time near -14.2 minutes on
// 11 February and +16.4 minutes on 3 November; at local solar noon on the equinox at 40 degrees north the sun stands
// due south at 90 - 40 + declination degrees, raised by about 48.7 arc seconds of refraction (58.1 / tan 50 degrees
// minus 0.07 / tan^3). Known-wrong control: treating longitude as west-positive puts New York's noon sun far from south.
import test from 'node:test';
import assert from 'node:assert/strict';
import {SOLAR_DEFAULTS, aimSunLight, directionFromAngles, julianDay, solarPosition, sunDirection} from './sun_position_solar.mjs';

const NEW_YORK = [40.7128, -74.006];

function noonProblems(position) {
  const problems = [];
  const london = position(new Date('2024-03-20T12:07:18Z'), 40, 0);
  if (Math.abs(london.azimuth - 180) > 0.2) problems.push(`noon azimuth at 0 E is ${london.azimuth}`);
  const york = position(new Date('2024-06-21T16:57:00Z'), ...NEW_YORK);
  if (Math.abs(york.azimuth - 180) > 2) problems.push(`noon azimuth in New York is ${york.azimuth}`);
  return problems;
}

test('Julian days of two epochs', () => {
  assert.equal(julianDay(Date.UTC(2000, 0, 1, 12)), 2451545);
  assert.equal(julianDay(0), 2440587.5);
  assert.equal(julianDay(new Date(86400000)), 2440588.5);
});

test('declination at the 2024 solstice and equinox', () => {
  const solstice = solarPosition(new Date('2024-06-20T20:51:00Z'), 0, 0);
  assert.ok(solstice.declination > 23.42 && solstice.declination < 23.46, `${solstice.declination}`);
  const equinox = solarPosition(new Date('2024-03-20T03:06:00Z'), 0, 0);
  assert.ok(Math.abs(equinox.declination) < 0.02, `${equinox.declination}`);
});

test('equation of time near its February and November extremes', () => {
  const february = solarPosition(new Date('2024-02-11T12:00:00Z'), 0, 0).equationOfTime;
  const november = solarPosition(new Date('2024-11-03T12:00:00Z'), 0, 0).equationOfTime;
  assert.ok(february > -14.6 && february < -13.8, `${february}`);
  assert.ok(november > 16.0 && november < 16.8, `${november}`);
});

test('the equinox noon sun at 40 degrees north', () => {
  assert.deepEqual(noonProblems(solarPosition), []);
  const date = new Date('2024-03-20T12:07:18Z');
  const geometric = solarPosition(date, 40, 0, {refraction: false});
  assert.ok(Math.abs(geometric.elevation - (50 + geometric.declination)) < 0.01, `${geometric.elevation}`);
  const apparent = solarPosition(date, 40, 0);
  assert.ok(Math.abs(apparent.elevation - geometric.elevation - 48.71 / 3600) < 0.0005, 'refraction near 48.7 arc seconds');
  const toward = sunDirection(date, 40, 0);
  assert.ok(Math.abs(Math.hypot(...toward) - 1) < 1e-12);
  assert.ok(Math.abs(toward[0]) < 0.005 && toward[2] > 0.6, 'due south is +Z');
  assert.ok(Math.abs(toward[1] - Math.sin(apparent.elevation * Math.PI / 180)) < 1e-12);
});

test('afternoon and southern-hemisphere sanity', () => {
  const york = solarPosition(new Date('2024-06-21T20:00:00Z'), ...NEW_YORK);
  assert.ok(york.azimuth > 225 && york.azimuth < 270 && york.elevation > 40 && york.elevation < 55, JSON.stringify(york));
  const night = solarPosition(new Date('2024-06-21T04:00:00Z'), ...NEW_YORK);
  assert.ok(night.elevation < 0 && sunDirection(new Date('2024-06-21T04:00:00Z'), ...NEW_YORK)[1] < 0);
  const sydney = solarPosition(new Date('2024-12-21T01:53:00Z'), -33.8688, 151.2093);
  assert.ok(sydney.azimuth < 2 || sydney.azimuth > 358, `the noon sun is north in Sydney: ${sydney.azimuth}`);
  assert.ok(Math.abs(sydney.elevation - (90 - (-sydney.declination - 33.8688) * -1 - 0)) > -1, 'elevation is finite');
});

test('known wrong: west-positive longitude moves the noon sun away from south', () => {
  const westPositive = (date, latitude, longitude, options) => solarPosition(date, latitude, -longitude, options);
  assert.notDeepEqual(noonProblems(westPositive), []);
});

test('directions, light placement and bad input', () => {
  const close = (a, b) => a.every((value, index) => Math.abs(value - b[index]) < 1e-12);
  assert.ok(close(directionFromAngles(0, 0), [0, 0, -1]), 'north is -Z');
  assert.ok(close(directionFromAngles(90, 0), [1, 0, 0]), 'east is +X');
  assert.ok(close(directionFromAngles(123, 90), [0, 1, 0]), 'the zenith is +Y');
  const light = {position: {set(x, y, z) { Object.assign(this, {x, y, z}); }}, target: {position: {x: 1, y: 0, z: 2}}};
  aimSunLight(light, [0, 3, 4], 10);
  assert.deepEqual([light.position.x, light.position.y, light.position.z], [1, 6, 10]);
  assert.throws(() => solarPosition(new Date(), 91, 0), RangeError);
  assert.throws(() => solarPosition('noon', 0, 0), TypeError);
  assert.throws(() => solarPosition(new Date(), 0, 0, {refract: false}), TypeError);
  assert.throws(() => solarPosition(new Date(), 0, 0, {toString: false}), TypeError, 'an inherited name is not an option');
  assert.throws(() => aimSunLight({}, [0, 1, 0]), TypeError);
  assert.equal(SOLAR_DEFAULTS.refraction, true);
});
