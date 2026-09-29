# Game and 3D rendering engines: 2D platformers, 3D space combat, and what an agent can ship

Kind: dated research record for September 29, 2026. Every repository, licence and command
below was read on September 29, 2026, United States Eastern time. The
[roadmap](../roadmap/roadmap.yaml) remains the only task authority. Nothing here adopts an
engine or grants a licence. Where a project's own licence and its asset licence differ, both
are stated, because that difference decides whether we may serve it.

This record answers a specific owner question of September 29, 2026: are there applications,
engines, forks or variations that do 2D Mario-style games, or 3D space battle style renders,
that a library could serve. It extends
[EXTERNAL-SYSTEMS-2026-09-29.md](EXTERNAL-SYSTEMS-2026-09-29.md), which covers the engine
licence landscape in general.

## 1. The short answers

```text
2D Mario-style, best stack for an agent
└── Godot 4 + CharacterBody2D, MIT
    └── one binary runs headless AND writes deterministic frames to video

3D space battle, best stack for an agent
└── Godot 4.7 + Jolt Physics, both MIT, Jolt built in
    └── continuous collision detection on by default, which is the whole ballgame for dogfights

The gap we can fill
└── No permissively licensed, genuinely 3D, ship-versus-ship dogfight with clean assets exists
    └── a per-step harness that builds one, with a determinism contract, is the product
```

## 2. The engine choice is the licence choice

Every engine question collapses into one question first: may a paid hosted service run this
for a customer? That is decided before any question about quality.

| Engine | Licence | Shippable in a paid product | Note |
|---|---|---|---|
| Godot 4 | MIT | Yes | Per-project export template, not the whole engine. Jolt vendored under Expat. |
| Phaser 4 | MIT | Yes | Node-native, deterministic `fixedStep: true` by default. |
| Excalibur.js | BSD-2-Clause | Yes | Its arcade solver ships a platformer-specific contact bias. |
| PlayCanvas | MIT | Yes | WebGL2 and WebGPU, code-first. |
| three.js, PixiJS, Kaplay, cannon-es | MIT | Yes | |
| LÖVE, raylib, Solar2D, Excalibur | zlib or MIT | Yes | |
| Rapier 3D and 2D | Apache-2.0 | Yes | Pin the deterministic build, not the default one. |
| Jolt Physics | MIT | Yes | Already inside Godot 4.4 and later. |
| Box2D, box2d-lite, Planck.js, matter.js | MIT | Yes | |
| Bevy | MIT or Apache-2.0 | Yes, with care | Breaking API changes every few months. |
| Unity | Proprietary | Only by customer licence | Pro seats are charged per build worker once the platform passes the revenue threshold. |
| Unreal | EULA | Only by customer licence | Royalty above the exclusion, or per-seat fees. |
| Defold | Defold License 1.0 | **No** | Section 4(a) forbids commercialising the work as a Game Engine Product, and that is defined to include the software used to show the created content. |
| Kaboom.js | MIT | No | The project states it is no longer maintained. |
| Cocos Creator | MIT runtime | Partly | The runtime embeds freely; the editor is a closed binary. |

Defold deserves one more sentence because it is the trap a careful reader would expect. Its
own licence says "You do not sell or otherwise commercialise the Work or Derivative Works as a
Game Engine Product", and "Game Engine Product" means "software used for video game
development. This includes both the content authoring software and the software used to show
the created content." A hosted service that runs Defold and streams finished games to paying
customers is arguing against the plain text of that sentence. The upside does not justify it.

## 3. 2D Mario-style: the exact scene an agent must write

```text
Player (CharacterBody2D, motion_mode = MOTION_MODE_GROUNDED)
├── CollisionShape2D (RectangleShape2D or CapsuleShape2D)
├── AnimatedSprite2D
├── AnimationPlayer          # idle, run, jump, fall
└── Camera2D (position_smoothing_enabled, limit_left/right/top/bottom)

Level (Node2D)
├── TileMapLayer (collidable)
├── TileMapLayer (decorative)
├── Area2D pickups and hazards
└── RayCast2D enemy ledge detection
```

