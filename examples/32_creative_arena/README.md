# Ashen Wilds: browser game and editable scene

Kind: original creative example. Source files use the repository's MIT licence.
Three.js has its own MIT licence, included in the browser build. No external
model, asset-generation service or downloaded character is needed to play.

The example has sword combat, three goblin waves, movement, sprinting, dodging,
collision, failure and restart. The original character has a weighted biped
skeleton and idle, run, attack and dance clips. Scene tools change lighting,
preview animations, capture a frame, import a self-contained GLB or export the
character and complete scene. The dance is original keyframe animation; no
video motion capture or automatic retargeting is claimed.

## Run and check

```bash
cd examples/32_creative_arena
npm ci --ignore-scripts
npm test
npm run build
npm run serve
```

Open `http://127.0.0.1:8094`. Use WASD to move, click or press J to strike,
Space to dodge and Shift to sprint. Drag the scene to orbit the camera.
Touch devices have a movement pad and action buttons. Software renderers and
touch devices use reduced effects; that choice does not establish performance
on every device.

`src/simulation.mjs` owns deterministic game state and rules. The renderer
advances it in fixed time steps. `src/characters.mjs` creates the rigs and
clips; `src/world.mjs` builds the environment. `src/game.mjs` connects the
controls, renderer, game state and exports. Render frames, bones and scene
objects are not executable Loop vertices.

## Blender and other tools

Export the scene or character as GLB. The file includes geometry, materials,
rigs and animation clips; gameplay behavior stays in this JavaScript project.
An imported character uses the clips it already contains. The browser does
not invent a rig for an unrigged model or upload the import to a service.

With Blender installed, run the supplied import and render script:

```bash
blender --background --python blender-import.py -- scene.glb scene.blend frame.png
```

It refuses existing output files. Blender's published Python module is another
headless option; the September 30 local check used `bpy==4.5.3` in an isolated
Python 3.11 environment. Native desktop installation, headless containers and
remote workers remain separate setup profiles in the
[delivery plan](../../docs/roadmap/DELIVERY-SEQUENCE.md).

The scene controls expose optional WebMCP tools when the browser provides
`document.modelContext`. The initial test browser did not provide that API,
so native WebMCP operation is not qualified. This is not a Blender MCP server.

## Evidence and reuse

The five game-rule checks cover movement bounds, collision, attack facing,
dodge, wave completion and invalid time steps. Browser checks exercised
movement, animation/lighting changes and GLB export. The first two attempts
found a missing favicon and software shadow-rendering errors; both failed
reports were preserved. The subsequent reduced-effects run passed.

The revised example also passed through the real service and its security
headers: seven browser/export checks, with no browser errors. The full GLB
contains four rigs and sixteen animation clips. Blender 4.5.3 imported it,
saved a native project and rendered a frame using CPU Cycles. A fresh process
reopened 892 meshes, four rigs and sixteen actions, observed pose changes and
found no missing images. These checks concern this example, not a measured
advantage over a model working without Baltor.

The repeatable checks are `tools/check_creative_arena.mjs` against a running
Baltor service and `tools/check_creative_arena_blender.py` against the exported
native project. Both require new evidence destinations and refuse overwriting
earlier reports. The [September 30 record](../../docs/verification/SESSION-REVIEW-AND-CUSTOMER-PROOFS-2026-09-30.md)
states the scope of the wider customer tests.

`asset-briefs.json` contains original prompts for a warden, goblin and ruined
gate. Tripo's prompt library informed the workflow idea; no Tripo-generated
asset or copied prompt is bundled. Reusable library candidates still need the
normal independent admission process. This example does not increase the
approved catalogue count.
