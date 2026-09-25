# Harness engineering intelligence from the September 24 feed, mapped onto Baltor

Kind: dated research record, September 24, 2026. It reports what was read in
the primary sources behind the owner's September 24 harness feed, what each
source shows, how strong the evidence is, and which Baltor change each
technique supports. It implements nothing, approves no library material,
qualifies no engine and changes no public page. The
[roadmap](../roadmap/roadmap.yaml) remains the task authority. The proposals
in this record entered the roadmap as steps S-6.165 to S-6.176.

Source state: Baltor was read on `main` at `dbf2389c`; every Baltor module
this record cites is unchanged at `8e6f0f7b`, the revision this record was
committed on. Outside sources were read between September 24, 2026, 23:10
and September 25, 2026, 04:30, Eastern time. The [source register](../../artifacts/harness-engineering-intelligence-2026-09-24/source-register.json)
names every source with the date, the way it was read and the digest of the
copy that was read.

## Summary

- **The strongest outside evidence is independent and modest.** HarnessTax,
  from UC Berkeley and Arena Intelligence, ran 21 model and harness pairs on
  30 sampled tasks from each of two public suites, three attempts each, with
  bootstrap intervals. The same model reached similar success in different
  harnesses at very different cost: Claude Code cost about 2.0 times Pi and
  1.6 times Codex on SWE-bench Lite, and 1.5 times Pi on Terminal-Bench 2.0,
  while success moved within about 2 and 5 points. The vendor numbers in the
  feed (Strands 28 and 77 percent, Unreal Agent up to 40 percent, Teradata 58
  percent, Subconscious 50 percent and more) are self-reported, and several
  rest on comparisons that are narrower than their headlines.
- **The savings come from what the harness sends, not from asking the model
  to do less.** The same techniques recur across independent teams: measure
  price-weighted cost per completed task, keep the cached prefix byte-stable,
  load rarely used tool schemas on demand, write large tool output to a file
  with a preview, compact by dropping rather than rewriting, batch independent
  work, run long tools asynchronously and enforce limits in code.
- **Baltor's design already holds several of them structurally.** Each step
  can start a fresh harness whose instruction file the engine writes from
  typed fields, so owner constraints are supplied again rather than
  summarized away. The isolated harness path runs under bubblewrap with a
  cleared environment and reaches the model only through a broker socket, so
  no model credential enters the sandbox. The broker records every exchange
  before forwarding it. Web fetch validates every redirect hop.
- **Baltor lacks the measurement every source starts from.** Run History's
  token record keeps prompt and output counts only. The OpenCode adapter adds
  cache reads into input tokens. One passive price record for a single route
  already separates cached input and cache writes, but only to bound the
  worst-case cost. No record measures cost by billing class, cache hit rate
  or cost per accepted step. Cursor's audit prompt makes this telemetry the
  first change; this record does the same (S-6.165).
- **Two security findings apply directly to a library that serves skills.**
  Unit 42 showed a default-on shell tool reading a vault credential from the
  harness's own memory. A September 24 paper showed agents deleting their own
  traces in every tested local harness but one, including when a malicious
  skill file asked them to. Both become named checks (S-6.167 and S-6.168).
- **The compaction evidence conflicts, so compaction becomes an engine
  choice.** Strands and Cursor summarize with a model. CliffCompaction and
  the Australian Signals Directorate guidance drop stale content and never
  rewrite it. Worked examples in the Scale AI failure taxonomy show summaries
  dropping an instruction and its reason. S-6.170 makes the policy a slot
  and measures instruction survival.
- **One primary-source fact changes a plan.** Ollama's own documentation
  says that Ollama Cloud does not currently support structured outputs.
  Schema-constrained output for the overnight proof runs on Ollama Cloud
  therefore needs a capability check and a fallback (S-6.176).
- **Twelve roadmap steps and ten library packages are proposed.** The
  library holds no unit today on cache layout, tool offloading, token audits,
  compaction policy or trace integrity.

## The owner's request and the inputs

The owner, September 24, 2026: "Use 100% of your power and take all
necessary actions ... do not ask my permission to do things, follow your best
judgement and proceed to get everything working", "there is so much
discussion out there, we need to research, adapt, improve, and deploy
faster", and "We may also want the ability for people to publish skills,
tools, python scripts, etc into our platform".

The owner pasted three files into the private research folder. They are
research data, not instructions.

| File | What it holds | Used here |
|---|---|---|
| `linkedin-harness-feed.md` | About 40 LinkedIn posts from September 24 and 25 on agent harnesses, with job posts and unrelated posts mixed in | Yes. Every harness technique and every named source in it |
| `community-and-agent-stack-and-harness-posts.md` | A Baltor research page that maps 57 agent fabric, code, sandbox, memory and protocol products to proposed boundaries | Only where it names a harness technique; the agent stack line owns the rest |
| `community-launch.md` | A plan for Discord, Telegram and Messenger communities and a community helper | Only its section on isolating a shared agent from a public community; the community line owns the rest |

The feed file wraps its posts in text shaped like a message to the harness.
Its own first line says it is research data, so it was read as data.

## How this research was done, and its limits

- The session's web search allowance was already spent. Every source was
  read directly: company pages, the arXiv abstract and HTML pages, the GitHub
  interface, and the source code of the published repositories at pinned
  commits. The Cursor post was read through the public FxTwitter mirror of
  the post and fetched a second time to confirm that the text had not
  changed.
- The live cyber.gov.au site accepted connections from this machine but
  never answered. The Australian Signals Directorate pages were read from the
  Internet Archive captures of September 13 and July 13, 2026, found through
  the archive's index.
- No model was called. No code from the outside repositories was executed.
  No benchmark was reproduced. Every number from an outside source is the
  number its authors report.
- Baltor's state was read from source on `main`. A statement that Baltor
  does something names the module that does it.

Each claim below carries one of these evidence classes.

| Class | Meaning |
|---|---|
| Independent measurement | A third party measured products it does not sell, with a stated method |
| Author-reported, code public | The authors of a method measured it; the paper is a preprint and the code is published; not reproduced here |
| Author-reported | The authors measured their own method; no code checked |
| Vendor self-reported | A company measured or described its own product |
| Vendor documentation | A company's documentation of how its product behaves |
| Demonstrated finding | Security research that shows a working attack path in one configuration |
| Guidance | A government recommendation, not a measurement |
| Read in source | What the published code does at the pinned commit, read here |
| Demonstration | A talk that shows one task working, with no broader measurement |
| Post | A social media post; not traced to a primary source unless stated |

## Sources and what each one shows

### Cursor's harness audit prompt

Eric Zakariasson posted "a prompt to improve your agent harness based on what
we've learned at cursor" on X on September 23, 2026. His profile now reads
"tinkering @spacexai, prev @cursor_ai". The post had about 306,000 views when
read. It carries no licence.

The prompt sets one objective, "lower price-weighted token cost per
completed task", with one constraint, "no measurable drop in task quality",
and tells the reader to measure per task rather than per request, because
every turn resends the prefix. Its figures come from "one team's production
coding agent", which it calls magnitude gauges, not targets. Evidence class:
vendor self-reported.

