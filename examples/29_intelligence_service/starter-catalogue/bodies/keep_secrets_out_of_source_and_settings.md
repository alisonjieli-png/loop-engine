# Keep secrets out of source and settings files

Make the settings name where a secret lives instead of holding its value, so a repository, an image or a report can never carry it.

## When to use it

Use it from the first day of a project, and whenever you add an integration that needs a key, a password or a certificate.

## Steps

1. Name every secret the system needs and where it comes from.
2. In settings, store a reference such as an environment variable name or a path in a secret store. Never the value.
3. Resolve the reference at start, refuse to start when it is missing, and never write the resolved value anywhere.
4. Keep secrets out of build arguments, image layers, command lines that other users can list, and error messages.
5. Give each environment its own secret. A development key that also works in production is a production key.
6. Add a check to the build that refuses a commit containing something that looks like a key, and run it on the history once.
7. Give every secret an owner, a place it is stored and a date it will be replaced.
8. Write down what to do when one leaks, before one leaks.

## Checks

- No settings file, image layer or build log holds a secret value.
- Starting without a required secret fails with a clear message and no value in it.
- The repository history was scanned once, not only new commits.
- Each environment uses a different secret.

## Known-wrong example

A team keeps the production database password in a settings file, because the repository is private. A new developer forks it to a personal account to try something. The password is now on a machine nobody controls and in a backup nobody tracks. Changing it later requires finding every copy. A reference to an environment variable would have left nothing to copy.

## What to record

- The secret list with owner, storage place and replacement date.
- The references used in settings, never the values.
- The result of scanning the history.

## Source

- `src/loop_engine/core/service_runtime/http_entrypoint.py`: the host settings here name an environment variable with a short prefix instead of holding a secret, and the resolver refuses anything that is not such a reference and does not write the value it reads.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
