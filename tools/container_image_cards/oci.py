"""Read an image index, a manifest and an image config into the facts a card states, by the OCI image specification.

```text
one tag family's documents, each read by digest and checked against it (registry.py)
├── index (OCI image index or Docker manifest list): one descriptor per platform image; attestation manifests
│   (platform unknown/unknown, vnd.docker.reference.type attestation-manifest) are not images and are left out
├── manifest (OCI or Docker schema 2) of each platform: its config descriptor and its layers (count and compressed
│   bytes; a Windows foreign layer is counted and named as foreign)
└── config of each platform: the runtime facts (Entrypoint, Cmd, Env, ExposedPorts, Volumes, WorkingDir, User,
    StopSignal, Healthcheck, Labels, OnBuild, Shell), its os, architecture, variant and os.version
```

The history (the build's commands) is never read into a card: it is the image's own build code, not a fact about
running it. Nothing here reads the network.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .registry import CONFIG_TYPES, INDEX_TYPES, MANIFEST_TYPES, RegistryError, digest_hex

#: The keys of an index descriptor, a manifest, a platform and an image config, as the specifications name them.
MEDIA_TYPE, DIGEST, SIZE, PLATFORM, ANNOTATIONS, MANIFESTS, CONFIG, LAYERS = (
    "mediaType", "digest", "size", "platform", "annotations", "manifests", "config", "layers")
OS, ARCHITECTURE, VARIANT, OS_VERSION, OS_FEATURES = "os", "architecture", "variant", "os.version", "os.features"
(ENTRYPOINT, CMD, ENV, EXPOSED_PORTS, VOLUMES, WORKING_DIR, USER, STOP_SIGNAL, HEALTHCHECK, LABELS, ON_BUILD,
 SHELL) = CONFIG_FIELDS = ("Entrypoint", "Cmd", "Env", "ExposedPorts", "Volumes", "WorkingDir", "User", "StopSignal",
                          "Healthcheck", "Labels", "OnBuild", "Shell")
HEALTH_TEST, HEALTH_FIELDS = "Test", (("Interval", "interval_ns"), ("Timeout", "timeout_ns"),
                                      ("StartPeriod", "start_period_ns"), ("StartInterval", "start_interval_ns"),
                                      ("Retries", "retries"))
#: A healthcheck whose test is this word turns off a check the base image declared.
HEALTH_NONE = "NONE"
#: The annotation that marks an attestation manifest in an index, and the platform such a manifest names.
REFERENCE_TYPE, ATTESTATION = "vnd.docker.reference.type", "attestation-manifest"
UNKNOWN_PLATFORM = "unknown"
#: A layer Docker downloads from another host than the registry (Windows base layers).
FOREIGN_LAYER_TYPES = ("application/vnd.docker.image.rootfs.foreign.diff.tar.gzip",
                       "application/vnd.oci.image.layer.nondistributable.v1.tar+gzip")
#: The annotations a card reads from an index descriptor or a manifest (OCI pre-defined keys, and the bashbrew
#: architecture the Docker Official Images add).
ANNOTATION_KEYS = {"org.opencontainers.image.created": "created", "org.opencontainers.image.version": "version",
                   "org.opencontainers.image.revision": "revision", "org.opencontainers.image.source": "source",
                   "org.opencontainers.image.url": "url", "org.opencontainers.image.base.name": "base_name",
                   "org.opencontainers.image.base.digest": "base_digest",
                   "com.docker.official-images.bashbrew.arch": "bashbrew_arch"}
PORT_KEY = re.compile(r"(\d{1,5})(?:-(\d{1,5}))?(?:/([a-z]+))?")
DEFAULT_PROTOCOL = "tcp"
PROTOCOLS = ("tcp", "udp", "sctp")
#: The most ports one exposed range may stand for before the config is refused as unreadable.
MAXIMUM_PORT_RANGE = 1024
ENV_SEPARATOR = "="


class DocumentError(ValueError):
    """A document a card cannot be written from, with a stable reason."""

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason, self.detail = reason, detail


MANIFEST_UNSUPPORTED, CONFIG_UNREADABLE, NO_PLATFORM = "manifest_unsupported", "config_unreadable", "no_platform"


def descriptor(value: dict) -> dict:
    """{digest, media_type, size} of a content descriptor; raises DocumentError for one that cannot be pinned."""
    if not isinstance(value, dict):
        raise DocumentError(MANIFEST_UNSUPPORTED, "a descriptor is not an object")
    digest, size = value.get(DIGEST), value.get(SIZE)
    try:
        digest_hex(digest)
    except RegistryError:
        raise DocumentError(MANIFEST_UNSUPPORTED, f"a descriptor's digest {str(digest)[:80]}") from None
    if type(size) is not int or size < 0:
        raise DocumentError(MANIFEST_UNSUPPORTED, f"a descriptor's size {size!r}")
    return {"digest": digest, "media_type": str(value.get(MEDIA_TYPE, "")), "size": size}


def platform_name(os_name: str, architecture: str, variant: "str | None") -> str:
    """os/architecture[/variant], the form docker run --platform takes."""
    return "/".join(part for part in (os_name, architecture, variant) if part)


def selected_annotations(values) -> dict:
    """The annotations a card states, by their short names."""
    if not isinstance(values, dict):
        return {}
    return {short: str(values[key]) for key, short in ANNOTATION_KEYS.items() if isinstance(values.get(key), str)}


@dataclass(frozen=True)
class PlatformEntry:
    """One platform image an index lists: its platform and its manifest descriptor and annotations."""

    os: str
    architecture: str
    variant: "str | None"
    os_version: "str | None"
    os_features: tuple
    manifest: dict
    annotations: dict

    @property
    def platform(self) -> str:
        return platform_name(self.os, self.architecture, self.variant)


def is_attestation(value: dict) -> bool:
    annotations = value.get(ANNOTATIONS) if isinstance(value.get(ANNOTATIONS), dict) else {}
    platform = value.get(PLATFORM) if isinstance(value.get(PLATFORM), dict) else {}
    return annotations.get(REFERENCE_TYPE) == ATTESTATION or UNKNOWN_PLATFORM in (platform.get(OS),
                                                                                    platform.get(ARCHITECTURE))


def read_index(document: dict, media_type: str) -> list:
    """[PlatformEntry] of an image index or manifest list, attestations left out; raises DocumentError."""
    declared = document.get(MEDIA_TYPE) or media_type
    if declared not in INDEX_TYPES or document.get("schemaVersion") != 2:
        raise DocumentError(MANIFEST_UNSUPPORTED, f"not an image index: {str(declared)[:80]}")
    entries = []
    for value in document.get(MANIFESTS) or []:
        if not isinstance(value, dict) or is_attestation(value):
            continue
        platform = value.get(PLATFORM)
        if not isinstance(platform, dict) or not platform.get(OS) or not platform.get(ARCHITECTURE):
            raise DocumentError(MANIFEST_UNSUPPORTED, "an index descriptor names no platform")
        manifest = descriptor(value)
        if manifest["media_type"] not in MANIFEST_TYPES:
            raise DocumentError(MANIFEST_UNSUPPORTED, f"a platform manifest of type {manifest['media_type'][:80]}")
        features = platform.get(OS_FEATURES) if isinstance(platform.get(OS_FEATURES), list) else []
        entries.append(PlatformEntry(str(platform[OS]), str(platform[ARCHITECTURE]), platform.get(VARIANT) or None,
                                     platform.get(OS_VERSION) or None, tuple(str(item) for item in features),
                                     manifest, selected_annotations(value.get(ANNOTATIONS))))
    if not entries:
        raise DocumentError(NO_PLATFORM, "the index lists no platform image")
    names = [entry.platform + (entry.os_version or "") for entry in entries]
    if len(set(names)) != len(names):
        raise DocumentError(MANIFEST_UNSUPPORTED, "the index lists one platform twice")
    return entries


def read_manifest(document: dict, media_type: str) -> dict:
    """{config, layers, compressed_bytes, foreign_layers, annotations} of one image manifest; raises DocumentError."""
    declared = document.get(MEDIA_TYPE) or media_type
    if declared not in MANIFEST_TYPES or document.get("schemaVersion") != 2:
        raise DocumentError(MANIFEST_UNSUPPORTED, f"not an image manifest: {str(declared)[:80]}")
    config = descriptor(document.get(CONFIG))
    if config["media_type"] not in CONFIG_TYPES:
        raise DocumentError(MANIFEST_UNSUPPORTED, f"a config of type {config['media_type'][:80]}")
    layers = [descriptor(layer) for layer in document.get(LAYERS) or []]
    return {"config": config, "layers": len(layers), "compressed_bytes": sum(layer["size"] for layer in layers),
            "foreign_layers": sum(1 for layer in layers if layer["media_type"] in FOREIGN_LAYER_TYPES),
            "annotations": selected_annotations(document.get(ANNOTATIONS))}


def _strings(value, label: str) -> "list | None":
    if value is None:
        return None
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise DocumentError(CONFIG_UNREADABLE, f"{label} is not a list of strings")
    return list(value)


def ports(value) -> list:
    """[{port, protocol}] of a config's ExposedPorts keys ("80/tcp", "53/udp", "8000-8001/tcp"), sorted."""
    if value is None:
        return []
    if not isinstance(value, dict):
        raise DocumentError(CONFIG_UNREADABLE, "ExposedPorts is not an object")
    found = set()
    for key in value:
        match = PORT_KEY.fullmatch(str(key))
        protocol = (match.group(3) or DEFAULT_PROTOCOL) if match else ""
        if not match or protocol not in PROTOCOLS:
            raise DocumentError(CONFIG_UNREADABLE, f"an exposed port {str(key)[:40]}")
        first, last = int(match.group(1)), int(match.group(2) or match.group(1))
        if not 1 <= first <= last <= 65535 or last - first >= MAXIMUM_PORT_RANGE:
            raise DocumentError(CONFIG_UNREADABLE, f"an exposed port {str(key)[:40]}")
        found.update((number, protocol) for number in range(first, last + 1))
    return [{"port": number, "protocol": protocol} for number, protocol in sorted(found)]


