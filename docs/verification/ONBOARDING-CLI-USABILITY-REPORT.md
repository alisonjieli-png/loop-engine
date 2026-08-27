# Onboarding CLI usability verification

## Result

`VERIFIED WORKING` locally for the Linux clean-install instructions, concise
default terminal output, full-test progress, free-port Studio startup, and the
provider-specific task-compilation shortcut.

## Problems reproduced

The previous onboarding path had four concrete problems:

- the main README mixed Linux, macOS, Windows, and operating-system package
  commands;
- the full self-test suppressed output for about a minute and looked frozen;
- doctor, inventory, and the five-step demonstration printed large internal
  JSON records by default;
- Studio used fixed port `8765` and returned a Python traceback when that port
  was occupied.

The provider-assisted compilation example also required several low-level
flags and assumed that a key was already exported.

## Current behavior

The main README contains Linux commands only. It links to separate Windows and
macOS README files. None of the Linux onboarding commands changes the operating
system.

The default terminal projections are short:

- `doctor` reports readiness, version, Python, runtime, architecture status,
  zero provider calls, and the fact that credentials were not tested;
- `models inventory` separates provider definitions, credential presence,
  configured routes, and task-compilation shortcuts;
- task compilation reports status, template, binding, operator, response,
  delegated choices, and model usage;
- the five-step demonstration reports compile, solve, verification, Run
  History, candidate state, and its exact Studio command.

Every command retains its complete typed JSON projection through
`--format json`.

## Full self-test behavior

`python -m loop_engine --self-test` now prints an immediate explanation and a
heartbeat every 10 seconds. The accepted local run reported:

- `1,373/1,373` checks passed;
- `78.352` seconds elapsed;
- `0` provider calls.

A clean wheel installation passed `1,372/1,372` applicable installed-package
checks in `71.725` seconds. The source checkout has one additional projection-
freshness check because it can compare root architecture files with packaged
copies.

The conformance scanner caches each source body and syntax tree for the current
test process. Every mutation canary and live-tree check still passes.

## Studio behavior

`loop-engine --studio --port 0` asks the operating system for a free local
port, prints the selected address, and starts normally. A fixed occupied port
returns exit code `2` with this recovery instruction:

```text
Retry with --port 0 to select a free port.
```

No traceback is shown for an ordinary address-in-use failure.

## Provider shortcut

These flags select one advisory review, apply one bounded call, and use the
standard environment variable when present. Otherwise, they open a hidden
prompt:

- `--ollama-api-key`;
- `--openrouter-api-key`;
- `--opencode-go-api-key`.

The Ollama shortcut passed one real provider call. The deterministic compiler
made zero calls, the advisory review made one call, and the command did not
contain or print the raw key.

## Current limit

The alpha package still installs data, modeling, storage, and integration
dependencies together. A clean installation is therefore large. Splitting a
slim core from optional capability extras remains separate packaging work.