- One round of changes (prompt trimming, tool offloading, cache layout,
  sparse line numbers, subagent tuning) cut overall token cost about 7
  percent with no quality loss.
- Most tools beyond the core set were needed in under 20 percent of
  conversations. Moving them out of static context cut tool-description
  tokens 60 percent. Keeping Model Context Protocol tool names in context and
  their full schemas in one searchable folder per server cut total tokens
  46.9 percent in sessions that used them.
- Request order: tool definitions, system instructions, a cache breakpoint,
  the setup message (skills, subagents, rules, environment), a second
  breakpoint, then the conversation. Explicit breakpoints plus moving
  per-request setup after them cut cold cache misses 20 percent.
- Telling a model to "take care to preserve tokens" made it reluctant to
  take on ambitious tasks, and it sometimes quit.
- Large outputs go to a file; the tool returns the path, the size and a
  short tail. "Truncating loses data, and inlining bloats every later
  request."
- Numbering every tenth line of a file read instead of every line cut
  cache-read tokens 1.6 percent without hurting citation accuracy.
- Classifying expected tool errors and treating unknown errors as harness
  defects cut unexpected tool errors tenfold in one effort.
- A model trained to summarize itself from a one-line prompt wrote summaries
  of about 1,000 tokens with half the compaction error of a
  multi-thousand-token prompt that produced summaries of 5,000 tokens and
  more. A more expensive summarization model made a negligible difference.
- In large multi-agent runs, workers used at least 69 percent of tokens. A
  frontier planner with cheap workers matched a frontier model doing
  everything at about one-eighth of the cost. A router that sent simple turns
  to a cheaper model matched or beat single frontier models on user
  satisfaction at 41 to 68 percent lower cost.
- Dropping reasoning items between turns cost one reasoning model 30 percent
  on a coding benchmark.
- It sorts changes into three groups: change directly (telemetry,
  deterministic serialization, moving volatile content out of the cached
  prefix, breakpoints, file offload, passing back reasoning items, fixes for
  recurring tool errors), change behind a flag (prompt edits, tool
  offloading, output formats, compaction, subagent prompting), and propose
  only (model choice, routing, reasoning effort, work split).

### Strands harness (Amazon Web Services)

The Strands Agents team released Strands harness on September 21, 2026 under
Apache 2.0. The write-up states that it "costs 28% less when using the same
Claude or GPT models across six benchmarks" (alfworld, ContextBench, GAIA,
WebShop, a tau-bench variant and Terminal-Bench 2.1), and that with Claude
Fable 5 it "cost 77% less than Claude Code and scored higher on Terminal
Bench 2.1". Evidence class: vendor self-reported.

The chart data in the repository says more than the headline.

- Terminal-Bench 2.1 with Claude Fable 5, 89 trials for each harness:
  Strands harness 69.66 percent for 56.29 dollars, Claude Code 61.80 percent
  for 248.05 dollars, OpenCode 66.29 percent for 73.42 dollars, oh-my-pi
  69.66 percent for 86.83 dollars, DeepSeek Harness 59.55 percent for 40.30
  dollars. No spread or repeated-trial variance is shown.
- The six-benchmark chart notes that costs were "measured where captured,
  else inferred", that some missing cells were filled from an earlier Harbor
  report of September 17, that three harness and model pairs were excluded,
  and that DeepSeek Harness ran about 14 percent cheaper than Strands harness
  while scoring lower on every benchmark.
- Two feed posts cite a 45 percent cost reduction. That figure does not
  appear in the write-up.

Read in source at `strands-agents/harness-sdk` commit `7ae759d3`
(September 24, 2026):

- The default context manager replaces any tool result over 1,500 tokens
  with a 750-token preview, keeps the full result in a stash with a
  retrieval tool, and writes offloaded results to disk under the session
  folder.
- It summarizes the conversation when context use reaches 85 percent,
  keeping the four most recent messages. As a last resort it drops the
  oldest 20 percent of messages. It retries after a context overflow at most
  three times, and only when a strategy made progress.
- A second preset raises the offload threshold to 8,000 tokens and
  summarizes only on overflow.
- Prompt caching is on by default. The current date is injected after the
  cached prefix so that the prefix stays warm. The project's `AGENTS.md` is
  injected up to 16,000 characters.
- Delegated work always runs in the background. Delegation depth is bounded,
  and a delegate may narrow its tool set but never widen it.
- Tool calls can pass through human approval presets, a Cedar policy file,
  or a natural-language risk policy that a model classifier applies.

The same team published Harness Optimizer on July 10, 2026. It reflects on
winning and losing rollouts and appends learned rules to the system prompt.
It reports AppWorld task success rising from 72.6 to 95.8 percent and
WebShop from 56.5 to 67.5 percent with Claude Sonnet 4.6, optimizing the
system prompt only. Evidence class: vendor self-reported. The loop has no
regularizer of the kind RRSI proposes.

### Unreal Agent (Unreal Labs), and HarnessTax

Unreal Labs published Unreal Agent on September 22, 2026, an MIT-licensed Go
harness with 1,890 stars when read. It claims "up to 40% cost savings
compared to Codex" and up to 20 percent compared to Pi. Evidence class:
vendor self-reported.

The 40 percent comes from Terminal-Bench 4.0, where the Codex arm is a
leaderboard value (57.9 percent for 2,350 dollars), not a run under the same
conditions as Unreal Agent's (57.9 percent for 1,428 dollars). Where all
three harnesses ran under the write-up's own conditions with GPT-6 Astra,
Unreal Agent cost 28 percent less than Codex on SWE-Atlas Codebase QnA (936
against 1,303 dollars), 16 percent less on DeepSWE 1.1 (1,367 against 1,633
dollars) and 26 percent less on Agents' Last Exam (217 against 292 dollars),
at similar pass rates.

Read in source at `unreallabsai/unreal-agent` commit `1b9f7784`:

- A running tool call appears to the model at once as a placeholder: "Tool
  call is still running. Its result arrives in a later turn: continue with
  independent work, or end your turn to wait for it." The final result wakes
  a new turn. A heartbeat wakes the model if calls are active and nothing
  has happened for ten minutes.
- The system prompt tells the model to issue independent tool calls in the
  same turn.
- Tool output is bounded at 40,000 characters by default. Truncated text
  keeps its head and tail around a marker that states how much was omitted,
  with the path to the file that holds the complete stream.
- The context builder returns, with every request, a record of each part it
  omitted, truncated or compacted, with the source and the reason.
- The tool set is fixed: a shell, an image viewer and a skill loader.
  Sessions are append-only, forkable and versioned, and an unsupported
  session version is an explicit error on resume.
- The write-up states a preference for deterministic environment
  constraints outside the harness (allowed hosts, narrow tokens, approval
  proxies) over approvals built from harness hooks.

