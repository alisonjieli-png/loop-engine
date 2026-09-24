# Overnight candidate batch handoff, September 24, 2026

Kind: dated handoff record for the running candidate generation batch.
Written by Claude Code (GLM 5.3) so that Claude Code, Codex, GPT Astra or
any other session can monitor, restart or collect the batch without
re-deriving any of it. The
[commit, push and release authority](../../AGENTS.md#commit-push-and-release-authority)
section of AGENTS.md remains the one statement of authority, and
[roadmap.yaml](../roadmap/roadmap.yaml) (S-6.40, S-6.53) remains the
task authority. This is a snapshot, not new authority.

**Scale change, September 24 (owner direction):** the batch grew from
1,000 to **10,000 ideas** with a **12,000-call ceiling**, on **six
lanes** (five Ollama Cloud models plus Tactical), grounded in the
**expanded stratified occupation inventory** (175 occupations across 22
SOC major groups with 3,500 real O*NET task statements, up from 10
occupations and 179 statements). The completed ~500 candidates from
the 1,000-scale run were kept by journal replay. Diversity also grew
along the file-kind axis: each method hypothesis now generates its
best-fit one of seven harness file kinds (skill, harness routing file,
subagent definition, workflow recipe, rules file, plugin manifest,
hook).

## What is running and where

A supervised batch is generating **10,000 harness intelligence
candidates** from the deterministic idea matrix, across **six separate
OpenCode setups** (lanes). Everything lives under one run root:

```text
/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/
├── matrix.json          the first 1,000-scale matrix (10-occupation)
├── matrix-10k.json     the active matrix over the expanded inventory
│                        (same 29,625 method identities; applicability
│                        now rotates 175 occupations and 7 file kinds)
├── start-batch.sh       restartable launcher (resolves the Tactical key
│                        from the system keyring inside the process)
├── batch/
│   ├── journal.jsonl    one dispatch event before each model call, one
│   │                    outcome event after; the recovery source of truth
│   ├── status.json      atomic status record, rewritten after every idea
│   ├── supervisor.pid   pid of the live supervisor (removed at clean exit)
│   ├── candidates/      one Markdown file per generated candidate, under
│   │   └── <lane-id>/<idea-id>.md
│   └── manifest.json    written when the batch completes
├── lanes/               the four separate OpenCode setups, each with its
│   └── <lane-id>/       own opencode-config/, opencode-data/, workspace/
├── supervisor.log       the detached supervisor's output
└── watchdog.log         the cron watchdog's output
```

The run root is gitignored by design; after completion, export counts and
evidence into `artifacts/` (the batch directory itself stays a run
artifact, like the smoke run recorded in
`artifacts/opencode-generation-lanes-2026-09-24/README.md`).

## The six lanes

| Lane | Provider | Model | Endpoint |
|---|---|---|---|
| lane-ollama-gpt-oss-20b | Ollama Cloud | gpt-oss:20b | https://ollama.com/v1 |
| lane-ollama-gemma4-31b | Ollama Cloud | gemma4:31b | https://ollama.com/v1 |
| lane-ollama-glm-53-flash | Ollama Cloud | glm-5.3-flash | https://ollama.com/v1 |
| lane-ollama-kimi-k3 | Ollama Cloud | kimi-k3 | https://ollama.com/v1 |
| lane-ollama-nemotron-30b | Ollama Cloud | nemotron-3-nano:30b | https://ollama.com/v1 |
| lane-tactical-gemma4 | Tactical | gemma-4-coding-abliterated | https://ai.tacticalengineering.net:6969/v1 |

No local model is installed, started or called. Any lane naming a local
endpoint is refused before a process starts. The Tactical key is never
in a file or the environment; the runner resolves it from the system
keyring through `tools/operator_credentials.py` (reference
`tactical-model-generation`) inside each process. The Tactical endpoint
serves a Cloudflare Origin certificate issued for `ai.iamretarded.net`,
so the lane runs its own subprocess with Node hostname TLS verification
disabled, the owner-documented trust model for that endpoint.

## How to check progress

```bash
# The live status record (updates after every idea):
/home/username/loop-engine/.venv/bin/python tools/overnight_candidate_batch.py \
  --batch-directory /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch \
  --matrix /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/matrix-10k.json \
  --lane-root /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/lanes \
  --ideas 10000 --max-calls 12000 --status

# Or directly:
python3 -c "import json; print(json.dumps(json.load(open(
  '/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch/status.json')), indent=1))"

# Is the supervisor alive?
cat /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch/supervisor.pid
ps -p $(cat /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch/supervisor.pid) -o stat=,etime=
```

Status fields: `state` (incomplete/complete), `candidates`, `failed`,
`remaining`, `calls_used`/`calls_ceiling`, `ceiling_reached`, and per
lane: `candidates`, `failed`, `degraded`, `consecutive_failures`.

## Recovery, fallbacks and monitoring (all proven live)

- **Crash recovery**: every dispatch is journaled before its model call
  and every outcome after; on restart the supervisor replays the journal
  and skips every idea that already has a terminal outcome, so no model
  call is ever repeated silently. Proven live: a supervisor killed
  mid-run resumed with all prior candidates intact and 0 repeated calls.
- **Provider outage**: each idea gets 3 attempts with declared outage
  waits (60, 180, 300 seconds). A third failure records
  `failed_provider` and the batch moves on; the run never ends on a
  fixed attempt count.
- **Shape-failure fallback**: a candidate failing the deterministic
  shape check is retried once with a stricter prompt.
- **Lane degradation**: 5 consecutive failures mark a lane `degraded`
  in the journal and its unstarted ideas are reassigned round-robin to
  healthy lanes.
- **Call ceiling**: 12,000 calls for 10,000 ideas. At the ceiling the
  batch records `ceiling_reached` and stops clean; that is a clean
  stop, not a crash.
- **Watchdog**: cron runs `--watchdog` every 10 minutes (entry marked
  `BEGIN/END OVERNIGHT CANDIDATE BATCH WATCHDOG 2026-09-24` in the
  user crontab). It reads `status.json`: `complete` or no work remaining
  means do nothing; a live `supervisor.pid` means do nothing; otherwise
  it restarts the supervisor detached and journals a
  `watchdog_restart` event.

## How to restart manually (if cron is disabled or you prefer hands on)

```bash
setsid nohup /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/start-batch.sh \
  >> /home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/supervisor.log 2>&1 < /dev/null &
```

Use `setsid`: a plain `nohup` from a closing shell session still dies
with the session's process group (observed and repaired on September 24;
the journal recovered all 8 prior candidates with no repeated calls).

