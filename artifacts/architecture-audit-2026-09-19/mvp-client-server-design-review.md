# Client and server diagram redesign

Date: 2026-09-19. Scope: the standalone, project-owned architecture diagram.
No deployment, runtime source change, account, payment, or live service call.

## Delivered

Open [the redesigned diagram](mvp-client-server.html).

The page separates four views: overview, sign-in and access, material
retrieval, and local execution. Each contains three to six boxes. A
keyboard-accessible selection opens the component's scope and implementation
limits. The diagram pairs customer, Loop Engine, and external-service
ownership labels with restrained boundary colors.

ELK.js calculates layout and orthogonal routing. The page is not a stock
Mermaid theme or an embedded screenshot. The renderer measures actual text
before laying out the boxes. Narrow views reflow vertically at full text size.
Optional cross-boundary connections remain in the visible text connection list
on narrow screens. The local execution view keeps the remote model outside
the customer-controlled runtime.

The humanizer pass used the repository's neutral technical voice. Labels name
actions such as "Sign in", "Select exact material", and "Record Run History".
Full descriptive terms remain where shortening would blur meaning. No
marketing claims or invented humanization score were added.

The visualization skill distinguishes standalone project files from inline
conversation visuals. This deliverable is a normal HTML document with scoped
assets. There is no Sites configuration, and nothing was published.

## Content checks

The diagram explicitly separates these facts:

- Vercel, Supabase, Stripe, the website, and hosted billing are proposed.
- The Python provisioning domain has local implementation evidence.
- Remote provisioning HTTP and OAuth are not implemented.
- A plain Model Context Protocol client retrieves material without enforcing
  full Loop Engine graph governance.
- The local Loop Engine path owns graphs, subgraphs, atomic assignments,
  execution governance, verification, Runtime Memory, and Run History.
- Run History belongs to Loop Engine. Remote models are external,
  separately authorized services.
- Supabase Postgres plus pgvector for metadata/search and a private bucket for
  body bytes are proposals, not current integrations.
- Current retrieval defaults are SQLite FTS5 and hash vectors. model2vec and
  LanceDB are optional.
- Retrieval, native loading, use, independent verification, and promotion are
  separate observations. Payment never promotes a candidate.

The complete runtime classification is available in a compact disclosure
before the specialized diagrams. Captions distinguish passive software boxes
and workflow steps from executable Loop vertices.

## Package and provenance