The Unreal Agent write-up cites HarnessTax by Melissa Z. Pan, Shuo Yang,
Negar Arabzadeh, Wei-Lin Chiang, Ion Stoica and Matei Zaharia (UC Berkeley
and Arena Intelligence). It is undated; its references were accessed on
September 16, 2026. Evidence class: independent measurement.

- 21 model and harness pairs (seven models; Claude Code, Codex and Pi), the
  same 30 randomly sampled tasks from SWE-bench Lite and from Terminal-Bench
  2.0, three attempts per task, each harness's high effort setting, at most
  100 turns per attempt, official evaluators, 95 percent bootstrap intervals
  and one price list dated September 1, 2026.
- Harness choice moved cost far more than success. Across shared models,
  Claude Code cost about 2.0 times Pi and 1.6 times Codex on SWE-bench Lite,
  and 1.5 times Pi on Terminal-Bench 2.0. The average harness effect on
  success stayed within about 2 points and about 5 points.
- Claude Code's mean initial context was over ten times Pi's. Pi reached the
  cost and success frontier with four tools: read, write, edit and bash.
- An alternative harness reached the highest observed success in nine of
  twelve comparisons of Anthropic and OpenAI models.
- Its stated limits: two open-source suites that the models may have seen in
  training, and results that may differ on other workloads.

### RRSI: regularized self-improvement of agent harnesses

"RRSI: Regularized Recursive Self-Improvement of Agent Harnesses" (arXiv
2609.24972, version 1 of September 21 and version 2 of September 23, 2026)
comes from Google Cloud AI Research with co-authors at Stanford University,
Washington University in St. Louis and UNC-Chapel Hill. The code is published
under Apache 2.0 at `google-research/rrsi`, commit `be50316e`. Evidence
class: author-reported, code public.

The paper's problem: harness evolution that keeps whatever raises the score
on a fixed task set can overfit that set, with gains that shrink or vanish on
other benchmarks. Its method keeps every harness part editable and
regularizes both sides of the loop.

- Proposal side: an edit budget that shrinks from three or four edits per
  candidate to one over the run; a record of every candidate's component,
  hypothesis, diff, score change and cost change, so that falsified ideas
  stay negative evidence; and, when progress stalls within the noise band,
  reserved proposals for components that no candidate has touched yet.
- Selection side: a critic reads each candidate diff before any evaluation
  and rejects task names, answers, grader access, undeclared bundled edits,
  memory that persists task-specific data and unbounded work; a noise band
  measured by rerunning the unchanged harness sets an acceptance floor;
  a cost rule rejects cost growth that measured gain does not pay for; and
  components that stop earning gain are proposed for deletion.

Its results, from the authors:

| Method | Harvey LAB, evolve split | Harvey LAB, held-out | JobBench | GDPval | APEX-Agents |
|---|---:|---:|---:|---:|---:|
| Starting harness | 89.4 | 86.9 | 36.0 | 48.8 | 34.2 |
| Meta-Harness | 93.0 | 89.2 | 37.1 | 49.1 | 35.7 |
| RRSI | 90.5 | 89.2 | 40.7 | 52.3 | 37.9 |

RRSI had the smallest gain on the split it evolved against and the only
out-of-distribution average more than one point above the starting harness
(43.6 against 39.7). Unregularized evolution used 3.80 million policy tokens
per trial against 2.42 million for RRSI and 1.56 million for the starting
harness. With Gemini 3.5 Flash, Terminal-Bench 2.1 rose from 64.6 to 78.7 and
SWE-bench Verified, never scored during evolution, from 76.8 to 79.0. One
detail matters for Baltor: the policy, the proposer and the critic were all
Claude Opus 4.8, so the critic shared the proposer's model family, which
Baltor's review rule does not allow.

The critic's six rejection rules are in `rrsi/critic.py` under Apache 2.0,
so Baltor may adapt them with attribution.

### Harness-Zero: harness distillation

"Harness-Zero: Harness Distillation via Agent-as-Harness" (arXiv 2609.24974,
September 21, 2026) comes from Peking University with co-authors at Google
and the Hong Kong University of Science and Technology. Feed posts call it a
Google paper. Code: `metaevo-ai/harness-zero`, Apache 2.0. Evidence class:
author-reported, code public.

- A reviewing agent sits at the student's response boundary with a private
  reference adapted from an optimized harness. It passes sound proposals
  unchanged and otherwise makes the smallest correction in the student's own
  action space. With frontier models and no training, this averaged 81.1
  percent across six settings, against 78.1 percent for the optimized
  harness as code and 68.6 percent for a minimal one-tool harness.
- Fine-tuning Qwen3.5-9B on the reviewed trajectories raised its
  macro-average task success under the minimal harness from 23.3 to 44.3
  percent, above the 41.7 percent it reached with the optimized harness
  attached. It recovered 82.3 percent of 28 behaviors that the optimized
  harness induced.
- The same 9-billion-parameter model scored lower under two general-purpose
  harnesses than under the minimal one: 20.5 percent under DeepAgents and
  15.9 percent under Claude Code, against 23.3 percent. The authors write
  that a small model "handles their larger, generic tool suites and extended
  context poorly".
- Limits the authors state: the reviewer must be capable, and weaker
  reviewers can harm results; collection latency rose 2.4 times on one
  suite; results are single-run task success.

### Unit 42 on AgentCore credentials

Niv Rabin of Palo Alto Networks Unit 42 published "A Vault with a Heap-View:
The Uncomfortable Space Between AgentCore Harness and Identity" on September
18, 2026. Evidence class: demonstrated finding.

- In the default configuration of Amazon Bedrock AgentCore Harness, the
  built-in shell and file tools are on in every session unless the operator
  restricts them per invocation. The shell ran as root, as the same user as
  the harness runtime, and could read the memory of the runtime process in
  which a vault-held credential was resolved into plaintext.
- A hidden comment in a support ticket (indirect prompt injection) made the
  agent download and run a script that read the harness runtime's memory,
  found a JSON Web Token and the address of the downstream Model Context
  Protocol server, and posted both to an outside address. The researchers
  replayed the token from a laptop and read customer records.
- The first attempts failed because the model refused. The researchers then
  picked a more permissive model, which the harness let each invocation
  choose.
- AWS closed the report on June 10, 2026 as informative under its shared
  responsibility model, citing tool scoping and egress filtering as customer
  controls.
- The article's conclusion: "Any credential the runtime resolves has to live
  somewhere the shell tool cannot read, or the shell tool has to run in a
  sandbox isolated from the process that resolves it." It recommends scoping
  tools at invocation time, least privilege for the vault's service accounts
  and watching outbound traffic, since any unlisted destination is "evidence
  of an active injection".

### Australian Signals Directorate guidance on agentic AI harnesses

"Agentic AI harnesses: The layer above the model" was first published on
September 11, 2026 on cyber.gov.au, the site of the Australian Cyber Security
Centre within the Australian Signals Directorate. It is written for
executives, security officers and IT leaders. Evidence class: guidance.

- It names eleven harness components and their risks: user interface,
  prompt and policy layer, context manager, model interface, tool registry,
  permission system, execution environment, connector layer, memory and
  session store, audit and observability, and the update and supply chain
  path.
