# Independent review panel for harness intelligence candidates

Kind: component guide for roadmap package LS2. It describes current behavior.
The first real pilot is recorded in
[`reviews-panel-2026-09-22.json`](../../examples/29_intelligence_service/starter-catalogue/reviews-panel-2026-09-22.json),
and both of its attempts, their ledgers and their comparison are kept in
[`artifacts/candidate-review-pilot-2026-09-22`](../../artifacts/candidate-review-pilot-2026-09-22/README.md).
That version-one worker evidence remains historical. Current worker records
use version two and refuse version-one resume or admission input. The live
service's separate historical approval-source format is unchanged.

## What the panel does

The panel decides whether independent reviewers approve the exact bytes of one
candidate item for the harness intelligence library. It first compares the
body with its selected reference's exact digest and byte size, then runs six deterministic
pre-checks first, then asks reviewers from different model families, and
writes a dated review record beside the catalogue's `reviews.json`. It never
edits `reviews.json`, the item file, a body or a host manifest, and it serves
nothing. The lead engineer merges its verdicts into the served catalogue
through the existing carry and manifest tools.

The approval rule is the owner's rule of 22 September 2026:

- at least three reviewers approve the item;
- the approving reviewers come from at least three model families;
- none of them is from the family that produced the item;
- no reviewer rejects it. One written rejection keeps the item a candidate with
  its reasons.

A policy that weakens any part of the rule is refused when the panel loads. The
decision itself counts no approval from the producer's family, so the rule
holds even if a defect let that family be asked.

The panel is the first two of the three review layers that the harness and
library plan names: deterministic checks that can only refuse, and reviewers
that did not produce the item. The third layer, a person's spot audit of a
random sample before a batch is served, is not part of this panel.

## Where it sits

The panel is an operator command, like the other catalogue tools in `tools/`.
It runs off the production machine. Every model call it makes goes through the
repository's model gateway or a harness command line, and the gateway gives
each physical call its own model Loop. The panel grants no authority: model
calls need the explicit `--authorize-model-calls` flag and stay inside a
declared ceiling.

```text
Operational runtime type
└── Loop
    ├── Operational relationship
    │   ├── Starting
    │   ├── Spawned by
    │   ├── Queried by
    │   ├── Retrieved by
    │   └── Connected from
    ├── Role
    │   ├── Practitioner
    │   ├── Intelligence
    │   └── Solution
    ├── Versioned role profile
    ├── Purpose and domain categories
    ├── Run mode
    │   ├── deterministic
    │   ├── hybrid
    │   └── non-deterministic, with model-led semantic work
    ├── Step profile
    ├── Typed input and output contract
    ├── Loop condition
    ├── Exit condition
    ├── Graph relationships
    ├── Budget, permissions, and effect policy
    ├── Model settings when the selected mode permits a model
    └── Run History records
```

Today the panel command is not a registered boundary of its own. The proposed
registration, a deterministic Practitioner code execution Loop at a boundary
named "independent candidate review", is in the registration request of the
LS2 report. Until it lands, the ledger and the dated record are the evidence.

## Fixed edges and engines

Each swappable part sits behind a fixed, versioned edge, and the factory tables
in `engines.py` are the only code that names a concrete engine class.

```text
Candidate review
├── Pre-check edge: request in, candidate_precheck_result/v1 per engine out
│   ├── licence: builtin_licence_rules
│   ├── format: builtin_format_rules, agent_skills_reference
│   ├── safety: builtin_static_rules, skillspector_static
│   ├── effects: builtin_effect_rules
│   ├── secrets: builtin_secret_patterns
│   └── duplicates: exact_shingle_jaccard, datasketch_minhash_lsh
├── Reviewer edge: prompt and call allowance in, ReviewerAttempt out
│   ├── model_gateway: Ollama Cloud models through core.model_gateway
│   ├── command_line: codex exec and claude -p, each read by its own protocol
│   ├── provider_binding: an organisation endpoint named by a committed
│   │   provider binding, through core.model_gateway
│   └── fixture: scripted reviewers for offline checks, never in a real record
└── Envelope: panel.ReviewPanel
    ├── pre-checks, eligibility, family exclusion and the quorum rule
    ├── one item per call, or several items per call for a calibrated reviewer
    ├── budget, per-group call ceilings, rate limit pauses, spent allowances
    │   and a stop after repeated identical failures
    └── the ledger: dispatch, call, batch call and verdict rows, the resumable
        cursor
```

