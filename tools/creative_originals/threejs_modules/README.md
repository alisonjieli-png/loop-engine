# Original three.js and WebGL modules

Kind: tool component family (`threejs_modules`). Each item is one standalone ES module for three.js and WebGL 2
with one distinct capability: a `ShaderMaterial` builder, a post-processing pass, a geometry generator, an instancing
or scatter tool, a camera rig, a picking helper, a glTF reader, writer or validator, a kinematics helper, a procedural
texture or a lighting helper. The owner, October 9, 2026: "entire asset libraries of thousands of godots, blender,
and other files, textures, logic, tools, contracts, procedures, js plugins, etc".

Every file is an original Baltor implementation written from the mathematics of a named technique. Nothing is copied
from three.js examples or addons, Shadertoy, tutorials or any repository. The verifier uses three.js's own
`GLTFLoader` and `GLTFExporter` as independent engines for the glTF items; they are never part of a package.

## Module rules

- One root module, `<identity>.mjs`, with no `import` of any kind. A function that needs three.js takes the
  namespace (`import * as THREE from 'three'` in the caller) as its first argument, named `THREE`. Everything else
  works on numbers, plain objects and typed arrays, so it runs in a page, a worker or Node.
- Exports are `export function`, `export class` or `export const` declarations only, never `export default`,
  `export let` or export lists. An exported object constant is frozen.
- No network, storage, code evaluation, worker, process or page-global API (`window.`, `document.`, `globalThis.`).
  `inspect_module.py` refuses them.
- Options objects are strict: an unknown key throws `TypeError` and a value out of range throws `RangeError`, so a
  misspelt option never passes silently. Defaults live in one frozen `*_DEFAULTS` constant.
- Shader math has a CPU mirror (for example `toonBandLevel` for the GLSL `toonBandLevel`) that tests and tools use,
  and the verifier compares the GPU result with the mirror.
- GLSL is written for three.js `ShaderMaterial` under WebGL 2: three.js adds `#version 300 es`, precision and the
  built-in uniforms and attributes; the code uses `varying`, `texture2D` and `gl_FragColor`, which three.js maps.
  Shaders meant for the screen end with `#include <colorspace_fragment>` (r155 and later), so they write sRGB to the
  canvas and linear values into linear render targets. Every uniform is declared literally in the module text with
  its type.
- A post-processing pass is a shader definition `{name, uniforms, vertexShader, fragmentShader}` with the input
  texture uniform `tDiffuse`, returned fresh by `create<Name>Shader(options)`, so three.js `ShaderPass` and
  `ShaderMaterial` both take it; `create<Name>Material(THREE, options)` wraps it. Vector uniforms are plain arrays.
- A geometry generator returns `{positions, normals, uvs, indices, ...}` typed arrays from `<name>Data(options)`
  (counter-clockwise triangles seen from outside, `Uint16Array` indices up to 65,535 vertices, else `Uint32Array`)
  and builds a `BufferGeometry` in `create<Name>Geometry(THREE, options)`.

## Package

```text
<package>/
├── <identity>.mjs           the module (role skill_asset)
├── test_<identity>.mjs      node:test known answers and at least one known-wrong control
├── demo/scene.mjs           demo(THREE, module, harness): the scene the verifier renders, also a usage example
├── README.md                first line "# " + title; sections When to use it, Use it, Exports, Checks, Limits
├── inspect_module.py        shared: reads the package as text and reports problems (standard library)
├── test_package.py          shared: the inspector on this package and on known-wrong copies
├── test_contract.mjs        shared: exports, contract examples and GLSL declarations against component.json
├── component.json           the contract card, written by assembly
├── verification/native.json the native evidence record
└── preview.png              the demo frame the verifier captured
```

The qualification sandbox runs `test_package.py` with the isolated system interpreter and the root `test_*.mjs`
files with `node --test --test-reporter=tap`, then replaces every export of the root `.mjs` module (and every public
function of `inspect_module.py`) with one that throws and requires the tests to fail. Qualification's manifest rule
asks code components for a root Python module; `inspect_module.py` is that module and a real tool:
`python3 inspect_module.py PACKAGE` prints its report and exits 1 on a problem.

