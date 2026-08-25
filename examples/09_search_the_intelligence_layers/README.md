# Search the four intelligence layers

This example builds the real categorized catalog, adds one prior run and one
piece of user guidance, then performs one comparable search across all layers.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/09_search_the_intelligence_layers/run.py
```

- Network or model: none
- External effects: writes `example-output/intelligence-layers/`
- Shows: layer, category group, category, scope, lifecycle, and source metadata
- Does not treat Runtime Memory as a fifth layer; it remains run-scoped notes
