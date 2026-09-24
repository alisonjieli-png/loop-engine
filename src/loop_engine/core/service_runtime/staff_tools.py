"""The staff tools: typed, paged operations for running the service, shared by both staff transports.

Kind: internal service mechanics. Each call is one governed operation that
the transport runs through `invoke_http_service_as_loop`, so the existing
Practitioner boundary of the remote service owns it. The tools add no runtime
type, no store and no graph vertex; the protocol endpoint `/admin/mcp` and the
routes under `/api/v1/admin/tools/` are adapters over the same functions
(`admin_mcp.py`).

The owner asked on September 24, 2026 for "an MCP or tool or API endpoint for
management functions" so the person running Baltor can manage it from Claude
Code, Codex or any protocol client.

```text
One staff tool call
├── the caller: a staff key or a signed-in staff browser session, checked now
├── the permission: the role table in account_policy.py, and nothing else
├── the arguments: one closed JSON schema for each tool; anything else refused
├── a tool without an effect answers at once
├── a tool with an effect takes two calls
│   ├── step "plan": what would change, and a plan digest over the exact
│   │   arguments, the caller and the version of every record it depends on
│   └── step "apply": the same arguments, that plan digest and a new request
│       identity; a digest that differs, because the state or the arguments
│       moved, is refused with plan_changed and nothing changes
└── one audit record for every call, under the request reference; the audit
    record, the effect and the request identity of an apply commit together
```

A repeated apply under the same request identity returns its first result and
changes nothing. An apply committed while the key was being revoked is refused
by the key record's own version guard.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields as dataclass_fields
from pathlib import Path
import secrets

from .activity import arguments_digest, audit_row, unique_guards, write_audit
from .http import ServiceHttpError
from .http_auth import HttpAuthenticationError
from .records import ServiceRuntimeError, digest

SETTINGS_VERSION = "service_staff_tools/v1"
RESULT_VERSION = "service_staff_tool_result/v1"
PLAN_VERSION = "service_staff_plan/v1"
APPLY, APPLY_VERSION = "service_staff_apply", "service_staff_apply/v1"
PLAN_STEP, APPLY_STEP, READ_STEP = "plan", "apply", "read"
COMPLETED, IN_PROGRESS, FAILED = "completed", "in_progress", "failed"
#: The mail provider's free plan sends 100 messages a day for the whole
#: service. Staff messages draw on their own daily allowance, half of that by
#: default, so public sign-up and password recovery keep the other half.
DEFAULT_MAIL_DAILY_CAP, PROVIDER_FREE_DAILY_MESSAGES = 50, 100
REQUEST_ID_PATTERN = "^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"
DIGEST_PATTERN = "^[0-9a-f]{64}$"


@dataclass(frozen=True)
class StaffToolSettings:
    """The host file's optional `staff_tools` block. Without it the defaults apply."""

    mail_daily_cap: int = DEFAULT_MAIL_DAILY_CAP
    catalogue_incoming_root: str = ""
    record_type: str = SETTINGS_VERSION

    def __post_init__(self):
        if self.record_type != SETTINGS_VERSION:
            raise ServiceRuntimeError("unsupported_staff_tool_settings", f"this release reads {SETTINGS_VERSION}")
        if type(self.mail_daily_cap) is not int or not 0 <= self.mail_daily_cap <= PROVIDER_FREE_DAILY_MESSAGES:
            raise ServiceRuntimeError("invalid_staff_tool_settings",
                                      "the staff daily message allowance is a whole number from 0 to 100")
        root = self.catalogue_incoming_root
        if not isinstance(root, str) or (root and (not Path(root).is_absolute() or Path(root).resolve() != Path(root))):
            raise ServiceRuntimeError("invalid_staff_tool_settings",
                                      "the catalogue incoming folder is an absolute path without symbolic links")

    @classmethod
    def from_host(cls, value):
        names = {item.name for item in dataclass_fields(cls)}
        if not isinstance(value, dict) or set(value) - names or value.get("record_type") != SETTINGS_VERSION:
            raise ServiceRuntimeError("unsupported_staff_tool_settings",
                                      "a staff_tools block names its record version and only the fields of that version")
        return cls(**value)


