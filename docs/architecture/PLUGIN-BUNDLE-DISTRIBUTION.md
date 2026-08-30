# Plugin bundle distribution

Loop Engine plugins are passive distribution bundles. They do not create a
runtime, registry, permission system, scheduler, or intelligence layer.

```text
PluginBundleManifest
├── exact admitted SkillManifest references
├── profile references
├── capability references
└── canonical Run History subscriptions
        ↓
deterministic validation in an Intelligence Loop
        ↓
ResolvedPluginSnapshot
├── complete manifest digest
├── complete skill-file digests
├── exact SkillAdmissionRecord digests
├── resolution reasons
├── JSON view
└── ASCII tree
```

Installed and project-local bundles with identical content deduplicate. A
project bundle with the same identity and different content fails. There is no
silent local override. Changing an admitted skill file invalidates resolution.

This design takes inspiration from HCF's deterministic self-discovery and
debuggable text/JSON output while retaining Loop Engine's independent skill
admission, complete semantic digests, typed event vocabulary, and one Loop
runtime.

Current limitations:

- No marketplace installer is implemented.
- No Claude Code or Codex wrapper is packaged yet.
- Profile and capability admission remain future bundle gates.
- Plugin bundles may be discovered from explicit roots or from an added-file
  extension root's `plugins/` folder. Resolution still requires exact admitted
  skills.
- Signing, remote acquisition, and publisher trust are not implemented.
