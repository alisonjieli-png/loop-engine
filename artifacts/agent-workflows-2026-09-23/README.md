# Reusable development workflows

Kind: development tooling, September 23, 2026. Roadmap step S-6.76 and
delivery package D-29 own this folder.

These five scripts orchestrate several agents in one Claude Code session. They
are development operations for the people and agents who build Baltor. They
are not part of the product runtime, they are not Loops, and they schedule
nothing by themselves. Roadmap step S-6.77 turns the recurring ones into
Practitioner Loops later.

The same patterns ran by hand on September 23, 2026: a state review with ten
readers and verifiers, the five research lines that an earlier session lost to
a usage limit, a library wave of original packages, harness discovery with
retrieval and health studies, and the functional component standard research.
These files are the parameterized versions of those runs.

## What each workflow does

| Workflow | What it produces | Effect policy |
|---|---|---|
| [state-review.js](state-review.js) | A current-state record, a comparison of every agent session, the ordered work with owners and collision risks, and a completeness critique | Reports only; no repository or provider change |
| [library-wave.js](library-wave.js) | A wave of original multi-file harness packages with a manifest, pre-check logs, critiques, repairs and retrieval probes | Candidates only; nothing is approved, released or served |
| [harness-discovery.js](harness-discovery.js) | Harnesses found round by round until a round finds almost nothing new, a profile of the files and settings each reads, and a fork-or-wrap study | Research and candidate profile changes only |
| [research-sweep.js](research-sweep.js) | Hands-on research lines with saved trials, an adversarial check of each, and one successor research record draft | Research and draft records only |
| [plan-validation.js](plan-validation.js) | Plans from several angles, scores from independent judges, and one validated order of work | Draft plan only; the roadmap changes through review |

Every workflow checks its findings adversarially before it synthesizes them,
and every agent it starts follows AGENTS.md and the repository's CLAUDE.md.

## How to run one

Run a workflow from Claude Code with the Workflow tool, passing the script path
and its arguments. Every path is an argument, so the scripts carry no machine
paths. For example, a state review takes:

```json
{
  "repo": "<absolute path of the shared checkout>",
  "main_ref": "origin/main",
  "out": "<absolute path of a new report folder>",
  "sessions": "<which agent sessions are active, their worktrees and transcripts>",
  "extracted": "<optional file of owner prompts already extracted>",
  "live_hosts": ["baltor.ai", "www.baltor.ai", "app.baltor.ai", "docs.baltor.ai"]
}
```

The comment block at the top of each script lists its arguments. Write the
output folder outside the repository, then carry reviewed results into the
repository like any other change.

## Rules every run keeps

- Readers and researchers never change a repository, a worktree or a provider.
  Generators write only to their output folder.
- A producer never approves its own work. Library candidates go to the
  independent review panel of roadmap step S-6.63.
- Model calls are allowed only where the arguments grant them, within the
  recorded authority, and each call is recorded with its model, usage and
  outcome.
- A capped run logs what it did not cover.

## Recurring schedule

The roadmap's `recurring_reviews` list declares when each workflow should run
and its effect policy: a daily state review, a nightly library wave, a weekly
harness profile refresh, a weekly research and news sweep, a weekly plan
validation and a weekly restore drill. Their scheduling state stays
`not_scheduled` until a scheduler that can run them against the build machine
is chosen and its first runs are recorded.