Every kind of pre-check must be decided for every item. A kind whose engines
are all unavailable, or an engine that fails, refuses the item. Every available
engine of a kind runs, so the record shows each result.

The fixed request edge checks the body's declared digest and exact integer
byte size before any replaceable pre-check engine or reviewer runs. A mismatch
is a `format` refusal by `candidate_request_integrity`, with no reviewer call
or budget reservation. Calibration deliberately changes its fixture metadata
to identify the planted body; normal requests never silently replace a bad
declaration with their measured digest.

## Pre-checks

### Original native packages

`--content-profile native-original` reads the preparation tool's exact
version-three item/specification files. The adapter checks the complete
`CataloguePackage`, every declared file, its bytes, source provenance and
producer. It selects [native package criteria](resources/NATIVE-PACKAGE-REVIEW.md)
and [native reviewer instructions](resources/NATIVE-REVIEWER-INSTRUCTIONS.md).
The existing panel, model engines, family rule and budgets remain in force.

The first native profile covers text instruction files, skills, declared
Python tools, text references, JSON Schema contracts and supporting JSON data.
Scripts are parsed and inspected, never executed by review prechecks. Missing
helpers, role/effect disagreements, unsupported required components and binary
assets without separate verification withhold review. Native loading and task
acceptance still require their own evidence. Packages are not flattened into
synthetic skills. Every exact text file reaches the reviewer in its own block.
The format engine's version two confines passive resources to `examples/`,
`verification/`, `references/`, `assets/` and `contracts/`, with a licence-notice
exception. Reserved native configuration paths cannot become passive by being
labelled as a reference, schema or data file.

The canonical package digest is the review subject's `body_sha256`; individual
file digests remain in its typed manifest. Version-two records explicitly name
the native subject type and persist its complete manifest, original item,
specification, producer method and request binding. A reader recomputes the
request hash from this material and binds it to each decision's call.

The native reader currently bounds each payload file at 256 KiB and each
package at 2 MiB, with the existing 64-file package ceiling. Oversized input
is refused, never truncated. Populations above the declared exact-comparison
ceiling select the existing MinHash engine; its missing optional dependency
refuses the duplicate check. `--calibrate` selects the
[frozen native control set](resources/native-calibration/README.md) for this
profile. It never reinterprets the starter-body calibration set.

### Starter catalogue bodies

| Kind | Engine | What it refuses |
|---|---|---|
| Licence | `builtin_licence_rules` | A licence outside the accepted permissive list, a licence state that is not settled, or a licence line in the text that disagrees with the declared licence. |
| Format | `builtin_format_rules` | Text that is not UTF-8, no title line, a word count outside the catalogue's range, a missing part, a wrong or misplaced grounding sentence, a practice sentence on the wrong kind of body, internal vocabulary, and a rendered skill file whose name or description a client would reject or truncate. |
| Format | `agent_skills_reference` | What the Agent Skills reference validator reports on the rendered skill file. |
| Safety | `builtin_static_rules` | Invisible characters, control characters, hidden comments, instructions to ignore earlier instructions or to approve the item, a download piped into a shell, decoded text handed to a shell, destructive commands and reads of credential files. |
| Safety | `skillspector_static` | A SkillSpector issue at or above HIGH, an issue of unknown severity, a scan that did not run and a partial scan for an undeclared reason. Lower issues are recorded as notes. |
| Effects | `builtin_effect_rules` | An effect outside the engine's vocabulary, a repeated effect, `pure` beside another effect, and a shell block without `spawns_process`. |
| Secrets | `builtin_secret_patterns` | A value shaped like a credential anywhere a reviewer would be sent it: the body, the purpose, the item record and every cited source file. The patterns are the repository's secret patterns plus declared extra shapes. A finding names the place and the pattern number, never the value. |
| Duplicates | `exact_shingle_jaccard` | A byte copy or a word-for-word copy under another identity, and a five-word shingle Jaccard similarity of 0.8 or more. |
| Duplicates | `datasketch_minhash_lsh` | The same, found through a MinHash index for large populations and confirmed with the exact similarity. |

The built-in rules were calibrated against every committed body: all 123 pass
except the two whose licence is unknown, and the largest similarity between two
real bodies stays below the threshold.

