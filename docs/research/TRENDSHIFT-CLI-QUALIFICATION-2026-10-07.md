# Trendshift CLI qualification

Owner-local date: October 7, 2026. Source reads occurred early October 8 UTC.
This is an engineering qualification record, not a deployment record or
permission to start a recurring crawl.

## Decision and reuse

Use Trendshift as a source of repository discovery signals. Keep its rankings
out of public raw-data packages. The existing knowledge-radar source edge
owns both adapters, query-multiplier Transport owns bounded HTTP, and
CommunityStore with RecordOperationService owns private observations and
request holds. The command uses the existing canonical Loop. There is no
separate runtime, source registry, database implementation or scheduler.

The [public homepage](https://trendshift.io/) already contains a JSON-LD
ItemList. A normal HTTP read was enough; no browser automation, hidden
endpoint, script execution or session impersonation was needed. The public
adapter deliberately supports only that current daily page. The
[official API documentation](https://api.trendshift.io/docs) supplied a
machine-readable schema, so the authenticated adapter uses those documented
routes instead of reverse-engineering the application's private requests.

## Rights and account boundary

The [terms](https://trendshift.io/tos), effective July 19, 2026, allow use of
API data within a subscriber's products and analysis but restrict raw-data
redistribution and substantial reproductions without written permission.
Derived analysis still needs a rights and evidence review. Repository code
has separate licence and trust requirements. Discovery does not grant either.

The [Signal page](https://trendshift.io/signal) advertised Starter at $9 per
month when read. That is a vendor offer, not a purchase, an available account
entitlement or a verified future price. No account was created or changed.
No subscription or API key was supplied for this qualification. The command
accepts an existing key only from the host environment and binds its bearer
header to `api.trendshift.io`. Public requests never receive that header.

## Observed requests

Three web-document reads preceded the direct probes: terms, Signal and API
documentation. The API documentation web result exposed no text. A separate
allowance then authorized three direct HTTP requests. These are six
observations, not three. No authenticated API request was made.

| Direct read | HTTP date (UTC) | Status | Body bytes | Finding |
| --- | --- | --- | ---: | --- |
| `/docs` on the API host | 02:41:07 | 200 | 841 | References `/openapi.yaml` |
| `/openapi.yaml` on the API host | 02:41:49 | 200 | 69,072 | Full 1,583-line contract read |
| `/` on the public host | 02:43:13 | 200 | 323,446 | One 25-item JSON-LD list |

All three direct reads used HTTPS, no redirects, a disclosed Baltor user
agent, a twenty-second timeout and a one-MiB response bound. More than ten
seconds separated each read. Captures and response headers remain in the
private qualification directory, outside the public repository. Synthetic
fixtures, not source rankings, are checked into the tests.

| Capture | SHA-256 |
| --- | --- |
| Documentation HTML | `e9095fb0d383802637c9e4b542716c0637ea16bc4a01290a9938690323563613` |
| OpenAPI schema | `f8946f14e06e80e94636f606ffa155a30263bab8a58fd9a9a12875b843465bdc` |
| Public homepage | `c1afb50615814c298c8de5d156a6f26a84a41f8de48ed04c133dff54df46909b` |

## API contract and meaning

The [OpenAPI schema](https://api.trendshift.io/openapi.yaml) declares version
0.1.0. It documents trending lists by day, ISO week, month and year, captured
GitHub daily lists, and engagement gains over explicit date windows.
Pagination uses an opaque cursor. The stated provider limit is one hundred
requests per minute per token; successful responses may be cached for
fifteen minutes. Baltor imposes a lower one-request run ceiling and shared
ten-second spacing across both adapters.

Historical lists contain current `stars_now` and `forks_now` values. Those
totals are not historical period-end denominators. The parser keeps them
apart from source rank and windowed gains, and calculates no growth ratio.
GitHub lists carry a scraper-local `trend_date`; the current Trendshift list
does not report its actual list date. Its freshness remains unknown.
Numeric `ghr_id` values are provider-reported identities, not independently
resolved GitHub observations. A public slug can change after a rename.

The schema's prose calls GitHub `data` an array, while its type also admits
null. The adapter refuses null as an invalid collection rather than reporting
an empty source. Unsupported shapes fail visibly. An explicit empty array,
partial row exclusions, stale dates and unavailable history remain distinct.

## Tested boundary and next qualification

The observed homepage capture produced twenty-five observations with zero
exclusions in the offline CLI. Its list date and numeric GitHub identities
remained unknown. The operator supplied the capture's parse timestamp; that
does not establish a fresh transport read. No actual source rows were queued,
approved or published during this qualification.

Offline tests cover API route selection, history, pagination, gain bands,
identity changes, malformed and partial responses, current-count semantics,
missing credentials, fixed-host bearer headers, body bounds, source holds,
unknown-outcome reconciliation and private unapproved records. Deliberately
removed request-budget and provider-hold guards expose extra requests, so the
tests demonstrate those protections rather than merely exercising happy
paths. See the commit's check results for the exact attempt counts.

The next authorized Signal qualification needs an existing entitlement and a
host-injected key. Read one small current page, then a separately authorized
historical page, retaining the same private state and holds. Compare a bounded
sample with GitHub's own identity and dated event evidence before claiming
growth or adoption. No source response is permission to enlarge that budget.

For Baltor Feeds, the commercial test is whether a newly discovered tool
changes a customer's stack or cost decision. For Harness Files, it is whether
a separately licensed and tested implementation improves a task. A higher
rank or a larger lead count does not establish either result.
