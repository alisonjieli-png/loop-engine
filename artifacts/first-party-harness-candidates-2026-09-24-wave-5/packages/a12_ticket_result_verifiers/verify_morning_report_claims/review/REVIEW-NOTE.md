# Review note: Verify morning report claims

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a12_ticket_result_verifiers, model family anthropic. An earlier pass of the same generator wrote a first script, tests and examples on September 23, 2026 and stopped before the entry file, the checklist, this note and the manifest; this pass reviewed that script, rebuilt its checking core and wrote the rest. The earlier bytes are kept in `packages/verify_morning_report_claims/earlier-attempt-20260924T0101Z.tar.gz`. This note is never delivered to a harness.

## Method

One verifier method. The script reads a morning report and, for every item that claims completion, opens each cited evidence file below the root. A citation fails when its file is missing, unsafe or unreadable, when its bytes differ from a cited SHA-256 digest, when a cited exit code differs from the exit code the file records or from the result it shows, or when the file shows a failure where the citation states a pass. An item fails when it cites nothing, or when no cited file without a problem shows a passing run by itself (a JSON gate record, a JUnit XML file without failures, or a runner summary line). Some findings need a reader, not a refusal: a failing file cited with no stated expectation (often the run before the fix), a step handoff whose listed files have other bytes now, and a pass reached by changing only tests. They go to `needs_reading` with verdict `review`. For a `night_morning_report/v1` record the script also opens each complete entry's `night_step_handoff/v1` file, requires status complete, compares every listed file with its recorded digest, checks the report's counts against its lists, and warns about notes whose file is missing. A `ticket_reproduction_run/v1` record with the verdict `failing_test_recorded` counts as a failure recorded on purpose, never as a pass. Exit 0 pass, 1 fail or review, 2 refused.

## Authoring basis and sources

