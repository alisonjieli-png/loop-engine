# Data cleanup with and without Baltor material: frozen design

Kind: study design, frozen and committed on September 22, 2026 before the
first model call. The machine-readable form is [design.json](design.json).
The digests of every frozen file are in [design-freeze.json](design-freeze.json).
Roadmap steps: D-07, D-08, S-6.37 and S-6.47.

This is a measured demonstration of one product claim. It is not a full Loop
Engine case study under the [case-study admission rule](../README.md): no
Starting Practitioner, Solution Canvas or Run History is involved. Each step
is one fresh standard harness process with one model.

## 1. Question

Does an approved Baltor item, placed in a fresh harness step, raise a small or
cheap model's independently checked result on a data cleanup step? Does it
close the gap to a larger model that works without the item?

A negative or mixed answer is a valid result and is reported the same way.

## 2. Prior art checked before building

| Source | What it is | Licence | Decision |
|---|---|---|---|
| [SkillsBench](https://arxiv.org/abs/2602.12670), [repository](https://github.com/benchflow-ai/skillsbench) | 87 tasks with deterministic verifiers, run with no skills, curated skills and self-generated skills; three trials for each configuration, task and condition; the same container and model-harness pair for each paired comparison. Reported: curated skills raised the average pass rate from 33.9 to 50.5 percent; self-generated skills scored below the no-skill arm on all three configurations it names. | Apache 2.0 (repository) | Adopted the method: paired arms with the same model, harness and task, material delivered through files the harness already reads, three repetitions, a deterministic verifier. Its tasks were not used, because none maps to the approved catalogue items. |
| [Febrl](https://sourceforge.net/projects/febrl/) and its data sets as described by the [recordlinkage documentation](https://recordlinkage.readthedocs.io/en/latest/ref-datasets.html) | A record linkage package with a generator that writes original records and corrupted duplicates. | Mozilla Public License 1.1 for the software. The documentation page states no licence for the four bundled data sets. | Adapted the idea only: clean originals, named corruptions, known duplicate pairs. No code or data was copied. |
| [DeepMatcher data sets](https://github.com/anhaidgroup/deepmatcher/blob/master/Datasets.md), drawn from the Magellan and Leipzig collections | Entity matching pairs for products, citations, restaurants and companies. | No licence is stated on the page. | Rejected: the licence is unknown, and product and citation pairs do not match the approved items. |
| [Clean Me If You Can](https://github.com/D2IP-TUB/Clean-Me-If-You-Can) | Postal addresses with ground truth and 13 error categories. | MIT for code; Open Database License 1.0 for the ground truth, which is share-alike. | Rejected for this first run: the share-alike terms need their own decision before the data enters this repository, and its task is correcting addresses, not splitting them. It remains the strongest candidate for a later address correction run. |
| [usaddress](https://github.com/datamade/usaddress) | Labelled United States address parsing. | MIT | Not used: its labels are United States only, and the approved item also covers Canada and the United Kingdom. |
| Fictional telephone numbers | 555-0100 to 555-0199 are reserved by the North American Numbering Plan Administrator for fiction; Ofcom reserves drama ranges such as 020 7946 0xxx and 07700 900xxx. Source: [the fictitious telephone number article](https://en.wikipedia.org/wiki/Fictitious_telephone_number), which cites both. The Ofcom page itself refused the fetch with HTTP 403. | Not applicable | Adopted: every telephone number in the population is in a reserved fictional range. |

The web search budget of the preparing session was exhausted during this
check, so the table holds only what was fetched from the linked pages.

## 3. Population and selection rule

The population is synthetic. A seeded generator,
[generate_population.py](population/generate_population.py), writes every
row from a clean truth and a named corruption. Seed: 20260922. It uses only
the Python standard library and writes the same bytes on every run
(`--check`). People, companies, email addresses and street numbers are
invented. Street, city and postal code formats follow real conventions.

| Family | Rows | What the step must do | Rows whose right answer is to hold or review |
|---|---|---|---|
| phones | 38 | Write each number in E.164 form with a declared default country code 1; keep extensions; leave null markers | 7 held numbers, and 1 row where holding and repairing are both accepted |
| emails | 35 | Lower-case, unwrap and repair addresses only when the intended address is certain | 8 held values |
| addresses | 32 | Split one address line into seven parts, copied exactly as written | 4 rows to flag for review |
| duplicates | 38 | List every pair of rows that are the same company at the same location; 18 true duplicate pairs | 4 ambiguous pairs to mark for review; 5 hard negative pairs that must not be merged |

Hard rows were chosen from real conventions, not from the items. Several of
them are cases where the item's own method gives the wrong answer, for example
a United Kingdom number written with `(0)`, a number dialled from North
America with the 011 prefix, an area code starting with 0 and a plus sign
followed by an impossible length. They test for harm as well as help.

The task text in each `prompt.txt` states every decision rule the scorer
checks, so a step without the item has everything it needs to be right. The
item adds method and domain knowledge, not new requirements.

## 4. Material and its selection rule

For each family, the material is the approved starter catalogue item that the
catalogue's own search fixtures, written before this study, name as the
expected answer for a query that describes the step:

| Family | Query in `search-queries.json` | Item | Body SHA-256 |
|---|---|---|---|
| phones | format phone numbers with country code | `normalize_phone_numbers` | `b451b3663599c0971185feb21c5dd74e84145da5fad99580cfdd05067c209b63` |
| emails | fix typos in email domains like gmail.con | `normalize_and_recover_email_addresses` | `64ce838e3053982542820402655c12728f0844e7d70641fef3caa6b7cf732809` |
| addresses | parse street address into parts | `split_address_lines_into_components` | `1c97907b8c86d67cd059d9c63efb77cce3f54acb86de3c7480ebbc535042a2b7` |
| duplicates | dedupe my contacts csv | `find_duplicate_records_with_blocking_keys` | `80645d9eba97e1d4c27d1e5eefc4c30980dcae52069223e502fc40f0945ae6fa` |
| duplicates | fuzzy match two company records | `score_duplicate_pairs_by_weakest_signal` | `4278146c5996b8774d2a7fceec1429818e09f81daae4d4874f3309bb015ce299` |

The runner refuses an item unless `reviews.json` records it as approved and
its bytes match the reviewed digest.

## 5. Arms

All arms use the same harness, prompt, tools, permissions, step cap and
timeout. Only the model and the material differ.

| Arm | Model | Material |
|---|---|---|
| small-none | `qwen2.5-coder:7b`, 7.6 billion parameters, local | none |
| small-agents | `qwen2.5-coder:7b`, local | item bytes in `AGENTS.md` in the step folder |
| flash-none | `glm-5.3-flash:cloud`, Ollama Cloud | none |
| flash-agents | `glm-5.3-flash:cloud`, Ollama Cloud | item bytes in `AGENTS.md` |
| large-none | `glm-5.2:cloud`, Ollama Cloud | none |
| small-prompt (optional) | `qwen2.5-coder:7b`, local | item bytes pasted after the prompt |

The optional arm runs only if at least 96 requests remain after the main plan.
Parameter counts for the cloud models are as listed by the local Ollama
server; their active parameter counts are not known here.

## 6. Harness and isolation

Pi 0.73.1 (`@mariozechner/pi-coding-agent`) on Node v22.22.1, with its
default tools read, bash, edit and write. The recipe is the one proven on
September 22 in [the independent instance record](../../docs/research/HARNESS-INDEPENDENT-INSTANCES-2026-09-22.md):
an empty home folder, a new `PI_CODING_AGENT_DIR` holding only `models.json`
and `settings.json`, the step folder its own git root under a parent with no
instruction file, `env -i` with a fixed path, and every other network proxy
pointed at a closed local port. Automatic retry and compaction are switched
off, so the harness makes no request that the runner does not see. Python 3.14
with its standard library is the only interpreter in the step.

A capture check with no model behind the endpoint confirmed, before the
freeze, that the `AGENTS.md` text reaches the system prompt in the material
arm, that it is absent in the no-material arm, that the pasted text reaches
the prompt in the optional arm, and that no text from the owner's own global
files appears.

## 7. Budget and counting

- Ceiling: 400 physical model requests in total, counted by
  [meter.py](runner/meter.py), a proxy between Pi and the local Ollama server.
  It writes a ledger line before it forwards a request and refuses anything
  beyond the ceiling.
- Step cap: 8 requests. A step that reaches it is stopped and scored as it is.
- A step starts only when the remaining budget can hold a full step cap.
- Order: three rounds, each holding every family and arm once, shuffled with
  seeds 20260923 to 20260925. If the budget ends early, complete rounds stay
  balanced.
- Pilot: one phones step each for `small-none` and `flash-none`, and one probe
  request to the large model. The pilot is excluded from results. After it,
  only harness plumbing may change, as a recorded amendment.
- Provider outage: a step with a rate limit or provider error is kept as an
  excluded attempt and run again after 60, 120, 300, 600 and then 900 seconds.
  Its requests still count.

## 8. Scorer, metrics and thresholds

[score_step.py](scorer/score_step.py) reads only `truth.json` and the step's
`output.csv`. It never reads the transcript or the model's claim of success.
Its leniency (column name case, surrounding spaces, yes and no spellings) is
written in its opening text and was fixed before the first call.

| Family | Primary metric | Passes when |
|---|---|---|
| phones | record accuracy: value and review flag both right | at least 0.90 and no wrong change to an already correct value |
| emails | record accuracy | at least 0.90 and no wrong change to an already correct value |
| addresses | record accuracy: all seven parts and the review flag right | at least 0.90 and no part rewritten away from the input text |
| duplicates | pair F1 over pairs marked `same` | at least 0.90 and no hard negative pair merged |

Also reported: wrong changes to correct values, correct holds on ambiguous
rows, guesses on held rows, change precision and recall, rewritten parts,
false merges, the F1 after closing clusters, time for each step, physical
requests and provider-reported tokens. Unknown tokens stay unknown.

Known-wrong outputs must fail the scorer: a copied input, an all-empty output
and a shuffled output for every family, plus an output that marks every pair
as the same company. The tests in [test_score_step.py](scorer/test_score_step.py)
also prove that each second condition of a threshold is the reason an
otherwise accurate output fails.

## 9. Claim rules

- A difference between two arms on one family is clear only when every
  repetition of one arm scores above every repetition of the other on the
  primary metric. With three repetitions each, that has a one-sided exact
  permutation probability of 1 in 20.
- Otherwise the difference is reported as not separated, with means and
  ranges.
- "Material helps" across families needs a clear difference in the same
  direction in at least three of the four families and no clear difference
  the other way.
- "The small model with material matches the larger model" needs
  `small-agents` to be not clearly worse than `large-none` in at least three
  of the four families.
- Every step counts except a provider outage attempt, including crashes,
  timeouts, cap stops and malformed files.