## Reviewers

`resources/panel.json` declares every reviewer installation: its engine kind,
exact model, declared family, allowance group, lens, switch and typed settings.
A family is declared, never inferred from a model name. The panel asks
installations in declared order, a new family first, and skips every
installation of the item's producer family.

| Installation | Family | Engine | Notes |
|---|---|---|---|
| `ollama.deepseek-v4-pro` | deepseek | model_gateway | Model `deepseek-v4-pro:0813`. |
| `ollama.qwen3.5-397b` | alibaba | model_gateway | Model `qwen3.5:397b`. |
| `codex.gpt-6-sol` | openai | command_line | Protocol `codex_exec_session`: the model is pinned with `-m {model}` and read back from the command line's own session record for the thread the events name (every turn context must name the pinned model). `--ephemeral`, which suppresses that record, is refused for this protocol. The older `codex_exec_jsonl` protocol reports no model and stays refused. On 24 September 2026 the subscription's usage limit ran until 29 September, so the readback has offline checks only. |
| `ollama.minimax-m3` | minimax | model_gateway | |
| `ollama.kimi-k2.6` | moonshot | model_gateway | The admissible model of the Kimi family. |
| `ollama.glm-5.3` | zhipu | model_gateway | Writes its reasoning into the answer text, so it declares the answer format `json_after_reasoning` and a 32,768 token allocation. |
| `ollama.mistral-large-3` | mistral | model_gateway | Model `mistral-large-3:675b`. |
| `ollama.gpt-oss-120b` | openai | model_gateway | Model `gpt-oss:120b`. |
| `ollama.kimi-k3` | moonshot | model_gateway | Disabled. The repository's model policy refuses this model on every route. |
| `claude_code.bare` | anthropic | command_line | Disabled. `claude -p --bare` reads only `ANTHROPIC_API_KEY`, never the login of an interactive session; on this machine that variable is not set, and one probe recorded `authentication_unavailable` with no model call. |
| `claude_code.subscription` | anthropic | command_line | `claude -p --safe-mode` with no tools and no session persistence: every customization (instruction files, skills, plugins, hooks, protocol servers) is off while the owner's subscription login still works. The model is pinned with `--model {model}`, and the result's model usage must name only that model. The owner capped it at 150 review calls in total on 24 September 2026, because it shares the subscription with the engineering sessions; the command's `--quota-group-ceiling claude_subscription=N` holds each command to what remains. Never asked about an item Claude Code wrote. |
| `tactical.gemma-4-coding-abliterated` | google | provider_binding | The owner's Tactical Engineering endpoint through the committed provider binding `tools/resources/original-native-generation-providers/tactical-gemma-4-coding-abliterated.json`, which declares the review purpose `decide_label` beside `generation`. The TLS trust contract, family evidence and measured capacity are the binding's; the credential reference `tactical-model-generation` is resolved inside the review process only. The model writes reasoning before its verdict, so the installation declares `json_after_reasoning` and a 16,384 token allocation within the measured 65,536. Never asked about an item the same endpoint produced, because both are the google family. |

## The provider_binding engine

A `provider_binding` installation names a committed provider binding by path and
exact digest. The engine validates it with the candidate generator's own loader
at the checkout's current commit: the binding bytes, trust anchor, family
evidence, capacity record and panel vocabulary must be committed unchanged, the
binding's model and family must be the installation's, and the binding must
declare the installation's purpose. Only then is the operator credential
resolved, inside the review process, by the resolver the command supplies when
model calls are authorized. A command without model authority resolves no
credential, and the engine is then unavailable with
`authentication_unavailable`. Every call goes through `core.model_gateway` with
one route, no failover and a typed output allocation within the binding's
measured capacity; the answering model is the one the endpoint reports.

## What one reviewer is sent

Each reviewer receives, in one prompt: the shared instructions of
`resources/REVIEWER-INSTRUCTIONS.md` with the section for its own lens, the
candidate's identity, body digest and size, the declared producer, the kind of
body the item declares, the written criteria for that kind, the item record,
every cited source file at its pinned revision and the exact body text.

