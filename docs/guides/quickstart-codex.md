# Codex quickstart

Kind: customer quickstart for Codex. It repeats the connection table that Get set up publishes for Codex and adds the first search, the first download and the check that it worked.

One page from an account to a checked download. Every address, field and command on it is read from the service source, and a nightly check runs the same connection, search and download against the live service with a plain protocol client. That check does not run Codex itself: the published recipe still says that native end-to-end qualification is pending.

## What you need

- A Baltor account with an active plan. Create it on [Get started](https://app.baltor.ai/get-started).
- A client token from [your account page](https://app.baltor.ai/account), under Your client tokens. The service shows it once.
- Codex installed. Check the version with `codex --version`.
- A terminal where the token is set, because Codex reads the token from the environment variable the table names.

## Set the token

The prompt below hides the value while you enter it, and the value stays out of the command history:

```bash
read -rsp "Baltor service token: " BALTOR_SERVICE_TOKEN
export BALTOR_SERVICE_TOKEN
```

Start Codex from this terminal.

## Paste the configuration

Merge this table into your existing Codex `config.toml`. Do not replace your other settings. The table holds the name of the variable, never the token.

```toml
[mcp_servers.baltor]
url = "https://baltor.ai/mcp"
bearer_token_env_var = "BALTOR_SERVICE_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 45
```

## Check the connection

```bash
codex mcp list
```

This command shows configuration, not a completed handshake. In a Codex session, inspect `/mcp` and confirm that Baltor's five tools are available before asking it to search: `intelligence_search`, `provisioning_discover`, `provisioning_list`, `provisioning_manifest` and `provisioning_read`.

## Your first search

The first search is `review inputs`. In a session, ask in plain words:

```text
Search Baltor for review inputs with the intelligence_search tool. Show the top three references with their identity, source and body digest.
```

Codex calls `intelligence_search` with your words as the `query`. The tool answers a `service_http_result/v1` wrapper whose `result` is the `service_retrieval_result/v1` record: a list of `hits`, each with a `reference` that names the item's `identity`, its `body_digest` and its `size_bytes`, its source and licence, and `body_allowed`. A search never loads a body, so `bodies_loaded` is false, and a search is not measured.

## Your first download

Choose one reference and ask for it by its identity:

```text
Download ITEM-IDENTITY from Baltor with provisioning_read. Use its body digest as the expected_digest and a new request_id. Save the body as .agents/skills/ITEM-IDENTITY/SKILL.md in this repository.
```

`provisioning_read` takes the `identity`, a new `request_id` for each logical download and the `expected_digest` from the search, so a changed body is refused rather than substituted. The tool answers the same wrapper. For a single-file item its `result` is `provisioning_body/v3`, with the `body` inline and its `digest`. For a package of several files it is `provisioning_package_read/v1`: each file's exact content with its `path` and SHA-256 `digest`, one page at a time; ask for the next page with `file_offset` set to `next_file_offset` and the same `request_id`. [Searching and retrieving](service-searching-and-retrieving.md#package-files-through-the-protocol-tool) describes the record. This download is one measured unit and appears in your usage. A single-file item larger than the `inline_body_bytes` limit that `/api/v1/capabilities` reports answers `download_required`; fetch it through `/api/v1/download` as the [Baltor Harness quickstart](quickstart-baltor-harness.md) shows.

Codex reads repository skills from `.agents/skills/`. Today the file is written by the agent or by you, as the prompt above asks; the service does not place it. Automatic placement remains under development.

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
| `unauthorized` | 401 | The token is missing, wrong, expired or revoked. Set `BALTOR_SERVICE_TOKEN` in the terminal that starts Codex, then run the session check above. |
| `insufficient_scope` | 403 | The token lacks the scope this operation needs. Create a token with `provisioning:read`. |
| `item_unavailable` | 404 | The identity is not in your library, or it was withdrawn. Search again and use a fresh reference. |
| `request_identity_required` | 400 | A download needs a `request_id`. Give each logical download a new one. |
| `download_required` | 413 | The body is larger than the inline limit. Fetch it through `/api/v1/download`. |
| `failed_attempt_limit_reached` | 429 | Too many refused attempts from your address. Fix the token, then wait a minute. |

A `startup_timeout_sec` that passes before the service answers shows as a server that never started; the service answers within a few seconds, so check the network and the token before raising it. [Troubleshooting](service-troubleshooting.md) explains every code, [Service status](https://app.baltor.ai/status) shows a current outage, and [Serving and connections](service-serving-and-connections.md) names the protocol versions. The nightly record of this page's steps is written under `artifacts/quickstart-checks/` in the repository by [the quickstart check](../../tools/check_quickstarts.py).
