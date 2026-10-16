# Repeatable external source checks

This development tool supports roadmap step `S-6.22`. It watches a small set
of official repositories and pages in
[`tools/research_source_watch.json`](../../tools/research_source_watch.json).
The manifest records each source's URL, license review state, and related
roadmap step. The source list is a starting point, not an approved library or
a claim that any client works with Loop Engine.

Run the offline validation first:

```bash
python3 tools/refresh_research_sources.py
```

To check public sources, opt in to bounded read-only network requests:

```bash
python3 tools/refresh_research_sources.py --online --max-online-sources 50
```

Each invocation writes a new JSON report in `artifacts/research-source-watch/`.
An existing result is never replaced. Offline reports say `unknown` because
they fetch nothing. Online reports record the retrieval time, exact Git commit
or page content digest, available `ETag` and `Last-Modified` validators,
change status relative to the latest successful local observation or the
manifest's exact baseline, and a failure when a check did not complete. Each
report includes the manifest and tool digests used for that attempt.
The tool reads at most 12 sources by default, with a five-second timeout and
512 kilobytes per response. It does not follow redirects or use environment
proxies. Its only credential is an optional read-only token in `GITHUB_TOKEN`,
sent to `api.github.com` alone. The daily workflow passes its own token,
because GitHub allows 60 unauthenticated requests an hour per address and a
shared runner can spend that before fifty sources are read; a spent limit is
reported as `rate_limited`. Page hosts are an explicit small allowlist in the
tool; adding a new host requires source review and a code change. A move,
authentication requirement, rate limit, or unavailable source appears as a
failure for human review.

The current manifest fills its fifty-source ceiling. Superpowers and Context
Mode occupy the final two slots because their planning, verification and
context behavior directly address the owner's repeated-work investigation.
Other reviewed leads stay in the research backlog; adding them requires a
deliberate rotation or a separately qualified coverage design, not a larger
unchecked request limit. Watching a restricted-licence implementation does
not authorize hosting it. Source inspection, adoption and measured benefit
remain separate.

Review each changed source at its recorded revision before revising a research
claim. Save the new research assessment under a new dated name, record the
observed and untested parts separately, and update the existing roadmap step
if the finding affects work. A changed hash alone does not show a meaningful
product change. The watcher does not download repository content, scrape
bulk material, create intelligence, run models, qualify harnesses, change
runtime authority, or publish anything. Intelligence ingestion and review
use the existing candidate and approval path.

The daily research-watch workflow keeps the report, summary and command log
as artifacts. It opens or updates the existing research issue when a source
changes or collection coverage fails. A successful unchanged watch adds no
issue comment. A failed check does not establish that a source changed or
disappeared.

The summary records changes and coverage errors separately. A missing or
malformed report leaves the change count unknown and records a monitoring
error. The workflow retains the watcher's exit status and fails degraded
runs after the artifact and issue steps. It makes no model call.

Run the focused checks with:

```bash
python3 -m unittest tools.test_refresh_research_sources tools.test_summarize_research_watch
```