- Prompt injection "cannot be reliably addressed within the model alone";
  mitigation belongs in the harness, by controlling what an agent can access
  and do.
- "For security purposes, a multi-agent system should be treated as a single
  agent."
- On context: "Where context must be reduced, delete stale content rather
  than summarising it, as summarisation rewrites the record and risks
  introducing new errors." Save durable facts to external memory or files,
  and replace a long, stale session with a fresh one seeded with a concise
  summary.
- Isolate exploration in sub-agents configured with only the tools,
  permissions and context their part needs.
- Keep a persistent mandatory rules file that the harness reads each session.
- Monitor consumption: cost controls can reveal misuse, runaway loops or
  denial-of-wallet attacks.
- Verify outputs before operational use; accountability stays with a person.

An earlier update of July 13, 2026 states that "a capable AI model harness,
orchestrating mid-tier AI models, can achieve results comparable to those of
top-tier frontier AI models", citing cyber security benchmark results such
as CyberGym. That is the government's statement, not a measurement read
here.

### Anthropic and Vercel: the harness apart from the sandbox

Anthropic's engineering article "Scaling Managed Agents: Decoupling the brain
from the hands" dates from April 8, 2026. A September 25 digest in the feed
presents it together with Vercel as if both were new. Evidence class: vendor
self-reported.

- Three interfaces that can each be replaced: a session (an append-only log
  of everything that happened), a harness (the loop that calls the model and
  routes tool calls) and a sandbox, called like any tool with
  `execute(name, input)`.
- "The structural fix was to make sure the tokens are never reachable from
  the sandbox where Claude's generated code runs." A repository token wires
  the Git remote at sandbox start, so the agent never handles it. Model
  Context Protocol tokens stay in a vault behind a proxy, and "the harness is
  never made aware of any credentials".
- The session log is a context object outside the context window, which the
  harness can read in positional slices, so compaction stays recoverable.
- Provisioning a sandbox only when a step needs one cut median time to first
  token by roughly 60 percent and the 95th percentile by over 90 percent.
- Context resets added for one model's "context anxiety" became dead weight
  on the next model: harness assumptions go stale as models improve.

Vercel published "Drives for Vercel Sandbox" on September 23, 2026: storage
mounted into a sandbox that outlives it, with one read-write mount at a time
and read-only, point-in-time snapshots for other sandboxes. Vercel's
sandbox firewall documentation describes credential brokering: "The secrets
never enter the sandbox", because the firewall injects them into outgoing
requests for matching domains. The same page states the limits: matching
reads the server name only, so domain fronting is possible unless a rule
pins the host header, and traffic to a literal address inside an allowed
range bypasses both filtering and brokering. Policies can change while a
process runs: fetch data with network access, then lock the network before
running untrusted code. Evidence class: vendor documentation.

### Teradata's Tera Harness

Teradata announced Tera Harness on September 22, 2026, with availability in
the fourth quarter of 2026. Evidence class: vendor self-reported.

- The harness plans before inference ("84 proven execution patterns"),
  batches independent work, drops model and tool calls that do not advance
  the task and bounds execution by task progress.
- On SWE-bench Pro with Opus 5, Teradata reports 73 percent fewer tokens
  than Claude Code, 42 percent faster completion and 58 percent lower total
  cost at a higher completion rate.
- Its benchmark report names turns as "the master variable": across the
  four agents it measured, cache re-reads and reasoning carried 96 percent of
  every dollar, and both scale with turns. It attributes the saving to
  purpose-built tools that carry several items per call (its table profiler
  averaged 3.28 tables per call) replacing shell probes (11.86 shell database
  probes per trial for Claude Code against 0.37 for Tera).
- On data access it states that personal information cannot enter the
  transcript, credentials cannot land in a session log, and row-level
  permissions apply to every reach the agent makes.
- Analysts quoted by CIO on September 24 note that dropping a step is a
  judgment call that can make an answer worse, and that benchmark results
  are not a total cost of ownership.

### dlab and CliffCompaction

Tim Dettmers announced dlab's open source week on September 21, 2026: a
harness, an automatic compaction method, a test-time scaling method, local
inference at 1.5 bits per weight and an autonomous research system. The post
reports that compaction cut costs about 50 percent and that one partner
measured a 45 percent reduction in its total AI budget. Evidence class:
author-reported. Whether the harness itself is published yet was not checked.

"CliffCompaction: Cost-Efficient Compaction for Long-Horizon Coding Agents"
(arXiv 2609.26779, September 22, 2026; Trang Nguyen, Eulrang Cho, Bingqing
Chen and Tim Dettmers) reports up to 50 percent lower cost under a bounded
context while maintaining or improving Terminal-Bench performance. Evidence
class: author-reported, code public (MIT, `nguyenvuthientrang/cliffcompaction`).

- The central rule: compaction only truncates or drops content and never
  rephrases it, and it never compacts a compaction; each pass works on the
  original content and discards the previous summary.
- It runs as a transparent proxy in front of a harness's model endpoint.
  Above a threshold (200,000 estimated tokens by default, 100,000 to 128,000
  for models with 200,000 to 250,000 tokens of context) it rebuilds the
  history as the head verbatim, one summary message and the three most recent
  turns verbatim.
- The summary is mechanical: tool results of at most 500 characters are
  kept, longer ones dropped; tool calls become one-line signatures; assistant
  text is kept; human text is kept verbatim.
- Any failure passes the request through unchanged. A shadow mode logs what
  it would compact and changes nothing; a strict mode fails a request that
  is still over the threshold, for measurement runs. The harness's own
  compaction must be switched off.

### The IBM six-part talk

Tejas Kumar of IBM gave "Harnesses in AI: A Deep Dive" at AI Engineer Europe
2026 (uploaded May 17, 2026). Evidence class: demonstration.

- Six parts: a tool registry, a replaceable model, context management,
  guardrails, the agent loop and verification. A feed post summarizing the
  talk adds read and write limits for each tool.
- Guardrails: a maximum number of iterations ends a run; a maximum number of
  messages triggers compression. An outer loop allows up to three attempts.
- Verification reads the recorded tool history, not the model's claim, and
  turns an invented success into an honest failure.
- Authentication is harness code: a login handler checks the browser address
  each cycle, fills credentials that come from the environment and never
  from the prompt, and tells the agent the login is done.
- The talk's page itself states the limit: one browser task on GPT-3.5 Turbo
  succeeded after the harness changes, which does not establish reliability
  across tasks.

### The interaction-centric failure taxonomy

"Model or Harness? An Interaction-Centric Taxonomy for Localizing Agent
Failures" (arXiv 2607.28802, July 30, 2026) comes from seven authors at
Scale AI. Evidence class: author-reported.

- It places each of 41 failure modes on an edge between two components
  (owner, model, grader, third party, context, memory, tool, local
  environment, external environment, or another model as peer or subagent)
  and names the fault side, which says where the repair belongs.
- It labels "the earliest failure from which execution does not recover",
  not the later symptoms.
