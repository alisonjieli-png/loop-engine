# Pi semantic-step embodiment

For development, read [the harness instructions](../AGENTS.md),
[ASTRA.md](../../ASTRA.md), and
[the layered harness design](../../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md).
An outer Loop may govern Pi's native iteration while preserving cumulative
authority and independent acceptance. Native control and session reuse need
their own qualified profile; this guidance does not change the launch flags.

The pinned Pi installation is inside this repository at `/home/username/loop-engine/embodiments/pi/runtime/node_modules/@earendil-works/pi-coding-agent`. Version: 0.85.1. Package installation used `--ignore-scripts`; the lockfile records dependency integrity.

Observed here: the actual CLI completed an isolated text-only round trip through the new broker mechanics, with one scripted callback and no live provider call. Evidence: `/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y/installed-probes/core-pi-v2.json`.

This is now selectable through `loop-engine solve --embodiment pi`. The live
three-function comparison passed 34/34 cases on three Ollama Cloud calls.
A complete-solve fixture passed, and a separate deliberately wrong-math fixture
was rejected by independent verification despite passing producer tests.
The first live complete-solve attempt failed verification; its saved failure is
not overwritten by later attempts. Read
`/home/username/loop-engine/embodiments/HARNESS-GUIDE.md` for the integration and
`/home/username/loop-engine/artifacts/harness-expansion-20260909-DNMQ3Y` for results.
Native Pi tools are disabled. Loop Engine retains intelligence, task control,
capability execution, independent verification and history.

The source is [earendil-works/pi](https://github.com/earendil-works/pi), under MIT. Use its `models.json` mechanism for custom providers. An ignored `OPENAI_BASE_URL` environment variable does not establish that custom endpoints are unsupported. Tool-schema absence is distinct from filesystem/network isolation; the process adapter supplies an explicit OS boundary.

Start with `/home/username/loop-engine/build/astra-harness-blueprint-2026-09-09/README.md` for the build plan and exact limits.
