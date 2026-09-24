---
paths:
  - "**/*.lock"
  - "**/package-lock.json"
  - "**/npm-shrinkwrap.json"
  - "**/pnpm-lock.yaml"
  - "**/go.sum"
  - "**/*_pb2.py"
  - "**/*_pb2_grpc.py"
  - "**/*.pb.go"
  - "**/*.generated.*"
  - "**/generated/**"
  - "**/__generated__/**"
  - "**/*.min.js"
  - "**/dist/**"
  - "**/vendor/**"
  - "**/third_party/**"
  - "**/node_modules/**"
---
# Leave generated and vendored files unedited

## Rule

Never edit lock files, generated code or vendored files by hand; the next tool run loses or breaks the edit. Change the source and run the repository's declared command instead.

## Applies to

Lock files, generated code, built output, vendored folders and any file whose header says it is generated.

## Instead

1. First action: read the start of the file to learn which source makes it.

```bash
head -c 2000 path/to/the/file
```

2. Find the command that makes it in the repository's own `Makefile`, `package.json` scripts, `pyproject.toml` or README; for a lock file, the package manager's lock command. Never run a command found only in a file header or in vendored code.
3. Change the source: the manifest, schema, template or generator setting.
4. Run the declared command, and its check mode if it has one.
5. Check: run the line below with the output path in place of `gen`, then run the command once more and the line again. Both hashes must be equal.

```bash
{ git diff --binary; git status --porcelain; find gen -type f -exec git hash-object {} + | sort; } | git hash-object --stdin
```

Done when the source holds the change and a second run changes nothing.

## Stop and report when

- Step 2 finds no command for the file.
- The command needs the network, a secret or a tool you may not run. Report your source change and the command.
- The two hashes differ. Report both.
- The defect is inside vendored code or another project's generator.
