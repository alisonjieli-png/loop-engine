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

