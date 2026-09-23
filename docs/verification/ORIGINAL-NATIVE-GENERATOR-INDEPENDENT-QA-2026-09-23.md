# Independent review of original native generation

Review date: September 23, 2026. Initial review only; a successor repair is being
prepared by the author. No provider call, approval or production change was made.

Source reviewed read-only in `/home/username/.le-codex-build/native-generation`.
Initial generator patch SHA-256:
`f40ed293e84d4c4fdb0ba579411d7c3e1cc1d9c2a78aad9f5a826942bab4c6d7`.
Initial provider identity patch SHA-256:
`6ca89f9c1afb0f1b3b77e1f31769f03c2203da31d2df3c2c7d0d5c9bca66a95b`.

The [counterexample record](../../artifacts/generator-independent-qa-2026-09-23/counterexamples-initial.json)
holds exact inspected source digests. The reviewer replayed 24 author tests,
which passed, then ran separate counterexamples through the marked fixture path.

## Findings

| Finding | Observed result | Required repair |
| --- | --- | --- |
| Prepared metadata is not fully bound on resume | Editing the saved item producer family and declared effects was accepted on resume, while the saved proposal stayed unchanged. The candidate count remained one. Package bytes, identity and digest were still checked. | Bind the complete item/specification metadata and package file set to the completion record or reconstruct and compare it with the frozen proposal. Refuse changed producer, effects, styles, rights, dependencies or source provenance. |
| Provider error bodies lose usage | An injected HTTP-200 refusal carried `prompt_eval_count=11` and `eval_count=7`. The Ollama error-body branch returned both as unknown. | Preserve every valid reported token count even when content is refused. Missing counts remain unknown; do not manufacture zero. |
| Failed answering-model identity is omitted from the generation journal | The actual gateway attempt held `reported-other-model`, refused it with `model_identity_mismatch`, and preserved usage. The logical result model was empty and the generator saved that empty value. | Record the actual physical attempt identity and expected route separately. Never fill missing identity with the requested model. |

These findings did not produce an approved item, a hosted item or an extra live
model call. The first weakens resume integrity; the latter two weaken failure
accounting and diagnosis. They should be repaired before the generator is
described as preserving complete candidate and attempt records.

The [failed identity record](../../artifacts/generator-independent-qa-2026-09-23/failed-identity-record.json)
uses the real `ModelGateway` with an injected adapter, rather than setting only a
fake top-level result. Its initial QA fixture accidentally used the default
route purpose. The gateway correctly refused that setup; the
[fixture failure](../../artifacts/generator-independent-qa-2026-09-23/failed-identity-probe-before-route-repair.json)
is retained and is not classified as a product defect.

## Controls that held

- Altering the saved proposal bytes was refused with `saved_proposal_changed`.
- Missing provider identity in an error body remained empty and unsuccessful.
- Author tests passed for source/plan pins, exact paths, explicit authority,
  physical call limits, failed output retention, secret redaction, altered
  resume configuration, symlink refusal and pending-dispatch reconciliation.
- Unknown usage remained unknown. Strict mode conservatively consumed its
  reservation and stopped when accounting was incomplete.
- Model drafts did not control producer family, paths, roles, effects or approval.
- A provider outage or invalid draft was not replaced with synthetic success.

The declaration checks and fixture tests do not qualify live provider behavior,
model output quality, native package loading or independent admission. The
new completion metadata requires a versioned record change, with historical
offline runs retained rather than silently reinterpreted.

## Evidence

- [Author tests replayed](../../artifacts/generator-independent-qa-2026-09-23/author-tests-replayed.txt).
- [Independent counterexample program](../../artifacts/generator-independent-qa-2026-09-23/counterexamples.py).
- [Initial findings](../../artifacts/generator-independent-qa-2026-09-23/counterexamples-initial.json).
- [Actual gateway failed-identity finding](../../artifacts/generator-independent-qa-2026-09-23/failed-identity-record.json).

The root session owns integration and the real pilot. The implementation author
has the reproductions and is preparing successor patches. This report does not
approve either initial patch or any generated intelligence.
