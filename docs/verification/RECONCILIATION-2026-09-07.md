# Reconciling two implementations of the same review

Branch `fork/reconciled` (a1699f3), based on main at d194123.
Gates: self-test 3378 of 3378, conformance all gates pass, hardcoding 217
blocking new high findings, no allowlist problems.

## What happened

Two Claude sessions independently implemented the same 31-finding review of
2026-09-07, both branching from cc6117f. One landed on main as d194123; the
other became `fork/hardened-learning`. Neither knew about the other.

A 52-agent comparison ran the review's own archived probes against both
trees, dimension by dimension, and adversarially re-checked every contested
verdict. Result: main stronger on 36 findings, the fork on 6, equivalent on
3, neither on 6. Four verdicts were overturned by the verification pass,
three of them against the fork.

## What each side got wrong

Both commit messages overstated what shipped, in ways only running the code
revealed.

| Claim | What running it showed |
|---|---|
| Main: self-test 3401 of 3401 | 3358 of 3359 on this interpreter; the failure is main's own new check |
| Main: deep nesting refused typed | With the stack raised, 20,000 levels are admitted |
| Main: hardcoding delta unchanged at 260 | True, and its blocking set is byte-identical to base: zero R1 progress |
| Fork: the iteration ceiling can be set to None | Every value a caller passes is discarded; the ceiling was a hard 25 |
| Fork: an unkeyed history is labelled unverified | A signed history that was saved and reloaded also said unverified |
| Fork: W6 refusal implemented | Only the check suite ever sets the flag that turns it on |

## What the reconciled branch does differently

**B1.** The backstop lives on the supervision policy, which survives the
LoopDefinition round trip, so it is raisable. It applies in exactly the two
shapes main's pass ceiling cannot see: an open framework, which has no
passes, and a declared budget, which disables it. Both new checks assert an
upper bound rather than the constant under test, so raising the ceiling to
a million fails them. Main's equivalent check passed at 2000.

**Serialization guard.** Every declared SupervisionPolicy field is asserted
to survive to_dict, by comparing the dataclass fields to the serialized
keys. Both implementations shipped a dead knob on a different field.

**B2.** Admission declares its own maximum nesting depth and refuses by
that limit, counted without decoding and ignoring brackets inside strings.
The refusal is now a property of the boundary rather than of CPython's
stack, and the check tests both directions.

**W1.** All ten Loop-owned event kinds are refused for an unbound Loop id;
main refused eight, so a phantom Loop could still write its own beginning.
The fork's HMAC authorship module lands whole, and its label reports three
honest states instead of two.

**C6.** Main's headline digest refusal aborted the whole campaign with a
KeyError and wrote no report. Fixed and reproduced against main.

## Still open

- The authorship module refuses forged events at the history, but no
  running loop is wired through it yet. That is the change that would make
  W1 a property of the system rather than of the record.
- 217 blocking hardcoding findings remain, mostly closed vocabularies in
  five modules. CI stays red until they are dispositioned.
- Main's H1 narrowed an existing guarantee by changing the fixture of the
  check that protected it. Worth revisiting.
- The campaign's v1 audit module still executes model-authored code on the
  host beside the new container-only v2.