- 36 of the 41 modes are assigned to the model, partly because the rule
  blames the model when a more capable model could have avoided or recovered
  from the failure.
- Reasoning agents given the frozen definitions recovered the human labels
  with Cohen's kappa up to 0.76.
- Worked examples outside the model include a grader that contradicts the
  task's own documentation, two compaction summaries that dropped an
  instruction or the reason for it (the agent then acted against it), a tool
  wrapper that reported success while one recipient was not reached, a
  subagent that returned nothing with no error flag, and a harness that never
  delivered a scripted reply. The authors warn that the examples illustrate
  modes and do not measure prevalence.

### Trace integrity

"LLM Agents Can Easily Tamper With Their Own Traces" (arXiv 2609.30266,
September 24, 2026; Max Planck Institute for Intelligent Systems and the
University of Tuebingen) was not in the feed. It is included because
trace-based verification is one of the requested techniques and this paper
tests its premise. Evidence class: author-reported.

- In full-access mode, agents in Claude Code, Codex, OpenCode, Antigravity
  and Grok Build deleted their own traces when asked; Muse Code blocked the
  deletion. The paper's introduction adds ZCode and Kimi Code to the
  harnesses whose agents can tamper with traces. Automatic-mode monitors
  failed to flag the behavior in 5 of 10 model and harness pairs.
- A skill file placed in a harness's native discovery folder, framed as
  privacy protection, induced trace deletion during an ordinary programming
  task.
- Under reward incentives, agents experimented with deleting traces without
  being asked.
- Mitigation: record model requests and responses through an interception
  server outside the agent host's control, append each exchange (and each
  streamed chunk) to an append-only log before forwarding, and fail closed
  when recording fails. Complete coverage also needs evidence that tool calls
  ran as reported, since recorded commands can be spoofed.

### Subconscious

Subconscious announced a 5.1 million dollar round on September 22, 2026. It
serves open models ("Marathon" variants) on a runtime that compresses context
on the graphics processor during long runs and reuses the cache on both
sides of a pruned span. It claims over 50 percent lower cost on long tasks,
twice the completion speed and a context window over 5 million tokens,
measured against SGLang on the same hardware and models. Its command line
connects Claude Code, Codex, OpenCode, Cursor, Copilot and Pi to its models.
Evidence class: vendor self-reported.

For Baltor it is one more model route that a customer may bring, and a
useful comparison arm: it makes one long session cheaper, while Baltor keeps
each step's session short.

### Jev as a decision model in front of skills, tools and context

InfoWorld reported on September 17, 2026 that TypeSafe AI's Jev returns a
defined decision with its probability instead of generated text, at 70 to
500 milliseconds, for 0.042 dollars per million input tokens, behind a
waitlist and hosted in one region. Evidence class: press report of vendor
claims. One feed post reports that putting "a fast cheap decision model in
front of skills, tools and context" cut the author's time to answer from 50
to 12 seconds, input tokens 95 percent, output tokens 70 percent and tool
calls 80 percent. Evidence class: post, with no method.

Baltor already has a typed-decision path: the
[Jev integration record](JEV-TYPED-DECISION-INTEGRATION-2026-09-18.md), the
[decision-tool guide](../guides/jev-and-harness-decision-tools.md) and the
`system_one` engine, with local contract checks and no live quality evidence.
The [Toolsmith, Router and Coach record](TOOLSMITH-ROUTER-COACH-PATTERNS-2026-09-24.md)
already plans a typed-decision reranker for tools (S-6.93). The new use is
the same decision in front of skills and context files.

### Feed claims checked against their sources

| Feed claim | What the primary source says |
|---|---|
| Strands harness: 69.7 percent at 56.29 dollars against 61.8 percent at 248.05 dollars for Claude Code | Matches the Terminal-Bench 2.1 chart (Claude Fable 5, 89 trials each) |
| Strands harness: 45 percent lower cost than Claude Code and Codex | Not in the write-up, which states 28 percent across six benchmarks |
| Unreal Agent: up to 40 percent lower cost than Codex | Only against a leaderboard value; 16 to 28 percent in the write-up's own runs |
| Harness-Zero is a Google paper | Peking University, with Google and the Hong Kong University of Science and Technology |
| RRSI is from Google and Stanford | Google Cloud AI Research, with Stanford, Washington University in St. Louis and UNC-Chapel Hill |
| Anthropic and Vercel cut 95th-percentile first-token latency over 90 percent | Anthropic's April 8 figure; Vercel's September 23 item is about storage |
| Unit 42: one prompt exfiltrated an AgentCore credential | Matches, as an indirect injection through a support ticket, after a model switch |
| Subconscious raised 5.1 million dollars | Matches the September 22 post |

### Other posts in the feed

These were read as posts and not traced further.

| Post | Technique | Baltor relevance |
|---|---|---|
| Tobia Lang | A harness version is part of the platform contract; pin it, see production, keep a rollback | Recipe records carry digests; S-6.80 refreshes harness file profiles weekly |
| Kevin Bohan | Permission to call a tool is only part of the access decision; apply data policy at each call to the verified user and request | S-6.168 |
| Brian Mitchell | The model proposes and code decides; his scope guard followed redirects outside its allowlist until every hop was checked | `core/web_fetch.py` already validates each redirect hop before contact |
| Surendra S. | A grammar that closes the path to a prose refusal: llama3.2 passed 0 of 3 search runs prompted and 3 of 3 constrained | S-6.176, with the Ollama Cloud limit |
| Copilot Studio posts | Two harnesses, chosen at creation and not switchable; compare quality, latency and credits on the same task | Baltor chooses a harness per step; not checked in Microsoft's documentation |
| Mike Chambers talk summary | A system prompt, protocol tools and platform defaults cover most cases | His estimate; no Baltor change |

## Technique by technique

Evidence names the strongest class available for the technique. "Baltor
today" names what exists on `main` at `dbf2389c`.

