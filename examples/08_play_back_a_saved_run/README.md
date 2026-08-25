# Play back a saved run

This example records a nested inventory run, verifies its saved hash chain,
prints the event transcript, and points Studio at the same run directory.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/08_play_back_a_saved_run/run.py
loop-engine --studio --runs-dir example-output/runs --port 8765
```

Open the playback URL printed by `run.py`.

- Network or model: localhost only; zero model calls
- External effects: saves a Run History and static HTML report
- Shows: playback without re-execution, chain verification, and Studio scrubber
- Does not show: semantic replay or a production event store
