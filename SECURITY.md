# Security

## Reporting a vulnerability

Open a private security advisory through GitHub's *Security* tab. Please do not
open a public issue for anything exploitable.

## What this library does with credentials

- **Keys are read, never written.** Provider keys come from arguments or
  environment variables. Nothing writes them to disk, a log, or a report.
- **Endpoint records carry posture, not credentials.** A custom endpoint record
  can show `has_key: true`. It never contains the key. A test enforces this.
- **A conformance gate scans for secret-shaped literals** in code *and* in
  evidence files, and fails the build on any hit.
- **`.env` is gitignored** and never copied into a run record.

## What it does over the network

Only two kinds of outbound request, both to endpoints you configure:

1. Chat completions to a provider you supplied a key for.
2. Model-catalog reads used to discover what your key can reach.

There is no telemetry, no analytics, and no phone-home. With no provider
configured the library makes **no network calls at all**, and the full test
suite runs offline.

## Running untrusted input

The loop executes code you give it. Treat a task description from an untrusted
source the way you would treat any untrusted input. In particular, model
output that is used to select an estimator or build a feature is parsed through
a closed vocabulary rather than executed, and `eval`/`exec` are refused
anywhere in the codebase by a conformance gate.
