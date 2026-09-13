# Configuration capability, setter, and preference review, September 13, 2026

A read-only review of `core/configuration_capabilities.py`,
`core/configuration_setters.py`, `core/configuration_preferences.py`, their
checks, the existing `core/parameter_resolution.py` they build on, and the
registry rows in `core/boundary_registry.py`, as the Codex session landed
them in `ccf5dce`. Probe scripts and their outputs are under
`.loop-engine-dev/fable-review-probe-20260913/agent-review-configuration/`.
Every self-test count in the Codex session's verification report matched
(setters 38, preferences 31, parameter resolution 16, registry 9).

## Defects, and what was fixed the same evening

1. **High. An agent's abstaining or outranked proposal still rewrote the
   configuration to the repository default or a prior source's value,
   reported as applied.** The setter never treated the current in-memory
   value as a source; every authorized request re-resolved the whole
   precedence stack and wrote whatever won, so an abstention with a
   default present mutated state (0.7 to 0.5 in the probe) and a
   `DERIVED_VALUE` authority could never apply its own value yet reported a
   successful change. **Fixed:** an abstained proposal is refused before
   resolution (`proposal_abstained`); when the resolved source is not the
   requester's own candidate the effective value still lands, since
   precedence decides it, but the status is `applied_by_precedence`, the
   report names the governing source per setting in `governing_sources`,
   and `requester_candidate_selected` is false. The checks that had locked
   the rewrite in now assert the distinct status.

2. **Medium. The report never compared the resolved value with the value
   that landed**, so a clamping or rounding constructor was reported as
   success or as unchanged. **Fixed:** after construction each updated
   setting's effective digest is compared with the resolved digest; a
   mismatch is refused as `constructor_coerced_value` with both digests.

3. **Medium. Constraint values of the wrong type passed spec construction
   and crashed the setter Loop with a raw type error.** **Fixed:** minimum
   and maximum must be numbers, allowed values a sequence, and non-empty a
   Boolean, at `ConfigurationSettingSpec` construction.

4. **Medium. Constructor exceptions other than value or type errors, and a
   declared field missing from the instance, escaped as a Loop error with
   no report.** **Fixed:** any constructor exception is a typed refusal
   naming the exception class (never its text), and an absent field is
   refused as `target_field_absent`.

5. **Medium. The report said an intelligence was invoked for a merely
   supplied proposal and carried no boundary-level model-call field.**
   **Fixed:** every report carries `model_call_performed_by_boundary:
   false` and each attempt `proposal_supplied`; the resolver's
   `intelligence_invoked` remains its own name for "resolved from a
   proposal".

6. **Medium. Sensitive values leave the report as unsalted SHA-256
   fingerprints** (`value_digest`, `values_digest`, candidate digests), so
   a low-entropy value is recoverable by dictionary. This follows the
   repository-wide `resolved_value_digest` convention in the parameter
   resolver and is left open; the honest fix is a keyed digest bound to the
   target digest for sensitive settings, across both modules at once.

7. **Medium, documentation.** "Abstention when evidence is missing" is only
   a non-empty-tuple check; evidence references are never resolved. The
   guide and the advisory note should say abstention fires on engine
   unavailability, failure, or an invalid ordering, or the boundary should
   accept an evidence resolver. Left open for the guide's owner.

8. **Low. A proposal the record contract refuses inside `rank` was
   classified as an engine crash.** **Fixed:** `invalid_proposal`, so a
   policy that falls back on crashes does not mistake it for one.

9. **Low. The boundary registry never resolved a row's `test` reference.**
   **Fixed the same evening,** registry-wide: the self-test resolves both
   reference forms statically, and eleven rows that named tests which did
   not exist now cite the checks that cover them.

10. **Low. Records were not JSON-plain and had no typed readers.**
    **Fixed:** setting records emit lists, the decision record is plain
    JSON, and the fact, setting, and target records have `from_dict`
    readers that rebuild with equal digests and refuse unknown or missing
    fields, changed digests, and redacted records.

11. **Low. Facts had no typed expiry handling.** **Fixed:** expiry must be
    ISO 8601 text, is normalized to one UTC spelling so `Z` and `+00:00`
    digest identically, parse errors are typed, and references must be text
    whatever the state.

12. **Low. `affects_qualification` was validated and then ignored.**
    **Fixed:** qualification is invalidated only by changed settings whose
    parameter says it affects qualification; the report lists them.

13. **Low. Miscellany** left open: the identity codec can write a list into
    a tuple field, the tuple codec is shallow, an `init=False` field can be
    declared as a setting, two rejections are recorded for one agentic
    change lacking a proposal, and `source_digest` and
    `implementation_digest` are stored but never compared to a source.

## Verified sound

Unauthorized pins refused; loop profile above domain policy above agent
proposal; an invalid explicit pin cannot fall back; unsupported and unknown
support refused with both allowances; unavailable refused without
`allow_unavailable`; expired facts read unknown and are refused; wrong
target reference and missing grants refused; private and dunder fields
refused; expiry compares as instants; every fact, phase, mode, mutability,
codec, constraint, default, description, and sensitivity change moves the
target digest; a stale target or values digest is refused; preference
proposals that are subsets, supersets, foreign, stale, or untyped are
invalid; adapter exceptions leak no text; the meta-selector's own score
cannot make an unqualified engine eligible; the layering consumer refuses
non-executable indices through allowed values; reports are deterministic.

## Not verifiable offline

Live provider behaviour, real task populations, and native harness
reconfiguration are outside these modules; the advisory note's
"invocation-time revalidation" has no implementation here and is delegated
to callers by the guide.
