# The Harness Working Directory Compiler component

Kind: dated component design record, September 23, 2026 local time. It names
one functional component — the Harness Working Directory Compiler — and the
standing profile handshake that keeps it current. It builds on the verified
[file standards and their differences](HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md),
the [file-kinds and admission research](HARNESS-INTELLIGENCE-FILE-KINDS-AND-ADMISSION-2026-09-22.md),
the [placement research](NATIVE-HARNESS-INTELLIGENCE-PLACEMENT-2026-09-22.md),
and the agent-harness prior-art review. It introduces no new runtime type and
no new intelligence layer, per the classification in those records. The
[roadmap](../roadmap/roadmap.yaml) stays the task authority.

## The component

The compiler is the functional component that turns selected, approved
intelligence into the exact working directory one harness reads. It is the
typed edge that every other part of the system talks to; the per-harness
profile and the placement rule are its swappable engines. A caller never builds
a directory by hand, never names a path, and never guesses a filename: it asks
the compiler for a plan against an item identity and a target harness, and the
compiler answers with a typed, versioned placement plan or a refusal.

```text
Harness working-directory compiler
├── Typed edge (fixed, versioned): compile a placement plan
│   ├── input: a selected item's identity + digest + kind + family, the
│   │   target harness, and the step's declared authority and scope
│   ├── output: placement_plan/v1 (per-file rendered identity, path, digest,
│   │   load rule, precedence note, trust requirement) or a typed refusal
│   └── never touches the model, never writes before authorization
├── Engine one: the per-harness profile records (data, swappable)
│   └── harness_file_profile/v1 per harness and version
└── Engine two: the placement rule (how an item maps through a profile)
    └── today: native location lookup, digest-bound render, conflict policy
        per the existing native-client seam
```

The owner direction this implements, September 23, 2026: most differences are
absorbed by per-harness profiles plus the compiler; a few corner cases need a
duplicated, harness-specific file, which the plan represents as an explicit
variant of one item, never a silent second copy.

## The two engines and why they are separate

The profile records and the placement rule are swappable independently.

- **The profiles are data.** One versioned record per harness and version.
  Adding a harness is adding a record; a version changing is a new record. The
  catalog holds them; the serving policy gates them like anything else.
- **The placement rule is logic.** It reads a profile, resolves an item's kind
  and family to the harness's native location, renders the body to exact
  digests, refuses a conflict or an unsupported kind, and compiles the plan.
  Today this is the native-client placement seam; the compiler extends that
  seam rather than replacing it.

The seams already exist in `tools/install_selected_material.py`:
`ClientLayoutProfile` (one native location per served kind, plus a native
listing command and observed versions) and its refusals
(`client_has_no_layout_profile`, `kind_has_no_native_location`,
`install_not_authorized`). The compiler generalizes that record from one
profile (OpenCode) into a registry keyed by harness and version, and keeps the
typed refusals.

Verified on September 23, 2026, without a model turn and without writing a
file: four profiles instantiated from the same record type for Claude Code,
Codex, Gemini CLI and OpenCode each resolve the one item identity `my-skill`
to its correct native skill path — `.claude/skills/my-skill/SKILL.md`,
`.agents/skills/my-skill/SKILL.md`, `.gemini/skills/my-skill/SKILL.md`,
`.opencode/skills/my-skill/SKILL.md` — with no change to the placement rule,
only the profile data. That is the flexibility working: one item, four
harnesses, four destinations, one lookup.

## How the verified differences map through, cleanly

The compiler exists *because* these differ, and each maps to a profile field:

| Difference (verified) | Absorbed by |
|---|---|
| Codex instruction file: global `~/.codex/AGENTS.md` first, then root→cwd, one candidate per directory; `CODEX.md` only as a configured fallback that never beats `AGENTS.md` | the profile's instruction placement record: target path, precedence slot, and "fallback only when no AGENTS.md exists" trust note |
| Claude Code reads every ancestor `CLAUDE.md` + `CLAUDE.local.md`, and `AGENTS.md` only when no `CLAUDE.md` is in the ancestry; `.claude/rules/**/*.md` is a separate class | the profile records `CLAUDE.md` as the instruction file, marks `AGENTS.md` as a conditional alternative, and gives `rules/` its own placement class with per-file path gating |
| Aider auto-loads no instruction Markdown | the profile has no instruction location; the plan falls back to the `read:` config mechanism or refuses step instructions there explicitly |
| Goose reads both `.goosehints` and `AGENTS.md`, but has no per-project config | instruction placement lists both files; configuration placement is recorded as global-only |
| Gemini adds a just-in-time subdirectory tier | the profile marks the JIT tier so the plan knows a nested file is discovered lazily, not at start |
| Skill precedence is per-harness (Claude user-before-project; Codex repo-last; Gemini workspace-over-user) | the profile records the precedence class the plan must honour; the conflict policy resolves or refuses before writing |
| Claude hooks merge across every scope and managed hooks cannot be disabled; Codex has no custom slash-command files; Goose recipes are name-resolved on demand | each has a typed `unplaced` entry in its profile with a refusal reason, so the compiler refuses rather than emits a file the harness ignores |
| Codex `model_instructions_file` replaces built-ins; `instructions` key is reserved and inert | the configuration placement record names the real key and refuses the reserved one |

## The standing handshake that keeps it current

The profiles go stale, because the harnesses ship weekly. The design bakes a
standing, near-daily intelligent handshake between the library and the
harnesses it has qualified, structured as Loop work per the classification:

1. A scheduled Intelligence query asks each qualified harness's own native
   mechanism what it discovers now — Claude's `--help` and docs surface,
   Codex's `codex debug prompt-input` probe, Gemini's settings layering,
   OpenCode's config, Goose's `goose info` and hint loader.
2. The observed layout and precedence are compared to the stored profile
   record of the same harness and version.
3. A divergence is not patched in place: the stale profile is kept, a new
   versioned profile record is written beside it, and the new record stays a
   candidate until it is reviewed. No host serves it by default until then.
4. A confirmed change rolls the placement plan for future steps to the new
   profile version; nothing running is mutated.

This is the flexibility the owner asked for: the library learns a harness's
difference by measurement and stores it as data, so serving stays a lookup,
not a cascade of tool-specific code.

## Current state, future state, evolution vectors

- **Current state:** the native placement seam with one wired profile
  (OpenCode) exists and is checked; the family policy, the open intelligence
  folders, the file-kinds admission and the standards matrix are on main or
  staged in the shared checkout.
- **Future state:** the compiler as one functional component behind a typed,
  versioned edge; one verified `harness_file_profile/v1` per supported
  harness and version; a variant mechanism for the genuinely harness-specific
  file; and the standing handshake keeping profiles measured.
- **Evolution vectors:** (1) promote `ClientLayoutProfile` to the versioned
  `harness_file_profile/v1` registry keyed by harness and version, without
  changing the existing refusals; (2) add Codex, Claude Code, Gemini, Goose,
  Aider profiles from the verified matrix, each landing as a reviewed record;
  (3) add the explicit file-variant mechanism for corner cases, bound to one
  item identity and digest; (4) add the handshake probes as admission checks
  and a scheduled Intellgence query, so staleness is detected by measurement
  before a customer hits it. Each is a data or registry change at the
  catalogue edge, never a fork of the runtime and never a new intelligence
  layer.

## Known-wrong controls (so a claim cannot coast)

| Known-wrong case | What the compiler must do |
|---|---|
| An item is compiled for a harness whose profile has no shape for its kind | Refuse with `kind_has_no_native_location`, naming the kind and harness |
| Two selected items render to the same native path and name | Refuse or resolve under an explicit policy before any write |
| A profile's observed version no longer matches the installed harness | The handshake surfaces a new candidate profile; the old plan stays until replaced |
| A harness-specific variant is created as a second silent copy of a body the Loop family owns | Refuse; a variant is an explicit, digest-bound rendering of one item, never a duplicate body |
| A plan is requested for Aider with step instructions and no opt-in record | Refuse or emit the `.aider.conf.yml` `read:` mechanism, never a bare Markdown file it will not auto-read |
| The plan names a path but the native probe does not list the file | The step may not claim the item was loaded; placement and discovery are separate facts |
