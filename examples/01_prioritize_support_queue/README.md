# Prioritize a support queue

This deterministic example ranks real-shaped support tickets by severity,
wait time, and customer impact.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/01_prioritize_support_queue/run.py
```

- Network or model: none
- External effects: none
- Output: ordered tickets plus a run report
- Shows: ordinary utility code inside a logged loop
- Does not show: learned prioritization or a production support-system link
