# Independent review panel for harness intelligence candidates

Kind: component guide for roadmap package LS2. It describes current behavior.
The first real pilot is recorded in
[`reviews-panel-2026-09-22.json`](../../examples/29_intelligence_service/starter-catalogue/reviews-panel-2026-09-22.json),
and both of its attempts, their ledgers and their comparison are kept in
[`artifacts/candidate-review-pilot-2026-09-22`](../../artifacts/candidate-review-pilot-2026-09-22/README.md).

## What the panel does

The panel decides whether independent reviewers approve the exact bytes of one
candidate item for the harness intelligence library. It runs six deterministic
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
│   └── fixture: scripted reviewers for offline checks, never in a real record
└── Envelope: panel.ReviewPanel
    ├── pre-checks, eligibility, family exclusion and the quorum rule
    ├── budget, rate limit pauses and spent allowances
    └── the ledger: dispatch, call and verdict rows, the resumable cursor
```

Every kind of pre-check must be decided for every item. A kind whose engines
are all unavailable, or an engine that fails, refuses the item. Every available
engine of a kind runs, so the record shows each result.

## Pre-checks

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
| `codex.gpt-6-sol` | openai | command_line | `codex exec`, read-only sandbox, its tools switched off, an empty working folder. |
| `ollama.minimax-m3` | minimax | model_gateway | |
| `ollama.kimi-k2.6` | moonshot | model_gateway | The admissible model of the Kimi family. |
| `ollama.glm-5.3` | zhipu | model_gateway | Writes its reasoning into the answer text, so it declares the answer format `json_after_reasoning` and a 32,768 token allocation. |
| `ollama.mistral-large-3` | mistral | model_gateway | Model `mistral-large-3:675b`. |
| `ollama.gpt-oss-120b` | openai | model_gateway | Model `gpt-oss:120b`. |
| `ollama.kimi-k3` | moonshot | model_gateway | Disabled. The repository's model policy refuses this model on every route. |
| `claude_code.bare` | anthropic | command_line | `claude -p --bare` with no tools. Never asked about an item Claude Code wrote. In bare mode the command line reads only `ANTHROPIC_API_KEY`, never the login of an interactive session; on the pilot machine that variable is not set, and one probe recorded `authentication_unavailable` with no model call. |

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

## Calibration

With `--calibrate`, every eligible reviewer is first asked about every item of
`resources/calibration-set.json`: real bodies with one planted defect that a
written criterion names, and one body an earlier independent review approved,
unchanged. A reviewer that approves a known-wrong item, or gives no valid
verdict on one, or that the calibration never reached, is not asked about real
candidates in the same command, and the record says why. A rejection of the
known-good item is recorded as a false refusal. The calibration measures known
defect classes on a small fixed set; it does not estimate a reviewer's error
rate on real candidates.

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
| `candidate_review_request/v1`, `candidate_precheck_result/v1`, `candidate_review_verdict/v1` | edges | What one reviewer is shown, what each pre-check found, what one reviewer decided. |
| `candidate_review_run/v1`, `candidate_review_run_end/v1`, `candidate_review_dispatch/v1`, `candidate_review_call/v1` | the ledger | Every run, every dispatch and every call with its model, version, route or command, usage, charge, pause and outcome. |
| `starter_catalogue_panel_review/v1` | beside `reviews.json` | The dated review record, read back by a strict reader before it is written. Each row names its kind of body and the criteria applied; each reviewer is named with the model and engine version its calls answered with; every path is relative to the repository root; the record lists every call and every interrupted dispatch. |

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
| `tools/test_candidate_review_prechecks.py` | Every known-wrong body is refused by its own kind, a secret-shaped value in a cited source or the item record is refused, every real body passes except the two unknown licences, a kind is never skipped, and each kind needs its engine. |
| `tools/test_candidate_review_engines.py` | The gateway engine keeps provider usage exactly, honours the model policy and is unavailable without its credential variable, and the model listing reads the key only from the environment; the command line engine reads each protocol exactly, sends the prompt on standard input only, and keeps failures apart. |
| `tools/test_candidate_review_panel.py` | The approval rule, the family exclusion in both the selection and the decision, pre-checks before any call, the kind of body and its criteria in the prompt, answer validation, ceilings, pauses, spent allowances, failures that last a run, the cursor bound to the exact prompt, and secret redaction. |
| `tools/test_candidate_review_calibration.py` | The committed calibration set, each item's criterion applying to its kind, and the exclusion of a reviewer that approves a known-wrong item or was never measured. |
| `tools/test_candidate_review_record.py` | The strict reader of the dated record, interrupted dispatches, criteria applied per row, its serialization, and the committed pilot record against the bodies in the tree. |

Each file holds mutant controls: with one guard replaced, its known-wrong case
passes, which proves the case is held by that guard. The pilot evidence folder
also holds `source_mutants.py`, which removes each guard from the source itself
in a scratch copy, and its report of which checks then fail.
