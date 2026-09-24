"""The addresses of the staff transports, named once.

Kind: passive constants. The transport in `http.py` reads them before it asks
who is calling, and the staff tools read the tool names; a check in
`admin_mcp_checks.py` requires the names here to be exactly the registered
staff tools, so the two cannot drift apart. This module imports nothing.
"""
from __future__ import annotations

#: The staff protocol endpoint. It answers staff keys only.
ADMIN_PROTOCOL_PATH = "/admin/mcp"
#: The Administration page's staff key route: a superadmin browser session lists, mints and revokes keys.
STAFF_KEYS_PATH = "/api/v1/admin/staff-keys"
STAFF_TOOL_ROUTE_PREFIX = "/api/v1/admin/tools/"
STAFF_TOOL_NAMES = ("accounts_search", "account_get", "account_action", "accounts_invite", "accounts_import",
                    "credits_grant", "credits_revoke", "message_send", "activity_search", "data_search",
                    "catalogue_status", "catalogue_publish", "catalogue_rollback", "item_withdraw", "service_health")
#: One route for each staff tool: the same arguments and the same answer as the protocol tool.
STAFF_TOOL_ROUTES = {STAFF_TOOL_ROUTE_PREFIX + name: name for name in STAFF_TOOL_NAMES}
#: Staff request bodies can name addresses, so no recording choice keeps one.
STAFF_BODY_ROUTES = (ADMIN_PROTOCOL_PATH, STAFF_KEYS_PATH, *STAFF_TOOL_ROUTES)
