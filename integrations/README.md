# Loop Engine integrations

Host-specific packages are thin adapters over the installed Loop Engine CLI or
typed service boundary. They do not contain another Practitioner, scheduler,
provider gateway, permission system, or Run History.

```text
Claude Code or Codex
→ thin skill adapter
→ installed loop-engine command
→ canonical Loop runtime
```

See `architecture.yaml` for the enforced boundary.

The project [CLAUDE.md](../CLAUDE.md) imports the shared [AGENTS.md](../AGENTS.md)
rules and the main advisory comments in [ASTRA.md](../ASTRA.md). Harness
development follows [its scoped instructions](../embodiments/AGENTS.md).

The [layered harness design](../docs/architecture/LAYERED-HARNESS-WRAPPERS-AND-NATIVE-CONTROL.md)
permits an outer Loop around native harness iteration. Host adapters must
preserve authority, cancellation, accounting, and independent acceptance
across that boundary. Development instructions are not executable capability
grants or evidence that a native profile has been qualified.
