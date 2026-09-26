# Session handoff, September 26, 2026

Kind: dated handoff. It records what went live during the day, the owner's
directions of the day and the decisions made under them, what runs unattended,
the state of the owner's attached drive as seed material, and the order of the
next steps. The [September 25 night handoff](SESSION-HANDOFF-2026-09-25-NIGHT.md)
is the snapshot before it. The roadmap remains the task authority.

## What is live

| Fact | State at the time of writing |
|---|---|
| Fly release | 36 (`cd079477`), unchanged since 23:23 UTC on September 25. The page and table work of this day (S-6.208) is on `main` and waits for release 37. |
| Catalogue | release `856bff51…` since 11:55 UTC: 6,398 packages (42 Verified, 6,356 Community), published by the daily job's 10:17 UTC slot, the first slot that cron started and ran through every stage itself ([record](../../artifacts/community-release-6-2026-09-26/README.md)). Before it `a7451e06…` (4,812) from 06:19 UTC. Every release passed the customer retrieval check 6 of 6. |
| Daily job | every six hours from cron (04:17, 10:17, 16:17, 22:17 UTC), 2,000 packages a slot. The 16:17 UTC slot is the first with the balanced kind mix and the tags. Its counts record is version 2 (`daily_library_release_counts/v2`) with the mix kept, the exported kinds, the approved harness kinds and the step functions. |
| Overnight batch | the 10,000-idea batch of September 24 finished on this day: 8,904 candidates written, 1,096 failed, 11,417 calls (`/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch/status.json`). The candidates wait for the native review path; none is served. |
| The owner's drive | `/run/media/username/Expansion` (7.3 TB, exFAT, 3.1 TB used) is being inventoried read-only into `~/baltor-library/volumes/expansion/inventory-1` (`progress.json` shows the walk). A dry seed run over the first 407 projects kept 169 as seed ideas (`~/.le-ci-tmp/expansion/seeds-dry-2`). |

## The owner's directions of the day, and the decisions

1. "Make sure that our library isn't just skills, it should be skills,
   plugins, python scripts, literally a large mix of everything that can be
   placed into a harness working directory": the export now draws every kind
   in a declared share (the "Library composition" row of the decision table,
   roadmap S-6.205), and a package with code reaches Community when the
   reviewer read every executable line under the new executable-code
   criterion; the sandbox-tests route stays the Verified route for code. The
   4,812 packages served that morning held no script, because the export
   ranked instruction-only packages first and the format rule held every
   package with code for sandbox tests that no imported skill ships.
2. "Tag some of these skills by whether they support acting, reasoning,
   building, analysis, verification, etc": the `library_step_function_tagging`
   engine slot with a rules engine, the `step_functions` served attribute,
   the writer, the snapshot, the bundle, the search result, the list rows and
   the pages (S-6.206). A tag names its engine; an item whose words name no
   function has no tag.
