# Accepted test outputs

The script reads one result line per test. Save the whole output of each run, standard output and standard error together, as UTF-8 text.

| Runner | Save the output of | A test id looks like |
|---|---|---|
| pytest | `python3 -m pytest -rA` or `-v` | `tests/test_dates.py::test_rejects_day_32` |
| unittest | `python3 -m unittest -v` | `tests.test_dates.DateTests.test_rejects_day_32` |
| go | `go test -v ./...` or `go test -json ./...` | `TestParseDate` or `TestParseDate/day_32` |
| cargo | `cargo test` | `dates::tests::rejects_day_32` |
| JUnit XML | the report file any runner writes | `tests.test_dates.test_rejects_day_32` |

## Rules

- Use the same command, the same folder and the same test selection for both runs. Outputs of two different runners fail `same_runner_format`, because their test ids do not line up.
- Quiet output, such as `pytest -q`, lists only the failures. It cannot show that the other tests passed, so `baseline_has_other_tests` fails. Save `-v` or `-rA` output instead.
- The format is detected. Add `--format pytest`, `unittest`, `go`, `cargo` or `junit` when detection picks the wrong one.
- A short id works when it names one test, for example `test_rejects_day_32`. When two tests share it, the script refuses and asks for the full id.
- An id without its bracket part, for example `tests/test_dates.py::test_parse`, means every parameter case of that test. It failed before when any case failed, and it passes after only when every case passed.
- A test that prints text can split its own result line. Keep output capture on (for pytest, do not pass `-s`) or save a JUnit XML report.
- JUnit XML that holds DOCTYPE or ENTITY declarations is refused.

## Which files count as tests

A changed file counts as a test when one of its folders is named test, tests, testing, `__tests__`, spec, specs or e2e, or when its name looks like `test_x.py`, `x_test.py`, `conftest.py`, `x_test.go`, `x.test.ts`, `x.spec.js`, `x_spec.rb`, `XTest.java` or `x_test.rs`. For another layout, add a pattern such as `--test-glob 'checks/**'`. In a pattern, `*` stays inside one folder and a whole `**` segment crosses folders.
