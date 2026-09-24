# Review note: Small working context rules

Candidate only. Not approved, staged, served or published.

This note is for the independent review panel. It is never delivered to a harness.

## Method

A composable instruction section for the model that does the work inside one step. It tells a small or low-cost model how to read so that its context stays small: start from the paths the assignment names, search before reading, check a file's size before opening it, read large files in slices of at most 120 lines, never print whole trees, lock files, generated or data files or logs, send long command output to a file and read only its end and its error lines, keep a notes file instead of rereading, and write long results to files. When the step needs more than 10 files or 2,000 lines to understand, the model stops and reports that the step is too large.

The thresholds (300 lines or 20,000 bytes, 120-line slices, 40 lines of output, 10 files, 2,000 lines) are design choices for small models, stated as fixed numbers so that a small model does not have to judge them. They are not measured optima.

The package has no script. Every rule uses tools that each target already has: the harness's own read and search tools, or `grep`, `sed`, `head`, `tail`, `wc` and `mkdir` in a shell. A script would duplicate the harness read tools. Each command in the section was run once on this machine against a synthetic file to confirm its syntax.

## Authoring basis and sources

Original text, MIT. Repository files at `a1fc7432`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package format.
- `src/loop_engine/core/context_budget.py`: command output, fetched pages and generated files must not grow a prompt without bound; head and tail trimming.
- `src/loop_engine/core/llm_work_packet.py`: one model step gets labelled parts, not everything.
- `case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md`: added material cost 45 to 446 percent more prompt tokens per step and helped nothing on that population; the section is therefore 320 words and holds no background.
- `examples/29_intelligence_service/starter-catalogue/bodies/assemble_the_context_for_one_step.md` and `.../decide_what_to_leave_out_of_a_prompt.md`: the closest items.

No outside text or code was copied or paraphrased.

## Inputs and outputs

Input: the step's own assignment and the workspace. Output: the model's normal work, plus `.baltor/state/small-working-context-rules/out.txt` for long command output, an optional `notes.md` there, and files for results longer than 40 lines.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The section tells the model to read and search files, run shell commands (it holds one shell block) and write output, notes and long results to files. No network, no model call, no secret.

## Closest existing items

- Starter `assemble_the_context_for_one_step`: written for whoever builds the prompt for a step. This section speaks to the working model after the step has started.
- Starter `decide_what_to_leave_out_of_a_prompt`: prose for the prompt assembler on ranking and removing parts. This section gives the working model reading rules with fixed limits and exact commands.
- Wave 5 a05 `repository_scout` answers one where-question in a helper, and a03 `map_repository_layout` prints a map. Neither sets reading rules for the main step.

## Positive example

A step must fix a failing test in a 4,000-line module. The model runs `grep -rn -m 20 "def parse_date" src | head -n 40`, finds line 2,310, checks `wc -l -c src/dates.py`, reads `sed -n '2280,2360p' src/dates.py`, sends the test output to `out.txt`, and reads `tail -n 40` and the matching error lines. About 120 lines enter its context instead of several thousand.

## Known-wrong example

The model prints the whole 4,000-line module and a 3,000-line test log. The ticket's instruction scrolls far back in its context, the small model loses track of it, and the step ends without the fix. The section forbids both reads and gives the exact slice and tail commands instead.

## Harness placement and verification state

- `AGENTS.md` is composed into the step's root `AGENTS.md` for codex, opencode and pi (observed), goose (documented in `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` of the shared checkout) and kimi_cli (unverified).
- Claude Code gets `CLAUDE.md` holding `@AGENTS.md` (file observed, import documented). Gemini CLI gets `GEMINI.md`, a byte copy (documented). `LICENSE` goes to `.baltor/small-working-context-rules/LICENSE`.
- Not observed: a harness or model following these rules, the size of any context saving, a Kimi CLI project `AGENTS.md`, and how each harness's read tool counts offsets. The phrase "your read tool with an offset and a limit" assumes such parameters exist; where they do not, the shell commands apply.

## Customer requests

- "My local model reads whole files and runs out of context. What rules should it follow?"
- "How do I stop the agent from dumping a full test log into the conversation?"
- "Keep token use down for a small model without losing the task."

## Limits

- The shell commands assume a POSIX shell; Windows shells without these tools are not covered.
- Text does not enforce anything. A harness may still return a whole file when the model asks for one.
- The numeric limits are unmeasured choices. A later paired run could tune them.
- No measurement shows that the section improves outcomes or saves tokens.

## Pre-check history

Every command output is kept in `review/PRECHECKS.txt`, and every checker report in `review/precheck-*.json`; the newest report is the gate record.

- Round 1: fill and check passed (package digest `d9b86a07`) with one warning: `reads_fs` and `writes_fs` are declared but not detected. The section tells the model to read files and to write output, notes and long results to files, which the static scan does not see in prose; the declaration stays.
- Edit after round 1: the grep example gained `| head -n 40`, because `-m 20` limits matches per file, not in total.
- Round 2: fill and check passed with the same warning (package digest `0db2b122`). The package has no Python code, so no test runs.
- Final round: fill and check passed with the same warning (package digest `0db2b122`, unchanged since round 2). The check was run once more after this history was written.
