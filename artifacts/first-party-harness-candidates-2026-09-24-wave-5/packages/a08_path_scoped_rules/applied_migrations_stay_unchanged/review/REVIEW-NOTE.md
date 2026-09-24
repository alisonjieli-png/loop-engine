# Review note: Keep applied migrations unchanged

Candidate only. Not approved, staged, served or published.

Identity `applied_migrations_stay_unchanged`, native name `applied-migrations-stay-unchanged`, wave 5 assignment `a08_path_scoped_rules`, file class `rules_file`, version 0.1.0. Producer: the Claude Code wave 5 generator for this assignment, model family `anthropic`. This text is the repaired version of round 2, written after the wave critic's findings of 2026-09-23. This note is for reviewers. It is never delivered to a harness.

## Method

One path-scoped rule, rendered in four native rule formats that share one identical body. The rule loads when the harness works in a database migration folder. It forbids editing, renaming, reordering or deleting any migration that may already have run, and puts every schema or data change in a new migration made with the project's own migration tool. It gives a small model a test it can apply without database access: every migration in the start commit counts as applied, and only a migration the current step created may still change. The four steps:

1. Record the start commit: the base commit the task names, else the output of `git rev-parse HEAD` at the start of the step. The hash goes into the report. Shell variables do not survive between tool calls in most harnesses, so the model keeps the printed hash and writes it into the check.
2. Create a new migration with the project's own command so it gets the next number and parent.
3. Put the change there, with a reverse step when the tool supports one.
4. Check: `git diff --name-only --diff-filter=MDR START` over seven glob pathspecs, one per pattern of the rule, with the start commit in place of `START`. It must print nothing except an index file the tool updates itself, and the body names the allowed ones: an Entity Framework `*ModelSnapshot.cs`, a Drizzle `meta/_journal.json`, or a Liquibase master changelog that only gains `include` lines.

Diffing against the start commit, not `HEAD`, keeps the check able to fail after the step commits its work, as the a14 fragment `unattended_git_rules` tells each ticket to do. The glob pathspecs cover every migration folder of a project, such as the app folders of a Django project.

The rule tells the model to stop and report when the tool reports two heads, a conflict or a numbering gap, when making or checking the migration needs a live database, a secret or the network, when the task asks to edit, squash or delete an existing migration, and when it cannot tell whether a migration has run.

## Authoring basis and sources

Original text written for this package from general database practice. No text or code was copied from an outside project.

Repository grounding at revision `a1fc74321912cb9e7d0af7dc5d0ecee24c7081f4`:

- `src/loop_engine/core/service_runtime/catalogue_packages.py`: the package file contract this package follows.
- `AGENTS.md` and `docs/architecture/ADR-PRELAUNCH-VERSIONED-CONTRACTS.md`: the repository's rule that a record an older release must not honor needs a new record version, and that a changed contract gets a new version. The same principle applies to a released migration: never change what already shipped; add a new one.
- `examples/29_intelligence_service/starter-catalogue/bodies/write_a_migration_that_is_safe_to_run_twice.md` and `plan_a_schema_change_in_compatible_steps.md`: the two closest starter items (see below).

Placement basis: `docs/research/HARNESS-FILE-STANDARDS-FLEXIBILITY-2026-09-23.md`, `/home/username/.le-codex-build/integration/docs/research/HARNESS-PACKAGES-CLAUDE-AND-EDITORS-2026-09-23.md`, section 6 of the wave specification, and the official pages the repairer read on 2026-09-24: Claude Code's memory page (code.claude.com/docs/en/memory), Cline's rules page (docs.cline.bot/features/cline-rules), Cursor's rules page (cursor.com/docs/context/rules) and GitHub's page on repository custom instructions (docs.github.com). These were documentation reads, not observations of native loading.

## Inputs and outputs