Original text and code, written for this wave, MIT like the repository. No outside text or code was copied. Sources at the pinned revision `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format this candidate follows.
- `src/loop_engine/core/overnight_outcome.py`: grades a night from the gate and structured state and never asks a step how well it did; its rung names (`verified`, `negative_result`, `blocked_named`, `verified_by_test_change` and the rest) are the status words the script knows, and `verified_by_test_change` is always sent to reading.
- `examples/29_intelligence_service/starter-catalogue/bodies/reproduce_the_evidence_a_report_claims.md`: the closest prose method.

The night report, handoff, reproduction and verification record shapes are those of the wave 5 a09 packets `morning_report_packet`, `ticket_reproduction_packet` and `ticket_fix_verification_packet` in this wave folder (not on `main`). The shipped night example and its handoff were validated against the a09 `output.schema.json` and `handoff.schema.json` with `jsonschema` draft 2020-12, and both are valid.

## Inputs and outputs

Inputs: `--report` (a path below `--root` or `-` for standard input), optional `--require-digests` and `--claim-word`. Every input and cited file is at most 64 MiB, and at most 1000 files are read. Output: one JSON object with `verdict`, `unsupported` (item, status, problems), `needs_reading` (item, status, reasons), `supported`, `unbound` (citations without a digest), `not_claims`, `report_problems`, `warnings`, an `evidence` list that pairs every claim with what its file shows, counts, the report form and the digest of the report.

## Effects

`reads_fs`: the script reads the report, every cited evidence file and handoff, and every file a handoff lists, refusing `..`, paths that resolve outside `--root`, non-regular files and oversized input. `spawns_process`: `SKILL.md` tells the reader to start `python3`, and the tests start the script with `subprocess`. The script writes nothing, starts no process, uses no network and reads no secret. The tests read the shipped examples or pass text on standard input and write no file.

## Closest existing items

- `reproduce_the_evidence_a_report_claims` (starter, prose): a person reruns the numbers of a claim. This package reruns nothing; it checks that each cited file is there, unchanged and says what the report says.
- `verify_an_agent_result_without_trusting_its_summary` (starter, prose) and `report_observed_derived_assumed_and_unknown` (served, prose): the practice of not trusting a summary, with no executable part.
- `morning_report_packet` (wave 5, a09) compiles the report and checks only that each cited path exists; its context says a separate check of the finished report may run later. This package is that check: digests, exit codes, passing runs, handoff digests and counts. `write_step_handoff` (a06) writes one step's handoff; `verify_criteria_have_evidence` (a12) checks one ticket's criteria.
- A search of `scout/existing-inventory.tsv` found no executable check of a report against its evidence.

## Positive example

`examples/night-morning-report.json` marks T-104 complete with two claims: the reproduction record `examples/evidence/t104-reproduction.json` shows a failing run recorded on purpose, and the verification record `examples/evidence/t104-verification.json` shows six passing checks. The handoff `examples/handoffs/t-104-verification.json` says complete and its listed file matches its digest. The verdict is pass with T-104 supported and T-105 and T-106 listed as not claims. The generic `examples/night-report.json` and the Markdown table `examples/night-report.md` also pass.

## Known-wrong example

`examples/night-report-overclaimed.json`: T-205 cites a log with exit 0 whose summary says 1 failed (`exit_code_contradicted`, `no_passing_gate_evidence`); T-206 cites nothing (`no_evidence`); T-207 cites a passing gate with the digest of another file (`digest_mismatch`); T-208 cites a gate record with `passed` false (`evidence_shows_failure`); and the report counts four verified items where its entries give three (`count_mismatch`). The verdict is fail and only T-201 is supported. The tests add a missing handoff, a handoff whose files changed, a handoff that says unfinished, a reproduction record cited as a pass, a failing run with no stated expectation, and a note whose file is missing.

## Harness placement and verification state

The whole folder is copied with `copy_exact_bytes` to `.claude/skills/verify-morning-report-claims/`, `.agents/skills/verify-morning-report-claims/` (Codex), `.opencode/skills/verify-morning-report-claims/`, `.pi/skills/verify-morning-report-claims/` and `.gemini/skills/verify-morning-report-claims/`. Basis: specification section 6 marks the first four skill folders observed and the Gemini CLI folder documented. No harness binary was run. A host-style walkthrough (recorded in `PRECHECKS.txt`) built a night of four handoffs under `.baltor/night/`, compiled it with the a09 `compile_morning_report.py` script itself, which listed three tickets as complete because their cited files exist, then copied this folder to `.gemini/skills/verify-morning-report-claims/`, found it with the discovery command of `SKILL.md` and ran the first action as written: T-301 supported, T-302 unsupported because its cited run failed, and T-304 in `needs_reading` because a file its handoff lists changed afterwards. Unverified: whether each harness gives the model the folder path for SKILL_DIR (the entry gives an `ls -d .*/skills/...` fallback), and whether a harness asks for permission before `python3` runs from a skill folder.

## Customer requests

- "Before I read the overnight report, tell me which done items are not backed by their evidence."
- "The agent says all tickets passed. Check the logs it cites."
- "Did anything change after the night's handoffs were written?"

## Limits

The script cannot tell whether a claim's sentence matches what its file shows; it pairs them in `evidence` and sends failing files without a stated expectation to reading. It cannot tell whether a passing run happened after the last change for its ticket; the checklist asks. A citation without a digest is accepted and listed under `unbound` unless `--require-digests` is given. Markdown reports are read only from a table with a status column and an evidence column. Blocked and unfinished items are not checked. A handoff is compared only for `night_step_handoff/v1` records.

Checks that failed before they passed. The baseline check (run 1 in `PRECHECKS.txt`) refused the earlier bytes: no `SKILL.md`, no checklist, no note, no `package.json`. Review of the earlier script found a literal em dash in a string, which the vocabulary pre-check refuses, and an invisible variation selector; both are now escapes. It also found that every failing file under a complete claim was refused, so an honest night report that cites its run from before the fix would fail, while the a09 reproduction record was read as an unknown word; the expectation rule, the reproduction record rule and the review verdict fix both. The generic examples first reused the ticket ids and night of the a09-shaped example with other meanings; they now use T-201 to T-208 and the night of September 21. Each new guard was removed once in a temporary copy and its named test failed; three inherited guards were removed the same way and their tests failed too.
