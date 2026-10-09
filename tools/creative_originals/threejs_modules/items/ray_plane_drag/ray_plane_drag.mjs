// Pointer rays and plane dragging for three.js: normalized device coordinates from a pointer, the world-space ray
// under it for perspective and orthographic cameras (unprojecting the near and far clip planes), ray-plane
// intersection, and a drag controller that keeps the grab offset and can snap to a grid laid in the plane. Original
// Baltor implementation; it works on plain arrays (camera.projectionMatrixInverse.elements, camera.matrixWorld.elements).

/** Default options of PlaneDrag: the plane n . p + constant = 0, and a grid step (0 for no snapping). */
export const PLANE_DRAG_DEFAULTS = Object.freeze({normal: Object.freeze([0, 1, 0]), constant: 0, snap: 0});

const PARALLEL_EPSILON = 1e-12;

function checkMatrix(matrix, name) {
  if (!(matrix && matrix.length === 16 && Array.prototype.every.call(matrix, Number.isFinite))) {
    throw new RangeError(`${name} must hold 16 finite numbers`);
  }
}

function checkVector(vector, name) {
  if (!(vector && vector.length === 3 && Array.prototype.every.call(vector, Number.isFinite))) {
    throw new RangeError(`${name} must be three finite numbers`);
  }
}

function normalize(vector, name) {
  const length = Math.hypot(vector[0], vector[1], vector[2]);
  if (!(length > 0)) throw new RangeError(`${name} must not be zero`);
  return [vector[0] / length, vector[1] / length, vector[2] / length];
}

function transformPoint(matrix, x, y, z, w) {
  return [0, 1, 2, 3].map((row) => matrix[row] * x + matrix[4 + row] * y + matrix[8 + row] * z + matrix[12 + row] * w);
}

/**
 * Normalized device coordinates [x, y] in [-1, 1] for a pointer at (clientX, clientY) over an element whose bounding
 * rectangle is rect = {left, top, width, height} (element.getBoundingClientRect()). +y is up.
 */
export function ndcFromPointer(clientX, clientY, rect) {
  if (!(rect && rect.width > 0 && rect.height > 0)) throw new RangeError('rect needs a positive width and height');
  return [((clientX - rect.left) / rect.width) * 2 - 1, -((clientY - rect.top) / rect.height) * 2 + 1];
}

/** The inverse of a column-major 4 x 4 matrix by cofactors, as a Float64Array; a singular matrix throws RangeError. */
export function invertMatrix(m) {
  checkMatrix(m, 'matrix');
  const inverse = new Float64Array(16);
  const minor = (rows, columns) => {
    const at = (r, c) => m[columns[c] * 4 + rows[r]];
    return at(0, 0) * (at(1, 1) * at(2, 2) - at(1, 2) * at(2, 1)) - at(0, 1) * (at(1, 0) * at(2, 2) - at(1, 2) * at(2, 0))
      + at(0, 2) * (at(1, 0) * at(2, 1) - at(1, 1) * at(2, 0));
  };
  const others = (skip) => [0, 1, 2, 3].filter((index) => index !== skip);
  let determinant = 0;
  for (let column = 0; column < 4; column += 1) {
    determinant += (column % 2 === 0 ? 1 : -1) * m[column * 4] * minor(others(0), others(column));
  }
  if (!(Math.abs(determinant) > 1e-300)) throw new RangeError('the matrix is singular');
  for (let row = 0; row < 4; row += 1) {
    for (let column = 0; column < 4; column += 1) {
      const cofactor = ((row + column) % 2 === 0 ? 1 : -1) * minor(others(row), others(column));
      inverse[row * 4 + column] = cofactor / determinant;
    }
  }
  return inverse;
}

/**
 * The world-space ray under a point in normalized device coordinates: {origin, direction} with origin on the near
 * plane and a unit direction. It unprojects the clip-space points at depth nearDepth (-1 for WebGL, 0 for WebGPU)
 * and 1, so it serves perspective and orthographic cameras alike. Pass camera.projectionMatrixInverse.elements and
 * camera.matrixWorld.elements.
 */
export function rayFromCamera(ndcX, ndcY, inverseProjection, cameraWorld, nearDepth = -1) {
  checkMatrix(inverseProjection, 'inverseProjection');
  checkMatrix(cameraWorld, 'cameraWorld');
  if (!(Number.isFinite(ndcX) && Number.isFinite(ndcY))) throw new RangeError('ndc coordinates must be finite');
  if (!(nearDepth === -1 || nearDepth === 0)) throw new RangeError('nearDepth is -1 (WebGL) or 0 (WebGPU)');
  const points = [nearDepth, 1].map((depth) => {
    const view = transformPoint(inverseProjection, ndcX, ndcY, depth, 1);
    if (!(Math.abs(view[3]) > 1e-300)) throw new RangeError('the point unprojects to infinity');
    const world = transformPoint(cameraWorld, view[0] / view[3], view[1] / view[3], view[2] / view[3], 1);
    return [world[0], world[1], world[2]];
  });
  const direction = normalize([points[1][0] - points[0][0], points[1][1] - points[0][1], points[1][2] - points[0][2]],
    'the ray direction');
  return {origin: points[0], direction};
}

