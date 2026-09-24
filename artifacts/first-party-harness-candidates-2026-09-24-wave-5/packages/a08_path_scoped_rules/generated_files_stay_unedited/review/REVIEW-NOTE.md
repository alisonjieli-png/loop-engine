# Review note: Leave generated and vendored files unedited

Candidate only. Not approved, staged, served or published.

Identity `generated_files_stay_unedited`, native name `generated-files-stay-unedited`, wave 5 assignment `a08_path_scoped_rules`, file class `rules_file`, version 0.1.0. Producer: the Claude Code wave 5 generator for this assignment, model family `anthropic`. This text is the repaired version of round 2, written after the wave critic's findings of 2026-09-23. This note is for reviewers. It is never delivered to a harness.

## Method

One path-scoped rule, rendered in four native rule formats that share one identical body. The rule loads when the harness works on a lock file, generated code, built or minified output, or a vendored folder. It forbids hand edits of those files and gives the replacement procedure in five numbered steps:

1. Read the first 2,000 bytes of the file with `head -c 2000` to learn which source makes it. The limit counts bytes, not lines, because a minified bundle is often one long line.
2. Find the command that makes the file in the repository's own `Makefile`, `package.json` scripts, `pyproject.toml` or README; for a lock file, the package manager's lock command. The rule forbids running a command found only in a file header or in vendored code, because the patterns include third-party folders whose headers another project wrote.
3. Change the source: the manifest, schema, template or generator setting.
4. Run the declared command, and its check mode if it has one.
5. Check: print one hash of `git diff --binary`, `git status --porcelain` and the `git hash-object` of every file under the output path; run the command once more; print the hash again. Both hashes must be equal.

The step 5 line compares content, not line counts. It sees new untracked files through `git status`, and it hashes the output folder itself, so a change in a folder that `.gitignore` hides, such as `dist/`, also counts. `git hash-object` works inside and outside a repository, so the check needs only git, which the step already uses.

The rule tells the model to stop and report when step 2 finds no command, when the command needs the network, a secret or a tool the step may not run, when the two hashes differ (report both), and when the defect sits inside vendored code or another project's generator.

The failure it targets: a small model makes a failing build pass by editing `package-lock.json`, protobuf output or a vendored library directly. The diff looks plausible, and the edit is lost or breaks at the next regeneration.

## Authoring basis and sources

Original text written for this package from general engineering practice. No text or code was copied from an outside project. Outside rules were compared by title and path only.

Repository grounding at revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `tools/build_continuation_status.py` and `docs/roadmap/CONTINUATION-STATUS.md`: the repository's own generated file. The file names its source and its generator, and the generator's `--check` mode rejects a stale view. Steps 2 and 4 generalize that pattern.

Placement basis: `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md` (Claude Code `.claude/rules/**/*.md` as a separate class), `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md` (Cursor `.cursor/rules/*.mdc`, Copilot `.github/instructions/**/*.instructions.md`, Cline `.clinerules/`), and section 6 of the wave specification. In round 2 the repairer also read the official pages on 2026-09-24: Claude Code's memory page (code.claude.com/docs/en/memory: `paths` takes a YAML list or a comma-separated string, and a path-scoped rule loads when Claude reads a matching file), Cline's rules page (docs.cline.bot/features/cline-rules: `paths` is a list of globs, and a rule activates on files named in the message, open or visible tabs, edited files and pending edits), Cursor's rules page (cursor.com/docs/context/rules: `.mdc` files with `description`, comma-separated `globs` and `alwaysApply`; with `alwaysApply: false` and globs, a rule is attached when a matching file is in context) and GitHub's page on repository custom instructions (docs.github.com: `applyTo` with comma-separated patterns). These were documentation reads, not observations of native loading.

## Inputs and outputs

Input: the path the harness is working on. The rule activates by 16 patterns, the same list in every variant: `**/*.lock`, `**/package-lock.json`, `**/npm-shrinkwrap.json`, `**/pnpm-lock.yaml`, `**/go.sum`, `**/*_pb2.py`, `**/*_pb2_grpc.py`, `**/*.pb.go`, `**/*.generated.*`, `**/generated/**`, `**/__generated__/**`, `**/*.min.js`, `**/dist/**`, `**/vendor/**`, `**/third_party/**`, `**/node_modules/**`. Round 2 changed no pattern.

