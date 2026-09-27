# OpenCode quickstart

Kind: customer quickstart for OpenCode 1.x. It repeats the connection entry that Get set up publishes for OpenCode and adds the first search, the first download and the check that it worked.

One page from an account to a checked download. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service with a plain protocol client. That check does not run OpenCode itself: the published recipe still says that native end-to-end qualification is pending.

## What you need

- A Baltor account with an active plan. Create it on [Get started](https://app.baltor.ai/get-started).
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- OpenCode 1.x installed. Check the version with `opencode --version`. OpenCode 2.x uses a different configuration layout, and this page does not cover it.
- A terminal where the token is set, because the entry reads it from the environment.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start OpenCode from this terminal.

## Paste the configuration

Merge the `baltor` entry into the `mcp` section of your existing `opencode.json`. Do not replace your other settings. The file holds the name of the variable, never the token.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "baltor": {
      "type": "remote",
      "url": "https://baltor.ai/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {"Authorization": "Bearer {env:BALTOR_SERVICE_TOKEN}"}
    }
  }
}
```

## Check the connection

```bash
opencode mcp list
```

Confirm that Baltor connects and exposes its five tools: `intelligence_search`, `provisioning_discover`, `provisioning_list`, `provisioning_manifest` and `provisioning_read`. This service uses a supplied token; do not start an OAuth login for it.

## Your first search

The first search is `review inputs`. In a session, ask in plain words:

```text
Search Baltor for review inputs with the intelligence_search tool. Show the top three references with their identity, tier and body digest.
```

OpenCode calls `intelligence_search` with your words as the `query`. The tool answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, the tier label in `library_tier_label` (Verified or Community) and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Your first download

Choose one reference and ask for it by its identity:

```text
Download ITEM-IDENTITY from Baltor with provisioning_read. Use its body digest as the expected_digest and a new request_id. Save the body as .opencode/skills/ITEM-IDENTITY/SKILL.md in this project.
```

`provisioning_read` takes the `identity`, a new `request_id` for each logical download and the `expected_digest` from the search, so a changed body is refused rather than substituted. The tool answers the same wrapper; its `result` is `provisioning_body/v3`, with the `body` inline and its `digest`. This download is one measured unit and appears in your usage. An item larger than the `inline_body_bytes` limit that `/api/v1/capabilities` reports answers `download_required`; fetch it through `/api/v1/download` as the [Baltor Harness quickstart](quickstart-baltor-harness.md) shows.

OpenCode reads project skills from `.opencode/skills/`. Today the file is written by the agent or by you, as the prompt above asks; the service does not place it. Automatic placement remains under development.

## Check that it worked

1. Compare the digest: `sha256sum` of the saved file must equal the `body_digest` the search returned.
2. Open [your account page](https://app.baltor.ai/account): the download is listed in your usage.
3. Confirm the account and its scopes from the terminal with the command below.

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The answer's `result` is `service_session/v1`. Its `principal` names the account and its `scopes`: a search needs `provisioning:metadata` and a download needs `provisioning:read`.

## When it does not work

| Code | Status | What to do |
| --- | --- | --- |
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts OpenCode, then run the session check above. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_required` | 413 | The body is larger than the inline limit. Fetch it through `/api/v1/download`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

An entry with `oauth` set to true starts a login this service does not offer; keep it false. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
