"""Sign-up links for addresses a superadmin types or imports from a form or a spreadsheet, through the one way in.

Kind: internal service mechanics used by the governed staff tools
`accounts_invite` and `accounts_import`. It adds no runtime type, no store and
no graph vertex, and it adds no way in.

The owner asked on September 24, 2026 for "signing users up if they sign up
offline via an email collection form or spreadsheet share". The owner's rule
of September 23 is one way in, so each address receives Baltor's own sign-up:
the account is created with both marks by `AccountOrigins.prepare_signup`, the
link opens the same `/auth/confirm` page, and the person chooses their own
password there. Nothing in a row can choose a password, confirm an address,
name a provider identity, a role, scopes, a plan or credits.

```text
One import, row by row
├── a row with a value in a column that carries authority: second_way_in,
│   nothing is sent and the value is never kept
├── an address that is not one printable address: invalid_address
├── the same address again: duplicate, only the first row counts
├── an address whose account is open, confirmed or signed in: has_an_account
├── an address whose sign-up link is waiting to be used: sign_up_pending,
│   sent again only with resend_pending
├── every other address: send
└── the rows to send must fit the staff daily message allowance
Apply
├── the allowance and the request identity are reserved first
├── the allowance for one address that public sign-up keeps is honoured
└── Baltor's own sign-up runs for each address: one link, one message
```

The engine is the staff sign-up link of `staff_sign_up_links.py`, the same
one the Administration page's form uses: the message names the staff member
who sent it, the pending link record completes when the account opens, and
free monthly Baltor Pro is granted then when the superadmin asked for it.
"""
from __future__ import annotations

import csv
import io
import re

from dataclasses import dataclass

from . import staff_sign_up_links as links
from .account_email import counted_email_key, email_address
from .account_messages import require_allowance, reservation
from .account_policy import GRANT_FREE_MONTHLY, SEND_SIGN_UP_LINKS
from .http import ServiceHttpError
from .records import ServiceRuntimeError, digest
from .staff_tools import COMPLETED, FAILED, Plan, StaffTool, forbid_unless

RESULT_VERSION = "service_staff_sign_up_result/v1"
ENGINE = "staff_sign_up_link/v1"
SEND, INVALID, DUPLICATE, HAS_ACCOUNT, PENDING, SECOND_WAY_IN, EMPTY = (
    "send", "invalid_address", "duplicate", "address_has_an_account", "sign_up_pending", "second_way_in", "empty_row")
SENT, SENT_RECENTLY, FAILED_TO_SEND = "sent", "address_sent_recently", "failed"
MOST_ADDRESSES, MOST_ROWS, MOST_COLUMNS, LONGEST_CELL, LONGEST_CSV = 50, 1000, 50, 1000, 400_000
#: Column names read as an address, after lower case and underscores.
EMAIL_COLUMNS = frozenset({"email", "email_address", "e_mail", "e_mail_address", "emailaddress", "mail",
                           "your_email", "your_email_address", "work_email", "contact_email"})
#: Columns that would carry authority into an account. A row with a value in
#: one would make the import a second way in, so the row is refused.
AUTHORITY_COLUMNS = frozenset({
    "pass", "pin", "key", "api_key", "secret", "access_token", "refresh_token", "provider_user_id", "user_id", "uid",
    "subject", "sub", "tenant_id", "account_id", "role", "staff", "staff_role", "admin", "is_admin", "superadmin",
    "scope", "scopes", "entitlement", "plan", "plan_state", "confirmed", "confirmed_at", "email_confirmed",
    "email_confirmed_at", "email_confirm", "email_verified", "verified", "credits", "free_monthly", "app_metadata",
    "user_metadata", "baltor_account"})
AUTHORITY_WORDS = ("password", "passwd", "passcode", "token", "secret", "api_key")


