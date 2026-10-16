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

Once signed in, open `/account` and find Your Baltor keys. Read the terms and
privacy notice linked beside account creation before submitting.

Create one Baltor key for each client or machine and give it a useful label.
The secret is shown once; subsequent listings show its label, scopes, expiry
and state. Use the smallest scopes the client needs. A key cannot create more
keys through the customer management endpoint.

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
`/assets/client-recipes.json`, with the endpoint filled in as
`https://baltor.ai/mcp`. Use that address. It is the resource that the
service's OAuth metadata names, so the same entry works for a key and for an
OAuth sign-in. Merge the relevant entry into your existing configuration. Do
not replace unrelated settings.

Each entry sends the `Baltor-Step-Effects` header: what your harness's steps
may do with a Baltor item, here reading and writing files in your project,
running commands and using the network. Remove any effect your harness does
not allow. Without the header, your steps hold `reads_fs` only, and a download
of an item that declares more is refused with `step_effects_required`.

### Codex

In your existing `config.toml`:

```toml
[mcp_servers.baltor]
url = "https://baltor.ai/mcp"
bearer_token_env_var = "BALTOR_SERVICE_TOKEN"
startup_timeout_sec = 20
tool_timeout_sec = 45

[mcp_servers.baltor.http_headers]
Baltor-Step-Effects = "reads_fs, writes_fs, spawns_process, network"
```

Confirm the configured server:

```bash
codex mcp list
```

This lists configuration. In a session, inspect `/mcp` and confirm that the
server's tools are available before relying on the connection.

To sign in with OAuth instead of a key, run
`codex mcp add baltor --url https://baltor.ai/mcp` without the token setting.
Codex 0.162.1 detects the OAuth support, prints the sign-in address and
finishes the sign-in as part of that command. Run `codex mcp login baltor`
only when that sign-in did not finish.

### OpenCode 1.x

Merge the `baltor` entry into the `mcp` section of your existing
`opencode.json`, the global `~/.config/opencode/opencode.json` or the
project's own file:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "baltor": {
      "type": "remote",
      "url": "https://baltor.ai/mcp",
      "enabled": true,
      "oauth": false,
      "headers": {
        "Authorization": "Bearer {env:BALTOR_SERVICE_TOKEN}",
        "Baltor-Step-Effects": "reads_fs, writes_fs, spawns_process, network"
      }
    }
  }
}
```

```bash
opencode mcp list
```

This entry uses a supplied token, so do not start an external login flow for
it. For an OAuth sign-in, leave out the Authorization header and the `oauth`
setting, then run `opencode mcp auth baltor`. The published recipe targets the
1.x layout. Check your installed client version before applying it to a
different configuration format.

### Claude Code

Create or update `.mcp.json` in the project folder:

```json
{
  "mcpServers": {
    "baltor": {
      "type": "http",
      "url": "https://baltor.ai/mcp",
      "headers": {
        "Authorization": "Bearer ${BALTOR_SERVICE_TOKEN}",
        "Baltor-Step-Effects": "reads_fs, writes_fs, spawns_process, network"
      }
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

Check your version with `pi --version`. Pi 0.99.2 has a built-in Model
Context Protocol client; follow the [Pi quickstart](quickstart-pi.md) for its
native connection. Pi 0.73.1 has none, so Baltor connects to it through a
small Pi extension: one TypeScript file, served at
[`/assets/pi/baltor.ts`](https://app.baltor.ai/assets/pi/baltor.ts). Pi runs
every extension in `.pi/extensions` with your permissions and does not ask
first, so read the file before you start Pi. It needs no other packages.

```bash
mkdir -p .pi/extensions
curl -fsSL https://baltor.ai/assets/pi/baltor.ts -o .pi/extensions/baltor.ts
```

Create `.pi/baltor.json` beside it. It holds the name of the variable, never
the token. `step_effects` is the list the extension sends in the
`Baltor-Step-Effects` header:

```json
{
  "baltor": {
    "url": "https://baltor.ai/mcp",
    "token_env": "BALTOR_SERVICE_TOKEN",
    "step_effects": ["reads_fs", "writes_fs", "spawns_process", "network"]
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
curl -sS -H "Authorization: Bearer $BALTOR_SERVICE_TOKEN" https://baltor.ai/api/v1/session
```

The result identifies the principal and its scopes. `token_expires_at` is when
the credential expires, as Unix time in seconds, for a Baltor key as well as
for an OAuth access token or a browser sign-in. It is `null` only for a key
created without an expiry. Your Baltor keys on `/account` shows the same date.
Then confirm that your client sees `provisioning_discover`,
`provisioning_list`, `provisioning_manifest`, `provisioning_read` and
`intelligence_search`.

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
