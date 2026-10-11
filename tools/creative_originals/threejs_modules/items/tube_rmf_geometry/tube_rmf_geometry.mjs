// Tube geometry for three.js along a path with rotation-minimizing frames: the cross-section does not spin around the
// path the way Frenet frames do at inflections, closed loops spread their leftover twist evenly so the seam matches,
// radii can vary per point, polyline corners are mitred, and open tubes get caps. Original Baltor implementation; the
// curve sampler, the frames and tubeRmfData work on plain arrays and typed arrays alone.

/** Default options of tubeRmfData and createTubeRmfGeometry. */
export const TUBE_RMF_DEFAULTS = Object.freeze({
  radius: 0.1,
  radii: null,
  radialSegments: 12,
  curve: 'catmull-rom',
  samplesPerSegment: 8,
  closed: false,
  caps: true,
  correctTwist: true,
  initialNormal: null,
});

const CURVES = Object.freeze(['catmull-rom', 'polyline']);
const POLYLINE = 'polyline';
const MAXIMUM_SEGMENTS = 1024;
const TINY = 1e-12;
const ALPHA = 0.5;

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const length = (a) => Math.hypot(a[0], a[1], a[2]);
const unit = (a) => scale(a, 1 / length(a));
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

function pointsOf(points, closed) {
  if (!Array.isArray(points)) throw new TypeError('points is an array of [x, y, z]');
  const list = points.map((point, index) => {
    if (!Array.isArray(point) || point.length !== 3 || !point.every(Number.isFinite)) {
      throw new TypeError(`point ${index} must be [x, y, z] with finite numbers`);
    }
    return [point[0], point[1], point[2]];
  });
  if (list.length < (closed ? 3 : 2)) throw new RangeError(`a ${closed ? 'closed' : 'open'} path needs ${closed ? 3 : 2} points`);
  const count = closed ? list.length : list.length - 1;
  for (let k = 0; k < count; k += 1) {
    if (length(sub(list[(k + 1) % list.length], list[k])) < TINY) throw new RangeError(`points ${k} and ${k + 1} coincide`);
  }
  return list;
}

// Point and derivative of the centripetal Catmull-Rom segment between p1 and p2 at fraction f of its knot interval
// (Barry and Goldman's pyramid of linear interpolations, differentiated level by level).
function catmullRom(p0, p1, p2, p3, fraction) {
  const t0 = 0;
  const t1 = t0 + length(sub(p1, p0)) ** ALPHA;
  const t2 = t1 + length(sub(p2, p1)) ** ALPHA;
  const t3 = t2 + length(sub(p3, p2)) ** ALPHA;
  const t = t1 + (t2 - t1) * fraction;
  const a1 = mix(p0, p1, (t - t0) / (t1 - t0));
  const a2 = mix(p1, p2, (t - t1) / (t2 - t1));
  const a3 = mix(p2, p3, (t - t2) / (t3 - t2));
  const da1 = scale(sub(p1, p0), 1 / (t1 - t0));
  const da2 = scale(sub(p2, p1), 1 / (t2 - t1));
  const da3 = scale(sub(p3, p2), 1 / (t3 - t2));
  const b1 = mix(a1, a2, (t - t0) / (t2 - t0));
  const b2 = mix(a2, a3, (t - t1) / (t3 - t1));
  const db1 = add(scale(sub(a2, a1), 1 / (t2 - t0)), mix(da1, da2, (t - t0) / (t2 - t0)));
  const db2 = add(scale(sub(a3, a2), 1 / (t3 - t1)), mix(da2, da3, (t - t1) / (t3 - t1)));
  const point = mix(b1, b2, (t - t1) / (t2 - t1));
  const derivative = add(scale(sub(b2, b1), 1 / (t2 - t1)), mix(db1, db2, (t - t1) / (t2 - t1)));
  return [point, derivative];
}

/**
 * Sample the centripetal Catmull-Rom spline through the points: samplesPerSegment samples per segment at equal
 * parameter steps, starting exactly on each input point, plus the last point of an open curve. Returns
 * {points, tangents, segments, fractions} as arrays ([x, y, z] and unit tangents; the segment index and fraction of
 * each sample).
 */
