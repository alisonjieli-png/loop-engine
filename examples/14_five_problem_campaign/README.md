# Run five open problems

This example runs five utility problems through deterministic Practitioner
loops. Each problem uses a frozen input and evaluator. Every run is saved as a
Run History in a temporary directory.

```bash
python -m pip install "https://github.com/alisonjieli-png/loop-engine/archive/refs/heads/main.zip"
python3 examples/14_five_problem_campaign/run.py
```

- Network or model: none
- External effects: creates and removes a temporary local run directory
- Shows: campaign expansion, live console events, deterministic verification,
  Run History creation, and result accounting
- Problems: support priority, customer import, invoice reconciliation,
  deployment decision, and delivery estimate

Use the package CLI when you want to keep the runs for reports and Studio:

```bash
loop-engine campaign run \
  --modes deterministic \
  --runs-dir "$HOME/.loop-engine/pilot/runs" \
  --watch
```

Read [Five-problem campaign](../../docs/guides/campaigns.md) before enabling
provider-backed arms.
