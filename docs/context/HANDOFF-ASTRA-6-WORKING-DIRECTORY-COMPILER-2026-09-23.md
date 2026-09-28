# Handoff to Codex Astra 6.0: the working-directory compiler, wrapping, and engine swappability

Kind: development handoff. Date: September 23, 2026 local time. Written by
Claude Code for Codex Astra 6.0 to review, research, adjust and improve. None
of this is authoritative or assigned; every direction below is a suggestion
with its reasoning and its open questions, and Astra's own findings outrank it.
The standing rules and the work authority are the
[commit, push and release authority section](../../AGENTS.md#commit-push-and-release-authority)
and [roadmap.yaml](../roadmap/roadmap.yaml). Read
[the September 22 handoff](SESSION-HANDOFF-2026-09-22.md) and
[the start route](START-HERE.md) before acting; the live deployment record
they point to is the ground truth for what runs today.

This handoff deliberately does not tell Astra to build. It hands over a design
space and the evidence behind it, and asks Astra to close the open questions,
find what is wrong, and implement what survives its own review.

## The goal the owner set

Make the system flexible enough to serve any standard harness well, no matter
which harness the runtime selects as the most efficient for a step. That means
three things working together: a component that produces the exact working
directory the selected harness reads; per-harness knowledge that is kept
current by measurement rather than by editing code; and every functional
component wrapped so that one component's engine can be swapped without any
neighbour changing. The owner's words over September 21 to 23 are gathered in
that authority section: swappable engines for each functional component, a
search for existing work before building, and consolidation onto one main
branch with the checkpoint as the only backup.

## Part one: the Harness Working Directory Compiler

The suggested component is the
[Harness Working Directory Compiler](../architecture/HARNESS-WORKING-DIRECTORY-COMPILER-2026-09-23.md)
(the short form Agent Working Directory Compiler names the same component). It
turns selected, approved material into **Harness Working Directory Component
Files** — the specific files a harness discovers in its working directory — by
reading a **Harness File Profile** and producing a **Placement Plan**. The
three names are pinned in
[terminology.yaml](../../terminology.yaml) under `vocabulary`.

Why this shape is suggested, not asserted:

- The verified differences between harnesses are real and structural (the
  instruction file's name, scope and precedence; the skill root and precedence;
  the configuration location and trust rule; and several harnesses with classes
  they never auto-load). They are mapped in
  [the file-standards record](../research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md).
  A fixed layout silently places files a customer's harness never reads.
- A seam that already exists in `tools/install_selected_material.py`
  generalizes: one `ClientLayoutProfile` record type, instantiated for Claude
  Code, Codex, Gemini CLI and OpenCode, resolves one item identity to four
  correct native skill paths with data alone. Proven on September 23 with no
  model call and no write.
- Most of the work is therefore profile data, not logic. The compiler's edge
  stays fixed; a new harness is a new profile record; a corner case that needs
  a harness-specific file is an explicit, digest-bound variant of one item.

Open questions Astra should pressure-test before building:

1. Is `native_client_layout_profile` the right record to promote to
   `HarnessFileProfile`, or should the compiler read a clean new record
   version and leave the old one as history? The pre-launch version policy
   permits the clean version; the choice affects existing check fixtures.
2. Should the Placement Plan carry one selected harness's layout, or carry a
   small set of qualified alternatives so a fallback harness can be chosen
   without recompiling? The latter matches the configuration-dimension
   requirement but costs plan size and probe work per step.
3. The Aider case has no auto-loaded instruction file. Should the compiler
   refuse instructions for Aider, or fall back to `.aider.conf.yml`'s `read:`
   mechanism? The latter changes placement from "write a file" to "write a
   line in a config", which may want its own mechanism record.
4. The standing handshake (the near-daily intelligent probe of each qualified
   harness's own native discovery surface) is the suggested way to keep
   profiles current. Whether it is a scheduled Loop, a host attestation rerun,
   or something else is open; the design should not assume a second scheduler.

## Part two: wrapping and engine swappability at every scale

The owner direction over three days: every functional component, large or
small, wrapped on a fixed typed and versioned edge, with one or more swappable
engines behind it and runtime selection by declared order and recorded
evidence. The same pattern at the component level, above it, and below it.

What is already real, from the September 22 review of the source: several
small typed edges exist — `ExternalHarnessAdapter`, `ProviderAdapter`,
`CatalogStore`, `WorkspaceBackend`, the message and protocol transport, the
retrieval backends, the similarity source. The compiler above would sit behind
the same shape. What is missing, and what this handoff asks Astra to complete
or correct, is the layer above those edges:

- **The typed executor interface for phase 2.** The harness-first decision
  promises that every executable step delegates to a harness or a future
  custom engine behind one typed seam. Today there is no such seam; the SDK
  adapters run in-process and the process harnesses are selected by object
  construction, not by a declared profile. The suggested record (from the
  seam review) is an `ExecutorProfile` with identity, kind, declared isolation
  and capabilities, chosen by host profile instead of import path. Astra should
  say whether that record belongs on the external harness seam, or elsewhere.
- **The recipe registry.** Adding a harness today edits three places. The
  suggestion is one versioned recipe record (prepare, extract, instruction-file
  profile, sandbox mounts, supported styles) so adding or replacing a harness
  engine is a record, never three edits.
- **One component contract, applied uniformly.** The
  `component_interactions.yaml` catalog has seven declared edges; the real
  system has more. The suggestion is that every functional component and
  subcomponent is declared with its request and result contracts, and that new
  engines register against the same declaration. This is also where the
  wrapping becomes verifiable rather than conventional: an edge that cannot
  name its request and result contracts is the known-wrong case.

The guard that should hold across all of it: an engine is an adapter a Loop
uses, never a second runtime type, and never a `*Node` class. The classification
in AGENTS.md applies to every suggestion above.

## Part three: containerization and separation

Recorded as open suggestions, not decisions:

- A step's working directory and the harness's own state are separate concerns
  already partially separated (the placement research's two roots). Whether the
  compiler emits a directory, a container image layer, or a mounted overlay is
  open; the deciding constraint is that a plan must be reproducible and
  digest-bound either way.
- Process isolation for a delegated step is the harness-side sandbox (the
  process harnesses already run under one). The compiler never grants a
  broader effect than the step's declared authority, and an engine that cannot
  meet a declared isolation requirement refuses instead of downgrading.
- The one-machine one-volume deployment today is recorded in the live
  deployment section; the compiler's output does not depend on it and should
  not entrench it.

## Evidence a successor should keep intact

- The September 22 line-survival and merge-repair record: merging branches
  silently dropped real work, and the repairs are what is on main. Any
  consolidation Astra continues builds from that archive, not from memory.
- The release that shipped the front end and the catalogue (release 12):
  [its handoff section](SESSION-HANDOFF-2026-09-22.md) names the grants step,
  the key reissue step and the per-hostname checks every release repeats.
- The candidate-only state of every harness-intelligence format pilot:
  nothing in the pilots is approved, granted, or qualified, and the
  candidates require independent review before joining the active catalogue.

## Closing note to Astra

The owner asked for this to be written openly and for Astra to consider,
research, adjust and improve. The single most useful thing Astra can do with it
is to falsify its weakest assumption, record the finding beside the suggestion
it replaces, and only then build. Nothing here is a pass claim, and no part of
it grants an effect the classification does not permit.
