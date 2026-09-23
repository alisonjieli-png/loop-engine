# Native review calibration: independent successor QA

September 23, 2026. This succeeds the preserved
[initial independent review](NATIVE-REVIEW-CALIBRATION-INDEPENDENT-QA-2026-09-23.md).
No provider calls, real approvals or catalogue admission occurred.

**The frozen successor closes the reproduced enforcement defects.** The
nineteen focused native calibration tests pass independently. All inspected
source hashes match the author's frozen bindings.

| Independent replay | Final result |
| --- | --- |
| Failed reviewer still contributes a candidate decision | Refused: `excluded_calibration_reviewer_decided` |
| Remove both exclusion projections while retaining four false approvals | Refused: `calibration_inconsistent` |
| OpenAI reviewer skipped because the controls are OpenAI-produced | Recorded `calibration_incomplete`; zero candidate-phase calls |
| Coherent calibrated candidate record | Accepted as an explicitly permitted test fixture only |
| Replace control prompt digest and recompute its linked review keys | Refused: `calibration_prompt_mismatch` |

[Replay evidence](../../artifacts/native-review-calibration-independent-qa-2026-09-23/successor-counterexamples-2.json),
[focused checks](../../artifacts/native-review-calibration-independent-qa-2026-09-23/successor-focused-tests-3.txt),
[frozen-source comparison](../../artifacts/native-review-calibration-independent-qa-2026-09-23/successor-source-bindings.json).

The reader now resolves deployment-owned or explicitly host-supplied typed
controls independently of the untrusted export. It verifies control metadata,
complete native request identity, criteria/instructions, installation identity,
answering model, call/verdict correspondence and decisions. The full export
provides panel configuration, allowing the exact prompt to be reconstructed
from trusted request, instructions and the configured reviewer/lens. Eligibility
and both exclusion projections are recomputed instead of trusting summary lists.
Every configured installation must be accounted for; lack of measurement cannot
qualify it.

The change uses `starter_catalogue_panel_review/v3` and
`candidate_review_calibration_result/v2`, so older readers cannot silently accept
the stronger record semantics. Unknown usage remains distinct from zero, and
fixture-engine results remain barred from real exports. These records provide
internal consistency and exact binding; they are not cryptographic attestations
of a provider's honesty.

The first successor closed the original two defects but accepted a replaced
prompt hash with consistently rewritten review keys. That intermediate result
is retained as `successor-counterexamples-1.json`. The final source rebuilds the
expected prompt and rejects the same mutation. The first test invocation also
used a nonexistent worktree-local interpreter; its shell error is retained.
The successful rerun used the integrating session's qualified environment.

The earlier five bounded label observations still apply. The revised calibration
limits now explicitly treat rejection of an expected-approve control as a label
disagreement until full admission eligibility, including applicable native
loading evidence, is established. The benign schedule fixture is not represented
as proof that every native criterion has been independently satisfied. The set
still supplies no real-world error-rate estimate or general safety guarantee.

No remaining blocker was found in this bounded code/record replay. Full
integrated CI, explicit call ceilings for a live pilot, and formal independent
candidate admission remain separate gates owned by the integrating session.
