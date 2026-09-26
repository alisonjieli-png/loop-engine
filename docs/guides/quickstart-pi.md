# Pi quickstart

Kind: customer quickstart for Pi. It repeats the extension setup that Get set up publishes for Pi and adds the first search, the first download and the check that it worked.

One page from an account to an installed, checked skill. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service in the shape the extension sends them. This is the one harness with a recorded end-to-end run: on September 23, 2026, Pi 0.73.1 with Gemma 4 31B through Ollama Cloud found and installed a Baltor skill with the two tools, and a new Pi session loaded that skill and used it. Read [the Pi case study](https://app.baltor.ai/case-studies/pi-and-gemma-4) for the record.

## What you need

- A Baltor account with an active plan. Create it on [Get started](https://app.baltor.ai/get-started).
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

Pi has no built-in Model Context Protocol client, so Baltor connects through one small Pi extension. Pi runs every extension in `.pi/extensions` with your permissions and does not ask first, so read the file before you start Pi. It needs no other packages.

```bash
mkdir -p .pi/extensions
curl -fsSL https://baltor.ai/assets/pi/baltor.ts -o .pi/extensions/baltor.ts
```

Create `.pi/baltor.json` beside it. It holds the name of the variable, never the token:

```json
{
  "baltor": {
    "url": "https://baltor.ai/mcp",
    "token_env": "BALTOR_SERVICE_TOKEN"
  }
}
```

## Check the connection

Run this in the project folder, in the terminal where the token is set:

```bash
pi -p --baltor-check
```

It makes no model call and downloads nothing. It shows whether the service answered, which account the token belongs to, and each installed Baltor skill with its digest check and whether Pi's skill loader accepts it. The last line says `Result: ready`. In a Pi session, the /baltor command runs the same check.

## Your first search

The first search is `review inputs`. In a Pi session, ask in plain words:

```text
Search Baltor for review inputs and show the top three results with their tier and digest.
```

The extension's `baltor_search` tool asks `/api/v1/retrieval` with `service_retrieval_request/v2`. The service answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, the tier label in `library_tier_label` (Verified or Community) and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Your first download

Choose one result and ask Pi to install it:

```text
Install ITEM-IDENTITY from Baltor.
```

The extension's `baltor_download` tool reads the item's manifest through `/api/v1/provisioning`, downloads it through `/api/v1/download` with a new `request_id`, checks every file against its published SHA-256 digest before it writes anything, installs the skill in `.pi/skills` and never replaces a folder it did not install. Its install record is kept in `.pi/baltor/installed`. This download is one measured unit and appears in your usage. Pi lists the new skill from the next session.

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
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `unsupported_version` | 400 | The service moved to a newer request version. The extension asks the service again once; if it still refuses, download the extension file again. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A check whose last line is not `Result: ready` names the step that failed above it. A skill that Pi's loader does not accept is installed but not loaded; the check says so. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