## When the batch completes

1. Read `batch/manifest.json` (written at completion) and `status.json`.
2. Export the measured numbers (candidates, failures, calls, per-lane
   yield, shape-retry rate) into a new `artifacts/` record with a new
   name. Keep failed attempts beside successors.
3. The candidates are **candidate material only**: no independent
   review, admission, staging or serving has happened. A producer never
   approves its own work. The existing candidate staging contracts
   (`tools/prepare_harness_candidates.py`,
   `tools/stage_intelligence_candidates.py`) and the independent
   admission process own the next step.
4. Update the S-6.53 evidence line in `roadmap.yaml` and regenerate
   `CONTINUATION-STATUS.md`
   (`python tools/build_continuation_status.py`).
5. Remove the watchdog crontab entry (the lines between the
   `BEGIN/END OVERNIGHT CANDIDATE BATCH WATCHDOG 2026-09-24` markers).

## Owning tools (all committed on main, with known-wrong checks)

- `tools/harness_idea_matrix.py` (+21 checks): deterministic
  datatype x operation x use-case matrix over the pinned O*NET 31.0
  grid; 29,625 unique method hypotheses; facets never multiply methods.
- `tools/opencode_generation_lanes.py` (+14 checks): the four separate
  OpenCode setups, remote-endpoint enforcement, scrubbed per-lane
  environments, shape checks, the tactical TLS model.
- `tools/overnight_candidate_batch.py` (+17 checks): the supervisor,
  journal, stratified selection, recovery, degradation, ceiling and
  watchdog described above.

Commits: `c038e26b` (matrix and lanes), `f6a7fb2c` (supervisor). Both
pushed to `origin/main` with their checks passing.

## Open cautions for the next session

- The shared checkout `/home/username/loop-engine` still carries other
  sessions' uncommitted edits (CLAUDE.md, docs, roadmap and more).
  They are not this batch's work; resolve ownership before touching
  them. The two zero-tolerance conformance gates that fail on the dirty
  tree pass on a clean export of `HEAD`.
- The 10,000 candidates will not fit the current hosted serving (the
  100,000-row probe recorded the limits); they stay in the run
  directory until the S-6.62 store/release work lands.
- Review throughput, not generation, is the constraint for the 10,000
  target. The batch measures precheck pass rate and per-lane yield;
  independent reviewers are named separately before any admission.
- Do not run `git pull` or rebase this shared checkout casually: the
  uncommitted work of other sessions lives here.