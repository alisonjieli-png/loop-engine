# Getting set up with the Baltor service

Kind: operating guide for a paying customer. It takes you from no account to a
harness that has connected to the service and can see its tools.

Baltor is the public brand. Loop Engine is the repository, the Python package
and the technical name. This page uses the exact technical names, because you
copy them into configuration files.

## The whole journey in one view

```text
Getting connected
├── 1. Account
│   ├── The operator invites your email address
│   └── You set a password and sign in at https://app.baltor.ai
├── 2. Client token
│   ├── Account page, Your client tokens, create one token for each client
│   └── The secret is shown once and is never recoverable
├── 3. Keep the token out of your files
│   └── One environment variable, BALTOR_SERVICE_TOKEN
├── 4. Client settings
│   ├── Codex, OpenCode 1.x or Claude Code
│   └── The file holds the name of the variable, never the value
└── 5. Confirm the connection
    ├── The client lists the server
    └── The server answers the protocol handshake and lists five tools
```

Steps one and two happen in a browser. Steps three to five happen on the
machine that runs your harness.

## 1. Get an account

Registration is closed during the private beta. The capabilities record says
so, and you can read it without signing in:

```bash
curl -sS https://app.baltor.ai/api/v1/capabilities
```

Observed on the deployed service on 2026-09-21, the `website` section of that
answer reports `registration_available` as false and `access_profile` as
`operator_provisioned`. The operator creates an invited account for your email
address and sends you a link that lets you set a password. The link works once
and it expires.

After you have a password, sign in at `/login`. Your account page is
`/account`.

## 2. Create one client token for each client

Open `/account` and find the section named Your client tokens. Create one
token for each client you intend to connect, and give each one a label you
will recognise later, such as the name of the machine.

The browser sends this request for you. It is recorded here so that you can
recognise it in a network log:

| Field | Value |
|---|---|
| Address | `/api/v1/account/access` |
| Method | POST |
| Request record | `service_client_access_request/v1` |
| Answer record | `service_client_access_result/v1` |

Three facts about the secret:

- It is shown once. The service stores only a digest of it, so nobody,
  including the operator, can show it to you again.
- It carries the scopes your account already holds, and never more. A client
  token cannot create another token.
- It expires. The account page shows the expiry beside each token, and a token
  whose `state` is `expired` or `revoked` is refused on its next request.

Revoking is in the same place. Select Revoke beside the token. The service
refuses that token on its next request. Revoking does not recall material that
was already downloaded.

## 3. Keep the token in one environment variable

Every supported client reads the token from the environment. The variable name
is published by the service itself, in
`/assets/client-recipes.json`, under `credential_variable`, and it is
`BALTOR_SERVICE_TOKEN`.

Put it in your shell profile, your secret manager or your process supervisor.
Do not put the value in a configuration file, a repository, a ticket or a chat
window.

```bash
read -rs BALTOR_SERVICE_TOKEN && export BALTOR_SERVICE_TOKEN
```

That command reads the token without printing it and without writing it to
your shell history file.

## 4. Configure your client

The service publishes the settings entry for each supported client, and the
Connect page at `/connect` shows the same text with the endpoint already
filled in. The endpoint is the origin plus `/mcp`, which for the deployed
service is `https://app.baltor.ai/mcp`.

Three clients are published by this revision. Their identifiers are the recipe
identifiers the service serves: `codex`, `opencode` and `claude-code`.

One thing to expect. Checked on 2026-09-21, the deployed pilot still serves an
earlier version of that file, which carries the Codex and OpenCode entries and
not the Claude Code one. The Codex and OpenCode settings below are the same
text in both versions. The Claude Code settings below are correct and arrive
on the Connect page with the next release.

### Codex

Merge this table into your existing `config.toml`. Do not replace your other
settings.

```toml
[mcp_servers.baltor]
url = "https://app.baltor.ai/mcp"
bearer_token_env_var = "BALTOR_SERVICE_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 45
```

### OpenCode 1.x

Merge the `baltor` entry into the `mcp` section of your existing
`opencode.json`. OpenCode 2.x uses a different layout, which the service does
not publish yet.

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "baltor": {
      "type": "remote",
      "url": "https://app.baltor.ai/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {"Authorization": "Bearer {env:BALTOR_SERVICE_TOKEN}"}
    }
  }
}
```

This service takes a supplied token. Do not start a login flow for it. The
deployed service reports `oauth_resource_metadata` as false.

### Claude Code

Create a `.mcp.json` file in your project folder, or merge the `baltor` entry
into the `mcpServers` section of an existing one. The file holds the name of
the variable, never the token, so it is safe to keep in version control.

```json
{
  "mcpServers": {
    "baltor": {
      "type": "http",
      "url": "https://app.baltor.ai/mcp",
      "headers": {"Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}"}
    }
  }
}
```

## 5. Confirm that the connection succeeded

Each client has one command that lists its configured servers. Run it in the
terminal where `BALTOR_SERVICE_TOKEN` is set.

```bash
codex mcp list
```

```bash
opencode mcp list
```

```bash
claude mcp list
```

A listing shows configuration. It is not proof of a completed handshake. Two
further facts are separate and both are worth checking:

1. **The server answers.** In a Codex or Claude Code session, open `/mcp` in
   the session and confirm that Baltor's tools appear. In Claude Code, a
   status of Pending approval means you must start the session once in that
   folder and approve the server.
2. **The service recognises your token.** Ask the service who you are:

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" \
  https://app.baltor.ai/api/v1/session
```

Run against the deployed service on 2026-09-21, with an operator-issued pilot
token, that request answered:

```json
{
 "record_type": "service_http_result/v1",
 "operation": "session",
 "result": {
  "record_type": "service_session/v1",
  "principal": {
   "record_type": "service_principal/v1",
   "tenant_id": "pilot-owner",
   "namespace": "pilot-owner:private",
   "key_id": "8867ec11ec6f446fb629bbba3b212f5d",
   "entitlement": "bodies",
   "scopes": ["provisioning:metadata", "provisioning:read", "usage:read"]
  },
  "authentication_mode": "host_key",
  "token_expires_at": null
 }
}
```

Read three things from it. `tenant_id` is the account the token belongs to.
`entitlement` is `bodies` when you may download material and `metadata` when
you may only search it. `scopes` are the operations the token itself permits.

The browser at `/connect` runs the same check and also performs a real
protocol handshake against `/mcp`.

## What a connection does not give you

- It does not give you a model, a model allowance or permission to spend.
- It does not give the service permission to run code on your machine.
- It does not make downloaded material independently qualified. Every answer
  names its `qualification_basis`, and `host_attested` means the host reviewed
  it, not that an independent process did.

## When something refuses

Read [troubleshooting](service-troubleshooting.md) for what each refusal means
and what to do. [Serving and connections](service-serving-and-connections.md)
holds the complete refusal table.

## Related pages

- [Searching and retrieving](service-searching-and-retrieving.md)
- [Serving and connections](service-serving-and-connections.md)
- [Troubleshooting](service-troubleshooting.md)
- [Run the service locally](../../examples/29_intelligence_service/README.md)
- [Private beta operations](private-beta-operations.md), for the operator side