/** The plane through point with the given normal, as {normal (unit), constant} with normal . p + constant = 0. */
export function planeFromNormalAndPoint(normal, point) {
  checkVector(normal, 'normal');
  checkVector(point, 'point');
  const unit = normalize(normal, 'normal');
  return {normal: unit, constant: -(unit[0] * point[0] + unit[1] * point[1] + unit[2] * point[2])};
}

/**
 * The distance t >= 0 along the ray to the plane normal . p + constant = 0, or null when the ray runs parallel to the
 * plane or points away from it. The hit point is origin + t * direction.
 */
export function intersectRayPlane(origin, direction, normal, constant) {
  checkVector(origin, 'origin');
  checkVector(direction, 'direction');
  checkVector(normal, 'normal');
  const facing = normal[0] * direction[0] + normal[1] * direction[1] + normal[2] * direction[2];
  if (Math.abs(facing) < PARALLEL_EPSILON) return null;
  const t = -(normal[0] * origin[0] + normal[1] * origin[1] + normal[2] * origin[2] + constant) / facing;
  return t >= 0 ? t : null;
}

/**
 * Drag an object across a plane: begin(ray, objectPosition) stores where the ray met the plane and the object's
 * offset from that point; move(ray) returns the new object position (hit + offset, snapped to a grid of step snap
 * laid in the plane) or null when the ray misses the plane; end() stops. Rays are {origin, direction}.
 */
export class PlaneDrag {
  constructor(options = {}) {
    for (const key of Object.keys(options)) {
      if (!Object.prototype.hasOwnProperty.call(PLANE_DRAG_DEFAULTS, key)) throw new TypeError(`unknown plane drag option ${key}`);
    }
    const settings = {...PLANE_DRAG_DEFAULTS, ...options};
    checkVector(settings.normal, 'normal');
    if (!Number.isFinite(settings.constant)) throw new RangeError('constant must be finite');
    if (!(settings.snap >= 0 && Number.isFinite(settings.snap))) throw new RangeError('snap must be zero or positive');
    this.normal = normalize(settings.normal, 'normal');
    this.constant = settings.constant / Math.hypot(...settings.normal);
    this.snap = settings.snap;
    const [nx, ny, nz] = this.normal;
    const helper = Math.abs(nx) < 0.9 ? [1, 0, 0] : [0, 0, 1];
    const along = helper[0] * nx + helper[1] * ny + helper[2] * nz;
    this.axisU = normalize([helper[0] - along * nx, helper[1] - along * ny, helper[2] - along * nz], 'axis');
    const [ux, uy, uz] = this.axisU;
    this.axisV = [ny * uz - nz * uy, nz * ux - nx * uz, nx * uy - ny * ux];
    this.offset = null;
  }

  get active() {
    return this.offset !== null;
  }

  hit(ray) {
    const t = intersectRayPlane(ray.origin, ray.direction, this.normal, this.constant);
    if (t === null) return null;
    return [0, 1, 2].map((axis) => ray.origin[axis] + t * ray.direction[axis]);
  }

  begin(ray, objectPosition) {
    checkVector(objectPosition, 'objectPosition');
    const point = this.hit(ray);
    this.offset = point === null ? null : [0, 1, 2].map((axis) => objectPosition[axis] - point[axis]);
    return this.offset !== null;
  }

  move(ray) {
    if (this.offset === null) return null;
    const point = this.hit(ray);
    if (point === null) return null;
    const position = [0, 1, 2].map((axis) => point[axis] + this.offset[axis]);
    return this.snap > 0 ? this.snapToGrid(position) : position;
  }

  snapToGrid(position) {
    if (!(this.snap > 0)) return [...position];
    const base = this.normal.map((value) => -this.constant * value);
    const relative = [0, 1, 2].map((axis) => position[axis] - base[axis]);
    const dot = (axis) => axis[0] * relative[0] + axis[1] * relative[1] + axis[2] * relative[2];
    const u = Math.round(dot(this.axisU) / this.snap) * this.snap;
    const v = Math.round(dot(this.axisV) / this.snap) * this.snap;
    const height = dot(this.normal);
    return [0, 1, 2].map((axis) => base[axis] + u * this.axisU[axis] + v * this.axisV[axis] + height * this.normal[axis]);
  }

  end() {
    this.offset = null;
  }
}
