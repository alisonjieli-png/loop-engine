# Evidence format

The evidence is JSON: a list of entries, or an object with an `evidence` list. Each entry names the criteria it supports with `criteria` (a list) or `criterion` (one id), and has one `kind`.

| kind | Required fields | Optional fields | Holds up when |
|---|---|---|---|
| `test` | `test`, `output` | none | The test, or every parameter case of it, passed in the saved test output. |
| `command` | `command`, `exit_code`, `output` | `expect_exit` (default 0), `sha256` | The saved output exists, matches `sha256` when it is given, does not contradict `exit_code`, and `exit_code` equals `expect_exit`. |
| `file` | `path` | `sha256`, `contains` | The file exists, matches `sha256` and holds the `contains` text when they are given. |

A failing test or a wrong exit code contradicts every criterion its entry names. Any other kind, such as a note, is not evidence. Every path is relative to the workspace root.

The `output` of a command is the file its run was saved to. An exit code typed into the evidence without that file does not count (`output_not_cited`). The script reads the file by itself: a JSON record with `exit_code` or `passed`, a JUnit XML report, or a summary line of pytest, unittest, go test, cargo test, Jest or a Gradle or Maven build. When that file records another exit code, or shows a failure beside `exit_code` 0, or a pass beside a nonzero `exit_code`, the entry contradicts its criteria.

## Criteria ids

Ids come from the checklist, written as `AC-1: text`, `[R2] text` or `C3) text`. Items without an id are numbered C1, C2 and so on, in order. A Markdown checklist is read from the list under the first heading that says acceptance, criteria or done. Without such a heading, every checkbox item counts. A nested item belongs to its parent. JSON criteria are a list of strings, or of objects with `id` and `text`, alone or under a `criteria` or `acceptance_criteria` key, as a ticket criteria extractor writes them.

## Example

```json
{"evidence": [
  {"criteria": ["AC-1", "AC-2"], "kind": "test", "test": "tests/test_slugs.py::test_lowercases_and_collapses_spaces", "output": "evidence/after-run.txt"},
  {"criterion": "AC-3", "kind": "command", "command": "python3 -m pytest -rA", "exit_code": 0, "output": "evidence/after-run.txt"},
  {"criterion": "AC-4", "kind": "file", "path": "CHANGELOG.md", "contains": "slugify"}
]}
```

To give the entries without writing a file, put them on standard input:

```bash
python3 -I -B SKILL_DIR/scripts/verify_criteria_evidence.py --criteria ticket.md --evidence - <<'EOF'
{"evidence": [{"criterion": "AC-3", "kind": "command", "command": "python3 -m pytest -rA", "exit_code": 0, "output": "evidence/after-run.txt"}]}
EOF
```

Saved test outputs can come from pytest (`-rA` or `-v`), `python -m unittest -v`, `go test -v` or `-json`, `cargo test`, or a JUnit XML report.