The review sheet judges its two kinds of body by different criteria. A body
that restates its cited file must say what that file says or does. A body of
general practice is judged as practice, and only its one sentence about the
cited file must be true of that file. `resources/criteria.json` therefore
declares each kind with the sheet's own words for it, and names, for each
criterion, the kinds it applies to. A reviewer is told the kind of the body in
front of it and receives only the criteria for that kind, and an answer that
cites a criterion of the other kind is not counted. The first pilot attempt
sent every criterion for every body: 26 of its 34 rejections of bodies of
general practice cited, among their reasons, the criterion for the other kind.
None rested on it alone, and correcting the request changed no decision on a
real item; the comparison of the two attempts is in the pilot evidence folder.

The prompt digest names both parts of the prompt, and the ledger reuses a
verdict only for the same installation, the same exact request and the same
exact prompt. A changed prompt is a new review, and the ledger keeps both.

## Batched review

With `--batch-size INSTALLATION=N` one call asks that reviewer about up to N
items (at most 12) of one content profile. The system part is the reviewer's
instructions and lens followed by the batch answer contract in
[`resources/BATCH-ANSWER.md`](resources/BATCH-ANSWER.md). The request part holds
each item's own material exactly as its single prompt holds it, inside a block
fenced by markers built from that item's digest, and ends with the ordered list
of identities and digests the answer must copy.

The answer is one JSON object with exactly the key `verdicts`: exactly one
verdict per item, in order, each with the item's `identity` and
`body_sha256` and the single answer's fields, read by the single answer's
rules. A verdict that names another item or other bytes, or breaks a rule,
costs only its own item, which moves to the next reviewer alone. A list of
another length counts for no item. Items are still chosen reviewer by reviewer
in the same order as one at a time, so the approval rule, the family exclusion
and the quorum are unchanged.

Each item's verdict is keyed by a member digest that names the batch system part
and that item's own material, never its companions, so a later command reuses
it whichever items share the request. A batched verdict never reuses a
single-item verdict or the other way round. The ledger writes one batch dispatch
row naming every member's key before the call, and one batch call row with the
call's usage once and one member row per item with its own outcome.
Calibration runs in the same mode as the command, so a reviewer is measured
exactly as it will be asked; the engines and the batch contract are recorded in
[the September 24 review engines record](../../docs/verification/REVIEW-ENGINES-AND-BATCHING-2026-09-24.md).
The dated review record does not yet read batch calls, so `--record` is refused
with a batch size above one; the ledger holds every batch call and verdict.

## Calibration

With `--calibrate`, every eligible reviewer is first asked about every item of
the content profile's calibration set. Starter bodies use
`resources/calibration-set.json`: real bodies with one planted defect that a
written criterion names, and one body an earlier independent review approved,
unchanged. A reviewer that approves a known-wrong item, or gives no valid
verdict on any control, or that the calibration never reached, is not asked about real
candidates in the same command, and the record says why. This includes reviewers
skipped for the control producer's family, disabled reviewers and unavailable
engines. A rejection of the expected-approve item is recorded as a label refusal;
it is not an empirical false-refusal measurement without full control eligibility
evidence. The calibration measures known
defect classes on a small fixed set; it does not estimate a reviewer's error
rate on real candidates.

Native packages use `candidate_native_review_calibration_set/v1` and typed
native control items that bind the entire package digest. Their expected
decisions and defect explanations stay outside reviewer prompts. The native
set includes a benign package and separate correctness, output-contract,
declared-effect and source-claim controls. Calls, invalid answers and unknown
usage use the existing ledger. An excluded calibration reviewer cannot supply
a candidate decision accepted by the export reader. The reader reconstructs
eligibility from trusted control requests, exact calls and complete typed
verdicts, including the applicable criteria. Removing or changing the status
or exclusion lists does not change that reconstruction. Custom control sets
need separately supplied host-selected `CalibrationInputs`; the default reader
trusts only the shipped set digests, never labels supplied by a reviewer/export.

The current native benign control has algorithm and contract checks but lacks
the applicable native-loading evidence needed for universal admission. Its
expected-approve label is provisional. The real native calibration pilot stays
on hold until that evidence or a separately approved control scope exists;
the admission criterion is unchanged.

## Budget, pauses and the cursor

