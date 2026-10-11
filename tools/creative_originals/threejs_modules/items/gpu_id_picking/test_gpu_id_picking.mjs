// Known answers for GPU picking: ids round-trip through three bytes at every byte boundary, the shader's float
// encoding (floor, mod, divide by 255) gives the same bytes, the material and instance attributes are wired, and the
// picker (run on a stand-in renderer that "draws" the frontmost mesh under the view offset with the material it is
// given) returns the right ids and restores every material, the background, the camera view and the renderer state.
// A decoder with the bytes in the wrong order is the known-wrong control the round-trip check must refuse.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  PICKING_DEFAULTS, PICKING_FRAGMENT, PICKING_VERTEX, PICK_ID_LIMIT, createPicker, createPickingMaterial, decodeId,
  encodeId, setInstancePickIds,
} from './gpu_id_picking.mjs';

const EDGES = [0, 1, 255, 256, 65535, 65536, 65537, 1000000, PICK_ID_LIMIT];

function roundTripProblems(encode, decode) {
  const problems = [];
  for (const id of EDGES) {
    const bytes = encode(id);
    if (bytes.some((value) => !(Number.isInteger(value) && value >= 0 && value <= 255))) problems.push(`${id} bytes ${bytes}`);
    if (decode(...bytes) !== id) problems.push(`${id} came back as ${decode(...bytes)}`);
  }
  return problems;
}

// The fragment shader's arithmetic, in float32 as a GPU would do it, then the 8-bit store round(c * 255).
function shaderBytes(id, bias = 0.25) {
  const f = Math.fround;
  const value = f(Math.floor(f(f(id) + bias)));
  const red = f(value - 256 * Math.floor(f(value / 256)));
  const green = f(Math.floor(f(value / 256)) - 256 * Math.floor(f(Math.floor(f(value / 256)) / 256)));
  const blue = f(Math.floor(f(value / 65536)));
  return [red, green, blue].map((channel) => Math.round(f(f(channel / 255) * 255)));
}

test('ids round-trip through three bytes at every byte boundary', () => {
  assert.deepEqual(roundTripProblems(encodeId, decodeId), []);
  assert.deepEqual(encodeId(65793), [1, 1, 1]);
  assert.equal(decodeId(255, 255, 255), PICK_ID_LIMIT);
});

test('known wrong: a decoder that reads the bytes in the wrong order is refused', () => {
  assert.notDeepEqual(roundTripProblems(encodeId, (red, green, blue) => blue + green * 256 + red * 65536), []);
  assert.throws(() => encodeId(PICK_ID_LIMIT + 1), RangeError);
  assert.throws(() => encodeId(-1), RangeError);
  assert.throws(() => encodeId(2.5), RangeError);
  assert.throws(() => decodeId(256, 0, 0), RangeError);
});