Input: the path the harness is working on. Seven patterns, the same in every variant: `**/migrations/**`, `**/Migrations/**`, `**/db/migrate/**`, `**/db/migration/**`, `**/db/changelog/**`, `**/alembic/versions/**`, `**/drizzle/*.sql`. The capitalized folder covers frameworks that name it `Migrations`, because glob matching is usually case sensitive. Round 2 changed no pattern, and the check's seven pathspecs repeat them with git's `:(glob)` prefix.

Output: behavior. A step that follows the rule produces new migration files and leaves every migration of the start commit byte-identical, or a stop report.

## Effects

Declared: `reads_fs`, `writes_fs`, `spawns_process`. The steps tell the model to run `git rev-parse` and `git diff`, to run the project's migration tool to create a file, and to write the new migration. The rule forbids running a migration against a live database without authority. The package holds no code. The checker detects the shell blocks; the file read and write effects are declared from the text of the steps.

## Closest existing items

- `write_a_migration_that_is_safe_to_run_twice` (starter, named in the assignment): makes each migration idempotent with conditional statements, a completion table and a double run. It says nothing about editing existing migration files.
- `plan_a_schema_change_in_compatible_steps` (starter, named in the assignment): spreads a change over add, dual write, backfill, switch and remove releases. It plans releases; it does not guard the migration folder.
- `rehearse_a_migration_on_a_copy_of_real_data` (starter): measures a migration on a copy of production. Also a method, not a folder guard.
- Difference for all three: this package is a short path-scoped rule with a git-based applied test and a folder check. The three methods are complementary: the new migration this rule asks for should still be safe to run twice and compatible across releases.
- Outside material: the critic compared the bodies and found that the only overlap is one principle line in the staged skill `Database Migration Patterns` (1,587 words). The staged Cursor rule `Database Best Practices` was compared by title only.
- Duplicate check after round 2: the highest five-word shingle similarity of this package's model-facing text with the 225 first-party bodies and the other 74 wave 5 packages is 0.008 (with `generated_files_stay_unedited`). The checker warns at 0.5 and refuses at 0.8.

## Positive example

Repairer trial M-pos, round 2, in a Bubblewrap sandbox with no network (`repair-a08_path_scoped_rules/round-2/trials/repair-trials-output-1.txt` in the wave folder). Two migrations and a Drizzle-style journal `migrations/meta/_journal.json` are committed. The first action printed the start commit. The model adds `0003_add_phone.sql` and the tool's journal entry. The check printed only `migrations/meta/_journal.json`, which step 4 allows. After the step's single commit, the check against the start commit printed the same single line. In a second repository, an Entity Framework snapshot and a Liquibase master changelog that gained one `include` entry (0 removed lines) were the only files listed, and both are allowed.

## Known-wrong example

- M-kw1, the critic's case M1: the model adds `NOT NULL` to the applied `0002_add_email.sql` and commits. The predecessor's check against `HEAD` printed nothing. The repaired check against the start commit printed `migrations/0002_add_email.sql`.
- M-kw2, the critic's case M2: a Django project with `shop/migrations/` and `users/migrations/`; the model edits `users/migrations/0001_initial.py`. The literal pathspec `migrations/` printed nothing; the repaired glob pathspecs printed the file.
- M-kw3: a rename with `git mv` printed the new path, and a deletion printed the deleted path.
- M-idx known-wrong: an inline changeset inside a Liquibase master changelog was edited. The file was listed, and its diff removed a line, so it did not only gain `include` lines and step 4 does not allow it.
- Pathspec table: across 15 committed sample paths that were all changed, the check listed exactly the 10 migration paths (root and nested `migrations/`, `db/migrate/`, `db/migration/`, `db/changelog/`, `alembic/versions/`, `Data/Migrations/`, `prisma/migrations/`, `supabase/migrations/`, `drizzle/*.sql`) and left out `src/models.py`, `docs/migration-guide.md`, `scripts/migrate_users.py`, `drizzle.config.ts` and `drizzle/meta/_journal.json`.

## Harness placement and verification state

