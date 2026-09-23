# Original native generator successor review

September 23, 2026. **Go for the first bounded real generation pilot.** This
decision covers the reviewed controller and accounting repairs. It does not
approve generated material, qualify live model quality or authorize publication.
The root session retains the declared model-call and output allowance.

## Frozen versions

| File | SHA-256 |
| --- | --- |
| Generator | `6293bcbdbb6c0109e5d93e738d001d2431c881ba4cf0c3a4a5c3d4cc0bde2db1` |
| Ollama adapter | `a81402bbfd7fbeb8c8d5c21c95bf4ef76901f07c76309b270f1eb64bff703f3c` |
| Model gateway | `eaca708ce5d5bce2a1483798260f71698aacde86eae7a6ef946d88d5f536fe2b` |

Integration patches: `native-generation-v3.patch`, SHA-256
`8848970681aa86915ff56276665f7975ca404834c741642c79de3d02da8bb125`, and
`provider-model-identity-v4.patch`, SHA-256
`0015313b51f6c1ae729cdef635558682cc4d99458fe71c2d79e8b27a3eff6d4a`.

## Independent results

- All [57 owning tests](../../artifacts/generator-independent-qa-2026-09-23/final-owning-tests.txt)
  passed using fixtures only.
- [The original counterexamples](../../artifacts/generator-independent-qa-2026-09-23/counterexamples-final.json)
  now refuse altered prepared producer/effect metadata and preserve reported
  usage from provider error bodies. Proposal-byte modification remains refused.
- [Additional final controls](../../artifacts/generator-independent-qa-2026-09-23/final-independent-controls.json)
  verify actual failed-attempt model/provider/request identity, empty identity
  for malformed responses, and refusal to resume after a direct gateway
  implementation fingerprint changes.
- Run records use version three; journal events use version two. Older offline
  records are not silently reinterpreted. Completed package trees, including
  metadata, specifications and reports, are digest-bound.
- The gateway invocation does not call provider verification or model listing
  as a hidden generation step. Its adapter call explicitly permits one attempt.

The initial findings and failures remain in the
[initial review](ORIGINAL-NATIVE-GENERATOR-INDEPENDENT-QA-2026-09-23.md).
No provider call or intelligence approval was made during this independent QA.

## Related native profile finding

The unsupported active-configuration counterexamples also now pass their
[successor controls](../../artifacts/generator-independent-qa-2026-09-23/native-active-path-successor-controls.json):
OpenCode and Pi settings cannot masquerade as inert JSON; ordinary example JSON
remains accepted. All 24 native tests passed. The exact inspected precheck source
digest was `304a7e1d92d85290ac46aba86b9e3c809491d6280382aa2a8f263a818a356107`.

## Limits

This was a focused, offline review of the reported risks. The real pilot must
still record actual provider identity, usage and failures; preserve candidates
for independent whole-package review; and separately establish native loading
and task acceptance. An explicitly call-limited run does not imply a strict
total-token or monetary ceiling. The final decision is scoped to the frozen
versions above, not every future implementation or generated package.