One declared ceiling of calls and tokens covers the whole command. Each call
reserves its estimated input, its output allocation and any declared command
line overhead before it is dispatched, and is settled with the usage the
provider or command line reported. Unknown usage stays unknown in the record
and is charged at its reservation. A rate limit pauses for the wait the provider
asked for, or a doubling wait, never longer than the declared longest pause and
never beyond the declared total, then retries up to the declared number of
times. A spent allowance stops every installation that shares it for the rest
of the command. A refused login, a model the provider does not know, a route
the model policy refuses and a missing engine are failures that do not change
within one run: the installation that reports one is asked no more in that
run, and the record names it with the reason `unusable_during_run:` and the
failure. The next reviewer of a family not yet heard takes its place.

A command may also declare `--quota-group-ceiling GROUP=N`, which stops a quota
group after N calls in the command (calibration included) while other groups
continue, and `--stop-after-repeated-failures N`, which stops asking an
installation that failed the same way, with the same outcome and code, N calls
in a row. A rate limit, which is paused and retried, and a spent allowance never
count toward that limit. `--exclude-installation ID=REASON` keeps an
installation out of the command with its written reason, for example an
allowance known to be spent.

`--collect-below-quorum REASON` is for a family that is out of reach for a
known time. Without it the panel spends no call on an item whose reachable
families cannot reach the quorum. With it, each reachable family is asked once
for each item; the approval rule is unchanged, so such an item ends rejected
or incomplete, never approved, and its verdicts wait in the ledger. A later
command with the missing family asks only that family.

The ledger is the resumable cursor. A dispatch row is synced to disk before a
call and a call row after it. A later command with the same ledger reuses every
verdict already given for the same installation, the same exact request and
the same exact prompt, and never repeats a call that was dispatched and not
completed. Such a call's outcome and usage are unknown, and the dated record
lists it under `interrupted_dispatches`. A call is named by its run identity and
its sequence number, so every command on one ledger needs a new run identity:
the ledger refuses a run identity it already holds, and refuses a ledger file
that holds one twice. A reused identity would give a new call the name of an
earlier dispatch that never completed, and that dispatch would then read as
completed.

## Records

| Record | Where | Purpose |
|---|---|---|
| `candidate_review_panel/v1` with `candidate_review_panel_policy/v1` and `candidate_reviewer_installation/v1` | `resources/panel.json` | The policy, families, pre-check engine settings and reviewer installations. |
| `candidate_review_criteria/v2` | `resources/criteria.json` | The kinds of body and the written criteria, each a quote of the catalogue's `REVIEW.md` matched with whitespace collapsed, and the kinds each criterion applies to. Version one had no kinds and sent every criterion for every body; the current reader refuses version one. |
| `candidate_producer_declaration/v1` | `resources/producer-starter-catalogue.json` | Who produced the items, with a quote of the evidence. |
| `candidate_review_calibration_set/v1` | `resources/calibration-set.json` | Known-wrong and known-good items. |
| `candidate_review_request/v1`, `candidate_native_package_review_request/v1`, `candidate_precheck_result/v1`, `candidate_review_verdict/v2` | edges | The explicitly typed body or native-package subject, each pre-check result, and the exact model verdict. |
| `candidate_review_run/v2`, `candidate_review_run_end/v2`, `candidate_review_dispatch/v2`, `candidate_review_call/v2` | the ledger | Every run, dispatch and call, including requested and reported model identity, subject type, usage, charge, pause and outcome. |
| `candidate_review_batch_dispatch/v1`, `candidate_review_batch_call/v1` | the ledger | One call about several items: the dispatch names every member's review key before the call; the call row holds the requested and reported model, the usage once, and one member row per item with its own outcome, code and decision. A verdict row names its batch call and must agree with its member row. |
| `starter_catalogue_panel_review/v3` | dated review artifact | The complete typed panel configuration and exact subjects bind both content profiles. Calibration eligibility is reconstructed from trusted requests and typed verdict/call evidence; version two exports are historical and refused. |
| `candidate_review_calibration_result/v2` | calibration section of the dated artifact | Complete verdict records, calls, all installation outcomes, and recomputable exclusions. Missing any control verdict makes an installation incomplete. |

In active version-two records, `model` is the requested installation model
and `reported_model` is the observed answering identity. The fixed panel,
ledger and export reader require a matching identity before a verdict counts.
Command-line availability reports the CLI version and leaves model version
unknown. Claude's reported model set must contain only the requested model.
A no-model result does not imply zero tokens: absent usage remains unknown,
partial counts are preserved and only explicitly reported zero is zero.
Historical version-one worker records keep their bytes and cannot be resumed
or admitted through the current reader. They are not retroactively qualified.

