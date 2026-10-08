---
name: plan-mcp-service-setup
description: Discover remote MCP services for a task and prepare a scoped setup plan from dated registry and publisher metadata. Use when choosing a service or planning an MCP connection, not to install local server packages or authorize account operations.
license: MIT
metadata:
  asset_version: "1.0.0"
  data_file: "references/mcp-services-table.json"
---

# Plan a remote MCP connection

Return a task-relevant shortlist and the missing setup checks. Keep four
states separate: listed in a directory, documented as MCP-compatible,
authenticated in this client, and successfully tested for a named tool.
A listing proves only the first state.

## Discover

Use the dated source table shipped with this package, or ask the existing
MCP directory for a newer one. Read publisher documentation before treating
a listed transport, endpoint or authentication method as current. The helper
does lexical filtering; its order is not a quality ranking.

```text
python scripts/plan_mcp_service_setup.py '{"record_type":"mcp_setup_plan_request/v1","query":"logs","publisher":"cloudflare.com","transport":"streamable-http","count":3,"on":"2026-10-08"}'
```

The [request contract](contracts/input.schema.json) defines the parameters.
The helper reads its own table, makes no network call and writes nothing.
It returns [typed plans](contracts/output.schema.json), not client settings
or credentials. An expired table returns no current candidates.

## Prepare setup

For the selected service, use [the setup checklist](references/setup.md).
Use the chosen client's current configuration syntax; an `mcpServers` example
is not a universal client format. Preserve unrelated settings.

If the user asked for configuration changes, prepare the smallest necessary
change. Do not treat this skill, a directory row or an existing broad token
as permission to connect accounts, grant scopes, spend money or execute tools.
Use the client's supported sign-in or secret store; never put credential
values in a report, a package or an example.

Do not turn an absent authentication declaration into "no authentication."
If registry and publisher transport declarations conflict, report both and
resolve the current contract before connecting. A URL ending in `/sse` does
not by itself prove the old SSE transport.

After separately authorized setup, record the exact endpoint, transport,
negotiated protocol, granted scopes and tool schemas. Test a harmless read
only when authorized. Report failures and leave untested operations unknown.
Never enable a write-capable tool merely because `tools/list` succeeded.

Run `python scripts/test_plan_mcp_service_setup.py` for the offline checks.
These checks validate the planner, not any external MCP server.
