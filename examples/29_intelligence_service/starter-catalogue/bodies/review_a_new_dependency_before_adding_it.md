# Review a new dependency before adding it

Decide whether a package is worth the permanent cost of depending on it, before the first import reaches the main branch.

## When to use it

Use it whenever someone proposes a new library, a new service or a new tool, including one an agent added while solving a task.

## Steps

1. Write down what the dependency is for, in one sentence, and what happens if it is not added.
2. Estimate the code you would write instead. If it is under about a hundred lines you understand, prefer your own.
3. Check the licence and whether it allows your use and your distribution. Record the exact identifier.
4. Check the maintenance signals: last release, open issue count, how quickly security reports are answered, how many people can publish a release.
5. Count what it brings with it. A package with forty of its own dependencies adds forty places a problem can start.
6. Check the size it adds to your build, the start time it adds, and whether it pulls in a runtime you do not already have.
7. Check what it does at import time: network calls, file writes, environment reads. A package that acts on import is hard to contain.
8. Write the decision with the reason, the version chosen and who will notice when it stops being maintained.

## Checks

- The licence identifier is recorded and allowed.
- The full dependency list, not only the direct one, was read.
- The alternative of writing it yourself was estimated, not dismissed.
- An owner is named for watching the dependency after it is added.

## Known-wrong example

A team adds a small package to pad strings, because writing it seemed wasteful. The package is one file and has one maintainer. It is later removed from the registry, and every build in the company fails at once, including the release that was meant to repair it. Twelve lines of local code would have carried no such risk.

## What to record

- The purpose, the alternative considered and the decision.
- The exact version, the licence identifier and the full dependency list.
- The owner who watches it.

## Source

- `src/loop_engine/core/code_intelligence_assets.py`: before a reusable code asset is treated as active here, its record must carry a source identity, a version, its dependencies, its declared effects, a licence, a typed input and output contract and a digest.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision 1700841.
