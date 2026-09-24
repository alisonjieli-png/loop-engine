# Review throughput evidence, September 24, 2026

Roadmap step S-6.63. The engine and panel changes are recorded in the
[review engines record](../../docs/verification/REVIEW-ENGINES-AND-BATCHING-2026-09-24.md).
Nothing here is approved, staged or served.

```text
review-throughput-2026-09-24
├── probes/review-engine-probes.json
│   └── two Codex probes (usage limit, no model response) and one Claude probe
└── overnight-attribution/
    ├── attribution.json   every overnight candidate of the zhipu, moonshot and
    │                      nvidia lanes: lane, model, declared family, file kind,
    │                      recorded write time and exact bytes by digest
    └── ideas/             the idea record each producer was asked to answer,
                           one file per idea, cited as the package's source
```

## Probes

| Probe | Route | Outcome |
|---|---|---|
| codex-1 | `codex exec --json`, the panel's arguments without `--ephemeral` | The service refused for the subscription's usage limit, until September 29 at 5:24 PM. The session record names the thread once and the pinned model `gpt-6-sol`. |
| codex-2 | the same with `-c project_doc_max_bytes=0` | The same refusal. The owner's global instruction pointer (624 characters) was still sent, so the setting does not keep it out. |
| claude-1 | `claude -p --safe-mode --tools '' --output-format json --no-session-persistence --model claude-opus-5-5` | Answered `READY`; model usage names only `claude-opus-5-5`; 2 input, 4 output, 531 cache read and 1,311 cache write tokens; a list cost of 0.0107 United States dollars, charged to the owner's subscription, not billed separately. |

The Codex probes count against the Codex ceiling of 300 calls (2 used, no
model response). The Claude probe counts against the owner's cap of 150 Claude
review calls (1 used).

## Overnight attribution

The overnight candidate batch
(`/home/username/loop-engine/.loop-engine-dev/overnight-2026-09-24/batch`)
was read without being changed while it kept running for its other lanes.
`tools/native_proposals_from_overnight_candidates.py attribute` attributed
141 candidates: 131 skills and 4 harness routing files from the
`glm-5.3-flash` lane (family zhipu), 3 harness routing files from the
`kimi-k3` lane (family moonshot) and 3 harness routing files from the
`nemotron-3-nano:30b` lane (family nvidia). No file was left unattributed.

The file kind each producer was asked for depends on the matrix in effect at
the recorded write. The first matrix (`matrix.json`, every idea a skill) took
effect at its file time, 04:49:38 UTC, and the ten-thousand matrix
(`matrix-10k.json`, seven file kinds) at its file time, 07:45:19 UTC; the
supervisor that reads it started at 07:46:00 UTC. Nine files whose ideas are
subagents in the later matrix were written before 05:03 UTC under the first
matrix, so they were asked for and are attributed as skills.

The `kimi-k3` lane's model is refused on every route by the repository's model
policy. Its three candidates are reviewed as bytes like any other; admitting
them to a release waits for the model policy's owner, because the policy is
outside this panel.
