---
applyTo: "**/tests/**,**/test/**,**/__tests__/**,**/spec/**,**/test_*.py,**/*_test.*,**/*.test.*,**/*.spec.*,**/conftest.py,**/pytest.ini,**/jest.config.*,**/vitest.config.*,**/__snapshots__/**,**/*.snap"
---
# Keep test changes honest

## Rule

Repair the code, not the test. Never weaken, skip, exclude or delete a test to pass a check. A new test must fail before the fix and pass after it.

## Applies to

Tests, snapshots and test settings, also in `pyproject.toml`, `setup.cfg`, `tox.ini` or `package.json`.

## Instead

1. First action: run the test file you will change with the project's test command. Keep the summary line. If nothing fails, go to step 3.

```bash
python3 -m pytest tests/test_example.py -q
```

2. Decide whether the code or the test is wrong. Change a test only when the task or a specification says the behavior changed; quote that line.
3. Write a test for the defect or new behavior and see it fail for the expected reason.
4. Repair the code until the new and old tests pass.
5. Check: rerun step 1 and read `git diff` of every changed test file and setting. Without a step 2 quote, passed plus failed must not fall, skipped, deselected and expected-failure counts must not rise, and the diff must not drop or loosen an assertion, or add a skip or expected-failure marker, an exclusion, a `try` around a checked call or a snapshot change.

Done when the new test failed first, passes now, and the check passes.

## Stop and report when

- The test contradicts the task or documentation. Leave it and report both.
- The failure comes from the environment, network or timing.
- You cannot make the new test fail before the fix.
