# Require a test run after the last edit

## What is active

A hook records each source file you edit and each run of the step's test command. The test command is in `.baltor/step/require-tests-before-stop.json`. When you try to finish and a source file changed after the last test run, the hook blocks the finish one time and names the command to run.

Run the tests yourself after your last edit, before you finish. A failing run still counts, but you must read its result. A run in the background, a run after `||` and a run that only lists or describes tests do not count.

If that file is missing, the hook is off. Still run the project's tests after your last edit, and say in your handoff that the file was missing.

## If something is refused

1. Run the named test command exactly as written.
2. Read the result. Fix failures your change caused.
3. If a failure is not yours or cannot be fixed in this step, write it into your handoff with the failing test name.
4. Then finish. The hook does not block the same changes a second time.