export function sampleCentripetalCatmullRom(points, samplesPerSegment = 8, closed = false) {
  const list = pointsOf(points, closed);
  if (!Number.isInteger(samplesPerSegment) || samplesPerSegment < 1 || samplesPerSegment > MAXIMUM_SEGMENTS) {
    throw new RangeError(`samplesPerSegment must be an integer from 1 to ${MAXIMUM_SEGMENTS}`);
  }
  const n = list.length;
  const at = (k) => {
    if (closed) return list[((k % n) + n) % n];
    if (k < 0) return sub(scale(list[0], 2), list[1]);
    if (k >= n) return sub(scale(list[n - 1], 2), list[n - 2]);
    return list[k];
  };
  const result = {points: [], tangents: [], segments: [], fractions: []};
  const segmentCount = closed ? n : n - 1;
  for (let k = 0; k < segmentCount; k += 1) {
    for (let s = 0; s < samplesPerSegment; s += 1) {
      const fraction = s / samplesPerSegment;
      const [point, derivative] = catmullRom(at(k - 1), at(k), at(k + 1), at(k + 2), fraction);
      const tangent = length(derivative) > TINY ? unit(derivative) : unit(sub(at(k + 1), at(k)));
      result.points.push(s === 0 ? [...at(k)] : point);
      result.tangents.push(tangent);
      result.segments.push(k);
      result.fractions.push(fraction);
    }
  }
  if (!closed) {
    const [, derivative] = catmullRom(at(n - 3), at(n - 2), at(n - 1), at(n), 1);
    result.points.push([...list[n - 1]]);
    result.tangents.push(length(derivative) > TINY ? unit(derivative) : unit(sub(list[n - 1], list[n - 2])));
    result.segments.push(n - 2);
    result.fractions.push(1);
  }
  return result;
}

function rotateAbout(vector, axis, angle) {
  const cosine = Math.cos(angle);
  const sine = Math.sin(angle);
  return add(add(scale(vector, cosine), scale(cross(axis, vector), sine)), scale(axis, dot(axis, vector) * (1 - cosine)));
}

// Double reflection (Wang, Juttler, Zheng and Liu): carry normal r from point x0 with tangent t0 to x1 with tangent t1.
function transport(x0, t0, r, x1, t1) {
  const v1 = sub(x1, x0);
  const c1 = dot(v1, v1);
  if (c1 < TINY * TINY) return r;
  const rL = sub(r, scale(v1, (2 / c1) * dot(v1, r)));
  const tL = sub(t0, scale(v1, (2 / c1) * dot(v1, t0)));
  const v2 = sub(t1, tL);
  const c2 = dot(v2, v2);
  if (c2 < TINY * TINY) return rL;
  return sub(rL, scale(v2, (2 / c2) * dot(v2, rL)));
}

/**
 * Rotation-minimizing frames along sampled points with unit tangents, by the double reflection method. Returns
 * {normals, binormals, closingAngle}: binormal = tangent x normal. For a closed path, closingAngle is the twist (in
 * radians) by which the carried frame misses the first frame after a full loop; with correctTwist (the default) frame
 * i is turned by closingAngle * i / count about its tangent, so the loop closes on the first frame.
 */
