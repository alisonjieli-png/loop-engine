# Continuous integration timing, September 26, 2026

Kind: dated evidence for roadmap step S-6.200, the owner's request to speed
up the merge and deployment process.

| File | What it holds |
|---|---|
| `before.json` | The ten newest completed runs of the CI workflow on `main` before the change, from `gh run list` and `gh run view --json jobs`: each job and each step with its duration in seconds. Measured on September 26, 2026 at about 12:30 UTC. |
| `module-times-2026-09-26.json` | The wall seconds of each of the 102 tools test modules, run alone in its own process on the development machine, six at a time. The shard manifest `tools/ci_test_shards.json` was balanced on these numbers. Two modules failed in that run for reasons outside the modules: `test_architecture_audit` needed the report layout dependency, which was then installed, and `test_build_records_index` reports the stale committed records index that also fails the latest run of `main`. |
| `expected-after.json` | The expected wall time of the new layout, from arithmetic on the measured step medians. It is an expectation, not a measurement. |

Measured before the change: the ten runs took 413 to 1,500 seconds of wall
time; the eight that ran every job to the end took 1,451 to 1,500 seconds.
The slowest job, "suite + conformance gates (3.10)", took a median of 1,466
seconds. Its steps, by median: the tools tests 522 seconds, the self-test
354, the hardcoding gates 195, the component guides 148, the conformance
gates 85, the site map 56, the install 36.

Not yet measured: the wall time after the change. The next run of `main`
records it; save that run's jobs beside these files under a new name
(`after.json`), and do not overwrite `before.json`.