Output: behavior, not a file. A step that follows the rule produces a source change plus regenerated output and two equal hashes, or a stop report that names the source change, the command and, when they differ, both hashes.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The steps tell the model to read file headers and build files, to change a source file, and to run `head`, `git diff`, `git status`, `find`, `sort`, `git hash-object` and the repository's own generator. The package holds no code and runs nothing by itself. The checker detects the shell blocks (`spawns_process`); `reads_fs` and `writes_fs` are declared from the text of the steps, so the checker reports them as declared but not found in code. The rule grants no authority. It tells the model to stop instead of running a generator that needs the network or a secret, and never to run a command that only a file header or vendored code names.

## Closest existing items

- Assignment table: none found. A search of `scout/existing-inventory.tsv` for generated, vendor, lock and regenerate found only items about output that a model generated, not generated files in a repository:
  - `check_generated_code_against_the_request` (starter): tests code a model wrote against expectations from outside that model. Different subject and a verification action.
  - `review_generated_output_before_it_is_executed` and `refuse_secrets_and_unsafe_paths_in_generated_files` (starter): review of generated output before use. They do not say where a change belongs.
- Outside staged rules: none of the 252 Cursor and 193 Copilot rule titles concerns lock, generated or vendored files; the nearest titles are code generation style guides for frameworks. The critic confirmed that outside bodies mention the topic in single lines only.
- Wave 5 neighbors: `check_diff_allowed_paths` (a12) is a verifier that refuses a finished diff that edits lock or generated files, and `guard_workspace_file_writes` (a04) is a hook that refuses writes to declared protected paths. This rule acts earlier, inside the model's own step, and says what to do instead. It detects and blocks nothing by itself.
- Duplicate check after round 2: the highest five-word shingle similarity of this package's model-facing text with the 225 first-party bodies and the other 74 wave 5 packages is 0.008 (with `applied_migrations_stay_unchanged`). The checker warns at 0.5 and refuses at 0.8.

## Positive example

