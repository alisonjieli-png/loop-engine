// GPU picking for three.js: 24-bit object ids written as colours by a picking ShaderMaterial (one id per mesh, or one
// per instance through a pickId attribute), and a picker that renders only the pixel under the pointer, through
// camera.setViewOffset into a 1 x 1 render target, and reads the id back. Every material, the background and the
// camera are restored afterwards. Original Baltor implementation; three.js is passed in.

/** The largest id a picking colour can hold (2^24 - 1); id 0 means nothing (background or an unnamed occluder). */
export const PICK_ID_LIMIT = 16777215;

/** Default options of createPickingMaterial. */
export const PICKING_DEFAULTS = Object.freeze({id: 0, instanced: false});

/** Vertex stage: the id from uPickId, or per instance from the pickId attribute when BALTOR_PICK_INSTANCED is set. */
export const PICKING_VERTEX = `
#ifdef BALTOR_PICK_INSTANCED
attribute float pickId;
#endif
uniform float uPickId;
flat varying float vPickId;

void main() {
#ifdef BALTOR_PICK_INSTANCED
  vPickId = pickId;
#else
  vPickId = uPickId;
#endif
  mat4 placement = modelMatrix;
#ifdef USE_INSTANCING
  placement = modelMatrix * instanceMatrix;
#endif
  gl_Position = projectionMatrix * viewMatrix * placement * vec4(position, 1.0);
}
`;

/**
 * Fragment stage: the id as bytes, red the lowest. No tone mapping or colour space conversion: the bytes are data.
 * floor(id + 0.25) keeps an exact integer in float32 all the way to 2^24 (adding 0.5 would round odd ids above 2^23
 * up to the next even number).
 */
export const PICKING_FRAGMENT = `
flat varying float vPickId;

vec3 encodePickId(float id) {
  float value = floor(id + 0.25);
  float red = mod(value, 256.0);
  float green = mod(floor(value / 256.0), 256.0);
  float blue = floor(value / 65536.0);
  return vec3(red, green, blue) / 255.0;
}

void main() {
  gl_FragColor = vec4(encodePickId(vPickId), 1.0);
}
`;

function checkId(id) {
  if (!(Number.isInteger(id) && id >= 0 && id <= PICK_ID_LIMIT)) {
    throw new RangeError(`a pick id is an integer from 0 to ${PICK_ID_LIMIT}, got ${id}`);
  }
  return id;
}

/** The id as the [red, green, blue] bytes the fragment shader writes. */
export function encodeId(id) {
  checkId(id);
  return [id & 255, (id >>> 8) & 255, (id >>> 16) & 255];
}

/** The id stored in three bytes (the inverse of encodeId). */
export function decodeId(red, green, blue) {
  for (const value of [red, green, blue]) {
    if (!(Number.isInteger(value) && value >= 0 && value <= 255)) throw new RangeError(`a byte is 0 to 255, got ${value}`);
  }
  return red + green * 256 + blue * 65536;
}

/**
 * A picking ShaderMaterial: uniforms.uPickId.value holds the id, or, with instanced true, each instance's id comes
 * from the pickId attribute (see setInstancePickIds).
 */
export function createPickingMaterial(THREE, options = {}) {
  for (const key of Object.keys(options)) {
    if (!Object.prototype.hasOwnProperty.call(PICKING_DEFAULTS, key)) throw new TypeError(`unknown picking option ${key}`);
  }
  const settings = {...PICKING_DEFAULTS, ...options};
  checkId(settings.id);
  return new THREE.ShaderMaterial({
    name: 'BaltorPickingMaterial',
    uniforms: {uPickId: {value: settings.id}},
    defines: settings.instanced === true ? {BALTOR_PICK_INSTANCED: ''} : {},
    vertexShader: PICKING_VERTEX,
    fragmentShader: PICKING_FRAGMENT,
    blending: THREE.NoBlending,
    toneMapped: false,
  });
}

