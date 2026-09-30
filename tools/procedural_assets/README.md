# Original procedural asset references

This factory extends the existing native candidate preparation path. Its helper
operations run inside the owning preparation Loop. It adds no runtime, store,
approval route or automatic engine installation.

Twelve constructors cover a bear, a round creature, humanoid and quadruped
proxies, conifer and broadleaf trees, a boulder, a house, a fence, a vehicle,
a water-wave surface and a visible sun disc. They are original static
blockouts, not production characters, fitted clothes, biological models,
simulation-ready vehicles or physically based skies.

Each constructor has fifteen sizing references: the default, six single-axis
limits and eight corners of its declared range. These are 180 parameter cases
of twelve capabilities, not 180 new generators. Each reference includes a
recipe, embedded-buffer glTF model, and front, side, top and isometric SVGs.
Two reference groups per constructor keep native packages below the existing
64-file limit. Shared source, tests and licences have identical bytes and count
once in a distinct-file inventory. Uniformly scaled previews may also deduplicate.

The small contract names metre units, axes, dimensional limits, implementation
identity and missing capabilities. The model can inspect that contract and send
parameters to the packaged constructor without reading or regenerating source.
Source remains available for inspection. Parameters do not introduce a new
model call or executable graph vertex.

## Build and checks

Commit the declared sources before preparing a real batch. Use a new private
output directory whose parent already exists:

```bash
PYTHONPATH=src:tools .venv/bin/python -m tools.build_procedural_assets \
  --run-folder /absolute/private/new-asset-candidate-run \
  --authorize-preparation
```

The command uses `build_creative_components.build` with this proposal engine.
The existing pinned-source check and native catalogue compiler still own the
boundary. Preparation creates candidates only; independent review, admission,
search publication and native-engine qualification have not been performed.

Run `PYTHONPATH=src:tools .venv/bin/python -m unittest tools.test_procedural_assets`.
Checks cover finite geometry, nonzero triangle area, exact primitive answers,
range limits, repeatability, parameter edits without topology rewrites,
embedded buffers, unit normals, escaped previews, existing package limits and
execution from isolated package folders. Deliberately broken triangles and
invalid inputs must fail. The test source is first-party; a temporary folder
is not a security sandbox for arbitrary imported code.

The website's two prototype images come from the same constructors. Their
builder is a registered generated view. They remain labeled as unqualified
research prototypes, not examples of approved library downloads.

## What remains

Native renderer import, visual review, animation, skinning, joints, UVs,
collision proxies, materials beyond flat colors, garment fitting and performance
qualification remain open. Art-direction templates describe future production
requirements; they do not add those capabilities to the blockout constructor.
Do not promote a pretty preview as proof that any of them works.
