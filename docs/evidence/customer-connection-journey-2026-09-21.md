# Walking the customer connection journey, September 21, 2026

Kind: dated evidence record. It reports what happened when the connection
instructions the live website serves were followed exactly, on this machine,
on that date.

Why it exists: the site tells a customer how to connect their coding tool.
Nothing had checked that those instructions work when a person follows them.
A recipe that does not work is worse than no recipe, because the customer
blames their own setup.

## What was done

The connection recipe was fetched from the deployed service, not copied from
the repository, so the subject is what a customer actually receives:

```bash
curl https://app.baltor.ai/assets/client-recipes.json
```

It returns `website_client_recipes/v2` with three recipes, for Codex,
OpenCode and Claude Code, each naming the documentation page it was drawn
from. The Claude Code recipe was followed to the letter.

## Step one: the configuration file

The recipe says to create `.mcp.json` in the project folder, or merge its
`baltor` entry into an existing one, and that the file holds the name of the
variable and never the token. Written exactly as served:

```json
{
  "mcpServers": {
    "baltor": {
      "type": "http",
      "url": "https://app.baltor.ai/mcp",
      "headers": { "Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}" }
    }
  }
}
```

Checked: the file contains no credential. The token appears only as the name
of an environment variable, so the file is safe to keep in version control,
which is what the recipe claims.

## Step two: the credential

`BALTOR_SERVICE_TOKEN` was set in the shell from the system keyring. It was
never written to a file, never passed on a command line and never printed.

## Step three: the documented verification command

The recipe names `claude mcp list` as its verification command. Run in that
folder, in that shell:

```text
baltor: https://app.baltor.ai/mcp (HTTP) - ⏸ Pending approval (run `claude` to approve)
```

The recipe's own verification note says: "If the status is Pending approval,
start claude in this folder once and approve the server." The observed
output is exactly the case that note describes. The instructions match what
the tool does.

## What this shows

A customer who copies the Claude Code recipe from the live site, sets one
environment variable and runs the documented command sees the server listed
and is told the one remaining step, in the words the recipe already gave
them. The address is right, the header shape is right, the variable name is
right, and no secret lands in a file.

## What this does not show

The approval step needs an interactive session and was not performed here,
so no tool call was made through this path. That gap is closed from the
other side: a separate probe spoke the protocol to the same address directly
with the same credential and observed `initialize` answering 200 with server
`loop-engine-intelligence` version 1.0.0 and protocol version `2025-11-25`,
and `tools/list` answering 200 with five tools. Between the two, every part
of the path is observed, but not in one continuous session.

The Codex and OpenCode recipes were not followed. Neither client is
installed on this machine. Their addresses and header shapes are the same as
the Claude Code recipe's, and their configuration locations and file formats
differ, so this record says nothing about whether those two work.

## One thing worth fixing

A client that offers a protocol version the service does not support is
refused with HTTP 400 and the typed record `service_http_error/v1`, code
`unsupported_protocol_version`, `effect_commitment` `not_asserted`,
`automatic_retry` false. That refusal is correct and it is not a silent
downgrade, which the version policy requires.

It does not name the versions the service does support. That information
exists in the capabilities record at `/api/v1/capabilities` as
`protocol.versions`, so a client author has to make a second request or
guess. A refusal should say what to do next.
