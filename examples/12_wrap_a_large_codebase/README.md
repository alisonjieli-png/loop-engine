# Wrap a large codebase

This example represents a forty-file, one-million-line fulfillment worker as
one small top-level card and six subsystem cards. The repository body and a 9 GB
dataset remain behind separate digest-bound references.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
python3 examples/12_wrap_a_large_codebase/run.py
```

- Network or model: none
- External effects: none
- Shows: top-level card, subsystem cards, repository and dataset references,
  digest-keyed materialization cache, and Code Intelligence Loop execution
- Uses a fixture resolver, so it does not clone the example repository or load
  the example dataset
- Demonstrates three entry points: preflight, export, and postflight

The repository and dataset locators are examples. The important behavior is
that search sees only the card. The selected repository body is materialized
once, its digest is checked, and each selected entry point runs in its own
Code Intelligence Loop.

Read
[Code Intelligence templates](../../docs/components/intelligence-layers/CODE-INTELLIGENCE-TEMPLATES.md)
for package, repository, tool, skill, workflow, notebook, and service patterns.
