# Blog, Team and logo integration preview

This is a local, draft-only content and interface artifact based on committed
source abcad4f8ce346e7d0759ccad703e0111574148a6. It does not add live service
routes, change the current header or publish an article. The owner requested
independent work on blog and Team pages and supplied Taylor Amarel as the
person to show, with engineering judgment for the draft.

Open [the blog preview](site/index.html), [Team](site/team.html), or
[logo integration study](site/brand.html). The three complete article drafts
are linked from the blog. Every page carries a draft banner and noindex
metadata. There is no newsletter form, analytics call, account operation or
invented customer result.

## Content and facts

The [draft source](content.json) holds the articles and Taylor's profile.
The Team page uses the supplied name, a descriptive Building Baltor label,
an initials portrait and a project-focused biography. It adds no career,
education, location, staffing or investor claims. The byline Baltor names
the project, not a fabricated individual author.

The featured experiment article uses the committed
[data cleanup report](../../case-studies/data-cleanup-with-and-without-baltor/REPORT-2026-09-22.md)
and [frozen design](../../case-studies/data-cleanup-with-and-without-baltor/DESIGN.md).
An independent factual read checked its 143-row population, 38 phone rows,
72 counted steps, 225 requests, model and harness versions, percentages and
pass counts. The draft includes the population author's knowledge of the
items and the fact that the frequency of difficult cases affects the effect
size. It does not infer a production error rate.

The phone instruction was removed from the homepage example but remained
offered at the current audit. Its exact catalogue disposition needs
independent adjudication before publishing the article. That open gate
appears in the article's draft-review panel. A download proves receipt of
bytes; it does not establish tool operation, model use or task acceptance.

The other articles explain what native harnesses read and what a larger
library count should represent. They cite the
[Agent Skills specification](https://agentskills.io/specification) and the
[official protocol registry](https://modelcontextprotocol.io/registry/about).
No scraped source text is republished. Current inventory and client-support
claims must be refreshed before publication.

## Reproduction and checks

Run from this worktree's repository root:

    python3 artifacts/editorial-pages-2026-09-23/render_preview.py
    python3 -m http.server --bind 127.0.0.1 --directory artifacts/editorial-pages-2026-09-23/site 41487

The renderer uses only the standard library, escapes text, permits only named
block kinds and safe article slugs, and accepts explicit draft content only.
It copies the current site's mark and locally served Geist fonts together
with their distribution notices. The visual tokens match the current site.
The logo study shows existing candidates beside the current mark at actual
16- and 32-pixel sizes; it makes no new brand choice.

The [browser record](browser-check.json) checked six routes at desktop and
phone widths: all twelve page loads returned 200, every image loaded, and
there were no page errors or horizontal overflows. The
[desktop blog](screenshots/index-1440.png), [phone blog](screenshots/index-390.png),
[desktop Team](screenshots/team-1440.png), and [phone Team](screenshots/team-390.png)
screenshots were inspected. This establishes the preview only, not a live
customer journey.

## Claude Code integration

Reuse the existing public page boundary and application shell. There is no
need for a separate content-management service to publish three reviewed
articles. Add the blog index, exact article routes and Team route through
the existing web page registry and navigation after review.

The current browser sign-in lives in page memory. A standalone-page link
that reloads the application can discard that session, so integration must
test navigation while signed in. Reuse the existing single-page route
mechanism or deliberately resolve session behavior before adding links.
Do not copy the preview header into production as a second account shell.

Before publishing, check article-specific title and description, deep links,
back navigation, source links, keyboard use, phone layout and the current
invitation action. An unknown article address should return the existing
404 page. Add sitemap or feed entries only for published articles. The
draft gate panel and noindex metadata belong to review, not the published
article. User-provided team changes should update the one profile record.

The owning roadmap work is S-6.33 for public pages, S-6.36 for factual
marketing material, and S-6.47 for benefit evidence. The roadmap remains
the task authority.
