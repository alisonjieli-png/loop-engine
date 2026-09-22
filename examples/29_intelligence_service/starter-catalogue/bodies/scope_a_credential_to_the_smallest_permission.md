# Scope a credential to the smallest permission that works

Give each caller its own credential, limited to the actions and the data it really needs, and for no longer than it needs them.

## When to use it

Use it whenever you create a key, a token, a database user or a service account, including one for a script, a test or an agent.

## Steps

1. List the exact actions the caller performs and the exact data they touch.
2. Create a separate credential for that caller. Do not share one credential between two callers.
3. Grant only those actions. Start with read, and add write only where a step needs it.
4. Limit the reach: one database schema, one storage folder, one set of records, one set of addresses.
5. Give the credential an expiry. A credential without one is a permanent risk.
6. Make the credential traceable to its holder, so a record shows who acted.
7. Cap how much a credential can do, such as a spending limit or a request rate, when the interface offers it.
8. Review the grants on a schedule and remove the ones nothing uses.

## Checks

- Each caller has its own credential with its own expiry.
- Removing one grant breaks exactly one caller, and the tests show which.
- An action outside the grant is refused, and a test proves it.
- Unused grants are removed at the review.

## Known-wrong example

A reporting script is given the same administrative database user as the application, because it was quicker. Months later the script is changed to clean up old rows and, through an error in a date filter, deletes live orders. A read only user limited to the reporting schema would have made that change impossible and the error visible at once.

## What to record

- The caller, its actions, its credential and the grants.
- The expiry and the review date.
- The refusals observed when a caller went outside its grant.

## Source

- `src/loop_engine/core/credential_leases.py`: this repository hands out a lease with a named scope, a lifetime and a ceiling on how many are live at once, so a process acts without ever holding the credential itself.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision e2898c7.
