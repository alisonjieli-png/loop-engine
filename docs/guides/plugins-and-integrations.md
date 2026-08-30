# Plugins and integrations

Loop Engine can be consumed through its Python package, CLI, local Studio, MCP
adapters, and thin host-specific plugins.

```text
Host adapter
→ typed Loop Engine CLI or service request
→ canonical Loop runtime
→ Run History and typed result
```

Host adapters do not reimplement the Practitioner, scheduler, provider gateway,
permissions, or verification.

Plugin bundles reference exact admitted skills and declared profiles,
capabilities, and lifecycle subscriptions. Project-local content cannot silently
override installed content. Changed skill files invalidate plugin resolution.

Claude Code and Codex adapter packages are maintained as thin integrations.
Marketplace installation and remote publisher trust remain separate release
gates until their conformance and clean-install checks pass.

## Add files without changing Loop Engine source

Place provider routes, capability candidates, skills, plugin bundles, or
plugin-provenance intelligence under `.loop-engine/extensions/` in a project,
under `~/.config/loop-engine/extensions/` for one user, or in a root listed by
`LOOP_ENGINE_EXTENSION_ROOTS`.

```bash
loop-engine extensions discover
```

Discovery validates and lists the files without executing code or calling a
provider. See [Added-file extensions](../architecture/ADDED-FILE-EXTENSIONS.md)
for folder layouts, schemas, activation rules, and examples.
