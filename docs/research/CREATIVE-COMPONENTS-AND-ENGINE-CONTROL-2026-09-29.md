# Creative components, engine control and the million-file target

Kind: research and implementation record, September 29, 2026. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. This record
distinguishes upstream descriptions, creator reports, local checks and work
not yet implemented. It does not grant a license or approve a package.

## Owner direction

The owner asked for more than one million original component files, not just
skills; fixed typed edges and swappable engines; composition without reading
or rewriting every implementation; creative production and games; learning
from r/aigamedev and other communities; and an internal way to ask practitioners
about useful workflows. Their examples include a Godot and Blender scene,
Bioneural, and a Three.js driving scene.

The million-file target and the accepted-output target both stand. A large
library is useful only when a harness can select a small part of it, execute
or apply that part correctly, and preserve the result through changes.

## New source-backed directions

| Source | Observed mechanism | Baltor opportunity and boundary |
|---|---|---|
| [Barty-Bart motion graphics](https://github.com/Barty-Bart/motion-graphics) | Transcript-aligned clips, time-addressable animation, a shared implementation and comparison views. | Reusable timing, morphing, capture and comparison operations. Its code, fonts and icons have separate notices; a directory listing does not clear every asset. |
| [Text-to-Lottie](https://github.com/diffusionstudio/lottie) | Agent-authored Lottie JSON, live scene preview and explicit customization controls. | Editable animation structures and revision fixtures. Test renderer support rather than assume every Lottie player behaves alike. |
| [Anidoodle](https://github.com/alexgreensh/anidoodle) | Code-defined drawing styles, motion and synthesized sound, with published examples. | Mark-making, drawing order, palette and score components. Repeatability and quality claims remain upstream claims until reproduced. |
| [thi.ng umbrella](https://github.com/thi-ng/umbrella) | Independently usable TypeScript libraries for geometry, images, color, spatial indexing and related tasks. | Small functional implementations and dependency-complete reuse. Inspect each selected package, revision and license before import. |
| [LYGIA](https://github.com/patriciogonzalezvivo/lygia) | Granular shader functions across several shading languages. | A reference for shader-family contracts and cross-backend conformance. No blanket license approval or code copying is implied. |
| [JSCAD](https://github.com/jscad/OpenJSCAD.org) | Modular browser and command-line parametric geometry. | Geometry generators, constrained parameters, export and mesh checks. A parameterized generator is one capability, not one capability per random seed. |
| [MaterialX](https://github.com/AcademySoftwareFoundation/MaterialX) | Material and look-development interchange across applications. | Preserve material structure and distinguish supported translation from lossless conversion. |
| [Faust](https://faust.grame.fr/) | Compiled signal-processing programs targeting different environments. | Audio envelopes, filters, synthesis and spectral checks as executable components rather than prompts. Compiler, libraries and produced artifacts need separate qualification. |

The [video-skills directory](https://github.com/zhuyansen/awesome-claude-video-skills)
is useful for discovery. It describes model-assisted inclusion and security
grading. Those labels are not a Baltor security audit, source execution result
or permission to redistribute the listed projects.

Anthropic's [creative-work announcement](https://www.anthropic.com/news/claude-for-creative-work)
describes tool integrations spanning design, 3D and audio. Some connectors
retrieve documentation; others edit a project or access an asset catalog.
Record the actual operations instead of treating the word connector as proof
of full application control. The community Blender integration and the
Blender developers' integration are not necessarily the same package.

## Engine alternatives and their control surfaces

| System | Route to investigate | Appropriate first use |
|---|---|---|
| Godot | Text projects, scripting and CLI, plus a qualified editor/runtime bridge | Native and browser-exportable games, scene assembly, gameplay checks |
| Godot with Terrain3D | [Terrain3D](https://github.com/TokisanGames/Terrain3D), a script-accessible GDExtension with terrain and foliage facilities | Terrain recipes, collision, biome placement and level-of-detail tests; this is an add-on, not a Godot fork |
| PlayCanvas | [Official Editor MCP](https://github.com/playcanvas/editor-mcp-server) | Browser-first 3D authoring with viewport and runtime observation, state queries and input injection |
| Babylon.js | [Authoring-tool MCP interfaces](https://github.com/BabylonJS/Documentation/blob/master/content/toolsAndResources/mcpServers.md) and [scene-editor contract](https://github.com/BabylonJS/Editor/blob/master/mcp/mcp-tools-contract.md) | Material, geometry, particle, UI and scene composition; inspect editor-specific units and conventions |
| Three.js | Application code, development server and browser inspection, with libraries chosen for physics and state | Custom web visuals, interactive explainers and lightweight game compositions |
| Unity | [Community Unity MCP](https://github.com/CoplayDev/unity-mcp), editor scripts and command-line tooling | Existing Unity projects and workflows whose dependencies justify the editor; qualify licensing and worker setup separately |
| Phaser | [Browser-focused 2D framework](https://github.com/phaserjs/phaser) and source-level test tooling | Platformers, tilemaps and arcade games without requiring a native editor |
| GDevelop | [Event-based editor and modular behaviors](https://github.com/4ian/GDevelop) | Reusable behavior and extension packages for visual authoring; qualify agent control separately |
| Bevy | [Rust game engine](https://github.com/bevyengine/bevy), code and test tooling | Typed systems and data-driven game logic where the native build toolchain is appropriate |
| Redot | [Godot-derived engine](https://github.com/redot-engine/redot-engine) | A fork to evaluate only for a specific needed difference; do not infer Godot add-on or bridge compatibility |
| Blender | Python scripting and [community MCP for Blender](https://github.com/ahujasid/mcp-for-blender) | Meshes, materials, scenes, rigs, exports and offline renders, usually beside a game runtime |

These are candidates, not a universal compatibility claim. The initial PATH
check found no Godot, Blender or FFmpeg executable. A later bounded experiment
downloaded the official Godot 4.7.2 portable build into a private directory,
verified its published archive digest and ran an original control fixture.
No system-wide engine installation, Blender integration or comparative
performance benchmark was performed.

Godot bridges differ materially. [hi-godot/godot-ai](https://github.com/hi-godot/godot-ai/blob/main/docs/TOOLS.md)
documents session-aware editing, game capture and log access; its GDScript
validation differs from C# text editing. [Erodenn's runtime bridge](https://github.com/Erodenn/godot-mcp-runtime)
documents runtime screenshots, simulated input and scene inspection through
an injected helper. Neither is an official universal Godot interface. Inspect
the exact package, license, local listener authentication, injected files and
cleanup behavior before adoption. More exposed tools do not establish better
task performance or isolation.

PlayCanvas is particularly relevant to the owner's request: its official
server documents authoring plus observation of a running application. It acts
on the editor session currently connected, so identity checks and recovery
points must precede edits. Its [user manual](https://github.com/playcanvas/developer-site/blob/main/docs/user-manual/editor/mcp-server.md)
also describes keyboard, mouse and touch testing. These are upstream
capabilities, not Baltor's own measured results.

Three.js is a graphics library rather than a complete game editor. That does
not make JavaScript inherently unmaintainable. Project structure, typed
contracts, asset organization and tests determine maintenance cost. Browser
delivery does not imply every asset must download on every visit; cache and
storage policy matter. Likewise, a browser demo does not prove support on all
devices. Godot also supports web export, subject to its documented renderer,
threading, language and browser limitations in the [web export guide](https://docs.godotengine.org/en/stable/tutorials/export/exporting_for_web.html).

## What the community examples establish

The [post-apocalyptic scene](https://www.reddit.com/r/aigamedev/comments/1w9bkiw/gpt6_astra_built_this_postapocalyptic_game_scene/)
is a creator report, not a reproducible cost benchmark. The
[follow-up](https://www.reddit.com/r/aigamedev/comments/1walwfc/gpt6_astra_built_this_postapocalyptic_game_scene/)
describes roughly 10 to 12 hours, a detailed initial specification and further
guidance. The [aircraft installment](https://www.reddit.com/r/aigamedev/comments/1wnbn6k/gpt6_astra_ultra_blender_mcp_godot_built_this_3d/)
reports another roughly eight hours and explicitly says the model is not
production ready. Reconstruct the asset inputs, modeling, integration and
testing separately. A short showcase video alone cannot resolve those stages.

Another [mechanics collection](https://www.reddit.com/r/aigamedev/comments/1wj27lc/playing_around_with_gpt_astra_godot/)
describes scripted Blender assets, Godot with C#, streamed voxel terrain,
destruction, grappling and detachable robot parts. The author calls it a
collection of mechanics rather than a finished game. That is a useful
component-mining distinction: a grappling controller, a structural-breakage
fixture and a streaming test can be reusable even when the overall project is
not a product.

A [minigolf workflow](https://www.reddit.com/r/aigamedev/comments/1upf5z3/coding_agent_built_a_9_hole_minigolf_in_godot_and/)
is another useful creator report: the agent was required to play each hole,
not only build it. The [runtime-bridge author's post](https://www.reddit.com/r/godot/comments/1rh7tkd/i_built_an_mcp_server_that_lets_ai_assistants/)
also distinguishes edit access from actual playtesting. A corresponding
Baltor package should retain a replayable route and assertions for objectives,
collision and input response. The reports do not establish the quality of an
automated tester on arbitrary games.

The [Godot versus Unity discussion](https://www.reddit.com/r/aigamedev/comments/1wclimf/godot_vs_unity_engine_through_mcp/)
contains conflicting reports on token use, procedural terrain and MCP value.
Treat these as hypotheses to test, not an engine ranking. In particular,
prebuilt scenes and explicit terrain parameters are candidate tactics; the
claim that one model or engine always performs better is not established.

The owner supplied the Bioneural post, reporting a four-day browser FPS built
with Opus 5.5, and a Three.js driving-scene discussion. A later read-only HTTP
inspection reached [Bioneural](https://bioneural.de/) and its
[public client entrypoint](https://bioneural.de/js/main.js?v=bots1). That code
imports Three.js and separates world, maps, audio, touch/gamepad controls,
networking, HUD and gameplay into modules. This is observed client structure,
not a copied implementation, browser playtest or server audit. Asset origin,
creator time, model attribution, reuse permission and the all-device claim
remain unverified. No account was created and no multiplayer session joined.

## The engine-control contract

An owning Loop should be able to select a qualified adapter for each of these
operations without changing its callers:

1. Describe the exact session, engine version, project, graphics backend and available operations.
2. Inspect selected scene elements, assets, scripts, dependencies and current runtime state.
3. Create a recovery point and apply a bounded edit with expected starting-state checks.
4. Launch or attach, wait for observable readiness, and distinguish an editor image from a game image.
5. Capture at a specified camera and simulation time, read logs and query state.
6. Inject a recorded input sequence, check behavior and record performance with hardware context.
7. Export editable source and outputs, then stop only the process this run owns.

The adapter must say unsupported when it cannot perform an operation.
Screenshots are not gameplay tests. Successful tool returns are not acceptance.
Timeout after mutation means an uncertain outcome that must be reconciled,
not permission to repeat the mutation. A localhost listener is not a sandbox.
No single broad execute-code tool should inherit the account's unrestricted
filesystem, credentials and network access.

MCP, CLI, scripting, REST and browser automation are transports or execution
options behind existing edges. The existing tool transport, workspace,
process confinement and effect-approval components retain authority. The
scene hierarchy remains engine data; the only executable graph vertex in
Loop Engine remains Loop.

The [native Godot fixture](../../tools/creative_components/fixtures/godot_control/README.md)
now supplies a concrete local check. Injected action input moved an object
into a wall; headless and rendered runs passed the expected position check,
while removal of the collision shape made it fail. Xvfb and software OpenGL
produced a frame that was visually inspected and repaired for camera framing.
This verifies a small CLI-controlled scene, not the proposed general MCP adapter.

## Original generation and contract-first composition

The initial native factory in `tools/creative_components/` provides 35 original
numeric operations across motion, timelines, layout, geometry, camera paths,
physics, audio and color. Each package has a callable implementation, a
bounded JSON launcher, a small contract card, frozen examples, refusal tests,
provenance, a small AGENTS.md entry and the repository license. There is no SKILL.md. It uses
the existing native candidate preparation path and cannot approve itself.

This is a seed collection, not an adequate game-production library by itself.
It establishes a cheap deterministic supply route while larger engine-facing
packages are developed. Per-package execution tests cover numeric behavior;
they do not prove a playable scene, artistic quality or a model-cost advantage.

Use the existing `CodeAssetSpec`, body references, materialization cache,
capability directory and solution graph. The model selects small cards and
writes composition and parameter changes; the executor obtains the immutable
implementations. Source remains available for debugging, adaptation or audit.
Do not hide it, inline every body into the selection prompt, or ask the model
to rewrite unchanged source after every revision.

An offline check composes frame-to-time, segment progress and easing through
the existing Solution Loops. Changing duration changes the result without
changing implementation bytes. That establishes this deterministic composition
path, not automatic model selection or a measured token-cost improvement.

Standards worth qualifying at those edges include JSON Schema for requests,
[WIT](https://component-model.bytecodealliance.org/design/wit.html) when a
WebAssembly component is actually used, [OpenTimelineIO](https://opentimelineio.readthedocs.io/en/latest/tutorials/otio-file-format-specification.html)
for editorial timing, and [Design Tokens](https://www.designtokens.org/tr/2025.10/format/)
for design values. WIT specifies an interface, not the behavior behind it.
None replaces Baltor's effect policy, version negotiation or qualification.

Expansion families should include shader implementations, geometry generators,
camera rigs, typography and layout, motion systems, audio synthesis and edits,
scene recipes, controllers, simulations, native assets, import/export adapters,
validators, failure fixtures and technical workflow components. Track semantic
jobs separately from file digests. Do not inflate the target with repeated
licenses, renamed copies, generated IDs or a Cartesian product of presets.
Useful presets can be assets without becoming independent implementations.

The release metric is distinct payload digests in approved, active,
non-withdrawn packages. Candidate files, placements, package manifests and
repeated bodies are separate counts. The new catalogue count computes this
from metadata and marks it incomplete if any package manifest is unavailable.
The million-file goal is not yet achieved.

## Community discovery and outreach

Start with r/aigamedev, r/godot, r/threejs, r/gamedev, r/blender,
r/creativecoding, r/GraphicsProgramming, r/proceduralgeneration,
r/MotionDesign and r/LocalLLaMA as topic seeds. These are selected for task
relevance, not claimed to be the most popular or exhaustive communities.
Follow links to primary documentation and source. Preserve author-reported
status, contrary reports, dates and gaps. Votes select leads; they do not
approve components.

`tools/knowledge_radar/community.py` constructs disclosed research questions,
binds exact account, destination and text to the existing external-message
approval request, and normalizes replies into unreviewed leads. It makes no
network request. A posting connector, durable dispatch/outcome reconciliation
and authorized reply collector remain to be wired through existing services.
Drafts and outcomes belong in the managed record store, not a second queue.

Automatic Reddit collection needs platform-access review before activation.
[Reddit's Data API terms](https://redditinc.com/policies/data-api-terms)
require a separate agreement for commercial use and preserve contributors'
rights. A reply or a public link does not grant redistribution or training
rights. Use permitted research notes and primary-source leads; do not bulk
republish threads or profile users. Check each community's current rules and
disclose Baltor's purpose before asking questions. No public post was sent.

## Corrections to inherited research

The archived [external systems](../evidence/EXTERNAL-SYSTEMS-2026-09-29.md)
and [game engines](../evidence/GAME-AND-3D-ENGINES-2026-09-29.md) records retain
their original bytes. Their adoption verdicts are not current policy.

- Godot's [RigidBody3D reference](https://docs.godotengine.org/en/stable/classes/class_rigidbody3d.html)
  lists continuous collision detection as false by default. Choosing Jolt
  does not justify omitting a tunneling fixture or verifying per-body settings.
- [RenderingServer](https://docs.godotengine.org/en/stable/classes/class_renderingserver.html)
  documents that headless mode disables rendering functions. Logic checks and
  rendered capture require separately qualified paths. Fixed frame capture
  alone proves neither simulation determinism nor pixel identity across GPUs.
- [Unreal's coordinate system](https://dev.epicgames.com/documentation/unreal-engine/coordinate-system-and-spaces-in-unreal-engine)
  is Z-up, not Y-up. Units, handedness and forward direction belong in adapters.
- A rigid-body ship is one valid design, not a universal requirement. Kinematic
  and arcade flight can be deliberate. Exactly 60 Hz and one global random
  generator are not universal prerequisites for a testable game.
- The claim that no permissively licensed 3D space-combat project exists was
  not established. [BabylonJS SpacePirates](https://github.com/BabylonJS/SpacePirates)
  is at least a concrete lead, although archived and still requiring per-asset review.
- [Remotion's license FAQ](https://www.remotion.dev/docs/license/faq) distinguishes
  service-generated code and edits to it from arbitrary uploaded customer
  projects. Its commercial routes and costs depend on the actual deployment;
  blanket refusal was too broad.
- [Defold's license](https://defold.com/license/) distinguishes games and
  extensions from commercialization as a game-engine product. GPL and AGPL
  are not blanket commercial-use bans either. Baltor's own per-file ingestion
  allowlist remains separate from whether an external tool may run.
- [Cognee](https://github.com/topoteretes/cognee) documents retrieval routes
  without an LLM. The claim that it necessarily answers through a model was
  too broad. Evaluate its functions against existing source and retrieval edges.

OpenAI identity, plan use and plugin distribution also remain separate.
[Website sign-in](https://developers.openai.com/siwc/website) describes selected
commercial access; the [local plan-use route](https://developers.openai.com/siwc/token-sharing-open-source)
does not grant every hosted product access. Its [preview limitations](https://developers.openai.com/siwc/preview-limitations)
differ from a regular API route. [Plugin guidelines](https://developers.openai.com/plugins/app-guidelines)
allow existing entitlements but restrict in-plugin digital subscription sales.
Do not design a marketplace checkout or promise remote GPU access from login
alone. Exact eligibility and current policy need verification before launch.
