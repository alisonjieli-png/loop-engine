# Inspect five text requests

This is a task-intake component check. It does not execute the five requested
solutions.

The example sends five plain-text requests through the same Practitioner
`Loop`. Four use autonomous interaction mode. One contains a material gap that
requires a question. This first inspection makes no model or network calls.

The output labels each request as:

- `ready`: every missing value is provided or covered by a registered
  delegated-choice policy;
- `needs_clarification`: interactive mode would ask a material question;
- `abstain_required`: autonomous mode cannot resolve the request safely.

Autonomous does not mean unrestricted. A missing permission, contract, or
non-delegable fact produces a terminal abstention instead of an invented value.

Run from a checkout after installing Loop Engine:

```bash
python examples/20_compile_text_tasks/run.py
```

The five files in `tasks/` are inputs only. They do not contain code or create
task-specific runtime classes.

The repository-audit request is intentionally unsupported by the current
template catalog. In autonomous mode it must terminate with
`abstain_required`. That result is part of the example, not a hidden failure.
The source-digestion request uses `ask_when_material` and omits its sources, so
it returns `needs_clarification` without opening an interactive prompt.

## Live Ollama check

The same five task files also support an authorized live orientation check.
The first inspection stays model-free. One Ollama Cloud model then reviews the
next-state decision for each task, and ordinary code validates all five typed
responses. This check does not execute the requested solutions. The model
cannot grant permissions or claim that work ran.

Run it only when provider calls are authorized:

```bash
python examples/20_compile_text_tasks/run_live.py \
  --authorize-model-calls \
  --max-model-calls 5 \
  --evidence-out /tmp/live-ollama-scenarios.json
```

The live runner uses `ModelGateway`, pins one provider route, disables
failover, and allows one physical attempt per task. Its saved evidence contains
task, prompt, output, and error digests. It does not contain credentials, raw
prompts, raw model output, private reasoning, or provider error text.

The suite derives its total token ceiling from the selected model's declared
maximum and the five exact assembled prompts. `--max-total-tokens` is optional
and can impose a stricter user ceiling, but it cannot undercut that derived
minimum.

GitHub Actions runs this live check once on trusted pushes to `main`. It does
not run in the three-version Python matrix or on pull requests. Only the live
execution step receives `OLLAMA_API_KEY`.
