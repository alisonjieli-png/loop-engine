# Respond to a report that a dependency is vulnerable

Turn a security advisory into a decision you can defend, instead of upgrading everything or ignoring it.

## When to use it

Use it when a scanner, a mailing list or a customer reports a weakness in something you ship or run.

## Steps

1. Confirm that you actually use the affected package and the affected version. Read your exact version list, not the accepted range.
2. Read what the weakness needs in order to be exploited: a particular function, a particular setting, or input from outside.
3. Decide whether your use reaches it. A parser weakness does not apply if you never parse untrusted input with that package.
4. Record the decision as one of three: not affected with the reason, affected and fixed by an upgrade, or affected with a temporary limit in place.
5. If you upgrade, upgrade only that package first and run the full suite. Keep the upgrade separate from other work.
6. If you cannot upgrade, write down the limit you applied, who approved it and when it will be reviewed again.
7. Mark the old version as one that must not be used, so a later change cannot bring it back quietly.
8. Tell the people who need to know, with the exact versions and the date.

## Checks

- The affected version is confirmed against the exact installed list.
- The reason for not affected, if that is the answer, names the code path that is absent.
- An upgrade was released and observed working, not only merged.
- The old version cannot be installed again without a new decision.

## Known-wrong example

A scanner reports a serious weakness. The team upgrades twelve packages on the same afternoon to clear the report. Two of them change behaviour, the service breaks, and the rollback also removes the security fix. One upgrade at a time, with the suite run between them, would have shipped the fix the same day and kept the service up.

## What to record

- The advisory, the affected versions and your exact installed version.
- The decision with its reason and the approver for any temporary limit.
- The version you moved to and the date it was observed running.

## Source

- `src/loop_engine/core/asset_lifecycle.py`: this repository keeps one vocabulary for how far a resource has been promoted, with deprecated and retired as final states, so a resource that must not be used can be marked once for every consumer.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision ae7362f.
