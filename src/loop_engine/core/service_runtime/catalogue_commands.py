"""Operator commands for catalogue releases, run on the host that owns the service store.

Every command reads the host file first and refuses unless it declares its
`catalogue` section. That is deliberate: a release that predates catalogue
state refuses a host file with a section it does not know, so once any
catalogue state exists, an image that could ignore it cannot start against
this host. `catalogue-status` only reads. The others write through the
atomic batch contract of the service store and print one result record.

```text
loop-engine service
├── publish-catalogue                  validate a bundle, write bodies and records, move the pointer
├── rollback-catalogue                 move the pointer to an earlier, fully verified release
├── withdraw-catalogue-item            record a durable withdrawal that every release and rollback honours
├── catalogue-status                   report the state version, the active release and every release
├── follow-catalogue-release           move named accounts, or with --all-tenants only the accounts
│                                      already granted every served item, to grants that follow the release
└── stop-following-catalogue-release   return one account to a fixed list of what it receives now
```

The two grant commands read the catalogue the host serves now, built the way
the service builds it at start, so a decision is taken on what accounts are
actually offered.
"""
from __future__ import annotations

from pathlib import Path

from .records import ServiceRuntimeConfig, ServiceRuntimeError
from .storage import ServiceCatalogBinding

CATALOGUE_COMMANDS = ("publish-catalogue", "rollback-catalogue", "withdraw-catalogue-item",
                      "catalogue-status", "follow-catalogue-release", "stop-following-catalogue-release")


def _refuse(code, message):
    raise ServiceRuntimeError(code, message)


def _host(path, *, needs_bodies=False):
    """Read the host file for one catalogue command, refusing a host without its catalogue section."""
    from .catalogue_serving import catalogue_settings, catalogue_state_gate
    from .http_entrypoint import HOST_CONFIGURATION_VERSION, _host_json
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
    return configuration, settings, config


def operator_context(path, *, needs_bodies=False):
    """The operator context, runtime settings and host policies of one catalogue command."""
    from .catalogue_releases import CatalogueOperatorContext
    from .http_entrypoint import host_family_policy, host_license_policy
    configuration, settings, config = _host(path, needs_bodies=needs_bodies)
    context = CatalogueOperatorContext(ServiceCatalogBinding(config), settings.body_store_root)
    return context, config, host_license_policy(configuration), host_family_policy(configuration)


def served_view(path):
    """The runtime of the host file and the catalogue view it serves now, built as the service builds it at start."""
    from .catalogue_serving import load_catalogue_view
    from .http_entrypoint import host_family_policy, host_license_policy
    from .runtime import ServiceRuntime
    configuration, _settings, config = _host(path)
    view, _source = load_catalogue_view(configuration, config, license_policy=host_license_policy(configuration),
                                        family_policy=host_family_policy(configuration))
    return ServiceRuntime(config), view


def publish_catalogue(path, bundle_folder, *, expected_bundle_digest, expected_release=None):
    from .catalogue_bundle import read_bundle
    from .catalogue_releases import publish
    context, _config, license_policy, family_policy = operator_context(path, needs_bodies=True)
    bundle = read_bundle(Path(bundle_folder), license_policy=license_policy, family_policy=family_policy,
                         verify_blobs=False)
    if bundle.digest != expected_bundle_digest:
        _refuse("bundle_digest_mismatch", "the bundle header differs from the digest its builder printed")
    return publish(context, bundle, expected_release=expected_release)


def _grant_command(command, arguments):
    """Follow or stop following, for the accounts one command names."""
    from .catalogue_grants import follow_accounts_already_granted, follow_active_release, stop_following_release
    denials = tuple(arguments.deny or ())
    if command == "stop-following-catalogue-release":
        if not arguments.tenant or arguments.all_tenants or denials:
            _refuse("invalid_request", "stop-following-catalogue-release names one --tenant, with no --all-tenants "
                                       "and no --deny")
        runtime, view = served_view(arguments.config)
        return stop_following_release(runtime, arguments.tenant, view)
    if bool(arguments.tenant) == bool(arguments.all_tenants):
        _refuse("invalid_request", "name one --tenant or --all-tenants")
    if arguments.all_tenants:
        runtime, view = served_view(arguments.config)
        return follow_accounts_already_granted(runtime, view, denials=denials)
    from .runtime import ServiceRuntime
    _context, config, *_rest = operator_context(arguments.config)
    return follow_active_release(ServiceRuntime(config), [arguments.tenant], denials=denials)


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
    if command in ("follow-catalogue-release", "stop-following-catalogue-release"):
        return _grant_command(command, arguments)
    _refuse("invalid_request", "not a catalogue command")
