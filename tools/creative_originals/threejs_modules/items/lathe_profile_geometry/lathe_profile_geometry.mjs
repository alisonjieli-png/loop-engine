// Lathe geometry for three.js with creases and caps: revolve a 2D profile [[r, y], ...] around the Y axis, give each
// profile vertex a smooth normal or split it where the profile turns sharply, close open ends with caps, and lay UVs
// out by arc length. Exact volume and area of the revolved shape come with it. Original Baltor implementation;
// latheProfileData works on typed arrays alone.

/** Default options. Angles: phiStart and phiLength in radians, creaseAngle in degrees. */
export const LATHE_PROFILE_DEFAULTS = Object.freeze({
  segments: 48,
  phiStart: 0,
  phiLength: 2 * Math.PI,
  creaseAngle: 30,
  caps: true,
  closed: false,
});

const MAXIMUM_SEGMENTS = 4096;
const FULL_TURN = 2 * Math.PI;
const SAME_POINT = 1e-12;

// sin and cos of grid angles with the floating-point residue at multiples of pi / 2 set to an exact zero.
function snap(value) {
  return Math.abs(value) < SAME_POINT ? 0 : value;
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(LATHE_PROFILE_DEFAULTS, key)) throw new TypeError(`unknown lathe option ${key}`);
  }
  const settings = {...LATHE_PROFILE_DEFAULTS, ...options};
  if (!Number.isInteger(settings.segments) || settings.segments < 3 || settings.segments > MAXIMUM_SEGMENTS) {
    throw new RangeError(`segments must be an integer from 3 to ${MAXIMUM_SEGMENTS}`);
  }
  if (!(settings.phiLength > 0 && settings.phiLength <= FULL_TURN)) throw new RangeError('phiLength must be in (0, 2 pi]');
  if (!Number.isFinite(settings.phiStart)) throw new RangeError('phiStart must be a finite angle');
  if (!(settings.creaseAngle >= 0 && settings.creaseAngle <= 180)) throw new RangeError('creaseAngle must be in [0, 180]');
  for (const key of ['caps', 'closed']) {
    if (typeof settings[key] !== 'boolean') throw new TypeError(`${key} must be true or false`);
  }
  return settings;
}

function profileOf(profile, closed) {
  if (!Array.isArray(profile)) throw new TypeError('the profile is an array of [r, y] points');
  const points = profile.map((point, index) => {
    if (!Array.isArray(point) || point.length !== 2 || !point.every(Number.isFinite)) {
      throw new TypeError(`profile point ${index} must be [r, y] with finite numbers`);
    }
    if (point[0] < 0) throw new RangeError(`profile point ${index} has a negative radius`);
    return [point[0], point[1]];
  });
  if (closed && points.length > 1) {
    const first = points[0];
    const last = points[points.length - 1];
    if (Math.abs(first[0] - last[0]) < SAME_POINT && Math.abs(first[1] - last[1]) < SAME_POINT) points.pop();
  }
  if (points.length < (closed ? 3 : 2)) throw new RangeError(`the profile needs at least ${closed ? 3 : 2} distinct points`);
  const count = closed ? points.length : points.length - 1;
  for (let s = 0; s < count; s += 1) {
    const [r0, y0] = points[s];
    const [r1, y1] = points[(s + 1) % points.length];
    if (Math.hypot(r1 - r0, y1 - y0) < SAME_POINT) throw new RangeError(`profile points ${s} and ${s + 1} coincide`);
  }
  return points;
}

/**
 * Signed volume of the solid the profile sweeps in a full turn, closed by caps (or by itself when closed is true):
 * the sum over profile segments of pi / 3 (r0^2 + r0 r1 + r1^2) (y1 - y0). Positive when the profile runs from bottom
 * to top on the outside (or counter-clockwise in the r-y plane for a closed loop).
 */
export function latheProfileVolume(profile, closed = false) {
  const points = profileOf(profile, closed);
  const count = closed ? points.length : points.length - 1;
  let volume = 0;
  for (let s = 0; s < count; s += 1) {
    const [r0, y0] = points[s];
    const [r1, y1] = points[(s + 1) % points.length];
    volume += (Math.PI / 3) * (r0 * r0 + r0 * r1 + r1 * r1) * (y1 - y0);
  }
  return volume;
}

/** Area of the surface the profile sweeps in a full turn (caps excluded): the sum of pi (r0 + r1) times each length. */
export function latheProfileArea(profile, closed = false) {
  const points = profileOf(profile, closed);
  const count = closed ? points.length : points.length - 1;
  let area = 0;
  for (let s = 0; s < count; s += 1) {
    const [r0, y0] = points[s];
    const [r1, y1] = points[(s + 1) % points.length];
    area += Math.PI * (r0 + r1) * Math.hypot(r1 - r0, y1 - y0);
  }
  return area;
}

/**
 * The revolved profile as typed arrays {positions, normals, uvs, indices}. The outside is to the right of the
 * profile's direction (draw a solid from bottom to top on its outer edge, as LatheGeometry expects). A profile vertex
 * where the profile turns by more than creaseAngle gets two rings, one per side; elsewhere one smooth ring. With caps,
 * an open profile end that is off the axis is closed by a flat cap facing -Y at the start and +Y at the end.
 */
