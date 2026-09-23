# Maintain the website documentation

Kind: developer guide to the customer documentation index, rendering and checks.

Edit the customer Markdown guides and rebuild their served bodies. The website
keeps one header and footer, a compact index, page navigation and a contents list.
The setup entry opens the existing interactive guide rather than a second copy.

```text
Customer documentation
├── Source
│   ├── Customer table in docs/guides/README.md
│   ├── Seven Markdown guides
│   └── web_assets/documentation-index.json
├── Build
│   ├── tools/build_documentation_index.py
│   ├── documentation_pages.json with exact source and body digests
│   └── Six web_assets/docs/*.html bodies
└── Delivery
    ├── WEB_ASSETS declares every page and file address
    ├── service.js selects the page view
    └── documentation.js validates the index and rebuilds allowed markup
```

## Edit and build

The index uses `website_documentation_index/v1`. Its sections and pages are
ordered lists. Each page has an identity, title, short summary and address.
Built pages also name their source guide and body address. The setup page has
an alias at `/docs/getting-set-up`; the alias must select the same view as
`/setup`.

The builder supports headings through level four, paragraphs, fenced examples,
tables, lists, code spans, bold text and links. Unsupported markup is refused.
The source title and repository `Kind:` line are omitted from the body: the
index supplies the website title and summary. Same-site links stay on the
current origin, indexed guide links open their website page, and other
repository links open the repository's declared home.

```bash
PYTHONPATH=src:tools python tools/build_documentation_index.py --repository .
PYTHONPATH=src:tools python tools/build_documentation_index.py --repository . --check
PYTHONPATH=src:tools python tools/check_documentation_index.py --repository .
PYTHONPATH=src:tools python -m unittest tools.test_documentation_index tools.test_service_documentation
```

The index check compares the customer table, factual-check page set, explicit
routes, aliases, exact rendered bytes and the terminology contract. A guide
whose file name starts with `service-` is not automatically a customer page.
For example, the failure-diagnosis guide is for operators.

## Browser behavior

The client refuses an unsupported index version, unknown fields, duplicate
identities or addresses, external page/body addresses and invalid dates. It
rebuilds each body from an element and attribute allowlist. An unexpected
head element, script, form or event attribute refuses the whole body. Dynamic
index and body reads use `no-store` so a cached document does not survive the
next page load after a release.

In-page navigation uses the existing application's history. It does not reload
the document or reset its in-memory account state. A downloaded package is
still separate from these public documentation bodies.

```bash
node tools/check_documentation_browser.mjs artifacts/documentation-browser-new.json
```

Use a new output path. The checker runs a real loopback service and browser,
checks every page at 1440 and 390 pixels, preserves screenshots, checks contrast
in both appearances and exercises malformed index/body controls. It uses no
model or provider account. For read-only public checks after release, append
the exact live origin as the second argument; local mutation controls are then
omitted. Run it for each deployed hostname alongside the hosted website check.

## Review content

Use current service source and recorded public capabilities. A client recipe
is configuration guidance, not evidence of a completed native-client task.
Keep offered, retrieved, loaded, used and accepted separate. Describe the
hosted library and local engine separately, and distinguish format support
from material actually approved and published.

The source-fact checker detects many record, field, address, command and
refusal changes. It does not establish semantic truth, validate model cost
claims or replace an independent reading of the guides.
