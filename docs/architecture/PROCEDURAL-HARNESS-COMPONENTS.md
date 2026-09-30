# Procedural generators as harness components

Kind: current implementation direction, September 29, 2026. The owner asked
whether procedural engines, deterministic engines and programmatic generators
should be specific harness components. They should be discoverable executable
capabilities within the existing component model, not a second runtime.
The [functional component standard](FUNCTIONAL-COMPONENT-STANDARD.md) owns their
typed edges and selectable engines. The [roadmap](../roadmap/roadmap.yaml) owns
implementation status and acceptance.

## Keep four distinctions

| Dimension | Examples | Meaning |
| --- | --- | --- |
| Capability | Generator, transformer, simulator, renderer, validator | What a caller asks the component to do |
| Method | Parametric, procedural, constraint-based, optimization, model-assisted | How the result is constructed |
| Engine | Original Python implementation, qualified Blender adapter, qualified native binary | The selected implementation behind the same edge |
| Reproducibility | Same-environment repeatability, seeded replay, tolerance-bound equivalence, unknown | What has actually been tested |

A procedural generator may use randomness, floating-point simulation or a
model. It is not automatically deterministic. A deterministic renderer does
not generate a new design. A template is passive data until an existing engine
interprets it. A compiled binary is a delivery form, not a new execution mode.

Every executable graph vertex remains a Loop. A Loop can call one pure function,
use a renderer or compose several qualified components. Pixels, mesh vertices,
asset parts and animation frames remain data or low-level operations inside
their owning work. They do not each start a fresh harness or model call.

## The component package

The discovery card should be small enough to select without loading source.
It names the purpose, typed input/output, parameter units and ranges, required
assets, engine compatibility, effects, budgets, failure codes and evidence.
The complete package retains editable source or the declared binary, its
licence, dependency identity, reference inputs, expected properties and tests.

```text
Small contract card
  -> select an eligible engine and exact version
  -> validate parameters, dependencies and authority
  -> execute unchanged implementation
  -> inspect output and run independent checks
  -> retain output identity, configuration and evidence
```

The initial asset factory implements twelve original constructors as tool
packages. `contract.json` declares `capability_type: procedural_generator` and
`execution_mode: deterministic_code`; its version is
`procedural_asset_constructor/v1`. The existing service kind is still `tool`.
This is a package-level contract, not an already deployed global catalogue
filter or a new protocol standard.

The native engine accepts three named sizing values and produces static glTF
geometry. It exposes no arbitrary code input. Its parameter references include
the original recipe, model, four views and structural checks. Different sizing
cases are variants of one capability, not separate implementations. See
[the factory](../../tools/procedural_assets/README.md).

Source is still available when inspection or repair needs it. Keeping source
out of routine selection is an optimization, not a security boundary or a
reason to conceal behavior. Measure whole-task cost before claiming savings.

## Engine substitution

An alternative engine must satisfy the same declared semantic contract, not
merely emit a file with the same extension. Check dimensions, coordinates,
orientation, material roles, topology requirements, sockets, object identity,
effects, error behavior and applicable performance limits. Different qualified
engines need not produce identical vertices unless the contract requires it.

The initial engine is the original static mesh constructor. Blender, Infinigen,
Godot and browser renderers are candidate adapters, not tested drop-in replacements.
Do not list them as supported until their adapters pass the conformance kit.
Preserve generator source separately from baked export; renderer or material
loss must be reported, not hidden by a nominally successful conversion.

One failed backend does not authorize downloading software, changing a licence,
using another tenant's cache or switching to a paid provider. Fallback selection
remains within the caller's original compatibility and effect boundaries.

## More than 3D assets

The same form can hold pixel-art conversion, dithering, ASCII frames, layout,
chart animation, audio synthesis, caption timing, map geometry, schema conversion,
test-fixture generation, migrations and data validation. Build a new component
when behavior or its contract differs. Do not create a million renamed copies
of one constructor or a Cartesian product of untested presets.

A detailed creative brief is another input. It can preserve silhouette,
materials, palette, expressions, camera, timing and sound decisions, while a
generator makes only the subset it supports. The
[art-direction templates](../../tools/procedural_assets/ART-DIRECTION-TEMPLATES.md)
separate image, non-human character, video, slideshow and music requirements.
They do not magically add rigging, cloth, fur or music generation to the current
static mesh engine.

## Website and plugin boundary

The homepage now targets Engineers, Designers and AI Agents, as requested by
the owner. These are three entry paths to one library and account. AI Agents
is an integration path, not a separate paying legal customer. The designer
path must disclose the current creative collection's development status.

Plugins may retrieve contracts, inspect allowed material and return supported
exports. They must not hide arbitrary execution behind a generic dispatcher,
inherit a user's whole chat history or treat subscription access as permission
to run code. Hosted execution needs its own explicitly exposed operations,
reviewed schemas and effect authority. A website subscription and a plugin
listing remain separate commercial and distribution steps.
