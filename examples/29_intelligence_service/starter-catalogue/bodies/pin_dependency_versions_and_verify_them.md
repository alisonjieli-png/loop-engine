# Pin dependency versions and verify what you install

Make every build install exactly the same bytes, and check those bytes before they run.

## When to use it

Use it for any project that builds more than once: a service, a library you publish, a container image, or a tool your team installs.

## Steps

1. Separate the versions you accept from the versions you install. The first is a range you choose; the second is one exact version per package.
2. Keep the exact list in a file in the repository, produced by the package tool, and install from that file everywhere.
3. Store the digest of each downloaded file in that same list, and make the installer refuse a file whose digest does not match.
4. Pin your own build inputs too: the language version, the base image by digest rather than by tag, and the tool versions.
5. Update deliberately, on a schedule, in a change that only updates dependencies, so a failure has one cause.
6. Read the notes for each update that crosses a major version, and run the full suite before merging.
7. Keep one command that rebuilds the exact list from the accepted ranges, so an update is reproducible.
8. Check in continuous integration that the committed list is the one the accepted ranges produce.

## Checks

- Two builds from the same revision install the same versions and the same digests.
- The installer refuses a file whose digest does not match.
- The base image is named by digest, not by a moving tag.
- Dependency updates arrive in their own change with the suite run.

## Known-wrong example

A build installs the latest version that matches a range. It works for months. One morning a dependency of a dependency publishes a broken release, and every build fails, including the one carrying the urgent fix. Nobody can say which versions the last good build used. An exact committed list would have kept the build working and made the difference one line.

## What to record

- The exact version list with digests, committed.
- The base image digest and the language version.
- The date and content of each dependency update.

## Source

- `src/loop_engine/core/skill_registry.py`: this repository computes an exact reference and a digest for each file of a packaged skill, and keeps discovery of a skill separate from loading its full text.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision d893bba.