Two facts in that structure are the whole game, and both are where generated games break.
`TileMapLayer` replaced `TileMap` in Godot 4.3, and **tiles only collide once the TileSet has
a Physics Layer and the tiles are marked in its Physics tab**. A generated level that omits
that step is a scene the player falls straight through, and it opens and renders perfectly.
One-way platforms are `one_way_collision` on the `CollisionShape2D`, and the direction is
commonly set backwards.

The headless commands that make this testable, quoted from the Godot command line reference:

```text
--headless        "Enable headless mode (--display-driver headless --audio-driver Dummy)"
--write-movie     "usually with .avi or .png extension. --fixed-fps is forced when enabled"
--fixed-fps       "Force a fixed number of frames per second. This setting disables real-time
                   synchronization."
--quit-after      "can be used to specify the number of frames to write"
--benchmark       "Benchmark the run time and print it to console"   [editor builds only]
```

That combination is the reason Godot is first: one binary runs the game with no display, and
writes the frames a reviewer needs, and forces a fixed timestep so the run is reproducible.
Note the documented warning that also governs how we wrap it: "unknown command line arguments
have no effect whatsoever. The engine will not warn you." A typo produces a green run, so our
wrapper must check the engine's own `--version` output and fail on anything unrecognised.

Phaser 4 is the second choice and its own documentation states the limit honestly:
`Phaser.HEADLESS` "doesn't create either a Canvas or WebGL Renderer. However, it still
absolutely relies on the DOM being present and available. This mode is meant for unit testing,
not for running Phaser on the server." Server use needs a separate Node binding. Its arcade
tilemap separation is velocity-axis aware, which is exactly the platformer case.

## 4. 3D space battle: the exact scene, and the one choice that matters

```text
Main (Node3D)
├── Arena (Node3D)
│   ├── Asteroids (NavigationRegion3D)
│   │   └── Asteroid (StaticBody3D + ConvexPolygonShape3D or SphereShape3D)
│   └── CapitalShip (RigidBody3D + CollisionShape3D)
│       ├── Weapons (Area3D + CollisionShape3D)   # monitoring, body_entered
│       └── Thrusters (GPUParticles3D)
├── PlayerShip (RigidBody3D, custom_integrator = false)
│   ├── NavAgent (NavigationAgent3D)
│   └── CameraRig (Node3D) -> Chase / Overview / Orbit (Camera3D)
└── GameState (Node)   # the win condition lives here, not in a signal handler
```

**The ship is a `RigidBody3D`, not a `CharacterBody3D`.** Newtonian flight wants real inertia
and angular momentum. `CharacterBody3D` with `move_and_slide()` is a kinematic walk model, and
it is the single most common mistake in generated space games: the ship drifts, or sticks, or
slides along an asteroid, and looks fine in a still frame.

**The physics engine must have continuous collision detection on by default.** At 60 metres per
second and a 1/60 second step, a ship moves one metre per step, which is wider than most
asteroids. Without CCD the projectiles pass through the hulls:

| Engine | Licence | Headless | Determinism | CCD |
|---|---|---|---|---|
| Jolt | MIT | Yes, no GPU, no RTTI | "The simulation runs deterministically." | Built in, for sphere, box, capsule, convex hull, compound, mesh, terrain. |
| Rapier | Apache-2.0 | Yes | "a perfectly deterministic simulation on different machine, as long as they are compliant with the IEEE 754-2008 floating point standard" | Yes; `max_ccd_substeps`, `soft_ccd_prediction` |
| Bullet3 | zlib | Yes | Not guaranteed | `ccdMotionThreshold` and `ccdSweptSphereRadius` per body, **off by default** |
| cannon-es | MIT | Yes | Not guaranteed | **None at all** |
| MuJoCo | Apache-2.0 | Yes | Yes | A robotics solver, the wrong tool for a dogfight |

Jolt wins on CCD being on without configuration and on being zero-setup inside Godot 4.4 and
later. Rapier wins on the determinism guarantee and on its Python bindings. Bullet's CCD is
per-body and off by default, and cannon-es has none, so both put a correctness burden on
every generated weapon.

