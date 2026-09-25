# Get set up with Baltor

Kind: customer guide to account access, client configuration and a first verified connection.

Use [Get set up](https://app.baltor.ai/setup) for the interactive guide and the
configuration recipe for your client. `/connect` and `/docs/getting-set-up` open
that same guide. You do not need to install the local engine to connect an
existing coding tool to the hosted library.

## Account and client token

Open [Get started](https://app.baltor.ai/get-started) for access. When registration
is open, enter your email address, open the emailed link and choose your password
twice on the confirmation page. Signup never asks you to send a password to the
service's email endpoint. The confirmation page opens your account only after
the identity provider accepts the password.

Once signed in, open `/account` and
Your client tokens. Read the terms and privacy notice linked beside account
creation before submitting.

Create one token for each client or machine and give it a useful label. The
secret is shown once; subsequent listings show its identity, expiry and state.
Use the smallest scopes the client needs. A token cannot create more client
tokens through the customer management endpoint.

## Keep the token in your client's environment

The published recipes use `BALTOR_SERVICE_TOKEN`. Set it in the environment of
the process that starts your client. The configuration files contain the
variable's name, not its secret value. Keep the secret out of repositories,
prompts, screenshots and support messages.

The guide provides a terminal input method that avoids putting the token in
shell history. Start the client from that terminal, or use its documented
secret configuration for your operating system. A variable set in one terminal
does not automatically reach a separately launched desktop application.

## Configure the connection

The recipes below are the formats this service publishes in
`/assets/client-recipes.json`. Merge the relevant entry into your existing
configuration. Do not replace unrelated settings. The endpoint shown by the
interactive guide follows the current website origin.

### Codex

In your existing `config.toml`:

```toml
[mcp_servers.baltor]
url = "https://app.baltor.ai/mcp"
bearer_token_env_var = "BALTOR_SERVICE_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 45
```

Confirm the configured server:

```bash
codex mcp list
```

This lists configuration. In a session, inspect `/mcp` and confirm that the
server's tools are available before relying on the connection.

### OpenCode 1.x

Merge the entry into `opencode.json`:

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

```bash
opencode mcp list
```

This service uses a supplied token, so do not start an external login flow for
this entry. The published recipe targets the 1.x layout. Check your installed
client version before applying it to a different configuration format.

### Claude Code

Create or update `.mcp.json` in the project folder:

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

Run this in that project, from the terminal holding the environment variable:

```bash
claude mcp list
```

If the status is Pending approval, start a session in that folder and approve
the server through the client's prompt. A missing-variable warning means the
client process did not receive the variable. In a session, inspect `/mcp` to
confirm that the tools are listed.

### Pi

Pi has no built-in Model Context Protocol client, so Baltor connects to Pi
through a small Pi extension: one TypeScript file, served at
[`/assets/pi/baltor.ts`](https://app.baltor.ai/assets/pi/baltor.ts). Pi runs
every extension in `.pi/extensions` with your permissions and does not ask
first, so read the file before you start Pi. It needs no other packages.

```bash
mkdir -p .pi/extensions
curl -fsSL https://app.baltor.ai/assets/pi/baltor.ts -o .pi/extensions/baltor.ts
```

Create `.pi/baltor.json` beside it. It holds the name of the variable, never
the token:

```json
{
  "baltor": {
    "url": "https://app.baltor.ai/mcp",
    "token_env": "BALTOR_SERVICE_TOKEN"
  }
}
```

Check the connection from the terminal holding the environment variable:

```bash
pi -p --baltor-check
```

The check makes no model call and downloads nothing. Its last line says
`Result: ready`. In a Pi session, the /baltor command runs the same check.
The extension adds a search tool and a download tool. A download checks every
file against its published SHA-256 digest before it writes anything, installs
the skill in `.pi/skills` and never replaces a folder it did not install. Pi
lists a new skill from the next session.

### Baltor Harness

The Baltor Harness is Baltor's own engine: the free, open source `loop-engine`
command from this repository. It works through a task in small steps on the
model you choose and keeps a record of every step. It does not search or
download from Baltor by itself yet. Search and download with your token as
[Searching and retrieving](service-searching-and-retrieving.md) shows, check
each download's SHA-256 against its digest, and add the material to your task
file.

```bash
python3 -m venv ~/.baltor-harness
~/.baltor-harness/bin/pip install 'git+https://github.com/alisonjieli-png/loop-engine'
export PATH="$HOME/.baltor-harness/bin:$PATH"
loop-engine doctor
```

The first line of the answer should read `Loop Engine doctor: CONFIGURATION
VALID`. This checks the installation only: it makes no model call and does not
contact Baltor. Then run the task with the material in it, for example on
Ollama Cloud with `OLLAMA_API_KEY` in your environment:

```bash
loop-engine solve --file task.md --ollama-api-key --model-route cloud.default --unattended --max-model-calls 60 --workspace baltor-run
```

`--workspace` must be an empty folder or one that does not exist yet. When the
run ends it prints its output files; compare them with what you asked for.
The engine's own verification is strict and can refuse a correct result, so
check the output yourself. To run on a model on your own machine, follow the
local engine's [installation guide](../../README.md#install).

## Check account, tools and material separately

A configured server entry is not a completed handshake or a finished task.
Confirm your account first:

```bash
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://app.baltor.ai/api/v1/session
```

The result identifies the principal, scopes and expiry. Then confirm that your
client sees `provisioning_discover`, `provisioning_list`,
`provisioning_manifest`, `provisioning_read` and `intelligence_search`.

Ask the client to search for one relevant item. Inspect its manifest, download
it and verify its digest. Finally, verify that your harness actually loaded it
through its native mechanism. The published recipes do not claim that every
client/version combination has completed this whole journey.

## Configure models separately

Baltor's service token is not a model provider key. Use your harness's own
provider settings for local Ollama, a private endpoint or a hosted provider.
An address such as `127.0.0.1` belongs to the machine or container where the
harness runs. The hosted library does not configure or forward that endpoint.

The local engine has a separate [installation guide](../../README.md#install).
Its quickstart has its own runtime and sandbox requirements. Connecting the
hosted library does not grant permission to run downloaded code.

Read [Searching and retrieving](service-searching-and-retrieving.md) next, or
[Troubleshooting](service-troubleshooting.md) if a step refuses. The published
client recipes link their official configuration sources.

Read the [privacy notice](https://app.baltor.ai/privacy) and
[terms of service](https://app.baltor.ai/terms) before using the service.