## Contract

`item.json` `contract` holds:

- `module`, `category`, `language`, `three` (`injected`, `argument`, `tested_version`, `needed_by`);
- `exports`: every export with `name`, `kind` (`function`, `class` or `constant`), `signature` and `summary`; a GLSL
  export also has `glsl` (`vertex`, `fragment` or `chunk`), and a function that returns GLSL has `glsl_args`;
- `options` and `uniforms` (`name`, `type`, `option`), where they apply;
- `examples`: calls with JSON arguments (`{"$typed": "Float32Array", "values": [...]}` for a typed array), an optional
  `select` path such as `indices.length`, and `expect` with a `tolerance`, or `throws` with an error name.
  `test_contract.mjs` runs each one and also checks that a wrong expectation would be refused;
- `demo` (`file`, `export`, `addons` from `GLTFLoader` and `GLTFExporter`) and `tests` (the item's own test files).

## Native verification

`native.py` checks one item at a time, on a copy of its package files:

1. `module_contract_static`: the exports read as text equal the contract's names and kinds; the module and its demo
   import nothing.
2. `node_tests_pass`: every root `test_*.mjs` passes under `node --test` (Node 22, `/usr/bin/node`, the sandbox's
   runtime) with at least one passing test and none failed or cancelled.
3. `node_tests_catch_mutants`: each root module, its exports replaced by qualification's own mutant builder, makes
   the same tests fail.
4. `three_runtime_pinned`: the three.js files the page may load have the SHA-256 digests of the official
   `three-0.186.1.tgz` npm tarball (SHA-512 integrity checked against the package lock on October 9, 2026).
5. In headless Google Chrome 148 (WebGL 2 on SwiftShader through ANGLE over Vulkan), driven over the DevTools
   protocol on a pipe with every host name resolving to nothing, `harness/page.html` imports three.js, the module and
   `demo/scene.mjs`; the demo builds its scene and makes its own checks (GPU results against the CPU mirror, bounds,
   round trips through three.js's glTF loader and exporter), the harness renders the scene at 256 x 256 and reads
   the pixels back:
   `browser_page_clean` (no exception, console error, three.js or WebGL warning, `gl.getError()` clean),
   `three_shaders_compiled` (no shader compile or link error, at least one program), `demo_checks_passed` (at least
   one check, all passed), `render_not_uniform` and, when the demo declares a baseline without the effect,
   `render_differs_from_baseline`.

The evidence record binds the item digest and the verifier digest (native.py, `harness/` and this README) and holds
no time stamp: a second run on the same bytes and engines writes the same record. ANGLE's notice that a synchronous
`readPixels` stalled the GPU is the only message ignored, because the verifier reads pixels back on purpose.

Engines on this host: Chrome at `/opt/google/chrome/chrome` (or `BALTOR_CHROME`), three.js unpacked at
`~/.cache/baltor-creative/runtimes/three-0.186.1/package` (or `BALTOR_THREE`; download
`three-0.186.1.tgz` from the npm registry, check its SHA-512 against the lock file and extract `package/build`,
`package/examples/jsm`, `package/LICENSE` and `package/package.json`), Node at `/usr/bin/node`. About 2 to 4 seconds
an item.

## Commands

```bash
export PYTHONPATH=src:.
python -m tools.creative_originals.verify --family threejs_modules --output EVIDENCE_DIR --jobs 3
python -m tools.creative_originals.check --family threejs_modules --evidence EVIDENCE_DIR --packages PACKAGES_DIR
```

## What this does not establish

A pass shows that the exact bytes ran in Node 22 and rendered without error in one Chrome build on SwiftShader with
three.js 0.186.1, and that the demo's own checks held there. It does not establish behaviour on hardware GPUs,
Firefox, Safari, mobile browsers, WebGPU or other three.js releases, frame time, visual quality, or benefit to a
customer's task. Each item's limits say which three.js release it was written for.
