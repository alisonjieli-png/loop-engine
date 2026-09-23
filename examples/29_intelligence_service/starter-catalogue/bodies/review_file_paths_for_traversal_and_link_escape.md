# Review file paths for traversal and link escape

Make sure a path built from outside input cannot reach a file outside the folder it is supposed to stay in.

## When to use it

Use it for uploads, downloads, archive unpacking, template loading, log file selection, and any place where part of a path comes from a request, a file name or a model answer.

## Steps

1. Name the one folder each operation may read or write inside. Write it down as an absolute path.
2. Reject any supplied component that is absolute, that contains a parent folder step, or that starts with a dot.
3. Join the supplied part to the folder, then resolve the result and confirm that the folder is still a parent of it. Do the check after resolving, not before.
4. Refuse symbolic links and hard links, both in the supplied path and in every folder along the way.
5. When unpacking an archive, apply the same checks to every entry inside it, and refuse entries that are links or devices.
6. Set a limit on the number of entries and the total size, and refuse when it is passed.
7. Refuse to overwrite an existing file unless overwriting was asked for explicitly.
8. Write tests for each refusal: a parent step, an absolute path, a link that points outside, an oversized archive.

## Checks

- The containment check runs after the path is resolved.
- Links are refused in the supplied path and in the folders above it.
- Archive entries are checked one by one with the same rules.
- Each refusal has a test that would fail if the rule were removed.

## Known-wrong example

An upload handler removes the text for a parent folder step from the file name and then joins it to the upload folder. A caller sends a name where the parent step is written twice in an overlapping way, so removing it once leaves a valid parent step behind, and the file lands in the settings folder. Resolving the joined path and checking that the upload folder is still a parent would have refused it whatever the spelling.

## What to record

- The allowed folder for each operation.
- The rules applied and the refusals observed.
- The limits on entry count and total size.

## Source

- `src/loop_engine/core/task_materials.py`: this repository unpacks supplied archives into one folder, refuses entries whose path is unsafe, refuses link and device entries, and stops when a declared capacity is passed.

The steps above are ordinary engineering practice, written for this catalogue in its own words.

Licence: MIT. Written for this catalogue at revision a0ca182.
