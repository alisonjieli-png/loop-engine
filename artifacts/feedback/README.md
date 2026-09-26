# Feedback reports

Kind: dated aggregate records written by `tools/feedback_report.py`.

Each `feedback-report-YYYY-MM-DD.json` is a `feedback_report/v1` record: how
many downloads were rated useful and not useful, how many items were rated,
how many requests for material were made and by how many accounts, and how
many searches found nothing in each hour and each mode. The file holds counts
only. No rating note, no request text, no account identity and no search text
is in it, so it can live in the public repository and feed the weekly number.

The same tool writes a suggestion batch, `harness_idea_batch/v1`, under
`ideas/`. Each request for material and each hour of searches that found
nothing becomes one `harness_idea_record/v1` the generation lanes can take.
A request carries the customer's own words, so `ideas/` is ignored by git and
is never committed. The mapping is in the tool and is held by
`tools/test_feedback_report.py`.

Search gaps are counted by the service without the query text and without
the account. Storing the text would need a change to the published privacy
notice, which the owner decides. The operations themselves are described in
[the customer feedback guide](../../docs/guides/customer-feedback-and-requests.md).
