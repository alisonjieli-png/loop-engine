# Contributing

Thanks for looking. This project has a few unusual rules, and they exist
because they were each learned the expensive way.

## Before you open a pull request

```bash
python -m loop_engine --self-test      # complete built-in test suite
python -m loop_engine --conformance    # the zero-tolerance architecture gates
```

**Both must exit 0.** Do not configure provider keys for routine test runs.

## The rules that are actually enforced

These are machine-checked by `--conformance`, not style preferences:

| Gate | What it means |
|---|---|
| HTTP only in a declared adapter | Network calls live in `static_architecture/*_client.py` or `custom_endpoint.py`. Adding a provider means adding its adapter to `forbidden_paths.json` with a reason. Do not relax the rule. |
| No `eval` / `exec` anywhere | `logic_ast` interprets a closed operator set instead. |
| No secret-shaped literals | Scanned in code and run evidence. Evidence files must be free of credentials too. |
| Closed event vocabulary | Every ledger event maps to one of the 59 canonical families. A computed event kind is refused, because its family cannot be checked. |
| No direct resource access | Product code reaches stores through a loop envelope, never by opening them. |
| Every module's self-test runs | A test the suite never executes is not a test. |
| Module size cap (800 lines) | Exceptions must be declared with a split plan. |

If a gate blocks you, fix the cause. Do not raise a baseline to make a build
pass. The baselines are zero on purpose.

## Writing tests

Every module owns a `self_test()` folded into the suite. A few conventions
that matter more here than usual:

- **Assert properties, not states.** `0 < coverage < 1` survives the code
  improving; `coverage == 0.53` does not, and a test that fails when things
  get better trains people to ignore it.
- **Include the adversarial case.** Most defects in this codebase were found
  by the test that tried to break the rule, not the one that confirmed it.
- **NOT RUN is never PASS.** A skipped live-call test reports itself as
  skipped, with the reason.
- **Establish your own preconditions.** A test that depends on files left over
  from a previous run passes on your machine and fails on a fresh clone.

## Honesty rules for anything measured

- Token counts are provider-reported. Never estimated, and they always carry
  the provider that produced them.
- One task is not a rate. Record what a result does **not** establish next to
  what it does.
- If a model arm and a zero-model arm agree, checksum the artifacts before
  interpreting it. Identical output means the model never reached the result,
  which is a different finding entirely.

## Style

Match the surrounding code. Module docstrings state what the module owns, what
it does not own, its key invariants, and how it is verified. Comments explain
why a non-obvious rule exists. The syntax speaks for itself.

For public Markdown, follow [humanizer-context.md](humanizer-context.md) and
the [documentation templates](docs/templates/). Use simple technical English,
sentence-case headings, and the current product terms. Do not use em dashes or
en dashes.
