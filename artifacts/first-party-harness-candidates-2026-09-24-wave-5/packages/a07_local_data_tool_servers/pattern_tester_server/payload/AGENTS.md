# Pattern tester tool server

## What is active

`test_pattern` (local server `pattern_tester_server`) runs one Python regular expression on your texts; it opens no files. Any listed tool ending in `test_pattern` is this tool.

First action: before a cleaning rule uses a pattern, call `test_pattern` with `pattern`, `should_match` (values to accept) and `should_not_match` (values to reject).

1. Take the texts from real data, odd values too.
2. Keep the default `fullmatch` mode for whole values; in `search` mode `$` also matches before a final line break.
3. Add `replacement` to preview the rule's output.
4. Adjust the pattern until `passed` is true.

Done when `passed` is true and `should_not_match` covers each kind of rejected value.

## If something is refused

`isError: true` names the problem, such as a compile error or time limit; fix it. If it returns after a change, stop and report the pattern, texts and error. If no listed tool ends in `test_pattern`, run `python3 -I -B -m unittest discover -s .baltor/pattern-tester-server/tests`. OK means the server works but the harness did not start it; report that. Otherwise report the last line.
