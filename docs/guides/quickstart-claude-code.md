# Claude Code quickstart

Kind: customer quickstart for Claude Code. It repeats the connection entry that Get set up publishes for Claude Code and adds the first search, the first download and the check that it worked.

One page from an account to a checked download. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service with a plain protocol client. That check does not run Claude Code itself: the published recipe still says that native end-to-end qualification is pending.

## What you need

- A Baltor account with an active plan. Create it on [Get started](https://app.baltor.ai/get-started).
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- Claude Code installed, and a project folder that it opens. Check the version with `claude --version`.
- A terminal where the token is set, because Claude Code reads it from the environment.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start Claude Code from this terminal. A variable set in one terminal does not reach a desktop application started elsewhere.

## Paste the configuration

Create `.mcp.json` in your project folder, or merge the `baltor` entry into the `mcpServers` section of an existing one. Do not replace your other settings. The file holds the name of the variable, never the token, so it is safe to keep in version control.

```json
{
  "mcpServers": {
    "baltor": {
      "type": "http",
      "url": "https://baltor.ai/mcp",
      "headers": {"Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}"}
    }
  }
}
```

## Check the connection

Run this in the project folder, in the terminal where the token is set:

```bash
claude mcp list
```

The list shows a status next to `baltor`. If the status is Pending approval, start `claude` in this folder once and approve the server. If the list warns about a missing environment variable, set the token before you start Claude Code. In a session, enter `/mcp` and confirm that Baltor's five tools are listed: `intelligence_search`, `provisioning_discover`, `provisioning_list`, `provisioning_manifest` and `provisioning_read`.

## Your first search

The first search is `review inputs`. In a session, ask in plain words:

```text
Search Baltor for review inputs with the intelligence_search tool. Show the top three references with their identity, tier and body digest.
```

Claude Code calls `intelligence_search` with your words as the `query`. The tool answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, the tier label in `library_tier_label` (Verified or Community) and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Your first download

Choose one reference and ask for it by its identity:

```text
Download ITEM-IDENTITY from Baltor with provisioning_read. Use its body digest as the expected_digest and a new request_id. Save the body as .claude/skills/ITEM-IDENTITY/SKILL.md in this project.
```

`provisioning_read` takes the `identity`, a new `request_id` for each logical download and the `expected_digest` from the search, so a changed body is refused rather than substituted. The tool answers the same wrapper; its `result` is `provisioning_body/v3`, with the `body` inline and its `digest`. This download is one measured unit and appears in your usage. An item larger than the `inline_body_bytes` limit that `/api/v1/capabilities` reports answers `download_required`; fetch it through `/api/v1/download` as the [Baltor Harness quickstart](quickstart-baltor-harness.md) shows.

Claude Code reads project skills from `.claude/skills/` and lists a new one at the next session. Today the file is written by the agent or by you, as the prompt above asks; the service does not place it. Placing served files into each harness's own layout is planned work.

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
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts Claude Code, then run the session check above. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_required` | 413 | The body is larger than the inline limit. Fetch it through `/api/v1/download`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A configured entry is not a completed handshake, and a listed tool is not a loaded file. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
