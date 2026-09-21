# Set up an overnight local run

You have a hard problem, a machine with weights on it, and eight hours in
which nobody is at the keyboard. This example walks the whole setup: whether
the model fits in the memory you have, whether the server answers in the
shape the engine expects, what the night is allowed to do, what it does when
the server stops answering, and what is waiting for you at breakfast.

It runs with no provider key and opens no socket, so the setup itself is
checkable.

## Why use a loop

Every part of an unattended night is a decision nobody will be awake to
make. What happens after a failed step, how long to wait for a server that
went quiet, when to stop, and whether the result is good enough are all
decisions, and a run that takes them silently produces a morning report
nobody should trust. The loop runtime already owns them as typed settings:
declared authority, a supervision policy, a provider failure class, a
terminal code, and a saved Run History that can be played back. This example
declares each one out loud before the night starts.

## Run settings

| Setting | Value |
|---|---|
| Loop role | Practitioner loop, with one Spawned Practitioner loop |
| Run mode | Deterministic |
| Step profile | Custom four step: orient, reproduce, repair, verify |
| Intelligence layers | None searched; the layers are described, not queried |
| Runtime Memory | Used, and shown writing nothing to disk |
| Run History | Saved, verified, played back, and measured |

## Install

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

## Run it

```bash
python examples/30_overnight_local_run/run.py
```

No environment variable, key, file or port is required. To keep the saved run
and its report instead of discarding them:

```bash
python examples/30_overnight_local_run/run.py --output-root example-output/overnight
python examples/30_overnight_local_run/run.py --json
```

## Expected result

Five sections and then the guard block. Section 1 prints the memory
arithmetic for three machine tiers and four model sizes. Section 2 makes one
governed call over the real local endpoint adapter. Section 3 declares the
night and screens its route. Section 4 shows what each kind of provider
silence decides. Section 5 saves the Run History, verifies its hash chain,
plays it back, grades the night, and measures the bytes on disk.

```text
45 of 45 checks passed
```

The process exits non-zero when any check fails. Zero model calls are made,
zero sockets are opened and no credential is read.

## Watch it live

This example does not stream events. Use
[07 watch a run live](../07_watch_a_run_live/) for live viewing.

## Play it back

Yes. Section 5 plays the saved run back in process. With `--output-root` the
run survives the example, and Studio opens the same directory:

```bash
loop-engine studio --runs-dir example-output/overnight/runs --port 0
```

## What this example does not prove

It does not prove that any local server on any machine answers, or how fast,
or how well. Section 2 answers the real adapter from a fixture transport, the
way the repository's own custom endpoint checks do, so it proves the wire
format, the requested output ceiling, the token accounting and the refusal
classification, and nothing about a physical server. The machine tier rows in
section 1 are arithmetic over inputs stated in the source; read your own
model's configuration file before trusting a row for a model you have not
loaded. The disk figures are one run on one machine, not a rate.

The companion guide is
[overnight solving on local models](../../docs/guides/overnight-solving-on-local-models.md).