The diagram uses the published elkjs version 0.12.0 browser bundle. The
upstream project documents its browser bundle and layout interface.
[ELK.js primary repository](https://github.com/kieler/elkjs).

The layered algorithm supports orthogonal routes and port constraints. Those
options keep connectors outside measured boxes.
[Layered algorithm](https://eclipse.dev/elk/reference/algorithms/org-eclipse-elk-layered.html),
[edge routing](https://eclipse.dev/elk/reference/options/org-eclipse-elk-edgeRouting.html).

Primary documentation was inspected on 2026-09-19. The npm registry command:

    npm view elkjs@0.12.0 version license dist.integrity --json

returned version 0.12.0, license EPL-2.0 OR GPL-3.0-or-later, and this package
integrity value:

    sha512-YZcKynxVxYoKIOEpywEPwCFdg+BTbxQRNf3pbwdDCvc8O3kQD8bmIwSxKU1eOTVc4Xo+VG9Te+575mlfvOrhEQ==

The page loads one version-pinned static asset:

    https://cdn.jsdelivr.net/npm/elkjs@0.12.0/lib/elk.bundled.js

Its exact browser integrity attribute is:

    sha384-ww57TDqx4cGknIavPm0QKO+aygLUR1BLSn2Vhbnt1XdYKWcwLyWTFKX7aZMaKIi2

The package is not vendored. The page links to its upstream repository.
Application code makes no fetch, XMLHttpRequest, WebSocket, or service call.
The content security policy forbids connections. The observed request log
contains only owned HTML, CSS and JavaScript and the pinned static package.
If that package cannot load, the page says so and preserves readable boxes
and text connections without claiming automatic layout succeeded.

## Browser and adversarial verification

Reproduce with the existing project browser test driver:

    node artifacts/architecture-audit-2026-09-19/mvp-client-server-checks.mjs

The test uses fresh headless Chrome at /opt/google/chrome/chrome through the
existing showcase/node_modules/playwright-core package. It opens only the
owned local diagram. No browser account or production page is involved.

Final [machine-readable results](mvp-client-server-checks-final.json):

| Check population | Result |
| --- | --- |
| Four views × six widths × two themes | 48/48 |
| Browser control groups, including the matrix aggregate | 14/14 |
| False or broken content variants | 8/8 refused |
| Planted overlap and clipping | both detected |
| Minimum measured contrast among tested card/status text | 5.47:1 |
| Runtime JavaScript errors | 0 |
| Unexpected requests | 0 |

Widths are 320, 360, 736, 1024, 1280, and 1440 pixels. Checks inspect real
browser rectangles, node/edge intersections, label/box intersections,
horizontal overflow, clipping, minimum card text size, contrast, and selected
view. Mobile support does not shrink a fixed desktop drawing.

Other controls cover keyboard activation and tab order, opening details into
the viewport, Escape and focus return, theme changes, rapid view changes,
blocked package loading, long unbroken labels, and markup-shaped text.
Markup stays text and does not execute.

False-content controls change a vendor to implemented, put bodies in Postgres,
claim pgvector as the current default, assign Run History to a model provider,
claim remote authorization is implemented, change a visible vendor status,
move a model into the product boundary, or create a dangling connection.
Every variant receives an explicit validation failure.

### Retained failed attempt

The [first browser sweep](mvp-client-server-checks-attempt-1.json) passed 47 of
48 layout cases. A pending resize callback rebuilt overlapping boxes during
the 1024-pixel light overview check. That failure was not ignored or counted
as a successful layout. Explicit rendering now cancels queued resize work;
the generation check prevents an older layout from replacing a newer view.
Subsequent complete sweeps passed all 48 cases. The first failure remains
beside the final evidence.

### Visual inspection

Real screenshots were generated and visually inspected for all four views,
desktop and mobile, and both themes during iteration. The final run
regenerated sixteen captures:

    mvp-client-server-{overview,sign-in,retrieval,execution}-1440-light.png
    mvp-client-server-{overview,sign-in,retrieval,execution}-1440-dark.png
    mvp-client-server-{overview,sign-in,retrieval,execution}-360-light.png
    mvp-client-server-{overview,sign-in,retrieval,execution}-360-dark.png

Examples: [desktop overview](mvp-client-server-overview-1440-light.png),
[dark local execution](mvp-client-server-execution-1440-dark.png),
[mobile retrieval](mvp-client-server-retrieval-360-light.png).

This is one-browser presentation verification. It is not a full assistive
technology audit, native-device qualification, vendor integration test, or
production onboarding acceptance.

## Preservation and changed paths

The rejected HTML is preserved as
[mvp-client-server-rejected-2026-09-19.html](mvp-client-server-rejected-2026-09-19.html).
The original rendered Markdown and three SVG files were left unchanged.
The new page does not embed those rejected renders.

Only files with the mvp-client-server prefix in this artifact directory were
created or changed:

    mvp-client-server.html
    mvp-client-server.css
    mvp-client-server.data.js
    mvp-client-server.js
    mvp-client-server-checks.mjs
    mvp-client-server-checks-attempt-1.json
    mvp-client-server-checks-final.json
    mvp-client-server-design-review.md
    mvp-client-server-rejected-2026-09-19.html
    sixteen final screenshots listed above
    mvp-client-server-overview-desktop-light.png [first visual working capture]

The architecture Markdown, runtime source, managed records, deployment
configuration, and other agents' files were not edited.

Final source identities:

    69d9cbe817b8e9f8484347c379a850eaf71e41c293efb6fb447d712c84fcdc08  mvp-client-server.html
    13a805b73de3535d255844ff9b0fff31f53569dda2030080a7d7474ee8ae2a05  mvp-client-server.css
    a1a757704143b1c547a297f4c2831c60bfba5ba7dd2994dc74471abe569429fb  mvp-client-server.data.js
    38fb756fe46267fe03c8cd2b87510febb7ffda910698571d8fcd2bd4bf96fc99  mvp-client-server.js
    ec194edae6a503555c785c2100b2a13d9b1fc14cca9fe60b7f7315d5bebd40ce  mvp-client-server-checks.mjs
    19fbc63fda415ba3bbabede3392d7a5d3edef943e6a5fdad162c44a68b9e45fc  mvp-client-server-rejected-2026-09-19.html
