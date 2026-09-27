# Baltor library skill

One first-party skill, version 0.3.0, for Claude Code, Codex, OpenCode and Pi.
It searches the Baltor library and stages one selected item or complete
package in a new folder, after it checks versions, sizes and SHA-256 digests.
It never installs or runs what it downloads, and it never calls a model. Its
client, `scripts/baltor.py`, uses only the Python standard library.

## What is in this folder

Every client reads the same six files. Only the manifests differ.

```text
integrations/baltor-library
├── skills/baltor-library           the skill: the same bytes for every client
│   ├── SKILL.md                    when and how a harness uses the client
│   ├── scripts/baltor.py           the client (Python 3.10 or later)
│   ├── references/client.md        configuration, commands, failure and retry rules
│   ├── assets/client.example.json  a configuration that names the token variable
│   ├── verification/test_client.py the client's offline tests
│   └── LICENSE                     MIT
├── .claude-plugin                  Claude Code plugin and marketplace
├── .codex-plugin                   Codex plugin
├── .agents/plugins                 Codex marketplace
├── package.json                    Pi package
├── release.json                    the pinned version, file digests and package digest
└── SHA256SUMS                      the same file digests, for sha256sum
```

## Status

- Version 0.3.0 is pinned. `release.json` records the SHA-256 digest of each
  file and the package digest
  `ab45e58b1e1a601b4bc97ab0df84e4c4b37ca814b6c1c9bba5dfdc32578e3926`. The
  repository check `tools/test_baltor_library_integration.py` fails when a
  byte, a manifest version or a native folder changes without the record.
- The skill is not in the Baltor catalogue. Catalogue candidate
  `baltor_library_client` holds the same bytes and waits for independent
  review. This folder is the source distribution of the same files.
- Observed on September 27, 2026, with the network switched off, an empty
  home folder and no model call. Claude Code 2.1.283 installed the plugin from
  this folder and listed the skill in its component inventory. Codex 0.155.1
  installed the plugin and offered the skill in its rendered model input. It
  did the same for a copy in `~/.agents/skills`. OpenCode 1.18.32 listed the
  skill from `.opencode/skills` and from `~/.config/opencode/skills`. Pi 0.73.1
  listed the skill from this folder as a package and from `.pi/skills`.
- Not observed yet: a model choosing the skill during a real task, a live
  download from baltor.ai by this client, and Windows. The client declares
  POSIX file operations.

## Set up your token once

The client reads your personal Baltor client token from an environment
variable. Your configuration file names that variable. It never holds the
token itself.

1. Create a client token on [your account page](https://app.baltor.ai/account),
   under Your client tokens. The service shows it once.
2. Copy the example configuration. It names the variable
   `BALTOR_SERVICE_TOKEN`, the same name the setup page uses for every client.

   ```bash
   mkdir -p ~/.config/baltor
   cp skills/baltor-library/assets/client.example.json ~/.config/baltor/client.json
   ```

3. Set the token in the terminal that starts your harness. The prompt hides
   the value and keeps it out of the command history.

   ```bash
   read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
   export BALTOR_SERVICE_TOKEN
   ```

The client sends the token only in the request header to the configured
Baltor address. It never prints the token. It refuses the token as a command
argument, refuses a configuration file that contains a token field, and stops
when a response repeats the token.

## Install for your client

Replace `/path/to/loop-engine` with the folder of your copy of this
repository. Start a new session afterwards, because each client reads skills
when a session starts.

### Claude Code

```bash
claude plugin marketplace add /path/to/loop-engine/integrations/baltor-library
claude plugin install baltor-library@baltor
```

Without the plugin, copy `skills/baltor-library` to
`~/.claude/skills/baltor-library` for every project, or to
`.claude/skills/baltor-library` in one project.

### Codex

```bash
codex plugin marketplace add /path/to/loop-engine/integrations/baltor-library
codex plugin add baltor-library@baltor
```

Without the plugin, copy `skills/baltor-library` to
`~/.agents/skills/baltor-library` for every project, or to
`.agents/skills/baltor-library` in one project.

### OpenCode

```bash
mkdir -p ~/.config/opencode/skills
cp -R /path/to/loop-engine/integrations/baltor-library/skills/baltor-library ~/.config/opencode/skills/
```

This creates `~/.config/opencode/skills/baltor-library` for every project. For
one project, copy it to `.opencode/skills/baltor-library` instead.

### Pi

```bash
pi install /path/to/loop-engine/integrations/baltor-library
```

Pi reads a local package from its folder and does not copy it. You can also
copy `skills/baltor-library` to `~/.pi/agent/skills/baltor-library` for every
project, or to `.pi/skills/baltor-library` in one project.

## Check what you installed

```bash
cd /path/to/loop-engine/integrations/baltor-library
sha256sum -c SHA256SUMS
python3 skills/baltor-library/verification/test_client.py
```

The first command compares every file with the pinned digests. The second
runs the client's offline tests. They open no network connection and need no
token.

## Your first search

In a session, ask in plain words: "Use the Baltor library skill to search for
review inputs and show the top three results with their source and digest."
The same search from a terminal, with the token set:

```bash
python3 skills/baltor-library/scripts/baltor.py search "review inputs" --limit 3 > review-inputs.json
```

The saved file is the selection that a later `fetch` command reads. A search
reads metadata only and does not count as a download.
[The client reference](skills/baltor-library/references/client.md) explains
`fetch`, its folder rules and what to do after a failure.

## How the skill relates to the protocol connection

The quickstarts connect each client to the Baltor Model Context Protocol
endpoint. This skill is a second way in that needs no protocol client, only
Python and the token. Both use the same account and the same catalogue.

## Repository checks

`tools/test_baltor_library_integration.py` runs in continuous integration on
Python 3.10, 3.11 and 3.12. It checks the pinned bytes, the versions in every
manifest, the native skill folders against the placement profiles in
`tools/install_selected_material.py`, and that the configuration names only an
environment variable. It also runs the client's offline tests, and it runs the
pinned client against the service application in the same process, with
network connections refused. A change to the service contract that this client
does not accept fails that check.

A new version changes the files, `release.json`, `SHA256SUMS` and every
manifest together. Its bytes need their own independent review before they
enter the catalogue.
