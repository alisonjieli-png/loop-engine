# Baltor library skill: native discovery, September 27, 2026

This folder records one observation of the first-party skill in
[integrations/baltor-library](../../integrations/baltor-library/README.md),
version 0.3.0, package digest
`ab45e58b1e1a601b4bc97ab0df84e4c4b37ca814b6c1c9bba5dfdc32578e3926`.

Each client ran inside a network namespace with loopback only, from an
environment with an empty home folder and an empty client configuration
folder. No token was set, no credential was read and no model was called.

| Client | Version | Route | Observed |
|---|---|---|---|
| Claude Code | 2.1.283 | plugin from the folder | Strict validation passed; plugin 0.3.0 installed; the component inventory lists the skill |
| Codex | 0.155.1 | plugin from the folder | Plugin 0.3.0 installed; `codex debug prompt-input` offers `baltor-library:baltor-library` |
| Codex | 0.155.1 | `~/.agents/skills/baltor-library` | `codex debug prompt-input` offers `baltor-library` |
| OpenCode | 1.18.32 | `.opencode/skills` and `~/.config/opencode/skills` | `opencode debug skill --pure` lists `baltor-library` |
| Pi | 0.73.1 | package from the folder and `.pi/skills` | RPC `get_commands` lists `skill:baltor-library` |

The installed copies that Claude Code and Codex keep in their caches were
byte for byte the files of the folder.

[native-discovery-v1.json](native-discovery-v1.json) holds the commands and
the results. Discovery is not use: this record does not show a model choosing
the skill, a live download from baltor.ai, or Windows behavior.
