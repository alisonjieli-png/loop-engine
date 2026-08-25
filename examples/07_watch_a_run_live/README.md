# Watch a run live

This example shows the same run through the console, incremental JSON, and a
server-sent event stream. The finished Chronicle is saved for Studio playback.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/07_watch_a_run_live/run.py --port 8770 \
  --runs-dir example-output/runs
```

Open `http://127.0.0.1:8770` while it runs. You can leave scoped advice and
restart the fixture to see that guidance consulted on the next run.

- Network or model: localhost only; zero model calls
- External effects: saves a Chronicle under `example-output/runs/`
- Shows: console, polling, SSE parity, modes, intelligence pulls, and closure
- Does not show: an external provider or remote deployment
