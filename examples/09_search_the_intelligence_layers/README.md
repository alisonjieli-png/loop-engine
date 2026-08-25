# Search the four intelligence layers

This example builds the real categorized catalog, adds one prior run and one
piece of user guidance, then searches all four layers through one loop. Search
returns body-free `LoopRef` objects. The example selects one reference and
materializes only that item through a second loop.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/09_search_the_intelligence_layers/run.py
```

- Network or model: none
- External effects: creates and removes a temporary local example directory
- Shows: layer, category group, category, scope, lifecycle, source metadata,
  search loop identity, selected `LoopRef`, and access loop identity
- Does not treat Runtime Memory as a fifth layer; it remains run-scoped notes
