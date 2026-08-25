# Run a Kaggle competition workflow

This advanced example downloads and solves a simple top-level CSV competition.
It can submit only when you explicitly pass `--submit`.

```bash
python -m pip install "git+https://github.com/alisonjieli-png/loop-engine.git"
```

Run from the repository checkout:

```bash
python3 examples/05_kaggle_competition/run.py --competition titanic
```

- Network: Kaggle download; optional model use with `--model`
- External effects: download, local files, and optional submission
- Requirements: Kaggle credentials and accepted competition rules
- Shows: a narrow competition workflow with local validation
- Does not support: arbitrary archives, nested data, separate label tables,
  multiple related tables, or non-tabular competitions
