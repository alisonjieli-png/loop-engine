# Refuse secrets and unsafe paths in generated files

Check every generated file before it is written and again when it is verified on disk. Refuse the file and name it when its path can escape or its text looks like a secret.

## When to use it

Use it whenever code or configuration written by a tool or a model is packaged for other people: exports, archives, pull requests and containers.

## Steps

1. Accept only relative paths. Refuse an empty path, `.` and `..`, a leading slash, a backslash, any `..` part, a drive prefix and any control character.
2. Refuse content that matches a secret shape. The shapes are patterns, not a list of known secrets:
   - a key that starts with `sk-` followed by twenty or more letters or digits;
   - an access key identifier that starts with `AKIA` followed by sixteen upper case letters or digits;
   - a bearer authorization header that carries a token;
   - the header line of a private key block.
3. Refuse content that imports the framework that produced it, when the package must run on its own.
4. Raise a typed error that names the file for every refusal.
5. Run the same content scan again during verification, on the files as they are on disk.
6. During verification, walk from the file up to the package directory and refuse a symbolic link at any level. Then resolve the path and require that it is still inside the package directory.

## Checks

- A file path of `../outside.py` is refused. So is `/etc/passwd`.
- A file whose text holds a private key header is refused, and the error names that file.
- A file that was changed on disk after the export fails the digest check before it reaches the content scan.
- A symbolic link inside the export that points outside it is refused.

## Known-wrong example

A packager checks only that the path text has no `..` part. The export holds a symbolic link named `data` that points to the home directory. The verifier then reads `data/notes.txt`, which passes the text check and leaves the package. Walking the path and refusing a link at every level closes this gap.

## What to record

- Each refusal with the file and the rule that refused it, without copying the secret-shaped text into the record.
- The digest of every accepted file.

## Source

- `src/loop_engine/code_nodes/solution_export.py`: `ExportedFile`, the path and content checks used at construction, and the path resolution used by `verify_export`.

Licence: MIT. Compiled from revision 9a483df. The checks use only the Python standard library.
