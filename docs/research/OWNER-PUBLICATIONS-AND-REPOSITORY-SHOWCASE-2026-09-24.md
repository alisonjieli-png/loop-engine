# Showcasing the owner's publications and repositories on Baltor

Kind: dated research record, September 24, 2026. It reports what was read,
measured and decided. It runs no demonstration, makes no model call,
approves no library material and publishes nothing. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. The build
work in this record entered the roadmap as proposed steps S-6.110 to
S-6.118, and the competition facts were added to the existing side project
step S-6.90. The numbers start at S-6.110 because S-6.99 is on `main`,
S-6.100 is taken by the staff protocol line, and several research lines were
adding steps on the same day.

Source state: Baltor was read on `main` at `3bbdb109`. GitHub was read
through its programming interface, Kaggle pages were rendered in a headless
browser, and the Kaggle command line was used read-only, all on
September 24, 2026.

## Summary

- **Top five to build first**, in order: DueCare rebuilt per step
  (`duecare.baltor.ai`), the safety research tracked on current models with
  its test framework repaired (`safety.baltor.ai`), the owner's small tools
  rebuilt from their documentation and reused (`recreate.baltor.ai`), the
  owner's media tools as seeded short videos and Baltor's own social posts
  (`media.baltor.ai`), and the Gemma 4 Developer Agent entry (side project
  S-6.90, on `kaggle.baltor.ai` after the deadlines). An index at
  `papers.baltor.ai` lists every work with its run state. A configuration
  search on the owner's entity resolution pipeline follows as a page on the
  index.
- **The owner's findings are also Baltor's claims, measured by someone
  else first.** DueCare's published benchmark says a harness is an
  equalizer, and that its small offline core scored slightly higher than
  the full harness: the right files for a step beat more files.
- **Measurements today.** The LLM Safety Testing Framework's continuous
  integration has failed since March 8, 2026; a local check found two files
  that need Python 3.12 while the project declares Python 3.11, and 3,230
  lint findings. Twenty-four of the owner's small tools pass all 640 of
  their original tests. Eighteen of the owner's media repositories pass all
  1,582 of theirs.
- **Media is a library gap.** A keyword scan of 3,861 public agent
  extensions found none for deterministic video rendering or still-image
  motion, and Baltor's 43 served items include no media item. The owner's
  MIT media tools can become original first-party packages, each through
  the independent review, and can make Baltor's own social posts, each
  approved and posted by a person.
- **The Gemma 4 Developer Agent tracks** close on November 12, 2026 (paper)
  and December 2, 2026 (competition). The competition takes one declarative
  agent package for one fixed 4-bit Gemma 4 31B model, run offline. The
  owner's Kaggle account is entered in both. Nothing was submitted or
  posted.
- **Safety pages show no prompts and no responses**, only categories,
  criteria and counts, and link to the owner's writeups. **Media pages use
  only public material**: nothing private, no client work, no personal
  media and nothing with people in it.
- **No demonstration has run.** The run plans carry call ceilings, pilots
  first, and a schedule that respects the spent Ollama Cloud weekly
  allowance and the priority of the paid service.

## The owner's request

The owner, September 24, 2026:

> I would like to have demos of some of my publications and papers but
> ported over to the Baltor infrastructure/solutionining, / maintainence /
> continuous improvement. Dedicated subdomains for
> <https://github.com/TaylorAmarelTech/gemma4_comp>,
> <https://github.com/TaylorAmarelTech/llm-safety-framework>,
> [the gpt-oss-20b red-teaming writeup](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind)
> [and the Gemma 4 Good writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1779103293133),
> as well as other examples, and things like [the Gemma 4 Developer Agent
> Paper Track and Competition] we need to do some more advanced research on
> how we can present these in a way that helps baltor showcase its
> capability

And: "You can search various github projects and solutioning systems and
code and projects and projects on this system and external drive and public
resources, and papers, to find which items can be good for dedicated pages
on how Baltor can recreate systems, continuously improve upon them, solve
the same problem, optimize, search, etc."

Later the same day: "I have some create content on this drive and external
drives and historical projects related to image manipulation, video, media
generation, social media, generation, etc that is often not covered by many
public skills and harness files, we may want to have a dedicated subdomain
to showcase some of this or dedicated pages".

## How this research was done, and its limits

```text
Sources read
├── GitHub: three accounts through the programming interface
│   ├── repository lists, descriptions, languages, sizes, pushes, licences
│   ├── recent continuous integration runs of the strongest candidates
│   └── shallow clones in a temporary folder under the home folder
├── Kaggle
│   ├── both writeups, both Developer Agent tracks, the Gemma 4 Good
│   │   overview and winners page, rendered in headless Chromium
│   └── command line, read-only: competition list, data file list,
│       the harness guide, dataset metadata, the owner's notebook list
├── This machine: top-level folders under /home/username
├── External drive: folder names and file counts only, read-only
├── Public agent extensions: github-radar's feed of September 24, 2026
└── Presentation prior art: primary pages and repositories
```

The session's web search allowance was spent before this work began, so
every outside fact comes from a direct fetch of a primary page, the GitHub
interface or the Kaggle command line.

Measurements made today, with no model call:

- the test suites of 24 small tools, 18 media repositories and the DueCare
  benchmark scorer, and `ruff` on the LLM Safety Testing Framework, each in
  a temporary environment outside the repository;
- counts of test functions by reading source, where a repository states no
  current count;
- a keyword scan of a public agent extension feed.

Limits:

- A count quoted from a README is the author's claim unless this record says
  it was measured.
- Kaggle rules, timelines and prizes can change; recheck the pages before
  acting.
- The harness guide of the Developer Agent competition is competition data
  that entrants may not redistribute. It was downloaded under the owner's
  accepted rules to a folder outside the repository. This record states
  only the few constraints that shape the plan and quotes none of it.
- Private repositories, local-only projects and personal media are counted
  here but not named. Their list is kept outside the repository for the
  owner.
- A second external drive holds the owner's social video and newsletter
  projects, reached through two links in the home folder. It was not
  mounted on September 24, 2026 and was not inventoried.
- No video was rendered: `ffmpeg` is not installed on this machine, and the
  media tests cover planning, specifications and pages, not encoding.

## The four linked works

### DueCare and its Gemma 4 Good writeup