export function rotationMinimizingFrames(points, tangents, options = {}) {
  const allowed = ['closed', 'correctTwist', 'initialNormal'];
  for (const key of Object.keys(options)) {
    if (!allowed.includes(key)) throw new TypeError(`unknown frame option ${key}`);
  }
  const closed = options.closed === true;
  const correctTwist = options.correctTwist !== false;
  if (points.length !== tangents.length || points.length < 2) throw new RangeError('points and tangents need equal lengths of at least 2');
  const t0 = tangents[0];
  let r0;
  if (options.initialNormal) {
    const guess = options.initialNormal;
    r0 = sub(guess, scale(t0, dot(guess, t0)));
    if (length(r0) < 1e-9) throw new RangeError('initialNormal is parallel to the first tangent');
  } else {
    const absolute = t0.map(Math.abs);
    const axis = [0, 0, 0];
    axis[absolute.indexOf(Math.min(...absolute))] = 1;
    r0 = sub(axis, scale(t0, dot(axis, t0)));
  }
  const normals = [unit(r0)];
  for (let i = 1; i < points.length; i += 1) {
    const carried = transport(points[i - 1], tangents[i - 1], normals[i - 1], points[i], tangents[i]);
    normals.push(unit(sub(carried, scale(tangents[i], dot(carried, tangents[i])))));
  }
  let closingAngle = 0;
  if (closed) {
    const last = points.length - 1;
    const back = transport(points[last], tangents[last], normals[last], points[0], tangents[0]);
    closingAngle = Math.atan2(dot(cross(back, normals[0]), tangents[0]), dot(back, normals[0]));
    if (correctTwist) {
      for (let i = 1; i < points.length; i += 1) {
        normals[i] = unit(rotateAbout(normals[i], tangents[i], (closingAngle * i) / points.length));
      }
    }
  }
  const binormals = normals.map((normal, i) => unit(cross(tangents[i], normal)));
  return {normals, binormals, closingAngle};
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(TUBE_RMF_DEFAULTS, key)) throw new TypeError(`unknown tube option ${key}`);
  }
  const settings = {...TUBE_RMF_DEFAULTS, ...options};
  if (!(settings.radius > 0 && Number.isFinite(settings.radius))) throw new RangeError('radius must be positive');
  if (!Number.isInteger(settings.radialSegments) || settings.radialSegments < 3 || settings.radialSegments > MAXIMUM_SEGMENTS) {
    throw new RangeError(`radialSegments must be an integer from 3 to ${MAXIMUM_SEGMENTS}`);
  }
  if (!CURVES.includes(settings.curve)) throw new RangeError(`curve must be one of ${CURVES.join(', ')}`);
  for (const key of ['closed', 'caps', 'correctTwist']) {
    if (typeof settings[key] !== 'boolean') throw new TypeError(`${key} must be true or false`);
  }
  if (settings.initialNormal !== null && !(Array.isArray(settings.initialNormal) && settings.initialNormal.length === 3
    && settings.initialNormal.every(Number.isFinite))) {
    throw new TypeError('initialNormal must be null or [x, y, z]');
  }
  return settings;
}

/**
 * The tube as typed arrays {positions, normals, uvs, indices, pathLength}: rings of radialSegments + 1 vertices (the seam
 * repeats for UVs) at every sample, triangles counter-clockwise from outside, u along the path by arc length and v
 * around it. Open tubes get flat caps when caps is true; a closed tube ends on a copy of its first ring.
 */
