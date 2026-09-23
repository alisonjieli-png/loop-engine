# Verify an exported package in an isolated interpreter

Prove that an exported package is complete, clean and able to run on its own. Run the static checks first. Run code only with explicit authority that is bound to the exact manifest.

## When to use it

Use it after an export and before anyone installs, schedules or publishes the package.

## Steps

1. Require an existing directory that is not a symbolic link, and a manifest with the supported record type, a valid package name and a known isolation mode.
2. Resolve every declared path without following a symbolic link. Refuse a path that leaves the package directory.
3. Recompute the manifest digest and compare it. Recompute the digest of every listed file and compare it.
4. Scan every listed Python file for secret-shaped text and for an import of the producing framework.
5. Require that every file under `src` and `tests` is listed in the manifest and that no compiled cache file is present.
6. Stop here unless the caller supplies a policy that allows local execution and names the exact manifest digest. Interpreter isolation is not an operating system sandbox. An untrusted export needs a separately qualified sandbox.
7. Start the interpreter in isolated mode and without site packages for the standard library only mode. Pass only the search path from the environment, and fix the locale and the stream encoding. Set a finite timeout. The default is 120 seconds.
8. Import the package and confirm that the producing framework was not loaded. Run the exported tests and require that at least one test ran. When arguments are given, run the entry point and require every expected artifact.

## Checks

- A changed file, a changed manifest, an undeclared source file or a cache file fails verification before any code runs.
- Without execution authority, the result is not passed. Only the static checks ran, and full verification remains incomplete.
- A policy that allows execution without a 64 character manifest digest is refused.

## Known-wrong example

A developer imports the package in the development environment, sees no error and reports that it runs on its own. The development environment had the framework and its dependencies installed, so the hidden import was satisfied. In the isolated interpreter the same import fails, which is the true result.

## What to record

- Every check with its name, its result and its detail.
- The manifest digest that the verification was bound to.
- Whether execution was authorized, and by whom.

## Source

- `src/loop_engine/code_nodes/solution_export.py`: `verify_export`, `ExportVerificationPolicy` and `isolation_environment`.

Licence: MIT. Compiled from revision 1700841. The module uses the Python standard library and starts the verification in a separate interpreter process.
