# Open harness interoperability research inputs

These files support the [research report](../../../docs/research/HARNESS-PACKAGES-OPEN-HARNESSES-2026-09-23.md).
They are not approved intelligence packages, runtime dependencies or a new task
list. No library item is added by this research.

## Contents

- `source-manifest.json` records original repository, immutable revision, original
  path, exact raw URL, fetch time, SHA-256 and stored path for each source.
- `source-snapshots/` contains unmodified retrieved bytes, with `.source.txt`
  appended to filenames so third-party examples are not mistaken for local
  executable tools or repository documentation. Original paths remain in the
  manifest. Each inspected repository's root licence is retained alongside its
  selected sources.
- `*-paths.json` holds repository tree inventories used to locate the relevant
  source files. These are discovery metadata, not counts of harness intelligence.
- `probe_pi_loader.mjs` invokes already installed Pi discovery functions against
  synthetic files in a newly created temporary directory.
- `pi-loader-observation-2026-09-23.json` records the seven passing observations,
  installed package identity and exact loader module digest.

## Local observation limits

The Pi probe did not start a model, launch a CLI session, load an extension,
install anything or modify native configuration. The process environment was
scrubbed and proxy addresses pointed to a closed local port; this is not an
operating-system network sandbox. The directly invoked functions were given
their own temporary working and agent directories; skill discovery used explicit
paths with defaults disabled.

The temporary synthetic files are removed only after the report is saved. The
runner refuses to overwrite an existing report. To repeat, supply the installed
package root and a new output path:

```bash
node probe_pi_loader.mjs /absolute/path/to/installed/pi-coding-agent new-observation.json
```

This command is a loader observation. It is not an accepted-task test. The
seven cases deliberately include ignored files, conflicting files, an ancestor
instruction above a git root and duplicate skill names. Run it in an isolated
environment as done for the saved observation; no provider configuration is
needed.

The immutable upstream Pi source identifies version 0.87.1. The installed
package tested here is version 0.73.1. Their findings are kept separate in the
report. The resource-loading code was read from its installed location; no
credential files or values were read or saved.
