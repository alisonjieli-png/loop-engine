# Review note: Verify acceptance criteria have evidence

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a12_ticket_result_verifiers, model family anthropic. An earlier pass of the same generator wrote the first version on September 23, 2026; this pass reviewed it, changed it and checked it again. The earlier bytes are kept in `packages/verify_criteria_have_evidence/earlier-attempt-20260924T0101Z.tar.gz`. This note is never delivered to a harness.

## Method

One verifier method. The script reads a ticket checklist (Markdown or JSON) and a set of evidence entries (JSON), gives every criterion an id (its own, such as `AC-1`, or C1, C2 in order), and then checks each entry against the files it cites before it counts. A `test` entry holds up only when the named test, or every parameter case of it, passed in the saved test output, read with the same pytest, unittest, Go, Cargo and JUnit XML readers as the fail-then-pass verifier. A `command` entry must cite the saved output of its run; the script reads that file by itself (a JSON record with an exit code or `passed` flag, a JUnit XML file, or a runner summary line) and the entry holds up only when the file does not contradict the stated exit code and that code equals the expected one. A `file` entry holds up when the file exists, matches its digest and holds the required text. A failing test, a wrong exit code or an output that contradicts its exit code contradicts every criterion the entry names. A criterion passes only with at least one entry that holds up and none that contradicts it; an entry that names an unknown criterion also fails the run, because it usually hides a mistyped id. A ticked box never counts.

## Authoring basis and sources

Original text and code, written for this wave, MIT like the repository. No outside text or code was copied. Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `artifacts/first-party-harness-candidates-2026-09-22/packages/software/map-independent-acceptance-evidence/SKILL.md`: the closest existing method, a prose procedure that maps completion claims to evidence and its provenance.
- `src/loop_engine/core/overnight_outcome.py`: grades a night from the gate's exit code and structured state and never asks a step whether it succeeded; the command and test entries here apply the same rule to each criterion.

The output readers were checked in this pass on real outputs of pytest 9.1.1 (`-v`, `-rA`, `-q`), pytest's JUnit XML writer and `python -m unittest -v` on Python 3.14.4 and 3.10.20, made in a probe project under `generator-a12-work/probe/proj`: every failing run read as a failure and every passing run as a pass. The JSON criteria reader accepts the `ticket_criteria/v1` shape that the a03 `extract_ticket_acceptance_criteria` script writes (an `acceptance_criteria` list of objects with `id` and `text`); a test uses that shape.

## Inputs and outputs

Inputs: `--criteria` and `--evidence` (paths below `--root`, one of them may be `-` for standard input), optional `--format` for the saved test outputs. Every input and cited file is at most 64 MiB. Output: one JSON object with `verdict`, `uncovered`, `contradicted`, `unknown_criteria`, a row per criterion (id, text, status, supporting and contradicting entries, whether it was ticked), `evidence_problems`, `warnings`, counts and the digests of the two main inputs.

## Effects

`reads_fs`: the script reads the checklist, the evidence and every cited file, refusing `..`, paths that resolve outside `--root`, non-regular files and oversized input. A cited path outside the root is reported as a problem of that entry, not read. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The instructions never tell the reader to write an evidence file; entries without a file go through standard input.

## Closest existing items

- `map_independent_acceptance_evidence` (wave 1, prose): builds a provenance map and flags circular evidence by reading. This package executes one narrower rule: every criterion needs cited evidence that holds up against real files, and it returns a machine verdict. Independence of evidence stays in the checklist.
- `write_acceptance_criteria_a_reviewer_can_check` (starter, prose) and `extract_ticket_acceptance_criteria` (wave 5, a03) produce criteria; this package checks criteria against evidence afterwards.
- `verify_morning_report_claims` (a12) checks a whole night's report against evidence files; this package checks one ticket's criteria.
- A search of `scout/existing-inventory.tsv` found no executable criteria-to-evidence check.

## Positive example

`examples/criteria.md` holds four ticked criteria under "Acceptance criteria", one with a nested detail line that is not a criterion. `examples/evidence.json` cites a passing test in `examples/test-run.txt` for AC-1 and AC-2, a command with exit code 0 and the digest of that output for AC-3, and `examples/changelog.txt` containing "slugify" for AC-4. The verdict is pass with four criteria covered.

## Known-wrong example

The same evidence without the AC-4 entry: AC-4 is ticked but uncovered, the warning says so, and the script exits 1. The tests also cover citing the failing run `examples/test-run-before.txt` (AC-1 and AC-2 contradicted), exit code 1 (AC-3 contradicted), a command without its saved output (`output_not_cited`), exit code 0 beside an output that shows a failure (`output_shows_failure`), a nonzero exit beside a passing output (`output_shows_pass`), an exit code that the saved record `examples/style-check.json` contradicts (`exit_code_contradicted`), a wrong digest, a missing file, missing text, a mistyped criterion id, a note offered as evidence, a test that is absent or skipped, and a cited path outside the root.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/verify-criteria-have-evidence/`, `.agents/skills/verify-criteria-have-evidence/` (Codex), `.opencode/skills/verify-criteria-have-evidence/`, `.pi/skills/verify-criteria-have-evidence/` and `.gemini/skills/verify-criteria-have-evidence/`. Basis: specification section 6 marks the first four skill folders observed and the Gemini CLI folder documented. No harness binary was run. A host-style walkthrough (recorded in `PRECHECKS.txt`) copied the folder to `.pi/skills/verify-criteria-have-evidence/` in a fresh workspace, found it with the discovery command of `SKILL.md`, and ran the first action as written with a Markdown ticket and a real pytest `-rA` output: pass, and both criteria contradicted when the output was swapped for the failing run. Unverified: whether each harness gives the model the folder path for SKILL_DIR (the entry gives an `ls -d .*/skills/...` fallback), and whether a harness allows a heredoc on standard input without a prompt.

## Customer requests

- "Check that every acceptance criterion on this ticket has real evidence."
- "The agent ticked all the boxes. Which ones are actually backed by a passing test?"
- "Fail the ticket if any requirement has no proof."

## Limits

The script reads a command's saved output but cannot prove that the output came from that command; the checklist asks where each exit code came from. An output without a summary line it knows is accepted on its exit code, and the detail says the output showed no summary. The script cannot judge whether a passing test really checks the criterion it is cited for. Markdown criteria must be list items under an acceptance, criteria or done heading, or checkbox items; prose criteria in a paragraph are not found and the run is refused. An id such as `UTF8:` at the start of an item is read as a criterion id.

Checks that failed before they passed. Earlier pass, as its own note recorded: the first test file held a leftover line in one test and did not cover a skipped test cited as evidence; both were fixed, and a mutation pass over 18 guards killed every one. This pass: the baseline check (run 1 in `PRECHECKS.txt`) refused the package because it had no `package.json`. Review found that a `command` entry could cover a criterion with an exit code typed into the evidence and no saved output, which a model finishing a night could write from memory; the output is now required and read. Each new guard was removed once in a temporary copy and its named test failed; two inherited guards were removed the same way and their tests failed too.
