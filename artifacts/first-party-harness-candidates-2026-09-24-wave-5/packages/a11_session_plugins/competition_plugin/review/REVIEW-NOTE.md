# Review note: competition_plugin

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a11_session_plugins, model family
anthropic. This note is never delivered to a customer harness.

## Method

One session kit for a data science competition, where every session starts
fresh and must not lose the competition's rules. Three parts:

1. A session start hook (`scripts/brief_summary.py`) validates the
   competition brief and adds a short summary to the new session: metric and
   direction, target and id columns, submission columns, validation scheme,
   data version, deadline, daily submission limit, rules, and the number of
   experiment notes with the latest one.
2. An experiment note command sends one note to `scripts/experiment_note.py`,
   which checks it against the brief (metric name, fold count, data version),
   refuses a reused experiment id, computes the fold mean and population
   standard deviation itself, refuses a draft that carries its own mean, and
   records the SHA-256 of the submission file when one is named.
3. A pre-submission gate skill (`skills/pre-submission-gate/`) decides
   `ready_for_host_upload` or `hold` from eight checks, appends every decision
   to a gate log, and never uploads. The skill folder is self-contained so it
   works when copied alone.

## Authoring basis and sources

Original text and code under the repository MIT licence; nothing copied from
outside projects. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:
`src/loop_engine/core/service_runtime/catalogue_packages.py` (package file
contract) and `benchmarks/kaggle_competitions/README.md`, which separates
metadata access, source qualification and a scored solve, and records that
no score is claimed; this plugin likewise keeps the upload with the host.
Format facts: the Claude Code manifest, command and hook layout (SessionStart
`additionalContext`) follows the Codex plugin candidate whose SessionStart
hook ran on Claude Code 2.1.280; that observation does not cover a plugin
`skills/` folder, so the skill's pickup there is unverified. The research file
`HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` in the Codex integration
worktree documents the Gemini CLI extension layout. The Gemini hook details
were checked by reading, not running, the installed Gemini CLI 0.59.0 source:
SessionStart sources are `startup`, `resume` and `clear`; a lifecycle matcher
is compared as an exact string, so the Gemini registration has no matcher;
`timeout` is in milliseconds (default 60000); `${extensionPath}` is filled in
hook commands; hooks are on by default; and
`hookSpecificOutput.additionalContext` is added to the session wrapped in a
`hook_context` tag, with angle brackets escaped.

## Inputs and outputs

Inputs: `.baltor/competition/brief.json` (`competition_brief/v1`, proposed
here; contract `contracts/competition-brief.schema.json`), a note draft on
standard input (`contracts/experiment-note-draft.schema.json`), the notes file
and the submission file. Outputs: the hook's JSON answer; one JSON line per
note in `.baltor/state/competition-plugin/experiments.jsonl`
(`experiment_note/v1`); one JSON line per gate decision in
`gate-decisions.jsonl` (`submission_gate_decision/v1`) plus the printed
decision. Exit codes: 0 done or ready, 1 rule failed or hold, 2 refused input.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The hook only reads. The
note script and the gate append one line each to their files under
`.baltor/state/competition-plugin/`. The note command runs `git rev-parse
--short HEAD`. No network code anywhere; a test parses the gate and refuses
network or process imports. No model call, no secret read. Commands start
`python3 -I -B`; the host must bind a trusted interpreter, because an earlier
independent review showed that a `python3` first on `PATH` can be replaced.

## Closest existing items

`assignments.json` lists none. Nearest by search:
`freeze_the_success_metric_before_measuring` and
`read_the_train_validation_gap` (served text skills) give advice on metrics
and validation gaps with no records or scripts;
`audit_data_splits_for_errors_and_leakage` (served text skill) reviews
splits. Wave 5 boundaries: `competition_brief_packet` writes the brief,
this plugin only reads it; `rank_experiments_by_fold_scores` ranks runs and
`pick_next_experiment` chooses one, while the note command records one run;
`recompute_claimed_cv_score` recomputes a score from predictions, while the
note script only averages given fold scores; `validate_submission_file`
checks the file's rows and values, which this gate does not; and
`submission_assembly_packet` builds the file.

## Positive example

With `examples/competition/`, the Claude Code hook answers
`Competition store-demand-demo (regression). Metric: rmse, lower is better.
... Validation: group_kfold, 5 folds, groups by store_id. ...`. Sending
`examples/experiment-note-draft.json` with a submission file records
`cv_mean` 12.644 and its digest, and the gate then answers
`ready_for_host_upload` (`test_recorded_unchanged_file_is_ready_for_the_host`).

## Known-wrong example

The submission file is written again after its note, with another seed. Its
SHA-256 differs from the note, so the gate holds with `submission_unchanged`
failed (`test_file_written_again_after_its_note_is_held`). A draft that sends
its own `cv_mean` is refused with exit 2 (`test_a_claimed_mean_is_refused`).

## Harness placement and verification state

- Claude Code: plugin folder at `.baltor/plugins/competition-plugin/`
  (plugin_directory_binding), bound with
  `claude --plugin-dir .baltor/plugins/competition-plugin`. Plugin binding
  and a SessionStart hook were observed on Claude Code 2.1.280 for a
  different plugin; this plugin was not run.
- Gemini CLI: extension folder at the same path with `variants/gemini_cli/`,
  activated with `gemini extensions link .baltor/plugins/competition-plugin`.
  Listed in `unverified_targets`: activation, the SessionStart output and
  extension skills were not observed here.
- The skill and both note commands use workspace-relative script paths,
  which assume the shell starts in the workspace root. Hook registrations use
  `${CLAUDE_PLUGIN_ROOT}` and `${extensionPath}`, which the harnesses fill in
  for hook commands only.

## Customer requests

- "Every new session should know the competition metric, the folds and how
  many submissions I have left today."
- "Keep a log of my experiments with the fold scores, and do the math for me."
- "Check that the file I am about to submit is really the one from my best
  experiment, but never submit it for me."

## Limits

The brief, note and decision formats are proposals to align with the brief
and assembly packets. The daily limit counts ready decisions, which can be
more than real uploads, so it is conservative. The deadline uses the
machine clock unless `--now` is given. The gate does not validate the file's
rows or values. The standard deviation is the population form.

### Pre-check history

The first version (digest `98887b6b...`) passed every pre-check on September
23. The third run of this generator then found two consistency faults that
no pre-check covered: the Claude Code note command ran the script through
`${CLAUDE_PLUGIN_ROOT}`, a variable the harness fills in for hook commands,
while every other body uses the placed path; and the hook script accepted a
`fork` source that its registered matcher never sends. Both were repaired,
and the layout test now asserts both rules. With each fault put back in a
scratch copy, the layout test failed; with the repair all 31 tests pass.
Every report stays in `review/precheck-*.json`.
