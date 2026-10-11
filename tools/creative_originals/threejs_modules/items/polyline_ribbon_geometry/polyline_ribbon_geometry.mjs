// Flat ribbons along polylines for three.js: roads, rivers, paint strokes, motion trails and track outlines. The
// ribbon faces a fixed up vector (lying on the ground) or a camera position (a trail that always faces the viewer),
// keeps its width through corners with miter joins, falls back to a bevel past the miter limit, takes a width per
// point, and lays UVs along its length (stretched or tiled) and across it. Original Baltor implementation;
// miterJoin and polylineRibbonData work on plain arrays and typed arrays alone.

/** Default options of polylineRibbonData and createPolylineRibbonGeometry. */
export const POLYLINE_RIBBON_DEFAULTS = Object.freeze({
  width: 0.2,
  widths: null,
  up: Object.freeze([0, 1, 0]),
  cameraPosition: null,
  miterLimit: 4,
  closed: false,
  uvMode: 'stretch',
  uvScale: 1,
});

const UV_MODES = Object.freeze(['stretch', 'tile']);
const TILE = 'tile';
const TINY = 1e-9;

const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const scale = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const length = (a) => Math.hypot(a[0], a[1], a[2]);
const unit = (a) => scale(a, 1 / length(a));

function vector3(value, name) {
  if (!Array.isArray(value) || value.length !== 3 || !value.every(Number.isFinite)) {
    throw new TypeError(`${name} must be [x, y, z] with finite numbers`);
  }
  return value;
}

/**
 * The join where a ribbon of half width halfWidth turns from directionIn to directionOut while facing `facing`
 * (directions and facing are unit vectors). Returns {miter, scale, offset, turn, sideIn, sideOut}: scale is the miter
 * length over the half width (1 / cos of half the turn), offset the right-side offset of the miter point (limited to
 * miterLimit when the join is a bevel), turn +1 when the path turns left about the facing (the right side is the
 * outside) and -1 otherwise, and sideIn and sideOut the right-side offsets of the two segments.
 */
export function miterJoin(directionIn, directionOut, facing, halfWidth, miterLimit = POLYLINE_RIBBON_DEFAULTS.miterLimit) {
  vector3(directionIn, 'directionIn');
  vector3(directionOut, 'directionOut');
  vector3(facing, 'facing');
  if (!(halfWidth > 0)) throw new RangeError('halfWidth must be positive');
  if (!(miterLimit >= 1)) throw new RangeError('miterLimit must be at least 1');
  const before = cross(directionIn, facing);
  const after = cross(directionOut, facing);
  if (length(before) < TINY || length(after) < TINY) throw new RangeError('a segment points along the facing direction');
  const sideIn = unit(before);
  const sideOut = unit(after);
  const turning = dot(cross(directionIn, directionOut), facing);
  const turn = turning < 0 ? -1 : 1;
  const sum = add(sideIn, sideOut);
  if (length(sum) < TINY) {
    return {miter: false, scale: Infinity, offset: [0, 0, 0], turn, sideIn: scale(sideIn, halfWidth),
      sideOut: scale(sideOut, halfWidth)};
  }
  const bisector = unit(sum);
  const ratio = 1 / dot(bisector, sideIn);
  const miter = ratio <= miterLimit;
  return {miter, scale: ratio, offset: scale(bisector, halfWidth * Math.min(ratio, miterLimit)), turn,
    sideIn: scale(sideIn, halfWidth), sideOut: scale(sideOut, halfWidth)};
}

function settingsOf(options) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(POLYLINE_RIBBON_DEFAULTS, key)) throw new TypeError(`unknown ribbon option ${key}`);
  }
  const settings = {...POLYLINE_RIBBON_DEFAULTS, ...options};
  if (!(settings.width > 0 && Number.isFinite(settings.width))) throw new RangeError('width must be positive');
  vector3(settings.up, 'up');
  if (length(settings.up) < TINY) throw new RangeError('up must not be zero');
  if (settings.cameraPosition !== null) vector3(settings.cameraPosition, 'cameraPosition');
  if (!(settings.miterLimit >= 1 && Number.isFinite(settings.miterLimit))) throw new RangeError('miterLimit must be at least 1');
  if (typeof settings.closed !== 'boolean') throw new TypeError('closed must be true or false');
  if (!UV_MODES.includes(settings.uvMode)) throw new RangeError(`uvMode must be one of ${UV_MODES.join(', ')}`);
  if (!(settings.uvScale > 0 && Number.isFinite(settings.uvScale))) throw new RangeError('uvScale must be positive');
  return settings;
}

function pointsOf(points, closed) {
  if (!Array.isArray(points)) throw new TypeError('points is an array of [x, y, z]');
  const list = points.map((point, index) => [...vector3(point, `point ${index}`)]);
  if (list.length < (closed ? 3 : 2)) throw new RangeError(`a ${closed ? 'closed' : 'open'} ribbon needs ${closed ? 3 : 2} points`);
  const count = closed ? list.length : list.length - 1;
  for (let k = 0; k < count; k += 1) {
    if (length(sub(list[(k + 1) % list.length], list[k])) < TINY) throw new RangeError(`points ${k} and ${k + 1} coincide`);
  }
  return list;
}

