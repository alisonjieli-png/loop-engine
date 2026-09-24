"""Reviewer engine ``provider_binding``: one organisation endpoint named by a committed provider binding.

The installation names a provider binding that the repository commits, the same
record the candidate generator reads: the endpoint, its TLS trust contract, the
family evidence, the measured output capacity and the name of an operator
credential reference. The binding must declare the review purpose the
installation uses, so a binding committed for generation only is refused here.

The engine validates the binding at the checkout's current commit with the
generator's own loader, before any credential is read, and refuses a binding
whose bytes differ from the committed ones or from the digest the installation
names, whose model or family differs from the installation's, or whose measured
capacity is smaller than the output allocation. Only then is the credential
resolved, inside this process, by the resolver the host supplies. The
credential stays in the provider object in memory and reaches only the request
header; it is never written, printed or recorded.

Every call goes through the repository's ``ModelGateway`` with one route, no
failover and a typed output allocation within the binding's measured capacity,
exactly as the ``model_gateway`` engine does for a hosted model. The answering
model is the one the endpoint reports in its response.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

from loop_engine.core.model_routes import PURPOSES, ModelRoute, RouteViolation, screen_route

from ..configuration import thawed
from ..records import SHA256, positive_integer, positive_number, read_part, refuse, text_field
from ..verdicts import ANSWER_FORMATS, JSON_ONLY
from . import (
    AUTHENTICATION_UNAVAILABLE, ENGINE_UNAVAILABLE, REFUSED_BY_ROUTE_POLICY, Availability, ReviewerAttempt, failed,
)
from .gateway import invoke_once

SETTINGS_FIELDS = ("binding_path", "binding_sha256", "route_name", "purpose", "timeout_seconds")
#: Optional settings: an output allocation within the binding's measured capacity (otherwise the panel
#: policy's), and the answer format the model uses (otherwise ``json_only``).
OPTIONAL_FIELDS = ("output_allocation_tokens", "answer_format")
#: The generator's refusal code for an unavailable credential, which this engine reports as a refused login.
CREDENTIAL_UNAVAILABLE = "provider_credential_unavailable"
GIT_TIMEOUT_SECONDS = 30.0


def checkout_revision(repository: Path) -> str:
    """The commit the checkout stands on; a binding is read only as committed there."""
    try:
        finished = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True,
                                  text=True, timeout=GIT_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.SubprocessError):
        return ""
    revision = finished.stdout.strip()
    return revision if finished.returncode == 0 and len(revision) == 40 else ""


class BindingReviewer:
    """One installation of an organisation endpoint, reached only through its committed binding."""

    def __init__(self, installation, policy, context) -> None:
        raw = thawed(installation.settings)
        optional = {name: raw.pop(name) for name in OPTIONAL_FIELDS if name in raw}
        settings = read_part(raw, installation.installation_id, SETTINGS_FIELDS)
        self.installation, self.policy = installation, policy
        self.binding_path = text_field(settings["binding_path"], "binding_path", limit=400)
        if type(settings["binding_sha256"]) is not str or not SHA256.fullmatch(settings["binding_sha256"]):
            refuse("installation_setting_invalid", "binding_sha256 is the exact SHA-256 of the committed binding")
        self.binding_sha256 = settings["binding_sha256"]
        self.route_name = text_field(settings["route_name"], "route_name", limit=200)
        if settings["purpose"] not in PURPOSES:
            refuse("installation_setting_invalid", f"purpose is one of {list(PURPOSES)}")
        self.purpose = settings["purpose"]
        self.timeout_seconds = positive_number(settings["timeout_seconds"], "timeout_seconds")
        self.output_allocation_tokens = (positive_integer(optional["output_allocation_tokens"],
                                                          "output_allocation_tokens")
                                         if "output_allocation_tokens" in optional else None)
        self.answer_format = optional.get("answer_format", JSON_ONLY)
        if self.answer_format not in ANSWER_FORMATS:
            refuse("installation_setting_invalid", f"answer_format is one of {list(ANSWER_FORMATS)}")
        self.repository = Path(context.repository) if context.repository is not None else None
        self.resolver = context.credential_resolver
        self.binding, self.spec, self.route = None, None, None
        self._availability = None

    @property
    def route_or_command(self) -> str:
        return f"{self.spec.provider_id if self.spec is not None else 'binding'}:{self.route_name}"

    def availability(self) -> Availability:
        if self._availability is None:
            self._availability = self._load()
        return self._availability

    def _load(self) -> Availability:
        if self.repository is None:
            return Availability(False, "no checkout was supplied to read the committed binding from", "", {},
                                ENGINE_UNAVAILABLE)
        if self.resolver is None:
            return Availability(False, "no operator credential resolver was supplied", "", {},
                                AUTHENTICATION_UNAVAILABLE)
        from tools import generate_original_native_candidates as generation
        revision = checkout_revision(self.repository)
        if not revision:
            return Availability(False, "the checkout's commit could not be read", "", {}, ENGINE_UNAVAILABLE)
        try:
            binding = generation.load_provider_binding(self.repository, revision, self.binding_path,
                                                       self.binding_sha256, self.installation.model,
                                                       self.installation.family, purpose=self.purpose)
        except generation.GenerationError as error:
            return Availability(False, f"the provider binding is refused: {error}", "", {}, ENGINE_UNAVAILABLE)
        allocation = self.output_allocation_tokens or self.policy.output_allocation_tokens
        if binding.capability.declared_maximum is None or binding.capability.declared_maximum < allocation:
            return Availability(False, "the declared output allocation exceeds the binding's measured capacity", "",
                                {}, ENGINE_UNAVAILABLE)
        try:
            spec = generation.binding_provider_spec(self.repository, binding, self.resolver)
        except generation.GenerationError as error:
            code = str(error)
            return Availability(False, f"the provider could not be built: {code}", "", {},
                                AUTHENTICATION_UNAVAILABLE if code == CREDENTIAL_UNAVAILABLE else ENGINE_UNAVAILABLE)
        try:
            route = screen_route(ModelRoute(self.route_name, spec.provider_id, self.installation.model, spec.locality,
                                            purposes=(self.purpose,)), purpose=self.purpose)
        except (ValueError, RouteViolation) as error:
            return Availability(False, "the model policy refuses this route: " + str(error)[:300], "", {},
                                REFUSED_BY_ROUTE_POLICY)
        self.binding, self.spec, self.route = binding, spec, route
        return Availability(True, "", f"provider_binding/{binding.binding_id}",
                            {"binding_sha256": binding.sha256, "endpoint": binding.settings.endpoint,
                             "capacity_sha256": binding.capacity_sha256,
                             "tls_pinned_sha256": binding.settings.tls_pinned_sha256 or ""})

    def review(self, prompt, allowance) -> ReviewerAttempt:
        probe = self.availability()
        if not probe.available:
            return failed(probe.reason_code or ENGINE_UNAVAILABLE, self.route_or_command, probe.reason)
        return invoke_once(self.spec, self.route, self.installation.model, self.purpose, prompt, allowance,
                           min(allowance.timeout_seconds, self.timeout_seconds), self.route_or_command)
