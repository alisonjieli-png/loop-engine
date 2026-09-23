# Custom endpoint identity evidence

All provider responses in these controls are local fixtures. No model calls.

- `checks-before-repair.json`: known-wrong cases, 30 failing assertions.
- `checks-first-repair.json`: first successor; two existing positive fixtures lacked
  the genuine model needed to isolate their framing/completion behavior.
- `checks-after-repair.json`: 22 endpoint and 70 adapter checks pass.
- `gateway-adjacent-checks.json`: 22 gateway and 33 accounting checks pass.
- `check_removed_guards.py`: seven fixed source mutations, evaluated in memory.
- `removed-guards.json` and `removed-guards-final.json`: all mutations detected;
  final record binds final production source bytes.
- `ruff-current.json`: empty output retained from an unsuccessful invocation using
  a nonexistent virtual-environment Ruff executable; system Ruff was used next.
- `ruff-delta.json`: zero added diagnostics in either existing source module.

Run from the repository with `PYTHONPATH=src` and its Python environment:

```sh
python artifacts/custom-endpoint-reported-identity-2026-09-23/check_removed_guards.py
```
