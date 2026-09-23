"""Operator commands for catalogue releases, run on the host that owns the service store.

Every command reads the host file first and refuses unless it declares its
`catalogue` section. That is deliberate: a release that predates catalogue
state refuses a host file with a section it does not know, so once any
catalogue state exists, an image that could ignore it cannot start against
this host. `catalogue-status` only reads. The others write through the
atomic batch contract of the service store and print one result record.

```text
loop-engine service
├── publish-catalogue         validate a bundle, write bodies and records, move the pointer
├── rollback-catalogue        move the pointer to an earlier, fully verified release
├── withdraw-catalogue-item   record a durable withdrawal that every release and rollback honours
├── catalogue-status          report the state version, the active release and every release
└── follow-catalogue-release  move accounts to the grants engine that follows the active release
```
"""
from __future__ import annotations

from pathlib import Path

from .records import ServiceRuntimeConfig, ServiceRuntimeError
from .storage import ServiceCatalogBinding

CATALOGUE_COMMANDS = ("publish-catalogue", "rollback-catalogue", "withdraw-catalogue-item",
                      "catalogue-status", "follow-catalogue-release")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def operator_context(path, *, needs_bodies=False):
    """Read the host file for one catalogue command, refusing a host without its catalogue section."""
    from .catalogue_releases import CatalogueOperatorContext
    from .catalogue_serving import catalogue_settings, catalogue_state_gate
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, _host_json, host_family_policy, host_license_policy
    configuration = _host_json(path)
    if configuration.get("record_type") != HOST_CONFIGURATION_VERSION or "runtime" not in configuration:
        _refuse("unsupported_host_configuration", "a host configuration names its record version and runtime")
    settings = catalogue_settings(configuration)
    if settings is None:
        _refuse("catalogue_section_required",
                "declare the catalogue section in the host file before any catalogue state is written, so that "
                "an image which predates catalogue state refuses this host file")
    if needs_bodies and not settings.body_store_root:
        _refuse("catalogue_section_required", "the catalogue section names its body store root")
    config = ServiceRuntimeConfig(**configuration["runtime"])
    catalogue_state_gate(config, settings)
    context = CatalogueOperatorContext(ServiceCatalogBinding(config), settings.body_store_root)
    return context, config, host_license_policy(configuration), host_family_policy(configuration)


def publish_catalogue(path, bundle_folder, *, expected_bundle_digest, expected_release=None):
    from .catalogue_bundle import read_bundle
    from .catalogue_releases import publish
    context, _config, license_policy, family_policy = operator_context(path, needs_bodies=True)
    bundle = read_bundle(Path(bundle_folder), license_policy=license_policy, family_policy=family_policy,
                         verify_blobs=False)
    if bundle.digest != expected_bundle_digest:
        _refuse("bundle_digest_mismatch", "the bundle header differs from the digest its builder printed")
    return publish(context, bundle, expected_release=expected_release)


def run_catalogue_command(arguments):
    """Dispatch one parsed catalogue command and return its result record."""
    from .catalogue_releases import rollback, status, withdraw
    command, path = arguments.command, arguments.config
    if command == "publish-catalogue":
        if not arguments.bundle or not arguments.expected_bundle_digest:
            _refuse("invalid_request", "publish-catalogue needs --bundle and --expected-bundle-digest")
        return publish_catalogue(path, arguments.bundle, expected_bundle_digest=arguments.expected_bundle_digest,
                                 expected_release=arguments.expected_release)
    if command == "rollback-catalogue":
        if not arguments.to_release or not arguments.expected_release:
            _refuse("invalid_request", "rollback-catalogue needs --to-release and --expected-release")
        context, *_rest = operator_context(path, needs_bodies=True)
        return rollback(context, to_release=arguments.to_release, expected_release=arguments.expected_release)
    if command == "withdraw-catalogue-item":
        if not arguments.identity or arguments.note is None:
            _refuse("invalid_request", "withdraw-catalogue-item needs --identity and --note")
        context, *_rest = operator_context(path)
        return withdraw(context, identity=arguments.identity, note_text=arguments.note,
                        item_version=arguments.item_version, all_versions=arguments.all_versions)
    if command == "catalogue-status":
        context, *_rest = operator_context(path)
        return status(context)
    if command == "follow-catalogue-release":
        from .catalogue_grants import all_tenants, follow_active_release
        from .runtime import ServiceRuntime
        _context, config, *_rest = operator_context(path)
        if bool(arguments.tenant) == bool(arguments.all_tenants):
            _refuse("invalid_request", "name one --tenant or --all-tenants")
        runtime = ServiceRuntime(config)
        tenants = all_tenants(runtime) if arguments.all_tenants else [arguments.tenant]
        return follow_active_release(runtime, tenants, denials=tuple(arguments.deny or ()))
    _refuse("invalid_request", "not a catalogue command")