One more headless fact that decides architecture: `GPUParticles3D` dies with no GPU, so a
thruster effect has a CPU counterpart for the headless run, or the test result differs from
the render.

## 5. The determinism contract for any space or platformer component

Nothing in this section is optional. An agent-generated game that cannot be replayed is a
screenshot generator.

1. **Fixed timestep, decoupled from the render.** Integrate in an accumulator loop at exactly
   one sixtieth of a second. Never integrate with the frame delta.
2. **Drive simulation from the physics step**, never from the per-frame callback, and run the
   whole thing with the engine's fixed-fps flag.
3. **One seeded random source.** A single generator, an explicit integer seed passed in, and
   the seed written into every run record. Unseeded global random is refused.
4. **No wall clock in the simulation.** No millisecond timers, no high-resolution clocks, no
   dates in scoring, spawning, artificial intelligence or weapon logic. Time is a tick count.
5. **No GPU in the simulation path.** Particles and post-processing are CPU equivalents or
   no-ops when headless.
6. **Input is a recorded stream**, a frame-indexed array replayed, never live key state.
7. **Assertions return typed results.** Win condition reached within a tick budget, no body
   outside the arena bounds, no non-finite value in any transform, hit count equal to the
   expected count. A rendered image is evidence; a boolean is a test.

## 6. Existing open-source projects: which are clean enough to serve

The finding that matters most here is a negative one. Almost every famous open-source game
either carries copyleft or carries assets with a separate, incompatible licence.

**2D platformers.** `godotengine/godot-demo-projects` is MIT and contains `2d/platformer` and
`2d/physics_platformer`; it is clean. SuperTux is GPL-3.0 with data under CC BY-SA, so both
the copyleft and the share-alike bite. Pekka Kana 2 is GPL with assets under a non-commercial
licence. Lyle in Cube Sector is freeware with no OSI licence and third-party music used by
permission, so it is not a component.

**3D space games.**

| Project | Code | Assets | Verdict |
|---|---|---|---|
| gdquest-demos godot-2d-space-game (Harvester) | MIT | The author's own | Clean and complete: asteroids, pirates, upgrades, docking. |
| diagonalcounty/heliopoly | MIT | Self-made | Clean. Most valuable idea in the list: "Pure rules engine in `src/core/` with no DOM", plus a headless batch simulation over 100 games. |
| orbitersim/orbiter | MIT core | LGPL graphics engine, mixed bundled assets | The most complete Newtonian simulator, and explicitly "no predefined missions, no aliens to destroy", so no combat. Not clean enough to serve. |
| tristanpenman/asteroids | MIT | **"Game assets are under copyright by Atari"** | A faithful Asteroids clone. Code yes, assets no, and the assets are a trademark exposure. |
| nsmoooose/csp | GPL-2.0 | Separate | The best combat model of anything found, and not servable. |
| thiagoharry/spacewar, mrbid/AstroImpact | GPL | Own or third-party | Not servable. |

**So: no permissively licensed, genuinely 3D, ship-versus-ship dogfight with clean assets
exists today.** That is the opening, and it is a component-shaped opening rather than a
product-shaped one: the deliverable is a harness that builds such a game from a written
contract, plus the determinism checks that make the result testable, plus the failure library
for the specific defects below.

## 7. The failure library these components must ship with

Measured and observed failures, kept because a diagnostic without its known case is a guess.

From the game-generation benchmark work: at its best configuration, agents reach about 41
percent overall on a hundred-and-forty-task Godot suite, with core mechanics 55 percent,
content depth 39 percent, functional visuals 43 percent and art 37 percent. Its named
failures are "unresponsive controls, incorrect collisions, inactive enemies, unreachable
objectives, missing UI feedback", plus "incorrect camera framing, unreadable UI, missing
visual feedback, broken level layout, and demo states that fail to reveal the intended
mechanic". One operational finding is worth keeping: agents that rendered and inspected about
twenty-one screens per task scored better than agents that only read source. Inspecting the
render is not optional.

The defect classes a 2D platformer component must detect:

- Jump arcs measured from controller dynamics, not from artwork.
- No coyote time and no input buffering, or a forbidden repeated air jump.
- `is_on_floor()` checked before the move instead of after it.
- The camera as a sibling of the player rather than a child.
- One-way platform direction set backwards.
- A TileSet with no Physics Layer, so nothing collides.
- Diagonal speed that increases with direction.

The defect classes a 3D space component must detect:

- Tunnelling, which the CCD requirement above removes.
- Newtonian drift with no angular or linear damping and no flight assist.
- A chase camera inside geometry; it needs a sphere cast or ray pull-in.
- No game loop: the win condition must be an explicit state, not a side effect of a collision
  signal.
- A coordinate frame bug. Godot is Y-up, right-handed, with negative Z forward. Unity and
  Unreal are Y-up left-handed. A three.js camera looks down its local negative Z with a
  default up of zero, one, zero. Importing a forward vector from one convention into another
  produces a ship that pitches when it should yaw, and it renders plausibly.
- Thruster particles that kill the frame rate, with no level of detail.

## 8. Headless WebGPU, stated plainly

Viable and degraded. Chrome needs a software WebGPU adapter or the SwiftShader flags, and the
upstream project itself warns that "SwiftShader is a high security risk due to JIT-ed code
running in Chromium's GPU process". WebGPU on Linux is still rolling out by adapter generation.
A three.js forum thread documents headless WebGPU producing a blank canvas where the canvas
should be, and three.js's own end-to-end harness runs WebGPU on a software rasterizer.

**The decision that follows: a native engine in a container is strictly better for correctness
testing. Use a browser path for capture and for what the customer downloads, never as the
authority on whether the game works.**

## 9. What to build first, in order

1. **A 2D platformer bundle** in Godot 4, with the scene structure above, the jump-arc and
   coyote-time checks, a recorded input route, and headless frame capture. It is the smallest
   complete proof that the per-step harness can build, test and repair a real game.
2. **A 3D space combat bundle** in Godot 4.7 with Jolt, with the determinism contract in
   section 5 as its own acceptance test, and a tunnelling fixture that fails without CCD.
3. **A physics engine adapter** behind the existing process and workspace edges, with Rapier as
   the second engine, because deterministic physics is a component and not a script a model
   wrote.
4. **A failure and repair atlas** seeded with the defect classes above, each with a
   deliberately broken fixture that an independent check must catch, and a passing case where
   doing nothing is the correct answer.

## 10. Sources

- Godot 4 licence, `https://godotengine.org/license/`, and the stable command line reference
  for `--headless`, `--write-movie`, `--fixed-fps`, `--quit-after` and `--benchmark`.
- `https://godotengine.org` scene and node documentation for `CharacterBody2D`, `RigidBody3D`,
  `Area3D`, `NavigationRegion3D`, `NavigationAgent3D`, `TileMapLayer` and `Camera3D`.
- `https://github.com/godotengine/godot-demo-projects`
- `https://phaser.io` and the `Phaser.HEADLESS` documentation note quoted above.
- `https://github.com/excaliburjs/Excalibur.js` and its `ContactSolveBias` documentation.
- `https://github.com/jrouwe/JoltPhysics`, `https://github.com/dimforge/rapier`,
  `https://github.com/bulletphysics/bullet3`, `https://github.com/pmndrs/cannon-es`,
  `https://github.com/google-deepmind/mujoco`
- `https://github.com/dimforge/rapier.js` for the deterministic build note.
- `https://defold.com/product/license/`
- `https://github.com/gdquest-demos/godot-2d-space-game`,
  `https://github.com/diagonalcounty/heliopoly`, `https://github.com/orbitersim/orbiter`,
  `https://github.com/tristanpenman/asteroids`, `https://github.com/nsmoooose/csp`,
  `https://github.com/thiagoharry/spacewar`, `https://github.com/mrbid/AstroImpact`
- `https://kenney.nl` for the CC0 asset statement, and the per-item licensing notes on
  OpenGameArt and itch.io.
- The owner message of September 29, 2026 that asked this question.
