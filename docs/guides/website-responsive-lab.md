# Website responsive lab

Kind: operating guide.

The responsive lab loads the signed-out pages of the Baltor website on many
screen sizes and three browser engines. It takes screenshots, scrolls each
page, opens the phone menu, the disclosures and the tab sets, and measures
the layout. It is read-only: it submits no form, signs in to nothing and
sends no credential.

Two files make up the lab:

- [capture_website_devices.mjs](../../tools/capture_website_devices.mjs), the
  command.
- [website_devices.json](../../tools/website_devices.json), the device list,
  the page lists, the budgets and the thresholds. Change a size or a budget
  there, not in the command.

The first report is the
[responsive lab report of September 23, 2026](../verification/WEBSITE-RESPONSIVE-LAB-2026-09-23.md).

## What one run does

```text
One run
├── For each engine (Chromium, WebKit, Firefox)
│   └── For each device configuration and each address
│       ├── Load the page and wait for the network to settle
│       ├── Screenshot of the first screen, then of the full page
│       ├── Measure the page (see below)
│       ├── Scroll run: steps of 80 percent of the screen, one screenshot each,
│       │   the share of the screen that a fixed or sticky header covers
│       ├── Jump to each visible in-page anchor and check that its heading is
│       │   not under a fixed or sticky box
│       ├── Phone menu: open, screenshot, check every link, close with Escape
│       ├── Open every closed disclosure once and measure again
│       └── Select every tab of every tab set once, one screenshot each
├── Contact sheets: one image per page, the first screens of every device
└── One metrics record, written once under a new name
```

A load whose own style sheet, script, font or document failed is marked
degraded, waits and loads again, up to three attempts. A degraded load is
never counted as a layout finding.

## What it measures

| Measure | How |
|---|---|
| Horizontal overflow | The page is wider than the window. The outermost elements that reach past the window, outside any scrolling box, are named. |
| Clipped boxes and scrolling boxes | A box whose text is cut by hidden overflow, and a box that scrolls sideways, such as a code block. |
| Overlapping text and controls | Line boxes of two different text nodes that share more than half of their height; two controls whose boxes intersect. |
| Tap targets | On touch devices, every control smaller than 44 by 44 pixels. A link inside running text is marked `inline_in_text`. |
| Text size | Any text under 12 pixels, and running text under 15 pixels on screens up to 600 pixels wide. |
| Line length | Characters per line for paragraphs and list items, from the number of line boxes. Over 90 is reported. |
| Page height | Height in pixels and in screens. |
| First screen | Whether the headline, the lead line, the primary action and, on the homepage, the price sit entirely in the first screen. |
| Empty vertical runs | Stretches with no text, control, image or card edge, 96 pixels or more. |
| Contrast | Every text line against the nearest painted background colour, 4.5 to 1, or 3 to 1 for large text. Disabled controls are exempt. |
| Console errors | Errors and failed requests, and separately the errors seen before the first screenshot. |
| Media | Images, video, frames and drawings wider than the window or their container. |
| Layout shift and largest contentful paint | Buffered performance observers installed before the page script runs. Engines without them report unsupported. |

## Before the first run

The lab uses Playwright from `showcase/node_modules`. In a separate worktree,
link that folder from the shared checkout; the link is ignored by Git:

```bash
ln -s /home/username/loop-engine/showcase/node_modules showcase/node_modules
node showcase/node_modules/playwright-core/cli.js install chromium firefox webkit
```

WebKit stands in for Safari on iPhone, iPad and Mac. It is not Safari itself.
No paid device service is used.

## Commands

The whole lab against the live site and every hostname, from the repository
root. Both paths must be new: the command refuses to reuse a screenshot folder
that holds files or to overwrite a metrics record.

```bash
node tools/capture_website_devices.mjs \
  --base https://baltor.ai \
  --hosts https://www.baltor.ai,https://app.baltor.ai,https://docs.baltor.ai,https://status.baltor.ai,https://examples.baltor.ai,https://demo.baltor.ai,https://baltor-pilot.fly.dev \
  --out /home/username/.le-ci-tmp/site-audit/devices-full-1 \
  --metrics artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20-full-1.json \
  --concurrency 2
```

Against a local build or any other address, give its origin as `--base` and
leave out `--hosts`:

```bash
node tools/capture_website_devices.mjs --base http://127.0.0.1:8765 \
  --page-set all \
  --out /home/username/.le-ci-tmp/site-audit/devices-local-1 \
  --metrics /home/username/.le-ci-tmp/site-audit/responsive-metrics-local-1.json \
  --compare artifacts/website-audit-2026-09-23/responsive-metrics-live-release-20.json
```

`--page-set all` adds the addresses of the target site map to the release 20
pages. `--compare` adds a comparison with an earlier metrics record for the
same engine, device and page, and marks each capture that got worse.

Useful narrower runs:

| Option | Effect |
|---|---|
| `--devices phone-390x844,desktop-1440x900,webkit-390x844` | Only these device configurations. A special case runs only when named by its own identifier. |
| `--engines webkit` | Only one engine. |
| `--pages /,/pricing` | Only these addresses. |
| `--no-scroll-shots`, `--no-full-page` | Measure without the scroll screenshots or the full-page screenshot. |
| `--concurrency 2` | Page loads at once for each engine. Four at once drew 503 answers from the live service. |

The same command measures other websites for comparison, read-only, with
`--benchmark` and a list of addresses. It loads each address once for each
device and does nothing else on the page:

```bash
node tools/capture_website_devices.mjs \
  --benchmark https://example.com/,https://example.com/pricing \
  --devices desktop-1440x900,phone-390x844 --no-scroll-shots \
  --out /home/username/.le-ci-tmp/site-audit/benchmark-1 \
  --metrics /home/username/.le-ci-tmp/site-audit/benchmark-1.json
```

## Where the results go

```text
OUT folder
├── ENGINE/DEVICE/PAGE/
│   ├── first-screen.png, full-page.png
│   ├── scroll-00.png, scroll-01.png, ...
│   ├── menu-open.png, disclosures-open.png
│   └── tabs-SET-TAB.png
└── contact-sheets/PAGE.png and PAGE.html
```

Screenshots are in layout pixels and stay outside the repository. The metrics
record, `website_responsive_metrics/v1`, holds every capture, a summary for
each page with its budget verdict, the engine versions, the repository
revision and the digest of the device list.

## Limits

- Headless engines with emulated viewports on one Linux workstation, not
  physical phones or tablets.
- Text at 200 percent is emulated by overriding the root text size in the
  served markup, because the page fixes the root size in pixels. That case
  turns off the page's content security policy, and only that case.
- WebKit logs one refused style for each screenshot the lab takes. Use
  `console_errors_before_screenshots` for the page's own errors.
- Contrast is computed against the nearest painted background colour. Text
  over an image or a gradient is marked `over_image` and is not certified.
- A timing from this workstation is not a field measurement.
