# Validate a customer import

This example prepares customer rows for a safe import. It normalizes fields,
validates each row, holds duplicate customer IDs, and builds the final import
batch.

The strict validation operation fails because two source rows have invalid
email addresses. Its declared fallback separates valid rows from rows that
need review. The run does not drop bad data or hide the fallback.

Install Loop Engine directly from GitHub:

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run the example from the repository directory:

```bash
python examples/10_validate_customer_import/run.py
```

The output includes:

- the two rows that are ready to import;
- the three rows that need review;
- the compiled Solution Canvas as Mermaid text;
- the operation trace, including the validation fallback; and
- a short event-log summary for each Solution Canvas loop.

This example uses four deterministic `SolutionLoopSpec` operations. It uses no
model, network, external service, or file write.
