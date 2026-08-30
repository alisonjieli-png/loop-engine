# Read run reports

This example runs a checkout incident investigation with a Spawned Loop, then
writes text, Markdown, HTML, and JSON views of the same log.

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Run from the repository checkout:

```bash
python3 examples/04_read_run_reports/run.py
```

- Network or model: none
- External effects: writes `example-output/incident-report/`
- Shows: nesting, modes, steps, events, and report formats
- Does not show: live streaming or saved-run playback