Every reader refuses another version, an unknown field and a missing field.
Every text written passes through the secret patterns first. The dated record
is written as ASCII JSON, and any retired word inside reviewer text has its
first letter written as a JSON escape, so the record decodes to exactly the
reviewers' words while the repository's scans find no retired word.

## Running it

Check the pre-checks without any model call:

```bash
PYTHONPATH=src:tools python tools/review_catalogue_candidates.py \
  --catalogue examples/29_intelligence_service/starter-catalogue \
  --ledger RUN_FOLDER/ledger.jsonl --count 30 --seed SEED \
  --call-ceiling 0 --token-ceiling 0
```

Review with real reviewers, calibrated first, and write the dated record:

```bash
PYTHONPATH=src:tools python tools/review_catalogue_candidates.py \
  --catalogue examples/29_intelligence_service/starter-catalogue \
  --ledger RUN_FOLDER/ledger.jsonl --count 30 --seed SEED \
  --call-ceiling 220 --token-ceiling 3000000 --calibrate --item-concurrency 3 \
  --program skillspector_static=PATH --program agent_skills_reference=PATH \
  --record examples/29_intelligence_service/starter-catalogue/reviews-panel-DATE.json \
  --recorded-at DATE --authorize-model-calls
```

To write the record again from the verdicts a ledger already holds, run the
same command with the same ledger, `--call-ceiling 0 --token-ceiling 0` and
`--replace-record`. The provider listing is read again, which is not a model
call, so the gateway reviewers are available; every stored verdict for the same
installation, request and prompt is reused, and a verdict that is missing stays
missing because the ceiling allows no call.

The Ollama Cloud key is read only from the environment variable the provider
declares, `OLLAMA_API_KEY`, and only to be sent in the request header. A
gateway reviewer is unavailable when that variable is not set, so no other
place a key could be read from is ever consulted. Each command line reads its
own login. Nothing in the panel prints, logs or stores a credential, and every
text it writes passes through the secret patterns first.

The pilot was run with the two adapted command engines from their own Python
3.12 environment, and with the MinHash engine made available to the shared
interpreter by a folder that holds only the `datasketch` package and its
metadata, placed on `PYTHONPATH` after `src` and `tools`. Its own numerical
libraries are the shared interpreter's, at the same versions. Nothing was
installed into the shared interpreter.

## The first pilot

On 22 September 2026 the panel reviewed 30 of the 74 starter catalogue items
that had no verdict. Every one is a body of general practice that Claude Code
wrote. The full account, both attempts and their ledgers are in the
[pilot evidence folder](../../artifacts/candidate-review-pilot-2026-09-22/README.md).

| Measure | Result |
|---|---|
| Items refused by the pre-checks | 0 of 30 |
| Items approved | 0 of 30 |
| Items rejected | 30 of 30 |
| Items with at least one approval beside the rejections | 14 |
| Reviewers asked about every item | `qwen3.5:397b`, `gpt-6-sol` through `codex-cli 0.155.1`, `minimax-m3`; `kimi-k2.6` once in place of an invalid answer |
| Excluded by calibration | `deepseek-v4-pro:0813`, which approved a planted defect |
| Calls | 91 on items and 32 calibration, all with usage reported; 2 answers were not valid verdicts |
| Tokens reported | 1,154,280 input and 106,936 output for the whole command |
| Throughput | 234.5 items an hour in the review run, three items at a time; 164 an hour with calibration |

Most rejections name a promise the steps do not keep, a sentence about the
cited file that overstates it, or a declared effect list that does not match
the steps. Those reasons are the repair list for the next version of each
body; a repaired body is new bytes and needs a new review.

## Merging the verdicts

The dated record holds rows in the row shape of `reviews.json`, and a strict
reader. It cannot be copied into `reviews.json` as it is, for two reasons, and
the merge is the lead engineer's step through the carry and manifest tools:

- `starter_catalogue_independent_review/v2` names one fixed set of reviewers,
  and the manifest builder requires every judged row to carry a decision from
  each of them. A panel row is decided by the reviewers its families called
  for, which differ from item to item.
- The carry tool proves an approval against the bytes its reviewers read, and
  reads one anchor revision for the whole record. The panel read bodies
  anchored at revision `f29bddc`; the rows of 21 September were read at
  `381efec`, and `main` has since anchored the catalogue again.