export function latheProfileData(profile, options = {}) {
  const settings = settingsOf(options);
  const points = profileOf(profile, settings.closed);
  const pointCount = points.length;
  const segmentCount = settings.closed ? pointCount : pointCount - 1;
  const segmentNormals = [];
  const lengths = [];
  for (let s = 0; s < segmentCount; s += 1) {
    const [r0, y0] = points[s];
    const [r1, y1] = points[(s + 1) % pointCount];
    const length = Math.hypot(r1 - r0, y1 - y0);
    lengths.push(length);
    segmentNormals.push([(y1 - y0) / length, -(r1 - r0) / length]);
  }
  const total = lengths.reduce((sum, value) => sum + value, 0);
  const crease = Math.cos((settings.creaseAngle * Math.PI) / 180);
  // Per profile vertex: the normal on its incoming side and on its outgoing side, one bisector when the profile turns
  // by no more than the crease angle (then the two sides share one ring).
  const sides = points.map((_, k) => {
    const incoming = k > 0 ? k - 1 : (settings.closed ? segmentCount - 1 : -1);
    const outgoing = k < segmentCount ? k : -1;
    if (incoming >= 0 && outgoing >= 0) {
      const [ar, ay] = segmentNormals[incoming];
      const [br, by] = segmentNormals[outgoing];
      const cosine = ar * br + ay * by;
      if (cosine >= crease && cosine > -1 + 1e-9) {
        const length = Math.hypot(ar + br, ay + by);
        const normal = [(ar + br) / length, (ay + by) / length];
        return {incoming: normal, outgoing: normal, smooth: true};
      }
    }
    return {incoming: incoming >= 0 ? segmentNormals[incoming] : null,
      outgoing: outgoing >= 0 ? segmentNormals[outgoing] : null, smooth: false};
  });
  // A ring is a profile vertex with one normal and one v; each segment joins its start ring to its end ring. A closed
  // profile ends on a second ring at its first point (v = 1) so the UVs wrap.
  const rings = [];
  const addRing = (pointIndex, normal, arcLength) => {
    rings.push({r: points[pointIndex][0], y: points[pointIndex][1], nr: normal[0], ny: normal[1], v: arcLength / total});
    return rings.length - 1;
  };
  const segmentRings = [];
  let arc = 0;
  let previousEnd = null;
  for (let s = 0; s < segmentCount; s += 1) {
    const start = s;
    const end = (s + 1) % pointCount;
    const startRing = previousEnd !== null && sides[start].smooth ? previousEnd : addRing(start, sides[start].outgoing, arc);
    arc += lengths[s];
    const endRing = addRing(end, sides[end].incoming, arc);
    segmentRings.push([startRing, endRing]);
    previousEnd = endRing;
  }
  const {segments, phiStart, phiLength} = settings;
  const columns = segments + 1;
  const capStart = settings.caps && !settings.closed && points[0][0] > SAME_POINT;
  const capEnd = settings.caps && !settings.closed && points[pointCount - 1][0] > SAME_POINT;
  const vertexCount = rings.length * columns + (capStart ? columns + 1 : 0) + (capEnd ? columns + 1 : 0);
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const angles = Array.from({length: columns}, (_, i) => {
    const phi = phiStart + (phiLength * i) / segments;
    return [snap(Math.sin(phi)), snap(Math.cos(phi))];
  });
  // A full turn ends on exactly the first column, so the seam vertices have identical positions.
  if (phiLength === FULL_TURN) angles[segments] = angles[0];
  let vertex = 0;
  for (const ring of rings) {
    for (let i = 0; i < columns; i += 1) {
      const [sine, cosine] = angles[i];
      positions.set([ring.r * sine, ring.y, ring.r * cosine], vertex * 3);
      normals.set([ring.nr * sine, ring.ny, ring.nr * cosine], vertex * 3);
      uvs.set([i / segments, ring.v], vertex * 2);
      vertex += 1;
    }
  }
  const triangles = [];
  for (const [startRing, endRing] of segmentRings) {
    const onAxisStart = rings[startRing].r <= SAME_POINT;
    const onAxisEnd = rings[endRing].r <= SAME_POINT;
    for (let i = 0; i < segments; i += 1) {
      const a = startRing * columns + i;
      const b = a + 1;
      const d = endRing * columns + i;
      const c = d + 1;
      if (!onAxisStart) triangles.push(a, b, c);
      if (!onAxisEnd) triangles.push(a, c, d);
    }
  }
  const addCap = (pointIndex, facingUp) => {
    const [radius, height] = points[pointIndex];
    const centre = vertex;
    positions.set([0, height, 0], centre * 3);
    normals.set([0, facingUp ? 1 : -1, 0], centre * 3);
    uvs.set([0.5, 0.5], centre * 2);
    vertex += 1;
    for (let i = 0; i < columns; i += 1) {
      const [sine, cosine] = angles[i];
      positions.set([radius * sine, height, radius * cosine], vertex * 3);
      normals.set([0, facingUp ? 1 : -1, 0], vertex * 3);
      uvs.set([0.5 + 0.5 * sine, 0.5 + 0.5 * cosine], vertex * 2);
      vertex += 1;
    }
    for (let i = 0; i < segments; i += 1) {
      const p = centre + 1 + i;
      if (facingUp) triangles.push(centre, p, p + 1);
      else triangles.push(centre, p + 1, p);
    }
  };
  if (capStart) addCap(0, false);
  if (capEnd) addCap(pointCount - 1, true);
  const indices = vertexCount > 65535 ? Uint32Array.from(triangles) : Uint16Array.from(triangles);
  return {positions, normals, uvs, indices};
}

/** A THREE.BufferGeometry of the revolved profile with position, normal and uv attributes and an index. */
export function createLatheProfileGeometry(THREE, profile, options = {}) {
  const data = latheProfileData(profile, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