[DueCare](https://github.com/TaylorAmarelTech/gemma4_comp) is a Gemma 4
safety harness for migrant-worker protection. It wraps the model in layers:
deterministic indicator rules, audience personas, knowledge packs of law
and guidance, retrieval, tools such as a corridor fee-cap lookup, privacy
checks and rubric grading. It serves six lanes: content moderation, case
analysis, worker support, research, anonymized knowledge sharing and custom
interface integrations.

State on September 24, 2026:

| Fact | Value | Source |
|---|---|---|
| Repositories | `gemma4_comp` is the frozen competition submission; development continues in `TaylorAmarelTech/duecare` with the same history | both READMEs |
| Size and shape | 18 workspace packages, about 4,450 test functions by source count | local clone |
| Licence | MIT | repository |
| Automation | scheduled scrape and weekly jobs succeeded daily through September 24, 2026 | GitHub runs |
| Benchmark scorer | 8 of 8 tests passed in 0.08 seconds under Python 3.12 | measured today |
| Public evidence | a CC BY 4.0 grades dataset with 85,417 grade rows over 7,973 prompts, eight subject models, a three-judge panel and three arms (baseline, deterministic core, full harness); no prompt text | Kaggle dataset metadata |

The [Gemma 4 Good writeup](https://www.kaggle.com/competitions/gemma-4-good-hackathon/writeups/new-writeup-1779103293133)
was submitted on May 18, 2026 under CC BY 4.0 and lists the Main, Impact and
Special Technology tracks. Its evaluation is a four-arm smoke matrix on
Gemma 4 E2B: stock 29.5 percent, stock with the harness 35.6, fine-tuned
26.4, fine-tuned with the harness 41.2. The later README reports a paired
lift on `gemma4:31b` from 48.4 to 89.1 on a 0 to 100 rubric over 7,953
prompts under a three-judge panel, and names its own limit: these are
benchmark response-quality results, not field-detection metrics.

Two published findings matter most for Baltor:

1. **The harness is an equalizer.** Lift falls as the baseline rises, and
   models converge near the same score behind the harness.
2. **Less material scored higher.** The cheap offline core (fired indicator
   rules plus retrieved law) scored 87.1 against 84.9 for the full harness,
   and the full harness never beat the core for any model.

The hackathon's winners page, checked on September 24, 2026, does not list
DueCare. No Baltor page may imply an award for it.

### The safety research: the red-team writeup and the test framework

The writeup
[LLM Complicity in Modern Slavery: Native Blind Spots to Amplified Exploitation](https://www.kaggle.com/competitions/openai-gpt-oss-20b-red-teaming/writeups/llm-complicity-in-modern-slavery-from-native-blind)
(August 26, 2025, CC0) received an **Honorable Mention in the Overall
Track** of the OpenAI gpt-oss-20b Red-Teaming Challenge. It reports that
the model gave operational guidance for labour exploitation when a request
was framed as ordinary business, and that it failed to recognize documented
trafficking patterns.

At the level of detail a Baltor page may use, the writeup has five failure
categories, each checked against a list of required elements of a safe
answer:

| Category | Required elements | Failed | Partial | Passed |
|---|---:|---:|---:|---:|
| Business-framed requests | 9 | 7 | 2 | 0 |
| Jurisdictional hierarchy | 11 | 9 | 2 | 0 |
| Legal standards and financial crime | 13 | 13 | 0 | 0 |
| Amplification by known prompting methods | 11 | 11 | 0 | 0 |
| Harm to people seeking help | 11 | 11 | 0 | 0 |
| **Total** | **55** | **51** | **4** | **0** |

The required elements are defensive, for example "reference ILO C181" or
"provide worker rights warnings before any guidance". They can be shown.
The prompts and the model's responses are not shown on any Baltor page.

The [LLM Safety Testing Framework](https://github.com/TaylorAmarelTech/llm-safety-framework)
is the evaluation system that followed. It tests whether models refuse
requests that would help exploitation. Its defensive core is chain
detection: individually legal activities that combine into a trafficking
pattern, graded from BLIND (0) to EXPERT (4), cross-referenced with the 11
ILO forced labour indicators and migration corridors. It also contains
prompt transformation and attack modules for robustness testing. Those
modules are never shown on a public page.

State on September 24, 2026:

| Fact | Value | Source |
|---|---|---|
| Continuous integration | the last three runs failed (March 8, 12 and 13, 2026): lint, type check, all three Windows jobs and the Ubuntu Python 3.11 job; logs have expired | GitHub runs |
| Python 3.11 defect | two files under `src/prompt_injection/` use backslash escapes inside f-strings, which Python accepts only from 3.12; the project declares Python 3.11 or later | measured today |
| Lint | 3,230 findings with ruff 0.16.5, 2,540 automatically fixable | measured today |
| Test counts | the README badge says 5,208, the README tree and footer say 4,069, and source holds 3,717 test functions in 58 files | README and local clone |
| Size | about 353,000 lines of Python in 593 files; a 1.6 GB checkout | local clone |

The failing matrix, the syntax defect and the drifting counts make this the
clearest maintenance demonstration of the set.

## The two Gemma 4 Developer Agent tracks

Both were read on September 24, 2026. The Kaggle command line reports that
the owner's account has entered both.

| Subject | Competition | Paper track |
|---|---|---|
| Page | [gemma-4-developer-agent](https://www.kaggle.com/competitions/gemma-4-developer-agent) | [gemma-4-developer-agent-paper](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper) |
| Start | September 23, 2026 | September 22, 2026 |
| Deadlines | entry and team merger November 25; final submission December 2, 2026 | final submission November 12, 2026 |
| Time of day | 11:59 p.m. UTC | 11:59 p.m. UTC |
| Prizes | 65,000 dollars: 37,000, 18,000, 10,000 | 35,000 dollars: best paper 15,000, best new resource 10,000, best new application 10,000 |
| Participation shown | 1,411 entrants, 61 teams, 99 submissions | 423 entrants, 3 teams, 4 submissions |
| Submissions | 1 a day; choose up to 2 final | 5 a day |
| Team size | at most 5 | at most 5 |
| What is judged | percentage of tasks whose patch passes the task's hidden tests, on a private leaderboard | novelty, quality and generality, relevance, verifiability and clarity, each 0 to 5, averaged |
| What is submitted | `submission.zip` with `agent.yaml` at its root, optional prompts, sub-agents, skills and LoRA adapters | a Kaggle Writeup of at most 3,000 words: title, abstract, introduction, methods and experiments, related work; optional public notebook or arXiv-ready PDF |

Rules that shape a Baltor entry:

- **One model.** Every agent and sub-agent must use
  `gemma-4-31b-it-qat-w4a16-ct`. Different LoRA adapters per agent are
  allowed.
- **Declarative only.** The package is YAML, Markdown, skill scripts that
  run inside the task sandbox, adapter configuration and `.safetensors`
  weights, compiled into a Google Agent Development Kit agent tree. No
  Python entry point is accepted. The harness guide sets a size limit for
  the unpacked package and a 32,768-token context window.
- **Offline.** Each task runs in a sandbox without network access, with
  nine built-in tools: shell, patch submission, status, file read, edit and
  write, and three code graph tools over precomputed graphs and embeddings.
  The whole test set must finish within 12 hours.
- **Data.** 129 public training tasks from `fastapi`, `rich`, `requests` and
  `httpx` (22.42 GB in total with snapshots, graphs, embeddings and wheels).
  About 120 hidden test tasks come from private repositories. Participants
  may not redistribute competition data to anyone outside the competition.
- **Sharing.** Code may not be shared privately outside a team. Code shared
  publicly during the competition must be shared on Kaggle's forum or
  notebooks for the competition.
- **Licence.** A winner licenses the submission and the code that produced
  it under an open source licence that does not limit commercial use, and
  delivers training and inference code.
- **Paper.** The research must be original and unpublished. Submission is
  non-archival. Top papers are shown at a Google-hosted expo during NeurIPS
  2026.
- **Traces.** The harness writes one trajectory file per task in the Agent
  Trajectory Interchange Format, version 1.7.

The Gemma 4 Good hackathon, for comparison, judged mainly on video (impact
and vision 40 points, video 30, technical depth 30) with a writeup of at
most 1,500 words, a public repository and a working demo. The red-teaming
challenge judged each finding on severity, breadth, novelty,
reproducibility and methodological insight, and the report on clarity, with
an optional notebook that verifies each finding still reproduces.

## Candidate inventory

### GitHub accounts

| Account | Public repositories | Languages | Pattern |
|---|---:|---|---|
| TaylorAmarelTech | 14 | Python 10, Kotlin 2, TypeScript 1, JavaScript 1 | the flagship projects: DueCare, the safety framework, entity resolution, a trading system, directories |
| Amarel-Taylor-Scott | 186 | Python 177, Svelte 3, TypeScript 2, Kotlin 2, JavaScript 1, HTML 1 | about 100 small stdlib-only tools indexed by the LLM Dev Toolkit, 22 numpy machine learning systems, about 40 curated directories, about 15 media tools, Gemma hackathon apps, research systems, mirrors of the flagships |
| taylor-s-amarel | 13 | Python, JavaScript | Open Harness Hub, and projects from 2022 and 2023 |

Strongest candidates outside media. "Measured" means measured today; other
counts are the author's.

| Repository | What it does | Last push | Tests | Licence | Automation today |
|---|---|---|---|---|---|
| TaylorAmarelTech/gemma4_comp and duecare | DueCare safety harness | Aug 21 and Aug 9, 2026 | about 4,450 functions by source count | MIT | succeeding |
| TaylorAmarelTech/llm-safety-framework | safety evaluation framework | Mar 13, 2026 | 3,717 functions by source count | MIT (README and project file) | failing since March |
| Amarel-Taylor-Scott small tools (24 checked) | stdlib-only tools for model and agent work | Jun 22 to Aug 15, 2026 | 640 of 640 passed, measured | MIT, measured | none needed |
| TaylorAmarelTech/bq-entity-resolution | configuration-driven entity resolution: Python writes SQL, BigQuery or DuckDB runs it | Mar 19, 2026 | 3,833 (badge), 3,651 (description) | MIT | dependency updates succeeded through May 2026 |
| Amarel-Taylor-Scott/github-radar | daily discovery feeds of fast-moving repositories and agent extensions | Sep 24, 2026 | not stated | MIT | daily jobs succeeding |
| taylor-s-amarel/open-harness-hub | catalogue of harnesses, rule packs, tools and rubrics with exports to open formats | May 22, 2026 | not stated | MIT | succeeding |
| Amarel-Taylor-Scott/verdictkit, matchedfork, evidencegate | accept, reject or inconclusive verdicts for experiments, with matched controls and anytime-valid evidence | Jul 11 to Aug 15, 2026 | 17, 11, 19 | MIT | none |
| Amarel-Taylor-Scott/toolloop | a tool-calling coding agent in about 1,100 lines of stdlib for Ollama and compatible endpoints | Aug 15, 2026 | 91 | MIT | none |
| Amarel-Taylor-Scott/agenttape | records and replays agent tool calls and finds the first divergence | Aug 15, 2026 | 63 | MIT | none |
| Amarel-Taylor-Scott/codemap, astmap | code graphs and search across repositories | Aug 14 and Jun 23, 2026 | not stated | MIT | none |
| Amarel-Taylor-Scott/this-already-exists-dont-rebuild-it | research stub on recognizing that working code already exists | Jul 22, 2026 | not stated | none stated | none |
| TaylorAmarelTech/giga-trader | a trading research system | Mar 7, 2026 | 2,719 (README) | none | failing since March |
| TaylorAmarelTech/duecare-journey-android | on-device companion app on Gemma 4 E2B | Jun 7, 2026 | not stated | MIT | build succeeded |
| Amarel-Taylor-Scott/hisabsaathi-gemma-bharat, aksilokal-nusa-putra | Gemma apps with deterministic checks for small shops and community teams | Jul 12, 2026 | 106, not stated | MIT | none |
| Amarel-Taylor-Scott/stocks-return-prediction-v2, worldexplorer | a leakage-audited Kaggle pipeline and a zero-configuration tabular engine | Jul 12 and Jun 15, 2026 | not stated | MIT | none |

The owner's Kaggle profile (September 24, 2026) shows the title Notebooks
Grandmaster, 70 competitions, 228 datasets, 272 notebooks and two
writeups, the two above. Public notebook series beyond DueCare include
Graph Solutions 1 to 11 and Graph Jobs 1 to 4 (August 2026), which express
problems as graphs, and the Humor Genome studies (July 2026).

### Creative and media category

Eighteen public media repositories carry MIT licence files, and all 1,582 of
their tests passed on September 24, 2026 under Python 3.12. All are in the
Amarel-Taylor-Scott account.

| Repository | What it does | Created | Tests passed |
|---|---|---|---:|
| mathreel | mathematics visualization reels: a scene and a seed become one self-contained page, then an MP4 | Aug 14, 2026 | 332 |
| statreel | probability simulation reels | Aug 14, 2026 | 286 |
| algoreel | algorithm visualization reels, 15 algorithms with a compare mode | Aug 14, 2026 | 259 |
| physicsreel | physics simulation reels | Aug 14, 2026 | 140 |
| worldsmith | seeded voxel worlds with a camera flythrough; an optional model brief whose fields are clamped into ranges | Aug 15, 2026 | 160 |
| postguard | posting cadence, rolling caps, near-duplicate and never-repost ledgers, caption scrubbing | Aug 15, 2026 | 153 |
| datareel | data-story reels: bar races, line draws, counters | Aug 14, 2026 | 44 |
| quizreel | quiz shorts: question, countdown, reveal | Aug 14, 2026 | 43 |
| kinetype | kinetic typography reels | Aug 14, 2026 | 43 |
| slidesmith | seeded slideshow decks rendered to MP4, 13 themes | Aug 14, 2026 | 41 |
| cutlist | a keep list becomes `ffmpeg` cut commands and a timeline | Aug 14, 2026 | 23 |
| rep-counter | repetition counting from pose keypoints | Jun 23, 2026 | 12 |
| kenburns | pan and zoom plans over a still image for `ffmpeg` | Aug 14, 2026 | 11 |
| youtube-notes | a transcript becomes sectioned notes | Jun 23, 2026 | 10 |
| smartcrop | crop plans for 1:1, 4:5, 9:16 and 16:9 | Aug 14, 2026 | 9 |
| horizon | feeds become a ranked daily briefing | Jun 23, 2026 | 8 |
| ai-image-video-models-directory | open-weight generative media models with commercial-use flags | Jun 22, 2026 | 6 |
| web_animation | WebGL and canvas scenes with synthesized audio, recorded to MP4 by Playwright and FFmpeg | Jun 20, 2026 | 2 |

Every video generator above renders from code and a seed, with no stock
footage and no people. The same seed gives the same page, so a clip is a
recipe that anyone can render again.

Other media work:

- **Public without a licence file**: `social_media_automation`,
  `ai-video-pipeline`, `WorkoutAutoEditor`, `promptlens-extension` and
  `creativelens`. No package can derive from them until the owner adds a
  licence. `ai-video-pipeline` turns a source address into a commentary
  video, which also raises the rights of the source material, and
  `WorkoutAutoEditor` edits videos of people.
- **Reference directories**: text-to-speech, speech recognition, voice
  agent and image generation interface directories, useful as reference
  material for choosing media models.
- **This machine**: three files from June 10, 2026 (a batch recorder and
  two WebGL scenes) are early versions of `web_animation`.
- **The external drive**: about 786,000 files in 29 top-level media folders
  (generated images and frames, rendered videos, downloads and audio,
  counted to two folder levels), and eight private media repositories.
  They are listed for the owner outside the repository. Downloads made from
  other people's accounts are never usable.

Evidence that public collections lack this: github-radar's agent extension
feed of September 24, 2026 lists 3,861 public extensions (2,865 plugins,
684 skills, 134 tools, 128 agents, 50 frameworks). A keyword scan found no
extension for deterministic or seeded video rendering and none for
still-image pan and zoom. `ffmpeg` appears in 8 plugins, mostly for
watching videos. Cropping for social formats appears once, as a skill that
calls a commercial service, and posting appears as 3 hosted scheduling
services. Baltor's own served catalogue has 43 items and none for media. A
keyword scan can miss entries, so the claim a page may make is narrow: the
public collections scanned had few media packages, and none that render
video deterministically.

### Local repositories under /home/username

Sixteen top-level folders are Git repositories. Two are Baltor checkouts
and two are third-party sources. The other twelve are working copies of
about eight of the owner's projects with no public remote. They are not
named here and need the owner's decision before any page.

### External drive

The drive was listed read-only. Its `code_projects/repos` folder holds 242
project folders: 153 local copies of public repositories (the candidates
above), 53 private repositories and 36 folders missing from the account
inventory. An archive folder holds the August 25, 2026 copy of the
architecture presentation that now lives in the repository's
[showcase folder](../../showcase/README.md). Personal document folders were
not opened. Nothing was copied from the drive.

## What Baltor can do with each strong candidate

Each demonstration below is built from steps. Each step is a
[discrete cognitive or act step Loop node](../../ASTRA.md#complete-behavioral-explanation):
one clearly defined cognitive step or action that receives only the
context, instructions, skills, tools and working files it needs, runs in a
separately started harness, may change its approach and repeat until its
declared completion conditions hold, and may publish an output while it
continues. Publishing an output is not finishing, and an external effect is
never repeated without its own authorization. Public pages describe the
same thing in plain words: each step gets its own harness and only the
files it needs.

The five capabilities the owner named:

- **Recreate**: rebuild the system, or its core, from its paper or README.
- **Maintain**: dependency updates and test repair.
- **Improve**: a continuous improvement loop judged by measured results.
- **Smaller models**: the same problem solved with a smaller or cheaper
  model for each step.
- **Search**: optimize or search the configuration.

### DueCare

| Capability | What Baltor does | Independent check |
|---|---|---|
| Recreate | Rebuild the moderation lane as four steps from the writeup and README: find indicators, look up the controlling law, decide the verdict and severity, check the decision. Each step's working directory holds only its files, for example the indicator rules for the post's corridor in step one and the statute excerpts in step two. | DueCare's own `score_row` on the 25-item smoke set, with no model call |
| Maintain | Weekly dependency update of the 18-package workspace, full test run, repair of any failure in its own step | the workspace's tests and the collection gate |
| Improve | A self-improvement task proposes one change a week to a knowledge pack or rule; a different process evaluates it on a held-out split with the same judges and records accept, reject or inconclusive. The proposal stays a candidate until that evaluation. | the frozen judge panel on held-out prompts |
| Smaller models | Gemma 4 31B on each step against a larger model in one call, same prompts and judges | the three-judge panel on DueCare's rubric |
| Search | Which layers each step receives (rules, law, persona, tools) and which model size, searched on a small grid; DueCare's core-versus-full result is the first hypothesis | the same panel, with cost per arm |

Evidence that exists: DueCare's published records (the owner's, cited as
such), its public grades dataset, and today's scorer test pass. No Baltor
run exists. What must still run: runs D1 and D2 in the run plans below.

### The safety research

| Capability | What Baltor does | Independent check |
|---|---|---|
| Recreate | Turn the 55 published required elements into a frozen checklist and rebuild the evaluation from the writeup | two judges from families other than the subject model, plus deterministic checks for cited instruments |
| Maintain | Reproduce the framework's continuous integration jobs in containers, group the failures, repair each group in its own step, rerun | the project's own tests, ruff, black and mypy; then the project's GitHub checks on a pull request, after the owner's go-ahead |
| Improve | Rerun the checklist every month on current models and show the trend: does each 2025 failure still occur | the same checklist and judges each month |
| Smaller models | A current small model with a Baltor safety working directory against larger models without it | the checklist |
| Search | Which safety files a step needs: indicator rules, corridor fee rules, jurisdiction checklist, alone and together | the checklist, with tokens per arm |

Evidence that exists: the writeup's published grid (51 failed, 4 partial,
0 passed), the framework's run history and today's lint and syntax
measurements. What must still run: runs S1 and S2.

### The small tools

| Capability | What Baltor does | Independent check |
|---|---|---|
| Recreate | A small model rebuilds each tool from its README alone, in steps: plan the interface, implement, write its own tests, repair | the tool's original tests, never shown to the model |
| Reuse | A downstream task that needs a tool's function either rewrites it or receives the owner's package in the step's working directory | a deterministic checker for each downstream task |
| Smaller models | Gemma 4 31B on Ollama Cloud, and the owner's Tactical server as a second route | the original tests |
| Search | Which files the implement step needs: the full README, the interface section only, a packaging skill, a testing checklist | the original tests, with tokens per arm |

Evidence that exists: all 24 tools passed 640 of 640 original tests today
under Python 3.12; each carries an MIT licence file; each was created
between June 23 and July 11, 2026, after Gemma 4 was released, so Gemma 4
cannot have seen them in training. What must still run: runs R1 and R2.

### The media tools

| Capability | What Baltor does | Independent check |
|---|---|---|
| Recreate | Rebuild one scene type of a reel family from its README, for example a new `algoreel` algorithm | the family's tests, and a second render with the same seed that must match the first |
| Maintain | Keep renders reproducible as Chromium, Playwright and `ffmpeg` change: render a fixed set of seeds every week and compare frame digests | the recorded digests |
| Improve | Add scenes and themes; check text size and contrast in every frame automatically, and read engagement of Baltor's own posts later as aggregate data | frame checks now, recorded engagement later |
| Smaller models | Only the scene specification and the caption need a model; a small model writes both, and the render needs none | schema validation and the render comparison |
| Search | Theme, pacing, length and aspect ratio for each platform | frame checks, then recorded engagement |

Two questions the owner added for this category:

- **Original first-party packages for media work.** Yes, from the MIT
  repositories only, each through the independent review. Candidates: a
  seeded explainer reel from a scene specification (data, algorithm,
  typography and slide families); recording a canvas or WebGL scene to MP4
  with a fixed time step; a crop plan for social aspect ratios; a pan and
  zoom plan for a still image; a cut list to `ffmpeg` commands; a
  transcript to sectioned notes; a posting cadence and duplicate ledger for
  one account; and a media model chooser with commercial-use flags that
  must be kept current. `postguard` qualifies only in a reframed form: its
  own framing is avoiding bans across many accounts, which is evasion of
  platform integrity systems. The package keeps the cadence, duplicate and
  caption checks for one account within each platform's rules and leaves
  out the rest.
- **Baltor's own social posts as a case study.** Yes. `datareel` can show
  recorded numbers such as library growth, `algoreel` can explain the
  methods Baltor's steps use (lexical search, rank fusion, fitting context
  into a budget), `kinetype` can carry one-line lessons from runs, and
  `slidesmith` can summarize a case study. `smartcrop` and `cutlist` turn
  screen recordings of Baltor runs into platform formats. A person approves
  and posts every item, as roadmap step S-6.59 already requires, from the
  accounts the owner names in owner action OWNER-19.

```text
One Baltor post, one step each
├── pick a subject from Baltor's saved records
├── write the script: facts only from the record, each number linked
├── write the scene specification for one generator
├── render twice with the same seed and compare the digests
├── cut, crop and caption for each platform
├── check: facts trace to records, style guide, duplicate ledger, captions
└── a person approves and posts; the post address is recorded
```

Evidence that exists: 1,582 of 1,582 tests passed today, MIT licence
files, and the keyword scan above. What must still run: runs M1 to M3.

### The Gemma 4 Developer Agent entry

See the competition plan below. It is the strongest external check
available, because the hidden test set and private leaderboard are outside
Baltor's control, and it is a side project.

### Entity resolution configuration search

`bq-entity-resolution` runs its pipeline on DuckDB for local testing, so a
search costs processor time only. Baltor proposes configuration changes
(blocking keys, comparisons, thresholds, tiers) one step at a time from a
profile of the data; a deterministic scorer measures pairwise precision,
recall and F1 on labelled pairs; random search and the default quick
configuration get the same number of evaluations. Evidence that exists:
the README's local backend and the green dependency update runs. What must
still run: run E1.

### Candidates kept for later, with reasons

| Candidate | Reason it waits |
|---|---|
| github-radar | Continuous operation is already its nature; its best page needs a delayed ground truth (later star growth) that takes weeks to collect. |
| Open Harness Hub | Its 500 or more manifests fit the library's licensed import line better than a demonstration page. |
| The curated directories | Overnight link and entry maintenance is useful but shows less than the top five. |
| giga-trader | A maintenance run is possible, but a trading system invites performance claims that no page should make. |
| duecare-journey-android | An Android build is outside the harness steps the other pages show. |
| worldsmith and web_animation | Striking video, but further from a developer's task than the explainer reels; a later media page. |
| verdictkit, matchedfork, evidencegate | Better used inside the pages as candidate evaluator engines than as pages of their own. |
| toolloop, agenttape | Candidate engines: a minimal harness behind the step executor, and a record and replay tool. |
| Graph Solutions notebook series | Supports the paper track's graph reasoning topic; cite it in the paper's related work. |
| Private, local-only and personal media | Need the owner's selection before anything about them is public. |

## How strong agent work is presented

| Source | What it shows | What Baltor takes |
|---|---|---|
| [SWE-bench experiments](https://github.com/SWE-bench/experiments) | Every leaderboard entry publishes predictions, per-task logs with the patch, the report and the test output, and human-readable trajectories; entries are re-graded from the recorded test output | A trajectory and log for every step, and re-grading from saved output |
| [SWE-agent trajectory inspector](https://swe-agent.com/latest/usage/inspector/) | Web and terminal viewers that step through a run's thoughts, actions and observations | A step-by-step replay |
| [Aider leaderboards](https://aider.chat/docs/leaderboards/) | Percent correct beside the total cost of the benchmark run and the exact command used | Cost and the exact command beside every score |
| [MLE-bench](https://github.com/openai/mle-bench) | 75 Kaggle competitions scored by medal, a lighter 22-competition split, fixed hardware and a 24-hour limit, rule-violation and plagiarism detectors | A declared compute budget and rule checks on Kaggle pages |
| [AIDE](https://github.com/WecoAI/aideml) | The best solution file and an interactive tree of every solution tried | Show the alternatives tried, not only the winner |
| [Inspect log viewer](https://inspect.aisi.org.uk/log-viewer.html) | Per-sample messages, scoring explanations and metadata; logs bundle into a static site | Static publishing and a scoring explanation per item |
| [Harbor](https://github.com/harbor-framework/harbor) (Apache-2.0) | The Agent Trajectory Interchange Format: steps with tool calls, observations and per-step tokens and cost, nested sub-agent trajectories; a trajectory viewer | The trajectory format, and the viewer as a candidate engine |
| [PaperBench](https://github.com/openai/preparedness/tree/main/project/paperbench) | 20 ICML 2024 papers replicated from scratch, graded against hierarchical rubrics by a judge; a cheaper variant grades code only | Rubric grading for rebuilding a paper |
| [Paper2Code](https://github.com/going-doer/Paper2Code) (Apache-2.0) | Planning, analysis and code generation stages; reference-based and reference-free evaluation; about 0.50 to 0.70 dollars per paper with o3-mini | Stages as steps, and the cost of each rebuild stated |
| [asciinema player](https://docs.asciinema.org/manual/player/) (Apache-2.0) | Text-based terminal recordings with markers and speed control | Replays of harness sessions without video files |
| Kaggle judging, above | Hackathons reward a story with a working demo and a public repository; the red-teaming challenge rewarded reproducibility; the paper track weighs verifiability equally with novelty | A working demo, a story, and a record anyone can check |
| DueCare's own [results record](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md) | Every headline number pinned to a source revision, dataset version and model revision, with its limits beside it | The same rule on every Baltor page |
| The owner's reel generators, above | A video as a recipe: code, a scene specification and a seed that render the same frames again | Short replays and social clips that anyone can render again |
| Baltor's [showcase folder](../../showcase/README.md) | A slide player with play, pause, scrubbing, speed and captions, with video, PowerPoint and PDF exports checked in continuous integration | Reuse it for run videos instead of building another player |

What convinces developers: commands they can run, pinned versions, full
trajectories including failures, cost beside each score, a check that the
builder did not write, and plain limits. What convinces judges: the rubric
of that competition, above all reproducibility and verifiability, then a
clear story.

### The page anatomy Baltor should use

Every demonstration page is generated from saved run records, in this
order:

1. **The task and its source**: one sentence, and the link to the owner's
   writeup or repository.
2. **The result strip**: the independent check's result, elapsed time,
   calls, tokens and cost state, each linked to its record.
3. **The step timeline**: one card per step with its purpose, harness,
   model, time, tokens and outcome.
4. **The working directory viewer**: for each step, the tree of files its
   harness received, with digests and library item identities, and
   offered, fetched, loaded and used shown as separate facts.
5. **The replay**: each step's trajectory, with a terminal replay where the
   harness is a terminal program.
6. **With and without**: the same population, model and checker on both
   sides, with denominators, failures and excluded attempts. A negative
   result is shown as prominently as a positive one; the
   [data cleanup study](../../case-studies/data-cleanup-with-and-without-baltor/README.md)
   answered no, and a page of that kind must be possible.
7. **Before and after**, for maintenance: the check matrix and the diff
   statistics. Changes to attack or prompt modules are shown as file names
   and digests only.
8. **The independent check**: who or what checked, with which version, and
   its own record.
9. **Limits**: what the run does not establish.
10. **Reproduce**: the commands, the frozen design and its digest, data
    sources and licences.

The run record behind a page:

```text
Showcase run record
├── design: frozen before the first counted call, with its digest
├── population: items, selection rule, denominator, licence
├── arms: harness, model route, steps and material of each arm
├── steps
│   ├── working directory: files, digests, library item identities
│   ├── facts: offered, fetched, loaded, used, verified
│   ├── trajectory: one Agent Trajectory Interchange Format file
│   └── ledger: calls, input tokens, output tokens, seconds, cost state
├── independent check: evaluator, version, result, its own record
├── failures and excluded attempts
└── limits
```

## Subdomain plan

One page purpose for each hostname. The addresses follow the `/demo/...`
form of the Kaggle demonstration that the hostname line is building.

| Hostname | Address | Page purpose | Goes live |
|---|---|---|---|
| `papers.baltor.ai` | `/papers` | The index: each publication and repository, what Baltor does with it, and its run state (recorded, planned or not yet recorded) | first, before any run |
| `duecare.baltor.ai` | `/demo/duecare` | DueCare rebuilt as steps, with and without Baltor, and its improvement log | with the D1 pilot record |
| `safety.baltor.ai` | `/demo/safety` | The 2025 finding tracked on current models, and the framework's checks before and after repair | with the S1 record |
| `recreate.baltor.ai` | `/demo/recreate` | Small tools rebuilt from their READMEs, and reuse against rewriting | with the R1 pilot record |
| `media.baltor.ai` | `/media` | The owner's media tools: seeded short videos, the media package family with its review states, and how Baltor makes its own posts | with the M1 pilot record |
| `kaggle.baltor.ai` | `/demo/kaggle` | Kaggle work from task to submission: the homepage's Kaggle demonstration now, and the Developer Agent entry after the deadlines | with the hostname line's page |

The media hostname has two pages under it: `/demo/reels` ("Short videos
from a seed") and `/demo/social-posts` ("How Baltor makes its own posts").

Names considered and not chosen:

| Name | Reason |
|---|---|
| `studio` | Collides with Loop Engine's existing Studio interface, and suggests a hosted editor that Baltor does not offer. |
| `create` | Reads as account creation beside Get started, and names no subject. |
| `redteam` | Promises attack material the page will never show. The writeup lives on the safety page instead. |
| `gemma` | Gemma appears on the DueCare, Kaggle and Journey pages; one hostname for a model family would overlap them. |
| A second hostname for the Gemma 4 Good writeup | The writeup and the repository are one project; two hostnames would split one story and repeat it. |
| `tools` | Easily confused with the library's tools and with the public directory line. |
| `research` | Too general; `papers` is the owner's own word. |

The releasing session handles domain name records and certificates. Facts
for it: the Fly application holds eight certificates today, all ready. Fly
charges nothing for an organization's first ten single-hostname
certificates, then 0.10 dollars a month each, or 1 dollar a month for a
wildcard. Six more hostnames would cost about 0.40 dollars a month, within
the recorded allowance. Each hostname also needs its entry in the host
file's allowed hosts and origins (a missing hostname answers 421), a
`hostnames` row in the typed site map, and the check of S-6.67 that it does
not serve another page byte for byte. Records and certificates can be
prepared at once; each hostname joins the allowed hosts and the site map
only when its page has a recorded pilot, and the index lists it as planned
until then.

## Content outline for each page

### papers.baltor.ai

1. What the page is: published research and open-source projects by
   Taylor S. Amarel, each with what Baltor rebuilt, maintained or improved,
   and the record of the run.
2. One card for each work: DueCare; the 2025 red-team writeup; the LLM
   Safety Testing Framework; the small tools; the media tools; the Gemma 4
   Developer Agent entry; entity resolution; further reading (Graph
   Solutions notebooks, github-radar, Open Harness Hub).
3. Each card: source links and dates, one line on what it is, which of
   rebuild, maintain, improve, smaller models and search Baltor shows, the
   run state with its date and record, and the link to its page.
4. How to read these pages: every number has a run record; with and without
   comparisons use the same tasks, model and checker; failures are shown;
   safety pages show no prompts.

### duecare.baltor.ai

1. The problem in the writeup's words: exploitation hidden in paperwork,
   and models that miss fee camouflage.
2. What DueCare found, labelled as DueCare's published results with dates
   and links: the four-arm smoke matrix, the lift on `gemma4:31b`, the
   equalizer finding, and the core that beat the full harness. DueCare's
   own limit sentence beside them.
3. What Baltor did: the moderation lane as four steps, the working
   directory of each step, and the model.
4. The result strip and the with and without table for the moderation
   lane. At most three items from DueCare's published smoke set may be shown
   as examples, because DueCare publishes them as moderation examples.
5. The harness-lift lane: aggregate scores, judge agreement and tokens per
   arm. No prompt text and no responses.
6. The improvement log, once cycles run: each proposal and its verdict.
7. Limits and how to reproduce.

### safety.baltor.ai

1. The 2025 finding: five categories, 55 required elements, 51 failed and 4
   partial on gpt-oss-20b, the Honorable Mention, and the link to the
   writeup.
2. Tracked today: a grid of categories by current models, with and without
   a Baltor safety working directory, and the monthly trend.
3. The framework: what chain detection tests, and its checks before and
   after repair with the failure groups and the measured test count.
4. What this page never shows, and why: prompts, responses, attack and
   transformation content.
5. Limits and how to reproduce.

### recreate.baltor.ai

1. The question: can a small model rebuild a tool from its documentation,
   and when should a step reuse the tool instead?
2. The population: 24 tools, 640 original tests, MIT licences, creation
   dates after Gemma 4's release.
3. The steps and each step's working directory.
4. Results per tool: pass rate on the tests the README specifies and on all
   tests, with and without, with tokens and time.
5. Reuse against rewriting on downstream tasks.
6. What failed and why, the limits, and how to reproduce.

### media.baltor.ai

1. The index at `/media`: the owner's media tools and what each makes, the
   media package family with each package's review state, and links to the
   two pages below.
2. `/demo/reels`, "Short videos from a seed": a subject, the scene
   specification written by a small model, the deterministic render, the
   second render that matches it, and the finished clip in each aspect
   ratio. Each step's working directory, time and calls, usually two or
   three model calls for one clip.
3. `/demo/social-posts`, "How Baltor makes its own posts": for each post,
   the record it came from, the steps, the checks, the person who approved
   it and the post's address. Aggregate engagement once it is recorded.
4. The publishing rule on every media page: only material that is already
   public or rendered by these runs; no private files, client work,
   personal media or people.

### kaggle.baltor.ai

1. The hostname line's Kaggle demonstration, unchanged.
2. Until the paper is submitted, one line that an entry to the Gemma 4
   Developer Agent tracks is in preparation, with no approach, code, data
   or results.
3. After November 12, 2026, the paper and its records. After December 2,
   2026, the competition result and the package's records, with problem
   statements shown as links to the public issues rather than copies of
   competition data.

## Demonstration run plans and budgets

Rules for every run:

- A frozen design before the first counted call, with the population, arms,
  checker, metric and claim rules, as in the
  [overnight study](../../case-studies/overnight-cheap-model-with-and-without-baltor/README.md).
- Every call passes the counting proxy and lands in a ledger with its
  model, usage and outcome. Missing usage stays unknown.
- A pilot first; the main run only after the pilot record is reviewed.
- The run stops at its call ceiling, on `usage_limit_reached` or
  `payment_required`, and waits through a provider outage only within a
  declared wait, as the
  [persistent solving decision record](../architecture/ADR-PERSISTENT-GENERAL-SOLVING-AND-CONTRACT-FAILURE-REVIEW.md)
  requires.
- Cost state: Ollama Cloud calls are covered by the owner's subscription
  and their cost per call is unknown; Tactical calls run on the owner's
  hardware and their cost per call is unknown; Kaggle submissions run on
  Kaggle's hardware.

Token figures are estimates from assumed prompt and answer sizes, stated so
that a ceiling can be chosen. The ledger replaces them with measured
values.

| Run | Page | Population and arms | Route | Calls: pilot, ceiling | Estimated tokens | Time | Independent check |
|---|---|---|---|---|---|---|---|
| D1 | DueCare | 25 smoke items, 3 repetitions; one call, DueCare's pipeline, Baltor per step (4 steps) | Ollama Cloud `gemma4:31b` | 50, 900 | 2.2 million in, 0.25 million out | 1 to 2 hours | DueCare `score_row` |
| D2 | DueCare | 200 prompts sampled by category and difficulty from the 7,973 graded prompts; baseline, DueCare core, Baltor per step (5 steps) | Ollama Cloud `gemma4:31b`; judges `gpt-oss:120b`, `glm-5.2`, `deepseek-v4-pro` | 320, 3,500 | 11.4 million in, 1.4 million out | 3 to 4 hours at 4 at once | the published three-judge panel and rubric |
| D3 | DueCare | one candidate change a week on 100 held-out prompts | Ollama Cloud | none, 1,200 a cycle | 4 million in a cycle | overnight | the same panel; accept, reject or inconclusive |
| S1 | Safety | the framework's Linux jobs on Python 3.11, 3.12 and 3.13, lint and type check; repair by failure group | Tactical `gemma-4-coding-abliterated`, exact identity recorded | 400 is both | 3 million in | overnight | the project's own tests and linters; its GitHub checks after the owner's go-ahead |
| S2 | Safety | the prompts of the five public SET 1 notebooks; 4 current models, with and without | Ollama Cloud: `gpt-oss:20b`, `gemma4:31b`, `glm-5.3`, `qwen3.5-397b`; judges from other families | 30, 600 a month | 2.5 million in a month | 2 hours | the 55-element checklist |
| R1 | Recreate | 24 tools; one session per tool, Baltor per step | Ollama Cloud `gemma4:31b` headline; Tactical as a second route | 270, 5,000 | 10 million in, 0.8 million out | one night per route | original tests, held out |
| R2 | Recreate | 10 downstream tasks; rewrite or reuse | Ollama Cloud `gemma4:31b` | 40, 400 | 1 million in | 1 hour | a deterministic checker per task |
| M1 | Media | 10 subjects from Baltor's saved records; scene specification and caption steps | Ollama Cloud `gemma4:31b`, or Tactical for the pilot | 6, 60 | 0.15 million in | 2 to 4 hours with rendering | two renders with the same seed match; schema and fact checks |
| M2 | Media | 8 first-party media package candidates drafted from the MIT tools | Tactical | 10, 40 | 0.5 million in | 1 hour | the independent review panel, under its own budget |
| M3 | Media | 3 post drafts a week, after OWNER-19 is answered | Ollama Cloud `gemma4:31b` | 10, 30 a week | 0.1 million a week | 1 hour a week | fact trace, style and duplicate checks, then a person |
| E1 | Entity resolution | one labelled dataset; 60 evaluations each for default, random search and Baltor proposals | Ollama Cloud `gemma4:31b`; DuckDB on this machine | 30, 250 | 0.5 million in | 2 hours | pairwise F1 on held-out pairs |
| K1, K2 | Kaggle (S-6.90) | a frozen 20-task development subset of the 129 public tasks; the sample package and Baltor's package | Ollama Cloud `gemma4:31b` as an approximation of the competition model | 10 tasks, 1,200 each | 15 million in each | 10 to 20 hours each | the tasks' own tests in the competition harness |

Rendering for M1 needs `ffmpeg`, which is not installed on this machine; a
static build in a folder under the home folder is enough, with Playwright's
Chromium already present.

Schedule:

1. This week, while the Ollama Cloud weekly allowance stays spent: S1 and
   the R1 pilot on Tactical, the M1 pilot and M2 on Tactical, and the
   deterministic parts (the E1 scorer, the test labels for R1, the D2
   sample, the fixed render seeds for the media maintenance check).
2. After the allowance resets, with one recorded probe call first: pilots of
   D1, S2, R2 and E1, then the D1, R1, M1 and E1 main runs overnight.
3. D2, D3, S2 monthly, M3 and the Kaggle runs only after the library review
   batches of the week, each within its own ceiling. The paid service comes
   first.

Design details that keep the comparisons honest:

- **D2** re-grades every arm now with one panel. The July grades are shown
  beside the result as DueCare's record, never merged into it. If a July
  judge is no longer served, the whole run uses the new panel.
- **S2** judges exclude the subject model's family, as DueCare's panel did.
- **R1** labels every hidden test as specified by the README or not, by two
  reviewers, before the first model call, and reports both pass rates.
- **M1** takes every number in a clip from a saved record, and a clip whose
  number has no record fails its check.
- **K1 and K2** record that `gemma4:31b` on Ollama Cloud is not the
  competition's 4-bit quantized build; only Kaggle's own scoring counts as
  the result.

## The Gemma 4 Developer Agent side project

This extends roadmap step S-6.90 and replaces nothing in it.

What a Baltor entry would demonstrate: the right files for each step,
compiled into the declarative package the competition accepts. The Agent
Development Kit tree is the competition's form of one fresh harness per
step: each sub-agent starts with only its own instruction and skills, and a
read-only analyzer used as a tool keeps its file reads out of the coder's
context.

```text
submission.zip, compiled by Baltor
├── agent.yaml: root coder, gemma-4-31b-it-qat-w4a16-ct
│   ├── instruction: reproduce, patch, verify, submit
│   └── skills: minimal patch, test-first reproduction
├── sub_agents/localizer.yaml: read-only analyzer used as a tool
│   └── skills: repository navigation with the three code graph tools
├── sub_agents/verifier.yaml: runs targeted tests, reports only a verdict
├── prompts/: one short instruction file for each agent
└── adapters/: none in version 1; LoRA adapters only if compute allows
```

The research question for the paper track: at the same 32,768-token window
and the same model, does compiling separate material for each sub-agent
resolve more tasks than one agent holding all of it? That fits the
competition's topics of code comprehension and tasks and benchmarks. A
resource entry is possible only with material Baltor is willing to release
under an open source licence.

Plan:

| Date (2026) | Work | Needs the owner |
|---|---|---|
| Week of September 28 | Download the competition data under the owner's accepted rules to a folder outside the repository. Run the sample package on the frozen 20-task subset (K1). | no |
| October 5 to 18 | Add an Agent Development Kit submission profile to the Harness Working Directory Compiler, validated against the package rules; build package version 1 from new, releasable skills; run K2 on the same subset. | no |
| October 19 | First Kaggle submission. | yes, each submission |
| October 20 to November 5 | Ablations on the subset (separate material against one instruction; graph tools on and off; thinking budget); a paper draft with trajectory files and results folders. | no |
| November 5 to 10 | Independent review of the paper and a fact check of every number. | reads the draft |
| November 12 | Paper deadline, 11:59 p.m. UTC. | submits |
| November 25 | Entry and team merger deadline (already entered). | no |
| December 2 | Final submission; choose up to two. | selects and submits |

Risks and answers:

| Risk | Answer |
|---|---|
| It delays the paid service | Runs only after the week's library review batches; K1 and K2 are capped at 1,200 calls each. |
| Model mismatch in local runs | Local runs rank ideas only; Kaggle's scoring is the only result. |
| Overfitting to the 129 public tasks | The hidden tasks come from private repositories; freeze the development subset and keep a held-out share of the public tasks. |
| Private sharing is prohibited; public sharing must be on Kaggle | No code leaves the team during the competition; no Baltor page shows the package before December 2. |
| Competition data may not be redistributed | Data stays outside the repository; pages link to public issues instead of copying tasks. |
| The paper must be unpublished | No Baltor page or record shows the paper's results before it is submitted. |
| A winner must license the submission as open source | The package holds only new material written for it, never paid library items; entering a submission accepts that obligation, so the owner decides it with the submission. |
| The Ollama Cloud allowance | A probe call before each batch; stop on a spent allowance. |

## Proposals added to the roadmap

| Step | Title | Depends on |
|---|---|---|
| S-6.110 | Replayable showcase run records: step working directories, trajectories in the Agent Trajectory Interchange Format, and a cost and time ledger | S-6.37, S-6.44 |
| S-6.111 | The owner's publications index on `papers.baltor.ai` and the showcase hostnames, each with its own page | S-6.67, S-6.110 |
| S-6.112 | DueCare rebuilt per step, with and without Baltor | S-6.110 |
| S-6.113 | The 2025 red-team finding tracked on current models, and the safety framework's checks repaired | S-6.110 |
| S-6.114 | Recreate and reuse: the owner's small tools rebuilt from their READMEs by small models | S-6.110, S-6.44 |
| S-6.115 | Configuration search on the owner's entity resolution pipeline | S-6.110 |
| S-6.116 | `media.baltor.ai`: seeded short videos from the owner's media tools | S-6.110, S-6.111 |
| S-6.117 | Original first-party media packages from the owner's MIT tools, through the independent review | S-6.40, S-6.63 |
| S-6.118 | Baltor's own social posts, made step by step and approved by a person | S-6.59, S-6.116 |

The Developer Agent entry stays in S-6.90, which now carries the facts of
this record.

## Decisions made and why

| Decision | Choice and reason |
|---|---|
| Top five and their order | DueCare first: the owner's flagship with the most public evidence, and its published findings match Baltor's claim. Safety second: two of the owner's four links, a real maintenance defect, and a finding that can be tracked over time. The small tools third: the cleanest objective test of rebuilding and reuse, cheap and fully public. Media fourth: the owner named it, it fills a measured library gap, and it gives Baltor its first posts. The Developer Agent fifth: the strongest outside check, but a side project with rule limits and fixed deadlines. Entity resolution follows as a page on the index. |
| One hostname per project | The two writeups become sections of their projects' pages, because each project is one story. |
| `media`, not `studio` or `create` | `media` names the subject in a plain word; `studio` collides with the existing Studio interface, and `create` reads as account creation. |
| Hostnames go live with a pilot record | A hostname with no run adds work and shows an empty page; the index lists planned pages honestly in the meantime. |
| `kaggle.baltor.ai` points at the existing `/demo/kaggle` page | One Kaggle page, not two; the Developer Agent entry becomes a later section. |
| No prompts or responses on safety pages | The owner asked to keep harmful prompts and attack content off public pages. Checklists and counts carry the finding. |
| Up to three DueCare smoke items may be shown | They are recruitment posts published by DueCare as moderation examples, not requests for harm. |
| Media pages use only public or newly rendered material | The owner's rule: private files, client work, personal media and anything with people are listed for the owner and never copied. The seeded generators need none of them. |
| `postguard` enters the library only reframed | Its own framing is avoiding bans across many accounts. Baltor keeps cadence, duplicate and caption checks for one account within each platform's rules. |
| Every social post is approved and posted by a person | S-6.59 already rules out automated posting, and a post speaks for the company. |
| Unlicensed media repositories wait | No package may derive from code without a licence; the owner can add one. |
| Headline runs on Ollama Cloud models; Tactical for pilots and repair steps | A public comparison needs a model others can call. Tactical's model identity is recorded exactly whenever it is used, and it is not a subject model in safety evaluations. |
| Trajectories in the Agent Trajectory Interchange Format | The competition harness writes it, Harbor reads and views it, and Baltor's `run_history_export` slot already names a trajectory exporter kind with no engine. An engine there adds a format, not a component. |
| Prompt text leaves a run only by an explicit choice per run | The export slot's default carries no prompt text. A public showcase export is allowed only for public or synthetic inputs, after a secret scan, and never for safety runs. |
| Reuse the repository's showcase player for run videos | It already plays, scrubs, captions and exports, and continuous integration checks it. |
| Evaluator engines from the owner's tools stay candidates | verdictkit and its parts may judge with and without comparisons only after independent qualification, like any engine. |
| DueCare counts on pages come from DueCare's own verification script | DueCare's README asks for that before any exact figure is copied into public text. |
| Private candidates are listed outside the repository | The repository is public; names and descriptions of private work are private material. |
| Cost shown as unknown per call | Subscription and owner hardware costs are not metered per call; unknown stays unknown. |

## What still needs the owner

- Any Kaggle submission, notebook, writeup or post.
- Any pull request or push to the owner's own repositories, such as the
  safety framework repair.
- Anything public about private repositories, local-only projects,
  personal media or the drives, chosen from the private list.
- A licence on the unlicensed media repositories, if packages should derive
  from them.
- The social accounts and the approving person, through OWNER-19.
- Mounting the second external drive, so that its social video and
  newsletter projects can be inventoried.

## What this record does not establish

- No demonstration has run. Every Baltor result above is planned.
- The results quoted from DueCare and the red-team writeup are the owner's
  published records, not Baltor measurements.
- The test counts not marked as measured are the authors' claims.
- The media tests passed without rendering any video.
- The keyword scan of public extensions is approximate; it supports a
  narrow claim only.
- The call, token and time budgets are estimates for choosing ceilings.
- The Kaggle rules were read on one day and can change.
- Whether Baltor's per-step material helps any of these tasks is the open
  question the runs exist to answer; the data cleanup study answered no for
  its task.
