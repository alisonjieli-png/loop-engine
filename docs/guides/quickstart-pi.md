# Pi quickstart

Kind: customer quickstart for native Pi 0.99.2 connections and the retained Pi 0.73.1 extension recipe.

Pi 0.99.2 connects to Baltor through its built-in MCP client. Use the native
connection below for that version. The extension section preserves the
Pi 0.73.1 recipe used by the [recorded Pi case study](https://app.baltor.ai/case-studies/pi-and-gemma-4).
Check your installed version with `pi --version` before choosing a route.

## Native MCP connection for Pi 0.99.2

The current official package is `@earendil-works/pi-coding-agent`. Merge this
entry into your user-level `~/.pi/agent/mcp.json`, preserving other servers:

```json
{
  "mcpServers": {
    "baltor": {
      "url": "https://baltor.ai/mcp",
      "headers": {"Baltor-Step-Effects": "reads_fs, writes_fs, spawns_process, network"},
      "exposure": "direct"
    }
  }
}
```

Keep only the step effects your work permits. For OAuth, start sign-in from Pi,
use your Baltor account and review the consent screen:

```bash
pi mcp login baltor
pi mcp list
```

Pi manages the connection credentials. Keep the OAuth entry free of an
`Authorization` header. For a supplied-token connection instead, add
`"Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}"` to its headers and provide
that variable privately to Pi. The [OAuth guide](service-serving-and-connections.md#oauth-connections)
describes scopes and account linking.

Use `intelligence_search` for the first `review inputs` query, or
`public_good_files` for goal-filtered free material. Inspect a selected package
with `provisioning_manifest` and retrieve its exact files with
`provisioning_read`. Follow [the file guide](service-searching-and-retrieving.md#find-free-public-good-files)
for hashes, package dependencies and native placement.

Project resources and account consent are separate settings. Pi 0.99.2 reads
project `.pi/mcp.json` and `.pi/skills` after the project is trusted. Its
noninteractive default skips untrusted project resources. Use the user-level
MCP file for personal connections. The session-only `--approve` option can
authorize project-resource discovery for one isolated session; the shell MCP
commands use their own documented options. See the pinned
[MCP guide](https://github.com/earendil-works/pi/blob/v0.99.2/packages/coding-agent/docs/mcp.md)
and [project security guide](https://github.com/earendil-works/pi/blob/v0.99.2/packages/coding-agent/docs/security.md).

## Extension recipe for Pi 0.73.1

## What you need

- A [Baltor account](https://app.baltor.ai/get-started). Public Good files are free with an account; Baltor Pro adds the full library.
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- Pi installed, and a project folder that it opens. Check the version with `pi --version`.
- A terminal where the token is set, because the extension reads it from the environment.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start Pi from this terminal.

## Save the extension and its settings

For Pi 0.73.1, the Baltor extension supplies the connection and placement
tools. Review the extension before starting Pi: it runs with your permissions.
It uses the packages supplied with that Pi version.

```bash
mkdir -p .pi/extensions
curl -fsSL https://baltor.ai/assets/pi/baltor.ts -o .pi/extensions/baltor.ts
```

Create `.pi/baltor.json` beside it. It holds the name of the variable, never the token:

```json
{
  "baltor": {
    "url": "https://baltor.ai/mcp",
    "token_env": "BALTOR_SERVICE_TOKEN",
    "step_effects": ["reads_fs", "writes_fs", "spawns_process", "network"]
  }
}
```

`step_effects` says what Pi's steps may do with a Baltor item: `reads_fs` reads files in your project, `writes_fs` writes them, `spawns_process` runs commands and `network` uses the network. `reads_secret` is left out unless your steps read secrets. Remove any effect Pi should not have. The extension sends the list in the `Baltor-Step-Effects` header. Search shows every item your account may use, and marks one whose effects your list leaves out; the extension does not download that item and names the effects to add. The extension needs version 2 of the file for this setting: download it again if an older copy refuses `step_effects`.

## Check the connection

Run this in the project folder, in the terminal where the token is set:

```bash
pi -p --baltor-check
```

It makes no model call and downloads nothing. It shows whether the service answered, which account the token belongs to, and each installed Baltor skill with its digest check and whether Pi's skill loader accepts it. The last line says `Result: ready`. In a Pi session, the /baltor command runs the same check.

## Your first search

The first search is `review inputs`. In a Pi session, ask in plain words:

```text
Search Baltor for review inputs and show the top three results with their source and digest.
```

The extension's `baltor_search` tool asks `/api/v1/retrieval` with `service_retrieval_request/v2`. The service answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, its source and licence, and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Your first download

Choose one result and ask Pi to install it:

```text
Install ITEM-IDENTITY from Baltor.
```

The extension's `baltor_download` tool reads the item's manifest through `/api/v1/provisioning`, downloads it through `/api/v1/download` with a new `request_id`, checks every file against its published SHA-256 digest before it writes anything, installs the skill in `.pi/skills` and never replaces a folder it did not install. Its install record is kept in `.pi/baltor/installed`. The first download of an item version in a calendar month is one measured unit and appears in your usage; downloading the same version again that month, with any `request_id`, adds nothing. Pi lists the new skill from the next session.

## Check that it worked

1. Run `pi -p --baltor-check` again: the new skill is listed with its digest check passed and accepted by Pi's skill loader.
2. Start a new Pi session and ask for the task the skill covers; Pi names the skill when it uses it.
3. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
4. Confirm the account and its scopes from the terminal with the command below.

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The answer's `result` is `service_session/v1`. Its `principal` names the account and its `scopes`: a search needs `provisioning:metadata` and a download needs `provisioning:read`.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts Pi, then run the check again. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `plan_required` | 403 | Your account has no plan that includes downloads; search still works. Choose Baltor Pro on the [pricing page](https://baltor.ai/pricing). The refusal's `details` name that page, and the founding offer while places remain. |
| `step_effects_required` | 403 | The item declares effects your configuration does not declare. Add the `effects_to_declare` that the refusal's `details` name, if your harness may do them, or choose another item. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `unsupported_version` | 400 | The service moved to a newer request version. The extension asks the service again once; if it still refuses, download the extension file again. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A check whose last line is not `Result: ready` names the step that failed above it. A skill that Pi's loader does not accept is installed but not loaded; the check says so. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
