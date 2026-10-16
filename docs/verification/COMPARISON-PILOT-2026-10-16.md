# Popular-project comparison pilot, October 16, 2026

Kind: verification record of a diagnostic pilot, dated October 16, 2026. It
keeps its bytes; later work belongs in a new record. Roadmap steps: D-06, D-09,
S-6.173 and S-6.185 for the comparison, S-6.35.09 for the AgentBriefs briefs.
Protocol: the [customer-task comparison programme](../roadmap/DELIVERY-SEQUENCE.md#customer-task-comparison-programme)
and the [AgentBriefs proposal qualification](../roadmap/DELIVERY-SEQUENCE.md#agentbriefs-proposal-qualification).
Machine-readable records: [artifacts/comparison-pilot-2026-10-16](../../artifacts/comparison-pilot-2026-10-16/).

The owner, October 16, 2026: "we should also try more demos, tests, E2E tests,
including using baltor.ai and similar systems to monitor, recreate, redo, side
by side comparison of popular coding projects, such as coderabbit lists, github
lists of common projects, kaggle, etc, and also show how agentbriefs can suggest
ways to improve upon them as new technologies, systems, architectures, are
released".

## Outcome

Three tasks from popular-project sources ran twice in each arm. Both arms used
the same pinned OpenCode 1.17.9, the same `gemma4:31b` route on Ollama Cloud,
the same sandbox and the same budget. The only intended difference was the
Baltor connection of a fresh customer account.

| Task | Without Baltor | With Baltor |
| --- | --- | --- |
| a. Recreate cachetools `TLRUCache` | 0 of 2 accepted; 31 of 34 hidden tests each | 0 of 2 accepted; 31 of 34 hidden tests each |
| b. Repair a seeded python-dotenv parser fault | 0 of 2 accepted; both stopped at the 20-request cap | 0 of 2 accepted; both stopped at the 20-request cap |
| c. Spaceship Titanic, held-out travel groups | 2 of 2 accepted; accuracy 0.8120 and 0.7992 | 1 of 2 accepted; accuracy 0.8108 and 0.7847 |

The Baltor-arm harness never searched, read, downloaded or loaded anything from
Baltor in any of its six runs. The treatment reached every request: the
connection line in the prompt and twelve `baltor_*` tools. The model chose not to
use them. This pilot therefore measured what the connection costs, not what
Baltor material does. The connection added 2,617 input tokens to each task's
first request, before any work, and the same definitions travel with every later
request. The published skill bootstrap took 2.3 to 2.9 seconds.
The one-run difference in task c cannot be attributed to Baltor material,
because none was used. Two repetitions cannot separate it from chance.

The pilot used 145 of its 300 allowed model requests: 2 for the declared probe
and 143 for the twelve trials. Every request reported its usage. No provider
failure or wrong-file incident was recorded, and no tool command tried to reach
an outside host.

## Where this fits

The two with-and-without studies in the repository's case studies,
[data cleanup](../../case-studies/data-cleanup-with-and-without-baltor/README.md)
and the [overnight batch](../../case-studies/overnight-cheap-model-with-and-without-baltor/README.md),
used the Pi harness, synthetic rows and hand-placed material. This pilot uses
popular public projects and a fresh customer account instead. Here the Baltor
arm used the published [OpenCode quickstart](../guides/quickstart-opencode.md)
connection and skill bootstrap, and discovery was left to the harness, as it
would be for a customer.

A pilot of this size is a diagnostic. It shows whether the method, the
records and the scorers work, and where the next study must change. It supports
no percentage claim in either direction.

## Sources

The inventory is [sources/source-directory.json](../../artifacts/comparison-pilot-2026-10-16/sources/source-directory.json),
written in the packaged Feeds source format and checked by its own parser
(16 sources, 2 collections). The repository research watch pinned the GitHub
revisions in [a pilot report](../../artifacts/comparison-pilot-2026-10-16/sources/RESEARCH-SOURCE-WATCH-2026-10-16-pilot.json)
(9 sources, 0 failures). Everything was read on October 16, 2026.

| Source | What it can supply | Licence or terms |
| --- | --- | --- |
| [CodeRabbit open-source leaderboard](https://coderabbit.ai/blog/one-million-open-source-reviews-september-2026) | The ten public repositories with the most CodeRabbit reviews in September 2026, from stablyai/orca (5,629) to jdx/mise (1,386) | No reuse terms beyond a copyright notice; names and counts kept as facts |
| [CodeRabbit sponsorship post](https://coderabbit.ai/blog/coderabbit-commits-1-million-to-open-source) | Sponsored projects: pnpm, Biome, ast-grep, iTerm2, markdownlint | No reuse terms stated |
| [awesome-coderabbit](https://github.com/coderabbitai/awesome-coderabbit) | 13 open-source projects that use CodeRabbit, configuration examples | CC0-1.0 |
| [GitHub Trending](https://github.com/trending) | Fast-rising repositories by language and period | GitHub Acceptable Use Policies, section 7 |
| [GitHub Topics](https://github.com/topics) | Repositories by topic and stars | GitHub terms |
| [awesome-python](https://github.com/vinta/awesome-python) | Curated list of common Python projects; source of tasks a and b | CC BY 4.0 |
| [awesome](https://github.com/sindresorhus/awesome) | Index of curated lists | CC0-1.0 |
| [Kaggle Getting Started](https://www.kaggle.com/competitions) | Knowledge competitions; source of task c | Each competition's rules |
| [Kaggle notebooks](https://www.kaggle.com/code) | Most-voted public notebooks per competition | Each notebook's licence |
| PyPI, OSV and each project's changelog | Release and advisory evidence for the briefs | Stored facts under existing source contracts |
| Baltor [model directory](https://baltor.ai/models) and [MCP directory](https://baltor.ai/directory) | Model and tool evidence for the briefs | Existing source contracts |

The owner's "CodeRabbit lists" match three published lists: the September 2026
review leaderboard, the sponsorship post and awesome-coderabbit. None of their
projects fit a small offline task. They are large applications, Rust,
TypeScript or Zig toolchains, or need a GPU or services. markdownlint was
considered and left out because its acceptance tests are snapshot suites that
need the full Node development toolchain. GitHub Trending's monthly Python view
was mostly large AI agent projects. The selection rule in the
[design](../../artifacts/comparison-pilot-2026-10-16/design/design.json) records
these reasons.

## Frozen tasks

The design was committed as `1bd1f2e8` before the first model call. The
[freeze record](../../artifacts/comparison-pilot-2026-10-16/design/design-freeze.json)
holds the digest of each of its 28 frozen files.

| Task | Source and workspace | Hidden acceptance (never mounted in the sandbox) | Passes when |
| --- | --- | --- | --- |
| a-cachetools-tlru | cachetools 7.2.2 (MIT), commit `be0b2eba`, with `TLRUCache` and `tests/test_tlru.py` removed; documentation and type stub kept | The upstream tests folder at v7.2.2, run against the harness's `src` folder | All 353 upstream tests pass, including the 34 TLRUCache tests |
| b-dotenv-backslash | python-dotenv 1.2.4 (BSD-3-Clause), commit `a565c2cc`, with the parser half of upstream fix `f7b18d9c` (pull request 680) and its parser tests reversed; the bug report blames `set_key` | The upstream tests folder at v1.2.4, the seeded tree and the reference parser | Upstream tests pass, the library change touches only `parser.py` in at most 12 lines, a new test fails before and passes after, and `ROOT_CAUSE.md` names `parser.py` and the single-quoted value pattern |
| c-spaceship-titanic | Kaggle Spaceship Titanic, 6,970 visible passengers; 1,723 passengers from 20 percent of travel groups held out with seed 20261016 | The held-out labels | `predictions.csv` covers every held-out passenger and scores at least 0.790 accuracy |

Before the freeze, 17 scorer controls behaved as expected
([scorer-controls.json](../../artifacts/comparison-pilot-2026-10-16/design/scorer-controls.json)).
The three known-good controls passed: the upstream `TLRUCache`, the upstream
parser fix with a test and an explanation, and a gradient boosting reference at
0.8131. The 14 known-wrong controls failed. They include a `TLRUCache` that
ignores its time-to-use function, the misleading `set_key` fix, a fix of the
single-quoted pattern alone, the right fix with an unrelated change, plain
logistic regression at 0.7841 and predictions with missing passengers. No
competition row is committed; only counts and digests are.

## Method

- **Harness.** OpenCode 1.17.9 (binary SHA-256
  `ff18379ebe33df346d2b3b36080ccef9c0eb0b0cdf68dd471567e0304651db70`), run as
  `opencode run --format json` in a Bubblewrap sandbox. The sandbox saw the
  system folders, the shared Python 3.14.4 environment and the trial's own home
  folder. The repository, the hidden acceptance material and the rest of the
  workstation home were not mounted.
- **Model route.** `gemma4:31b` on Ollama Cloud, reached through the counting
  proxy copied from the overnight case study. The proxy counts each request
  before sending it and refuses requests beyond the cap or the deadline. The
  provider key stayed outside the sandbox. A declared probe confirmed tool
  calls in 2 requests.
- **Arms.** The Baltor arm added the published `mcp.baltor` connection entry,
  ran the published baltor-library skill bootstrap in the project, put the
  customer's key in `BALTOR_SERVICE_TOKEN` and appended one sentence to the
  prompt: the library is connected, and the harness may search it or continue
  without it.
- **Customer account.** One fresh account was created through the live sign-up
  with `tools/check_live_account_journeys.mjs --fresh-only`. Its tenant is
  `customer.e62171d41ebd73ac6f2f887e1773ee1324391b08ae0fba057f893394e6bd4fc1`.
  It took a founding place, and its account page showed Pro, free each month.
  One Baltor key was created on that page with the search and download scopes
  and a 2,880-minute lifetime.
- **Network.** Every proxy variable in the sandbox pointed at an allowlisting
  proxy that opened tunnels only to `baltor.ai` and `app.baltor.ai`, for both
  arms. A program that ignores proxy variables would not be stopped, so the
  tool calls were scanned afterwards.
- **Budget and order.** 20 model requests and 30 minutes per trial, the same for
  both arms, with Baltor's setup inside its arm. The order was a fixed ABBA
  design written before the runs; the Baltor arm went first in three of six
  pairs.
- **Scoring.** The scorers read only the final project and the hidden material,
  never the transcript. Harness-written code ran in a second sandbox without
  network.

## Results per run

Input tokens are provider-reported; the figure in brackets is the part the
provider reported as cached. "Secondary" is TLRUCache tests passed of 34 for
task a, upstream parser tests passed of 56 for task b and held-out accuracy for
task c.

| Order | Attempt | Accepted | Secondary | Requests | Input tokens (cached) | Output tokens | Seconds | Stop | Baltor use |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | a-baltor-r1 | no | 31 | 8 | 237,086 (200,160) | 4,556 | 55 | finished | abstained |
| 2 | a-none-r1 | no | 31 | 7 | 199,325 (172,384) | 2,070 | 40 | finished | |
| 3 | b-none-r1 | no | 54 | 20 | 382,928 (365,600) | 6,168 | 89 | request cap | |
| 4 | b-baltor-r1 | no | 54 | 20 | 366,809 (343,648) | 4,389 | 76 | request cap | abstained |
| 5 | c-baltor-r1 | yes | 0.8108 | 9 | 103,088 (99,168) | 1,590 | 45 | finished | abstained |
| 6 | c-none-r1 | yes | 0.8120 | 7 | 53,872 (47,136) | 1,319 | 29 | finished | |
| 7 | a-none-r2 | no | 31 | 12 | 348,863 (313,440) | 2,010 | 45 | finished | |
| 8 | a-baltor-r2 | no | 31 | 8 | 258,578 (228,352) | 4,883 | 46 | finished | abstained |
| 9 | b-baltor-r2 | no | 54 | 20 | 374,593 (362,720) | 3,669 | 57 | request cap | abstained |
| 10 | b-none-r2 | no | 54 | 20 | 246,536 (227,072) | 1,257 | 65 | request cap | |
| 11 | c-none-r2 | yes | 0.7992 | 5 | 37,677 (35,616) | 904 | 41 | finished | |
| 12 | c-baltor-r2 | no | 0.7847 | 7 | 73,428 (63,648) | 1,480 | 37 | finished | abstained |

Each attempt has a [trial record](../../artifacts/comparison-pilot-2026-10-16/results/trials/),
and the [summary](../../artifacts/comparison-pilot-2026-10-16/results/summary.json)
holds the per-arm cells. Per arm, the Baltor arm used 72 requests, 1,413,582
input tokens (115,886 uncached), 20,567 output tokens and 316 seconds. The arm
without Baltor used 71 requests, 1,269,201 input tokens (107,953 uncached),
13,728 output tokens and 310 seconds. Cost is the owner's existing Ollama
subscription and is not metered per request.

## Side-by-side summary

**Task a.** All four runs made the same design choice. Each turned `TTLCache`'s
insertion-ordered linked list into `TLRUCache`, with the fixed time-to-live
replaced by the time-to-use function. That list assumes items expire in the
order they were inserted. The upstream class keeps a heap ordered by expiration
time instead. All four failed the same three hidden tests, which insert items
that expire out of insertion order or are already expired:
`test_ttu`, `test_ttu_expired` and `test_ttu_reverse_insert`. The prompt
pointed at `TTLCache` as the class to stay consistent with, which may have
encouraged this reading in both arms. The four
[patches](../../artifacts/comparison-pilot-2026-10-16/results/patches/) are kept.

**Task b.** No run changed the library. All four stopped at the request cap.
Three spent 6 to 16 of their 20 tool calls writing reproduction scripts and
tests through unquoted shell heredocs, which change backslashes. Two runs, one
in each arm, opened `parser.py` before the cap. Three runs added a test that
fails before and after, because nothing was fixed. No run wrote
`ROOT_CAUSE.md`. The Baltor-arm runs left scratch files such as `.env_repro`
and `reproduce_issue.py` in the project root. The rule counts only changes to
existing files outside the task's paths, so these are not wrong-file incidents.

**Task c.** All four runs wrote `RandomForestClassifier(n_estimators=100,
random_state=42)` on label-encoded columns, with a random 80/20 validation
split. Their own validation figures were between 0.0014 below and 0.0144 above
their held-out accuracy. The run that missed the floor, c-baltor-r2 at 0.7847,
had dropped the cabin number and added a total-spend column. Its own estimate
was 0.7991. Every `solution.py` reproduced its predictions exactly when the
scorer reran it without network. The
[solutions](../../artifacts/comparison-pilot-2026-10-16/results/solutions/) are kept.

## What Baltor offered and what the harness did

The treatment was delivered. Each Baltor-arm request carried the connection
sentence, the `baltor-library` skill in the skill list and 12 `baltor_*` tools.
The requests without Baltor carried 9 tools. In the first request of each task
the difference was 2,617 input tokens: 9,277 against 6,660 for task a, 9,347
against 6,730 for b and 9,360 against 6,743 for c. Later requests repeat the
same tool definitions; most of those tokens were reported as cached.

For library items, offered, selected, downloaded, placed, loaded and used were
all zero in the six Baltor-arm runs. The harness made no search, read, manifest
or skill call, and ran no client command. The bootstrap placed the
baltor-library client skill, as the quickstart publishes it, and the harness
never loaded it. The egress records show `baltor.ai` reached 54 times, nine per
Baltor-arm run: the seven bootstrap downloads, then two connections from the
harness that stayed open for the whole session, which match its MCP
connection. OpenCode's own attempts to reach `registry.npmjs.org` were refused in
both arms (18 times in total). No other host was attempted.

After the trials, a [retrieval diagnostic](../../artifacts/comparison-pilot-2026-10-16/results/retrieval-diagnostic.json)
outside the comparison sent nine searches with the customer's key, three per
task, and recorded hit metadata only. For task c it found two Verified skills
that fit the task's validation problem, `audit_data_splits_for_errors_and_leakage`
and `read_the_train_validation_gap`. For tasks a and b most hits were unrelated.
"time aware LRU cache" returned the same two data-split skills first.
"Spaceship Titanic" returned only a science fiction panel texture generator.
The first hit for "dotenv parser" was an install recipe for dotenv-linter, a
Rust linter for `.env` files. The diagnostic changes no trial result.

## AgentBriefs demonstration

Each source project has one brief in
[briefs/](../../artifacts/comparison-pilot-2026-10-16/briefs/), in Markdown and
JSON. Every candidate cites dated evidence, states its benefit as a hypothesis
and names the experiment and acceptance rule that would test it. No experiment
has run and no realized benefit is claimed.

| Brief | Candidates for one experiment | Withheld, with no alert |
| --- | --- | --- |
| [cachetools](../../artifacts/comparison-pilot-2026-10-16/briefs/cachetools.md) | Stateful property tests for the timed caches; documenting out-of-order expiry, from this pilot's shared failure | An agent-memory server matched by the word "memoize" and by Trending stars |
| [python-dotenv](../../artifacts/comparison-pilot-2026-10-16/briefs/python-dotenv.md) | Round-trip property tests; a conformance table against Node's `util.parseEnv` and Docker Compose; Python 3.15 in the test matrix | A model that repairs `.env` files while loading |
| [Spaceship Titanic](../../artifacts/comparison-pilot-2026-10-16/briefs/spaceship-titanic.md) | TabICL against the boosting reference, TabPFN only after a licence review; boosting libraries with native categories; grouped validation with Baltor's split checks | Fine-tuning a hosted model on the rows, which the competition rules forbid |

The briefs also record what is already in place, so it is not recommended
again. OSV listed no advisory for any pinned version on October 16, 2026, and
the briefs raise nothing on that empty answer. cachetools already tests free-threaded builds and Python 3.15, and keeps
an AI-assisted review record dated October 15, 2026. AutoGluon is not
installable on this task's Python 3.14. Baltor's model directory listed no
tabular model, so that evidence came from PyPI and the Hugging Face Hub.

## Proposed public demo page

This is a proposal. Nothing is published by this record.

- Build the page from a typed page record generated from the trial records,
  as `tools/build_showcase_page.py` does for the decision red team page. The
  generator should refuse a record that leaves out an attempt or shows a
  number that is not in a trial record. It should also refuse a percentage
  headline from a pilot of this size.
- Show one task at a time with two columns, without Baltor and with Baltor.
  Each column shows the actual patch or `solution.py`, the hidden-test or
  accuracy result, requests, input, cached and output tokens, seconds and the
  stop reason.
- Under the Baltor column, show the six use stages: offered, selected,
  downloaded, placed, loaded and used. For this pilot every stage reads zero
  and the column says the harness abstained. Show the 2,617-token connection
  cost per request beside it.
- Show failures as prominently as passes. This pilot's useful lessons are
  failures: the shared `TLRUCache` design error, the request cap in the
  debugging task and the off-target searches.
- Link each AgentBriefs brief from its task, with the withheld item visible,
  so a visitor sees what the brief refused to recommend and why.
- End with the declared limits and a link to the frozen design, so a reader
  can rerun the comparison.

## Limits

- Twelve trials on three tasks with one model, one harness and two repetitions
  per arm. This is a diagnostic, not an estimate of benefit or harm.
- The Baltor arm abstained in all six runs, so nothing here measures Baltor
  material. A different treatment wording, model or harness may behave
  differently.
- The task-a prompt's pointer to `TTLCache` may have steered both arms toward
  the same design error.
- The request cap of 20 stopped every run of task b before any fix.
- Popular projects may be in the model's training data; both arms share that
  exposure.
- The sandbox confines files, not every network path. The scan found no
  command that tried to bypass the proxy.
- Spaceship Titanic rows reached the model provider during the runs, as they
  would for any customer using a hosted model. No row is committed.
- The frozen design and the trial records state that cached input tokens were
  not reported. That is wrong: the provider reported them in each usage object,
  which the ledger keeps whole, and the
  [summary script](../../artifacts/comparison-pilot-2026-10-16/analysis/summarize.py)
  reads them from there. The dated records keep their bytes.
- The fresh account holds a founding place. The coordinating session will
  return it; this record does not.

## Decisions for the next run

These decisions are recorded here so that the next frozen design can adopt
them. None of them changes this pilot's results.

1. **Add a directive treatment arm.** The permissive sentence produced six
   abstentions in six runs. The next design keeps the permissive arm and adds
   a third arm whose prompt asks the harness to search Baltor before starting.
   That separates "the library had nothing" from "the harness did not look".
2. **Raise the request cap for the debugging family to 40 in both arms.**
   Twenty requests ended all four runs before any library change, so the cap
   decided the outcome and not the treatment.
3. **Drop the pointer to `TTLCache` from the task-a prompt.** The cachetools
   brief's documentation experiment needs that version of the prompt anyway.
4. **Treat the off-target search hits as retrieval-quality evidence.** The
   nine diagnostic searches belong to the retrieval quality work in the
   delivery sequence. Ranking was not changed here.
5. **Use Pro access as the treatment and state it.** The pilot account holds a
   founding place. A study of the paid offer should say so, and a study of the
   free tier needs a second account.

## Reproduce

From `artifacts/comparison-pilot-2026-10-16/runner`, with the inputs named in
the design:

```bash
python3 prepare_tasks.py --cachetools-repo CACHETOOLS --dotenv-repo DOTENV \
  --spaceship-train TRAIN_CSV --python-env PYTHON_ENV --out PILOT_ROOT
python3 controls.py --pilot-root PILOT_ROOT --python-env PYTHON_ENV \
  --extra-bin EXTRA_BIN --output controls.json
python3 -m unittest test_runner
python3 freeze.py --check
python3 probe.py --work WORK --python-env PYTHON_ENV --extra-bin EXTRA_BIN \
  --model gemma4:31b --output ../results/probe-gemma4-31b.json
python3 run_pilot.py --pilot-root PILOT_ROOT --work WORK --python-env PYTHON_ENV \
  --extra-bin EXTRA_BIN --baltor-key-file KEY_FILE --all
python3 ../analysis/summarize.py
```

`EXTRA_BIN` holds the `dotenv` command launcher that python-dotenv's tests call.
The runner refuses to start when a frozen file has changed. A rerun needs a
customer key in a private file, the Ollama key in `OLLAMA_API_KEY` and the
Kaggle competition data, which is not in the repository.
