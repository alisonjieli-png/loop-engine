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
python3 tools/refresh_research_sources.py --online
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
proxies or credentials. Page hosts are an explicit small allowlist in the
tool; adding a new host requires source review and a code change. A move,
authentication requirement, rate limit, or unavailable source appears as a
failure for human review.

Review each changed source at its recorded revision before revising a research
claim. Save the new research assessment under a new dated name, record the
observed and untested parts separately, and update the existing roadmap step
if the finding affects work. A changed hash alone does not show a meaningful
product change. The watcher does not download repository content, scrape
bulk material, create intelligence, run models, qualify harnesses, change
runtime authority, or publish anything. Intelligence ingestion and review
use the existing candidate and approval path.

Run the focused checks with:

```bash
python3 -m unittest tools.test_refresh_research_sources
```