| Harness | Destination | Activation front matter | Basis |
|---|---|---|---|
| Claude Code | `.claude/rules/applied-migrations-stay-unchanged.md` | `paths` list | documented: research file, and the official memory page read on 2026-09-24 |
| Cline | `.clinerules/applied-migrations-stay-unchanged.md` | `paths` list | documented: research file, and the official rules page read on 2026-09-24 |
| Cursor | `.cursor/rules/applied-migrations-stay-unchanged.mdc` | `description`, `globs`, `alwaysApply: false` | documented: official rules page read on 2026-09-24; kept in `unverified_targets` |
| Copilot | `.github/instructions/applied-migrations-stay-unchanged.instructions.md` | `applyTo` | documented: official GitHub page read on 2026-09-24; kept in `unverified_targets` |

The licence goes to `.baltor/applied-migrations-stay-unchanged/LICENSE` for every harness. `wave5.unverified_targets` keeps Cursor and Copilot, now with reasons that cite the official pages and say what stays unverified.

Unverified harness behaviors:

1. Native loading was not observed for any of the four harnesses. No harness binary was run.
2. Cursor's documented example puts a space after each comma in `globs`; this package writes none. How Cursor splits the value was not tested.
3. On GitHub.com, only Copilot cloud agent and Copilot code review read path-specific instruction files, according to GitHub's page.
4. When each harness loads a rule. A migration created only through a shell command may not load the rule until the model reads a migration file.
5. Whether a leading `**/` matches zero folders in each harness's glob engine. Python 3.14 `PurePath.full_match` matched all 10 intended sample paths and kept all 4 unrelated paths out (for example `scripts/migrate_users.py` and `drizzle.config.ts`). Git's own `:(glob)` pathspecs in the check did the same in the pathspec table above.

## Customer requests

- "Claude edited an old Alembic migration instead of adding a new one, and production broke. Add a rule."
- "Rule for our Django project: never touch migrations that are already committed."
- "Make the agent create a new Rails migration for every schema change and leave db/migrate history alone."

## Limits

- The rule is guidance, not enforcement. A diff check on migration folders enforces.
- "In the start commit means applied" is deliberately conservative. A migration committed only on a local branch has not run anywhere, but the rule still asks for a new migration; a corrective migration is always safe, while an edit can be wrong.
- A later step, such as a separate verification step in a fresh harness, sees an earlier step's edit only when the task names the base commit of the whole ticket; with the current commit as its start, that step cannot see what earlier steps committed.
- A migration that an earlier step left uncommitted is not in the start commit, so the check does not list an edit of it, although the rule text forbids that edit.
- Squashing migrations is left to people; the rule sends it to a stop report.
- `**/migrations/**` also matches folders of non-database migration scripts; there the rule is harmless but may be unnecessary. A migration folder outside the seven patterns, such as a singular `src/migration/`, is not covered by the rule or its check.
- The check needs git and a repository with at least one commit. The model must copy the start hash into the check by hand.

### Pre-check and review history

- Producer round: the first draft held 239 words. A later review found that the first check would report the index file that some tools update for every new migration as a forbidden change; the wording was corrected. Checker runs 1 to 3 passed the wave gate with one warning: `reads_fs` and `writes_fs` are declared from the text of the steps and are not found in code.
- Critic round (2026-09-23, recommendation repair): (1) the check diffed against `HEAD`, so it passed without checking anything once the edit was committed; (2) the literal `migrations/` pathspec missed other app folders; (3) the allowance for index files was open-ended and could excuse an edited Liquibase master changelog.
- Repair round 2 (2026-09-24): the first action records the start commit and the check diffs against it (finding 1); the check uses seven glob pathspecs, one per pattern (finding 2); step 4 names the allowed index files and requires a Liquibase master changelog to only gain `include` lines (finding 3). The first round 2 draft held 268 words; it was tightened to 249 without removing a step, a check or a stop case. Every checker run of both rounds is listed in `review/PRECHECKS.txt`, and every report is kept as a `precheck-*.json` file beside this note.
