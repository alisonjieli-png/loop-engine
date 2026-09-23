# Overnight batch with a cheap model, with and without Baltor material: frozen design

Kind: study design, frozen and committed on September 23, 2026, before the
first counted model call. The machine-readable form is
[design.json](design.json). The digests of every frozen file are in
[design-freeze.json](design-freeze.json). Roadmap steps: S-6.37, D-07 and
D-08.

This is a measured demonstration of two product claims. It is not a full
Loop Engine case study under the [case-study admission rule](../README.md):
no Starting Practitioner, Solution Canvas or Run History is involved. Each
step is one fresh standard harness process with one model.

## 1. Question

Can a cheap model, reached through an endpoint and a key that the customer
supplies, work through a queue of checkable data cleanup steps with nobody
watching, one fresh harness process for each step? Does an approved Baltor
item, placed in each step, raise the independently checked result on a
population where the model without the item fails part of the work?

A negative or mixed answer is a valid result and is reported the same way.

The owner, September 23, 2026: "Baltor is not a tool to run models, people
are expected to bring their own API key, or auth, or API + auth to be able to
access whatever system they have Ollama + local model at 127.0.0.1, Ollama
cloud, another system in their house on a local IP running local AI endpoint,
etc. We can still prove out overnight solving using cheap/local models using
Ollama Cloud and something like Gemma 4."

## 2. What this study builds on

The [data cleanup study](../data-cleanup-with-and-without-baltor/README.md)
of September 22 and 23 measured the same kind of step and found no benefit.
Its cloud models already scored between 0.914 and 1.000 without material, the
approved phone item made the cheap model clearly worse, and a local 7B model
could not make structured tool calls. Its report asked for a harder
population, where the arm without material does not score near 1.0, and a
model that fails without help. This study keeps its method, its isolation
recipe, its counting proxy and its scorer, and changes four things:

- The model is `gemma4:31b` on Ollama Cloud, reached directly with the key in
  the environment. It is the only Gemma 4 model the provider lists.
- The population is harder: 311 rows in six families instead of 143 rows in
  four. Every row of the earlier population is kept except one whose truth
  its report disputed.
- The runner works through the plan unattended, survives a crash and
  resumes. A declared drill kills it once in the middle of a step.
- The exact approved item bytes are copied into this study. The earlier
  study froze the digests of the catalogue files; the catalogue re-anchored
  every body on September 23, and that study's own `freeze.py --check` has
  failed since.

## 3. Prior art checked before building

