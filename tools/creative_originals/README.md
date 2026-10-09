# Original creative component families

Kind: tool component. These families hold original Baltor implementations for
2D, 2.5D, 3D and 4D work: Godot shaders, scenes and GDScript components,
Blender Python tools, procedural texture generators, tile and sprite tools,
geometry and simulation code, validators, contracts and procedures. The owner,
October 9, 2026: generate "entire asset libraries of thousands of godots,
blender, and other files, textures, logic, tools, contracts, procedures, js
plugins, etc that can improve baltor.ai's offering".

The families are source in this repository (MIT, the root `LICENSE`). The
`creative_originals` supply line packages each item at a pinned commit, one
package per item, and qualification then treats it like every other supply
package. Nothing here approves, stages or publishes anything.

## Runtime classification

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

A native verification run is a Starting Practitioner task of the code
execution profile that an operator starts; it runs deterministically. Godot,
Blender, the PNG codec and the record readers are adapters the run uses. None
is a graph vertex, a role, a mode or a runtime type, and none grants authority.

## Layout

```text
tools/creative_originals/
├── records.py, media.py, pngio.py, assemble.py, engines.py, verify.py, check.py   (standard library only)
└── <family>/
    ├── family.json        creative_original_family/v1
    ├── native.py          verify(context) -> {"engine", "checks", "preview"}; omitted when native_verifier is null
    ├── shared/            files every package of the family carries byte for byte
    └── items/<identity>/
        ├── item.json      creative_original_item/v1
        ├── README.md      first line "# " + the item title
        └── native files   shaders, scenes, scripts, generators, data
```

### family.json

```json
{
  "record_type": "creative_original_family/v1",
  "family": "godot_shaders",
  "title": "Original Godot 4 shaders",
  "description": "What the family holds, the shape of its item contracts, and how it is verified.",
  "engine": {"name": "godot", "minimum_version": "4.3", "notes": "Compatibility renderer verified"},
  "shared_files": [{"path": "inspect_shader.py", "role": "executable_tool"},
                   {"path": "test_package.py", "role": "executable_tool"}],
  "native_verifier": "native.py",
  "generator_version": "1.0.0",
  "default_dimension": "3d"
}
```

### item.json

```json
{
  "record_type": "creative_original_item/v1",
  "identity": "toon_rim_lighting",
  "title": "Toon shading with a rim light",
  "purpose": "Cel-shade a lit mesh in a fixed number of bands and add a view-dependent rim. Use for stylized characters and props.",
  "form": "library_module",
  "asset_role": null,
  "dimension": "3d",
  "engine": {"name": "godot", "minimum_version": "4.3"},
  "tags": ["shader", "toon", "cel shading", "rim light", "stylized"],
  "files": [{"path": "README.md", "role": "other"},
            {"path": "toon_rim_lighting.gdshader", "role": "skill_asset"},
            {"path": "toon_rim_lighting.tres", "role": "skill_asset"},
            {"path": "demo.tscn", "role": "skill_asset"}],
  "contract": {"shader_type": "spatial", "uniforms": [{"name": "bands", "type": "int", "default": 3}]},
  "limits": "Directional and omni lights only; the band edge aliases at grazing angles without MSAA.",
  "related": ["outline_inverted_hull"],
  "technique_references": ["Lambert term quantized into bands", "Schlick Fresnel approximation"],
  "native_checks": ["godot_compatibility_compile_and_render"]
}
```

`form` is one of `library_module`, `function`, `code_example`, `evaluation_set`
(served as code modules), `template`, `three_d_model` or `schema`. A
`template`, `three_d_model` or `code_example` declares `asset_role`
(`reference`, `generation_input`, `editable_source`, `test_evidence`).
`dimension` is `2d`, `2.5d`, `3d`, `4d` or `none` (a tool for any of them).
File roles: `other` for README.md and documentation, `skill_asset` for native
creative files (shaders, scenes, GDScript, textures, models), `executable_tool`
for Python a harness runs, `configuration`, `skill_reference`,
`instruction_file` only for a procedure a harness is meant to follow.

## Rules every item follows

1. **One distinct capability per item.** A different effect, behavior,
   algorithm, data structure or workflow. Never a renamed copy, a recoloured
   preset or a parameter value of another item: parameters stay parameters of
   one item. `check.py` refuses repeated titles and repeated file bytes; a
   reviewer refuses near copies.
