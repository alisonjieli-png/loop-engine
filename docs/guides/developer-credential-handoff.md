# Reuse Baltor credentials in Claude Code

Kind: operator setup guide for this workstation. No credential values are
stored in this guide, Git or the development HTML.

Claude Code has six project-local connections configured for this repository:
`baltor-resend`, `baltor-cloudflare`, `baltor-supabase`, `baltor-stripe-test`
`baltor-fly` and `baltor-namecheap`. Installed Claude Code 2.1.271 reported
the first five connected; the later Namecheap connection also passes its
connection check and has completed real domain-record reads and writes.
The existing GitHub command-line authentication also works. No model session
was started to perform these checks.

## Start the takeover

Use the same operating-system user in `/home/username/loop-engine`, with the
login keyring unlocked. Select the requested Fable model through Claude's
normal model selector; this handoff supplies no Anthropic account credential.

This command uses only the exported Baltor connections. It does not disable
permission prompts or change global connection settings:

```bash
cd /home/username/loop-engine
claude --strict-mcp-config --mcp-config .loop-engine-dev/baltor-claude-handoff/claude-mcp.json
```

The same six connections are installed at local project scope, so an
ordinary new Claude Code session in this checkout can use them too. Inspect
`/mcp` and reconnect if needed. Read `CLAUDE.md` and the
[Fable handoff](../context/FABLE-5-1-HANDOFF-2026-09-20.md) before acting.

## Exported references

The private directory is
`/home/username/loop-engine/.loop-engine-dev/baltor-claude-handoff/`.
It is excluded from Git, with owner-only directory and file permissions.
Its configuration and reference manifest contain no plaintext secrets.

The reusable source is
[`operator_credentials.json`](../../tools/operator_credentials.json).
It names thirteen existing keyring references. It also declares two names
that hold no credential yet, `cloudflare-dns` and `supabase-auth-settings`,
for grants that have not been given:

| Reference | Purpose |
|---|---|
| `fly` | Existing Baltor organization deployment access. |
| `stripe-test` | Approved sandbox account `acct_1UHZ9KCCxLfArYED`. |
| `supabase-publishable`, `supabase-secret` | Application identification and separately permitted server operations for the existing project. |
| `supabase-legacy-anon`, `supabase-legacy-service-role` | Retained legacy references. Prefer modern key types and never inject privileged keys into browsers. |
| `resend-send`, `resend-management` | Separate sending credential and authorized management connection. |
| `cloudflare-management` | Newly approved write grant, used successfully to create the Free zone and manage its records. |
| `supabase-management` | Existing project-scoped management connection. |
| `baltor-admin` | Existing pilot administrator token, not unrestricted cloud authority. |
| `baltor-pilot-owner`, `baltor-pilot-boundary` | Diagnostic service credentials with their original expiry and scope. |

Earlier Stripe operator and temporary-sandbox credentials are excluded from
active use because they are not the selected runtime account. Unrelated
personal and model-provider credentials are not exported. Namecheap uses
Claude Code's native authorization store and refresh mechanism; its token
values are not copied into this export. GitHub reuses existing `gh`
authentication; no second token was
created or copied.

## How the connection works

[`operator_credentials.py`](../../tools/operator_credentials.py) reads one
named credential from the system keyring when needed. For remote connections,
it checks Claude Code's exact server name and URL before returning a header
through the client's private process pipe. It refuses unbound use and
terminal output. Never run its `headers` command in a chat tool, save its
output to a file, or paste that output.

The credential's own destination must also match, so changing only a client
URL cannot redirect a valid provider credential. The Stripe profile refuses
keys outside test mode. Twenty-three local checks cover these guards, refresh
handling, conflicting selections, native authorization configuration and
secret suppression. Required Cloudflare scopes are checked before use and
after refresh; a read-only grant cannot satisfy the write profile.

Namecheap publishes matching issuer metadata at
`https://www.namecheap.com/.well-known/oauth-authorization-server`.
The native connection explicitly uses that metadata. Do not disable issuer
validation or copy its authorization response into another credential store.
`claude mcp get baltor-namecheap` checks the connection and can refresh its
expired access token through the already approved grant.

Claude Code documents this `headersHelper` mechanism and runs it on connection
and reconnection. Local-scope helpers require project trust. Keep normal
permission checks enabled.
[Claude Code documentation](https://code.claude.com/docs/en/mcp#use-dynamic-headers-for-custom-authentication).

Expired Resend and Cloudflare tokens were refreshed through existing grants.
The helper refreshes named operator connections at pinned token endpoints and
saves rotated credentials in the same keyring item. It does not request new
scopes. A refused refresh requires provider authorization, not a different
route around the refusal.

Fly uses the existing keyring-aware helper and official local server. A
process outside the desktop login session may lack
`DBUS_SESSION_BUS_ADDRESS`. Reuse the actual authorized user session. Do not
copy the keyring database into a container or expose a credential server.
The first isolated protocol probe lacked that variable; its corrected probe
and Claude Code's own check succeeded.

## Command-line access

Inspect safe metadata without values:

```bash
/usr/bin/python3 tools/operator_credentials.py inventory
```

Give a trusted command only the selected credential in its environment:

```bash
/usr/bin/python3 tools/operator_credentials.py run --ref stripe-test --timeout 30 -- stripe get /v1/account
/usr/bin/python3 tools/fly_operator.py --account baltor -- machine list --app baltor-pilot --json
gh auth status
```

The commands can return account metadata. Do not paste private customer data
into chat just because the key is redacted. The wrapper suppresses exact
selected secrets in the output of the command it runs; it is not a sandbox or a general detector
for transformed secrets. Never run `printenv`, logging scripts or untrusted
code with injected credentials.

Multiple `--ref` choices are supported when a trusted operation needs them.
Their environment names are declared in the manifest. Conflicting names
refuse. A timeout leaves the external outcome unknown and does not retry.
Inspect provider state before repeating a possible write.

## Limits

This handoff works on this workstation under its authorized user. It is not
a portable raw-secret backup. Another machine, cloud session or user account
needs authorized secret-manager access or fresh provider login.
Copying these configuration files alone grants nothing.

Namecheap authorization works. The owner approved the corrected Cloudflare
connection, and real zone creation and DNS writes succeeded. The helper now
selects `cloudflare-baltor-write`; the older read-only credential is retained
but not selected. Reconnect an already running Claude connection to load the
new header. Valid requested scopes include `zone.write` and `dns.write`;
`zone.edit` and `dns.edit` are invalid OAuth scope names.
Supabase authentication-settings
permission remains separate from database and storage permission.

This does not extend pilot entitlements,
approve model calls, enable live charges or authorize GitHub publication.
Tool discovery proves connection, not a complete customer journey.
