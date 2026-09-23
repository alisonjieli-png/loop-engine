# Native context-file candidates

This pilot holds **two original candidate task briefs**. Each has four native
client renderings. They are two logical items, not ten approved catalogue
items. Only a selected client’s `work/` files would enter a fresh step
workspace. The sibling `review-note.json` stays outside the model-visible
workspace and records required render inputs, effect boundaries, exact-byte
digests and remaining review.

```text
Native context-file pilot
├── repair-one-failing-test/
│   ├── codex/work/AGENTS.md
│   ├── claude/work/AGENTS.md and CLAUDE.md
│   ├── opencode/work/AGENTS.md
│   ├── pi/work/AGENTS.md
│   └── review-note.json
└── profile-one-csv/
    ├── codex/work/AGENTS.md
    ├── claude/work/AGENTS.md and CLAUDE.md
    ├── opencode/work/AGENTS.md
    ├── pi/work/AGENTS.md
    └── review-note.json
```

Every `{{...}}` placeholder must be rendered from a validated, typed task
contract before installation. The rendered brief is still a proposal until
its exact bytes and native placement are independently qualified. The text
does not supply permissions. It is not a substitute for effect authority,
client isolation, a native-load observation, or a checked task outcome.

The paths follow the [placement research](../../../docs/research/NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md)
and the official [Codex instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[Claude memory and imports](https://code.claude.com/docs/en/memory),
[OpenCode rules](https://opencode.ai/docs/rules/), and
[Pi context files at v0.73.1](https://github.com/earendil-works/pi/blob/v0.73.1/packages/coding-agent/docs/usage.md).
The installed clients reported Codex 0.155.1, Claude Code 2.1.280,
OpenCode 1.17.9 and Pi 0.73.1 during this pilot. The earlier no-model
placement experiment tested OpenCode 1.18.32; the exact installed OpenCode
version still needs its own native-load observation on rendered files.
`CODEX.md` is absent: Codex does not auto-discover that name by default.
The separate [configured-fallback probe](CODEX-MD-CONFIGURED-FALLBACK-2026-09-22.json)
used a temporary `CODEX.md` in a clean git root. Codex 0.155.1 omitted
its marker with the default empty fallback list and included it when the
isolated configuration explicitly set
`project_doc_fallback_filenames = ["CODEX.md"]`. This is no-model
prompt-input evidence for an optional route, not a third package or a
default Codex behavior claim.

Run `python3 check_context_candidates.py` here to verify file names, the
local Claude import, placeholders, expected duplication and source digests.
An edited-byte copy was rejected by that checker. A separate no-model
`codex debug prompt-input` probe saw both unchanged template files after
each was copied into its own fresh git root with an empty home and Codex
configuration directory. A direct probe from the candidate folder inside
this shared repository did not show the candidate marker; the fresh root
is the intended step layout. Neither probe rendered the task inputs or
started a model. Independent review, hosted indexing, retrieval, rendered
native discovery in all four clients, model use and task benefit remain open.
The [initial nested attempt](CODEX-NESTED-DISCOVERY-INITIAL-2026-09-22.json)
and [isolated-root successor](CODEX-NO-MODEL-DISCOVERY-2026-09-23T023342361705Z.json)
retain both observations.
