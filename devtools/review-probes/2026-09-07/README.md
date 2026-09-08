# Review probes, 2026-09-07

The execution probes behind `docs/verification/CODE-REVIEW-2026-09-07.md`,
copied verbatim from the review session's scratch directory, which lives on
tmpfs and does not survive a reboot. Each `.out` or `.out.json` beside a
probe is the output recorded at `main` `f2e8b15`/`14153a1`, before any fix.

They are the regression tests for `FIXES-AND-FORK-PLAN-2026-09-07.md`: a
fix is done when its probe reads green here and red on the pre-fix tree.

The probes were written to run from the review's environment. Several
import with `PYTHONPATH=src` from the repository root; a few hardcode the
review's scratch path or `/home/username/loop-engine` and need that path
replaced before they run elsewhere. They are kept byte for byte on purpose:
the recorded outputs are evidence of what the probes did, and an edited
probe would no longer match its output.

| directory | findings |
|---|---|
| `agent_reactive/` | W1 to W10 (`probe_e_forge.py` forgery, `probe_g_natural_race.py` the SQLite race) |
| `agent_bindings/` | B1 to B7 (`probe_loop_runtime.py` section b2 is the unbounded iteration) |
| `agent_host/` | H1 to H4 (`bin/docker` is the fake docker they expect on PATH) |
| `novel_runs/` | C1 to C3, one directory per contradiction, each with `probe.py` |
| `novel_probe.py` | sections A to E of the campaign audit |
