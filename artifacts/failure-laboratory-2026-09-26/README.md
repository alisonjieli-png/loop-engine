# Failure laboratory numbers, September 26, 2026

These files record one run of `tools/check_package_activation.py` over the
served bundle `daily-2026-09-26-10` and one run over the twelve fixtures of
`examples/31_failure_laboratory/packages/`.

- `activation-summary.json`: the bundle and items digests, the verdict counts
  by package kind, the refusal and unknown codes, the undeclared effects, the
  collision counts, the run time and memory, and the laboratory outcome.
- `activation-findings.jsonl`: one line for each package that did not
  activate, with its served digest, every fact that did not pass and, for a
  skill, what OpenCode's listing reported, then one line for each named slot
  (a skill folder or a command file, per harness) that two or more packages
  wrote with different bytes.
- In the summary, `rerun_with_final_code` compares a second run of the final
  check with the recorded one, and `loader_listing` holds the
  `package_activation_listing/v1` summary of the run with `--observe-listing`
  (OpenCode 1.18.32), with the hand-run probe of the same listing beside it.

The research record that reads these numbers is
[Package activation and the failure laboratory](../../docs/research/PACKAGE-ACTIVATION-FAILURE-LABORATORY-2026-09-26.md).
