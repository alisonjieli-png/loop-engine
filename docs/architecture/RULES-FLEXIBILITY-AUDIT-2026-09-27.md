# Rules and tests flexibility audit, September 27, 2026

Kind: dated architecture record. It reviews the checks that gate a change to
this repository, names the ones that block iterative work without protecting
a real invariant, and proposes a narrower check for each. Four small changes
made in this pass are listed with the known-wrong test that proves each one
still rejects the case it exists for. Everything else is a proposal.

Date: 2026-09-27. Observed at `origin/main` revisions `923453a4` and
`389fe7c6`, in the dated handoffs under `docs/context/`, in 300 runs of
`ci.yml` read with `gh run list` and `gh run view`, and in `git log` since
August 28, 2026 (973 commits). Inferred facts are marked as inferred.

## Why this audit exists

The owner, September 27, 2026: "We also need to watch out for any rules or
tests that are not flexible enough as we continuously and iteratively
develop."

[AGENTS.md](../../AGENTS.md#persistent-general-solving) already says how a
check may change: "When a check fails, first decide whether the work, the
check, or the environment is wrong, and record why. Do not weaken a check to
make it pass. A revised check must still reject a known-wrong answer." This
audit applies that rule to the checks themselves, before they fail again.

## What a flexible check looks like

A check earns its place when it protects one named invariant and fails the
known-wrong case for that invariant. It becomes rigid when it holds a stand-in
for the invariant instead:

| Rigid form | What it really wants | Flexible form that still fails the wrong case |
|---|---|---|
| Whole-file bytes of a cited source | The cited passage still says what the item claims | Pin the revision, and compare the tree only where a body restates the file |
| Exact page copy or a count in a browser test | The page shows the element and it works | Assert the role, the landmark, the link target and a live value read from the service |
| A committed generated file that must match its generator | Readers see a current index | Keep only lines that an addition inserts, so a merge adds lines instead of rewriting one |
| A baseline file of accepted findings | No new finding of a known-bad pattern | Identify findings by value and symbol, not by position, and fail on a new one with its place |
| The newest file name, a date or a release number | A route points at a current record | Resolve the newest record by its date field |
| A job that runs on any event of a type | The job runs when someone asked for it | Gate on an explicit input or a named caller |

Checks of behaviour are preferred over checks of wording. A wording check is
still right where the words are the invariant: the owner's quoted rules in
the [authority section](../../AGENTS.md#commit-push-and-release-authority),
the full phrase "discrete cognitive or act step Loop node", the retired public
terms and the runtime words kept off the public pages. Those stay.

## Where the red runs came from

Every one of the 46 red push runs of `ci.yml` on `main` from September 20 to
27, 2026 was traced to its failing check (observed):

| Red push runs | Cause | Section |
|---|---|---|
| 10 | `tools/test_build_records_index.py`, the committed index against a fresh build | [Records index](#2-records-index-totals-line-commit-cb950039) |
| 8 | `tools/test_starter_catalogue.py`, whole-file pins of cited source files | [Starter catalogue](#1-starter-catalogue-citations-commit-3b6b3ddd) |
| 8 | markdownlint on hand-written documents (bare addresses, a missing final newline), two causes repeated | Kept |
| 8 | `tools/test_opencode_generation_lanes.py` needed a local credential variable (September 24) | An environment fault, since fixed |
| 5 | The hardcoding delta gate | [Hardcoding gate](#hardcoding-delta-gate) |
| 5 | A `candidate_review` import error on Python 3.11 | A real fault, since fixed |
| 3 | markdownlint on the generated `CONTINUATION-STATUS.md` | [Generated roadmap views](#generated-roadmap-views) |
| 3 | A rule of at least three verification cases for each delivery package, known only to `tools/test_architecture_audit.py` | [Hidden audit rules](#hidden-rules-in-the-audit-test) |
| 3 | A self-test that failed at random, since fixed | Fixed |
| 2 | The retired-word source scan tripping on its own test cases | [Retired-word scanners](#retired-word-scanners) |
| 1 each | Contract copies out of step, the documentation charter gate, a stale status view | [Charter](#3-documentation-folder-charter-commit-3e9de4d6), [Contract copies](#contract-copies) |

In addition, all five manually dispatched runs of `ci.yml` from September 13
to 27 failed, four of them started by the directory refresh workflows. Checks
of generated files and of views derived from the roadmap caused 17 of the 46
red push runs.

## Changes made in this pass

Each change is its own commit in the worktree `/home/username/.le-cons-d`, so
the integrating session can take or leave each one. None touches the
authority section, a secret, a permission, spending or an external effect.

### 1. Starter catalogue citations (commit `3b6b3ddd`)

Where: `rule_cited_source_bytes_are_the_pinned_bytes` in
`tools/test_starter_catalogue.py`, with the data in
`examples/29_intelligence_service/starter-catalogue/items.json`, and
`cited_sources` in `tools/candidate_review/catalogue.py`.

What it protects: a body graded `restates_cited_source` must still describe
the bytes it cites. That invariant is real. The catalogue holds 123 bodies:
49 restate a cited file and 74 are graded
`general_practice_beside_cited_source`, which each say that the steps are
ordinary engineering practice written in the catalogue's own words. Of the 80
pinned files, 22 are cited by a restating body and 58 only by general-practice
bodies.

Friction: the rule compared every cited file with the working tree, so an edit
of any cited file forced a new anchor, which rewrites all 123 body digests. It
caused 8 red push runs on September 21 and 22 (from `fb00a009` to
`a8f1c18d`), twelve anchor commits from September 22 to 24 (`641ae2ff` alone
touched 174 files for a 48-line edit of `http_entrypoint.py`), and it helped
pull the staff tools line out of release 26 (`e09d70bd`). All fourteen
recorded anchor moves were forced by files that only general-practice bodies
cite. Since September 24 no commit on `main` has changed any of the 80 files
except a reverted pair, while 67 commits changed `service_runtime` (inferred:
people route work around cited files).

Change: the strict comparison with the tree stays for every file a restating
body cites, and an item without a recorded grounding counts as restating. For
a file that only general-practice bodies cite, the pin must equal the file at
the anchor revision in the repository history, and a later edit in the tree
is no longer a finding. A missing cited file is still reported. The review
path reads each cited source at the anchor revision and falls back to the tree
only when no history is available; the pinned digest decides either way.

Known-wrong tests: an edit of a restated file gives exactly one finding; a
wrong pin on a general-practice file gives one; an item that loses its
grounding is held to the strict side; a missing file is reported; the review
reads the committed bytes when the tree differs and the tree only without
history. Mutants that drop the history comparison, or treat every file as
general practice, fail these tests. `tools/test_starter_catalogue.py` (33
tests) and `tools/test_candidate_review_prechecks.py` (29 tests) pass.

Proposal beyond this change: give each item its own anchor revision and move
the "Compiled from" or "Written for this catalogue at revision" sentence out
of the digested body into the item record, so that an anchor move changes no
body digest, no approval and no homepage digest.

### 2. Records index totals line (commit `cb950039`)

Where: `render` in `tools/build_records_index.py` and
`test_the_committed_index_is_current` in `tools/test_build_records_index.py`.

What it protects: every dated record is listed. That is real.

Friction: every added record rewrote the line "Records: N. Subjects: M.
Folders: K.", so two sessions that each added a record always conflicted on
`docs/RECORDS-INDEX.md`. Ten red push runs followed (`cada3f3c`, `1da8263f`,
`88714c27`, `a8f1c18d`, `ac484b14`, `f30e7961`, `4ca0f568`, `b599675b`,
`20a2c2b2`, `76e14faa`), and 15 of the 122 merges since September 18 needed a
hand resolution of this file.

Change: the index no longer writes the totals line. An added record now only
inserts lines. The committed-index check is unchanged and still fails a stale
index.

Known-wrong test: an added record must leave every earlier line in place and
in order. A mutant that restores a totals line fails it.
`tools/test_build_records_index.py` passes (8 tests).

A further option, not taken: `docs/RECORDS-INDEX.md merge=union` in
`.gitattributes`. Replayed on the 15 historical merges, all 15 merged without
stopping, but 2 produced an index that differs from a fresh build, so the
regeneration that `--check` demands is still needed. `.gitattributes` and
`.gitignore` belong to a parallel builder in this consolidation.

### 3. Documentation folder charter (commit `3e9de4d6`)

Where: `_docs_folders_without_charter` in `src/loop_engine/conformance_report.py`,
the zero-tolerance gate `docs_folders_without_a_charter_readme`.

What it protects: every documentation folder states its kind. Real and cheap.

Friction: on September 26, 2026 continuous integration refused `edcc77a3` for
the new `docs/design` folder although its only brief already said "Kind: a
working brief" on its third line. The log said only
`{"docs_folders_without_a_charter_readme": 1}` and named no folder. The fix
took two red runs and 43 minutes (the handoff of September 26 records it).

Change: a folder states its kind in a README, or, without a README, in every
Markdown file it holds. The self-test note names the uncharted folders when
the gate fails.

Known-wrong tests in the self-test canary: a README-less folder with one file
that states no kind, a README without a kind, and a folder with no Markdown at
all are still reported; a folder whose briefs each state a kind passes.
Mutants that always require a README, or pass every README-less folder, both
change the canary's result. The conformance report's self-test passes 8 of 8.

### 4. Conformance manifest moving fields (commit `fb34a1e0`)

Where: `run_conformance` in `src/loop_engine/conformance_report.py`, which
rewrites the committed `src/loop_engine/architecture_conformance.json` on
every conformance or self-test run.

What it protects: nothing in the committed copy is read by a check; the run's
printed report and returned manifest are what gates and tools read.

Friction: the committed file changed in 141 commits over 30 days, 39 of the
51 since September 20 only because `files_scanned` moved; it needed a hand
resolution in 9 merges, and a manifest-only commit (`cd079477`) became
release 36's revision. Every local test run dirtied the tree.

Change: the written copy leaves out the scanned-file count and the line
numbers of known findings. It keeps every gate, every finding by rule, file
and detail, and `all_gates_pass`. The printed report and the returned
manifest still carry both fields.

Known-wrong test in the self-test: a written manifest that keeps the count,
drops a finding, or changes a gate or the pass flag fails the new check.
Mutants that keep the count or drop the findings are both caught. The
conformance report's self-test passes 9 of 9 and the regenerated manifest
reports every gate passing.

## Checks that matter for maintained decisions and capabilities

The [four-zone architecture record](FOUR-ZONE-ARCHITECTURE-2026-09-27.md#research-privileges-and-release-privileges)
describes the research and capability release pipeline the owner endorsed on
September 27, 2026. The design names six behaviours that show it is ready for
production. They are behaviour checks, and they come before any wording check
for this pipeline:

| Behaviour | Known-wrong case the check must fail | Today |
|---|---|---|
| An interrupted campaign resumes | A campaign killed between two stages redoes a finished stage or loses a claim | Partial: the daily job keeps a journal for each stage and reuses an uploaded archive whose bytes match; no test kills and resumes a campaign |
| A duplicate trigger does not duplicate publication | Two triggers of one bundle produce two releases or two pointer moves | Exists at the service edge: `publish` in `core/service_runtime/catalogue_releases.py` is idempotent by content and refuses a moved pointer; no end-to-end test runs two triggers |
| A malicious source cannot authorize an action | Text inside a fetched source changes a question, a criterion, a credential or an effect | Partial: the prechecks refuse unsafe instructions and undeclared effects in packages; no source snapshots exist yet, and no test injects instructions into one |
| An expired claim is not served as current | A claim past its check-again date is served as an approved result | Missing: the catalogue schema has no expiry field |
| A release is revocable | A withdrawn item stays served, or a later release brings it back | Exists in the service: durable withdrawals that no release undoes, and a verified rollback; reaching copies already installed on customer machines is missing |
| A harness can reproduce a published acceptance result | A published result that its pinned bundle and evaluation record cannot reproduce | Missing for single items; the quickstart check covers search, download and placement only |

## Proposals

Each proposal names the invariant, the friction, the flexible version and the
known-wrong case it must still fail. They are ordered by friction and ease.
None is implemented in this pass.

### Continuous integration on the wrong trigger

The job "manual live Ollama orientation" in `.github/workflows/ci.yml` ran on
every `workflow_dispatch`, and the two directory refresh workflows dispatch
`ci.yml` after each data commit, so every refresh ran live model calls and
turned `main` red (four of four dispatched runs from September 26). Fixed on
`main` by a parallel builder in `db393512`: the job now needs the dispatch
input `live_ollama`, and `tools/test_ci_live_ollama_dispatch.py` holds the
condition. Recorded here as done.

### Hardcoding delta gate

Where: `devtools/src/loop_engine_devtools/cli.py` (exit on any new high
finding or allowlist problem) and `assurance/hardcoding.py` (a finding's
identity includes list indices in JSON and YAML and an ordinal; the baseline
comparison is a plain set difference; an expired allowlist entry fails even
when its finding is gone; only a symbol named exactly `self_test` is exempt as
a fixture).

What it protects: secret-shaped values and endpoints that settings should
own. It misses the owner's rule against hard-coded solution paths: a probe
found that `if task_id == "titanic-survival"` passes as medium and a hard-coded
competition input path gives no finding, while `status == "active"` blocks as
high.

Friction: the baseline changed in 29 commits and was regenerated four times
(`604029ad` on September 21 alone added 71,368 lines after 8,507 findings
became "new"); the allowlist grew to 750 entries in 54 commits, about 47 of
them only to pass; inserting into a JSON list moved index-bound identities
(`b599675b`, `bcd05095`); 31 of 86 failed runs since September 13 failed here.
A sample of 30 allowlist entries held 26 false positives. One entry expires on
October 26, 2026 and will fail the gate even though its finding is gone.

Flexible version: require a host after a URL scheme; exempt any symbol path
that contains `self_test`; skip a shell variable that the same script assigns;
look a finding up before judging an entry's expiry and warn 14 days ahead; then
a second baseline version that matches moved findings by value digest,
classification and symbol, and `[]` instead of list indices in key paths.
Tested on a copy of the tree, the first four changes keep the gate passing,
keep the module's own 24 checks passing, and lower high findings from 1,364 to
1,294. Known-wrong cases that must still fail: a provider address with a
host, a credential variable name, `status == "active"` in production code, an
unassigned `$FLY_API_TOKEN`, and an expired entry whose finding still exists.

### Generated roadmap views

Where: `cell()` in `tools/build_continuation_status.py` and `_cell()` in
`tools/build_development_tracker.py` escape only the pipe and the newline, and
both views write a plan fingerprint line.

Friction: three red documentation runs (`61d8b317`, `e199f715`, `29016cb3`)
came from roadmap prose (a bare address, `<day>`, `<run>`) reaching the
generated view, and each was fixed by rewording the roadmap. The roadmap
changed in 117 commits, the status view in 86 and the tracker in 79 over 30
days.

Flexible version: escape angle brackets outside code spans and wrap bare
addresses in the two cell functions (a prototype changes 0 of today's 1,358
lines); drop the fingerprint lines, which nothing reads. Known-wrong case: a
step whose next work holds `~/x/<run>/journal.jsonl` and a bare address renders
with no raw tag and no bare address, and code spans stay untouched; a stale
view still fails its freshness test.

### Retired-word scanners

Where: `src/loop_engine/nomenclature_conformance.py` matches retired terms as
plain substrings, and one permitted fragment anywhere on a line exempts the
whole line; the "Refuse retired public language" step of `ci.yml` and the Vale
rules match bare English words.

What it protects: the retired topology words, the retired record names and
the old decision step name must not come back. Real.

Friction: `dd52314a` and `d072b8c9` (September 21) were red because the
scanner flagged its own test cases; the starter catalogue test now assembles
the retired heading from separate words just to name what it refuses
(`46577821`); `ddc69a93` (September 26) had to reword the owner's to-do page
request in six files. A probe flagged 8 of 8 innocent lines (third-party
parameter and property names, a line about customers' payment records, a
privacy sentence about minors) and found the reverse leak too: a line that
holds a permitted fragment hides a real retired term written on the same
line.

Flexible version: remove each permitted fragment from the line before
searching, instead of exempting the line (about six lines; on today's package
it surfaces two lines, both a checker's own test cases, whose fragments
extend in the same change); later, refuse the retired phrases and identifier
forms instead of the bare words. Known-wrong case: a line with a permitted
parameter name and a retired phrase in a comment must be reported; the same
line without the comment must pass.

### Browser checks that pin copy and counts

Where and friction:

- `tools/check_service_workspace.mjs` compares the shown library count with
  `String(served)`, while the page renders the count with thousands
  separators, so from 1,000 items a correct page fails.
- `test_homepage_demonstration.py` pins the packaged homepage's count to the
  starter release's 43 items, and until September 27 the service sent that
  number unchanged, so link previews and crawlers read 43 while 12,191 were
  served. Since `4c2350f1` on `main` (a parallel builder) the service writes
  the live count into the page as it serves it, with its own known-wrong
  test, so the pin now fixes only the packaged fallback.
- One scroll budget is written in four places, and the documentation check
  keeps its own 1,800-pixel budget, which refused a working page in
  `e5d21e89`.
- `tools/check_hosted_website.mjs` (the check named
  `live_hero_shows_a_working_directory_and_no_worked_example`, with the
  owner's September 24 direction in its comment) still refuses any search,
  reference, digest or download in the hero band, but the September 26 hero
  has a search demonstration, so the check fails on the current page. The
  design changed and the check did not.
- 52 of the 70 commits to `index.html` also changed the browser suite; the
  owner asked on September 25 for "more flexible, reasonable, and human
  oriented tests rather than something too strict" (ledger R-76).

Flexible version: compare the count with its localized rendering; one budget
helper read from the layout standard; the hero's parts read from one declared
design record that both the page and the check use. Known-wrong cases: "1200",
"1,201" and "43" fail for 1,200 served items while "1,200" passes; a hero
that shows a worked example where the design record declares none fails, and
a hero that omits the demonstration the record declares fails.

### Gates the pre-push check skips

Where: `tools/pre_push_check.sh` declines "Check public language" and "Check
local links and section anchors" when `vale` or `lychee` is not on the path,
and prints the decline as one line in the table.

Friction: continuous integration refused `f4979336` for a link to this record
before it existed, because the local check had skipped the link checker; the
fix `389fe7c6` says so. Both tools are now installed under `~/.local/bin`.

Flexible version: when a gate that continuous integration enforces is
skipped, print a warning block after the table that names each skipped gate
and the missing tool, look in `~/.local/bin` before declining, and offer a
strict setting that fails the run on a skip. Known-wrong case: a run on a
machine without `lychee` must name the link gate in the warning; with the
strict setting it must exit with a failure.

### Test shard manifest

Where: `tools/ci_test_shards.json` holds the four shards' module lists and
per-shard time estimates in `measured_seconds`; `tools/test_ci_test_shards.py`
requires every test module in exactly one shard.

Friction: each commit that adds a test module rewrites the time estimates of
all four shards, so every merge of two lines that add tests conflicts on the
same four numbers (15 commits to the file since September 26). The manifest
took 8 commits within about 15 hours of its creation, and release 38 waited on
the sharding check.

Flexible version: compute the shard totals from the per-module times recorded
in `artifacts/ci-speed-2026-09-26/` when the balancer runs, instead of
committing them, and give a module that no shard lists a stable fallback shard
reported as a note. Known-wrong cases: a module in two shards, a listed module
that does not exist, and, with the fallback removed, a new module that runs in
no shard all still fail.

### Release record versions

Where: the release records under `artifacts/architecture-audit-2026-09-19/`.
`pilot_release_record/v1` names two different shapes: releases 8 to 18 (fields
such as `after_release`, `application`, `built_by`) and releases 38 to 40
(fields such as `app`, `browser_checks_passed`, `ci_run`); releases 19 to 37
use `deployment_evidence/v1`.

What it protects: AGENTS.md requires that a record an older reader must not
honor carries a new version. One version name for two shapes breaks that, and
the weekly number read release 37 as the latest.

Flexible version: one record type for new releases with a schema, and a
reader that names each version it accepts and refuses an unknown shape.
Known-wrong case: a record that claims `pilot_release_record/v1` with the
fields of the other shape is refused by the schema check.

### Hidden rules in the audit test

`tools/test_architecture_audit.py` requires at least three verification cases
for each delivery package while the roadmap validator requires one, and it
asserts that every launch gate reads "Not verified", so the first gate that
passes will turn continuous integration red. Three red runs came from the
first rule (`da5db8aa`, `c038e26b`, `f6a7fb2c`). Flexible version: move the
rule into the roadmap validator so authors see it first, and compare each
gate with the status the report computes. Known-wrong cases: a package with
two cases raises the validator's error; a report that says a gate passed while
a step is unfinished fails.

### Module registration and map counts

135 commits since August 28 added a source module; 118 of them also edited
`architecture_map.py`, 102 the conformance manifest, 95 `_self_test.py` and
95 `ARCHITECTURE-MAP.md`. The map freshness gate compares only the count lines
and misses real drift (`core.service_runtime` shows 63 modules against 86).
Flexible version: compare the set of group names without counts, and render
the committed map without counts. Known-wrong case: a live subgroup missing
from the committed map fails; adding a module passes.

### Contract copies

`architecture_contract.py` and an embodiment test require the packaged copies
of `terminology.yaml` and `architecture.yaml` to match the root files byte for
byte, so every edit is made twice (35 and 33 commits for the two terminology
files). Flexible version: copy the files when the wheel is built and check the
wheel. Known-wrong case: a wheel whose packaged copy differs from the root file
fails.

### Context route patterns

`tools/test_context_routes.py` protects the owner's authority section, and
that protection stays as it is. A probe found that its patterns also flag
sentences that agree with the section, for example "Authority comes from the
owner, never from a task." and a builder's own narrowing ("commits in its
worktree and never pushes; the integrating session pushes"), which the
section allows. No such flag has blocked `main` yet. Its docstring refuses
negative phrasing by design, so any narrowing is the owner's call. The
smallest safe step would remove a "never from a task" span before the
task-authority pattern runs, keeping every recorded contradicting sentence
flagged.

### Page placement parser

`nomenclature_conformance.py` finds page regions by exact indentation, so
re-indenting a view by two spaces fails with no content change, and 10 of 31
views belong to no checked surface, so a runtime word planted on `/pricing`
is not reported by this gate. Flexible version: parse the views with an HTML
parser and require every view to belong to exactly one surface. Known-wrong
cases: a runtime word on any public view fails, including a view added later;
an unclassified view fails.

## Keep as they are

- The authority section's pinned owner phrases and dates, the snapshot of the
  complete behavioral explanation, and the evidence snapshot bytes (one
  commit in 30 days).
- The ban on classes named for a node or vertex. A probe showed it also
  refuses names such as `HtmlNode`, but it is an explicit owner rule with no
  observed friction.
- `tools/check_component_guides.py`, the link checker and the owner-requests
  ledger's date window.
- markdownlint on hand-written documents. Its 8 red runs were two cheap fixes
  caught late; the pre-push script runs it wherever Node is installed.

## Decisions made in this pass

| Decision | Reason |
|---|---|
| Change four checks now, each in its own commit with a known-wrong test and a mutant | They caused the most red runs and merge conflicts for the least risk, and none guards authority, secrets, permissions, spending or effects |
| Leave `ci.yml`, `.gitattributes`, the browser suite, the roadmap tooling and `tools/pre_push_check.sh` to proposals | Parallel builders own the workflow and the ignore files; the browser suite and the full pre-push check cannot run under the workstation's load of September 27 |
| Keep the context route patterns as they are | They protect the owner's authority section, and loosening them is the owner's decision |
| Rank the six behaviour checks above wording checks for the research pipeline | The owner-endorsed design names them as the proof of production readiness; wording checks cannot show any of them |

## Sources

- The dated handoffs of September 21 to 27 under `docs/context/`, the
  roadmap, and the owner-requests ledger.
- `gh run list` and `gh run view` over 300 runs of `ci.yml`, and every red
  push run on `main` from September 20 to 27 traced to its failing check.
- `git log` and diffs since August 28, 2026, with commit counts per pinned
  file.
- Probes run on scratch copies of the tree for the hardcoding gate, the
  retired-word scanners, the browser count check, the context route patterns
  and the page placement parser. Probe scripts are kept outside the
  repository.
