// Verification page script of the threejs_modules family. native.py writes page.html next to a copy of the package,
// opens it in headless Chrome and awaits window.__baltorVerification. This file is part of the verifier, never of a
// package.
//
// run(config) imports the item's module and its demo/scene.mjs, makes a three.js WebGLRenderer on a WebGL 2 canvas
// of config.size pixels, hands the demo a small harness, renders the scene the demo returns (and the baseline scene
// when it declares one) to the canvas, reads the pixels back and returns them with every shader compile or link
// error, the WebGL error state and the checks the demo made. The demo receives THREE, the item's module namespace
// and the harness; it imports nothing itself.
import * as THREE from 'three';

const ADDON_MODULES = {
  GLTFLoader: 'three/addons/loaders/GLTFLoader.js',
  GLTFExporter: 'three/addons/exporters/GLTFExporter.js',
};

function toBase64(bytes) {
  let text = '';
  const step = 0x8000;
  for (let start = 0; start < bytes.length; start += step) {
    text += String.fromCharCode.apply(null, bytes.subarray(start, start + step));
  }
  return btoa(text);
}

function describe(error) {
  return String((error && error.stack) || error).slice(0, 3000);
}

function fullscreen(material) {
  // One triangle that covers clip space; uv runs 0..1 across the visible square.
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute([-1, -1, 0, 3, -1, 0, -1, 3, 0], 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute([0, 0, 2, 0, 0, 2], 2));
  const mesh = new THREE.Mesh(geometry, material);
  mesh.frustumCulled = false;
  const scene = new THREE.Scene();
  scene.add(mesh);
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
  return {scene, camera, mesh};
}

export async function run(config) {
  const size = config.size;
  const shaderErrors = [];
  const checks = [];
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const renderer = new THREE.WebGLRenderer({canvas, antialias: false, alpha: false, preserveDrawingBuffer: true});
  renderer.setPixelRatio(1);
  renderer.setSize(size, size, false);
  renderer.debug.checkShaderErrors = true;
  renderer.debug.onShaderError = (gl, program, vertexShader, fragmentShader) => {
    shaderErrors.push({
      program: (gl.getProgramInfoLog(program) || '').slice(0, 1500),
      vertex: (gl.getShaderInfoLog(vertexShader) || '').slice(0, 1500),
      fragment: (gl.getShaderInfoLog(fragmentShader) || '').slice(0, 1500),
    });
  };
  const gl = renderer.getContext();

  function readCanvas() {
    const pixels = new Uint8Array(size * size * 4);
    gl.readPixels(0, 0, size, size, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
    return pixels;
  }

  const harness = {
    THREE,
    size,
    renderer,
    addons: {},
    check(name, passed, detail = {}) {
      checks.push({name: String(name), passed: passed === true, detail});
      return passed === true;
    },
    fullscreen,
    renderToCanvas(scene, camera) {
      renderer.setRenderTarget(null);
      renderer.render(scene, camera);
      return readCanvas();
    },
    floatTarget(width, height) {
      return new THREE.WebGLRenderTarget(width, height, {
        type: THREE.FloatType, format: THREE.RGBAFormat, depthBuffer: false,
        minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
      });
    },
    byteTarget(width, height) {
      return new THREE.WebGLRenderTarget(width, height, {
        type: THREE.UnsignedByteType, format: THREE.RGBAFormat,
        minFilter: THREE.NearestFilter, magFilter: THREE.NearestFilter, generateMipmaps: false,
      });
    },
    renderToTarget(scene, camera, target) {
      renderer.setRenderTarget(target);
      renderer.render(scene, camera);
      renderer.setRenderTarget(null);
      const count = target.width * target.height * 4;
      const values = target.texture.type === THREE.FloatType ? new Float32Array(count) : new Uint8Array(count);
      renderer.readRenderTargetPixels(target, 0, 0, target.width, target.height, values);
      return values;
    },
  };

  let built;
  try {
    for (const name of config.addons) {
      const loaded = await import(ADDON_MODULES[name]);
      harness.addons[name] = loaded[name];
    }
    const module = await import(config.module);
    const demoModule = await import(config.demo);
    built = await demoModule.demo(THREE, module, harness);
  } catch (error) {
    return {fatal: describe(error), shaderErrors, checks};
  }
  if (!built || !built.scene || !built.camera) {
    return {fatal: 'demo() returned no {scene, camera}', shaderErrors, checks};
  }
  const pixels = harness.renderToCanvas(built.scene, built.camera);
  const triangles = renderer.info.render.triangles;
  const points = renderer.info.render.points;
  const lines = renderer.info.render.lines;
  let baseline = null;
  if (built.baseline) {
    baseline = toBase64(harness.renderToCanvas(built.baseline.scene, built.baseline.camera));
    renderer.render(built.scene, built.camera);
  }
  const debug = gl.getExtension('WEBGL_debug_renderer_info');
  return {
    revision: THREE.REVISION,
    webgl2: renderer.capabilities.isWebGL2 === true,
    context: {
      version: gl.getParameter(gl.VERSION),
      shading: gl.getParameter(gl.SHADING_LANGUAGE_VERSION),
      renderer: debug ? gl.getParameter(debug.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
    },
    programs: renderer.info.programs.length,
    drawn: {triangles, points, lines},
    glError: gl.getError(),
    shaderErrors,
    checks,
    size,
    pixels: toBase64(pixels),
    baseline,
  };
}
