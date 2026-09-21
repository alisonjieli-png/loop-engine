# Run the restore before you call the backup a backup

Kind: recorded failure and its repair, from Runtime History and Solution
Intelligence.

## When to use this record

Use it before you tell anyone that a service can be recovered, and before you
write a recovery step into a runbook you have not executed.

## What was recorded

Two recovery exercises were run against a saved copy of a hosted pilot
service, minutes apart. Both are kept.

The first exercise passed 2 of its 3 checks. The private copy was saved with
owner-only permissions and the owned volume was removed, but the restore
exercise itself failed and the record names the error type it raised. The
record states that no production data was changed and that no new cloud
resource was created.

The second exercise passed. It checked the copy's integrity and the exact file
digests, ran the restore in a container with no network and no published
ports, and then checked the restored service twice: once immediately and once
after a restart. Both times it checked that a caller was authenticated, that
the tenant scope was preserved, that revoked records stayed revoked, that the
body digest was verified, and that repeat-safe behaviour was preserved.

## What the record refuses to claim

The saved limits are part of the record. This is local point-in-time
restoration only, with no cross-region recovery. The private copy is
permission-restricted rather than separately encrypted by the tool. Old copies
can restore old authority, so revocations and external payment state must be
reconciled before a production restore. The exercise does not establish a
scheduled off-site copy or any recovery time.

## The known-wrong case

The wrong move is to keep only the successful exercise. Without the first
record, nobody knows that the restore path failed once, why it failed, or
whether the second pass fixed it or avoided it.

## What to record

Record the copy's digest, the checks by name, the failure and its error type,
the state after a restart, and the limits.

## Source

`artifacts/architecture-audit-2026-09-19/pilot-backup-restore-1.json` (the
failure) and `pilot-backup-restore-2.json` (the pass), both record type
`pilot_backup_restore_check/v1`.
