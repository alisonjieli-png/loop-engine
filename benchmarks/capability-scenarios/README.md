# Open-ended capability scenarios

This directory holds machine-readable capability scenarios. A scenario is
a typed task record that a Practitioner or self-improvement Loop can read,
compile, execute, verify, and log. A scenario is data. It is not a new
runtime type, a new Loop profile, or an instruction to bypass the
architecture.

Every scenario below is an open-ended, developer-style task that exercises
capability gaps the engine must close over time: external search,
authorized download, media transformation, generative rendering, LLM-led
subjective verification, and self-awareness about missing capability.

`catalog.json` is the source of truth. Every record names its inputs,
operators, expected output, authorized effects, verification, and the
capability requirement that must exist before the engine can claim the
task solved. Unavailable capabilities surface as typed capability gaps,
not silent failures.

## How to read the records

- `task_id`: stable, versioned identity.
- `family`: the capability family the task exercises.
- `text`: the task prompt as a user would write it.
- `operators`: the intellectual operations the task requires (from the
  operator vocabulary: retrieve, fetch, transform, generate, validate,
  diagnose, learn).
- `authorized_effects`: effects the scenario may use when authorized;
  everything outside the list needs a separate approval.
- `verification`: how the solution must prove it worked, including
  subjective visual verification where applicable.
- `requires_capabilities`: capability IDs the engine needs. Missing
  entries become capability-gap records.
- `mode`: suggested run mode (deterministic, hybrid, non_deterministic);
  the compiler decides.

## Families

- `media.image_to_video` — image search, download, Ken Burns-style
  transitions, slideshow video assembly.
- `media.video_people_rigging` — download videos with people, run limb /
  motion rigging, render highlighted outline overlay.
- `media.game_generation` — three.js or Minecraft-style generation with
  visual verification of texture alignment, overlap, realism.
- `data.open_data_report` — download an open dataset, generate a report.
- `data.sec_filings` — download SEC filings, extract, report.
- `data.laws_states_pdf` — laws across all 50 states, compiled PDF.
- `data.stock_prediction` — prediction task with explicitly selected
  modeling approach (fundamentals, analogy, or first principles).
- `data.kaggle_advanced` — end-to-end advanced Kaggle workflow.
- `data.schema_org_pipeline` — ingest a dataset, standardize to
  Schema.org, typo-check, entity resolution.
- `meta.capability_gap` — self-awareness scenario: log missing capability
  instead of pretending the task ran.

## Rules

- A scenario that needs network names the requirement in
  `authorized_effects`; discovery alone must stay effect-free.
- Downloaded media stays in its declared workspace and never leaves the
  user's machine without a separate approval.
- A subjective output (does it look right) requires a declared visual
  verifier path — a deterministic check where possible, a bounded model
  check where authorized, never an unchecked "it seems fine."
- The engine may decline a scenario with a capability-gap report. Decline
  is an honest result; silent failure is not.
