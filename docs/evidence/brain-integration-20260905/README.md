# Frozen generated duration-parser artifacts

These two files are the unchanged output of public repair run
`adaptive-51141ecb49499529308e8197`. They are evidence fixtures, not a built-in
solver, promoted Code Intelligence, or an unseen evaluation population.

The model generated both files. The existing Docker executor ran 34 unit tests,
and a separate unchanged oracle passed 179 checks. See the
[integration report](../../verification/BRAIN-INTEGRATION-CODE-ONLY-2026-09-05.md)
for the failed predecessors, exact scopes, runtime repairs, and limitations.
No private prompt, credential, or competition data is included here.

`independent_duration_probe.py` is the unchanged independent oracle. Its
SHA-256 is `1b2d365d959fbda3bd03a69e03d292f507827c8f4888db04767b3952fcd73307`.
Run it inside the same container with
`python independent_duration_probe.py --project-root /work --module iso_duration --function parse_duration`.
It emits a JSON report. Inspect the reported checks and counts; a successful
process exit alone does not establish that the candidate passed.

| File | SHA-256 |
|---|---|
| `iso_duration.py` | `812389078e56be4c5bc3ab0da57539df2bf6a023525d73e112e3e65087f4929d` |
| `test_iso_duration.py` | `e34c05ef13a6b10a6a10e247795bced80cf7e05ba365d96bc4f4b0fcbdc990c0` |

Run the published fixture in the same pinned sandbox from the repository root:

```bash
docker run --rm --pull never --network none --read-only \
  --cap-drop ALL --security-opt no-new-privileges \
  --user "$(id -u):$(id -g)" --memory 256m --cpus 1 --pids-limit 64 \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=67108864 \
  --env PYTHONDONTWRITEBYTECODE=1 \
  --volume "$PWD/docs/evidence/brain-integration-20260905:/work:ro" \
  --workdir /work \
  python@sha256:2407c61b1a18067393fecd8a22cf6fceede893b6aaca817bf9fbfe65e33614a3 \
  python -m unittest
```

The tested scope is integer Y/M/D/H/M/S unit forms with the requested fixed
year/month conversion. Do not claim complete ISO-8601 conformance or use these
published examples as a future unseen holdout.