| Source | What it is | Decision |
|---|---|---|
| [SkillsBench](https://arxiv.org/abs/2602.12670) | Paired runs with and without skills, three trials, deterministic verifiers, the same model and harness on each side. | Method adopted again, as in the data cleanup study. |
| The data cleanup study in this repository | Frozen design, counting proxy, fresh Pi process per step, deterministic scorer. | Reused and extended: files are copied with their origin named in each file, so that study's frozen bytes stay untouched. |
| `tools/overnight_queue.py` in this repository | Runs a queue of `loop-engine solve` tasks overnight: a wall clock per task with SIGTERM before SIGKILL, resume by skipping finished tasks, a queue-wide call ceiling, never blocking. | Its rules are adopted: stop a step politely before killing it, skip finished steps, count against one ceiling, never ask for input. Its code is not used, because each of its tasks is a full engine solve, while each step here is one customer harness process. |
| `src/loop_engine/core/night_budget.py` | Grants each step a share of the remaining night instead of a fixed timeout. | Not used. A fixed step timeout is simpler to freeze, and the batch is expected to finish well inside a night. |
| North American Numbering Plan, Ofcom and ACMA ranges for fiction, from [the fictitious telephone number article](https://en.wikipedia.org/wiki/Fictitious_telephone_number) | 555-0100 to 555-0199; the Ofcom drama ranges such as 020 7946 0xxx, 0113 496 0xxx and 07700 900xxx; the Australian range (02) 5550 xxxx. | Every telephone number in the population is in one of these ranges, and a test checks it. |
| RFC 2606 and RFC 5737 | Reserved example domain names and the 192.0.2.0/24 documentation network. | Every web address in the population uses them. |

## 4. Model and why

The provider's model list, read with the key in the environment on
September 23, 2026, offers one Gemma 4 model: `gemma4:31b`, 32.7 billion
parameters, BF16, a context of 262,144 tokens, with tool calling. Its
thinking setting defaults to off, and the harness sends none. The metadata is
in [probe/ollama-model-metadata.json](probe/ollama-model-metadata.json).

Before the freeze, one short probe checked that the model makes structured
tool calls through Pi. The design fixed the order of candidates in advance:
`gemma4:31b`, then `nemotron-3-nano:30b`, then `gpt-oss:20b`, stopping at the
first that passes. `gemma4:31b` passed every check in 3 requests and 3.6
seconds: it called `bash`, then `write`, wrote `42` to the answer file,
replied DONE and reported usage for every request. The record is
[probe/probe-gemma4-31b-a1.json](probe/probe-gemma4-31b-a1.json). No other
candidate was probed.

The model runs on Ollama Cloud. Nothing in this study is evidence about a
model running on local hardware.

## 5. Population and selection rule

The population is synthetic. A seeded generator,
[generate_population.py](population/generate_population.py), writes every row
from a clean truth and a named case type. Seed: 20260923. It uses only the
Python standard library and writes the same bytes on every run (`--check`).
People, companies, email addresses and street numbers are invented. Street,
city and postal code formats follow real conventions.

| Family | Rows | What the step must do | Rows to hold or review |
|---|---|---|---|
| phones | 62 | E.164 form with default country code 1, extensions kept | 13 held numbers, and 1 row where holding and repairing are both accepted |
| emails | 57 | lower case, unwrap and repair only when the intended address is certain | 15 held values |
| addresses | 48 | split one line into seven parts, copied exactly as written | 5 rows to flag for review |
| duplicates | 59 records | list every pair of rows that are the same company at the same location | 30 true duplicate pairs, 5 ambiguous pairs to mark for review, 11 hard negative pairs that must not be merged |
| names | 53 | restore standard capitalisation to names typed in one case | 6 names to hold, 9 values to keep exactly |
| websites | 32 | one standard form: small letters in scheme and host, no default port, no final slash | 6 values to hold |

The phones, emails and duplicates prompts are the same bytes as in the data
cleanup study. The addresses prompt changes one phrase, "not a postal
address" to "not one postal address", to cover a new row with two
addresses. Names and websites are new families. Each prompt states the
output form and every decision policy the scorer checks, such as when to
hold a value for review. Some rows also need knowledge of a public convention
that the prompt implies but does not spell out: the United Kingdom trunk
prefix inside an E.164 number, the 00 and 011 exit prefixes, North American
area codes that cannot exist, the Canadian form that writes a unit number
before the civic number, or name particles such as `van der` and `de la`,
whose capitalisation differs from one family to another.
Knowing those conventions is part of the expertise that material could
supply. The item adds method and domain knowledge, not new requirements.

Hard rows were chosen from real conventions before any counted call. They
include cases where an item's method gives the wrong answer, so they test for
harm as well as help.

To make that visible without relying on a reading of the item text, the
repository operation that each item was compiled from was run on every row
with no model, under the thresholds of the approved item
`apply_hold_or_escalate_each_correction`
([item_reference.py](runner/item_reference.py),
[item-reference.json](population/item-reference.json)). It labels every row as
one where the item's own method gives the truth or gives a different answer.

| Family | Item method alone, primary metric | Rows where the item method gives the truth |
|---|---|---|
| phones | 0.7097 | 44 of 62 |
| emails | 0.6140 | 35 of 57 |
| addresses | 0.5625 | 27 of 48 |
| duplicates | 0.5366 pair F1 | not labelled by row |
| names | 0.6415 | 34 of 53 |
| websites | 0.8438 | 27 of 32 |

This is a reference line and a coverage label, not an arm and not a result of
Baltor material. The items are Markdown methods; the code behind them is not
served with them.

## 6. Material and its selection rule

For each family, the material is the approved starter catalogue item that the
catalogue's own search fixtures name as the expected answer for a query that
describes the step. The fixtures were written on or before September 21,
2026. The exact approved bytes were copied into [material/](material/) at
revision `243a8811` with their approval rows in
[material/approvals.json](material/approvals.json). All seven approvals are
carried approvals: three independent reviewers approved each item at an
earlier digest, and the catalogue carried the approval to the current digest
after proving that only the last line, which names a revision, changed.

| Family | Query in `search-queries.json` | Item | Body SHA-256 |
|---|---|---|---|
| phones | format phone numbers with country code | `normalize_phone_numbers` | `8f0ab269db267078c2f9b3f4671d8785a9e8a3dcce0fbdac578f6b2dacf255ef` |
| emails | fix typos in email domains like gmail.con | `normalize_and_recover_email_addresses` | `42cd00ff5e56371e874274859786143e8804bc1830cc64c6bcf8fb98257b5253` |
| addresses | parse street address into parts | `split_address_lines_into_components` | `27cc9e736c19b9599d5430c04ff0ca3f0e26cd8ea11042ab505a2f3416f186b1` |
| duplicates | dedupe my contacts csv | `find_duplicate_records_with_blocking_keys` | `175d693f77e844140c4431ab1b19c51e0a560dbf90baefdb81575653905644e5` |
| duplicates | fuzzy match two company records | `score_duplicate_pairs_by_weakest_signal` | `b983cf3e13d5ce17198a33d3c1b1d9558c9031392ec46622aa19eeb35d4bfc8e` |
| names | names are in ALL CAPS fix the casing | `restore_capitalisation_of_names` | `502eee3c685bbd6d589813feaa719e56ddae12f26e875f23fb6f842a189ae50e` |
| websites | clean URLs lowercase host | `normalize_website_addresses` | `327711dbf31097556cd0057770288bd4ef4d1e528a93da2974fbaf9eb2b3e0b6` |

The runner refuses an item whose bytes differ from its frozen approval.

## 7. Arms

Both arms use the same model, harness, prompt, tools, permissions, step cap
and timeout. Only the material differs.

| Arm | Model | Material |
|---|---|---|
| `gemma-none` | `gemma4:31b` on Ollama Cloud | none |
| `gemma-agents` | `gemma4:31b` on Ollama Cloud | the item bytes in `AGENTS.md` in the step folder |

A capture check with no model behind the endpoint confirmed, before the
freeze, that the item text reaches the system prompt of the material arm,
that it is absent from the arm without material, and that no text from the
owner's own instruction files appears
([probe/capture-report.json](probe/capture-report.json)).

## 8. Harness and isolation

Pi 0.73.1 (`@mariozechner/pi-coding-agent`) on Node v22.22.1, with its
default tools read, bash, edit and write. Every attempt gets a new step
folder: an empty home folder, a new `PI_CODING_AGENT_DIR` holding only
`models.json` and `settings.json`, the working folder as its own git root
under parents with no instruction file, an environment built from nothing
with a fixed path, and every other network proxy pointed at a closed local
port. Automatic retry and compaction are off. Python 3.14 with its standard
library is the only interpreter in the step.

The step folders are not a sandbox. The model can read any file the
workstation user can read. After the run, every tool call is scanned for
paths outside the step folder and for any read of a truth file, and the
report states what was found.

## 9. The unattended batch

```text
runner/overnight.sh (supervisor)
└── runner/run_trials.py main (runner)
    ├── on start: close every lease without a step record
    │   ├── stop what is left of that harness and observe it end
    │   └── write an interrupted record with every request it used
    ├── for each step of the frozen plan, in order
    │   ├── skip a step that already has a counted record
    │   ├── reserve a full step cap under the ceiling, or stop
    │   ├── write a lease, build a fresh step folder, start one Pi process
    │   ├── count every request in the proxy ledger before it is sent
    │   ├── score output.csv with the independent scorer
    │   └── write one record, one score and a copy of the output
    └── exit 0 complete, 3 budget, 4 outage, 5 missing key
```

- The plan is three rounds. Each round holds every family and arm once,
  shuffled with seeds 20260924 to 20260926. If the budget ends early,
  complete rounds stay balanced.
- The supervisor restarts the runner after a crash, after 30 seconds, at most
  five times. It stops on the four exit codes above.
- Interruption drill: once, the runner kills itself with SIGKILL during the
  fourth step, `r1-addresses-gemma-none`, after that step's first model
  response. No clean-up code runs. The resumed runner must close the step as
  an interrupted attempt and run it again as attempt 2. The drill is
  recorded in `drill-fired.json` in the run folder and copied into the study.
- Provider outage: a step with a rate limit, a provider error or an
  unreachable provider is kept as an excluded attempt and run again after 60,
  120, 300, 600 and then 900 seconds, at most 7,200 seconds in total. Its
  requests still count.

## 10. Budget and counting

- Ceiling: 600 physical model requests for the whole study, counted by
  [meter.py](runner/meter.py), a proxy between Pi and the provider. It writes
  a ledger line before it forwards a request and refuses anything beyond the
  ceiling. The probe before the freeze used 3 of them.
- Step cap: 10 requests. A step that reaches it is stopped and scored as it
  is.
- Worst case: 36 main steps, 2 pilot steps and 1 drill attempt at the cap,
  plus the probe, is 395 requests.
- The key is read from `OLLAMA_API_KEY` when a request is forwarded, sent
  only to the provider and never written to the ledger, a saved body or a
  log.
- Cost: covered by the owner's existing Ollama subscription and not metered
  for each request. No money is spent.

## 11. Scorer, metrics and thresholds

[score_step.py](scorer/score_step.py) reads only `truth.json` and the step's
`output.csv`. It never reads the transcript or the model's claim of success.
Its leniency (column name case, surrounding spaces, Unicode composition, yes
and no spellings) is written in its opening text and was fixed before the
first counted call.

| Family | Primary metric | Passes when |
|---|---|---|
| phones, emails, names, websites | record accuracy: value and review flag both right | at least 0.90 and no wrong change to an already correct value |
| addresses | record accuracy: all seven parts and the review flag right | at least 0.90 and no part rewritten away from the input text |
| duplicates | pair F1 over pairs marked `same` | at least 0.90 and no hard negative pair merged |

Known-wrong outputs must fail the scorer: a copied input, an all-empty
output and a shuffled output for every family, an output that marks every
pair as the same company, a generic title case of every name and an output
that writes every whole web address in small letters.

## 12. Claim rules

- A difference between the two arms on one family is clear only when every
  repetition of one arm scores above every repetition of the other on the
  primary metric. With three repetitions each, that has a one-sided exact
  permutation probability of 1 in 20.
- Otherwise the difference is reported as not separated, with means and
  ranges.
- "The material helps" needs a clear difference in favour of the material in
  at least 3 of the 6 families and no clear difference against it. "The
  material hurts" needs the reverse. Clear differences in both directions are
  reported as mixed.
- The population is called hard enough only when the arm without material
  fails part of the work in at least 3 of the 6 families: a mean below 0.95,
  or a step that fails the pass rule.
- Every step counts except a provider outage attempt and an interrupted
  attempt, including crashes, timeouts, cap stops and malformed files.
- The batch is called unattended only when every main step was started by
  the runner with no human input after the supervisor started, and the drill
  was recovered with no human input.
- Every physical request must belong to a probe, pilot or main step record.
- A step whose output failed the scorer is never called finished work.

## 13. Pilot and amendments

The pilot runs two steps before the main plan, `names` without material and
`websites` with material, and is excluded from results. After it, only
harness or recording plumbing may change, as a recorded amendment in
`amendments.json` with its reason and the digests before and after. The
population, prompts, arms, model, material, step cap, metrics, thresholds and
claim rules may not change.

## 14. Limits declared in advance

- The data is synthetic and written by the author of the study, who also
  read the items. Hard rows include cases where an item's method is wrong.
  The coverage labels in section 5 show where.
- One harness, one model and one provider are tested. Three repetitions can
  show only large, consistent differences.
- The model ran in the provider's cloud. Local hardware, local model serving
  and a declared overnight duration are not tested here; they remain roadmap
  step D-07.
- Cloud cost is a subscription and is not metered for each request. Token
  counts are provider-reported.
- The step folders are not a sandbox; see section 8.