/**
 * The ribbon as typed arrays {positions, normals, uvs, indices, length}: two vertices per station (left with v = 0,
 * right with v = 1; right is cross(direction, facing)), one station per point at a miter and two at a bevel, triangles
 * counter-clockwise seen from the facing side, normals along the facing direction. u is the distance along the path
 * over its length (stretch) or over uvScale (tile).
 */
export function polylineRibbonData(points, options = {}) {
  const settings = settingsOf(options);
  const list = pointsOf(points, settings.closed);
  const n = list.length;
  const widths = settings.widths === null ? list.map(() => settings.width) : settings.widths;
  if (!Array.isArray(widths) || widths.length !== n || !widths.every((value) => value > 0 && Number.isFinite(value))) {
    throw new RangeError('widths must hold one positive width per point');
  }
  const facing = list.map((point) => unit(settings.cameraPosition === null ? settings.up : sub(settings.cameraPosition, point)));
  const segmentCount = settings.closed ? n : n - 1;
  const directions = [];
  for (let s = 0; s < segmentCount; s += 1) directions.push(unit(sub(list[(s + 1) % n], list[s])));
  const arcs = [0];
  for (let i = 1; i < n; i += 1) arcs.push(arcs[i - 1] + length(sub(list[i], list[i - 1])));
  const total = settings.closed ? arcs[n - 1] + length(sub(list[0], list[n - 1])) : arcs[n - 1];
  const stationsAt = (i) => {
    const point = list[i];
    const half = widths[i] / 2;
    const incoming = i > 0 ? i - 1 : (settings.closed ? segmentCount - 1 : -1);
    const outgoing = i < segmentCount ? i : -1;
    if (incoming < 0 || outgoing < 0) {
      const direction = directions[incoming < 0 ? outgoing : incoming];
      const side = cross(direction, facing[i]);
      if (length(side) < TINY) throw new RangeError(`the path at point ${i} points along the facing direction`);
      const offset = scale(unit(side), half);
      return [{left: sub(point, offset), right: add(point, offset), normal: facing[i]}];
    }
    const join = miterJoin(directions[incoming], directions[outgoing], facing[i], half, settings.miterLimit);
    if (join.miter) return [{left: sub(point, join.offset), right: add(point, join.offset), normal: facing[i]}];
    if (join.turn > 0) {
      const inner = sub(point, join.offset);
      return [{left: inner, right: add(point, join.sideIn), normal: facing[i]},
        {left: inner, right: add(point, join.sideOut), normal: facing[i]}];
    }
    const inner = add(point, join.offset);
    return [{left: sub(point, join.sideIn), right: inner, normal: facing[i]},
      {left: sub(point, join.sideOut), right: inner, normal: facing[i]}];
  };
  const stations = [];
  const firstStations = stationsAt(0);
  // A closed ribbon starts on its first point's outgoing station and ends on copies of all its stations at u = 1.
  stations.push(...(settings.closed ? firstStations.slice(-1) : firstStations).map((station) => ({...station, distance: 0})));
  for (let i = 1; i < n; i += 1) stations.push(...stationsAt(i).map((station) => ({...station, distance: arcs[i]})));
  if (settings.closed) stations.push(...firstStations.map((station) => ({...station, distance: total})));
  const vertexCount = stations.length * 2;
  const positions = new Float32Array(vertexCount * 3);
  const normals = new Float32Array(vertexCount * 3);
  const uvs = new Float32Array(vertexCount * 2);
  stations.forEach((station, k) => {
    const u = settings.uvMode === TILE ? station.distance / settings.uvScale : station.distance / total;
    positions.set(station.left, k * 6);
    positions.set(station.right, k * 6 + 3);
    normals.set(station.normal, k * 6);
    normals.set(station.normal, k * 6 + 3);
    uvs.set([u, 0, u, 1], k * 4);
  });
  const triangles = [];
  const area = (a, b, c) => length(cross(sub(stations[0].left, stations[0].left), [0, 0, 0])) + length(cross(
    sub(positions.subarray(b * 3, b * 3 + 3), positions.subarray(a * 3, a * 3 + 3)),
    sub(positions.subarray(c * 3, c * 3 + 3), positions.subarray(a * 3, a * 3 + 3))));
  for (let k = 0; k + 1 < stations.length; k += 1) {
    const a = 2 * k;
    const b = a + 1;
    const d = a + 2;
    const c = a + 3;
    if (area(a, b, d) > TINY * TINY) triangles.push(a, b, d);
    if (area(b, c, d) > TINY * TINY) triangles.push(b, c, d);
  }
  const indices = vertexCount > 65535 ? Uint32Array.from(triangles) : Uint16Array.from(triangles);
  return {positions, normals, uvs, indices, length: total};
}

/** A THREE.BufferGeometry of the ribbon with position, normal and uv attributes and an index. */
export function createPolylineRibbonGeometry(THREE, points, options = {}) {
  const data = polylineRibbonData(points, options);
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(data.positions, 3));
  geometry.setAttribute('normal', new THREE.BufferAttribute(data.normals, 3));
  geometry.setAttribute('uv', new THREE.BufferAttribute(data.uvs, 2));
  geometry.setIndex(new THREE.BufferAttribute(data.indices, 1));
  geometry.computeBoundingBox();
  geometry.computeBoundingSphere();
  return geometry;
}