@dataclass(frozen=True)
class StaffTool:
    """One staff tool: its name, what it does, its closed arguments, who may call it and what runs."""

    name: str
    description: str
    arguments: dict
    permissions: tuple
    run: object = field(repr=False)
    apply: object = field(default=None, repr=False)
    required: tuple = ()
    provider_reads: bool = False

    @property
    def effect(self):
        return self.apply is not None

    def input_schema(self):
        properties = dict(self.arguments)
        required = list(self.required)
        if self.effect:
            properties.update({"step": {"enum": [PLAN_STEP, APPLY_STEP],
                                        "description": "plan first; apply with the plan digest the plan returned"},
                               "plan_digest": {"type": "string", "pattern": DIGEST_PATTERN},
                               "request_id": {"type": "string", "pattern": REQUEST_ID_PATTERN,
                                              "description": "a new identity for each apply; a repeat replays"}})
            required = ["step", *required]
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": required}


@dataclass(frozen=True)
class Plan:
    """What an effect would do, and the exact state it was worked out against.

    `guards` are the versions of the records the effect depends on; `facts`
    is what it depends on outside those records, such as the recipients of a
    message, read from the identity provider. Both are in the plan digest.
    """

    summary: dict
    guards: tuple = field(default=(), repr=False)
    tenant_id: str = ""
    target: str = ""
    context: object = field(default=None, repr=False, compare=False)
    facts: object = field(default=None, repr=False)

    @property
    def records(self):
        return sorted([guard.record_id, guard.record_version, guard.must_not_exist]
                      for guard in unique_guards(self.guards))

    @property
    def state(self):
        return {"records": self.records, "facts": self.facts}


def plan_digest(tool, fields, actor, state):
    """The digest an apply must name: the tool, its exact arguments, the caller and the state behind the plan."""
    return digest({"record_type": PLAN_VERSION, "tool": tool, "arguments": fields, "actor": actor.actor_ref,
                   "role": actor.role, "state": state})


def forbid_unless(actor, permission):
    if not actor.may(permission):
        raise ServiceHttpError("staff_tool_forbidden", 403)


