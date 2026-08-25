# Architecture conformance

Architecture conformance checks rules that must remain true across the
package. The command reads the live source tree and exits with a nonzero status
when a required rule fails.

```bash
python -m loop_engine --conformance
```

Use the command output for the current result. Do not copy a test count or gate
result into documentation because it becomes stale when the suite changes.

## What it checks

The current checks cover:

| Area | Required condition |
|---|---|
| Package layout | Each module belongs to one declared architecture area. |
| Runtime identity | The package API exposes only the canonical recursive `Loop` runtime. |
| Retired planning surface | Obsolete decision-spine names and modules remain absent. |
| Flat legacy paths | Retired package-level module paths stay unreachable and unused. |
| Network and models | Calls stay behind declared provider and endpoint adapters. |
| Processes | Subprocess use stays inside declared adapters. |
| Dynamic code | `eval` and `exec` remain absent. |
| Secrets | Secret-shaped literals do not enter code or shipped evidence files. |
| Registration | Dynamic imports cannot bypass declared registration paths. |
| Providers | Forbidden provider families remain behind their guards. |
| Modules | Empty placeholders and unexplained size exceptions fail. |
| Python versions | Source syntax stays compatible with the declared minimum. |
| Module contracts | Required context docstrings remain present. |
| Documentation | Current architecture projections stay fresh. |
| Tests | Conformance suites cannot hide skip markers. |
| Events | Runtime events stay inside the canonical vocabulary. |
| Self-tests | Every module self-test remains connected to the full suite. |
| Envelopes | Modules that own execution envelopes remain registered. |
| Loop ontology | Every operational boundary resolves to `Loop` and an exact registered profile or validated profile source. |
| Relationships | Boundary relationship kinds remain compatible with their role families. |
| Graph vertices | Every executable graph vertex uses the canonical `Loop` runtime type. |
| Resource access | Product code does not add undeclared direct store access. |
| Architecture map | The generated module map matches the current package. |

The machine-readable configuration is
[`architecture_conformance.json`](../../src/loop_engine/architecture_conformance.json).
The current generated module inventory is
[`ARCHITECTURE-MAP.md`](../../src/loop_engine/ARCHITECTURE-MAP.md).

## How to read a result

- `PASS` means the current source tree satisfied that check.
- A failing line names the rule and the observed violation.
- A successful command does not prove production readiness, model quality,
  external service availability, or plugin support.
- A check that does not exist provides no assurance.

Run the complete built-in suite as a separate step:

```bash
python -m loop_engine --self-test
```

The self-test checks behavior. The conformance command checks architecture
boundaries. The default self-test output is concise. Use
`python -m loop_engine --self-test-verbose` for module demo output and the full
JSON record. Run both gates before a release.
