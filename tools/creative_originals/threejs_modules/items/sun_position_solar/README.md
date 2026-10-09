# Solar position and sun light placement

Computes where the sun is for a UTC instant at a latitude and longitude, from the low-precision solar coordinates: Julian day and century, mean longitude and anomaly, equation of centre, apparent longitude, obliquity, declination, equation of time, true solar time and hour angle, then elevation and azimuth, with optional atmospheric refraction. It turns the result into a unit direction in a scene convention of +Y up, -Z north and +X east (north is where three.js's default camera looks), and places a light along it.

## When to use it

Use it for time-of-day lighting in architectural and landscape scenes, shadow studies for a real site and date, sundials and planetariums, games with a day cycle tied to a calendar, and checking whether a terrace gets sun at a given hour.

## Use it

```js
import * as THREE from 'three';
import {aimSunLight, solarPosition, sunDirection} from './sun_position_solar.mjs';

const when = new Date('2024-06-21T15:30:00Z');
const [latitude, longitude] = [48.8566, 2.3522];        // Paris; longitude east positive
const sun = new THREE.DirectionalLight(0xfff1d6, 3);
sun.castShadow = true;
scene.add(sun, sun.target);
aimSunLight(sun, sunDirection(when, latitude, longitude), 30);

const {elevation, azimuth, equationOfTime} = solarPosition(when, latitude, longitude);
```

`demo/scene.mjs` lights a Paris courtyard on the afternoon of the 2024 June solstice with shadows.

## Exports

- `solarPosition(date, latitude, longitude, options = {})`: `{elevation, azimuth, zenith, declination, hourAngle, equationOfTime, julianDay}`; angles in degrees (azimuth clockwise from north, elevation apparent unless `refraction: false`), equation of time in minutes. `date` is a `Date` or epoch milliseconds; latitude is north positive, longitude east positive.
- `sunDirection(date, latitude, longitude, options = {})`: the unit vector toward the sun; its y is negative below the horizon.
- `directionFromAngles(azimuth, elevation)`: the unit vector for an azimuth and elevation in the same axes.
- `julianDay(date)`: the Julian day of an instant.
- `aimSunLight(light, direction, distance = 20)`: sets `light.position` to the light's target (or the origin) plus `direction * distance`; works with a `THREE.DirectionalLight` or any object with `position.set`.
- `SOLAR_DEFAULTS`: the frozen default options.

## Options

| Option | Type | Default | Meaning |
|---|---|---|---|
| `refraction` | boolean | true | Add atmospheric refraction to the elevation (where an observer sees the sun) or keep the geometric position. |

An unknown option throws `TypeError`; a latitude outside [-90, 90] or a longitude outside [-180, 180] throws `RangeError`.

## Checks

- `test_sun_position_solar.mjs`, against published facts and hand calculation: the Julian days of J2000 (2451545) and of the Unix epoch (2440587.5); declination between 23.42 and 23.46 degrees at the June 2024 solstice and within 0.02 of 0 at the March 2024 equinox; the equation of time near -14.2 minutes on 11 February and near +16.4 on 3 November; on the equinox at 40 degrees north the noon sun stands due south at 90 - 40 + declination degrees, raised by 48.7 arc seconds of refraction (58.1 / tan 50 degrees - 0.07 / tan^3 50 degrees); afternoon sun in the southwest for New York, the noon sun to the north in Sydney, unit directions with north at -Z. Known-wrong control: treating longitude as west positive moves New York's noon sun far from south and is refused.
- `test_contract.mjs`: the exports and the contract examples.
- The verifier places a shadow-casting light in a three.js scene with `aimSunLight`, checks the light lies along the computed direction, renders the courtyard and requires the ground on the post's far side from the sun to be darker than the same distance toward the sun; the baseline puts the light straight overhead.

## Limits

Low-precision solar coordinates: positions agree with published values to about 0.01 to 0.05 degrees for dates within a few centuries of 2000, not to ephemeris accuracy. Refraction uses a standard-atmosphere fit and is approximate near the horizon. Time is UTC: there is no time zone or daylight saving handling, and longitude is east positive. It gives the sun's direction only: no sunrise and sunset search, sky colour, irradiance or moon. The scene axes are a convention (+Y up, -Z north); rotate the result for a scene whose north is elsewhere. Checked against published solstice, equinox and equation-of-time values and hand calculation, not against an ephemeris. Only three.js 0.186.1 shadows in headless Chrome on SwiftShader WebGL 2 were rendered.

## Technique

- Low-precision solar coordinates: mean anomaly, equation of centre, apparent longitude, obliquity of the ecliptic
- Equation of time and hour angle from true solar time
- Altitude and azimuth from hour angle, declination and latitude, with a refraction fit