export function tubeRmfData(points, options = {}) {
  const settings = settingsOf(options);
  const list = pointsOf(points, settings.closed);
  const radii = settings.radii === null ? list.map(() => settings.radius) : settings.radii;
  if (!Array.isArray(radii) || radii.length !== list.length || !radii.every((value) => value > 0 && Number.isFinite(value))) {
    throw new RangeError('radii must hold one positive radius per point');
  }
  let samples;
  if (settings.curve === POLYLINE) {
    const n = list.length;
    const tangents = list.map((point, k) => {
      const before = k > 0 ? unit(sub(point, list[k - 1])) : (settings.closed ? unit(sub(point, list[n - 1])) : null);
      const after = k < n - 1 ? unit(sub(list[k + 1], point)) : (settings.closed ? unit(sub(list[0], point)) : null);
      if (before && after) return length(add(before, after)) > 1e-9 ? unit(add(before, after)) : after;
      return before || after;
    });
    samples = {points: list.map((point) => [...point]), tangents, segments: list.map((_, k) => k), fractions: list.map(() => 0)};
  } else {
    samples = sampleCentripetalCatmullRom(list, settings.samplesPerSegment, settings.closed);
  }
  const frames = rotationMinimizingFrames(samples.points, samples.tangents, {closed: settings.closed,
    correctTwist: settings.correctTwist, initialNormal: settings.initialNormal});
  const count = samples.points.length;
  const sampleRadius = samples.segments.map((k, i) => {
    const next = settings.closed ? (k + 1) % list.length : Math.min(k + 1, list.length - 1);
    return radii[k] + (radii[next] - radii[k]) * samples.fractions[i];
  });
  const arcs = [0];
  for (let i = 1; i < count; i += 1) arcs.push(arcs[i - 1] + length(sub(samples.points[i], samples.points[i - 1])));
  const total = settings.closed ? arcs[count - 1] + length(sub(samples.points[0], samples.points[count - 1])) : arcs[count - 1];
  const rings = settings.closed ? count + 1 : count;
  const columns = settings.radialSegments + 1;
  const capped = settings.caps && !settings.closed;
  const vertexCount = rings * columns + (capped ? 2 * (columns + 1) : 0);
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  const ringOffsets = [];
  let vertex = 0;
  for (let ring = 0; ring < rings; ring += 1) {
    const i = ring % count;
    const centre = samples.points[i];
    const tangent = samples.tangents[i];
    const normal = frames.normals[i];
    const binormal = frames.binormals[i];
    // Polyline corners: stretch the ring along the bend by 1 / cos(half turn) so straight runs keep their radius.
    let bend = null;
    let stretch = 1;
    if (settings.curve === POLYLINE && (settings.closed || (i > 0 && i < count - 1))) {
      const before = unit(sub(centre, samples.points[(i - 1 + count) % count]));
      const after = unit(sub(samples.points[(i + 1) % count], centre));
      const turn = sub(after, before);
      if (length(turn) > 1e-9) {
        bend = unit(turn);
        stretch = 1 / Math.max(dot(tangent, before), 0.05);
      }
    }
    const previous = (i - 1 + count) % count;
    const next = (i + 1) % count;
    const hasBefore = settings.closed || i > 0;
    const hasAfter = settings.closed || i < count - 1;
    const r0 = hasBefore ? sampleRadius[previous] : sampleRadius[i];
    const r1 = hasAfter ? sampleRadius[next] : sampleRadius[i];
    const span = (hasBefore ? length(sub(centre, samples.points[previous])) : 0)
      + (hasAfter ? length(sub(samples.points[next], centre)) : 0);
    const slope = span > TINY ? (r1 - r0) / span : 0;
    ringOffsets.push(vertex);
    for (let j = 0; j < columns; j += 1) {
      const angle = (2 * Math.PI * (j % settings.radialSegments)) / settings.radialSegments;
      let offset = add(scale(normal, Math.cos(angle)), scale(binormal, Math.sin(angle)));
      const surfaceNormal = unit(sub(offset, scale(tangent, slope)));
      if (bend) offset = add(offset, scale(bend, dot(offset, bend) * (stretch - 1)));
      positions.set(add(centre, scale(offset, sampleRadius[i])), vertex * 3);
      normals.set(surfaceNormal, vertex * 3);
      uvs.set([ring === count ? 1 : arcs[i] / total, j / settings.radialSegments], vertex * 2);
      vertex += 1;
    }
  }
  const triangles = [];
  for (let ring = 0; ring < rings - 1; ring += 1) {
    for (let j = 0; j < settings.radialSegments; j += 1) {
      const a = ringOffsets[ring] + j;
      const b = a + 1;
      const d = ringOffsets[ring + 1] + j;
      const c = d + 1;
      triangles.push(a, b, c, a, c, d);
    }
  }
  if (capped) {
    for (const [i, facingForward] of [[0, false], [count - 1, true]]) {
      const centre = vertex;
      const direction = facingForward ? samples.tangents[i] : scale(samples.tangents[i], -1);
      positions.set(samples.points[i], centre * 3);
      normals.set(direction, centre * 3);
      uvs.set([0.5, 0.5], centre * 2);
      vertex += 1;
      for (let j = 0; j < columns; j += 1) {
        const source = ringOffsets[i] + j;
        positions.set(positions.subarray(source * 3, source * 3 + 3), vertex * 3);
        normals.set(direction, vertex * 3);
        const angle = (2 * Math.PI * j) / settings.radialSegments;
        uvs.set([0.5 + 0.5 * Math.cos(angle), 0.5 + 0.5 * Math.sin(angle)], vertex * 2);
        vertex += 1;
      }
      for (let j = 0; j < settings.radialSegments; j += 1) {
        const p = centre + 1 + j;
        if (facingForward) triangles.push(centre, p, p + 1);
        else triangles.push(centre, p + 1, p);
      }
    }
  }
  const indices = vertexCount > 65535 ? Uint32Array.from(triangles) : Uint16Array.from(triangles);
  return {positions, normals, uvs, indices, pathLength: total};
}

/** A THREE.BufferGeometry of the tube with position, normal and uv attributes and an index. */
export function createTubeRmfGeometry(THREE, points, options = {}) {
  const data = tubeRmfData(points, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