@dataclass
class ApplyContext:
    """Everything an apply commits beside its effect: the caller check, the request identity and the audit record."""

    tools: object
    actor: object
    tool: str
    reference: object
    request_id: str
    plan_digest: str
    audit: dict
    plan: Plan

    def _marker(self, store, state, result):
        catalog, runtime = self.tools.runtime._catalog, self.tools.runtime
        return catalog.record(APPLY, (self.actor.actor_ref, self.tool, self.request_id), {
            "record_type": APPLY_VERSION, "tool": self.tool, "plan_digest": self.plan_digest, "state": state,
            "result": result, "at": int(runtime._now())}, tenant_id=self.plan.tenant_id)

    def _event(self, code=""):
        return audit_row(self.tools.runtime, self.reference, step=APPLY_STEP, outcome="ok", code=code,
                         request_id=self.request_id, plan_digest=self.plan_digest, target=self.plan.target,
                         tenant_id=self.plan.tenant_id, **self.audit)

    def _commit(self, store, rows, guards):
        runtime, catalog = self.tools.runtime, self.tools.runtime._catalog
        caller = self.tools.keys.current_guards(store, self.actor)
        # The time check runs again right before the write: a key that expired
        # while the effect was prepared changes nothing.
        if self.actor.expires_at <= runtime._now():
            raise HttpAuthenticationError("staff_key_expired")
        catalog.commit(store, tuple(rows), unique_guards((*caller, *guards)))

    def require_planned_state(self, guards):
        """Refuse an apply whose effect now depends on another state than the plan's."""
        if Plan({}, tuple(guards)).records != self.plan.records:
            raise ServiceHttpError("plan_changed", 409)

    def commit(self, store, rows, guards, result):
        """Commit the effect, its request identity and its audit record in one batch."""
        self.require_planned_state(guards)
        marker, event = self._marker(store, COMPLETED, result), self._event()
        self._commit(store, (*rows, marker, event), (*guards, self.tools.runtime._catalog.guard(None, marker["record_id"]),
                                                     self.tools.runtime._catalog.guard(None, event["record_id"])))
        return result

    def reserve(self, prepare=None):
        """Commit the request identity as in progress before an outside effect.

        `prepare(store)` returns reservation rows and their guards, read and
        written in the same batch, such as the day's message count.
        """
        catalog = self.tools.runtime._catalog
        with catalog.store(write=True) as store:
            rows, guards = prepare(store) if prepare is not None else ((), ())
            marker, event = self._marker(store, IN_PROGRESS, None), self._event()
            self._commit(store, (*rows, marker, event), (*guards, catalog.guard(None, marker["record_id"]),
                                                         catalog.guard(None, event["record_id"])))

    def finish(self, result, state=COMPLETED, prepare=None):
        """Record the outcome of an apply that reached outside the store, with any rows that outcome needs."""
        catalog = self.tools.runtime._catalog
        with catalog.store(write=True) as store:
            held = catalog.read(store, APPLY, (self.actor.actor_ref, self.tool, self.request_id))
            if held is None or held["payload"].get("state") != IN_PROGRESS:
                raise ServiceRuntimeError("concurrent_update")
            rows, guards = prepare(store) if prepare is not None else ((), ())
            catalog.commit(store, (*rows, {**held, "record_version": secrets.token_hex(16),
                                           "payload": {**held["payload"], "state": state, "result": result}}),
                           unique_guards((*guards, catalog.guard(held))))
        return result


