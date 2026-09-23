# Replace a credential without an outage

Change a key or a password while the system keeps running, by letting the old and the new one work at the same time for a short period.

## When to use it

Use it on a schedule for every long lived credential, and immediately whenever one may have been exposed.

## Steps

1. Check first that the system can hold two valid credentials at once. If it cannot, that is the change to make before any replacement.
2. Create the new credential with the same grants as the old one, and verify those grants before switching anything.
3. Add the new credential to the store, so both are valid.
4. Move the callers over one at a time, watching each one after the move.
5. Watch the use of the old credential until it reaches zero. Do not rely on a list of callers, because one is always forgotten.
6. Disable the old credential without deleting it, so a mistake can be undone quickly.
7. After a period you decide in advance, delete the old credential.
8. Record what was replaced, by whom and when, and set the next replacement date.

## Checks

- Two credentials can be valid at once, and a test shows it.
- The grants of the new credential were verified before the switch.
- The use of the old credential reached zero before it was disabled.
- Disabling was reversible for a stated period.

## Known-wrong example

An engineer replaces an interface key by editing the value in the store, because it is the same field. Every service using it starts failing within a minute, including a background job whose owner is on holiday. The rollback takes an hour because the old value was not kept. Adding the new key beside the old one would have made the switch invisible.

## What to record

- The credential, the reason for replacing it and the date.
- The callers moved and the moment the old use reached zero.
- The date the old credential was disabled and the date it was deleted.

## Source

- `src/loop_engine/core/service_api.py`: the hosted surface here stores a tenant key as a digest rather than the value, so a key can be checked, replaced and withdrawn without keeping a copy of it.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