2. **Original code.** Write every file yourself. A well-known technique (Fresnel
   rim, Perlin noise, A*, Verlet integration) is fine, implemented from its
   mathematics; never copy text or code from godotshaders.com, the Godot asset
   library, Blender Market, Shadertoy, three.js examples, tutorials or any
   repository. Name the technique in `technique_references`, not a source URL to
   copied code.
3. **Honest limits.** `limits` says what is approximate, untested, renderer
   specific or out of scope. Say "stylized", "approximate" or "not physically
   based" when that is true. Never claim a renderer, platform or performance
   number nothing measured.
4. **It works in the engine.** A family with an engine has a native verifier
   that opens the exact item bytes in the pinned engine; an item whose check
   fails is not packaged. A package's own Python tests run in a sandbox that has
   no engine, so they check structure, contracts and known-wrong controls.
5. **Small and complete.** Each file at most 256 KiB, each package at most
   2 MiB and 64 files (the review bounds). Text formats, or PNG checked by
   `pngio`. Opaque binaries (.blend, .fbx, .exr, .jpg, audio, .glb) are refused:
   ship the script that builds them.

## The package and its tests

`assemble.package_entries` writes the item files, the shared files,
`component.json` (the contract card a harness reads first), and, for a family
with a verifier, `verification/native.json` and `preview.png`. The line adds
LICENSE and ATTRIBUTION.md.

The qualification sandbox imports every root-level `.py` of the package with
`/usr/bin/python3 -E -s -B` (standard library only, no network, no engine)
and runs its root `test_*.py` unittest modules. The mutation check then
replaces every public function of each root module with one that raises, and
the tests must fail. So:

- Root modules import with the standard library alone. Code that needs `bpy`
  imports it inside the function that needs it, or lives below a folder.
- Keep pure logic (geometry, noise, parsing, layout) in importable functions,
  and test it with known answers.
- Each test module reads `component.json`, checks the item's files against it,
  and includes a known-wrong control: a corrupted copy, a broken value or a
  removed declaration that the check must refuse.

## Native verification

`native.py` defines `verify(context)` and returns
`{"engine": {...}, "checks": [{"name", "state", "detail"}], "preview": bytes or None}`.
`context` has `family`, `item`, `family_dir`, `item_dir`, `shared_dir`, an empty
`workspace` and the `engines` module. Use `engines.locate("godot")` and
`engines.run(engine, args, workspace=..., display=True)`.

Recipes measured on this host on October 9, 2026:

- **Godot shaders and scenes**: a project in the workspace with
  `renderer/rendering_method="gl_compatibility"`, run with
  `--path PROJECT --rendering-driver opengl3 --resolution 256x256 --script res://capture.gd -- ARGS`
  and `display=True` (xvfb, Mesa llvmpipe). A `extends SceneTree` script adds
  the scene, awaits a few `process_frame`s and `RenderingServer.frame_post_draw`,
  then saves `root.get_texture().get_image()` as PNG. **Godot exits 0 on a
  shader error**: scan the output for `SHADER ERROR` and `Shader compilation
  failed`, and refuse a capture whose pixels are uniform. About 1.3 s per item.
- **GDScript**: `--headless --path PROJECT --script res://run_tests.gd`, exit
  code and a printed summary line; scan for `SCRIPT ERROR` and `Parse Error`.
- **Blender**: `--background --factory-startup --python SCRIPT -- ARGS`; read a
  printed JSON line. Blender 5.2 exports glTF as `GLB` or `GLTF_SEPARATE`
  (`GLTF_EMBEDDED` no longer exists). About 3 s per item.

The evidence record binds the item digest and the verifier digest (native.py and
every other family file outside items/ and shared/), so an edited item or an
edited verifier needs a new run. It carries the engine build's SHA-256 and no
time stamp.

## Commands

```bash
export PYTHONPATH=src:.
python -m tools.creative_originals.verify --family FAMILY --output EVIDENCE_DIR --jobs 3
python -m tools.creative_originals.check --family FAMILY --evidence EVIDENCE_DIR --packages PACKAGES_DIR
python -m unittest tools.test_creative_originals
```

## What this does not establish

A native pass shows the exact bytes opened, compiled or ran in one engine build
on one renderer on this host. It does not establish behavior on other GPUs,
renderers or engine versions, visual quality, performance, or benefit to a
customer's task. Independent review is ongoing after qualification, as for
every supply line.