def environment(value) -> list:
    """[{name, value}] of a config's Env, in its order; a repeated name keeps its last value, as a container does."""
    rows = _strings(value, ENV) or []
    found = {}
    for row in rows:
        name, separator, text = row.partition(ENV_SEPARATOR)
        if not name:
            raise DocumentError(CONFIG_UNREADABLE, f"an environment entry without a name: {row[:40]}")
        found[name] = text if separator else None
    return [{"name": name, "value": text} for name, text in found.items()]


def healthcheck(value) -> "dict | None":
    """The healthcheck as a card states it, None when the config declares none."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise DocumentError(CONFIG_UNREADABLE, "Healthcheck is not an object")
    record = {"test": _strings(value.get(HEALTH_TEST), HEALTH_TEST) or []}
    for key, name in HEALTH_FIELDS:
        item = value.get(key)
        if item is not None and (type(item) is not int or item < 0):
            raise DocumentError(CONFIG_UNREADABLE, f"Healthcheck {key} is not a count")
        record[name] = item
    return record


def runtime(document: dict) -> dict:
    """The runtime facts of one image config, in the card's names; raises DocumentError."""
    if not isinstance(document, dict) or not isinstance(document.get(OS), str) or \
            not isinstance(document.get(ARCHITECTURE), str):
        raise DocumentError(CONFIG_UNREADABLE, "the config names no os and architecture")
    config = document.get("config") if document.get("config") is not None else {}
    if not isinstance(config, dict):
        raise DocumentError(CONFIG_UNREADABLE, "the config's config is not an object")
    volumes = config.get(VOLUMES)
    if volumes is not None and not isinstance(volumes, dict):
        raise DocumentError(CONFIG_UNREADABLE, "Volumes is not an object")
    labels = config.get(LABELS)
    if labels is not None and (not isinstance(labels, dict) or any(not isinstance(item, str)
                                                                   for item in labels.values())):
        raise DocumentError(CONFIG_UNREADABLE, "Labels is not an object of strings")
    for key in (WORKING_DIR, USER, STOP_SIGNAL):
        if config.get(key) is not None and not isinstance(config.get(key), str):
            raise DocumentError(CONFIG_UNREADABLE, f"{key} is not a string")
    return {"entrypoint": _strings(config.get(ENTRYPOINT), ENTRYPOINT),
            "command": _strings(config.get(CMD), CMD),
            "working_dir": config.get(WORKING_DIR) or None,
            "user": config.get(USER) or None,
            "stop_signal": config.get(STOP_SIGNAL) or None,
            "shell": _strings(config.get(SHELL), SHELL),
            "healthcheck": healthcheck(config.get(HEALTHCHECK)),
            "on_build": _strings(config.get(ON_BUILD), ON_BUILD) or [],
            "labels": dict(sorted((labels or {}).items())),
            "environment": environment(config.get(ENV)),
            "ports": ports(config.get(EXPOSED_PORTS)),
            "volumes": sorted(str(key) for key in (volumes or {}))}


def config_platform(document: dict) -> dict:
    """{os, architecture, variant, os_version} an image config states for itself."""
    return {"os": str(document.get(OS, "")), "architecture": str(document.get(ARCHITECTURE, "")),
            "variant": document.get(VARIANT) or None, "os_version": document.get(OS_VERSION) or None}


__all__ = ["DocumentError", "PlatformEntry", "read_index", "read_manifest", "runtime", "config_platform",
           "platform_name", "descriptor", "ports", "environment", "healthcheck", "is_attestation",
           "MANIFEST_UNSUPPORTED", "CONFIG_UNREADABLE", "NO_PLATFORM", "CONFIG_FIELDS"]
