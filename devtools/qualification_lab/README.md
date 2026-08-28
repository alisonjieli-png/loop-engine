# Loop component qualification lab

This is a standalone black-box reference lab. It does not import
`loop_engine`, read private run state, or share the Loop Engine runtime. Copy
this directory into a separate repository when you want complete process
isolation.

The lab qualifies one component contract at a time. Its deterministic runner
renders one bounded prompt per case, optionally sends that prompt to Ollama,
validates the returned JSON, and audits a saved Loop Engine result for progress
and terminal-state defects.

## Run without a model

```bash
python runner.py list
python runner.py render --case route-breakout
python -m unittest -v test_runner.py
```

## Run one bounded Ollama qualification

```bash
export OLLAMA_API_KEY='YOUR_OLLAMA_API_KEY'

python runner.py ollama \
  --case route-breakout \
  --model deepseek-v4-flash:0731 \
  --base-url https://ollama.com
```

The model is advisory. A case passes only when every registered invariant has
an explicit result and no required evidence is missing.

## Audit a saved Loop Engine run

```bash
python runner.py audit-run \
  --result /path/to/adaptive-result.json
```

The audit reports repeated research, deterministic artifacts that were not
integrated, excessive passes, repeated verification gaps, and terminal-state
contradictions. It never changes the run.

## Qualification order

```text
Component qualification
├── Identity and passivity
├── Atomic deterministic operation
├── Typed input and output contract
├── One interaction
├── One state integration
├── Verification scope
├── Continue and exit conditions
├── Two-component composition
├── One complete pass
└── Bounded multi-pass task
```

Do not begin with a flagship task. A component advances only after its own
positive, negative, ambiguous, adversarial, replay, and mutation cases pass.
