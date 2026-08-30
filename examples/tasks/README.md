# Downloadable task files

These task files are acceptance data for the public `solve` command. They are
not branches in the generic runtime.

Download one task directly from GitHub:

```bash
curl -LO \
  https://raw.githubusercontent.com/alisonjieli-png/loop-engine/main/examples/tasks/01-expense-report.txt
```

Set the provider once before running a task:

```bash
export OLLAMA_API_KEY="your-key"

loop-engine models probe ollama_cloud \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 1 \
  --max-total-tokens 70000
```

Stop if the provider probe fails.

## 1. Build a utility

[Download the task](01-expense-report.txt?raw=1), then run:

```bash
loop-engine solve \
  --file 01-expense-report.txt \
  --workspace ./expense-workspace \
  --runs-dir ./expense-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --model-id deepseek-v4-flash:0731 \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

## 2. Transform inventory data

Download the [task](02-inventory-transform.txt?raw=1) and
[sample inventory](../22_product_quickstart/fixtures/inventory.csv?raw=1).

```bash
loop-engine solve \
  --file 02-inventory-transform.txt \
  --dataset inventory.csv \
  --allow-source-to-model \
  --workspace ./inventory-workspace \
  --runs-dir ./inventory-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

## 3. Index Markdown documents

Download the [task](03-document-index.txt?raw=1) and the two sample files:

- [alpha.md](../22_product_quickstart/fixtures/docs/alpha.md?raw=1)
- [beta.md](../22_product_quickstart/fixtures/docs/beta.md?raw=1)

Place the Markdown files in `sample-docs/`, then run:

```bash
loop-engine solve \
  --file 03-document-index.txt \
  --repository ./sample-docs \
  --allow-source-to-model \
  --workspace ./document-workspace \
  --runs-dir ./document-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

## 4. Repair a failing package

Download the [task](04-package-repair.txt?raw=1) and sample package files:

- [calc.py](../22_product_quickstart/fixtures/failing_package/calc.py?raw=1)
- [test_calc.py](../22_product_quickstart/fixtures/failing_package/test_calc.py?raw=1)

Place the Python files in `failing-package/`, then run:

```bash
loop-engine solve \
  --file 04-package-repair.txt \
  --repository ./failing-package \
  --allow-source-to-model \
  --workspace ./repair-workspace \
  --runs-dir ./repair-runs \
  --interaction-mode autonomous \
  --model-route cloud.default \
  --authorize-model-calls \
  --max-model-calls 16 \
  --max-total-tokens 1000000
```

## 5. See an honest blocker

[Download the task](05-capability-gap.txt?raw=1). It deliberately requests
effects and authority that the public solve path does not have. A correct run
must return an authority or capability blocker, not `COMPLETED_VERIFIED`.

## Inspect any run

```bash
loop-engine --runs --runs-dir ./expense-runs
loop-engine --report @last --runs-dir ./expense-runs
loop-engine --studio --runs-dir ./expense-runs --port 8765
```

The Studio reads saved Run History. It does not rerun the task.