class StaffTools:
    """The registry and the call rules of the staff tools, bound to one running service."""

    def __init__(self, application, administration, keys, settings=None, *, catalogue=None):
        self.application, self.administration, self.keys = application, administration, keys
        self.runtime = application.runtime
        self.settings = settings if isinstance(settings, StaffToolSettings) else StaffToolSettings()
        self.catalogue = catalogue
        self.tools = registry()

    def visible(self, actor):
        """The tools one caller may call, for its tool list."""
        return [tool for tool in self.tools.values() if any(actor.may(name) for name in tool.permissions)]

    def _validated(self, tool, arguments):
        from jsonschema import ValidationError, validate
        if not isinstance(arguments, dict):
            raise ServiceHttpError("invalid_request")
        try:
            validate(arguments, tool.input_schema())
        except ValidationError:
            raise ServiceHttpError("invalid_request") from None
        return dict(arguments)

    def _replay(self, actor, tool, request_id, given):
        catalog = self.runtime._catalog
        with catalog.store() as store:
            held = catalog.read(store, APPLY, (actor.actor_ref, tool, request_id))
        if held is None:
            return None
        value = held["payload"]
        if value.get("record_type") != APPLY_VERSION:
            raise ServiceRuntimeError("unsupported_or_corrupt_record")
        if value.get("plan_digest") != given:
            raise ServiceHttpError("staff_request_identity_conflict", 409)
        if value.get("state") == IN_PROGRESS:
            raise ServiceHttpError("staff_apply_in_progress", 409)
        return value

    def call(self, actor, name, arguments, reference, transport):
        """Run one staff tool call for one verified caller, and write its audit record."""
        tool, step = self.tools.get(name), READ_STEP
        audit = {"transport": transport, "tool": name if isinstance(name, str) and name else "unknown",
                 "actor_kind": actor.kind, "actor_ref": actor.actor_ref, "role": actor.role,
                 "arguments_digest": arguments_digest(arguments)}
        try:
            if tool is None:
                raise ServiceHttpError("staff_tool_unknown", 404)
            if not any(actor.may(permission) for permission in tool.permissions):
                raise ServiceHttpError("staff_tool_forbidden", 403)
            fields = self._validated(tool, arguments)
            if not tool.effect:
                result = tool.run(self, actor, fields)
                write_audit(self.runtime, reference, step=READ_STEP, outcome="ok", **audit)
                return {"record_type": RESULT_VERSION, "tool": name, "step": READ_STEP, "result": result}
            step = fields.pop("step")
            given, request_id = fields.pop("plan_digest", None), fields.pop("request_id", None)
            if step == APPLY_STEP:
                if given is None or request_id is None:
                    raise ServiceHttpError("plan_digest_required")
                held = self._replay(actor, name, request_id, given)
                if held is not None:
                    write_audit(self.runtime, reference, step=APPLY_STEP, outcome="ok", code="replayed",
                                request_id=request_id, plan_digest=given, **audit)
                    return {"record_type": RESULT_VERSION, "tool": name, "step": APPLY_STEP, "plan_digest": given,
                            "state": held["state"], "result": held["result"], "replayed": True}
            plan = tool.run(self, actor, fields)
            current = plan_digest(name, fields, actor, plan.state)
            if step == PLAN_STEP:
                write_audit(self.runtime, reference, step=PLAN_STEP, outcome="ok", plan_digest=current,
                            target=plan.target, tenant_id=plan.tenant_id, **audit)
                return {"record_type": PLAN_VERSION, "tool": name, "plan_digest": current, "plan": plan.summary,
                        "apply": "call again with step apply, this plan_digest, the same arguments and a new "
                                 "request_id; nothing has changed yet"}
            if not secrets.compare_digest(given, current):
                raise ServiceHttpError("plan_changed", 409)
            context = ApplyContext(self, actor, name, reference, request_id, current, audit, plan)
            result = tool.apply(self, actor, fields, context)
            return {"record_type": RESULT_VERSION, "tool": name, "step": APPLY_STEP, "plan_digest": current,
                    "state": COMPLETED, "result": result, "replayed": False}
        except Exception as error:
            try:
                write_audit(self.runtime, reference, step=step, outcome="refused",
                            code=getattr(error, "code", "operation_failed"), **audit)
            except Exception:
                # The caller is already being refused. The failure journal keeps
                # the refusal under the same reference.
                pass
            raise


def registry():
    """Every staff tool, by name, from the `TOOLS` tuple of each tool module.

    A new group of operations, such as customer support tickets, adds one
    module with its own `TOOLS` tuple to the list below and its tool names to
    `staff_routes.STAFF_TOOL_NAMES`; a named check holds the two lists together
    and nothing else changes. A tool that sends email, or has any other
    effect, declares an `apply`: it is planned, approved by its plan digest and
    applied under a request identity that replays instead of sending twice.
    """
    from . import account_import, account_messages, staff_tool_accounts, staff_tool_catalogue
    tools = {}
    for module in (staff_tool_accounts, account_import, account_messages, staff_tool_catalogue):
        for tool in module.TOOLS:
            if not isinstance(tool, StaffTool) or tool.name in tools or not tool.permissions:
                raise ServiceRuntimeError("invalid_staff_tool")
            tools[tool.name] = tool
    return tools


def install_staff_tools(application, configuration, *, license_policy=None, family_policy=None):
    """Install the staff tools on a host application that has staff administration, or leave it without them."""
    from .staff_keys import StaffKeys
    from .staff_tool_catalogue import StaffCatalogue
    administration = getattr(application, "account_administration", None)
    if administration is None:
        return None
    settings = (StaffToolSettings.from_host(configuration["staff_tools"]) if configuration.get("staff_tools")
                else StaffToolSettings())
    catalogue = StaffCatalogue.from_host(configuration, settings, license_policy=license_policy,
                                         family_policy=family_policy)
    application.staff_tools = StaffTools(application, administration, StaffKeys(application.runtime, administration),
                                         settings, catalogue=catalogue)
    return application.staff_tools
