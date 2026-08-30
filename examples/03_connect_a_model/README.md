# Connect a model provider

This example checks configured providers, then makes one loop-governed task
call through the first provider that answers.

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
```

Run from the repository checkout:

```bash
python3 examples/03_connect_a_model/run.py
```

- Network: provider discovery and calls when keys are configured
- Model cost: provider checks plus one task call; inspect your provider bill
- External effects: model requests only
- Shows: honest provider availability, failover attempts, tokens, and run log
- Does not show: model quality or a cost comparison
