# Engine-generated verifier example

These are exact generated files from live run
`adaptive-b3adcefbff5a2c0f8f7bc5c0`. The task had no supplied feedback. The
engine generated the implementation, generated and reviewed the checker, and
compared its actual output outside the candidate process.

The checker imports the actual function and observes four values. It also
checks file presence, counts three assertions in the test source, and runs
unittest. Assertion counting is lexical. This is one batched comparison, not
an exhaustive test or a guarantee that generated oracles are correct.

| File | SHA-256 |
|---|---|
| `subject/seconds.py` | `2295e3ed0fdd34aa4b207753d729f9efe404055756a2be11fd1b1eb2e114f36d` |
| `subject/test_seconds.py` | `28910790c7e75ec232ce98ab0f93c72118521fb7d0e593e55ec2f9b27128c336` |
| `checks/probe.py` | `600406737231502f114b9dfc85f0ca3e852f9163c72e04ac49e17454f231e81f` |

From this directory, with the pinned image already installed:

```bash
docker run --rm --pull never --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --memory 4g --cpus 2 --pids-limit 256 --tmpfs /tmp \
  --volume "$PWD:/workspace:ro" --workdir /workspace \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3 \
  python checks/probe.py
```

The JSON output must contain four values `0`, `3600`, `5400`, and `8100`, both
file-presence flags `true`, assertion count `3`, and unittest return code `0`.
Exit zero alone is not acceptance. The engine's controller compares the
complete JSON object against the frozen expectation in its probe bundle.

These files are evidence fixtures, not a registered solver or promoted
capability. See the [verification report](../../verification/AUTONOMOUS-TASK-FEEDBACK-2026-09-05.md)
and [structured evidence](../autonomous-task-feedback-2026-09-05.json).