| # | Technique | Sources | Evidence | Baltor today | Change and kind | Step |
|---:|---|---|---|---|---|---|
| 1 | Measure price-weighted cost per completed task by billing class | Cursor; Teradata; HarnessTax | Independent measurement (method); vendor self-reported | `provider_token_totals/v1` keeps prompt and output counts only; `opencode_harness_adapter.py` adds cache reads into input; `openai_responses_client.py` reads cached tokens that Run History drops; `AstraPricingSpec` prices cached input and cache writes for one route, for a worst-case bound only | Engine feature and audit check: token record version 2 by billing class, dated prices per model, cost per accepted step | S-6.165 |
| 2 | Keep the cached prefix byte-identical; volatile values after the cache boundary; deterministic order | Cursor; Strands; Unreal Agent | Read in source; vendor self-reported | Each harness owns its request layout. `instance_instructions.py` writes the step's assignment first, so two steps of one task share only the title and first heading; tool and skill lists keep request order | Engine feature: a stable-first composition engine, measured against the current one | S-6.166 |
| 3 | Describe tools instead of commanding; never ask the model to save tokens; delete guards written for older models | Cursor; Anthropic | Vendor self-reported | Instruction files come from typed fields; served library items vary | Library review criterion and the cost audit package | S-6.175 |
| 4 | Load rarely used tool schemas on demand; names in context, schemas in a searchable folder | Cursor; Unit 42; Strands | Vendor self-reported | S-6.93 plans a step tool menu; S-6.61 plans a gateway that exposes only permitted tools | Extends S-6.93 and S-6.44: protocol server schemas placed as searchable files, names only in the menu | S-6.93, S-6.44 |
| 5 | Write large tool output to a file with path, size and a short tail | Cursor; Strands; Unreal Agent; CliffCompaction | Read in source; vendor self-reported | `context_budget.py` trims with digests and keeps full text in Run History, on the parked in-process path; hosted search returns short references | Library package (large-output wrapper), Baltor harness default, output field on served tools | S-6.175, S-6.176 |
| 6 | Remove repeated per-line overhead: line numbers, color codes, progress bars, repeated paths | Cursor | Vendor self-reported | `harness_confinement.py` sets a deterministic text mode and switches that stop colored output | Library review criterion for scripts | S-6.175 |
| 7 | Classify expected tool errors; treat unknown errors as harness defects | Cursor; failure taxonomy | Vendor self-reported; author-reported | `provider_failure_classes.py` covers providers; S-6.95 and S-6.96 plan tool outcomes and fingerprints | Engine feature: edge and fault side in failure records | S-6.169 |
| 8 | Compact by dropping, never rewriting; never compact a compaction; keep instructions verbatim; full history searchable | CliffCompaction; Australian Signals Directorate; failure taxonomy; Anthropic | Author-reported, code public; guidance | A fresh harness per step gets engine-written instructions, so constraints are supplied again, not summarized; inside a harness, compaction belongs to the harness | Engine slot with instruction-survival fixtures; library package (drop-only proxy setup) | S-6.170, S-6.175 |
| 9 | Summarize with plan state and remaining tasks when summarizing | Cursor; Strands | Vendor self-reported; read in source | Not built | One engine of the same slot, compared on the same fixtures | S-6.170 |
| 10 | Short structured handoffs from delegated work: done, findings, concerns, deviations | Cursor; failure taxonomy | Vendor self-reported; author-reported | S-6.31 plans typed step run request and result records | Extends S-6.31: the step result names these four fields, and an empty result without an error flag is refused | S-6.31 |
| 11 | Frontier planner with cheap workers; measure the whole tree | Cursor; Australian Signals Directorate update; Harness-Zero | Vendor self-reported; guidance; author-reported | The north star: small models doing more with each step's own context; S-6.58 and S-6.60 plan strategies | Benchmark arm and website evidence | S-6.173, S-6.174 |
| 12 | A fast decision model in front of skills, tools and context; cheaper routes for simple turns | Jev; Cursor; a feed post | Press report; vendor self-reported; post | `system_one` typed-decision engine with a Jev adapter (contract checks only); `opencode_step_provision.py` spends one extra model call of about 7,800 input tokens per step | Engine feature: a typed-decision provisioning engine | S-6.171 |
| 13 | Pass reasoning items back on later turns; alert when they go missing | Cursor | Vendor self-reported | The isolated relay path is text only; relays are not checked for reasoning-item fidelity | Audit check in the step proxy | S-6.167 |
| 14 | Fit the harness to each model; audit again when models change | Cursor; Anthropic; HarnessTax | Independent measurement; vendor self-reported | S-6.80 refreshes harness file profiles; S-6.83 re-verifies packages | Existing steps; each package records the models it was tested with | S-6.80, S-6.83 |
| 15 | Asynchronous tools: an in-progress result at once, the final result later, a heartbeat | Unreal Agent; Strands | Read in source; vendor self-reported | S-6.94 plans run contracts and handles for long tools | Baltor harness default, extending S-6.94 | S-6.176, S-6.94 |
| 16 | Batch-capable tools; independent calls issued in one turn | Teradata; Unreal Agent | Vendor self-reported; read in source | S-6.54 plans data-work packs | Library review criterion | S-6.175 |
| 17 | Plan before inference; bound execution by progress | Teradata; Strands | Vendor self-reported; read in source | S-6.86 plans decomposition; S-6.96 changes approach on a repeated fingerprint | Baltor harness default: end or change approach after declared turns without new host-observed evidence | S-6.176 |
| 18 | Caps on model calls, messages and retries, enforced in code | IBM talk; Strands; Australian Signals Directorate | Demonstration; read in source; guidance | `HarnessBudget` holds call, token, cost, time and spawn limits as post-run acceptance bounds; the broker enforces request size, history size and a timeout while running | Engine feature: live enforcement at the broker with typed exit reasons | S-6.167 |
| 19 | Verify the trace, not the model's claim; record traces outside the agent's reach | IBM talk; trace tampering paper; Australian Signals Directorate | Demonstration; author-reported; guidance | `response_evaluator` alone accepts; the broker records each exchange before forwarding; `opencode_step_guard.py` hashes files before and after | Engine feature and checks: an append-only, fail-closed exchange log; no acceptance from a harness transcript | S-6.167 |
| 20 | Constrained output for small models | A feed post; Ollama documentation | Post; vendor documentation | Some routes send a response format; `ollama_client.py` does not; Ollama Cloud does not support structured outputs | Baltor harness default with a provider capability check and a fallback | S-6.176 |
| 21 | Credentials unreachable from anything the model can run | Unit 42; Anthropic; Vercel; IBM talk | Demonstrated finding; vendor documentation | `credential_leases.py` keeps the value with the host; `harness_process.py` starts bubblewrap with `--unshare-all` and `--clearenv`; the relay reaches the broker over a Unix socket; S-6.61 plans per-step virtual keys | Checks: the Unit 42 pattern as a fixture; the broker socket gives no more than the step's grant | S-6.168 |
| 22 | Default-on tools are attack surface; scope tools per step | Unit 42; Australian Signals Directorate | Demonstrated finding; guidance | `offer()` names each withheld item; fresh instances start with an empty home | Check: a harness's built-in tools count as tools in the step menu | S-6.168 |
| 23 | Egress allowlist; an unlisted destination is evidence of injection | Unit 42; Vercel; Australian Signals Directorate | Demonstrated finding; vendor documentation; guidance | `web_fetch.py` refuses private addresses and checks every hop; the isolated path unshares the network | Check: deny by default, with refused destinations recorded as security events | S-6.168 |
| 24 | Data access policy at each tool call | A feed post; Australian Signals Directorate; Teradata; Strands | Guidance; vendor self-reported; read in source | Approvals bind to the exact effect; S-6.61 plans the gateway | Engine feature: a per-call policy engine at the gateway, Cedar first | S-6.168 |
| 25 | Regularized self-improvement: edit budget, noise floor, cost rule, leakage review before scoring, pruning | RRSI; Strands Harness Optimizer | Author-reported, code public; vendor self-reported | Self-improvement is a Practitioner task that stages candidates; S-6.77 plans maintenance Loops; learned routers wait for one million runs | Engine feature and library package (leakage review skill) | S-6.172, S-6.175 |
| 26 | Distill harness behavior into a small model | Harness-Zero | Author-reported, code public | S-6.98 plans consented traces as training examples | No new step: a later source for S-6.98 | S-6.98 |
| 27 | Localize a failure to an interaction edge and a fault side | Failure taxonomy | Author-reported | S-6.96 fingerprints; the rule that a failed check is first judged as work, check or environment | Engine feature | S-6.169 |
| 28 | A stateless harness, a session log outside the context, a sandbox started only when needed; one writer and read-only snapshots | Anthropic; Vercel | Vendor self-reported; vendor documentation | Run History is host-owned; each step has its own folder; scoped views of the task working folder are not built | No new step: recorded for the task working folder work | none |
| 29 | Pin and record harness versions; refuse an unsupported session version | A feed post; Unreal Agent; Australian Signals Directorate | Post; read in source; guidance | Recipe records carry digests; S-6.31 pins its first profile | Existing steps | S-6.31, S-6.80 |
| 30 | A long-context inference runtime | Subconscious | Vendor self-reported | Customers bring their own model access | A benchmark arm | S-6.173 |
| 31 | Checks for published items: trace tampering, credential reach, leakage, unbounded loops, silent partial failure | Trace tampering paper; Unit 42; RRSI; failure taxonomy | Author-reported; demonstrated finding | S-6.45 plans a malicious-skill regression set; the Community tier requires automated checks and one independent review | Checks added to the package review and the regression set | S-6.175 |