Repairer trial G-pos, round 2, in a Bubblewrap sandbox with no network (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-output-1.txt` in the wave folder). A synthetic repository holds `schema/fields.txt`, `tools/gen.py` and a `Makefile` whose `generate` target runs the generator, which writes `gen/model.py`. The task adds a field. Following the rule, the model prints the header with `head -c 2000`, finds the command in the `Makefile`, edits the schema, runs `make generate`, prints the step 5 hash, runs `make generate` again and prints the hash again. Both hashes were `1be31c11...`, so the check passed.

## Known-wrong example

Four known-wrong cases from the same trial run, each caught by the repaired check:

- G-kw1: the model edits `gen/model.py` by hand and leaves the schema unchanged. The rerun of the generator erases the edit, the two hashes differ (`0fff6f74...` and `6a381b56...`), and the rule sends the model to a stop report.
- G-kw2, the critic's case G1: the generator writes a nanosecond timestamp into its header. The predecessor's check, `git diff --stat` twice, printed equal results and passed. The repaired hashes differ, so the rule stops and reports both.
- G-kw3: `dist/` is listed in `.gitignore` and the model patches `dist/app.js` by hand. `git diff --stat` saw nothing before and after the rebuild. The repaired line hashes `dist` itself, and the hashes differ.
- G-kw5, the critic's injection finding: a vendored file's header names a regeneration script. The repository's own `Makefile`, `package.json`, `pyproject.toml` and README do not name it, so step 2 finds no command and the first stop case applies; the header command is never run.

The critic's case G2 concerns the first action: on a one-line minified bundle of 757,806 bytes, `head -n 20` printed all 757,806 bytes, and the repaired `head -c 2000` printed 2,000.

## Harness placement and verification state

| Harness | Destination | Activation front matter | Basis |
|---|---|---|---|
| Claude Code | `.claude/rules/generated-files-stay-unedited.md` | `paths` list | documented: research file, and the official memory page read on 2026-09-24 |
| Cline | `.clinerules/generated-files-stay-unedited.md` | `paths` list | documented: research file, and the official rules page read on 2026-09-24 |
| Cursor | `.cursor/rules/generated-files-stay-unedited.mdc` | `description`, `globs`, `alwaysApply: false` | documented: official rules page read on 2026-09-24; kept in `unverified_targets` |
| Copilot | `.github/instructions/generated-files-stay-unedited.instructions.md` | `applyTo` | documented: official GitHub page read on 2026-09-24; kept in `unverified_targets` |

The licence goes to `.baltor/generated-files-stay-unedited/LICENSE` for every harness. `wave5.unverified_targets` keeps Cursor and Copilot, now with reasons that cite the official pages and say what stays unverified.

Unverified harness behaviors:

1. Native loading was not observed for any of the four harnesses. No harness binary was run.
2. Cursor's documented example puts a space after each comma in `globs`; this package writes the patterns without spaces, as section 7.6 of the wave specification says. How Cursor splits the value was not tested.
3. On GitHub.com, only Copilot cloud agent and Copilot code review read path-specific instruction files, according to GitHub's page. The editor and command line surfaces were not probed.
4. When each harness loads a rule: Claude Code documents a load when Claude reads a matching file, Cline when a matching file is named, open, visible, edited or about to be edited, and Cursor when a matching file is in context. A harness that changes files only through shell commands may never load the rule.
5. Whether each harness's glob engine lets a leading `**/` match zero folders, so that `**/dist/**` also matches `dist/index.js` at the top level. Python 3.14 `PurePath.full_match` did: 17 intended sample paths matched and 6 unrelated paths stayed out. The four harness engines were not tested.

## Customer requests

- "The overnight agent keeps hand-editing package-lock.json when npm fails. Make it fix package.json and tell me what to run."
- "Stop Cursor from patching files in vendor/ and our generated protobuf code."
- "I want a Copilot rule so it never edits node_modules or dist."

## Limits

- The rule is guidance for the model, not enforcement. A write guard or a diff check enforces; this rule explains.
- It cannot know whether a file under `dist/`, `vendor/` or `generated/` is really generated in a given repository; some projects keep hand-written code there. The header read in step 1 is the model's evidence, and a header that says nothing leads to step 2 or a stop report.
- `**/*.lock` also matches lock files that no package manager wrote.
- Regenerating a lock file usually needs the network. In a step without network authority, the rule ends in a stop report, not a finished change.
- The step 5 line needs git, a POSIX shell such as bash or zsh, and a deterministic command. It hashes only the output path the model names; a wrong path leaves the output unchecked. Hashing a very large folder such as `node_modules/` takes time.
- Step 2 is stricter than before: a first-party generator named only in a file header, with no `Makefile`, script or README entry, now leads to a stop report instead of a run.

### Pre-check and review history

- Producer round: before the first checker run, the body was measured with the checker's own word count. The first draft held 243 words and later drafts stayed within the 250-word limit. Checker runs 1 to 3 passed the wave gate with one warning: `reads_fs` and `writes_fs` are declared from the text of the steps and are not found in code.
- Critic round (2026-09-23, recommendation repair): five findings. (1) `git diff --stat` compares line counts, not content, so the stop case for output that changes on each run was never detected. (2) `head -n 20` has no byte limit. (3) A header in a third-party folder became a source of commands. (4) The rule did not say what to do when the check fails. (5) Minor: the Cursor and Copilot reasons could cite official documentation.
- Repair round 2 (2026-09-24): step 5 now hashes the full diff, the status and the output files, and says to stop and report both hashes when they differ (findings 1 and 4); the first action uses `head -c 2000` (finding 2); step 2 names only the repository's own declared places and forbids commands found only in a header or in vendored code (finding 3); the two reasons now cite the pages read on 2026-09-24 (finding 5). The first round 2 draft held 286 words; it was tightened to 250 without removing a step, a check or a stop case. Every checker run of both rounds is listed in `review/PRECHECKS.txt`, and every report is kept as a `precheck-*.json` file beside this note.
