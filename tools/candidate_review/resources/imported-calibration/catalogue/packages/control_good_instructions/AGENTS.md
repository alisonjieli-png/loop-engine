# Instructions for this repository

This repository holds a small Python service that reads orders from
`data/orders.csv` and writes a daily summary to `reports/`.

## Before changing code

- Run `python -m pytest -q` first. Every test must pass before and after
  your change; a test you did not touch that starts failing is your problem
  to explain, not to delete.
- Read `docs/decisions.md` for the choices already made. Do not reverse one
  without adding a dated note there that says why.

## Conventions

- Python 3.11. Format with `ruff format` and fix imports with `ruff check --fix`.
- No new dependency without adding it to `pyproject.toml` with a pinned
  version and a one-line reason in the pull request.
- Money is stored in integer cents, never in floats.
- A function that reads a file takes its path as an argument; nothing reads
  a hard-coded path.

## When you finish

- Add a line to `CHANGELOG.md` under "Unreleased".
- Say which tests you ran, which files you changed, and anything you were
  unsure about.
