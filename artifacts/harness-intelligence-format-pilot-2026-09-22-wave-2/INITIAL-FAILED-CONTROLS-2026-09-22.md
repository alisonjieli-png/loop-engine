# Initial independent-review failures

This is the preserved failed snapshot of the second multi-file candidate batch. The [initial manifest](manifest-initial-failed-2026-09-22.json) has SHA-256 `92d792aa5abe5bbe7c6609fc0d49928fa86917ab91831560411ec86a9cf7715e`. It identifies the exact pre-repair source bytes. The independent reviewer found the cases below. The producer added known-wrong tests before each repair. The first full pre-repair run had 34 tests, six failures and one timeout error. Two later ZIP controls also failed against the unchanged original ZIP script before its repair.

| Known-wrong input | Initial observation |
|---|---|
| Both join inputs contain only a single-space key | Exit 0, `blank_keys=0`, projected join rows 1. |
| ZIP contains `Readme.txt` and `README.txt` | Exit 0; no portable path collision. |
| ZIP contains composed `café.txt` and decomposed `café.txt` | Exit 0; no normalized path collision. |
| ZIP contains `report.txt` and `report.txt.` | Exit 0; trailing-dot alias accepted. |
| ZIP contains reserved Windows device name `CON` | Exit 0; reserved name accepted. |
| ZIP contains nested alternate-data-stream colon, reserved device names and trailing-space component | Exit 0; all four invalid components accepted. |
| ZIP contains Unix FIFO and character-device metadata plus a setuid regular entry | Exit 0; unsupported and privileged modes accepted. |
| ZIP contains 130,000 zero-byte entries in 11,700,098 bytes, run under a 96 mebibyte address-space cap | Uncaught `MemoryError` before the 5,000-entry check, no JSON response. |
| ZIP contains 500 distinct zero-byte entries, each with 5,000 nested `a/` segments, in 10,040,802 bytes | No JSON response within five seconds; the deep-path control timed out. |

These are candidate blockers, not customer incidents. The initial manifest and failures remain here beside the successor review. A pass from the repaired local tests still does not approve or publish the three packages.
