# Respond to a credential that may have leaked

Act on the assumption that the credential is already being used by someone else, and take away its power before anything else.

## When to use it

Use it the moment a key appears in a commit, a log, a ticket, a screenshot, a chat message or an error report, even when you believe nobody saw it.

## Steps

1. Withdraw the credential first. Deleting the commit, the message or the log entry does not withdraw it, and copies already exist.
2. Issue a replacement and move the callers, following the replacement procedure.
3. Find out what the credential could do. Its grants define the worst case, not your guess about the finder.
4. Read the access records for the whole period the credential existed, not only since it was noticed. Look for unusual addresses, times and volumes.
5. Decide whether data was reached. Record what you can prove, what you can rule out and what you cannot tell.
6. Remove the value from the place it leaked, knowing this is cleanup and not containment. For a repository, rewriting history does not remove copies others hold.
7. Decide who must be told, including customers and any authority, and by when. Take advice for anything involving personal data.
8. Add the check that would have caught it, and prove that the check fails on the known case.

## Checks

- The credential was withdrawn before any cleanup started.
- The access records for the full period were read, not sampled.
- What can be proved, ruled out and not told apart are recorded separately.
- A new check fails on the leaked value when it is put back.

## Known-wrong example

A key is pasted into a public issue. The team edits the message and considers it handled. The key stays valid for three more weeks, and search services have already indexed the original text. Charges appear on the account. Withdrawing the key in the first minute would have made the copy worthless.

## What to record

- The time the leak was noticed and the time the credential was withdrawn.
- The grants the credential held and what the access records show.
- The notifications made and the new check added.

## Source

- `src/loop_engine/core/credential_leases.py`: this repository gives every lease a state, including revoked and expired, so authority can be taken away at one place without collecting copies of the secret.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