The change that makes the merge mechanical is a version three of the review
record in which each judged row names its own reviewers (with engine kind,
family, model, model version, route or command and engine version, as the panel
record does), the rule that decided it (the unanimous rule of 21 September, or
the family quorum rule of the panel), and where the bytes its reviewers read
are kept (revision, folder and anchor revision). The manifest builder and the
carry tool then read the rule and the bytes per row. This pilot approved
nothing, so nothing waits to be served; its 30 rejections stand in the dated
record with their reasons.

## Library decisions

| Library | Licence | Decision | Reason |
|---|---|---|---|
| datasketch 2.0.0 | MIT (licence file and package metadata read from the installed package) | Adopted as an optional engine | MinHash with locality-sensitive hashing is the standard way to find near duplicates without comparing every pair. It needs numpy and scipy, so it is optional; the exact engine decides populations up to 5,000 bodies. |
| skills-ref 0.1.1 (Agent Skills reference validator, command `agentskills`) | Apache-2.0 (licence file and package metadata) | Adapted as a command engine | It validates the rendered skill file exactly as the specification owner does. It needs Python 3.11 or later and the shared interpreter is 3.10, so it runs from its own environment. |
| NVIDIA SkillSpector 2.11.2, installed from its GitHub repository at commit `844ac30f47ca4cc6ff0d1481ac88945eb0eff039` | Apache-2.0 (licence file and package metadata) | Adapted as a command engine in static mode | 71 patterns across 17 categories in one scan, JSON output. It needs Python 3.12 or later, takes several seconds per item, and its MEDIUM skill enumeration rule fires on a body's own provenance citation, so it refuses at HIGH and records lower issues as notes. |
| Snyk agent-scan | Not adopted | Rejected as a default engine | It sends material to an outside analysis service and needs an account token (recorded in the harness and library plan). |

## Checks

| Check file | What it proves |
|---|---|
| `tools/test_candidate_review_configuration.py` | A weakened policy, an undeclared family, a record of another version, a criterion that is not a quote, a kind of body that is not a quote or not declared, and a producer claim without evidence are refused; each kind of body receives only its own grounding criterion. |
| `tools/test_candidate_review_prechecks.py` | Every known-wrong body is refused by its own kind, a secret-shaped value in a cited source or the item record is refused, every real body passes except the two unknown licences, a kind is never skipped, each kind needs its engine, and the catalogue reader refuses a path outside its folder or through a hidden part and a cited source that is not the pinned bytes at the anchor revision. |
| `tools/test_candidate_review_engines.py` | The gateway engine keeps provider usage exactly, honours the model policy and is unavailable without its credential variable, and the model listing reads the key only from the environment; the command line engine reads each protocol exactly, sends the prompt on standard input only, and keeps failures apart. |
| `tools/test_candidate_review_panel.py` | The approval rule, the family exclusion in both the selection and the decision, pre-checks before any call, the kind of body and its criteria in the prompt, answer validation, ceilings, pauses, spent allowances, failures that last a run, the cursor bound to the exact prompt, and secret redaction. |
| `tools/test_candidate_review_calibration.py` | The committed calibration set, each item's criterion applying to its kind, and the exclusion of a reviewer that approves a known-wrong item or was never measured. |
| `tools/test_candidate_review_record.py` | The strict reader of the dated record, interrupted dispatches, criteria applied per row, each reviewer's family and installation bound to its calls, each row's pre-checks and licence, its serialization, and the committed pilot record against the bodies committed with it, read from the repository history. |
| `tools/test_candidate_review_batching.py` | Batch answers bound per item, batch prompts whose members keep their keys, batched runs under the unchanged rule, the cursor across batches, per-group ceilings, the stop after repeated failures, collection below the quorum, the batch ledger rows and the command's new options. |
| `tools/test_candidate_review_binding_engine.py` | The provider_binding engine through the real adapter and gateway with a fixture transport: the credential reaches only the request header, and a binding that is not committed, names another model or family, lacks the review purpose or cannot hold the allocation is refused before the credential is read. |

Each file holds mutant controls: with one guard replaced, its known-wrong case
passes, which proves the case is held by that guard. The pilot evidence folder
also holds `source_mutants.py`, which removes each guard from the source itself
in a scratch copy, and its report of which checks then fail.
