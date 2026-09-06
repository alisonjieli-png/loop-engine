# Local OpenCode fault blocking live step runs

`opencode run` exits 1 before emitting a single event on this machine:

```
SQLiteError: no such column: replacement_seq
    at prepare (bun:sqlite:345:37)
```

The failure is inside OpenCode's own startup migration, so it happens for
every invocation regardless of model, flags or working directory. It is not
caused by `core.opencode_step_session`; that module's own offline suite
passes, and the same command fails when typed by hand.

## The database is 303 GB

Discovered while diagnosing the above:

```
~/.local/share/opencode/opencode.db       303,124,455,424 bytes   (283 GiB)
~/.local/share/opencode/opencode.db-wal     1,000,150,632 bytes
```

Root filesystem is 1.9 TB at 97 % used with 67 GB free, so this one file is
roughly 15 % of the disk.

Measured, not assumed:

| fact | value |
|---|---|
| page_size × page_count | 4096 × 74,004,994 ≈ **303 GB** |
| freelist pages | **0** |
| rows in `event` | 264,736 |
| rows in `part` | 76,376 |
| rows in `message` | 18,433 |

Zero free pages means this is not deletion bloat that a `VACUUM` would
reclaim — the pages are live. With only ~360 k rows across the three content
tables, the bytes are in individual row payloads, averaging on the order of a
megabyte per row. A per-table byte census was started and abandoned: a full
scan of a 303 GB file on a 97 %-full disk costs more than the answer is
worth while the schema is broken anyway.

## Non-destructive workaround (in use)

`XDG_DATA_HOME` relocates OpenCode's whole data directory, so a fresh path
gives a clean database and leaves the 303 GB one untouched. Verified: a live
`opencode run` completes with exit 0 this way. Credentials come from
`OLLAMA_API_KEY` in the environment rather than the data directory's
`auth.json`, so nothing needs copying.

This unblocks development. It does not reclaim the disk.

## Recommended repair — needs a human decision

The database holds session history, and `auth.json` / `mcp-auth.json` sit
beside it and hold credentials. **Nothing here has been deleted or moved.**

The likely fix is to retire the corrupt database and let OpenCode recreate
it, which resolves both the migration failure and the disk usage:

```bash
mv ~/.local/share/opencode/opencode.db{,.broken} && mv ~/.local/share/opencode/opencode.db-wal{,.broken}
```

Two caveats before running it:

1. **Renaming does not free space.** The 283 GiB is only reclaimed when the
   `.broken` files are deleted, which is the irreversible step.
2. **Session history is lost** with the database. `auth.json` and
   `mcp-auth.json` are separate files and are not touched, so providers and
   MCP credentials survive.

Worth reporting upstream: a coding-agent session store reaching 303 GB from
~360 k rows, with no pruning, looks like a bug rather than expected growth.
