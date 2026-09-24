# Review note: pick_next_experiment

Candidate only. Not approved, staged, served or published.

Producer: Claude Code wave 5 generator a06_step_ritual_commands (family anthropic), repaired by the a06 repairer
on 2026-09-24 after the second critic round. File class: command_file. Version 0.1.0. This note is never
delivered to a harness.

## Method

One named command chooses exactly one next experiment between runs, for example in a data science competition.
A tested helper reads the ledger `.baltor/experiments/ledger.jsonl` and prints a summary: the best finished run by
the header's metric and direction, the top three with the spread of their fold scores when the ledger has them,
the lead of the best run over the second and whether that lead is smaller than the best run's fold spread
(`lead_within_fold_spread`), open and failed runs, which config keys varied and which stayed constant,
`known_keys`, and minutes used. The model reads that summary and the notes, then writes one proposal: the full
config, the base run, a change that names every key it changes, the reason, the expected effect, the cost and an
ending rule that contains a number.

The helper refuses a proposal when:

- its configuration fingerprint equals any ledger entry, whatever its status; the fingerprint ignores key order
  and the header's `ignore_keys` and writes whole floats as integers, so `300.0` equals `300`;
- a config key is not a setting of the ledger: the header's `config_keys` when present, else the keys that earlier
  runs used. A key that no earlier run used, such as a dummy `attempt`, can no longer make a repeat look new; only
  a person adds a setting to the header;
- the change text does not name a key that differs from the base;
- the base, metric, cost, ending rule or a field name is wrong, or the minute budget would be exceeded.

A failed configuration may run again only as a retry: `retry_of` names the newest run with that configuration,
which must have failed, and `environment_change` says what was fixed outside the configuration, such as more
memory. A passing proposal is appended as `planned` with the next `E-` number. The command does not start the run.
The `record` subcommand appends update lines that move an experiment from planned to running, done (with a score,
optional fold scores and minutes) or failed (with notes); the ledger stays append-only and the summary folds the
updates in order, refusing an update for an unknown run or a move out of done or failed.

## Authoring basis and sources

Original text and code written for this wave. No outside text or code was copied. Sources at revision
`a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract.
- `docs/guides/configuration-grid-search-and-optimization.md`: keep exact configurations, failures and exclusions
  visible; the ledger keeps failed runs, and a failed run is retried only with a stated outside fix.
- `docs/guides/native-client-material-loading.md`: the OpenCode command folder.

The formats are published in `contracts/experiment-ledger-line.schema.json` (header, experiment and update lines)
and `contracts/experiment-proposal.schema.json`.

## Inputs and outputs

Inputs: the ledger, the optional notes file and `.baltor/experiments/proposal.json`. Outputs: one JSON object per
run (`experiment_ledger_summary/v1`, `experiment_proposal_result/v1`, `experiment_record_result/v1` or
`experiment_ledger_refused/v1`) and one appended ledger line per `propose` or `record`. Exit 0 success, 1 proposal
or move refused (ledger unchanged), 2 refused input (no ledger, no header, an unknown header key, a line that is not
strict JSON, a repeated id, an update that breaks the move rules, an unknown run for `record`).

## Effects

`reads_fs`; `writes_fs` (one appended line; the model writes the proposal file; tests write only in temporary
folders); `spawns_process` (the model starts the helper with `python3 -I -B`; tests start it with the current
interpreter and load it by path to compare its constants with the contracts). No network, no model call, no secret
read. The helper never runs an experiment.

## Closest existing items

- `choose_one_next_action` (starter, prose): choose one bounded action with finishing and abandoning rules. This
  package applies that idea to an experiment ledger and enforces what code can enforce.
- Wave 5: `rank_experiments_by_fold_scores` (a02) decides whether a lead between finished runs is real across
  folds; this package only reports the fold spread and flags a lead smaller than it. `recompute_claimed_cv_score`
  (a15) checks a claimed score. This command plans the next run and records results.

## Positive example

The example ledger has three finished runs (best E-003, rmse 0.405, fold spread 0.017, lead 0.007 over E-002, so
`lead_within_fold_spread` is true) and a run that an update line marks failed after it ran out of memory. The
example proposal halves the learning rate and doubles the trees from E-003, names both keys in its change,
expects rmse lower by about 0.003, costs 40 minutes and stops at 50 minutes or when fold 1 is above 0.415. It is
appended as E-005 with changed keys `learning_rate` and `n_estimators`.

## Known-wrong example

A proposal copies E-002's configuration with its keys in another order and `n_estimators` written as `300.0`; the
helper answers `repeat_of` E-002 and leaves the ledger bytes unchanged
(`test_known_wrong_repeat_with_reordered_keys_and_float_counts_is_refused`). The critic's case is a test: E-003's
configuration plus `"attempt": 2` is refused because `attempt` is not a setting of the ledger, while a declared
setting (`subsample`) is accepted and the same setting is refused once the header no longer declares it
(`test_known_wrong_a_dummy_key_does_not_make_a_new_experiment`).

## Harness placement and verification state

No harness binary was run. Claude Code `.claude/commands/pick-next-experiment.md` and Gemini CLI
`.gemini/commands/pick-next-experiment.toml`: documented in the spec table. OpenCode
`.opencode/commands/pick-next-experiment.md`: documented and observed in the repository guide (the spec table
names `.opencode/command/`). Copilot `.github/prompts/pick-next-experiment.prompt.md` (now with `agent: agent`
and `argument-hint`, following the VS Code prompt file documentation read on 2026-09-24) and Cursor
`.cursor/commands/pick-next-experiment.md` (the Cursor page read the same day described skills, not a command
folder): unverified. `$ARGUMENTS` and `{{args}}` are vendor documented, not recorded in a repository research
file; the sentence that holds them reads correctly when empty. The proposal example and the contracts go to
`.baltor/pick-next-experiment/`; the ledger and notes examples and the tests are not placed. The host must bind a
trusted `python3`.

## Customer requests

- "Look at what we already tried and tell me the one experiment to run next."
- "Stop my agent from rerunning the same settings it already tried last night, even with a renamed field."
- "The run ran out of memory; let it try again now that the machine is bigger, and log the result."

## Limits

Two configs that mean the same thing under different key names are not caught; list order inside a config counts.
The expected effect is the model's estimate. The fold spread is a range, not a statistical test. A person must add
a new setting to `config_keys` before a proposal can use it. The helper assumes one writer at a time.

## Repair history

Critic round 2 found: a dummy key that let a repeat through with no warning; no way to record results and no
ledger contract; no retry for a run that failed for an outside reason; `best` reported without fold spread;
examples with role `other` that the first native profile would refuse (`application/jsonl` and Markdown); and a
Copilot variant without `agent`. The repairer reproduced the dummy-key case at digest `577a9b45`
(`repairer-a06_step_ritual_commands/baseline/`) and made the changes above. The ledger example is now a
`skill_asset` and the notes a `skill_reference`; neither is placed.

Mutation checks: seven guards removed one at a time (unknown keys, naming changed keys, the retry environment
change, the repeat comparison, the budget, the score for a done run, update lines) were each killed by a named test
while the unchanged copy passed. Native loading of the command is unobserved. Every run is listed in
`PRECHECKS.txt`.
