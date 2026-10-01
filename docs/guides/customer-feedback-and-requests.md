# Customer feedback and requests for material

Kind: operating guide to the three feedback signals of the hosted service, for customers who send them and staff who read them.

The hosted service records three kinds of feedback from customers about the
library. Each one is a typed record in the service database, written through
the same store as every other account record. Staff read them on the
administration page. The "report this item" operation is a separate feature
and is not described here.

```text
feedback signals
├── rate a download        useful or not useful, for an item the account downloaded
├── request material       a short description of what a step needs and the library lacks
└── search gap             counted by the service when a search finds nothing
```

Every field, record type, address and refusal code on this page is held to the
service source by `tools/check_service_documentation.py`, run from
`tools/test_feedback_report.py`.

## Current behaviour

### Rate a download

After a successful download, a customer may rate the item. The workspace and
the library table show a Useful and a Not useful button on the download's
status line. A client can send the same operation directly:

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/provisioning -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Content-Type: application/json" -d '{"record_type":"service_provisioning_request/v2","operation":"rate","identity":"skill.alpha","expected_digest":"<the digest that was downloaded>","value":"useful","note":"Saved the source review."}'
```

| Request field | Meaning |
| --- | --- |
| `record_type` | Exactly `service_provisioning_request/v2`. Version 1 predates feedback and is refused with `unsupported_version`. |
| `operation` | `rate`. |
| `identity` | The item, as the search or the list named it. |
| `expected_digest` | The digest of the revision the account downloaded. A rating names one exact revision. |
| `value` | `useful` or `not_useful`. |
| `note` | Optional. At most 500 characters, written on purpose for staff. The buttons on the website send none. |

The result is `catalogue_item_rating_result/v1`. It states `committed`,
`item_identity`, `body_digest`, `value`, `replaced` and `revision`. The record
is `catalogue_item_rating/v1`, keyed by the account and the item, so a second
rating of the same item replaces the first and `replaced` is true. The
service checks the account's own usage records before it writes: an item the
account never downloaded, or a revision it never downloaded, is refused with
`rating_requires_download`. The operation needs the `provisioning:metadata`
scope.

### Request material

When the library does not have what a step needs, a customer describes it.
The workspace has a form under the search results, Ask for material. A client
sends:

```bash
curl -sS -X POST https://app.baltor.ai/api/v1/provisioning -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" -H "Content-Type: application/json" -d '{"record_type":"service_provisioning_request/v2","operation":"request_material","request_id":"<a new identity for this request>","description":"A hook that refuses a commit without a changelog line."}'
```

| Request field | Meaning |
| --- | --- |
| `operation` | `request_material`. |
| `request_id` | One identity for one request. A retry with the same identity and the same text repeats the request instead of recording a second one. |
| `description` | What the step needs. At most 2000 characters, written on purpose for staff. |

The result is `material_request_result/v1` with `committed`, `repeated`,
`request_id_digest` and `state`. The record is `material_request/v1`, keyed by
the account and the request identity, and starts in the state `open`. The
same `request_id` with a different `description` is refused with
`material_request_identity_conflict`. Nothing is promised in return: staff
read every request, and a request may become a candidate for the generation
lanes (see the report below).

### Search gap

When a search returns no hit, the service counts it and the answer carries one
extra line, `ask_for_material`, which says that the customer can ask for
material with the operation above. The count is `search_gap/v1`, one record
for each hour, retrieval mode, set of declared filters and set of library
tiers, with `hit_count` zero and `searches` for how many searches in that hour
found nothing. It holds no account and never the query text; a filter value is
kept only when it is a short token of a declared attribute, and any other
value is counted as `other`.

The privacy notice distinguishes deliberate submissions from aggregate search
gaps. The current search-gap operation leaves query text out, and a guard
refuses a gap payload that carries it (`search_gap_holds_query_text`). This
operation is not a general log of successful requests.

### What staff read

A superadmin whose role holds `accounts.list`, or an operator whose token holds
the `access:manage` scope, opens the administration page and sees Feedback
from customers: how downloads were rated, every request for material with
its account and date, and the hours in which searches found nothing. The same
view is served at `/api/v1/admin/feedback` as `service_feedback_view/v1`, with
`ratings`, `material_requests` and `search_gaps`. Analytics staff may read the
counts-only summary below, not this private view. Developers and ordinary
customers may read neither. A caller without the required role or scope is
refused before private feedback is returned.

### Connected harnesses and the feedback command

The Model Context Protocol tools `provisioning_rate` and
`provisioning_request_material` accept the same fields as the corresponding
HTTP operations, without `record_type` or `operation`. They require the
existing `provisioning:metadata` scope. A connected harness using an ordinary
OAuth delegation can submit them without transferring a key into its prompt.
Ratings still require an exact-version download, including an eligible Public
Good download. Neither operation counts as another paid download.

Notes and descriptions are private staff feedback, stored with the account.
They are not automatically published or expired. Include no secrets or
private project data. A rating replaces the earlier rating and increments
its revision, so its tool does not claim exact idempotency. A material request
retains its existing request-identity rule. The separate `provisioning_report`
tool reports an item defect and can withdraw material; a rating is not a
withdrawal report.

The `feedback_review` tool takes an empty object and returns only
`service_feedback_summary/v1`: `ratings` (`useful`, `not_useful`,
`items_rated`), `material_requests` (`total`, `open`) and `search_gaps`
(`groups`, `searches`). The same result is available through
`GET /api/v1/admin/feedback/summary`. No note, description, account or item
identity, request digest, filter value or timestamp is returned.

This summary retains the existing staff gate: an operator credential with
`access:manage`, or a current staff browser session permitted to read usage
counts. Ordinary OAuth delegation cannot acquire that scope or a staff role.
The service checks access again after serialization. The full private view
keeps its schema but requires `accounts.list` or `access:manage`. The counts endpoint is not public,
and an unlisted page is not an authorization boundary.

The repository command `tools/baltor_feedback.py` is a standalone Python 3.10+
client. It uses the same HTTP operations and reads a credential from the named
environment variable, `BALTOR_SERVICE_TOKEN` by default. It does not create,
refresh or export credentials, accept a token argument, or change a harness's
configuration. Customer fields arrive as one JSON object on standard input:

```bash
python3 tools/baltor_feedback.py request_material --origin https://baltor.ai < request-fields.json
python3 tools/baltor_feedback.py rate --origin https://baltor.ai < rating-fields.json
python3 tools/baltor_feedback.py review --origin https://baltor.ai
```

The first two files contain the fields in the tables above, without
`record_type` or `operation`. The last command requires the existing staff or
operator authority; it returns counts only. Configure only a trusted Baltor
origin, never an address copied from feedback. The client honors environment
proxy settings, verifies HTTPS, refuses redirects and prints no credential or
submitted text. It makes one attempt and never retries automatically. After an
uncertain submission, keep its request identity and reconcile the outcome
instead of silently creating another request.

The feedback tools use the existing records and retention rules. The owner
approved general voluntary submissions, uploads and data exchange on
October 1. The privacy notice describes those purposes and current retention. These
feedback calls still publish no customer text and invoke no model or external
connection automatically.

### Refusals

| Code | Status | Meaning |
| --- | --- | --- |
| `rating_requires_download` | 409 | The account has no usage record of that item at that digest. Download it first. |
| `rating_value_invalid` | 400 | The value is not `useful` or `not_useful`. |
| `feedback_note_too_long` | 400 | The note is over 500 characters, is not text, or holds control characters. |
| `material_request_description_invalid` | 400 | The description is missing, empty, over 2000 characters or not text. |
| `material_request_identity_conflict` | 409 | The same request identity was used with different text. Use a new identity. |
| `unsupported_version` | 400 | The request named the first request version, which predates feedback. |
| `account_administration_forbidden` | 403 | The caller may not read the feedback view. |

### The weekly number and the idea matrix

`tools/feedback_report.py` reads the three records and writes a dated
aggregate, the feedback report record (feedback_report, version 1), under
`artifacts/feedback/`: counts only, so the file holds no note, no request
text, no account and no search text. The same run writes a suggestion batch
(harness_idea_batch, version 1) whose ideas are harness idea records
(harness_idea_record, version 1): one for each request for material, in the
customer's own words, and one for each hour of searches that found nothing,
shaped by the declared filters. The suggestion file is written under an
`ideas/` folder that git ignores, because a request carries the customer's
words. `tools/test_feedback_report.py` holds the mapping to the idea matrix
vocabularies.

```bash
PYTHONPATH=src:tools python tools/feedback_report.py --database /data/service.db --output artifacts/feedback
```

## Planned behaviour

- A staff member cannot yet change the state of a request from `open`, and no
  rating or request is removed by the retention task. Both need their own
  steps.
- The lanes do not yet read the suggestion file on their own; a person runs
  the report and hands the batch to a lane.

## Private work reports and files

The Administration page includes a Dot work log for authorized administrators.
It accepts research, test results, component candidates, review replies and
blockers through the existing managed-record and catalogue-store contracts.
Each saved report is immutable. A reply is a new report linked to its parent;
it neither marks a public task complete nor approves a library component.

`POST /api/v1/admin/work` takes `service_staff_work_request/v1`, with
`request_id`, `brief` (`context` or `feedback`), `brief_revision`, `task_id`,
`kind`, `title`, `message`, `links`, `files` and `reply_to`. Empty lists and an
empty `reply_to` are explicit. Get the current brief revision from the ETag of
the matching public JSON brief. Each file names a relative `name` and UTF-8
`content`. Exact bytes, including a byte-order mark and line endings, determine
its stored checksum. The server derives the author from the authenticated
account. Supplied actor, tenant, storage path or permission fields are refused.

The response is `service_staff_work_result/v1`, naming its exact `id`,
`record_version`, `committed`, `repeated` and `promotes_intelligence: false`.
Repeating the same account/request identity and content returns the saved
result. Different content conflicts. A new submission with a stale brief is
refused; an exact replay of a saved submission keeps its original binding.
An uncertain outcome needs inspection or the exact same request, not a new
identity and an automatic retry.

`GET /api/v1/admin/work?id=...` reads one complete report. Without `id`, use
`day` in UTC and optional `task_id` to list up to one hundred matching reports.
The result's `complete` flag identifies truncation. Narrow the task/day when
needed. The first profile permits sixteen files, 64 KiB per file and 256 KiB
of file content per submission. Private HTTP request and response limits are
separately configurable, defaulting to 512 KiB and one MiB. Ordinary HTTP and
MCP retain their existing limits; an encoded request must fit its transport.

The MCP tools `staff_work_read` and `staff_work_submit` accept the same read
or write fields without the HTTP `record_type`. Both require the existing
superadmin browser or operator authority. Ordinary customer OAuth does not
inherit staff access. The browser work log is the route for the owner's
already signed-in Dot; no session credential needs to be copied into a prompt.

Submissions are untrusted data. The service does not execute files, fetch
source links, call models, send notifications or publish them automatically.
Reports and attachments currently have no automatic expiry. The general
privacy notice covers explicit submissions; it does not give every account
access to this first interface or add a recurring schedule.
