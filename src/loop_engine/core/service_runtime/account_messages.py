"""Service messages a superadmin sends to one account or a filtered set, and the staff daily message allowance.

Kind: internal service mechanics used by the governed staff tool
`message_send`. It sends through the mail provider of the existing account
email adapter and adds no runtime type, no store and no graph vertex.

The owner asked on September 24, 2026 for "emailing users custom
information". A message here is a service message only:

```text
One staff message
├── a purpose from the service vocabulary: account_notice, service_notice,
│   security_notice or support_reply
│   ├── no purpose: refused with message_service_purpose_required
│   └── marketing, a newsletter, a promotion or an offer: refused with
│       marketing_needs_recorded_consent, because the service records no
│       marketing consent
├── the service message template around the staff member's plain text, and a
│   preview of exactly what each recipient reads, in the plan
├── recipients: one account, or the accounts a filter selects, each at the
│   confirmed address the identity provider holds for it
└── the staff daily message allowance, counted in the service store before
    anything is sent; a plan or an apply over it is refused
```

The mail provider's free plan sends 100 messages a day for the whole service.
Staff messages, and the sign-up links a superadmin sends, draw on their own
allowance of `mail_daily_cap`, 50 by default, so public sign-up and password
recovery keep the rest. The allowance counts a message when it is reserved,
so a message that fails after its reservation still counts.
"""
from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .account_policy import MESSAGES_SEND
from .http import ServiceHttpError
from .records import ServiceRuntimeError, digest
from .staff_tools import COMPLETED, FAILED, Plan, StaffTool

MAIL_DAY, MAIL_DAY_VERSION = "service_staff_mail_day", "service_staff_mail_day/v1"
TEMPLATE_VERSION, RESULT_VERSION = "service_message_template/v1", "service_staff_message_result/v1"
SERVICE_PURPOSES = ("account_notice", "service_notice", "security_notice", "support_reply")
#: Purposes that would make a message marketing. The service records no
#: marketing consent, so each is refused with its own code.
MARKETING_PURPOSES = ("marketing", "newsletter", "promotion", "promotional", "offer", "announcement",
                      "product_update", "campaign")
TEMPLATES = ("service_message",)
LONGEST_SUBJECT, LONGEST_BODY, SHOWN_RECIPIENTS = 120, 4000, 20


def _day(moment):
    return datetime.fromtimestamp(int(moment), timezone.utc).strftime("%Y-%m-%d")


def mail_day(runtime, store, now):
    """Today's staff message count, in UTC, and its row, or a zero count and None."""
    day = _day(now)
    row = runtime._catalog.read(store, MAIL_DAY, day)
    if row is None:
        return None, {"record_type": MAIL_DAY_VERSION, "day": day, "sent": 0}
    value = row["payload"]
    if value.get("record_type") != MAIL_DAY_VERSION or type(value.get("sent")) is not int:
        raise ServiceRuntimeError("unsupported_or_corrupt_record")
    return row, value


def allowance(tools, now=None):
    """The staff daily allowance: its cap, what today has used and what remains."""
    runtime = tools.runtime
    now = runtime._now() if now is None else now
    with runtime._catalog.store() as store:
        _row, value = mail_day(runtime, store, now)
    cap = tools.settings.mail_daily_cap
    return {"day": value["day"], "cap": cap, "used": value["sent"], "remaining": max(0, cap - value["sent"])}


def require_allowance(tools, count):
    held = allowance(tools)
    if count > held["remaining"]:
        raise ServiceHttpError("staff_mail_daily_cap_reached", 429, details={
            "record_type": "service_staff_mail_allowance/v1", **held, "requested": count})
    return held


def reservation(tools, count):
    """A `prepare` for `ApplyContext.reserve`: today's count moves by `count` in the same batch, or refuses."""
    def prepare(store):
        runtime = tools.runtime
        row, value = mail_day(runtime, store, runtime._now())
        cap = tools.settings.mail_daily_cap
        if value["sent"] + count > cap:
            raise ServiceHttpError("staff_mail_daily_cap_reached", 429, details={
                "record_type": "service_staff_mail_allowance/v1", "day": value["day"], "cap": cap,
                "used": value["sent"], "remaining": max(0, cap - value["sent"]), "requested": count})
        updated = runtime._catalog.record(MAIL_DAY, value["day"], {**value, "sent": value["sent"] + count})
        return (updated,), (runtime._catalog.guard(row, updated["record_id"]),)
    return prepare


def mail_adapter(tools):
    """The account email adapter, when it may send a message now."""
    adapter = getattr(tools.application, "account_email", None)
    if adapter is None or getattr(adapter.configuration, "allow_network", False) is not True:
        raise ServiceHttpError("staff_messages_unavailable", 503)
    return adapter


def send_one(adapter, recipient, subject, body):
    """Send exactly one message through the adapter's mail provider, as sign-up and recovery do."""
    return adapter.send_message(recipient, subject, body)


def purpose_of(value):
    if value in SERVICE_PURPOSES:
        return value
    if isinstance(value, str) and value.strip().lower().replace("-", "_").replace(" ", "_") in MARKETING_PURPOSES:
        raise ServiceHttpError("marketing_needs_recorded_consent", 403)
    raise ServiceHttpError("message_service_purpose_required")


