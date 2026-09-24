# Project commands and layout

## Applies when

You build, test, lint, format or change code in this project. The host filled in the values below before the step started.

## Rules

1. For build, test, lint and format, use only these commands, from the workspace root. Never guess other build or test commands or install anything.
   - Build: `{{BUILD_COMMAND}}`
   - All tests: `{{TEST_COMMAND}}`
   - Tests in one file: `{{TEST_ONE_FILE_COMMAND}}`, with the test file path in place of FILE
   - Lint: `{{LINT_COMMAND}}`
   - Format: `{{FORMAT_COMMAND}}`, with the paths of the files you changed in place of FILES
2. Every step needs All tests. Any other command written as `none` does not exist in this project: skip it and say so in your report.
3. Source code is in {{SOURCE_DIRS}}. Tests are in {{TEST_DIRS}}. Search there first.
4. Never edit these paths: {{PROTECTED_PATHS}}.
5. Before your first edit, run the tests for the file you will change, or All tests when the one-file command is `none`. Write down which tests fail. A test that already failed then is not your failure: keep working and name it in your report.
6. Put a new test beside the existing tests for the same code.
7. After your last edit, run Format on the files you changed, then Lint, Build and All tests, in that order. Report each command with its exit code, and every test that fails now but passed before.
8. After Format, check that it changed no protected path and no file you did not change, for example with `git status --short` in a git repository.
9. Do not change these commands or the test configuration to get a pass.

## If a rule blocks the work

Stop and report when All tests is `none`, a value above still shows double curly braces, a command cannot start (for example "command not found"), Format changed a protected path or a file you did not change, or the work needs an edit to a protected path. Give the command, its exit code and the last 20 lines of its output.