def column_name(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def carries_authority(name):
    return name in AUTHORITY_COLUMNS or any(word in name for word in AUTHORITY_WORDS)


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if not isinstance(value, (str, int, float)):
        raise ServiceHttpError("import_cell_invalid")
    text = str(value)
    if len(text) > LONGEST_CELL:
        raise ServiceHttpError("import_cell_too_long")
    return text.strip()


def table(fields):
    """The rows of an import as header names and (row number, cells by name), from CSV text or JSON rows."""
    if ("csv" in fields) == ("rows" in fields):
        raise ServiceHttpError("import_source_required")
    if "csv" in fields:
        text = fields["csv"]
        if len(text) > LONGEST_CSV:
            raise ServiceHttpError("import_too_large", 413)
        try:
            lines = list(csv.reader(io.StringIO(text), strict=True))
        except csv.Error:
            raise ServiceHttpError("import_csv_unreadable") from None
        if not lines:
            raise ServiceHttpError("import_header_missing")
        header, body = [column_name(name) for name in lines[0]], lines[1:]
        rows = [(number, dict(zip(header, [_cell(value) for value in line])))
                for number, line in enumerate(body, start=1) if any(cell.strip() for cell in line)]
    else:
        header = sorted({column_name(name) for row in fields["rows"] for name in row})
        rows = [(number, {column_name(name): _cell(value) for name, value in row.items()})
                for number, row in enumerate(fields["rows"], start=1)]
    if len(set(header)) != len(header) or "" in header:
        raise ServiceHttpError("import_header_invalid")
    if len(header) > MOST_COLUMNS or len(rows) > MOST_ROWS:
        raise ServiceHttpError("import_too_large", 413)
    return header, rows


def email_column(header, named=None):
    if named is not None:
        chosen = column_name(named)
        if chosen not in header:
            raise ServiceHttpError("import_email_column_missing")
        return chosen
    found = [name for name in header if name in EMAIL_COLUMNS]
    if not found:
        raise ServiceHttpError("import_email_column_missing")
    if len(found) > 1:
        raise ServiceHttpError("import_email_column_ambiguous")
    return found[0]


def _masked(address):
    local, _, domain = address.partition("@")
    return (local[:1] + "***@" + domain) if local and domain else "***"


def _existing(tools):
    """Each provider address and what it holds: an open account, a pending sign-up or a replaceable one."""
    from .account_origin import ORIGIN, ORIGIN_VERSION
    from .runtime import SUBJECT
    from .staff_tool_accounts import identity_users
    users = identity_users(tools)
    if users is None:
        raise ServiceHttpError("account_signup_unavailable", 503)
    runtime, issuer = tools.runtime, tools.administration.issuer
    with runtime._catalog.store() as store:
        bound = {row["payload"].get("subject") for row in runtime._catalog.rows_all(store, SUBJECT)
                 if row["payload"].get("issuer") == issuer}
        recorded = {row["payload"].get("subject") for row in runtime._catalog.rows_all(store, ORIGIN)
                    if row["payload"].get("record_type") == ORIGIN_VERSION and row["payload"].get("issuer") == issuer}
    held = {}
    for user in users:
        honoured = user.marked and user.user_id in recorded
        held[user.email] = (HAS_ACCOUNT if user.user_id in bound or (honoured and user.email_confirmed_at)
                            else PENDING if honoured else "replaceable")
    return held


def classify(tools, entries, resend_pending):
    """One outcome for each row: (row number, address or None, authority columns with a value)."""
    held, seen, rows = _existing(tools), set(), []
    for number, raw, authority in entries:
        if authority:
            rows.append({"row": number, "outcome": SECOND_WAY_IN, "columns": sorted(authority)})
            continue
        if not raw:
            rows.append({"row": number, "outcome": EMPTY})
            continue
        try:
            address = email_address(raw)
        except ServiceHttpError:
            rows.append({"row": number, "outcome": INVALID})
            continue
        if address in seen:
            rows.append({"row": number, "outcome": DUPLICATE, "address": address})
            continue
        seen.add(address)
        state = held.get(address)
        outcome = (HAS_ACCOUNT if state == HAS_ACCOUNT else PENDING if state == PENDING and not resend_pending
                   else SEND)
        rows.append({"row": number, "outcome": outcome, "address": address,
                     "replaces_an_account_made_elsewhere": state == "replaceable"})
    return rows


def _signup_ready(tools):
    adapter = getattr(tools.application, "account_email", None)
    if adapter is None or getattr(adapter, "account_origins", None) is None or not adapter.signup_available:
        raise ServiceHttpError("account_signup_unavailable", 503)
    return adapter


def _plan(tools, actor, entries, fields, extra=None):
    _signup_ready(tools)
    if fields.get("free_monthly"):
        forbid_unless(actor, GRANT_FREE_MONTHLY)
    rows = classify(tools, entries, fields.get("resend_pending", False))
    sending = [row for row in rows if row["outcome"] == SEND]
    held = require_allowance(tools, len(sending))
    counts = {}
    for row in rows:
        counts[row["outcome"]] = counts.get(row["outcome"], 0) + 1
    shown = [{key: (_masked(value) if key == "address" else value) for key, value in row.items()} for row in rows]
    facts = [[row["row"], row["outcome"], digest(row.get("address", "")), row.get("columns", [])] for row in rows]
    return Plan({"engine": ENGINE, "rows": len(rows), "outcomes": counts, "to_send": len(sending), "allowance": held,
                 "free_monthly": bool(fields.get("free_monthly")), "row_outcomes": shown, **(extra or {})},
                (), "", "sign_up:" + str(len(sending)), context=[row["address"] for row in sending], facts=facts)


@dataclass(frozen=True)
class _LinkChoice:
    """What the staff sign-up link engine reads of a request: whether the account includes free monthly."""

    free_monthly: bool


def staff_sender(tools, actor):
    """How a sign-up link message names the staff member who sent it, as the Administration page's form does."""
    session = actor.session
    member = (tools.administration.policy.member_for(session.subject, session.email) if session is not None
              else tools.keys._member_for(actor.identity_digest))
    return ((member.name if member is not None and member.name else "")
            or (session.email if session is not None else "") or (member.email if member is not None else "")
            or "A member of the team")


def _apply(tools, actor, fields, context):
    adapter = _signup_ready(tools)
    addresses, free = context.plan.context, bool(fields.get("free_monthly"))
    context.reserve(reservation(tools, len(addresses)))
    sender, secret, choice = staff_sender(tools, actor), adapter.identity_secret(), _LinkChoice(free)
    outcomes, sent = [], []
    for address in addresses:
        try:
            # The staff sign-up link engine: the one way in with both marks,
            # one link, one message naming the sender, and the allowance for
            # one address that public sign-up keeps, shared with it.
            user_id = links._sent_once(adapter, adapter.account_origins, choice, address, sender, secret)
        except links._Refused as refusal:
            outcomes.append({"address_hint": _masked(address), "outcome": refusal.outcome})
            continue
        except (ServiceHttpError, ServiceRuntimeError) as error:
            outcomes.append({"address_hint": _masked(address), "outcome": FAILED_TO_SEND,
                             "code": getattr(error, "code", "failed")})
            continue
        outcomes.append({"address_hint": _masked(address), "outcome": SENT})
        sent.append((counted_email_key(address), user_id))
    result = {"record_type": RESULT_VERSION, "engine": ENGINE, "free_monthly": free,
              "sent": len(sent), "outcomes": outcomes}

    def pending(store):
        return links.pending_link_rows(tools.runtime, store, tools.administration.issuer, sent, free_monthly=free,
                                       sent_by_subject=actor.actor_ref, sent_by_role=actor.role,
                                       request_id=context.request_id, now=int(tools.runtime._now()))
    return context.finish(result, COMPLETED if sent or not addresses else FAILED, prepare=pending)


def invite_plan(tools, actor, fields):
    addresses = fields["addresses"]
    if len(addresses) > MOST_ADDRESSES:
        raise ServiceHttpError("import_too_large", 413)
    return _plan(tools, actor, [(index, value, ()) for index, value in enumerate(addresses, start=1)], fields)


def import_plan(tools, actor, fields):
    header, rows = table(fields)
    column = email_column(header, fields.get("email_column"))
    authority = [name for name in header if carries_authority(name) and name != column]
    entries = [(number, row.get(column, ""), tuple(name for name in authority if row.get(name)))
               for number, row in rows]
    return _plan(tools, actor, entries, fields, {"email_column": column, "authority_columns": authority,
                                          "ignored_columns": [name for name in header
                                                              if name != column and name not in authority]})


ADDRESS = {"type": "string", "minLength": 3, "maxLength": 254}
TOOLS = (
    StaffTool("accounts_invite", "Start Baltor's own sign-up for typed addresses: each gets one sign-up link that "
              "names you, chooses a password and confirms; with free_monthly the account includes Baltor Pro when it "
              "opens. Duplicates, open accounts and pending sign-ups are skipped. Plan first, then apply.",
              {"addresses": {"type": "array", "items": ADDRESS, "minItems": 1, "maxItems": MOST_ADDRESSES},
               "resend_pending": {"type": "boolean"}, "free_monthly": {"type": "boolean"}},
              (SEND_SIGN_UP_LINKS,), invite_plan, _apply,
              required=("addresses",), provider_reads=True),
    StaffTool("accounts_import", "Start Baltor's own sign-up for rows exported from a form or a spreadsheet, given "
              "as CSV text with a header row or as JSON rows. Each row is validated and deduplicated; a row that "
              "carries a password, a confirmation, an identity, a role, scopes, a plan or credits is refused. Plan "
              "first, then apply.",
              {"csv": {"type": "string", "maxLength": LONGEST_CSV},
               "rows": {"type": "array", "maxItems": MOST_ROWS, "items": {"type": "object", "maxProperties":
                                                                             MOST_COLUMNS}},
               "email_column": {"type": "string", "minLength": 1, "maxLength": 100},
               "resend_pending": {"type": "boolean"}, "free_monthly": {"type": "boolean"}},
              (SEND_SIGN_UP_LINKS,), import_plan, _apply,
              provider_reads=True),
)
