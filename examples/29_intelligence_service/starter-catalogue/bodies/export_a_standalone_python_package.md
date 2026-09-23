# Export a solution as a standalone Python package with a manifest

Write a finished solution as one installable package that runs without the framework that produced it. A manifest lists every file with its digest.

## When to use it

Use it when code written during an assisted session must leave that session: to be installed, reviewed, scheduled or handed to another team.

## Steps

1. Describe the export in one typed specification: a lower case package name, a version with three numbers, a summary, the source files, the tests, an optional console command, the dependencies, the supported Python versions and the container settings.
2. Require an `__init__.py` file. Require a `__main__.py` file with a `main` function when a console command is declared. Refuse repeated file paths.
3. Choose the isolation mode. With the standard library only mode, refuse any declared dependency.
4. Refuse file paths that are absolute or that leave the package. Refuse file content that holds secret-shaped text or that imports the producing framework.
5. Write only into a new or empty directory that is not a symbolic link.
6. Write the package under `src`, the tests under `tests`, and then `pyproject.toml`, `README.md`, `Dockerfile`, `k8s/job.yaml` and `.dockerignore`.
7. Write `MANIFEST.json` last. It holds the specification digest, the settings, and a SHA-256 digest for every other written file. It also holds a digest of the manifest itself.
8. Return an export record with the target, the package name, the version, the manifest digest and the file count.

## Checks

- Every written file appears in the manifest with its digest.
- The README explains how to install, run, test, build the container and start the job.
- Exporting into a directory that already holds files is refused.
- The export is only written at this point. Whether it runs on its own is a separate verification.

## Known-wrong example

A session copies its working folder into a zip file and calls it the deliverable. One file is declared with an absolute path into the home directory of the author. A settings file holds a private key block. The main module imports the framework. The package runs only on the machine of the author. The typed export refuses each of these three problems before it writes a file.

## What to record

- The export record and the manifest digest.
- The reference of the solution and of the work session that the export came from, when they exist.

## Source

- `src/loop_engine/code_nodes/solution_export.py`: `SolutionExportSpec`, `ExportedFile`, `ContainerSpec`, `export_solution` and the render functions.

Licence: MIT. Compiled from revision a0ca182. The module uses the Python standard library and one template module of the same package.
