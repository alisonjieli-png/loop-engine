# Examples

Install Loop Engine once, then run any example. Most examples need no API key.

| | Needs | What it shows |
|---|---|---|
| [01_hello_loop.py](01_hello_loop.py) | nothing else | the smallest real loop: an answer and a log, produced together |
| [02_solve_a_problem.py](02_solve_a_problem.py) | nothing else | hand the loop a dataset and a goal; it generates its own data so it runs anywhere |
| [03_bring_your_own_model.py](03_bring_your_own_model.py) | a provider key (optional) | discovery, failover, cost attribution — and what it says when nothing is reachable |
| [04_reports.py](04_reports.py) | nothing else | text, Markdown, HTML and structured report data |
| [05_kaggle_competition.py](05_kaggle_competition.py) | Kaggle credentials and competition access | a real competition end to end, with optional submission |
| [06_your_own_loop.py](06_your_own_loop.py) | nothing else | your steps, your stop condition, your domain: invoice reconciliation |

```bash
python -m pip install .
python examples/01_hello_loop.py
python examples/02_solve_a_problem.py
python examples/06_your_own_loop.py
python examples/05_kaggle_competition.py --competition titanic
```

## Two things these examples are careful about

**A store hit outranks a model call by design.** Pass both a warm advice store
and a model and the store answers — the model is never reached. That is the
cheapest-first waterfall working correctly, and a trap if you are trying to
measure whether the model helps. Vary *what serves the step*, not just whether
a provider exists.

**The stop condition is a real choice.** `run_to_completion` runs the steps;
`success_once` stops at the first accepted success and keeps retrying until it
gets one, bounded by the budget. Example 06 shows both, and says plainly what
happened when the wrong one was chosen.
