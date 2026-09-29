# Godot control fixture

Original first-party scene for testing engine execution, an injected input
action, collision state and rendered capture. It is not a finished game,
MCP integration, performance benchmark or qualified customer package.

The scene uses an arcade-style kinematic body. The input action moves it
toward a static wall for 120 physics ticks. The final x position must be
within 0.02 of 3.2. The `--broken-wall` control omits the collision shape;
the same assertion must fail, with exit status 1. Rendering and headless
logic checks are separate runs.

Copy this folder to a new private working directory before running it.
Godot creates its import cache, result records and screenshot there.
Use a reviewed executable path instead of an unpinned package install:

```bash
godot --headless --path PRIVATE_FIXTURE --fixed-fps 60 --quit-after 300
godot --headless --path PRIVATE_FIXTURE --fixed-fps 60 --quit-after 300 -- --broken-wall
xvfb-run -a godot --path PRIVATE_FIXTURE --rendering-method gl_compatibility --fixed-fps 60 --quit-after 300
```

The first and last commands should exit 0; the middle command should exit 1.
Check the result records, not only exit codes. The frame limit can terminate
a project that never reaches its assertion. Headless mode must report no
frame capture. A rendered run must report successful capture and produce
`capture.png`; inspect the image as well as the record.

## Observed September 29, 2026

The private run used Godot 4.7.2 stable, official revision ed1daf0bf. The
downloaded Linux x86_64 archive's SHA-256 matched the digest published in the
official release API:
`cadd3204e728a35d3f13adb7fd0d7902636b79f6b95c40c265eb73b6c35329e4`.

- Headless and rendered runs reached x = 3.19986891746521 and passed.
- The missing-wall control reached x = 9.99999809265137 and failed as expected.
- Render capture used Xvfb and Mesa llvmpipe, not a measured hardware-GPU path.
- The first camera hid most of the moving object behind the wall. Inspection
  prompted a camera correction and a collision-envelope correction; the
  original attempt and outputs were retained privately.

The final source digest of `control_fixture.gd` was
`7dc23dbb9000c297799aef5ba40d170d415f42448dfb1a79bdea2ed51f3b47cd`.
The final captured image digest was
`7278c7f52ea98ce190f59c9d4cfaabfd9b7bcb5bb6b635827ed589eefee674f4`.
Evidence lives at `/home/username/baltor-private/godot-control-20260929-Cs3K5g`.
The engine binary is not committed or redistributed here.

The action enters Godot through `Input.action_press`; this is not evidence
of keyboard binding, OS input injection, multiplayer, controller feel or
arbitrary-game playtesting. Native adapter qualification must additionally
test session identity, mutation boundaries, cancellation, timeouts and
unknown-outcome reconciliation. Scene elements are engine data, not new
Loop Engine runtime types.
