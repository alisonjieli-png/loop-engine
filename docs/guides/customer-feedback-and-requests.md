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

The published privacy notice promises no log of requests that succeed and,
since September 24, 2026, aggregate counts. Storing the query text would need
a change to the notice, which the owner decides. The service therefore leaves
the text out, and a guard in the source refuses a gap payload that carries it
(`search_gap_holds_query_text`).

### What staff read

A staff member whose role reads usage counts, or an operator whose token holds
the `access:manage` scope, opens the administration page and sees Feedback
from customers: how downloads were rated, every request for material with
its account and date, and the hours in which searches found nothing. The same
view is served at `/api/v1/admin/feedback` as `service_feedback_view/v1`, with
`ratings`, `material_requests` and `search_gaps`. Any other caller is refused
with `account_administration_forbidden`.

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

- The privacy notice does not yet name ratings or requests for material in
  its table of what the service stores. The owner decides that change; until
  then the website's rating buttons and request form state, beside each, that
  the text is kept with the account.
- A staff member cannot yet change the state of a request from `open`, and no
  rating or request is removed by the retention task. Both need their own
  steps.
- The lanes do not yet read the suggestion file on their own; a person runs
  the report and hands the batch to a lane.
