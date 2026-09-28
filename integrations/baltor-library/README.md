# Baltor library skill

One first-party skill, version 0.4.0, for Claude Code, Codex, OpenCode and Pi.
It searches the Baltor library, stages one selected item or complete package
in a new folder after it checks versions, sizes and SHA-256 digests, and
places a fetched skill in the client's own skill folder byte for byte. It never
runs what it downloads, and it never calls a model. Its client,
`scripts/baltor.py`, uses only the Python standard library.

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

- Version 0.4.0 is pinned. `release.json` records the SHA-256 digest of each
  file and the package digest; `release.json` also names the 0.3.0 package
  digest it replaces. The repository check
  `tools/test_baltor_library_integration.py` fails when a byte, a manifest
  version or a native folder changes without the record, and when the copy
  the website serves at `/assets/baltor-library/` differs from these files.
- What 0.4.0 changed, after a customer run on September 27, 2026 found that a
  model retyping a downloaded skill corrupted it: the new `install` command
  places a fetched skill byte for byte, and `verify` checks it later; the
  configured effects travel in the `Baltor-Step-Effects` header, so search
  shows every item with the effects still to declare, and fetch refuses an
  item whose effects the configuration leaves out; the example configuration
  declares `reads_fs`, `writes_fs`, `spawns_process` and `network`; a refusal
  that recorded nothing and names a short wait is sent again after it.
- The skill is not in the Baltor catalogue. The 0.3.0 bytes are catalogue
  candidate `baltor_library_client`, which waits for independent review; the
  0.4.0 bytes need their own review before they enter the catalogue. This
  folder is the source distribution of the same files.
- Observed for version 0.3.0 on September 27, 2026, with the network switched
  off, an empty home folder and no model call. Claude Code 2.1.283 installed
  the plugin from this folder and listed the skill in its component inventory.
  Codex 0.155.1 installed the plugin and offered the skill in its rendered
  model input. It did the same for a copy in `~/.agents/skills`. OpenCode
  1.18.32 listed the skill from `.opencode/skills` and from
  `~/.config/opencode/skills`. Pi 0.73.1 listed the skill from this folder as
  a package and from `.pi/skills`. In a customer run the same day, 0.3.0
  fetched a complete 18-file package from baltor.ai with every file digest
  checked.
- Not observed yet for 0.4.0: a client loading a skill that `install` placed,
  a model choosing the skill during a real task, and Windows. The client
  declares POSIX file operations.

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

The Baltor website serves the same six files, and the digests to check them,
under `https://baltor.ai/assets/baltor-library/`. The commands below place
them in a project's OpenCode skill folder; use the folder your client reads,
as the table in [the client reference](skills/baltor-library/references/client.md#placement)
shows:

```bash
mkdir -p .opencode/skills/baltor-library && cd .opencode/skills/baltor-library
for file in SKILL.md LICENSE scripts/baltor.py references/client.md assets/client.example.json verification/test_client.py; do
  curl -fsSL --create-dirs "https://baltor.ai/assets/baltor-library/$file" -o "$file"
done
curl -fsSL https://baltor.ai/assets/baltor-library/SHA256SUMS | sha256sum -c -
cd -
```

From a copy of this repository, replace `/path/to/loop-engine` below with its
folder. Start a new session afterwards, because each client reads skills when
a session starts.

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

## Place a fetched skill

`fetch` stages files in a new folder and places nothing. To use a fetched
skill in your client, place it with `install`, which checks every staged file
again and writes the exact bytes into the client's skill folder:

```bash
python3 skills/baltor-library/scripts/baltor.py install --staged /absolute/new-download-folder \
  --client opencode --project /absolute/project --authorize-install
python3 skills/baltor-library/scripts/baltor.py verify --client opencode --name NATIVE-NAME --project /absolute/project
```

The install prints its record, whose `native_name` is the folder name `verify`
takes. It places skill packages only and never replaces a folder it did not
install. [Placement](skills/baltor-library/references/client.md#placement)
names every client's folder.

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
