# Claude Code instructions for Loop Engine

@AGENTS.md

@ASTRA.md

Start with the [context route](docs/context/START-HERE.md). It names the
newest dated handoff, now the
[September 22 session handoff](docs/context/SESSION-HANDOFF-2026-09-22.md):
what is live, how it was released, what was lost and repaired, what is in
flight and what is open. The
[takeover checkpoint](docs/context/TAKEOVER-CHECKPOINT-2026-09-20.md) holds the
working cycle for changes, tests, checkpoints and releases. The north star and
the ordered initiatives are in
[AGENTS.md](AGENTS.md#north-star-and-current-initiatives).

The owner's standing rules for committing, pushing, branching and releasing,
what still needs the owner, and the decisions that stand until the owner
changes them are in one place, the
[commit, push and release authority](AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md. This file adds nothing to that section and takes
nothing away from it.

The machine-readable work authority is [roadmap.yaml](docs/roadmap/roadmap.yaml)
and its delivery packages. The single development HTML is generated
from the roadmap and the source; do not edit it by hand and do not start
another dashboard.

Use the [prepared credential handoff](docs/guides/developer-credential-handoff.md)
for the existing connections. Never print the header-helper output, repeat
account creation or work around a recorded permission gap.

Verify current source and provider state before relying on a dated result.
Read the relevant component guide before implementation and preserve
concurrent work.

These are development instructions, not executable harness configuration.
Do not enable native tools or goals merely because an instruction file
describes them.
