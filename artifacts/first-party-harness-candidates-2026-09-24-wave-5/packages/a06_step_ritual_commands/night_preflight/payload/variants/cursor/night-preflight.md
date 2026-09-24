# Run an overnight preflight check

## Purpose
Use this right before an unattended night run, in the same harness and with the same model that will work through the night. The helper checks that this model makes real tool calls and uses their results, that the test command works, that the budget is set, that each guard file holds guard rules and no bypass, and that the queue holds work. It writes a go or no-go report.

## First action
Run the probe with your shell tool. Do not write the command as text in your reply.

```bash
python3 -I -B .baltor/night-preflight/scripts/night_preflight.py probe --root .
```

## Steps
1. Read the `nonce` value in the probe result. It is new on every run, so it cannot be guessed.
2. Show the person the `will_run` value from the probe result: the test command, folder and timeout that the check will use.
3. Run the check as a second tool call, with that exact value in place of NONCE:

```bash
python3 -I -B .baltor/night-preflight/scripts/night_preflight.py check --root . --nonce NONCE
```

4. Wait for it to finish. It runs the test command from `.baltor/night/settings.json`, which can take several minutes.
5. Read `decision`, `failed` and the `detail` of each check.
6. Do not change settings, guard files, tests or the queue to make a check pass. Only report.

## Output
Reply with the decision, the report path under `.baltor/state/night-preflight/`, the test command it ran and one line for each failed check with its detail. The night run may start only when that report file exists and says `go`. The step is done when the check has written its report.

## Stop and report when
- The probe or the check exits with status 2. Report its `reason`.
- You could not run a command as a tool call. Say so plainly: this model cannot drive the night run.
- The decision is `no-go`. Report the failed checks and wait for a person to fix them.
