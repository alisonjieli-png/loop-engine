# Reconcile invoices

This example gives each invoice its own child loop and makes retry attempts in
a vendor lookup visible.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/06_reconcile_invoices/run.py
```

- Network or model: none
- External effects: none
- Shows: custom steps, nested loops, stop conditions, and visible retries
- Does not show: accounting-system integration or payment authorization
