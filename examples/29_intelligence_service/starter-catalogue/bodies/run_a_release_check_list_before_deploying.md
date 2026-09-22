# Run a release check list before deploying

Go through the same short list every time, so that the release that goes wrong is the one you were watching rather than the one nobody prepared.

## When to use it

Use it for every deployment to an environment that people or customers depend on, however small the change.

## Steps

1. Confirm the exact revision you are releasing, and that its checks passed on that revision rather than on a similar one.
2. Confirm what changed since the running version, and read the list. A release nobody can describe is a release nobody can undo.
3. Confirm the order: database changes that add, then the application, then any change that removes. Never the reverse.
4. Confirm the settings and secrets the new version needs exist in the target environment.
5. Deploy by an exact identifier such as an image digest, not by a moving tag, and keep the previous identifier written down.
6. Release to a small part of the traffic first, and watch the signals you chose in advance for a stated period.
7. Run the checks that only work against the live system, and write down what you observed rather than that you looked.
8. Announce the release with the revision, the time and the person to contact.

## Checks

- The released revision is the one whose checks passed.
- The previous version's exact identifier is written down before the deployment.
- Required settings and secrets are present in the target before the switch.
- The observation after release is written down with values, not with the word fine.

## Known-wrong example

A team deploys a change that reads a new settings value. The value was added to the test environment and forgotten in production. The service starts, serves errors on one path, and the cause takes forty minutes to find because the release notes list only the code change. Confirming the settings before the switch takes one minute.

## What to record

- The revision, the previous identifier and the change list.
- The settings and secrets confirmed.
- The observations after the release, with values and times.

## Source

- `src/loop_engine/code_nodes/smoke_ladder.py`: this repository proves a path in stages, starting with a deterministic local fixture that runs end to end with no model calls before any stage that touches a real provider.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision f29bddc.