def _plain(value, longest, code):
    if (not isinstance(value, str) or not value.strip() or len(value) > longest
            or any(ord(character) < 32 and character != "\n" for character in value)):
        raise ServiceHttpError(code)
    return value.strip()


def render(display_name, origin, subject, body):
    """The one service message template: the staff member's text inside a frame that says what it is."""
    return (display_name + ": " + subject,
            "Hello,\n\n" + body + "\n\n"
            "This is a service message about your " + display_name + " account. It is not marketing: "
            + display_name + " sends marketing only to people who agreed to receive it.\n\n"
            + display_name + "\n" + origin + "\n")


def _masked(address):
    local, _, domain = address.partition("@")
    return local[:1] + "***@" + domain


def _recipients(tools, fields):
    from .staff_tool_accounts import _matches, joined_accounts
    rows, details = joined_accounts(tools)
    if not details:
        raise ServiceHttpError("message_recipients_unavailable", 503)
    if ("tenant_id" in fields) == ("audience" in fields):
        raise ServiceHttpError("message_recipients_required")
    if "tenant_id" in fields:
        chosen = [row for row in rows if row["tenant_id"] == fields["tenant_id"]]
        if not chosen:
            raise ServiceHttpError("account_not_found", 404)
    else:
        chosen = [row for row in rows if _matches(row, fields["audience"])]
    kept = [row for row in chosen if row["email"] and row["email_confirmed"]]
    return sorted(kept, key=lambda row: row["tenant_id"]), len(chosen) - len(kept)


def message_plan(tools, actor, fields):
    adapter = mail_adapter(tools)
    purpose = purpose_of(fields.get("purpose"))
    subject = _plain(fields["subject"], LONGEST_SUBJECT, "invalid_message_subject")
    body = _plain(fields["body"], LONGEST_BODY, "invalid_message_body")
    if "\n" in subject:
        raise ServiceHttpError("invalid_message_subject")
    recipients, unconfirmed = _recipients(tools, fields)
    if not recipients:
        raise ServiceHttpError("message_has_no_recipients", 404)
    held = require_allowance(tools, len(recipients))
    shown_subject, shown_body = render(adapter.display_name, adapter.public_base_url, subject, body)
    facts = {"purpose": purpose, "template": TEMPLATE_VERSION, "message": digest([shown_subject, shown_body]),
             "recipients": [[row["tenant_id"], digest(row["email"])] for row in recipients]}
    return Plan({"purpose": purpose, "template": fields.get("template", TEMPLATES[0]), "recipients": len(recipients),
                 "recipients_without_a_confirmed_address": unconfirmed,
                 "first_recipients": [{"tenant_id": row["tenant_id"], "address_hint": _masked(row["email"])}
                                      for row in recipients[:SHOWN_RECIPIENTS]],
                 "preview": {"subject": shown_subject, "body": shown_body}, "allowance": held},
                (), fields.get("tenant_id", ""), "message:" + str(len(recipients)),
                context={"recipients": [(row["tenant_id"], row["email"]) for row in recipients],
                         "subject": shown_subject, "body": shown_body}, facts=facts)


def message_apply(tools, actor, fields, context):
    adapter = mail_adapter(tools)
    planned = context.plan.context
    context.reserve(reservation(tools, len(planned["recipients"])))
    outcomes = []
    for tenant_id, address in planned["recipients"]:
        try:
            send_one(adapter, address, planned["subject"], planned["body"])
            outcomes.append({"tenant_id": tenant_id, "outcome": "sent"})
        except (ServiceHttpError, ServiceRuntimeError) as error:
            outcomes.append({"tenant_id": tenant_id, "outcome": "failed", "code": getattr(error, "code", "failed")})
    result = {"record_type": RESULT_VERSION, "message_id": uuid.uuid4().hex, "purpose": fields["purpose"],
              "sent": sum(row["outcome"] == "sent" for row in outcomes),
              "failed": sum(row["outcome"] == "failed" for row in outcomes), "outcomes": outcomes}
    return context.finish(result, FAILED if result["sent"] == 0 else COMPLETED)


AUDIENCE = {"type": "object", "additionalProperties": False, "properties": {
    "plan_state": {"type": "string", "maxLength": 32}, "founding": {"type": "boolean"}, "enabled": {"type": "boolean"},
    "created_after": {"type": "string", "maxLength": 25}, "created_before": {"type": "string", "maxLength": 25}}}

TOOLS = (
    StaffTool("message_send", "Send a plain-text service message to one account or to the accounts a filter "
              "selects, inside the service message template. The plan shows the exact preview and the daily "
              "allowance. Service purposes only: marketing needs recorded consent the service does not hold.",
              {"purpose": {"type": "string", "maxLength": 40}, "template": {"enum": list(TEMPLATES)},
               "subject": {"type": "string", "minLength": 1, "maxLength": LONGEST_SUBJECT},
               "body": {"type": "string", "minLength": 1, "maxLength": LONGEST_BODY},
               "tenant_id": {"type": "string", "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
               "audience": AUDIENCE},
              (MESSAGES_SEND,), message_plan, message_apply, required=("subject", "body"), provider_reads=True),
)