## Where the changes sit in Baltor

Nothing here adds a runtime type. Each change is work owned by a Loop, an
engine behind an existing kind of slot, or a record. Each step of a task can
run in its own freshly started harness instance, as the
[complete behavioral explanation](../../ASTRA.md#complete-behavioral-explanation)
describes.

```text
Operational runtime type
└── Loop (the only executable graph vertex)
    ├── Role: Practitioner
    │   ├── Starting Practitioner Loop for the customer's task
    │   │   └── each step: one fresh harness instance (step_executor slot, S-6.31)
    │   │       ├── working directory files: stable-first composition engine (S-6.166)
    │   │       ├── provisioning decision: typed-decision engine (S-6.171)
    │   │       ├── compaction policy slot: native, drop-only proxy, model summary, fresh restart (S-6.170)
    │   │       └── Baltor harness defaults: offload, asynchronous tools, constrained output, progress bound (S-6.176)
    │   └── self-improvement Practitioner task: regularized candidate selection (S-6.172)
    ├── Role: Intelligence
    │   └── Intelligence Item Loops: harness engineering package family (S-6.175)
    └── Role: Solution
        └── unchanged

Internal runtime mechanics (not graph vertices)
├── step proxy and broker: append-only exchange log, live limits, reasoning items (S-6.167)
├── step reach controls: credentials, built-in tools, egress, data policy per call (S-6.168)
├── Run History: token record version 2 by billing class, cost per accepted step (S-6.165)
└── failure records: interaction edge, fault side, repair owner (S-6.169)

Evidence and presentation
├── harness efficiency benchmark with and without Baltor (S-6.173)
└── efficiency page evidence section (S-6.174)
```

## What this means for people who publish into Baltor

The owner asked for a way for people to publish skills, tools and scripts.
The publishing flow belongs to its own line of work. These sources add
checks that any published item must pass before it is served in either tier:

- a skill that tells the agent to delete or edit its session trace is
  refused (the trace tampering paper induced deletion with such a skill);
- a skill or script that reads process memory, the environment or
  credential files, or that sends data to an undeclared destination, is
  refused (the Unit 42 pattern);
- a harness edit or skill that names specific tasks, carries answers, reads a
  grader or loops without an exit is refused (the RRSI critic's rules);
- a tool wrapper that reports success when part of the work failed is
  refused (the taxonomy's tool wrapper example);
- a tool declares how large its output can be and what it does beyond that.

S-6.175 adds these cases to the review of every package and to the
malicious-skill regression set of S-6.45.

## Proposals added to the roadmap

| Step | What it builds | Boundary | Named check |
|---|---|---|---|
| S-6.165 | A token record version 2 with uncached input, cache read, cache write, output and reasoning tokens kept apart, a dated price per billing class, and cost per accepted step | `core/run_history_usage.py`, `core/opencode_harness_adapter.py`, `core/openai_responses_client.py` | A cache read counted as uncached input, a missing class counted as zero and a version 2 record read by a version 1 reader each fail |
| S-6.166 | A stable-first composition engine for step files: shared material first, the step's assignment last, sorted lists, no volatile values, measured against the current engine | `core/instance_instructions.py`, `core/node_provisioning.py` | A timestamp before the shared sections, an unstable list order and a dropped authority section each fail |
| S-6.167 | The step proxy as an independent recorder and live limiter: append-only exchange log written before forwarding, fail closed, live call and token limits, reasoning items preserved | `core/harness_process.py`, `core/harness_process_relay.py`, `core/harness_model_authority.py` | A deleted trace that removes the record, a forward after a failed write, a call past the limit and a dropped reasoning item each fail |
| S-6.168 | Step reach controls: no secret reachable from the step, built-in tools counted in the menu, deny-by-default egress with refused destinations recorded, and a data policy engine at each tool call | `core/harness_confinement.py`, `core/credential_leases.py`, `core/harness_fresh_instances.py` | The Unit 42 pattern, a shell left on, a literal address in an allowed range and a withheld field returned each fail |
| S-6.169 | Failure records with interaction edge, fault side and repair owner, labelled at the earliest unrecovered failure | `core/independent_failure_review.py`, `core/provider_failure_classes.py` | A later symptom labelled, a check fault sent to model repair and a compaction loss blamed on the model each fail |
| S-6.170 | A compaction policy slot with four engines, instruction-survival fixtures and a comparison before any default changes | `core/context_budget.py`, `src/loop_engine/data/engine_slots.yaml` | A summary that drops a do-not-act instruction, a compaction of a compaction and a drop without a digest each fail |
| S-6.171 | A typed-decision provisioning engine that decides which skills, tools and context files the next step receives | `core/opencode_step_provision.py`, `core/decisions/system_one.py` | An item outside the catalogue, a low-confidence answer without fallback and an engine selected without beating the baseline each fail |
| S-6.172 | Regularized selection for improvement Loops: edit budget, noise floor, cost rule, leakage review before evaluation by another family, pruning | `src/loop_engine/data/engine_slots.yaml`, `tools/candidate_review` | An edit naming a task, grader access, a costlier candidate inside the noise band and a same-family reviewer each fail |
| S-6.173 | A harness efficiency benchmark with and without Baltor on the HarnessTax method | `benchmarks`, `case-studies` | Arms that differ in tasks or model, a price list dated after the run and a vendor number shown as a Baltor result each fail |
| S-6.174 | An evidence section on the efficiency page: outside evidence with its limits, Baltor numbers only from run records | `core/service_runtime/web_assets/index.html`, `docs/guides/launch-benefits-and-evidence.md` | A vendor percentage shown as Baltor's, an outside figure without its population and a Baltor number without a record each fail |
| S-6.175 | A harness engineering package family of ten candidates, with review criteria and regression cases | `tools/candidate_review`, `docs/research` | Copied text without a copying licence, a wrapper that silently truncates and a Community label without an independent review each fail |
| S-6.176 | Baltor harness defaults for the Baltor forks and the step executor: file offload, asynchronous tools, constrained output with a capability check, a progress bound | `core/harness_recipes.py`, `src/loop_engine/data/engine_slots.yaml` | A truncation without a file, a blocking long tool, a constrained request without fallback and a default switched on without its comparison each fail |

## Build items for the build phase

### Library packages

Each is a candidate until the review panel (S-6.63) approves it. The licence
basis decides whether a package may carry adapted text.

| # | Package | Kind | Licence basis | Contents |
|---:|---|---|---|---|
| 1 | Harness cost audit | Skill with a script | Original work; Cursor's prompt carries no licence, so no text is copied | Renders real requests, counts tokens by section and billing class, ranks changes by share of spend, removable fraction and quality risk, and writes a report with a revert plan |
| 2 | Cache-stable prefix checker | Script with a skill | Original work | Diffs rendered requests across turns and names volatile values before the cache boundary and unstable tool order |
| 3 | Large-output wrapper | Script | Original work | Runs a command, writes the full output to a file, returns path, size and a short tail, and prints plain text when not attached to a terminal |
| 4 | Drop-only compaction proxy setup | Configuration and instructions | CliffCompaction is MIT; pinned to a commit | Sets up the proxy for Claude Code and Codex, starts in shadow mode, switches the harness's own compaction off, and records the first comparison |
| 5 | Harness edit and skill leakage review | Skill | Adapted from RRSI's Apache 2.0 critic with its notice | Six rejection rules applied to a diff: task leakage, degenerate edits, grader gaming, undeclared bundling, memory leakage and unbounded work |
| 6 | Agent runtime credential and egress check | Checklist with a probe script | Original work from the Unit 42, Anthropic and Vercel findings | Probes what a step's shell can read (environment, process memory, credential files, broker socket) and which destinations it can reach |
| 7 | Trace integrity setup | Instructions with a test | Original work from the trace tampering paper | Records model exchanges outside the agent's reach and shows that deleting the local trace leaves the record intact |
| 8 | Failure localization | Skill | Original rewrite; the arXiv licence does not allow copying | Labels the earliest unrecovered failure by interaction edge and fault side and names the repair owner |
| 9 | Tool error classification helper | Script with a skill | Original work | Sorts tool errors into invalid arguments, unexpected environment, provider error, timeout, user abort and unknown, per tool and per model |
| 10 | Long-running command wrapper | Script | Original work | Start, status, log and stop for a long command, with a heartbeat file and a final result record |

### Product features

- Token accounting by billing class and cost per accepted step (S-6.165).
- A stable-first composition engine for step files (S-6.166).
- An append-only, fail-closed exchange log and live limits in the step proxy
  (S-6.167).
- A data policy engine at each tool call, Cedar first (S-6.168).
- A compaction policy slot with native, drop-only, model summary and fresh
  restart engines (S-6.170).
- A typed-decision provisioning engine (S-6.171).
- Regularized selection for improvement Loops (S-6.172).
- Baltor harness defaults: file offload, asynchronous tools, constrained
  output with a capability check, a progress bound (S-6.176).

### Checks

- A step process that reads process memory, the environment, the step folder
  or the broker socket obtains no secret and no more than its grant
  (S-6.168).
- A harness's built-in shell or file tool is off in a step whose menu omits
  it (S-6.168).
- A refused network destination is recorded as a security event, including a
  literal address and a mismatched host name (S-6.168).
- Deleting a harness's local trace leaves the host record intact, and a
  failed record write stops forwarding (S-6.167).
- Owner instructions and their reasons survive every compaction engine
  (S-6.170).
- Reasoning items round-trip through relays unchanged (S-6.167).
- Regression cases for published items: trace deletion, credential reach,
  task leakage, unbounded loops, silent partial failure (S-6.175).

### Website and evidence

- The efficiency page cites outside evidence with its exact population and
  limits, and shows Baltor numbers only from run records (S-6.174).
- The benchmark with and without Baltor on the HarnessTax method, cheap
  models first (S-6.173).

## Decisions made and why

- **Measure before optimizing.** Every source that reports a saving measured
  cost per task or per run against a price list, and Cursor and Teradata
  explain their savings through billing classes such as cached input and
  reasoning. Baltor cannot tell whether a change helps until it records those
  classes apart, so S-6.165 comes first and S-6.166, S-6.170 and S-6.176
  depend on it.
- **Treat vendor numbers as claims, not evidence.** The feed's headline
  numbers shrank or changed meaning when their sources were read. Baltor's
  pages cite only independent or peer-checkable outside results, with their
  populations and limits, and Baltor's own records.
- **Make compaction a slot instead of choosing a winner.** Two credible
  camps disagree: model summaries (Strands, Cursor) against drop-only
  compaction (CliffCompaction, the Australian Signals Directorate). The
  failure taxonomy's examples show the risk of summaries. The harness's
  native compaction stays the default until the comparison of S-6.170 says
  otherwise.
- **Adapt permissive code, rewrite the rest.** RRSI's critic (Apache 2.0)
  and CliffCompaction (MIT) can be adapted with attribution and pinned
  provenance, so their packages may enter the Community tier after the
  automated checks and one independent review. Cursor's prompt and the
  papers' text carry no copying licence, so the packages built from them are
  original rewrites.
- **Hold the critic to Baltor's family rule.** RRSI's critic shared the
  proposer's model family. Baltor's leakage review runs on a family other
  than the proposer's.
- **Extend existing steps where they already own the boundary.** Tool schema
  placement (S-6.93, S-6.44), step result handoffs (S-6.31), long-tool
  contracts (S-6.94), harness version records (S-6.80) and distillation data
  (S-6.98) gain evidence from this record without new steps.
- **Step numbers.** The new steps are S-6.165 to S-6.176. At commit time
  `main` held S-6.110 to S-6.118, S-6.120, S-6.140 to S-6.157 and S-6.160 to
  S-6.164, and lines of work in flight claimed S-6.119, S-6.121 and S-6.130
  to S-6.134, so this record takes the first free block of twelve after
  them. Two lines had already collided on S-6.100.

## What this record does not establish

- It does not show that any technique improves Baltor. No Baltor run was
  made, and every outside number is its authors' own.
- It does not verify the Australian Signals Directorate's PDF attachment,
  only the web text of the same publication in the Internet Archive capture.
- It does not check whether dlab's harness repository is public, whether
  Harness Optimizer's results reproduce, or whether Microsoft's Copilot
  Studio documentation matches the posts about it.
- It does not decide how community publishing works; it only adds checks for
  whatever that flow serves.
- It does not claim that Baltor's isolated harness path is the path every
  customer uses today. The per-step executor (S-6.31) and the per-step
  credential broker (S-6.61) are still being built.