/** Give each instance of an InstancedMesh its own id through a pickId attribute on its (shared) geometry. */
export function setInstancePickIds(THREE, mesh, ids) {
  if (!(mesh && mesh.isInstancedMesh === true)) throw new TypeError('setInstancePickIds needs an InstancedMesh');
  if (!(ids && ids.length === mesh.count)) throw new RangeError('one id per instance is needed');
  const values = new Float32Array(ids.length);
  for (let index = 0; index < ids.length; index += 1) values[index] = checkId(ids[index]);
  mesh.geometry.setAttribute('pickId', new THREE.InstancedBufferAttribute(values, 1));
  return mesh;
}

/**
 * A picker for one renderer. pick(scene, camera, x, y) returns the id at canvas pixel (x, y), counted from the top
 * left in the same units as renderer.getSize(): object.userData.pickId for a mesh, the pickId attribute for an
 * instanced mesh, 0 for background and for meshes without an id (they still hide what is behind them). Points,
 * lines and sprites are hidden while picking. dispose() frees the render target and the cached materials.
 */
export function createPicker(THREE, renderer) {
  const target = new THREE.WebGLRenderTarget(1, 1, {
    type: THREE.UnsignedByteType, format: THREE.RGBAFormat, minFilter: THREE.NearestFilter,
    magFilter: THREE.NearestFilter, generateMipmaps: false,
  });
  const pixel = new Uint8Array(4);
  const size = new THREE.Vector2();
  const clearColour = new THREE.Color();
  const cache = new Map();
  const materialFor = (id, instanced, side) => {
    const key = `${instanced ? 'instanced' : id}|${side}`;
    if (!cache.has(key)) {
      const material = createPickingMaterial(THREE, {id: instanced ? 0 : id, instanced});
      material.side = side;
      cache.set(key, material);
    }
    return cache.get(key);
  };
  return {
    pick(scene, camera, x, y) {
      renderer.getSize(size);
      if (!(x >= 0 && x < size.x && y >= 0 && y < size.y)) return 0;
      const swapped = [];
      const hidden = [];
      const saved = {
        target: renderer.getRenderTarget(), alpha: renderer.getClearAlpha(), background: scene.background,
        override: scene.overrideMaterial, view: camera.view && camera.view.enabled ? {...camera.view} : null,
      };
      renderer.getClearColor(clearColour);
      try {
        scene.traverse((object) => {
          if (object.isMesh === true) {
            const instanced = object.isInstancedMesh === true && Boolean(object.geometry.getAttribute('pickId'));
            const named = Number.isInteger(object.userData.pickId) ? checkId(object.userData.pickId) : 0;
            const original = Array.isArray(object.material) ? object.material[0] : object.material;
            swapped.push([object, object.material]);
            object.material = materialFor(named, instanced, original ? original.side : THREE.FrontSide);
          } else if ((object.isPoints === true || object.isLine === true || object.isSprite === true) && object.visible) {
            hidden.push(object);
            object.visible = false;
          }
        });
        scene.background = null;
        scene.overrideMaterial = null;
        camera.setViewOffset(size.x, size.y, Math.floor(x), Math.floor(y), 1, 1);
        renderer.setRenderTarget(target);
        renderer.setClearColor(0x000000, 0);
        renderer.clear();
        renderer.render(scene, camera);
        renderer.readRenderTargetPixels(target, 0, 0, 1, 1, pixel);
      } finally {
        if (saved.view) {
          const view = saved.view;
          camera.setViewOffset(view.fullWidth, view.fullHeight, view.offsetX, view.offsetY, view.width, view.height);
        } else {
          camera.clearViewOffset();
        }
        renderer.setRenderTarget(saved.target);
        renderer.setClearColor(clearColour, saved.alpha);
        scene.background = saved.background;
        scene.overrideMaterial = saved.override;
        for (const [object, material] of swapped) object.material = material;
        for (const object of hidden) object.visible = true;
      }
      return pixel[3] === 0 ? 0 : decodeId(pixel[0], pixel[1], pixel[2]);
    },
    dispose() {
      target.dispose();
      for (const material of cache.values()) material.dispose();
      cache.clear();
    },
  };
}
