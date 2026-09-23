# Native passive-path repair, September 23, 2026

Independent review reproduced two gaps in the initial native review profile:
`opencode.json` containing a plugin declaration and `.pi/settings.json`
containing a package declaration passed when labelled as passive JSON data.
No package was installed, executed, approved or published in that experiment.

The new format-engine implementation, version two, reserves known native
configuration basenames and activation directories regardless of claimed file
role or media type. Root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` instruction
entrypoints and a root `SKILL.md` skill entrypoint have their existing explicit
qualification paths. Supporting resources otherwise belong under `examples/`,
`verification/`, `references/`, `assets/` or `contracts/`; the licence notice
has its existing exception. Unknown required activation paths remain held.
This checks contradictions and eligibility. No filename grants permission.

The restriction also catches configurations disguised as a reference,
instruction or JSON Schema, including nested reserved config names. It
preserves the input/output contracts and example data in the twelve original
packages. A positive schema fixture was moved into the profile's `contracts/`
location; its MIME and regular-expression checks remain in place.

Evidence in [the existing evidence directory](../../artifacts/native-package-review-2026-09-23/README.md):

- `tests-before-passive-path-repair.txt`: nine failed assertions reproduced the
  missing boundary, including an arbitrary root JSON resource.
- `tests-after-passive-path-repair.txt`: one positive fixture still used an
  unqualified root schema location; the expected layout was corrected.
- `tests-passive-path-final.txt`: all 24 native checks passed.
- `tests-passive-path-component-final.txt`: all 262 component tests passed,
  with one optional dependency skip.
- `removed-guards-20260923T151501927593.json`: all eleven native removed-guard
  controls detected the missing guards.
- `mixed-native-originals-after-passive-path-repair.json`: all twelve complete
  original packages pass static prechecks, with zero approvals or model calls.

The previous native patch is retained unchanged. This is a separate successor
delta. Old static checks do not retroactively gain this new qualification;
the independent admission process must judge exact current package bytes and
current checks before publication. This task changes no hosted approval record.
