# Independent test design before implementation review

September 23, 2026. The following counterexamples were selected from package
identities and task descriptions before reading authored implementations.
Exact inputs and expected outputs will be bound to the authors' declared
contracts. Contract ambiguities will be reported, not resolved by guessing.
No entry below is an approval or claim that execution has passed.

## Data methods

| Package | Distinguishing positive and negative cases |
| --- | --- |
| profile_csv_structure | Quoted embedded delimiter/newline, escaped quotes, UTF-8 text, CRLF, trailing blank line, ragged row, duplicate headers, empty document. Report physical lines separately from logical records if both exist. Malformed quoting must follow the declared parser policy. |
| reconcile_multiset_rows | Repeated identical rows with unequal multiplicities; counts rather than set membership. Permuting inputs should not alter the semantic delta. Type distinction between booleans, numbers, null and strings must be explicit. |
| compute_weighted_quantiles | Exact threshold equality; zero weights; duplicate values; unsorted input; q=0 and q=1; negative/nonfinite weights; empty/all-zero sample. Scaling positive weights must preserve quantiles under declared numeric bounds. |
| audit_half_open_interval_overlaps | Touching intervals do not overlap; nested and identical intervals do. Equal endpoints/empty intervals and reversed intervals need an explicit policy. Permutation invariance and translation invariance. |
| apply_flat_record_changes | Missing versus null fields; remove/replace absent fields; sequential actions touching same field; mismatched optimistic precondition; unknown operation or fields; input must not mutate on refusal. |
| reconcile_keyed_tables | Missing/null/duplicate key; compound versus delimiter-joined identity ambiguity if supported; changed nonkey fields; row reordering; duplicate nonkey rows with unique keys; explicit type semantics. |

## Systems methods

| Package | Distinguishing positive and negative cases |
| --- | --- |
| compare_file_inventories | Same path different digest/size, missing paths, duplicate path declarations, path spelling normalization ambiguity, identical bodies at different paths remain distinct file identities. |
| resolve_selected_dependency_closure | Diamond dependencies, selected leaf, transitive missing dependency, selected versus unselected cycle, duplicate dependency, cycle diagnostic, unknown root. Closure must not include unrelated nodes. |
| assign_digest_shards | Boundary hex digits, leading zero, shard count one and nonpower-of-two, invalid digest, duplicate input, input order invariance, chosen entire-digest or prefix method explicit. |
| validate_event_precedence | Partial-order diamond with two legal permutations; missing and duplicate event IDs; unknown event; extra event; cycle; transitive violation; unrelated events must not acquire accidental order. |
| apply_nonoverlapping_text_edits | Adjacent ranges, same insertion point, overlapping/nested ranges, Unicode indexing, out-of-range bounds, before/after coordinate convention. Apply against original positions, not shifting positions sequentially. |
| detect_portable_path_collisions | Exact duplicates, ASCII case collisions, NFC/NFD equivalents, parent-file collision, trailing dot/space, Windows reserved basenames, backslash and slash semantics, root/absolute/traversal rejection; behavior explicitly scoped by policy. |

## Cross-cutting checks

- Reject duplicate JSON keys, nonfinite literals, unexpected top-level fields,
  wrong scalar types (including booleans where integers are required), invalid
  UTF-8 and trailing non-JSON data where the contract declares strict JSON.
- Input schema acceptance must agree with actual documented validation; schema
  alone cannot express all semantic constraints. Classify the difference.
- Validate every successful output against its output schema and independent
  expected result, then repeat relevant permutation/idempotence properties.
- Preserve exact bytes/digests for scripts, schemas and instructions before and
  after each run. Changed source requires a new report, not rewritten evidence.
- Execute candidate code only under a minimal Bubblewrap filesystem with no
  network/home, CPU/memory/wall/file-output bounds and credential-free environment.
- Audit declared effects against observed imports/operations, not package titles.
- Test an independent deliberately wrong algorithm where it distinguishes the
  package's useful method; do not count syntactic mutants as semantic evidence.

## Four subsequently announced root-authored interfaces

These additions were planned from the root's interface message, still before
reading candidate implementations or implementation-derived expected values.

- `render_focused_task_context`: preserve exact original structured state and
  its version; repeated rendering is deterministic; a context block containing
  fake instructions must remain visibly quoted as data; multiline labels/text,
  Markdown fences, Unicode and line endings must not escape that presentation.
  Reject absolute/traversing paths and invalid digests. Confirm the documented
  canonical byte serialization before checking the state digest.
- `evaluate_capability_requirements`: a positive resolution below minimum
  evidence is unverified; missing or unknown observations cannot satisfy a
  requirement; explicit unsupported capability blocks it; declaration order
  must not affect sorted results; duplicate observations must be refused.
  Native/translated/enforced are declared states, not inferred authorization.
- `select_context_blocks`: dependency costs count once across shared closures;
  mandatory transitive dependencies cannot be dropped to fit; a higher-priority
  optional block whose full closure does not fit must not crowd out another
  fitting block; selected dependencies precede dependents and remaining budget
  reconciles; unknown dependencies and cycles are refused under the declared
  graph validation policy. No claim of globally optimal knapsack selection.
- `paired_sign_test`: ties do not increase the binomial trial count; missing
  pairs are distinguished from ties; all ties/missing produce no p-value;
  exact finite decimal comparisons; direction reversal swaps wins and losses
  and preserves two-sided probability; 4 wins/0 losses gives exactly 1/8 and
  2 wins/1 loss gives 1. Confirm which input is baseline before assigning wins.
