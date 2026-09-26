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

## Evening update, 21:00 to 22:00 UTC

| Fact | State at 22:00 UTC |
|---|---|
| Fly release | 37 (`43b421f8`), live since 13:25 UTC. The Machine restarted once more at 16:59 UTC for a host setting (below). |
| Catalogue | release `add925433546` since 21:38 UTC: 7,806 packages, the first release in the balanced mix and with the tags ([record](../../artifacts/community-release-7-2026-09-26/README.md)); its publish needed two retries and a repair of the private publish script. |
| Live fixes | The signed-in library table's list answer was refused (413) because the whole list exceeded the 256 KB answer cap; `http.maximum_response_bytes` is now 16 MiB. With the list answered, a signed-in account saw 534 of 6,398 packages: 1,988 that declare only `pure` were withheld from every step (fixed on the integration tree at the served-record boundary) and the page carries no effect authority (the paged-listing agent lists everything and asks before a fetch). The volume is 3 GB. |
| Integration tree | `/home/username/.le-integration`: origin/main `c3db3408` plus twelve package commits and the repairs above, not pushed. The conformance gates pass; the failing tools tests were repaired (a naming clash between the two feedback packages, two conformance findings, the shard manifest, the architecture map). Release 38 waits for the verifiers, above all the CI sharding one, because a wrong shard map would block every push. |
| Seed wave 1 | 203 candidates from the owner's drive; the Claude Code reviewer approved 0 of 197 (S-6.207 evidence has the reasons). Drive-derived content moves to the Codex lane with stricter packaging rules. |
| Agents | Two usage limits stopped every agent (the Fable credits at about 16:00 UTC, the session limit until 21:20 UTC). Every unfinished worktree was saved as a patch twice (`~/.le-ci-tmp/agent-partial-2026-09-26` and `-b`), and both workflows plus the paged-listing agent were resumed at 21:30 UTC on Opus 5.5. |
| Codex | Running beside Claude in `/home/username/.le-codex-build/library-expansion-20260926` with 2,195 candidate components (2,065 API operation references), a source discovery timer and a design integration plan. The split is in its note `docs/context/CODEX-COORDINATION-2026-09-26-1725.md` and Claude's reply `docs/context/CLAUDE-COORDINATION-REPLY-2026-09-26-1735.md`, both uncommitted in the shared checkout `/home/username/loop-engine`: Codex supplies sources and candidate content, Claude integrates, reviews, releases and builds the site. |

The owner's later directions of the evening, each now a roadmap step or a
delegated package: the public changelog, feature list and todo pages
(S-6.212, building), the benchmark-radar setup as a model for a first-party
Baltor skill and a daily public snapshot (S-6.213), and daily distillations of
papers, skills, plugins, protocol servers, services and repositories served as
pages, RSS, JSON and components (S-6.214). The design package the owner gave
Codex (`Baltor.ai page improvements.zip`) is Claude's to implement, after
release 39, following Codex's integration plan.

## Next steps, in order

1. Release 38 from the integration tree once the verifiers report: the
   feedback reports and withdrawal, user feedback, the red-team page, the
   oracles, the request ledger, the weekly number, tag rules 1.1.0, the pure
   fix, CI sharding if its verifier passes; then install the rescan, oracle and
   ledger cron entries against the job checkout, fast-forward the job checkout
   between slots, and add the redteam.baltor.ai record and certificate.
2. Release 39: the public status pages, facet tags, quickstarts and paging
   with the effect confirmation, when their builders and verifiers finish.
3. The design integration, steps 1 and 2 of the Codex plan, as one checked
   increment after release 39.
4. Review and integrate the Codex drafts (adapted references, the shared
   compiler review, the verification plan), then review the Codex lane's
   candidates with a non-OpenAI reviewer and publish through the daily job.
5. Restart or merge the seven paused lines the request ledger lists, and the
   Procedural Graphs research that never reached main.
6. Feed the overnight batch's 8,904 native candidates to the native review
   path as a second input of the daily job.
