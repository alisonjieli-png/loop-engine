# Complete native package review evidence

This work reviews exact multi-file packages through the existing candidate
panel. No provider call, payload execution or real candidate approval occurred.
The positive approval records in tests use explicitly marked fixture reviewers.

## Evidence retained

| Record | Observation |
| --- | --- |
| `tests-before-implementation.txt` | The first tests could not import the new adapter because it did not exist yet. This is test-first scaffolding evidence, not a functional regression failure. |
| `tests-first-implementation.txt` | Thirteen reader, format, effects and complete-prompt cases passed. |
| `tests-before-direct-payload-repair.txt` | Replacing an in-memory payload bypassed the initial fixed manifest check. The repair binds every payload again before prechecks. |
| `tests-before-versioned-persistence.txt` | Native panel configuration and versioned export were not yet implemented. |
| `tests-after-versioned-persistence.txt` | New record fields exposed six outdated manual dispatch fixtures and three assertion/fixture mismatches. |
| `tests-second-persistence.txt` | All 254 component tests passed, with one optional dependency skip, after the active fixtures were updated to the new contract. |
| `mixed-native-originals-prechecks-first.json` | The twelve original packages were initially refused by incorrect schema-media and overly broad static detection. |
| `tests-before-static-profile-repair.txt` | A positive case reproduced those false refusals. |
| `mixed-native-originals-prechecks-after-profile-repair.json` | All twelve complete eight-file packages passed deterministic prechecks after generic MIME and syntax-tree repairs. This grants no approval. |
| `tests-frozen.txt` | 260 owning-component tests passed, with one optional `datasketch` skip. |
| `removed-guards-20260923T150022973849.json` | Nine native guards detected by assertion failures, with passing baselines and no control errors. |
| `tests-python311.txt` | Bare Python 3.11 lacked `jsonschema`; tests did not run. |
| `tests-python311-with-existing-dependencies.txt` | Trying the existing Python 3.12 dependency folder under Python 3.11 lacked a compatible `rpds` extension; tests did not run. |

The direct Python 3.11 import of the repaired configuration module passed.
Full native checks on Python 3.11 still need its correctly installed dependency
environment. No shared environment was changed. Python 3.12.13 ran the final
owning-component suite.

The native guard runner changes fixed local functions in memory, never on
disk, and performs no model or supplied-script execution. It writes a new
dated JSON record each time. Older guard reports remain alongside successors.
The first integrity guard suite was also rerun: the
[successful successor](../candidate-review-integrity-2026-09-23/removed-guards-20260923T145625584580.json)
detected all eight earlier guards. Its preceding unsuccessful report remains
in that directory. The new ledger correctly refused the deliberately broken
panel output; the test now reports that unexpected lower-level exception as
an assertion about the missing panel-level refusal record.

See the [integration report](../../docs/verification/NATIVE-PACKAGE-REVIEW-2026-09-23.md)
for active versions, commands and limits.
