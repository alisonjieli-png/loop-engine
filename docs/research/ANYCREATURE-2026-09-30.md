# anyCreature compiler candidate: native consumer qualification

Status: prototype qualification evidence, not production adoption or independent
library admission. Observation date: September 30, 2026, United States Eastern
time (October 1 UTC). The experiment changed no website, catalogue or production release.
This reviewed record preserves the experiment in the repository.

## Source and fixed edge

The proposed source engine is [anyCreature 1.3.2](https://github.com/Ariescar/anyCreature/tree/88041c1efb316370dd78963f422decd854fd9067),
pinned to commit `88041c1efb316370dd78963f422decd854fd9067`. Its
[MIT notice](https://github.com/Ariescar/anyCreature/blob/88041c1efb316370dd78963f422decd854fd9067/LICENSE)
names Alsomind Tech Co., Ltd.; preserve that notice with copied source.
The tested compiler closure is 21 unchanged files, 271,831 bytes. Setup,
publication, shipping, prompt cards and the bundled web viewer are excluded
from that execution closure. There was no CC0 stamping or public upload.

The private adapter fixes `anycreature_compile_request/v1` and
`anycreature_compile_result/v1`: a digest-selected authored JSON source,
explicit local execution/file authority and the pinned engine profile produce
a GLB, machine check output and exact file hashes. Unsupported versions,
source changes and authority changes refuse. The engine ran through the
existing local Docker service using the already available image
`node@sha256:64af3819f9275802414d7cdc38c27e9d82bd564dec4d4da87d008255d36c63b4`,
without networking, package installation, image pull or model calls.

## Observed qualification

The previous bounded trial compiled the shipped spec and a 1.25 multiplier on
its authored spatial parameters. Both outputs passed a separate structural
inspector; a joint-cycle control failed and produced no model. Thirteen
structural/authority checks passed. This continuation opened the exact outputs
in Blender 4.5.3 LTS, build `67807e1800cc`, through the already installed bpy
module on Python 3.11.15. Every import and reopen started a new process with
factory settings, automatic scripts disabled, an empty user configuration,
read-only GLB mounts and a separate network namespace.

Both models imported as one armature-deformed mesh, with 31 bones and the
idle/move actions. Blender adds a bone-display helper object; it is not counted
as an authored creature mesh. Cycles CPU rendered eight samples per action per
model at 720 by 540, 16 samples, no denoising, with the same camera and lighting.
Four MP4 previews encode those actual frames; they contain eight video samples
each. Their measured durations are 2.200 seconds for idle and 0.947 seconds for
move, compared with the imported actions' approximately 2.2 and 0.95 seconds.
These are sampled previews, not a real-time frame-rate benchmark.

| Observation | Shipped spec | Spatial revision |
| --- | ---: | ---: |
| GLB bytes | 302,916 | 311,944 |
| Delivered vertices before native import | 3,648 | 3,758 |
| Native bones / clips | 31 / 2 | 31 / 2 |
| Blender XYZ bounds at idle start, declared metres | 0.676 × 2.154 × 1.476 | 0.844 × 2.692 × 1.878 |
| Largest observed idle vertex movement | 0.07838 m | 0.09797 m |
| Largest observed move vertex movement | 0.50860 m | 0.63575 m |
| Frozen-motion control | 0 m | 0 m |

The revision changes native bounding dimensions by approximately
1.2485 / 1.2498 / 1.2727 on Blender X/Y/Z under the same camera. It preserves
bone and clip counts. It is a meaningful size revision; sampling and fixed
defaults mean it is not exact geometric similarity.

Each edited native project was saved to .blend and reopened in a new process.
For each asset, all eight measured action poses reproduced exact evaluated-
vertex hashes. The reopened move render has identical RGB pixels to its
matching initial render. PNG file bytes differ because timing, file and date
metadata differ; the comparison treats that separately.

Input hashes:

- Shipped GLB: `b166f998c095a9031b3067991f6667b5f19b05150db42109bcf9f31581e5f041`.
- Revised GLB: `fe6f6fc65e4c47d75d150d46fc1ec6e939c25ab9be2d6ec00d0846e332027bf2`.

Final native project hashes:

- Shipped .blend: `25c89d8ab9f2ee425828a37d27df4adf2569650bb7da644333f47a21eea4b32e`.
- Revised .blend: `a4f006f2b7af1741c068dd1aa3b02b43491c71d0cfe84b5720c6005a35f2040d`.

## Failure retained and repaired

The complete native process population is 14: thirteen completed successfully,
one failed, and none timed out. The first reopen comparison failed for idle
while move matched. The QA script had retained unkeyed bone transforms from
the preceding move action. It was repaired by clearing the active action and
resetting pose transforms before selecting another clip. Both assets were
rebuilt, rendered and reopened again. The exact pose-equality guard was kept;
no tolerance was widened. Original renders, native files, failing process log,
diagnostic measurements and the pre-repair script remain in the evidence.

The final native audit passes 21 checks. The native environment emitted a
mounted-filesystem enumeration warning; model import, rendering, save and
reopen still completed. No standalone ffmpeg executable was available, so
preview encoding used Blender's already compiled codec rather than installing
anything.

## Adoption decision and native alternative

Keep this as a candidate source adapter in the existing CodeAssetSpec
command_line_tool/package family and creative/procedural candidate preparation
path. Its Node compiler is effectful, so use the existing authorized
harness/sandbox route, not the effect-free direct callable executor. Loop
remains the only executable graph vertex; frames and mesh objects are not
additional runtimes.

A creature-compilation engine slot is proposed, not registered. The native
alternative remains required before promising interchangeable generation
engines. The current original Baltor quadruped/blockout constructors do not
satisfy the skinned, animated GLB edge and must not be relabelled as conforming.
The narrow next native candidate is an original rigged quadruped generator
under the same input/output and qualification profile. That generator is not
implemented by this study. Blender is a separately tested native consumer,
not a substitute compilation engine.

The next admission package should include the unchanged source closure and
licence, the wrapper contracts, source/input/output manifests, independent
structural wrong controls, and this native consumer recipe. Keep shared source
files deduplicated. A later adopted version needs the existing independent
rights, code and content review; it receives no access policy from this study.

## Limits

Producing-session visual inspection shows a visible stylized canid and a
clear size change. It also shows simple eyes without pupils, low contrast in
some adjacent materials and diagnostic render noise. The studio floor is
offset for inspection; contact physics and foot sliding were not evaluated.
There is no attack clip. No broad aesthetic acceptance, unfamiliar-creature
benchmark, game-engine import, frame-rate target, arbitrary hostile-input
security guarantee, model-cost benefit or native alternative is established.

Upstream issues remain: setup/calibration claims and CI references disagree
with the pinned files; the pre-generated example has a different generator
version; and its structural checker is not a complete security boundary.
Do not ship setup/publisher/cards as effect authority. Output reuse rights
remain an exact-artifact review matter; source MIT is not a blanket claim of
CC0 for models. No SDG or special free-access classification is proposed.

Evidence is held in the private source-research, compiler-prototype and native-
qualification manifests. Publish only a reviewed, sanitized evidence subset,
not those directories wholesale.