3. The Expansion drive as seed material "without license concerns, because
   everything on the drive was created and written by me as the original
   author": `tools/scan_local_volume.py` inventories a volume read-only and
   classes each project by typed provenance signals; the owner's declaration
   is the recorded basis, and a git remote under another account, a licence
   naming another holder or a copyright line naming someone else makes a
   project third-party material, which stays inspiration only. The drive's
   own index also marks imported workspaces (stable-diffusion-webui, AnyV2V),
   and the seed builder honours it. `tools/build_volume_seed_ideas.py` turns
   the owner-authored projects into `harness_idea_batch/v1` ideas with a
   bounded excerpt the generation lanes may copy (S-6.207; the "Seed material
   from the owner's own volumes" row of the decision table).
4. The library page: "make people sign up before showing them", "a searchable
   table format", "size, and digest are useless", "ALL types of harness working
   directory component files not just SKILLS": the public page counts by
   harness kind and label and lists no item; the signed-in library is one
   searchable, sortable table with the purpose, the kind of file, the label,
   the step functions, the licence, the effects and the tools, and no size or
   digest column (S-6.208, waits for release 37).
5. "Tag/label our harness component files by job title, industry, level,
   language, geography, etc, and allow people to search in the dashboard":
   recorded as S-6.209, behind the same tagging edge, for the signed-in
   dashboard only.

## What runs unattended, and the traps of the day

- The cron entry names `REPOSITORY=/home/username/.le-library-job`, a
  detached worktree at the day's commit `edcc77a3`, since 12:15 UTC; the
  earlier entry named the session's own worktree. Move the job checkout to a
  newer revision only between slots (`git -C ~/.le-library-job checkout
  <revision>` after a slot's `counts` stage and before the next `17` past
  the hour), and never while a slot runs.
- A new folder under `docs/` needs a charter `README.md`: the self-test's
  zero-tolerance gate counts every docs folder without one, and continuous
  integration refused `edcc77a3` for the new `docs/design` folder until the
  README followed.
- The website redesign brief for Claude Code Design is
  [docs/design/WEBSITE-REDESIGN-BRIEF-2026-09-26.md](../design/WEBSITE-REDESIGN-BRIEF-2026-09-26.md);
  the owner pastes it into the design tool, and the pages it describes are
  the ones this handoff records as live or waiting for release 37.
- Never edit a prompt-affecting file (the criteria, the reviewer instructions,
  `prompt.py`), the writer, the combine tool or the bundle builder while a
  slot is between its review and bundle stages: the writer keys each verdict
  by the exact prompt, so a changed criterion between review and write leaves
  every item without a verdict. Never edit the bash job while it runs.
- The drive inventory walks about 300 files a second on exFAT; the Windows
  backup tree holds most of the files and few projects.
- A folder that is only a README about other folders seeds nothing: the seed
  builder requires a module outline or five code files.

## Parallel work in flight (from 12:40 UTC)

The owner asked at 12:30 UTC for sub-agents to "track, review, resolve, and
iteratively improve all aspects of this, start to finish, including
user-level feedback, but also oracles that can run server side to review our
files and double check them and generate variations of them automatically".
Two workflows of the session's harness run thirteen builders, each in its
own detached worktree of `origin/main` named `/home/username/.le-agent-<package>`,
each followed by a skeptic verifier. A builder commits in its worktree and
never pushes; the integrating session cherry-picks the verified commits onto
`main`, resolves the conflicts (expected in `catalogue-browser.js`,
`service.js`, `index.html`, `web_site_map.json`, the documentation index,
`catalogue_attributes.py`, `engine_slots.yaml`, `architecture_map.py` and
`_self_test.py`), runs the preflight and pushes one release train.

| Package | Roadmap | What it builds |
|---|---|---|
| feedback-withdrawal | S-6.199 | the report and flag operations, the withdrawal rule, the report button, the nightly rescan, the weekly upstream check |
| serving-measurement | S-6.203 | the measurement at 6,398, about 12,800 and about 25,000 with the real bundle and a labelled doubling |
| quickstarts | S-6.202 | one quickstart per harness, the nightly checker, its cron entry |
| red-team-page | S-6.201, S-6.198 | the showcase page generator, the served case study, the hostname row |
| weekly-number | S-6.204 | the weekly number command, its record, its Monday cron entry |
| ci-speed | S-6.200 | sharded continuous integration, the pre-push check, the timing record |
| tag-precision | S-6.206 | the 100-item precision sample of the step function rules and the rule fixes |
| facet-tags | S-6.209 | job title, industry, level, language and geography rules behind the tagging edge, the table filters |
| seed-wave | S-6.207 | media in the seed excerpts, the full seed batch, the wave script; its generation stage started on Tactical |
| request-tracker | (all) | the owner requests ledger and its checking tool |
| user-feedback | S-6.199 | rate a download, request material, search gaps as metadata, the staff view |
| oracle-review | S-6.199, S-6.178 | the hourly second-look review of served items by an eligible family, withdrawal and upgrade candidates |
| oracle-variations | S-6.40 | variations of served items generated on Tactical, reviewed by another family, published by the daily job |
| source-volume | S-6.40 | the true stock by kind and licence, the days of stock, eight ways to reach 100,000 sources, one new discovery source and a bounded real round into the import store |
| code-extraction | S-6.62, S-6.44 | code_module packages extracted from the owner's projects with their import closure, a wrapper and a sandboxed smoke test, run on ten projects |
| production-resources | S-6.40 | templates, SQL transformations, media command files and lookup tables from the owner's projects as packages with validators |
| retrieval-and-recipes | S-6.63 | a 40-query evaluation set against the real bundle, curated recipes with conflict rules, and the abstention floor in search |
| failure-laboratory | S-6.62 | the failure fixtures as reusable components and the activation checker run over the active release bundle |
| factory-economics | S-6.197 | cost and time per admitted package by stage, the projection to each mark, and the smallest scheduling change the journals justify |

The third workflow (six researcher-builders, from 12:55 UTC) follows the
owner's exploration protocol of the same hour: current reality, five to ten
alternatives, external research with dates, analogies, comparable products,
synthesis, then a tested increment and a decision record under
`docs/research/`, with the untouched ideas kept as a queue.

Model use by the oracles and the seed wave stays inside the recorded
authority: Tactical for generation and for imported-package reviews,
`claude_code.subscription` for the small reviews of Tactical-produced work,
Codex from September 29, Ollama Cloud when its allowance returns on October 1.
The Fly Machine holds no model key and makes no model call; every oracle runs
on this machine from cron, outside the daily slots' two-hour windows, with a
cap per run, and publishes only through the daily job's review and publish
path.

## Next steps, in order

1. Release 37 from a green `main` with the library page, the table, the
   search-result tags and the list-row attributes; screenshot `/library`
   signed out and the table signed in; live checks on every hostname.
2. Read the 16:17 UTC slot's `counts.json` (`~/baltor-library/daily/2026-09-26-16/`):
   the mix kept, the harness kinds approved and the tags; sample ten approved
   packages with scripts and check each reviewer answer against the code.
3. When the drive inventory finishes, build the seed ideas from the full
   inventory and run the first generation wave (fifty seeds) on the Tactical
   lane, then the native review and the daily publish.
4. Feed the overnight batch's 8,904 native candidates to the native review
   path as a second input of the daily job.
5. S-6.209 (occupation, industry, level, language and geography tags), then
   S-6.203 (serving measurement at 10,000, which the count will pass within a
   day).