test('the shader arithmetic writes the same bytes as encodeId, in float32', () => {
  for (const id of [...EDGES, 8388609, 9999999, 16777213]) assert.deepEqual(shaderBytes(id), encodeId(id), `id ${id}`);
  assert.match(PICKING_FRAGMENT, /floor\(id \+ 0\.25\)/);
  // Known wrong: adding 0.5 in float32 rounds an odd id above 2^23 up to the next even number.
  assert.notDeepEqual(shaderBytes(9999999, 0.5), encodeId(9999999));
  assert.match(PICKING_FRAGMENT, /mod\(value, 256\.0\)/);
  assert.match(PICKING_VERTEX, /#ifdef BALTOR_PICK_INSTANCED/);
});

const FakeThree = {
  NoBlending: 0, FrontSide: 0, BackSide: 1, DoubleSide: 2, UnsignedByteType: 1009, RGBAFormat: 1023, NearestFilter: 1003,
  ShaderMaterial: class { constructor(parameters) { Object.assign(this, parameters); this.disposed = false; } dispose() { this.disposed = true; } },
  WebGLRenderTarget: class { constructor(width, height, options) { Object.assign(this, {width, height, options}); } dispose() { this.disposed = true; } },
  Vector2: class { constructor() { this.x = 0; this.y = 0; } },
  Color: class { constructor() { this.hex = 0x123456; } },
  InstancedBufferAttribute: class { constructor(array, itemSize) { Object.assign(this, {array, itemSize}); } },
};

test('createPickingMaterial and setInstancePickIds wire ids', () => {
  const material = createPickingMaterial(FakeThree, {id: 70000});
  assert.equal(material.uniforms.uPickId.value, 70000);
  assert.deepEqual(material.defines, {});
  assert.equal(material.blending, FakeThree.NoBlending);
  assert.deepEqual(createPickingMaterial(FakeThree, {instanced: true}).defines, {BALTOR_PICK_INSTANCED: ''});
  const attributes = {};
  const mesh = {isInstancedMesh: true, count: 3, geometry: {setAttribute: (name, value) => { attributes[name] = value; }}};
  setInstancePickIds(FakeThree, mesh, [5, 6, 16777215]);
  assert.deepEqual(Array.from(attributes.pickId.array), [5, 6, 16777215]);
  assert.throws(() => setInstancePickIds(FakeThree, mesh, [1, 2]), RangeError);
  assert.throws(() => setInstancePickIds(FakeThree, {isMesh: true}, [1]), TypeError);
  assert.throws(() => createPickingMaterial(FakeThree, {pickId: 3}), TypeError);
  assert.throws(() => createPickingMaterial(FakeThree, {toString: 1}), TypeError, 'an inherited name is not an option');
  assert.deepEqual({...PICKING_DEFAULTS}, {id: 0, instanced: false});
});

// A renderer that draws the frontmost visible mesh covering the view offset's pixel with the material it holds.
function fakeRenderer(log) {
  let target = null;
  let lastScene = null;
  let lastCamera = null;
  return {
    getSize(vector) { vector.x = 100; vector.y = 50; return vector; },
    getRenderTarget: () => target,
    setRenderTarget(value) { target = value; log.push(['target', value === null ? null : 'picking']); },
    getClearAlpha: () => 1,
    getClearColor(colour) { return colour; },
    setClearColor(colour, alpha) { log.push(['clear colour', typeof colour === 'number' ? colour : colour.hex, alpha]); },
    clear() {},
    render(scene, camera) {
      lastScene = scene;
      lastCamera = camera;
      log.push(['render', scene.children.filter((child) => child.visible).map((child) => child.name)]);
    },
    readRenderTargetPixels(_target, _x, _y, _width, _height, buffer) {
      const {offsetX, offsetY} = lastCamera.view;
      const covering = lastScene.children.filter((child) => child.isMesh && child.visible && child.userData.covers(offsetX, offsetY));
      covering.sort((a, b) => a.userData.depth - b.userData.depth);
      buffer.fill(0);
      if (covering.length === 0) return;
      const front = covering[0];
      const id = front.material.defines.BALTOR_PICK_INSTANCED === '' ? front.geometry.attributes.pickId.array[0]
        : front.material.uniforms.uPickId.value;
      buffer.set([...encodeId(id), 255]);
    },
  };
}

function fakeScene() {
  const box = (name, pickId, depth, covers) => ({name, isMesh: true, visible: true, userData: {pickId, depth, covers},
    material: {side: 2, name: `${name} material`}, geometry: {getAttribute: () => undefined}});
  const left = box('left', 70000, 5, (x) => x < 50);
  const cover = box('cover', undefined, 1, (x, y) => x < 20 && y < 10);
  const crowd = {name: 'crowd', isMesh: true, isInstancedMesh: true, visible: true, userData: {depth: 3, covers: (x) => x >= 60},
    material: {side: 0, name: 'crowd material'}, geometry: {attributes: {pickId: {array: [1000000]}}, getAttribute(name) {
      return this.attributes[name];
    }}};
  const dots = {name: 'dots', isPoints: true, visible: true};
  const children = [left, cover, crowd, dots];
  return {children, background: 'sky', overrideMaterial: null, traverse(visit) { children.forEach(visit); }};
}

test('the picker returns the frontmost id and restores every piece of state', () => {
  const log = [];
  const picker = createPicker(FakeThree, fakeRenderer(log));
  const scene = fakeScene();
  const camera = {view: null, setViewOffset(...values) {
    this.view = {enabled: true, fullWidth: values[0], fullHeight: values[1], offsetX: values[2], offsetY: values[3],
      width: values[4], height: values[5]};
  }, clearViewOffset() { this.view.enabled = false; }};
  const materials = scene.children.map((child) => child.material);
  assert.equal(picker.pick(scene, camera, 30.7, 20), 70000);
  assert.equal(picker.pick(scene, camera, 10, 5), 0, 'a mesh without an id hides what is behind it');
  assert.equal(picker.pick(scene, camera, 75, 40), 1000000, 'an instanced mesh reports its pickId attribute');
  assert.equal(picker.pick(scene, camera, 55, 40), 0, 'background');
  const renders = log.filter((entry) => entry[0] === 'render');
  assert.equal(renders.length, 4);
  assert.ok(renders.every((entry) => !entry[1].includes('dots')), 'points are hidden while picking');
  assert.deepEqual(scene.children.map((child) => child.material), materials);
  assert.equal(scene.children[3].visible, true);
  assert.equal(scene.background, 'sky');
  assert.equal(camera.view.enabled, false);
  assert.deepEqual(log[log.length - 1], ['clear colour', 0x123456, 1]);
  assert.equal(picker.pick(scene, camera, 100, 10), 0, 'outside the canvas nothing is rendered');
  assert.equal(log.filter((entry) => entry[0] === 'render').length, 4);
  picker.dispose();
});
