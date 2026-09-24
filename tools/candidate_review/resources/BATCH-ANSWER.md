# Answer contract for several candidates in one request

Kind: the answer contract a reviewer follows when one request holds several
candidates. The review panel adds it after the reviewer instructions when it
asks about several candidates at once. It changes only the shape of the
answer; the criteria, the lens and the rules for a decision stay as the
instructions state them.

## Batch answer

This request holds several candidates, so the answer shape below replaces the
single JSON object the instructions above describe. Judge each candidate on its
own, only by the criteria listed for that candidate, as if it were the only
candidate in the request. Another candidate in the same request is never
evidence for or against this one, and a decision about one candidate never
decides another.

Answer with one JSON object with exactly one key, `verdicts`. Its value is a
list with exactly one verdict for each candidate, in the order the candidates
appear in the request. Each verdict is one JSON object with exactly
`identity`, `body_sha256`, `decision`, `findings` and `reasons`. Copy each
candidate's identity and digest exactly as the request names them. The rules
for a decision are unchanged: `decision` is `approve` or `reject`, each finding
has exactly `criterion_id`, `blocking` and `text` and cites only a criterion
listed for that candidate, a rejection needs at least one blocking finding and
nonempty reasons, and an approval has no blocking finding. Do not return other
fields or prose outside the JSON object.
