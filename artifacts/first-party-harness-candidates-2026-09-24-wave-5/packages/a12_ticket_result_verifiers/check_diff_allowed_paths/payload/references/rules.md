# Rules, permits and patterns

| Rule | What it refuses | `--permit` value |
|---|---|---|
| `outside_allowed_paths` | A changed, deleted, renamed or new file whose path matches no allowed pattern. A rename checks both paths. | none |
| `unsafe_path` | An empty or absolute path, a `..` segment or a `.git` folder. | none |
| `test_file_deleted` | A deleted test file, or a test file renamed out of the test folders. | `test_deletion` |
| `binary_file` | An added or changed binary file. Deleting one is allowed. | `binary_file` |
| `large_file` | A file that gains more than 2000 lines or 262144 bytes. Change the limits with `--max-file-lines` and `--max-file-bytes`. | `large_file` |
| `lock_file` | Any change to a lock file such as `package-lock.json`, `yarn.lock`, `poetry.lock`, `uv.lock`, `Cargo.lock` or `go.sum`. | `lock_file` |
| `generated_file` | A path such as `*.min.js`, `*_pb2.py`, `dist/`, `vendor/` or `node_modules/`, or a file whose diff shows a marker such as `@generated` or `Code generated ... DO NOT EDIT`. Add project patterns with `--generated-glob`. | `generated_file` |
| `symlink` | A new or changed symbolic link, which can point outside the allowed paths. | none |
| `submodule` | A changed submodule pointer. | none |

A permitted finding moves to the `permitted` list, so the report still shows it.

Files the host placed for the step are not the step's change. Give their patterns with `--ignore`; each such file moves to the `ignored` list with its reason. Files below the folder of this skill are left out the same way without an option. An unsafe path is never left out.

## Patterns

- A pattern matches the whole path from the repository root. `*.md` matches only files at the root.
- A name without `*`, `?` or braces is one file or one folder: `src/slugs.py` is that file, and `src` or `src/` is everything below `src`. A leading `./` is ignored.
- `*` and `?` stay inside one folder. A whole `**` segment crosses folders: `src/**` matches every file below `src`, and `**/*.md` matches Markdown files at any depth.
- A pattern that ends with `/` means everything below that folder. `{src,lib}/**` gives alternatives.
- Character classes such as `[ab]` and patterns that use `..` are refused.
- `--allow-file` reads one pattern per line (lines that start with `#` are skipped), a JSON list, or a JSON object with an `allowed_paths` list.

## New files

`git diff HEAD` does not show files that git does not track yet. The `--untracked` run reads their names, one per line, and checks each one like an added file. It also reads the first bytes of each file to find binary content, symbolic links and files above the size limits.

Give the output of `git ls-files --others --exclude-standard`. Lines from `git status --short` that start with `?? ` also work. A status line for a tracked file, such as ` M src/a.py`, is refused with `status_line_in_untracked_list`, because that change belongs in the `--diff` run.

## Test files

Paths with a folder named test, tests, testing, `__tests__`, spec, specs or e2e, and names such as `test_x.py`, `x_test.go`, `x.spec.ts` or `XTest.java` count as tests. Add other layouts with `--test-glob`.
